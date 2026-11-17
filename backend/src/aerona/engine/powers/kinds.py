import math
from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import func, select

from aerona.catalog.kinds.power_hazards import POWER_HAZARDS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.powers import MagicSystemRow, PowerRegistryRow, PowerRow, PowerSourceRow, SourceTideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.powers import (
    GiftedAttitude,
    GiftedStance,
    Learnability,
    PowerHazard,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerTrigger,
    SourceAccess,
    SourceLocus,
    SystemRelation,
    TideCycle,
)
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import shift_stat, stat_or

Check = Callable[[TickContext, EntityRow], Awaitable[bool]]
GIFTED_ORIGINS = frozenset({PowerOrigin.BORN, PowerOrigin.AWAKENED, PowerOrigin.EXPOSURE, PowerOrigin.BLOODLINE})
MADE_ORIGINS = frozenset({MindOrigin.MADE, MindOrigin.GROWN, MindOrigin.TRAINED, MindOrigin.COPIED, MindOrigin.MERGED, MindOrigin.DIVIDED})
PACT_BONDS = frozenset({BondKind.WORSHIPS, BondKind.PARTY_TO, BondKind.SWORN_KIN})
SEASONS = 4
STANCE_ATTITUDE: Mapping[GiftedStance, GiftedAttitude | None] = total(
    GiftedStance,
    {
        GiftedStance.SACRED: GiftedAttitude.HONOURED,
        GiftedStance.FORBIDDEN: GiftedAttitude.PERSECUTED,
        GiftedStance.SUSPECT: GiftedAttitude.FEARED,
        GiftedStance.TOOL: GiftedAttitude.REGULATED,
        GiftedStance.SILENT: None,
    },
)


async def holds_origin(ctx: TickContext, user: EntityRow, origins: frozenset[PowerOrigin]) -> bool:
    found = await ctx.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id == user.id, PowerRow.origin.in_(list(origins))).limit(1))
    return found is not None


async def anyone(_ctx: TickContext, _user: EntityRow) -> bool:
    return True


async def gifted(ctx: TickContext, user: EntityRow) -> bool:
    return await holds_origin(ctx, user, GIFTED_ORIGINS)


async def trained(ctx: TickContext, user: EntityRow) -> bool:
    return await holds_origin(ctx, user, frozenset({PowerOrigin.DISCIPLINE})) or await gifted(ctx, user)


async def granted(ctx: TickContext, user: EntityRow) -> bool:
    return await holds_origin(ctx, user, frozenset({PowerOrigin.GRANTED}))


async def bloodline(ctx: TickContext, user: EntityRow) -> bool:
    return await holds_origin(ctx, user, frozenset({PowerOrigin.BLOODLINE, PowerOrigin.BORN}))


async def bonded(ctx: TickContext, user: EntityRow) -> bool:
    if await holds_origin(ctx, user, frozenset({PowerOrigin.BONDED})):
        return True
    found = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == user.id, BondRow.kind.in_(list(PACT_BONDS)), BondRow.state == BondState.ACTIVE).limit(1)
    )
    return found is not None


async def nobody(_ctx: TickContext, _user: EntityRow) -> bool:
    return False


async def made(ctx: TickContext, user: EntityRow) -> bool:
    mind = await ctx.session.get(MindProfileRow, user.id)
    return mind is not None and mind.origin in MADE_ORIGINS


ACCESS: Mapping[SourceAccess, Check] = total(
    SourceAccess,
    {
        SourceAccess.ANYONE: anyone,
        SourceAccess.GIFTED: gifted,
        SourceAccess.TRAINED: trained,
        SourceAccess.GRANTED: granted,
        SourceAccess.BLOODLINE: bloodline,
        SourceAccess.BONDED: bonded,
        SourceAccess.MADE: made,
    },
)
TEACHING: Mapping[Learnability, Check] = total(
    Learnability,
    {
        Learnability.ANYONE: anyone,
        Learnability.GIFTED_ONLY: gifted,
        Learnability.GRANTED_ONLY: granted,
        Learnability.CANNOT_BE_TAUGHT: nobody,
    },
)


async def access_refused(ctx: TickContext, user: EntityRow, source: PowerSourceRow) -> str | None:
    if await ACCESS[source.access](ctx, user):
        return None
    return f"{source.name} opens only to the {spoken(source.access)}"


async def licence_refused(ctx: TickContext, user: EntityRow, polity_id: int | None) -> str | None:
    if polity_id is None:
        return None
    licensed = await ctx.session.scalar(
        select(PowerRegistryRow.licensed).where(PowerRegistryRow.holder_node_id == user.id, PowerRegistryRow.polity_entity_id == polity_id).limit(1)
    )
    return None if licensed else "drawing on it here needs a licence you do not hold"


async def teachable(ctx: TickContext, system_id: int | None, learner: EntityRow) -> bool:
    system = await ctx.session.get(MagicSystemRow, system_id) if system_id is not None else None
    return system is None or await TEACHING[system.learnability](ctx, learner)


async def structure_holds(ctx: TickContext, power: PowerRow) -> float:
    system = await ctx.session.get(MagicSystemRow, power.system_id) if power.system_id is not None else None
    if system is None:
        return 1.0
    table = ctx.rules.magic_systems
    kind = system.structure
    if kind is PowerStructure.CRAFTED:
        return 1.0 if power.item_node_id is not None else table.unheld_structure_pct / PERCENT
    if kind is PowerStructure.GRANTED:
        giver = await ctx.session.get(EntityRow, power.granted_by_node_id) if power.granted_by_node_id is not None else None
        return 1.0 if power.granted_by_node_id is not None and (giver is None or giver.status is EntityStatus.CANON) else table.unheld_structure_pct / PERCENT
    if kind is PowerStructure.BONDED:
        holder = await ctx.session.get(EntityRow, power.holder_node_id)
        return 1.0 if holder is not None and await bonded(ctx, holder) else table.unheld_structure_pct / PERCENT
    if kind is PowerStructure.INNATE:
        return (PERCENT + table.innate_bonus_pct) / PERCENT if power.origin in GIFTED_ORIGINS else 1.0
    return total(
        PowerStructure,
        {
            PowerStructure.RITE: 1.0,
            PowerStructure.MIXED: 1.0,
            PowerStructure.CRAFTED: 1.0,
            PowerStructure.GRANTED: 1.0,
            PowerStructure.BONDED: 1.0,
            PowerStructure.INNATE: 1.0,
        },
    )[kind]


async def system_bond(ctx: TickContext, relation: SystemRelation) -> float:
    table = ctx.rules.magic_systems
    return total(
        SystemRelation,
        {
            SystemRelation.OPPOSES: 1 - table.oppose_pct / PERCENT,
            SystemRelation.COMPLEMENTS: 1 + table.complement_pct / PERCENT,
            SystemRelation.SAME_ROOT: 1.0,
            SystemRelation.UNAWARE: 1.0,
        },
    )[relation]


async def locus_factor(ctx: TickContext, user: EntityRow, locus: SourceLocus) -> float:
    table = ctx.rules.power_sources
    profile = await ctx.session.get(MortalProfileRow, user.id)
    stress = profile.stress if profile is not None else 0
    if locus is SourceLocus.EMOTION:
        return 1 + (stress - PERCENT // 2) / PERCENT * table.locus_pct / PERCENT
    if locus is SourceLocus.DREAM:
        return 1 + (PERCENT // 2 - stress) / PERCENT * table.locus_pct / PERCENT
    if locus is SourceLocus.STORY:
        return 1 + min(PERCENT, stat_or(user, "renown", 0)) / PERCENT * table.locus_pct / PERCENT
    if locus is SourceLocus.BOND:
        pacts = await ctx.session.scalar(
            select(func.count())
            .select_from(BondRow)
            .where(BondRow.source_node_id == user.id, BondRow.kind.in_(list(PACT_BONDS)), BondRow.state == BondState.ACTIVE)
        )
        return 1 + min(4, int(pacts or 0)) * table.locus_pct / PERCENT / 4
    if locus is SourceLocus.MADE_THINGS:
        made_here = await ctx.session.scalar(
            select(func.count())
            .select_from(EntityRow)
            .where(EntityRow.location_id == user.location_id, EntityRow.entity_type.in_([EntityType.ITEM, EntityType.STRUCTURE]))
        )
        return 1 + min(10, int(made_here or 0)) * table.locus_pct / PERCENT / 10
    return 1.0


def tide_period(tide: SourceTideRow, moon_days: int) -> int:
    return max(
        1,
        total(
            TideCycle,
            {
                TideCycle.SEASON: SEASONS,
                TideCycle.SKY: max(1, moon_days // 7),
                TideCycle.EPOCH: tide.period,
                TideCycle.AUTHORED: tide.period,
            },
        )[tide.cycle],
    )


def tide_wave(epoch: int, tide: SourceTideRow, moon_days: int) -> float:
    if tide.cycle is TideCycle.AUTHORED:
        return tide.phase / PERCENT
    period = tide_period(tide, moon_days)
    return math.sin(2 * math.pi * ((epoch + tide.phase) % period) / period)


async def triggered(ctx: TickContext, holder: EntityRow, triggers: set[PowerTrigger]) -> bool:
    profile = await ctx.session.get(MortalProfileRow, holder.id)
    if PowerTrigger.EMOTION in triggers and profile is not None and profile.stress >= PERCENT * 3 // 4:
        return True
    return PowerTrigger.WILL in triggers and stat_or(holder, "willpower", 0) >= PERCENT * 3 // 4


async def suffer(ctx: TickContext, user: EntityRow, power: PowerRow, hazard: PowerHazard) -> str | None:
    if held(user.id):
        return None
    spec = POWER_HAZARDS[hazard]
    await harm(ctx, user, power, spec.harm)
    if spec.noted:
        await note(ctx, f"Drawing on power marked {user.name}: {spoken(hazard)}.", key="power.hazard", ids=[user.id])
    return hazard.value


async def harm(ctx: TickContext, user: EntityRow, power: PowerRow, kind: str) -> None:
    table = ctx.rules.powers
    if kind == "wound":
        shift_stat(user, "hp", -table.scar_hp, 0)
    elif kind == "stress":
        profile = await ctx.session.get(MortalProfileRow, user.id)
        if profile is not None and "stress" not in (profile.locked or []):
            profile.stress = clamp_percent(profile.stress + table.hazard_stress)
    elif kind == "exhaust" and "state" not in power.locked:
        power.state = PowerState.EXHAUSTED
    elif kind == "mutate":
        await add_flag(ctx.session, user.id, EntityFlag.MUTATED, ctx.epoch)
    elif kind == "strain" and "state" not in power.locked:
        power.state = PowerState.STRAINED
    elif kind == "notice" and user.location_id is not None:
        shift_stat(user, "renown", table.hazard_stress // 2, 0)
