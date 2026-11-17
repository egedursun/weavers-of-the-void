from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import LEGEND_MORALS
from aerona.catalog.rumours import is_alarm, is_atrocity, is_quiet, legend_archetype
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import LanguageStandingRow, LegendProfileRow, RumourRow
from aerona.db.tables.customs import TavernRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import RumourChannel
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.travel import JourneyStatus
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.climes.shifts import current_coasts
from aerona.engine.context import TickContext
from aerona.engine.cosmos.commerce import news_delay
from aerona.engine.customs.relief import tavern_of
from aerona.engine.folkways.biases import lean_community
from aerona.engine.lore.language import barrier
from aerona.engine.lore.printing import printed
from aerona.engine.mind.memories import remember
from aerona.engine.networks.book import reach_pct
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity, load_entities, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.services.community_relations import change_relation

CARRIER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.POLITY})
CULPRIT_TYPES = frozenset({*CARRIER_TYPES, EntityType.MORTAL, EntityType.ARMY})
LOUD_ROLES = (IncidentRole.ACTOR, IncidentRole.SUBJECT, IncidentRole.TARGET)
HELD = "fidelity"
RUMOUR_FIXUP = "lore.rumours_backfill"
PLANTED_KIND = "rumour.planted"
PLANTED_ATROCITY = "rumour.planted_atrocity"
FRESH_EPOCHS = 1
LEGEND_POWER = 2
UNKNOWN_FAR = 20
LOAD_CHUNK = 500


@dataclass
class Links:
    routes: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    pilgrims: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    journeys: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    spies: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    currents: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))

    def of(self, carrier: int) -> list[tuple[int, RumourChannel]]:
        found: dict[int, RumourChannel] = {}
        for channel, table in (
            (RumourChannel.SPY, self.spies),
            (RumourChannel.ROUTE, self.routes),
            (RumourChannel.JOURNEY, self.journeys),
            (RumourChannel.PILGRIMAGE, self.pilgrims),
            (RumourChannel.CURRENT, self.currents),
        ):
            for target in sorted(table.get(carrier, set())):
                found.setdefault(target, channel)
        return sorted(found.items())


async def is_carrier(session: AsyncSession, entity_id: int | None) -> EntityRow | None:
    entity = await living_entity(session, entity_id)
    return entity if entity is not None and entity.entity_type in CARRIER_TYPES else None


async def participants(session: AsyncSession, incident_id: int) -> list[IncidentParticipantRow]:
    rows = await session.scalars(
        select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident_id).order_by(IncidentParticipantRow.position)
    )
    return list(rows)


async def fresh_incidents(ctx: TickContext, since: int | None = None) -> list[IncidentRow]:
    rows = await ctx.session.scalars(
        select(IncidentRow)
        .outerjoin(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .where(
            IncidentRow.epoch >= (ctx.epoch if since is None else since),
            IncidentRow.epoch <= ctx.epoch,
            IncidentRow.magnitude >= ctx.rules.rumours.min_magnitude,
            ChronicleRow.visible.is_not(False),
        )
        .order_by(IncidentRow.id)
    )
    return [row for row in rows if not is_quiet(row.kind)]


async def casts_of(session: AsyncSession, incidents: list[IncidentRow]) -> dict[int, list[IncidentParticipantRow]]:
    found: dict[int, list[IncidentParticipantRow]] = {incident.id: [] for incident in incidents}
    for start in range(0, len(incidents), LOAD_CHUNK):
        chunk = [incident.id for incident in incidents[start : start + LOAD_CHUNK]]
        statement = select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id.in_(chunk))
        for row in await session.scalars(statement.order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position)):
            found[row.incident_id].append(row)
    return found


async def witnesses(ctx: TickContext, incident: IncidentRow, atlas: RegionAtlas, cast: list[IncidentParticipantRow] | None = None) -> list[int]:
    found: set[int] = set()
    for row in cast if cast is not None else await participants(ctx.session, incident.id):
        entity = await living_entity(ctx.session, row.node_id)
        if entity is None:
            continue
        if entity.entity_type in CARRIER_TYPES:
            found.add(entity.id)
        elif await is_carrier(ctx.session, entity.location_id) is not None:
            found.add(entity.location_id or 0)
    place = await living_entity(ctx.session, incident.place_entity_id)
    if place is not None and place.entity_type in CARRIER_TYPES:
        found.add(place.id)
    if not found and incident.place_entity_id is not None:
        region = atlas.top_region(incident.place_entity_id)
        if region is not None:
            found.update(atlas.communities_in(region))
    return sorted(found - {0})


async def known_pairs(session: AsyncSession, incident_ids: list[int]) -> set[tuple[int, int]]:
    if not incident_ids:
        return set()
    rows = await session.execute(select(RumourRow.incident_id, RumourRow.carrier_entity_id).where(RumourRow.incident_id.in_(incident_ids)))
    return {(incident, carrier) for incident, carrier in rows.all()}


async def seed(ctx: TickContext, atlas: RegionAtlas, since: int | None = None) -> int:
    incidents = await fresh_incidents(ctx, since)
    known = await known_pairs(ctx.session, [row.id for row in incidents])
    casts = await casts_of(ctx.session, incidents)
    cast = await load_entities(ctx.session, [*(row.node_id for rows in casts.values() for row in rows), *(incident.place_entity_id for incident in incidents)])
    await load_entities(ctx.session, [entity.location_id for entity in cast])
    made = 0
    for incident in incidents:
        age = max(0, ctx.epoch - incident.epoch)
        for carrier in await witnesses(ctx, incident, atlas, casts[incident.id]):
            if (incident.id, carrier) in known or held(carrier) or await is_carrier(ctx.session, carrier) is None:
                continue
            ctx.session.add(
                RumourRow(
                    incident_id=incident.id,
                    carrier_entity_id=carrier,
                    channel=RumourChannel.WITNESS,
                    fidelity=clamp_int(PERCENT - age * ctx.rules.rumours.linger_decay, 0, PERCENT),
                    hops=0,
                    epoch=incident.epoch,
                    lingered=age,
                    acted=False,
                    planted=False,
                    locked=[],
                )
            )
            known.add((incident.id, carrier))
            made += 1
    await ctx.session.flush()
    return made


async def backfill(ctx: TickContext, atlas: RegionAtlas) -> int:
    if await ctx.session.get(AppliedFixupRow, RUMOUR_FIXUP) is not None:
        return 0
    made = await seed(ctx, atlas, since=max(1, ctx.epoch - ctx.rules.rumours.backfill_epochs))
    ctx.session.add(AppliedFixupRow(key=RUMOUR_FIXUP, result={"rumours": made}))
    await ctx.session.flush()
    return made


async def links(ctx: TickContext) -> Links:
    found = Links()
    roads = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE)
    )
    for first, second in roads.all():
        found.routes[first].add(second)
        found.routes[second].add(first)
    for owner, target in (await ctx.session.execute(select(SpyNetworkRow.owner_entity_id, SpyNetworkRow.target_entity_id))).all():
        found.spies[target].add(owner)
    arrived = await ctx.session.scalars(
        select(JourneyRow).where(
            JourneyRow.status == JourneyStatus.ARRIVED,
            JourneyRow.end_epoch.is_not(None),
            JourneyRow.end_epoch >= ctx.epoch - FRESH_EPOCHS - ctx.rules.cosmography.intercluster_news_epochs,
        )
    )
    for journey in arrived:
        delay = news_delay(ctx.rules, journey.scope)
        if journey.end_epoch is None or not 0 <= ctx.epoch - journey.end_epoch - delay <= FRESH_EPOCHS:
            continue
        traveller = await living_entity(ctx.session, journey.traveller_entity_id)
        home = traveller.id if traveller is not None and traveller.entity_type in CARRIER_TYPES else traveller.location_id if traveller is not None else None
        if home is not None and journey.result_entity_id is not None and journey.result_entity_id != home:
            found.journeys[home].add(journey.result_entity_id)
            found.journeys[journey.result_entity_id].add(home)
    for coast, downstream in await current_coasts(ctx.session):
        found.currents[coast].add(downstream)
    return found


async def pilgrims_of(ctx: TickContext, carrier: EntityRow, cache: dict[int, list[int]]) -> set[int]:
    patron = await living_patron(ctx.session, carrier)
    if patron is None:
        return set()
    if patron.id not in cache:
        faithful = []
        for entity in await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.world_id == carrier.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(CARRIER_TYPES))
            )
        ):
            found = await living_patron(ctx.session, entity)
            if found is not None and found.id == patron.id:
                faithful.append(entity.id)
        cache[patron.id] = faithful
    return set(cache[patron.id]) - {carrier.id}


async def written(ctx: TickContext, community_id: int) -> float:
    culture = await ctx.session.get(PeopleCultureRow, community_id)
    letters = (culture.literacy if culture is not None else 0) / PERCENT
    tongue = await spoken_language(ctx.session, community_id)
    standing = await ctx.session.get(LanguageStandingRow, tongue.id) if tongue is not None else None
    settled = (standing.standardisation if standing is not None else 0) / PERCENT
    return max(letters, settled) * ctx.rules.rumours.written_pct / PERCENT


async def fidelity_after(ctx: TickContext, atlas: RegionAtlas, fidelity: int, *, source: int, target: int, channel: RumourChannel) -> int:
    table = ctx.rules.rumours
    hops = atlas.hops(source, target)
    understood = await barrier(ctx.session, ctx.rules, source, target, ctx.epoch)
    garble = ctx.rules.belief.distortion_rate * (1 - await written(ctx, target))
    garble *= await ctx.hook_factor(source, DomainHook.RUMOUR_TWIST)
    if await printed(ctx.session, target):
        garble *= 1 - ctx.rules.discovery.printed_rumour_pct / PERCENT
    loss = (
        table.hop_loss
        + table.distance_loss * min(UNKNOWN_FAR, hops if hops is not None else UNKNOWN_FAR)
        + round_half_up(table.barrier_loss * (1 - understood))
        + round_half_up(garble)
    )
    if channel is RumourChannel.SPY:
        loss -= table.spy_bonus
    return clamp_int(fidelity - max(0, loss), 0, PERCENT)


CHANCES = {
    RumourChannel.ROUTE: "route_chance",
    RumourChannel.PILGRIMAGE: "pilgrimage_chance",
    RumourChannel.JOURNEY: "journey_chance",
    RumourChannel.SPY: "spy_chance",
    RumourChannel.CURRENT: "current_chance",
}


async def spread(ctx: TickContext, atlas: RegionAtlas) -> dict[str, int]:
    table = ctx.rules.rumours
    counts = {channel.value: 0 for channel in CHANCES}
    found = await links(ctx)
    faithful: dict[int, list[int]] = {}
    fresh = list(
        await ctx.session.scalars(
            select(RumourRow)
            .where(RumourRow.epoch >= ctx.epoch - FRESH_EPOCHS, RumourRow.fidelity >= table.floor, RumourRow.hops < table.max_hops)
            .order_by(RumourRow.id)
        )
    )
    known = await known_pairs(ctx.session, sorted({row.incident_id for row in fresh}))
    passed = 0
    taverns: dict[int, TavernRow | None] = {}
    for rumour in fresh:
        carrier = await is_carrier(ctx.session, rumour.carrier_entity_id)
        if carrier is None:
            continue
        for community_id in await pilgrims_of(ctx, carrier, faithful):
            found.pilgrims[carrier.id].add(community_id)
        for target, channel in found.of(carrier.id):
            if passed >= table.cap or (rumour.incident_id, target) in known or held(carrier.id, target) or await is_carrier(ctx.session, target) is None:
                continue
            if target not in taverns:
                taverns[target] = await tavern_of(ctx.session, target)
            tavern = taverns[target]
            boost = (ctx.rules.taverns.rumour_pct if tavern is not None else 0) + await reach_pct(
                ctx.session, ctx.rules, target, ctx.epoch, kind="carries_opinion"
            )
            if not ctx.rng(f"rumour.{rumour.incident_id}.{carrier.id}.{target}.{ctx.epoch}").chance(int(getattr(table, CHANCES[channel])) + boost):
                continue
            if tavern is not None and "rumours" not in tavern.locked:
                tavern.rumours += 1
            fidelity = await fidelity_after(ctx, atlas, rumour.fidelity, source=carrier.id, target=target, channel=channel)
            if fidelity < table.floor:
                continue
            ctx.session.add(
                RumourRow(
                    incident_id=rumour.incident_id,
                    carrier_entity_id=target,
                    source_entity_id=carrier.id,
                    channel=channel,
                    fidelity=fidelity,
                    hops=rumour.hops + 1,
                    epoch=ctx.epoch,
                    lingered=0,
                    acted=False,
                    planted=rumour.planted,
                    locked=[],
                )
            )
            known.add((rumour.incident_id, target))
            counts[channel.value] += 1
            passed += 1
    await ctx.session.flush()
    return counts


async def culprit(ctx: TickContext, incident_id: int, hearer: int) -> int | None:
    rows = await participants(ctx.session, incident_id)
    ordered = sorted(rows, key=lambda row: (row.role is not IncidentRole.ACTOR, row.position))
    for row in ordered:
        if row.node_id == hearer or row.role not in LOUD_ROLES:
            continue
        entity = await living_entity(ctx.session, row.node_id)
        if entity is not None and entity.entity_type in CULPRIT_TYPES:
            return entity.id
    return None


async def enemies_of(ctx: TickContext, community_id: int) -> set[int]:
    mine = list(
        await ctx.session.execute(select(WarSideRow.war_id, WarSideRow.side).where(WarSideRow.entity_id == community_id, WarSideRow.left_epoch.is_(None)))
    )
    found: set[int] = set()
    for war_id, side in mine:
        others = await ctx.session.scalars(
            select(WarSideRow.entity_id).where(WarSideRow.war_id == war_id, WarSideRow.side != side, WarSideRow.left_epoch.is_(None))
        )
        found.update(others)
    return found


async def atrocity_heard(ctx: TickContext, rumour: RumourRow, incident: IncidentRow) -> bool:
    if rumour.channel is RumourChannel.WITNESS or not is_atrocity(incident.kind):
        return False
    doer = await culprit(ctx, incident.id, rumour.carrier_entity_id)
    if doer is None:
        return False
    size = -ctx.rules.rumours.atrocity_hatred * rumour.fidelity / PERCENT
    if not round_half_up(size):
        return False
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=rumour.carrier_entity_id,
        subject_id=doer,
        kind=MemoryKind.ILL_WILL,
        magnitude=size,
        epoch=ctx.epoch,
        note="heard tell of an atrocity",
    )
    return True


async def alarm(ctx: TickContext, atlas: RegionAtlas, rumour: RumourRow, incident: IncidentRow) -> int | None:
    table = ctx.rules.rumours
    if not is_alarm(incident.kind):
        return None
    hostile = await enemies_of(ctx, rumour.carrier_entity_id)
    if not hostile:
        return None
    named = {row.node_id for row in await participants(ctx.session, incident.id) if row.role in LOUD_ROLES}
    enemy = next((node for node in sorted(named) if node in hostile), None)
    if enemy is None:
        return None
    near = incident.place_entity_id if incident.place_entity_id is not None else enemy
    hops = atlas.hops(rumour.carrier_entity_id, near)
    if hops is None or hops > table.alarm_regions:
        return None
    weight = rumour.fidelity / PERCENT * await lean_community(ctx, rumour.carrier_entity_id, BiasedDecision.BELIEF)
    town = await living_entity(ctx.session, rumour.carrier_entity_id)
    if town is not None and stat(town, "defense") is not None:
        shift_stat(town, "defense", table.alarm_defense * weight)
    allies = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.ALLY,
            BondRow.state == BondState.ACTIVE,
            (BondRow.source_node_id == rumour.carrier_entity_id) | (BondRow.target_node_id == rumour.carrier_entity_id),
        )
    )
    for first, second in allies.all():
        ally = second if first == rumour.carrier_entity_id else first
        if ally == enemy:
            continue
        await change_relation(ctx, ally, rumour.carrier_entity_id, table.ally_call * weight, MemoryKind.GOODWILL, note="called to help against a coming army")
        await change_relation(ctx, ally, enemy, -table.ally_call * weight, MemoryKind.ILL_WILL, note="marches on our ally")
    return enemy


async def react(ctx: TickContext, atlas: RegionAtlas) -> dict[str, int]:
    counts = {"atrocities": 0, "alarms": 0}
    heard = list(await ctx.session.scalars(select(RumourRow).where(RumourRow.acted.is_(False)).order_by(RumourRow.id)))
    for rumour in heard:
        rumour.acted = True
        incident = await ctx.session.get(IncidentRow, rumour.incident_id)
        if incident is None or held(rumour.carrier_entity_id) or await is_carrier(ctx.session, rumour.carrier_entity_id) is None:
            continue
        counts["atrocities"] += int(await atrocity_heard(ctx, rumour, incident))
        enemy = await alarm(ctx, atlas, rumour, incident)
        if enemy is not None:
            counts["alarms"] += 1
            hearer = await ctx.session.get(EntityRow, rumour.carrier_entity_id)
            foe = await ctx.session.get(EntityRow, enemy)
            if hearer is not None and foe is not None:
                await note(
                    ctx,
                    f"Word reached {hearer.name} that the host of {foe.name} was near; they made ready and called on their friends.",
                    key="rumour.alarm",
                    ids=[hearer.id, foe.id],
                )
    return counts


async def linger(ctx: TickContext) -> int:
    old = list(await ctx.session.scalars(select(RumourRow).where(RumourRow.epoch < ctx.epoch, RumourRow.fidelity > 0)))
    for rumour in old:
        rumour.lingered += 1
        if HELD not in rumour.locked:
            rumour.fidelity = clamp_int(rumour.fidelity - ctx.rules.rumours.linger_decay, 0, PERCENT)
    return len(old)


async def subject_of(ctx: TickContext, incident: IncidentRow) -> EntityRow | None:
    for row in await participants(ctx.session, incident.id):
        if row.role is IncidentRole.PLACE:
            continue
        entity = await ctx.session.get(EntityRow, row.node_id)
        if entity is not None:
            return entity
    return await ctx.session.get(EntityRow, incident.place_entity_id) if incident.place_entity_id is not None else None


async def harden(ctx: TickContext, incident: IncidentRow, rumours: list[RumourRow]) -> EntityRow | None:
    table = ctx.rules.rumours
    garbled = [row for row in rumours if row.fidelity <= table.legend_fidelity and row.lingered >= table.legend_epochs]
    tellers = sorted({row.carrier_entity_id for row in garbled})
    if len(tellers) < table.legend_tellers:
        return None
    home = await is_carrier(ctx.session, tellers[0])
    if home is None:
        return None
    subject = await subject_of(ctx, incident)
    archetype = legend_archetype(incident.kind)
    title = subject.name if subject is not None else home.name
    legend = await create_record(
        ctx,
        RecordSpec(
            name=f"The Tale of {title}",
            entity_type=EntityType.LEGEND,
            stats=LegendStats(spread=clamp_int(len(tellers) * 10, 0, PERCENT)),
            body=f"What is told of {title}, garbled in the telling from what truly happened.",
            power=LEGEND_POWER,
            world_id=home.world_id,
            location_id=home.id,
        ),
    )
    fidelity = sum(row.fidelity for row in garbled) / len(garbled)
    ctx.session.add(
        LegendProfileRow(
            legend_entity_id=legend.id,
            archetype=archetype,
            credence=clamp_int(len(tellers) * ctx.rules.belief.credence_per_teller * 5, 0, PERCENT),
            distortion=clamp_int(PERCENT - round_half_up(fidelity), 0, PERCENT),
            source_incident_id=incident.id,
            subject_node_id=subject.id if subject is not None else None,
            moral={axis.value: value for axis, value in LEGEND_MORALS[archetype].items()},
            tellers=tellers,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    if subject is not None:
        await connect(ctx.session, legend.id, subject.id, BondKind.TELLS_OF, ctx.epoch, description="the tale is of")
    for teller in tellers:
        await connect(ctx.session, teller, legend.id, BondKind.CELEBRATES, ctx.epoch, description="tells the tale")
    for row in rumours:
        row.legend_entity_id = legend.id
    return legend


async def legends(ctx: TickContext) -> list[EntityRow]:
    table = ctx.rules.rumours
    candidates = list(
        await ctx.session.scalars(
            select(RumourRow)
            .where(RumourRow.legend_entity_id.is_(None), RumourRow.lingered >= table.legend_epochs)
            .order_by(RumourRow.incident_id, RumourRow.id)
        )
    )
    by_incident: dict[int, list[RumourRow]] = defaultdict(list)
    for row in candidates:
        by_incident[row.incident_id].append(row)
    made = []
    for incident_id, rows in sorted(by_incident.items()):
        incident = await ctx.session.get(IncidentRow, incident_id)
        if incident is None:
            continue
        legend = await harden(ctx, incident, rows)
        if legend is not None:
            made.append(legend)
            await note(ctx, f"Garbled in the retelling, word of old deeds hardened into {legend.name}.", key="rumour.legend", ids=[legend.id])
    return made


async def heard_by(session: AsyncSession, community_id: int) -> list[tuple[RumourRow, IncidentRow, str]]:
    rows = await session.execute(
        select(RumourRow, IncidentRow, ChronicleRow.text)
        .join(IncidentRow, IncidentRow.id == RumourRow.incident_id)
        .outerjoin(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .where(RumourRow.carrier_entity_id == community_id)
        .order_by(RumourRow.fidelity.desc(), RumourRow.epoch.desc(), RumourRow.id)
    )
    return [(rumour, incident, text or incident.note or incident.kind.replace(".", " ")) for rumour, incident, text in rows.all()]


async def plant(
    ctx: TickContext, carrier_id: int, *, incident_id: int | None, subject_id: int | None, text: str, fidelity: int, atrocity: bool = False
) -> RumourRow:
    carrier = await is_carrier(ctx.session, carrier_id)
    if carrier is None:
        raise NotFoundError("No such living community to whisper to.")
    if not 0 <= fidelity <= PERCENT:
        raise ValidationFailedError(f"Fidelity runs from 0 to {PERCENT}.")
    incident = await ctx.session.get(IncidentRow, incident_id) if incident_id is not None else None
    if incident_id is not None and incident is None:
        raise NotFoundError("No such happening.")
    if incident is None:
        subject = await living_entity(ctx.session, subject_id) if subject_id is not None else None
        if subject is None or not text.strip():
            raise ValidationFailedError("Name whom the rumour is about and what it says.")
        incident = IncidentRow(
            kind=PLANTED_ATROCITY if atrocity else PLANTED_KIND,
            epoch=max(1, ctx.epoch),
            world_id=carrier.world_id,
            place_entity_id=carrier.id,
            note=text.strip(),
            magnitude=ctx.rules.rumours.min_magnitude,
        )
        ctx.session.add(incident)
        await ctx.session.flush()
        ctx.session.add(IncidentParticipantRow(incident_id=incident.id, node_id=subject.id, role=IncidentRole.ACTOR, position=0))
    existing = await ctx.session.scalar(select(RumourRow).where(RumourRow.incident_id == incident.id, RumourRow.carrier_entity_id == carrier.id))
    if existing is not None:
        existing.fidelity, existing.planted, existing.acted = fidelity, True, False
        existing.locked = sorted({*existing.locked, HELD})
        await ctx.session.flush()
        return existing
    row = RumourRow(
        incident_id=incident.id,
        carrier_entity_id=carrier.id,
        channel=RumourChannel.PLANTED,
        fidelity=fidelity,
        hops=0,
        epoch=max(1, ctx.epoch),
        lingered=0,
        acted=False,
        planted=True,
        locked=[HELD],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit(ctx: TickContext, rumour_id: int, *, fidelity: int | None, release: bool) -> RumourRow:
    row = await ctx.session.get(RumourRow, rumour_id)
    if row is None:
        raise NotFoundError("No such rumour.")
    if fidelity is not None:
        if not 0 <= fidelity <= PERCENT:
            raise ValidationFailedError(f"Fidelity runs from 0 to {PERCENT}.")
        row.fidelity = fidelity
        row.locked = sorted({*row.locked, HELD})
    if release:
        row.locked = [key for key in row.locked if key != HELD]
    await ctx.session.flush()
    return row


async def suppress(ctx: TickContext, rumour_id: int, *, everywhere: bool) -> int:
    row = await ctx.session.get(RumourRow, rumour_id)
    if row is None:
        raise NotFoundError("No such rumour.")
    rows = list(await ctx.session.scalars(select(RumourRow).where(RumourRow.incident_id == row.incident_id))) if everywhere else [row]
    for item in rows:
        await ctx.session.delete(item)
    await ctx.session.flush()
    return len(rows)
