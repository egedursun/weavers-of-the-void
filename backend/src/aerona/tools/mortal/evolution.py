from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CarrierRow, CureResearchRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.disease_agents import CureClass
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.agentless_conditions.arise import ConditionTally
from aerona.engine.agentless_conditions.course import eased, named_of
from aerona.engine.body.state import refresh
from aerona.engine.disease.agents import apply_cure, works_on
from aerona.engine.disease.research import institutions
from aerona.engine.disease.responses import take_up
from aerona.engine.eras.effects import home_community
from aerona.engine.mind.book import skill_level
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_among, homes_for
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.tongues import realm_of


class AnswerSicknessInput(ToolInput):
    disease_id: int
    response: PlagueResponse
    cure_class: CureClass | None = None


class SeekCureInput(ToolInput):
    disease_id: int | None = None
    condition_id: int | None = None
    cure_class: CureClass | None = None


class FindCarrierInput(ToolInput):
    mortal_id: int
    disease_id: int


async def home_of(call: MortalCall) -> EntityRow | None:
    return await home_community(call.session, call.me)


async def healing_skill(call: MortalCall, places: set[int]) -> int:
    if call.me.entity_type is EntityType.MORTAL:
        return await skill_level(call.session, call.me.id, SkillKind.MEDICINE)
    folk = await call.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_among(call.session, places))
        .order_by(EntityRow.id)
    )
    return max([await skill_level(call.session, being, SkillKind.MEDICINE) for being in folk], default=0)


async def sickness(call: MortalCall, disease_id: int, refused: MortalResult) -> EntityRow:
    disease = await living_entity(call.session, disease_id)
    if disease is None or disease.entity_type is not EntityType.DISEASE:
        fail(refused, why="that is no sickness")
    return disease


async def answer_sickness(call: MortalCall, args: AnswerSicknessInput) -> str:
    disease = await sickness(call, args.disease_id, MortalResult.ANSWER_REFUSED)
    realm = await realm_of(call)
    community = await living_entity(call.session, realm) if realm is not None else await home_of(call)
    if community is None:
        fail(MortalResult.ANSWER_REFUSED, why="you lead no community")
    if realm is None and call.me.entity_type not in COMMUNITY_TYPES and await skill_level(call.session, call.me.id, SkillKind.MEDICINE) <= 0:
        fail(MortalResult.ANSWER_REFUSED, why="you neither rule nor heal")
    await take_up(call.tick, community, disease.id, args.response)
    worked = await apply_cure(call.tick, community, disease.id, args.cure_class) if args.cure_class is not None else None
    call.target(community.id)
    await call.record(
        "tools.mortal.answer_sickness",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: community.id, IncidentRole.TARGET: disease.id},
        facts={"response": args.response},
    )
    told = "" if worked is None else " The cure works on it." if worked else " The cure does nothing against it."
    return result(MortalResult.ANSWERED, name=community.name, response=spoken(args.response)) + told


async def place_of_healing(call: MortalCall) -> tuple[EntityRow, set[int], int]:
    home = await home_of(call)
    places = await homes_for(call.session, [home.id]) if home is not None else set()
    seat = next((row for row in await institutions(call.session) if row.location_id in places), None)
    if seat is None:
        fail(MortalResult.CURE_REFUSED, why="there is no hospital, academy or monastery where you live")
    skill = await healing_skill(call, places)
    if skill <= 0:
        fail(MortalResult.CURE_REFUSED, why="you know nothing of medicine")
    return seat, places, skill


async def seek_relief(call: MortalCall, condition_id: int) -> str:
    row = await call.session.get(ConditionRow, condition_id)
    bearer = await call.session.get(EntityRow, row.bearer_node_id) if row is not None else None
    if row is None or bearer is None or row.ended_epoch is not None:
        fail(MortalResult.CURE_REFUSED, why="there is no such condition still borne")
    if bearer.id != call.me.id and bearer.id not in await close_kin_of(call.session, call.me.id):
        fail(MortalResult.CURE_REFUSED, why="you seek relief only for yourself and your close kin")
    if held(bearer.id):
        fail(MortalResult.CURE_REFUSED, why="a god holds that body as it is")
    seat, _places, skill = await place_of_healing(call)
    kind = await call.session.get(AgentlessConditionRow, row.kind_id) if row.kind_id is not None else None
    call.target(bearer.id)
    if not call.tick.rng(f"relief.{row.id}.{call.tick.epoch}").chance(min(PERCENT, skill)):
        return result(MortalResult.RELIEF_FAILED, condition=named_of(row, kind), place=seat.name)
    await eased(call.tick, row, bearer, kind, ConditionTally(), by=call.me.id)
    await refresh(call.session, call.rules, bearer, call.tick.epoch)
    return result(MortalResult.RELIEF_FOUND, condition=named_of(row, kind), place=seat.name, severity=row.severity)


async def seek_cure(call: MortalCall, args: SeekCureInput) -> str:
    if args.condition_id is not None:
        return await seek_relief(call, args.condition_id)
    if args.disease_id is None:
        fail(MortalResult.CURE_REFUSED, why="name a sickness or a condition to seek a cure for")
    disease = await sickness(call, args.disease_id, MortalResult.CURE_REFUSED)
    seat, _places, skill = await place_of_healing(call)
    row = await call.session.get(CureResearchRow, (seat.id, disease.id))
    if row is None:
        row = CureResearchRow(institution_entity_id=seat.id, disease_entity_id=disease.id, points=0, specimens=0, started_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    if row.cured_epoch is not None:
        fail(MortalResult.CURE_REFUSED, why="that cure is found already")
    works = await works_on(call.tick, disease.id, args.cure_class) if args.cure_class is not None else None
    gain = max(1, skill // 10) * call.rules.cure_research.per_scholar
    gain = gain * 3 // 2 if works else gain // 2 if works is False else gain
    if "points" not in row.locked:
        row.points = (row.points or 0) + gain
    await call.session.flush()
    call.target(seat.id)
    await call.record(
        "tools.mortal.seek_cure",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.HOST: seat.id, IncidentRole.TARGET: disease.id},
        facts={"points": row.points},
    )
    return result(MortalResult.CURE_SOUGHT, name=disease.name, points=row.points, threshold=call.rules.cure_research.threshold)


async def find_carrier(call: MortalCall, args: FindCarrierInput) -> str:
    disease = await sickness(call, args.disease_id, MortalResult.CARRIER_REFUSED)
    row = await call.session.get(CarrierRow, (args.mortal_id, disease.id))
    suspect = await living_entity(call.session, args.mortal_id)
    if row is None or suspect is None:
        fail(MortalResult.CARRIER_NOT_FOUND, disease=disease.name)
    if await skill_level(call.session, call.me.id, SkillKind.MEDICINE) < call.rules.carriers.identify_skill:
        fail(MortalResult.CARRIER_REFUSED, why="your medicine is not deep enough to see it")
    atlas = await RegionAtlas.load(call.session)
    if atlas.top_region(suspect.id) != atlas.top_region(call.me.id):
        fail(MortalResult.CARRIER_REFUSED, why="they are not in your land")
    if "identified" not in row.locked:
        row.identified = True
    call.target(suspect.id)
    await call.record("tools.mortal.find_carrier", roles={IncidentRole.HEALER: call.me.id, IncidentRole.PATIENT: suspect.id, IncidentRole.SUBJECT: disease.id})
    return result(MortalResult.CARRIER_FOUND, name=suspect.name, disease=disease.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.DEVELOP_KNOWLEDGE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.ANSWER_SICKNESS, mortal, AnswerSicknessInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), answer_sickness),
        ToolSpec(MortalToolId.SEEK_CURE, mortal, SeekCureInput, meta, seek_cure),
        ToolSpec(MortalToolId.FIND_CARRIER, mortal, FindCarrierInput, meta, find_carrier),
    ]
