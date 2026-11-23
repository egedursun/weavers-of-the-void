from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.entities import LanguageProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind, WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.tongues.scripts import reveal
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
LANGUAGES = frozenset({EntityType.LANGUAGE})


class RevealScriptInput(ToolInput):
    language_id: int
    system: WritingSystem
    prophet_id: int | None = None
    reason: Reason


async def reveal_script(call: SonCall, args: RevealScriptInput) -> str:
    language = require_type(await require_canon(call.session, args.language_id), LANGUAGES, SonResult.SCRIPT_REFUSED, why="that is not a tongue")
    if language.world_id is not None and call.son.current_world_id is not None and language.world_id != call.son.current_world_id:
        fail(SonResult.SCRIPT_REFUSED, why="that tongue is spoken on another world")
    profile = await call.session.get(LanguageProfileRow, language.id)
    if held(language.id):
        fail(SonResult.SCRIPT_REFUSED, why="that tongue is held as it is")
    if profile is not None and profile.writing_system is args.system:
        fail(SonResult.SCRIPT_REFUSED, why=f"{language.name} is already written so")
    prophet = await require_canon(call.session, args.prophet_id) if args.prophet_id is not None else None
    row = await reveal(call.tick, call.son.id, language, args.system, prophet_id=prophet.id if prophet is not None else None)
    call.target(language.id)
    await call.record(
        "tools.son.reveal_script",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: language.id},
        facts={"system": args.system},
        kind=ChronicleKind.LANGUAGE,
    )
    return result(SonResult.SCRIPT_REVEALED, name=language.name, script=row.name, system=spoken(args.system))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(SonToolId.REVEAL_SCRIPT, AgentKind.SON, RevealScriptInput, ToolMeta(ActionKind.INFLUENCE, son_standard_action), reveal_script),
    ]
