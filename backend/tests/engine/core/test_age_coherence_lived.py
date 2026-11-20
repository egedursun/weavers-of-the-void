from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.methods import METHODS, PROCESS_METHODS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.industry import CommunityIndustryRow, CommunityMethodRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world import TechnologyEra
from aerona.domain.models.entity_stats import PeopleStats, SettlementStats
from aerona.domain.models.genesis import GenesisSettings
from aerona.engine.eras.effects import era_order, era_techniques
from aerona.engine.industry.methods import blocked_by, method_era
from aerona.engine.pipeline import simulate
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import active_bonds
from tests.engine.core.factories import bond, entity
from tests.engine.integration.factories import Frontier, seed_rich_cosmos

EPOCHS = 3
STARTED_IN = TechnologyEra.INFORMATION
MODERN_FROM = TechnologyEra.ELECTRICAL
OLD_INPUTS = frozenset({CommodityKind.TIMBER, CommodityKind.LIVESTOCK, CommodityKind.WOOL, CommodityKind.FIBRE, CommodityKind.MAGICAL_REAGENTS})
OLD_WORDS = ("scribe", "craft guild", "took the throne of", "alchemist", "charcoal burning")
DARK_AT = 50
THRONG = 180000
GATE_TOWN = 2000


async def throng_with_one_small_town(session: AsyncSession, frontier: Frontier) -> None:
    kin = frontier.peoples[0]
    region = frontier.regions[3]
    throng = await entity(
        session,
        f"{frontier.world.name} Throng",
        EntityType.PEOPLE,
        PeopleStats(population=THRONG, martiality=40, magic=20, craft=45, piety=55, prosperity=50, wealth=40),
        world_id=frontier.world.id,
        location_id=region.id,
        creator_son_id=frontier.son.id,
    )
    gate = await entity(
        session,
        f"{frontier.world.name} Gate",
        EntityType.SETTLEMENT,
        SettlementStats(population=GATE_TOWN, prosperity=50, defense=30, piety=50),
        world_id=frontier.world.id,
        location_id=region.id,
        creator_son_id=frontier.son.id,
    )
    for shared in await active_bonds(session, [BondKind.SPEAKS, BondKind.KNOWS, BondKind.WORSHIPS], sources=[kin.id]):
        for member in (throng, gate):
            await bond(session, member.id, shared.target_node_id, shared.kind)
    await bond(session, gate.id, throng.id, BondKind.DESCENDS_FROM)
    await session.flush()


async def facts_of(session: AsyncSession, kind: str) -> list[tuple[int, dict[str, str | float | None]]]:
    found: list[tuple[int, dict[str, str | float | None]]] = []
    for incident_id in await session.scalars(select(IncidentRow.id).where(IncidentRow.kind == kind).order_by(IncidentRow.id)):
        facts = await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id).order_by(IncidentFactRow.position))
        found.append((incident_id, {fact.key: fact.enum_value if fact.enum_value is not None else fact.number for fact in facts}))
    return found


async def subject_of(session: AsyncSession, incident_id: int, role: IncidentRole) -> int | None:
    return await session.scalar(
        select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident_id, IncidentParticipantRow.role == role).limit(1)
    )


async def lagging_methods(session: AsyncSession) -> list[str]:
    knowledge = await KnowledgeMap.load(session)
    lagging: list[str] = []
    for row in await session.scalars(select(CommunityMethodRow).order_by(CommunityMethodRow.community_node_id, CommunityMethodRow.process)):
        current = METHODS[row.method]
        if era_order(method_era(current)) >= era_order(MODERN_FROM):
            continue
        industry = await session.get(CommunityIndustryRow, row.community_node_id)
        techniques = set(await era_techniques(session, row.community_node_id))
        for spec in PROCESS_METHODS[row.process]:
            if spec.climate is not None or spec.coast or era_order(method_era(spec)) < era_order(MODERN_FROM):
                continue
            supply = int(getattr(industry, spec.energy.value)) if industry is not None else 0
            levels = {spec.branch: knowledge.level(row.community_node_id, spec.branch)} if spec.branch is not None else {}
            if blocked_by(spec, techniques=techniques, levels=levels, band=None, coastal=False, supply=supply) is None:
                lagging.append(f"{row.community_node_id} {row.process.value} by {current.kind.value} though {spec.kind.value} runs")
                break
    return lagging


async def test_a_world_that_begins_in_the_information_age_lives_like_one(database: Database) -> None:
    async with database.write() as session:
        rich = await seed_rich_cosmos(session)
        await throng_with_one_small_town(session, rich.frontiers[1])
        cosmos = await CosmosRepository(session).get()
        assert cosmos is not None
        cosmos.genesis_settings = GenesisSettings(magic=50, danger=50, peoples=2, technology=STARTED_IN)
    await simulate(database, EPOCHS)
    async with database.read() as session:
        lagging = await lagging_methods(session)
        old_shortages = [
            f"{facts['output']} for want of {facts['missing']}"
            for _, facts in await facts_of(session, "refining.bottleneck")
            if facts.get("missing") in OLD_INPUTS
        ]
        cold: list[int] = []
        for incident_id, _ in await facts_of(session, "consumption.cold_deaths"):
            victim = await subject_of(session, incident_id, IncidentRole.VICTIM)
            industry = await session.get(CommunityIndustryRow, victim) if victim is not None else None
            if industry is not None and industry.electric - industry.spent.get(EnergyKind.ELECTRIC.value, 0) > 0:
                cold.append(victim or 0)
        dark = [
            facts
            for _, facts in await facts_of(session, "industry.energy_short")
            if facts.get("energy") == EnergyKind.ELECTRIC.value and float(facts.get("unmet") or 0) >= DARK_AT
        ]
        lines = [
            text for text in await session.scalars(select(ChronicleRow.text).order_by(ChronicleRow.id)) if any(word in text.casefold() for word in OLD_WORDS)
        ]
    found = {"lagging methods": lagging, "old shortages": old_shortages, "cold with power": cold, "dark works": dark, "old words": lines}
    assert found == {"lagging methods": [], "old shortages": [], "cold with power": [], "dark works": [], "old words": []}
