from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations, product

from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import canon, living_entity
from aerona.engine.services.war import declare_war


@dataclass(frozen=True)
class Feud:
    first_son: str
    second_son: str

    @property
    def gods(self) -> str:
        return f"{self.first_son} and {self.second_son}"


async def leak(ctx: TickContext, feud: Feud, first: EntityRow, second: EntityRow) -> bool:
    holy = EntityType.CULT in (first.entity_type, second.entity_type)
    reason = f"holy war: {feud.gods}" if holy else f"the grudge between {feud.gods}"
    if not await declare_war(ctx, first.id, second.id, reason, cause=WarCause.DIVINE_GRUDGE):
        return False
    if holy:
        text = f"The grudge between {feud.gods} turned into a holy war: {first.name} and {second.name} came to blows."
    else:
        text = f"The grudge between {feud.gods} leaked to the mortals: {first.name} and {second.name} became enemies."
    await note(ctx, text, key="grudges.holy_war" if holy else "grudges.enmity", ids=[first.id, second.id])
    return True


async def within_reach(ctx: TickContext, atlas: RegionAtlas, first: EntityRow, second: EntityRow) -> bool:
    if first.world_id != second.world_id or atlas.distance(first.id, second.id) > ctx.rules.world_effects.god_grudge_distance:
        return False
    return await living_entity(ctx.session, first.id) is not None and await living_entity(ctx.session, second.id) is not None


async def worshippers_by_patron(ctx: TickContext) -> tuple[dict[int, list[EntityRow]], dict[int, str]]:
    by_patron: dict[int, list[EntityRow]] = defaultdict(list)
    names: dict[int, str] = {}
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        patron = await living_patron(ctx.session, community)
        if patron is not None:
            by_patron[patron.id].append(community)
            names[patron.id] = patron.name
    return by_patron, names


@reads("table.bonds", "table.epoch_year_cursors", "table.nodes", "table.son_relations", "table.war_sides", "table.wars", "table.world_maps")
@writes("table.bonds", "table.chronicle", "table.chronicle_entities", "table.epoch_year_cursors", "table.incident_participants", "table.incidents")
async def divine_grudges(ctx: TickContext) -> None:
    effects = ctx.rules.world_effects
    rng = ctx.rng()
    by_patron, names = await worshippers_by_patron(ctx)
    sons = SonRepository(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    leaked = 0
    for first_son, second_son in combinations(sorted(by_patron), 2):
        if await sons.relation(first_son, second_son) > -effects.god_grudge_relation:
            continue
        feud = Feud(names[first_son], names[second_son])
        for first, second in product(by_patron[first_son], by_patron[second_son]):
            if leaked >= effects.god_grudge_cap:
                return
            if not await within_reach(ctx, atlas, first, second) or not rng.chance(ctx.rules.world_engine.god_grudge_spill_chance):
                continue
            leaked += await leak(ctx, feud, first, second)


PHASES = (Phase("divine_grudges", divine_grudges),)
