from typing import Any

from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.ages import EcoTransformationRow, IrregularSeasonRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.ages import ArcRole, ArcTemplate
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import LongPlanStatus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_id_of
from aerona.engine.cycles.ecology import set_back
from aerona.engine.primitives.queries import living_entity
from aerona.engine.sacred.places import region_of, town_of
from aerona.engine.storyteller import control
from aerona.engine.storyteller.arcs import KIN, open_arcs_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class ForecastSeasonsInput(ToolInput):
    long_season_id: int


class SabotageRemakingInput(ToolInput):
    plan_id: int


class SwearVengeanceInput(ToolInput):
    foe_id: int


async def forecast_seasons(call: MortalCall, args: ForecastSeasonsInput) -> str:
    spell = await call.session.get(IrregularSeasonRow, args.long_season_id)
    if spell is None or spell.world_id != call.me.world_id:
        fail(MortalResult.FORECAST_DECLINED, why="no such long season holds your world")
    skill = await call.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == call.me.id, SkillRow.skill == SkillKind.ASTRONOMY).limit(1))
    if (skill or 0) < call.tick.rules.long_seasons.scholar_skill:
        fail(MortalResult.FORECAST_DECLINED, why="you lack the learning of the sky to read the seasons")
    folk = await people_id_of(call.session, await town_of(call.session, call.me))
    if folk is None:
        fail(MortalResult.FORECAST_DECLINED, why="you belong to no people that would heed you")
    made = await control.read_winter(call.tick, spell.id)
    call.target(folk)
    await call.record("tools.mortal.forecast_seasons", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.BENEFICIARY: folk}, facts={"peoples": made})
    return result(MortalResult.SEASONS_FORECAST, peoples=made)


async def sabotage_remaking(call: MortalCall, args: SabotageRemakingInput) -> str:
    plan = await call.session.get(LongPlanRow, args.plan_id)
    work = await call.session.get(EcoTransformationRow, args.plan_id)
    if plan is None or work is None or plan.status is not LongPlanStatus.ACTIVE:
        fail(MortalResult.SABOTAGE_DECLINED, why="no such remaking of the land is under way")
    region = await region_of(call.session, call.me)
    if region is None or plan.target_node_id not in (region.id, call.me.world_id):
        fail(MortalResult.SABOTAGE_DECLINED, why="it does not touch your land")
    if held(plan.holder_node_id) or "progress" in plan.locked:
        fail(MortalResult.SABOTAGE_DECLINED, why="it is held")
    await set_back(call.tick, plan, work)
    call.target(call.me.id)
    await call.record(
        "tools.mortal.sabotage_remaking",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OPPONENT: plan.holder_node_id, IncidentRole.PLACE: plan.target_node_id},
        facts={"plan": plan.name, "progress": plan.progress},
    )
    return result(MortalResult.REMAKING_SABOTAGED, plan=plan.name, progress=plan.progress)


async def swear_vengeance(call: MortalCall, args: SwearVengeanceInput) -> str:
    foe = await living_entity(call.session, args.foe_id)
    if foe is None or foe.id == call.me.id:
        fail(MortalResult.VENGEANCE_DECLINED, why="there is no such foe")
    kin = select(BondRow.target_node_id).where(BondRow.kind.in_(KIN), BondRow.source_node_id == call.me.id)
    kin_back = select(BondRow.source_node_id).where(BondRow.kind.in_(KIN), BondRow.target_node_id == call.me.id)
    wronged = await call.session.scalar(
        select(BondRow.id)
        .where(BondRow.kind == BondKind.KILLED, BondRow.source_node_id == foe.id, BondRow.target_node_id.in_(kin) | BondRow.target_node_id.in_(kin_back))
        .limit(1)
    )
    if wronged is None:
        fail(MortalResult.VENGEANCE_DECLINED, why=f"{foe.name} took none of your kin")
    if any(row.template is ArcTemplate.REVENGE for row in await open_arcs_of(call.tick, call.me.id)):
        fail(MortalResult.VENGEANCE_DECLINED, why="your vow of vengeance already stands")
    row = await control.begin_arc(call.tick, call.me.id, ArcTemplate.REVENGE, foe.id, ArcRole.FOE)
    call.target(foe.id)
    await call.record(
        "tools.mortal.swear_vengeance",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OPPONENT: foe.id},
        facts={"stage": row.stage},
    )
    return result(MortalResult.VENGEANCE_SWORN, foe=foe.name, stage=spoken(row.stage))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FORECAST_SEASONS, mortal, ForecastSeasonsInput, meta, forecast_seasons),
        ToolSpec(MortalToolId.SABOTAGE_REMAKING, mortal, SabotageRemakingInput, meta, sabotage_remaking),
        ToolSpec(MortalToolId.SWEAR_VENGEANCE, mortal, SwearVengeanceInput, meta, swear_vengeance),
    ]
