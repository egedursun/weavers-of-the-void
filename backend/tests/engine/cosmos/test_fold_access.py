from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.models.entity_stats import PeopleStats, ResourceStats
from aerona.engine.cosmos.resources import cosmic_access
from aerona.engine.cosmos.routes import _passage_problem
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_route, make_world


async def deposit(session: AsyncSession, cosmos: Cosmos, name: str, abundance: int) -> EntityRow:
    return await make_entity(
        session, name, EntityType.RESOURCE, ResourceStats(abundance=abundance), world_id=cosmos.home.id, engine_kind=EngineKind.COSMIC_TRAVEL_RESOURCE
    )


async def bond(session: AsyncSession, source: int, target: int, kind: BondKind) -> None:
    await BondRepository(session).connect(BondDraft(source, target, kind, 1, None))


async def test_folding_space_needs_a_rich_enough_deposit_owned_or_traded_for(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    need = rules.travel.fold_min_abundance
    folk = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=800), world_id=cosmos.home.id)
    partner = await make_entity(session, "Vel", EntityType.PEOPLE, PeopleStats(population=800), world_id=cosmos.home.id)
    other = await make_world(session, "Far Shore")
    fold = await make_route(session, cosmos.home.id, other.id, TravelMethod.SPACE_FOLD)
    assert await cosmic_access(session, folk.id, need) is None
    assert await _passage_problem(session, rules, folk, fold) is not None
    thin = await deposit(session, cosmos, "Thin Seam", need - 1)
    await bond(session, folk.id, thin.id, BondKind.OWNS)
    assert await cosmic_access(session, folk.id, need) is None
    rich = await deposit(session, cosmos, "Rich Seam", need + 10)
    await bond(session, partner.id, rich.id, BondKind.OWNS)
    assert await cosmic_access(session, folk.id, need) is None
    assert await cosmic_access(session, partner.id, need) == rich
    await bond(session, folk.id, partner.id, BondKind.TRADES_WITH)
    assert await cosmic_access(session, folk.id, need) == rich
    assert await _passage_problem(session, rules, folk, fold) is None
