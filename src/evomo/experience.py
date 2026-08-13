"""Versioned experience rules extracted from completed ALFWorld trajectories."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Mapping

from evomo.data import Episode, TaskSpec

if TYPE_CHECKING:
    from evomo.policies.alfworld_state import AlfworldState

EXPERIENCE_SCHEMA_VERSION = 1
_TAKE_RE = re.compile(r"^take (.+) from (.+)$", re.IGNORECASE)
_MOVE_RE = re.compile(r"^move (.+) to (.+)$", re.IGNORECASE)
_GO_RE = re.compile(r"^go to (.+)$", re.IGNORECASE)
_OPEN_RE = re.compile(r"^open (.+)$", re.IGNORECASE)
_TOGGLE_RE = re.compile(r"^toggle (.+)$", re.IGNORECASE)


def _normalized_type(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.casefold())


def _object_type(instance: str) -> str:
    return _normalized_type(re.sub(r"\s+\d+$", "", instance.strip()))


def task_targets(task: TaskSpec) -> dict[str, str]:
    params = task.metadata.get("pddl_params", {})
    if not isinstance(params, Mapping):
        params = {}
    return {
        "object": str(params.get("object_target", "")).strip(),
        "destination": str(params.get("parent_target", "")).strip(),
        "toggle": str(params.get("toggle_target", "")).strip(),
    }


@dataclass(frozen=True, slots=True)
class ExperienceEvidence:
    episode_id: str
    task_id: str
    step_index: int | None
    action: str | None
    observation: str


@dataclass(frozen=True, slots=True)
class ExperienceRule:
    rule_id: str
    kind: str
    task_types: tuple[str, ...]
    instruction: str
    evidence: tuple[ExperienceEvidence, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping) -> "ExperienceRule":
        data = dict(value)
        data["task_types"] = tuple(data["task_types"])
        data["evidence"] = tuple(ExperienceEvidence(**item) for item in data["evidence"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ExperienceSet:
    version: str
    source_policy_id: str
    rules: tuple[ExperienceRule, ...]
    source_episode_ids: tuple[str, ...]
    schema_version: int = EXPERIENCE_SCHEMA_VERSION
    parent_version: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != EXPERIENCE_SCHEMA_VERSION:
            raise ValueError(f"unsupported experience schema: {self.schema_version}")
        if not self.version.strip() or not self.source_policy_id.strip():
            raise ValueError("experience version and source policy must be non-empty")
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError("experience rule IDs must be unique")

    def to_dict(self) -> dict:
        value = asdict(self)
        if self.parent_version is None:
            value.pop("parent_version")
        return value

    @classmethod
    def from_dict(cls, value: Mapping) -> "ExperienceSet":
        data = dict(value)
        data.setdefault("parent_version", None)
        data["rules"] = tuple(ExperienceRule.from_dict(item) for item in data["rules"])
        data["source_episode_ids"] = tuple(data["source_episode_ids"])
        return cls(**data)

    def applicable_rules(self, task_type: str) -> tuple[ExperienceRule, ...]:
        return tuple(rule for rule in self.rules if task_type in rule.task_types)

    def render(self, task_type: str) -> str:
        rules = self.applicable_rules(task_type)
        if not rules:
            return "(no applicable learned experience)"
        return "\n".join(f"- [{rule.rule_id}] {rule.instruction}" for rule in rules)


def save_experience_set(experiences: ExperienceSet, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(experiences.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_experience_set(path: str | Path) -> ExperienceSet:
    with Path(path).open(encoding="utf-8") as stream:
        return ExperienceSet.from_dict(json.load(stream))


def promote_experience_by_task_type(
    incumbent: ExperienceSet,
    candidate: ExperienceSet,
    *,
    selected_versions: Mapping[str, str],
    version: str,
) -> ExperienceSet:
    """Compile per-task-type version choices into one immutable experience set."""

    sources = {incumbent.version: incumbent, candidate.version: candidate}
    unknown = set(selected_versions.values()) - set(sources)
    if unknown:
        raise ValueError(f"selected unknown experience versions: {sorted(unknown)}")
    if not selected_versions:
        raise ValueError("at least one task-type selection is required")

    rules_by_source = {
        source_version: {rule.rule_id: rule for rule in source.rules}
        for source_version, source in sources.items()
    }
    rule_ids = tuple(
        dict.fromkeys(
            rule.rule_id
            for source in (incumbent, candidate)
            for rule in source.rules
        )
    )
    promoted_rules: list[ExperienceRule] = []
    for rule_id in rule_ids:
        templates = [
            source_rules[rule_id]
            for source_rules in rules_by_source.values()
            if rule_id in source_rules
        ]
        if any(
            (rule.kind, rule.instruction) != (templates[0].kind, templates[0].instruction)
            for rule in templates[1:]
        ):
            raise ValueError(f"rule {rule_id!r} changed semantics across selected versions")
        task_types: list[str] = []
        evidence: list[ExperienceEvidence] = []
        used_sources: set[str] = set()
        for task_type, source_version in selected_versions.items():
            rule = rules_by_source[source_version].get(rule_id)
            if rule is not None and task_type in rule.task_types:
                task_types.append(task_type)
                if source_version not in used_sources:
                    evidence.extend(rule.evidence)
                    used_sources.add(source_version)
        if not task_types:
            continue
        unique_evidence = list(dict.fromkeys(evidence))
        promoted_rules.append(
            ExperienceRule(
                rule_id=rule_id,
                kind=templates[0].kind,
                task_types=tuple(task_types),
                instruction=templates[0].instruction,
                evidence=_retain_scoped_evidence(unique_evidence, task_types),
            )
        )

    evidence_episode_ids = tuple(
        dict.fromkeys(
            item.episode_id for rule in promoted_rules for item in rule.evidence
        )
    )
    return ExperienceSet(
        version=version,
        source_policy_id=(
            f"promotion:{incumbent.version}->{candidate.version}"
        ),
        rules=tuple(promoted_rules),
        source_episode_ids=evidence_episode_ids,
        parent_version=candidate.version,
    )


def _retain_scoped_evidence(
    evidence: Iterable[ExperienceEvidence],
    task_types: Iterable[str],
    *,
    limit: int = 48,
) -> tuple[ExperienceEvidence, ...]:
    """Bound evidence while retaining one concrete item per declared task type."""

    items = tuple(evidence)
    task_types = tuple(task_types)
    if limit < len(task_types):
        raise ValueError("evidence limit cannot cover every declared task type")

    selected: list[ExperienceEvidence] = []
    for task_type in task_types:
        match = next(
            (
                item
                for item in items
                if any(
                    segment == task_type or segment.startswith(f"{task_type}-")
                    for segment in item.task_id.split("/")
                )
            ),
            None,
        )
        if match is not None and match not in selected:
            selected.append(match)
    selected.extend(item for item in items if item not in selected)
    return tuple(selected[:limit])


def extract_failure_experiences(
    episodes: Iterable[Episode], *, version: str
) -> ExperienceSet:
    """Derive generic rules and retain concrete trajectory evidence for each rule."""

    from evomo.policies.alfworld_state import reconstruct_alfworld_state
    from evomo.policies.contracts import HistoryItem

    episodes = tuple(episodes)
    if not episodes:
        raise ValueError("at least one episode is required")
    policies = {episode.policy_id for episode in episodes}
    if len(policies) != 1:
        raise ValueError("source episodes must use one policy")
    failed = tuple(episode for episode in episodes if not episode.success)
    if not failed:
        raise ValueError("experience extraction requires failed episodes")

    wrong_object: list[ExperienceEvidence] = []
    revisits: list[ExperienceEvidence] = []
    unfinished: list[ExperienceEvidence] = []
    affected_types: set[str] = set()
    for episode in failed:
        affected_types.add(episode.task.task_type)
        target = _normalized_type(task_targets(episode.task)["object"])
        history: list[HistoryItem] = []
        for step in episode.steps:
            state = reconstruct_alfworld_state(
                episode.task, tuple(history), step.observation
            )
            take = _TAKE_RE.fullmatch(step.action)
            if take and target and _object_type(take.group(1)) != target:
                wrong_object.append(
                    ExperienceEvidence(
                        episode.episode_id,
                        episode.task.task_id,
                        step.step_index,
                        step.action,
                        "The policy picked an object whose type did not match object_target.",
                    )
                )
            go = _GO_RE.fullmatch(step.action)
            exploring_with_target = (
                episode.task.task_type == "look_at_obj_in_light"
                and state.inventory is not None
                and _object_type(state.inventory) == target
            )
            if (
                go
                and (state.inventory is None or exploring_with_target)
                and go.group(1).strip().casefold()
                in {item.casefold() for item in state.visited_locations}
            ):
                revisits.append(
                    ExperienceEvidence(
                        episode.episode_id,
                        episode.task.task_id,
                        step.step_index,
                        step.action,
                        "The target was not held and the policy revisited an explored location.",
                    )
                )
            history.append(HistoryItem.from_step(step))
        target_seen = any(
            target and _object_type(match.group(1)) == target
            for step in episode.steps
            if (match := _TAKE_RE.fullmatch(step.action))
        )
        unfinished.append(
            ExperienceEvidence(
                episode.episode_id,
                episode.task.task_id,
                None,
                None,
                "Episode reached max_steps after target acquisition."
                if target_seen
                else "Episode reached max_steps without acquiring the target object.",
            )
        )

    rules: list[ExperienceRule] = []
    if wrong_object:
        rules.append(
            ExperienceRule(
                "target-object-lock",
                "target_object_lock",
                tuple(sorted(affected_types)),
                "Use pddl_params.object_target as an invariant: do not take, transform, "
                "or deliver a different object type; release a wrongly held object first.",
                tuple(wrong_object[:24]),
            )
        )
    if revisits:
        rules.append(
            ExperienceRule(
                "novelty-before-revisit",
                "novelty_exploration",
                tuple(sorted(affected_types)),
                "While searching for the target or a required lamp, open the current "
                "closed receptacle, then prefer an unvisited location over a known empty "
                "or already explored location.",
                tuple(revisits[:24]),
            )
        )
    rules.append(
        ExperienceRule(
            "ordered-task-recipe",
            "ordered_subgoals",
            tuple(sorted(affected_types)),
            "Follow the task recipe in order for the target object: acquire it, perform "
            "the required clean/cool/heat/light interaction, then deliver or examine it.",
            tuple(unfinished),
        )
    )
    return ExperienceSet(
        version=version,
        source_policy_id=next(iter(policies)),
        rules=tuple(rules),
        source_episode_ids=tuple(episode.episode_id for episode in failed),
    )


def evolve_experience_set(
    base: ExperienceSet,
    episodes: Iterable[Episode],
    *,
    version: str,
    repeated_type_threshold: int = 4,
) -> ExperienceSet:
    """Merge failure evidence into a new child version of an experience set."""

    episodes = tuple(episode for episode in episodes if not episode.success)
    if not episodes:
        raise ValueError("experience evolution requires failed episodes")
    policies = {episode.policy_id for episode in episodes}
    if len(policies) != 1:
        raise ValueError("evolution episodes must use one policy")
    if repeated_type_threshold < 2:
        raise ValueError("repeated_type_threshold must be at least two")

    # Preserve the first published evolution exactly: exp-v1 adds only the
    # location-type diversity rule. Later versions merge fresh evidence into
    # the complete rule set.
    if not any(rule.rule_id == "diversify-location-types" for rule in base.rules):
        evidence: list[ExperienceEvidence] = []
        affected_types: set[str] = set()
        for episode in episodes:
            visited_type_counts: dict[str, int] = {}
            for step in episode.steps:
                match = _GO_RE.fullmatch(step.action)
                if not match:
                    continue
                place_type = _object_type(match.group(1))
                available_types = {
                    _object_type(candidate.group(1))
                    for action in step.admissible_actions
                    if (candidate := _GO_RE.fullmatch(action))
                }
                visited_type_counts[place_type] = visited_type_counts.get(place_type, 0) + 1
                if (
                    visited_type_counts[place_type] >= repeated_type_threshold
                    and len(available_types - set(visited_type_counts)) > 0
                ):
                    affected_types.add(episode.task.task_type)
                    evidence.append(
                        ExperienceEvidence(
                            episode.episode_id,
                            episode.task.task_id,
                            step.step_index,
                            step.action,
                            f"Visited location type {place_type!r} repeatedly while other "
                            "unvisited location types remained admissible.",
                        )
                    )
        if not evidence:
            raise ValueError("no repeated location-type exploration found")
        diversity_rule = ExperienceRule(
            "diversify-location-types",
            "location_type_diversity",
            tuple(sorted(affected_types)),
            "When searching and one location type has already been explored, prefer an "
            "unvisited location of a different type before trying more numbered "
            "instances of the same type.",
            tuple(evidence[:24]),
        )
        return ExperienceSet(
            version=version,
            source_policy_id=next(iter(policies)),
            rules=base.rules + (diversity_rule,),
            source_episode_ids=tuple(episode.episode_id for episode in episodes),
            parent_version=base.version,
        )

    wrong_object: list[ExperienceEvidence] = []
    revisits: list[ExperienceEvidence] = []
    unfinished: list[ExperienceEvidence] = []
    diversity: list[ExperienceEvidence] = []
    rule_types: dict[str, set[str]] = {
        "target-object-lock": set(),
        "novelty-before-revisit": set(),
        "ordered-task-recipe": set(),
        "diversify-location-types": set(),
    }
    for episode in episodes:
        target = _normalized_type(task_targets(episode.task)["object"])
        visited_type_counts: dict[str, int] = {}
        visited_locations: set[str] = set()
        for step in episode.steps:
            take = _TAKE_RE.fullmatch(step.action)
            if take and target and _object_type(take.group(1)) != target:
                rule_types["target-object-lock"].add(episode.task.task_type)
                wrong_object.append(
                    ExperienceEvidence(
                        episode.episode_id,
                        episode.task.task_id,
                        step.step_index,
                        step.action,
                        "The policy manipulated an object whose type did not match "
                        "object_target.",
                    )
                )
            match = _GO_RE.fullmatch(step.action)
            if not match:
                continue
            place = match.group(1).strip()
            place_type = _object_type(place)
            available_types = {
                _object_type(candidate.group(1))
                for action in step.admissible_actions
                if (candidate := _GO_RE.fullmatch(action))
            }
            visited_type_counts[place_type] = visited_type_counts.get(place_type, 0) + 1
            if place.casefold() in visited_locations:
                rule_types["novelty-before-revisit"].add(episode.task.task_type)
                revisits.append(
                    ExperienceEvidence(
                        episode.episode_id,
                        episode.task.task_id,
                        step.step_index,
                        step.action,
                        "The target was not complete and the policy revisited an "
                        "explored location.",
                    )
                )
            visited_locations.add(place.casefold())
            if (
                visited_type_counts[place_type] >= repeated_type_threshold
                and len(available_types - set(visited_type_counts)) > 0
            ):
                rule_types["diversify-location-types"].add(episode.task.task_type)
                diversity.append(
                    ExperienceEvidence(
                        episode.episode_id,
                        episode.task.task_id,
                        step.step_index,
                        step.action,
                        f"Visited location type {place_type!r} repeatedly while other "
                        "unvisited location types remained admissible.",
                    )
                )
        rule_types["ordered-task-recipe"].add(episode.task.task_type)
        unfinished.append(
            ExperienceEvidence(
                episode.episode_id,
                episode.task.task_id,
                None,
                None,
                "Episode reached max_steps without completing the ordered task recipe.",
            )
        )

    additions = {
        "target-object-lock": (
            "target_object_lock",
            "Use pddl_params.object_target as an invariant: do not take, transform, "
            "or deliver a different object type; release a wrongly held object first.",
            wrong_object,
        ),
        "novelty-before-revisit": (
            "novelty_exploration",
            "While searching for an unfinished target, open the current closed "
            "receptacle, then prefer an unvisited location over an explored location.",
            revisits,
        ),
        "ordered-task-recipe": (
            "ordered_subgoals",
            "Follow the task recipe in order for the target object: acquire it, perform "
            "the required interaction, then deliver or examine it. For two-object "
            "tasks, deliver two distinct target instances.",
            unfinished,
        ),
        "diversify-location-types": (
            "location_type_diversity",
            "When searching and one location type has already been explored, prefer an "
            "unvisited location of a different type before trying more numbered "
            "instances of the same type.",
            diversity,
        ),
    }
    existing = {rule.rule_id: rule for rule in base.rules}
    merged_rules: list[ExperienceRule] = []
    for rule_id in additions:
        kind, instruction, evidence = additions[rule_id]
        prior = existing.pop(rule_id, None)
        if prior is None and not evidence:
            continue
        types = set(prior.task_types if prior else ()) | rule_types[rule_id]
        combined_evidence = list(prior.evidence if prior else ()) + evidence
        merged_rules.append(
            ExperienceRule(
                rule_id,
                prior.kind if prior else kind,
                tuple(sorted(types)),
                prior.instruction if prior else instruction,
                _retain_scoped_evidence(combined_evidence, sorted(types)),
            )
        )
    merged_rules.extend(existing.values())
    return ExperienceSet(
        version=version,
        source_policy_id=next(iter(policies)),
        rules=tuple(merged_rules),
        source_episode_ids=tuple(episode.episode_id for episode in episodes),
        parent_version=base.version,
    )


@dataclass(frozen=True, slots=True)
class ExperienceOverride:
    action_index: int
    reason: str
    rule_ids: tuple[str, ...]


def choose_experience_override(
    *,
    task: TaskSpec,
    state: "AlfworldState",
    proposed_action: str | None,
    admissible_actions: tuple[str, ...],
    experiences: ExperienceSet,
) -> ExperienceOverride | None:
    """Apply only rules present in the loaded, evidence-backed experience set."""

    rules = experiences.applicable_rules(task.task_type)
    kinds = {rule.kind: rule.rule_id for rule in rules}
    target = _normalized_type(task_targets(task)["object"])
    destination = _normalized_type(task_targets(task)["destination"])

    takes: list[tuple[int, str, str]] = []
    moves: list[tuple[int, str, str]] = []
    goes: list[tuple[int, str]] = []
    opens: list[tuple[int, str]] = []
    for index, action in enumerate(admissible_actions):
        if match := _TAKE_RE.fullmatch(action):
            takes.append((index, match.group(1).strip(), match.group(2).strip()))
        elif match := _MOVE_RE.fullmatch(action):
            moves.append((index, match.group(1).strip(), match.group(2).strip()))
        elif match := _GO_RE.fullmatch(action):
            goes.append((index, match.group(1).strip()))
        elif match := _OPEN_RE.fullmatch(action):
            opens.append((index, match.group(1).strip()))

    if "target_object_lock" in kinds:
        if state.inventory and _object_type(state.inventory) != target:
            for index, obj, _ in moves:
                if obj.casefold() == state.inventory.casefold():
                    return ExperienceOverride(
                        index,
                        "release_non_target_inventory",
                        (kinds["target_object_lock"],),
                    )
        if state.inventory is None:
            for index, obj, _ in takes:
                already_delivered = any(
                    fact.casefold().startswith(f"{obj.casefold()} in/on ")
                    and _object_type(fact.rsplit(" in/on ", 1)[-1]) == destination
                    for fact in state.known_placements
                )
                if (
                    _object_type(obj) == target
                    and not (
                        task.task_type == "pick_two_obj_and_place"
                        and already_delivered
                    )
                ):
                    return ExperienceOverride(
                        index,
                        "take_visible_target_object",
                        (kinds["target_object_lock"],),
                    )
            proposed_take = _TAKE_RE.fullmatch(proposed_action or "")
            if proposed_take and _object_type(proposed_take.group(1)) != target:
                proposed_action = None

    if "ordered_subgoals" in kinds and state.inventory:
        held_type = _object_type(state.inventory)
        if held_type == target:
            operation = {
                "pick_clean_then_place_in_recep": "clean",
                "pick_cool_then_place_in_recep": "cool",
                "pick_heat_then_place_in_recep": "heat",
            }.get(task.task_type)
            completed = any(
                fact.startswith(f"{state.inventory}:") and operation in fact
                for fact in state.transformed_objects
            ) if operation else True
            if operation and not completed:
                for index, action in enumerate(admissible_actions):
                    if action.casefold().startswith(f"{operation} {state.inventory.casefold()} "):
                        return ExperienceOverride(
                            index,
                            f"execute_required_{operation}",
                            (kinds["ordered_subgoals"],),
                        )
                appliance = {"clean": "sinkbasin", "cool": "fridge", "heat": "microwave"}[operation]
                for index, place in goes:
                    if _object_type(place) == appliance:
                        return ExperienceOverride(
                            index,
                            f"navigate_to_{operation}_appliance",
                            (kinds["ordered_subgoals"],),
                        )
            if completed and destination:
                for index, obj, place in moves:
                    if obj.casefold() == state.inventory.casefold() and _object_type(place) == destination:
                        return ExperienceOverride(
                            index,
                            "deliver_completed_target",
                            (kinds["ordered_subgoals"],),
                        )
                for index, place in goes:
                    if _object_type(place) == destination:
                        return ExperienceOverride(
                            index,
                            "navigate_to_target_destination",
                            (kinds["ordered_subgoals"],),
                        )

            if task.task_type == "look_at_obj_in_light":
                toggle_type = _normalized_type(task_targets(task)["toggle"])
                toggled_types = {_object_type(item) for item in state.toggled_objects}
                if toggle_type not in toggled_types:
                    for index, action in enumerate(admissible_actions):
                        if match := _TOGGLE_RE.fullmatch(action):
                            if _object_type(match.group(1)) == toggle_type:
                                return ExperienceOverride(
                                    index,
                                    "toggle_required_lamp",
                                    (kinds["ordered_subgoals"],),
                                )
                    for index, place in goes:
                        if _object_type(place) == toggle_type:
                            return ExperienceOverride(
                                index,
                                "navigate_to_required_lamp",
                                (kinds["ordered_subgoals"],),
                            )
                else:
                    for index, action in enumerate(admissible_actions):
                        if action.casefold() == f"examine {state.inventory.casefold()}":
                            return ExperienceOverride(
                                index,
                                "examine_target_under_lit_lamp",
                                (kinds["ordered_subgoals"],),
                            )

    searching_for_lamp = (
        task.task_type == "look_at_obj_in_light"
        and state.inventory is not None
        and _object_type(state.inventory) == target
        and _normalized_type(task_targets(task)["toggle"])
        not in {_object_type(item) for item in state.toggled_objects}
    )
    if "novelty_exploration" in kinds and (
        state.inventory is None or searching_for_lamp
    ):
        for index, receptacle in opens:
            if (
                state.current_location
                and receptacle.casefold() == state.current_location.casefold()
                and receptacle.casefold()
                not in {item.casefold() for item in state.opened_receptacles}
            ):
                return ExperienceOverride(
                    index,
                    "open_unsearched_current_receptacle",
                    (kinds["novelty_exploration"],),
                )
        visited = {place.casefold() for place in state.visited_locations}
        candidates = [(index, place) for index, place in goes if place.casefold() not in visited]
        if candidates:
            visited_types = {_object_type(place) for place in state.visited_locations}
            diverse_candidates = [
                candidate
                for candidate in candidates
                if _object_type(candidate[1]) not in visited_types
            ]
            if "location_type_diversity" in kinds and diverse_candidates:
                candidates = diverse_candidates
            proposed_go = _GO_RE.fullmatch(proposed_action or "")
            proposed_open = _OPEN_RE.fullmatch(proposed_action or "")
            proposal_is_useful = bool(
                proposed_go
                and proposed_go.group(1).strip().casefold() not in visited
                or proposed_open
                and state.current_location
                and proposed_open.group(1).strip().casefold()
                == state.current_location.casefold()
            )
            if (
                proposal_is_useful
                and "location_type_diversity" in kinds
                and diverse_candidates
                and proposed_go
                and _object_type(proposed_go.group(1)) in visited_types
            ):
                proposal_is_useful = False
            if not proposal_is_useful:
                return ExperienceOverride(
                    candidates[0][0],
                    "explore_unvisited_location_type"
                    if "location_type_diversity" in kinds and diverse_candidates
                    else "explore_unvisited_location",
                    (
                        kinds["novelty_exploration"],
                        kinds["location_type_diversity"],
                    )
                    if "location_type_diversity" in kinds and diverse_candidates
                    else (kinds["novelty_exploration"],),
                )
    return None
