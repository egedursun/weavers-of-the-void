from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository, snapshot_rules
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.domain.enums.entity import EntityOrigin, EntityType, MortalRole
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.models.entity_stats import LegendStats, MortalStats, PeopleStats
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
    scribe = await entities.create(
        EntityDraft(
            name="Ehmel",
            entity_type=EntityType.MORTAL,
            description="A scribe who keeps the record of the age.",
            stats=MortalStats(age=40, lifespan=70),
            power_level=1,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=core.world.id,
            location_id=core.regions[0].id,
            mortal_role=MortalRole.SCRIBE,
            split_title=False,
        )
    )
    await session.flush()
    session.add_all(
        [
            RecordKeeperRow(kind=RecordKeeperKind.CHRONICLER, scope_node_id=core.creator.id, keeper_entity_id=scribe.id, since_epoch=1, locked=[]),
            RecordKeeperRow(kind=RecordKeeperKind.HISTORIAN, scope_node_id=core.people.id, keeper_entity_id=scribe.id, since_epoch=1, locked=[]),
        ]
    )
    await session.flush()
    return AgentWorld(core, creation, pending)
