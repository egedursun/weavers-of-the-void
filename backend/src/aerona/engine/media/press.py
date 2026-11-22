from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import RECORD_FORM_TRAITS, having
from aerona.catalog.media_shapes import FORM_DECAY_PCT, FUNDING_REVENUE_PCT, ITEM_SWAY_PCT, UNCENSORED_FUNDING
from aerona.constants.units import PERCENT
from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.customs import EvidenceRow
from aerona.db.tables.economy import MarketPriceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow, RecordMediumRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.urban import MarketPlayRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import EvidenceKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.life_traits import RecordFormTrait
from aerona.domain.enums.media import CensorMeasure, MediaItemKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.urban import MarketPlay
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.economy.purse import shift_points
from aerona.engine.polity.laws import ruling_law
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.engine.works.building import take_treasury

TEN = 10
HONEST = 50
APPROVAL_SPAN = 100
FOUND_TRUST = 5
RECORDED_FORMS = having(RECORD_FORM_TRAITS, RecordFormTrait.RECORDED_FORMS)


@dataclass
class MediaTally:
    published: int = 0
    exposed: int = 0
    decayed: int = 0
    found: int = 0
    stars: int = 0
    censored: int = 0
    swayed: int = 0
    alarmed: int = 0


async def medium_of(session: AsyncSession, outlet: MediaOutletRow) -> RecordMediumRow | None:
    return await session.get(RecordMediumRow, outlet.medium_id) if outlet.medium_id is not None else None


def accuracy_for(outlet: MediaOutletRow, medium: RecordMediumRow | None, slant: int) -> int:
    fidelity = medium.fidelity if medium is not None else HONEST
    return clamp_int(PERCENT - abs(slant) // 2 - (PERCENT - fidelity) // 4, 0, PERCENT)


async def reach_and_revenue(ctx: TickContext, outlet: MediaOutletRow, medium: RecordMediumRow | None) -> None:
    table = ctx.rules.media
    if "reach" not in (outlet.locked or []):
        reach = outlet.staff * table.reach_per_staff + (medium.reach // 2 if medium is not None else 0)
        outlet.reach = clamp_int(reach // 2 if outlet.censored else reach, 0, PERCENT)
    owner = await ctx.session.get(EntityRow, outlet.owner_node_id)
    revenue = round_half_up(outlet.reach / TEN * table.revenue_per_reach * outlet.trust / PERCENT * FUNDING_REVENUE_PCT[outlet.funding] / PERCENT)
    if "revenue" not in (outlet.locked or []):
        outlet.revenue = revenue
    if owner is not None and revenue:
        await shift_points(ctx.session, owner, revenue)


async def report(ctx: TickContext, outlet: MediaOutletRow, medium: RecordMediumRow | None, tally: MediaTally) -> None:
    incident = await ctx.session.scalar(
        select(IncidentRow)
        .where(IncidentRow.place_entity_id == outlet.seat_entity_id, IncidentRow.epoch == ctx.epoch, IncidentRow.kind.not_like("media.%"))
        .order_by(IncidentRow.id.desc())
        .limit(1)
    )
    if incident is None:
        return
    kind = MediaItemKind.RECORD_OF_EVENT if medium is not None and medium.form in RECORDED_FORMS else MediaItemKind.NEWS
    item = MediaItemRow(
        outlet_id=outlet.id,
        owner_node_id=outlet.owner_node_id,
        kind=kind,
        subject_incident_id=incident.id,
        slant=outlet.lean,
        accuracy=accuracy_for(outlet, medium, outlet.lean),
        reach=outlet.reach,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(item)
    await ctx.session.flush()
    await record(
        ctx,
        "media.item_published",
        roles={IncidentRole.ACTOR: outlet.owner_node_id, IncidentRole.PLACE: outlet.seat_entity_id},
        facts={"kind": kind, "outlet": outlet.name},
    )
    tally.published += 1


async def sway(ctx: TickContext, outlet: MediaOutletRow, item: MediaItemRow, tally: MediaTally) -> None:
    if item.subject_node_id is None or item.slant == 0 or held(outlet.seat_entity_id):
        return
    opinion = await ctx.session.get(PublicOpinionRow, (outlet.seat_entity_id, item.subject_node_id))
    if opinion is None or "approval" in (opinion.locked or []):
        return
    shift = round_half_up(
        ctx.rules.media.opinion_shift_pct * item.reach / PERCENT * item.slant / PERCENT * outlet.trust / PERCENT * ITEM_SWAY_PCT[item.kind] / PERCENT
    )
    if not shift:
        return
    with explaining():
        term("media.opinion_shift_pct", shift, source_node_id=outlet.owner_node_id)
        opinion.approval = clamp_int(opinion.approval + shift, -APPROVAL_SPAN, APPROVAL_SPAN)
    tally.swayed += 1


async def alarm(ctx: TickContext, outlet: MediaOutletRow, item: MediaItemRow, tally: MediaTally) -> None:
    table = ctx.rules.media
    if item.kind is not MediaItemKind.NEWS or item.slant > -table.alarm_slant or item.subject_node_id is None or held(item.subject_node_id):
        return
    town = await ctx.session.get(EntityRow, item.subject_node_id)
    strength = clamp_int(-item.slant * item.reach * table.alarm_strength_pct // (PERCENT * PERCENT), 0, PERCENT)
    if town is None or town.entity_type is not EntityType.SETTLEMENT or strength <= 0:
        return
    latest = select(func.max(MarketPriceRow.epoch)).where(MarketPriceRow.market_entity_id == town.id).scalar_subquery()
    short = await ctx.session.scalar(
        select(MarketPriceRow.commodity)
        .where(MarketPriceRow.market_entity_id == town.id, MarketPriceRow.epoch == latest)
        .order_by((MarketPriceRow.demand - MarketPriceRow.supply).desc(), MarketPriceRow.commodity)
        .limit(1)
    )
    if short is None:
        return
    play = await ctx.session.get(MarketPlayRow, (town.id, town.id, short, MarketPlay.CORNER))
    if play is None:
        lasting = {"since_epoch": ctx.epoch, "until_epoch": ctx.epoch, "locked": []}
        ctx.session.add(
            MarketPlayRow(holder_entity_id=town.id, settlement_entity_id=town.id, commodity=short, play=MarketPlay.CORNER, strength=strength, **lasting)
        )
    elif "strength" not in (play.locked or []):
        play.strength, play.until_epoch = max(play.strength, strength), max(play.until_epoch or ctx.epoch, ctx.epoch)
    await record(
        ctx, "media.market_alarmed", roles={IncidentRole.PLACE: town.id}, facts={"outlet": outlet.name, "commodity": short, "strength": strength}, place=town.id
    )
    tally.alarmed += 1


async def expose(ctx: TickContext, outlet: MediaOutletRow, item: MediaItemRow, tally: MediaTally) -> None:
    if item.exposed or item.accuracy >= HONEST:
        return
    if not ctx.rng(f"media_exposed.{item.id}.{ctx.epoch}").chance((PERCENT - item.accuracy) * item.reach / PERCENT):
        return
    item.exposed = True
    if "trust" not in (outlet.locked or []):
        with explaining():
            term("media.trust_loss_on_exposure", -ctx.rules.media.trust_loss_on_exposure, source_node_id=outlet.owner_node_id)
            outlet.trust = clamp_int(outlet.trust - ctx.rules.media.trust_loss_on_exposure, 0, PERCENT)
    await record(
        ctx,
        "media.item_exposed",
        roles={IncidentRole.ACTOR: outlet.owner_node_id, IncidentRole.PLACE: outlet.seat_entity_id},
        facts={"kind": item.kind, "accuracy": item.accuracy, "outlet": outlet.name},
    )
    tally.exposed += 1


async def wear(ctx: TickContext, outlet: MediaOutletRow, item: MediaItemRow, medium: RecordMediumRow | None, tally: MediaTally) -> bool:
    if "condition" in (item.locked or []):
        return True
    durability = medium.durability if medium is not None else 0
    frailty = FORM_DECAY_PCT[medium.form] if medium is not None else PERCENT
    decay = round_half_up(ctx.rules.media.record_decay_per_epoch * (PERCENT - durability) / PERCENT * frailty / PERCENT)
    item.condition = clamp_int(item.condition - decay, 0, PERCENT)
    if item.condition > 0:
        return True
    await ctx.session.delete(item)
    tally.decayed += 1
    return False


async def rediscover(ctx: TickContext, outlet: MediaOutletRow, item: MediaItemRow, tally: MediaTally) -> None:
    table = ctx.rules.media
    if item.kind is not MediaItemKind.RECORD_OF_EVENT or ctx.epoch - item.epoch < table.epochs(table.record_age_years):
        return
    if not ctx.rng(f"media_found.{item.id}.{ctx.epoch}").chance(table.found_pct):
        return
    item.epoch, item.reach = ctx.epoch, outlet.reach
    if "trust" not in (outlet.locked or []):
        outlet.trust = clamp_int(outlet.trust + FOUND_TRUST, 0, PERCENT)
    await record(
        ctx, "media.record_found", roles={IncidentRole.ACTOR: outlet.owner_node_id, IncidentRole.PLACE: outlet.seat_entity_id}, facts={"outlet": outlet.name}
    )
    tally.found += 1


async def crown_star(ctx: TickContext, outlet: MediaOutletRow, item: MediaItemRow, tally: MediaTally) -> None:
    table = ctx.rules.media
    if item.kind is not MediaItemKind.ENTERTAINMENT or item.epoch != ctx.epoch or item.reach < table.star_reach or item.subject_node_id is None:
        return
    profile = await ctx.session.get(MortalProfileRow, item.subject_node_id)
    if profile is None or held(item.subject_node_id) or "renown" in (profile.locked or []):
        return
    with explaining():
        term("media.star_renown", table.star_renown, source_node_id=outlet.owner_node_id)
        profile.renown = clamp_int(profile.renown + table.star_renown, 0, PERCENT)
    await record(
        ctx,
        "media.star_rose",
        roles={IncidentRole.SUBJECT: item.subject_node_id, IncidentRole.ACTOR: outlet.owner_node_id},
        facts={"outlet": outlet.name, "reach": item.reach},
    )
    tally.stars += 1


async def censor(ctx: TickContext, outlet: MediaOutletRow, tally: MediaTally) -> None:
    if outlet.funding in UNCENSORED_FUNDING:
        return
    if not outlet.censored and "censored" not in (outlet.locked or []) and await ruling_law(ctx.session, outlet.seat_entity_id, LawKind.CENSORSHIP) is not None:
        outlet.censored = True
        await record(
            ctx,
            "media.outlet_censored",
            roles={IncidentRole.TARGET: outlet.owner_node_id, IncidentRole.PLACE: outlet.seat_entity_id},
            facts={"outlet": outlet.name, "measure": CensorMeasure.CENSOR},
        )
        tally.censored += 1
    if outlet.censored:
        realm = await realm_of(ctx.session, outlet.seat_entity_id)
        if realm is not None and not held(realm):
            await take_treasury(ctx.session, realm, ctx.rules.media.censorship_cost)


async def keep_media(ctx: TickContext) -> MediaTally:
    tally = MediaTally()
    for outlet in list(await ctx.session.scalars(select(MediaOutletRow).order_by(MediaOutletRow.id))):
        if held(outlet.owner_node_id) or held(outlet.seat_entity_id):
            continue
        medium = await medium_of(ctx.session, outlet)
        await censor(ctx, outlet, tally)
        await reach_and_revenue(ctx, outlet, medium)
        await report(ctx, outlet, medium, tally)
        for item in list(await ctx.session.scalars(select(MediaItemRow).where(MediaItemRow.outlet_id == outlet.id).order_by(MediaItemRow.id))):
            if item.epoch == ctx.epoch:
                await sway(ctx, outlet, item, tally)
                await alarm(ctx, outlet, item, tally)
                await crown_star(ctx, outlet, item, tally)
            await expose(ctx, outlet, item, tally)
            if await wear(ctx, outlet, item, medium, tally):
                await rediscover(ctx, outlet, item, tally)
    await ctx.session.flush()
    return tally


async def recorded_evidence(ctx: TickContext, case: CrimeCaseRow) -> list[EvidenceRow]:
    if case.settlement_entity_id is None or case.culprit_entity_id is None:
        return []
    statement = (
        select(MediaItemRow, MediaOutletRow)
        .join(MediaOutletRow, MediaOutletRow.id == MediaItemRow.outlet_id)
        .where(
            MediaOutletRow.seat_entity_id == case.settlement_entity_id,
            MediaItemRow.kind == MediaItemKind.RECORD_OF_EVENT,
            MediaItemRow.epoch >= case.opened_epoch,
            MediaItemRow.exposed.is_(False),
        )
        .order_by(MediaItemRow.accuracy.desc(), MediaItemRow.id)
        .limit(1)
    )
    found = (await ctx.session.execute(statement)).first()
    if found is None:
        return []
    item, _outlet = found
    return [
        EvidenceRow(
            case_id=case.id,
            kind=EvidenceKind.DOCUMENT,
            points_to_node_id=case.culprit_entity_id,
            reliability=round_half_up(ctx.rules.media.evidence_weight_pct * item.accuracy / PERCENT),
            found_epoch=ctx.epoch,
            locked=[],
        )
    ]
