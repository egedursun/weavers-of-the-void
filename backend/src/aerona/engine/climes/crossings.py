from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.climes import CosmopolitanCultureRow, CosmopolitanMemberRow, LaunchWindowRow
from aerona.db.tables.culture import SpeakerCohortRow
from aerona.db.tables.discovery import ArtFormPractitionerRow, ArtFormProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import ArtMode, SpeakerKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import ArtFormStats
from aerona.engine.body.customs import people_of
from aerona.engine.climes.windows import PHYSICAL, opens, pair
from aerona.engine.context import TickContext
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.recording.record import record as record_incident
from aerona.language.generator import NameKind

DAYS = 365


@dataclass
class CrossingTally:
    windows: int = 0
    open_windows: int = 0
    cultures: int = 0
    members: int = 0
    speakers: int = 0


def synodic_of(rules_min: int, rules_max: int, first: WorldRow, second: WorldRow, years_per_epoch: int) -> int:
    one, two = first.year_length_days or DAYS, second.year_length_days or DAYS
    if one == two:
        return rules_max
    days = one * two / abs(one - two)
    return clamp_int(round_half_up(days / (min(one, two) * max(1, years_per_epoch))), rules_min, rules_max)


async def keep_windows(ctx: TickContext, tally: CrossingTally) -> None:
    table = ctx.rules.launch_windows
    worlds = {row.id: row for row in await ctx.session.scalars(select(WorldRow))}
    routes = await ctx.session.scalars(select(RouteRow).where(RouteRow.method.in_(PHYSICAL)).order_by(RouteRow.id))
    for route in list(routes):
        key = pair(route.world_a_id, route.world_b_id)
        if key[0] not in worlds or key[1] not in worlds or held(key[0]) or held(key[1]):
            continue
        row = await ctx.session.get(LaunchWindowRow, key)
        if row is None:
            synodic = synodic_of(table.synodic_min, table.synodic_max, worlds[key[0]], worlds[key[1]], ctx.rules.time.years_per_epoch)
            offset = ctx.rng(seed_of("window", *key)).below(synodic)
            row = LaunchWindowRow(from_world_id=key[0], to_world_id=key[1], synodic=synodic, offset=offset, locked=[])
            ctx.session.add(row)
        if "open" not in row.locked:
            row.open = opens(row, ctx.epoch)
        tally.windows += 1
        tally.open_windows += int(row.open)
    await ctx.session.flush()


async def travellers_of(ctx: TickContext, route_id: int) -> list[int]:
    rows = await ctx.session.scalars(select(JourneyRow.traveller_entity_id).where(JourneyRow.route_id == route_id).order_by(JourneyRow.id))
    found: list[int] = []
    for traveller in rows:
        entity = await ctx.session.get(EntityRow, traveller)
        home = await community_of(ctx, entity) if entity is not None and entity.status is EntityStatus.CANON else None
        if home is not None and home not in found:
            found.append(home)
    return found


async def community_of(ctx: TickContext, entity: EntityRow) -> int | None:
    if entity.entity_type in COMMUNITY_TYPES:
        return entity.id
    home = await ctx.session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
    return home.id if home is not None and home.status is EntityStatus.CANON and home.entity_type in COMMUNITY_TYPES else None


async def values_of(ctx: TickContext, members: list[int]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    for member in members:
        entity = await ctx.session.get(EntityRow, member)
        folk = await people_of(ctx.session, entity) if entity is not None else None
        if folk is None:
            continue
        for row in await ctx.session.scalars(select(CultureValueRow).where(CultureValueRow.entity_id == folk.id)):
            totals[row.axis.value] += row.value
            counts[row.axis.value] += 1
    return {axis: round_half_up(totals[axis] / counts[axis]) for axis in sorted(totals)}


async def found_culture(ctx: TickContext, route: RouteRow, tally: CrossingTally) -> None:
    members = await travellers_of(ctx, route.id)
    if len(members) < 2:
        return
    tongues: Counter[int] = Counter()
    for member in members:
        tongue = await spoken_language(ctx.session, member)
        if tongue is not None:
            tongues[tongue.id] += 1
    lingua = tongues.most_common(1)[0][0] if tongues else None
    name = await Namer(ctx.session, ctx.rules).from_speaker(members[0], seed_of("cosmopolitan", route.id), NameKind.PEOPLE)
    first, second = await ctx.session.get(WorldRow, route.world_a_id), await ctx.session.get(WorldRow, route.world_b_id)
    called = name or f"The folk of the road between {first.name if first else 'one world'} and {second.name if second else 'another'}"
    culture = CosmopolitanCultureRow(
        route_id=route.id, name=called, lingua_franca_entity_id=lingua, values=await values_of(ctx, members), formed_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(culture)
    await ctx.session.flush()
    for member in members:
        ctx.session.add(
            CosmopolitanMemberRow(culture_id=culture.id, community_entity_id=member, share=ctx.rules.cosmopolitan.join_share, joined_epoch=ctx.epoch, locked=[])
        )
    tally.cultures += 1
    await found_art(ctx, called, members)
    await record_incident(ctx, "cosmopolitan.formed", roles={IncidentRole.MEMBER: list(members)}, facts={"culture": called})


async def found_art(ctx: TickContext, called: str, members: list[int]) -> None:
    first = await ctx.session.get(EntityRow, members[0])
    if first is None:
        return
    folk = await people_of(ctx.session, first)
    discipline = ctx.rng(seed_of("road.art", members[0], ctx.epoch)).pick(list(ArtMode))
    art = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.ART_FORM,
            name=f"The art of {called}",
            body=f"An art the travellers of {called} made their own on the road between worlds.",
            stats=ArtFormStats(),
            power=1,
            world_id=first.world_id,
            subtype="art of the road",
        ),
    )
    ctx.session.add(ArtFormProfileRow(art_form_entity_id=art.id, discipline=discipline, origin_culture_id=folk.id if folk is not None else None, locked=[]))
    for member in members:
        ctx.session.add(ArtFormPractitionerRow(art_form_entity_id=art.id, practitioner_entity_id=member, since_epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()


async def road_belonging(session: AsyncSession, people_id: int) -> int:
    towns = await towns_of_people(session, people_id)
    found = await session.scalar(
        select(func.max(CosmopolitanMemberRow.share)).where(
            or_(CosmopolitanMemberRow.community_entity_id == people_id, CosmopolitanMemberRow.community_entity_id.in_(towns))
        )
    )
    return int(found or 0)


async def pull_values(ctx: TickContext, culture: CosmopolitanCultureRow, member: CosmopolitanMemberRow) -> None:
    entity = await ctx.session.get(EntityRow, member.community_entity_id)
    folk = await people_of(ctx.session, entity) if entity is not None else None
    if folk is None or held(folk.id):
        return
    pull = ctx.rules.cosmopolitan.value_pull_pct / PERCENT * member.share / PERCENT
    for axis, target in culture.values.items():
        row = await ctx.session.get(CultureValueRow, (folk.id, ValueAxis(axis)))
        if row is not None:
            row.value = clamp_int(row.value + round_half_up((int(target) - row.value) * pull), -PERCENT, PERCENT)


async def speak_lingua(ctx: TickContext, culture: CosmopolitanCultureRow, member: CosmopolitanMemberRow, tally: CrossingTally) -> None:
    lingua = culture.lingua_franca_entity_id
    if lingua is None or member.share < ctx.rules.cosmopolitan.lingua_share:
        return
    row = await ctx.session.get(SpeakerCohortRow, (member.community_entity_id, lingua, SpeakerKind.SECOND))
    if row is None:
        native = await ctx.session.get(SpeakerCohortRow, (member.community_entity_id, lingua, SpeakerKind.NATIVE))
        if native is not None:
            return
        ctx.session.add(
            SpeakerCohortRow(
                community_entity_id=member.community_entity_id,
                language_entity_id=lingua,
                kind=SpeakerKind.SECOND,
                share=member.share,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.speakers += 1
    elif "share" not in row.locked:
        row.share = max(row.share, member.share)


async def keep_cultures(ctx: TickContext, tally: CrossingTally) -> None:
    table = ctx.rules.cosmopolitan
    known = set(await ctx.session.scalars(select(CosmopolitanCultureRow.route_id).where(CosmopolitanCultureRow.route_id.is_not(None))))
    busy = await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True), RouteRow.traffic >= table.traffic_from).order_by(RouteRow.id))
    busy_ids = set()
    for route in list(busy):
        busy_ids.add(route.id)
        if route.id not in known and not held(route.world_a_id) and not held(route.world_b_id):
            await found_culture(ctx, route, tally)
    for culture in list(await ctx.session.scalars(select(CosmopolitanCultureRow).order_by(CosmopolitanCultureRow.id))):
        members = list(await ctx.session.scalars(select(CosmopolitanMemberRow).where(CosmopolitanMemberRow.culture_id == culture.id)))
        for member in members:
            if held(member.community_entity_id):
                continue
            if "share" not in member.locked:
                step = table.share_gain if culture.route_id in busy_ids else -table.share_fade
                member.share = clamp_int(member.share + step, 0, PERCENT)
            await pull_values(ctx, culture, member)
            await speak_lingua(ctx, culture, member, tally)
            tally.members += 1
    await ctx.session.flush()
