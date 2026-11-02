from sqlalchemy.ext.asyncio import AsyncSession

from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules


class Neighbourhood:
    def __init__(self, atlas: RegionAtlas, hops: int) -> None:
        self.atlas = atlas
        self._hops = hops

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "Neighbourhood":
        return cls(await RegionAtlas.load(session), rules.diplomacy.neighbor_hops)

    def top_region(self, entity_id: int | None) -> int | None:
        return self.atlas.top_region(entity_id)

    def hop_distance(self, first: int, second: int) -> int | None:
        return self.atlas.hops(first, second)

    def are_neighbours(self, first: int, second: int) -> bool:
        distance = self.hop_distance(first, second)
        return distance is not None and distance <= self._hops
