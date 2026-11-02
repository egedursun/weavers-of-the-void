from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.domain.enums.world import Discovery
from aerona.engine.primitives.tired_motifs import MotifCache
from aerona.rules.registry import Rules


@dataclass
class Scope:
    session: AsyncSession
    rules: Rules
    cosmos: CosmosRow
    creator: CreatorRow
    worlds: dict[int, WorldRow]
    motifs: MotifCache = field(default_factory=MotifCache)

    @property
    def epoch(self) -> int:
        return self.cosmos.epoch

    @property
    def primary_world_id(self) -> int:
        if self.cosmos.primary_world_id is not None:
            return self.cosmos.primary_world_id
        return min(self.worlds) if self.worlds else 0

    @property
    def primary_world(self) -> WorldRow | None:
        return self.worlds.get(self.primary_world_id)

    @property
    def living_worlds(self) -> list[WorldRow]:
        return [world for world in self.worlds.values() if world.discovery is not Discovery.FORGOTTEN]

    @property
    def multi_world(self) -> bool:
        return len(self.living_worlds) > 1

    def world_name(self, world_id: int | None) -> str:
        world = self.worlds.get(world_id) if world_id is not None else None
        return world.name if world is not None else ""


async def load_scope(session: AsyncSession, rules: Rules) -> Scope:
    repository = CosmosRepository(session)
    cosmos = await repository.require_cosmos()
    creator = await repository.require_creator()
    worlds = {world.id: world for world in await session.scalars(select(WorldRow).order_by(WorldRow.id))}
    return Scope(session, rules, cosmos, creator, worlds)
