from collections.abc import Mapping
from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.affairs import NobleDemandRow, TaxPolicyRow
from aerona.db.tables.agrarian import LandRingRow
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.collective import ArmsRow
from aerona.db.tables.culture import SpeakerCohortRow
from aerona.db.tables.ecology import SpeciesUseKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.integrity import StructureSectionRow
from aerona.db.tables.mind import CultureHonourRow, FearRow, PressureRow, WantRow
from aerona.db.tables.polity import HouseProfileRow, OfficeRow, PolityProfileRow, VassalageRow
from aerona.db.tables.relations import SocialCircleRow
from aerona.db.tables.society_depth import DriftCauseRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.agrarian import LandUseRing
from aerona.domain.enums.body import MaimedKind
from aerona.domain.enums.collective import (
    ArmsRim,
    ChargeArrangement,
    DatingSystemKind,
    HeraldicCharge,
    HeraldicDivision,
    HeraldryHolderKind,
    NormBehaviour,
    NormSituation,
    PartitionLine,
    RoleEligibility,
    RoleKind,
    ShieldShape,
    SupporterPose,
    Tincture,
)
from aerona.domain.enums.cosmography import OmenReading
from aerona.domain.enums.culture import CustomCatalog, LanguageRegister, SpeakerKind
from aerona.domain.enums.cycles import LegacyKind, ReproductiveCaste
from aerona.domain.enums.discovery import AgeKind, BlueprintKind
from aerona.domain.enums.ecology import AnimalRole
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.integrity import SectionState
from aerona.domain.enums.law_depth import JurisdictionClaim
from aerona.domain.enums.military import CommanderTrait
from aerona.domain.enums.mind import EthicalStance, HonourModel, PressureKind, WantKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import CrewStation, PointOfSail, ShotKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.relations import CircleKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.enums.statecraft import NobleWant, SubjectKind, TaxKind
from aerona.domain.enums.structure import StructureSection
from aerona.domain.enums.urban import RacketKind
from aerona.domain.enums.vehicles import VehicleSection
from aerona.engine.agrarian.control import set_ring
from aerona.engine.body.customs import people_of
from aerona.engine.collective.control import set_dating, set_role
from aerona.engine.collective.dating import current_year
from aerona.engine.collective.norms import write_norm
from aerona.engine.cosmos.control import set_reading
from aerona.engine.cycles.control import set_caste, set_legacy
from aerona.engine.cycles.legacy import legacy_key
from aerona.engine.law.control import set_claim
from aerona.engine.lore.blueprints import draw
from aerona.engine.lore.culture_control import set_register
from aerona.engine.lore.discovery_control import set_era
from aerona.engine.lore.kinds import create_kind
from aerona.engine.military.control import set_trait
from aerona.engine.operations.control import set_crew, set_ship
from aerona.engine.polity.control import create_vassalage
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import FactInput, RoleValue
from aerona.engine.sacred.places import town_of
from aerona.engine.structures.control import edit_section
from aerona.engine.urban.control import set_racket
from aerona.engine.vehicles.control import set_vessel_section
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

NAME_MAX = 120
TEXT_MAX = 600
LEVY_MAX = 60
CYCLE_MAX = 1000
AGE_MAX = 120
CREW_MAX = 2000
TRIBUTE_PCT = 10
LEVY_PCT = 10
RACKET_INCOME = 5
TONGUE_GAIN = 5
CLAIM_STRENGTH = 30
FEAR_EASE = 20
PRESSURE_EASE = 15
REPAIR = 20
MOVEMENT_SUPPORT = 10


class ArmsInput(ToolInput):
    field: Tincture
    shape: ShieldShape = ShieldShape.HEATER
    division: HeraldicDivision = HeraldicDivision.PLAIN
    line: PartitionLine = PartitionLine.STRAIGHT
    second: Tincture | None = None
    charge: HeraldicCharge = HeraldicCharge.NONE
    charge_tincture: Tincture | None = None
    rim: ArmsRim = ArmsRim.LINE
    arrangement: ChargeArrangement | None = None
    supporter: HeraldicCharge = HeraldicCharge.NONE
    supporter_pose: SupporterPose | None = None
    motto: str | None = Field(default=None, max_length=200)


class DatingInput(ToolInput):
    kind: DatingSystemKind
    cycle_years: int = Field(default=60, ge=1, le=CYCLE_MAX)


class NormInput(ToolInput):
    situation: NormSituation
    behaviour: NormBehaviour
    stance: EthicalStance


class RoleInput(ToolInput):
    role: RoleKind
    eligibility: RoleEligibility
    min_age: int = Field(default=16, ge=0, le=AGE_MAX)
    stance: EthicalStance


class ReadingInput(ToolInput):
    celestial_id: int
    reading: OmenReading


class RegisterInput(ToolInput):
    speech: LanguageRegister
    language_id: int


class TongueInput(ToolInput):
    language_id: int
    kind: SpeakerKind = SpeakerKind.LITURGICAL


class LegacyInput(ToolInput):
    predecessor_id: int
    kind: LegacyKind


class CasteInput(ToolInput):
    mortal_id: int
    caste: ReproductiveCaste


class AgeInput(ToolInput):
    age: AgeKind


class DesignInput(ToolInput):
    kind: BlueprintKind
    subject: str = Field(min_length=2, max_length=NAME_MAX)


class UseInput(ToolInput):
    use: AnimalRole
    name: str = Field(min_length=2, max_length=NAME_MAX)
    description: str | None = Field(default=None, max_length=TEXT_MAX)


class MovementInput(ToolInput):
    cause: MovementCause


class ClaimInput(ToolInput):
    realm_id: int
    claim: JurisdictionClaim


class TraitInput(ToolInput):
    trait: CommanderTrait


class FearInput(ToolInput):
    fear_id: int


class WantInput(ToolInput):
    kind: WantKind
    target_id: int | None = None


class PressureInput(ToolInput):
    pressure: PressureKind


class HonourInput(ToolInput):
    model: HonourModel


class DriftInput(ToolInput):
    cause: DriftCause


class StationInput(ToolInput):
    vessel_id: int
    station: CrewStation
    count: int = Field(ge=0, le=CREW_MAX)


class SailInput(ToolInput):
    vessel_id: int
    point_of_sail: PointOfSail
    shot: ShotKind


class CircleInput(ToolInput):
    kind: CircleKind


class DemandInput(ToolInput):
    want: NobleWant


class FealtyInput(ToolInput):
    overlord_id: int
    kind: SubjectKind = SubjectKind.VASSAL


class LevyInput(ToolInput):
    kind: TaxKind
    rate: int = Field(ge=0, le=LEVY_MAX)


class RacketInput(ToolInput):
    kind: RacketKind


class RefitInput(ToolInput):
    vessel_id: int
    section: VehicleSection


class ShoreInput(ToolInput):
    structure_id: int
    section: StructureSection


class RingInput(ToolInput):
    ring: LandUseRing


class MaimedInput(ToolInput):
    kind: MaimedKind


class CustomInput(ToolInput):
    catalog: CustomCatalog
    base: str = Field(min_length=1, max_length=NAME_MAX)
    name: str = Field(min_length=2, max_length=NAME_MAX)
    description: str = Field(default="", max_length=TEXT_MAX)


async def ruled_realm(call: MortalCall) -> EntityRow:
    polity_id = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    realm = await living_entity(call.session, polity_id) if polity_id is not None else None
    if realm is None:
        fail(MortalResult.WAY_REFUSED, why="you rule no realm")
    if held(realm.id):
        fail(MortalResult.WAY_REFUSED, why="the gods hold your realm as it is")
    return realm


async def my_people(call: MortalCall) -> EntityRow:
    people = await people_of(call.session, call.me)
    if people is None:
        fail(MortalResult.WAY_REFUSED, why="you belong to no people")
    if held(people.id):
        fail(MortalResult.WAY_REFUSED, why="the gods hold your people as they are")
    return people


async def my_town(call: MortalCall) -> EntityRow:
    town = await town_of(call.session, call.me)
    if town is None:
        fail(MortalResult.WAY_REFUSED, why="you stand in no town")
    if held(town.id):
        fail(MortalResult.WAY_REFUSED, why="the gods hold your town as it is")
    return town


async def led_faction(call: MortalCall) -> FactionProfileRow:
    row = await call.session.scalar(
        select(FactionProfileRow).where(FactionProfileRow.leader_entity_id == call.me.id).order_by(FactionProfileRow.faction_entity_id).limit(1)
    )
    if row is None:
        fail(MortalResult.WAY_REFUSED, why="you lead no faction")
    if held(row.faction_entity_id):
        fail(MortalResult.WAY_REFUSED, why="the gods hold your faction as it is")
    return row


async def recorded(call: MortalCall, key: str, what: str, *, roles: Mapping[IncidentRole, RoleValue], facts: Mapping[str, FactInput]) -> str:
    await call.record(key, roles={IncidentRole.ACTOR: call.me.id, **roles}, facts=facts)
    return result(MortalResult.WAY_TAKEN, what=what)


async def take_arms(call: MortalCall, args: ArmsInput) -> str:
    house = await call.session.scalar(select(HouseProfileRow).where(HouseProfileRow.head_entity_id == call.me.id).limit(1))
    if house is not None and not held(house.house_entity_id):
        holder_id, kind = house.house_entity_id, HeraldryHolderKind.HOUSE
    else:
        holder_id, kind = (await ruled_realm(call)).id, HeraldryHolderKind.POLITY
    row = await call.session.get(ArmsRow, holder_id)
    if row is None:
        row = ArmsRow(holder_entity_id=holder_id, holder_kind=kind, field=args.field, since_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    elif "field" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold these arms as they are")
    row.field, row.shape, row.division, row.line, row.second = args.field, args.shape, args.division, args.line, args.second
    row.charge, row.charge_tincture, row.rim, row.motto, row.supporter = args.charge, args.charge_tincture, args.rim, args.motto, args.supporter
    if args.arrangement is not None:
        row.arrangement = args.arrangement
    if args.supporter_pose is not None:
        row.supporter_pose = args.supporter_pose
    await call.session.flush()
    call.target(holder_id)
    what = await call.record("tools.mortal.take_arms", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: holder_id}, facts={"field": args.field})
    return result(MortalResult.WAY_TAKEN, what=what)


async def reckon_years(call: MortalCall, args: DatingInput) -> str:
    realm = await ruled_realm(call)
    await set_dating(call.tick, realm.id, args.kind, anchor_year=await current_year(call.session), label_id=call.me.id, cycle_years=args.cycle_years)
    call.target(realm.id)
    await call.record("tools.mortal.reckon_years", roles={IncidentRole.AUTHORITY: realm.id, IncidentRole.ACTOR: call.me.id}, facts={"dating": args.kind})
    return result(MortalResult.WAY_TAKEN, what=f"years counted by {spoken(args.kind)} in {realm.name}")


async def speak_for_norm(call: MortalCall, args: NormInput) -> str:
    people = await my_people(call)
    row = await write_norm(call.tick, people.id, args.situation, args.behaviour, args.stance, cause=f"{call.me.name} spoke for it")
    if row is None or row.stance is not args.stance:
        fail(MortalResult.WAY_REFUSED, why="the custom is held as it is")
    call.target(people.id)
    return await recorded(
        call,
        "tools.mortal.speak_for_norm",
        f"{spoken(args.behaviour)} in {spoken(args.situation)} held {spoken(args.stance)}",
        roles={IncidentRole.AUTHORITY: people.id},
        facts={"situation": args.situation, "behaviour": args.behaviour, "stance": args.stance},
    )


async def set_role_custom(call: MortalCall, args: RoleInput) -> str:
    await ruled_realm(call)
    people = await my_people(call)
    try:
        await set_role(call.tick, people.id, args.role, eligibility=args.eligibility, min_age=args.min_age, classes=[], stance=args.stance)
    except (NotFoundError, ValidationFailedError) as error:
        fail(MortalResult.WAY_REFUSED, why=str(error).rstrip("."))
    call.target(people.id)
    return await recorded(
        call,
        "tools.mortal.set_role_custom",
        f"who may be {spoken(args.role)}: {spoken(args.eligibility)}",
        roles={IncidentRole.AUTHORITY: people.id},
        facts={"role": args.role, "eligibility": args.eligibility, "min_age": args.min_age, "stance": args.stance},
    )


async def read_the_sky(call: MortalCall, args: ReadingInput) -> str:
    people = await my_people(call)
    body = await living_entity(call.session, args.celestial_id)
    if body is None or body.entity_type is not EntityType.CELESTIAL or body.world_id != call.me.world_id:
        fail(MortalResult.WAY_REFUSED, why="no such body stands in your sky")
    await set_reading(call.tick, body.id, people.id, args.reading)
    call.target(body.id)
    return await recorded(
        call,
        "tools.mortal.read_the_sky",
        f"{body.name} read as {spoken(args.reading)}",
        roles={IncidentRole.SUBJECT: body.id, IncidentRole.AUTHORITY: people.id},
        facts={"reading": args.reading},
    )


async def set_speech(call: MortalCall, args: RegisterInput) -> str:
    await ruled_realm(call)
    people = await my_people(call)
    language = await living_entity(call.session, args.language_id)
    if language is None or language.entity_type is not EntityType.LANGUAGE:
        fail(MortalResult.WAY_REFUSED, why="there is no such living language")
    await set_register(call.tick, people.id, args.speech, language.id, hold=False)
    call.target(language.id)
    return await recorded(
        call,
        "tools.mortal.set_speech",
        f"{language.name} as the tongue for {spoken(args.speech)}",
        roles={IncidentRole.AUTHORITY: people.id, IncidentRole.INSTRUMENT: language.id},
        facts={"speech": args.speech},
    )


async def teach_tongue(call: MortalCall, args: TongueInput) -> str:
    town = await my_town(call)
    language = await living_entity(call.session, args.language_id)
    if language is None or language.entity_type is not EntityType.LANGUAGE:
        fail(MortalResult.WAY_REFUSED, why="there is no such living language")
    row = await call.session.get(SpeakerCohortRow, (town.id, language.id, args.kind))
    if row is None:
        row = SpeakerCohortRow(community_entity_id=town.id, language_entity_id=language.id, kind=args.kind, share=0, since_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    elif "share" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold that tongue's speakers as they are")
    row.share = clamp_int(row.share + TONGUE_GAIN, 0, PERCENT)
    await call.session.flush()
    call.target(town.id)
    await call.record(
        "tools.mortal.teach_tongue",
        roles={IncidentRole.TEACHER: call.me.id, IncidentRole.LEARNER: town.id, IncidentRole.SUBJECT: language.id},
        facts={"use": args.kind, "share": row.share},
    )
    return result(MortalResult.WAY_TAKEN, what=f"{language.name} taught in {town.name} for {spoken(args.kind)} use")


async def keep_legacy(call: MortalCall, args: LegacyInput) -> str:
    people = await my_people(call)
    predecessor = await call.session.get(EntityRow, args.predecessor_id)
    if predecessor is None or predecessor.entity_type is not EntityType.PEOPLE or predecessor.id == people.id:
        fail(MortalResult.WAY_REFUSED, why="that is no people before yours")
    key = await legacy_key(call.tick, args.kind, people, predecessor)
    if key is None:
        fail(MortalResult.WAY_REFUSED, why=f"{predecessor.name} left nothing of that kind to keep")
    await set_legacy(call.tick, people.id, args.kind, key, predecessor.id)
    call.target(people.id)
    return await recorded(
        call,
        "tools.mortal.keep_legacy",
        f"the {spoken(args.kind)} of {predecessor.name}",
        roles={IncidentRole.HEIR: people.id, IncidentRole.PREDECESSOR: predecessor.id},
        facts={"legacy": args.kind},
    )


async def assign_caste(call: MortalCall, args: CasteInput) -> str:
    await ruled_realm(call)
    people = await my_people(call)
    target = await living_entity(call.session, args.mortal_id)
    if target is None or target.entity_type is not EntityType.MORTAL or held(target.id):
        fail(MortalResult.WAY_REFUSED, why="there is no such living mortal")
    found = await people_of(call.session, target)
    if found is None or found.id != people.id:
        fail(MortalResult.WAY_REFUSED, why=f"{target.name} is not of your people")
    await set_caste(call.tick, target.id, args.caste)
    call.target(target.id)
    return await recorded(
        call, "tools.mortal.assign_caste", f"{target.name} as {spoken(args.caste)}", roles={IncidentRole.TARGET: target.id}, facts={"caste": args.caste}
    )


async def proclaim_age(call: MortalCall, args: AgeInput) -> str:
    realm = await ruled_realm(call)
    await set_era(call.tick, realm.id, None, args.age, hold=False)
    call.target(realm.id)
    return await recorded(
        call, "tools.mortal.proclaim_age", f"an age of {spoken(args.age)} in {realm.name}", roles={IncidentRole.AUTHORITY: realm.id}, facts={"age": args.age}
    )


async def draw_blueprint(call: MortalCall, args: DesignInput) -> str:
    row = await draw(call.tick, call.me, args.kind, args.subject.strip())
    if row is None:
        fail(MortalResult.WAY_REFUSED, why="you hold that design already")
    await call.record("tools.mortal.draw_blueprint", roles={IncidentRole.MAKER: call.me.id}, facts={"design": args.kind, "purpose": args.subject.strip()})
    return result(MortalResult.WAY_TAKEN, what=f"a design of {spoken(args.kind)} for {args.subject.strip()}")


async def devise_use(call: MortalCall, args: UseInput) -> str:
    await my_people(call)
    row = SpeciesUseKindRow(name=args.name.strip(), base_use=args.use, output_pct=PERCENT, description=args.description, locked=[])
    call.session.add(row)
    await call.session.flush()
    return await recorded(
        call, "tools.mortal.devise_use", f"{row.name}, a way to keep beasts for {spoken(args.use)}", roles={}, facts={"name": row.name, "use": args.use}
    )


async def raise_movement(call: MortalCall, args: MovementInput) -> str:
    faction = await led_faction(call)
    row = await call.session.get(MovementProfileRow, faction.faction_entity_id)
    if row is None:
        row = MovementProfileRow(faction_entity_id=faction.faction_entity_id, cause=args.cause, founded_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    elif "cause" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold your movement's cause as it is")
    row.cause = args.cause
    row.support = clamp_int(row.support + MOVEMENT_SUPPORT, 0, PERCENT)
    await call.session.flush()
    call.target(faction.faction_entity_id)
    return await recorded(
        call,
        "tools.mortal.raise_movement",
        f"a movement for {spoken(args.cause)}",
        roles={IncidentRole.PRODUCT: faction.faction_entity_id},
        facts={"cause": args.cause, "support": row.support},
    )


async def claim_courts(call: MortalCall, args: ClaimInput) -> str:
    realm = await ruled_realm(call)
    other = await living_entity(call.session, args.realm_id)
    if other is None or other.entity_type is not EntityType.POLITY or other.id == realm.id or held(other.id):
        fail(MortalResult.WAY_REFUSED, why="that is no other realm")
    await set_claim(call.tick, other.id, realm.id, args.claim, CLAIM_STRENGTH)
    call.target(other.id)
    return await recorded(
        call,
        "tools.mortal.claim_courts",
        f"a claim of {spoken(args.claim)} over {other.name}",
        roles={IncidentRole.AUTHORITY: realm.id, IncidentRole.TARGET: other.id},
        facts={"claim": args.claim},
    )


async def drill_trait(call: MortalCall, args: TraitInput) -> str:
    if await call.session.scalar(select(ArmyRow.entity_id).where(ArmyRow.commander_entity_id == call.me.id).limit(1)) is None:
        fail(MortalResult.WAY_REFUSED, why="you command no army")
    if not await set_trait(call.tick, call.me.id, args.trait, held=True):
        fail(MortalResult.WAY_REFUSED, why="you have that way of command already")
    await call.record("tools.mortal.drill_trait", roles={IncidentRole.LEADER: call.me.id}, facts={"trait": args.trait})
    return result(MortalResult.WAY_TAKEN, what=f"a commander's way: {spoken(args.trait)}")


async def face_fear(call: MortalCall, args: FearInput) -> str:
    row = await call.session.get(FearRow, args.fear_id)
    if row is None or row.holder_node_id != call.me.id:
        fail(MortalResult.WAY_REFUSED, why="you hold no such fear")
    if "strength" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold that fear in you")
    row.strength = clamp_int(row.strength - FEAR_EASE, 0, PERCENT)
    fear, strength = row.kind, row.strength
    if row.strength == 0:
        await call.session.delete(row)
    await call.session.flush()
    return await recorded(call, "tools.mortal.face_fear", f"the fear of {spoken(fear)}", roles={}, facts={"fear": fear, "strength": strength})


async def take_up_want(call: MortalCall, args: WantInput) -> str:
    target = await living_entity(call.session, args.target_id) if args.target_id is not None else None
    if args.target_id is not None and target is None:
        fail(MortalResult.WAY_REFUSED, why="there is no such living thing to want")
    call.session.add(WantRow(holder_node_id=call.me.id, kind=args.kind, target_node_id=args.target_id, epoch=call.tick.epoch, locked=[]))
    await call.session.flush()
    return await recorded(
        call,
        "tools.mortal.take_up_want",
        f"a want of {spoken(args.kind)}",
        roles={IncidentRole.TARGET: target.id if target is not None else None},
        facts={"want": args.kind},
    )


async def ease_pressure(call: MortalCall, args: PressureInput) -> str:
    row = await call.session.get(PressureRow, (call.me.id, args.pressure))
    if row is None or row.value <= 0:
        fail(MortalResult.WAY_REFUSED, why="that does not weigh on you")
    row.value = max(0, row.value - PRESSURE_EASE)
    await call.session.flush()
    return await recorded(call, "tools.mortal.ease_pressure", f"{spoken(args.pressure)} eased", roles={}, facts={"pressure": args.pressure, "left": row.value})


async def teach_honour(call: MortalCall, args: HonourInput) -> str:
    await ruled_realm(call)
    people = await my_people(call)
    row = await call.session.get(CultureHonourRow, people.id)
    if row is None:
        row = CultureHonourRow(entity_id=people.id, model=args.model, locked=[])
        call.session.add(row)
    elif "model" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold your people's honour as it is")
    row.model = args.model
    await call.session.flush()
    call.target(people.id)
    return await recorded(
        call,
        "tools.mortal.teach_honour",
        f"honour as {spoken(args.model)} among {people.name}",
        roles={IncidentRole.LEARNER: people.id},
        facts={"honour": args.model},
    )


async def resist_drift(call: MortalCall, args: DriftInput) -> str:
    town = await my_town(call)
    rows = list(await call.session.scalars(select(DriftCauseRow).where(DriftCauseRow.community_entity_id == town.id, DriftCauseRow.cause == args.cause)))
    rows = [row for row in rows if row.amount != 0]
    if not rows:
        fail(MortalResult.WAY_REFUSED, why="nothing of that kind moves your town's ways")
    for row in rows:
        row.amount = row.amount // 2
    await call.session.flush()
    call.target(town.id)
    return await recorded(
        call,
        "tools.mortal.resist_drift",
        f"{town.name} held against the change {spoken(args.cause)} drove",
        roles={IncidentRole.PLACE: town.id},
        facts={"cause": args.cause, "causes": len(rows)},
    )


async def my_vessel(call: MortalCall, vessel_id: int) -> EntityRow:
    vessel = await living_entity(call.session, vessel_id)
    if vessel is None or vessel.entity_type is not EntityType.VESSEL or held(vessel.id):
        fail(MortalResult.WAY_REFUSED, why="there is no such vessel")
    if vessel.location_id not in {call.me.location_id, call.me.id} and call.me.location_id != vessel.id:
        fail(MortalResult.WAY_REFUSED, why=f"{vessel.name} does not carry you")
    return vessel


async def man_station(call: MortalCall, args: StationInput) -> str:
    vessel = await my_vessel(call, args.vessel_id)
    await set_crew(call.tick, vessel.id, args.station, {"count": args.count})
    call.target(vessel.id)
    what = await call.record(
        "tools.mortal.man_station",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: vessel.id},
        facts={"station": args.station, "count": args.count},
    )
    return result(MortalResult.WAY_TAKEN, what=what)


async def trim_sails(call: MortalCall, args: SailInput) -> str:
    vessel = await my_vessel(call, args.vessel_id)
    await set_ship(call.tick, vessel.id, {"point_of_sail": args.point_of_sail.value, "shot": args.shot.value})
    call.target(vessel.id)
    what = f"{vessel.name} {spoken(args.point_of_sail)} with {spoken(args.shot)} shot"
    await call.record(
        "tools.mortal.trim_sails",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: vessel.id},
        facts={"point_of_sail": args.point_of_sail, "shot": args.shot},
    )
    return result(MortalResult.WAY_TAKEN, what=what)


async def found_circle(call: MortalCall, args: CircleInput) -> str:
    faction = await led_faction(call)
    town = await my_town(call)
    row = await call.session.get(SocialCircleRow, faction.faction_entity_id)
    if row is None:
        row = SocialCircleRow(faction_entity_id=faction.faction_entity_id, kind=args.kind, founded_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    elif "kind" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold your circle as it is")
    row.kind, row.meeting_place_id = args.kind, town.id
    await call.session.flush()
    call.target(faction.faction_entity_id)
    return await recorded(
        call,
        "tools.mortal.found_circle",
        f"a circle of {spoken(args.kind)} in {town.name}",
        roles={IncidentRole.PRODUCT: faction.faction_entity_id, IncidentRole.PLACE: town.id},
        facts={"circle": args.kind},
    )


async def press_demand(call: MortalCall, args: DemandInput) -> str:
    if call.me.social_class is not SocialClass.NOBLE:
        fail(MortalResult.WAY_REFUSED, why="only the nobly born press such demands")
    row = await call.session.get(NobleDemandRow, (call.me.id, args.want))
    if row is not None and row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold that demand as it is")
    if row is None:
        row = NobleDemandRow(mortal_entity_id=call.me.id, want=args.want, since_epoch=call.tick.epoch)
        call.session.add(row)
    row.met = False
    await call.session.flush()
    return await recorded(call, "tools.mortal.press_demand", f"a demand of {spoken(args.want)}", roles={}, facts={"want": args.want})


async def swear_fealty(call: MortalCall, args: FealtyInput) -> str:
    realm = await ruled_realm(call)
    overlord = await living_entity(call.session, args.overlord_id)
    if overlord is None or overlord.entity_type is not EntityType.POLITY or overlord.id == realm.id or held(overlord.id):
        fail(MortalResult.WAY_REFUSED, why="that is no other realm")
    for polity in (realm, overlord):
        profile = await call.session.get(PolityProfileRow, polity.id)
        if profile is None or profile.core_entity_id is None:
            fail(MortalResult.WAY_REFUSED, why=f"{polity.name} has no heartland")
    if await call.session.get(VassalageRow, realm.id) is not None:
        fail(MortalResult.WAY_REFUSED, why="your realm is bound to an overlord already")
    try:
        row = await create_vassalage(call.tick, realm.id, overlord.id, tribute_pct=TRIBUTE_PCT, levy_pct=LEVY_PCT)
    except (NotFoundError, ValidationFailedError) as error:
        fail(MortalResult.WAY_REFUSED, why=str(error).rstrip("."))
    row.kind = args.kind
    await call.session.flush()
    call.target(overlord.id)
    return await recorded(
        call,
        "tools.mortal.swear_fealty",
        f"{realm.name} bound to {overlord.name} as {spoken(args.kind)}",
        roles={IncidentRole.SUBJECT: realm.id, IncidentRole.AUTHORITY: overlord.id},
        facts={"bond": args.kind},
    )


async def set_levy(call: MortalCall, args: LevyInput) -> str:
    realm = await ruled_realm(call)
    row = await call.session.get(TaxPolicyRow, (realm.id, args.kind))
    if row is None:
        row = TaxPolicyRow(polity_entity_id=realm.id, kind=args.kind, rate=args.rate, epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    elif "rate" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold that tax as it is")
    row.rate, row.epoch = args.rate, call.tick.epoch
    await call.session.flush()
    call.target(realm.id)
    await call.record(
        "tools.mortal.set_levy", roles={IncidentRole.AUTHORITY: call.me.id, IncidentRole.SUBJECT: realm.id}, facts={"tax": args.kind, "rate": args.rate}
    )
    return result(MortalResult.WAY_TAKEN, what=f"{spoken(args.kind)} at {args.rate} in a hundred")


async def run_racket(call: MortalCall, args: RacketInput) -> str:
    faction = await led_faction(call)
    town = await my_town(call)
    try:
        await set_racket(call.tick, faction.faction_entity_id, town.id, args.kind, RACKET_INCOME)
    except (NotFoundError, ValidationFailedError) as error:
        fail(MortalResult.WAY_REFUSED, why=str(error).rstrip("."))
    call.target(town.id)
    await call.record(
        "tools.mortal.run_racket",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OWNER: faction.faction_entity_id, IncidentRole.VICTIM: town.id},
        facts={"racket": args.kind, "income": RACKET_INCOME},
        place=town.id,
    )
    return result(MortalResult.WAY_TAKEN, what=f"{spoken(args.kind)} in {town.name}")


async def refit_section(call: MortalCall, args: RefitInput) -> str:
    vessel = await my_vessel(call, args.vessel_id)
    await set_vessel_section(call.tick, vessel.id, args.section, {"condition": PERCENT, "state": SectionState.SOUND.value})
    call.target(vessel.id)
    await call.record(
        "tools.mortal.refit_section",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.SUBJECT: vessel.id},
        facts={"section": args.section},
        place=vessel.location_id,
    )
    return result(MortalResult.WAY_TAKEN, what=f"the {spoken(args.section)} of {vessel.name} made sound")


async def shore_up(call: MortalCall, args: ShoreInput) -> str:
    town = await my_town(call)
    structure = await living_entity(call.session, args.structure_id)
    if structure is None or structure.entity_type is not EntityType.STRUCTURE or structure.location_id not in {town.id, town.location_id}:
        fail(MortalResult.WAY_REFUSED, why="no such building stands in your town")
    row = await call.session.get(StructureSectionRow, (structure.id, args.section))
    if row is None:
        fail(MortalResult.WAY_REFUSED, why=f"{structure.name} has no such part")
    if "condition" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold that part as it is")
    before, after = row.condition, min(PERCENT, row.condition + REPAIR)
    await edit_section(call.tick, structure.id, args.section, {"condition": after}, [])
    call.target(structure.id)
    await call.record(
        "tools.mortal.shore_up",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: structure.id},
        facts={"section": args.section, "before": before, "after": after},
    )
    return result(MortalResult.WAY_TAKEN, what=f"the {spoken(args.section)} of {structure.name} shored up")


async def replan_land(call: MortalCall, args: RingInput) -> str:
    await ruled_realm(call)
    town = await my_town(call)
    region = await living_entity(call.session, town.location_id) if town.location_id is not None else None
    if region is None or region.entity_type is not EntityType.REGION or held(region.id):
        fail(MortalResult.WAY_REFUSED, why="your town stands in no land you can plan")
    row = await call.session.get(LandRingRow, region.id)
    if row is not None and "ring" in row.locked:
        fail(MortalResult.WAY_REFUSED, why="the gods hold that land's use as it is")
    await set_ring(call.tick, region.id, {"ring": args.ring.value, "market_entity_id": town.id})
    call.target(region.id)
    await call.record(
        "tools.mortal.replan_land",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: region.id, IncidentRole.PLACE: town.id},
        facts={"ring": args.ring},
        place=town.id,
    )
    return result(MortalResult.WAY_TAKEN, what=f"{region.name} given over to {spoken(args.ring)}")


async def tend_maimed(call: MortalCall, args: MaimedInput) -> str:
    town = await my_town(call)
    row = await call.session.get(MaimedCohortRow, (town.id, args.kind))
    if row is None or row.count <= 0:
        fail(MortalResult.WAY_REFUSED, why=f"no one in {town.name} lives with that harm")
    row.count -= 1
    row.updated_epoch = call.tick.epoch
    await call.session.flush()
    call.target(town.id)
    await call.record(
        "tools.mortal.tend_maimed", roles={IncidentRole.HEALER: call.me.id, IncidentRole.PLACE: town.id}, facts={"maimed": args.kind, "left": row.count}
    )
    return result(MortalResult.WAY_TAKEN, what=f"one with {spoken(args.kind)} brought back to work in {town.name}")


async def devise_custom(call: MortalCall, args: CustomInput) -> str:
    try:
        row = await create_kind(call.tick, args.catalog, args.base, args.name, description=args.description, params={}, world_id=call.me.world_id)
    except (NotFoundError, ValidationFailedError) as error:
        fail(MortalResult.WAY_REFUSED, why=str(error).rstrip("."))
    return await recorded(
        call, "tools.mortal.devise_custom", f"{row.name}, a new {spoken(args.catalog)}", roles={}, facts={"name": row.name, "catalog": args.catalog}
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.TAKE_ARMS, mortal, ArmsInput, meta, take_arms),
        ToolSpec(MortalToolId.RECKON_YEARS, mortal, DatingInput, meta, reckon_years),
        ToolSpec(MortalToolId.SPEAK_FOR_NORM, mortal, NormInput, meta, speak_for_norm),
        ToolSpec(MortalToolId.SET_ROLE_CUSTOM, mortal, RoleInput, meta, set_role_custom),
        ToolSpec(MortalToolId.READ_THE_SKY, mortal, ReadingInput, meta, read_the_sky),
        ToolSpec(MortalToolId.SET_SPEECH, mortal, RegisterInput, meta, set_speech),
        ToolSpec(MortalToolId.TEACH_TONGUE, mortal, TongueInput, meta, teach_tongue),
        ToolSpec(MortalToolId.KEEP_LEGACY, mortal, LegacyInput, meta, keep_legacy),
        ToolSpec(MortalToolId.ASSIGN_CASTE, mortal, CasteInput, meta, assign_caste),
        ToolSpec(MortalToolId.PROCLAIM_AGE, mortal, AgeInput, meta, proclaim_age),
        ToolSpec(MortalToolId.DRAW_BLUEPRINT, mortal, DesignInput, meta, draw_blueprint),
        ToolSpec(MortalToolId.DEVISE_USE, mortal, UseInput, meta, devise_use),
        ToolSpec(MortalToolId.RAISE_MOVEMENT, mortal, MovementInput, meta, raise_movement),
        ToolSpec(MortalToolId.CLAIM_COURTS, mortal, ClaimInput, meta, claim_courts),
        ToolSpec(MortalToolId.DRILL_TRAIT, mortal, TraitInput, meta, drill_trait),
        ToolSpec(MortalToolId.FACE_FEAR, mortal, FearInput, meta, face_fear),
        ToolSpec(MortalToolId.TAKE_UP_WANT, mortal, WantInput, meta, take_up_want),
        ToolSpec(MortalToolId.EASE_PRESSURE, mortal, PressureInput, meta, ease_pressure),
        ToolSpec(MortalToolId.TEACH_HONOUR, mortal, HonourInput, meta, teach_honour),
        ToolSpec(MortalToolId.RESIST_DRIFT, mortal, DriftInput, meta, resist_drift),
        ToolSpec(MortalToolId.MAN_STATION, mortal, StationInput, meta, man_station),
        ToolSpec(MortalToolId.TRIM_SAILS, mortal, SailInput, meta, trim_sails),
        ToolSpec(MortalToolId.FOUND_CIRCLE, mortal, CircleInput, meta, found_circle),
        ToolSpec(MortalToolId.PRESS_DEMAND, mortal, DemandInput, meta, press_demand),
        ToolSpec(MortalToolId.SWEAR_FEALTY, mortal, FealtyInput, meta, swear_fealty),
        ToolSpec(MortalToolId.SET_LEVY, mortal, LevyInput, meta, set_levy),
        ToolSpec(MortalToolId.RUN_RACKET, mortal, RacketInput, meta, run_racket),
        ToolSpec(MortalToolId.REFIT_SECTION, mortal, RefitInput, meta, refit_section),
        ToolSpec(MortalToolId.SHORE_UP, mortal, ShoreInput, meta, shore_up),
        ToolSpec(MortalToolId.REPLAN_LAND, mortal, RingInput, meta, replan_land),
        ToolSpec(MortalToolId.TEND_MAIMED, mortal, MaimedInput, meta, tend_maimed),
        ToolSpec(MortalToolId.DEVISE_CUSTOM, mortal, CustomInput, meta, devise_custom),
    ]
