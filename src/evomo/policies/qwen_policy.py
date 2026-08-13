"""Local Hugging Face Qwen policy for admissible-action selection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Protocol

from evomo.data.schema import JsonValue, TaskSpec, _copy_json_mapping
from evomo.policies.contracts import ActionDecision, PolicyInput

_ACTION_PATTERN = re.compile(r"<action>\s*(\d+)\s*</action>", re.IGNORECASE)
_BARE_INDEX_PATTERN = re.compile(r"^\s*(\d+)\s*$")
_INDEX_AND_ACTION_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(.+?)\s*$")


@dataclass(frozen=True, slots=True)
class ModelGeneration:
    """Text and runtime metadata returned by a generation backend."""

    text: str
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("generated text must be a string")
        object.__setattr__(self, "metadata", _copy_json_mapping("metadata", self.metadata))


class TextGenerator(Protocol):
    def generate(self, messages: list[dict[str, str]]) -> ModelGeneration: ...


class HuggingFaceQwenGenerator:
    """Load one local Qwen checkpoint and generate short action selections."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        device: str = "cuda:0",
        max_new_tokens: int = 16,
    ) -> None:
        if not isinstance(max_new_tokens, int) or max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be a positive integer")
        self.model_path = Path(model_path).expanduser().resolve()
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Qwen model directory does not exist: {self.model_path}")

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Qwen inference requires torch and transformers>=4.51"
            ) from exc

        self._torch = torch
        self._device = torch.device(device)
        if self._device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable")
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            local_files_only=True,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            local_files_only=True,
            dtype=torch.bfloat16 if self._device.type == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
        ).to(self._device)
        self._model.eval()
        self._max_new_tokens = max_new_tokens

    def generate(self, messages: list[dict[str, str]]) -> ModelGeneration:
        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        prompt_tokens = int(inputs.input_ids.shape[1])
        with self._torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        generated_ids = output[0, prompt_tokens:]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        return ModelGeneration(
            text=text,
            metadata={
                "model_path": str(self.model_path),
                "device": str(self._device),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": int(generated_ids.shape[0]),
                "max_new_tokens": self._max_new_tokens,
                "enable_thinking": False,
                "do_sample": False,
            },
        )


def build_action_messages(
    policy_input: PolicyInput,
    *,
    max_history_items: int,
) -> list[dict[str, str]]:
    """Render a bounded ALFWorld action-selection prompt."""

    history = policy_input.history[-max_history_items:] if max_history_items else ()
    history_lines: list[str] = []
    for item in history:
        history_lines.extend(
            [
                f"Observation: {item.observation}",
                f"Action: {item.action}",
                f"Result: {item.next_observation}",
            ]
        )
    history_text = "\n".join(history_lines) if history_lines else "(none)"
    action_text = "\n".join(
        f"{index}: {action}" for index, action in enumerate(policy_input.admissible_actions)
    )
    user_content = (
        f"Goal: {policy_input.task.goal}\n"
        f"Task type: {policy_input.task.task_type}\n"
        f"Recent history:\n{history_text}\n\n"
        f"Current observation:\n{policy_input.observation}\n\n"
        f"Admissible actions:\n{action_text}\n\n"
        "Choose the single best next action. Reply only with "
        "<action>INDEX</action>, where INDEX is one listed integer."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are an agent acting in the ALFWorld text environment. "
                "Work toward the goal using only the supplied admissible actions. "
                "Track which subgoals are already complete. Avoid repeating an action "
                "that just produced no useful progress when another admissible action "
                "can explore or advance the goal. Never invent an action and never add "
                "explanation."
            ),
        },
        {"role": "user", "content": user_content},
    ]


class QwenPolicy:
    """Select an admissible action using a Qwen text generator."""

    def __init__(
        self,
        generator: TextGenerator,
        *,
        policy_id: str = "qwen3-1.7b-admissible-v1",
        max_history_items: int = 6,
    ) -> None:
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError("policy_id must be a non-empty string")
        if not isinstance(max_history_items, int) or max_history_items < 0:
            raise ValueError("max_history_items must be a non-negative integer")
        self._generator = generator
        self._policy_id = policy_id
        self._max_history_items = max_history_items
        self._task_id: str | None = None
        self._seed: int | None = None

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def reset(self, *, task: TaskSpec, seed: int) -> None:
        if not isinstance(task, TaskSpec):
            raise TypeError("task must be a TaskSpec")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an integer")
        self._task_id = task.task_id
        self._seed = seed

    def decide(self, policy_input: PolicyInput) -> ActionDecision:
        if self._task_id is None or self._seed is None:
            raise RuntimeError("reset() must be called before decide()")
        if policy_input.task.task_id != self._task_id:
            raise ValueError("PolicyInput task does not match the reset task")
        if not policy_input.admissible_actions:
            raise ValueError("cannot choose an action from an empty admissible action set")

        messages = build_action_messages(
            policy_input,
            max_history_items=self._max_history_items,
        )
        generation = self._generator.generate(messages)
        tagged_match = _ACTION_PATTERN.fullmatch(generation.text.strip())
        bare_match = _BARE_INDEX_PATTERN.fullmatch(generation.text)
        indexed_match = _INDEX_AND_ACTION_PATTERN.fullmatch(generation.text)
        parsed_index: int | None = None
        parse_format: str | None = None
        if tagged_match:
            parsed_index = int(tagged_match.group(1))
            parse_format = "tagged_index"
        elif bare_match:
            parsed_index = int(bare_match.group(1))
            parse_format = "bare_index"
        elif indexed_match:
            candidate_index = int(indexed_match.group(1))
            if (
                candidate_index < len(policy_input.admissible_actions)
                and indexed_match.group(2).strip().casefold()
                == policy_input.admissible_actions[candidate_index].casefold()
            ):
                parsed_index = candidate_index
                parse_format = "index_and_exact_action"
        parse_ok = parsed_index is not None and parsed_index < len(policy_input.admissible_actions)
        selected_index = parsed_index if parse_ok else 0
        assert selected_index is not None

        return ActionDecision(
            action=policy_input.admissible_actions[selected_index],
            policy_id=self.policy_id,
            source="model_generation" if parse_ok else "fallback_first_admissible",
            metadata={
                "raw_response": generation.text,
                "parse_ok": parse_ok,
                "parse_format": parse_format,
                "parsed_index": parsed_index,
                "selected_index": selected_index,
                "candidate_count": len(policy_input.admissible_actions),
                "seed": self._seed,
                "generation": dict(generation.metadata),
            },
        )
