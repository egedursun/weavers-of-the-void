from typing import Annotated, Any

from pydantic import Field

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.tongues import SoundChangeCause, SoundChangeKind, SoundEnvironment
from aerona.engine.tongues.divine import give_tongue, knows, teach, tongue_of
from aerona.engine.tongues.meaning import veil
from aerona.engine.tongues.sounds import Change, add_change, rederive
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Sound = Annotated[str, Field(min_length=1, max_length=KEY_MAX_LENGTH)]
LANGUAGES = frozenset({EntityType.LANGUAGE})


class RevealTongueInput(ToolInput):
    mortal_id: int
    reason: Reason


class DecreeSoundInput(ToolInput):
    language_id: int
    kind: SoundChangeKind
    source: Sound
    target: Annotated[str, Field(max_length=KEY_MAX_LENGTH)] = ""
    environment: SoundEnvironment = SoundEnvironment.ANYWHERE
    reason: Reason


class VeilNameInput(ToolInput):
    language_id: int
    node_id: int
    reason: Reason


async def world_tongue(call: SonCall, language_id: int) -> EntityRow:
    language = require_type(await require_canon(call.session, language_id), LANGUAGES, SonResult.TONGUE_REFUSED, why="that is not a tongue")
    if language.world_id is not None and call.son.current_world_id is not None and language.world_id != call.son.current_world_id:
        fail(SonResult.TONGUE_REFUSED, why="that tongue is spoken on another world")
    return language


async def reveal_tongue(call: SonCall, args: RevealTongueInput) -> str:
    mortal = require_type(
        await require_canon(call.session, args.mortal_id), frozenset({EntityType.MORTAL}), SonResult.TONGUE_REFUSED, why="only a mortal learns"
    )
    await ensure_in_reach(call, mortal)
    await give_tongue(call.tick, call.son)
    language_id = await tongue_of(call.session, call.son.id)
    if await knows(call.session, mortal.id, language_id):
        fail(SonResult.TONGUE_REFUSED, why=f"{mortal.name} already knows your tongue")
    if not await teach(call.tick, call.son.id, mortal):
        fail(SonResult.TONGUE_REFUSED, why=f"{mortal.name} cannot be taught now")
    call.target(mortal.id)
    await call.record(
        "tools.son.reveal_tongue",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: mortal.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.LANGUAGE,
    )
    return result(SonResult.TONGUE_REVEALED, name=mortal.name)


async def decree_sound(call: SonCall, args: DecreeSoundInput) -> str:
    language = await world_tongue(call, args.language_id)
    change = Change(args.kind, args.source.strip().casefold(), args.target.strip().casefold(), args.environment)
    await add_change(call.tick, language.id, change, SoundChangeCause.DECREE)
    changed = await rederive(call.tick, language.id)
    call.target(language.id)
    await call.record(
        "tools.son.decree_sound",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: language.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.LANGUAGE,
    )
    return result(SonResult.SOUND_DECREED, name=language.name, count=changed)


async def veil_name(call: SonCall, args: VeilNameInput) -> str:
    language = await world_tongue(call, args.language_id)
    named = await call.session.get(EntityRow, args.node_id)
    name = named.name if named is not None else call.son.name if args.node_id == call.son.id else None
    if name is None:
        fail(SonResult.TONGUE_REFUSED, why="there is no such name")
    word = await veil(call.tick, language, args.node_id, name)
    if word is None:
        fail(SonResult.TONGUE_REFUSED, why=f"{language.name} has too few words for a euphemism")
    call.target(language.id)
    await call.record(
        "tools.son.veil_name",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: language.id},
        facts={"name": str(name), "reason": args.reason},
        kind=ChronicleKind.LANGUAGE,
    )
    return result(SonResult.NAME_VEILED, name=name, word=word.word)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.REVEAL_TONGUE, son, RevealTongueInput, meta, reveal_tongue),
        ToolSpec(SonToolId.DECREE_SOUND, son, DecreeSoundInput, meta, decree_sound),
        ToolSpec(SonToolId.VEIL_NAME, son, VeilNameInput, meta, veil_name),
    ]
