from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyOfficerRow, ArmyProfileRow, ArmyTemplateRow, ArmyUnitRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind, TerrainKind
from aerona.domain.enums.military import ArmyRole, CommandArea, CommanderTrait, OutcomeClass, Stance, UnitKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import ItemStats, PolityStats
from aerona.engine.economy.route_dangers import patrol_share
from aerona.engine.economy.stocks import goods_of
from aerona.engine.environment.profile import SCAR_FERTILITY
from aerona.engine.military import orders, records
from aerona.engine.military.battle import BattleResult, Field, dug_in, family_factor
from aerona.engine.military.campaign import bridged, on_road, spar, step_cost
from aerona.engine.military.command import areas_from, best_area, thrift
from aerona.engine.military.engineering import engineer, engineers, leave_earthworks, supply_limit
from aerona.engine.military.logistics import dig_rate, regroup, restock
from aerona.engine.military.marshal import keep_templates
from aerona.engine.military.standards import capture_standard
from aerona.engine.military.templates import blend, upgrades, weights_of
from aerona.engine.phases.environment import SCAR_DECAY
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx
from tests.engine.warfare.test_battle_depth_rp2 import side, unit
from tests.tools.factories import connect, make_entity

RULES = Rules()


def land(**values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "entity_id": 1,
        "farmed": 10,
        "harvest_pct": 100,
        "scars": {},
        "built": 0,
        "river_class": RiverClass.NONE,
        "passability": {"on_foot": 100},
        "locked": [],
    }
    return RegionEnvironmentRow(**(base | values))


def test_the_land_feeds_more_on_a_road_and_less_after_a_poor_harvest_or_plunder() -> None:
    plain = supply_limit(RULES, land(), None)
    assert supply_limit(RULES, land(scars={ScarKind.MILITARY_ROAD.value: RULES.army_depth.road_at}), None) > plain
    assert supply_limit(RULES, land(harvest_pct=40), None) < plain
    assert supply_limit(RULES, land(scars={ScarKind.PLUNDERED.value: 50}), None) < plain
    assert supply_limit(RULES, land(farmed=0), None) == RULES.army_depth.supply_floor


def test_sappers_lay_roads_blow_bridges_and_spare_the_ford() -> None:
    sappers = [unit(UnitKind.SAPPERS, RULES.army_depth.sappers_needed, ident=1)]
    few = [unit(UnitKind.SAPPERS, max(0, RULES.army_depth.sappers_needed - 1), ident=2)]
    assert engineers(RULES, sappers) and not engineers(RULES, few)
    marching = ArmyProfileRow(army_entity_id=1, stance=Stance.MARCH, entrenchment=0, locked=[])
    road = land()
    for _ in range(4):
        assert engineer(RULES, marching, sappers, road) == "road laid"
    assert on_road(road, RULES)
    river = land(river_class=RiverClass.RIVER, built=RULES.campaign_depth.bridge_built)
    retreating = ArmyProfileRow(army_entity_id=1, stance=Stance.RETREAT, entrenchment=0, locked=[])
    assert bridged(RULES, river)
    assert engineer(RULES, retreating, sappers, river) == "bridge blown"
    assert not bridged(RULES, river)
    assert step_cost(RULES, river, None, pontoon=True) < step_cost(RULES, river, None)
    assert engineer(RULES, retreating, few, land(river_class=RiverClass.RIVER, built=RULES.campaign_depth.bridge_built)) is None


def test_earthworks_stay_on_the_land_and_shelter_the_defender_against_charges() -> None:
    profile = ArmyProfileRow(army_entity_id=1, stance=Stance.MARCH, entrenchment=RULES.army_depth.earthworks_at, locked=[])
    ground = land()
    assert leave_earthworks(RULES, profile, ground) == RULES.army_depth.earthworks_at
    shallow = ArmyProfileRow(army_entity_id=1, stance=Stance.MARCH, entrenchment=RULES.army_depth.earthworks_at - 1, locked=[])
    assert leave_earthworks(RULES, shallow, land()) == 0
    defender = side("Holders", [unit(UnitKind.LINE_INFANTRY, 100, ident=1)], defending=True)
    field = Field(TerrainKind.PLAIN, None, night=False, earthworks=ground.scars[ScarKind.EARTHWORKS.value])
    assert dug_in(defender, field) == RULES.army_depth.earthworks_at


def test_every_scar_heals_and_weighs_on_the_harvest() -> None:
    assert set(SCAR_DECAY) == set(ScarKind) and set(SCAR_FERTILITY) == set(ScarKind)


def test_commanders_lead_best_where_their_skills_and_traits_lie() -> None:
    areas = areas_from({SkillKind.SIEGECRAFT: 80, SkillKind.ENGINEERING: 60}, [CommanderTrait.SIEGE_EXPERT])
    assert best_area(areas) is CommandArea.SIEGE
    assert areas_from({}, []) == dict.fromkeys(CommandArea, 0) and best_area(areas_from({}, [])) is None
    quartermaster = areas_from({SkillKind.LOGISTICS: 100, SkillKind.STRATEGY: 100}, [])
    assert thrift(RULES, quartermaster) < 1.0
    archers = side("Bows", [unit(UnitKind.ARCHERS, 100, ident=1)]).stacks[0]
    assert family_factor(RULES, {CommandArea.FIRE: 100}, archers.spec.family) > family_factor(RULES, {}, archers.spec.family)


def test_a_template_fills_its_share_of_a_muster_and_outdated_kinds_are_refitted() -> None:
    plan = {UnitKind.LEVY: 1.0}
    mixed = blend(RULES, plan, {UnitKind.LINE_INFANTRY: 1})
    assert mixed[UnitKind.LINE_INFANTRY] == pytest.approx(RULES.army_depth.template_share / 100)
    template = ArmyTemplateRow(composition={UnitKind.LEVY.value: 60, "not_a_kind": 5}, doctrine=MartialStyle.SHIELDWALL, locked=[])
    assert weights_of(template) == {UnitKind.LEVY: 60}
    swaps = upgrades({UnitKind.LEVY: 60}, MartialStyle.SHIELDWALL, {UnitKind.LEVY, UnitKind.SHIELD_INFANTRY, UnitKind.LINE_INFANTRY})
    assert UnitKind.LEVY in swaps and swaps[UnitKind.LEVY] in {UnitKind.SHIELD_INFANTRY, UnitKind.LINE_INFANTRY}
    assert upgrades({UnitKind.LEVY: 60}, MartialStyle.SHIELDWALL, {UnitKind.LEVY}) == {}


def test_patrols_take_bandit_danger_off_the_routes_through_their_region() -> None:
    assert patrol_share(RULES, [1, 2], frozenset({1, 2})) == pytest.approx(RULES.army_depth.patrol_pct / 100)
    assert patrol_share(RULES, [1, 2], frozenset({1})) == pytest.approx(RULES.army_depth.patrol_pct / 200)
    assert patrol_share(RULES, [1, 2], frozenset()) == 0


def test_template_compositions_must_name_real_soldiers() -> None:
    assert records.mix_of({UnitKind.ARCHERS.value: 3, UnitKind.LEVY.value: 0}) == {UnitKind.ARCHERS.value: 3}
    for bad in ({"dragons": 2}, {UnitKind.ARCHERS.value: -1}, {UnitKind.ARCHERS.value: "many"}, ["archers"]):
        with pytest.raises(ValidationFailedError):
            records.mix_of(bad)


async def test_a_routed_side_loses_its_standard_to_the_victor(session: AsyncSession, world_id: int) -> None:
    rules = replace(RULES, army_depth=replace(RULES.army_depth, standard_capture_pct=100))
    ctx = make_ctx(session, rules)
    victors = await make(session, "Hill Folk", EntityType.PEOPLE, world_id, population=5000)
    losers = await make(session, "River Folk", EntityType.PEOPLE, world_id, population=5000)
    banner = await make_entity(session, "Heron Banner", EntityType.ITEM, world_id=world_id, stats=ItemStats())
    session.add(ItemProfileRow(item_entity_id=banner.id, item_class=ItemClass.STANDARD, symbol=True, condition=100, renown=10, locked=[]))
    await connect(session, losers.id, banner.id, BondKind.OWNS)
    await session.flush()
    war = await open_war(ctx, victors, losers)
    winner = side("Hill Folk", [unit(UnitKind.LINE_INFANTRY, 100, ident=1)], ident=victors.id)
    loser = side("River Folk", [replace_army(unit(UnitKind.LEVY, 100, ident=2, morale=50), losers.id)], ident=losers.id)
    winner.entity, loser.entity = victors, losers
    result = BattleResult(winner, loser, winner, loser, False, OutcomeClass.ROUT, 50.0, [], {}, {}, {})
    before = war.score
    assert await capture_standard(ctx, war, result, attacker_id=victors.id) == banner.id
    owners = set(
        await session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == banner.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        )
    )
    profile = await session.get(ItemProfileRow, banner.id)
    assert owners == {victors.id} and profile is not None and profile.renown == 10 + rules.army_depth.standard_renown
    assert war.score == before + rules.army_depth.standard_score and loser.stacks[0].row.morale == 50 - rules.army_depth.standard_shock
    assert result.standard_taken == banner.id
    stalemate = BattleResult(winner, loser, winner, loser, False, OutcomeClass.VICTORY, 5.0, [], {}, {}, {})
    assert await capture_standard(ctx, war, stalemate, attacker_id=victors.id) is None


def replace_army(row: ArmyUnitRow, army_id: int) -> ArmyUnitRow:
    row.army_entity_id = army_id
    return row


async def test_a_marshal_draws_a_template_and_raised_armies_fill_from_it(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    marshal = await make(session, "Tarn", EntityType.MORTAL, world_id)
    realm = await make_entity(session, "Iron Crown", EntityType.POLITY, world_id=world_id, stats=PolityStats())
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=folk.id, locked=[]))
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.MARSHAL, holder_entity_id=marshal.id))
    await session.flush()
    counts = await keep_templates(ctx)
    template = await session.scalar(select(ArmyTemplateRow).where(ArmyTemplateRow.polity_entity_id == realm.id))
    assert counts["drawn"] == 1 and template is not None and weights_of(template)
    template.composition = {UnitKind.ARCHERS.value: 100}
    army = await orders.raise_standing_army(ctx, folk.id, 1000)
    archers = sum(
        row.count for row in await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army.id, ArmyUnitRow.kind == UnitKind.ARCHERS))
    )
    assert archers >= 1000 * ctx.rules.army_depth.template_share // 100 - 50
    assert (await keep_templates(ctx))["drawn"] == 0


async def test_drilling_officers_now_and_then_take_a_sparring_injury(session: AsyncSession, world_id: int) -> None:
    rules = replace(RULES, army_depth=replace(RULES.army_depth, sparring_injury_pct=100))
    ctx = make_ctx(session, rules)
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    army = await orders.raise_standing_army(ctx, folk.id, 200)
    officer = await make(session, "Brannoc", EntityType.MORTAL, world_id)
    session.add(ArmyOfficerRow(army_entity_id=army.id, mortal_entity_id=officer.id, role=ArmyRole.SUB_COMMANDER, since_epoch=ctx.epoch))
    await session.flush()
    assert await spar(ctx, army.id) == 1


def test_the_field_summary_names_a_taken_standard() -> None:
    battle = BattleRow(width=0, reserves_committed=0, feint=False, salvaged=0, standard_entity_id=5)
    assert "standard Heron Banner taken" in records.battle_field(battle, {5: "Heron Banner"})


def test_sappers_and_a_siege_minded_commander_dig_faster() -> None:
    crews = [unit(UnitKind.SAPPERS, RULES.army_depth.sappers_needed, ident=1)]
    assert dig_rate(RULES, [], {}) == 1.0
    assert dig_rate(RULES, crews, {}) > 1.0
    assert dig_rate(RULES, crews, {CommandArea.SIEGE: 100}) > dig_rate(RULES, crews, {})


async def test_volleys_are_restocked_from_weapon_stores_not_from_nothing(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    folk = await make(session, "Bow Folk", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    army = await orders.raise_standing_army(ctx, folk.id, 300)
    archers = await records.create_record(ctx, "stack", {"army_entity_id": army.id, "kind": UnitKind.ARCHERS.value, "count": 100, "ammunition": 0})
    profile = ArmyProfileRow(army_entity_id=army.id, stance=Stance.MARCH, baggage=50, supply_days=30, locked=[])
    regroup(ctx.rules, [archers], profile)
    assert archers.ammunition == 0
    assert await restock(ctx, folk, profile, [archers]) == 0 and archers.ammunition == 0
    await goods_of(session, ctx.epoch).add(folk.id, CommodityKind.WEAPONS, 10, GoodsFlow.PRODUCTION)
    assert await restock(ctx, folk, profile, [archers]) > 0
    assert archers.ammunition == ctx.rules.battle_depth.resupply_volleys
