import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.belonging_lines import mortal_belonging_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.belonging import HeldIdentityRow, PeerGroupRow, PeerMemberRow, SanctuaryLawRow, SanctuaryRow, SatireRow
from aerona.db.tables.collective import AccountRow, AccountStanceRow, CrowdMoodRow, SocialNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.folkways import BiasWeightRow, PurityRankRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionPlaceRow, CollectionRow
from aerona.db.tables.law_depth import DefectionRow, OutlawRow
from aerona.db.tables.mind import FacetRow, SkillRow
from aerona.db.tables.mortal import MarriageRow, MortalProfileRow
from aerona.db.tables.polity import LawJurisdictionRow, LawProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.belonging import FugitiveKind, IdentityLayer, PlayKind, SalienceDriver, SanctuaryKind, SanctuaryState, SatireSource
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import AccountStance, CollectiveActKind, NormBehaviour, NormSituation
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.folkways import DecisionBias
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.mind import EthicalStance, Facet
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, Jurisdiction, LawArea, LawKind, OfficeKind
from aerona.domain.enums.relations import RelationType
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import LoyaltyPart
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.war import WarCause, WarSide
from aerona.domain.models.entity_stats import EventStats, FactionStats, HouseStats, LawStats, PeopleStats, PolityStats, StructureStats
from aerona.engine.belonging.effects import apart_from_ruler, identity_levy, shared_identity
from aerona.engine.belonging.identities import IdentityTally, keep_identities
from aerona.engine.belonging.mockery import sting, vent
from aerona.engine.belonging.peers import PeerTally, companions_of, keep_peers
from aerona.engine.belonging.sanctuary import SanctuaryTally, keep_sanctuaries
from aerona.engine.belonging.satire import SatireTally, keep_satire
from aerona.engine.collective.accounts import HistoryTally, chronicle_collection
from aerona.engine.collective.crowds import crowd_for
from aerona.engine.context import TickContext
from aerona.engine.law.prisons import imprison
from aerona.engine.polity.book import Realm
from aerona.engine.polity.loyalty import loyalty_parts
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import bond_exists
from aerona.engine.relations.book import refresh_kinds
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "belonging", rules=tuned_rules(**rules))


async def realm(session: AsyncSession, world: CoreWorld, towns: list[EntityRow], ruler: EntityRow | None) -> EntityRow:
    polity = await entity(session, f"Crown of {towns[0].name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=towns[0].id,
            core_entity_id=polity.id,
            legitimacy=50,
            stability=50,
            treasury=4000,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    for member in towns:
        session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=member.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity


async def youngster(session: AsyncSession, world: CoreWorld, name: str, town: EntityRow) -> EntityRow:
    child = await mortal(session, name, world, town.id, age=9)
    child.social_class = SocialClass.FARMER
    session.add(MortalProfileRow(entity_id=child.id, life_stage=LifeStage.CHILD, locked=[]))
    await session.flush()
    return child


async def test_a_holy_war_raises_faith_salience_and_shared_salient_identity_warms_opinion(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await settlement(session, "Velmor", world, world.regions[0])
    ruler = await mortal(session, "Arden", world, town.id)
    polity = await realm(session, world, [town], ruler)
    event = await entity(session, "The Long Schism", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOLY_WAR, started_epoch=1)
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=polity.id, side=WarSide.ATTACKER, joined_epoch=1))
    first, second = await mortal(session, "Iri", world, town.id), await mortal(session, "Oss", world, town.id)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    await session.flush()
    tally = IdentityTally()
    await keep_identities(await at(session, 3), tally)
    faith = await session.get(HeldIdentityRow, (town.id, IdentityLayer.FAITH))
    assert faith is not None and faith.driver is SalienceDriver.HOLY_WAR
    assert faith.salience == rules.identities.base_salience + round(rules.identities.holy_war * rules.identities.decay_pct / 100)
    mine = await session.get(HeldIdentityRow, (first.id, IdentityLayer.LOCALITY))
    assert mine is not None and mine.value_node_id == town.id and tally.mortals >= 2
    assert await shared_identity(session, rules, first.id, second.id) > 0


async def test_marriages_across_peoples_quiet_people_salience(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    other = await entity(session, "Hillfolk", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    first, second = await mortal(session, "Iri", world, town.id), await mortal(session, "Oss", world, town.id)
    await bond(session, first.id, world.people.id, BondKind.DESCENDS_FROM)
    await bond(session, second.id, other.id, BondKind.DESCENDS_FROM)
    session.add(MarriageRow(first_id=first.id, second_id=second.id, start_epoch=1))
    await session.flush()
    tally = IdentityTally()
    await keep_identities(await at(session, 3), tally)
    people = await session.get(HeldIdentityRow, (town.id, IdentityLayer.PEOPLE))
    assert people is not None and people.driver is SalienceDriver.CROSSING and people.salience < tuned_rules().identities.base_salience
    assert tally.crossed >= 1


async def test_a_fault_line_on_people_breeds_separatism_and_a_salient_realm_holds_and_levies(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town, far = await settlement(session, "Velmor", world, world.regions[0]), await settlement(session, "Ostra", world, world.regions[1])
    other = await entity(session, "Hillfolk", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    ruler = await mortal(session, "Arden", world, town.id)
    polity = await realm(session, world, [town, far], ruler)
    session.add_all(
        [
            HeldIdentityRow(holder_entity_id=town.id, layer=IdentityLayer.PEOPLE, value_node_id=world.people.id, salience=80, locked=[]),
            HeldIdentityRow(holder_entity_id=far.id, layer=IdentityLayer.PEOPLE, value_node_id=other.id, salience=80, locked=[]),
            HeldIdentityRow(holder_entity_id=far.id, layer=IdentityLayer.POLITY, value_node_id=polity.id, salience=90, locked=[]),
            HeldIdentityRow(holder_entity_id=ruler.id, layer=IdentityLayer.PEOPLE, value_node_id=world.people.id, salience=60, locked=[]),
        ]
    )
    await session.flush()
    profile = await session.get(PolityProfileRow, polity.id)
    assert profile is not None
    office = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity.id))
    assert office is not None
    members = {row.member_entity_id: row for row in await session.scalars(select(PolityMemberRow).where(PolityMemberRow.polity_entity_id == polity.id))}
    parts = await loyalty_parts(await at(session, 3), Realm(polity, profile, members=members, offices=[office]), far, 0)
    assert parts[LoyaltyPart.SEPARATISM] == round(rules.identities.separatism * 80 / 100)
    assert parts[LoyaltyPart.IDENTITY] == round(rules.identities.cohesion * 90 / 100)
    assert await identity_levy(session, rules, far.id) > 1
    assert await apart_from_ruler(session, rules, far.id) == 80 and await apart_from_ruler(session, rules, town.id) == 0
    mood = CrowdMoodRow(settlement_entity_id=far.id, anger=0, anxiety=0, fervour=0, deterrence=0, agitation=0, locked=[])
    ctx = await at(session, 3, identities={"revolt_cut": 20})
    calm = crowd_for(ctx, mood, CollectiveActKind.RIOT, 0.2)
    divided = crowd_for(ctx, mood, CollectiveActKind.RIOT, 0.2, divided=80)
    assert divided.cut == calm.cut + 16


async def test_children_of_a_town_play_learn_befriend_and_grow_into_companions(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(peer_groups={"friend_chance": 100, "rival_chance": 0})
    town = await settlement(session, "Velmor", world, world.regions[0])
    first, second = await youngster(session, world, "Iri", town), await youngster(session, world, "Oss", town)
    tally = PeerTally()
    await keep_peers(await at(session, 3, peer_groups={"friend_chance": 100, "rival_chance": 0}), tally)
    group = await session.scalar(select(PeerGroupRow).where(PeerGroupRow.settlement_entity_id == town.id))
    assert group is not None and tally.members == 2 and tally.friendships == 1
    facet = await session.get(
        FacetRow, (first.id, Facet.ASSERTIVENESS if group.play in {PlayKind.MOCK_FIGHTS, PlayKind.RIDING, PlayKind.ARCHERY} else Facet.COOPERATION)
    )
    assert facet is not None and facet.value != 0
    learned = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == first.id))
    assert learned is not None and rules.peer_groups.play_skill > 0
    member = await session.get(PeerMemberRow, (group.id, second.id))
    assert member is not None
    member.deprived_epochs = 2
    profile = await session.get(MortalProfileRow, second.id)
    assert profile is not None
    profile.life_stage = LifeStage.ADULT
    first_profile = await session.get(MortalProfileRow, first.id)
    assert first_profile is not None
    first_profile.life_stage = LifeStage.ADULT
    await keep_peers(await at(session, 4), tally)
    assert await session.get(PeerMemberRow, (group.id, second.id)) is None and tally.grown == 2
    assert profile.stress == 2 * rules.peer_groups.deprived_stress
    assert await bond_exists(session, second.id, first.id, BondKind.COMPANION) or await bond_exists(session, first.id, second.id, BondKind.COMPANION)
    assert second.id in await companions_of(await at(session, 4), first.id)


async def test_an_outlaw_shelters_in_a_temple_until_the_pursuer_breaks_in(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await settlement(session, "Velmor", world, world.regions[0])
    ruler = await mortal(session, "Arden", world, town.id)
    polity = await realm(session, world, [town], ruler)
    temple = await entity(session, "Hall of Rest", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=temple.id, kind=StructureKind.TEMPLE))
    outlaw = await mortal(session, "Vesk", world, town.id)
    session.add(OutlawRow(mortal_entity_id=outlaw.id, polity_entity_id=polity.id, declared_epoch=1, locked=[]))
    await session.flush()
    tally = SanctuaryTally()
    await keep_sanctuaries(await at(session, 3, sanctuary={"seek_chance": 100, "violate_chance": 0, "negotiate_chance": 0, "besiege_chance": 0}), tally)
    row = await session.scalar(select(SanctuaryRow).where(SanctuaryRow.fugitive_entity_id == outlaw.id))
    assert row is not None and row.kind is SanctuaryKind.TEMPLE and row.fugitive_kind is FugitiveKind.OUTLAW and row.pursuer_entity_id == polity.id
    assert await imprison(await at(session, 3), outlaw) is None
    await keep_sanctuaries(await at(session, 4, sanctuary={"violate_chance": 100}), tally)
    profile = await session.get(MortalProfileRow, ruler.id)
    assert row.state is SanctuaryState.VIOLATED and tally.violated == 1
    assert profile is not None and profile.infamy >= rules.sanctuary.infamy


async def test_a_besieged_fugitive_gives_up_and_the_realm_takes_its_share_of_fees(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    ruler = await mortal(session, "Arden", world, town.id)
    polity = await realm(session, world, [town], ruler)
    session.add(SanctuaryLawRow(polity_entity_id=polity.id, restricted=False, fee_pct=50, locked=[]))
    fugitive = await mortal(session, "Vesk", world, town.id)
    session.add(MortalProfileRow(entity_id=fugitive.id, wealth=60, locked=[]))
    row = SanctuaryRow(
        fugitive_entity_id=fugitive.id,
        host_entity_id=town.id,
        kind=SanctuaryKind.HOSPITALITY,
        fugitive_kind=FugitiveKind.ACCUSED,
        pursuer_entity_id=polity.id,
        state=SanctuaryState.BESIEGED,
        fee=10,
        siege_epochs=2,
        locked=[],
    )
    session.add(row)
    await session.flush()
    tally = SanctuaryTally()
    await keep_sanctuaries(await at(session, 3, sanctuary={"seek_chance": 0, "surrender_years": 150}), tally)
    assert row.state is SanctuaryState.ENDED and tally.surrendered == 1 and tally.paid == 1


async def test_a_defector_finds_asylum_and_sours_the_realm_it_fled(session: AsyncSession, world: CoreWorld) -> None:
    town, far = await settlement(session, "Velmor", world, world.regions[0]), await settlement(session, "Ostra", world, world.regions[2])
    home = await realm(session, world, [town], None)
    refuge = await realm(session, world, [far], None)
    defector = await mortal(session, "Vesk", world, town.id)
    session.add(DefectionRow(defector_entity_id=defector.id, from_entity_id=home.id, to_entity_id=refuge.id, epoch=2, locked=[]))
    await session.flush()
    tally = SanctuaryTally()
    await keep_sanctuaries(await at(session, 3, sanctuary={"seek_chance": 0}), tally)
    row = await session.scalar(select(SanctuaryRow).where(SanctuaryRow.fugitive_entity_id == defector.id))
    assert row is not None and row.kind is SanctuaryKind.ASYLUM and row.host_entity_id == refuge.id and tally.asylums == 1


async def test_a_jester_mocks_the_ruler_at_will_and_untolerated_satire_is_punished(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await settlement(session, "Velmor", world, world.regions[0])
    ruler, fool, wit = (
        await mortal(session, "Arden", world, town.id),
        await mortal(session, "Pell", world, town.id),
        await mortal(session, "Wren", world, town.id),
    )
    polity = await realm(session, world, [town], ruler)
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.JESTER, holder_entity_id=fool.id, since_epoch=0, powers=[], locked=[]))
    session.add(BiasWeightRow(holder_node_id=ruler.id, bias=DecisionBias.GROUPTHINK, weight=60, locked=[]))
    await session.flush()
    tally = SatireTally()
    await keep_satire(await at(session, 3, satire={"jest_chance": 100}), tally)
    jest = await session.scalar(select(SatireRow).where(SatireRow.source == SatireSource.JESTER))
    bias = await session.get(BiasWeightRow, (ruler.id, DecisionBias.GROUPTHINK))
    assert jest is not None and jest.tolerated and jest.judged and tally.jests == 1
    assert bias is not None and bias.weight == 60 - rules.satire.groupthink_relief
    assert await sting(session, rules, ruler.id, 3) == round(jest.bite * rules.satire.opinion_pct / 100)
    assert await vent(session, rules, polity.id, 3) > 0
    session.add(
        SocialNormRow(holder_entity_id=polity.id, situation=NormSituation.COURT, behaviour=NormBehaviour.JEST, stance=EthicalStance.SHAMEFUL, locked=[])
    )
    session.add(
        SatireRow(satirist_entity_id=wit.id, target_entity_id=ruler.id, polity_entity_id=polity.id, source=SatireSource.MORTAL, bite=30, epoch=3, locked=[])
    )
    await session.flush()
    await keep_satire(await at(session, 3, satire={"jest_chance": 0}), tally)
    told = await session.scalar(select(SatireRow).where(SatireRow.satirist_entity_id == wit.id))
    assert told is not None and not told.tolerated and told.punished and tally.punished == 1


async def test_a_mortal_reads_its_identities_and_refuge_in_its_context(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    me = await mortal(session, "Iri", world, town.id)
    session.add(HeldIdentityRow(holder_entity_id=me.id, layer=IdentityLayer.LOCALITY, value_node_id=town.id, salience=70, locked=[]))
    session.add(
        SanctuaryRow(
            fugitive_entity_id=me.id, host_entity_id=town.id, kind=SanctuaryKind.HOSPITALITY, fugitive_kind=FugitiveKind.OUTLAW, granted_epoch=1, locked=[]
        )
    )
    await session.flush()
    lines = " ".join(await mortal_belonging_lines(await load_scope(session, tuned_rules()), me))
    assert "your locality (Velmor) matters 70 out of 100 to you" in lines and "you shelter in Velmor" in lines


async def test_the_salient_identity_group_of_a_place_keeps_its_own_account(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    house = await entity(session, "House Arvel", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    kin, stranger = await mortal(session, "Iri", world, town.id), await mortal(session, "Oss", world, town.id)
    session.add_all(
        [
            HeldIdentityRow(holder_entity_id=town.id, layer=IdentityLayer.HOUSE, value_node_id=house.id, salience=80, locked=[]),
            HeldIdentityRow(holder_entity_id=kin.id, layer=IdentityLayer.HOUSE, value_node_id=house.id, salience=60, locked=[]),
        ]
    )
    battle = CollectionRow(kind=CollectionKind.WAR, name="The siege", world_id=world.world.id, start_epoch=3, locked=[])
    session.add(battle)
    await session.flush()
    session.add_all(
        [
            CollectionMemberRow(collection_id=battle.id, node_id=kin.id, role=CollectionRole.WINNER, since_epoch=0),
            CollectionMemberRow(collection_id=battle.id, node_id=stranger.id, role=CollectionRole.WINNER, since_epoch=0),
            CollectionPlaceRow(collection_id=battle.id, place_entity_id=town.id),
        ]
    )
    await session.flush()
    await chronicle_collection(await at(session, 3), battle, HistoryTally())
    told = await session.scalar(select(AccountRow).where(AccountRow.holder_entity_id == house.id, AccountRow.collection_id == battle.id))
    assert told is not None
    stances = {row.node_id: row.stance for row in await session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id == told.id))}
    assert stances == {kin.id: AccountStance.GLORIFY, stranger.id: AccountStance.NEUTRAL}


async def test_a_law_that_puts_children_to_work_keeps_labouring_children_from_play(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    await youngster(session, world, "Iri", town)
    await youngster(session, world, "Oss", town)
    law = await entity(session, "Law of the mills", EntityType.LAW, LawStats(), world_id=world.world.id)
    session.add(LawProfileRow(law_entity_id=law.id, kind=LawKind.LABOUR_LAW, area=LawArea.SOCIAL, params={"child_labour": True}, enforcement=80))
    session.add(LawJurisdictionRow(law_entity_id=law.id, node_entity_id=town.id, jurisdiction=Jurisdiction.POLITY))
    await session.flush()
    tally = PeerTally()
    await keep_peers(await at(session, 3), tally)
    group = await session.scalar(select(PeerGroupRow).where(PeerGroupRow.settlement_entity_id == town.id))
    assert group is not None and group.deprived and tally.deprived == 2


async def test_childhood_friends_keep_relationships_of_known_kinds_that_the_social_step_can_read(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Velmor", world, world.regions[0])
    first, second = await youngster(session, world, "Iri", town), await youngster(session, world, "Oss", town)
    await keep_peers(await at(session, 3, peer_groups={"friend_chance": 100, "rival_chance": 0}), PeerTally())
    rows = list(await session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id.in_([first.id, second.id]))))
    assert rows and all(set(row.kinds) <= set(RelationType) for row in rows)
    await refresh_kinds(session, tuned_rules(), first.id, 3)
    with pytest.raises(ValueError, match="known kind"):
        rows[0].kinds = ["childhood"]


async def test_caste_quarters_raise_rank_and_mixed_guilds_quiet_the_lines_they_cross(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Tierwall", world, world.regions[0])
    rank = PurityRankRow(people_entity_id=world.people.id, name="Keepers", standing=80, professions=[], endogamous=False, commensal=False, locked=[])
    session.add(rank)
    await session.flush()
    session.add(DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.MARKET, built_epoch=1, purity_rank_id=rank.id, locked=[]))
    other = await entity(session, "Hillfolk", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    guild = await entity(session, "The Joiners", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.CRAFT_GUILD, locked=[]))
    first, second = await mortal(session, "Iri", world, town.id), await mortal(session, "Oss", world, town.id)
    await bond(session, first.id, world.people.id, BondKind.DESCENDS_FROM)
    await bond(session, second.id, other.id, BondKind.DESCENDS_FROM)
    await bond(session, first.id, guild.id, BondKind.MEMBER_OF)
    await bond(session, second.id, guild.id, BondKind.MEMBER_OF)
    await session.flush()
    await keep_identities(await at(session, 3), IdentityTally())
    rank_line = await session.get(HeldIdentityRow, (town.id, IdentityLayer.CLASS))
    people_line = await session.get(HeldIdentityRow, (town.id, IdentityLayer.PEOPLE))
    rest = tuned_rules().identities.base_salience
    assert rank_line is not None and rank_line.driver is SalienceDriver.SEGREGATION and rank_line.salience > rest
    assert people_line is not None and people_line.driver is SalienceDriver.CROSSING and people_line.salience < rest
