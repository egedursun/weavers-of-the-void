from collections import Counter
from collections.abc import Awaitable, Callable
from types import MappingProxyType

from sqlalchemy import select

from aerona.catalog.structures import acting
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.entity import HERO_ROLES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import hidden_sky
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.printing import printed
from aerona.engine.mind.hooks import practised
from aerona.engine.phases.knowledge_levels import known_records, shift_level
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.structures.readers import Working, working

K = StructureKind
Effect = Callable[[TickContext, Working, EntityRow, "Tally"], Awaitable[None]]


class Tally:
    def __init__(self) -> None:
        self.deepened = 0
        self.deepened_in: Counter[int | None] = Counter()
        self.held = 0
        self.duels = 0


def hold_floor(entity: EntityRow, key: str, floor: int, step: int) -> bool:
    current = stat(entity, key)
    if current is None or current >= floor:
        return False
    set_stats(entity, **{key: clamp_int(current + min(step, floor - current), 0, PERCENT)})
    return True


def floor_of(item: Working, pct: int) -> int:
    return round_half_up(item.profile.effect_pct * pct / PERCENT)


async def piety_house(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    table = ctx.rules.structure_functions
    pct = {
        K.TEMPLE: table.temple_piety_pct,
        K.SHRINE: table.shrine_piety_pct,
        K.MONASTERY: table.monastery_piety_pct,
        K.WONDER: table.wonder_piety_pct,
    }.get(item.profile.kind, table.shrine_piety_pct)
    tally.held += hold_floor(host, "piety", floor_of(item, pct), ctx.rules.record_schema.function_step)


async def deepen(ctx: TickContext, item: Working, host: EntityRow, tally: Tally, *, pct: int, branch: KnowledgeBranch | None = None) -> None:
    if tally.deepened_in[item.structure.world_id] >= ctx.rules.record_schema.function_knowledge_cap or not ctx.rng(
        f"structure_knowledge.{item.structure.id}"
    ).chance(item.profile.effect_pct * pct / PERCENT):
        return
    options = [
        entry
        for entry in await known_records(ctx.session, host.id)
        if knowledge_level(ctx.rules, entry) < ctx.rules.knowledge.level_cap and (branch is None or entry.knowledge_branch is branch)
    ]
    if not options:
        return
    chosen = ctx.rng(f"structure_pick.{item.structure.id}").pick(options)
    level = shift_level(ctx.rules, chosen, 1)
    if level is None:
        return
    tally.deepened += 1
    tally.deepened_in[item.structure.world_id] += 1
    await record(
        ctx,
        "living_stats.work_knowledge",
        roles={IncidentRole.ACTOR: item.structure.id, IncidentRole.SUBJECT: chosen.id, IncidentRole.PLACE: host.id},
        facts={"level": level, "effect": item.profile.effect_pct * pct / PERCENT},
        steps=(
            StepDraft(
                StepAction.LEARN,
                actor=host.id,
                target=chosen.id,
                instrument_kind=InstrumentKind.STRUCTURE,
                instrument_node=item.structure.id,
                amount=level,
                unit=FactUnit.KNOWLEDGE,
                outcome=StepOutcome.SUCCESS,
            ),
        ),
        place=host.id,
    )


async def library(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    await deepen(ctx, item, host, tally, pct=ctx.rules.structure_functions.library_deepen_pct)


async def monastery(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    await piety_house(ctx, item, host, tally)
    await deepen(ctx, item, host, tally, pct=ctx.rules.structure_functions.monastery_deepen_pct)


async def academy(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    await deepen(ctx, item, host, tally, pct=ctx.rules.structure_functions.academy_deepen_pct)


async def archive(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    await deepen(ctx, item, host, tally, pct=ctx.rules.structure_functions.archive_deepen_pct)


async def observatory(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    clear = 1 - await hidden_sky(ctx.session, ctx.rules, host.world_id)
    await deepen(ctx, item, host, tally, pct=round(ctx.rules.structure_functions.observatory_deepen_pct * clear), branch=KnowledgeBranch.ASTRONOMY)


async def residents(ctx: TickContext, host: EntityRow, roles: frozenset[MortalRole]) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_in(ctx.session, host),
            EntityRow.mortal_role.in_(list(roles)),
        )
        .order_by(EntityRow.id)
    )
    return list(rows)


async def school(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    table = ctx.rules.structure_functions
    people = host if host.entity_type is EntityType.PEOPLE else await people_of(ctx.session, host)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is not None and "literacy" not in culture.locked:
        pressed = await printed(ctx.session, host.id)
        reach = table.school_literacy_pct + (
            round_half_up(table.school_literacy_pct * ctx.rules.technique_effects.press_literacy_pct / PERCENT) if pressed else 0
        )
        floor = floor_of(item, reach)
        if culture.literacy < floor:
            culture.literacy = clamp_int(culture.literacy + min(table.school_literacy_step, floor - culture.literacy), 0, PERCENT)
            tally.held += 1
    for scholar in await residents(ctx, host, frozenset({MortalRole.SCRIBE, MortalRole.SAGE, MortalRole.APPRENTICE, MortalRole.SCIENTIST})):
        await practised(ctx, scholar.id, SkillKind.WRITING, round_half_up(table.school_xp * item.strength))


async def hospital(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    xp = round_half_up(ctx.rules.structure_functions.hospital_healer_xp * item.strength)
    for healer in await residents(ctx, host, frozenset({MortalRole.HEALER, MortalRole.PRIEST, MortalRole.PHYSICIAN})):
        await practised(ctx, healer.id, SkillKind.MEDICINE, xp)


async def stronghold(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    table = ctx.rules.structure_functions
    gain = table.citadel_defense if item.profile.kind is K.CITADEL else table.fort_defense
    tally.held += hold_floor(host, "defense", round_half_up(gain * item.strength * item.profile.level), gain)


async def market(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    tally.held += hold_floor(host, "prosperity", floor_of(item, ctx.rules.structure_functions.market_prosperity_pct), ctx.rules.record_schema.function_step)


async def workshop(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    key = "wealth" if stat(host, "wealth") is not None else "prosperity"
    tally.held += hold_floor(host, key, floor_of(item, ctx.rules.structure_functions.workshop_wealth_pct), ctx.rules.record_schema.function_step)


async def arena(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    table = ctx.rules.structure_functions
    rng = ctx.rng(f"arena.{item.structure.id}")
    if not rng.chance(item.profile.effect_pct * table.arena_duel_chance / PERCENT):
        return
    fighters = await residents(ctx, host, HERO_ROLES)
    if len(fighters) < 2:
        return
    first = rng.pick(fighters)
    second = rng.pick([fighter for fighter in fighters if fighter.id != first.id])
    first_roll = stat_or(first, "strength", 0) + rng.die(PERCENT)
    second_roll = stat_or(second, "strength", 0) + rng.die(PERCENT)
    victor, loser = (first, second) if first_roll >= second_roll else (second, first)
    victor.importance = (victor.importance or 0) + table.arena_duel_renown
    await apply_hits(ctx, loser, Harm(table.arena_duel_hp, HarmCause.SPORT, f"fell in the arena of {item.structure.name}"))
    await record(
        ctx,
        "structures.duel",
        roles={IncidentRole.ACTOR: victor.id, IncidentRole.OPPONENT: loser.id, IncidentRole.PLACE: item.structure.id},
        facts={"victor_roll": max(first_roll, second_roll), "loser_roll": min(first_roll, second_roll), "renown": table.arena_duel_renown},
        steps=(
            StepDraft(
                StepAction.STRIKE,
                actor=victor.id,
                target=loser.id,
                round=1,
                instrument_kind=InstrumentKind.BODY,
                damage_type=DamageType.BLUNT,
                amount=table.arena_duel_hp,
                unit=FactUnit.HP,
                outcome=StepOutcome.WOUNDED,
            ),
            StepDraft(StepAction.WIN, actor=victor.id, target=loser.id, round=1),
        ),
        place=item.structure.id,
    )
    tally.duels += 1


async def nothing(ctx: TickContext, item: Working, host: EntityRow, tally: Tally) -> None:
    del ctx, item, host, tally


EFFECTS: MappingProxyType[StructureKind, Effect] = acting(
    {
        K.TEMPLE: piety_house,
        K.SHRINE: piety_house,
        K.MONASTERY: monastery,
        K.WONDER: piety_house,
        K.LIBRARY: library,
        K.ACADEMY: academy,
        K.COSMIC_ARCHIVE: archive,
        K.OBSERVATORY: observatory,
        K.SCHOOL: school,
        K.HOSPITAL: hospital,
        K.FORT: stronghold,
        K.CITADEL: stronghold,
        K.MARKET: market,
        K.WORKSHOP: workshop,
        K.ARENA: arena,
    }
)


async def dedication(ctx: TickContext, item: Working, host: EntityRow | None) -> None:
    profile = item.profile
    if profile.dedicated_son_id is None:
        return
    son = await ctx.session.get(SonRow, profile.dedicated_son_id)
    if son is None or not son.alive:
        return
    table = ctx.rules.structure_functions
    if profile.anchor:
        son.existence = min(PERCENT, son.existence + round_half_up(table.anchor_existence * item.strength))
    patron = await living_patron(ctx.session, host) if host is not None else None
    if host is not None and patron is not None and patron.id == son.id and stat(host, "piety") is not None:
        set_stats(host, piety=clamp_int((stat(host, "piety") or 0) + round_half_up(table.dedicated_faith * item.strength), 0, PERCENT))


async def run_functions(ctx: TickContext) -> Tally:
    tally = Tally()
    for item in ctx.rng("functions.order").shuffled(await working(ctx.session, list(StructureKind))):
        host = await ctx.session.get(EntityRow, item.profile.host_entity_id) if item.profile.host_entity_id is not None else None
        live = host if host is not None and host.status is EntityStatus.CANON else None
        await dedication(ctx, item, live)
        if live is None:
            continue
        await EFFECTS.get(item.profile.kind, nothing)(ctx, item, live, tally)
    return tally
