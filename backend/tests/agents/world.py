from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository, snapshot_rules
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.models.entity_stats import LegendStats, PeopleStats
from aerona.domain.models.phonology import Phonology
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, seed_rich_world

PHONOLOGY = Phonology(
    vowels=("a", "e", "i", "o"), consonants=("k", "l", "m", "n", "r", "s", "t", "v"), syllable_patterns=("CV", "CVC"), min_syllables=1, max_syllables=3
)


@dataclass
class AgentWorld:
    core: CoreWorld
    creation: EntityRow
    pending: EntityRow


async def seed_agent_world(session: AsyncSession, rules: Rules) -> AgentWorld:
    core = await seed_rich_world(session)
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.rules_snapshot = snapshot_rules(rules)
    core.world.phonology = PHONOLOGY
    entities = EntityRepository(session)
    creation = await entities.create(
        EntityDraft(
            name="Orrin Folk",
            entity_type=EntityType.PEOPLE,
            description="A people of salt-diggers who sing to the stone before they cut it, and keep the bones of their mothers in the walls.",
            stats=PeopleStats(population=900, martiality=30, magic=20, craft=60, piety=50, prosperity=40, wealth=30),
            power_level=3,
            origin=EntityOrigin.SON,
            birth_epoch=1,
            world_id=core.world.id,
            location_id=core.regions[0].id,
            creator_son_id=core.son.id,
            split_title=False,
        )
    )
    pending = await entities.create(
        EntityDraft(
            name="Unnamed Tale",
            entity_type=EntityType.LEGEND,
            description="[World engine] A tale born of the drought.",
            stats=LegendStats(),
            power_level=2,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=core.world.id,
            pending_name=True,
            split_title=False,
        )
    )
    await session.flush()
    return AgentWorld(core, creation, pending)
