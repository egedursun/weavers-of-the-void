from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.factions import FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.db.tables.polity import (
    ClaimRow,
    HouseProfileRow,
    LawProfileRow,
    MortalReputeRow,
    OathRow,
    OfficeRow,
    TreatyBreachRow,
    TreatyClauseRow,
    TreatyProfileRow,
)
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionGoalKind, FactionKind, FactionRank
from aerona.domain.enums.polity import (
    ClauseKind,
    HouseTrait,
    LawKind,
    OathKind,
    OathStatus,
    OfficeKind,
    OfficePower,
    PartyRole,
    TreatyKind,
    TreatyStatus,
)
from aerona.domain.models.entity_stats import MortalStats, SettlementStats
from aerona.engine.factions.balance import power_balance
from aerona.engine.polity.accords import bond_ends, clause_pairs
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.law_effects import bequest_order
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.offices import powers_of, seize_throne
from aerona.services.player import factions, heroes, realms
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, bond, make_entity, make_son


async def town(session: AsyncSession, world: PlayerWorld, name: str, population: int = 4000) -> int:
    row = await make_entity(
        session, name, EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats(population=population)
    )
    return row.id


async def realm_of(session: AsyncSession, scope: PlayerScope, core: int) -> int:
    outcome = await realms.found_realm(scope, realms.FoundRealm(core_id=core))
    return outcome.created_ids[0]


async def test_a_sealed_alliance_makes_the_bond_and_a_breach_ends_it(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await town(session, world, "Greatford"), await town(session, world, "Saltreach")
    outcome = await realms.sign_treaty(
        scope,
        realms.SignTreaty(kind=TreatyKind.ALLIANCE_DEFENSIVE, parties=[realms.TreatyParty(party_id=first), realms.TreatyParty(party_id=second)]),
    )
    profile = await session.get(TreatyProfileRow, outcome.created_ids[0])
    assert profile is not None and profile.source_bond_id is not None
    assert await BondRepository(session).exists_between(first, second, BondKind.ALLY)
    await realms.break_treaty(scope, realms.BreakTreaty(treaty_id=profile.treaty_entity_id, breaker_id=first))
    derived = await session.get(BondRow, profile.source_bond_id)
    assert profile.status is TreatyStatus.BROKEN and derived is not None and derived.state is not BondState.ACTIVE
    breach = await session.scalar(select(TreatyBreachRow).where(TreatyBreachRow.treaty_entity_id == profile.treaty_entity_id))
    assert breach is not None and breach.incident_id is not None


async def test_clauses_and_guarantors_can_be_written_in_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second, third = await town(session, world, "Ardford"), await town(session, world, "Brine"), await town(session, world, "Cairn")
    outcome = await realms.sign_treaty(
        scope,
        realms.SignTreaty(kind=TreatyKind.TRADE_PACT, parties=[realms.TreatyParty(party_id=first), realms.TreatyParty(party_id=second)], epochs=4),
    )
    treaty = outcome.created_ids[0]
    added = await realms.add_clause(scope, realms.AddClause(treaty_id=treaty, kind=ClauseKind.RELIGIOUS_FREEDOM, obligor_id=first, beneficiary_id=second))
    assert frozenset((first, second)) in await clause_pairs(session, ClauseKind.RELIGIOUS_FREEDOM)
    await realms.remove_clause(scope, realms.ClauseTarget(clause_id=int(added.values["clause_id"] or 0)))
    assert await session.get(TreatyClauseRow, int(added.values["clause_id"] or 0)) is None
    await realms.add_party(scope, realms.TreatyPartyChange(treaty_id=treaty, party_id=third, role=PartyRole.GUARANTOR))
    await realms.edit_treaty(scope, realms.EditTreaty(treaty_id=treaty, until_epoch=99, hold=["until_epoch"]))
    profile = await session.get(TreatyProfileRow, treaty)
    assert profile is not None and "until_epoch" in profile.locked
    await realms.edit_treaty(scope, realms.EditTreaty(treaty_id=treaty, release=["until_epoch"]))
    assert "until_epoch" not in profile.locked


def test_tribute_bonds_run_from_the_vassal_to_the_lord() -> None:
    assert bond_ends(TreatyKind.TRIBUTE, [(2, PartyRole.VASSAL), (1, PartyRole.OVERLORD)], []) == (2, 1)
    assert bond_ends(TreatyKind.ALLIANCE_DEFENSIVE, [(1, PartyRole.SIGNATORY), (2, PartyRole.GUARANTOR)], []) is None


async def test_a_protected_law_holds_and_its_kind_and_conflict_can_be_rewritten(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    core = await town(session, world, "Lawhold")
    polity = await realm_of(session, scope, core)
    outcome = await realms.enact_law(scope, realms.EnactLaw(holder_id=polity, kind=LawKind.TOLLS, params={"rate": 12}, hold=["repeal"]))
    law = outcome.created_ids[0]
    profile = await session.get(LawProfileRow, law)
    assert profile is not None and profile.kind is LawKind.TOLLS and "repeal" in profile.locked
    await realms.protect_law(scope, realms.ProtectLaw(law_id=law, hold=["params"], release=["repeal"]))
    assert profile.locked == ["params"]
    await realms.edit_law(scope, realms.EditLaw(law_id=law, kind=LawKind.LEVY_LAW, conflict=40, release=["params"]))
    assert profile.kind is LawKind.LEVY_LAW and profile.conflict == 40 and "share" in profile.params


async def test_a_cult_law_binds_the_faithful_of_its_god(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    god = await make_son(session, "The Tide", world.world.id)
    cult = await make_entity(session, "Church of the Tide", EntityType.CULT, world_id=world.world.id, location_id=world.region.id)
    place = await town(session, world, "Tidewater")
    await bond(session, cult.id, god.id, BondKind.WORSHIPS)
    await bond(session, place, god.id, BondKind.WORSHIPS)
    await realms.enact_law(scope, realms.EnactLaw(holder_id=cult.id, kind=LawKind.BURIAL_LAW, params={"rite": "burning"}))
    laws = await LawBook.load(session)
    assert laws.param(place, LawKind.BURIAL_LAW, "rite") == "burning"


async def test_offices_carry_powers_and_can_be_made_and_abolished(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    core = await town(session, world, "Crownmere")
    polity = await realm_of(session, scope, core)
    keeper = await make_entity(session, "Ovo", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=40, charisma=60))
    made = await realms.create_office(
        scope, realms.CreateOffice(polity_id=polity, kind=OfficeKind.CHANCELLOR, title="Keeper of Envoys", powers=["negotiate", "embassy"], holder_id=keeper.id)
    )
    office = await session.get(OfficeRow, int(made.values["office_id"] or 0))
    assert office is not None and powers_of(office) == {OfficePower.NEGOTIATE, OfficePower.EMBASSY} and office.holder_entity_id == keeper.id
    await realms.abolish_office(scope, realms.OfficeTarget(office_id=office.id))
    assert await session.get(OfficeRow, office.id) is None


async def test_a_seized_throne_marks_the_usurper_with_infamy(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    core = await town(session, world, "Thronefast")
    await realm_of(session, scope, core)
    usurper = await make_entity(session, "Vel", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=30))
    book = await RealmBook.load(session)
    found = next(item for item in book.realms.values() if item.profile.core_entity_id == core)
    ctx = await scope.context("test_coup")
    assert await seize_throne(ctx, found, usurper, "a test of arms")
    repute = await session.get(MortalReputeRow, usurper.id)
    assert found.ruler_id == usurper.id and "usurper" in found.profile.legitimacy_parts and repute is not None and repute.infamy > 0


async def test_claims_can_be_granted_edited_and_revoked(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    core = await town(session, world, "Claimhold")
    polity = await realm_of(session, scope, core)
    claimant = await make_entity(session, "Ise", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=22))
    await realms.grant_claim(scope, realms.GrantClaim(mortal_id=claimant.id, polity_id=polity, strength=40))
    claim = await session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == claimant.id))
    assert claim is not None
    await realms.edit_claim(scope, realms.EditClaim(claim_id=claim.id, strength=75, pressed=False))
    assert claim.strength == 75 and "strength" in claim.locked
    await realms.revoke_claim(scope, realms.ClaimTarget(claim_id=claim.id))
    assert claim.ended_epoch is not None


async def test_a_house_can_be_reshaped_and_an_oath_released_with_honour(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    lord = await make_entity(session, "Aric", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id, stats=MortalStats(age=35))
    founded = await realms.found_house(scope, realms.FoundHouse(mortal_id=lord.id))
    house = founded.created_ids[0]
    await realms.edit_house(scope, realms.EditHouse(house_id=house, values={"prestige": 80, "motto": "We remember", "traits": ["seer_gift"]}))
    profile = await session.get(HouseProfileRow, house)
    assert profile is not None and profile.prestige == 80 and profile.traits == [HouseTrait.SEER_GIFT] and "prestige" in profile.locked
    await realms.edit_house(scope, realms.EditHouse(house_id=house, release=["prestige"]))
    assert "prestige" not in profile.locked
    await realms.swear_oath(scope, realms.SwearOath(swearer_id=lord.id, kind=OathKind.PILGRIMAGE))
    oath = await session.scalar(select(OathRow).where(OathRow.swearer_entity_id == lord.id))
    assert oath is not None
    await realms.release_oath(scope, realms.OathTarget(oath_id=oath.id))
    repute = await session.get(MortalReputeRow, lord.id)
    assert oath.status is OathStatus.KEPT and repute is not None and repute.honour > 50


async def test_a_faction_is_typed_steered_and_weighs_in_its_realm(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    core = await town(session, world, "Guildport")
    polity = await realm_of(session, scope, core)
    founded = await heroes.found_faction(scope, heroes.Faction(community_id=core, kind=FactionKind.MERCHANT_GUILD))
    faction = founded.created_ids[0]
    profile = await session.get(FactionProfileRow, faction)
    assert profile is not None and profile.kind is FactionKind.MERCHANT_GUILD and profile.home_entity_id == core
    await factions.set_goal(scope, factions.FactionGoal(faction_id=faction, kind=FactionGoalKind.LOWER_TAXES, target_id=polity))
    goal = await session.scalar(select(FactionGoalRow).where(FactionGoalRow.faction_entity_id == faction))
    assert goal is not None and goal.set_by_player
    member = await make_entity(session, "Ama", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=33))
    await factions.set_member(scope, factions.FactionMember(faction_id=faction, mortal_id=member.id, rank=FactionRank.LEADER))
    assert (await session.get(FactionMembershipRow, (faction, member.id))) is not None and profile.leader_entity_id == member.id
    await factions.fund(scope, factions.FundFaction(faction_id=faction, amount=200))
    await factions.charter(scope, factions.CharterFaction(faction_id=faction, polity_id=polity, monopoly="luxuries"))
    assert profile.treasury >= 200 and profile.chartered_by_entity_id == polity and profile.monopoly == "luxuries"
    book = await RealmBook.load(session)
    found = book.realms[polity]
    assert faction in await power_balance(await scope.context("test_balance"), found)
    await factions.outlaw(scope, factions.OutlawFaction(faction_id=faction))
    assert profile.outlawed and profile.chartered_by_entity_id is None
    assert faction not in await power_balance(await scope.context("test_balance"), found)


async def test_inheritance_law_chooses_who_inherits(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    core = await town(session, world, "Heirsby")
    polity = await realm_of(session, scope, core)
    father = await make_entity(session, "Old Bran", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=70))
    elder = await make_entity(session, "Bran", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=40))
    younger = await make_entity(session, "Brin", EntityType.MORTAL, world_id=world.world.id, location_id=core, stats=MortalStats(age=20))
    assert await bequest_order(session, father, [younger, elder]) == [younger]
    await realms.enact_law(scope, realms.EnactLaw(holder_id=polity, kind=LawKind.INHERITANCE_SPLIT, params={"split": "eldest"}))
    assert await bequest_order(session, father, [younger, elder]) == [elder]
    law = await session.scalar(select(LawProfileRow).where(LawProfileRow.kind == LawKind.INHERITANCE_SPLIT))
    assert law is not None
    await realms.edit_law(scope, realms.EditLaw(law_id=law.law_entity_id, params={"split": "equal"}))
    assert await bequest_order(session, father, [younger, elder]) == [elder, younger]
