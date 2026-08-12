"""Record and read one synthetic episode through the first data-flow slice."""

from pathlib import Path
from tempfile import TemporaryDirectory

from evomo.data import EpisodeRecorder, EpisodeStore, TaskSpec, TerminationReason


def main() -> None:
    task = TaskSpec(
        task_id="example/pick_and_place/001",
        split="train",
        task_type="pick_and_place",
        goal="Put the apple on the table.",
    )
    recorder = EpisodeRecorder(
        task=task,
        policy_id="scripted-example-v1",
        seed=42,
        initial_observation="You are in a kitchen. An apple is on the counter.",
    )
    recorder.record_step(
        observation=recorder.next_observation,
        admissible_actions=["take apple from counter", "look"],
        action="take apple from counter",
        next_observation="You pick up the apple.",
        reward=0.0,
        terminated=False,
    )
    recorder.record_step(
        observation=recorder.next_observation,
        admissible_actions=["put apple on table"],
        action="put apple on table",
        next_observation="You put the apple on the table. Task completed.",
        reward=1.0,
        terminated=True,
    )
    episode = recorder.finish(
        success=True,
        termination_reason=TerminationReason.SUCCESS,
    )

    with TemporaryDirectory() as directory:
        store = EpisodeStore(Path(directory) / "episodes.jsonl")
        store.append(episode)
        restored = store.load_all()[0]
        print(
            f"episode={restored.episode_id} task={restored.task.task_id} "
            f"steps={len(restored.steps)} success={restored.success}"
        )


if __name__ == "__main__":
    main()
