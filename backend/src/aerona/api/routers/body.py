from collections.abc import Iterable

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.body import (
    ArmourView,
    BodyCustomsView,
    BodyView,
    CapacityView,
    CohortView,
    ConditionKindChoice,
    ConditionView,
    DigitView,
    FunctionView,
    InjuryView,
    MaimedView,
    PartView,
    ProsthesisView,
)
from aerona.catalog.body_plans import PLANS
from aerona.catalog.conditions import OPEN_INJURY_STATES, STATES
from aerona.catalog.stats import max_hp
from aerona.catalog.tissues import DIGIT_LIMBS, TISSUES, covering_of, digit_keys, digit_label, digit_weight
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import BodyCustomRow, BodyRow, ConditionRow, MaimedCohortRow, ProsthesisRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import BodyFunction, BodyReading, Capacity, InjuryState, TreatmentStep
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.engine.body.book import Bearer, anatomy_for, bearer_stats, counts_of, injuries_of, prostheses_of, wounds_from
from aerona.engine.body.capacities import BodyState, capacities
from aerona.engine.body.cohorts import maimed_share
from aerona.engine.body.customs import derived_reading, maimed_for_rule, people_of
from aerona.engine.body.functions import function_levels
from aerona.engine.body.healing import HealingWorld
from aerona.engine.body.state import reading_of
from aerona.engine.body.treatment import wanted_steps
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

router = APIRouter(tags=["body"])

DEAD = "dead"
TREATMENT_VALUES = frozenset(step.value for step in TreatmentStep)


LINK_KINDS = {
    NodeKind.ENTITY: "entity",
    NodeKind.SON: "son",
    NodeKind.FOREIGN_GOD: "foreign-god",
    NodeKind.CREATOR: "creator",
    NodeKind.WORLD: "world",
    NodeKind.STAR: "star",
    NodeKind.GALAXY: "galaxy",
    NodeKind.CLUSTER: "cluster",
    NodeKind.DIMENSION: "dimension",
}


async def nodes_of(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, tuple[str, str]]:
    wanted = sorted({node_id for node_id in ids if node_id is not None})
    if not wanted:
        return {}
    rows = await session.execute(select(NodeRow.id, NodeRow.name, NodeRow.kind).where(NodeRow.id.in_(wanted)))
    return {row.id: (row.name, LINK_KINDS[row.kind]) for row in rows}


def name_in(nodes: dict[int, tuple[str, str]], node_id: int | None) -> str | None:
    return nodes[node_id][0] if node_id is not None and node_id in nodes else None


def link_in(nodes: dict[int, tuple[str, str]], node_id: int | None) -> str | None:
    return nodes[node_id][1] if node_id is not None and node_id in nodes else None


async def bearer_row(session: AsyncSession, node_id: int) -> Bearer:
    found: Bearer | None = await session.get(EntityRow, node_id) or await session.get(SonRow, node_id) or await session.get(ForeignGodRow, node_id)
    if found is None:
        raise NotFoundError("No such bearer.")
    return found


def kind_of(bearer: Bearer) -> str:
    if isinstance(bearer, SonRow):
        return "son"
    if isinstance(bearer, ForeignGodRow):
        return "foreign_god"
    return bearer.entity_type.value


def alive(bearer: Bearer) -> bool:
    if isinstance(bearer, EntityRow):
        return bearer.status is EntityStatus.CANON
    return bearer.status.value != DEAD


def hp_of(rules: Rules, bearer: Bearer, body: BodyRow) -> tuple[int | None, int | None]:
    if isinstance(bearer, SonRow):
        return bearer.hp, max_hp(rules, bearer.endurance)
    if isinstance(bearer, EntityRow) and bearer.entity_type is EntityType.MORTAL:
        return stat(bearer, "hp"), body.hp_max
    return None, None


def prosthesis_view(row: ProsthesisRow, names: dict[int, tuple[str, str]]) -> ProsthesisView:
    return ProsthesisView(
        id=row.id,
        injury_id=row.injury_id,
        part=row.part,
        material=row.material,
        quality=row.quality,
        restored_pct=row.restored_pct,
        item_entity_id=row.item_entity_id,
        item_name=name_in(names, row.item_entity_id),
        maker_node_id=row.maker_node_id,
        maker_name=name_in(names, row.maker_node_id),
        epoch=row.epoch,
        world_material_id=row.world_material_id,
    )


@router.get("/bodies/{node_id}", response_model=BodyView | None)
async def body_view(services: ServicesDep, node_id: int = Path(ge=1)) -> BodyView | None:
    rules = services.rules.current
    async with reader(services) as session:
        bearer = await bearer_row(session, node_id)
        body = await session.get(BodyRow, node_id)
        if body is None:
            return None
        anatomy = anatomy_for(body)
        injuries = await injuries_of(session, node_id)
        prostheses = await prostheses_of(session, node_id)
        home_world = getattr(bearer, "world_id", None)
        catalogue = select(AgentlessConditionRow).where(AgentlessConditionRow.world_id == home_world).order_by(AgentlessConditionRow.id)
        kinds = {kind.id: kind for kind in await session.scalars(catalogue)}
        conditions = list(
            await session.scalars(select(ConditionRow).where(ConditionRow.bearer_node_id == node_id).order_by(ConditionRow.since_epoch, ConditionRow.id))
        )
        names = await nodes_of(
            session,
            [
                *(row.cause_node_id for row in injuries),
                *(row.event_entity_id for row in injuries),
                *(row.treated_by_node_id for row in injuries),
                *(row.source_node_id for row in conditions),
                *(row.item_entity_id for row in prostheses),
                *(row.maker_node_id for row in prostheses),
            ],
        )
        fitted = {row.injury_id: row for row in prostheses}
        reading = await reading_of(session, rules, bearer)
        wounds = wounds_from(injuries, prostheses)
        levels = function_levels(rules.capacities, anatomy, wounds, counts_of(body), rules.injury.venom_paralysis_at)
        stats = bearer_stats(bearer)
        whole = capacities(rules, stats, BodyState(anatomy, (), anatomy.full_counts, 0))
        world = await HealingWorld.load(session, rules)
        care = await world.care_for(session, bearer)
        people = await people_of(session, bearer) if isinstance(bearer, EntityRow) else None
        custom = await session.get(BodyCustomRow, people.id) if people is not None else None
        hp, hp_max = hp_of(rules, bearer, body)
        walking = {part.key for part in anatomy.with_function(BodyFunction.LOCOMOTION)}
        parts = []
        for part in anatomy.parts:
            on_part = [row for row in injuries if row.part == part.key]
            lasting = [row for row in on_part if row.state is not InjuryState.LETHAL]
            worst = max(on_part, key=lambda row: STATES[row.state].rank, default=None)
            loss = max((row.function_loss for row in lasting), default=0)
            if part.counted:
                loss = max(loss, round((part.counted - min(part.counted, counts_of(body).get(part.key, part.counted))) * PERCENT / part.counted))
            prosthesis = next((fitted[row.id].material for row in lasting if row.id in fitted), None)
            parts.append(
                PartView(
                    key=part.key,
                    label=part.label,
                    region=part.region,
                    functions=list(part.functions),
                    severable=part.severable,
                    internal=part.internal,
                    vital=part.vital,
                    counted=part.counted,
                    loss=loss,
                    state=worst.state if worst else None,
                    prosthesis=prosthesis,
                )
            )
        return BodyView(
            node_id=bearer.id,
            world_id=getattr(bearer, "world_id", None),
            name=bearer.name,
            bearer_kind=kind_of(bearer),
            alive=alive(bearer),
            plan=body.plan,
            plan_label=PLANS[body.plan].label,
            height_class=body.height_class,
            build=body.build,
            traits=[BodyFunction(trait) for trait in body.traits],
            hp=hp,
            hp_max=hp_max,
            pain=body.pain,
            fingers=body.fingers,
            toes=body.toes,
            teeth=body.teeth,
            blood=body.blood,
            exertion=body.exertion,
            consciousness=body.consciousness,
            handedness=body.handedness,
            digits=[
                DigitView(
                    key=key,
                    label=digit_label(key),
                    part=part,
                    side=key.split("_", 1)[0],
                    name=key.split(".", 1)[-1],
                    weight=digit_weight(key),
                    lost=key in body.lost_digits,
                )
                for part in DIGIT_LIMBS
                if anatomy.part(part) is not None
                for key in digit_keys(part)
            ],
            covering=covering_of(body.plan),
            covering_label=TISSUES[covering_of(body.plan)].label,
            armour=ArmourView(head=body.armour_head, torso=body.armour_torso, limbs=body.armour_limbs),
            capacities=[
                CapacityView(
                    key=capacity,
                    factor=getattr(body, capacity.value),
                    value=round(whole[capacity] * getattr(body, capacity.value) / PERCENT),
                    base=whole[capacity],
                    locked=capacity.value in body.locked,
                )
                for capacity in Capacity
            ],
            functions=[FunctionView(key=function, level=round(levels[function] * PERCENT)) for function in sorted(anatomy.functions)],
            parts=parts,
            injuries=[
                InjuryView(
                    id=row.id,
                    part=row.part,
                    part_label=(found.label if (found := anatomy.part(row.part)) is not None else row.part.replace("_", " ").capitalize()),
                    kind=row.kind,
                    damage_type=row.damage_type,
                    severity=row.severity,
                    state=row.state,
                    function_loss=row.function_loss,
                    cause_kind=row.cause_kind,
                    cause_node_id=row.cause_node_id,
                    cause_name=name_in(names, row.cause_node_id),
                    cause_link=link_in(names, row.cause_node_id),
                    event_entity_id=row.event_entity_id,
                    event_name=name_in(names, row.event_entity_id),
                    epoch=row.epoch,
                    year=row.year,
                    treated_by_node_id=row.treated_by_node_id,
                    treated_by_name=name_in(names, row.treated_by_node_id),
                    visible=row.visible,
                    infected_epochs=row.infected_epochs,
                    healed_epoch=row.healed_epoch,
                    prosthesis=prosthesis_view(fitted[row.id], names) if row.id in fitted else None,
                    tissue=row.tissue,
                    tissue_label=TISSUES[row.tissue].label if row.tissue is not None else None,
                    bleeding=row.bleeding,
                    nerve=row.nerve,
                    treatments=[TreatmentStep(step) for step in row.treatments if step in TREATMENT_VALUES],
                    wanted=wanted_steps(row, walking=row.part in walking) if row.state in OPEN_INJURY_STATES else [],
                    misdiagnosed=row.misdiagnosed,
                )
                for row in sorted(injuries, key=lambda row: (row.state not in OPEN_INJURY_STATES, -row.epoch, -row.id))
            ],
            conditions=[
                ConditionView(
                    id=row.id,
                    kind=row.kind,
                    severity=row.severity,
                    part=row.part,
                    source=row.source,
                    variant_id=row.variant_id,
                    source_node_id=row.source_node_id,
                    source_name=name_in(names, row.source_node_id),
                    source_link=link_in(names, row.source_node_id),
                    since_epoch=row.since_epoch,
                    ended_epoch=row.ended_epoch,
                    visible=row.visible,
                    cause=row.cause,
                    kind_id=row.kind_id,
                    kind_name=kinds[row.kind_id].name if row.kind_id in kinds else None,
                )
                for row in sorted(conditions, key=lambda row: (row.ended_epoch is not None, -row.since_epoch))
            ],
            condition_kinds=[
                ConditionKindChoice(id=kind.id, name=kind.name, cause=kind.cause, system=kind.system, course=kind.course)
                for kind in kinds.values()
                if kind.world_id == home_world
            ],
            locked=list(body.locked),
            patients_healed=body.patients_healed,
            patients_lost=body.patients_lost,
            medicine=care.tier,
            healer_id=care.healer.mortal.id if care.healer else None,
            healer_name=care.healer.mortal.name if care.healer else None,
            healer_skill=care.healer.skill if care.healer else None,
            presence_pct=reading.presence_pct,
            people_id=people.id if people else None,
            people_name=people.name if people else None,
            reading=custom.reading if custom else None,
            wholeness_required=custom.wholeness_required if custom else False,
            updated_epoch=body.updated_epoch,
        )


@router.get("/peoples/{people_id}/body-customs", response_model=BodyCustomsView)
async def body_customs(services: ServicesDep, people_id: int = Path(ge=1)) -> BodyCustomsView:
    rules = services.rules.current
    async with reader(services) as session:
        people = await session.get(EntityRow, people_id)
        if people is None or people.entity_type is not EntityType.PEOPLE:
            raise NotFoundError("No such people.")
        custom = await session.get(BodyCustomRow, people_id)
        derived, wholeness = await derived_reading(session, rules, people)
        if custom is None:
            custom = BodyCustomRow(
                people_entity_id=people_id, reading=derived, wholeness_required=wholeness, seer_eye=False, scar_festivals=False, pension=False, locked=[]
            )
        tradition = await session.get(EntityRow, custom.tradition_entity_id) if custom.tradition_entity_id else None
        rulers = 0
        for bond in await active_bonds(session, [BondKind.RULES], targets=[people_id]):
            ruler = await session.get(EntityRow, bond.source_node_id)
            if ruler is not None and maimed_for_rule(
                BodyCustomRow(people_entity_id=people_id, reading=custom.reading, wholeness_required=True, locked=[]), await injuries_of(session, ruler.id)
            ):
                rulers += 1
        return BodyCustomsView(
            people_id=people_id,
            reading=custom.reading,
            derived_reading=derived,
            wholeness_required=custom.wholeness_required,
            seer_eye=bool(custom.seer_eye),
            scar_festivals=bool(custom.scar_festivals),
            pension=bool(custom.pension),
            tradition_id=tradition.id if tradition else None,
            tradition_name=tradition.name if tradition else None,
            locked=list(custom.locked),
            maimed_rulers=rulers,
        )


@router.get("/communities/{community_id}/maimed", response_model=MaimedView)
async def maimed(services: ServicesDep, community_id: int = Path(ge=1)) -> MaimedView:
    rules = services.rules.current
    table = rules.maimed
    async with reader(services) as session:
        community = await session.get(EntityRow, community_id)
        if community is None or community.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
            raise NotFoundError("No such community.")
        rows = list(await session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.community_entity_id == community_id).order_by(MaimedCohortRow.kind)))
        share = maimed_share(rules, community, rows)
        people = await people_of(session, community)
        custom = await session.get(BodyCustomRow, people.id) if people is not None else None
        martial = custom is not None and custom.reading is BodyReading.MARTIAL_HONOUR
        appetite = 1.0 if martial else max(0.0, 1 - share * table.anti_war_pct / PERCENT)
        return MaimedView(
            community_id=community_id,
            population=stat(community, "population") or 0,
            total=sum(row.count for row in rows),
            veterans=sum(row.veterans for row in rows),
            share_pct=round(share * PERCENT),
            labour_pct=round(max(0.0, 1 - share * table.labour_loss_pct / PERCENT) * PERCENT),
            war_appetite_pct=round(appetite * PERCENT),
            healer_demand_pct=round((1 + share * table.healer_demand_pct / PERCENT) * PERCENT),
            pension=bool(custom.pension) if custom else False,
            reading=custom.reading if custom else None,
            people_id=people.id if people else None,
            people_name=people.name if people else None,
            cohorts=[CohortView(kind=row.kind, count=row.count, veterans=row.veterans, updated_epoch=row.updated_epoch) for row in rows],
        )
