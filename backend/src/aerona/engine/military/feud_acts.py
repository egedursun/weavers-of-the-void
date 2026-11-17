from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import FeudRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.military import FeudAction, FeudLevel, FeudStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction, StepOutcome, StepState
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.opinion import mortal_rulers
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import FactInput, StepDraft
from aerona.engine.services.community_relations import change_relation, end_blood_feud, feud_between
from aerona.engine.services.war import held_captive, take_captive


@dataclass(frozen=True)
class Deed:
    roles: Mapping[IncidentRole, int | Sequence[int]] = field(default_factory=dict)
    facts: Mapping[str, FactInput] = field(default_factory=dict)
    key: str | None = None
    steps: tuple[StepDraft, ...] = ()


LEVELS: Mapping[FeudAction, FeudLevel | None] = total(
    FeudAction,
    {
        FeudAction.RAID: FeudLevel.RAID,
        FeudAction.ASSASSINATE: FeudLevel.BLOOD,
        FeudAction.DEMAND_WERGILD: None,
        FeudAction.ESCALATE: FeudLevel.WAR,
        FeudAction.REST: None,
        FeudAction.AMBUSH: FeudLevel.RAID,
        FeudAction.ABDUCT: FeudLevel.BLOOD,
        FeudAction.DESTROY_PROPERTY: FeudLevel.RAID,
        FeudAction.SEEK_MEDIATION: None,
        FeudAction.CALL_ALLIES: None,
    },
)
RANK = {FeudLevel.INSULT: 0, FeudLevel.BLOOD: 1, FeudLevel.RAID: 2, FeudLevel.WAR: 3}


async def people_of_side(ctx: TickContext, side: EntityRow) -> list[EntityRow]:
    found = select(EntityRow).where(
        await folk_among(ctx.session, [side.id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    return [row for row in await ctx.session.scalars(found.order_by(EntityRow.id).limit(ctx.rules.vendetta.cap)) if not held(row.id)]


async def ambush(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> Deed | None:
    caught = (await people_of_side(ctx, enemy))[:2]
    for victim in caught:
        await apply_hits(
            ctx, victim, Harm(ctx.rules.vendetta.ambush_hp, HarmCause.BATTLE, f"caught in an ambush by {avenger.name}", killer_id=avenger.id), lethal=False
        )
    if not caught:
        return None
    avenged = tuple(StepDraft(StepAction.AVENGE, actor=avenger.id, target=victim.id, outcome=StepOutcome.WOUNDED) for victim in caught)
    return Deed({IncidentRole.VICTIM: [victim.id for victim in caught]}, {"harm": ctx.rules.vendetta.ambush_hp}, steps=avenged)


async def abduct(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> Deed | None:
    for victim in await people_of_side(ctx, enemy):
        if await held_captive(ctx.session, victim.id) is None:
            await take_captive(ctx, avenger, victim, None, description=f"carried off in the feud with {enemy.name}", home_id=enemy.id)
            return Deed(
                {IncidentRole.VICTIM: victim.id},
                steps=(
                    StepDraft(StepAction.AVENGE, actor=avenger.id, target=victim.id, outcome=StepOutcome.CAPTURED),
                    StepDraft(
                        StepAction.CARRY_OFF,
                        actor=avenger.id,
                        target=victim.id,
                        parent=0,
                        outcome=StepOutcome.CAPTURED,
                        states=((victim.id, StepState.CAPTURED),),
                    ),
                ),
            )
    return None


async def destroy_property(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> Deed | None:
    shift_stat(enemy, "prosperity", -ctx.rules.vendetta.property_loss)
    return Deed(
        facts={"prosperity_loss": ctx.rules.vendetta.property_loss},
        steps=(StepDraft(StepAction.AVENGE, actor=avenger.id, target=enemy.id, outcome=StepOutcome.DAMAGED),),
    )


async def mediator_for(ctx: TickContext, first: EntityRow, second: EntityRow) -> int | None:
    for side in (first, second):
        for ruler_id in await mortal_rulers(ctx.session, side.id):
            if await living_entity(ctx.session, ruler_id) is not None:
                return ruler_id
    return None


async def seek_mediation(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> Deed | None:
    mediator = await mediator_for(ctx, avenger, enemy)
    if mediator is None:
        return None
    row = await feud_between(ctx.session, avenger.id, enemy.id)
    if row is not None and "mediator_node_id" not in row.locked:
        row.mediator_node_id = mediator
    await end_blood_feud(ctx.session, avenger.id, enemy.id, epoch=ctx.epoch, status=FeudStatus.SETTLED)
    await change_relation(ctx, avenger.id, enemy.id, ctx.rules.vendetta.grievance // 3, MemoryKind.MADE_PEACE, note="a mediated feud")
    return Deed(
        {IncidentRole.MEDIATOR: mediator},
        {"status": FeudStatus.SETTLED},
        steps=(StepDraft(StepAction.RECONCILE, actor=avenger.id, target=enemy.id, outcome=StepOutcome.ACCEPTED),),
    )


async def call_allies(ctx: TickContext, avenger: EntityRow, enemy: EntityRow) -> Deed | None:
    allies = await active_bonds(ctx.session, [BondKind.ALLY], sources=[avenger.id])
    joined: list[int] = []
    for bond in allies:
        ally = await living_entity(ctx.session, bond.target_node_id)
        if ally is None or ally.id == enemy.id or held(ally.id):
            continue
        await change_relation(ctx, ally.id, enemy.id, -ctx.rules.vendetta.grievance // 3, MemoryKind.ILL_WILL, note=f"joined the feud of {avenger.name}")
        joined.append(ally.id)
    return Deed({IncidentRole.ALLY: joined}) if joined else None


def raise_level(row: FeudRow, action: FeudAction | None, insult_below: int) -> None:
    if "level" in row.locked:
        return
    reached = LEVELS[action] if action is not None else None
    floor = FeudLevel.INSULT if row.intensity < insult_below else FeudLevel.BLOOD
    current = max(row.level, floor, key=lambda level: RANK[level]) if row.level is not None else floor
    row.level = max(current, reached, key=lambda level: RANK[level]) if reached is not None else current


async def banned(ctx: TickContext, first: EntityRow, second: EntityRow) -> bool:
    return bool(await law_param(ctx.session, first.id, LawKind.BLOOD_FEUD, "banned") or await law_param(ctx.session, second.id, LawKind.BLOOD_FEUD, "banned"))
