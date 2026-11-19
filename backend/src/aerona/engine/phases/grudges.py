from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations, product

from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.queries import canon, count_communities, living_entity
from aerona.engine.recording.record import RoleValue, record
from aerona.engine.services.war import declare_war


@dataclass(frozen=True)
class Feud:
    first_son: str
    second_son: str
    first_id: int
    second_id: int

    @property
    def gods(self) -> str:
        return f"{self.first_son} and {self.second_son}"


async def leak(ctx: TickContext, feud: Feud, first: EntityRow, second: EntityRow) -> bool:
    holy = EntityType.CULT in (first.entity_type, second.entity_type)
    reason = f"holy war: {feud.gods}" if holy else f"the grudge between {feud.gods}"
    if not await declare_war(ctx, first.id, second.id, reason, cause=WarCause.DIVINE_GRUDGE):
        return False
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.ACTOR: first.id,
        IncidentRole.OPPONENT: second.id,
        IncidentRole.PATRON: (feud.first_id, feud.second_id),
    }
    await record(ctx, "grudges.holy_war" if holy else "grudges.enmity", roles=roles, facts={"cause": WarCause.DIVINE_GRUDGE})
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


@reads("table.bonds", "table.nodes", "table.son_relations", "table.war_sides", "table.wars", "table.world_maps")
@writes("table.bonds", "table.chronicle", "table.chronicle_entities", "table.incident_participants", "table.incidents")
async def divine_grudges(ctx: TickContext) -> None:
    effects = ctx.rules.world_effects
    rng = ctx.rng()
    by_patron, names = await worshippers_by_patron(ctx)
    sons = SonRepository(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    leaked = 0
    cap = scaled_cap(effects.god_grudge_cap, effects.god_grudge_cap_community_divisor, await count_communities(ctx.session))
    order = ctx.rng("order")
    for first_son, second_son in order.shuffled(combinations(sorted(by_patron), 2)):
        if await sons.relation(first_son, second_son) > -effects.god_grudge_relation:
            continue
        feud = Feud(names[first_son], names[second_son], first_son, second_son)
        for first, second in order.shuffled(product(by_patron[first_son], by_patron[second_son])):
            if leaked >= cap:
                return
            if not await within_reach(ctx, atlas, first, second) or not rng.chance(ctx.rules.world_engine.god_grudge_spill_chance):
                continue
            leaked += await leak(ctx, feud, first, second)


PHASES = (Phase("divine_grudges", divine_grudges),)
