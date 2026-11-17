from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import DESCRIPTION_MAX, DESCRIPTION_MIN, IMAGE_PROMPT_MAX, NAME_MAX, NAME_MIN, SUBTYPE_MAX
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.engine.primitives.queries import spoken_language
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.errors import RejectionError
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.shared_inputs import WordInput, add_words
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.mortal import lines
from aerona.tools.mortal.support import MortalCreation, create_record, name_free

WORD_SEPARATOR = ", "
SPEAKERS = (EntityType.PEOPLE, EntityType.SETTLEMENT)


class FoundLanguageInput(ToolInput):
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    subtype: Annotated[str, Field(max_length=SUBTYPE_MAX)] | None = None
    description: Annotated[str, Field(min_length=DESCRIPTION_MIN, max_length=DESCRIPTION_MAX)]
    words: Annotated[list[WordInput], Field(min_length=1)]
    image_prompt: Annotated[str, Field(max_length=IMAGE_PROMPT_MAX)] | None = None


class CoinWordsInput(ToolInput):
    words: Annotated[list[WordInput], Field(min_length=1)]


async def parent_language(call: MortalCall) -> EntityRow | None:
    if call.me.entity_type is not EntityType.MORTAL:
        return None
    own = await spoken_language(call.session, call.me.id)
    if own is not None:
        return own
    atlas = await call.atlas()
    region = atlas.top_region(call.me.id)
    if region is None:
        return None
    for placement_id in await _speakers_in(call, region):
        language = await spoken_language(call.session, placement_id)
        if language is not None:
            return language
    return None


async def _speakers_in(call: MortalCall, region: int) -> list[int]:
    atlas = await call.atlas()
    statement = select(EntityRow.id).where(
        EntityRow.world_id == call.me.world_id, EntityRow.entity_type.in_(list(SPEAKERS)), EntityRow.status == EntityStatus.CANON
    )
    return [entity_id for entity_id in await call.session.scalars(statement.order_by(EntityRow.id)) if atlas.top_region(entity_id) == region]


async def found_language(call: MortalCall, args: FoundLanguageInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.LANGUAGES_FOUNDED, tools.language_per_epoch, "mortal_tools.language_per_epoch", MortalResult.LANGUAGE_LIMIT)
    await name_free(call, args.name)
    parent = await parent_language(call)
    subtype = args.subtype
    if parent is not None:
        subtype = lines.DIALECT_SUBTYPE.format(parent=parent.name, suffix=lines.DIALECT_SUFFIX.format(subtype=args.subtype) if args.subtype else "")
    stats = {
        "spread": tools.dialect_spread if parent is not None else tools.language_spread,
        "complexity": tools.language_complexity,
        "sacredness": tools.language_sacredness,
    }
    language = await create_record(
        call, MortalCreation(args.name, EntityType.LANGUAGE, args.description, subtype=subtype, stats=stats, image_prompt=args.image_prompt)
    )
    bonds = BondRepository(call.session)
    if parent is not None:
        await bonds.connect(BondDraft(language.id, parent.id, BondKind.DESCENDS_FROM, call.epoch, lines.DIALECT_BOND))
    for bond in await bonds.outgoing(call.me.id, BondKind.SPEAKS):
        await bonds.deactivate(bond, call.epoch, language.name)
    await bonds.connect(BondDraft(call.me.id, language.id, BondKind.SPEAKS, call.epoch))
    added = await add_words(call.session, language, args.words[: tools.coin_word_max_words], actor=(ActorKind.MORTAL, call.me.id), epoch=call.epoch)
    await call.record("tools.mortal.language_born", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PRODUCT: language.id}, facts={"words": list(added)})
    await call.bump(TurnCounter.LANGUAGES_FOUNDED)
    return result(MortalResult.LANGUAGE_BORN, id=language.id, name=language.name)


async def coin_words(call: MortalCall, args: CoinWordsInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.WORDS_COINED, tools.coin_word_per_epoch, "mortal_tools.coin_word_per_epoch", MortalResult.WORDS_LIMIT)
    language = await spoken_language(call.session, call.me.id)
    if language is None:
        fail(MortalResult.NO_LANGUAGE)
    reason = state_reason(language, language.id)
    if reason is not None:
        raise RejectionError(reason)
    await call.bump(TurnCounter.WORDS_COINED)
    call.target(language.id)
    added = await add_words(call.session, language, args.words[: tools.coin_word_max_words], actor=(ActorKind.MORTAL, call.me.id), epoch=call.epoch)
    if not added:
        return result(MortalResult.NO_NEW_WORDS)
    joined = WORD_SEPARATOR.join(added)
    await call.record("tools.mortal.words", roles={IncidentRole.MAKER: call.me.id, IncidentRole.PRODUCT: language.id}, facts={"words": list(added)})
    return result(MortalResult.WORDS_ADDED, words=joined)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(MortalToolId.FOUND_LANGUAGE, mortal, FoundLanguageInput, ToolMeta(ActionKind.FOUND_LANGUAGE, mortal_standard_action), found_language),
        ToolSpec(MortalToolId.COIN_WORDS, mortal, CoinWordsInput, ToolMeta(ActionKind.COIN_WORDS, no_cost), coin_words),
    ]
