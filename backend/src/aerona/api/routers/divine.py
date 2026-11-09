from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.divine import (
    BreachPointView,
    CommunityRegard,
    CouncilRulings,
    CouncilRulingView,
    CreatorDivinity,
    CreatorTabooView,
    DivineDomainView,
    DivineStandingView,
    DivineWoundView,
    DomainActivityPoint,
    DomainHookView,
    DomainSynergyView,
    GodAvatarView,
    GodDivinity,
    GodGoalView,
    NaturalLawProfileView,
    OuterBargainView,
    OuterBeingProfileView,
    WorldAttentionView,
    WorldDivinity,
    WorldHookView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.domain_effects import ACTIVITY_LABELS, DOMAIN_EFFECTS, HOOKS, SYNERGY_OF
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.knowledge import NATURAL_LAWS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import (
    AvatarRow,
    BreachPointRow,
    CouncilRulingRow,
    CreatorTabooRow,
    DivineStandingRow,
    DivineWoundRow,
    DomainActivityRow,
    GodGoalRow,
    NaturalLawProfileRow,
    OuterBeingProfileRow,
    WorldAttentionRow,
    WorldDomainHookRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow, OuterBargainRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.divine import CouncilMotion, DivineWoundKind, GodGoalKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.divine.goals import GOAL_LABELS, SON_ONLY
from aerona.engine.divine.outer import HUNGER_LABELS, oppose_cost
from aerona.engine.divine.rulings import MOTION_LABELS
from aerona.engine.divine.wounds import WOUND_LABELS
from aerona.rules.registry import Rules

router = APIRouter(tags=["divine"])
Id = Annotated[int, Path(ge=1)]


def act_label(value: str) -> str:
    return value.replace("_", " ").capitalize()


def ref(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def standing_views(session: AsyncSession, rows: list[DivineStandingRow]) -> list[DivineStandingView]:
    refs = await node_refs(session, [item for row in rows for item in (row.community_entity_id, row.god_node_id)])
    return [
        DivineStandingView(
            community=refs[row.community_entity_id],
            god=refs[row.god_node_id],
            awe=row.awe,
            love=row.love,
            fear=row.fear,
            neglect=row.neglect,
            epoch=row.epoch,
            locked=row.locked,
        )
        for row in rows
        if row.community_entity_id in refs and row.god_node_id in refs
    ]


def domain_views(rules: Rules, domains: tuple[Domain, ...], severed: set[Domain]) -> list[DivineDomainView]:
    steps = {2: rules.domains.major_hook_pct, 1: rules.domains.minor_hook_pct}
    return [
        DivineDomainView(
            domain=domain,
            label=DOMAIN_LABELS[domain],
            activity=DOMAIN_EFFECTS[domain].activity,
            activity_label=ACTIVITY_LABELS[DOMAIN_EFFECTS[domain].activity],
            severed=domain in severed,
            hooks=[
                DomainHookView(
                    hook=hook, label=HOOKS[hook].label, effect=HOOKS[hook].effect, weight=weight, pct=float(steps[weight]), harmful=HOOKS[hook].harmful
                )
                for hook, weight in DOMAIN_EFFECTS[domain].hooks.items()
            ],
        )
        for domain in domains
    ]


@router.get("/gods/{god_id}/divinity", response_model=GodDivinity)
async def god_divinity(god_id: Id, services: ServicesDep) -> GodDivinity:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        son = await session.get(SonRow, god_id)
        foreign = await session.get(ForeignGodRow, god_id) if son is None else None
        if son is None and foreign is None:
            raise NotFoundError("No such son or foreign god.")
        domains = (
            son.domains
            if son is not None
            else tuple(item for item in (foreign.domain_primary, foreign.domain_secondary) if item is not None)
            if foreign
            else ()
        )
        wounds = list(await session.scalars(select(DivineWoundRow).where(DivineWoundRow.god_node_id == god_id).order_by(DivineWoundRow.id)))
        severed = {row.domain for row in wounds if row.kind is DivineWoundKind.SEVERED_DOMAIN and row.healed < PERCENT and row.domain is not None}
        living = [domain for domain in domains if domain not in severed]
        synergy = SYNERGY_OF.get(frozenset(living)) if len(living) > 1 else None
        goals = list(await session.scalars(select(GodGoalRow).where(GodGoalRow.god_node_id == god_id).order_by(GodGoalRow.id.desc())))
        standing = list(
            await session.scalars(select(DivineStandingRow).where(DivineStandingRow.god_node_id == god_id).order_by(DivineStandingRow.community_entity_id))
        )
        avatars = list(await session.scalars(select(AvatarRow).where(AvatarRow.god_node_id == god_id).order_by(AvatarRow.avatar_entity_id)))
        activity = list(
            await session.scalars(
                select(DomainActivityRow).where(DomainActivityRow.god_node_id == god_id).order_by(DomainActivityRow.epoch, DomainActivityRow.id)
            )
        )
        ids = [god_id, *(item for goal in goals for item in (goal.target_node_id, goal.world_id) if item is not None)]
        ids += [row.cause_node_id for row in wounds if row.cause_node_id is not None]
        ids += [item for row in avatars for item in (row.avatar_entity_id, row.world_id) if item is not None]
        refs = await node_refs(session, ids)
        alive = {
            row.id
            for row in await session.scalars(
                select(EntityRow).where(EntityRow.id.in_([item.avatar_entity_id for item in avatars]), EntityRow.status == EntityStatus.CANON)
            )
        }
        return GodDivinity(
            god=refs[god_id],
            domains=domain_views(rules, domains, severed),
            synergy=DomainSynergyView(label=synergy.label, hook=synergy.hook, hook_label=HOOKS[synergy.hook].label) if synergy is not None else None,
            activity=[DomainActivityPoint(epoch=row.epoch, domain=row.domain, activity=row.activity, count=row.count, essence=row.essence) for row in activity],
            goals=[
                GodGoalView(
                    id=row.id,
                    kind=row.kind,
                    label=GOAL_LABELS[row.kind],
                    target=ref(refs, row.target_node_id),
                    world=ref(refs, row.world_id),
                    domain=row.domain,
                    amount=row.amount,
                    progress=row.progress,
                    state=row.state,
                    source=row.source,
                    since_epoch=row.since_epoch,
                    closed_epoch=row.closed_epoch,
                    locked=row.locked,
                )
                for row in goals
            ],
            standing=await standing_views(session, standing),
            wounds=[
                DivineWoundView(
                    id=row.id,
                    kind=row.kind,
                    label=WOUND_LABELS[row.kind],
                    domain=row.domain,
                    severity=row.severity,
                    healed=row.healed,
                    cause=row.cause,
                    cause_node=ref(refs, row.cause_node_id),
                    epoch=row.epoch,
                    locked=row.locked,
                )
                for row in wounds
            ],
            avatars=[
                GodAvatarView(
                    avatar=refs[row.avatar_entity_id],
                    god=refs[god_id],
                    world=ref(refs, row.world_id),
                    since_epoch=row.since_epoch,
                    deeds=row.deeds,
                    alive=row.avatar_entity_id in alive,
                    locked=row.locked,
                )
                for row in avatars
                if row.avatar_entity_id in refs
            ],
            goal_kinds=[kind for kind in GodGoalKind if son is not None or kind not in SON_ONLY],
        )


@router.get("/entities/{entity_id}/regard", response_model=CommunityRegard)
async def community_regard(entity_id: Id, services: ServicesDep) -> CommunityRegard:
    async with reader(services) as session:
        rows = list(
            await session.scalars(select(DivineStandingRow).where(DivineStandingRow.community_entity_id == entity_id).order_by(DivineStandingRow.god_node_id))
        )
        refs = await node_refs(session, [entity_id])
        if entity_id not in refs:
            raise NotFoundError("No such community.")
        return CommunityRegard(community=refs[entity_id], standing=await standing_views(session, rows))


async def attention_views(session: AsyncSession, rules: Rules, rows: list[WorldAttentionRow]) -> list[WorldAttentionView]:
    refs = await node_refs(session, [row.world_id for row in rows])
    return [
        WorldAttentionView(
            world=refs[row.world_id],
            attention=row.attention,
            watched=row.watched,
            far=row.attention < rules.creator.far_eye_below,
            epoch=row.epoch,
            locked=row.locked,
        )
        for row in rows
        if row.world_id in refs
    ]


@router.get("/creator/divinity", response_model=CreatorDivinity)
async def creator_divinity(services: ServicesDep) -> CreatorDivinity:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        creator = await session.scalar(select(CreatorRow).limit(1))
        taboos = list(await session.scalars(select(CreatorTabooRow).order_by(CreatorTabooRow.act)))
        refs = await node_refs(session, [row.last_breaker_node_id for row in taboos if row.last_breaker_node_id is not None])
        standing = (
            list(
                await session.scalars(
                    select(DivineStandingRow).where(DivineStandingRow.god_node_id == creator.id).order_by(DivineStandingRow.community_entity_id)
                )
            )
            if creator is not None
            else []
        )
        return CreatorDivinity(
            taboos=[
                CreatorTabooView(
                    act=row.act,
                    label=act_label(row.act.value),
                    severity=row.severity,
                    since_epoch=row.since_epoch,
                    broken=row.broken,
                    last_broken_epoch=row.last_broken_epoch,
                    last_breaker=ref(refs, row.last_breaker_node_id),
                )
                for row in taboos
            ],
            attention=await attention_views(session, rules, list(await session.scalars(select(WorldAttentionRow).order_by(WorldAttentionRow.world_id)))),
            standing=await standing_views(session, standing),
            far_below=rules.creator.far_eye_below,
        )


@router.get("/worlds/{world_id}/divinity", response_model=WorldDivinity)
async def world_divinity(world_id: Id, services: ServicesDep) -> WorldDivinity:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        hooks = list(
            await session.scalars(
                select(WorldDomainHookRow).where(WorldDomainHookRow.world_id == world_id).order_by(WorldDomainHookRow.domain, WorldDomainHookRow.hook)
            )
        )
        attention = await session.get(WorldAttentionRow, world_id)
        views = await attention_views(session, rules, [attention] if attention is not None else [])
        refs = await node_refs(session, [world_id])
        return WorldDivinity(
            world=refs[world_id],
            hooks=[WorldHookView(domain=row.domain, hook=row.hook, label=HOOKS[row.hook].label, pct=row.pct) for row in hooks],
            attention=views[0] if views else None,
        )


@router.get("/council/rulings", response_model=CouncilRulings)
async def council_rulings(services: ServicesDep) -> CouncilRulings:
    async with reader(services) as session:
        rows = list(await session.scalars(select(CouncilRulingRow).order_by(CouncilRulingRow.id.desc())))
        refs = await node_refs(session, [item for row in rows for item in (row.target_node_id, row.world_id) if item is not None])
        return CouncilRulings(
            rulings=[
                CouncilRulingView(
                    id=row.id,
                    motion=row.motion,
                    label=MOTION_LABELS[row.motion],
                    target=ref(refs, row.target_node_id),
                    world=ref(refs, row.world_id),
                    school=row.school,
                    punishment=row.punishment,
                    epoch=row.epoch,
                    until_epoch=row.until_epoch,
                    active=row.active,
                    enacted=row.enacted,
                    note=row.note,
                    locked=row.locked,
                )
                for row in rows
            ],
            motions=[motion for motion in CouncilMotion if motion is not CouncilMotion.NONE],
        )


@router.get("/entities/{entity_id}/law-profile", response_model=NaturalLawProfileView)
async def law_profile(entity_id: Id, services: ServicesDep) -> NaturalLawProfileView:
    async with reader(services) as session:
        row = await session.get(NaturalLawProfileRow, entity_id)
        if row is None:
            raise NotFoundError("The world has not yet given this law its working; it will after the next epoch.")
        refs = await node_refs(session, [item for item in (entity_id, row.world_id, row.region_entity_id, row.author_node_id) if item is not None])
        spec = NATURAL_LAWS[row.effect]
        return NaturalLawProfileView(
            law=refs[entity_id],
            effect=row.effect,
            effect_label=spec.label,
            effect_text=spec.effect,
            scope=row.scope,
            world=ref(refs, row.world_id),
            region=ref(refs, row.region_entity_id),
            strength=row.strength,
            stability=row.stability,
            author=ref(refs, row.author_node_id),
            exception=row.exception,
            contested=row.contested,
            updated_epoch=row.updated_epoch,
            locked=row.locked,
        )


@router.get("/entities/{entity_id}/outer-profile", response_model=OuterBeingProfileView)
async def outer_profile_view(entity_id: Id, services: ServicesDep) -> OuterBeingProfileView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        being = await session.get(EntityRow, entity_id)
        row = await session.get(OuterBeingProfileRow, entity_id)
        if being is None or being.entity_type is not EntityType.OUTER_BEING or row is None:
            raise NotFoundError("The world has not yet described this outer being; it will after the next epoch.")
        breaches = list(await session.scalars(select(BreachPointRow).where(BreachPointRow.outer_entity_id == entity_id).order_by(BreachPointRow.id)))
        bargains = list(await session.scalars(select(OuterBargainRow).where(OuterBargainRow.outer_entity_id == entity_id).order_by(OuterBargainRow.epoch)))
        ids = [entity_id, *(item for breach in breaches for item in (breach.world_id, breach.region_entity_id) if item is not None)]
        ids += [item for bargain in bargains for item in (bargain.son_id, bargain.price_world_id) if item is not None]
        refs = await node_refs(session, ids)
        return OuterBeingProfileView(
            being=refs[entity_id],
            hunger=row.hunger,
            hunger_label=HUNGER_LABELS[row.hunger],
            reach=row.reach,
            fed=row.fed,
            oppose_cost=oppose_cost(rules.outer_beings.oppose_cost_pct, being),
            updated_epoch=row.updated_epoch,
            locked=row.locked,
            breaches=[
                BreachPointView(
                    id=breach.id,
                    world=ref(refs, breach.world_id),
                    region=ref(refs, breach.region_entity_id),
                    strength=breach.strength,
                    opened_epoch=breach.opened_epoch,
                    locked=breach.locked,
                )
                for breach in breaches
            ],
            bargains=[
                OuterBargainView(
                    son=refs[bargain.son_id],
                    epoch=bargain.epoch,
                    terms=bargain.terms,
                    gain=bargain.gain,
                    price=bargain.price,
                    price_domain=bargain.price_domain,
                    price_world=ref(refs, bargain.price_world_id),
                    paid=bargain.paid,
                )
                for bargain in bargains
                if bargain.son_id in refs
            ],
        )
