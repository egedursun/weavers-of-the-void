from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.society import BUILT_IN_JOBS, BUILT_IN_ORGANISATIONS, BUILT_IN_PROFESSIONS, BUILT_IN_RANKS
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_kinds import OrganisationKindRow, ProfessionKindRow, RankKindRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import RoleEligibility
from aerona.domain.enums.cycles import AdoptionKind, KinshipDescent, KinTermSystem
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mind import Profession
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_kinds import OrganisationLegalForm, ProfessionCategory
from aerona.domain.models.entity_stats import FactionStats, PeopleStats, SettlementStats
from aerona.engine.body.customs import people_id_of
from aerona.engine.cycles.seeding import Reading, adoption_for, cousins_for, descent_for
from aerona.engine.cycles.sides import drawn_side
from aerona.engine.kinds.professions import professions_by_purity
from aerona.engine.kinds.society import ensure_built_ins, keep_society_kinds, mortals_may_found, organisation_of
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.cosmos.factories import Cosmos, make_entity, seed_cosmos, tick, tuned
from tests.tools.factories import connect


@pytest.fixture
async def session(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[AsyncSession]:
    database: Database = open_database(tmp_path / "society_kinds.db")
    async with database.write() as found:
        yield found
    await database.dispose()


@pytest.fixture
async def cosmos(session: AsyncSession) -> Cosmos:
    return await seed_cosmos(session)


async def people_with_town(session: AsyncSession, cosmos: Cosmos) -> tuple[EntityRow, EntityRow]:
    people = await make_entity(session, "Orrin", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    town = await make_entity(session, "Vessa", EntityType.SETTLEMENT, SettlementStats(population=900, prosperity=40), world_id=cosmos.home.id)
    await connect(session, town.id, people.id, BondKind.DESCENDS_FROM)
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            share_farmer=60.0,
            share_artisan=10.0,
            share_merchant=10.0,
            share_priest=5.0,
            share_warrior=10.0,
            share_scribe=5.0,
            satisfaction_farmer=40,
            satisfaction_artisan=50,
            satisfaction_merchant=50,
            satisfaction_priest=50,
            satisfaction_warrior=50,
            satisfaction_scribe=50,
            stock_food=100,
            stock_ore=100,
            stock_goods=100,
            price_food=10,
            price_ore=10,
            price_goods=10,
        )
    )
    await session.flush()
    return people, town


async def hold(session: AsyncSession, concept: KindConcept, kind_id: int, holder: EntityRow, strength: int = 100) -> None:
    session.add(KindHoldingRow(concept=concept, kind_id=kind_id, holder_node_id=holder.id, stance=KindStance.USES, strength=strength, locked=[]))
    await session.flush()


async def test_the_built_in_kinds_are_made_once_for_every_profession_class_and_faction(session: AsyncSession, cosmos: Cosmos) -> None:
    assert await ensure_built_ins(session) == len(BUILT_IN_PROFESSIONS) + len(BUILT_IN_JOBS) + len(BUILT_IN_RANKS) + len(BUILT_IN_ORGANISATIONS)
    assert await ensure_built_ins(session) == 0
    for table in (ProfessionKindRow, RankKindRow, OrganisationKindRow):
        assert await session.scalar(select(func.count()).select_from(table).where(table.built_in.is_(True)))
    assert {KindConcept.PROFESSION, KindConcept.RANK, KindConcept.ORGANISATION} <= set(CONCEPTS)


async def test_a_people_s_own_profession_kind_sets_where_that_work_stands_in_purity(session: AsyncSession, cosmos: Cosmos) -> None:
    people, _ = await people_with_town(session, cosmos)
    await ensure_built_ins(session)
    before = await professions_by_purity(session, people.id)
    assert before[-1] is Profession.MINER
    own = ProfessionKindRow(name="Deep Delvers", category=ProfessionCategory.EXTRACTION, base=Profession.MINER, purity=99, locked=[])
    session.add(own)
    await session.flush()
    await hold(session, KindConcept.PROFESSION, own.id, people)
    after = await professions_by_purity(session, people.id)
    assert after[0] is Profession.MINER


async def test_a_rank_with_more_privilege_than_duty_contents_its_class(session: AsyncSession, cosmos: Cosmos) -> None:
    people, town = await people_with_town(session, cosmos)
    rank = RankKindRow(name="Landed", category=SocialClass.FARMER, privilege=90, duty=10, locked=[])
    session.add(rank)
    await session.flush()
    await hold(session, KindConcept.RANK, rank.id, people)
    await keep_society_kinds(tick(session, tuned(Rules(), "society_kinds", rank_pull_pct=50)))
    society = await session.get(CommunitySocietyRow, town.id)
    assert society is not None and society.satisfaction_farmer == 80


async def test_the_earnings_of_held_professions_raise_the_towns_of_a_people(session: AsyncSession, cosmos: Cosmos) -> None:
    people, town = await people_with_town(session, cosmos)
    trade = ProfessionKindRow(name="Brokers", category=ProfessionCategory.TRADE, base=Profession.MERCHANT, income=100, locked=[])
    session.add(trade)
    await session.flush()
    await hold(session, KindConcept.PROFESSION, trade.id, people)
    await keep_society_kinds(tick(session, tuned(Rules(), "society_kinds", income_pct=10)))
    assert stat(town, "prosperity") == 50


async def test_a_faction_takes_on_its_organisation_kind_and_an_outlawed_form_outlaws_it(session: AsyncSession, cosmos: Cosmos) -> None:
    people, town = await people_with_town(session, cosmos)
    faction = await make_entity(session, "Night Ledger", EntityType.FACTION, FactionStats(), world_id=cosmos.home.id)
    profile = FactionProfileRow(faction_entity_id=faction.id, kind=FactionKind.MERCHANT_GUILD, home_entity_id=town.id, cohesion=20, secrecy=0, reputation=50)
    profile.locked = []
    session.add(profile)
    own = OrganisationKindRow(
        name="Hidden Purse",
        category=BUILT_IN_ORGANISATIONS[FactionKind.MERCHANT_GUILD].category,
        base=FactionKind.MERCHANT_GUILD,
        cohesion=100,
        secrecy=100,
        prestige=50,
        legal_form=OrganisationLegalForm.OUTLAWED,
        locked=[],
    )
    session.add(own)
    await session.flush()
    await hold(session, KindConcept.ORGANISATION, own.id, people)
    assert await organisation_of(session, profile) is own
    await keep_society_kinds(tick(session, tuned(Rules(), "society_kinds", drift_pct=50)))
    assert (profile.cohesion, profile.secrecy, profile.outlawed) == (60, 50, True)


async def test_held_nodes_keep_their_ranks_and_factions(session: AsyncSession, cosmos: Cosmos) -> None:
    people, town = await people_with_town(session, cosmos)
    rank = RankKindRow(name="Landed", category=SocialClass.FARMER, privilege=90, duty=10, locked=[])
    session.add(rank)
    await session.flush()
    await hold(session, KindConcept.RANK, rank.id, people)
    token = HELD_SCOPE.set(HeldScope(only=None, nodes=frozenset({people.id, town.id})))
    try:
        await keep_society_kinds(tick(session, tuned(Rules(), "society_kinds", rank_pull_pct=50)))
    finally:
        HELD_SCOPE.reset(token)
    society = await session.get(CommunitySocietyRow, town.id)
    assert society is not None and society.satisfaction_farmer == 40


async def test_mortals_found_only_the_organisation_kinds_their_people_allow(session: AsyncSession, cosmos: Cosmos) -> None:
    _, town = await people_with_town(session, cosmos)
    assert await mortals_may_found(session, town, FactionKind.MERCHANT_GUILD)
    assert not await mortals_may_found(session, town, FactionKind.PARTY)
    people = await people_id_of(session, town)
    assert people is not None
    closed = OrganisationKindRow(
        name="Sealed Ledger", category=BUILT_IN_ORGANISATIONS[FactionKind.MERCHANT_GUILD].category, base=FactionKind.MERCHANT_GUILD, foundable=False, locked=[]
    )
    session.add(closed)
    await session.flush()
    session.add(KindHoldingRow(concept=KindConcept.ORGANISATION, kind_id=closed.id, holder_node_id=people, stance=KindStance.USES, strength=80, locked=[]))
    await session.flush()
    assert not await mortals_may_found(session, town, FactionKind.MERCHANT_GUILD)


def test_kin_terms_adoption_and_the_first_side_follow_the_culture_never_a_fixed_sex() -> None:
    rules = Rules()
    table = rules.kinship_systems
    warm = Reading(kin=table.all_siblings_at, family=0, hierarchy=0, tradition=0, wealth=0, perseverance=0)
    assert cousins_for(warm, rules, KinshipDescent.BILATERAL) is KinTermSystem.GENERATIONAL
    middling = Reading(kin=table.parallel_siblings_at, family=0, hierarchy=0, tradition=0, wealth=0, perseverance=0)
    assert cousins_for(middling, rules, KinshipDescent.THROUGH_FIRST_LINE) is KinTermSystem.BIFURCATE_MERGING
    assert cousins_for(middling, rules, KinshipDescent.BILATERAL) is KinTermSystem.CROSS_PARALLEL
    cold = Reading(kin=table.descriptive_at, family=0, hierarchy=0, tradition=0, wealth=0, perseverance=0)
    assert cousins_for(cold, rules, KinshipDescent.BILATERAL) is KinTermSystem.DESCRIPTIVE
    lofty = Reading(kin=0, family=0, hierarchy=table.heir_adoption_at, tradition=0, wealth=0, perseverance=0)
    assert adoption_for(lofty, rules) is AdoptionKind.HEIR
    sides = {drawn_side(people) for people in range(1, 40)}
    assert sides == {SexKind.BEARER, SexKind.BEGETTER}
    plain = Reading(kin=0, family=0, hierarchy=0, tradition=0, wealth=0, perseverance=0)
    for first in (SexKind.BEARER, SexKind.BEGETTER):
        line = descent_for(None, RoleEligibility.BEARERS_ONLY, plain, rules, people_id=1, first=first)
        assert line is (KinshipDescent.THROUGH_FIRST_LINE if first is SexKind.BEARER else KinshipDescent.THROUGH_SECOND_LINE)
