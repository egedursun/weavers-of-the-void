from collections.abc import Awaitable
from typing import Any, Literal

from pydantic import Field
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.ecology import SpeciesProductRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, SymbiontRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.living import CultivationMethod, Fertility, HostPlacement, HostRelation, LineTrait
from aerona.domain.enums.made import AugmentKind, AugmentSlot
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.agrarian.control import plant
from aerona.engine.agrarian.lands import kind_of
from aerona.engine.living import control
from aerona.engine.living.disease import design_cure, design_disease
from aerona.engine.living.grown import Growing, found_living_works, grow_gear, grow_organ, grow_structure, grow_vessel, license_line, raise_sapience
from aerona.engine.living.kin import clone, remove_symbiont, sampled
from aerona.engine.living.lines import LineDraft, make_line
from aerona.engine.mind.book import best_skill
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.inputs import EnactLawInput
from aerona.tools.mortal.ruler import enact_law

PERCENT = 100
Name = Field(min_length=1, max_length=120)
SAMPLE_SKILLS = (SkillKind.SCIENCE, SkillKind.MEDICINE, SkillKind.FORAGING, SkillKind.BEAST_HANDLING)
LivingMethod = Literal["cultured_crops", "grown_timber", "fibre_from_life", "vat_culture", "bioreactor"]


class TraitPick(ToolInput):
    trait: LineTrait
    strength: int = Field(default=30, ge=-PERCENT, le=PERCENT)


class BreedLineInput(ToolInput):
    species_id: int
    name: str = Name
    traits: list[TraitPick] = Field(default_factory=list, max_length=6)


class DesignLineInput(ToolInput):
    name: str = Name
    method: CultivationMethod
    source_ids: list[int] = Field(default_factory=list, max_length=6)
    traits: list[TraitPick] = Field(default_factory=list, max_length=6)
    fertility: Fertility = Fertility.BREEDS_TRUE


class BankSampleInput(ToolInput):
    bank_id: int
    organism_id: int


class LineInput(ToolInput):
    line_id: int


class SampleInput(ToolInput):
    sample_id: int


class GrowInput(ToolInput):
    name: str = Name
    line_id: int | None = None


class GrowOrganInput(ToolInput):
    slot: AugmentSlot = AugmentSlot.PART
    kind: AugmentKind = AugmentKind.REPLACEMENT
    bearer_id: int | None = None


class CloneInput(ToolInput):
    source_id: int


class HostSymbiontInput(ToolInput):
    line_id: int
    placement: HostPlacement = HostPlacement.SKIN
    relation: HostRelation = HostRelation.MUTUAL


class SymbiontInput(ToolInput):
    symbiont_id: int


class DesignDiseaseInput(ToolInput):
    name: str = Name
    target_id: int | None = None
    lethality: int = Field(default=30, ge=1, le=PERCENT)
    virulence: int = Field(default=40, ge=1, le=PERCENT)


class DesignCureInput(ToolInput):
    disease_id: int
    line_id: int


class LivingWorksInput(ToolInput):
    method: LivingMethod
    name: str = Name


class LicenseLineInput(ToolInput):
    line_id: int
    fee: int = Field(default=10, ge=0, le=10000)


class CloneLawInput(ToolInput):
    level: Literal["banned", "licensed", "free"]


async def attempt[T](declined: MortalResult, step: Awaitable[T]) -> T:
    try:
        return await step
    except (ValidationFailedError, NotFoundError) as error:
        fail(declined, why=str(error).rstrip("."))


def unheld(call: MortalCall, declined: MortalResult) -> None:
    if held(call.me.id):
        fail(declined, why="a stronger hand holds you")


async def my_line(call: MortalCall, line_id: int, declined: MortalResult) -> LivingLineRow:
    line = await call.session.get(LivingLineRow, line_id)
    if line is None or call.me.id not in {line.owner_node_id, line.maker_node_id}:
        fail(declined, why="you hold no such line")
    return line


def traits(picks: list[TraitPick]) -> tuple[tuple[LineTrait, int], ...]:
    return tuple((pick.trait, pick.strength) for pick in picks)


async def breed_line(call: MortalCall, args: BreedLineInput) -> str:
    unheld(call, MortalResult.LINE_DECLINED)
    species = await living_entity(call.session, args.species_id)
    if species is None:
        fail(MortalResult.LINE_DECLINED, why="there is no such kind of life to breed from")
    draft = LineDraft(args.name, CultivationMethod.SELECTIVE_BREEDING, call.me.id, call.me.id, (species.id,), traits(args.traits))
    line = await attempt(MortalResult.LINE_DECLINED, make_line(call.tick, draft))
    await call.record("tools.mortal.line_made", roles={IncidentRole.ACTOR: call.me.id}, facts={"line": line.name})
    return result(MortalResult.LINE_MADE, name=line.name, line=line.id, outcome=spoken(line.outcome))


async def design_line(call: MortalCall, args: DesignLineInput) -> str:
    unheld(call, MortalResult.LINE_DECLINED)
    draft = LineDraft(args.name, args.method, call.me.id, call.me.id, tuple(args.source_ids), traits(args.traits), args.fertility)
    line = await attempt(MortalResult.LINE_DECLINED, make_line(call.tick, draft))
    await call.record("tools.mortal.line_made", roles={IncidentRole.ACTOR: call.me.id}, facts={"line": line.name})
    return result(MortalResult.LINE_MADE, name=line.name, line=line.id, outcome=spoken(line.outcome))


async def bank_sample(call: MortalCall, args: BankSampleInput) -> str:
    unheld(call, MortalResult.SAMPLE_DECLINED)
    bank = await call.session.get(GeneBankRow, args.bank_id)
    works = await call.session.get(EntityRow, args.bank_id)
    if bank is None or works is None or (bank.holder_node_id != call.me.id and works.location_id != call.me.location_id):
        fail(MortalResult.SAMPLE_DECLINED, why="there is no bank of life you can reach")
    organism = await living_entity(call.session, args.organism_id)
    if organism is None:
        fail(MortalResult.SAMPLE_DECLINED, why="there is nothing living there to sample")
    quality = clamp_percent(PERCENT // 2 + await best_skill(call.session, call.me.id, SAMPLE_SKILLS) // 2)
    await attempt(MortalResult.SAMPLE_DECLINED, sampled(call.tick, bank.structure_entity_id, organism.id, quality))
    await call.record(
        "tools.mortal.sample_banked",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: organism.id, IncidentRole.DESTINATION: bank.structure_entity_id},
        facts={"quality": quality},
    )
    return result(MortalResult.SAMPLE_BANKED, name=organism.name, quality=quality)


async def plant_line(call: MortalCall, args: LineInput) -> str:
    unheld(call, MortalResult.PLANTING_DECLINED)
    line = await my_line(call, args.line_id, MortalResult.PLANTING_DECLINED)
    region = (await RegionAtlas.load(call.session)).top_region(call.me.id)
    if region is None or held(region):
        fail(MortalResult.PLANTING_DECLINED, why="you have no land to plant in")
    yields = set(await call.session.scalars(select(SpeciesProductRow.commodity).where(SpeciesProductRow.species_entity_id == line.species_entity_id)))
    land = await call.session.get(RegionEnvironmentRow, region)
    kind = kind_of({commodity for commodity in yields if commodity is not None}, land, call.rules.commons.woods_forest)
    row = await attempt(
        MortalResult.PLANTING_DECLINED,
        plant(call.tick, region, kind, species_id=line.species_entity_id, owner_id=call.me.id, area=call.rules.perennials.area, line_id=line.id),
    )
    await call.record("tools.mortal.line_planted", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: region}, facts={"line": line.name})
    return result(MortalResult.LINE_PLANTED, name=line.name, planting=row.id)


async def raise_line(call: MortalCall, args: SampleInput) -> str:
    unheld(call, MortalResult.LINE_DECLINED)
    sample = await call.session.get(GeneBankSampleRow, args.sample_id)
    bank = await call.session.get(GeneBankRow, sample.bank_entity_id) if sample is not None else None
    if sample is None or bank is None or bank.holder_node_id not in {call.me.id, call.me.location_id}:
        fail(MortalResult.LINE_DECLINED, why="you hold no such sample")
    line = await attempt(MortalResult.LINE_DECLINED, control.raise_line(call.tick, sample.id, call.me.id))
    await call.record("tools.mortal.line_made", roles={IncidentRole.ACTOR: call.me.id}, facts={"line": line.name})
    return result(MortalResult.LINE_MADE, name=line.name, line=line.id, outcome=spoken(line.outcome))


async def growing(call: MortalCall, args: GrowInput, declined: MortalResult) -> Growing:
    unheld(call, declined)
    if args.line_id is not None:
        await my_line(call, args.line_id, declined)
    return Growing(call.me, args.line_id, args.name)


async def grow_structure_tool(call: MortalCall, args: GrowInput) -> str:
    work = await attempt(MortalResult.GROWING_DECLINED, grow_structure(call.tick, await growing(call, args, MortalResult.GROWING_DECLINED)))
    await call.record("tools.mortal.grown", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: work.id}, facts={"made": EntityType.STRUCTURE})
    return result(MortalResult.GROWN, name=work.name)


async def grow_vessel_tool(call: MortalCall, args: GrowInput) -> str:
    vessel = await attempt(MortalResult.GROWING_DECLINED, grow_vessel(call.tick, await growing(call, args, MortalResult.GROWING_DECLINED)))
    await call.record("tools.mortal.grown", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: vessel.id}, facts={"made": vessel.entity_type})
    return result(MortalResult.GROWN, name=vessel.name)


async def grow_gear_tool(call: MortalCall, args: GrowInput) -> str:
    gear = await attempt(MortalResult.GROWING_DECLINED, grow_gear(call.tick, await growing(call, args, MortalResult.GROWING_DECLINED)))
    await call.record("tools.mortal.grown", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: gear.id}, facts={"made": gear.entity_type})
    return result(MortalResult.GROWN, name=gear.name)


async def grow_organ_tool(call: MortalCall, args: GrowOrganInput) -> str:
    unheld(call, MortalResult.ORGAN_DECLINED)
    bearer = await living_entity(call.session, args.bearer_id) if args.bearer_id is not None else call.me
    if bearer is None or held(bearer.id) or (bearer.id != call.me.id and bearer.location_id != call.me.location_id):
        fail(MortalResult.ORGAN_DECLINED, why="there is no one here to grow it for")
    await grow_organ(call.tick, bearer, args.slot, args.kind, call.me.id)
    await call.record(
        "tools.mortal.organ_grown", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PATIENT: bearer.id}, facts={"slot": args.slot, "augment": args.kind}
    )
    return result(MortalResult.ORGAN_GROWN, name=bearer.name)


async def clone_tool(call: MortalCall, args: CloneInput) -> str:
    unheld(call, MortalResult.CLONE_DECLINED)
    source = await living_entity(call.session, args.source_id)
    if source is None or (source.id != call.me.id and source.location_id != call.me.location_id):
        fail(MortalResult.CLONE_DECLINED, why="there is no body here to copy")
    copy = await attempt(MortalResult.CLONE_DECLINED, clone(call.tick, source.id, call.me.id))
    call.target(copy.id)
    await call.record("tools.mortal.cloned", roles={IncidentRole.MAKER: call.me.id, IncidentRole.ORIGIN: source.id, IncidentRole.PRODUCT: copy.id})
    return result(MortalResult.CLONED, name=copy.name)


async def host_symbiont(call: MortalCall, args: HostSymbiontInput) -> str:
    unheld(call, MortalResult.SYMBIONT_DECLINED)
    line = await my_line(call, args.line_id, MortalResult.SYMBIONT_DECLINED)
    await attempt(
        MortalResult.SYMBIONT_DECLINED,
        control.host(call.tick, call.me.id, line_id=line.id, placement=args.placement, relation=args.relation, strength=PERCENT // 3),
    )
    await call.record(
        "tools.mortal.symbiont_hosted",
        roles={IncidentRole.ACTOR: call.me.id},
        facts={"line": line.name, "placement": args.placement, "relation": args.relation},
    )
    return result(MortalResult.SYMBIONT_HOSTED, name=line.name)


async def remove_symbiont_tool(call: MortalCall, args: SymbiontInput) -> str:
    unheld(call, MortalResult.SYMBIONT_DECLINED)
    row = await call.session.get(SymbiontRow, args.symbiont_id)
    if row is None or row.host_node_id != call.me.id:
        fail(MortalResult.SYMBIONT_DECLINED, why="nothing such lives within you")
    await remove_symbiont(call.tick, row)
    await call.record("tools.mortal.symbiont_removed", roles={IncidentRole.ACTOR: call.me.id}, facts={"relation": row.relation})
    return result(MortalResult.SYMBIONT_REMOVED)


async def design_disease_tool(call: MortalCall, args: DesignDiseaseInput) -> str:
    unheld(call, MortalResult.DISEASE_DESIGN_DECLINED)
    disease = await attempt(
        MortalResult.DISEASE_DESIGN_DECLINED,
        design_disease(call.tick, call.me, args.name, target_id=args.target_id, lethality=args.lethality, virulence=args.virulence),
    )
    await call.record(
        "tools.mortal.disease_designed",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: disease.id, IncidentRole.TARGET: args.target_id},
        facts={"lethality": args.lethality, "virulence": args.virulence},
    )
    return result(MortalResult.DISEASE_DESIGNED, name=disease.name)


async def design_cure_tool(call: MortalCall, args: DesignCureInput) -> str:
    unheld(call, MortalResult.CURE_DECLINED)
    line = await my_line(call, args.line_id, MortalResult.CURE_DECLINED)
    disease = await living_entity(call.session, args.disease_id)
    if disease is None:
        fail(MortalResult.CURE_DECLINED, why="there is no such sickness")
    await attempt(MortalResult.CURE_DECLINED, design_cure(call.tick, call.me, disease.id, line.id))
    await call.record("tools.mortal.cure_cultured", roles={IncidentRole.HEALER: call.me.id, IncidentRole.TARGET: disease.id, IncidentRole.INSTRUMENT: line.id})
    return result(MortalResult.CURE_CULTURED, name=disease.name)


async def found_living_works_tool(call: MortalCall, args: LivingWorksInput) -> str:
    unheld(call, MortalResult.GROWING_DECLINED)
    works = await attempt(MortalResult.GROWING_DECLINED, found_living_works(call.tick, call.me, MethodKind(args.method), args.name))
    await call.record("tools.mortal.grown", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: works.id}, facts={"made": works.entity_type})
    return result(MortalResult.GROWN, name=works.name)


async def release_line(call: MortalCall, args: LineInput) -> str:
    unheld(call, MortalResult.RELEASE_DECLINED)
    line = await my_line(call, args.line_id, MortalResult.RELEASE_DECLINED)
    await attempt(MortalResult.RELEASE_DECLINED, control.release(call.tick, line))
    await call.record("tools.mortal.line_released", roles={IncidentRole.ACTOR: call.me.id}, facts={"line": line.name})
    return result(MortalResult.LINE_RELEASED, name=line.name)


async def raise_sapience_tool(call: MortalCall, args: LineInput) -> str:
    unheld(call, MortalResult.SAPIENCE_DECLINED)
    line = await my_line(call, args.line_id, MortalResult.SAPIENCE_DECLINED)
    skill = await best_skill(call.session, call.me.id, (SkillKind.SCIENCE, SkillKind.SPELLCRAFT, SkillKind.MEDICINE))
    trait = await attempt(MortalResult.SAPIENCE_DECLINED, raise_sapience(call.tick, line, skill))
    await call.record("tools.mortal.sapience_shaped", roles={IncidentRole.ACTOR: call.me.id}, facts={"line": line.name})
    return result(MortalResult.SAPIENCE_SHAPED, name=line.name, strength=trait.strength)


async def license_line_tool(call: MortalCall, args: LicenseLineInput) -> str:
    unheld(call, MortalResult.LINE_LICENCE_DECLINED)
    line = await call.session.get(LivingLineRow, args.line_id)
    if line is None or line.owner_node_id in {None, call.me.id}:
        fail(MortalResult.LINE_LICENCE_DECLINED, why="there is no line of another to license")
    await attempt(MortalResult.LINE_LICENCE_DECLINED, license_line(call.tick, line, call.me, args.fee))
    await call.record("tools.mortal.line_licensed", roles={IncidentRole.ACTOR: call.me.id}, facts={"line": line.name})
    return result(MortalResult.LINE_LICENSED, name=line.name)


async def set_clone_law(call: MortalCall, args: CloneLawInput) -> str:
    return await enact_law(call, EnactLawInput(kind=LawKind.CLONE_LAW, params={"level": args.level}))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.BREED_LINE, mortal, BreedLineInput, meta, breed_line),
        ToolSpec(MortalToolId.DESIGN_LINE, mortal, DesignLineInput, meta, design_line),
        ToolSpec(MortalToolId.BANK_SAMPLE, mortal, BankSampleInput, meta, bank_sample),
        ToolSpec(MortalToolId.PLANT_LINE, mortal, LineInput, meta, plant_line),
        ToolSpec(MortalToolId.RAISE_LINE, mortal, SampleInput, meta, raise_line),
        ToolSpec(MortalToolId.GROW_STRUCTURE, mortal, GrowInput, meta, grow_structure_tool),
        ToolSpec(MortalToolId.GROW_VESSEL, mortal, GrowInput, meta, grow_vessel_tool),
        ToolSpec(MortalToolId.GROW_GEAR, mortal, GrowInput, meta, grow_gear_tool),
        ToolSpec(MortalToolId.GROW_ORGAN, mortal, GrowOrganInput, meta, grow_organ_tool),
        ToolSpec(MortalToolId.CLONE, mortal, CloneInput, meta, clone_tool),
        ToolSpec(MortalToolId.HOST_SYMBIONT, mortal, HostSymbiontInput, meta, host_symbiont),
        ToolSpec(MortalToolId.REMOVE_SYMBIONT, mortal, SymbiontInput, meta, remove_symbiont_tool),
        ToolSpec(MortalToolId.DESIGN_DISEASE, mortal, DesignDiseaseInput, meta, design_disease_tool),
        ToolSpec(MortalToolId.DESIGN_CURE, mortal, DesignCureInput, meta, design_cure_tool),
        ToolSpec(MortalToolId.FOUND_LIVING_WORKS, mortal, LivingWorksInput, meta, found_living_works_tool),
        ToolSpec(MortalToolId.RELEASE_LINE, mortal, LineInput, meta, release_line),
        ToolSpec(MortalToolId.RAISE_SAPIENCE, mortal, LineInput, meta, raise_sapience_tool),
        ToolSpec(MortalToolId.LICENSE_LINE, mortal, LicenseLineInput, meta, license_line_tool),
        ToolSpec(MortalToolId.SET_CLONE_LAW, mortal, CloneLawInput, meta, set_clone_law),
    ]
