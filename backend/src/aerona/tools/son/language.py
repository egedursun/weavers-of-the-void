from typing import Annotated, Any

from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.shared_inputs import WordInput, add_words
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost
from aerona.tools.framework.validation import require_canon, require_type
from aerona.tools.son.support import ensure_in_reach

WORD_SEPARATOR = ", "


class CoinWordsInput(ToolInput):
    language_id: int
    words: Annotated[list[WordInput], Field(min_length=1)]


async def coin_words(call: SonCall, args: CoinWordsInput) -> str:
    tools = call.rules.son_tools
    await call.within_limit(TurnCounter.WORDS_COINED, tools.coin_word_per_epoch, "son_tools.coin_word_per_epoch", SonResult.WORDS_LIMIT)
    language = require_type(await require_canon(call.session, args.language_id), {EntityType.LANGUAGE}, SonResult.NOT_A_LANGUAGE)
    await ensure_in_reach(call, language)
    await call.bump(TurnCounter.WORDS_COINED)
    call.target(language.id)
    added = await add_words(call.session, language, args.words[: tools.coin_word_max_words], actor=(ActorKind.SON, call.son.id), epoch=call.epoch)
    if not added:
        return result(SonResult.WORDS_NONE)
    joined = WORD_SEPARATOR.join(added)
    await call.record(
        "tools.son.words", roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: language.id}, facts={"words": str(joined)}, kind=ChronicleKind.LANGUAGE
    )
    return result(SonResult.WORDS_ADDED, language=language.name, words=joined)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [ToolSpec(SonToolId.COIN_WORDS, AgentKind.SON, CoinWordsInput, ToolMeta(ActionKind.COIN_WORDS, no_cost), coin_words)]
