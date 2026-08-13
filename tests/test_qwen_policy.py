from __future__ import annotations

import unittest

from evomo.data import TaskSpec
from evomo.policies import (
    HistoryItem,
    ModelGeneration,
    PolicyInput,
    PromptVariant,
    QwenPolicy,
)
from evomo.policies.qwen_policy import build_action_messages


class FakeGenerator:
    def __init__(self, text: str) -> None:
        self.text = text
        self.messages: list[list[dict[str, str]]] = []

    def generate(self, messages: list[dict[str, str]]) -> ModelGeneration:
        self.messages.append(messages)
        return ModelGeneration(self.text, {"prompt_tokens": 10, "completion_tokens": 4})


def make_input(*, history: tuple[HistoryItem, ...] = ()) -> PolicyInput:
    return PolicyInput(
        task=TaskSpec(
            task_id="valid_train/problem/trial",
            split="valid_train",
            task_type="look_at_obj_in_light",
            goal="Look at the book under a lit lamp.",
        ),
        observation=history[-1].next_observation if history else "You see a desk and bed.",
        admissible_actions=("go to desk 1", "go to bed 1", "look"),
        history=history,
        step_index=len(history),
    )


class QwenPolicyTest(unittest.TestCase):
    def test_parses_tagged_action_index(self) -> None:
        generator = FakeGenerator("<action>1</action>")
        policy_input = make_input()
        policy = QwenPolicy(generator)
        policy.reset(task=policy_input.task, seed=42)

        decision = policy.decide(policy_input)

        self.assertEqual(decision.action, "go to bed 1")
        self.assertEqual(decision.source, "model_generation")
        self.assertTrue(decision.metadata["parse_ok"])
        self.assertEqual(decision.metadata["parsed_index"], 1)
        self.assertEqual(decision.metadata["generation"]["prompt_tokens"], 10)
        self.assertTrue(decision.metadata["required_format_ok"])

    def test_invalid_format_falls_back_to_first_action(self) -> None:
        generator = FakeGenerator("I would go to the desk.")
        policy_input = make_input()
        policy = QwenPolicy(generator)
        policy.reset(task=policy_input.task, seed=42)

        decision = policy.decide(policy_input)

        self.assertEqual(decision.action, "go to desk 1")
        self.assertEqual(decision.source, "fallback_first_admissible")
        self.assertFalse(decision.metadata["parse_ok"])
        self.assertEqual(decision.metadata["raw_response"], generator.text)

    def test_out_of_range_index_falls_back(self) -> None:
        generator = FakeGenerator("<action>99</action>")
        policy_input = make_input()
        policy = QwenPolicy(generator)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.action, "go to desk 1")
        self.assertFalse(decision.metadata["parse_ok"])
        self.assertEqual(decision.metadata["parsed_index"], 99)

    def test_accepts_bare_index(self) -> None:
        generator = FakeGenerator("2")
        policy_input = make_input()
        policy = QwenPolicy(generator)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.action, "look")
        self.assertEqual(decision.metadata["parse_format"], "bare_index")
        self.assertFalse(decision.metadata["required_format_ok"])

    def test_accepts_index_with_exact_action_text(self) -> None:
        generator = FakeGenerator("1: go to bed 1")
        policy_input = make_input()
        policy = QwenPolicy(generator)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.action, "go to bed 1")
        self.assertEqual(decision.metadata["parse_format"], "index_and_exact_action")

    def test_rejects_index_with_mismatched_action_text(self) -> None:
        generator = FakeGenerator("1: go to desk 1")
        policy_input = make_input()
        policy = QwenPolicy(generator)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.source, "fallback_first_admissible")
        self.assertFalse(decision.metadata["parse_ok"])

    def test_prompt_limits_history_and_lists_exact_actions(self) -> None:
        history = (
            HistoryItem("o0", "a0", "o1", 0),
            HistoryItem("o1", "a1", "current", 0),
        )
        messages = build_action_messages(make_input(history=history), max_history_items=1)
        user = messages[1]["content"]
        self.assertNotIn("Observation: o0", user)
        self.assertIn("Observation: o1", user)
        self.assertIn("0: go to desk 1", user)
        self.assertIn("2: look", user)
        self.assertIn("<action>INDEX</action>", user)

    def test_plan_variant_records_plan_and_index(self) -> None:
        generator = FakeGenerator("<plan>Inspect the likely bed.</plan><action>1</action>")
        policy_input = make_input()
        policy = QwenPolicy(generator, prompt_variant=PromptVariant.PLAN_THEN_INDEX)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.action, "go to bed 1")
        self.assertEqual(decision.metadata["reasoning"], "Inspect the likely bed.")
        self.assertEqual(decision.metadata["parse_format"], "plan_and_tagged_index")

    def test_think_variant_requires_exact_action_text(self) -> None:
        generator = FakeGenerator(
            "<think>The bed is a likely location.</think><action>go to bed 1</action>"
        )
        policy_input = make_input()
        policy = QwenPolicy(generator, prompt_variant=PromptVariant.THINK_THEN_ACTION_TEXT)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.action, "go to bed 1")
        self.assertEqual(decision.metadata["reasoning"], "The bed is a likely location.")
        self.assertEqual(decision.metadata["parse_format"], "think_and_exact_action")
        self.assertTrue(decision.metadata["required_format_ok"])

    def test_think_variant_executes_exact_action_when_think_is_missing(self) -> None:
        generator = FakeGenerator("<action>go to bed 1</action>")
        policy_input = make_input()
        policy = QwenPolicy(generator, prompt_variant=PromptVariant.THINK_THEN_ACTION_TEXT)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        self.assertEqual(decision.action, "go to bed 1")
        self.assertTrue(decision.metadata["parse_ok"])
        self.assertFalse(decision.metadata["required_format_ok"])
        self.assertEqual(
            decision.metadata["parse_format"], "tagged_exact_action_without_think"
        )

    def test_anti_loop_variant_injects_skill(self) -> None:
        generator = FakeGenerator("<action>0</action>")
        policy_input = make_input()
        policy = QwenPolicy(generator, prompt_variant=PromptVariant.ANTI_LOOP_SKILL)
        policy.reset(task=policy_input.task, seed=42)
        decision = policy.decide(policy_input)
        user_prompt = generator.messages[0][1]["content"]
        self.assertIn("Episode-level skill", user_prompt)
        self.assertIn("do not repeat", user_prompt)
        self.assertEqual(decision.metadata["prompt_variant"], "anti_loop_skill")

    def test_state_tracked_variant_injects_and_records_state(self) -> None:
        history = (
            HistoryItem(
                "You are in a bedroom.",
                "go to bed 1",
                "You arrive at bed 1. On it, you see a book 1.",
                0,
            ),
            HistoryItem(
                "You arrive at bed 1. On it, you see a book 1.",
                "take book 1 from bed 1",
                "You pick up the book 1 from the bed 1.",
                0,
            ),
        )
        generator = FakeGenerator("<action>go to desk 1</action>")
        policy_input = make_input(history=history)
        policy = QwenPolicy(
            generator,
            prompt_variant=PromptVariant.STATE_TRACKED_ACTION_TEXT,
        )
        policy.reset(task=policy_input.task, seed=42)

        decision = policy.decide(policy_input)

        self.assertEqual(decision.action, "go to desk 1")
        self.assertTrue(decision.metadata["required_format_ok"])
        self.assertEqual(decision.metadata["state_before"]["inventory"], "book 1")
        self.assertIn("Reconstructed task state", generator.messages[0][1]["content"])

    def test_state_repaired_variant_navigates_for_unavailable_future_intent(self) -> None:
        history = (
            HistoryItem(
                "You see a book.",
                "take book 1 from bed 1",
                "You pick up the book 1 from the bed 1.",
                0,
            ),
        )
        generator = FakeGenerator("<action>move book 1 to desk 1</action>")
        policy_input = make_input(history=history)
        policy = QwenPolicy(
            generator,
            prompt_variant=PromptVariant.STATE_TRACKED_REPAIRED_ACTION,
        )
        policy.reset(task=policy_input.task, seed=42)

        decision = policy.decide(policy_input)

        self.assertEqual(decision.action, "go to desk 1")
        self.assertEqual(decision.source, "state_prerequisite_repair")
        self.assertFalse(decision.metadata["parse_ok"])
        self.assertEqual(
            decision.metadata["repair_reason"],
            "navigate_held_object_to_proposed_destination",
        )


if __name__ == "__main__":
    unittest.main()
