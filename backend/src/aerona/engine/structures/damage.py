from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.domain import STANDING_STATES
from aerona.catalog.life_traits import STRUCTURE_SECTION_TRAITS, having
from aerona.catalog.structure_sections import FORM_GUARD, FORMS
from aerona.catalog.structures import KNOWLEDGE_KEEPERS, MEGASTRUCTURES, function_kind
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.integrity import HarmForce
from aerona.domain.enums.life_traits import StructureSectionTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.enums.structure import ConstructionState, StructureKind, StructureSection
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.happenings.effects import scar
from aerona.engine.means.strength import siege_guard
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import add_flag, living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.structures.integrity import StructureStrike, ensure_sections, mend_sections, overall, strike_rows
from aerona.engine.structures.megastructures import catastrophe
from aerona.engine.structures.profiles import material_props, refresh, standing_state
from aerona.engine.structures.workshops import unlink

X = StructureSection
BREACHES = having(STRUCTURE_SECTION_TRAITS, StructureSectionTrait.BREACHES)
FALLEN = frozenset({X.KEEP})
BREACHED_DECKS = having(STRUCTURE_SECTION_TRAITS, StructureSectionTrait.BREACHED_DECKS)


async def open_siege(session: AsyncSession, host_id: int) -> SiegeRow | None:
    statement = select(SiegeRow).where(SiegeRow.besieged_entity_id == host_id, SiegeRow.status == SiegeStatus.ONGOING)
    return await session.scalar(statement.order_by(SiegeRow.id.desc()).limit(1))


async def siege_effects(ctx: TickContext, host: EntityRow | None, fallen: set[StructureSection], weakened: set[StructureSection]) -> list[str]:
    siege = await open_siege(ctx.session, host.id) if host is not None else None
    if siege is None or "breaches" in siege.locked:
        return []
    found = []
    if weakened & BREACHES:
        siege.breaches += len(weakened & BREACHES)
        found.append("breached")
    if fallen & FALLEN:
        siege.breaches += ctx.rules.integrity.keep_breaches
        found.append("keep fallen")
    return found


async def lose_grain(ctx: TickContext, host: EntityRow, pct: int) -> int:
    stock = await holding(ctx.session, host.id, CommodityKind.GRAIN)
    lost = round_half_up(stock * pct / PERCENT)
    if lost > 0:
        await goods_of(ctx.session, ctx.epoch).take_units(host.id, CommodityKind.GRAIN, lost, GoodsFlow.LOSS)
    return lost


async def house_effects(
    ctx: TickContext, profile: StructureProfileRow, host: EntityRow | None, fallen: set[StructureSection], weakened: set[StructureSection]
) -> list[str]:
    table = ctx.rules.integrity
    found = []
    if X.SANCTUM in fallen and host is not None and stat(host, "piety") is not None:
        shift_stat(host, "piety", -table.desecration_piety)
        found.append("sanctum desecrated")
    if X.ARCHIVE in weakened and function_kind(profile.kind) in KNOWLEDGE_KEEPERS and "capacity" not in profile.locked:
        profile.capacity = round_half_up(profile.capacity * (PERCENT - table.archive_loss_pct) / PERCENT)
        found.append("archive lost")
    if X.STORES in fallen and host is not None and await lose_grain(ctx, host, table.stores_loss_pct):
        found.append("stores lost")
    return found


async def works_effects(ctx: TickContext, work: EntityRow, host: EntityRow | None, fallen: set[StructureSection]) -> list[str]:
    table = ctx.rules.integrity
    found = []
    if X.SPAN in fallen:
        await scar(ctx, work.id, ScarKind.BRIDGE_DOWN, table.bridge_scar)
        found.append("span fallen")
    if X.SLUICE in fallen and host is not None:
        await lose_grain(ctx, host, table.flood_loss_pct)
        found.append("sluice burst")
    population = stat(host, "population") if host is not None else None
    if fallen & BREACHED_DECKS and host is not None and population is not None:
        shift_stat(host, "population", -round_half_up(population * table.breach_population_pct / PERCENT))
        found.append("decks breached")
    return found


async def mega_effects(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, host: EntityRow | None) -> list[str]:
    found = await catastrophe(ctx, work, profile)
    if host is None:
        return found
    for sibling in list(await ctx.session.scalars(select(StructureProfileRow).where(StructureProfileRow.host_entity_id == host.id))):
        other = await ctx.session.get(EntityRow, sibling.structure_entity_id)
        if other is not None and other.id != work.id and sibling.construction_state in STANDING_STATES:
            await harm(ctx, other, sibling, ctx.rules.integrity.catastrophe_loss, cause=f"the fall of {work.name}", force=HarmForce.IMPACT, quiet=True)
    return found


async def consequences(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, strike: StructureStrike) -> list[str]:
    fallen = set(strike.destroyed)
    weakened = fallen | set(strike.disabled)
    host = await living_entity(ctx.session, profile.host_entity_id) if profile.host_entity_id is not None else None
    found = await siege_effects(ctx, host, fallen, weakened)
    found += await house_effects(ctx, profile, host, fallen, weakened)
    found += await works_effects(ctx, work, host, fallen)
    if X.CONTROL_CORE in fallen and profile.kind in MEGASTRUCTURES:
        found += await mega_effects(ctx, work, profile, host)
    return found


async def harm(
    ctx: TickContext,
    work: EntityRow,
    profile: StructureProfileRow,
    loss: float,
    *,
    cause: str,
    force: HarmForce = HarmForce.DECAY,
    quiet: bool = False,
    even: bool = False,
) -> bool:
    if "condition" in profile.locked or loss <= 0:
        return False
    before = profile.condition
    rows = await ensure_sections(ctx.session, work, profile)
    design = await ctx.session.get(StructureDesignRow, profile.design_id) if profile.design_id is not None else None
    form = design.form if design is not None and design.form is not None else FORMS[profile.kind]
    guard = FORM_GUARD.get(form)
    loss = (
        loss * (guard.get(force, PERCENT) if guard is not None else PERCENT) / PERCENT * siege_guard(ctx.rules, await material_props(ctx.session, work), force)
    )
    strike = strike_rows(ctx, rows, loss, force, even=even)
    profile.condition = clamp_int(overall(rows), 0, PERCENT)
    if profile.construction_state in STANDING_STATES and "construction_state" not in profile.locked:
        profile.construction_state = standing_state(ctx.rules, profile)
    collapsed = profile.condition <= 0 or strike.collapsed
    if collapsed:
        profile.construction_state = ConstructionState.RUINED
        await add_flag(ctx.session, work.id, EntityFlag.RUIN, ctx.epoch)
        await unlink(ctx.session, work.id)
    happened = await consequences(ctx, work, profile, strike)
    await refresh(ctx.session, ctx.rules, work, profile)
    if not quiet or happened:
        await record(
            ctx,
            "structures.collapsed" if collapsed else "structures.damaged",
            roles={IncidentRole.SUBJECT: work.id, IncidentRole.OWNER: profile.host_entity_id},
            facts={"force": force, "before": before, "after": profile.condition, "loss": round(loss), "sections_lost": list(strike.destroyed)},
            steps=tuple(
                StepDraft(
                    StepAction.COLLAPSE if collapsed else StepAction.BREAK,
                    target=work.id,
                    locus_kind=StepLocus.STRUCTURE_SECTION,
                    locus_key=section.value,
                    outcome=StepOutcome.DESTROYED,
                    record_table="structure_sections",
                    record_key=f"{work.id}:{section.value}",
                )
                for section in strike.destroyed
            ),
            place=work.location_id,
        )
    return collapsed


async def ruin_profile(session: AsyncSession, structure_id: int) -> None:
    profile = await session.get(StructureProfileRow, structure_id)
    if profile is None:
        return
    profile.construction_state = ConstructionState.RUINED
    profile.effect_pct = 0
    await unlink(session, structure_id)


async def quake_loss(ctx: TickContext, work: EntityRow, base: float) -> float:
    props = await material_props(ctx.session, work)
    toughness = props.toughness if props is not None else 0
    return base * (1 - fraction(toughness) * fraction(ctx.rules.upkeep.quake_toughness_pct))


DEFENCES = frozenset({StructureKind.WALL, StructureKind.GATE, StructureKind.TOWER, StructureKind.CITADEL, StructureKind.FORT, StructureKind.WATCHTOWER})


async def defences_of(session: AsyncSession, host_id: int) -> list[tuple[EntityRow, StructureProfileRow]]:
    found = []
    statement = select(StructureProfileRow).where(StructureProfileRow.host_entity_id == host_id).order_by(StructureProfileRow.structure_entity_id)
    for profile in await session.scalars(statement):
        if function_kind(profile.kind) in DEFENCES and profile.construction_state in STANDING_STATES:
            work = await session.get(EntityRow, profile.structure_entity_id)
            if work is not None:
                found.append((work, profile))
    return found


async def strike_defences(ctx: TickContext, host_id: int, loss: float, cause: str) -> int:
    struck = 0
    for work, profile in await defences_of(ctx.session, host_id):
        await harm(ctx, work, profile, loss, cause=cause, force=HarmForce.SIEGE, quiet=True)
        struck += 1
    return struck


async def mend_defences(ctx: TickContext, host_id: int, amount: int) -> int:
    mended = 0
    for work, profile in await defences_of(ctx.session, host_id):
        if "condition" in profile.locked:
            continue
        rows = await ensure_sections(ctx.session, work, profile)
        mended += await mend_sections(ctx.session, ctx.rules, work.id, amount, rebuild=False)
        profile.condition = clamp_int(overall(rows), 0, PERCENT)
    return mended
