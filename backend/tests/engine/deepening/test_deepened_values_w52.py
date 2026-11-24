from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.crafts import AssistiveAidRow, PublicClockRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.customs import CooperativeRow, EvidenceRow, MembershipRow, PoorReliefRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.integrity import StructureSectionRow
from aerona.db.tables.intrigue import IdentityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import AppealRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.museums import MuseumCollectionRow
from aerona.db.tables.polity import ClaimRow, OathRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.belonging import FugitiveKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium, SignalKind, SignalState
from aerona.domain.enums.crafts import AssistiveAid, ClockKind
from aerona.domain.enums.culture import CurseKind
from aerona.domain.enums.customs import CoopPurpose, EvidenceKind, Membership, Naturalisation, ReliefKind
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.faction import EstatePrivilege, FactionGoalKind, FactionKind
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.intrigue import IdentityReason
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.military import ArmourType, Formation, ShieldType, Stance, UnitKind
from aerona.domain.enums.museum import HoardKind
from aerona.domain.enums.polity import ClaimBasis, DecisionRule, GovernmentKind, OathKind, OfficeKind
from aerona.domain.enums.settlement import DistrictKind, SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import BuilderKind, BuildingForm, StructureKind, StructureSection
from aerona.domain.models.entity_stats import FactionStats, ItemStats, PolityStats, StructureStats
from aerona.engine.belonging.fugitives_w52 import flee
from aerona.engine.communication.dispatches import refused
from aerona.engine.communication.post import upgraded
from aerona.engine.context import TickContext
from aerona.engine.deepening import realms_w52, towns_w52
from aerona.engine.military.battle import Side, circle_up, make_stacks
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, surveyed, tuned_rules


async def at(session: AsyncSession, **deepened: int) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = 3
    await session.flush()
    return await manual_context(session, "deepened", rules=tuned_rules(deepened=deepened))


async def town(session: AsyncSession, world: CoreWorld, name: str = "Ferrow", **fields: int) -> tuple[EntityRow, SettlementProfileRow]:
    place = await settlement(session, name, world, world.regions[0])
    profile = SettlementProfileRow(settlement_entity_id=place.id, size_tier=SizeTier.CITY, locked=[], foreigners={}, **fields)
    session.add(profile)
    await session.flush()
    return place, profile


async def realm(session: AsyncSession, world: CoreWorld, seat: EntityRow, **fields: object) -> PolityProfileRow:
    polity = await entity(session, f"Crown of {seat.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    row = PolityProfileRow(
        polity_entity_id=polity.id,
        government=GovernmentKind.MONARCHY,
        decision_rule=DecisionRule.AUTOCRATIC,
        capital_entity_id=seat.id,
        core_entity_id=polity.id,
        legitimacy=50,
        stability=50,
        treasury=1000,
        emblem={},
        locked=[],
        **({"legitimacy_parts": {}} | fields),
    )
    session.add(row)
    await session.flush()
    return row


async def test_pilgrim_caravan_and_floating_quarters_act_on_their_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, floating_wet_at=0)
    place, profile = await town(session, world)
    for kind in (DistrictKind.PILGRIM_QUARTER, DistrictKind.CARAVAN_QUARTER, DistrictKind.FLOATING):
        session.add(DistrictRow(settlement_entity_id=place.id, kind=kind, built_epoch=1, condition=50, locked=[]))
    await session.flush()
    await towns_w52.live_quarters(ctx, towns_w52.TownTally())
    assert stat(place, "piety") == 50 + ctx.rules.deepened.pilgrim_piety
    assert stat(place, "prosperity") == 50 + ctx.rules.deepened.caravan_prosperity
    assert profile.foreigners["traders"] == ctx.rules.deepened.caravan_foreigners


async def test_hollowed_ground_opens_beneath_a_town_and_it_must_be_rebuilt(session: AsyncSession, world: CoreWorld) -> None:
    await surveyed(session, world)
    ctx = await at(session, sinkhole_pct=100, sinkhole_mined_at=0)
    place, _ = await town(session, world)
    await towns_w52.ruin_by_sinkhole_and_plague(ctx, towns_w52.TownTally())
    row = await session.scalar(select(ReconstructionRow).where(ReconstructionRow.settlement_entity_id == place.id))
    assert row is not None


async def test_a_realm_opens_shelters_for_its_homeless(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, shelter_homeless_at=10)
    place, profile = await town(session, world, homeless=500)
    seat = await realm(session, world, place)
    session.add(PolityMemberRow(polity_entity_id=seat.polity_entity_id, member_entity_id=place.id))
    await session.flush()
    await towns_w52.choose_relief(ctx, towns_w52.TownTally())
    relief = await session.get(PoorReliefRow, seat.polity_entity_id)
    assert relief is not None and relief.kind is ReliefKind.SHELTER
    assert profile.homeless == 500 - ctx.rules.deepened.shelter_housed


async def test_a_library_teaches_its_keeper(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, _ = await town(session, world)
    session.add(MuseumCollectionRow(keeper_entity_id=place.id, kind=HoardKind.LIBRARY, locked=[]))
    await session.flush()
    tally = towns_w52.TownTally()
    await towns_w52.keep_learning(ctx, tally)
    assert tally.learning == 1


async def test_a_kitchen_garden_feeds_its_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, _ = await town(session, world)
    session.add(GardenRow(settlement_entity_id=place.id, kind=GardenKind.KITCHEN_GARDEN, condition=100, locked=[]))
    await session.flush()
    tally = towns_w52.TownTally()
    await towns_w52.tend_gardens(ctx, tally)
    assert tally.gardens == 1


async def test_vaults_store_food_cisterns_hold_water_chimneys_clear_the_air_and_households_take_pride(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, profile = await town(session, world, unrest=20)
    work = await entity(session, "Granary", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=place.id)
    design = StructureDesignRow(name="Vaulted store", base_kind=StructureKind.GRANARY, form=BuildingForm.VAULT, locked=[])
    session.add(design)
    await session.flush()
    session.add(
        StructureProfileRow(
            structure_entity_id=work.id, kind=StructureKind.GRANARY, host_entity_id=place.id, design_id=design.id, builder_kind=BuilderKind.HOUSEHOLD, locked=[]
        )
    )
    session.add(StructureSectionRow(structure_entity_id=work.id, section=StructureSection.CISTERN, role="support", locked=[]))
    session.add(StructureSectionRow(structure_entity_id=work.id, section=StructureSection.CHIMNEY, role="support", locked=[]))
    await session.flush()
    supplies, water, sanitation = profile.siege_supplies, profile.siege_water, profile.sanitation
    await towns_w52.keep_works(ctx, towns_w52.TownTally())
    assert profile.siege_supplies == supplies + ctx.rules.deepened.vault_stores
    assert profile.siege_water == water + ctx.rules.deepened.cistern_water
    assert profile.unrest == 20 - ctx.rules.deepened.household_pride
    assert profile.sanitation == min(100, sanitation + ctx.rules.deepened.chimney_air)


async def test_a_fire_clock_keeps_order_and_aids_teach_their_holders(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, profile = await town(session, world, public_order=40)
    reader = await mortal(session, "Ilen", world, place.id)
    session.add(PublicClockRow(settlement_entity_id=place.id, kind=ClockKind.FIRE_CLOCK, locked=[]))
    session.add(AssistiveAidRow(holder_node_id=reader.id, kind=AssistiveAid.TACTILE_SCRIPT, quality=100, locked=[]))
    await session.flush()
    tally = towns_w52.TownTally()
    await towns_w52.keep_fire_clocks(ctx, tally)
    await towns_w52.use_aids(ctx, tally)
    assert profile.public_order == 40 + ctx.rules.deepened.fire_clock_order and tally.aids == 1


async def test_a_curse_of_weakness_saps_its_bearer(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, _ = await town(session, world)
    bearer = await mortal(session, "Tamsa", world, place.id, strength=50)
    item = await entity(session, "Ring", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=place.id)
    await bond(session, bearer.id, item.id, BondKind.OWNS)
    session.add(ItemProfileRow(item_entity_id=item.id, item_class="ring", curse=CurseKind.WEAKNESS, locked=[]))
    await session.flush()
    await towns_w52.bear_curses(ctx, towns_w52.TownTally())
    assert stat(bearer, "strength") == 50 - ctx.rules.deepened.weakness_drain


async def test_a_housing_cooperative_houses_the_homeless(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, profile = await town(session, world, homeless=100)
    faction = await entity(session, "Builders", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(FactionProfileRow(faction_entity_id=faction.id, kind=FactionKind.CRAFT_GUILD, home_entity_id=place.id, locked=[]))
    session.add(CooperativeRow(faction_entity_id=faction.id, purpose=CoopPurpose.HOUSING, locked=[]))
    await session.flush()
    await towns_w52.run_coops(ctx, towns_w52.TownTally())
    assert profile.homeless == 100 - ctx.rules.deepened.coop_housing


async def test_rights_of_assembly_calm_the_capital_and_wards_are_naturalised(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, profile = await town(session, world, unrest=30)
    seat = await realm(session, world, place)
    head = await mortal(session, "Orla", world, place.id)
    ward = await mortal(session, "Bek", world, place.id)
    session.add(MembershipRow(mortal_entity_id=head.id, polity_entity_id=seat.polity_entity_id, category=Membership.CITIZEN, locked=[]))
    house = HouseholdRow(name="Orla's", head_node_id=head.id, settlement_node_id=place.id, social_class=SocialClass.ARTISAN, locked=[])
    session.add(house)
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=ward.id, household_id=house.id, role=HouseholdRole.WARD))
    await session.flush()
    await realms_w52.keep_rights(ctx, realms_w52.RealmTally())
    await realms_w52.naturalise_wards(ctx, realms_w52.RealmTally())
    assert profile.unrest == 30 - ctx.rules.deepened.assembly_calm
    member = await session.get(MembershipRow, ward.id)
    assert member is not None and member.path is Naturalisation.ADOPTION


async def test_a_fugitive_is_left_stateless_and_its_kin_take_other_names(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, _ = await town(session, world)
    seat = await realm(session, world, place)
    runner = await mortal(session, "Vey", world, place.id)
    parent = await mortal(session, "Ama", world, place.id)
    await bond(session, parent.id, runner.id, BondKind.PARENT_OF)
    session.add(MembershipRow(mortal_entity_id=runner.id, polity_entity_id=seat.polity_entity_id, category=Membership.SUBJECT, locked=[]))
    await session.flush()
    await flee(ctx, runner, FugitiveKind.HERETIC, seat.polity_entity_id)
    await realms_w52.name_stateless(ctx, realms_w52.RealmTally())
    await realms_w52.protect_kin(ctx, realms_w52.RealmTally())
    member = await session.get(MembershipRow, runner.id)
    assert member is not None and member.category is Membership.STATELESS
    hidden = await session.get(IdentityRow, parent.id)
    assert hidden is not None and hidden.reason is IdentityReason.PROTECTION


async def test_conquest_fades_and_prophecy_follows_belief(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, _ = await town(session, world)
    seat = await realm(session, world, place, legitimacy_parts={"conquest": 40})
    seat.legitimacy = 20
    claimant = await mortal(session, "Hask", world, place.id)
    claim = ClaimRow(
        claimant_entity_id=claimant.id, polity_entity_id=seat.polity_entity_id, basis=ClaimBasis.PROPHECY, strength=0, office=OfficeKind.RULER, locked=[]
    )
    session.add(claim)
    await session.flush()
    await realms_w52.fade_conquests(ctx, realms_w52.RealmTally())
    await realms_w52.weigh_prophecies(ctx, realms_w52.RealmTally())
    assert seat.legitimacy_parts["conquest"] < 40 and seat.legitimacy < 20
    assert claim.strength > 0


async def test_an_appeal_overturns_a_wrongful_verdict_and_a_healer_reads_the_body(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, appeal_reverse_pct=100)
    place, _ = await town(session, world)
    seat = await realm(session, world, place)
    accused = await mortal(session, "Dorn", world, place.id)
    culprit = await mortal(session, "Lise", world, place.id)
    healer = await mortal(session, "Mott", world, place.id)
    healer.mortal_role = MortalRole.HEALER
    wrong = CrimeCaseRow(
        crime="theft",
        settlement_entity_id=place.id,
        polity_entity_id=seat.polity_entity_id,
        accused_entity_id=accused.id,
        verdict=Verdict.GUILTY,
        wrongful=True,
        stage=CaseStage.CLOSED,
        locked=[],
    )
    open_case = CrimeCaseRow(
        crime="theft",
        settlement_entity_id=place.id,
        polity_entity_id=seat.polity_entity_id,
        culprit_entity_id=culprit.id,
        stage=CaseStage.INVESTIGATION,
        locked=[],
    )
    session.add_all([wrong, open_case])
    await session.flush()
    await realms_w52.hear_appeals(ctx, realms_w52.RealmTally())
    await realms_w52.gather_evidence(ctx, realms_w52.RealmTally())
    assert await session.get(AppealRow, wrong.id) is not None and wrong.verdict is Verdict.ACQUITTED
    found = await session.scalar(select(EvidenceRow).where(EvidenceRow.case_id == open_case.id, EvidenceRow.kind == EvidenceKind.BODY))
    assert found is not None


async def test_a_new_officer_swears_an_oath_of_office(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    place, _ = await town(session, world)
    seat = await realm(session, world, place)
    holder = await mortal(session, "Pell", world, place.id)
    session.add(OfficeRow(polity_entity_id=seat.polity_entity_id, kind=OfficeKind.TREASURER, holder_entity_id=holder.id, since_epoch=ctx.epoch, locked=[]))
    await session.flush()
    await realms_w52.swear_officers(ctx, realms_w52.RealmTally())
    assert await session.scalar(select(OathRow).where(OathRow.swearer_entity_id == holder.id, OathRow.kind == OathKind.OFFICE)) is not None


async def test_a_faction_saves_toward_a_new_settlement_and_estates_keep_their_dress(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, settle_cost=10)
    place, profile = await town(session, world, unrest=10)
    seat = await realm(session, world, place)
    faction = await entity(session, "Wanderers", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add(FactionProfileRow(faction_entity_id=faction.id, kind=FactionKind.MOVEMENT, home_entity_id=place.id, treasury=100, locked=[]))
    goal = FactionGoalRow(faction_entity_id=faction.id, kind=FactionGoalKind.FOUND_SETTLEMENT, progress=0, locked=[])
    estate = await entity(session, "Nobles", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    session.add_all(
        [goal, EstateProfileRow(faction_entity_id=estate.id, polity_entity_id=seat.polity_entity_id, social_class=SocialClass.NOBLE, loyalty=40, locked=[])]
    )
    session.add(EstatePrivilegeRow(estate_entity_id=estate.id, privilege=EstatePrivilege.DRESS, locked=False))
    await session.flush()
    await realms_w52.pursue_goals(ctx, realms_w52.RealmTally())
    await realms_w52.keep_privileges(ctx, realms_w52.RealmTally())
    assert goal.achieved_epoch == ctx.epoch
    assert profile.unrest == 10 + ctx.rules.deepened.dress_resentment


async def test_burned_signals_are_restored_and_drums_join_forest_beacons(session: AsyncSession, world: CoreWorld) -> None:
    await surveyed(session, world)
    ctx = await at(session, drum_forest_at=0)
    place, _ = await town(session, world)
    seat = await realm(session, world, place)
    region = world.regions[0].id
    burned = SignalLinkRow(
        owner_node_id=seat.polity_entity_id, kind=SignalKind.BEACON_CHAIN, from_region_id=region, to_region_id=region, state=SignalState.BURNED, locked=[]
    )
    beacon = SignalLinkRow(
        owner_node_id=seat.polity_entity_id, kind=SignalKind.BEACON_CHAIN, from_region_id=region, to_region_id=region, state=SignalState.ACTIVE, locked=[]
    )
    session.add_all([burned, beacon])
    await session.flush()
    await realms_w52.restore_signals(ctx, realms_w52.RealmTally())
    await realms_w52.build_drum_relays(ctx, realms_w52.RealmTally())
    assert burned.state is SignalState.RESTORED
    assert await upgraded(ctx, seat.polity_entity_id, place.id, Medium.LETTER) is Medium.DRUM_AND_WHISTLE


async def test_a_hostile_court_refuses_a_proposal(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    first, _ = await town(session, world, "Avel")
    second, _ = await town(session, world, "Brun")
    session.add(RelationshipRow(holder_node_id=second.id, subject_node_id=first.id, friendship=-90, since_epoch=1, last_epoch=1))
    row = MessageRow(
        epoch=3,
        sender_node_id=first.id,
        recipient_node_id=second.id,
        intent=MessageIntent.DISPATCH,
        text="",
        content=DispatchContent.PROPOSAL,
        state=DispatchState.DELIVERED,
        locked=[],
    )
    session.add(row)
    await session.flush()
    assert await refused(ctx, row) and row.state is DispatchState.REFUSED


def test_a_side_with_wagons_forms_a_circle_against_riders() -> None:
    def unit(kind: UnitKind, ident: int, army: int) -> ArmyUnitRow:
        return ArmyUnitRow(
            id=ident,
            army_entity_id=army,
            kind=kind,
            count=100,
            quality=50,
            armour=ArmourType.NONE,
            shield=ShieldType.NONE,
            helmet=False,
            weapons=[],
            experience=10,
            morale=60,
            fatigue=0,
            wounded=0,
            condition=100,
            locked=[],
        )

    def side(ident: int, rows: list[ArmyUnitRow]) -> Side:
        body = EntityRow(id=ident, name=f"Host {ident}", entity_type=EntityType.PEOPLE)
        profile = ArmyProfileRow(army_entity_id=ident, stance=Stance.MARCH, doctrine=MartialStyle.SHIELDWALL, entrenchment=0, baggage=100, loot=50, locked=[])
        return Side(entity=body, army=body, profile=profile, stacks=make_stacks(rows), edge=1.0, defending=True, skill=0, traits=set())

    wagons = side(1, [unit(UnitKind.CHARIOTS, 1, 1), unit(UnitKind.LEVY, 2, 1)])
    riders = side(2, [unit(UnitKind.LIGHT_CAVALRY, 3, 2)])
    assert circle_up(Rules(), wagons, riders) > 0
    assert any(stack.row.formation is Formation.CIRCLE for stack in wagons.stacks)
