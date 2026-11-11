from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.society_depth import (
    ClassStandingView,
    CommunityNeedView,
    CorveeView,
    DriftCauseView,
    EffectView,
    ImpositionView,
    LabourReasonView,
    LoyaltyPartView,
    LoyaltyView,
    MobilityEventView,
    PriceView,
    SocietyDepthView,
)
from aerona.catalog.needs import SHORTFALL_EFFECTS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow, DriftCauseRow, DriftImpositionRow, LabourReasonRow, MobilityEventRow, PolityLoyaltyRow
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import GRIEVANCE_PARTS, LoyaltyPart
from aerona.engine.demography.basket import effect_shortfalls, held_got, needs_of, standing_of, staples_of
from aerona.engine.demography.prices import local_prices
from aerona.engine.demography.wealth import per_head
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

router = APIRouter(tags=["society-depth"])


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {entity_id: name for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(list(ids))))}


async def loyalty_views(session: AsyncSession, rules: Rules, entity_id: int) -> list[LoyaltyView]:
    members = {row.polity_entity_id: row for row in await session.scalars(select(PolityMemberRow).where(PolityMemberRow.member_entity_id == entity_id))}
    rows = {row.polity_entity_id: row for row in await session.scalars(select(PolityLoyaltyRow).where(PolityLoyaltyRow.member_entity_id == entity_id))}
    names = await names_of(session, set(rows))
    views: list[LoyaltyView] = []
    for polity_id in sorted(rows):
        row = rows.get(polity_id)
        member = members.get(polity_id)
        parts = []
        for key, value in sorted((row.parts if row is not None else {}).items()):
            try:
                part = LoyaltyPart(key)
            except ValueError:
                continue
            parts.append(LoyaltyPartView(part=part, value=value, grievance=part in GRIEVANCE_PARTS))
        distance = row.value_distance if row is not None else 0
        views.append(
            LoyaltyView(
                polity_id=polity_id,
                polity=names.get(polity_id, ""),
                value_distance=distance,
                distance_penalty=round_half_up(distance * rules.realm_loyalty.distance_pct / PERCENT),
                grievances=row.grievances if row is not None else 0,
                benefits=row.benefits if row is not None else 0,
                satisfaction=row.satisfaction if row is not None else 0,
                loyalty=row.loyalty if row is not None else PERCENT // 2,
                autonomy=member.autonomy if member is not None else 0,
                parts=parts,
                locked=list(row.locked) if row is not None else [],
            )
        )
    return views


async def mobility_views(session: AsyncSession, entity_id: int) -> list[MobilityEventView]:
    rows = list(
        await session.scalars(
            select(MobilityEventRow)
            .where(or_(MobilityEventRow.community_entity_id == entity_id, MobilityEventRow.mortal_entity_id == entity_id))
            .order_by(MobilityEventRow.epoch, MobilityEventRow.id)
        )
    )
    ids = {item for row in rows for item in (row.mortal_entity_id, row.house_entity_id, row.other_entity_id) if item is not None}
    names = await names_of(session, ids)
    return [
        MobilityEventView(
            id=row.id,
            event=row.event,
            count=row.count,
            mortal_id=row.mortal_entity_id,
            mortal=names.get(row.mortal_entity_id or 0, ""),
            house_id=row.house_entity_id,
            house=names.get(row.house_entity_id or 0, ""),
            other_id=row.other_entity_id,
            other=names.get(row.other_entity_id or 0, ""),
            by_hand=row.by_hand,
            epoch=row.epoch,
        )
        for row in rows
    ]


@router.get("/entities/{entity_id}/society-depth", response_model=SocietyDepthView)
async def society_depth(services: ServicesDep, entity_id: int = Path(ge=1)) -> SocietyDepthView:
    async with reader(services) as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        rules = rules_from_snapshot(cosmos.rules_snapshot)
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        society = await session.get(CommunitySocietyRow, entity.id)
        standing = await standing_of(session, entity.id)
        needs = await needs_of(session, entity.id)
        corvee = await session.get(CorveeRow, entity.id)
        work = await session.get(EntityRow, corvee.work_entity_id) if corvee is not None and corvee.work_entity_id is not None else None
        prices = await local_prices(session, rules, entity.id, stat(entity, "population") or 0) if society is not None else {}
        shares = {social_class: society.share(social_class) for social_class in SocialClass} if society is not None else {}
        return SocietyDepthView(
            entity_id=entity.id,
            gini=society.gini if society is not None else 0,
            staples=list(await staples_of(session, entity)),
            needs=[
                CommunityNeedView(
                    social_class=key[0],
                    commodity=key[1],
                    effect=SHORTFALL_EFFECTS[key[1]],
                    wanted=row.wanted,
                    got=min(row.wanted, held_got(row.wanted, row.got, row.held_pct)),
                    held_pct=row.held_pct,
                )
                for key, row in sorted(needs.items(), key=lambda item: (item[0][0].value, item[0][1].value))
                if row.wanted > 0 or row.held_pct is not None
            ],
            classes=[
                ClassStandingView(
                    social_class=social_class,
                    share=shares.get(social_class, 0.0),
                    satisfaction=society.satisfaction(social_class) if society is not None else 0,
                    fed_pct=row.fed_pct,
                    needs_met_pct=row.needs_met_pct,
                    luxury_pct=row.luxury_pct,
                    wealth=row.wealth,
                    per_head=per_head(row, shares.get(social_class, 0.0)),
                    income=row.income,
                    locked=list(row.locked),
                )
                for social_class, row in sorted(standing.items(), key=lambda item: item[0].value)
            ],
            effects=[EffectView(effect=effect, short_pct=value) for effect, value in sorted((await effect_shortfalls(session, entity.id)).items())],
            labour_reasons=[
                LabourReasonView(job=row.job, reason=row.reason, workers=row.workers, commodity=row.commodity, workshop=row.workshop, price_pct=row.price_pct)
                for row in await session.scalars(
                    select(LabourReasonRow).where(LabourReasonRow.community_entity_id == entity.id).order_by(LabourReasonRow.job, LabourReasonRow.reason)
                )
            ],
            held_jobs=[row.job for row in await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == entity.id, LabourRow.held))],
            prices=[PriceView(commodity=kind, price_pct=value) for kind, value in sorted(prices.items(), key=lambda item: item[0].value)],
            corvee=CorveeView(
                share_pct=corvee.share_pct,
                polity_id=corvee.polity_entity_id,
                work_id=corvee.work_entity_id,
                work_name=work.name if work is not None else None,
                laboured_epochs=corvee.laboured_epochs,
                since_epoch=corvee.since_epoch,
                by_hand=corvee.by_hand,
            )
            if corvee is not None
            else None,
            drift_causes=[
                DriftCauseView(cause=row.cause, axis=row.axis, amount=row.amount, total=row.total, epoch=row.epoch)
                for row in await session.scalars(
                    select(DriftCauseRow).where(DriftCauseRow.community_entity_id == entity.id).order_by(DriftCauseRow.cause, DriftCauseRow.axis)
                )
            ],
            impositions=[
                ImpositionView(id=row.id, cause=row.cause, axis=row.axis, amount=row.amount, epochs_left=row.epochs_left, created_epoch=row.created_epoch)
                for row in await session.scalars(
                    select(DriftImpositionRow).where(DriftImpositionRow.community_entity_id == entity.id).order_by(DriftImpositionRow.id)
                )
            ],
            loyalty=await loyalty_views(session, rules, entity.id),
            mobility=await mobility_views(session, entity.id),
        )
