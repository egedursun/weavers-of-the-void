from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.mythic import QUEST_PARTY_MAX
from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import spoken
from aerona.db.tables.culture import LegendProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.arcana.enchantments import lay_enchantment
from aerona.engine.arcana.longevity import begin_longevity
from aerona.engine.arcana.vis import vis_of
from aerona.engine.gods.queries import community_of
from aerona.engine.mind.book import skill_level
from aerona.engine.mythic.heroquests import begin_quest, eligible, fellows
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines

STRENGTH_MAX = 100


class QuestInput(ToolInput):
    legend_id: int | None = None
    companion_ids: list[int] = Field(default_factory=list, max_length=QUEST_PARTY_MAX)


class LongevityInput(ToolInput):
    form: SpellForm


class FoundEnchantmentInput(ToolInput):
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX_LENGTH)]
    effect: NaturalLaw
    form: SpellForm
    strength: Annotated[int, Field(ge=1, le=STRENGTH_MAX)]


async def undertake_heroquest(call: MortalCall, args: QuestInput) -> str:
    found = await eligible(call.tick, call.me)
    if found is None:
        fail(MortalResult.QUEST_REFUSED, why="you lack the renown, the faith of your people or a myth to walk")
    legend = await call.session.get(LegendProfileRow, args.legend_id) if args.legend_id is not None else found[0]
    if legend is None:
        fail(MortalResult.QUEST_REFUSED, why="there is no such legend")
    party = await fellows(call.tick, call.me, args.companion_ids)
    if isinstance(party, str):
        fail(MortalResult.QUEST_REFUSED, why=party)
    row = await begin_quest(call.tick, call.me, legend, party)
    await call.chronicle(ChronicleKind.WORLD, lines.HEROQUEST, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.QUEST_BEGUN, id=row.id, steps=row.steps)


async def take_longevity(call: MortalCall, args: LongevityInput) -> str:
    if await vis_of(call.tick, call.me.id, args.form) <= 0:
        community = await community_of(call.session, call.me)
        if community is None or await vis_of(call.tick, community.id, args.form) <= 0:
            fail(MortalResult.LONGEVITY_REFUSED, why=f"you hold no {spoken(args.form)} vis to pay for it")
    row = await begin_longevity(call.tick, call.me, args.form)
    if row is None:
        fail(MortalResult.LONGEVITY_REFUSED, why="your body will not take it")
    return result(MortalResult.LONGEVITY_BEGUN, form=args.form.value)


async def found_enchantment(call: MortalCall, args: FoundEnchantmentInput) -> str:
    need = call.rules.global_enchantments.mage_skill
    if await skill_level(call.session, call.me.id, SkillKind.SPELLCRAFT) < need:
        fail(MortalResult.ENCHANTMENT_REFUSED, why=f"you need spellcraft of {need} to lay a global enchantment")
    law = await lay_enchantment(
        call.tick, call.me.id, name=args.name, effect=args.effect, world_id=call.me.world_id, region_id=None, strength=args.strength, vis_form=args.form
    )
    call.target(law.law_entity_id)
    await call.chronicle(ChronicleKind.COSMIC_LAW, lines.ENCHANTMENT, entity_ids=[call.me.id, law.law_entity_id], me=call.me.name, name=args.name)
    return result(MortalResult.ENCHANTMENT_FOUNDED, id=law.law_entity_id, name=args.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.UNDERTAKE_HEROQUEST, mortal, QuestInput, meta, undertake_heroquest),
        ToolSpec(MortalToolId.TAKE_LONGEVITY, mortal, LongevityInput, meta, take_longevity),
        ToolSpec(MortalToolId.FOUND_ENCHANTMENT, mortal, FoundEnchantmentInput, meta, found_enchantment),
    ]
