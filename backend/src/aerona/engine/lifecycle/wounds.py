from dataclasses import dataclass, field, replace
from enum import StrEnum

from aerona.catalog.anatomy import FINGERS
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import SEVERITY_MAX, BodyRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import DamageType, InjuryKind, InjuryState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.body.book import Bearer, anatomy_for, ensure_body
from aerona.engine.body.hits import MARK_KINDS, Armour, Harm, Hit, hits_for, loss_for
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.aging import is_immortal, is_notable
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.notes import note
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import set_stats, stat


class WoundOutcome(StrEnum):
    IMMORTAL = "immortal"
    WOUNDED = "wounded"
    DIED = "died"


@dataclass
class Wounding:
    outcome: WoundOutcome | None
    injuries: list[InjuryRow] = field(default_factory=list)
    hp_lost: int = 0


NON_LETHAL_KIND = {DamageType.PIERCE: InjuryKind.PUNCTURE, DamageType.FIRE: InjuryKind.BURN}


def _spare(hit: Hit) -> Hit:
    if hit.kind is not InjuryKind.DESTROYED or not hit.part.vital:
        return hit
    return replace(hit, kind=NON_LETHAL_KIND.get(hit.damage_type, InjuryKind.CRUSH), severity=SEVERITY_MAX - 1)


def _armour(body: BodyRow) -> Armour:
    return Armour(body.armour_head, body.armour_torso, body.armour_limbs)


def _lethal(hit: Hit) -> bool:
    return hit.part.vital and hit.kind is InjuryKind.DESTROYED


async def _record(ctx: TickContext, bearer: Bearer, body: BodyRow, harm: Harm, hits: list[Hit], *, world_id: int | None) -> list[InjuryRow]:
    rows: list[InjuryRow] = []
    for hit in hits:
        if hit.absorbed:
            continue
        state = InjuryState.PERMANENT if hit.kind in MARK_KINDS else InjuryState.FRESH
        if _lethal(hit):
            state = InjuryState.LETHAL
        if hit.part.key == FINGERS and hit.kind is InjuryKind.SEVERED:
            body.fingers = max(0, body.fingers - hit.severity * ctx.rules.anatomy.fingers_per_severity)
        row = InjuryRow(
            bearer_node_id=bearer.id,
            world_id=world_id,
            part=hit.part.key,
            kind=hit.kind,
            damage_type=hit.damage_type,
            severity=hit.severity,
            state=state,
            function_loss=0 if hit.part.key == FINGERS and hit.kind is InjuryKind.SEVERED else loss_for(ctx.rules.injury, hit.kind, hit.severity),
            cause_kind=harm.cause,
            cause_node_id=harm.source_node_id or harm.killer_id,
            event_entity_id=harm.event_entity_id,
            epoch=ctx.epoch,
            year=ctx.environment.window.start if ctx.environment.window is not None else None,
            visible=hit.part.visible,
        )
        ctx.session.add(row)
        rows.append(row)
    if rows:
        await ctx.session.flush()
    return rows


def world_of(bearer: Bearer) -> int | None:
    return bearer.world_id if isinstance(bearer, EntityRow | ForeignGodRow) else None


async def _announce(ctx: TickContext, bearer: Bearer, rows: list[InjuryRow]) -> None:
    if not isinstance(bearer, EntityRow):
        return
    grave = [row for row in rows if row.severity >= ctx.rules.injury.note_severity or row.kind in MARK_KINDS]
    if not grave or not is_notable(ctx.rules, bearer, await EntityRepository(ctx.session).flags(bearer.id)):
        return
    body = await ctx.session.get(BodyRow, bearer.id)
    anatomy = anatomy_for(body) if body is not None else None
    for row in grave:
        part = anatomy.part(row.part) if anatomy is not None else None
        label = (part.label if part is not None else row.part).lower()
        await note(ctx, f"{wound_sentence(bearer.name, row.kind, label)}.", key=f"injury.{row.kind.value}", ids=[bearer.id])


INJURY_PHRASES: dict[InjuryKind, str] = {
    InjuryKind.BRUISE: "a bruising blow",
    InjuryKind.CUT: "a cut",
    InjuryKind.DEEP_CUT: "a deep cut",
    InjuryKind.PUNCTURE: "a piercing wound",
    InjuryKind.FRACTURE: "a broken bone",
    InjuryKind.CRUSH: "a crushing blow",
    InjuryKind.BURN: "burns",
    InjuryKind.FROSTBITE: "frostbite",
    InjuryKind.BITE: "a savage bite",
    InjuryKind.VENOM: "venom",
    InjuryKind.SEVERED: "the loss of a part",
    InjuryKind.GOUGED: "a gouging",
    InjuryKind.DESTROYED: "a ruinous wound",
    InjuryKind.CURSE_WITHER: "a withering curse",
    InjuryKind.VOID_TOUCH: "the touch of the void",
    InjuryKind.DIVINE_BRAND: "a divine brand",
}


def wound_sentence(name: str, kind: InjuryKind, part: str) -> str:
    if kind is InjuryKind.SEVERED:
        return f"{name} lost their {part}"
    if kind is InjuryKind.GOUGED:
        return f"{name} had their {part} gouged out"
    if kind is InjuryKind.DESTROYED:
        return f"{name}'s {part} was ruined"
    return f"{name} took {INJURY_PHRASES[kind]} to the {part}"


async def _hp_loss(ctx: TickContext, bearer: Bearer, harm: Harm, hits: list[Hit], lethal: bool) -> tuple[int, bool]:
    lost = round_half_up(sum(hit.hp for hit in hits))
    floor = 0 if lethal else 1
    if isinstance(bearer, SonRow):
        before = bearer.hp
        bearer.hp = max(floor, before - lost)
        return before - bearer.hp, bearer.hp <= 0
    if isinstance(bearer, EntityRow):
        current = stat(bearer, "hp")
        base = current if current is not None else ctx.rules.world_effects.heir_hp
        remaining = max(floor, round_half_up(base - lost))
        set_stats(bearer, hp=remaining)
        return base - remaining, remaining <= 0
    return 0, False


async def apply_hits(ctx: TickContext, bearer: Bearer, harm: Harm, *, lethal: bool = True) -> Wounding:
    if isinstance(bearer, EntityRow) and (bearer.entity_type is not EntityType.MORTAL or bearer.status is not EntityStatus.CANON):
        return Wounding(None)
    if isinstance(bearer, EntityRow) and await is_immortal(ctx.session, bearer):
        return Wounding(WoundOutcome.IMMORTAL)
    body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
    anatomy = anatomy_for(body)
    rng = ctx.rng(seed_of("hits", bearer.id, harm.cause.value, round_half_up(harm.damage)))
    hits = hits_for(ctx.rules, anatomy, harm, _armour(body), rng)
    if not lethal:
        hits = [_spare(hit) for hit in hits]
    rows = await _record(ctx, bearer, body, harm, hits, world_id=world_of(bearer))
    lost, emptied = await _hp_loss(ctx, bearer, harm, hits, lethal)
    await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
    await _announce(ctx, bearer, rows)
    killed = lethal and (emptied or any(row.state is InjuryState.LETHAL for row in rows))
    if not killed:
        return Wounding(WoundOutcome.WOUNDED, rows, lost)
    if not isinstance(bearer, EntityRow):
        return Wounding(WoundOutcome.DIED, rows, lost)
    if rows and not any(row.state is InjuryState.LETHAL for row in rows):
        max(rows, key=lambda row: row.severity).state = InjuryState.LETHAL
    result = await die(ctx, bearer, cause=harm.death_cause, killer_id=harm.killer_id, event_id=harm.event_entity_id)
    return Wounding(WoundOutcome.DIED if result is not None else WoundOutcome.WOUNDED, rows, lost)


async def fatal_injury(ctx: TickContext, mortal: EntityRow, harm: Harm) -> InjuryRow | None:
    if mortal.entity_type is not EntityType.MORTAL:
        return None
    body = await ensure_body(ctx.session, ctx.rules, mortal, ctx.epoch)
    anatomy = anatomy_for(body)
    rng = ctx.rng(seed_of("fatal", mortal.id, harm.cause.value))
    vital = [part for part in anatomy.parts if part.vital]
    target = harm.part or (vital[rng.below(len(vital))].key if vital else None)
    hits = hits_for(ctx.rules, anatomy, replace(harm, part=target, severity=harm.severity or SEVERITY_MAX), Armour(), rng)
    rows = await _record(ctx, mortal, body, harm, hits[:1], world_id=mortal.world_id)
    for row in rows:
        row.state = InjuryState.LETHAL
    return rows[0] if rows else None
