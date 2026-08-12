"""Single-task ALFWorld adapter backed by TextWorld."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Protocol

from evomo.data.schema import TaskSpec
from evomo.envs.contracts import EnvironmentReset, EnvironmentStep


class AlfworldDependencyError(RuntimeError):
    """Raised when the optional ALFWorld runtime is unavailable."""


class _TextWorldEnvironment(Protocol):
    def reset(self) -> Any: ...

    def step(self, action: str) -> tuple[Any, float, bool]: ...

    def close(self) -> None: ...


BackendFactory = Callable[[Path], _TextWorldEnvironment]


def _default_backend_factory(game_file: Path) -> _TextWorldEnvironment:
    try:
        import textworld
        from alfworld.agents.environment.alfred_tw_env import AlfredDemangler
    except ImportError as exc:
        raise AlfworldDependencyError(
            "ALFWorld runtime is unavailable; install the 'alfworld' optional "
            "dependencies or run inside the configured ALFWorld environment"
        ) from exc

    request_infos = textworld.EnvInfos(won=True, admissible_commands=True)
    return textworld.start(
        str(game_file),
        request_infos=request_infos,
        wrappers=[AlfredDemangler(shuffle=False)],
    )


def _state_value(state: Any, key: str, attribute: str) -> Any:
    if hasattr(state, attribute):
        return getattr(state, attribute)
    try:
        return state[key]
    except (KeyError, TypeError):
        raise ValueError(f"TextWorld state is missing {key!r}") from None


def _observation(state: Any) -> str:
    value = _state_value(state, "feedback", "feedback")
    if not isinstance(value, str):
        raise TypeError("TextWorld feedback must be a string")
    return value


def _admissible_actions(state: Any) -> tuple[str, ...]:
    value = _state_value(state, "admissible_commands", "admissible_commands")
    if not isinstance(value, (list, tuple)):
        raise TypeError("TextWorld admissible_commands must be a list or tuple")
    return tuple(value)


def _won(state: Any) -> bool:
    value = _state_value(state, "won", "won")
    if not isinstance(value, bool):
        raise TypeError("TextWorld won flag must be bool")
    return value


class AlfworldTextEnvironment:
    """Run exactly one TaskSpec at a time through TextWorld.

    The adapter owns the backend between ``reset`` and ``close``. Calling
    ``reset`` again closes the previous backend first. Paths stored in
    TaskSpec remain relative and are resolved beneath ``dataset_root``.
    """

    def __init__(
        self,
        dataset_root: str | Path,
        *,
        backend_factory: BackendFactory = _default_backend_factory,
    ) -> None:
        self.dataset_root = Path(dataset_root).expanduser().resolve()
        if self.dataset_root.name != "json_2.1.1":
            versioned_child = self.dataset_root / "json_2.1.1"
            if versioned_child.is_dir():
                self.dataset_root = versioned_child.resolve()
        if not self.dataset_root.is_dir():
            raise FileNotFoundError(
                f"ALFWorld dataset root does not exist: {self.dataset_root}"
            )
        self._backend_factory = backend_factory
        self._backend: _TextWorldEnvironment | None = None
        self._task: TaskSpec | None = None
        self._last_actions: tuple[str, ...] = ()
        self._terminated = False

    def _resolve_game_file(self, task: TaskSpec) -> Path:
        if task.game_file is None:
            raise ValueError(f"task is not playable (missing game_file): {task.task_id}")
        relative_path = Path(task.game_file)
        if relative_path.is_absolute():
            raise ValueError("TaskSpec.game_file must be relative to the dataset root")
        game_file = (self.dataset_root / relative_path).resolve()
        if not game_file.is_relative_to(self.dataset_root):
            raise ValueError("TaskSpec.game_file escapes the dataset root")
        if not game_file.is_file():
            raise FileNotFoundError(f"ALFWorld game file does not exist: {game_file}")

        try:
            with game_file.open("r", encoding="utf-8") as stream:
                game_metadata = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read ALFWorld game file {game_file}: {exc}") from exc
        if not isinstance(game_metadata, dict) or game_metadata.get("solvable") is not True:
            raise ValueError(f"ALFWorld game is not marked solvable: {game_file}")
        return game_file

    def reset(self, task: TaskSpec, *, seed: int) -> EnvironmentReset:
        if not isinstance(task, TaskSpec):
            raise TypeError("task must be a TaskSpec")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an integer")

        self.close()
        game_file = self._resolve_game_file(task)
        backend = self._backend_factory(game_file)
        try:
            state = backend.reset()
            observation = _observation(state)
            actions = _admissible_actions(state)
            success = _won(state)
        except Exception:
            backend.close()
            raise

        self._backend = backend
        self._task = task
        self._last_actions = actions
        self._terminated = success
        return EnvironmentReset(
            observation=observation,
            admissible_actions=actions,
            info={
                "task_id": task.task_id,
                "requested_seed": seed,
                "success": success,
                "domain_randomization": False,
            },
        )

    def step(self, action: str) -> EnvironmentStep:
        if self._backend is None or self._task is None:
            raise RuntimeError("reset() must be called before step()")
        if self._terminated:
            raise RuntimeError("cannot step a terminated environment")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("action must be a non-empty string")

        action = action.strip()
        was_admissible = action in self._last_actions
        state, reward, done = self._backend.step(action)
        success = _won(state)
        terminated = bool(done) or success
        actions = _admissible_actions(state)
        self._last_actions = actions
        self._terminated = terminated
        return EnvironmentStep(
            observation=_observation(state),
            admissible_actions=actions,
            reward=reward,
            terminated=terminated,
            success=success,
            info={
                "task_id": self._task.task_id,
                "action_was_admissible": was_admissible,
            },
        )

    def close(self) -> None:
        if self._backend is not None:
            self._backend.close()
        self._backend = None
        self._task = None
        self._last_actions = ()
        self._terminated = False

    def __enter__(self) -> "AlfworldTextEnvironment":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
