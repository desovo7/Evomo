"""Local Hugging Face Qwen policy for admissible-action selection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol

from evomo.data.schema import JsonValue, TaskSpec, _copy_json_mapping
from evomo.policies.contracts import ActionDecision, PolicyInput
from evomo.policies.alfworld_state import (
    reconstruct_alfworld_state,
    repair_unavailable_action,
)
from evomo.experience import ExperienceSet, choose_experience_override

_ACTION_PATTERN = re.compile(r"<action>\s*(\d+)\s*</action>", re.IGNORECASE)
_BARE_INDEX_PATTERN = re.compile(r"^\s*(\d+)\s*$")
_INDEX_AND_ACTION_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(.+?)\s*$")
_PLAN_ACTION_PATTERN = re.compile(
    r"<plan>\s*(.*?)\s*</plan>\s*<action>\s*(\d+)\s*</action>",
    re.IGNORECASE | re.DOTALL,
)
_THINK_ACTION_PATTERN = re.compile(
    r"<think>\s*(.*?)\s*</think>\s*<action>\s*(.*?)\s*</action>",
    re.IGNORECASE | re.DOTALL,
)
_ACTION_TEXT_PATTERN = re.compile(
    r"<action>\s*(.*?)\s*</action>",
    re.IGNORECASE | re.DOTALL,
)

ANTI_LOOP_SKILL = (
    "If the previous action produced the same observation or no useful new "
    "information, do not repeat it. Choose a different admissible action that "
    "explores an unvisited location or directly advances the next task subgoal."
)


class PromptVariant(str, Enum):
    """Controlled action-prompt variants used by the baseline ablation."""

    INDEX_BASELINE = "index_baseline"
    PLAN_THEN_INDEX = "plan_then_index"
    THINK_THEN_ACTION_TEXT = "think_then_action_text"
    ANTI_LOOP_SKILL = "anti_loop_skill"
    STATE_TRACKED_ACTION_TEXT = "state_tracked_action_text"
    STATE_TRACKED_REPAIRED_ACTION = "state_tracked_repaired_action"
    EXPERIENCE_CONDITIONED_ACTION = "experience_conditioned_action"
    EXPERIENCE_GUIDED_ACTION = "experience_guided_action"


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
                "model_id": self.model_path.name,
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
    prompt_variant: PromptVariant = PromptVariant.INDEX_BASELINE,
    skill_text: str = "",
    state_text: str = "",
    experience_text: str = "",
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
    context = (
        f"Goal: {policy_input.task.goal}\n"
        f"Task type: {policy_input.task.task_type}\n"
        f"Recent history:\n{history_text}\n\n"
        f"Current observation:\n{policy_input.observation}\n\n"
        f"Admissible actions:\n{action_text}\n"
    )
    if prompt_variant is PromptVariant.PLAN_THEN_INDEX:
        instruction = (
            "Write one short plan describing the immediate subgoal, then select the "
            "single best listed action. Reply only with "
            "<plan>SHORT PLAN</plan><action>INDEX</action>."
        )
    elif prompt_variant is PromptVariant.THINK_THEN_ACTION_TEXT:
        instruction = (
            "Reason briefly about the next subgoal, then copy exactly one complete "
            "action from the admissible action list. Reply only with "
            "<think>BRIEF REASONING</think><action>EXACT ACTION TEXT</action>."
        )
    else:
        instruction = (
            "Choose the single best next action. Reply only with "
            "<action>INDEX</action>, where INDEX is one listed integer."
        )
    if prompt_variant in (
        PromptVariant.STATE_TRACKED_ACTION_TEXT,
        PromptVariant.STATE_TRACKED_REPAIRED_ACTION,
        PromptVariant.EXPERIENCE_CONDITIONED_ACTION,
        PromptVariant.EXPERIENCE_GUIDED_ACTION,
    ):
        instruction = (
            "Use the reconstructed state and task recipe. Do not pick an unrelated "
            "object. Do not undo a completed placement. If an action is listed as "
            "making no progress, choose a different useful action. Copy exactly one "
            "complete admissible action and reply only with "
            "<action>EXACT ACTION TEXT</action>."
        )
    skill_section = f"\n\nEpisode-level skill:\n[{skill_text.strip()}]" if skill_text.strip() else ""
    state_section = f"\n\nReconstructed task state:\n{state_text.strip()}" if state_text.strip() else ""
    experience_section = (
        f"\n\nLearned experience rules:\n{experience_text.strip()}"
        if experience_text.strip()
        else ""
    )
    user_content = f"{context}{state_section}{experience_section}{skill_section}\n\n{instruction}"
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
        prompt_variant: PromptVariant | str = PromptVariant.INDEX_BASELINE,
        skill_text: str = "",
        experiences: ExperienceSet | None = None,
        experience_provenance: Mapping[str, JsonValue] | None = None,
    ) -> None:
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError("policy_id must be a non-empty string")
        if not isinstance(max_history_items, int) or max_history_items < 0:
            raise ValueError("max_history_items must be a non-negative integer")
        self._generator = generator
        self._prompt_variant = PromptVariant(prompt_variant)
        if self._prompt_variant is PromptVariant.ANTI_LOOP_SKILL and not skill_text.strip():
            skill_text = ANTI_LOOP_SKILL
        self._skill_text = skill_text.strip()
        self._experiences = experiences
        self._experience_provenance = _copy_json_mapping(
            "experience_provenance", experience_provenance or {}
        )
        if (
            self._prompt_variant in (
                PromptVariant.EXPERIENCE_CONDITIONED_ACTION,
                PromptVariant.EXPERIENCE_GUIDED_ACTION,
            )
            and experiences is None
        ):
            raise ValueError("experience-guided policy requires an ExperienceSet")
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
            prompt_variant=self._prompt_variant,
            skill_text=self._skill_text,
            state_text=(
                reconstruct_alfworld_state(
                    policy_input.task,
                    policy_input.history,
                    policy_input.observation,
                ).render()
                if self._prompt_variant in (
                    PromptVariant.STATE_TRACKED_ACTION_TEXT,
                    PromptVariant.STATE_TRACKED_REPAIRED_ACTION,
                    PromptVariant.EXPERIENCE_CONDITIONED_ACTION,
                    PromptVariant.EXPERIENCE_GUIDED_ACTION,
                )
                else ""
            ),
            experience_text=(
                self._experiences.render(policy_input.task.task_type)
                if self._experiences is not None
                and self._experiences.applicable_rules(policy_input.task.task_type)
                else ""
            ),
        )
        generation = self._generator.generate(messages)
        reasoning_text = ""
        state_snapshot = None
        proposed_action = None
        repair_reason = None
        if self._prompt_variant in (
            PromptVariant.STATE_TRACKED_ACTION_TEXT,
            PromptVariant.STATE_TRACKED_REPAIRED_ACTION,
            PromptVariant.EXPERIENCE_CONDITIONED_ACTION,
            PromptVariant.EXPERIENCE_GUIDED_ACTION,
        ):
            reconstructed_state = reconstruct_alfworld_state(
                policy_input.task,
                policy_input.history,
                policy_input.observation,
            )
            state_snapshot = reconstructed_state.to_dict()
            action_match = _ACTION_TEXT_PATTERN.fullmatch(generation.text.strip())
            action_text = action_match.group(1).strip() if action_match else ""
            proposed_action = action_text or None
            parsed_index = None
            if action_text:
                for index, candidate in enumerate(policy_input.admissible_actions):
                    if action_text.casefold() == candidate.casefold():
                        parsed_index = index
                        break
            parse_ok = parsed_index is not None
            required_format_ok = parse_ok and action_match is not None
            parse_format = "tagged_exact_action" if parse_ok else None
            selected_index = parsed_index if parse_ok else 0
            if not parse_ok and action_text and self._prompt_variant in (
                PromptVariant.STATE_TRACKED_REPAIRED_ACTION,
                PromptVariant.EXPERIENCE_GUIDED_ACTION,
            ):
                repaired = repair_unavailable_action(
                    action_text,
                    policy_input.admissible_actions,
                    reconstructed_state,
                )
                if repaired is not None:
                    selected_index, repair_reason = repaired
                    parse_format = "repaired_future_intent"
        elif self._prompt_variant is PromptVariant.THINK_THEN_ACTION_TEXT:
            think_match = _THINK_ACTION_PATTERN.fullmatch(generation.text.strip())
            selected_index = None
            parse_format = None
            required_format_ok = False
            if think_match:
                reasoning_text = think_match.group(1).strip()
                action_text = think_match.group(2).strip()
                required_format_ok = bool(reasoning_text)
            else:
                action_match = _ACTION_TEXT_PATTERN.fullmatch(generation.text.strip())
                indexed_match = _INDEX_AND_ACTION_PATTERN.fullmatch(generation.text)
                if action_match:
                    action_text = action_match.group(1).strip()
                    parse_format = "tagged_exact_action_without_think"
                elif indexed_match:
                    action_text = indexed_match.group(2).strip()
                    parse_format = "index_and_exact_action_without_think"
                else:
                    action_text = ""
            if action_text:
                for index, candidate in enumerate(policy_input.admissible_actions):
                    if action_text.casefold() == candidate.casefold():
                        selected_index = index
                        if think_match:
                            parse_format = "think_and_exact_action"
                        break
            parse_ok = selected_index is not None
            parsed_index = selected_index
            selected_index = selected_index if parse_ok else 0
        elif self._prompt_variant is PromptVariant.PLAN_THEN_INDEX:
            plan_match = _PLAN_ACTION_PATTERN.fullmatch(generation.text.strip())
            parsed_index = int(plan_match.group(2)) if plan_match else None
            reasoning_text = plan_match.group(1).strip() if plan_match else ""
            parse_format = "plan_and_tagged_index" if plan_match else None
            parse_ok = parsed_index is not None and parsed_index < len(policy_input.admissible_actions)
            required_format_ok = parse_ok and bool(reasoning_text)
            selected_index = parsed_index if parse_ok else 0
        else:
            required_format_ok = False
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
            required_format_ok = parse_ok and parse_format == "tagged_index"
        assert selected_index is not None

        experience_override_reason = None
        experience_rule_ids: tuple[str, ...] = ()
        experience_version = None
        applicable_rule_ids: tuple[str, ...] = ()
        if self._prompt_variant in (
            PromptVariant.EXPERIENCE_CONDITIONED_ACTION,
            PromptVariant.EXPERIENCE_GUIDED_ACTION,
        ):
            assert self._experiences is not None
            experience_version = self._experiences.version
            applicable_rule_ids = tuple(
                rule.rule_id
                for rule in self._experiences.applicable_rules(policy_input.task.task_type)
            )
            if self._prompt_variant is PromptVariant.EXPERIENCE_GUIDED_ACTION:
                override = choose_experience_override(
                    task=policy_input.task,
                    state=reconstructed_state,
                    proposed_action=proposed_action,
                    admissible_actions=policy_input.admissible_actions,
                    experiences=self._experiences,
                )
                if override is not None:
                    selected_index = override.action_index
                    experience_override_reason = override.reason
                    experience_rule_ids = override.rule_ids
                    repair_reason = None

        return ActionDecision(
            action=policy_input.admissible_actions[selected_index],
            policy_id=self.policy_id,
            source=(
                "experience_override"
                if experience_override_reason
                else "model_generation"
                if parse_ok
                else "state_prerequisite_repair"
                if repair_reason
                else "fallback_first_admissible"
            ),
            metadata={
                "raw_response": generation.text,
                "reasoning": reasoning_text,
                "prompt_variant": self._prompt_variant.value,
                "skill_text": self._skill_text,
                "state_before": state_snapshot,
                "proposed_action": proposed_action,
                "repair_reason": repair_reason,
                "experience_version": experience_version,
                "experience_provenance": self._experience_provenance,
                "applicable_experience_rule_ids": applicable_rule_ids,
                "experience_override_reason": experience_override_reason,
                "experience_rule_ids": experience_rule_ids,
                "parse_ok": parse_ok,
                "required_format_ok": required_format_ok,
                "parse_format": parse_format,
                "parsed_index": parsed_index,
                "selected_index": selected_index,
                "candidate_count": len(policy_input.admissible_actions),
                "seed": self._seed,
                "generation": dict(generation.metadata),
            },
        )
