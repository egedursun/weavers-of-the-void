from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.core.errors import ConflictError
from aerona.db.repositories.base import Repository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.travel import RouteClosure
from aerona.domain.enums.world import Atmosphere, Discovery, Gravity, StarType, WorldType
from aerona.domain.models.phonology import Phonology


@dataclass(frozen=True)
class StarDraft:
    name: str
    star_type: StarType
    brightness: int
    x: float
    y: float
    created_epoch: int
    description: str | None = None


@dataclass(frozen=True)
class WorldDraft:
    name: str
    world_type: WorldType
    orbit: float
    terrain_seed: str
    terrain_sea: float
    terrain_mountains: float
    terrain_humidity: float
    danger: int
    created_epoch: int
    star_id: int | None = None
    parent_world_id: int | None = None
    gravity: Gravity = Gravity.NORMAL
    atmosphere: Atmosphere = Atmosphere.NORMAL
    time_factor: float = 1.0
    discovery: Discovery = Discovery.KNOWN
    phonology: Phonology | None = None
    cosmology: str | None = None
    description: str | None = None
    creator_son_id: int | None = None


class WorldRepository(Repository):
    async def create_star(self, draft: StarDraft) -> StarRow:
        names = NameRepository(self.session)
        await self._ensure_free(names, draft.name)
        star = StarRow(
            name=draft.name,
            star_type=draft.star_type,
            brightness=draft.brightness,
            x=draft.x,
            y=draft.y,
            created_epoch=draft.created_epoch,
            description=draft.description,
        )
        await self.insert(star)
        star.name = await names.claim(star.id, draft.name)
        return star

    async def create_world(self, draft: WorldDraft) -> WorldRow:
        names = NameRepository(self.session)
        await self._ensure_free(names, draft.name)
        star_id = draft.star_id
        if draft.parent_world_id is not None:
            parent = await self.require(WorldRow, draft.parent_world_id, "world")
            star_id = await self.root_star_id(parent)
        world = WorldRow(
            name=draft.name,
            world_type=draft.world_type,
            star_id=star_id,
            parent_world_id=draft.parent_world_id,
            orbit=draft.orbit,
            gravity=draft.gravity,
            atmosphere=draft.atmosphere,
            time_factor=draft.time_factor,
            terrain_seed=draft.terrain_seed,
            terrain_sea=draft.terrain_sea,
            terrain_mountains=draft.terrain_mountains,
            terrain_humidity=draft.terrain_humidity,
            discovery=draft.discovery,
            danger=draft.danger,
            phonology=draft.phonology,
            cosmology=draft.cosmology,
            description=draft.description,
            creator_son_id=draft.creator_son_id,
            created_epoch=draft.created_epoch,
        )
        await self.insert(world)
        world.name = await names.claim(world.id, draft.name)
        return world

    async def root_star_id(self, world: WorldRow) -> int | None:
        seen: set[int] = set()
        current = world
        while current.parent_world_id is not None and current.id not in seen:
            seen.add(current.id)
            parent = await self.session.get(WorldRow, current.parent_world_id)
            if parent is None:
                break
            current = parent
        return current.star_id

    async def all_worlds(self) -> list[WorldRow]:
        return list(await self.session.scalars(select(WorldRow).order_by(WorldRow.id)))

    async def reachable_worlds(self) -> list[WorldRow]:
        statement = select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)
        return list(await self.session.scalars(statement))

    async def routes_touching(self, world_id: int, active_only: bool = False) -> list[RouteRow]:
        statement = select(RouteRow).where(or_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == world_id))
        if active_only:
            statement = statement.where(RouteRow.active.is_(True))
        return list(await self.session.scalars(statement.order_by(RouteRow.id)))

    async def set_discovery(self, world: WorldRow, discovery: Discovery) -> list[RouteRow]:
        previous = world.discovery
        world.discovery = discovery
        changed: list[RouteRow] = []
        if discovery is Discovery.FORGOTTEN and previous is not Discovery.FORGOTTEN:
            for route in await self.routes_touching(world.id, active_only=True):
                route.active = False
                route.closure = RouteClosure.FORGOTTEN
                route.closed_by_forgetting_world_id = world.id
                changed.append(route)
        if previous is Discovery.FORGOTTEN and discovery is not Discovery.FORGOTTEN:
            for route in await self.routes_touching(world.id):
                if route.closed_by_forgetting_world_id != world.id:
                    continue
                other_id = route.world_b_id if route.world_a_id == world.id else route.world_a_id
                other = await self.session.get(WorldRow, other_id)
                if other is not None and other.discovery is Discovery.FORGOTTEN:
                    route.closed_by_forgetting_world_id = other.id
                    continue
                route.active = True
                route.closure = None
                route.closed_by_forgetting_world_id = None
                changed.append(route)
        await self.flush()
        return changed

    async def connected(self, first_world_id: int, second_world_id: int) -> bool:
        if first_world_id == second_world_id:
            return True
        statement = select(RouteRow.id).where(
            RouteRow.active.is_(True),
            or_(
                (RouteRow.world_a_id == first_world_id) & (RouteRow.world_b_id == second_world_id),
                (RouteRow.world_a_id == second_world_id) & (RouteRow.world_b_id == first_world_id),
            ),
        )
        return await self.session.scalar(statement.limit(1)) is not None

    @staticmethod
    async def _ensure_free(names: NameRepository, name: str) -> None:
        if await names.is_taken(name):
            raise ConflictError(f"The name {name} is already taken.")
