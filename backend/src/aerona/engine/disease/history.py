import re
from collections import Counter

from sqlalchemy import func, select

from aerona.catalog.life.demography import MINOR_BANDS
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.disease import EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.course import ENDEMIC_LOAD
from aerona.engine.disease.emergence import WET
from aerona.engine.disease.outbreaks import disease_for, tally
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import stat

PLAGUE_FIXUP = "disease.plague_history"
LIVES_LOST = re.compile(r"(\d+) lives lost")
ENDEMIC_REPEATS = 2


def faded(rules_keep: float, value: float, epochs: int) -> int:
    return clamp_int(value * rules_keep ** max(0, epochs), 0, PERCENT)


async def past_dead(ctx: TickContext, event: EntityRow) -> tuple[int, list[int]]:
    dead = int(await ctx.session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.death_event_entity_id == event.id)) or 0)
    struck: list[int] = []
    for bond in await ctx.session.scalars(select(BondRow).where(BondRow.source_node_id == event.id, BondRow.kind == BondKind.CAUSED).order_by(BondRow.id)):
        found = LIVES_LOST.search(bond.description or "")
        dead += int(found.group(1)) if found else 0
        struck.append(bond.target_node_id)
    return dead, struck


async def event_incident(ctx: TickContext, event: EntityRow) -> int | None:
    statement = (
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentParticipantRow.node_id == event.id)
        .order_by(IncidentRow.epoch, IncidentRow.id)
        .limit(1)
    )
    return await ctx.session.scalar(statement)


async def remember_immunity(ctx: TickContext, book: DiseaseBook, community: EntityRow, disease_id: int, since: int) -> int:
    table = ctx.rules.epidemiology
    profile = book.profiles.get(disease_id)
    keep = 1 - 1 / max(1, profile.immunity_epochs if profile is not None else 1)
    elapsed = ctx.epoch - since
    made = 0
    rows = book.immunity.setdefault((community.id, disease_id), {})
    for band in AgeBand:
        start = table.backfill_immunity_pct * (1 - table.child_immunity_loss_pct / PERCENT if band in MINOR_BANDS else 1)
        value = faded(keep, start, elapsed)
        if value <= 0:
            continue
        row = rows.get(band) or await ctx.session.get(ImmunityRow, (community.id, disease_id, band))
        if row is None:
            row = ImmunityRow(community_entity_id=community.id, disease_entity_id=disease_id, age_band=band, immune_pct=0, since_epoch=since, locked=False)
            ctx.session.add(row)
            made += 1
        rows[band] = row
        if not row.locked:
            row.immune_pct = max(row.immune_pct, value)
    return made


async def remember_endemic(ctx: TickContext, book: DiseaseBook, region_id: int, disease_id: int, last: int) -> bool:
    table = ctx.rules.epidemiology
    ground = await ctx.session.get(RegionEnvironmentRow, region_id)
    if ground is None or (ground.wetland < WET and ground.disease_load < ENDEMIC_LOAD):
        return False
    load = table.endemic_load - table.endemic_decay * max(0, ctx.epoch - last)
    if load <= 0:
        return False
    rows = book.endemic.setdefault(region_id, [])
    if any(row.disease_entity_id == disease_id for row in rows):
        return False
    row = EndemicDiseaseRow(region_entity_id=region_id, disease_entity_id=disease_id, load=clamp_int(load, 0, PERCENT), since_epoch=last, locked=False)
    ctx.session.add(row)
    rows.append(row)
    return True


async def backfill_plagues(ctx: TickContext) -> dict[str, int]:
    if not await fixup_due(ctx.session, PLAGUE_FIXUP):
        return {}
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    table = ctx.rules.epidemiology
    covered = set(await ctx.session.scalars(select(OutbreakRow.event_entity_id).where(OutbreakRow.event_entity_id.is_not(None))))
    events = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind == EngineKind.PLAGUE, EntityRow.status != EntityStatus.REJECTED)
        .order_by(EntityRow.birth_epoch, EntityRow.id)
    )
    result: Counter[str] = Counter()
    seen: Counter[tuple[int, int]] = Counter()
    last: dict[tuple[int, int], int] = {}
    for event in list(events):
        if event.id in covered:
            continue
        region_id = book.atlas.top_region(event.location_id or event.id)
        region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
        if region is None or region.entity_type is not EntityType.REGION:
            continue
        before = len(book.diseases)
        disease = await disease_for(ctx, book, region, quiet=True)
        profile = book.profiles.get(disease.id)
        if len(book.diseases) > before and profile is not None:
            profile.emerged_epoch = min(profile.emerged_epoch, max(0, event.birth_epoch))
            incident = await event_incident(ctx, event)
            if incident is not None:
                profile.origin_incident_id = incident
            result["diseases"] += 1
        dead, struck = await past_dead(ctx, event)
        severity = clamp_int(stat(event, "severity") or 0, 0, PERCENT)
        ended = event.birth_epoch + table.outbreak_epochs
        live = ended >= ctx.epoch
        outbreak = OutbreakRow(
            disease_entity_id=disease.id,
            region_entity_id=region.id,
            event_entity_id=event.id,
            source_outbreak_id=None,
            path=SpreadPath.ORIGIN,
            status=OutbreakStatus.WANING if live else OutbreakStatus.ENDED,
            severity=severity,
            infected=0,
            dead=0,
            started_epoch=max(0, event.birth_epoch),
            ended_epoch=None if live else ended,
            quarantined=False,
            locked=[],
        )
        ctx.session.add(outbreak)
        await ctx.session.flush()
        if live:
            book.outbreaks.append(outbreak)
        lethality = profile.lethality if profile is not None else table.neutral_lethality
        tally(disease, outbreak, infected=round_half_up(dead * PERCENT / max(1, lethality)), dead=dead)
        await connect(ctx.session, disease.id, event.id, BondKind.CAUSED, ctx.epoch, description="the sickness behind it")
        result["outbreaks"] += 1
        for community_id in struck:
            community = await ctx.session.get(EntityRow, community_id)
            if community is not None and community.status is EntityStatus.CANON and community.entity_type in COMMUNITY_TYPES and not held(community.id):
                result["immunities"] += await remember_immunity(ctx, book, community, disease.id, outbreak.started_epoch)
        seen[(region.id, disease.id)] += 1
        last[(region.id, disease.id)] = outbreak.started_epoch
    for (region_id, disease_id), count in sorted(seen.items()):
        if count >= ENDEMIC_REPEATS and await remember_endemic(ctx, book, region_id, disease_id, last[(region_id, disease_id)]):
            result["endemic"] += 1
    found = dict(result)
    ctx.session.add(AppliedFixupRow(key=PLAGUE_FIXUP, result=found))
    await ctx.session.flush()
    return found
