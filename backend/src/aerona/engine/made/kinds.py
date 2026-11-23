from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.life.made import ENTRY_SKILL
from aerona.constants.units import PERCENT
from aerona.core.dispatch import Handlers
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.mind import DreamRow, SkillRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.powers import PowerRegistryRow, PowerRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import RealmAwareness, RealmEntry, RealmPurpose, SurveillanceFocus
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.powers import PowerState
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.powers.sources import polity_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.terms import explaining, term

Watch = Callable[[TickContext, EntityRow, SettlementProfileRow, int], Awaitable[None]]
Inside = Callable[[TickContext, MadeRealmRow, list[MindProfileRow], EntityRow | None], Awaitable[None]]
SKILL_TOP = 100


WATCHES: Handlers[SurveillanceFocus, Watch] = Handlers(SurveillanceFocus)


@WATCHES.on(SurveillanceFocus.CRIME)
async def cut_crime(ctx: TickContext, _town: EntityRow, profile: SettlementProfileRow, reach: int) -> None:
    if "crime" not in profile.locked:
        profile.crime = clamp_percent(profile.crime - ctx.rules.surveillance.crime_cut * reach // PERCENT)


@WATCHES.on(SurveillanceFocus.DISSENT)
async def cut_dissent(ctx: TickContext, _town: EntityRow, profile: SettlementProfileRow, reach: int) -> None:
    if "unrest" not in profile.locked:
        profile.unrest = clamp_percent(profile.unrest - ctx.rules.surveillance.crime_cut * reach // PERCENT)


@WATCHES.on(SurveillanceFocus.FOREIGNERS)
async def find_spies(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, reach: int) -> None:
    for spies in list(await ctx.session.scalars(select(SpyNetworkRow).where(SpyNetworkRow.target_entity_id == town.id))):
        if ctx.rng(f"watch.spies.{spies.id}.{ctx.epoch}").chance(reach * ctx.rules.surveillance.spy_find_pct // PERCENT):
            spies.agents = max(0, spies.agents - 1)


@WATCHES.on(SurveillanceFocus.FAITH)
async def watch_faith(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, reach: int) -> None:
    shift_stat(town, "piety", -ctx.rules.surveillance.chill * reach // PERCENT, 0)


@WATCHES.on(SurveillanceFocus.MINDS)
async def watch_minds(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, _reach: int) -> None:
    here = select(EntityRow.id).where(EntityRow.location_id == town.id)
    for mind in list(await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.node_id.in_(here), MindProfileRow.seat != MindSeat.BODY))):
        if not held(mind.node_id) and "stability" not in mind.locked:
            mind.stability = clamp_percent(mind.stability + 1)


@WATCHES.on(SurveillanceFocus.GIFTED)
async def register_gifted(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, _reach: int) -> None:
    polity = await polity_of(ctx.session, town.id)
    if polity is None:
        return
    here = select(EntityRow.id).where(EntityRow.location_id == town.id, EntityRow.status == EntityStatus.CANON)
    listed = select(PowerRegistryRow.holder_node_id).where(PowerRegistryRow.polity_entity_id == polity)
    found = await ctx.session.scalars(
        select(PowerRow.holder_node_id)
        .where(PowerRow.holder_node_id.in_(here), PowerRow.holder_node_id.not_in(listed), PowerRow.state == PowerState.ACTIVE)
        .distinct()
    )
    for holder in list(found):
        if not held(holder):
            ctx.session.add(
                PowerRegistryRow(polity_entity_id=polity, holder_node_id=holder, licensed=False, conscripted=False, registered_epoch=ctx.epoch, locked=[])
            )


@WATCHES.on(SurveillanceFocus.KIND)
async def watch_kinds(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, reach: int) -> None:
    present = await ctx.session.scalars(
        select(EntityRow.affiliated_entity_id)
        .where(await present_among(ctx.session, [town.id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .where(EntityRow.affiliated_entity_id.is_not(None))
        .distinct()
    )
    await single_out(ctx, town, profile, reach, len(list(present)) - 1)


@WATCHES.on(SurveillanceFocus.LANGUAGE)
async def watch_tongues(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, reach: int) -> None:
    tongues = await ctx.session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id == town.id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE).distinct()
    )
    await single_out(ctx, town, profile, reach, len(list(tongues)) - 1)


async def single_out(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, reach: int, others: int) -> None:
    table = ctx.rules.surveillance
    await cut_crime(ctx, town, profile, reach // 2)
    if others > 0 and "unrest" not in profile.locked:
        grievance = table.identity_grievance * min(others, table.identity_most) * reach // PERCENT
        with explaining():
            term("surveillance.identity_grievance", grievance)
            profile.unrest = clamp_percent(profile.unrest + grievance)


@WATCHES.on(SurveillanceFocus.EVERYTHING)
async def watch_all(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, reach: int) -> None:
    for kind in (cut_crime, cut_dissent, find_spies, watch_faith, watch_minds, register_gifted, watch_kinds, watch_tongues):
        await kind(ctx, town, profile, reach // 2)


WATCHES.seal()


PURPOSES: Handlers[RealmPurpose, Inside] = Handlers(RealmPurpose)


@PURPOSES.on(RealmPurpose.DWELLING)
@PURPOSES.on(RealmPurpose.CONFINEMENT)
async def dwelling(_ctx: TickContext, _realm: MadeRealmRow, _minds: list[MindProfileRow], _keeper: EntityRow | None) -> None:
    return None


@PURPOSES.on(RealmPurpose.AFTERLIFE)
@PURPOSES.on(RealmPurpose.REFUGE)
async def steadied(ctx: TickContext, _realm: MadeRealmRow, minds: list[MindProfileRow], _keeper: EntityRow | None) -> None:
    for mind in minds:
        if not held(mind.node_id) and "stability" not in mind.locked:
            mind.stability = clamp_percent(mind.stability + ctx.rules.made_realms.stability_step)


@PURPOSES.on(RealmPurpose.EXPERIMENT)
async def strained(ctx: TickContext, _realm: MadeRealmRow, minds: list[MindProfileRow], keeper: EntityRow | None) -> None:
    for mind in minds:
        if not held(mind.node_id) and "stability" not in mind.locked:
            mind.stability = clamp_percent(mind.stability - ctx.rules.made_realms.stability_step)
    if keeper is not None and not held(keeper.id):
        shift_stat(keeper, "intellect", 1, 0)


@PURPOSES.on(RealmPurpose.LEISURE)
async def rested(ctx: TickContext, _realm: MadeRealmRow, minds: list[MindProfileRow], _keeper: EntityRow | None) -> None:
    for mind in minds:
        profile = await ctx.session.get(MortalProfileRow, mind.node_id)
        if profile is not None and not held(mind.node_id) and "stress" not in (profile.locked or []):
            profile.stress = clamp_percent(profile.stress - ctx.rules.made_realms.rest_relief)


@PURPOSES.on(RealmPurpose.TRAINING)
async def trained(ctx: TickContext, _realm: MadeRealmRow, minds: list[MindProfileRow], _keeper: EntityRow | None) -> None:
    for mind in minds:
        best = await ctx.session.scalar(select(SkillRow).where(SkillRow.holder_node_id == mind.node_id).order_by(SkillRow.level.desc()).limit(1))
        if best is not None and not held(mind.node_id):
            best.level = clamp_int(best.level + 1, 0, SKILL_TOP)


@PURPOSES.on(RealmPurpose.WORSHIP)
async def worshipped(ctx: TickContext, _realm: MadeRealmRow, minds: list[MindProfileRow], keeper: EntityRow | None) -> None:
    if keeper is not None and not held(keeper.id) and minds:
        await shift_standing(ctx.session, keeper, "piety", ctx.rules.made_realms.worship_gain, ctx.epoch, default=0)


@PURPOSES.on(RealmPurpose.FREE)
async def freed(ctx: TickContext, _realm: MadeRealmRow, minds: list[MindProfileRow], _keeper: EntityRow | None) -> None:
    for mind in minds:
        if not held(mind.node_id) and "maker_bond" not in mind.locked:
            mind.maker_bond = clamp_int(mind.maker_bond - 1, -PERCENT, PERCENT)


@PURPOSES.on(RealmPurpose.MEMORIAL)
async def remembered(ctx: TickContext, _realm: MadeRealmRow, _minds: list[MindProfileRow], keeper: EntityRow | None) -> None:
    if keeper is None or held(keeper.id):
        return
    dead = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    for state in await ctx.session.scalars(select(MindStateRow).where(MindStateRow.owner_node_id == keeper.id, MindStateRow.mind_node_id.in_(dead))):
        if "fidelity_pct" not in state.locked:
            state.fidelity_pct = clamp_percent(state.fidelity_pct + ctx.rules.made_realms.memorial_fidelity)


@PURPOSES.on(RealmPurpose.MARKET)
async def traded(ctx: TickContext, realm: MadeRealmRow, minds: list[MindProfileRow], keeper: EntityRow | None) -> None:
    working = sum(1 for mind in minds if not mind.dormant)
    if keeper is None or held(keeper.id) or not working:
        return
    gain = round_half_up(ctx.rules.made_realms.market_yield * working * realm.time_ratio_pct / PERCENT)
    with explaining():
        term("made_realms.market_yield", gain, source_node_id=keeper.id)
        await shift_points(ctx.session, keeper, gain)


@PURPOSES.on(RealmPurpose.LABOUR)
async def labour(_ctx: TickContext, _realm: MadeRealmRow, _minds: list[MindProfileRow], _keeper: EntityRow | None) -> None:
    return None


PURPOSES.seal()
AWARE_ESCAPE: Mapping[RealmAwareness, int] = total(RealmAwareness, {RealmAwareness.KNOWS: 100, RealmAwareness.RUMOURED: 50, RealmAwareness.UNAWARE: 0})


async def entry_refused(ctx: TickContext, realm: MadeRealmRow, mind_id: int) -> str | None:
    being = await ctx.session.get(EntityRow, mind_id)
    if realm.entry is RealmEntry.DREAM:
        dreamt = await ctx.session.scalar(select(DreamRow.id).where(DreamRow.dreamer_node_id == mind_id, DreamRow.epoch >= ctx.epoch - 1).limit(1))
        return None if dreamt is not None else "only the dreaming walk into this realm"
    if realm.entry is RealmEntry.DEATH and being is not None and being.status is EntityStatus.CANON and being.entity_type is EntityType.MORTAL:
        return "only the dead enter this realm"
    if realm.entry is RealmEntry.BIRTH:
        return "only those born into this realm are in it"
    skill = ENTRY_SKILL[realm.entry]
    if skill is None:
        return None
    level = await ctx.session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id == mind_id, SkillRow.skill == skill, SkillRow.subject_node_id.is_(None))
    )
    return None if int(level or 0) >= ctx.rules.made_realms.entry_skill else "entering this realm takes a craft this one lacks"
