from dataclasses import dataclass

from aerona.catalog.society import son_relation_label
from aerona.catalog.stats import STATS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.son import SonStatus
from aerona.engine.gods.progress import Progress, grant_progress
from aerona.engine.primitives.numbers import round_half_up
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.validation import fail, label_of

PERCENT = 100


def share(base: float, percent: float) -> int:
    return max(1, round(base * percent / PERCENT))


def progress_notes(call: SonCall, son: SonRow, progress: Progress) -> str:
    notes: list[str] = []
    for step in progress.level_ups:
        notes.append(
            result(
                SonResult.LEVEL_UP,
                level=step.level,
                first=STATS[step.first].label,
                first_gain=step.first_gain,
                second=STATS[step.second].label,
                second_gain=step.second_gain,
            )
        )
        if step.awakened is not None:
            notes.append(result(SonResult.POWER_AWOKE, power=step.awakened))
    note = " ".join(notes)
    if son.id == call.son.id:
        call.turn.note_level_up(note or None)
    return note


async def grant(call: SonCall, son: SonRow, xp: int, fame: int) -> str:
    return progress_notes(call, son, await grant_progress(call.tick, son, xp=xp, fame=fame))


async def world_name(call: SonCall, world_id: int | None) -> str:
    world = await call.session.get(WorldRow, world_id) if world_id is not None else None
    return world.name if world is not None else ""


async def ensure_in_reach(call: SonCall, entity: EntityRow) -> None:
    if call.world_id is None or entity.world_id == call.world_id or await call.reachable_world(entity.world_id):
        return
    fail(
        SonResult.OTHER_WORLD,
        id=entity.id,
        name=entity.name,
        world_id=entity.world_id,
        world=await world_name(call, entity.world_id),
        own_id=call.world_id,
    )


async def require_sibling(call: SonCall, son_id: int) -> SonRow:
    sibling = await call.session.get(SonRow, son_id)
    if sibling is None or sibling.id == call.son.id:
        fail(SonResult.INVALID_SIBLING)
    return sibling


async def ensure_sibling_in_reach(call: SonCall, sibling: SonRow) -> None:
    there = sibling.current_world_id
    if there is None or call.world_id is None or there == call.world_id or await call.reachable_world(there):
        return
    fail(SonResult.SIBLING_FAR, name=sibling.name, world_id=there, world=await world_name(call, there))


@dataclass(frozen=True)
class Relation:
    value: int
    label: str


async def relation(call: SonCall, other_id: int) -> Relation:
    value = await SonRepository(call.session).relation(call.son.id, other_id)
    return Relation(value, label_of(son_relation_label(call.rules, value)))


async def shift_relation(call: SonCall, other_id: int | None, delta: float, note: str | None = None) -> Relation | None:
    if other_id is None or other_id == call.son.id:
        return None
    other = await call.session.get(SonRow, other_id)
    if other is None:
        return None
    value = await SonRepository(call.session).change_relation(call.son.id, other_id, delta, note)
    return Relation(value, label_of(son_relation_label(call.rules, value)))


async def has_covenant(call: SonCall, other_id: int) -> bool:
    return await BondRepository(call.session).exists_between(call.son.id, other_id, BondKind.ALLY)


def require_essence(call: SonCall, cost: int) -> None:
    if call.son.essence < cost:
        fail(SonResult.ESSENCE_SHORT, cost=cost, have=call.son.essence)


def is_active(son: SonRow | None) -> bool:
    return son is not None and son.status is SonStatus.ACTIVE


def rounded(value: float) -> int:
    return round_half_up(value)
