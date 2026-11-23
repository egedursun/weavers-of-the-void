from typing import Any

from aerona.catalog.careers import CAREERS
from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.soils import SOILS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.agrarian import SoilNutrientRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.affliction import CharmKind, CureKind, PackageKind, Transmission
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CareerPath
from aerona.engine.body.afflictions import afflict, cure
from aerona.engine.body.packages_w52 import Shape
from aerona.engine.mind.book import skill_level
from aerona.engine.mortal.acts import openings
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

HEALING_ROLES = frozenset({MortalRole.HEALER, MortalRole.PRIEST, MortalRole.PHYSICIAN, MortalRole.SAINT, MortalRole.SEER})


class BindWithCharmInput(ToolInput):
    target_id: int
    kind: CharmKind


class LiftAfflictionInput(ToolInput):
    affliction_id: int
    cure: CureKind


class ChoosePathInput(ToolInput):
    path: CareerPath


class ImproveSoilInput(ToolInput):
    nutrient: NutrientKind


async def bind_with_charm(call: MortalCall, args: BindWithCharmInput) -> str:
    target = await call.session.get(EntityRow, args.target_id)
    if target is None or target.entity_type is not EntityType.MORTAL or target.id == call.me.id or target.location_id != call.me.location_id:
        fail(MortalResult.CHARM_REFUSED, why="a charm goes only to another mortal in the same place")
    row = await afflict(
        call.tick,
        target,
        PackageKind.CHARM,
        Transmission.INGESTION,
        source_node_id=call.me.id,
        shape=Shape(charm_target_node_id=call.me.id, charm_kind=args.kind),
    )
    if row is None:
        fail(MortalResult.CHARM_REFUSED, why=f"{target.name} is shielded from it")
    call.target(target.id)
    await call.record("tools.mortal.bind_with_charm", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: target.id}, facts={"charm": args.kind})
    return result(MortalResult.CHARM_BINDS, kind=spoken(args.kind), name=target.name)


async def lift_affliction(call: MortalCall, args: LiftAfflictionInput) -> str:
    row = await call.session.get(AfflictionRow, args.affliction_id)
    bearer = await call.session.get(EntityRow, row.bearer_node_id) if row is not None else None
    if row is None or bearer is None or row.cured_epoch is not None or not (bearer.id == call.me.id or bearer.location_id == call.me.location_id):
        fail(MortalResult.LIFT_REFUSED, why="no such affliction lies on anyone here")
    skilled = call.me.mortal_role in HEALING_ROLES or await skill_level(call.session, call.me.id, SkillKind.MEDICINE) > 0
    if not skilled:
        fail(MortalResult.LIFT_REFUSED, why="lifting it needs a healer or a priest")
    if args.cure not in PACKAGES[row.package].cures:
        fail(MortalResult.LIFT_REFUSED, why=f"{PACKAGES[row.package].label.lower()} does not yield to {spoken(args.cure)}")
    await cure(call.tick, bearer, row, args.cure)
    call.target(bearer.id)
    await call.record("tools.mortal.lift_affliction", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PATIENT: bearer.id}, facts={"cure": args.cure})
    return result(MortalResult.AFFLICTION_LIFTED, name=bearer.name, package=PACKAGES[row.package].label.lower(), cure=spoken(args.cure))


async def choose_path_tool(call: MortalCall, args: ChoosePathInput) -> str:
    profile, _ = await ensure_profile(call.session, call.me.id, call.epoch)
    if is_held(profile, "career"):
        fail(MortalResult.PATH_REFUSED, why="your path is held")
    if args.path not in await openings(call.tick, call.me, profile):
        fail(MortalResult.PATH_REFUSED, why=f"{CAREERS[args.path].label.lower()} is not open to you here")
    profile.career = args.path
    call.target(call.me.id)
    await call.record("tools.mortal.choose_path", roles={IncidentRole.SUBJECT: call.me.id}, facts={"path": args.path})
    return result(MortalResult.PATH_CHOSEN, path=CAREERS[args.path].label.lower())


async def improve_soil(call: MortalCall, args: ImproveSoilInput) -> str:
    atlas = await RegionAtlas.load(call.session)
    region_id = atlas.top_region(call.me.id)
    land = await call.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if land is None or region_id is None or atlas.is_water(region_id):
        fail(MortalResult.SOIL_REFUSED, why="you live on no ground with soil to work")
    if held(region_id):
        fail(MortalResult.SOIL_REFUSED, why="a god holds that land as it is")
    row = await call.session.get(SoilNutrientRow, (region_id, args.nutrient))
    if row is None:
        row = SoilNutrientRow(
            region_entity_id=region_id, nutrient=args.nutrient, stock=0 if args.nutrient is NutrientKind.SALINITY else land.soil_base, locked=[]
        )
        call.session.add(row)
    if "stock" in row.locked:
        fail(MortalResult.SOIL_REFUSED, why="that stock of the soil is held")
    table = call.rules.soils
    spec = SOILS[land.soil]
    gain = round_half_up(table.amend_gain * spec.workability(call.rules) / PERCENT + table.leached_amend_gain * spec.acidity / PERCENT)
    row.stock = clamp_int(row.stock - gain if args.nutrient is NutrientKind.SALINITY else row.stock + gain, 0, PERCENT)
    row.updated_epoch = call.epoch
    await call.session.flush()
    call.target(region_id)
    await call.record(
        "tools.mortal.improve_soil",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: region_id},
        facts={"soil": land.soil, "nutrient": args.nutrient, "stock": row.stock},
        place=region_id,
    )
    region = await call.session.get(EntityRow, region_id)
    return result(
        MortalResult.SOIL_IMPROVED, soil=spec.label.lower(), region=region.name if region is not None else "", nutrient=spoken(args.nutrient), stock=row.stock
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BIND_WITH_CHARM, mortal, BindWithCharmInput, meta, bind_with_charm),
        ToolSpec(MortalToolId.LIFT_AFFLICTION, mortal, LiftAfflictionInput, meta, lift_affliction),
        ToolSpec(MortalToolId.CHOOSE_PATH, mortal, ChoosePathInput, meta, choose_path_tool),
        ToolSpec(MortalToolId.IMPROVE_SOIL, mortal, ImproveSoilInput, ToolMeta(ActionKind.RESHAPE_LAND, mortal_standard_action), improve_soil),
    ]
