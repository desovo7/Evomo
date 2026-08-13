from evomo.training.slime_alfworld import (
    RewardEvents,
    episode_grpo_reward_post_process,
    parse_exact_admissible_action,
    shaped_episode_reward,
)


class FakeSample:
    def __init__(self, group_index: int, index: int, reward: float) -> None:
        self.group_index = group_index
        self.index = index
        self.reward = reward


def test_exact_action_parser_rejects_invention_and_extra_text() -> None:
    actions = ("look", "go to desk 1")
    assert parse_exact_admissible_action("<action>GO TO DESK 1</action>", actions) == "go to desk 1"
    assert parse_exact_admissible_action("reason <action>look</action>", actions) is None
    assert parse_exact_admissible_action("<action>go to desk 2</action>", actions) is None


def test_shaped_reward_keeps_success_dominant() -> None:
    successful = shaped_episode_reward(RewardEvents(True, True, True, 0, 0, 12))
    progress = shaped_episode_reward(RewardEvents(False, True, True, 0, 0, 12))
    failed = shaped_episode_reward(RewardEvents(False, False, False, 2, 4, 30))
    assert successful > progress > failed
    assert successful == 1.288


def test_episode_grpo_normalizes_branches_and_broadcasts_to_turns() -> None:
    samples = [
        FakeSample(3, 10, 1.0),
        FakeSample(3, 10, 1.0),
        FakeSample(3, 11, 0.0),
        FakeSample(3, 11, 0.0),
        FakeSample(3, 11, 0.0),
        FakeSample(4, 12, 0.2),
        FakeSample(4, 13, 0.2),
    ]
    raw, advantages = episode_grpo_reward_post_process(None, samples)
    assert raw == [1.0, 1.0, 0.0, 0.0, 0.0, 0.2, 0.2]
    assert advantages[0] == advantages[1] > 0
    assert advantages[2] == advantages[3] == advantages[4] < 0
    assert advantages[5:] == [0.0, 0.0]
