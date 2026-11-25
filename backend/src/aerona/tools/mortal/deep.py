from typing import Any

from sqlalchemy import select

from aerona.catalog.catch import GROUNDS
from aerona.catalog.rocks import ROCKS
from aerona.catalog.strata import STRATA
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.couplings import SealKind
from aerona.domain.enums.crafts import CatchGround, CatchMedium, Gear
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.geology import DeepPassageState, UndergroundStratum
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.couplings.deep import SealLinks, active_seal, missing_link, seal_deep
from aerona.engine.crafts.shores import open_ground
from aerona.engine.environment.cells import dig_toward, ends_of, tell
from aerona.engine.environment.columns import columns_by_region
from aerona.engine.environment.deep import DeepTally, draw_reservoir, reach_stratum
from aerona.engine.environment.geomorph import shift_river
from aerona.engine.primitives.deep import Cell, passage_kind, shape_fault
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.water.courses import blame_works
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import home_of, i_know


class RegionInput(ToolInput):
    region_id: int


class BoreInput(ToolInput):
    region_id: int
    stratum: UndergroundStratum


async def ground_here(call: MortalCall, region_id: int) -> tuple[EntityRow, RegionEnvironmentRow]:
    atlas = await RegionAtlas.load(call.session)
    region = await call.session.get(EntityRow, region_id)
    ground = await call.session.get(RegionEnvironmentRow, region_id)
    if atlas.top_region(call.me.id) != region_id or region is None or ground is None:
        fail(MortalResult.DEEP_REFUSED, why="you work only the land you stand on")
    if held(region_id):
        fail(MortalResult.DEEP_REFUSED, why="a god holds that land unchanged")
    return region, ground


async def dig_deeper(call: MortalCall, args: RegionInput) -> str:
    region, ground = await ground_here(call, args.region_id)
    if "mined" in ground.locked:
        fail(MortalResult.DEEP_REFUSED, why="a god holds the mines of that land as they are")
    ground.mined = clamp_int(ground.mined + call.rules.underground.dig_step, 0, PERCENT)
    rows = (await columns_by_region(call.session, [region.id])).get(region.id, [])
    nearest = next((row for row in rows if row.reached_epoch is None), None)
    call.target(region.id)
    rock = ROCKS[nearest.rock].label.lower() if nearest is not None else "the deep beneath every layer"
    return result(MortalResult.DUG_DEEPER, place=region.name, rock=rock)


async def stratum_here(call: MortalCall, region_id: int, stratum: UndergroundStratum) -> RegionStratumRow:
    row = await call.session.scalar(
        select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region_id, RegionStratumRow.stratum == stratum).limit(1)
    )
    if row is None:
        fail(MortalResult.DEEP_REFUSED, why=f"no {STRATA[stratum].label.lower()} lies beneath that land")
    return row


async def bore(call: MortalCall, args: BoreInput) -> str:
    if not STRATA[args.stratum].bored:
        fail(MortalResult.DEEP_REFUSED, why="only water and traps of fuel can be bored")
    region, ground = await ground_here(call, args.region_id)
    row = await stratum_here(call, region.id, args.stratum)
    if row.reached_epoch is None:
        await reach_stratum(call.tick, ground, row, DeepTally(), digger_id=call.me.id)
    call.target(region.id)
    return result(MortalResult.BORED, place=region.name, stratum=STRATA[args.stratum].label.lower())


async def drill_reservoir(call: MortalCall, args: RegionInput) -> str:
    region, ground = await ground_here(call, args.region_id)
    row = await stratum_here(call, region.id, UndergroundStratum.RESERVOIR)
    if row.volume <= 0:
        fail(MortalResult.DEEP_REFUSED, why="that reservoir is spent")
    if row.reached_epoch is None:
        await reach_stratum(call.tick, ground, row, DeepTally(), digger_id=call.me.id)
    await draw_reservoir(call.tick, ground, row, DeepTally())
    call.target(region.id)
    return result(MortalResult.RESERVOIR_DRILLED, place=region.name, volume=row.volume)


class SealDepthInput(ToolInput):
    place_id: int
    kind: SealKind
    oath_id: int | None = None
    power_id: int | None = None
    line_id: int | None = None
    mind_id: int | None = None


async def owns_links(call: MortalCall, links: SealLinks) -> bool:
    oath = await call.session.get(OathRow, links.oath_id) if links.oath_id is not None else None
    power = await call.session.get(PowerRow, links.power_id) if links.power_id is not None else None
    line = await call.session.get(LivingLineRow, links.line_id) if links.line_id is not None else None
    mind = await call.session.get(MindProfileRow, links.mind_id) if links.mind_id is not None else None
    home = call.me.location_id
    return (
        (links.oath_id is None or (oath is not None and oath.swearer_entity_id == call.me.id))
        and (links.power_id is None or (power is not None and power.holder_node_id == call.me.id))
        and (links.line_id is None or (line is not None and line.owner_node_id in {call.me.id, home}))
        and (links.mind_id is None or (mind is not None and mind.made_by_node_id in {call.me.id, home}))
    )


async def seal_depth(call: MortalCall, args: SealDepthInput) -> str:
    if args.kind is SealKind.DIVINE:
        fail(MortalResult.DEEP_REFUSED, why="only a god seals with its own hand")
    atlas = await RegionAtlas.load(call.session)
    place = await call.session.get(EntityRow, args.place_id)
    if place is None or atlas.top_region(place.id) != atlas.top_region(call.me.id):
        fail(MortalResult.DEEP_REFUSED, why="you seal only a place in the land you stand on")
    if held(place.id) or await active_seal(call.session, place.id) is not None:
        fail(MortalResult.DEEP_REFUSED, why="that deep is already sealed or held")
    links = SealLinks(oath_id=args.oath_id, power_id=args.power_id, line_id=args.line_id, mind_id=args.mind_id)
    missing = missing_link(args.kind, links)
    if missing is not None:
        fail(MortalResult.DEEP_REFUSED, why=f"a seal of that kind names its {missing}")
    if not await owns_links(call, links):
        fail(MortalResult.DEEP_REFUSED, why="you can bind a seal only to what is yours")
    row = await seal_deep(call.tick, place.id, args.kind, call.me.id, links=links)
    call.target(place.id)
    await call.record("seal.made", roles={IncidentRole.SUBJECT: [call.me.id, place.id]}, place=place.id)
    return result(MortalResult.DEPTH_SEALED, place=place.name, kind=spoken(args.kind), strength=row.strength)


class DivertInput(ToolInput):
    region_id: int
    to_region_id: int


async def divert_river(call: MortalCall, args: DivertInput) -> str:
    region, ground = await ground_here(call, args.region_id)
    if ground.river_class is RiverClass.NONE:
        fail(MortalResult.DEEP_REFUSED, why="no river runs through that land")
    atlas = await RegionAtlas.load(call.session)
    if args.to_region_id not in atlas.neighbour_regions(region.id) or held(args.to_region_id):
        fail(MortalResult.DEEP_REFUSED, why="the river can be turned only into a free neighbouring land")
    canal = await call.session.scalar(
        select(StructureProfileRow.structure_entity_id)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.kind == StructureKind.CANAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == call.me.location_id)
        .limit(1)
    )
    if canal is None:
        fail(MortalResult.DEEP_REFUSED, why="your people have no canal to turn it through")
    shift = await shift_river(call.tick, region.id, args.to_region_id, RiverShiftCause.WORKS, event_id=canal)
    if shift is None:
        fail(MortalResult.DEEP_REFUSED, why="the water would not turn that way")
    await blame_works(call.tick, shift)
    target = await call.session.get(EntityRow, args.to_region_id)
    call.target(region.id)
    return result(
        MortalResult.RIVER_DIVERTED, river=spoken(shift.river_class), place=region.name, target=target.name if target is not None else "the next land"
    )


class OpenGroundInput(ToolInput):
    region_id: int
    ground: CatchGround
    gear: Gear
    kind_id: int | None = None


class BuildPondsInput(ToolInput):
    settlement_id: int


class ChangeGearInput(ToolInput):
    source_id: int
    region_id: int
    gear: Gear


async def open_catch_ground(call: MortalCall, args: OpenGroundInput) -> str:
    region, _ = await ground_here(call, args.region_id)
    if args.gear not in GROUNDS[args.ground].gear:
        fail(MortalResult.GROUND_REFUSED, why=f"that ground is not worked with {spoken(args.gear)}")
    living = GROUNDS[args.ground].medium is CatchMedium.LAND
    if living and (args.kind_id is None or await call.session.get(SpeciesRangeRow, (args.kind_id, region.id)) is None):
        fail(MortalResult.GROUND_REFUSED, why="name a kind that lives in that land")
    if args.ground is CatchGround.FISH_PONDS:
        fail(MortalResult.GROUND_REFUSED, why="fish ponds are built, not opened")
    source = args.kind_id if living and args.kind_id is not None else region.id
    row = await open_ground(call.tick, source, region.id, args.ground)
    if row is None:
        fail(MortalResult.GROUND_REFUSED, why="that ground is already open")
    row.gear = args.gear
    call.target(region.id)
    return result(MortalResult.GROUND_OPENED, ground=spoken(args.ground), place=region.name, gear=spoken(args.gear))


async def build_fish_ponds(call: MortalCall, args: BuildPondsInput) -> str:
    town = await call.session.get(EntityRow, args.settlement_id)
    atlas = await RegionAtlas.load(call.session)
    region_id = atlas.top_region(args.settlement_id)
    if town is None or call.me.location_id != town.id or region_id is None:
        fail(MortalResult.GROUND_REFUSED, why="you build ponds only for the town you live in")
    ground = await call.session.get(RegionEnvironmentRow, region_id)
    if ground is None or ground.river_class is RiverClass.NONE:
        fail(MortalResult.GROUND_REFUSED, why="no river feeds ponds there")
    if held(town.id) or await open_ground(call.tick, town.id, region_id, CatchGround.FISH_PONDS) is None:
        fail(MortalResult.GROUND_REFUSED, why="that town already keeps ponds, or a god holds it")
    call.target(town.id)
    return result(MortalResult.PONDS_BUILT, town=town.name)


async def change_gear(call: MortalCall, args: ChangeGearInput) -> str:
    await ground_here(call, args.region_id)
    row = await call.session.get(CatchGroundRow, (args.source_id, args.region_id))
    if row is None or "gear" in row.locked:
        fail(MortalResult.GROUND_REFUSED, why="there is no such ground you may change")
    if args.gear not in GROUNDS[row.ground].gear:
        fail(MortalResult.GROUND_REFUSED, why=f"that ground is not worked with {spoken(args.gear)}")
    row.gear = args.gear
    call.target(args.region_id)
    return result(MortalResult.GEAR_CHANGED, gear=spoken(args.gear))


class DigPassageInput(ToolInput):
    from_region_id: int
    from_stratum: UndergroundStratum | None = None
    to_region_id: int
    to_stratum: UndergroundStratum | None = None


class PassageInput(ToolInput):
    passage_id: int


async def cell_exists(call: MortalCall, region_id: int, stratum: UndergroundStratum | None) -> None:
    region = await call.session.get(EntityRow, region_id)
    if region is None or region.status is not EntityStatus.CANON:
        fail(MortalResult.DEEP_REFUSED, why="no such region")
    if stratum is not None:
        await stratum_here(call, region_id, stratum)


async def dig_passage(call: MortalCall, args: DigPassageInput) -> str:
    first, second = (args.from_region_id, args.from_stratum), (args.to_region_id, args.to_stratum)
    atlas = await RegionAtlas.load(call.session)
    fault = shape_fault(first, second, second[0] in atlas.neighbours(first[0]))
    if fault is not None:
        fail(MortalResult.DEEP_REFUSED, why=fault)
    await cell_exists(call, first[0], first[1])
    await cell_exists(call, second[0], second[1])
    if held(first[0], second[0]):
        fail(MortalResult.DEEP_REFUSED, why="that land is held")
    home = await home_of(call)
    if not await i_know(call, KnowledgeBranch.METALLURGY, home):
        fail(MortalResult.DEEP_REFUSED, why="your people do not know how to dig through rock")
    digger = home or call.me
    row = await dig_toward(call.tick, digger, first, second, by_node_id=call.me.id)
    if row.state is DeepPassageState.DIGGING and "progress" not in row.locked:
        row.progress = clamp_int(row.progress + call.rules.underground.dig_rate, 0, PERCENT)
    call.target(first[0])
    return result(
        MortalResult.PASSAGE_DIGGING,
        kind=spoken(passage_kind(first, second)),
        first=await end_name(call, first),
        second=await end_name(call, second),
        progress=row.progress,
    )


async def end_name(call: MortalCall, cell: Cell) -> str:
    region = await call.session.get(EntityRow, cell[0])
    name = region.name if region is not None else str(cell[0])
    return name if cell[1] is None else f"the {STRATA[cell[1]].label.lower()} beneath {name}"


async def passage_of(call: MortalCall, passage_id: int) -> DeepPassageRow:
    row = await call.session.get(DeepPassageRow, passage_id)
    if row is None:
        fail(MortalResult.DEEP_REFUSED, why="no such passage")
    first, second = ends_of(row)
    if held(first[0], second[0]) or "state" in row.locked:
        fail(MortalResult.DEEP_REFUSED, why="that passage is held")
    return row


async def clear_passage(call: MortalCall, args: PassageInput) -> str:
    row = await passage_of(call, args.passage_id)
    if row.state is not DeepPassageState.COLLAPSED:
        fail(MortalResult.DEEP_REFUSED, why="that passage has not fallen in")
    home = await home_of(call)
    row.dug_by_entity_id = (home or call.me).id
    first, second = ends_of(row)
    call.target(first[0])
    return result(
        MortalResult.PASSAGE_CLEARING, kind=spoken(passage_kind(first, second)), first=await end_name(call, first), second=await end_name(call, second)
    )


async def collapse_passage(call: MortalCall, args: PassageInput) -> str:
    row = await passage_of(call, args.passage_id)
    if row.state in {DeepPassageState.COLLAPSED, DeepPassageState.SEALED}:
        fail(MortalResult.DEEP_REFUSED, why="that passage is already closed")
    if not await i_know(call, KnowledgeBranch.METALLURGY, await home_of(call)) and not await i_know(call, KnowledgeBranch.WARFARE):
        fail(MortalResult.DEEP_REFUSED, why="you have no sappers and no knowledge of digging")
    row.state, row.progress = DeepPassageState.COLLAPSED, 0
    first, second = ends_of(row)
    await tell(call.tick, "deep.passage_collapsed", row, call.me.id)
    call.target(first[0])
    return result(
        MortalResult.PASSAGE_BROUGHT_DOWN, kind=spoken(passage_kind(first, second)), first=await end_name(call, first), second=await end_name(call, second)
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.DIG_DEEPER, mortal, RegionInput, meta, dig_deeper),
        ToolSpec(MortalToolId.BORE, mortal, BoreInput, meta, bore),
        ToolSpec(MortalToolId.DIG_PASSAGE, mortal, DigPassageInput, meta, dig_passage),
        ToolSpec(MortalToolId.CLEAR_PASSAGE, mortal, PassageInput, meta, clear_passage),
        ToolSpec(MortalToolId.COLLAPSE_PASSAGE, mortal, PassageInput, meta, collapse_passage),
        ToolSpec(MortalToolId.DRILL_RESERVOIR, mortal, RegionInput, meta, drill_reservoir),
        ToolSpec(MortalToolId.SEAL_DEPTH, mortal, SealDepthInput, meta, seal_depth),
        ToolSpec(MortalToolId.DIVERT_RIVER, mortal, DivertInput, meta, divert_river),
        ToolSpec(MortalToolId.OPEN_GROUND, mortal, OpenGroundInput, meta, open_catch_ground),
        ToolSpec(MortalToolId.BUILD_PONDS, mortal, BuildPondsInput, meta, build_fish_ponds),
        ToolSpec(MortalToolId.CHANGE_GEAR, mortal, ChangeGearInput, meta, change_gear),
    ]
