from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.mind_split import IDEAS
from aerona.catalog.renown import AXIS_LABELS
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import IdeaKind, IdeaSource, ThoughtKind
from aerona.domain.enums.mortal import Ability, MarriageKind
from aerona.domain.enums.relations import PassionKind, PassionSource
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.body.healing import mend
from aerona.engine.mind.book import ensure_mind_row
from aerona.engine.mind.ideas import Encounter, take_up
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kinship import betroth, foster, marry
from aerona.engine.mortal.standing import add_infamy, add_renown, add_stress
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.relations.book import ensure_relation, shift
from aerona.engine.relations.passions import kindle
from aerona.engine.renown.book import acclaim
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import require_essence

FULL = 100


class Binding(StrEnum):
    BETROTH = "betroth"
    WED = "wed"
    FOSTER = "foster"
    SWEAR_KIN = "swear_kin"


class Touch(StrEnum):
    EASE_MIND = "ease_mind"
    BURDEN_MIND = "burden_mind"
    GRANT_RENOWN = "grant_renown"
    SHAME = "shame"
    HEAL_BODY = "heal_body"
    STRENGTHEN = "strengthen"


class Stir(StrEnum):
    FRIENDSHIP = "friendship"
    ROMANCE = "romance"
    RIVALRY = "rivalry"
    LOVE = "love"
    LOYALTY = "loyalty"
    HATRED = "hatred"
    DEVOTION = "devotion"


STIR_PASSIONS = {Stir.LOVE: PassionKind.LOVE, Stir.LOYALTY: PassionKind.LOYALTY, Stir.HATRED: PassionKind.HATRED, Stir.DEVOTION: PassionKind.DEVOTION}


class StirInput(ToolInput):
    first_id: int
    second_id: int
    stir: Stir
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class SpreadInput(ToolInput):
    subject_id: int
    community_id: int
    axis: ReputationAxis
    raise_it: bool = Field(default=True, alias="raise")
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class PlantIdeaInput(ToolInput):
    mortal_id: int
    idea: IdeaKind
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class BindInput(ToolInput):
    first_id: int
    second_id: int
    binding: Binding
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class TouchInput(ToolInput):
    mortal_id: int
    touch: Touch
    ability: Ability | None = None
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def living_mortal(call: SonCall, mortal_id: int) -> EntityRow:
    found = await require_canon(call.session, mortal_id)
    if found.entity_type is not EntityType.MORTAL:
        fail(SonResult.NOT_A_MORTAL, name=found.name)
    return found


async def bind_mortals(call: SonCall, args: BindInput) -> str:
    if args.first_id == args.second_id:
        fail(SonResult.SAME_MORTAL)
    first = await living_mortal(call, args.first_id)
    second = await living_mortal(call, args.second_id)
    cost = call.rules.costs.influence
    require_essence(call, cost)
    call.spend_essence(cost)
    if args.binding is Binding.BETROTH:
        await betroth(call.session, first, second, call.epoch, description=args.reason)
    elif args.binding is Binding.WED:
        await marry(call.session, first, second, call.epoch, kind=MarriageKind.POLITICAL, description=args.reason)
    elif args.binding is Binding.FOSTER:
        await foster(call.session, first.id, second.id, call.epoch, description=args.reason)
    else:
        await connect(call.session, first.id, second.id, BondKind.SWORN_KIN, call.epoch, description=args.reason)
    call.target(first.id)
    await call.chronicle(
        ChronicleKind.LINEAGE,
        lines.BIND_MORTALS,
        entity_ids=[first.id, second.id],
        son=call.son.name,
        first=first.name,
        second=second.name,
        binding=args.binding.value.replace("_", " "),
        reason=args.reason,
    )
    return result(SonResult.MORTALS_BOUND, first=first.name, second=second.name, binding=args.binding.value.replace("_", " "))


async def touch_mortal(call: SonCall, args: TouchInput) -> str:
    mortal = await living_mortal(call, args.mortal_id)
    cost = call.rules.costs.influence
    require_essence(call, cost)
    call.spend_essence(cost)
    tools = call.rules.son_tools
    if args.touch is Touch.EASE_MIND:
        await add_stress(call.session, mortal.id, -tools.touch_amount, call.epoch)
    elif args.touch is Touch.BURDEN_MIND:
        await add_stress(call.session, mortal.id, tools.touch_amount, call.epoch)
    elif args.touch is Touch.GRANT_RENOWN:
        await add_renown(call.session, mortal.id, tools.touch_amount, call.epoch, rules=call.rules)
        await think(call.session, call.rules, mortal.id, ThoughtKind.GAINED_RENOWN, call.epoch, subject_id=call.son.id)
    elif args.touch is Touch.SHAME:
        await add_infamy(call.session, mortal.id, tools.touch_amount, call.epoch, rules=call.rules)
        await think(call.session, call.rules, mortal.id, ThoughtKind.WAS_SHAMED, call.epoch, subject_id=call.son.id)
    elif args.touch is Touch.HEAL_BODY:
        await mend(call.tick, mortal)
    else:
        if args.ability is None:
            fail(SonResult.ABILITY_NEEDED)
        key = args.ability.value
        set_stats(mortal, **{key: clamp_int((stat(mortal, key) or FULL // 2) + tools.touch_amount, 0, FULL)})
    call.target(mortal.id)
    await call.chronicle(
        ChronicleKind.INTRIGUE,
        lines.TOUCH_MORTAL,
        entity_ids=[mortal.id],
        son=call.son.name,
        mortal=mortal.name,
        touch=args.touch.value.replace("_", " "),
        reason=args.reason,
    )
    return result(SonResult.MORTAL_TOUCHED, name=mortal.name, touch=args.touch.value.replace("_", " "))


async def plant_idea(call: SonCall, args: PlantIdeaInput) -> str:
    mortal = await living_mortal(call, args.mortal_id)
    label = IDEAS[args.idea].label.lower()
    cost = call.rules.costs.influence
    require_essence(call, cost)
    await ensure_mind_row(call.session, mortal, call.epoch)
    if await take_up(call.session, mortal.id, Encounter(args.idea, IdeaSource.DIVINE, call.son.id), call.epoch) is None:
        fail(SonResult.IDEA_KNOWN, name=mortal.name, idea=label)
    call.spend_essence(cost)
    call.target(mortal.id)
    await call.chronicle(
        ChronicleKind.INTRIGUE, lines.PLANT_IDEA, entity_ids=[mortal.id], son=call.son.name, mortal=mortal.name, idea=label, reason=args.reason
    )
    return result(SonResult.IDEA_PLANTED, name=mortal.name, idea=label)


async def spread_word(call: SonCall, args: SpreadInput) -> str:
    subject = await require_canon(call.session, args.subject_id)
    community = await require_canon(call.session, args.community_id)
    cost = call.rules.costs.influence
    require_essence(call, cost)
    amount = call.rules.son_tools.touch_amount * (1 if args.raise_it else -1)
    row = await acclaim(call.session, subject.id, community.id, args.axis, amount=amount, epoch=call.epoch)
    if row is None:
        fail(SonResult.WORD_HELD, name=subject.name, community=community.name)
    call.spend_essence(cost)
    call.target(subject.id)
    await call.chronicle(
        ChronicleKind.INTRIGUE,
        lines.SPREAD_WORD,
        entity_ids=[subject.id, community.id],
        son=call.son.name,
        subject=subject.name,
        community=community.name,
        reason=args.reason,
    )
    return result(SonResult.WORD_SPREAD, name=subject.name, community=community.name, axis=AXIS_LABELS[args.axis].lower(), value=row.value)


async def stir_hearts(call: SonCall, args: StirInput) -> str:
    if args.first_id == args.second_id:
        fail(SonResult.SAME_MORTAL)
    first = await living_mortal(call, args.first_id)
    second = await living_mortal(call, args.second_id)
    cost = call.rules.costs.influence
    require_essence(call, cost)
    amount = call.rules.son_tools.touch_amount
    passion = STIR_PASSIONS.get(args.stir)
    if passion is not None:
        await kindle(call.session, first.id, passion, second.id, strength=FULL - amount, source=PassionSource.DIVINE, epoch=call.epoch)
    else:
        row = await ensure_relation(call.session, first.id, second.id, call.epoch)
        if row is None:
            fail(SonResult.HEART_HELD, name=first.name)
        shift(call.rules, row, call.epoch, **{args.stir.value: amount, "familiarity": amount})
    call.spend_essence(cost)
    call.target(first.id)
    stir = args.stir.value
    await call.chronicle(
        ChronicleKind.INTRIGUE,
        lines.STIR_HEARTS,
        entity_ids=[first.id, second.id],
        son=call.son.name,
        first=first.name,
        second=second.name,
        stir=stir,
        reason=args.reason,
    )
    return result(SonResult.HEARTS_STIRRED, first=first.name, second=second.name, stir=stir)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.BIND_MORTALS,
            son,
            BindInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            bind_mortals,
        ),
        ToolSpec(
            SonToolId.TOUCH_MORTAL,
            son,
            TouchInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            touch_mortal,
        ),
        ToolSpec(
            SonToolId.PLANT_IDEA,
            son,
            PlantIdeaInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            plant_idea,
        ),
        ToolSpec(
            SonToolId.SPREAD_WORD,
            son,
            SpreadInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            spread_word,
        ),
        ToolSpec(
            SonToolId.STIR_HEARTS,
            son,
            StirInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence),
            stir_hearts,
        ),
    ]
