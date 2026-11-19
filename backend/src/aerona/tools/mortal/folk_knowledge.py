from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkClassRow, FolkKnowledgeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.folk_knowledge.truth import hurts, misjudged, truth_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class TeachLoreInput(ToolInput):
    domain: FolkDomain
    learner_id: int


class TestLoreInput(ToolInput):
    domain: FolkDomain
    class_id: int


async def knowledge_of(call: MortalCall, people_id: int, domain: FolkDomain) -> FolkKnowledgeRow | None:
    return await call.session.scalar(select(FolkKnowledgeRow).where(FolkKnowledgeRow.people_entity_id == people_id, FolkKnowledgeRow.domain == domain).limit(1))


async def my_knowledge(call: MortalCall, domain: FolkDomain) -> tuple[EntityRow, FolkKnowledgeRow]:
    folk = await people_of(call.session, call.me)
    if folk is None:
        fail(MortalResult.FOLK_LORE_REFUSED, why="you belong to no people whose knowledge you could share")
    mine = await knowledge_of(call, folk.id, domain)
    if mine is None:
        fail(MortalResult.FOLK_LORE_REFUSED, why=f"your people hold no knowledge of {spoken(domain)} yet")
    return folk, mine


async def teach_lore(call: MortalCall, args: TeachLoreInput) -> str:
    folk, mine = await my_knowledge(call, args.domain)
    learner = await call.session.get(EntityRow, args.learner_id)
    if learner is None or learner.entity_type is not EntityType.MORTAL or not learner.living or learner.id == call.me.id:
        fail(MortalResult.FOLK_LORE_REFUSED, why="teach another living mortal")
    theirs_folk = await people_of(call.session, learner)
    if theirs_folk is None:
        fail(MortalResult.FOLK_LORE_REFUSED, why=f"{learner.name} belongs to no people to carry what you teach")
    if held(theirs_folk.id):
        fail(MortalResult.FOLK_LORE_REFUSED, why="a god holds that people as it is")
    theirs = mine if theirs_folk.id == folk.id else await knowledge_of(call, theirs_folk.id, args.domain)
    if theirs is None:
        fail(MortalResult.FOLK_LORE_REFUSED, why=f"{learner.name}'s people have no knowledge of {spoken(args.domain)} to build on")
    gain = call.rules.folk_knowledge.contact_gain
    if theirs is mine:
        if "depth" in (mine.locked or []):
            fail(MortalResult.FOLK_LORE_REFUSED, why="a god holds that knowledge as it is")
        moved = clamp_int(mine.depth + gain, 0, PERCENT) - mine.depth
        mine.depth += moved
    else:
        if mine.accuracy <= theirs.accuracy:
            fail(MortalResult.FOLK_LORE_REFUSED, why=f"{learner.name}'s people already know {spoken(args.domain)} as well as yours")
        if "accuracy" in (theirs.locked or []):
            fail(MortalResult.FOLK_LORE_REFUSED, why="a god holds that knowledge as it is")
        moved = min(gain, mine.accuracy - theirs.accuracy)
        theirs.accuracy += moved
    call.target(learner.id)
    await call.record(
        "folk.lore_exchanged",
        roles={IncidentRole.LEARNER: learner.id, IncidentRole.TEACHER: call.me.id},
        facts={"domain": args.domain, "gain": moved},
    )
    return result(MortalResult.LORE_TAUGHT, domain=spoken(args.domain), learner=learner.name, accuracy=theirs.accuracy, depth=theirs.depth)


async def test_lore(call: MortalCall, args: TestLoreInput) -> str:
    folk, mine = await my_knowledge(call, args.domain)
    cls = await call.session.get(FolkClassRow, args.class_id)
    if cls is None or cls.people_entity_id != folk.id or cls.domain is not args.domain:
        fail(MortalResult.FOLK_LORE_REFUSED, why=f"your people name no such class in {spoken(args.domain)}")
    if held(folk.id):
        fail(MortalResult.FOLK_LORE_REFUSED, why="a god holds your people as they are")
    truth = await truth_of(call.session, cls)
    if truth is None:
        return result(MortalResult.LORE_UNANSWERED, name=cls.name, taken_as=spoken(cls.taken_as))
    if not misjudged(cls.taken_as, truth):
        return result(MortalResult.LORE_CONFIRMED, name=cls.name, taken_as=spoken(cls.taken_as))
    if "taken_as" in (cls.locked or []):
        fail(MortalResult.FOLK_LORE_REFUSED, why="a god holds that class as it is")
    was = cls.taken_as
    cost = call.rules.folk_knowledge.harm_hp if hurts(was, truth) else 0
    if cost:
        shift_stat(call.me, "hp", -cost, low=1)
    cls.taken_as = truth
    if "misclassified" not in (cls.locked or []):
        cls.misclassified = False
    if "accuracy" not in (mine.locked or []):
        mine.accuracy = clamp_int(mine.accuracy + call.rules.folk_knowledge.failure_correction, 0, PERCENT)
    await call.record(
        "folk.class_corrected",
        roles={IncidentRole.SUBJECT: folk.id},
        facts={"name": cls.name, "domain": cls.domain, "taken_as": truth},
    )
    values = {"name": cls.name, "truth": spoken(truth), "was": spoken(was), "domain": spoken(args.domain), "accuracy": mine.accuracy}
    return result(MortalResult.LORE_CORRECTED_AT_COST, hp=cost, **values) if cost else result(MortalResult.LORE_CORRECTED, **values)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.TEACH_LORE, AgentKind.MORTAL, TeachLoreInput, ToolMeta(ActionKind.TEACH_KNOWLEDGE, mortal_standard_action), teach_lore),
        ToolSpec(MortalToolId.TEST_LORE, AgentKind.MORTAL, TestLoreInput, ToolMeta(ActionKind.DEVELOP_KNOWLEDGE, mortal_standard_action), test_lore),
    ]
