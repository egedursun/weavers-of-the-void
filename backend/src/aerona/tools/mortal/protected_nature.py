from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionBasis, ProtectionMeasure
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import living_entity
from aerona.engine.protected_nature.areas import protect_area
from aerona.engine.protected_nature.book import NatureTally
from aerona.engine.protected_nature.species import protect_species, reintroduce
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

SPECIES_KINDS = frozenset({EntityType.SPECIES})


class ProtectAreaInput(ToolInput):
    region_or_site_id: int
    basis: ProtectionBasis
    banned_uses: list[ProtectedUse] = Field(min_length=1, max_length=len(ProtectedUse))


class ProtectSpeciesInput(ToolInput):
    species_id: int
    measures: list[ProtectionMeasure] = Field(min_length=1, max_length=len(ProtectionMeasure))
    basis: ProtectionBasis = ProtectionBasis.LAW


class ReintroduceInput(ToolInput):
    species_id: int
    region_id: int


async def protector_in(call: MortalCall, region_id: int) -> int:
    atlas = await RegionAtlas.load(call.session)
    ruled = await call.session.scalars(select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER))
    for realm in sorted(set(ruled)):
        members = await call.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm))
        if any(atlas.top_region(member) == region_id for member in members):
            return realm
    return call.me.id


async def protect_area_tool(call: MortalCall, args: ProtectAreaInput) -> str:
    place = await living_entity(call.session, args.region_or_site_id)
    if place is None:
        fail(MortalResult.NATURE_REFUSED, why="there is no such land or site")
    atlas = await RegionAtlas.load(call.session)
    region_id = place.id if place.entity_type is EntityType.REGION else atlas.top_region(place.id)
    region = await living_entity(call.session, region_id) if region_id is not None else None
    if region is None or held(region.id):
        fail(MortalResult.NATURE_REFUSED, why="that land lies in no region, or a god holds it")
    if args.basis is ProtectionBasis.LAW and await protector_in(call, region.id) == call.me.id:
        fail(MortalResult.NATURE_REFUSED, why="protection by law is set by one who rules the land")
    site = place.id if place.id != region.id else None
    row = await protect_area(call.tick, region, args.basis, list(args.banned_uses), NatureTally(), protector=await protector_in(call, region.id), site=site)
    call.target(region.id)
    return result(MortalResult.AREA_PROTECTED, region=region.name, uses=", ".join(spoken(use) for use in args.banned_uses), strength=row.strength)


async def species_of(call: MortalCall, species_id: int) -> EntityRow:
    species = await living_entity(call.session, species_id)
    if species is None or species.entity_type not in SPECIES_KINDS:
        fail(MortalResult.NATURE_REFUSED, why="there is no such living kind")
    if held(species.id):
        fail(MortalResult.NATURE_REFUSED, why="a god holds that kind as it is")
    return species


async def protect_species_tool(call: MortalCall, args: ProtectSpeciesInput) -> str:
    species = await species_of(call, args.species_id)
    await protect_species(call.tick, species, args.basis, list(args.measures), NatureTally(), holder=call.me.id)
    call.target(species.id)
    return result(MortalResult.SPECIES_PROTECTED, species=species.name, measures=", ".join(spoken(measure) for measure in args.measures))


async def reintroduce_tool(call: MortalCall, args: ReintroduceInput) -> str:
    species = await species_of(call, args.species_id)
    region = await living_entity(call.session, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(MortalResult.NATURE_REFUSED, why="there is no such land")
    took = await reintroduce(call.tick, species, region.id, NatureTally(), by=call.me.id)
    call.target(region.id)
    outcome = "took hold" if took else "did not take hold, or the land cannot hold it, or it never left"
    return result(MortalResult.SPECIES_REINTRODUCED, species=species.name, region=region.name, outcome=outcome)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.PROTECT_AREA, AgentKind.MORTAL, ProtectAreaInput, act, protect_area_tool),
        ToolSpec(MortalToolId.PROTECT_SPECIES, AgentKind.MORTAL, ProtectSpeciesInput, act, protect_species_tool),
        ToolSpec(MortalToolId.REINTRODUCE, AgentKind.MORTAL, ReintroduceInput, act, reintroduce_tool),
    ]
