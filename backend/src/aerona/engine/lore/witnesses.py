from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.life.lore import RANK
from aerona.catalog.life_traits import WITNESS_MODE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import WorldAttentionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import WitnessModeTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import WitnessMode
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules

WITNESS_BATCH = 2000

HELD_PART = "witnesses"


@dataclass
class Seen:
    modes: dict[int, WitnessMode] = field(default_factory=dict)

    def add(self, node_id: int, mode: WitnessMode) -> None:
        current = self.modes.get(node_id)
        if current is None or RANK[mode] > RANK[current]:
            self.modes[node_id] = mode


def fidelity_of(rules: Rules, mode: WitnessMode) -> int:
    table = rules.records
    return {
        WitnessMode.SAW: table.fidelity_saw,
        WitnessMode.TOOK_PART: table.fidelity_saw,
        WitnessMode.HEARD: table.fidelity_heard,
        WitnessMode.WAS_TOLD: table.fidelity_told,
        WitnessMode.SENSED: table.fidelity_sensed,
    }[mode]


def within(atlas: RegionAtlas, region: int, radius: int) -> list[int]:
    found = {region}
    edge = [region]
    for _ in range(radius):
        edge = [other for current in edge for other in atlas.neighbours(current) if other not in found]
        found.update(edge)
    return sorted(found)


UNSIGHTED = 20


@dataclass
class Folk:
    at: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    affiliation: dict[int, int | None] = field(default_factory=dict)
    unsighted: set[int] = field(default_factory=set)


async def folk(session: AsyncSession) -> Folk:
    found = Folk()
    rows = await session.execute(
        select(EntityRow.id, EntityRow.location_id, EntityRow.affiliated_entity_id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal, location, affiliation in rows:
        if location is not None:
            found.at[location].append(mortal)
        found.affiliation[mortal] = affiliation
    found.unsighted = set(await session.scalars(select(BodyRow.node_id).where(BodyRow.sight < UNSIGHTED)))
    return found


@dataclass
class Gods:
    creator: int | None
    attention: dict[int, tuple[int, bool]]
    sons: list[int]
    made_by: dict[int, int]
    worshipping: dict[int, set[int]]


async def gods(session: AsyncSession) -> Gods:
    creator = await session.scalar(select(CreatorRow.id).order_by(CreatorRow.id).limit(1))
    attention = {row.world_id: (row.attention, row.watched) for row in await session.scalars(select(WorldAttentionRow).order_by(WorldAttentionRow.world_id))}
    sons = list(await session.scalars(select(SonRow.id).where(SonRow.status.in_([SonStatus.ACTIVE, SonStatus.ASLEEP, SonStatus.EXILED])).order_by(SonRow.id)))
    made = await session.execute(
        select(EntityRow.id, EntityRow.creator_son_id)
        .where(EntityRow.creator_son_id.is_not(None), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    worship: dict[int, set[int]] = defaultdict(set)
    if sons:
        bonds = await session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id)
            .where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(sons))
            .order_by(BondRow.id)
        )
        for source, target in bonds:
            worship[source].add(target)
    return Gods(creator, attention, sons, {entity: son for entity, son in made if son is not None}, worship)


def god_witnesses(scene: Gods, incident: IncidentRow, involved: Iterable[int], seen: Seen) -> None:
    if scene.creator is not None and incident.world_id is not None:
        attention, watched = scene.attention.get(incident.world_id, (0, False))
        if watched or incident.magnitude >= PERCENT - attention:
            seen.add(scene.creator, WitnessMode.SAW)
    for node in involved:
        son = scene.made_by.get(node)
        if son is not None:
            seen.add(son, WitnessMode.SAW)
        for patron in scene.worshipping.get(node, ()):
            seen.add(patron, WitnessMode.SAW)


def scene_of(atlas: RegionAtlas, incident: IncidentRow, cast: list[IncidentParticipantRow]) -> int | None:
    if incident.place_entity_id is not None:
        return incident.place_entity_id
    for row in cast:
        if row.role is IncidentRole.PLACE:
            return row.node_id
    for row in cast:
        if atlas.top_region(row.node_id) is not None:
            return row.node_id
    return None


def present(atlas: RegionAtlas, people: Folk, place: int, involved: set[int], *, radius: int | None, seen: Seen) -> None:
    region = atlas.top_region(place)
    if radius is None:
        near = [place] if region is not None and place in atlas.communities_in(region) else []
    else:
        near = [community for other in within(atlas, region, radius) for community in atlas.communities_in(other)] if region is not None else []
    for community in near:
        seen.add(community, WitnessMode.SAW if community == place else WitnessMode.HEARD)
    for mortal in people.at.get(place, ()):
        affiliation = people.affiliation.get(mortal)
        sensed = WitnessMode.SENSED if mortal in people.unsighted else WitnessMode.SAW
        seen.add(mortal, WitnessMode.TOOK_PART if affiliation is not None and affiliation in involved else sensed)


def told(kind: str) -> bool:
    spec = INCIDENT_KINDS.get(kind)
    return spec is None or spec.told


PRESENT = having(WITNESS_MODE_TRAITS, WitnessModeTrait.FIRST_HAND)


async def born_keys(session: AsyncSession) -> dict[int, tuple[int, int, int, int]]:
    rows = await session.execute(select(NodeBirthRow.node_id, NodeBirthRow.year, NodeBirthRow.season, NodeBirthRow.day, NodeBirthRow.hour))
    return {int(node): (int(year), season or 0, day or 0, hour or 0) for node, year, season, day, hour in rows}


async def give_modes(ctx: TickContext, atlas: RegionAtlas) -> int:
    births = await born_keys(ctx.session)
    modeless = list(
        await ctx.session.execute(
            select(IncidentParticipantRow, IncidentRow.place_entity_id, IncidentRow.year, IncidentRow.season, IncidentRow.day, IncidentRow.hour)
            .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
            .where(
                IncidentParticipantRow.role == IncidentRole.WITNESS,
                IncidentParticipantRow.witness_mode.is_(None),
                IncidentRow.epoch >= ctx.epoch - 1,
            )
            .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
        )
    )
    for row, place, year, season, day, hour in modeless:
        unborn = year is not None and row.node_id in births and births[row.node_id] > (year, season or 0, day or 0, hour or 0)
        mode = WitnessMode.SAW if not unborn and (place is None or atlas.holds(place, row.node_id)) else WitnessMode.HEARD
        row.witness_mode = mode
        row.fidelity = fidelity_of(ctx.rules, mode)
    return len(modeless)


async def choose_witnesses(ctx: TickContext, atlas: RegionAtlas) -> int:
    await give_modes(ctx, atlas)
    incidents = [
        row
        for row in await ctx.session.scalars(
            select(IncidentRow).where(IncidentRow.epoch >= ctx.epoch - 1, IncidentRow.epoch <= ctx.epoch).order_by(IncidentRow.id)
        )
        if told(row.kind)
    ]
    if not incidents:
        return 0
    ids = [row.id for row in incidents]
    casts: dict[int, list[IncidentParticipantRow]] = defaultdict(list)
    for start in range(0, len(ids), 500):
        statement = select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id.in_(ids[start : start + 500]))
        for row in await ctx.session.scalars(statement.order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position)):
            casts[row.incident_id].append(row)
    people = await folk(ctx.session)
    scene_gods = await gods(ctx.session)
    births = await born_keys(ctx.session)
    radius = ctx.rules.records.witness_radius
    loud = ctx.rules.rumours.min_magnitude
    made = 0
    chosen: list[dict[str, object]] = []
    for incident in incidents:
        if HELD_PART in (incident.locked or []):
            continue
        cast = casts[incident.id]
        taken = {(row.node_id, row.role) for row in cast}
        involved = {row.node_id for row in cast if row.role is not IncidentRole.WITNESS}
        seen = Seen()
        place = scene_of(atlas, incident, cast)
        if place is not None:
            present(atlas, people, place, involved, radius=radius if incident.magnitude >= loud else None, seen=seen)
        god_witnesses(scene_gods, incident, involved, seen)
        position = max((row.position for row in cast), default=-1) + 1
        moment = (incident.year, incident.season or 0, incident.day or 0, incident.hour or 0) if incident.year is not None else None
        for node, mode in sorted(seen.modes.items()):
            if node in involved or (node, IncidentRole.WITNESS) in taken or held(node):
                continue
            if mode in PRESENT and moment is not None and node in births and births[node] > moment:
                continue
            chosen.append(
                {
                    "incident_id": incident.id,
                    "node_id": node,
                    "role": IncidentRole.WITNESS,
                    "position": position,
                    "witness_mode": mode,
                    "fidelity": fidelity_of(ctx.rules, mode),
                }
            )
            position += 1
            made += 1
    await ctx.session.flush()
    for start in range(0, len(chosen), WITNESS_BATCH):
        await ctx.session.execute(insert(IncidentParticipantRow), chosen[start : start + WITNESS_BATCH])
    return made


async def tell(session: AsyncSession, incident_id: int, teller: int, audience: Iterable[int], rules: Rules) -> int:
    existing = {
        (node, role)
        for node, role in await session.execute(
            select(IncidentParticipantRow.node_id, IncidentParticipantRow.role).where(IncidentParticipantRow.incident_id == incident_id)
        )
    }
    position = (
        int(
            await session.scalar(
                select(IncidentParticipantRow.position)
                .where(IncidentParticipantRow.incident_id == incident_id)
                .order_by(IncidentParticipantRow.position.desc())
                .limit(1)
            )
            or 0
        )
        + 1
    )
    made = 0
    if (teller, IncidentRole.TELLER) not in existing and not held(teller):
        session.add(IncidentParticipantRow(incident_id=incident_id, node_id=teller, role=IncidentRole.TELLER, position=position))
        position += 1
        made += 1
    for node in sorted(set(audience) - {teller}):
        if (node, IncidentRole.WITNESS) in existing or held(node):
            continue
        session.add(
            IncidentParticipantRow(
                incident_id=incident_id,
                node_id=node,
                role=IncidentRole.WITNESS,
                position=position,
                witness_mode=WitnessMode.WAS_TOLD,
                fidelity=fidelity_of(rules, WitnessMode.WAS_TOLD),
            )
        )
        position += 1
        made += 1
    await session.flush()
    return made
