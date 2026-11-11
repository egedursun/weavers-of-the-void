from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.collective import (
    AccountStanceView,
    AccountView,
    ArmsView,
    BiasView,
    CascadeView,
    CastView,
    CollectiveView,
    CommemorationView,
    ComponentView,
    CopiedLessonView,
    DatingView,
    DiasporaView,
    GenerationView,
    LostLandView,
    MachineDesignView,
    MaterialChoice,
    MobView,
    MoodView,
    MythView,
    NormChangeView,
    NormView,
    PopularMovementView,
    RoleView,
    SexRatioView,
    StoryletChoiceView,
    StoryletSpecView,
    StoryletStepView,
    StoryletView,
    StrikeView,
    TransitionView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.storylets import STORYLETS
from aerona.core.errors import NotFoundError
from aerona.db.tables.collective import (
    AccountRow,
    AccountStanceRow,
    ArmsRow,
    CascadeRow,
    CommemorationRow,
    ComponentWearRow,
    CrowdMoodRow,
    DatingSystemRow,
    DemographicTransitionRow,
    DesignComponentRow,
    DesignRow,
    DiasporaRow,
    FoundingMythRow,
    GenerationRow,
    LearningBiasRow,
    LearningEventRow,
    LostLandRow,
    MemoryStrikeRow,
    MobRow,
    MovementRow,
    NormChangeRow,
    RoleNormRow,
    SexRatioRow,
    SocialNormRow,
    StoryletRunRow,
)
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.collective import DesignComponentKind, FormativeKind, StoryletRole
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.engine.collective.accounts import distance_from_truth
from aerona.engine.collective.dating import SINGLETON, current_year, render_date
from aerona.engine.collective.designs import lineage_of
from aerona.engine.collective.heraldry import blazon
from aerona.engine.collective.storylets import choice_texts, situation

router = APIRouter(tags=["collective"])


@dataclass(frozen=True)
class Clock:
    year: int
    epoch: int
    years_per_epoch: int

    def year_of(self, epoch: int) -> int:
        return max(0, self.year - (self.epoch - epoch) * self.years_per_epoch)


NodeId = Annotated[int, Path(ge=1)]


async def refs_for(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, NodeRef]:
    return await node_refs(session, [value for value in ids if value is not None])


def at(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def crowd_views(session: AsyncSession, node_id: int) -> tuple[MoodView | None, list[CascadeView], list[MobView], list[PopularMovementView]]:
    mood = await session.get(CrowdMoodRow, node_id)
    cascades = list(
        await session.scalars(select(CascadeRow).where(CascadeRow.settlement_entity_id == node_id).order_by(CascadeRow.epoch.desc(), CascadeRow.id.desc()))
    )
    districts = {
        row.id: row.kind.value.replace("_", " ") for row in await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == node_id))
    }
    mobs = list(await session.scalars(select(MobRow).where(MobRow.settlement_entity_id == node_id).order_by(MobRow.id.desc())))
    movements = list(await session.scalars(select(MovementRow).where(MovementRow.settlement_entity_id == node_id).order_by(MovementRow.id.desc())))
    refs = await refs_for(
        session,
        [
            *(item for mob in mobs for item in (mob.target_entity_id, mob.leader_entity_id)),
            *(item for row in movements for item in (row.leader_entity_id, row.cult_entity_id, row.faction_entity_id)),
        ],
    )
    return (
        MoodView(
            anger=mood.anger,
            anxiety=mood.anxiety,
            fervour=mood.fervour,
            deterrence=mood.deterrence,
            agitation=mood.agitation,
            last_trigger=mood.last_trigger,
            locked=list(mood.locked),
        )
        if mood is not None
        else None,
        [
            CascadeView(
                id=row.id,
                district_name=districts.get(row.district_id) if row.district_id is not None else None,
                trigger=row.trigger,
                act=row.act,
                participants=row.participants,
                share=row.share,
                outcome=row.outcome,
                deaths=row.deaths,
                fled=row.fled,
                epoch=row.epoch,
            )
            for row in cascades
        ],
        [
            MobView(
                id=mob.id,
                act=mob.act,
                size=mob.size,
                anger=mob.anger,
                target=mob.target,
                target_node=at(refs, mob.target_entity_id),
                leader=at(refs, mob.leader_entity_id),
                status=mob.status,
                ended_by=mob.ended_by,
                damage=mob.damage,
                since_epoch=mob.since_epoch,
                locked=list(mob.locked),
            )
            for mob in mobs
        ],
        [
            PopularMovementView(
                id=row.id,
                act=row.act,
                trigger=row.trigger,
                members=row.members,
                strength=row.strength,
                leader=at(refs, row.leader_entity_id),
                cult=at(refs, row.cult_entity_id),
                faction=at(refs, row.faction_entity_id),
                since_epoch=row.since_epoch,
                ended_epoch=row.ended_epoch,
                locked=list(row.locked),
            )
            for row in movements
        ],
    )


async def account_views(session: AsyncSession, node_id: int, clock: Clock) -> list[AccountView]:
    mentioned = select(AccountStanceRow.account_id).where(AccountStanceRow.node_id == node_id)
    rows = list(
        await session.scalars(
            select(AccountRow)
            .where(or_(AccountRow.holder_entity_id == node_id, AccountRow.subject_node_id == node_id, AccountRow.id.in_(mentioned)))
            .order_by(AccountRow.epoch.desc(), AccountRow.id.desc())
        )
    )
    stances: dict[int, list[AccountStanceRow]] = {}
    for stance in await session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id.in_([row.id for row in rows]))):
        stances.setdefault(stance.account_id, []).append(stance)
    named = select(CollectionRow.id, CollectionRow.name).where(CollectionRow.id.in_([row.collection_id for row in rows if row.collection_id]))
    names: dict[int, str] = {key: value for key, value in await session.execute(named)}
    refs = await refs_for(
        session,
        [
            *(item for row in rows for item in (row.holder_entity_id, row.author_node_id, row.subject_node_id, row.structure_entity_id, row.artwork_entity_id)),
            *(stance.node_id for items in stances.values() for stance in items),
        ],
    )
    found: list[AccountView] = []
    for row in rows:
        holder = refs.get(row.holder_entity_id)
        if holder is None:
            continue
        own = sorted(stances.get(row.id, []), key=lambda stance: stance.node_id)
        found.append(
            AccountView(
                id=row.id,
                holder=holder,
                author=at(refs, row.author_node_id),
                kind=row.kind,
                medium=row.medium,
                collection_id=row.collection_id,
                collection_name=names.get(row.collection_id) if row.collection_id is not None else None,
                subject=at(refs, row.subject_node_id),
                structure=at(refs, row.structure_entity_id),
                artwork=at(refs, row.artwork_entity_id),
                fidelity=row.fidelity,
                credence=row.credence,
                distance=distance_from_truth(row, [stance.stance for stance in own]),
                revised_from_id=row.revised_from_id,
                defaced=row.defaced,
                epoch=row.epoch,
                dated=await render_date(session, row.holder_entity_id, clock.year_of(row.epoch)),
                stances=[AccountStanceView(node=refs[stance.node_id], stance=stance.stance) for stance in own if stance.node_id in refs],
                locked=list(row.locked),
            )
        )
    return found


async def memory_views(session: AsyncSession, node_id: int) -> tuple[list[StrikeView], MythView | None, list[CommemorationView], list[LostLandView]]:
    strikes = list(
        await session.scalars(
            select(MemoryStrikeRow)
            .where(or_(MemoryStrikeRow.node_id == node_id, MemoryStrikeRow.by_entity_id == node_id))
            .order_by(MemoryStrikeRow.since_epoch.desc())
        )
    )
    myth = await session.get(FoundingMythRow, node_id)
    kept = list(
        await session.scalars(select(CommemorationRow).where(CommemorationRow.holder_entity_id == node_id).order_by(CommemorationRow.collection_id.desc()))
    )
    lands = list(
        await session.scalars(
            select(LostLandRow)
            .where(or_(LostLandRow.claimant_entity_id == node_id, LostLandRow.region_entity_id == node_id))
            .order_by(LostLandRow.strength.desc(), LostLandRow.region_entity_id)
        )
    )
    named = select(CollectionRow.id, CollectionRow.name).where(CollectionRow.id.in_([row.collection_id for row in kept]))
    names: dict[int, str] = {key: value for key, value in await session.execute(named)}
    refs = await refs_for(
        session,
        [
            node_id,
            *(item for row in strikes for item in (row.node_id, row.by_entity_id)),
            *(item for row in lands for item in (row.claimant_entity_id, row.region_entity_id)),
        ],
    )
    return (
        [
            StrikeView(node=refs[row.node_id], by=refs[row.by_entity_id], active=row.active, since_epoch=row.since_epoch, locked=list(row.locked))
            for row in strikes
            if row.node_id in refs and row.by_entity_id in refs
        ],
        MythView(
            holder=refs[node_id],
            account_id=myth.account_id,
            credence=myth.credence,
            debunked_epoch=myth.debunked_epoch,
            since_epoch=myth.since_epoch,
            locked=list(myth.locked),
        )
        if myth is not None and node_id in refs
        else None,
        [
            CommemorationView(
                holder=refs[node_id],
                collection_id=row.collection_id,
                collection_name=names.get(row.collection_id, "an event"),
                pride=row.pride,
                strength=row.strength,
                last_observed_epoch=row.last_observed_epoch,
                since_epoch=row.since_epoch,
                locked=list(row.locked),
            )
            for row in kept
            if node_id in refs
        ],
        [
            LostLandView(
                claimant=refs[row.claimant_entity_id],
                region=refs[row.region_entity_id],
                strength=row.strength,
                lost_epoch=row.lost_epoch,
                claimed_epoch=row.claimed_epoch,
                locked=list(row.locked),
            )
            for row in lands
            if row.claimant_entity_id in refs and row.region_entity_id in refs
        ],
    )


async def storylet_views(session: AsyncSession, node: EntityRow | None, node_id: int) -> list[StoryletView]:
    mentioned = cast(StoryletRunRow.cast, String).like(f"%: {node_id}%")
    clauses = [StoryletRunRow.chooser_node_id == node_id, mentioned]
    if node is None:
        clauses.append(StoryletRunRow.world_id == node_id)
    rows = list(await session.scalars(select(StoryletRunRow).where(or_(*clauses)).order_by(StoryletRunRow.opened_epoch.desc(), StoryletRunRow.id.desc())))
    rows = [row for row in rows if row.chooser_node_id == node_id or node_id in row.cast.values() or row.world_id == node_id]
    refs = await refs_for(session, [item for row in rows for item in (row.chooser_node_id, *row.cast.values())])
    found: list[StoryletView] = []
    for row in rows:
        choices = await choice_texts(session, row)
        found.append(
            StoryletView(
                id=row.id,
                storylet=row.storylet,
                title=STORYLETS[row.storylet].title,
                world_id=row.world_id,
                cast=[CastView(role=StoryletRole(role), node=refs[item]) for role, item in sorted(row.cast.items()) if item in refs],
                status=row.status,
                chooser=at(refs, row.chooser_node_id),
                choice=row.choice,
                step=row.step,
                situation=await situation(session, row),
                choices=[StoryletChoiceView(index=index, text=text) for index, text in enumerate(choices)],
                follows_run_id=row.follows_run_id,
                collection_id=row.collection_id,
                due_epoch=row.due_epoch,
                opened_epoch=row.opened_epoch,
                resolved_epoch=row.resolved_epoch,
                locked=list(row.locked),
            )
        )
    return found


async def culture_views(
    session: AsyncSession, node_id: int
) -> tuple[list[NormView], list[NormChangeView], BiasView | None, list[CopiedLessonView], list[RoleView]]:
    norms = await session.scalars(
        select(SocialNormRow).where(SocialNormRow.holder_entity_id == node_id).order_by(SocialNormRow.situation, SocialNormRow.behaviour)
    )
    changes = await session.scalars(
        select(NormChangeRow).where(NormChangeRow.holder_entity_id == node_id).order_by(NormChangeRow.epoch.desc(), NormChangeRow.id.desc())
    )
    bias = await session.get(LearningBiasRow, node_id)
    lessons = list(
        await session.scalars(
            select(LearningEventRow).where(LearningEventRow.learner_entity_id == node_id).order_by(LearningEventRow.epoch.desc(), LearningEventRow.id.desc())
        )
    )
    roles = await session.scalars(select(RoleNormRow).where(RoleNormRow.holder_entity_id == node_id).order_by(RoleNormRow.role))
    refs = await refs_for(session, [row.model_entity_id for row in lessons])
    return (
        [NormView(situation=row.situation, behaviour=row.behaviour, stance=row.stance, since_epoch=row.since_epoch, locked=list(row.locked)) for row in norms],
        [
            NormChangeView(id=row.id, situation=row.situation, behaviour=row.behaviour, before=row.before, after=row.after, cause=row.cause, epoch=row.epoch)
            for row in changes
        ],
        BiasView(prestige_pct=bias.prestige_pct, conformity_pct=bias.conformity_pct, content_pct=bias.content_pct, locked=list(bias.locked)) if bias else None,
        [CopiedLessonView(id=row.id, model=at(refs, row.model_entity_id), bias=row.bias, axis=row.axis, shift=row.shift, epoch=row.epoch) for row in lessons],
        [
            RoleView(
                role=row.role,
                eligibility=row.eligibility,
                min_age=row.min_age,
                classes=[SocialClass(item) for item in row.classes],
                stance=row.stance,
                since_epoch=row.since_epoch,
                locked=list(row.locked),
            )
            for row in roles
        ],
    )


async def people_views(session: AsyncSession, node_id: int) -> tuple[list[GenerationView], list[DiasporaView], TransitionView | None, SexRatioView | None]:
    generations = await session.scalars(
        select(GenerationRow).where(GenerationRow.community_entity_id == node_id).order_by(GenerationRow.generation_epoch.desc())
    )
    diasporas = list(
        await session.scalars(
            select(DiasporaRow)
            .where(or_(DiasporaRow.people_entity_id == node_id, DiasporaRow.host_entity_id == node_id, DiasporaRow.home_entity_id == node_id))
            .order_by(DiasporaRow.population.desc())
        )
    )
    transition = await session.get(DemographicTransitionRow, node_id)
    ratio = await session.get(SexRatioRow, node_id)
    refs = await refs_for(session, [item for row in diasporas for item in (row.people_entity_id, row.host_entity_id, row.home_entity_id)])
    return (
        [
            GenerationView(
                generation_epoch=row.generation_epoch,
                formative=[FormativeKind(item) for item in row.formative if item in FormativeKind._value2member_map_],
                value_shifts={ValueAxis(key): value for key, value in row.value_shifts.items() if key in ValueAxis._value2member_map_},
                alive=row.alive,
                passed_epoch=row.passed_epoch,
                locked=list(row.locked),
            )
            for row in generations
        ],
        [
            DiasporaView(
                people=refs[row.people_entity_id],
                host=refs[row.host_entity_id],
                home=at(refs, row.home_entity_id),
                population=row.population,
                ties=row.ties,
                remittance=row.remittance,
                since_epoch=row.since_epoch,
                locked=list(row.locked),
            )
            for row in diasporas
            if row.people_entity_id in refs and row.host_entity_id in refs
        ],
        TransitionView(
            fertility_pct=transition.fertility_pct,
            elder_share=transition.elder_share,
            urban_share=transition.urban_share,
            literacy=transition.literacy,
            locked=list(transition.locked),
        )
        if transition is not None
        else None,
        SexRatioView(males_per_hundred=ratio.males_per_hundred, widows=ratio.widows, locked=list(ratio.locked)) if ratio is not None else None,
    )


async def dating_view(session: AsyncSession, node_id: int, year: int) -> DatingView | None:
    row = await session.get(DatingSystemRow, node_id)
    if row is None:
        return None
    refs = await refs_for(session, [row.label_node_id])
    return DatingView(
        kind=row.kind,
        anchor_year=row.anchor_year,
        label=at(refs, row.label_node_id),
        cycle_years=row.cycle_years,
        reformed_epoch=row.reformed_epoch,
        since_epoch=row.since_epoch,
        today=await render_date(session, node_id, year),
        locked=list(row.locked),
    )


async def arms_view(session: AsyncSession, node_id: int) -> ArmsView | None:
    row = await session.get(ArmsRow, node_id)
    if row is None:
        return None
    refs = await refs_for(session, [row.parent_entity_id, row.quartered_entity_id])
    return ArmsView(
        holder_kind=row.holder_kind,
        field=row.field,
        division=row.division,
        second=row.second,
        charge=row.charge,
        charge_tincture=row.charge_tincture,
        motto=row.motto,
        parent=at(refs, row.parent_entity_id),
        quartered=at(refs, row.quartered_entity_id),
        blazon=blazon(row),
        since_epoch=row.since_epoch,
        locked=list(row.locked),
    )


async def design_views(session: AsyncSession, node_id: int, vessel: VesselProfileRow | None) -> list[MachineDesignView]:
    query = select(DesignRow).where(DesignRow.owner_entity_id == node_id)
    if vessel is not None and vessel.design_id is not None:
        query = select(DesignRow).where(or_(DesignRow.owner_entity_id == node_id, DesignRow.id == vessel.design_id))
    designs = list(await session.scalars(query.order_by(DesignRow.obsolete, DesignRow.epoch.desc(), DesignRow.id.desc())))
    ids = [row.id for row in designs]
    parts: dict[int, list[DesignComponentRow]] = {}
    for part in await session.scalars(select(DesignComponentRow).where(DesignComponentRow.design_id.in_(ids)).order_by(DesignComponentRow.component)):
        parts.setdefault(part.design_id, []).append(part)
    materials = {
        row.id: row.name or row.family.value
        for row in await session.scalars(
            select(WorldMaterialRow).where(WorldMaterialRow.id.in_([part.material_id for items in parts.values() for part in items if part.material_id]))
        )
    }
    counted = select(VesselProfileRow.design_id, func.count()).where(VesselProfileRow.design_id.in_(ids)).group_by(VesselProfileRow.design_id)
    counts: dict[int, int] = {key: value for key, value in await session.execute(counted) if key is not None}
    wear: dict[DesignComponentKind, int] = {}
    if vessel is not None:
        wear = {row.component: row.wear for row in await session.scalars(select(ComponentWearRow).where(ComponentWearRow.vessel_entity_id == vessel.entity_id))}
    refs = await refs_for(session, [item for row in designs for item in (row.owner_entity_id, row.designer_entity_id)])
    found: list[MachineDesignView] = []
    for row in designs:
        if row.owner_entity_id not in refs:
            continue
        own = vessel is not None and vessel.design_id == row.id
        found.append(
            MachineDesignView(
                id=row.id,
                owner=refs[row.owner_entity_id],
                kind=row.kind,
                hull=row.hull,
                name=row.name,
                designer=at(refs, row.designer_entity_id),
                parent_design_id=row.parent_design_id,
                mark=len(await lineage_of(session, row.id)),
                mass=row.mass,
                speed=row.speed,
                range=row.range,
                seaworthiness=row.seaworthiness,
                cargo=row.cargo,
                armament=row.armament,
                crew=row.crew,
                obsolete=row.obsolete,
                epoch=row.epoch,
                vessels=counts.get(row.id, 0),
                components=[
                    ComponentView(
                        component=part.component,
                        material_id=part.material_id,
                        material_name=materials.get(part.material_id) if part.material_id is not None else None,
                        size=part.size,
                        quality=part.quality,
                        wear=wear.get(part.component, 0) if own else None,
                    )
                    for part in parts.get(row.id, [])
                ],
                locked=list(row.locked),
            )
        )
    return found


@router.get("/collective/of/{node_id}", response_model=CollectiveView)
async def node_collective(services: ServicesDep, node_id: NodeId) -> CollectiveView:
    async with reader(services) as session:
        refs = await node_refs(session, [node_id])
        if node_id not in refs:
            raise NotFoundError("No such thing.")
        entity = await session.get(EntityRow, node_id)
        year = await current_year(session)
        cosmos = await session.get(CosmosRow, SINGLETON)
        rules = await world_rules(services, session)
        clock = Clock(year=year, epoch=cosmos.epoch if cosmos is not None else 0, years_per_epoch=rules.time.years_per_epoch)
        mood, cascades, mobs, movements = await crowd_views(session, node_id)
        strikes, myth, commemorations, lost_lands = await memory_views(session, node_id)
        norms, changes, biases, lessons, roles = await culture_views(session, node_id)
        generations, diasporas, transition, ratio = await people_views(session, node_id)
        vessel = await session.get(VesselProfileRow, node_id)
        world = entity.world_id if entity is not None else node_id
        materials = await session.scalars(select(WorldMaterialRow).where(WorldMaterialRow.world_id == world).order_by(WorldMaterialRow.id))
        return CollectiveView(
            node=refs[node_id],
            mood=mood,
            cascades=cascades,
            mobs=mobs,
            movements=movements,
            accounts=await account_views(session, node_id, clock),
            strikes=strikes,
            myth=myth,
            commemorations=commemorations,
            lost_lands=lost_lands,
            storylets=await storylet_views(session, entity, node_id),
            norms=norms,
            norm_changes=changes,
            biases=biases,
            lessons=lessons,
            generations=generations,
            diasporas=diasporas,
            transition=transition,
            sex_ratio=ratio,
            roles=roles,
            dating=await dating_view(session, node_id, year),
            arms=await arms_view(session, node_id),
            designs=await design_views(session, node_id, vessel),
            vessel_design_id=vessel.design_id if vessel is not None else None,
            materials=[MaterialChoice(id=row.id, name=row.name or row.family.value) for row in materials],
        )


@router.get("/collective/storylets", response_model=list[StoryletSpecView])
async def storylet_catalog() -> list[StoryletSpecView]:
    return [
        StoryletSpecView(
            storylet=storylet,
            title=spec.title,
            chooser=spec.chooser,
            roles=list(spec.roles),
            weight=spec.weight,
            steps=[StoryletStepView(text=step.text, choices=[choice.text for choice in step.choices]) for step in spec.steps],
        )
        for storylet, spec in STORYLETS.items()
    ]
