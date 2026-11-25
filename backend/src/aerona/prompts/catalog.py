from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from aerona.prompts.contexts import (
    accounts,
    blocks,
    chronicler,
    cosmos,
    council,
    divine_will,
    fate,
    genesis,
    imagery,
    localisation,
    mortal,
    narrative,
    opportunities,
    son_turn,
)
from aerona.prompts.contexts import agent as agent_contexts
from aerona.prompts.contexts.base import EmptyContext, LoreContext, PromptContext, RulesContext
from aerona.prompts.environment import TEMPLATE_SUFFIX, normalize, template
from aerona.prompts.errors import PromptContextMismatchError, PromptOutputMissingError
from aerona.prompts.ids import PromptArea, PromptId
from aerona.prompts.schemas import cosmos as cosmos_schemas
from aerona.prompts.schemas import council as council_schemas
from aerona.prompts.schemas import defaults
from aerona.prompts.schemas import divine_will as will_schemas
from aerona.prompts.schemas import fate as fate_schemas
from aerona.prompts.schemas import genesis as genesis_schemas
from aerona.prompts.schemas import localisation as localisation_schemas
from aerona.prompts.schemas import narrative as narrative_schemas
from aerona.prompts.schemas import shared as shared_schemas
from aerona.prompts.schemas.base import OutputModel
from aerona.prompts.schemas.build import build_json_schema
from aerona.prompts.schemas.constraints import Constraint, JsonSchema
from aerona.rules.registry import Rules

ConstraintFactory = Callable[[Rules], list[Constraint]]

DEFAULT_ATTENDANCE = "the summoned"


def no_constraints(rules: Rules) -> list[Constraint]:
    return []


@dataclass(frozen=True)
class PromptSpec:
    prompt_id: PromptId
    area: PromptArea
    context: type[PromptContext]
    output: type[OutputModel] | None = None
    constraints: ConstraintFactory = no_constraints
    schema_variables: Mapping[str, object] = field(default_factory=dict)

    @property
    def template_path(self) -> str:
        return f"{self.area}/{self.prompt_id}{TEMPLATE_SUFFIX}"


A = PromptArea
P = PromptId

SPECS: tuple[PromptSpec, ...] = (
    PromptSpec(P.IMAGE_PROMPT_RULES, A.SHARED, EmptyContext),
    PromptSpec(P.SECTION_KEYS_RULE, A.SHARED, EmptyContext),
    PromptSpec(P.NO_NUMBERS_CLAUSE, A.SHARED, EmptyContext),
    PromptSpec(P.LORE_LANGUAGE, A.SHARED, LoreContext),
    PromptSpec(P.RATIONALE_RULE, A.SHARED, RulesContext),
    PromptSpec(P.VERDICT_CRITERIA, A.SHARED, EmptyContext),
    PromptSpec(P.WORLD_HEADER, A.CONTEXT, blocks.WorldHeaderContext),
    PromptSpec(P.DIALECT_BLOCK, A.CONTEXT, blocks.DialectBlockContext),
    PromptSpec(P.WORLD_LINE, A.CONTEXT, blocks.WorldLineContext),
    PromptSpec(P.COSMOS_LINES, A.CONTEXT, blocks.CosmosLinesContext),
    PromptSpec(P.ENTITY_LINE, A.CONTEXT, blocks.EntityLineContext),
    PromptSpec(P.BOND_LINES, A.CONTEXT, blocks.BondLinesContext),
    PromptSpec(P.SOCIETY_LINES, A.CONTEXT, blocks.SocietyLinesContext),
    PromptSpec(P.ENTITY_DETAIL, A.CONTEXT, blocks.EntityDetailContext),
    PromptSpec(P.RECENT_CHRONICLE, A.CONTEXT, blocks.RecentChronicleContext),
    PromptSpec(P.THREAD_LINES, A.CONTEXT, blocks.ThreadLinesContext),
    PromptSpec(P.SIBLINGS, A.CONTEXT, blocks.SiblingsContext),
    PromptSpec(P.POWERS, A.CONTEXT, blocks.PowersContext),
    PromptSpec(P.LOCATION_TREE, A.CONTEXT, blocks.LocationTreeContext),
    PromptSpec(P.LANGUAGE_LINES, A.CONTEXT, blocks.LanguageLinesContext),
    PromptSpec(P.GEOGRAPHY_LINES, A.CONTEXT, blocks.GeographyLinesContext),
    PromptSpec(P.WORLD_SUMMARY, A.CONTEXT, blocks.WorldSummaryContext),
    PromptSpec(P.SON_MEMORY, A.CONTEXT, blocks.SonMemoryContext),
    PromptSpec(P.EVENT_ACCOUNT, A.CONTEXT, accounts.EventAccountContext),
    PromptSpec(P.EVENT_RECORDS, A.CONTEXT, accounts.EventRecordsContext),
    PromptSpec(P.SKY_CALENDAR, A.CONTEXT, blocks.SkyCalendarContext),
    PromptSpec(P.BUDGET_TRAILER, A.CONTEXT, blocks.BudgetTrailerContext),
    PromptSpec(P.INSPECT_SIBLING, A.CONTEXT, blocks.InspectSiblingContext),
    PromptSpec(P.GENESIS_SYSTEM, A.GENESIS, genesis.GenesisContext),
    PromptSpec(P.GENESIS_USER, A.GENESIS, genesis.GenesisContext, genesis_schemas.GenesisOutput, defaults.genesis_constraints),
    PromptSpec(P.GENESIS_WIZARD_SETTINGS, A.GENESIS, genesis.GenesisWizardContext),
    PromptSpec(P.SON_POWERS_SYSTEM, A.GENESIS, genesis.SonPowersContext),
    PromptSpec(P.SON_POWERS_USER, A.GENESIS, genesis.SonPowersContext, genesis_schemas.SonPowersOutput),
    PromptSpec(P.CREATOR_PORTRAIT_SYSTEM, A.GENESIS, genesis.CreatorPortraitContext),
    PromptSpec(P.CREATOR_PORTRAIT_USER, A.GENESIS, genesis.CreatorPortraitContext, shared_schemas.CreatorGodOutput),
    PromptSpec(P.SUMMON_SON_SYSTEM, A.GENESIS, genesis.SummonSonContext),
    PromptSpec(P.SUMMON_SON_USER, A.GENESIS, genesis.SummonSonContext, shared_schemas.SonProfileOutput),
    PromptSpec(P.AWAKEN_PEOPLES_SYSTEM, A.GENESIS, genesis.AwakenPeoplesContext),
    PromptSpec(P.AWAKEN_PEOPLES_USER, A.GENESIS, genesis.AwakenPeoplesContext, genesis_schemas.AwakenPeoplesOutput, defaults.awaken_constraints),
    PromptSpec(P.REVELATION_SYSTEM, A.GENESIS, genesis.RevelationContext),
    PromptSpec(P.REVELATION_USER, A.GENESIS, genesis.RevelationContext, genesis_schemas.RevelationOutput, defaults.revelation_constraints),
    PromptSpec(P.SON_TURN_SYSTEM, A.SON_TURN, son_turn.SonTurnSystemContext),
    PromptSpec(P.SON_TURN_USER, A.SON_TURN, son_turn.SonTurnUserContext),
    PromptSpec(P.SON_TURN_RESUME_NOTE, A.SON_TURN, EmptyContext),
    PromptSpec(P.SON_TURN_CONTINUATION, A.SON_TURN, son_turn.TurnContinuationContext),
    PromptSpec(P.CREATOR_WISHES, A.SON_TURN, son_turn.CreatorWishesContext),
    PromptSpec(P.REPUTATION_LINE, A.SON_TURN, son_turn.ReputationLineContext),
    PromptSpec(P.FATE_JUDGMENT_SYSTEM, A.FATE, fate.FateSystemContext),
    PromptSpec(P.FATE_JUDGMENT_USER, A.FATE, fate.FateJudgmentContext, fate_schemas.FateJudgmentOutput, defaults.judgment_constraints),
    PromptSpec(P.FATE_EXTRA_JUDGMENT_USER, A.FATE, fate.FateExtraJudgmentContext, fate_schemas.ExtraJudgmentOutput),
    PromptSpec(P.FATE_PRESCREEN_WARNINGS, A.FATE, fate.PrescreenWarningsContext),
    PromptSpec(P.FATE_CREATION_ENTRY, A.FATE, fate.FateCreationEntryContext),
    PromptSpec(P.AGE_EVENTS, A.FATE, fate.AgeEventsContext),
    PromptSpec(P.AGE_EVENTS_BY_WORLD, A.FATE, fate.AgeEventsByWorldContext),
    PromptSpec(P.CHRONICLER_SYSTEM, A.CHRONICLER, chronicler.ChroniclerSystemContext),
    PromptSpec(P.CHRONICLER_CONCISE_SYSTEM, A.CHRONICLER, chronicler.ChroniclerSystemContext),
    PromptSpec(P.CHRONICLER_USER, A.CHRONICLER, chronicler.ChroniclerUserContext, fate_schemas.ChronicleOutput, defaults.chronicle_constraints),
    PromptSpec(P.CHRONICLER_AUDIT_FIX_USER, A.CHRONICLER, chronicler.ChroniclerAuditFixContext, fate_schemas.ChronicleFixOutput),
    PromptSpec(
        P.CHRONICLER_MISSING_WORLDS_USER,
        A.CHRONICLER,
        chronicler.ChroniclerUserContext,
        fate_schemas.WorldSectionsOutput,
        defaults.world_sections_constraints,
    ),
    PromptSpec(P.CHRONICLER_LOST_AGE_USER, A.CHRONICLER, chronicler.ChroniclerUserContext, fate_schemas.ChronicleOutput, defaults.chronicle_constraints),
    PromptSpec(
        P.CHRONICLER_LOST_WORLD_SECTIONS_USER,
        A.CHRONICLER,
        chronicler.ChroniclerUserContext,
        fate_schemas.WorldSectionsOutput,
        defaults.world_sections_constraints,
    ),
    PromptSpec(P.NAMING_SYSTEM, A.NAMING, narrative.NamingContext),
    PromptSpec(P.NAMING_USER, A.NAMING, narrative.NamingContext, fate_schemas.NamingsOutput),
    PromptSpec(P.VOICES_SYSTEM, A.VOICES, narrative.VoicesContext),
    PromptSpec(
        P.VOICES_USER,
        A.VOICES,
        narrative.VoicesContext,
        narrative_schemas.VoicesOutput,
    ),
    PromptSpec(P.DEEPEN_ENTITY_SYSTEM, A.DEEPENING, narrative.DeepenEntityContext),
    PromptSpec(P.DEEPEN_ENTITY_USER, A.DEEPENING, narrative.DeepenEntityContext, narrative_schemas.DeepenOutput, defaults.deepen_constraints),
    PromptSpec(P.DEEPEN_CELESTIAL_SYSTEM, A.DEEPENING, narrative.DeepenCelestialContext),
    PromptSpec(P.DEEPEN_CELESTIAL_USER, A.DEEPENING, narrative.DeepenCelestialContext, narrative_schemas.DeepenOutput, defaults.deepen_constraints),
    PromptSpec(P.CREATOR_EPIC_SYSTEM, A.DEEPENING, narrative.CreatorEpicContext),
    PromptSpec(P.CREATOR_EPIC_USER, A.DEEPENING, narrative.CreatorEpicContext, narrative_schemas.CreatorEpicOutput, defaults.creator_epic_constraints),
    PromptSpec(P.CREATOR_DEEPEN_SYSTEM, A.DEEPENING, narrative.CreatorDeepenContext),
    PromptSpec(P.CREATOR_DEEPEN_USER, A.DEEPENING, narrative.CreatorDeepenContext, narrative_schemas.CreatorDepthOutput, defaults.creator_depth_constraints),
    PromptSpec(P.FOREIGN_GOD_DEEPEN_SYSTEM, A.DEEPENING, narrative.ForeignGodDeepenContext),
    PromptSpec(
        P.FOREIGN_GOD_DEEPEN_USER,
        A.DEEPENING,
        narrative.ForeignGodDeepenContext,
        narrative_schemas.ForeignGodDepthOutput,
        defaults.foreign_depth_constraints,
    ),
    PromptSpec(P.SON_EPIC_SYSTEM, A.DEEPENING, narrative.SonEpicContext),
    PromptSpec(P.SON_EPIC_USER, A.DEEPENING, narrative.SonEpicContext, narrative_schemas.SonEpicOutput),
    PromptSpec(P.ENTITY_IMAGE_PROMPTS_SYSTEM, A.IMAGE_PROMPTS, imagery.EntityImagePromptsContext),
    PromptSpec(P.ENTITY_IMAGE_PROMPTS_USER, A.IMAGE_PROMPTS, imagery.EntityImagePromptsContext, narrative_schemas.EntityImagePromptsOutput),
    PromptSpec(P.COSMOS_IMAGE_PROMPTS_SYSTEM, A.IMAGE_PROMPTS, imagery.CosmosImagePromptsContext),
    PromptSpec(P.COSMOS_IMAGE_PROMPTS_USER, A.IMAGE_PROMPTS, imagery.CosmosImagePromptsContext, narrative_schemas.CosmosImagePromptsOutput),
    PromptSpec(P.COUNCIL_PERSONA, A.COUNCIL, council.CouncilPersonaContext),
    PromptSpec(P.COUNCIL_AGENDA, A.COUNCIL, council.CouncilAgendaContext),
    PromptSpec(P.COUNCIL_SESSION_SYSTEM, A.COUNCIL, council.CouncilSessionContext),
    PromptSpec(
        P.COUNCIL_SESSION_USER,
        A.COUNCIL,
        council.CouncilSessionContext,
        council_schemas.CouncilOutput,
        defaults.council_constraints,
        {"attendance": DEFAULT_ATTENDANCE},
    ),
    PromptSpec(P.SON_CHAT_SYSTEM, A.COUNCIL, council.SonChatContext),
    PromptSpec(P.SON_CHAT_USER, A.COUNCIL, council.SonChatContext, council_schemas.SonChatOutput, defaults.son_chat_constraints),
    PromptSpec(P.TRANSLATE_SYSTEM, A.TRANSLATION, council.TranslateContext),
    PromptSpec(P.TRANSLATE_USER, A.TRANSLATION, council.TranslateContext, council_schemas.TranslationOutput, defaults.translation_constraints),
    PromptSpec(P.NEW_WORLD_SYSTEM, A.WORLD_BIRTH, cosmos.NewWorldContext),
    PromptSpec(P.NEW_WORLD_USER, A.WORLD_BIRTH, cosmos.NewWorldContext, cosmos_schemas.NewWorldOutput, defaults.new_world_constraints),
    PromptSpec(P.WORLD_INSPIRATION, A.WORLD_BIRTH, cosmos.WorldInspirationContext),
    PromptSpec(P.BOND_NODE_LINE, A.NETWORK_REPAIR, cosmos.BondNodeLineContext),
    PromptSpec(P.BOND_SUGGEST_SYSTEM, A.NETWORK_REPAIR, cosmos.BondSuggestContext),
    PromptSpec(P.BOND_SUGGEST_USER, A.NETWORK_REPAIR, cosmos.BondSuggestContext, cosmos_schemas.BondSuggestOutput, defaults.bond_suggest_constraints),
    PromptSpec(P.BOND_NAME_RELATED_SYSTEM, A.NETWORK_REPAIR, cosmos.BondNameRelatedContext),
    PromptSpec(
        P.BOND_NAME_RELATED_USER,
        A.NETWORK_REPAIR,
        cosmos.BondNameRelatedContext,
        cosmos_schemas.BondNameRelatedOutput,
        defaults.bond_name_related_constraints,
    ),
    PromptSpec(P.MORTAL_TURN_SYSTEM, A.MORTAL, mortal.MortalTurnSystemContext),
    PromptSpec(P.FALLEN_SON_TURN, A.MORTAL, mortal.FallenSonTurnContext),
    PromptSpec(P.MORTAL_TURN_USER, A.MORTAL, mortal.MortalTurnUserContext),
    PromptSpec(P.MORTAL_TURN_CONTINUATION, A.MORTAL, son_turn.TurnContinuationContext),
    PromptSpec(P.MORTAL_CONTEXT, A.MORTAL, mortal.MortalContextContext),
    PromptSpec(P.SON_OPPORTUNITIES, A.OPPORTUNITIES, opportunities.SonOpportunitiesContext),
    PromptSpec(P.MORTAL_OPPORTUNITIES, A.OPPORTUNITIES, opportunities.MortalOpportunitiesContext),
    PromptSpec(P.CREATOR_OPPORTUNITIES, A.OPPORTUNITIES, opportunities.CreatorOpportunitiesContext),
    PromptSpec(P.TOOL_REJECTION, A.AGENT, agent_contexts.ToolRejectionContext),
    PromptSpec(P.TOOL_FAILURE_REFUND, A.AGENT, agent_contexts.ToolFailureContext),
    PromptSpec(P.SON_GATE_REJECTION, A.AGENT, agent_contexts.SonGateContext),
    PromptSpec(P.MORTAL_GATE_REJECTION, A.AGENT, agent_contexts.MortalGateContext),
    PromptSpec(P.CAPTIVE_GATE_REJECTION, A.AGENT, agent_contexts.CaptiveGateContext),
    PromptSpec(P.ACTIONS_SPENT, A.AGENT, agent_contexts.ActionsSpentContext),
    PromptSpec(P.STATUS_LINE, A.AGENT, agent_contexts.StatusLineContext),
    PromptSpec(P.SLEEP_NOTICE, A.AGENT, agent_contexts.SleepNoticeContext),
    PromptSpec(P.PENDING_LONG_JOB, A.AGENT, agent_contexts.PendingLongJobContext),
    PromptSpec(P.ENTITY_STATE_REASON, A.AGENT, agent_contexts.EntityStateContext),
    PromptSpec(P.FIELD_ERROR, A.AGENT, agent_contexts.FieldErrorContext),
    PromptSpec(P.PER_EPOCH_LIMIT, A.AGENT, agent_contexts.PerEpochLimitContext),
    PromptSpec(P.LOCALISE_SYSTEM, A.LOCALISATION, localisation.LocaliseContext),
    PromptSpec(P.LOCALISE_USER, A.LOCALISATION, localisation.LocaliseContext, localisation_schemas.LocalisedLinesOutput),
    PromptSpec(P.DIVINE_WILL_SYSTEM, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_COMMAND, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_PLAN, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_ASK_LORE, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_CREATIVE_WORK, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_MECHANICS_GUIDE, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_FORESIGHT, A.DIVINE_WILL, divine_will.DivineWillSystemContext),
    PromptSpec(P.DIVINE_WILL_USER, A.DIVINE_WILL, divine_will.DivineWillUserContext),
    PromptSpec(P.DIVINE_WILL_TRANSLATE_SYSTEM, A.DIVINE_WILL, divine_will.DivineWillTranslateContext),
    PromptSpec(P.DIVINE_WILL_TRANSLATE_USER, A.DIVINE_WILL, divine_will.DivineWillTranslateContext, will_schemas.WillAnswerInLanguage),
)

PROMPTS: dict[PromptId, PromptSpec] = {spec.prompt_id: spec for spec in SPECS}


def spec_of(prompt_id: PromptId) -> PromptSpec:
    return PROMPTS[prompt_id]


def render(prompt_id: PromptId, context: PromptContext) -> str:
    spec = spec_of(prompt_id)
    if type(context) is not spec.context:
        raise PromptContextMismatchError(prompt_id, spec.context.__name__, type(context).__name__)
    return normalize(template(spec.template_path).render(**context.template_variables()))


def output_model(prompt_id: PromptId) -> type[OutputModel]:
    output = spec_of(prompt_id).output
    if output is None:
        raise PromptOutputMissingError(prompt_id)
    return output


def output_schema(
    prompt_id: PromptId,
    rules: Rules,
    constraints: Sequence[Constraint] = (),
    variables: Mapping[str, object] | None = None,
) -> JsonSchema:
    spec = spec_of(prompt_id)
    model = output_model(prompt_id)
    merged = {**spec.schema_variables, **(variables or {})}
    return build_json_schema(model, rules, [*spec.constraints(rules), *constraints], merged)


def validate_output(prompt_id: PromptId, payload: object) -> OutputModel:
    return output_model(prompt_id).model_validate(payload)
