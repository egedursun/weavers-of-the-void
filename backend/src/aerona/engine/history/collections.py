from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.gatherings import INCIDENT_ROLES, KEY_COLLECTIONS, KEY_PREFIX_COLLECTIONS, NEST_PARENTS
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.life.history import SCHEME_COLLECTIONS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionMemberRow, CollectionPlaceRow, CollectionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.node import NodeRow
from aerona.db.write_guard import held
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.intrigue import SchemePhase
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import PunishmentKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import stat_or

TEN_THOUSAND = 10000
NAMED_ROLES = (CollectionRole.LEADER, CollectionRole.HOST, CollectionRole.FOUNDER, CollectionRole.MEMBER, CollectionRole.VICTIM, CollectionRole.ACCUSED)


@dataclass
class CollectionTally:
    opened: int = 0
    joined: int = 0
    nested: int = 0
    closed: int = 0


def spoken(kind: CollectionKind) -> str:
    return kind.value.replace("_", " ")


def kind_of_key(key: str) -> CollectionKind | None:
    spec = INCIDENT_KINDS.get(key)
    found = spec.collection if spec is not None and spec.collection is not None else KEY_COLLECTIONS.get(key)
    if found is not None:
        return found
    return next((kind for prefix, kind in KEY_PREFIX_COLLECTIONS.items() if key.startswith(prefix)), None)


async def names_of(ctx: TickContext, ids: Iterable[int]) -> dict[int, str]:
    wanted = sorted(set(ids))
    if not wanted:
        return {}
    return {row.id: row.name for row in await ctx.session.scalars(select(NodeRow).where(NodeRow.id.in_(wanted)))}


async def title_for(ctx: TickContext, kind: CollectionKind, members: Mapping[int, CollectionRole], places: Iterable[int]) -> str:
    places = list(places)
    named = [node for role in NAMED_ROLES for node, given in members.items() if given is role]
    names = await names_of(ctx, [*named[:2], *places[:1]])
    label = spoken(kind).capitalize()
    leads = [names[node] for node in named[:2] if node in names]
    if leads:
        return f"{label} of {' and '.join(leads)}"
    if places and places[0] in names:
        return f"{label} at {names[places[0]]}"
    return label


def free_members(members: Mapping[int, CollectionRole]) -> dict[int, CollectionRole]:
    return {node: role for node, role in members.items() if not held(node)}


async def add_members(ctx: TickContext, collection: CollectionRow, members: Mapping[int, CollectionRole]) -> None:
    present = set(await ctx.session.scalars(select(CollectionMemberRow.node_id).where(CollectionMemberRow.collection_id == collection.id)))
    for node, role in free_members(members).items():
        if node not in present:
            ctx.session.add(CollectionMemberRow(collection_id=collection.id, node_id=node, role=role, since_epoch=ctx.epoch))
            present.add(node)


async def add_places(ctx: TickContext, collection: CollectionRow, places: Iterable[int]) -> None:
    present = set(await ctx.session.scalars(select(CollectionPlaceRow.place_entity_id).where(CollectionPlaceRow.collection_id == collection.id)))
    for place in places:
        if place not in present and not held(place) and await ctx.session.get(EntityRow, place) is not None:
            ctx.session.add(CollectionPlaceRow(collection_id=collection.id, place_entity_id=place))
            present.add(place)


async def open_collection(
    ctx: TickContext,
    kind: CollectionKind,
    *,
    world_id: int | None,
    members: Mapping[int, CollectionRole],
    places: Iterable[int] = (),
    name: str | None = None,
    source_key: str | None = None,
) -> CollectionRow | None:
    free = free_members(members)
    if not free or held(world_id):
        return None
    places = list(places)
    row = CollectionRow(
        kind=kind,
        name=name or await title_for(ctx, kind, free, places),
        world_id=world_id,
        start_epoch=ctx.epoch,
        source_key=source_key,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await add_members(ctx, row, free)
    await add_places(ctx, row, places)
    await nest(ctx, row, set(free))
    return row


async def open_of(ctx: TickContext, kinds: Iterable[CollectionKind], world_id: int | None, since: int) -> list[CollectionRow]:
    wanted = list(kinds)
    if not wanted:
        return []
    statement = select(CollectionRow).where(CollectionRow.kind.in_(wanted), CollectionRow.end_epoch.is_(None), CollectionRow.start_epoch >= since)
    if world_id is not None:
        statement = statement.where(CollectionRow.world_id == world_id)
    return list(await ctx.session.scalars(statement.order_by(CollectionRow.start_epoch.desc(), CollectionRow.id.desc())))


async def members_of(ctx: TickContext, collection_id: int) -> set[int]:
    return set(await ctx.session.scalars(select(CollectionMemberRow.node_id).where(CollectionMemberRow.collection_id == collection_id)))


async def nest(ctx: TickContext, row: CollectionRow, members: set[int]) -> bool:
    if row.parent_id is not None or "parent_id" in row.locked:
        return False
    since = ctx.epoch - ctx.rules.collections.join_window
    for parent in await open_of(ctx, NEST_PARENTS.get(row.kind, ()), row.world_id, since):
        if parent.id != row.id and members & await members_of(ctx, parent.id):
            row.parent_id = parent.id
            return True
    return False


async def join_or_open(
    ctx: TickContext,
    kind: CollectionKind,
    *,
    world_id: int | None,
    members: Mapping[int, CollectionRole],
    places: list[int],
    source_key: str,
    tally: CollectionTally,
) -> CollectionRow | None:
    since = ctx.epoch - ctx.rules.collections.join_window
    wanted = set(members)
    for found in await open_of(ctx, [kind], world_id, since):
        if found.locked and "members" in found.locked:
            continue
        if wanted & await members_of(ctx, found.id):
            await add_members(ctx, found, members)
            await add_places(ctx, found, places)
            tally.joined += 1
            return found
    opened = await open_collection(ctx, kind, world_id=world_id, members=members, places=places, source_key=source_key)
    if opened is not None:
        tally.opened += 1
        tally.nested += opened.parent_id is not None
    return opened


async def loose_incidents(ctx: TickContext) -> list[IncidentRow]:
    linked = select(CollectionIncidentRow.incident_id)
    return list(await ctx.session.scalars(select(IncidentRow).where(IncidentRow.epoch == ctx.epoch, IncidentRow.id.not_in(linked)).order_by(IncidentRow.id)))


async def participants(ctx: TickContext, incident_ids: list[int]) -> dict[int, dict[int, IncidentRole]]:
    found: dict[int, dict[int, IncidentRole]] = defaultdict(dict)
    if incident_ids:
        for row in await ctx.session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id.in_(incident_ids))):
            found[row.incident_id][row.node_id] = row.role
    return found


async def gather_incidents(ctx: TickContext, tally: CollectionTally) -> None:
    incidents = await loose_incidents(ctx)
    roles = await participants(ctx, [row.id for row in incidents])
    for incident in incidents:
        kind = kind_of_key(incident.kind)
        if kind is None:
            continue
        involved = roles.get(incident.id, {})
        members = {node: INCIDENT_ROLES[role] for node, role in involved.items() if role is not IncidentRole.PLACE}
        places = [node for node, role in involved.items() if role is IncidentRole.PLACE]
        if incident.place_entity_id is not None:
            places.append(incident.place_entity_id)
        if not members:
            continue
        found = await join_or_open(ctx, kind, world_id=incident.world_id, members=members, places=places, source_key=incident.kind, tally=tally)
        if found is not None:
            ctx.session.add(CollectionIncidentRow(collection_id=found.id, incident_id=incident.id))


async def from_schemes(ctx: TickContext, tally: CollectionTally) -> None:
    for scheme in await ctx.session.scalars(
        select(SchemeRow).where(SchemeRow.kind.in_(list(SCHEME_COLLECTIONS)), SchemeRow.phase == SchemePhase.SUCCEEDED, SchemeRow.ended_epoch == ctx.epoch)
    ):
        members = {scheme.owner_node_id: CollectionRole.LEADER}
        if scheme.target_node_id is not None:
            members[scheme.target_node_id] = CollectionRole.VICTIM
        owner = await ctx.session.get(EntityRow, scheme.owner_node_id)
        await join_or_open(
            ctx,
            SCHEME_COLLECTIONS[scheme.kind],
            world_id=owner.world_id if owner else None,
            members=members,
            places=[],
            source_key=f"scheme.{scheme.id}",
            tally=tally,
        )


async def from_purges(ctx: TickContext, tally: CollectionTally) -> None:
    deaths: Counter[int] = Counter()
    condemned: dict[int, list[int]] = defaultdict(list)
    for case in await ctx.session.scalars(
        select(CrimeCaseRow).where(
            CrimeCaseRow.closed_epoch == ctx.epoch, CrimeCaseRow.penalty == PunishmentKind.DEATH, CrimeCaseRow.polity_entity_id.is_not(None)
        )
    ):
        realm = case.polity_entity_id or 0
        deaths[realm] += 1
        if case.accused_entity_id is not None:
            condemned[realm].append(case.accused_entity_id)
    table = ctx.rules.collections
    for realm, count in sorted(deaths.items()):
        polity = await ctx.session.get(EntityRow, realm)
        subjects = stat_or(polity, "subjects", 0) if polity is not None else 0
        if count < max(table.purge_at, round(table.purge_per_ten_thousand * subjects / TEN_THOUSAND)):
            continue
        members = {realm: CollectionRole.LEADER, **{victim: CollectionRole.VICTIM for victim in condemned[realm]}}
        await join_or_open(
            ctx, CollectionKind.PURGE, world_id=polity.world_id if polity else None, members=members, places=[], source_key=f"purge.{realm}", tally=tally
        )


async def from_occupations(ctx: TickContext, tally: CollectionTally) -> None:
    for row in await ctx.session.scalars(select(OccupationRow).where(OccupationRow.since_epoch == ctx.epoch)):
        region = await ctx.session.get(EntityRow, row.region_entity_id)
        members = {row.occupier_entity_id: CollectionRole.LEADER}
        await join_or_open(
            ctx,
            CollectionKind.OCCUPATION,
            world_id=region.world_id if region else None,
            members=members,
            places=[row.region_entity_id],
            source_key=f"occupation.{row.region_entity_id}",
            tally=tally,
        )


async def close_quiet(ctx: TickContext, tally: CollectionTally) -> None:
    quiet = ctx.epoch - ctx.rules.collections.close_after
    for row in await ctx.session.scalars(select(CollectionRow).where(CollectionRow.end_epoch.is_(None), CollectionRow.start_epoch <= quiet)):
        if "end_epoch" in row.locked:
            continue
        last = await ctx.session.scalar(
            select(IncidentRow.epoch)
            .join(CollectionIncidentRow, CollectionIncidentRow.incident_id == IncidentRow.id)
            .where(CollectionIncidentRow.collection_id == row.id)
            .order_by(IncidentRow.epoch.desc())
            .limit(1)
        )
        ended = int(last) if last is not None else row.start_epoch
        if ended <= quiet:
            row.end_epoch = ended
            tally.closed += 1
