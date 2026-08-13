"""Deterministic, auditable state reconstruction from ALFWorld text transitions."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass

from evomo.data import TaskSpec
from evomo.policies.contracts import HistoryItem

_GO_RE = re.compile(r"^go to (.+)$", re.IGNORECASE)
_TAKE_RE = re.compile(r"^take (.+) from (.+)$", re.IGNORECASE)
_MOVE_RE = re.compile(r"^move (.+) to (.+)$", re.IGNORECASE)
_OPEN_RE = re.compile(r"^open (.+)$", re.IGNORECASE)
_TRANSFORM_RE = re.compile(r"^(clean|cool|heat) (.+?) (?:with|using) (.+)$", re.IGNORECASE)
_ARRIVE_RE = re.compile(r"You arrive at ([^.]+)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class AlfworldState:
    """Compact facts known immediately before one policy decision."""

    task_recipe: tuple[str, ...]
    current_location: str | None
    inventory: str | None
    visited_locations: tuple[str, ...]
    opened_receptacles: tuple[str, ...]
    empty_receptacles: tuple[str, ...]
    known_placements: tuple[str, ...]
    transformed_objects: tuple[str, ...]
    stalled_actions: tuple[str, ...]
    recent_actions: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    def render(self) -> str:
        def show(values: tuple[str, ...]) -> str:
            return ", ".join(values) if values else "none known"

        return "\n".join(
            (
                f"Task recipe: {' -> '.join(self.task_recipe)}",
                f"Current location: {self.current_location or 'unknown'}",
                f"Inventory: {self.inventory or 'empty'}",
                f"Visited locations: {show(self.visited_locations)}",
                f"Opened receptacles: {show(self.opened_receptacles)}",
                f"Known empty receptacles: {show(self.empty_receptacles)}",
                f"Known placements: {show(self.known_placements)}",
                f"Completed transformations: {show(self.transformed_objects)}",
                f"Actions that recently made no progress: {show(self.stalled_actions)}",
                f"Recent actions: {show(self.recent_actions)}",
            )
        )


def task_recipe(task: TaskSpec) -> tuple[str, ...]:
    recipes = {
        "pick_and_place_simple": (
            "find the goal object",
            "take the goal object",
            "go to the goal receptacle",
            "move the held object to that receptacle",
        ),
        "pick_two_obj_and_place": (
            "find both distinct goal objects",
            "take and place the first object",
            "return for a different instance",
            "place the second object in the goal receptacle",
        ),
        "pick_clean_then_place_in_recep": (
            "find and take the goal object",
            "go to a sinkbasin and clean the held object",
            "go to the goal receptacle",
            "place the cleaned object",
        ),
        "pick_cool_then_place_in_recep": (
            "find and take the goal object",
            "go to a fridge and cool the held object",
            "go to the goal receptacle",
            "place the cooled object",
        ),
        "pick_heat_then_place_in_recep": (
            "find and take the goal object",
            "go to a microwave and heat the held object",
            "go to the goal receptacle",
            "place the heated object",
        ),
        "look_at_obj_in_light": (
            "find and take the goal object",
            "find a desklamp or floorlamp",
            "toggle the lamp on if needed",
            "examine the held object under the lit lamp",
        ),
    }
    return recipes.get(task.task_type, ("work toward the stated goal",))


def reconstruct_alfworld_state(
    task: TaskSpec,
    history: tuple[HistoryItem, ...],
    current_observation: str,
) -> AlfworldState:
    """Replay successful textual effects; never invent facts missing from history."""

    location: str | None = None
    inventory: str | None = None
    visited: set[str] = set()
    opened: set[str] = set()
    empty: set[str] = set()
    placements: dict[str, str] = {}
    transformed: dict[str, set[str]] = {}
    stalled: Counter[str] = Counter()

    observations = [item.next_observation for item in history]
    observations.append(current_observation)
    for observation in observations:
        arrive = _ARRIVE_RE.search(observation)
        if arrive:
            location = arrive.group(1).strip().lower()
            visited.add(location)

    for item in history:
        action = item.action.strip().lower()
        result = item.next_observation.strip()
        no_progress = item.observation.strip() == result
        if no_progress:
            stalled[action] += 1

        go_match = _GO_RE.fullmatch(action)
        if go_match and _ARRIVE_RE.search(result):
            destination = go_match.group(1).strip()
            location = destination
            visited.add(destination)

        take_match = _TAKE_RE.fullmatch(action)
        if take_match and "you pick up" in result.lower():
            inventory = take_match.group(1).strip()
            placements.pop(inventory, None)

        move_match = _MOVE_RE.fullmatch(action)
        if move_match and "you move" in result.lower():
            obj, destination = (part.strip() for part in move_match.groups())
            placements[obj] = destination
            if inventory == obj:
                inventory = None

        open_match = _OPEN_RE.fullmatch(action)
        if open_match and "you open" in result.lower():
            receptacle = open_match.group(1).strip()
            opened.add(receptacle)
            if "you see nothing" in result.lower():
                empty.add(receptacle)

        transform_match = _TRANSFORM_RE.fullmatch(action)
        if transform_match and not no_progress:
            operation, obj, _ = transform_match.groups()
            transformed.setdefault(obj.strip(), set()).add(operation.lower())

        if action == "inventory":
            lowered = result.lower()
            if "not carrying anything" in lowered:
                inventory = None
            else:
                carrying = re.search(r"carrying[: ]+(.+?)(?:\.|$)", result, re.IGNORECASE)
                if carrying:
                    inventory = carrying.group(1).strip().lower()

    placement_facts = tuple(
        f"{obj} in/on {destination}" for obj, destination in sorted(placements.items())
    )
    transformation_facts = tuple(
        f"{obj}: {','.join(sorted(operations))}"
        for obj, operations in sorted(transformed.items())
    )
    stalled_actions = tuple(
        f"{action} ({count}x)" for action, count in sorted(stalled.items()) if count
    )
    return AlfworldState(
        task_recipe=task_recipe(task),
        current_location=location,
        inventory=inventory,
        visited_locations=tuple(sorted(visited)),
        opened_receptacles=tuple(sorted(opened)),
        empty_receptacles=tuple(sorted(empty)),
        known_placements=placement_facts,
        transformed_objects=transformation_facts,
        stalled_actions=stalled_actions,
        recent_actions=tuple(item.action for item in history[-6:]),
    )


def repair_unavailable_action(
    proposed_action: str,
    admissible_actions: tuple[str, ...],
    state: AlfworldState,
) -> tuple[int, str] | None:
    """Map a valid future intent to one explicit, currently admissible prerequisite."""

    proposed = proposed_action.strip().lower()
    indexed = {action.casefold(): index for index, action in enumerate(admissible_actions)}

    take_match = _TAKE_RE.fullmatch(proposed)
    if take_match:
        _, source = take_match.groups()
        navigation = f"go to {source.strip()}"
        index = indexed.get(navigation.casefold())
        if index is not None:
            return index, "navigate_to_proposed_take_source"

    move_match = _MOVE_RE.fullmatch(proposed)
    if move_match:
        obj, destination = (part.strip() for part in move_match.groups())
        navigation = f"go to {destination}"
        index = indexed.get(navigation.casefold())
        if state.inventory == obj and index is not None:
            return index, "navigate_held_object_to_proposed_destination"

    transform_match = _TRANSFORM_RE.fullmatch(proposed)
    if transform_match:
        _, obj, appliance = (part.strip() for part in transform_match.groups())
        navigation = f"go to {appliance}"
        index = indexed.get(navigation.casefold())
        if state.inventory == obj and index is not None:
            return index, "navigate_held_object_to_proposed_appliance"

    return None
