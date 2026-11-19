from typing import Any

from sqlalchemy import select

from aerona.catalog.tongues import SCRIPT_CHAIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import LanguageProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.tongues import LanguagePolicy, ScriptChangeCause
from aerona.engine.mind.book import skill_level
from aerona.engine.primitives.queries import has_flag, living_entity
from aerona.engine.tongues.decipher import DecipherTally, study
from aerona.engine.tongues.modality import own_tongue
from aerona.engine.tongues.policy import set_policy
from aerona.engine.tongues.scripts import record_script, script_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

PROCLAIMED = 60


class DecipherInput(ToolInput):
    language_id: int


class ProclaimInput(ToolInput):
    language_id: int
    policy: LanguagePolicy


class ReformInput(ToolInput):
    pass


async def decipher_script(call: MortalCall, args: DecipherInput) -> str:
    language = await living_entity(call.session, args.language_id)
    if language is None or language.entity_type is not EntityType.LANGUAGE or not await has_flag(call.session, language.id, EntityFlag.DECIPHERABLE):
        fail(MortalResult.DECIPHER_REFUSED, why="there is no dead script of that tongue left to read")
    if await skill_level(call.session, call.me.id, SkillKind.LANGUAGES) <= 0:
        fail(MortalResult.DECIPHER_REFUSED, why="you know nothing of languages")
    work = await study(call.tick, language, call.me, DecipherTally())
    call.target(language.id)
    await call.record("tools.mortal.decipher", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: language.id})
    return result(MortalResult.DECIPHERED, name=language.name, progress=work.progress)


async def realm_of(call: MortalCall) -> int | None:
    found = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return int(found) if found is not None else None


async def proclaim_tongue(call: MortalCall, args: ProclaimInput) -> str:
    realm = await realm_of(call)
    language = await living_entity(call.session, args.language_id)
    if realm is None:
        fail(MortalResult.PROCLAIM_REFUSED, why="you rule no realm")
    if language is None or language.entity_type is not EntityType.LANGUAGE:
        fail(MortalResult.PROCLAIM_REFUSED, why="that is not a tongue")
    await set_policy(call.tick, realm, language.id, args.policy, PROCLAIMED)
    call.target(realm)
    await call.record(
        "tools.mortal.proclaim",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: realm, IncidentRole.SUBJECT: language.id},
        facts={"policy": args.policy},
    )
    return result(MortalResult.PROCLAIMED, name=language.name, policy=spoken(args.policy))


async def reform_script(call: MortalCall, args: ReformInput) -> str:
    language = await own_tongue(call.session, call.me)
    profile = await call.session.get(LanguageProfileRow, language.id) if language is not None else None
    if language is None or profile is None or profile.writing_system is None:
        fail(MortalResult.REFORM_REFUSED, why="your people's tongue is not written")
    if await skill_level(call.session, call.me.id, SkillKind.LANGUAGES) <= 0:
        fail(MortalResult.REFORM_REFUSED, why="you know nothing of languages")
    current = await script_of(call.tick, language, profile)
    following = SCRIPT_CHAIN[current.system] if current is not None else None
    if current is None or following is None:
        fail(MortalResult.REFORM_REFUSED, why="the script can be made no simpler")
    row = await record_script(call.tick, language, profile, following, cause=ScriptChangeCause.REFORM, parent=current)
    call.target(language.id)
    await call.record("tools.mortal.reform", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: language.id}, facts={"script": following})
    return result(MortalResult.REFORMED, name=row.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.DEVELOP_KNOWLEDGE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.DECIPHER_SCRIPT, mortal, DecipherInput, meta, decipher_script),
        ToolSpec(MortalToolId.PROCLAIM_TONGUE, mortal, ProclaimInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), proclaim_tongue),
        ToolSpec(MortalToolId.REFORM_SCRIPT, mortal, ReformInput, meta, reform_script),
    ]
