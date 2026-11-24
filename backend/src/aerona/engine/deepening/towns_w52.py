from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.deepened import DENSE, HEAVY_CURSES, HELD_SECTIONS, LIVING_GARDENS, NEW_QUARTERS, SENSE_AIDS, SHAPED_FORMS, SOCIAL_COOPS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.crafts import AssistiveAidRow, PublicClockRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.customs import CooperativeRow, PoorReliefRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.integrity import StructureSectionRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.crafts import AssistiveAid, ClockKind
from aerona.domain.enums.culture import CurseKind, Technique
from aerona.domain.enums.customs import CoopPurpose, ReliefKind
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.made import RelicStance
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.structure import BuilderKind, BuildingForm, StructureSection
from aerona.engine.agrarian.ruin import mark_ruin
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.economy.stocks import goods_of
from aerona.engine.lore.research_depth import add_progress
from aerona.engine.mind.skills import practise
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term


@dataclass
class TownTally:
    quarters: int = 0
    ruins: int = 0
    relief: int = 0
    learning: int = 0
    gardens: int = 0
    works: int = 0
    relics: int = 0
    aids: int = 0
    clocks: int = 0
    curses: int = 0
    coops: int = 0


def nudge(profile: SettlementProfileRow, field: str, amount: int, key: str) -> None:
    if field in profile.locked or not amount:
        return
    term(key, amount)
    setattr(profile, field, clamp_int(getattr(profile, field) + amount, 0, PERCENT))


async def town_of(ctx: TickContext, town_id: int) -> tuple[EntityRow, SettlementProfileRow] | None:
    town = await living_entity(ctx.session, town_id)
    profile = await ctx.session.get(SettlementProfileRow, town_id)
    if town is None or profile is None or held(town_id):
        return None
    return town, profile


async def live_quarters(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(select(DistrictRow).where(DistrictRow.kind.in_(sorted(NEW_QUARTERS))).order_by(DistrictRow.id))
    for district in list(rows):
        found = await town_of(ctx, district.settlement_entity_id)
        if found is None or "condition" in district.locked:
            continue
        town, profile = found
        ground = await ctx.session.get(RegionEnvironmentRow, town.location_id) if town.location_id is not None else None
        with explaining():
            if district.kind is DistrictKind.PILGRIM_QUARTER:
                term("deepened.pilgrim_piety", table.pilgrim_piety)
                shift_stat(town, "piety", table.pilgrim_piety)
                if ground is not None and not held(ground.entity_id) and "disease_load" not in ground.locked:
                    term("deepened.pilgrim_disease", table.pilgrim_disease)
                    ground.disease_load = clamp_int(ground.disease_load + table.pilgrim_disease, 0, PERCENT)
            elif district.kind is DistrictKind.CARAVAN_QUARTER:
                term("deepened.caravan_prosperity", table.caravan_prosperity)
                shift_stat(town, "prosperity", table.caravan_prosperity)
                profile.foreigners = {**profile.foreigners, "traders": int(profile.foreigners.get("traders", 0)) + table.caravan_foreigners}
            elif ground is not None and ground.wetland >= table.floating_wet_at:
                term("deepened.floating_rise", table.floating_rise)
                district.condition = clamp_int(district.condition + table.floating_rise, 0, PERCENT)
        tally.quarters += 1


async def ruin_by_sinkhole_and_plague(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    ended = await ctx.session.scalars(
        select(OutbreakRow).where(OutbreakRow.status == OutbreakStatus.ENDED, OutbreakRow.infected >= table.plague_ruin_infected).order_by(OutbreakRow.id)
    )
    regions = sorted({row.region_entity_id for row in ended})
    hollowed = await ctx.session.scalars(
        select(RegionEnvironmentRow).where(RegionEnvironmentRow.mined >= table.sinkhole_mined_at).order_by(RegionEnvironmentRow.entity_id)
    )
    causes = [(region, RebuildCause.PLAGUE) for region in regions] + [
        (ground.entity_id, RebuildCause.SINKHOLE) for ground in hollowed if ctx.rng(f"sinkhole.{ground.entity_id}.{ctx.epoch}").chance(table.sinkhole_pct)
    ]
    for region, cause in causes:
        towns = await ctx.session.scalars(
            select(EntityRow).where(EntityRow.location_id == region, EntityRow.entity_type == EntityType.SETTLEMENT).order_by(EntityRow.id)
        )
        for town in list(towns):
            row = await mark_ruin(ctx, town, cause)
            if row is not None and row.started_epoch == ctx.epoch and row.cause is cause:
                tally.ruins += 1
                await record(ctx, "deepened.town_ruined", roles={IncidentRole.SUBJECT: town.id}, facts={"cause": cause}, place=town.id)


async def choose_relief(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    profiles = await ctx.session.scalars(select(SettlementProfileRow).order_by(SettlementProfileRow.settlement_entity_id))
    for profile in list(profiles):
        town = await living_entity(ctx.session, profile.settlement_entity_id)
        ruler = await realm_of(ctx.session, town.id) if town is not None else None
        if town is None or held(town.id) or ruler is None:
            continue
        wanted = ReliefKind.SHELTER if profile.homeless >= table.shelter_homeless_at else ReliefKind.PUBLIC_KITCHEN if profile.rationing else None
        if wanted is None:
            continue
        found = await ctx.session.get(PoorReliefRow, ruler)
        if found is not None and found.kind is not wanted and "kind" in found.locked:
            continue
        if found is None or found.kind is not wanted:
            if found is None:
                ctx.session.add(PoorReliefRow(polity_entity_id=ruler, kind=wanted, budget=table.relief_budget, reach=table.relief_reach, locked=[]))
            else:
                found.kind = wanted
            await ctx.session.flush()
            tally.relief += 1
            await record(
                ctx,
                "deepened.relief_opened",
                roles={IncidentRole.AUTHORITY: ruler, IncidentRole.PLACE: town.id},
                facts={"kind": wanted},
                place=town.id,
            )
        with explaining():
            if wanted is ReliefKind.SHELTER and "homeless" not in profile.locked:
                term("deepened.shelter_housed", -table.shelter_housed)
                profile.homeless = max(0, profile.homeless - table.shelter_housed)
            elif wanted is ReliefKind.PUBLIC_KITCHEN:
                nudge(profile, "unrest", -table.kitchen_calm, "deepened.kitchen_calm")
    await ctx.session.flush()


async def keep_learning(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    for row in list(await ctx.session.scalars(select(MuseumCollectionRow).order_by(MuseumCollectionRow.id))):
        keeper = await living_entity(ctx.session, row.keeper_entity_id)
        if keeper is None or held(keeper.id):
            continue
        pieces = list(await ctx.session.scalars(select(MuseumPieceRow.kind).where(MuseumPieceRow.collection_id == row.id)))
        with explaining():
            if row.kind is HoardKind.LIBRARY:
                term("deepened.library_learning", table.library_learning)
                await add_progress(ctx, keeper.id, Technique.UNIVERSITIES, table.library_learning)
            maps, tools = pieces.count(PieceKind.MAP), pieces.count(PieceKind.INSTRUMENT)
            if maps:
                term("deepened.map_charting", maps * table.map_charting)
                await add_progress(ctx, keeper.id, Technique.CARTOGRAPHY, maps * table.map_charting)
            if tools:
                term("deepened.instrument_study", tools * table.instrument_study)
                await add_progress(ctx, keeper.id, Technique.ASTRONOMY_INSTRUMENTS, tools * table.instrument_study)
        tally.learning += 1


async def tend_gardens(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(select(GardenRow).where(GardenRow.kind.in_(sorted(LIVING_GARDENS))).order_by(GardenRow.id))
    for garden in list(rows):
        found = await town_of(ctx, garden.settlement_entity_id)
        if found is None:
            continue
        town, profile = found
        crop = round_half_up(table.kitchen_crop * garden.condition / PERCENT)
        if garden.kind is GardenKind.ROOF_GARDEN:
            crop //= 2
            if profile.size_tier in DENSE:
                with explaining():
                    nudge(profile, "sanitation", table.roof_cooling, "deepened.roof_cooling")
        if crop > 0:
            await goods_of(ctx.session, ctx.epoch).add(town.id, CommodityKind.FRUIT, crop, GoodsFlow.HARVEST)
        tally.gardens += 1


async def keep_works(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.execute(
        select(StructureProfileRow, StructureDesignRow.form)
        .join(StructureDesignRow, StructureDesignRow.id == StructureProfileRow.design_id)
        .where(StructureDesignRow.form.in_(sorted(SHAPED_FORMS)))
        .order_by(StructureProfileRow.structure_entity_id)
    )
    for profile, form in rows.all():
        if held(profile.structure_entity_id) or profile.host_entity_id is None:
            continue
        host = await town_of(ctx, profile.host_entity_id)
        if host is None:
            continue
        town, town_profile = host
        ground = await ctx.session.get(RegionEnvironmentRow, town.location_id) if town.location_id is not None else None
        with explaining():
            if form is BuildingForm.STILT and ground is not None and ground.wetland >= table.floating_wet_at and "condition" not in profile.locked:
                term("deepened.stilt_spared", table.stilt_spared)
                profile.condition = clamp_int(profile.condition + table.stilt_spared, 0, PERCENT)
            elif form is BuildingForm.VAULT and "siege_supplies" not in town_profile.locked:
                term("deepened.vault_stores", table.vault_stores)
                town_profile.siege_supplies += table.vault_stores
        tally.works += 1
    built = await ctx.session.scalars(
        select(StructureProfileRow).where(StructureProfileRow.builder_kind == BuilderKind.HOUSEHOLD).order_by(StructureProfileRow.structure_entity_id)
    )
    for profile in list(built):
        host = await town_of(ctx, profile.host_entity_id) if profile.host_entity_id is not None else None
        if host is None:
            continue
        with explaining():
            nudge(host[1], "unrest", -table.household_pride, "deepened.household_pride")
        tally.works += 1
    sections = await ctx.session.execute(
        select(StructureSectionRow.section, StructureProfileRow.host_entity_id)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == StructureSectionRow.structure_entity_id)
        .where(StructureSectionRow.section.in_(sorted(HELD_SECTIONS)))
        .order_by(StructureSectionRow.structure_entity_id)
    )
    for section, host_id in sections.all():
        host = await town_of(ctx, host_id) if host_id is not None else None
        if host is None:
            continue
        town_profile = host[1]
        with explaining():
            if section is StructureSection.CISTERN and "siege_water" not in town_profile.locked:
                term("deepened.cistern_water", table.cistern_water)
                town_profile.siege_water += table.cistern_water
            elif section is StructureSection.CHIMNEY:
                nudge(town_profile, "sanitation", table.chimney_air, "deepened.chimney_air")
        tally.works += 1


async def trade_relics(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    cults = await ctx.session.scalars(
        select(CultDoctrineRow).where(CultDoctrineRow.relic_stance == RelicStance.TRADED).order_by(CultDoctrineRow.cult_entity_id)
    )
    for doctrine in list(cults):
        if held(doctrine.cult_entity_id) or "treasury" in doctrine.locked:
            continue
        renown = sum(
            row.renown
            for row in await ctx.session.scalars(
                select(ItemProfileRow).join(EntityRow, EntityRow.id == ItemProfileRow.item_entity_id).where(EntityRow.location_id == doctrine.cult_entity_id)
            )
        )
        price = round_half_up(table.relic_price * (1 + renown / PERCENT))
        with explaining():
            term("deepened.relic_price", price)
            doctrine.treasury += price
        tally.relics += 1
        await record(ctx, "deepened.relic_traded", roles={IncidentRole.SELLER: doctrine.cult_entity_id}, facts={"price": price})


async def use_aids(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(select(AssistiveAidRow).where(AssistiveAidRow.kind.in_(sorted(SENSE_AIDS))))
    for row in list(rows):
        if held(row.holder_node_id):
            continue
        skill = SkillKind.WRITING if row.kind is AssistiveAid.TACTILE_SCRIPT else SkillKind.LANGUAGES
        await practise(ctx.session, ctx.rules, row.holder_node_id, skill, table.aid_practice * row.quality / PERCENT, epoch=ctx.epoch)
        tally.aids += 1


async def keep_fire_clocks(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    for clock in list(await ctx.session.scalars(select(PublicClockRow).where(PublicClockRow.kind == ClockKind.FIRE_CLOCK))):
        found = await town_of(ctx, clock.settlement_entity_id)
        if found is not None:
            with explaining():
                nudge(found[1], "public_order", table.fire_clock_order, "deepened.fire_clock_order")
            tally.clocks += 1


async def bear_curses(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.execute(
        select(ItemProfileRow.curse, BondRow.source_node_id)
        .join(BondRow, BondRow.target_node_id == ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.curse.in_(sorted(HEAVY_CURSES)), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        .order_by(ItemProfileRow.item_entity_id, BondRow.id)
    )
    for curse, holder_id in rows.all():
        holder = await living_entity(ctx.session, holder_id)
        if holder is None or held(holder.id) or holder.entity_type is not EntityType.MORTAL:
            continue
        with explaining():
            if curse is CurseKind.WEAKNESS:
                term("deepened.weakness_drain", -table.weakness_drain)
                shift_stat(holder, "strength", -table.weakness_drain)
            else:
                for bond in await ctx.session.scalars(select(RelationshipRow).where(RelationshipRow.subject_node_id == holder.id)):
                    if not held(bond.holder_node_id):
                        term("deepened.isolation_chill", -table.isolation_chill)
                        bond.friendship = clamp_int(bond.friendship - table.isolation_chill, -PERCENT, PERCENT)
        tally.curses += 1


async def run_coops(ctx: TickContext, tally: TownTally) -> None:
    table = ctx.rules.deepened
    rows = await ctx.session.scalars(select(CooperativeRow).where(CooperativeRow.purpose.in_(sorted(SOCIAL_COOPS))))
    for coop in list(rows):
        faction = await ctx.session.get(FactionProfileRow, coop.faction_entity_id)
        if faction is None or faction.home_entity_id is None or held(coop.faction_entity_id):
            continue
        found = await town_of(ctx, faction.home_entity_id)
        if found is None:
            continue
        town, profile = found
        with explaining():
            if coop.purpose is CoopPurpose.HOUSING and "homeless" not in profile.locked:
                term("deepened.coop_housing", -table.coop_housing)
                profile.homeless = max(0, profile.homeless - table.coop_housing)
            elif coop.purpose is CoopPurpose.SCHOOL:
                people = await people_of(ctx.session, town)
                culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
                if culture is not None and "literacy" not in culture.locked and not held(culture.people_entity_id):
                    term("deepened.coop_school", table.coop_school)
                    culture.literacy = clamp_int(culture.literacy + table.coop_school, 0, PERCENT)
        tally.coops += 1


async def deepen_towns(ctx: TickContext, tally: TownTally) -> None:
    await live_quarters(ctx, tally)
    await ruin_by_sinkhole_and_plague(ctx, tally)
    await choose_relief(ctx, tally)
    await keep_learning(ctx, tally)
    await tend_gardens(ctx, tally)
    await keep_works(ctx, tally)
    await trade_relics(ctx, tally)
    await use_aids(ctx, tally)
    await keep_fire_clocks(ctx, tally)
    await bear_curses(ctx, tally)
    await run_coops(ctx, tally)
    await ctx.session.flush()
