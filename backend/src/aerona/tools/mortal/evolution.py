from typing import Any

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CarrierRow, CureResearchRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.disease.research import institutions
from aerona.engine.disease.responses import take_up
from aerona.engine.mind.book import skill_level
from aerona.engine.primitives.distance import RegionAtlas
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


class SeekCureInput(ToolInput):
    disease_id: int


class FindCarrierInput(ToolInput):
    mortal_id: int
    disease_id: int


async def home_of(call: MortalCall) -> EntityRow | None:
    home = await living_entity(call.session, call.me.location_id) if call.me.location_id is not None else None
    return home if home is not None and home.entity_type in COMMUNITY_TYPES else None


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
    if realm is None and await skill_level(call.session, call.me.id, SkillKind.MEDICINE) <= 0:
        fail(MortalResult.ANSWER_REFUSED, why="you neither rule nor heal")
    await take_up(call.tick, community, disease.id, args.response)
    call.target(community.id)
    response = args.response.value.replace("_", " ")
    await call.record(
        "tools.mortal.answer_sickness",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: community.id, IncidentRole.TARGET: disease.id},
        facts={"response": args.response},
    )
    return result(MortalResult.ANSWERED, name=community.name, response=response)


async def seek_cure(call: MortalCall, args: SeekCureInput) -> str:
    disease = await sickness(call, args.disease_id, MortalResult.CURE_REFUSED)
    home = await home_of(call)
    seat = next((row for row in await institutions(call.session) if home is not None and row.location_id == home.id), None)
    if seat is None:
        fail(MortalResult.CURE_REFUSED, why="there is no hospital, academy or monastery where you live")
    skill = await skill_level(call.session, call.me.id, SkillKind.MEDICINE)
    if skill <= 0:
        fail(MortalResult.CURE_REFUSED, why="you know nothing of medicine")
    row = await call.session.get(CureResearchRow, (seat.id, disease.id))
    if row is None:
        row = CureResearchRow(institution_entity_id=seat.id, disease_entity_id=disease.id, points=0, specimens=0, started_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    if row.cured_epoch is not None:
        fail(MortalResult.CURE_REFUSED, why="that cure is found already")
    if "points" not in row.locked:
        row.points = (row.points or 0) + max(1, skill // 10) * call.rules.cure_research.per_scholar
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
