"""slime custom-generate adapter for multi-turn ALFWorld GRPO.

The optional slime dependency is imported only inside the async entry point so
the deterministic parsing and reward helpers remain unit-testable in Evomo's
lightweight environment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections import defaultdict
from typing import Mapping, Sequence

from evomo.data import TaskSpec
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment
from evomo.experience import load_experience_set
from evomo.policies import HistoryItem, PolicyInput, PromptVariant
from evomo.policies.alfworld_state import reconstruct_alfworld_state
from evomo.policies.qwen_policy import build_action_messages


_ACTION = re.compile(r"<action>\s*(.*?)\s*</action>", re.IGNORECASE | re.DOTALL)


def parse_exact_admissible_action(
    text: str, admissible_actions: tuple[str, ...]
) -> str | None:
    """Accept only one fully tagged action copied from the current action set."""

    match = _ACTION.fullmatch(text.strip())
    if not match:
        return None
    proposed = match.group(1).strip()
    return next(
        (action for action in admissible_actions if action.casefold() == proposed.casefold()),
        None,
    )


@dataclass(frozen=True, slots=True)
class RewardEvents:
    success: bool
    acquired_target: bool
    completed_operation: bool
    invalid_actions: int
    unchanged_steps: int
    steps: int


def shaped_episode_reward(events: RewardEvents) -> float:
    """Dense development reward whose dominant term remains native success."""

    return (
        float(events.success)
        + 0.10 * int(events.acquired_target)
        + 0.20 * int(events.completed_operation)
        - 0.05 * events.invalid_actions
        - 0.01 * events.unchanged_steps
        - 0.001 * events.steps
    )


def episode_grpo_reward_post_process(args, samples: Sequence) -> tuple[list[float], list[float]]:
    """Normalize rewards across sampled episodes, then broadcast to their turns.

    slime flattens a custom multi-turn result before reward post-processing.  The
    original prompt group survives as ``group_index`` and every sampled episode
    survives as ``index``.  Grouping by both prevents adjacent turns from being
    mistaken for independent GRPO candidates.
    """

    del args
    if not samples:
        raise ValueError("episode GRPO reward post-processing requires samples")
    episode_rows: dict[tuple[int, int], list[int]] = defaultdict(list)
    episode_rewards: dict[tuple[int, int], float] = {}
    group_episodes: dict[int, list[tuple[int, int]]] = defaultdict(list)
    raw_rewards: list[float] = []
    for position, sample in enumerate(samples):
        if sample.group_index is None or sample.index is None:
            raise ValueError("multi-turn samples must retain group_index and index")
        reward = float(sample.reward)
        raw_rewards.append(reward)
        key = (int(sample.group_index), int(sample.index))
        episode_rows[key].append(position)
        if key in episode_rewards and episode_rewards[key] != reward:
            raise ValueError("all turns in one episode must share its terminal reward")
        if key not in episode_rewards:
            episode_rewards[key] = reward
            group_episodes[key[0]].append(key)

    advantages = [0.0] * len(samples)
    for keys in group_episodes.values():
        rewards = [episode_rewards[key] for key in keys]
        mean = sum(rewards) / len(rewards)
        centered = [reward - mean for reward in rewards]
        if len(centered) > 1:
            variance = sum(value * value for value in centered) / (len(centered) - 1)
            scale = variance**0.5 + 1e-6
            centered = [value / scale for value in centered]
        for key, advantage in zip(keys, centered, strict=True):
            for position in episode_rows[key]:
                advantages[position] = advantage
    return raw_rewards, advantages


def _object_type(value: str | None) -> str:
    return re.sub(r"[^a-z]", "", re.sub(r"\s+\d+$", "", value or "").casefold())


async def generate_alfworld_episode(args, sample, sampling_params, evaluation=False):
    """Generate one environment trajectory and return one trainable Sample per turn."""

    from slime.rollout.sglang_rollout import GenerateState, get_model_url
    from slime.utils.http_utils import post
    from slime.utils.types import Sample

    label = sample.label if isinstance(sample.label, Mapping) else {}
    task_value = label.get("task")
    if not isinstance(task_value, Mapping):
        raise ValueError("slime ALFWorld sample label must contain a TaskSpec under 'task'")
    task = TaskSpec.from_dict(task_value)
    data_root = str(getattr(args, "evomo_alfworld_data_root"))
    experience_file = str(getattr(args, "evomo_experience_file"))
    max_steps = int(getattr(args, "evomo_max_episode_steps", 30))
    max_history = int(getattr(args, "evomo_max_history_items", 6))
    experiences = load_experience_set(experience_file)
    generator_state = GenerateState(args)
    tokenizer = generator_state.tokenizer
    generate_url = get_model_url(args, "actor", "/generate")
    environment = AlfworldTextEnvironment(data_root)
    reset = environment.reset(task, seed=int(getattr(args, "rollout_seed", 42)))
    observation = reset.observation
    admissible = reset.admissible_actions
    history: list[HistoryItem] = []
    segments = []
    invalid_actions = 0
    unchanged_steps = 0
    acquired_target = False
    completed_operation = False
    success = bool(reset.info.get("success", False))
    target_params = task.metadata.get("pddl_params", {})
    target = _object_type(
        str(target_params.get("object_target", "")) if isinstance(target_params, Mapping) else ""
    )
    operation = {
        "pick_clean_then_place_in_recep": "clean",
        "pick_cool_then_place_in_recep": "cool",
        "pick_heat_then_place_in_recep": "heat",
    }.get(task.task_type)
    try:
        for step_index in range(max_steps):
            if success:
                break
            policy_input = PolicyInput(
                task=task,
                observation=observation,
                admissible_actions=admissible,
                history=tuple(history),
                step_index=step_index,
            )
            state = reconstruct_alfworld_state(task, tuple(history), observation)
            messages = build_action_messages(
                policy_input,
                max_history_items=max_history,
                prompt_variant=PromptVariant.EXPERIENCE_GUIDED_ACTION,
                state_text=state.render(),
                experience_text=experiences.render(task.task_type),
            )
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
            request = dict(sampling_params)
            request["max_new_tokens"] = min(int(request.get("max_new_tokens", 96)), 96)
            current_stop = request.get("stop") or []
            if isinstance(current_stop, str):
                current_stop = [current_stop]
            request["stop"] = list(dict.fromkeys([*current_stop, "</action>"]))
            output = await post(
                generate_url,
                {"input_ids": prompt_ids, "sampling_params": request, "return_logprob": True},
            )
            response = output["text"]
            logprob_rows = output.get("meta_info", {}).get("output_token_logprobs", ())
            if logprob_rows:
                response_ids = [row[1] for row in logprob_rows]
                log_probs = [row[0] for row in logprob_rows]
            else:
                response_ids = tokenizer(response, add_special_tokens=False)["input_ids"]
                log_probs = None
            action = parse_exact_admissible_action(response, admissible)
            if action is None:
                invalid_actions += 1
                # Execute the literal malformed intent so the environment, not a hidden
                # planner fallback, determines its lack of progress.
                tagged = _ACTION.search(response)
                action = tagged.group(1).strip() if tagged else response.strip() or "invalid"
            transition = environment.step(action)
            unchanged_steps += int(transition.observation.strip() == observation.strip())
            segment = Sample(
                group_index=sample.group_index,
                index=sample.index,
                prompt=prompt,
                tokens=prompt_ids + response_ids,
                response=response,
                response_length=len(response_ids),
                label=sample.label,
                loss_mask=[1] * len(response_ids),
                rollout_log_probs=log_probs,
                metadata={
                    "task_id": task.task_id,
                    "step_index": step_index,
                    "executed_action": action,
                    "action_parse_valid": parse_exact_admissible_action(response, admissible) is not None,
                    "native_success": transition.success,
                },
                status=Sample.Status.COMPLETED,
            )
            segments.append(segment)
            from evomo.data import StepRecord

            recorded = StepRecord(
                step_index=step_index,
                observation=observation,
                admissible_actions=admissible,
                action=action,
                next_observation=transition.observation,
                reward=transition.reward,
                terminated=transition.terminated,
                info={"success": transition.success},
            )
            history.append(HistoryItem.from_step(recorded))
            next_state = reconstruct_alfworld_state(task, tuple(history), transition.observation)
            acquired_target |= _object_type(next_state.inventory) == target
            if operation:
                completed_operation |= any(
                    fact.startswith(f"{next_state.inventory}:") and operation in fact
                    for fact in next_state.transformed_objects
                )
            observation = transition.observation
            admissible = transition.admissible_actions
            success = transition.success
            if transition.terminated:
                break
    finally:
        environment.close()
    if not segments:
        sample.status = Sample.Status.FAILED
        sample.reward = 0.0
        return sample
    events = RewardEvents(
        success=success,
        acquired_target=acquired_target,
        completed_operation=completed_operation,
        invalid_actions=invalid_actions,
        unchanged_steps=unchanged_steps,
        steps=len(segments),
    )
    reward = float(success) if evaluation else shaped_episode_reward(events)
    for segment in segments:
        segment.reward = reward
        segment.metadata.update({
            "episode_reward": reward,
            "episode_success": success,
            "episode_steps": len(segments),
            "invalid_action_count": invalid_actions,
            "unchanged_step_count": unchanged_steps,
        })
    return segments
