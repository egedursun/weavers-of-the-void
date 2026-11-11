from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from aerona.core.errors import NotFoundError
from aerona.rules.registry import Rules
from aerona.services.player import (
    affairs,
    afflictions,
    arcana,
    aspirations,
    assignments,
    beyond,
    body,
    bonds,
    calendar,
    canon,
    celestial_depth,
    cheats,
    civilization,
    communication,
    cosmic,
    cosmic_orders,
    cosmography,
    creation,
    creator,
    creatures,
    culture,
    culture_mind,
    curation,
    death,
    diplomacy,
    discovery,
    disease,
    divine,
    divinity,
    dominion,
    economy,
    economy_depth,
    engine_control,
    environment,
    estates,
    evolution,
    factions,
    faith,
    fate_controls,
    feelings,
    finance,
    flora,
    foreign_gods,
    foundations,
    gatherings,
    genetics,
    goals,
    god_power,
    happenings,
    heroes,
    horizon,
    households,
    incidents,
    industry,
    interventions,
    intrigue,
    justice,
    knowledge,
    language_contact,
    languages,
    law_depth,
    levers,
    life_cycles,
    living_stats,
    lore,
    made_things,
    market,
    mechanics,
    memory,
    messages,
    military,
    military_depth,
    mind,
    modifiers,
    mortals,
    mythic,
    native_faith,
    pantheon,
    peoples,
    physics,
    places,
    profiles,
    realms,
    record_rows,
    regions,
    relations,
    renown,
    rewards,
    routes,
    rumours,
    settings,
    settlements,
    society,
    society_depth,
    son_tools,
    statecraft,
    structures,
    theories,
    titles,
    tongues,
    urban,
    urban_depth,
    variants,
    warfare,
    wilds,
    world_edits,
)
from aerona.services.player.canon import ConfirmationWord
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.player.scope import ActionOutcome, PlayerScope

SyncHandler = Callable[[PlayerScope, Any], Awaitable[ActionOutcome]]
JobHandler = Callable[[PlayerRuntime, Rules, Any], Awaitable[ActionOutcome]]
CostText = Callable[[Rules], str]


class ActionMode(StrEnum):
    LEDGERED = "ledgered"
    JOB = "job"


class ActionGroup(StrEnum):
    CREATOR = "creator"
    SONS = "sons"
    GOD_POWER = "god_power"
    DEATH = "death"
    MESSAGES = "messages"
    INTERVENTIONS = "interventions"
    ENTITIES = "entities"
    DIPLOMACY = "diplomacy"
    CANON = "canon"
    COSMOS = "cosmos"
    WORLDS = "worlds"
    FOREIGN_GODS = "foreign_gods"
    GOALS = "goals"
    SETTINGS = "settings"
    SOCIETY = "society"
    WARFARE = "warfare"
    CREATURES = "creatures"
    BEYOND = "beyond"
    LANGUAGES = "languages"
    MEMORY = "memory"
    FATE = "fate"


@dataclass(frozen=True)
class ActionSpec:
    id: str
    title: str
    group: ActionGroup
    input_model: type[BaseModel]
    cost: CostText
    rows: tuple[str, ...]
    sync: SyncHandler | None = None
    job: JobHandler | None = None
    confirmation: ConfirmationWord | None = None

    @property
    def mode(self) -> ActionMode:
        return ActionMode.JOB if self.job is not None else ActionMode.LEDGERED


class ActionDescriptor(BaseModel):
    id: str
    title: str
    group: ActionGroup
    mode: ActionMode
    cost: str
    confirmation: str | None
    rows: list[str]
    input_schema: dict[str, Any]


def free(rules: Rules) -> str:
    del rules
    return "Free"


def foreign_kill_cost(rules: Rules) -> str:
    table = rules.god_power
    return f"{table.kill_foreign_base_cost} + power x {table.kill_foreign_strength_pct}% essence (x{table.kill_immortal_foreign_mult} if deathless)"


def scheme_costs(rules: Rules) -> str:
    table = rules.death
    return f"rite {table.sibling_rite_cost}, descent {table.sibling_descent_cost}, bargain {table.sibling_bargain_cost} essence from the sibling"


def essence(amount: int) -> str:
    return f"{amount} essence" if amount else "Free"


@dataclass(frozen=True)
class Meta:
    id: str
    title: str
    group: ActionGroup


def _sync(
    meta: Meta, handler: SyncHandler, model: type[BaseModel], cost: CostText, rows: tuple[str, ...], *, confirmation: ConfirmationWord | None = None
) -> ActionSpec:
    return ActionSpec(meta.id, meta.title, meta.group, model, cost, rows, sync=handler, confirmation=confirmation)


def _job(meta: Meta, handler: JobHandler, model: type[BaseModel], cost: CostText, rows: tuple[str, ...]) -> ActionSpec:
    return ActionSpec(meta.id, meta.title, meta.group, model, cost, rows, job=handler)


G = ActionGroup

CREATOR_ACTIONS = (
    _sync(Meta("creator:edit", "Edit the Creator", G.CREATOR), creator.edit_creator, creator.EditCreator, free, ("ACT-042",)),
    _sync(Meta("creator:note", "Standing note to the sons", G.CREATOR), creator.set_creator_note, creator.CreatorNote, free, ("ACT-043",)),
    _sync(Meta("creator:passions", "Reveal the Creator's passions", G.CREATOR), creator.set_passions, creator.SetPassions, free, ("ACT-121",)),
    _sync(Meta("creator:reputation", "Push a son's view of the Creator", G.CREATOR), creator.nudge_reputation, creator.NudgeReputation, free, ("ACT-122",)),
    _sync(Meta("creator:mood", "Set the Creator's mood", G.CREATOR), creator.set_mood, creator.SetMood, free, ("ACT-170",)),
    _job(
        Meta("creator:content", "Portrait, epic or deepening of the Creator", G.CREATOR),
        creator.write_creator_content,
        creator.CreatorContent,
        free,
        ("ACT-009", "ACT-010", "ACT-011"),
    ),
    _job(Meta("son:epic", "Compose a son's epic", G.SONS), creator.write_son_epic, creator.SonEpic, free, ("ACT-013",)),
)

SON_ACTIONS = (
    _job(
        Meta("summon_son", "Summon a son", G.SONS),
        creation.summon_son,
        creation.SummonSon,
        lambda rules: essence(rules.costs.summon_son),
        ("ACT-001", "EPOCH-052"),
    ),
    _sync(Meta("son:world", "Send a son to a world", G.SONS), assignments.assign_son_world, assignments.SonWorld, free, ("ACT-127",)),
    _sync(
        Meta("son:reset_counters", "Reset a son's tool counters for this epoch", G.SONS), son_tools.reset_counters, son_tools.SonTarget, free, ("TOOL-S-026",)
    ),
    _sync(Meta("son:turn_rank", "Set a son's place in the gods' turn", G.SONS), son_tools.set_turn_rank, son_tools.TurnRank, free, ("CAT-023",)),
    _job(Meta("son:birth_child", "Let a son bear a child", G.SONS), creation.birth_child, creation.BirthChild, free, ("LLM-036",)),
    _sync(Meta("son:protection", "Clear a son's assignment protection", G.SONS), assignments.clear_son_protection, assignments.SonTarget, free, ("ACT-128",)),
    _sync(
        Meta("son:distribute", "Distribute sons to godless worlds now", G.SONS),
        assignments.distribute_now,
        assignments.DistributeSons,
        free,
        ("ACT-129", "ACT-130"),
    ),
    _sync(
        Meta("son:edit", "Edit a son", G.SONS),
        assignments.edit_son,
        assignments.EditSon,
        free,
        ("ACT-149", "ACT-150", "ACT-151", "ACT-152", "ACT-153", "ACT-154"),
    ),
    _sync(Meta("son:image_prompt", "Describe a son's likeness", G.SONS), assignments.set_son_image_prompt, assignments.SonImagePrompt, free, ("ACT-041",)),
    _sync(
        Meta("son:star", "Set a star upon a son", G.SONS),
        assignments.add_star,
        assignments.SonTarget,
        lambda rules: f"{rules.core_rules.star_essence_base} + {rules.core_rules.star_essence_step} per star essence",
        ("ACT-024",),
    ),
    _sync(
        Meta("son:ascend", "Ascend a son to the next class", G.SONS),
        assignments.ascend,
        assignments.SonTarget,
        lambda rules: essence(rules.ascension.essence_cost),
        ("ACT-025", "ACT-026"),
    ),
    _sync(
        Meta("bless", "Bless a son", G.SONS),
        interventions.bless,
        interventions.Bless,
        lambda rules: f"essence or existence {rules.costs.bless_essence}, health {rules.costs.bless_hp}, stat {rules.costs.bless_stat} essence",
        ("ACT-022", "ACT-023"),
    ),
    _sync(
        Meta("punish", "Punish, suppress or pardon a son", G.SONS),
        interventions.punish,
        interventions.Punish,
        lambda rules: f"lightning {rules.costs.lightning}, suppression {rules.balance.suppress_revolt} essence; chain, exile and pardon free",
        ("ACT-027", "ACT-028", "ACT-029", "ACT-030", "ACT-031", "ACT-032", "ACT-033"),
    ),
    _sync(Meta("command", "Command a son", G.MESSAGES), messages.command_son, messages.CommandSon, free, ("ACT-021",)),
    _sync(Meta("son:address_sibling", "Order a son to address a sibling", G.MESSAGES), messages.address_sibling, messages.AddressSibling, free, ("CAT-056",)),
)

GOD_POWER_ACTIONS = (
    _sync(
        Meta("rebellion:force", "Force a son into rebellion", G.GOD_POWER),
        god_power.force_rebellion,
        god_power.ForceRebellion,
        free,
        ("POW-009", "POW-010"),
    ),
    _sync(Meta("drain:son", "Drain a son's essence", G.GOD_POWER), god_power.drain_son, god_power.SonTarget, free, ("ACT-067", "ACT-097")),
    _sync(Meta("devour:son", "Devour a son", G.GOD_POWER), god_power.devour_son, god_power.DevourSon, free, ("ACT-068", "ACT-098")),
    _sync(
        Meta("drain:mortal", "Drain or devour a mortal", G.GOD_POWER), god_power.drain_mortal, god_power.DrainMortal, free, ("ACT-069", "ACT-102", "ACT-103")
    ),
    _sync(Meta("harvest", "Harvest a community's faith", G.GOD_POWER), god_power.harvest, god_power.EntityTarget, free, ("ACT-070", "ACT-109")),
    _sync(Meta("drain:foreign_god", "Drain a foreign god", G.GOD_POWER), god_power.drain_foreign_god, god_power.ForeignGodTarget, free, ("ACT-071", "ACT-111")),
    _sync(
        Meta("kill:foreign_god", "Kill or devour a foreign god", G.GOD_POWER),
        god_power.kill_foreign_god,
        god_power.KillForeignGod,
        foreign_kill_cost,
        ("ACT-072", "ACT-112", "ACT-113"),
    ),
    _sync(
        Meta("resurrect:mortal", "Resurrect a mortal", G.GOD_POWER),
        god_power.resurrect_mortal,
        god_power.EntityTarget,
        lambda rules: f"{rules.god_power.resurrect_mortal_base_cost} + {rules.god_power.resurrect_mortal_cost_per_power} per power level essence",
        ("ACT-073", "ACT-104"),
    ),
    _sync(
        Meta("deify", "Raise a mortal to godhood", G.GOD_POWER),
        god_power.deify_mortal,
        god_power.EntityTarget,
        lambda rules: essence(rules.god_power.deify_cost),
        ("ACT-074", "ACT-114", "ACT-115", "ACT-116", "ACT-117"),
    ),
    _sync(
        Meta("demote", "Demote a son", G.GOD_POWER),
        god_power.demote_son,
        god_power.SonTarget,
        lambda rules: essence(rules.god_power.demote_cost),
        ("ACT-075", "ACT-099"),
    ),
    _sync(
        Meta("strip_power", "Strip a son's power", G.GOD_POWER),
        god_power.strip_power,
        god_power.StripPower,
        lambda rules: essence(rules.god_power.strip_power_cost),
        ("ACT-076", "ACT-100"),
    ),
    _sync(Meta("son:power", "Create, reshape or unmake a son's power", G.GOD_POWER), god_power.set_son_power, god_power.SonPower, free, ()),
    _sync(
        Meta("absolute_command", "Absolute command", G.GOD_POWER),
        god_power.absolute_command,
        god_power.AbsoluteCommand,
        lambda rules: essence(rules.god_power.absolute_command_cost),
        ("ACT-077", "ACT-101"),
    ),
    _sync(
        Meta("prophet", "Choose a prophet", G.GOD_POWER),
        god_power.choose_prophet,
        god_power.EntityTarget,
        lambda rules: essence(rules.god_power.prophet_cost),
        ("ACT-078", "ACT-105"),
    ),
    _sync(
        Meta("manifest", "Manifest before mortals", G.GOD_POWER),
        god_power.manifest,
        god_power.Manifest,
        lambda rules: essence(rules.god_power.manifest_cost),
        ("ACT-079", "ACT-106"),
    ),
    _sync(
        Meta("bloodline_curse", "Curse or free a bloodline", G.GOD_POWER),
        god_power.bloodline_curse,
        god_power.BloodlineCurse,
        lambda rules: f"curse {rules.god_power.bloodline_curse_cost}, lift {rules.god_power.bloodline_curse_lift_cost} essence",
        ("ACT-080", "ACT-107", "ACT-108"),
    ),
    _sync(
        Meta("convert", "Convert to the Creator", G.GOD_POWER),
        god_power.convert,
        god_power.EntityTarget,
        lambda rules: essence(rules.god_power.convert_cost),
        ("ACT-081", "ACT-110"),
    ),
    _sync(
        Meta("wrath", "Wrath upon a record", G.GOD_POWER),
        god_power.wrath,
        god_power.Wrath,
        lambda rules: f"{rules.god_power.wrath_base_cost} + {rules.god_power.wrath_cost_per_power} per power level essence",
        ("ACT-082", "ACT-118", "ACT-119"),
    ),
    _sync(
        Meta("wrath:world", "Wrath upon a world", G.GOD_POWER),
        god_power.world_wrath,
        god_power.WorldWrath,
        lambda rules: essence(rules.god_power.world_wrath_cost),
        ("ACT-083", "ACT-120"),
    ),
)

DEATH_ACTIONS = (
    _sync(
        Meta("resurrect:son", "Resurrect a son", G.DEATH),
        death.resurrect_son,
        death.ResurrectSon,
        lambda rules: essence(rules.balance.resurrection),
        ("ACT-044",),
    ),
    _sync(
        Meta("take_life", "Take a mortal's life", G.DEATH),
        death.take_life,
        death.TakeLife,
        lambda rules: essence(rules.death.creator_take_life_cost),
        ("ACT-045", "ACT-126"),
    ),
    _sync(
        Meta("sibling:scheme", "Order a sibling's resurrection scheme", G.DEATH),
        death.sibling_scheme,
        death.SiblingScheme,
        scheme_costs,
        ("DTH-015", "DTH-016", "DTH-017", "DTH-018"),
    ),
    _sync(
        Meta("sibling:scatter", "Order a sibling to scatter a dead son's bones", G.DEATH),
        death.scatter_bones,
        death.ScatterBones,
        lambda rules: f"{rules.death.scatter_bones_cost} essence from the sibling",
        ("DTH-019",),
    ),
    _sync(
        Meta("kill:son", "Kill a son", G.DEATH), death.kill_son, death.KillSon, lambda rules: essence(rules.death.creator_kill_son_cost), ("ACT-046", "ACT-125")
    ),
)

MESSAGE_ACTIONS = (
    _sync(Meta("dream", "Send a dream", G.MESSAGES), messages.send_dream, messages.SendDream, lambda rules: essence(rules.balance.dream), ("CNCL-016",)),
    _sync(
        Meta("answer_prayer", "Answer a prayer", G.MESSAGES),
        messages.answer_prayer,
        messages.AnswerPrayer,
        lambda rules: f"the essence you give (0 to {rules.god_actions.prayer_essence_cap})",
        ("ACT-034", "ACT-035", "ACT-036", "ACT-037"),
    ),
)

INTERVENTION_ACTIONS = (
    _job(
        Meta("revelation", "Send a revelation", G.INTERVENTIONS),
        interventions.revelation,
        interventions.Revelation,
        lambda rules: essence(rules.costs.revelation),
        ("ACT-002",),
    ),
    _sync(
        Meta("intervene", "Miracle, disaster, teaching or curse", G.INTERVENTIONS),
        interventions.intervene,
        interventions.Intervene,
        lambda rules: (
            f"miracle {rules.intervention_costs.miracle}, disaster {rules.intervention_costs.disaster}, "
            f"teaching {rules.intervention_costs.teach_knowledge}, curse {rules.intervention_costs.curse} essence"
        ),
        (
            "ACT-062",
            "ACT-063",
            "ACT-064",
            "ACT-065",
            "ACT-066",
            "INT-003",
            "INT-006",
            "INT-007",
            "INT-008",
            "INT-009",
            "INT-010",
            "INT-011",
            "INT-012",
            "INT-013",
            "INT-014",
            "INT-015",
            "INT-016",
            "INT-017",
            "INT-018",
            "INT-019",
            "INT-020",
            "INT-021",
            "INT-022",
        ),
    ),
    _sync(
        Meta("knowledge:set", "Grant or remove known knowledge", G.INTERVENTIONS),
        interventions.set_knowledge,
        interventions.SetKnowledge,
        free,
        ("INT-001", "INT-002"),
    ),
)

ENTITY_ACTIONS = (
    _sync(Meta("entity:move", "Move a record", G.ENTITIES), assignments.move_entity, assignments.MoveEntity, free, ("ACT-131", "ACT-132")),
    _sync(Meta("entity:patron", "Assign a patron", G.ENTITIES), assignments.assign_patron, assignments.AssignPatron, free, ("ACT-133", "ACT-134")),
    _sync(Meta("entity:stat", "Set a stat", G.ENTITIES), assignments.set_stat, assignments.SetStat, free, ("ACT-140",)),
    _sync(Meta("entity:tags", "Assign marks, traits, mechanics and laws", G.ENTITIES), assignments.set_tags, assignments.SetTags, free, ("ACT-141", "INT-004")),
    _sync(Meta("entity:agent", "Single out a mortal agent", G.ENTITIES), assignments.select_agent, assignments.SelectAgent, free, ("ACT-142",)),
)

DIPLOMACY_ACTIONS = (
    _sync(
        Meta("decree", "Decree war, peace, alliance or trade", G.DIPLOMACY),
        diplomacy.decree,
        diplomacy.Decree,
        free,
        ("ACT-135", "ACT-136", "ACT-137", "ACT-138", "ACT-139"),
    ),
    _sync(Meta("expedition", "Send an expedition", G.DIPLOMACY), diplomacy.expedition, diplomacy.Expedition, free, ("ACT-143", "ACT-144")),
    _sync(Meta("explore", "Send to explore", G.DIPLOMACY), diplomacy.explore, diplomacy.Explore, free, ("ACT-095", "ACT-145")),
    _sync(Meta("seek_route", "Show the road of the sky", G.DIPLOMACY), diplomacy.seek_route, diplomacy.EntityTarget, free, ("ACT-096", "ACT-146")),
    _sync(Meta("rite", "Order a resurrection rite", G.DIPLOMACY), diplomacy.order_rite, diplomacy.Rite, free, ("ACT-147",)),
    _sync(Meta("discovery_round", "Discovery round in a world", G.DIPLOMACY), diplomacy.discovery_round, diplomacy.DiscoveryRound, free, ("ACT-148",)),
    _sync(Meta("federation", "Found a federation", G.DIPLOMACY), diplomacy.found_federation, diplomacy.Federation, free, ("ACT-181",)),
)

CANON_ACTIONS = (
    _sync(Meta("canon:set", "Strike from or restore to canon", G.CANON), canon.set_canon, canon.SetCanon, free, ("ACT-038", "ACT-039")),
    _sync(Meta("record:edit", "Edit a record", G.CANON), canon.edit_record, canon.EditRecord, free, ("ACT-040", "CAT-035")),
    _sync(Meta("chronicle:edit", "Amend a chronicle line", G.CANON), curation.edit_chronicle_line, curation.EditChronicleLine, free, ("CORE-013",)),
    _sync(Meta("belief:rename", "Derive a people's name for a god anew", G.CANON), curation.rename_folk_god, curation.BeliefTarget, free, ("INV-016",)),
    _sync(Meta("name:accept", "Accept a name despite the dialect", G.CANON), curation.accept_name, curation.AcceptName, free, ("CORE-043",)),
    _sync(Meta("thread:open", "Open a story", G.CANON), canon.open_thread, canon.OpenThread, free, ("ACT-175",)),
    _sync(Meta("thread:close", "Close a story", G.CANON), canon.close_thread, canon.CloseThread, free, ("ACT-176",)),
    _sync(Meta("thread:advance", "Move a story forward", G.CANON), canon.advance_thread, canon.AdvanceThread, free, ("LLM-069",)),
    _sync(Meta("epoch:edit", "Rewrite an epoch's name or narrative", G.CANON), canon.edit_epoch, canon.EditEpoch, free, ("LLM-076",)),
    _sync(Meta("fact:add", "Add a canon fact", G.CANON), canon.add_fact, canon.AddFact, free, ("ACT-177",)),
    _sync(Meta("fact:remove", "Retire a canon fact", G.CANON), canon.remove_fact, canon.FactTarget, free, ("ACT-178",)),
    _sync(Meta("belief:edit", "Edit a people's belief", G.CANON), canon.edit_belief, canon.EditBelief, free, ("ACT-179",)),
    _sync(Meta("belief:forget", "Make a people forget its tale of a god", G.CANON), canon.forget_belief, canon.ForgetBelief, free, ("S9.1/RP3",)),
    _sync(Meta("bond:add", "Add a bond", G.CANON), canon.add_bond, canon.AddBond, free, ("ACT-182",)),
    _sync(Meta("bond:remove", "Break a bond", G.CANON), canon.remove_bond, canon.BondTarget, free, ("ACT-183",)),
    _sync(Meta("map_note:add", "Pin a map note", G.CANON), canon.add_map_note, canon.AddMapNote, free, ("SVC-126",)),
    _sync(Meta("map_note:remove", "Remove a map note", G.CANON), canon.remove_map_note, canon.MapNoteTarget, free, ("SVC-127",)),
    _sync(
        Meta("record:merge", "Merge two records", G.CANON),
        canon.merge_records,
        canon.MergeRecords,
        free,
        ("SVC-130", "SVC-131"),
        confirmation=ConfirmationWord.MERGE,
    ),
    _sync(Meta("record:favorite", "Mark a favourite", G.CANON), canon.set_favorite, canon.Favorite, free, ("SVC-132",)),
    _sync(Meta("record:note", "Personal note", G.CANON), canon.set_private_note, canon.PrivateNote, free, ("SVC-133",)),
)

COSMIC_ACTIONS = (
    _job(
        Meta("create_world", "Create a world", G.COSMOS),
        creation.create_world,
        creation.CreateWorld,
        lambda rules: essence(rules.balance.create_world),
        ("ACT-003", "ACT-084"),
    ),
    _job(
        Meta("awaken_peoples", "Awaken peoples", G.COSMOS),
        creation.awaken_peoples,
        creation.AwakenPeoples,
        lambda rules: f"{rules.balance.awaken_peoples} essence per {rules.awakening.batch_cap} peoples",
        ("ACT-005",),
    ),
    _sync(
        Meta("route", "Sever, reopen or reveal a route", G.COSMOS),
        cosmic.route_action,
        cosmic.RouteCommand,
        lambda rules: f"sever {rules.beyond.sever_route_cost}, reopen {rules.beyond.reopen_route_cost}, reveal {rules.travel.reveal_route_cost} essence",
        ("ACT-047", "ACT-088", "ACT-090", "ACT-091"),
    ),
    _sync(Meta("journey:recall", "Recall a journey", G.COSMOS), cosmic.recall_journey, cosmic.JourneyTarget, free, ("ACT-048", "ACT-089")),
    _sync(
        Meta("cosmic:hang_star", "Hang a star", G.COSMOS),
        cosmic.hang_star,
        cosmic.HangStar,
        lambda rules: essence(rules.cosmic_costs.ignite_star),
        ("ACT-049", "ACT-050", "ACT-059"),
    ),
    _sync(
        Meta("cosmic:seal_gate", "Seal a gate", G.COSMOS),
        cosmic.seal_gate,
        cosmic.RouteTarget,
        lambda rules: essence(rules.cosmic_costs.seal_gate),
        ("ACT-051", "ACT-058"),
    ),
    _sync(
        Meta("cosmic:cleanse_leak", "Mend a world's leak", G.COSMOS),
        cosmic.cleanse_leak,
        cosmic.WorldTarget,
        lambda rules: essence(rules.cosmic_costs.cleanse_leak),
        ("ACT-052", "ACT-060"),
    ),
    _sync(
        Meta("cosmic:forget_world", "Forget a world", G.COSMOS),
        cosmic.forget,
        cosmic.WorldTarget,
        lambda rules: essence(rules.cosmic_costs.forget_world),
        ("ACT-053", "ACT-061"),
    ),
    _sync(
        Meta("cosmic:rekindle_star", "Rekindle a dead star", G.COSMOS),
        cosmic.rekindle,
        cosmic.StarTarget,
        lambda rules: essence(rules.cosmic_costs.rekindle_dead_star),
        ("ACT-054", "ACT-180"),
    ),
    _sync(
        Meta("cosmic:extinguish_star", "Extinguish a star", G.COSMOS),
        cosmic.extinguish,
        cosmic.StarTarget,
        lambda rules: essence(rules.cosmic_costs.extinguish_star),
        ("PAN-023",),
    ),
    _sync(
        Meta("cosmic:soul_bind", "Bind a soul to a vessel", G.COSMOS),
        cosmic.bind_soul,
        cosmic.SoulBind,
        lambda rules: essence(rules.cosmic_costs.spirit_cloak),
        ("ACT-055", "ACT-086"),
    ),
    _sync(
        Meta("cosmic:legendary_quest", "Open a legendary quest", G.COSMOS),
        cosmic.legendary_quest,
        cosmic.LegendaryQuest,
        lambda rules: essence(rules.cosmic_costs.legendary_expedition),
        ("ACT-056", "ACT-087"),
    ),
    _sync(
        Meta("cosmic:sky_event", "Order a sky event", G.COSMOS),
        cosmic.order_sky_event,
        cosmic.SkyEvent,
        lambda rules: essence(rules.cosmic_costs.sky_event),
        ("ACT-057", "ACT-085"),
    ),
    _sync(Meta("exile", "Exile to another world", G.COSMOS), cosmic.exile, cosmic.Exile, free, ("ACT-092", "ACT-093")),
    _sync(Meta("pardon", "Pardon oath-breaking, exile and curse", G.COSMOS), cosmic.pardon, cosmic.EntityTarget, free, ("ACT-094",)),
    _sync(Meta("star:delete", "Remove a star", G.COSMOS), cosmic.delete_star, cosmic.StarTarget, free, ("ACT-164",)),
    _sync(Meta("star:edit", "Edit a star", G.COSMOS), cosmic.edit_star, cosmic.EditStar, free, ("ACT-165",)),
    _sync(Meta("star:depth", "Rewrite a star's lore", G.COSMOS), celestial_depth.edit_star_depth, celestial_depth.StarDepth, free, ()),
    _sync(Meta("world:depth", "Rewrite a world's lore", G.WORLDS), celestial_depth.edit_world_depth, celestial_depth.WorldDepth, free, ()),
    _sync(
        Meta("scale:depth", "Rewrite the lore of a galaxy, cluster or dimension", G.COSMOS),
        celestial_depth.edit_scale_depth,
        celestial_depth.ScaleDepth,
        free,
        ("S10.10", "S10.11", "S10.13"),
    ),
    _sync(Meta("route:open", "Open a road", G.COSMOS), cosmic.open_route, cosmic.OpenRoute, free, ("ACT-166",)),
    _sync(Meta("climate", "Command a climate era", G.COSMOS), cosmic.command_climate, cosmic.Climate, free, ("ACT-167",)),
    _sync(Meta("cosmos:resource", "Define the travel resource", G.COSMOS), cosmic.define_resource, cosmic.DefineResource, free, ("ACT-168",)),
    _sync(Meta("cosmos:deposit", "Open a cosmic deposit", G.COSMOS), cosmic.open_deposit, cosmic.OpenDeposit, free, ("ACT-169",)),
)

WORLD_ACTIONS = (
    _sync(
        Meta("world:edit", "Reshape a world", G.WORLDS),
        world_edits.edit_world,
        world_edits.EditWorld,
        free,
        ("ACT-155", "ACT-156", "ACT-157", "ACT-158", "ACT-159", "ACT-160", "ACT-161", "ACT-162"),
    ),
    _sync(Meta("world:orbit", "Move a world's orbit", G.WORLDS), cosmic.set_orbit, cosmic.Orbit, free, ("ACT-163",)),
)

FOREIGN_GOD_ACTIONS = (
    _job(Meta("foreign_god:place", "Place an old god", G.FOREIGN_GODS), creation.place_and_deepen, creation.PlaceForeignGod, free, ("ACT-171", "SVC-195")),
    _job(Meta("foreign_god:deepen", "Deepen a foreign god", G.FOREIGN_GODS), creation.deepen_foreign_god, creation.ForeignGodTarget, free, ("ACT-012",)),
    _sync(
        Meta("foreign_god:edit", "Edit a foreign god", G.FOREIGN_GODS),
        foreign_gods.edit_foreign_god,
        foreign_gods.EditForeignGod,
        free,
        ("ACT-172", "ACT-173", "ACT-174"),
    ),
)

GOAL_ACTIONS = (
    _sync(Meta("scenario:start", "Start a scenario", G.GOALS), goals.start_scenario, goals.StartScenario, free, ("ACT-123",)),
    _sync(Meta("scenario:abandon", "Abandon a scenario", G.GOALS), goals.abandon_scenario, goals.AbandonScenario, free, ("ACT-124",)),
)

SETTING_ACTIONS = (
    _sync(Meta("settings", "World settings", G.SETTINGS), settings.update_settings, settings.WorldSettings, free, ("SVC-196",)),
    _sync(
        Meta("cheat:essence", "Essence from nowhere", G.SETTINGS),
        cheats.cheat_essence,
        cheats.CheatEssence,
        lambda rules: f"adds up to {rules.server.cheat_essence_max} essence",
        ("SVC-197",),
    ),
)

SETTLEMENT_ACTIONS = (
    _sync(Meta("settlement:shelter", "Shelter a settlement from ruin", G.SOCIETY), settlements.shelter_from_ruin, settlements.RuinShelter, free, ()),
    _sync(Meta("settlement:abandon", "Abandon a settlement", G.SOCIETY), settlements.abandon, settlements.SettlementTarget, free, ()),
    _sync(Meta("settlement:resettle", "Resettle a ruin", G.SOCIETY), settlements.resettle, settlements.Resettle, free, ()),
    _sync(Meta("mortal:child", "Bless two mortals with a child", G.SOCIETY), settlements.bless_child, settlements.Parents, free, ()),
    _sync(Meta("settlement:capital", "Seat a realm's capital", G.SOCIETY), settlements.seat_capital, settlements.SettlementTarget, free, ("SVC-136",)),
    _job(Meta("mortal:act", "Let a mortal act now", G.ENTITIES), creation.mortal_act, creation.MortalTarget, free, ("LLM-129",)),
    _sync(Meta("community:notable", "Raise a notable", G.SOCIETY), settlements.raise_notable, settlements.Notable, free, ()),
    _sync(Meta("community:crown", "Crown a ruler", G.SOCIETY), settlements.crown, settlements.CommunityTarget, free, ()),
    _sync(Meta("people:village", "Send settlers to found a village", G.SOCIETY), settlements.found_village, settlements.PeopleTarget, free, ()),
    _sync(Meta("settlement:ethnogenesis", "Let a new people arise", G.SOCIETY), settlements.ethnogenesis, settlements.SettlementTarget, free, ()),
    _sync(Meta("species:awaken", "Awaken a species to sapience", G.CREATURES), settlements.awaken, settlements.SpeciesTarget, free, ()),
    _sync(Meta("ruler:heir", "Name a ruler's heir", G.SOCIETY), settlements.name_heir, settlements.Heir, free, ()),
    _sync(Meta("spirit:rest", "Lay a spirit to rest", G.BEYOND), settlements.rest_spirit, settlements.SpiritTarget, free, ()),
    _sync(Meta("record:retire", "End a record's life in the world", G.ENTITIES), settlements.retire, settlements.RetireRecord, free, ()),
)

SOCIETY_ACTIONS = (
    _sync(Meta("society:shares", "Set class shares", G.SOCIETY), society.shape_shares, society.ClassShares, free, ()),
    _sync(Meta("society:satisfaction", "Set class contentment", G.SOCIETY), society.shape_satisfaction, society.Satisfaction, free, ()),
    _sync(Meta("society:stores", "Set the stores", G.SOCIETY), society.shape_stores, society.Stores, free, ()),
    _sync(Meta("society:famine", "Send famine", G.SOCIETY), society.famine, society.SocietyTarget, free, ()),
    _sync(Meta("society:plenty", "Send plenty", G.SOCIETY), society.plenty, society.SocietyTarget, free, ()),
    _sync(Meta("society:forge", "Order weapons forged", G.SOCIETY), society.forge, society.SocietyTarget, free, ()),
    _sync(Meta("society:uprising", "Incite a class uprising", G.SOCIETY), society.class_uprising, society.ClassUprising, free, ()),
    _sync(Meta("resource:commodity", "Set what a resource yields", G.SOCIETY), society.resource_commodity, society.ResourceCommodity, free, ()),
    _sync(Meta("community:mint", "Order a coin minted", G.SOCIETY), society.mint, society.Mint, free, ()),
    _sync(Meta("community:work", "Commission a work", G.SOCIETY), society.raise_work, society.Work, free, ("S7.2",)),
    _sync(Meta("community:exodus", "Send a community into exodus", G.SOCIETY), society.exodus, society.Exodus, free, ()),
    _sync(Meta("community:contact", "Bring two cultures into contact", G.SOCIETY), society.contact, society.Contact, free, ()),
    _sync(Meta("world:golden_age", "Proclaim a golden age", G.WORLDS), society.golden_age, society.WorldTarget, free, ()),
    _sync(Meta("world:end_golden_age", "End a golden age", G.WORLDS), society.close_golden_age, society.WorldTarget, free, ()),
)

CIVILIZATION_ACTIONS = (
    _sync(Meta("civilization:tier", "Set a civilization tier", G.SOCIETY), civilization.tier, civilization.Tier, free, ()),
    _sync(Meta("civilization:independence", "Grant a colony independence", G.SOCIETY), civilization.independence, civilization.Independence, free, ()),
    _sync(Meta("civilization:reclaim", "Reclaim a colony", G.SOCIETY), civilization.reclaim, civilization.Reclaim, free, ()),
    _sync(Meta("world:previous_creation", "Reveal a previous creation", G.WORLDS), civilization.previous_creation, civilization.WorldTarget, free, ()),
    _sync(Meta("civilization:loan", "Impose a loan", G.SOCIETY), civilization.loan, civilization.Loan, free, ()),
    _sync(Meta("civilization:forgive_debt", "Forgive a debt", G.SOCIETY), civilization.forgive, civilization.DebtTarget, free, ()),
    _sync(Meta("civilization:enforce_debt", "Enforce a debt", G.SOCIETY), civilization.enforce, civilization.DebtTarget, free, ()),
    _sync(Meta("civilization:barter", "Order a barter", G.SOCIETY), civilization.barter, civilization.Pair, free, ()),
    _sync(Meta("civilization:adoption", "Order an adoption", G.SOCIETY), civilization.adoption, civilization.Adoption, free, ()),
    _sync(Meta("civilization:treaty", "Order an interworld treaty", G.DIPLOMACY), civilization.treaty, civilization.Treaty, free, ()),
)

HERO_ACTIONS = (
    _sync(Meta("hero:raise", "Raise a hero", G.SOCIETY), heroes.hero, heroes.CommunityTarget, free, ()),
    _sync(Meta("hero:quest", "Send a hero on a quest", G.SOCIETY), heroes.quest, heroes.Quest, free, ()),
    _sync(Meta("hero:resolve", "Resolve a hero's quest", G.SOCIETY), heroes.resolve, heroes.QuestEnd, free, ()),
    _sync(Meta("hero:recall", "Recall a hero", G.SOCIETY), heroes.recall, heroes.HeroTarget, free, ()),
    _sync(Meta("hero:apprentice", "Give a master an apprentice", G.SOCIETY), heroes.apprentice, heroes.HeroTarget, free, ()),
    _sync(Meta("hero:hunt", "Send a hero to hunt a monster", G.CREATURES), heroes.hunt, heroes.Hunt, free, ()),
    _sync(Meta("faction:found", "Found a faction", G.SOCIETY), heroes.found_faction, heroes.Faction, free, ("S4.3",)),
    _sync(
        Meta("faction:edit", "Edit a faction's kind, treasury, cohesion, secrecy and standing", G.SOCIETY),
        factions.edit_faction,
        factions.EditFaction,
        free,
        ("S4.3",),
    ),
    _sync(Meta("faction:goal", "Set, change or strike a faction's goal", G.SOCIETY), factions.set_goal, factions.FactionGoal, free, ("S4.3",)),
    _sync(Meta("faction:member", "Add, rank or cast out a faction member", G.SOCIETY), factions.set_member, factions.FactionMember, free, ("S4.3",)),
    _sync(Meta("faction:fund", "Fund a faction's treasury or drain it", G.SOCIETY), factions.fund, factions.FundFaction, free, ("S4.3",)),
    _sync(Meta("faction:outlaw", "Outlaw a faction or pardon it", G.SOCIETY), factions.outlaw, factions.OutlawFaction, free, ("S4.3",)),
    _sync(Meta("faction:charter", "Charter a faction, a guild monopoly or privateers", G.SOCIETY), factions.charter, factions.CharterFaction, free, ("S4.3",)),
    _sync(Meta("faction:contract", "Seal or end a free company's condotta", G.SOCIETY), factions.hire, factions.HireCompany, free, ("S4.3",)),
    _sync(Meta("faction:dissolve", "Dissolve a faction", G.SOCIETY), heroes.dissolve, heroes.FactionTarget, free, ()),
)

WARFARE_ACTIONS = (
    _sync(Meta("war:battle", "Force a battle", G.WARFARE), warfare.battle, warfare.WarTarget, free, ()),
    _sync(Meta("war:open", "Open a war now", G.WARFARE), warfare.open_war, warfare.OpenWar, free, ()),
    _sync(Meta("war:army", "Raise an army for a war", G.WARFARE), warfare.raise_army, warfare.WarArmy, free, ()),
    _sync(Meta("army:disband", "Disband an army", G.WARFARE), warfare.disband, warfare.ArmyTarget, free, ()),
    _sync(Meta("army:bless", "Strengthen an army", G.WARFARE), warfare.bless, warfare.ArmyBlessing, free, ()),
    _sync(Meta("war:duel", "Order a duel of mortals", G.WARFARE), warfare.duel, warfare.Duel, free, ()),
    _sync(Meta("war:victory", "Grant a side victory", G.WARFARE), warfare.victory, warfare.Victory, free, ()),
    _sync(Meta("war:end", "End a war by decree", G.WARFARE), warfare.end_war, warfare.EndWar, free, ()),
    _sync(Meta("community:rise_up", "Incite an uprising", G.WARFARE), warfare.uprising, warfare.CommunityTarget, free, ()),
    _sync(Meta("faction:spy", "Order a spy operation", G.WARFARE), warfare.spy, warfare.SpyOrder, free, ()),
    _sync(Meta("captive:free", "Free a captive", G.WARFARE), warfare.free, warfare.CaptiveTarget, free, ()),
    _sync(Meta("captive:ransom", "Pay a captive's ransom", G.WARFARE), warfare.ransom, warfare.CaptiveTarget, free, ()),
    _sync(Meta("tribute:impose", "Impose tribute", G.WARFARE), warfare.tribute, warfare.Tribute, free, ()),
    _sync(Meta("tribute:forgive", "Forgive a tribute", G.WARFARE), warfare.forgive, warfare.TributeTarget, free, ()),
    _sync(Meta("alliance:betray", "Order a betrayal", G.DIPLOMACY), warfare.betray, warfare.Betrayal, free, ()),
    _sync(Meta("alliance:marriage", "Seal an alliance by marriage", G.DIPLOMACY), warfare.marriage, warfare.Marriage, free, ()),
    _sync(Meta("feud:end", "End a blood feud", G.DIPLOMACY), warfare.end_feud, warfare.Feud, free, ()),
)

CREATURE_ACTIONS = (
    _sync(Meta("species:feed", "Order a species to feed", G.CREATURES), creatures.feed, creatures.Feeding, free, ()),
    _sync(Meta("species:mutate", "Force a mutation", G.CREATURES), creatures.mutate, creatures.SpeciesTarget, free, ()),
    _sync(Meta("people:split", "Split a changed people", G.CREATURES), creatures.split, creatures.PeopleTarget, free, ()),
    _sync(Meta("species:chimera", "Merge two species into a chimera", G.CREATURES), creatures.chimera, creatures.Chimera, free, ()),
    _sync(Meta("species:trail", "Lay a great beast's trail", G.CREATURES), creatures.trail, creatures.SpeciesTarget, free, ()),
    _sync(Meta("species:cull", "Cull a species", G.CREATURES), creatures.cull, creatures.Cull, free, ()),
    _sync(Meta("species:spare_prey", "Spare a species from its hunters", G.CREATURES), creatures.spare, creatures.SpeciesTarget, free, ()),
    _sync(Meta("species:introduce", "Carry a species to a new land", G.CREATURES), creatures.introduce, creatures.Introduction, free, ()),
    _sync(Meta("species:seed", "Let native life take root in a world", G.CREATURES), creatures.seed, creatures.LifeSeed, free, ("DEEP-189",)),
)

BEYOND_ACTIONS = (
    _sync(Meta("soul:descend", "Send a soul below", G.BEYOND), beyond.descend, beyond.MortalTarget, free, ()),
    _sync(Meta("soul:harvest", "Let a cult harvest a soul", G.BEYOND), beyond.harvest, beyond.SoulHarvest, free, ()),
    _sync(Meta("world:planet_stirs", "Make a living planet stir", G.BEYOND), beyond.planet_stirs, beyond.WorldTarget, free, ()),
    _sync(Meta("archive:raise", "Raise the Cosmic Archive", G.BEYOND), beyond.raise_archive, beyond.Empty, free, ()),
    _sync(Meta("archive:read", "Let a community read the Archive", G.BEYOND), beyond.read_archive, beyond.CommunityTarget, free, ()),
    _sync(Meta("plague:cosmic", "Loose the cosmic plague", G.BEYOND), beyond.plague, beyond.PlaceTarget, free, ()),
    _sync(Meta("soul:mirror", "Let a mirror birth happen", G.BEYOND), beyond.mirror, beyond.MortalTarget, free, ()),
    _sync(Meta("mortal:immortal", "Grant or take immortality", G.BEYOND), beyond.immortality, beyond.Immortality, free, ()),
    _sync(Meta("quest:abandon", "Abandon a legendary quest", G.BEYOND), beyond.abandon_quest, beyond.ThreadTarget, free, ()),
    _sync(Meta("sky:time_echo", "Order a time echo", G.BEYOND), beyond.time_echo, beyond.ThreadTarget, free, ()),
    _sync(Meta("horror:event", "Order a horror", G.BEYOND), beyond.horror_event, beyond.HorrorEvent, free, ()),
    _sync(Meta("horror:outer_being", "Summon an outer being", G.BEYOND), beyond.outer_being, beyond.WorldTarget, free, ()),
    _sync(Meta("horror:cult", "Seed an outer cult", G.BEYOND), beyond.outer_cult, beyond.EntityTarget, free, ()),
    _sync(Meta("horror:suppress_cult", "Scatter an outer cult", G.BEYOND), beyond.suppress_cult, beyond.CultTarget, free, ()),
    _sync(Meta("son:sanity", "Set a son's sanity", G.SONS), beyond.sanity, beyond.Sanity, free, ()),
    _sync(Meta("doom:apocalypse", "Bring the apocalypse", G.BEYOND), beyond.apocalypse, beyond.Apocalypse, free, ()),
    _sync(Meta("doom:clock", "Set the doom clock", G.BEYOND), beyond.doom_clock, beyond.DoomClock, free, ()),
)

PANTHEON_ACTIONS = (
    _sync(Meta("son:duel", "Make two sons duel", G.SONS), pantheon.duel, pantheon.SonDuel, free, ()),
    _sync(Meta("son:god_war", "Send a son to war with a foreign god", G.FOREIGN_GODS), pantheon.god_war, pantheon.GodWar, free, ()),
    _sync(Meta("foreign_god:raid_temple", "Let a foreign god raze a temple", G.FOREIGN_GODS), pantheon.raid_temple, pantheon.TempleRaid, free, ()),
    _job(Meta("foreign_god:wake", "Wake a foreign god", G.FOREIGN_GODS), creation.wake_foreign_god, pantheon.ForeignGodTarget, free, ("ACT-173",)),
    _sync(Meta("son:relation", "Set two sons' relation", G.SONS), pantheon.relation, pantheon.SonRelation, free, ()),
    _sync(Meta("son:outer_bargain", "Force or forbid a son's outer bargain", G.SONS), pantheon.outer_bargain, pantheon.OuterBargainOrder, free, ("PAN-022",)),
)

MEMORY_ACTIONS = (
    _sync(Meta("legend:forget", "Let a legend be forgotten", G.MEMORY), memory.forget_legend, memory.LegendTarget, free, ()),
    _sync(Meta("legend:revive", "Revive a legend", G.MEMORY), memory.revive, memory.LegendTarget, free, ()),
    _sync(Meta("legend:from_event", "Turn an event into legend", G.MEMORY), memory.legendify, memory.EventTarget, free, ()),
    _sync(Meta("legend:manifest", "Let a legend walk the world", G.MEMORY), memory.manifest, memory.LegendTarget, free, ()),
    _sync(Meta("prophecy:fulfil", "Fulfil a prophecy", G.MEMORY), memory.fulfil, memory.ProphecyTarget, free, ()),
    _sync(Meta("prophecy:forget", "Let a prophecy be forgotten", G.MEMORY), memory.forget_prophecy, memory.ProphecyTarget, free, ()),
)

COSMIC_ORDER_ACTIONS = (
    _sync(Meta("world:map", "Redraw a world's map", G.WORLDS), cosmic_orders.regenerate_map, cosmic_orders.WorldTarget, free, ()),
    _sync(Meta("map:snapshot", "Record the maps of this epoch now", G.WORLDS), cosmic_orders.snapshot_now, cosmic_orders.Empty, free, ("SVC-123",)),
    _sync(Meta("world:epoch_star", "Set the star of the epoch", G.WORLDS), cosmic_orders.epoch_star, cosmic_orders.EpochStar, free, ()),
    _sync(Meta("route:teach", "Teach a community a road", G.COSMOS), cosmic_orders.teach_route, cosmic_orders.RouteLesson, free, ()),
    _sync(Meta("foreign_god:raise_land", "Let a foreign god raise land", G.FOREIGN_GODS), cosmic_orders.raise_land, cosmic_orders.ForeignGodTarget, free, ()),
    _sync(Meta("deposit:owner", "Give a cosmic deposit an owner", G.COSMOS), cosmic_orders.deposit_owner, cosmic_orders.DepositOwner, free, ()),
    _sync(Meta("market:found", "Found a wandering market", G.COSMOS), cosmic_orders.wandering_market, cosmic_orders.RegionTarget, free, ()),
    _sync(Meta("pirates:spawn", "Loose void pirates", G.COSMOS), cosmic_orders.void_pirates, cosmic_orders.RegionTarget, free, ()),
    _sync(Meta("market:disband", "Disband a market or pirate band", G.COSMOS), cosmic_orders.disband, cosmic_orders.FactionTarget, free, ()),
    _sync(Meta("route:danger", "Set a road's danger", G.COSMOS), cosmic_orders.route_danger, cosmic_orders.RouteDanger, free, ()),
    _sync(
        Meta("economy:resources", "Run the resource mechanics now", G.COSMOS),
        cosmic_orders.run_resource_mechanics,
        cosmic_orders.Empty,
        free,
        ("ECO-001", "ECO-002", "ECO-003", "ECO-004", "ECO-005", "ECO-006"),
    ),
    _sync(Meta("economy:cosmic", "Run the cosmic economy now", G.COSMOS), cosmic_orders.run_cosmic_economy, cosmic_orders.Empty, free, ("ECO-001", "ECO-002")),
    _sync(
        Meta("addiction:cure", "Cure a community's addiction", G.COSMOS),
        cosmic_orders.cure_addiction,
        cosmic_orders.AddictionCure,
        free,
        ("ECO-003", "ECO-007"),
    ),
    _sync(
        Meta("addiction:set", "Set, hold or unmake a community's craving", G.COSMOS),
        cosmic_orders.set_addiction,
        cosmic_orders.AddictionSet,
        free,
        ("ECO-003", "ECO-007"),
    ),
    _sync(
        Meta("addiction:immunity", "Grant or take away immunity to a craving", G.COSMOS),
        cosmic_orders.set_immunity,
        cosmic_orders.ImmunitySet,
        free,
        ("ECO-003",),
    ),
)

DIVINE_ACTIONS = (
    _sync(Meta("essence:pour", "Pour essence into the land", G.CREATOR), divine.pour, divine.Pour, free, ()),
    _sync(Meta("creator:sign", "Send a sign of the Creator", G.CREATOR), divine.sign, divine.Sign, free, ()),
    _sync(Meta("mortal:protect", "Shield a mortal from death", G.DEATH), divine.protect, divine.Protection, free, ()),
    _sync(Meta("foreign_god:strike", "Let a foreign god strike a mortal", G.DEATH), divine.foreign_strike, divine.ForeignStrike, free, ()),
    _sync(Meta("reputation:drift", "Settle a son's view of the Creator now", G.CREATOR), divine.drift, divine.SonTarget, free, ()),
    _sync(Meta("goals:evaluate", "Weigh the goals now", G.GOALS), divine.evaluate, divine.Empty, free, ()),
    _sync(Meta("faith:first", "Give a community its first faith", G.GOD_POWER), divine.first_faith, divine.FirstFaith, free, ()),
)

DIVINITY_ACTIONS = (
    _sync(Meta("domain_hook:set", "Set how strongly a domain hook works in a world", G.WORLDS), divinity.set_hook, divinity.HookSetting, free, ("S9.1",)),
    _sync(Meta("domain_hook:clear", "Let a domain hook work as usual in a world", G.WORLDS), divinity.clear_hook, divinity.HookTarget, free, ("S9.1",)),
    _sync(Meta("god_goal:set", "Give a god an aim", G.SONS), divinity.set_goal, divinity.GoalDraft, free, ("S9.1",)),
    _sync(Meta("god_goal:edit", "Reshape or hold a god's aim", G.SONS), divinity.edit_goal, divinity.GoalEdit, free, ("S9.1",)),
    _sync(Meta("god_goal:drop", "Set a god's aim aside", G.SONS), divinity.drop_goal, divinity.GoalTarget, free, ("S9.1",)),
    _sync(Meta("divine_standing:set", "Set or hold how a people regards a god", G.SONS), divinity.set_standing, divinity.StandingEdit, free, ("S9.1",)),
    _sync(Meta("divine_standing:clear", "Make a people forget its regard of a god", G.SONS), divinity.clear_standing, divinity.StandingTarget, free, ("S9.1",)),
    _sync(Meta("divine_wound:inflict", "Wound a god", G.SONS), divinity.inflict_wound, divinity.WoundDraft, free, ("S9.1",)),
    _sync(Meta("divine_wound:edit", "Reshape, heal or hold a divine wound", G.SONS), divinity.edit_wound, divinity.WoundEdit, free, ("S9.1",)),
    _sync(Meta("divine_wound:remove", "Heal a divine wound at once", G.SONS), divinity.remove_wound, divinity.WoundTarget, free, ("S9.1",)),
    _sync(Meta("avatar:manifest", "Give a god a mortal form", G.SONS), divinity.manifest_avatar, divinity.AvatarDraft, free, ("S9.1",)),
    _sync(Meta("avatar:edit", "Reshape or hold a god's mortal form", G.SONS), divinity.edit_avatar, divinity.AvatarEdit, free, ("S9.1",)),
    _sync(Meta("avatar:withdraw", "Call a god back from its mortal form", G.SONS), divinity.withdraw_avatar, divinity.AvatarTarget, free, ("S9.1",)),
    _sync(Meta("taboo:set", "Make an act taboo to the Creator", G.CREATOR), divinity.set_taboo, divinity.TabooSetting, free, ("S9.2",)),
    _sync(Meta("taboo:remove", "Lift a taboo of the Creator", G.CREATOR), divinity.remove_taboo, divinity.TabooTarget, free, ("S9.2",)),
    _sync(Meta("attention:set", "Turn the Creator's eye to a world or away", G.CREATOR), divinity.set_attention, divinity.AttentionEdit, free, ("S9.2",)),
    _sync(
        Meta("attention:clear", "Let the Creator's eye on a world start afresh", G.CREATOR), divinity.clear_attention, divinity.AttentionTarget, free, ("S9.2",)
    ),
    _sync(
        Meta("divine_pact:seal", "Seal a divine pact between a son and a foreign god", G.FOREIGN_GODS), divinity.seal_pact, divinity.PactDraft, free, ("S9.3",)
    ),
    _sync(Meta("ruling:decree", "Lay down a ruling of the council", G.SONS), divinity.decree, divinity.RulingDraft, free, ("S9.4",)),
    _sync(Meta("ruling:edit", "Reshape or hold a ruling of the council", G.SONS), divinity.edit_ruling, divinity.RulingEdit, free, ("S9.4",)),
    _sync(Meta("ruling:revoke", "Strike out a ruling of the council", G.SONS), divinity.revoke_ruling, divinity.RulingTarget, free, ("S9.4",)),
    _sync(
        Meta("law_profile:edit", "Reshape a natural law's scope, strength, author and exceptions", G.COSMOS),
        divinity.edit_law,
        divinity.LawEdit,
        free,
        ("S9.5",),
    ),
    _sync(Meta("outer_profile:edit", "Reshape an outer being's hunger and reach", G.BEYOND), divinity.edit_outer, divinity.OuterEdit, free, ("S9.6",)),
    _sync(Meta("breach:open", "Open a breach point of an outer being", G.BEYOND), divinity.open_breach, divinity.BreachDraft, free, ("S9.6",)),
    _sync(Meta("breach:edit", "Reshape or hold a breach point", G.BEYOND), divinity.edit_breach, divinity.BreachEdit, free, ("S9.6",)),
    _sync(Meta("breach:close", "Seal a breach point", G.BEYOND), divinity.close_breach, divinity.BreachTarget, free, ("S9.6",)),
)

PHYSICS_ACTIONS = (
    _sync(
        Meta("star_physics:edit", "Reshape a star's mass, metal, age or upkeep", G.COSMOS),
        physics.edit_star_physics,
        physics.StarPhysicsEdit,
        free,
        ("S10.1/RP2",),
    ),
    _sync(Meta("star_system:create", "Gather stars into a system", G.COSMOS), physics.create_system, physics.SystemDraft, free, ("S10.9",)),
    _sync(Meta("star_system:edit", "Reshape or hold a star system", G.COSMOS), physics.edit_system, physics.SystemEdit, free, ("S10.9",)),
    _sync(Meta("star_system:delete", "Break a star system up", G.COSMOS), physics.delete_system, physics.SystemTarget, free, ("S10.9",)),
    _sync(Meta("star_system:move", "Set a star into a system as its primary or a companion", G.COSMOS), physics.move_star, physics.StarMove, free, ("S10.9",)),
    _sync(
        Meta("world_physics:edit", "Reshape a world's orbit, body, air, ice or seas", G.COSMOS),
        physics.edit_world_physics,
        physics.WorldPhysicsEdit,
        free,
        ("S10.9",),
    ),
    _sync(Meta("life_class:edit", "Set how complex a world's life is and where it lives", G.COSMOS), physics.edit_life, physics.LifeEdit, free, ("S10.9",)),
    _sync(
        Meta("cosmic_feature:create", "Set an asteroid field, wormhole, comet, rogue world or gravity well in the heavens", G.COSMOS),
        physics.create_feature,
        physics.FeatureDraft,
        free,
        ("S10.9",),
    ),
    _sync(Meta("cosmic_feature:edit", "Reshape or hold a cosmic feature", G.COSMOS), physics.edit_feature, physics.FeatureEdit, free, ("S10.9",)),
    _sync(Meta("cosmic_feature:delete", "Unmake a cosmic feature", G.COSMOS), physics.delete_feature, physics.FeatureTarget, free, ("S10.9",)),
    _sync(Meta("impact:call", "Call a body down upon a world", G.COSMOS), physics.call_impact, physics.ImpactCall, free, ("S10.9",)),
    _sync(Meta("impact:deflect", "Turn a falling body aside", G.COSMOS), physics.deflect_impact, physics.ImpactTarget, free, ("S10.9",)),
    _sync(Meta("impact:edit", "Reshape or hold an impact", G.COSMOS), physics.edit_impact, physics.ImpactEdit, free, ("S10.9",)),
    _sync(Meta("impact:delete", "Strike an impact from the record", G.COSMOS), physics.delete_impact, physics.ImpactTarget, free, ("S10.9",)),
    _sync(
        Meta("terraform:start", "Begin to reshape a world's air, warmth, water or face", G.COSMOS),
        physics.start_terraform,
        physics.TerraformDraft,
        free,
        ("S10.9",),
    ),
    _sync(Meta("terraform:edit", "Reshape or hold the work on a world", G.COSMOS), physics.edit_terraform, physics.TerraformEdit, free, ("S10.9",)),
    _sync(Meta("terraform:stop", "Stop the work on a world", G.COSMOS), physics.stop_terraform, physics.TerraformTarget, free, ("S10.9",)),
    _sync(Meta("survey:set", "Set how well a people or realm knows a world", G.COSMOS), physics.set_survey, physics.SurveySet, free, ("S10.2/RP2",)),
    _sync(Meta("survey:forget", "Make a people or realm forget a world", G.COSMOS), physics.forget_survey, physics.SurveyTarget, free, ("S10.2/RP2",)),
)

COSMOGRAPHY_ACTIONS = (
    _sync(
        Meta("dimension:create", "Bring a dimension into being", G.COSMOS),
        cosmography.create_dimension,
        cosmography.DimensionDraft,
        lambda rules: essence(rules.cosmic_costs.create_dimension),
        ("S10.13",),
    ),
    _sync(Meta("dimension:edit", "Reshape, hold or rule a dimension", G.COSMOS), cosmography.edit_dimension, cosmography.DimensionEdit, free, ("S10.13",)),
    _sync(Meta("dimension:delete", "Unmake a dimension", G.COSMOS), cosmography.delete_dimension, cosmography.DimensionTarget, free, ("S10.13",)),
    _sync(
        Meta("dimension:bind_law", "Make a natural law hold across a whole dimension", G.COSMOS),
        cosmography.bind_dimension_law,
        cosmography.DimensionLaw,
        free,
        ("S10.13",),
    ),
    _sync(
        Meta("dimension:release_law", "Let a law hold only on its own world again", G.COSMOS),
        cosmography.release_dimension_law,
        cosmography.LawTarget,
        free,
        ("S10.13",),
    ),
    _sync(
        Meta("heavens:worship", "Make a people worship its star, its galaxy or a dimension, or stop", G.COSMOS),
        cosmography.sky_worship,
        cosmography.SkyWorship,
        free,
        ("S10.16",),
    ),
    _sync(
        Meta("cluster:create", "Gather galaxies into a cluster", G.COSMOS),
        cosmography.create_cluster,
        cosmography.ClusterDraft,
        lambda rules: essence(rules.cosmic_costs.create_cluster),
        ("S10.11",),
    ),
    _sync(Meta("cluster:edit", "Reshape or hold a cluster", G.COSMOS), cosmography.edit_cluster, cosmography.ClusterEdit, free, ("S10.11",)),
    _sync(Meta("cluster:delete", "Scatter a cluster", G.COSMOS), cosmography.delete_cluster, cosmography.ClusterTarget, free, ("S10.11",)),
    _sync(
        Meta("galaxy:create", "Set a new galaxy among the others", G.COSMOS),
        cosmography.create_galaxy,
        cosmography.GalaxyDraft,
        lambda rules: essence(rules.cosmic_costs.create_galaxy),
        ("S10.10",),
    ),
    _sync(Meta("galaxy:edit", "Reshape, hold or take patronage of a galaxy", G.COSMOS), cosmography.edit_galaxy, cosmography.GalaxyEdit, free, ("S10.10",)),
    _sync(Meta("galaxy:delete", "Unmake a galaxy", G.COSMOS), cosmography.delete_galaxy, cosmography.GalaxyTarget, free, ("S10.10",)),
    _sync(
        Meta("galactic_structure:create", "Shape an arm, nebula, cluster or other structure in a galaxy", G.COSMOS),
        cosmography.create_structure,
        cosmography.StructureDraft,
        free,
        ("S10.10",),
    ),
    _sync(
        Meta("galactic_structure:edit", "Reshape or hold a galactic structure", G.COSMOS),
        cosmography.edit_structure,
        cosmography.StructureEdit,
        free,
        ("S10.10",),
    ),
    _sync(
        Meta("galactic_structure:delete", "Unmake a galactic structure", G.COSMOS), cosmography.delete_structure, cosmography.StructureTarget, free, ("S10.10",)
    ),
    _sync(
        Meta("galactic_event:trigger", "Bring about a galactic event", G.COSMOS),
        cosmography.trigger_galactic_event,
        cosmography.GalacticEventDraft,
        free,
        ("S10.10",),
    ),
    _sync(Meta("galactic_event:edit", "Reshape a galactic event", G.COSMOS), cosmography.edit_galactic_event, cosmography.GalacticEventEdit, free, ("S10.10",)),
    _sync(
        Meta("galactic_event:delete", "Strike a galactic event from the record", G.COSMOS),
        cosmography.delete_galactic_event,
        cosmography.GalacticEventTarget,
        free,
        ("S10.10",),
    ),
    _sync(
        Meta("dimensional_event:trigger", "Bring about a dimensional event", G.BEYOND),
        cosmography.trigger_dimensional_event,
        cosmography.DimensionalEventDraft,
        free,
        ("S10.13",),
    ),
    _sync(
        Meta("dimensional_event:edit", "Reshape a dimensional event", G.BEYOND),
        cosmography.edit_dimensional_event,
        cosmography.DimensionalEventEdit,
        free,
        ("S10.13",),
    ),
    _sync(
        Meta("dimensional_event:delete", "Strike a dimensional event from the record", G.BEYOND),
        cosmography.delete_dimensional_event,
        cosmography.DimensionalEventTarget,
        free,
        ("S10.13",),
    ),
    _sync(Meta("rift:open", "Tear a rift into another dimension", G.BEYOND), cosmography.open_rift, cosmography.RiftDraft, free, ("S10.14",)),
    _sync(Meta("rift:edit", "Reshape or hold a rift", G.BEYOND), cosmography.edit_rift, cosmography.RiftEdit, free, ("S10.14",)),
    _sync(Meta("rift:seal", "Seal a rift", G.BEYOND), cosmography.seal_rift, cosmography.RiftTarget, free, ("S10.14",)),
    _sync(Meta("rift:delete", "Remove a rift from the record", G.BEYOND), cosmography.delete_rift, cosmography.RiftTarget, free, ("S10.14",)),
    _sync(Meta("cosmic_being:call", "Call a cosmic being", G.BEYOND), cosmography.call_being, cosmography.BeingDraft, free, ("S10.15",)),
    _sync(Meta("cosmic_being:edit", "Reshape or hold a cosmic being", G.BEYOND), cosmography.edit_being, cosmography.BeingEdit, free, ("S10.15",)),
    _sync(Meta("cosmic_being:bind", "Bind a cosmic being to the Creator", G.BEYOND), cosmography.bind_being, cosmography.BeingTarget, free, ("S10.15",)),
    _sync(Meta("cosmic_being:banish", "Banish a cosmic being", G.BEYOND), cosmography.banish_being, cosmography.BeingTarget, free, ("S10.15",)),
    _sync(Meta("phenomenon:create", "Raise a phenomenon in a region", G.WORLDS), cosmography.create_phenomenon, cosmography.PhenomenonDraft, free, ("S10.6",)),
    _sync(Meta("phenomenon:edit", "Reshape or hold a phenomenon", G.WORLDS), cosmography.edit_phenomenon, cosmography.PhenomenonEdit, free, ("S10.6",)),
    _sync(
        Meta("phenomenon:footprint", "Spread a phenomenon to a region or draw it back", G.WORLDS),
        cosmography.set_footprint,
        cosmography.Footprint,
        free,
        ("S10.6",),
    ),
    _sync(Meta("phenomenon:contain", "Ward a phenomenon", G.WORLDS), cosmography.contain_phenomenon, cosmography.Containment, free, ("S10.6",)),
    _sync(
        Meta("star_life:edit", "Set or hold a star's age, steadiness, radiation, place in its galaxy and patron", G.COSMOS),
        cosmography.edit_star_life,
        cosmography.StarLifeEdit,
        free,
        ("S10.1",),
    ),
    _sync(
        Meta("world_life:edit", "Set or hold a world's magnetism, radiation, life, age, mood and place", G.WORLDS),
        cosmography.edit_world_life,
        cosmography.WorldLifeEdit,
        free,
        ("S10.2",),
    ),
    _sync(
        Meta("route_flow:edit", "Set or hold a route's capacity, traffic, toll, piracy, wear and window", G.COSMOS),
        cosmography.edit_route_flow,
        cosmography.RouteFlowEdit,
        free,
        ("S10.4",),
    ),
    _sync(
        Meta("journey:load", "Set and hold a journey's convoy, escorts, cargo and passengers", G.COSMOS),
        cosmography.load_journey,
        cosmography.JourneyLoad,
        free,
        ("S10.5",),
    ),
    _sync(
        Meta("journey:release", "Let a journey's load follow the road again", G.COSMOS),
        cosmography.release_journey,
        cosmography.JourneyRelease,
        free,
        ("S10.5",),
    ),
    _sync(Meta("celestial_reading:set", "Set how a people reads a celestial body", G.WORLDS), cosmography.set_reading, cosmography.Reading, free, ("S10.3",)),
    _sync(Meta("apocalypse:variant", "Choose the shape of the end", G.CREATOR), cosmography.set_variant, cosmography.Variant, free, ("S10.8",)),
    _sync(Meta("region_climate:turn", "Turn a region's climate", G.WORLDS), cosmography.turn_climate, cosmography.ClimateOrder, free, ("S10.7",)),
)

HORIZON_ACTIONS = (
    _sync(
        Meta("intuition:discard", "Let a sensed world stay a legend", G.COSMOS),
        horizon.discard_intuition,
        horizon.IntuitionTarget,
        free,
        ("EXP-017", "EXP-018"),
    ),
    _sync(Meta("sensed_world:request", "Bring a sensed world toward its birth", G.COSMOS), horizon.request_sensed, horizon.IntuitionTarget, free, ("EXP-017",)),
    _sync(
        Meta("sensed_world:hold", "Hold or release a sensed world waiting to be born", G.COSMOS),
        horizon.hold_sensed,
        horizon.HoldSensedStep,
        free,
        ("EXP-017",),
    ),
    _sync(
        Meta("sensed_world:retry", "Try again the birth of a sensed world that failed", G.COSMOS),
        horizon.retry_sensed,
        horizon.SensedStepTarget,
        free,
        ("EXP-017",),
    ),
    _sync(Meta("sensed_world:cancel", "Call off the birth of a sensed world", G.COSMOS), horizon.cancel_sensed, horizon.SensedStepTarget, free, ("EXP-017",)),
    _sync(Meta("intuition:discard_all", "Let all waiting intuitions go", G.COSMOS), horizon.discard_all, horizon.DiscardAll, free, ("EXP-017", "EXP-018")),
)

LANGUAGE_ACTIONS = (
    _sync(
        Meta("language:edit", "Edit a language's script, sounds and signature", G.LANGUAGES),
        languages.edit_language,
        languages.EditLanguage,
        free,
        ("LANG-002", "LANG-003", "LANG-007", "LANG-009", "LANG-019"),
    ),
    _sync(
        Meta("language:signature", "Redraw a language's signature", G.LANGUAGES),
        languages.regenerate_signature,
        languages.LanguageTarget,
        free,
        ("LANG-007", "LANG-008"),
    ),
    _sync(
        Meta("language:epoch_words", "Add the words of the epoch now", G.LANGUAGES),
        languages.run_epoch_words,
        languages.EpochWords,
        free,
        ("LANG-020", "LANG-021"),
    ),
    _sync(Meta("language:words", "Add words to a language", G.LANGUAGES), languages.add_lexicon_words, languages.AddWords, free, ("CORE-050",)),
)


def knowledge_deepen_cost(rules: Rules) -> str:
    return f"{essence(rules.knowledge.creator_deepen_cost)} to deepen; blunting is free"


WORLD_LAYER_ACTIONS = (
    _sync(Meta("knowledge:level", "Deepen or blunt a knowledge", G.SOCIETY), knowledge.change_level, knowledge.KnowledgeLevel, knowledge_deepen_cost, ()),
    _sync(Meta("knowledge:run", "Let the masters work on their knowledge now", G.SOCIETY), knowledge.run_now, knowledge.Empty, free, ()),
    _sync(Meta("mechanics:weigh", "Give every unweighed resource and law its working", G.COSMOS), mechanics.weigh_all, mechanics.Empty, free, ()),
    _sync(Meta("market:write_off", "Write off a debt", G.SOCIETY), market.write_off, market.DebtTarget, free, ()),
    _sync(Meta("market:run", "Open the markets now", G.SOCIETY), market.run_now, market.Empty, free, ()),
    _sync(Meta("faith:syncretize", "Join a community's faith with an old god", G.FOREIGN_GODS), native_faith.weave, native_faith.Syncretism, free, ()),
    _sync(Meta("faith:unsyncretize", "Let a people stop revering an old god", G.FOREIGN_GODS), native_faith.unweave, native_faith.Syncretism, free, ()),
    _sync(Meta("faith:native_run", "Let the old gods stir among the natives now", G.FOREIGN_GODS), native_faith.run_now, native_faith.Empty, free, ()),
    _sync(
        Meta("language:creole", "Fuse a community's two tongues into a creole", G.LANGUAGES),
        language_contact.creole,
        language_contact.CommunityTarget,
        free,
        (),
    ),
    _sync(Meta("language:contact_run", "Let tongues meet now", G.LANGUAGES), language_contact.run_now, language_contact.Empty, free, ()),
    _sync(
        Meta("records:living_stats", "Let mysteries, works and prophecies take their course now", G.ENTITIES),
        living_stats.run_now,
        living_stats.Empty,
        free,
        (),
    ),
)

ENGINE_CONTROL_ACTIONS = (
    _sync(
        Meta("engine:run_phase", "Run an engine step now", G.SETTINGS),
        engine_control.run_phase,
        engine_control.RunPhase,
        free,
        ("ENG-001", "ENG-009", "ENG-012", "ENG-034", "ENG-035", "ENG-037", "ENG-038", "ENG-042", "ENG-047", "ENG-055", "ENG-079", "DEEP-029", "DEEP-032"),
    ),
    _sync(
        Meta("relation:set", "Set the relation between two communities", G.DIPLOMACY),
        relations.set_community_relation,
        relations.SetRelation,
        free,
        ("DEEP-024",),
    ),
    _sync(Meta("feud:start", "Declare a blood feud", G.DIPLOMACY), relations.declare_feud, relations.DeclareFeud, free, ("DEEP-027",)),
)


def rejudge_cost(rules: Rules) -> str:
    return essence(rules.costs.rejudge_fate)


FATE_ACTIONS = (
    _job(Meta("fate:retry", "Retry Fate for the last epoch", G.FATE), fate_controls.retry_fate, fate_controls.NoInput, rejudge_cost, ("EPOCH-031",)),
    _job(Meta("fate:rejudge_debt", "Re-judge Fate's debt now", G.FATE), fate_controls.rejudge_debt, fate_controls.NoInput, rejudge_cost, ("LLM-060",)),
    _job(Meta("fate:rejudge_limbo", "Re-judge the creations in limbo", G.FATE), fate_controls.rejudge_limbo, fate_controls.NoInput, rejudge_cost, ("LLM-063",)),
    _sync(
        Meta("fate:override_verdict", "Overrule Fate's verdict on a creation", G.FATE),
        fate_controls.override_verdict,
        fate_controls.OverrideVerdict,
        lambda rules: essence(rules.costs.override_verdict),
        ("LLM-061",),
    ),
    _sync(Meta("creation:reward", "Take back or restore a creation's reward", G.FATE), rewards.set_reward, rewards.RewardShare, free, ()),
    _job(
        Meta("chronicle:audit", "Audit an age's chronicle against the facts again", G.FATE),
        fate_controls.audit_chronicle,
        fate_controls.EpochTarget,
        lambda rules: essence(rules.chronicle_audit.manual_cost),
        (),
    ),
    _job(
        Meta("voices:retry", "Run the voices of the peoples again", G.FATE),
        fate_controls.retry_voices,
        fate_controls.NoInput,
        lambda rules: essence(rules.costs.retry_voices),
        ("LLM-098", "LLM-099", "EPOCH-032"),
    ),
    _sync(
        Meta("voices:edit_view", "Amend a historian's account", G.FATE),
        fate_controls.edit_view,
        fate_controls.EditHistorianView,
        lambda rules: essence(rules.costs.edit_historian_view),
        ("LLM-100",),
    ),
    _sync(
        Meta("voices:delete_view", "Strike a historian's account", G.FATE),
        fate_controls.delete_view,
        fate_controls.HistorianViewTarget,
        lambda rules: essence(rules.costs.edit_historian_view),
        ("LLM-100",),
    ),
    _job(
        Meta("births:retry", "Retry the births of sensed worlds", G.FATE),
        fate_controls.retry_births,
        fate_controls.NoInput,
        lambda rules: essence(rules.costs.retry_births),
        ("EPOCH-037",),
    ),
)


def end_cost_text(rules: Rules) -> str:
    cycles = rules.life_cycles
    return f"{cycles.end_cost} + power x {cycles.end_cost_per_power} essence"


LIFE_CYCLE_ACTIONS = (
    _sync(Meta("community:collapse", "Make a community collapse", G.SOCIETY), life_cycles.collapse_community, life_cycles.CommunityEnd, end_cost_text, ()),
    _sync(Meta("structure:raze", "Raze a structure", G.SOCIETY), life_cycles.raze, life_cycles.StructureEnd, end_cost_text, ()),
    _sync(
        Meta("mortal:fate", "Seal a mortal's fate", G.DEATH), life_cycles.fate, life_cycles.MortalFate, lambda rules: essence(rules.casualties.fate_cost), ()
    ),
    _sync(
        Meta("memorial:order", "Order a war, disaster or death remembered", G.MEMORY),
        life_cycles.order_memorial,
        life_cycles.Commemoration,
        lambda rules: essence(rules.remembrance.commemorate_cost),
        (),
    ),
    _sync(
        Meta("world:revive", "Revive a world", G.WORLDS),
        life_cycles.revive,
        life_cycles.WorldTarget,
        lambda rules: essence(rules.world_balance.revive_cost),
        (),
    ),
    _sync(
        Meta("world:guardian", "Appoint a world's guardian", G.WORLDS),
        life_cycles.guardian,
        life_cycles.WorldGuardian,
        lambda rules: essence(rules.world_balance.guardian_cost),
        (),
    ),
    _sync(Meta("species:abundance", "Set a species' abundance", G.CREATURES), life_cycles.abundance, life_cycles.SpeciesAbundance, free, ()),
    _sync(Meta("region:seed_place", "Bring forth a place in a region", G.WORLDS), life_cycles.seed, life_cycles.RegionTarget, free, ()),
    _sync(Meta("pilgrimage:declare", "Declare a pilgrimage site", G.COSMOS), life_cycles.declare_site, life_cycles.SiteTarget, free, ()),
    _sync(Meta("record:end", "Order a record's end", G.ENTITIES), life_cycles.end_record, life_cycles.RecordEndOrder, end_cost_text, ()),
    _sync(Meta("cult:merge", "Merge a cult into another", G.SOCIETY), life_cycles.merge_cult, life_cycles.Union, free, ()),
    _sync(Meta("cult:schism", "Split a sect from a cult", G.SOCIETY), life_cycles.schism, life_cycles.Schism, free, ("ENG-035",)),
    _sync(Meta("people:unite", "Unite two peoples", G.SOCIETY), life_cycles.unite, life_cycles.Union, free, ()),
    _sync(Meta("place:swallow", "Let the earth swallow a place", G.WORLDS), life_cycles.swallow_place, life_cycles.PlaceTarget, end_cost_text, ()),
)

BODY_ACTIONS = (
    _sync(Meta("body:heal", "Heal a bearer's wounds", G.ENTITIES), body.heal_body, body.HealBody, free, ("F4.4",)),
    _sync(Meta("body:maim", "Wound a chosen body part", G.ENTITIES), body.maim, body.Maim, free, ("F4.2", "F4.3")),
    _sync(Meta("body:injury", "Change an injury", G.ENTITIES), body.edit_injury, body.EditInjury, free, ("F4.2",)),
    _sync(Meta("body:prosthesis", "Fit a prosthesis", G.ENTITIES), body.apply_prosthesis, body.FitProsthesis, free, ("F4.5",)),
    _sync(Meta("body:prosthesis_remove", "Take away a prosthesis", G.ENTITIES), body.remove_prosthesis, body.ProsthesisTarget, free, ("F4.5",)),
    _sync(Meta("body:condition", "Give a lasting condition", G.ENTITIES), body.add_condition, body.AddCondition, free, ("F4.5",)),
    _sync(Meta("body:condition_end", "End a lasting condition", G.ENTITIES), body.end_condition_action, body.ConditionTarget, free, ("F4.5",)),
    _sync(Meta("body:plan", "Change a body plan", G.ENTITIES), body.set_plan, body.SetBodyPlan, free, ("F4.1",)),
    _sync(Meta("body:frame", "Set a body's height and build", G.ENTITIES), body.set_frame, body.SetFrame, free, ("F4.3",)),
    _sync(Meta("body:set", "Set or hold a capacity, armour or body value", G.ENTITIES), body.set_body_value, body.SetBodyValue, free, ("F4.3", "F4.5")),
    _sync(Meta("body:unlock", "Let a held body value follow the body again", G.ENTITIES), body.unlock_body_value, body.UnlockBodyValue, free, ("F4.5",)),
    _sync(Meta("body:customs", "Set how a people reads scars", G.SOCIETY), body.set_customs, body.SetCustoms, free, ("F4.5",)),
    _sync(Meta("body:customs_unlock", "Let a people's reading of scars change again", G.SOCIETY), body.unlock_customs, body.UnlockCustoms, free, ("F4.5",)),
    _sync(Meta("body:cohort", "Set the maimed of a community", G.SOCIETY), body.set_cohort, body.SetCohort, free, ("F4.5",)),
)

MIND_ACTIONS = (
    _sync(Meta("mind:values", "Set and hold values or a culture", G.ENTITIES), mind.set_values, mind.SetValues, free, ("F5",)),
    _sync(
        Meta("mind:lock", "Hold a part of a mind as it is", G.ENTITIES),
        mind.lock_mind,
        mind.LockMind,
        free,
        ("F5", "F8", "F13/RP5", "F14/RP4", "F16/RP4", "F18/RP3"),
    ),
    _sync(
        Meta("mind:unlock", "Let a held part of a mind change again", G.ENTITIES),
        mind.unlock_mind,
        mind.LockMind,
        free,
        ("F5", "F8", "F13/RP5", "F14/RP4", "F16/RP4", "F18/RP3"),
    ),
    _sync(Meta("mind:trait", "Give a trait", G.ENTITIES), mind.give_trait, mind.TraitCommand, free, ("F5.1",)),
    _sync(Meta("mind:trait_remove", "Take a trait away", G.ENTITIES), mind.take_trait, mind.TraitCommand, free, ("F5.1",)),
    _sync(Meta("mind:skill", "Set a skill level", G.ENTITIES), mind.give_skill, mind.SetSkill, free, ("F6",)),
    _sync(Meta("mind:skill_remove", "Make a mortal forget a skill", G.ENTITIES), mind.forget_skill, mind.SkillTarget, free, ("F6",)),
    _sync(Meta("mind:role", "Set and hold a mortal's calling", G.ENTITIES), mind.set_role, mind.SetRole, free, ("F6",)),
    _sync(Meta("mind:memory", "Plant a memory", G.ENTITIES), mind.add_memory, mind.AddMemory, free, ("F7",)),
    _sync(Meta("mind:memory_edit", "Change a memory's strength or how fast it fades", G.ENTITIES), mind.edit_memory, mind.EditMemory, free, ("F7",)),
    _sync(Meta("mind:memory_remove", "Erase a memory", G.ENTITIES), mind.forget_memory, mind.MemoryTarget, free, ("F7",)),
    _sync(Meta("mind:need", "Set and hold a mortal's need", G.ENTITIES), mind.set_need, mind.SetNeed, free, ("F8",)),
    _sync(Meta("mind:pressure", "Set and hold a pressure on a community", G.SOCIETY), mind.set_pressure, mind.SetPressure, free, ("F8",)),
    _sync(Meta("mind:attributes", "Set and hold what a body and mind can do", G.ENTITIES), mind.set_attributes, mind.SetAttributes, free, ("F13",)),
    _sync(Meta("mind:facets", "Set and hold how a mortal or god reacts", G.ENTITIES), mind.set_facets, mind.SetFacets, free, ("F13",)),
    _sync(Meta("mind:idea", "Plant an idea for a mortal to turn over", G.ENTITIES), mind.implant_idea, mind.ImplantIdea, free, ("F13/RP5",)),
    _sync(Meta("mind:idea_edit", "Speed, settle or reshape an idea", G.ENTITIES), mind.edit_idea, mind.EditIdea, free, ("F13/RP5",)),
    _sync(Meta("mind:idea_remove", "Take an idea away", G.ENTITIES), mind.remove_idea, mind.IdeaTarget, free, ("F13/RP5",)),
    _sync(Meta("thought:send", "Send a mortal a thought and its feeling", G.ENTITIES), feelings.send_thought, feelings.SendThought, free, ("F14",)),
    _sync(Meta("thought:edit", "Sharpen, soften or redirect a thought", G.ENTITIES), feelings.edit_thought, feelings.EditThought, free, ("F14",)),
    _sync(Meta("thought:remove", "Take a thought away", G.ENTITIES), feelings.remove_thought, feelings.ThoughtTarget, free, ("F14",)),
    _sync(Meta("thought:mood", "Set and hold a mortal's mood", G.ENTITIES), feelings.set_mood, feelings.SetMood, free, ("F14",)),
    _sync(Meta("grief:start", "Make a mortal mourn someone", G.ENTITIES), feelings.begin_grief, feelings.StartGrief, free, ("F14",)),
    _sync(Meta("grief:edit", "Move a grief to another stage or reshape it", G.ENTITIES), feelings.edit_grief, feelings.EditGrief, free, ("F14",)),
    _sync(Meta("grief:remove", "Lift a grief", G.ENTITIES), feelings.remove_grief, feelings.GriefTarget, free, ("F14",)),
    _sync(Meta("dream:send", "Send a mortal a dream", G.ENTITIES), feelings.send_dream, feelings.SendDream, free, ("F14/RP4",)),
    _sync(Meta("dream:edit", "Reshape a dream or how it was read", G.ENTITIES), feelings.edit_dream, feelings.EditDream, free, ("F14/RP4",)),
    _sync(Meta("dream:remove", "Make a mortal forget a dream", G.ENTITIES), feelings.remove_dream, feelings.DreamTarget, free, ("F14/RP4",)),
    _sync(
        Meta("preference:set", "Set and hold a like or dislike of a mortal or people", G.ENTITIES),
        culture_mind.set_preference,
        culture_mind.SetPreference,
        free,
        ("F15",),
    ),
    _sync(Meta("preference:remove", "Take a like or dislike away", G.ENTITIES), culture_mind.remove_preference, culture_mind.PreferenceTarget, free, ("F15",)),
    _sync(Meta("ethics:set", "Set and hold how a people or cult judges an act", G.SOCIETY), culture_mind.set_stance, culture_mind.SetStance, free, ("F16",)),
    _sync(Meta("ethics:honour", "Set and hold a people's honour model", G.SOCIETY), culture_mind.set_honour, culture_mind.SetHonour, free, ("F16/RP4",)),
    _sync(Meta("aspiration:dream", "Set and hold a mortal's life's dream", G.ENTITIES), aspirations.set_dream, aspirations.SetDream, free, ("F17",)),
    _sync(Meta("aspiration:dream_remove", "Take a life's dream away", G.ENTITIES), aspirations.remove_dream, aspirations.MortalTarget, free, ("F17",)),
    _sync(Meta("aspiration:want", "Give a mortal a want", G.ENTITIES), aspirations.add_want, aspirations.AddWant, free, ("F17",)),
    _sync(Meta("aspiration:want_edit", "Fulfil, aim or hold a want", G.ENTITIES), aspirations.edit_want, aspirations.EditWant, free, ("F17",)),
    _sync(Meta("aspiration:want_remove", "Take a want away", G.ENTITIES), aspirations.remove_want, aspirations.WantTarget, free, ("F17",)),
    _sync(Meta("aspiration:fear", "Set a mortal's fear", G.ENTITIES), aspirations.set_fear, aspirations.SetFear, free, ("F17",)),
    _sync(Meta("aspiration:fear_remove", "Lift a fear", G.ENTITIES), aspirations.remove_fear, aspirations.FearTarget, free, ("F17",)),
    _sync(Meta("aspiration:focus", "Set and hold a mortal's lifestyle focus", G.ENTITIES), aspirations.set_focus, aspirations.SetFocus, free, ("F17",)),
    _sync(Meta("aspiration:perk", "Grant a perk", G.ENTITIES), aspirations.grant_perk, aspirations.PerkTarget, free, ("F17",)),
    _sync(Meta("aspiration:perk_remove", "Take a perk away", G.ENTITIES), aspirations.remove_perk, aspirations.PerkTarget, free, ("F17",)),
    _sync(Meta("aspiration:inspire", "Seize a mortal with inspiration", G.ENTITIES), aspirations.inspire, aspirations.Inspire, free, ("F17",)),
    _sync(Meta("aspiration:inspiration_edit", "Reshape an inspiration", G.ENTITIES), aspirations.edit_inspiration, aspirations.EditInspiration, free, ("F17",)),
    _sync(
        Meta("aspiration:inspiration_remove", "Quench an inspiration", G.ENTITIES),
        aspirations.remove_inspiration,
        aspirations.InspirationTarget,
        free,
        ("F17",),
    ),
    _sync(Meta("tie:set", "Set and hold how one mortal feels toward another", G.ENTITIES), bonds.set_relation, bonds.SetTie, free, ("F18",)),
    _sync(Meta("tie:remove", "Make a mortal forget a bond", G.ENTITIES), bonds.remove_relation, bonds.TieTarget, free, ("F18",)),
    _sync(Meta("circle:found", "Gather a circle in a place", G.SOCIETY), bonds.found_circle, bonds.FoundCircle, free, ("F18",)),
    _sync(Meta("circle:edit", "Reshape and hold a circle", G.SOCIETY), bonds.edit_circle, bonds.EditCircle, free, ("F18",)),
    _sync(Meta("circle:member", "Bring a mortal into a circle or send them out", G.SOCIETY), bonds.circle_member, bonds.CircleMember, free, ("F18",)),
    _sync(Meta("circle:disband", "Break up a circle", G.SOCIETY), bonds.disband_circle, bonds.CircleTarget, free, ("F18",)),
    _sync(Meta("passion:set", "Kindle and hold a passion", G.ENTITIES), bonds.set_passion, bonds.SetPassion, free, ("F18/RP3",)),
    _sync(Meta("passion:invoke", "Call on a passion for an inspiration roll", G.ENTITIES), bonds.invoke_passion, bonds.PassionTarget, free, ("F18/RP3",)),
    _sync(Meta("passion:remove", "Quench a passion", G.ENTITIES), bonds.remove_passion, bonds.PassionTarget, free, ("F18/RP3",)),
    _sync(Meta("rank:set", "Set and hold a place in a pecking order", G.SOCIETY), bonds.set_rank, bonds.SetRank, free, ("F18/RP3",)),
    _sync(Meta("rank:remove", "Take a place in a pecking order away", G.SOCIETY), bonds.remove_rank, bonds.RankTarget, free, ("F18/RP3",)),
    _sync(Meta("persuasion:attempt", "Have one mortal try to persuade another", G.ENTITIES), bonds.attempt_persuasion, bonds.Persuade, free, ("F18/RP3",)),
    _sync(Meta("persuasion:remove", "Forget an argument", G.ENTITIES), bonds.remove_persuasion, bonds.PersuasionTarget, free, ("F18/RP3",)),
    _sync(Meta("contest:hold", "Stage a contest of wit", G.ENTITIES), bonds.stage_contest, bonds.HoldContest, free, ("F18/RP6",)),
    _sync(Meta("contest:edit", "Retell how a contest ended", G.ENTITIES), bonds.edit_contest, bonds.EditContest, free, ("F18/RP6",)),
    _sync(Meta("contest:remove", "Strike a contest from memory", G.ENTITIES), bonds.remove_contest, bonds.ContestTarget, free, ("F18/RP6",)),
    _sync(Meta("renown:set", "Set and hold what a community thinks of someone", G.ENTITIES), renown.set_reputation, renown.SetReputation, free, ("F19",)),
    _sync(
        Meta("renown:remove", "Make a community forget a reputation", G.ENTITIES),
        renown.remove_reputation,
        renown.ReputationTarget,
        free,
        ("F19",),
    ),
    _sync(Meta("standing:set", "Set and hold a ruler's standing", G.ENTITIES), renown.set_currency, renown.SetStanding, free, ("F19",)),
    _sync(Meta("standing:remove", "Wipe a ruler's standing clean", G.ENTITIES), renown.remove_currency, renown.StandingTarget, free, ("F19",)),
    _sync(Meta("deed:record", "Set down a deed and who saw it", G.ENTITIES), renown.add_deed, renown.RecordDeed, free, ("F19/RP6",)),
    _sync(Meta("deed:edit", "Retell and hold a deed", G.ENTITIES), renown.edit_deed, renown.EditDeed, free, ("F19/RP6",)),
    _sync(Meta("deed:remove", "Strike a deed from memory", G.ENTITIES), renown.remove_deed, renown.DeedTarget, free, ("F19/RP6",)),
    _sync(Meta("deed_claim:set", "Give a true, shared or false claim to a deed", G.ENTITIES), renown.set_claim, renown.SetDeedClaim, free, ("F19/RP6",)),
    _sync(Meta("deed_claim:expose", "Expose a false claim", G.ENTITIES), renown.expose_claim, renown.DeedClaimTarget, free, ("F19/RP6",)),
    _sync(Meta("deed_claim:remove", "Withdraw a claim to a deed", G.ENTITIES), renown.remove_claim, renown.DeedClaimTarget, free, ("F19/RP6",)),
    _sync(Meta("lore_trade:make", "Pass a piece of lore from one holder to another", G.SOCIETY), renown.trade_lore, renown.TradeLore, free, ("F19/RP3",)),
    _sync(Meta("lore_trade:remove", "Strike a trade of lore from the record", G.SOCIETY), renown.remove_trade, renown.TradeTarget, free, ("F19/RP3",)),
    _sync(
        Meta("aspiration:conviction", "Set and hold a mortal's conviction", G.ENTITIES),
        aspirations.set_conviction,
        aspirations.SetConviction,
        free,
        ("F17/RP3",),
    ),
    _sync(Meta("variant:create", "Forge a new kind of trait, skill or state", G.ENTITIES), variants.create_variant, variants.CreateVariant, free, ("F9",)),
    _sync(Meta("variant:edit", "Reshape and hold a world-made kind", G.ENTITIES), variants.edit_variant, variants.EditVariant, free, ("F9",)),
    _sync(
        Meta("variant:release", "Let a held part of a world-made kind change again", G.ENTITIES), variants.release_variant, variants.VariantField, free, ("F9",)
    ),
    _sync(Meta("variant:delete", "Unmake a world-made kind", G.ENTITIES), variants.delete_variant, variants.VariantTarget, free, ("F9",)),
    _sync(Meta("variant:assign", "Give a skill or condition a made kind", G.ENTITIES), variants.assign_variant, variants.AssignVariant, free, ("F9",)),
    _sync(Meta("mind:skill_edit", "Change a skill's subject, practice and peak", G.ENTITIES), mind.edit_skill, mind.EditSkill, free, ("F6",)),
    _sync(Meta("body:condition_edit", "Change how heavy a condition lies", G.ENTITIES), body.edit_condition, body.EditCondition, free, ("F4.5",)),
    _sync(Meta("body:prosthesis_edit", "Change a prosthesis's make and quality", G.ENTITIES), body.edit_prosthesis, body.EditProsthesis, free, ("F4.5",)),
    _sync(Meta("body:injury_hold", "Hold a wound as it is or let it heal again", G.ENTITIES), body.hold_injuries, body.HoldInjuries, free, ("F4.4",)),
    _sync(Meta("body:treat", "Give a wound a treatment step", G.ENTITIES), body.treat_injury, body.TreatInjury, free, ("F23",)),
    _sync(Meta("body:consciousness", "Set or hold how awake a bearer is", G.ENTITIES), body.set_consciousness, body.SetConsciousness, free, ("F23",)),
    _sync(Meta("body:digit", "Take or give back a finger or toe", G.ENTITIES), body.set_digit, body.SetDigit, free, ("F23",)),
    _sync(Meta("body:handedness", "Set which hand a bearer leads with", G.ENTITIES), body.set_handedness, body.SetHandedness, free, ("F23",)),
    _sync(Meta("affliction:give", "Lay a venom, curse, blessing or trauma", G.ENTITIES), afflictions.give, afflictions.GiveAffliction, free, ("F30",)),
    _sync(Meta("affliction:edit", "Move an affliction's stage, source or onset", G.ENTITIES), afflictions.edit, afflictions.EditAffliction, free, ("F30",)),
    _sync(Meta("affliction:hold", "Hold an affliction at its stage or let it run", G.ENTITIES), afflictions.hold, afflictions.HoldAffliction, free, ("F30",)),
    _sync(Meta("affliction:cure", "Cure an affliction", G.ENTITIES), afflictions.cure_action, afflictions.CureAffliction, free, ("F30",)),
    _sync(Meta("affliction:delete", "Unmake an affliction as if it never was", G.ENTITIES), afflictions.delete, afflictions.AfflictionTarget, free, ("F30",)),
    _sync(Meta("record_row:create", "Make a new row of any record of a thing", G.ENTITIES), record_rows.create_row, record_rows.CreateRow, free, ()),
    _sync(Meta("record_row:edit", "Change or hold any value of a record row", G.ENTITIES), record_rows.edit_row, record_rows.EditRow, free, ()),
    _sync(Meta("record_row:delete", "Unmake a row of any record of a thing", G.ENTITIES), record_rows.delete_row, record_rows.RowTarget, free, ()),
    _sync(Meta("mortal:set", "Set and hold a mortal's life, standing or loyalty", G.ENTITIES), mortals.set_mortal, mortals.SetMortal, free, ("S3.1",)),
    _sync(
        Meta("mortal:release", "Let a held mortal value follow their life again", G.ENTITIES), mortals.release_mortal, mortals.ReleaseMortal, free, ("S3.1",)
    ),
    _sync(Meta("mortal:ability", "Set and hold a mortal's ability", G.ENTITIES), mortals.set_ability, mortals.SetAbility, free, ("S3.1",)),
    _sync(
        Meta("mortal:ability_release", "Let a held ability change with age again", G.ENTITIES), mortals.release_ability, mortals.ReleaseAbility, free, ("S3.1",)
    ),
    _sync(Meta("mortal:sex", "Set a mortal's sex", G.ENTITIES), mortals.set_sex, mortals.SetSex, free, ("S3.1",)),
    _sync(Meta("kin:betroth", "Promise two mortals to each other", G.ENTITIES), mortals.set_betrothal, mortals.PairCommand, free, ("S3.1",)),
    _sync(Meta("kin:marry", "Wed two mortals, by choice or by force", G.ENTITIES), mortals.force_marriage, mortals.ForceMarriage, free, ("S3.1",)),
    _sync(Meta("kin:end_marriage", "End a marriage", G.ENTITIES), mortals.end_marriage_action, mortals.EndMarriage, free, ("S3.1",)),
    _sync(Meta("kin:edit_marriage", "Change a marriage's kind, treaty or start", G.ENTITIES), mortals.edit_marriage, mortals.EditMarriage, free, ("S3.1",)),
    _sync(Meta("kin:delete_marriage", "Strike a marriage from the record", G.ENTITIES), mortals.delete_marriage, mortals.MarriageTarget, free, ("S3.1",)),
    _sync(Meta("kin:bond", "Bind two mortals as kin", G.ENTITIES), mortals.add_kin_bond, mortals.KinBond, free, ("S3.1",)),
    _sync(Meta("kin:unbond", "Undo a kin bond", G.ENTITIES), mortals.remove_kin_bond, mortals.KinBondTarget, free, ("S3.1",)),
    _sync(Meta("mortal:equip", "Set and hold what a mortal carries in a slot", G.ENTITIES), mortals.equip, mortals.Equip, free, ("S3.1",)),
    _sync(Meta("mortal:equip_release", "Let a mortal choose their own gear again", G.ENTITIES), mortals.release_slot, mortals.ReleaseSlot, free, ("S3.1",)),
    _sync(Meta("mortal:sentence", "Sentence a mortal under the law", G.ENTITIES), mortals.sentence_mortal, mortals.Sentence, free, ("S3.1",)),
    _sync(Meta("mortal:pardon", "Pardon a sentenced mortal", G.ENTITIES), mortals.pardon, mortals.Pardon, free, ("S3.1",)),
)

ECONOMY_ACTIONS = (
    _sync(Meta("material:edit", "Edit a material's properties in a world", G.WORLDS), economy.edit_material, economy.EditMaterial, free, ("F3.1", "F3/RP3")),
    _sync(Meta("stock:grant", "Add goods to a community's stores or take them away", G.SOCIETY), economy.grant_stock, economy.GrantStock, free, ("F3.2",)),
    _sync(
        Meta("resource:set", "Set a resource's reserve, richness, difficulty and quality", G.SOCIETY),
        economy.set_resource,
        economy.SetResource,
        free,
        ("S6.3",),
    ),
    _sync(Meta("resource:owner", "Give a resource to a new owner", G.SOCIETY), economy.set_owner, economy.SetOwner, free, ("S6.3",)),
    _sync(Meta("resource:reveal", "Reveal or hide a deposit", G.SOCIETY), economy.reveal, economy.Reveal, free, ("S6.3",)),
    _sync(Meta("workshop:set", "Raise, enlarge or pull down a workshop", G.SOCIETY), economy.set_workshop, economy.SetWorkshop, free, ("S6.3",)),
    _sync(Meta("trade_route:open", "Open a trade route between two markets", G.SOCIETY), economy.open_route, economy.OpenRoute, free, ("S6.4",)),
    _sync(Meta("trade_route:close", "Close a trade route", G.SOCIETY), economy.close_route, economy.RouteTarget, free, ("S6.4",)),
    _sync(Meta("trade_route:toll", "Set or release the toll on a stretch of a route", G.SOCIETY), economy.set_toll, economy.SetToll, free, ("S6.4",)),
    _sync(Meta("currency:edit", "Set a coin's purity, trust and supply", G.SOCIETY), economy.edit_currency, economy.EditCurrency, free, ("S6.4",)),
    _sync(Meta("currency:debase", "Debase a coin", G.SOCIETY), economy.debase, economy.CurrencyTarget, free, ("S6.4",)),
    _sync(Meta("currency:use", "Choose the coin a community counts in", G.SOCIETY), economy.use_currency, economy.UseCurrency, free, ("S6.4",)),
    _sync(Meta("loan:forgive", "Forgive a bank loan", G.SOCIETY), economy.forgive_loan, economy.LoanTarget, free, ("S6.4",)),
    _sync(Meta("hoard:inject", "Pour a hoard of treasure into a market", G.SOCIETY), economy.inject_hoard, economy.InjectHoard, free, ("S6.4",)),
    _sync(Meta("method:set", "Set and hold how a place does a kind of work", G.SOCIETY), industry.set_method, industry.SetMethod, free, ("F24",)),
    _sync(Meta("method:remove", "Let a place choose its own way of working again", G.SOCIETY), industry.remove_method, industry.MethodTarget, free, ("F24",)),
    _sync(
        Meta("industry:set", "Set and hold a place's energy and stores", G.SOCIETY),
        industry.set_industry,
        industry.SetIndustry,
        free,
        ("F24", "S6.3/RP2", "S6.4/RP2"),
    ),
    _sync(Meta("industry:remove", "Wipe a place's record of energy and stores", G.SOCIETY), industry.remove_industry, industry.IndustryTarget, free, ("F24",)),
    _sync(Meta("pollution:set", "Set and hold how fouled a land is", G.WORLDS), industry.set_pollution, industry.SetPollution, free, ("F24",)),
    _sync(Meta("pollution:purify", "Cleanse the air, water and soil of a land", G.WORLDS), industry.purify, industry.PurifyLand, free, ("F24",)),
    _sync(Meta("pollution:remove", "Wipe a land's record of pollution", G.WORLDS), industry.remove_pollution, industry.PollutionTarget, free, ("F24",)),
    _sync(Meta("workshop:owner", "Give a workshop to an owner", G.SOCIETY), industry.set_workshop_owner, industry.SetWorkshopOwner, free, ("S6.3/RP2",)),
    _sync(Meta("trade_policy:set", "Lay a tariff, subsidy or embargo", G.SOCIETY), finance.set_trade_policy, finance.SetTradePolicy, free, ("S6.4/RP2",)),
    _sync(
        Meta("trade_policy:remove", "Lift a tariff, subsidy or embargo", G.SOCIETY), finance.remove_trade_policy, finance.TradePolicyTarget, free, ("S6.4/RP2",)
    ),
    _sync(Meta("credit:set", "Set and hold a borrower's credit", G.SOCIETY), finance.set_credit, finance.SetCredit, free, ("S6.4/RP2",)),
    _sync(Meta("credit:remove", "Wipe a borrower's record of credit", G.SOCIETY), finance.remove_credit, finance.CreditTarget, free, ("S6.4/RP2",)),
    _sync(Meta("speculation:open", "Take goods off a market into a hoard", G.SOCIETY), finance.open_speculation, finance.OpenSpeculation, free, ("S6.4/RP2",)),
    _sync(Meta("speculation:edit", "Set and hold a hoard", G.SOCIETY), finance.edit_speculation, finance.EditSpeculation, free, ("S6.4/RP2",)),
    _sync(Meta("speculation:remove", "Strike a hoard", G.SOCIETY), finance.remove_speculation, finance.SpeculationTarget, free, ("S6.4/RP2",)),
    _sync(Meta("indicator:edit", "Rewrite a record of the economy", G.SOCIETY), finance.edit_indicator, finance.EditIndicator, free, ("S6.4/RP2",)),
    _sync(Meta("indicator:remove", "Strike a record of the economy", G.SOCIETY), finance.remove_indicator, finance.IndicatorTarget, free, ("S6.4/RP2",)),
    _sync(Meta("genome:found", "Write down the genome of a mortal", G.ENTITIES), genetics.found, genetics.GenomeTarget, free, ("F26",)),
    _sync(Meta("genome:gene", "Set and hold a pair of alleles in a mortal's blood", G.ENTITIES), genetics.set_gene, genetics.SetGene, free, ("F26",)),
    _sync(
        Meta("genome:edit", "Set and hold beauty, inbreeding, recognisability and divine blood", G.ENTITIES), genetics.edit, genetics.EditGenome, free, ("F26",)
    ),
    _sync(Meta("genome:redraw", "Draw a mortal's blood anew from the pool of its people", G.ENTITIES), genetics.redraw, genetics.GenomeTarget, free, ("F26",)),
    _sync(Meta("genome:remove", "Strike a mortal's written genome", G.ENTITIES), genetics.remove, genetics.GenomeTarget, free, ("F26",)),
    _sync(Meta("allele_pool:found", "Write down the allele pool of a people", G.SOCIETY), genetics.found_pool, genetics.PoolTarget, free, ("F26",)),
    _sync(
        Meta("allele_pool:frequency", "Set and hold how often an allele runs in a people", G.SOCIETY),
        genetics.set_frequency,
        genetics.SetFrequency,
        free,
        ("F26",),
    ),
    _sync(
        Meta("allele_pool:stance", "Set and hold how a people reads the magical gift", G.SOCIETY),
        genetics.set_stance,
        genetics.SetGiftStance,
        free,
        ("F26/RP8",),
    ),
    _sync(
        Meta("allele_pool:share", "Set and hold the gifted share of a people or a cohort", G.SOCIETY),
        genetics.edit_share,
        genetics.EditGiftShare,
        free,
        ("F26/RP8",),
    ),
    _sync(Meta("allele_pool:remove", "Strike a people's allele pool", G.SOCIETY), genetics.remove_pool, genetics.PoolTarget, free, ("F26",)),
    _sync(Meta("resemblance:set", "Set and hold the family likeness of a house", G.SOCIETY), genetics.set_resemblance, genetics.SetResemblance, free, ("F26",)),
    _sync(
        Meta("resemblance:remove", "Strike the family likeness of a house", G.SOCIETY), genetics.remove_resemblance, genetics.ResemblanceTarget, free, ("F26",)
    ),
    _sync(Meta("household:found", "Give a mortal a household of their own", G.SOCIETY), households.found, households.FoundHousehold, free, ("F29",)),
    _sync(
        Meta("household:edit", "Set and hold a household's purse, servants, burden and head", G.SOCIETY),
        households.edit,
        households.EditHousehold,
        free,
        ("F29",),
    ),
    _sync(Meta("household:debt", "Set and hold what a household owes another", G.SOCIETY), households.set_debt, households.SetDebt, free, ("F29",)),
    _sync(
        Meta("household:hold", "Hold or release the values and choices of a household", G.SOCIETY), households.hold, households.HoldHousehold, free, ("F29",)
    ),
    _sync(Meta("household:remove", "Dissolve a household", G.SOCIETY), households.remove, households.HouseholdTarget, free, ("F29",)),
    _sync(Meta("household:member", "Place a mortal in a household with a role", G.SOCIETY), households.set_member, households.SetMember, free, ("F29",)),
    _sync(Meta("household:release", "Take a mortal out of their household", G.SOCIETY), households.release, households.MemberTarget, free, ("F29",)),
    _sync(
        Meta("dwelling:set", "Set and hold the kind, quality, rooms and district of a home", G.SOCIETY),
        households.set_dwelling,
        households.SetDwelling,
        free,
        ("F29",),
    ),
    _sync(Meta("dwelling:remove", "Take a household's home away", G.SOCIETY), households.remove_dwelling, households.HouseholdTarget, free, ("F29",)),
    _sync(Meta("furnishing:add", "Furnish a home with an item or work of art", G.SOCIETY), households.furnish, households.Furnish, free, ("F29",)),
    _sync(Meta("furnishing:remove", "Take a furnishing out of a home", G.SOCIETY), households.unfurnish, households.FurnishingTarget, free, ("F29",)),
    _sync(
        Meta("household_aggregate:edit", "Set and hold the anonymous households of a community", G.SOCIETY),
        households.edit_aggregate,
        households.EditAggregate,
        free,
        ("F29",),
    ),
    _sync(
        Meta("household_aggregate:remove", "Strike a record of anonymous households", G.SOCIETY),
        households.remove_aggregate,
        households.AggregateTarget,
        free,
        ("F29",),
    ),
    _sync(Meta("secret:keep", "Give a thing a secret to keep", G.ENTITIES), intrigue.keep, intrigue.KeepSecret, free, ("F20",)),
    _sync(Meta("secret:edit", "Set and hold a secret's weight and who knows it", G.ENTITIES), intrigue.edit_secret, intrigue.EditSecret, free, ("F20",)),
    _sync(Meta("secret:hold", "Hold a secret as it stands or let it move", G.ENTITIES), intrigue.hold_secret, intrigue.EditSecret, free, ("F20",)),
    _sync(Meta("secret:expose", "Bring a secret to light", G.ENTITIES), intrigue.reveal, intrigue.SecretTarget, free, ("F20",)),
    _sync(Meta("secret:delete", "Strike a secret from the world", G.ENTITIES), intrigue.delete_secret, intrigue.SecretTarget, free, ("F20",)),
    _sync(Meta("hook:grant", "Give one thing a hook on another", G.ENTITIES), intrigue.grant, intrigue.GrantHook, free, ("F20",)),
    _sync(Meta("hook:edit", "Set and hold a hook's strength", G.ENTITIES), intrigue.edit_hook, intrigue.EditHook, free, ("F20",)),
    _sync(Meta("hook:use", "Press a hook with a demand", G.ENTITIES), intrigue.press, intrigue.UseHook, free, ("F20",)),
    _sync(Meta("hook:delete", "Break a hook", G.ENTITIES), intrigue.delete_hook, intrigue.HookTarget, free, ("F20",)),
    _sync(Meta("favour:owe", "Put one thing in another's debt", G.ENTITIES), intrigue.indebt, intrigue.OweFavour, free, ("F20",)),
    _sync(Meta("favour:edit", "Set and hold a favour's weight", G.ENTITIES), intrigue.edit_favour, intrigue.EditFavour, free, ("F20",)),
    _sync(Meta("favour:call", "Call a favour in, honoured or refused", G.ENTITIES), intrigue.call, intrigue.CallFavour, free, ("F20",)),
    _sync(Meta("favour:delete", "Forgive a favour", G.ENTITIES), intrigue.delete_favour, intrigue.FavourTarget, free, ("F20",)),
    _sync(
        Meta("gathering:convene", "Convene a gathering of any kind and hold it now or later", G.SOCIETY), gatherings.convene, gatherings.Convene, free, ("F25",)
    ),
    _sync(Meta("gathering:hold", "Hold a planned gathering now", G.SOCIETY), gatherings.hold_now, gatherings.GatheringTarget, free, ("F25",)),
    _sync(Meta("gathering:edit", "Edit and hold any value of a gathering", G.SOCIETY), gatherings.edit_gathering, gatherings.GatheringEdit, free, ("F25",)),
    _sync(Meta("gathering:delete", "Strike a gathering from memory", G.SOCIETY), gatherings.delete_gathering, gatherings.GatheringTarget, free, ("F25",)),
    _sync(
        Meta("gathering_guest:set", "Invite a guest, set its part and whether it came", G.SOCIETY), gatherings.set_guest, gatherings.GuestSet, free, ("F25",)
    ),
    _sync(Meta("gathering_guest:remove", "Send a guest away from a gathering", G.SOCIETY), gatherings.remove_guest, gatherings.GuestTarget, free, ("F25",)),
    _sync(
        Meta("collection:create", "Set down a history: a war, a plague, a wedding or any other", G.MEMORY),
        gatherings.create_collection,
        gatherings.CollectionDraft,
        free,
        ("F10/RP2",),
    ),
    _sync(Meta("collection:edit", "Edit and hold any value of a history", G.MEMORY), gatherings.edit_collection, gatherings.CollectionEdit, free, ("F10/RP2",)),
    _sync(Meta("collection:delete", "Unwrite a history", G.MEMORY), gatherings.delete_collection, gatherings.CollectionTarget, free, ("F10/RP2",)),
    _sync(
        Meta("collection_member:set", "Set the part a record played in a history", G.MEMORY), gatherings.set_member, gatherings.MemberSet, free, ("F10/RP2",)
    ),
    _sync(Meta("collection_member:remove", "Strike a record from a history", G.MEMORY), gatherings.remove_member, gatherings.MemberTarget, free, ("F10/RP2",)),
    _sync(Meta("collection:place", "Add or strike a place of a history", G.MEMORY), gatherings.set_place, gatherings.PlaceSet, free, ("F10/RP2",)),
    _sync(
        Meta("storyteller:set", "Set the storyteller of a world and hold its tension and pace", G.FATE),
        gatherings.set_storyteller,
        gatherings.StorytellerSet,
        free,
        ("F27",),
    ),
    _sync(Meta("site_room:create", "Open a room in a site", G.ENTITIES), gatherings.create_room, gatherings.RoomDraft, free, ("S6.2/RP2",)),
    _sync(Meta("site_room:edit", "Edit and hold any value of a room", G.ENTITIES), gatherings.edit_room, gatherings.RoomEdit, free, ("S6.2/RP2",)),
    _sync(Meta("site_room:delete", "Seal a room for good", G.ENTITIES), gatherings.delete_room, gatherings.RoomTarget, free, ("S6.2/RP2",)),
    _sync(
        Meta("room_content:add", "Set a thing, spirit, beast or trap in a room", G.ENTITIES),
        gatherings.add_content,
        gatherings.ContentDraft,
        free,
        ("S6.2/RP2",),
    ),
    _sync(
        Meta("room_content:remove", "Take a thing, spirit, beast or trap out of a room", G.ENTITIES),
        gatherings.remove_content,
        gatherings.ContentTarget,
        free,
        ("S6.2/RP2",),
    ),
    _sync(Meta("site:delve", "Send a mortal to walk a site room by room", G.ENTITIES), gatherings.delve, gatherings.DelveOrder, free, ("S6.2/RP2",)),
    _sync(Meta("site_holder:set", "Give a site into new hands", G.ENTITIES), gatherings.set_holder, gatherings.HolderSet, free, ("S6.2/RP2",)),
    _sync(
        Meta("site_holder:delete", "Strike a holding from a site's history", G.ENTITIES), gatherings.delete_holder, gatherings.HolderTarget, free, ("S6.2/RP2",)
    ),
    _sync(
        Meta("excavation:begin", "Begin a dig at a site with a leader and a sponsor", G.ENTITIES),
        gatherings.begin_dig,
        gatherings.DigDraft,
        free,
        ("S6.2/RP2",),
    ),
    _sync(Meta("excavation:edit", "Edit and hold any value of a dig", G.ENTITIES), gatherings.edit_dig, gatherings.DigEdit, free, ("S6.2/RP2",)),
    _sync(
        Meta("excavation:advance", "Carry a dig through its present stage now", G.ENTITIES), gatherings.advance_dig, gatherings.DigTarget, free, ("S6.2/RP2",)
    ),
    _sync(Meta("excavation:delete", "Fill in a dig and forget it", G.ENTITIES), gatherings.delete_dig, gatherings.DigTarget, free, ("S6.2/RP2",)),
    _sync(
        Meta("excavation_stage:edit", "Edit and hold the skill, technique, risk and find of a stage", G.ENTITIES),
        gatherings.edit_stage,
        gatherings.StageEdit,
        free,
        ("S6.2/RP2",),
    ),
    _sync(
        Meta("battlefield_feature:create", "Lay a mass grave or a field of salvage on a battlefield", G.ENTITIES),
        gatherings.create_feature,
        gatherings.FeatureDraft,
        free,
        ("S6.2/RP2",),
    ),
    _sync(
        Meta("battlefield_feature:edit", "Edit and hold a battlefield feature", G.ENTITIES),
        gatherings.edit_feature,
        gatherings.FeatureEdit,
        free,
        ("S6.2/RP2",),
    ),
    _sync(
        Meta("battlefield_feature:delete", "Clear a battlefield feature", G.ENTITIES), gatherings.delete_feature, gatherings.FeatureTarget, free, ("S6.2/RP2",)
    ),
    _sync(
        Meta("dominion:set", "Set and hold how strongly a god's dominion lies over a region", G.GOD_POWER),
        dominion.set_dominion,
        dominion.DominionSet,
        free,
        ("F31",),
    ),
    _sync(
        Meta("rite_grammar:edit", "Set the technique, form, range, duration and target of a rite", G.GOD_POWER),
        arcana.edit_grammar,
        arcana.RiteEdit,
        free,
        ("S8.6/RP3",),
    ),
    _sync(
        Meta("rite_grammar:delete", "Return a rite's grammar to that of its school", G.GOD_POWER), arcana.delete_grammar, arcana.RiteTarget, free, ("S8.6/RP3",)
    ),
    _sync(Meta("lab_text:write", "Have a mage set down a rite in a lab text", G.GOD_POWER), arcana.write_text, arcana.TextDraft, free, ("S8.6/RP3",)),
    _sync(Meta("lab_text:edit", "Edit a lab text", G.GOD_POWER), arcana.edit_text, arcana.TextEdit, free, ("S8.6/RP3",)),
    _sync(Meta("lab_text:delete", "Strike a rite from a lab text", G.GOD_POWER), arcana.delete_text, arcana.TextTarget, free, ("S8.6/RP3",)),
    _sync(Meta("vis:set", "Set and hold how much vis of one form a holder keeps", G.GOD_POWER), arcana.set_vis, arcana.VisSet, free, ("S8.6/RP3",)),
    _sync(Meta("vis:delete", "Take away a holder's vis of one form", G.GOD_POWER), arcana.delete_vis, arcana.VisTarget, free, ("S8.6/RP3",)),
    _sync(Meta("warping:edit", "Set and hold how warped a mortal is", G.GOD_POWER), arcana.edit_warping, arcana.BearerEdit, free, ("S8.6/RP3",)),
    _sync(Meta("warping:delete", "Undo a mortal's warping", G.GOD_POWER), arcana.delete_warping, arcana.BearerTarget, free, ("S8.6/RP3",)),
    _sync(
        Meta("longevity:begin", "Slow a mortal's ageing with longevity magic", G.GOD_POWER), arcana.begin_longevity, arcana.LongevityDraft, free, ("S8.6/RP3",)
    ),
    _sync(Meta("longevity:edit", "Edit a mortal's longevity magic", G.GOD_POWER), arcana.edit_longevity, arcana.LongevityEdit, free, ("S8.6/RP3",)),
    _sync(Meta("longevity:end", "End a mortal's longevity magic", G.GOD_POWER), arcana.end_longevity, arcana.LongevityTarget, free, ("S8.6/RP3",)),
    _sync(
        Meta("enchantment:lay", "Lay a global enchantment kept by its caster", G.GOD_POWER),
        arcana.lay_enchantment,
        arcana.EnchantmentDraft,
        free,
        ("S9.5/RP3",),
    ),
    _sync(Meta("law_upkeep:edit", "Set the upkeep and dispel resistance of a law", G.GOD_POWER), arcana.edit_upkeep, arcana.LawEdit, free, ("S9.5/RP3",)),
    _sync(Meta("law_upkeep:delete", "Free a law from its upkeep", G.GOD_POWER), arcana.delete_upkeep, arcana.LawTarget, free, ("S9.5/RP3",)),
    _sync(
        Meta("enchantment:dispel", "Dispel a global enchantment or law", G.GOD_POWER),
        arcana.dispel_enchantment,
        arcana.LawTarget,
        free,
        ("S8.6/RP3", "S9.5/RP3"),
    ),
    _sync(
        Meta("item_charge:edit", "Set the charges and recharge of an enchanted item", G.GOD_POWER), arcana.edit_charges, arcana.ChargeEdit, free, ("S8.6/RP3",)
    ),
    _sync(Meta("heroquest:party", "Choose who walks a heroquest beside its quester", G.GOD_POWER), mythic.set_party, mythic.QuestParty, free, ("S8.2/RP3",)),
    _sync(Meta("heroquest:begin", "Send a mortal on a heroquest", G.GOD_POWER), mythic.begin_quest, mythic.QuestDraft, free, ("S8.2/RP3",)),
    _sync(Meta("heroquest:edit", "Edit a heroquest", G.GOD_POWER), mythic.edit_quest, mythic.QuestEdit, free, ("S8.2/RP3",)),
    _sync(Meta("heroquest:advance", "Take a heroquest one step further", G.GOD_POWER), mythic.advance_quest, mythic.QuestTarget, free, ("S8.2/RP3",)),
    _sync(Meta("heroquest:delete", "Strike a heroquest from the record", G.GOD_POWER), mythic.delete_quest, mythic.QuestTarget, free, ("S8.2/RP3",)),
    _sync(Meta("mantling:edit", "Set and hold a mortal's path toward godhood", G.GOD_POWER), mythic.edit_mantling, mythic.MortalEdit, free, ("S3.1/RP3",)),
    _sync(Meta("mantling:delete", "End a mortal's path toward godhood", G.GOD_POWER), mythic.delete_mantling, mythic.MortalTarget, free, ("S3.1/RP3",)),
    _sync(Meta("servitor:make", "Make a servitor for a god", G.GOD_POWER), mythic.make_servitor, mythic.ServitorDraft, free, ("S3.3/RP3",)),
    _sync(Meta("servitor:edit", "Edit a servitor", G.GOD_POWER), mythic.edit_servitor, mythic.ServitorEdit, free, ("S3.3/RP3",)),
    _sync(Meta("servitor:release", "Release a servitor from service", G.GOD_POWER), mythic.release_servitor, mythic.ServitorTarget, free, ("S3.3/RP3",)),
    _sync(Meta("geas:lay", "Lay a geas on a mortal", G.GOD_POWER), mythic.lay_geas, mythic.GeasDraft, free, ("S4.8/RP3",)),
    _sync(Meta("geas:edit", "Edit a geas", G.GOD_POWER), mythic.edit_geas, mythic.GeasEdit, free, ("S4.8/RP3",)),
    _sync(Meta("geas:break", "Break a geas and let its doom fall", G.GOD_POWER), mythic.break_geas, mythic.GeasTarget, free, ("S4.8/RP3",)),
    _sync(Meta("geas:delete", "Lift a geas", G.GOD_POWER), mythic.delete_geas, mythic.GeasTarget, free, ("S4.8/RP3",)),
    _sync(Meta("cosmic_office:appoint", "Give a cosmic office to a god", G.GOD_POWER), mythic.appoint_office, mythic.OfficeSeat, free, ("S9.4/RP3",)),
    _sync(Meta("cosmic_office:edit", "Edit a cosmic office", G.GOD_POWER), mythic.edit_office, mythic.OfficeEdit, free, ("S9.4/RP3",)),
    _sync(Meta("cosmic_office:vacate", "Empty a cosmic office", G.GOD_POWER), mythic.vacate_office, mythic.OfficeTarget, free, ("S9.4/RP3",)),
    _sync(Meta("sound_change:add", "Decree a sound change in a tongue", G.LANGUAGES), tongues.add_change, tongues.ChangeDraft, free, ("S8.1/RP3",)),
    _sync(Meta("sound_change:edit", "Edit a sound change of a tongue", G.LANGUAGES), tongues.edit_change, tongues.ChangeEdit, free, ("S8.1/RP3",)),
    _sync(Meta("sound_change:delete", "Undo a sound change of a tongue", G.LANGUAGES), tongues.delete_change, tongues.ChangeTarget, free, ("S8.1/RP3",)),
    _sync(Meta("grammar:edit", "Edit the grammar of a tongue", G.LANGUAGES), tongues.edit_grammar, tongues.LanguageEdit, free, ("S8.1/RP3",)),
    _sync(Meta("grammar:reset", "Draw a tongue's grammar anew", G.LANGUAGES), tongues.reset_grammar, tongues.LanguageTarget, free, ("S8.1/RP3",)),
    _sync(Meta("tongue:edit", "Set a tongue's modality and stage", G.LANGUAGES), tongues.edit_profile, tongues.LanguageEdit, free, ("S8.1/RP3",)),
    _sync(Meta("word:register", "Move a word into another register", G.LANGUAGES), tongues.set_register, tongues.RegisterSet, free, ("S8.1/RP3",)),
    _sync(Meta("word:veil", "Forbid a name aloud and coin a euphemism for it", G.LANGUAGES), tongues.veil_name, tongues.VeilDraft, free, ("S8.1/RP3",)),
    _sync(Meta("meaning_shift:edit", "Edit the record of a word's shift in meaning", G.LANGUAGES), tongues.edit_shift, tongues.ShiftEdit, free, ("S8.1/RP3",)),
    _sync(
        Meta("meaning_shift:delete", "Strike a word's shift in meaning from the record", G.LANGUAGES),
        tongues.delete_shift,
        tongues.ShiftTarget,
        free,
        ("S8.1/RP3",),
    ),
    _sync(Meta("script:create", "Give a tongue a script", G.LANGUAGES), tongues.create_script, tongues.ScriptDraft, free, ("S8.1/RP3",)),
    _sync(Meta("script:edit", "Edit a script", G.LANGUAGES), tongues.edit_script, tongues.ScriptEdit, free, ("S8.1/RP3",)),
    _sync(Meta("script:delete", "Forget a script", G.LANGUAGES), tongues.delete_script, tongues.ScriptTarget, free, ("S8.1/RP3",)),
    _sync(Meta("script:assign", "Choose the script of a tongue, or none", G.LANGUAGES), tongues.assign_script, tongues.ScriptAssign, free, ("S8.1/RP3",)),
    _sync(Meta("decipherment:start", "Set scholars to decipher a dead script", G.LANGUAGES), tongues.start_work, tongues.WorkDraft, free, ("S8.1/RP3",)),
    _sync(Meta("decipherment:edit", "Edit a decipherment", G.LANGUAGES), tongues.edit_work, tongues.LanguageEdit, free, ("S8.1/RP3",)),
    _sync(Meta("decipherment:delete", "Strike a decipherment from the record", G.LANGUAGES), tongues.delete_work, tongues.LanguageTarget, free, ("S8.1/RP3",)),
    _sync(
        Meta("language_policy:set", "Make a tongue official, sacred, suppressed or revived somewhere", G.LANGUAGES),
        tongues.place_policy,
        tongues.PolicyDraft,
        free,
        ("S8.1/RP3",),
    ),
    _sync(Meta("language_policy:edit", "Edit a policy on a tongue", G.LANGUAGES), tongues.edit_policy, tongues.PolicyEdit, free, ("S8.1/RP3",)),
    _sync(Meta("language_policy:delete", "Lift a policy on a tongue", G.LANGUAGES), tongues.delete_policy, tongues.PolicyTarget, free, ("S8.1/RP3",)),
    _sync(Meta("divine_tongue:set", "Give a god its sacred tongue", G.LANGUAGES), tongues.choose_tongue, tongues.TongueChoice, free, ("S8.1/RP3",)),
    _sync(Meta("divine_tongue:edit", "Edit a god's sacred tongue", G.LANGUAGES), tongues.edit_tongue, tongues.TongueEdit, free, ("S8.1/RP3",)),
    _sync(Meta("divine_tongue:delete", "Take a god's sacred tongue away", G.LANGUAGES), tongues.delete_tongue, tongues.GodTarget, free, ("S8.1/RP3",)),
    _sync(Meta("divine_tongue:teach", "Teach a mortal words of a god's tongue", G.LANGUAGES), tongues.teach_tongue, tongues.TongueLesson, free, ("S8.1/RP3",)),
    _sync(
        Meta("species_trait:set", "Set and hold a trait of a species in one land", G.CREATURES),
        evolution.set_trait,
        evolution.TraitDraft,
        free,
        ("S3.2/RP3",),
    ),
    _sync(
        Meta("species_trait:edit", "Edit a trait of a species in one land", G.CREATURES),
        evolution.edit_trait,
        evolution.TraitEdit,
        free,
        ("S3.2/RP3",),
    ),
    _sync(
        Meta("species_trait:delete", "Let a species' traits in one land be drawn anew", G.CREATURES),
        evolution.delete_traits,
        evolution.TraitTarget,
        free,
        ("S3.2/RP3",),
    ),
    _sync(
        Meta("lineage:mark", "Mark a species' line with a blessing or a taint", G.CREATURES),
        evolution.mark_line,
        evolution.MarkDraft,
        free,
        ("S3.2/RP3",),
    ),
    _sync(Meta("lineage:edit", "Edit a mark on a species' line", G.CREATURES), evolution.edit_mark, evolution.MarkEdit, free, ("S3.2/RP3",)),
    _sync(Meta("lineage:delete", "Free a species' line of a mark", G.CREATURES), evolution.delete_mark, evolution.MarkTarget, free, ("S3.2/RP3",)),
    _sync(
        Meta("species_ecology:edit", "Set a species' keystone role and its feral past", G.CREATURES),
        evolution.edit_ecology,
        evolution.SpeciesEdit,
        free,
        ("S3.2/RP3",),
    ),
    _sync(
        Meta("ecosystem_service:set", "Set the service keystone species give a land", G.CREATURES),
        evolution.set_service,
        evolution.ServiceDraft,
        free,
        ("S3.2/RP3",),
    ),
    _sync(
        Meta("ecosystem_service:edit", "Edit a land's ecosystem service", G.CREATURES),
        evolution.edit_service,
        evolution.ServiceEdit,
        free,
        ("S3.2/RP3",),
    ),
    _sync(
        Meta("ecosystem_service:delete", "Strike a land's ecosystem service", G.CREATURES),
        evolution.delete_service,
        evolution.ServiceTarget,
        free,
        ("S3.2/RP3",),
    ),
    _sync(Meta("herd:release", "Loose a herd into the wild", G.CREATURES), evolution.release_herd, evolution.HerdTarget, free, ("S3.2/RP3",)),
    _sync(
        Meta("carrier:add", "Make a mortal carry a sickness unseen", G.SOCIETY),
        evolution.add_carrier,
        evolution.CarrierTarget,
        free,
        ("S3.4/RP3",),
    ),
    _sync(Meta("carrier:edit", "Edit a carrier of a sickness", G.SOCIETY), evolution.edit_carrier, evolution.CarrierEdit, free, ("S3.4/RP3",)),
    _sync(
        Meta("carrier:delete", "Free a mortal of the sickness it carries", G.SOCIETY),
        evolution.delete_carrier,
        evolution.CarrierTarget,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("plague_response:set", "Set how a community answers a sickness", G.SOCIETY),
        evolution.set_response,
        evolution.ResponseDraft,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("plague_response:edit", "Edit a community's answer to a sickness", G.SOCIETY),
        evolution.edit_response,
        evolution.ResponseEdit,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("plague_response:delete", "Lift a community's answer to a sickness", G.SOCIETY),
        evolution.delete_response,
        evolution.ResponseTarget,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("cure_research:start", "Set an institution to seek a cure", G.SOCIETY),
        evolution.start_research,
        evolution.ResearchTarget,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("cure_research:edit", "Edit an institution's search for a cure", G.SOCIETY),
        evolution.edit_research,
        evolution.ResearchEdit,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("cure_research:delete", "Abandon an institution's search for a cure", G.SOCIETY),
        evolution.delete_research,
        evolution.ResearchTarget,
        free,
        ("S3.4/RP3",),
    ),
    _sync(
        Meta("world_cycle:edit", "Set and hold a world's carbon, water and nutrient cycles", G.WORLDS),
        evolution.edit_cycle,
        evolution.CycleEdit,
        free,
        ("S10.9/RP3",),
    ),
    _sync(
        Meta("world_cycle:reset", "Return a world's cycles to balance", G.WORLDS),
        evolution.reset_cycle,
        evolution.CycleTarget,
        free,
        ("S10.9/RP3",),
    ),
    _sync(
        Meta("land:reshape", "Reshape a land: raise, lower, carve, fill, water, burn or sink it", G.WORLDS),
        evolution.reshape_land,
        evolution.LandDraft,
        free,
        ("S6.1/RP3",),
    ),
    _sync(
        Meta("district_urban:edit", "Set a district's homes, desirability and land value", G.SOCIETY),
        urban_depth.edit_district,
        urban_depth.DistrictEdit,
        free,
        ("S4.2/RP3",),
    ),
    _sync(Meta("town_urban:edit", "Set a town's growth pattern and its homeless", G.SOCIETY), urban_depth.edit_town, urban_depth.TownEdit, free, ("S4.2/RP3",)),
    _sync(
        Meta("structure:place", "Place a structure in a district of its town", G.SOCIETY),
        urban_depth.place_structure,
        urban_depth.Placement,
        free,
        ("S4.2/RP3",),
    ),
    _sync(Meta("slums:clear", "Clear a town's slums", G.SOCIETY), urban_depth.clear_slums, urban_depth.TownTarget, free, ("S4.2/RP3",)),
    _sync(
        Meta("district_service:set", "Set and hold how well a service covers a district", G.SOCIETY),
        urban_depth.set_service,
        urban_depth.ServiceDraft,
        free,
        ("S4.2/RP3",),
    ),
    _sync(
        Meta("district_service:edit", "Edit a district's service coverage", G.SOCIETY),
        urban_depth.edit_service,
        urban_depth.ServiceEdit,
        free,
        ("S4.2/RP3",),
    ),
    _sync(
        Meta("district_service:delete", "Let a district's service coverage be drawn anew", G.SOCIETY),
        urban_depth.delete_service,
        urban_depth.ServiceTarget,
        free,
        ("S4.2/RP3",),
    ),
    _sync(Meta("turf:set", "Give a criminal organisation turf in a district", G.SOCIETY), urban_depth.set_turf, urban_depth.TurfDraft, free, ("S4.2/RP3",)),
    _sync(Meta("turf:edit", "Edit a criminal organisation's turf", G.SOCIETY), urban_depth.edit_turf, urban_depth.TurfEdit, free, ("S4.2/RP3",)),
    _sync(
        Meta("turf:delete", "Drive a criminal organisation from a district", G.SOCIETY),
        urban_depth.delete_turf,
        urban_depth.TurfTarget,
        free,
        ("S4.2/RP3",),
    ),
    _sync(
        Meta("racket:set", "Set a racket a criminal organisation runs in a town", G.SOCIETY),
        urban_depth.set_racket,
        urban_depth.RacketDraft,
        free,
        ("S4.3/RP3",),
    ),
    _sync(Meta("racket:edit", "Edit a racket", G.SOCIETY), urban_depth.edit_racket, urban_depth.RacketEdit, free, ("S4.3/RP3",)),
    _sync(Meta("racket:delete", "Break a racket", G.SOCIETY), urban_depth.delete_racket, urban_depth.RacketTarget, free, ("S4.3/RP3",)),
    _sync(
        Meta("payroll:add", "Put an official on a criminal organisation's payroll", G.SOCIETY),
        urban_depth.add_payroll,
        urban_depth.PayrollDraft,
        free,
        ("S4.3/RP3",),
    ),
    _sync(Meta("payroll:edit", "Edit an official's bribe", G.SOCIETY), urban_depth.edit_payroll, urban_depth.PayrollEdit, free, ("S4.3/RP3",)),
    _sync(Meta("payroll:delete", "Take an official off a payroll", G.SOCIETY), urban_depth.delete_payroll, urban_depth.PayrollTarget, free, ("S4.3/RP3",)),
    _sync(
        Meta("crime_stance:set", "Set how a realm treats a criminal organisation", G.SOCIETY),
        urban_depth.set_stance,
        urban_depth.StanceDraft,
        free,
        ("S4.3/RP3",),
    ),
    _sync(
        Meta("crime_stance:edit", "Edit a realm's stance on a criminal organisation", G.SOCIETY),
        urban_depth.edit_stance,
        urban_depth.StanceEdit,
        free,
        ("S4.3/RP3",),
    ),
    _sync(
        Meta("crime_stance:delete", "Drop a realm's stance on a criminal organisation", G.SOCIETY),
        urban_depth.delete_stance,
        urban_depth.StanceTarget,
        free,
        ("S4.3/RP3",),
    ),
    _sync(Meta("order_law:set", "Give a magical order a law", G.SOCIETY), urban_depth.set_law, urban_depth.LawDraft, free, ("S4.3/RP3",)),
    _sync(Meta("order_law:edit", "Edit a law of a magical order", G.SOCIETY), urban_depth.edit_law, urban_depth.LawEdit, free, ("S4.3/RP3",)),
    _sync(Meta("order_law:delete", "Strike a law of a magical order", G.SOCIETY), urban_depth.delete_law, urban_depth.LawTarget, free, ("S4.3/RP3",)),
    _sync(
        Meta("tribunal:convene", "Convene a magical order's tribunal against a member", G.SOCIETY),
        urban_depth.convene,
        urban_depth.Trial,
        free,
        ("S4.3/RP3",),
    ),
    _sync(
        Meta("tribunal:strike", "Strike a tribunal's judgement from the record", G.SOCIETY),
        urban_depth.strike_trial,
        urban_depth.TrialTarget,
        free,
        ("S4.3/RP3",),
    ),
    _sync(
        Meta("trading_post:open", "Open a merchant house's trading post in a foreign town", G.SOCIETY),
        urban_depth.open_trading_post,
        urban_depth.PostDraft,
        free,
        ("S4.3/RP3",),
    ),
    _sync(Meta("trading_post:edit", "Edit a trading post", G.SOCIETY), urban_depth.edit_trading_post, urban_depth.PostEdit, free, ("S4.3/RP3",)),
    _sync(Meta("trading_post:close", "Close a trading post", G.SOCIETY), urban_depth.close_trading_post, urban_depth.PostTarget, free, ("S4.3/RP3",)),
    _sync(Meta("convoy:send", "Send a convoy along a trade route", G.SOCIETY), urban_depth.send_convoy, urban_depth.RouteTarget, free, ("S6.4/RP3",)),
    _sync(Meta("convoy:edit", "Edit a convoy", G.SOCIETY), urban_depth.edit_convoy, urban_depth.ConvoyEdit, free, ("S6.4/RP3",)),
    _sync(Meta("convoy:delete", "Strike a convoy from the road", G.SOCIETY), urban_depth.delete_convoy, urban_depth.ConvoyTarget, free, ("S6.4/RP3",)),
    _sync(Meta("fleet:set", "Set and hold an owner's wagons, boats or animals", G.SOCIETY), urban_depth.set_fleet, urban_depth.FleetDraft, free, ("S6.4/RP3",)),
    _sync(Meta("fleet:edit", "Edit a transport fleet", G.SOCIETY), urban_depth.edit_fleet, urban_depth.FleetEdit, free, ("S6.4/RP3",)),
    _sync(Meta("fleet:delete", "Take away a transport fleet", G.SOCIETY), urban_depth.delete_fleet, urban_depth.FleetTarget, free, ("S6.4/RP3",)),
    _sync(
        Meta("market_play:set", "Make a merchant house corner or flood a market", G.SOCIETY),
        urban_depth.set_play,
        urban_depth.PlayDraft,
        free,
        ("S6.4/RP3",),
    ),
    _sync(Meta("market_play:edit", "Edit a market play", G.SOCIETY), urban_depth.edit_play, urban_depth.PlayEdit, free, ("S6.4/RP3",)),
    _sync(Meta("market_play:delete", "End a market play", G.SOCIETY), urban_depth.delete_play, urban_depth.PlayTarget, free, ("S6.4/RP3",)),
    _sync(
        Meta("legal_system:set", "Set the legal system of a realm, cult or town", G.SOCIETY),
        law_depth.legal_system_set,
        law_depth.SystemDraft,
        free,
        ("S4.5/RP3",),
    ),
    _sync(Meta("legal_system:edit", "Edit a legal system", G.SOCIETY), law_depth.legal_system_edit, law_depth.SystemEdit, free, ("S4.5/RP3",)),
    _sync(
        Meta("legal_system:delete", "Let a legal system be chosen anew", G.SOCIETY), law_depth.legal_system_delete, law_depth.SystemTarget, free, ("S4.5/RP3",)
    ),
    _sync(
        Meta("precedent:add", "Set down a precedent in a realm's case law", G.SOCIETY), law_depth.precedent_add, law_depth.PrecedentDraft, free, ("S4.5/RP3",)
    ),
    _sync(Meta("precedent:edit", "Edit a precedent", G.SOCIETY), law_depth.precedent_edit, law_depth.PrecedentEdit, free, ("S4.5/RP3",)),
    _sync(
        Meta("precedent:delete", "Strike a precedent from the case law", G.SOCIETY), law_depth.precedent_delete, law_depth.PrecedentTarget, free, ("S4.5/RP3",)
    ),
    _sync(Meta("appeal:file", "Carry a conviction to a higher court", G.SOCIETY), law_depth.appeal_file, law_depth.AppealDraft, free, ("S4.5/RP3",)),
    _sync(Meta("appeal:edit", "Edit an appeal", G.SOCIETY), law_depth.appeal_edit, law_depth.AppealEdit, free, ("S4.5/RP3",)),
    _sync(Meta("appeal:hear", "Hear an appeal now", G.SOCIETY), law_depth.appeal_hear, law_depth.AppealTarget, free, ("S4.5/RP3",)),
    _sync(Meta("appeal:delete", "Withdraw an appeal", G.SOCIETY), law_depth.appeal_delete, law_depth.AppealTarget, free, ("S4.5/RP3",)),
    _sync(Meta("oracle:answer", "Answer an oracle trial, truly or falsely", G.SOCIETY), law_depth.oracle_answer, law_depth.OracleAnswer, free, ("S4.5/RP3",)),
    _sync(Meta("registry:add", "Register a title or contract", G.SOCIETY), law_depth.registry_add, law_depth.RegistryDraft, free, ("S4.5/RP3",)),
    _sync(Meta("registry:edit", "Edit a registered title or contract", G.SOCIETY), law_depth.registry_edit, law_depth.RegistryEdit, free, ("S4.5/RP3",)),
    _sync(Meta("registry:delete", "Strike a deed from the registry", G.SOCIETY), law_depth.registry_delete, law_depth.RegistryTarget, free, ("S4.5/RP3",)),
    _sync(
        Meta("jurisdiction:set", "Give a church, guild or realm its own courts in a realm", G.SOCIETY),
        law_depth.jurisdiction_set,
        law_depth.ClaimDraft,
        free,
        ("S4.5/RP3",),
    ),
    _sync(Meta("jurisdiction:edit", "Edit a claim to courts", G.SOCIETY), law_depth.jurisdiction_edit, law_depth.ClaimEdit, free, ("S4.5/RP3",)),
    _sync(Meta("jurisdiction:delete", "End a claim to courts", G.SOCIETY), law_depth.jurisdiction_delete, law_depth.ClaimTarget, free, ("S4.5/RP3",)),
    _sync(Meta("pardon:grant", "Have a mortal pardon a prisoner or an outlaw", G.SOCIETY), law_depth.pardon_grant, law_depth.PardonDraft, free, ("S4.5/RP3",)),
    _sync(Meta("amnesty:declare", "Have a realm's ruler declare an amnesty", G.SOCIETY), law_depth.amnesty_declare, law_depth.RealmTarget, free, ("S4.5/RP3",)),
    _sync(Meta("pardon:delete", "Strike a pardon from the record", G.SOCIETY), law_depth.pardon_delete, law_depth.PardonTarget, free, ("S4.5/RP3",)),
    _sync(Meta("outlaw:declare", "Declare a mortal an outlaw", G.SOCIETY), law_depth.outlaw_declare, law_depth.OutlawDraft, free, ("S4.5/RP3",)),
    _sync(Meta("outlaw:edit", "Edit an outlaw's bounty and renown", G.SOCIETY), law_depth.outlaw_edit, law_depth.OutlawEdit, free, ("S4.5/RP3",)),
    _sync(Meta("outlaw:delete", "Lift a mortal's outlawry", G.SOCIETY), law_depth.outlaw_delete, law_depth.MortalTarget, free, ("S4.5/RP3",)),
    _sync(Meta("prison:set", "Set a prison's food, crowding, cruelty and gangs", G.SOCIETY), law_depth.prison_set, law_depth.PrisonDraft, free, ("S4.5/RP3",)),
    _sync(Meta("prison:edit", "Edit a prison", G.SOCIETY), law_depth.prison_edit, law_depth.PrisonEdit, free, ("S4.5/RP3",)),
    _sync(Meta("prison:delete", "Let a prison's conditions be drawn anew", G.SOCIETY), law_depth.prison_delete, law_depth.PrisonTarget, free, ("S4.5/RP3",)),
    _sync(Meta("prisoner:jail", "Put a mortal in a prison", G.SOCIETY), law_depth.prisoner_jail, law_depth.JailDraft, free, ("S4.5/RP3",)),
    _sync(Meta("prisoner:edit", "Edit a prisoner's term and rank", G.SOCIETY), law_depth.prisoner_edit, law_depth.PrisonerEdit, free, ("S4.5/RP3",)),
    _sync(Meta("prisoner:free", "Free a prisoner", G.SOCIETY), law_depth.prisoner_free, law_depth.MortalTarget, free, ("S4.5/RP3",)),
    _sync(Meta("spy_cell:add", "Form a spy cell in a network", G.WARFARE), law_depth.spy_cell_add, law_depth.CellDraft, free, ("S5.10/RP3",)),
    _sync(Meta("spy_cell:edit", "Edit a spy cell", G.WARFARE), law_depth.spy_cell_edit, law_depth.CellEdit, free, ("S5.10/RP3",)),
    _sync(Meta("spy_cell:delete", "Break up a spy cell", G.WARFARE), law_depth.spy_cell_delete, law_depth.CellTarget, free, ("S5.10/RP3",)),
    _sync(
        Meta("mole_hunt:order", "Have a realm's spymaster hunt for moles now", G.WARFARE),
        law_depth.mole_hunt_order,
        law_depth.RealmTarget,
        free,
        ("S5.10/RP3",),
    ),
    _sync(Meta("mole_hunt:delete", "Strike a mole hunt from the record", G.WARFARE), law_depth.mole_hunt_delete, law_depth.HuntTarget, free, ("S5.10/RP3",)),
    _sync(
        Meta("defection:make", "Have a mortal defect with what they know", G.WARFARE), law_depth.defection_make, law_depth.DefectionDraft, free, ("S5.10/RP3",)
    ),
    _sync(Meta("defection:edit", "Edit a defection", G.WARFARE), law_depth.defection_edit, law_depth.DefectionEdit, free, ("S5.10/RP3",)),
    _sync(
        Meta("defection:delete", "Strike a defection from the record", G.WARFARE), law_depth.defection_delete, law_depth.DefectionTarget, free, ("S5.10/RP3",)
    ),
    _sync(Meta("killing:add", "Record a killing and how it was done", G.WARFARE), law_depth.killing_add, law_depth.KillingDraft, free, ("S5.10/RP3",)),
    _sync(
        Meta("killing:edit", "Edit how a killing was done and whether it was seen", G.WARFARE),
        law_depth.killing_edit,
        law_depth.KillingEdit,
        free,
        ("S5.10/RP3",),
    ),
    _sync(Meta("killing:delete", "Strike a killing from the record", G.WARFARE), law_depth.killing_delete, law_depth.KillingTarget, free, ("S5.10/RP3",)),
    _sync(Meta("pidgin:make", "Make a pidgin between two communities", G.LANGUAGES), tongues.make_pidgin, tongues.PidginDraft, free, ("S8.1/RP3",)),
    _sync(Meta("dominion:delete", "Lift a god's dominion from a region", G.GOD_POWER), dominion.delete_dominion, dominion.DominionTarget, free, ("F31",)),
    _sync(
        Meta("god_scale:set", "Set and hold where a god pulls the land on one of its scales", G.GOD_POWER),
        dominion.set_scale,
        dominion.ScaleSet,
        free,
        ("F31",),
    ),
    _sync(Meta("god_scale:delete", "Set a god's scale back to the middle", G.GOD_POWER), dominion.delete_scale, dominion.ScaleTarget, free, ("F31",)),
    _sync(
        Meta("god_design:edit", "Edit and hold a god's design: budget, dominion strength, magic, body, stats and rank", G.GOD_POWER),
        dominion.edit_design,
        dominion.GodEdit,
        free,
        ("S9.1/RP3",),
    ),
    _sync(Meta("god_design:delete", "Have a god's design weighed anew", G.GOD_POWER), dominion.delete_design, dominion.GodTarget, free, ("S9.1/RP3",)),
    _sync(
        Meta("god_image:edit", "Edit and hold the image peoples hold of a god, and whether it yields, resists or embraces it", G.GOD_POWER),
        dominion.edit_image,
        dominion.GodEdit,
        free,
        ("S9.1/RP3",),
    ),
    _sync(
        Meta("god_image:delete", "Have the image of a god read anew from its peoples", G.GOD_POWER),
        dominion.delete_image,
        dominion.GodTarget,
        free,
        ("S9.1/RP3",),
    ),
    _sync(
        Meta("miracle_record:edit", "Edit and hold how a miracle was seen and who was credited", G.INTERVENTIONS),
        dominion.edit_miracle,
        dominion.MiracleEdit,
        free,
        ("S9.1/RP3",),
    ),
    _sync(Meta("miracle_record:delete", "Strike a miracle from memory", G.INTERVENTIONS), dominion.delete_miracle, dominion.MiracleTarget, free, ("S9.1/RP3",)),
    _sync(Meta("magic_site:create", "Lay a magic site at a place, hidden or found", G.WORLDS), dominion.create_site, dominion.SiteDraft, free, ("S6.2/RP3",)),
    _sync(Meta("magic_site:edit", "Edit and hold any value of a magic site", G.WORLDS), dominion.edit_site, dominion.SiteEdit, free, ("S6.2/RP3",)),
    _sync(
        Meta("magic_site:reveal", "Reveal a hidden magic site, to a finder or to all", G.WORLDS), dominion.reveal_site, dominion.SiteReveal, free, ("S6.2/RP3",)
    ),
    _sync(Meta("magic_site:delete", "Unmake a magic site", G.WORLDS), dominion.delete_site, dominion.SiteTarget, free, ("S6.2/RP3",)),
    _sync(Meta("throne:create", "Raise a throne of power at a place", G.WORLDS), dominion.create_throne, dominion.ThroneDraft, free, ("S6.2/RP3",)),
    _sync(Meta("throne:edit", "Edit and hold a throne's power and holder", G.WORLDS), dominion.edit_throne, dominion.ThroneEdit, free, ("S6.2/RP3",)),
    _sync(Meta("throne:delete", "Cast down a throne of power", G.WORLDS), dominion.delete_throne, dominion.ThroneTarget, free, ("S6.2/RP3",)),
    _sync(
        Meta("divine_creature:raise", "Raise a divine creature for a god", G.CREATURES), dominion.raise_creature, dominion.CreatureDraft, free, ("S9.1/RP3",)
    ),
    _sync(
        Meta("divine_creature:edit", "Edit and hold a divine creature's hunger, neglect and last deed", G.CREATURES),
        dominion.edit_creature,
        dominion.CreatureEdit,
        free,
        ("S9.1/RP3",),
    ),
    _sync(
        Meta("divine_creature:teach", "Reward or punish a divine creature for a deed", G.CREATURES),
        dominion.teach_creature,
        dominion.CreatureLessonOrder,
        free,
        ("S9.1/RP3",),
    ),
    _sync(
        Meta("divine_creature:weight", "Set and hold how much a divine creature leans to a deed", G.CREATURES),
        dominion.weight_creature,
        dominion.CreatureWeight,
        free,
        ("S9.1/RP3",),
    ),
    _sync(
        Meta("divine_creature:release", "Release a divine creature from its god", G.CREATURES),
        dominion.release_creature,
        dominion.CreatureTarget,
        free,
        ("S9.1/RP3",),
    ),
    _sync(Meta("identity:assume", "Give a mortal a false name to live under", G.ENTITIES), intrigue.mask, intrigue.AssumeIdentity, free, ("F20",)),
    _sync(
        Meta("identity:edit", "Set and hold a false name, cover, community and exposure", G.ENTITIES),
        intrigue.edit_identity,
        intrigue.EditIdentity,
        free,
        ("F20",),
    ),
    _sync(Meta("identity:unmask", "Tear away a false name", G.ENTITIES), intrigue.unmask_identity, intrigue.IdentityTarget, free, ("F20",)),
    _sync(Meta("identity:delete", "Strike a false identity", G.ENTITIES), intrigue.delete_identity, intrigue.IdentityTarget, free, ("F20",)),
    _sync(Meta("scheme:begin", "Set a being plotting a scheme", G.ENTITIES), intrigue.plot, intrigue.BeginScheme, free, ("F20",)),
    _sync(
        Meta("scheme:edit", "Set and hold a scheme's phase, power, secrecy, progress and agents", G.ENTITIES),
        intrigue.edit_scheme,
        intrigue.EditScheme,
        free,
        ("F20",),
    ),
    _sync(Meta("scheme:hold", "Freeze a scheme where it stands or let it move", G.ENTITIES), intrigue.hold_scheme, intrigue.EditScheme, free, ("F20",)),
    _sync(Meta("scheme:delete", "Erase a scheme", G.ENTITIES), intrigue.delete_scheme, intrigue.SchemeTarget, free, ("F20",)),
    _sync(Meta("true_name:set", "Give, change or draw anew a true name", G.ENTITIES), intrigue.name_truly, intrigue.SetTrueName, free, ("F20/RP3",)),
    _sync(
        Meta("true_name:teach", "Reveal a true name to someone or make them forget it", G.ENTITIES), intrigue.teach, intrigue.TeachTrueName, free, ("F20/RP3",)
    ),
    _sync(Meta("true_name:delete", "Strike a true name", G.ENTITIES), intrigue.delete_true_name, intrigue.TrueNameTarget, free, ("F20/RP3",)),
    _sync(Meta("belief:set", "Put a belief in a mind, true or false, and hold it", G.ENTITIES), intrigue.set_belief, intrigue.SetBelief, free, ("F22",)),
    _sync(Meta("belief:delete", "Wipe a belief from a mind", G.ENTITIES), intrigue.delete_belief, intrigue.BeliefTarget, free, ("F22",)),
    _sync(
        Meta("dispatch:send", "Send a message between the living, by any medium", G.DIPLOMACY), communication.post, communication.SendDispatch, free, ("F21",)
    ),
    _sync(
        Meta("dispatch:edit", "Set and hold a message's state, arrival, forgery, misreading, cipher and interceptor", G.DIPLOMACY),
        communication.edit_dispatch,
        communication.EditDispatch,
        free,
        ("F21",),
    ),
    _sync(
        Meta("dispatch:hold", "Hold a message where it is or let it travel", G.DIPLOMACY),
        communication.hold_dispatch,
        communication.EditDispatch,
        free,
        ("F21",),
    ),
    _sync(Meta("dispatch:delete", "Unmake a message", G.DIPLOMACY), communication.delete_dispatch, communication.DispatchTarget, free, ("F21",)),
    _sync(
        Meta("opinion:set", "Set and hold what a community thinks of a ruler, war, law, god or creed", G.SOCIETY),
        communication.set_opinion,
        communication.SetOpinion,
        free,
        ("F21",),
    ),
    _sync(Meta("opinion:delete", "Wipe a community's opinion", G.SOCIETY), communication.delete_opinion, communication.OpinionTarget, free, ("F21",)),
    _sync(Meta("cipher:set", "Give or set and hold a cipher", G.DIPLOMACY), communication.set_cipher, communication.SetCipher, free, ("F21/RP3",)),
    _sync(Meta("cipher:break", "Let a codebreaker read a cipher", G.DIPLOMACY), communication.break_cipher, communication.BreakCipher, free, ("F21/RP3",)),
    _sync(Meta("cipher:mend", "Make a broken cipher new", G.DIPLOMACY), communication.mend_cipher, communication.CipherTarget, free, ("F21/RP3",)),
    _sync(Meta("cipher:delete", "Strike a cipher", G.DIPLOMACY), communication.delete_cipher, communication.CipherTarget, free, ("F21/RP3",)),
    _sync(
        Meta("signal:build", "Raise a signal link between two lands", G.DIPLOMACY), communication.build_signal, communication.BuildSignal, free, ("F21/RP3",)
    ),
    _sync(
        Meta("signal:edit", "Set and hold a signal link's state and owner", G.DIPLOMACY),
        communication.edit_signal,
        communication.EditSignal,
        free,
        ("F21/RP3",),
    ),
    _sync(Meta("signal:delete", "Tear down a signal link", G.DIPLOMACY), communication.delete_signal, communication.SignalTarget, free, ("F21/RP3",)),
    _sync(
        Meta("title:create", "Create a title of any rank, with its holder, realm, liege and lands", G.DIPLOMACY),
        titles.create,
        titles.CreateTitle,
        free,
        ("S4.11",),
    ),
    _sync(
        Meta("title:edit", "Set and hold a title's rank, liege, realm, capital, succession law, arms and prestige", G.DIPLOMACY),
        titles.edit,
        titles.EditTitle,
        free,
        ("S4.11",),
    ),
    _sync(Meta("title:hold", "Hold a title against the world or let it move", G.DIPLOMACY), titles.hold_title, titles.EditTitle, free, ("S4.11",)),
    _sync(Meta("title:grant", "Grant or usurp a title for a holder, or leave it dormant", G.DIPLOMACY), titles.grant, titles.PassTitle, free, ("S4.11",)),
    _sync(Meta("title:destroy", "Destroy a title, leaving it to be restored", G.DIPLOMACY), titles.destroy, titles.TitleTarget, free, ("S4.11",)),
    _sync(Meta("title:restore", "Restore a destroyed title to a holder", G.DIPLOMACY), titles.restore, titles.PassTitle, free, ("S4.11",)),
    _sync(Meta("title:remove", "Strike a title's record", G.DIPLOMACY), titles.remove, titles.TitleTarget, free, ("S4.11",)),
    _sync(Meta("de_jure:set", "Make a land or lesser title belong by right to a title", G.DIPLOMACY), titles.set_de_jure, titles.SetDeJure, free, ("S4.11",)),
    _sync(Meta("de_jure:remove", "Strike a land from a title's right", G.DIPLOMACY), titles.remove_de_jure, titles.DeJureTarget, free, ("S4.11",)),
    _sync(Meta("estate:found", "Gather a class of a realm as an estate", G.SOCIETY), estates.found, estates.FoundEstate, free, ("S4.3/RP2",)),
    _sync(Meta("estate:edit", "Set and hold an estate's loyalty and influence", G.SOCIETY), estates.edit, estates.EditEstate, free, ("S4.3/RP2",)),
    _sync(Meta("estate:privilege", "Grant or take back an estate's privilege", G.SOCIETY), estates.privilege, estates.SetPrivilege, free, ("S4.3/RP2",)),
    _sync(Meta("estate:remove", "Strike an estate's standing", G.SOCIETY), estates.remove, estates.EstateTarget, free, ("S4.3/RP2",)),
    _sync(Meta("movement:found", "Raise a movement for a cause in a realm", G.SOCIETY), estates.found_cause, estates.FoundMovement, free, ("S4.3/RP2",)),
    _sync(
        Meta("movement:edit", "Set and hold a movement's support, cause and whether it is a party", G.SOCIETY),
        estates.edit_movement,
        estates.EditMovement,
        free,
        ("S4.3/RP2",),
    ),
    _sync(
        Meta("movement:support", "Set and hold a community's support for a movement", G.SOCIETY), estates.set_support, estates.SetSupport, free, ("S4.3/RP2",)
    ),
    _sync(
        Meta("movement:support_remove", "Wipe a community's support for a movement", G.SOCIETY),
        estates.remove_support,
        estates.SupportTarget,
        free,
        ("S4.3/RP2",),
    ),
    _sync(Meta("movement:remove", "Strike a movement's cause", G.SOCIETY), estates.remove_movement, estates.MovementTarget, free, ("S4.3/RP2",)),
    _sync(
        Meta("company:edit", "Charter or set and hold a company's dividend, route, land and goods", G.SOCIETY),
        estates.edit_company,
        estates.EditCompany,
        free,
        ("S4.3/RP2",),
    ),
    _sync(Meta("company:share", "Set and hold a shareholder's stake in a company", G.SOCIETY), estates.set_share, estates.SetShare, free, ("S4.3/RP2",)),
    _sync(Meta("company:share_remove", "Strike a shareholder's stake", G.SOCIETY), estates.remove_share, estates.ShareTarget, free, ("S4.3/RP2",)),
    _sync(Meta("company:remove", "Strike a company's charter", G.SOCIETY), estates.remove_company, estates.CompanyTarget, free, ("S4.3/RP2",)),
    _sync(
        Meta("holy_order:edit", "Bind or set and hold a holy order's faith, fortress and tithe", G.SOCIETY),
        estates.edit_order,
        estates.EditOrder,
        free,
        ("S4.3/RP2",),
    ),
    _sync(Meta("holy_order:remove", "Strike a holy order's vows", G.SOCIETY), estates.remove_order, estates.OrderTarget, free, ("S4.3/RP2",)),
    _sync(Meta("guild:secret", "Make a guild keep or lose a craft secret", G.SOCIETY), estates.secret, estates.SetSecret, free, ("S4.3/RP2",)),
    _sync(
        Meta("proposal:create", "Bring a law before a realm, with its terms, champion and the law it would amend", G.SOCIETY),
        justice.create_proposal,
        justice.CreateProposal,
        free,
        ("S4.5/RP2",),
    ),
    _sync(
        Meta("proposal:edit", "Set and hold a proposal's terms, champion, progress, support, opposition, stall and state", G.SOCIETY),
        justice.edit_proposal,
        justice.EditProposal,
        free,
        ("S4.5/RP2",),
    ),
    _sync(Meta("proposal:hold", "Hold a proposal where it stands or let it move", G.SOCIETY), justice.hold_proposal, justice.HoldProposal, free, ("S4.5/RP2",)),
    _sync(Meta("proposal:pass", "Carry a proposal into law at once", G.SOCIETY), justice.pass_proposal, justice.ProposalTarget, free, ("S4.5/RP2",)),
    _sync(Meta("proposal:delete", "Strike a proposal", G.SOCIETY), justice.delete_proposal, justice.ProposalTarget, free, ("S4.5/RP2",)),
    _sync(
        Meta("stance:set", "Set and hold how a voice stands on a proposal and its weight", G.SOCIETY),
        justice.set_stance,
        justice.SetStance,
        free,
        ("S4.5/RP2",),
    ),
    _sync(Meta("stance:remove", "Silence a voice on a proposal", G.SOCIETY), justice.remove_stance, justice.StanceTarget, free, ("S4.5/RP2",)),
    _sync(
        Meta("case:open", "Bring a mortal to trial for a crime, naming the culprit, judge, investigator, trial and evidence", G.SOCIETY),
        justice.open_case,
        justice.OpenCase,
        free,
        ("S4.5/RP2",),
    ),
    _sync(
        Meta("case:edit", "Set and hold a case's accused, culprit, judge, investigator, trial, evidence, stage and crime", G.SOCIETY),
        justice.edit_case,
        justice.EditCase,
        free,
        ("S4.5/RP2",),
    ),
    _sync(Meta("case:hold", "Hold a case's course and verdict or let it run", G.SOCIETY), justice.hold_case, justice.HoldCase, free, ("S4.5/RP2",)),
    _sync(Meta("case:try", "Try a case at once", G.SOCIETY), justice.try_now, justice.CaseTarget, free, ("S4.5/RP2",)),
    _sync(Meta("case:delete", "Strike a case", G.SOCIETY), justice.delete_case, justice.CaseTarget, free, ("S4.5/RP2",)),
    _sync(Meta("witness:set", "Set and hold a witness's testimony and reliability", G.SOCIETY), justice.set_witness, justice.SetWitness, free, ("S4.5/RP2",)),
    _sync(Meta("witness:remove", "Strike a witness's testimony", G.SOCIETY), justice.remove_witness, justice.WitnessTarget, free, ("S4.5/RP2",)),
    _sync(
        Meta("regard:set", "Set and hold the threat and trust one realm feels toward another", G.DIPLOMACY),
        statecraft.set_regard,
        statecraft.SetRegard,
        free,
        ("S4.6/RP2",),
    ),
    _sync(
        Meta("regard:remove", "Wipe what one realm feels toward another", G.DIPLOMACY), statecraft.remove_regard, statecraft.RegardTarget, free, ("S4.6/RP2",)
    ),
    _sync(
        Meta("diplomacy:edit", "Set and hold a realm's diplomatic capacity, relations and strain", G.DIPLOMACY),
        statecraft.edit_diplomacy,
        statecraft.EditDiplomacy,
        free,
        ("S4.6/RP2",),
    ),
    _sync(Meta("crisis:open", "Open a crisis: one realm's demand on another", G.DIPLOMACY), statecraft.open_crisis, statecraft.OpenCrisis, free, ("S4.6/RP2",)),
    _sync(
        Meta("crisis:edit", "Set and hold a crisis's step, amount and subject", G.DIPLOMACY), statecraft.edit_crisis, statecraft.EditCrisis, free, ("S4.6/RP2",)
    ),
    _sync(Meta("crisis:hold", "Freeze a crisis or let it run", G.DIPLOMACY), statecraft.hold_crisis, statecraft.HoldCrisis, free, ("S4.6/RP2",)),
    _sync(
        Meta("crisis:resolve", "End a crisis at once: back down, concede or war", G.DIPLOMACY),
        statecraft.resolve_crisis,
        statecraft.ResolveCrisis,
        free,
        ("S4.6/RP2",),
    ),
    _sync(Meta("crisis:delete", "Strike a crisis", G.DIPLOMACY), statecraft.delete_crisis, statecraft.CrisisTarget, free, ("S4.6/RP2",)),
    _sync(
        Meta("backer:set", "Set and hold a realm's backing of a side in a crisis", G.DIPLOMACY),
        statecraft.set_backer,
        statecraft.SetBacker,
        free,
        ("S4.6/RP2",),
    ),
    _sync(Meta("backer:remove", "Withdraw a backer from a crisis", G.DIPLOMACY), statecraft.remove_backer, statecraft.BackerTarget, free, ("S4.6/RP2",)),
    _sync(Meta("sphere:set", "Set and hold a client in a great power's sphere", G.DIPLOMACY), statecraft.set_sphere, statecraft.SetSphere, free, ("S4.6/RP2",)),
    _sync(Meta("sphere:remove", "Free a client from a sphere", G.DIPLOMACY), statecraft.remove_sphere, statecraft.SphereTarget, free, ("S4.6/RP2",)),
    _sync(
        Meta("council:task", "Set and hold an officer's council task, its target and diligence", G.SOCIETY),
        affairs.set_task,
        affairs.SetTask,
        free,
        ("S4.6/RP2",),
    ),
    _sync(Meta("election:call", "Call an election in a realm at once", G.SOCIETY), affairs.call_election, affairs.CallElection, free, ("S4.6/RP2",)),
    _sync(Meta("election:delete", "Strike an election from the record", G.SOCIETY), affairs.delete_election, affairs.ElectionTarget, free, ("S4.6/RP2",)),
    _sync(Meta("seat:set", "Set and hold a holder's seats and votes in a realm's council", G.SOCIETY), affairs.set_seat, affairs.SetSeat, free, ("S4.6/RP2",)),
    _sync(Meta("seat:remove", "Empty a holder's council seats", G.SOCIETY), affairs.remove_seat, affairs.SeatTarget, free, ("S4.6/RP2",)),
    _sync(Meta("corruption:set", "Set and hold a realm's corruption", G.SOCIETY), affairs.set_corruption, affairs.SetCorruption, free, ("S4.6/RP2",)),
    _sync(
        Meta("tax:set", "Set and hold a realm's tax of one kind: rate, farming and efficiency", G.SOCIETY), affairs.set_tax, affairs.SetTax, free, ("S4.6/RP2",)
    ),
    _sync(Meta("tax:remove", "Return a realm's tax of one kind to custom", G.SOCIETY), affairs.remove_tax, affairs.TaxTarget, free, ("S4.6/RP2",)),
    _sync(Meta("mandate:issue", "Issue a mandate of a realm on one of its lands", G.SOCIETY), affairs.issue_mandate, affairs.IssueMandate, free, ("S4.6/RP2",)),
    _sync(
        Meta("mandate:edit", "Set and hold a mandate's state, deadline and amount", G.SOCIETY), affairs.edit_mandate, affairs.EditMandate, free, ("S4.6/RP2",)
    ),
    _sync(Meta("mandate:delete", "Withdraw a mandate", G.SOCIETY), affairs.delete_mandate, affairs.MandateTarget, free, ("S4.6/RP2",)),
    _sync(Meta("demand:set", "Set and hold a noble's demand and whether it is met", G.SOCIETY), affairs.set_demand, affairs.SetDemand, free, ("S4.6/RP2",)),
    _sync(Meta("demand:remove", "Forget a noble's demand", G.SOCIETY), affairs.remove_demand, affairs.DemandTarget, free, ("S4.6/RP2",)),
    _sync(
        Meta("approval:set", "Set and hold how a class approves of a realm's policies", G.SOCIETY),
        affairs.set_approval,
        affairs.SetApproval,
        free,
        ("S4.6/RP2",),
    ),
    _sync(Meta("approval:remove", "Let a class's approval be weighed anew", G.SOCIETY), affairs.remove_approval, affairs.ApprovalTarget, free, ("S4.6/RP2",)),
    _sync(
        Meta("resolution:propose", "Bring a resolution before an interworld assembly", G.SOCIETY),
        affairs.propose_resolution,
        affairs.ProposeResolution,
        free,
        ("S4.6/RP2",),
    ),
    _sync(
        Meta("resolution:edit", "Set and hold a resolution's state, term and votes", G.SOCIETY),
        affairs.edit_resolution,
        affairs.EditResolution,
        free,
        ("S4.6/RP2",),
    ),
    _sync(
        Meta("resolution:hold", "Hold a resolution as it stands or let it run", G.SOCIETY), affairs.hold_resolution, affairs.HoldResolution, free, ("S4.6/RP2",)
    ),
    _sync(Meta("resolution:delete", "Strike a resolution", G.SOCIETY), affairs.delete_resolution, affairs.ResolutionTarget, free, ("S4.6/RP2",)),
    _sync(Meta("vote:set", "Set and hold a member's vote on a resolution and its weight", G.SOCIETY), affairs.set_vote, affairs.SetVote, free, ("S4.6/RP2",)),
    _sync(Meta("vote:remove", "Strike a member's vote", G.SOCIETY), affairs.remove_vote, affairs.VoteTarget, free, ("S4.6/RP2",)),
    _sync(Meta("court:edit", "Set and hold a court's grandeur and courtiers", G.SOCIETY), affairs.edit_court, affairs.EditCourt, free, ("S4.6/RP2",)),
    _sync(Meta("position:set", "Set and hold who fills a court position", G.SOCIETY), affairs.set_position, affairs.SetPosition, free, ("S4.6/RP2",)),
    _sync(Meta("position:remove", "Strike a court position", G.SOCIETY), affairs.remove_position, affairs.PositionTarget, free, ("S4.6/RP2",)),
    _sync(Meta("site_profit:edit", "Rewrite a ledger entry of profits", G.SOCIETY), industry.edit_site_profit, industry.EditSiteProfit, free, ("S6.3/RP2",)),
    _sync(
        Meta("site_profit:remove", "Strike an entry from the ledger of profits", G.SOCIETY),
        industry.remove_site_profit,
        industry.SiteProfitTarget,
        free,
        ("S6.3/RP2",),
    ),
    _sync(
        Meta("material:create", "Forge a new material in a world", G.WORLDS),
        economy_depth.create_material,
        economy_depth.CreateMaterial,
        free,
        ("F3.1", "F3/RP3"),
    ),
    _sync(
        Meta("material:delete", "Unmake a substance or return a material to the catalog", G.WORLDS),
        economy_depth.delete_material,
        economy_depth.MaterialTarget,
        free,
        ("F3.1",),
    ),
    _sync(Meta("material:hold", "Hold a material's properties", G.WORLDS), economy_depth.hold_material, economy_depth.MaterialTarget, free, ("F3.1",)),
    _sync(Meta("material:release", "Release a held material", G.WORLDS), economy_depth.release_material, economy_depth.MaterialTarget, free, ("F3.1",)),
    _sync(
        Meta("node_material:set", "Make an item, structure, vessel or army of a material", G.ENTITIES),
        economy_depth.set_slot,
        economy_depth.SlotMaterial,
        free,
        ("F3.1",),
    ),
    _sync(Meta("node_material:release", "Release a held material slot", G.ENTITIES), economy_depth.release_slot, economy_depth.SlotTarget, free, ("F3.1",)),
    _sync(
        Meta("node_material:clear", "Clear a material slot so its makers choose anew", G.ENTITIES),
        economy_depth.clear_slot,
        economy_depth.SlotTarget,
        free,
        ("F3.1",),
    ),
    _sync(Meta("stock:set", "Set and hold a store of goods", G.SOCIETY), economy_depth.set_stock, economy_depth.SetStock, free, ("F3.2",)),
    _sync(Meta("stock:release", "Release a held store", G.SOCIETY), economy_depth.release_stock, economy_depth.StockTarget, free, ("F3.2",)),
    _sync(
        Meta("workshop:edit", "Set a workshop's fleet, idleness and building", G.SOCIETY),
        economy_depth.edit_workshop,
        economy_depth.EditWorkshop,
        free,
        ("S6.3",),
    ),
    _sync(Meta("workshop:release", "Release a held workshop", G.SOCIETY), economy_depth.release_workshop, economy_depth.WorkshopTarget, free, ("S6.3",)),
    _sync(
        Meta("workshop_design:create", "Draw a new workshop design", G.SOCIETY),
        economy_depth.create_design,
        economy_depth.CreateWorkshopDesign,
        free,
        ("S6.3",),
    ),
    _sync(Meta("workshop_design:edit", "Redraw a workshop design", G.SOCIETY), economy_depth.edit_design, economy_depth.EditWorkshopDesign, free, ("S6.3",)),
    _sync(
        Meta("workshop_design:release", "Release a held workshop design", G.SOCIETY), economy_depth.release_design, economy_depth.DesignTarget, free, ("S6.3",)
    ),
    _sync(Meta("workshop_design:delete", "Tear up a workshop design", G.SOCIETY), economy_depth.delete_design, economy_depth.DesignTarget, free, ("S6.3",)),
    _sync(Meta("resource:create", "Set a new deposit into the earth", G.SOCIETY), economy_depth.create_resource, economy_depth.CreateResource, free, ("S6.3",)),
    _sync(
        Meta("resource:edit", "Set a resource's knowledge, byproduct, seal and substance", G.SOCIETY),
        economy_depth.edit_resource,
        economy_depth.EditResourceDepth,
        free,
        ("S6.3",),
    ),
    _sync(Meta("resource:mechanic", "Tune a resource's working", G.SOCIETY), economy_depth.set_resource_mechanic, economy_depth.ResourceWorking, free, ()),
    _sync(Meta("resource:release", "Release a held resource", G.SOCIETY), economy_depth.release_resource, economy_depth.ResourceTarget, free, ("S6.3",)),
    _sync(Meta("resource:delete", "Unmake a resource", G.SOCIETY), economy_depth.delete_resource, economy_depth.ResourceTarget, free, ("S6.3",)),
    _sync(Meta("resource:workers", "Set and hold the workers of a resource", G.SOCIETY), economy_depth.set_workers, economy_depth.SetWorkers, free, ("S6.3",)),
    _sync(
        Meta("market:hold_price", "Hold a market's price or supply of a good", G.SOCIETY), economy_depth.hold_price, economy_depth.HoldPrice, free, ("S6.4",)
    ),
    _sync(
        Meta("market:release_price", "Let a held price follow the market again", G.SOCIETY),
        economy_depth.release_price,
        economy_depth.PriceTarget,
        free,
        ("S6.4",),
    ),
    _sync(Meta("currency:create", "Strike a new coin", G.SOCIETY), economy_depth.create_currency, economy_depth.CreateCurrency, free, ("S6.4",)),
    _sync(Meta("currency:release", "Release a held coin", G.SOCIETY), economy_depth.release_currency, economy_depth.CurrencyTarget, free, ("S6.4",)),
    _sync(Meta("currency:delete", "Melt a coin down", G.SOCIETY), economy_depth.delete_currency, economy_depth.CurrencyTarget, free, ("S6.4",)),
    _sync(Meta("loan:grant", "Make a loan", G.SOCIETY), economy_depth.grant_loan, economy_depth.GrantLoan, free, ("S6.4",)),
    _sync(Meta("loan:edit", "Set a loan's terms and hold them", G.SOCIETY), economy_depth.edit_loan, economy_depth.EditLoan, free, ("S6.4",)),
    _sync(Meta("loan:release", "Release a held loan", G.SOCIETY), economy_depth.release_loan, economy_depth.LoanTarget, free, ("S6.4",)),
    _sync(Meta("loan:delete", "Strike a loan from the ledgers", G.SOCIETY), economy_depth.delete_loan, economy_depth.LoanTarget, free, ("S6.4",)),
    _sync(Meta("people:edit", "Edit a people's biology, culture and customs", G.SOCIETY), peoples.edit_people, peoples.EditPeople, free, ("S4.1", "S10.2/RP2")),
    _sync(Meta("people:found", "Found a new people with its own body and customs", G.SOCIETY), peoples.found_people, peoples.FoundPeople, free, ("S4.1",)),
    _sync(Meta("cohort:move", "Move people from one class to another", G.SOCIETY), peoples.move_cohort, peoples.MoveCohort, free, ("F12", "S4.9")),
    _sync(
        Meta("needs:hold", "Hold or release how well a class's need is met", G.SOCIETY), society_depth.hold_need, society_depth.HoldNeed, free, ("F3", "S4.1")
    ),
    _sync(
        Meta("class:standing", "Set a class's wealth, food and needs", G.SOCIETY),
        society_depth.edit_standing,
        society_depth.EditStanding,
        free,
        ("S4.1", "S4.9"),
    ),
    _sync(Meta("labour:set", "Hold or release the workers of a trade", G.SOCIETY), society_depth.set_labour, society_depth.SetLabour, free, ("S4.1", "S4.9")),
    _sync(Meta("labour:corvee", "Impose or lift a corvee", G.SOCIETY), society_depth.set_corvee, society_depth.SetCorvee, free, ("S4.9",)),
    _sync(
        Meta("loyalty:edit", "Set a member's grievances, benefits and loyalty", G.SOCIETY),
        society_depth.edit_loyalty,
        society_depth.EditLoyalty,
        free,
        ("S4.1",),
    ),
    _sync(Meta("drift:impose", "Press an experience on a people's values", G.SOCIETY), society_depth.impose_drift, society_depth.ImposeDrift, free, ("S4.1",)),
    _sync(Meta("drift:edit", "Change a pressure on a people's values", G.SOCIETY), society_depth.edit_drift, society_depth.EditDrift, free, ("S4.1",)),
    _sync(Meta("drift:cancel", "Lift a pressure on a people's values", G.SOCIETY), society_depth.cancel_drift, society_depth.DriftTarget, free, ("S4.1",)),
    _sync(Meta("mobility:ennoble", "Raise a mortal among the nobles", G.SOCIETY), society_depth.ennoble, society_depth.MortalTarget, free, ("S4.9",)),
    _sync(Meta("mobility:ruin", "Ruin a mortal", G.SOCIETY), society_depth.ruin, society_depth.Ruin, free, ("S4.9",)),
    _sync(Meta("mobility:enslave", "Put free people in chains", G.SOCIETY), society_depth.enslave, society_depth.Enslave, free, ("S4.9",)),
    _sync(Meta("mobility:manumit", "Set the bound free", G.SOCIETY), society_depth.manumit, society_depth.Manumit, free, ("S4.9",)),
    _sync(Meta("disease:loose", "Loose a disease on a land or community", G.INTERVENTIONS), disease.loose, disease.Loose, free, ("S3.4",)),
    _sync(Meta("disease:edit", "Edit a disease's nature", G.INTERVENTIONS), disease.edit_disease, disease.EditDisease, free, ("S3.4", "S3.4/RP3")),
    _sync(Meta("disease:cure", "Give or take away the cure of a disease", G.INTERVENTIONS), disease.cure, disease.CureTarget, free, ("S3.4",)),
    _sync(Meta("disease:quarantine", "Seal a land in quarantine or lift it", G.INTERVENTIONS), disease.quarantine, disease.Quarantine, free, ("S3.4",)),
    _sync(Meta("disease:immunity", "Make a community immune to a disease", G.INTERVENTIONS), disease.immunity, disease.Immunity, free, ("S3.4",)),
    _sync(Meta("outbreak:end", "End an outbreak", G.INTERVENTIONS), disease.end_outbreak, disease.OutbreakTarget, free, ("S3.4",)),
    _sync(Meta("disease:create", "Forge a new disease", G.INTERVENTIONS), disease.create_disease, disease.CreateDisease, free, ("S3.4", "F4.6")),
    _sync(Meta("outbreak:edit", "Edit an outbreak's severity, toll and seal", G.INTERVENTIONS), disease.edit_outbreak, disease.EditOutbreak, free, ("S3.4",)),
    _sync(Meta("endemic:set", "Make a disease endemic in a land or set its load", G.INTERVENTIONS), disease.set_endemic, disease.Endemic, free, ("S3.4",)),
    _sync(Meta("endemic:remove", "Free a land of an endemic disease", G.INTERVENTIONS), disease.remove_endemic, disease.EndemicTarget, free, ("S3.4",)),
    _sync(Meta("cohort:set", "Set the headcount of one cohort", G.SOCIETY), peoples.set_cohort, peoples.SetCohort, free, ("F12",)),
    _sync(Meta("mortal:dormancy", "Wake or doze a named mortal, or hold it so", G.SOCIETY), peoples.set_dormancy, peoples.Dormancy, free, ("F12",)),
    _sync(Meta("settlement:edit", "Edit a settlement's order, treasury and works", G.SOCIETY), urban.edit_settlement, urban.EditSettlement, free, ("S4.2",)),
    _sync(Meta("district:build", "Build or enlarge a district", G.SOCIETY), urban.build_district, urban.BuildDistrict, free, ("S4.2",)),
    _sync(Meta("district:edit", "Edit a district", G.SOCIETY), urban.edit_district, urban.EditDistrict, free, ("S4.2",)),
    _sync(Meta("district:move", "Move a district to another hex of its town", G.SOCIETY), urban.move_district, urban.MoveDistrict, free, ("S4.2",)),
    _sync(Meta("district:raze", "Raze a district", G.SOCIETY), urban.raze_district, urban.DistrictTarget, free, ("S4.2",)),
    _sync(Meta("settlement:tax", "Set a settlement's tax", G.SOCIETY), urban.set_tax, urban.SetTax, free, ("S4.2",)),
    _sync(Meta("settlement:free_city", "Declare a free city or bind it again", G.SOCIETY), urban.free_city, urban.FreeCity, free, ("S4.2",)),
    _sync(Meta("settlement:charter", "Grant a settlement a charter", G.SOCIETY), urban.grant_charter, urban.Charter, free, ("S4.2",)),
    _sync(
        Meta("settlement:foreigners", "Set the foreign peoples living in a settlement", G.SOCIETY), urban.set_foreigners, urban.SetForeigners, free, ("S4.2",)
    ),
    _sync(Meta("district:design", "Design a new kind of district on a base kind", G.SOCIETY), urban.design_district, urban.DesignDistrict, free, ("S4.2",)),
    _sync(Meta("district:design_edit", "Rework a district design", G.SOCIETY), urban.edit_design, urban.EditDesign, free, ("S4.2",)),
    _sync(Meta("district:design_delete", "Strike a district design", G.SOCIETY), urban.delete_design, urban.DesignTarget, free, ("S4.2",)),
    _sync(Meta("polity:edit", "Edit a realm's government, legitimacy and treasury", G.SOCIETY), realms.edit_polity, realms.EditPolity, free, ("S4.6",)),
    _sync(Meta("polity:appoint", "Appoint or dismiss an officer", G.SOCIETY), realms.appoint, realms.Appoint, free, ("S4.6",)),
    _sync(Meta("polity:depose", "Depose a ruler", G.SOCIETY), realms.depose, realms.PolityTarget, free, ("S4.6",)),
    _sync(Meta("polity:split", "Split lands off a realm", G.SOCIETY), realms.split, realms.Split, free, ("S4.6",)),
    _sync(Meta("polity:merge", "Merge one realm into another", G.SOCIETY), realms.merge, realms.Merge, free, ("S4.6",)),
    _sync(Meta("polity:independence", "Free a realm from its overlord", G.SOCIETY), realms.independence, realms.PolityTarget, free, ("S4.6",)),
    _sync(Meta("polity:found", "Found a realm on a settlement or people", G.SOCIETY), realms.found_realm, realms.FoundRealm, free, ("S4.6",)),
    _sync(Meta("polity:dissolve", "Dissolve a realm", G.SOCIETY), realms.dissolve_realm, realms.PolityTarget, free, ("S4.6",)),
    _sync(Meta("polity:member", "Set a member land's autonomy or release it", G.SOCIETY), realms.edit_member, realms.EditMember, free, ("S4.6",)),
    _sync(Meta("polity:territory", "Set a held land's control and province", G.SOCIETY), realms.edit_territory, realms.EditTerritory, free, ("S4.6",)),
    _sync(Meta("office:create", "Create an office with its powers", G.SOCIETY), realms.create_office, realms.CreateOffice, free, ("S4.6",)),
    _sync(Meta("office:edit", "Edit an office's title, powers, seat and holder", G.SOCIETY), realms.edit_office, realms.EditOffice, free, ("S4.6",)),
    _sync(Meta("office:abolish", "Abolish an office", G.SOCIETY), realms.abolish_office, realms.OfficeTarget, free, ("S4.6",)),
    _sync(Meta("claim:edit", "Edit a claim to a throne", G.SOCIETY), realms.edit_claim, realms.EditClaim, free, ("S4.7",)),
    _sync(Meta("claim:revoke", "Void a claim to a throne", G.SOCIETY), realms.revoke_claim, realms.ClaimTarget, free, ("S4.7",)),
    _sync(Meta("mortal:repute", "Set a mortal's honour and infamy", G.SOCIETY), realms.edit_repute, realms.EditRepute, free, ("S4.6",)),
    _sync(Meta("polity:loan", "Have a lender lend to a realm", G.SOCIETY), realms.lend, realms.Lend, free, ("S4.6",)),
    _sync(Meta("law:enact", "Lay down a law", G.SOCIETY), realms.enact_law, realms.EnactLaw, free, ("S4.5",)),
    _sync(Meta("law:repeal", "Repeal a law", G.SOCIETY), realms.repeal_law, realms.LawTarget, free, ("S4.5",)),
    _sync(Meta("law:edit", "Rewrite a law", G.SOCIETY), realms.edit_law, realms.EditLaw, free, ("S4.5",)),
    _sync(Meta("law:protect", "Hold a law against repeal or change, or release it", G.SOCIETY), realms.protect_law, realms.ProtectLaw, free, ("S4.5",)),
    _sync(Meta("house:found", "Found a house", G.SOCIETY), realms.found_house, realms.FoundHouse, free, ("S4.7",)),
    _sync(Meta("house:merge", "Merge two houses", G.SOCIETY), realms.merge_house, realms.MergeHouse, free, ("S4.7",)),
    _sync(Meta("house:extinguish", "Extinguish a house", G.SOCIETY), realms.extinguish_house, realms.HouseTarget, free, ("S4.7",)),
    _sync(
        Meta("house:edit", "Edit a house's head, prestige, wealth, motto, bloodline and seats", G.SOCIETY), realms.edit_house, realms.EditHouse, free, ("S4.7",)
    ),
    _sync(Meta("house:member", "Add a mortal to a house or strike them from it", G.SOCIETY), realms.house_member, realms.HouseMember, free, ("S4.7",)),
    _sync(Meta("house:heirloom", "Make an item a house heirloom or take it away", G.SOCIETY), realms.house_heirloom, realms.HouseHeirloom, free, ("S4.7",)),
    _sync(Meta("claim:grant", "Grant a claim to a throne", G.SOCIETY), realms.grant_claim, realms.GrantClaim, free, ("S4.7",)),
    _sync(Meta("treaty:sign", "Seal a treaty", G.SOCIETY), realms.sign_treaty, realms.SignTreaty, free, ("S5.13",)),
    _sync(Meta("treaty:break", "Break a treaty", G.SOCIETY), realms.break_treaty, realms.BreakTreaty, free, ("S5.13",)),
    _sync(Meta("treaty:edit", "Change a treaty's term or standing", G.SOCIETY), realms.edit_treaty, realms.EditTreaty, free, ("S5.13",)),
    _sync(Meta("treaty:clause_add", "Add a clause to a treaty", G.SOCIETY), realms.add_clause, realms.AddClause, free, ("S5.13",)),
    _sync(Meta("treaty:clause_edit", "Rewrite a treaty clause", G.SOCIETY), realms.edit_clause, realms.EditClause, free, ("S5.13",)),
    _sync(Meta("treaty:clause_remove", "Strike a clause from a treaty", G.SOCIETY), realms.remove_clause, realms.ClauseTarget, free, ("S5.13",)),
    _sync(Meta("treaty:party_add", "Bind another party or guarantor to a treaty", G.SOCIETY), realms.add_party, realms.TreatyPartyChange, free, ("S5.13",)),
    _sync(Meta("treaty:party_remove", "Release a party from a treaty", G.SOCIETY), realms.remove_party, realms.TreatyPartyTarget, free, ("S5.13",)),
    _sync(Meta("vassal:create", "Make one realm the vassal of another", G.SOCIETY), realms.create_vassalage, realms.CreateVassalage, free, ("S4.6",)),
    _sync(
        Meta("vassal:edit", "Set a subject's kind, tribute, levies, loyalty, wish for liberty and contract rights", G.SOCIETY),
        realms.edit_vassalage,
        realms.EditVassalage,
        free,
        ("S4.6", "S4.6/RP2"),
    ),
    _sync(Meta("oath:swear", "Have a mortal swear an oath", G.SOCIETY), realms.swear_oath, realms.SwearOath, free, ("S4.8",)),
    _sync(Meta("oath:break", "Break an oath", G.SOCIETY), realms.break_oath, realms.OathTarget, free, ("S4.8",)),
    _sync(Meta("oath:edit", "Change an oath's deadline, words, recipient or witness", G.SOCIETY), realms.edit_oath, realms.EditOath, free, ("S4.8",)),
    _sync(Meta("oath:release", "Release a mortal from an oath with honour", G.SOCIETY), realms.release_oath, realms.OathTarget, free, ("S4.8",)),
    _sync(Meta("army:edit", "Edit an army's stance, supplies, chest and camp", G.WARFARE), military.edit_army, military.EditArmy, free, ("S5.1",)),
    _sync(Meta("army:command", "Command an army's stance, march and target", G.WARFARE), military.command_army, military.CommandArmy, free, ("S5.1",)),
    _sync(Meta("army:edit_stack", "Edit a unit stack", G.WARFARE), military.edit_stack, military.EditStack, free, ("S5.1",)),
    _sync(Meta("army:add_stack", "Add a unit stack to an army", G.WARFARE), military.add_stack, military.AddStack, free, ("S5.1",)),
    _sync(Meta("army:remove_stack", "Strike a stack from an army", G.WARFARE), military.remove_stack, military.StackTarget, free, ("S5.1",)),
    _sync(Meta("siege:edit", "Edit a siege's stores, walls and sickness", G.WARFARE), military.edit_siege, military.EditSiege, free, ("S5.4",)),
    _sync(Meta("war:aim", "Set or change a war aim", G.WARFARE), military.set_aim, military.SetAim, free, ("S5.8",)),
    _sync(Meta("war:drop_aim", "Abandon a war aim", G.WARFARE), military.drop_aim, military.AimTarget, free, ("S5.8",)),
    _sync(Meta("war:impose_peace", "Impose peace terms", G.WARFARE), military.impose_peace, military.ImposePeace, free, ("S5.8",)),
    _sync(Meta("war:call_allies", "Call allies to war", G.WARFARE), military.call_allies, military.CallAllies, free, ("S5.8",)),
    _sync(Meta("war:weariness", "Set a side's war weariness", G.WARFARE), military.set_weariness, military.Weariness, free, ("S5.8",)),
    _sync(Meta("war:edit_side", "Set and hold a side's weariness and war support", G.WARFARE), military.edit_side, military.EditSide, free, ("S5.8/RP2",)),
    _sync(Meta("war:separate_peace", "Have an ally make a separate peace", G.WARFARE), military.separate_peace, military.SideTarget, free, ("S5.8/RP2",)),
    _sync(Meta("occupation:edit", "Edit or end an occupation", G.WARFARE), military.edit_occupation, military.EditOccupation, free, ("S5.8",)),
    _sync(Meta("captives:settle", "Decide the fate of captives", G.WARFARE), military.settle_captives, military.SettleCaptives, free, ("S5.7",)),
    _sync(Meta("commander:trait", "Give or take a battle trait", G.WARFARE), military.commander_trait, military.CommanderTraitOrder, free, ("S5.1",)),
    _sync(Meta("spy:edit_network", "Edit or roll up a spy network", G.WARFARE), military.edit_network, military.EditNetwork, free, ("S5.10",)),
    _sync(
        Meta(
            "military:create",
            "Create a military record: design, stack, officer, contract, siege, aim, captives, spy network or agent, feud, army template",
            G.WARFARE,
        ),
        military_depth.create,
        military_depth.RecordCreate,
        free,
        ("S5.1", "S5.4", "S5.7", "S5.9", "S5.10", "S5.8/RP2"),
    ),
    _sync(
        Meta("military:edit", "Edit and hold any value of a military record", G.WARFARE),
        military_depth.edit,
        military_depth.RecordEdit,
        free,
        ("S5.1", "S5.4", "S5.7", "S5.8", "S5.9", "S5.10", "S7.3"),
    ),
    _sync(
        Meta("military:release", "Release held values of a military record", G.WARFARE),
        military_depth.release,
        military_depth.RecordRelease,
        free,
        ("S5.1", "S5.4", "S5.7", "S5.8", "S5.9", "S5.10", "S7.3"),
    ),
    _sync(
        Meta("military:delete", "Strike out a military record", G.WARFARE),
        military_depth.delete,
        military_depth.RecordDelete,
        free,
        ("S5.1", "S5.4", "S5.7", "S5.8", "S5.9", "S5.10"),
    ),
    _sync(
        Meta("army:raise", "Raise an army for a community, in war or in peace", G.WARFARE), military_depth.raise_army, military_depth.RaiseArmy, free, ("S5.1",)
    ),
    _sync(
        Meta("army:assign", "Set an army's commander and the community it serves", G.WARFARE),
        military_depth.assign,
        military_depth.ArmyCommand,
        free,
        ("S5.1",),
    ),
    _sync(Meta("war:battle_at", "Force a battle at a chosen region", G.WARFARE), military_depth.battle_at, military_depth.BattleAt, free, ("S5.2", "S5.3")),
    _sync(Meta("siege:start", "Lay siege to a settlement with an army", G.WARFARE), military_depth.siege_start, military_depth.SiegeStart, free, ("S5.4",)),
    _sync(Meta("war:declare", "Declare a war with a cause and its aims", G.WARFARE), military_depth.declare, military_depth.DeclareWar, free, ("S5.8",)),
    _sync(Meta("war:peace", "Make peace with chosen terms and clauses", G.WARFARE), military_depth.peace, military_depth.PeaceBuild, free, ("S5.8",)),
    _sync(
        Meta("vessel:create", "Lay down a new vessel to a hull design", G.WARFARE), military_depth.vessel_create, military_depth.VesselOrder, free, ("S7.3",)
    ),
    _sync(
        Meta("vessel:refit", "Refit a vessel to another hull, arms and materials", G.WARFARE),
        military_depth.vessel_refit,
        military_depth.VesselRefit,
        free,
        ("S7.3",),
    ),
    _sync(Meta("vessel:repair", "Repair a vessel at its home shipyard", G.WARFARE), military_depth.vessel_repair, military_depth.VesselTarget, free, ("S7.3",)),
    _sync(Meta("captive:take", "Take a named mortal captive", G.WARFARE), military_depth.captive_take, military_depth.CaptiveTake, free, ("S5.7",)),
    _sync(
        Meta("war:ordeal", "Order an ordeal: an honour duel, a trial by combat or a duel of gods' champions", G.WARFARE),
        military_depth.ordeal,
        military_depth.Ordeal,
        free,
        ("S5.6",),
    ),
    _sync(Meta("cult:doctrine", "Edit a faith's orthodoxy, tithes, clergy and judgement", G.SOCIETY), faith.edit_doctrine, faith.EditDoctrine, free, ("S4.4",)),
    _sync(
        Meta("cult:reset_doctrine", "Unwrite a faith's doctrine and let it be taught anew", G.SOCIETY), faith.reset_doctrine, faith.CultTarget, free, ("S4.4",)
    ),
    _sync(Meta("cult:tenet", "Add, rename or remove a tenet", G.SOCIETY), faith.set_tenet, faith.SetTenet, free, ("S4.4",)),
    _sync(Meta("cult:office", "Appoint, hold, vacate or strike a clergy office", G.SOCIETY), faith.set_office, faith.SetOffice, free, ("S4.4",)),
    _sync(Meta("cult:holding", "Grant or take a faith's holding", G.SOCIETY), faith.set_holding, faith.SetHolding, free, ("S4.4",)),
    _sync(Meta("cult:heresy", "Declare a heresy", G.SOCIETY), faith.declare_heresy, faith.DeclareHeresy, free, ("S4.4",)),
    _sync(Meta("cult:judge_heresy", "Hunt or suffer a heresy", G.SOCIETY), faith.judge_heresy, faith.JudgeHeresy, free, ("S4.4",)),
    _sync(Meta("cult:edit_heresy", "Edit a heresy's distance, hunting and tolerance", G.SOCIETY), faith.edit_heresy, faith.EditHeresy, free, ("S4.4",)),
    _sync(Meta("cult:undeclare_heresy", "Forgive a heresy and unname it", G.SOCIETY), faith.undeclare_heresy, faith.HeresyTarget, free, ("S4.4",)),
    _sync(Meta("cult:canonise", "Canonise a saint", G.SOCIETY), faith.canonise, faith.Canonise, free, ("S4.4",)),
    _sync(Meta("relic:edit", "Edit a relic's sanctity, pilgrims, shrine and keepers", G.SOCIETY), faith.edit_relic, faith.EditRelic, free, ("S4.4",)),
    _sync(Meta("relic:remove", "Strip a relic of its holiness", G.SOCIETY), faith.remove_relic, faith.RelicTarget, free, ("S4.4",)),
    _sync(Meta("soul:raise", "Call up the soul of a dead mortal", G.BEYOND), faith.raise_soul, faith.RaiseSoul, free, ("S3.3",)),
    _sync(Meta("soul:judge", "Judge a soul", G.BEYOND), faith.judge_soul, faith.JudgeSoul, free, ("S3.3",)),
    _sync(Meta("soul:release", "Release a soul", G.BEYOND), faith.release_soul, faith.SpiritTarget, free, ("S3.3",)),
    _sync(Meta("soul:bind", "Bind or loose a spirit", G.BEYOND), faith.bind_spirit, faith.BindSpirit, free, ("S3.3",)),
    _sync(Meta("soul:seal", "Seal a soul against rebirth", G.BEYOND), faith.seal_soul, faith.SealSoul, free, ("S3.3",)),
    _sync(Meta("soul:reincarnate", "Reincarnate a soul", G.BEYOND), faith.reincarnate, faith.Reincarnate, free, ("S3.3",)),
    _sync(Meta("soul:edit", "Edit a spirit's ledger, imprint, rite, state, patron and temper", G.BEYOND), faith.edit_spirit, faith.EditSpirit, free, ("S3.3",)),
    _sync(Meta("soul:reread_deeds", "Read a soul's deeds again from its life", G.BEYOND), faith.reread_deeds, faith.SpiritTarget, free, ("S3.3",)),
    _sync(Meta("soul:possess", "Set a spirit upon a living host", G.BEYOND), faith.possess, faith.Possess, free, ("S3.3",)),
    _sync(Meta("soul:possession", "Edit a possession's stress", G.BEYOND), faith.edit_possession, faith.EditPossession, free, ("S3.3",)),
    _sync(Meta("soul:exorcise", "Drive a possessing spirit out", G.BEYOND), faith.exorcise, faith.HostTarget, free, ("S3.3",)),
    _sync(Meta("afterlife:stratum", "Raise, edit or unmake a stratum of the afterlife", G.BEYOND), faith.set_stratum, faith.SetStratum, free, ("S3.3",)),
)


LORE_ACTIONS = (
    _sync(
        Meta("lore:edit", "Edit a language, legend, tradition, creed, rite, prophecy, item or artwork", G.LANGUAGES),
        lore.edit_lore,
        lore.EditLore,
        free,
        ("S8.1", "S8.2", "S8.3", "S8.5", "S8.6", "S8.7", "S7.1", "S7.4"),
    ),
    _sync(
        Meta("language:intelligibility", "Set how well two tongues understand each other", G.LANGUAGES),
        lore.set_intelligibility,
        lore.Intelligibility,
        free,
        ("S8.1",),
    ),
    _sync(Meta("language:speakers", "Set the speakers of a tongue in a community", G.LANGUAGES), lore.set_speakers, lore.Speakers, free, ("S8.1",)),
    _sync(
        Meta("language:register", "Set or hold the tongue of a court, faith, market or hearth", G.LANGUAGES),
        culture.set_register,
        culture.Register,
        free,
        ("S8.1",),
    ),
    _sync(
        Meta("language:release_understanding", "Let the world measure two tongues again", G.LANGUAGES),
        culture.release_understanding,
        culture.PairTarget,
        free,
        ("S8.1",),
    ),
    _sync(
        Meta("language:release_speakers", "Let a community's share of speakers move again", G.LANGUAGES),
        culture.release_speakers,
        culture.SpeakerTarget,
        free,
        ("S8.1",),
    ),
    _sync(Meta("research:level", "Set a people's level in a branch of knowledge", G.SOCIETY), lore.set_level, lore.HolderLevel, free, ("S8.4",)),
    _sync(Meta("research:technique", "Give or take a technique", G.SOCIETY), lore.set_technique, lore.HolderTechnique, free, ("S8.4",)),
    _sync(Meta("research:focus", "Choose what a people's scholars work on", G.SOCIETY), lore.set_focus, lore.ResearchFocus, free, ("S8.4",)),
    _sync(Meta("research:institution", "Found, shape or remove an institution", G.SOCIETY), lore.set_institution, lore.Institution, free, ("S8.4",)),
    _sync(Meta("research:boost", "Grant a boost toward a technique", G.SOCIETY), lore.grant_boost, lore.GrantBoost, free, ("S8.4",)),
    _sync(Meta("research:boost_edit", "Rewrite a research boost", G.SOCIETY), lore.edit_boost, lore.EditBoost, free, ("S8.4",)),
    _sync(Meta("research:boost_remove", "Strike a research boost", G.SOCIETY), lore.remove_boost, lore.BoostTarget, free, ("S8.4",)),
    _sync(Meta("discovery:raise_great", "Raise a mortal as a great person", G.SOCIETY), discovery.raise_great, discovery.RaiseGreat, free, ("S8.4",)),
    _sync(Meta("discovery:era", "Set a realm's era score and age", G.SOCIETY), discovery.set_era, discovery.SetEra, free, ("S8.4",)),
    _sync(Meta("discovery:world_era", "Set the era of a world", G.SOCIETY), discovery.set_world_era, discovery.SetWorldEra, free, ("S8.4",)),
    _sync(
        Meta("discovery:incident", "Strike a community with a research incident", G.SOCIETY), discovery.cause_incident, discovery.CauseIncident, free, ("S8.4",)
    ),
    _sync(
        Meta("discovery:design", "Grant a design of a ship, engine, building or pattern", G.SOCIETY),
        discovery.grant_design,
        discovery.GrantDesign,
        free,
        ("S8.4",),
    ),
    _sync(Meta("discovery:ban", "Ban or allow a work in a realm", G.SOCIETY), discovery.ban_work, discovery.BanWork, free, ("S8.4",)),
    _sync(Meta("theory:adherent", "Make a community or mortal hold a theory", G.SOCIETY), theories.set_adherent, theories.TheoryAdherent, free, ("S8.4b",)),
    _sync(Meta("theory:anomaly", "Lay an anomaly against a theory", G.SOCIETY), theories.add_anomaly, theories.TheoryAnomaly, free, ("S8.4b",)),
    _sync(Meta("theory:reveal", "Make the truth of a theory known", G.SOCIETY), theories.reveal_truth, theories.RevealTruth, free, ("S8.4b",)),
    _sync(Meta("art_form:practitioner", "Spread an art form or set its mastery", G.SOCIETY), theories.set_practitioner, theories.Practitioner, free, ("S7.5",)),
    _sync(
        Meta("research:holder", "Set a people's standing in a branch", G.SOCIETY),
        lore.edit_holder,
        lore.EditHolder,
        free,
        ("S8.4",),
    ),
    _sync(
        Meta("research:custom_technique", "Give or take a technique of your own making", G.SOCIETY),
        lore.set_custom_technique,
        lore.HolderCustomTechnique,
        free,
        ("S8.4",),
    ),
    _sync(Meta("creed:tenet", "Add or remove a creed's tenet", G.SOCIETY), lore.set_creed_tenet, lore.CreedTenet, free, ("S8.5",)),
    _sync(Meta("creed:adherent", "Set a community's adherence to a creed", G.SOCIETY), lore.set_adherent, lore.Adherent, free, ("S8.5",)),
    _sync(Meta("creed:found", "Let a mortal found a creed", G.SOCIETY), lore.found_creed, lore.FoundCreed, free, ("S8.5",)),
    _sync(
        Meta("creed:custom_tenet", "Give or take a tenet of your own", G.SOCIETY),
        lore.set_custom_tenet,
        lore.CreedCustomTenet,
        free,
        ("S8.5",),
    ),
    _sync(Meta("creed:suppress", "Suppress a creed", G.SOCIETY), lore.suppress_creed, lore.SuppressCreed, free, ("S8.5",)),
    _sync(Meta("rite:devise", "Let a mortal devise a rite", G.BEYOND), lore.devise_rite, lore.DeviseRite, free, ("S8.6",)),
    _sync(Meta("rite:effect", "Set what a rite does", G.BEYOND), lore.set_rite_effect, lore.RiteEffect, free, ("S8.6",)),
    _sync(Meta("rite:cast", "Work a rite now", G.BEYOND), lore.cast_rite, lore.CastRite, free, ("S8.6",)),
    _sync(Meta("rite:teach", "Teach a rite to a mortal, people or cult, or make them forget it", G.BEYOND), lore.teach_rite, lore.TeachRite, free, ("S8.6",)),
    _sync(Meta("rite:forbid", "Forbid a rite in a realm, cult or people, or lift the ban", G.BEYOND), lore.forbid_rite, lore.ForbidRite, free, ("S8.6",)),
    _sync(Meta("rite:dispel", "Undo the last working of a rite", G.BEYOND), lore.dispel_rite, lore.RiteTarget, free, ("S8.6",)),
    _sync(Meta("rite:requirements", "Set what a rite asks of its caster", G.BEYOND), lore.set_rite_requirements, lore.RiteRequirements, free, ("S8.6",)),
    _sync(Meta("prophecy:resolve", "Fulfil or fail a prophecy", G.MEMORY), lore.resolve_prophecy, lore.ResolveProphecy, free, ("S8.7",)),
    _sync(Meta("item:enchant", "Set an enchantment on an item", G.BEYOND), lore.set_enchantment, lore.Enchantment, free, ("S7.1", "S8.6")),
    _sync(
        Meta("tradition:participation", "Set how fully a community keeps a tradition", G.SOCIETY), lore.set_participation, lore.Participation, free, ("S8.3",)
    ),
    _sync(
        Meta("tradition:release_participation", "Let a community's keeping of a tradition move again", G.SOCIETY),
        culture.release_participation,
        culture.KeeperTarget,
        free,
        ("S8.3",),
    ),
    _sync(
        Meta("tradition:effect", "Set what a tradition brings its keepers", G.SOCIETY),
        culture.set_tradition_effect,
        culture.TraditionEffect,
        free,
        ("S8.3",),
    ),
    _sync(
        Meta("tradition:reseed", "Draw a tradition's effects again from its kind", G.SOCIETY),
        culture.reseed_tradition,
        culture.TraditionTarget,
        free,
        ("S8.3",),
    ),
    _sync(
        Meta("lore:create", "Make a new language, legend, tradition, creed, rite, prophecy, item, artwork, knowledge, theory or art form", G.LANGUAGES),
        lore.create_lore,
        lore.CreateLore,
        free,
        ("S8.1", "S8.2", "S8.3", "S8.4", "S8.5", "S8.6", "S8.7", "S7.1", "S7.4"),
    ),
    _sync(
        Meta("kind:create", "Name a new kind of technique, tenet, tradition, tale, item or working", G.LANGUAGES),
        lore.create_kind,
        lore.CreateKind,
        free,
        ("S8.2", "S8.3", "S8.4", "S8.5", "S8.6", "S7.1"),
    ),
    _sync(
        Meta("kind:edit", "Reshape a kind of your own making", G.LANGUAGES),
        lore.edit_kind,
        lore.EditKind,
        free,
        ("S8.2", "S8.3", "S8.4", "S8.5", "S8.6", "S7.1"),
    ),
    _sync(
        Meta("kind:delete", "Unmake a kind of your own making", G.LANGUAGES),
        lore.delete_kind,
        lore.KindTarget,
        free,
        ("S8.2", "S8.3", "S8.4", "S8.5", "S8.6", "S7.1"),
    ),
)


WILDS_ACTIONS = (
    _sync(
        Meta("species:edit", "Edit a kind's body, diet, habitat, temper and domestication", G.CREATURES), wilds.edit_species, wilds.EditSpecies, free, ("S3.2",)
    ),
    _sync(Meta("species:range", "Set how a kind ranges in a land", G.CREATURES), wilds.edit_range, wilds.EditRange, free, ("S3.2",)),
    _sync(Meta("species:move_range", "Move a kind's herds to another land", G.CREATURES), wilds.move_range, wilds.MoveRange, free, ("S3.2",)),
    _sync(Meta("species:drop_range", "Drive a kind out of a land", G.CREATURES), wilds.drop_range, wilds.DropRange, free, ("S3.2",)),
    _sync(Meta("species:yield", "Set what a kind yields", G.CREATURES), wilds.set_yield, wilds.SpeciesYield, free, ("S3.2",)),
    _sync(Meta("species:use", "Set what a kind is kept for", G.CREATURES), wilds.set_use, wilds.Use, free, ("S3.2",)),
    _sync(Meta("species:host", "Set a sickness a kind carries", G.CREATURES), wilds.set_host, wilds.Host, free, ("S3.2",)),
    _sync(Meta("species:sacred", "Make a kind sacred to a son", G.CREATURES), wilds.make_sacred, wilds.Sacred, free, ("S3.2",)),
    _sync(Meta("species:domesticate", "Domesticate a kind now", G.CREATURES), wilds.domesticate, wilds.Domesticate, free, ("S3.2",)),
    _sync(Meta("herd:edit", "Edit a community's herd", G.CREATURES), wilds.edit_herd, wilds.EditHerd, free, ("S3.2",)),
    _sync(Meta("beast:edit", "Edit a named beast", G.CREATURES), wilds.edit_beast, wilds.EditBeast, free, ("S3.3a",)),
    _sync(Meta("beast:rouse", "Wake or lull a beast", G.CREATURES), wilds.rouse, wilds.Rouse, free, ("S3.3a",)),
    _sync(Meta("beast:bind", "Bind or loose a beast", G.CREATURES), wilds.bind, wilds.Bind, free, ("S3.3a",)),
    _sync(Meta("beast:lair", "Shift a beast's lair", G.CREATURES), wilds.shift_lair, wilds.Lair, free, ("S3.3a",)),
    _sync(Meta("beast:spawn", "Raise a named beast from a kind", G.CREATURES), wilds.spawn, wilds.Spawn, free, ("S3.3a",)),
    _sync(Meta("species:create", "Create a new kind with a chosen nature", G.CREATURES), wilds.create_species, wilds.CreateSpecies, free, ("S3.2",)),
    _sync(Meta("species:prey", "Set what a kind hunts", G.CREATURES), wilds.set_prey, wilds.Prey, free, ("S3.2",)),
    _sync(Meta("species:custom_use", "Keep a kind in a way of your own", G.CREATURES), wilds.set_custom_use, wilds.CustomUse, free, ("S3.2",)),
    _sync(Meta("use_kind:create", "Devise a new way of keeping beasts", G.CREATURES), wilds.create_use_kind, wilds.NewUseKind, free, ("S3.2",)),
    _sync(Meta("use_kind:edit", "Reshape a way of keeping beasts", G.CREATURES), wilds.edit_use_kind, wilds.EditUseKind, free, ("S3.2",)),
    _sync(Meta("use_kind:drop", "Forget a way of keeping beasts", G.CREATURES), wilds.drop_use_kind, wilds.UseKindTarget, free, ("S3.2",)),
    _sync(Meta("herd:drop", "Scatter a community's herd", G.CREATURES), wilds.drop_herd, wilds.HerdTarget, free, ("S3.2",)),
    _sync(Meta("people:totem", "Set or clear a people's totem kind", G.CREATURES), wilds.set_totem, wilds.Totem, free, ("S3.2",)),
    _sync(Meta("beast:create", "Call forth a new named beast", G.CREATURES), wilds.create_beast, wilds.CreateBeast, free, ("S3.3a",)),
    _sync(Meta("beast:slay", "Slay a named beast", G.CREATURES), wilds.slay, wilds.Slay, free, ("S3.3a",)),
    _sync(Meta("beast:treasure", "Lay an item in a beast's hoard or take it out", G.CREATURES), wilds.move_treasure, wilds.Treasure, free, ("S3.3a",)),
    _sync(
        Meta("anatomy:edit", "Shape a kind's or a beast's body, attacks and nature", G.CREATURES), wilds.edit_anatomy, wilds.EditAnatomy, free, ("S3.3a/RP2",)
    ),
    _sync(Meta("anatomy:reroll", "Let the world shape a body anew", G.CREATURES), wilds.reroll_anatomy, wilds.AnatomyTarget, free, ("S3.3a/RP2",)),
    _sync(Meta("pet:set", "Make a beast a mortal's pet or set it free", G.CREATURES), wilds.set_pet, wilds.PetOwner, free, ("S3.3a/RP2",)),
    _sync(Meta("pet:give", "Give a mortal a pet of a kind", G.CREATURES), wilds.give_pet, wilds.PetGift, free, ("S3.3a/RP2",)),
    _sync(Meta("plant:edit", "Edit a plant's growth, soil and cultivation", G.CREATURES), flora.edit_plant, flora.EditPlant, free, ("S3.2/RP2",)),
    _sync(Meta("crop:set", "Sow a crop in a land or set its share of the fields", G.CREATURES), flora.set_crop, flora.SetCrop, free, ("S3.2/RP2",)),
    _sync(Meta("crop:drop", "Clear a crop from a land's fields", G.CREATURES), flora.drop_crop, flora.CropTarget, free, ("S3.2/RP2",)),
    _sync(Meta("crop_pest:set", "Set or clear a pest that feeds on a crop", G.CREATURES), flora.set_crop_pest, flora.CropPest, free, ("S3.2/RP2",)),
    _sync(Meta("world:life", "Set which kinds of life a world can bear", G.WORLDS), flora.set_world_life, flora.WorldLife, free, ("S3.2/RP2",)),
)

REGION_ACTIONS = (
    _sync(
        Meta("environment:biome", "Set the share of a biome in a region's land", G.WORLDS), environment.set_region_biome, environment.SetBiome, free, ("F2.1",)
    ),
    _sync(Meta("region:danger_create", "Set a danger of any kind upon a region", G.WORLDS), regions.create_danger, regions.CreateDanger, free, ("S6.1",)),
    _sync(Meta("region:danger_edit", "Change or hold the strength of a region's danger", G.WORLDS), regions.edit_danger, regions.EditDanger, free, ("S6.1",)),
    _sync(Meta("region:danger_release", "Let a held danger follow the land again", G.WORLDS), regions.release_danger, regions.DangerTarget, free, ("S6.1",)),
    _sync(Meta("region:danger_delete", "Drive a danger out of a region", G.WORLDS), regions.delete_danger, regions.DangerTarget, free, ("S6.1",)),
    _sync(Meta("region:sanctify", "Sanctify a region and set its sacredness", G.WORLDS), regions.sanctify, regions.Sanctify, free, ("S6.1",)),
    _sync(Meta("region:memory_add", "Write an event into a region's memory", G.WORLDS), regions.add_memory, regions.AddMemory, free, ("S6.1",)),
    _sync(Meta("region:memory_edit", "Reshape or hold a region's memory", G.WORLDS), regions.edit_memory, regions.EditMemory, free, ("S6.1",)),
    _sync(Meta("region:memory_delete", "Make a region forget an event", G.WORLDS), regions.delete_memory, regions.MemoryTarget, free, ("S6.1",)),
    _sync(Meta("region:knowledge_set", "Reveal or hide a region on a realm's maps", G.WORLDS), regions.set_knowledge, regions.SetKnowledge, free, ("S6.1",)),
    _sync(
        Meta("region:knowledge_release", "Let a realm's map of a region follow its explorers again", G.WORLDS),
        regions.release_knowledge,
        regions.KnowledgeTarget,
        free,
        ("S6.1",),
    ),
    _sync(Meta("region:river_redirect", "Turn a river into a neighbouring region", G.WORLDS), regions.redirect_river, regions.RedirectRiver, free, ("S6.1",)),
)

ENVIRONMENT_ACTIONS = (
    _sync(
        Meta("ley:sever", "Cut a ley line for some epochs", G.WORLDS),
        environment.sever_ley_line,
        environment.SeverLey,
        free,
        ("F2.6",),
    ),
    _sync(
        Meta("ley:restore", "Let a cut ley line flow again", G.WORLDS),
        environment.restore_ley_line,
        environment.LeyTarget,
        free,
        ("F2.6",),
    ),
    _sync(
        Meta("ley:forge", "Forge a ley line between two neighbouring regions", G.WORLDS),
        environment.forge_ley_line,
        environment.ForgeLey,
        free,
        ("F2.6",),
    ),
    _sync(
        Meta("ley:unforge", "Leave a forged ley line to the land's own magic", G.WORLDS),
        environment.unforge_ley_line,
        environment.LeyTarget,
        free,
        ("F2.6",),
    ),
    _sync(
        Meta("weather:force", "Hold a weather over a region for some epochs", G.WORLDS),
        environment.force_weather,
        environment.ForceWeather,
        free,
        ("F2.3",),
    ),
    _sync(
        Meta("weather:release", "Let a region's sky go its own way again", G.WORLDS),
        environment.release_weather,
        environment.ForcedTarget,
        free,
        ("F2.3",),
    ),
    _sync(
        Meta("year:force_notable", "Set down a notable year in a region's memory", G.WORLDS),
        environment.force_notable_year,
        environment.ForceNotableYear,
        free,
        ("F1",),
    ),
    _sync(
        Meta("environment:set", "Set or hold a value of a region's environment", G.WORLDS),
        environment.set_region_environment,
        environment.SetRegionEnvironment,
        free,
        ("F2.1", "F2.4", "S6.1/RP3"),
    ),
    _sync(
        Meta("environment:unlock", "Let a held environment value follow the world again", G.WORLDS),
        environment.unlock_region_environment,
        environment.UnlockRegionEnvironment,
        free,
        ("F2.1", "S6.1/RP3"),
    ),
    _sync(
        Meta("environment:scar", "Scar or heal a region's land", G.WORLDS),
        environment.set_region_scar,
        environment.SetScar,
        free,
        ("F2.1",),
    ),
    _sync(
        Meta("environment:mineral", "Set the richness of a mineral seam, of a catalog or a world material", G.WORLDS),
        environment.set_region_mineral,
        environment.SetMineral,
        free,
        ("F2.1",),
    ),
    _sync(
        Meta("environment:place", "Set a place's terrain, cover, water, height or chokepoint", G.WORLDS),
        environment.set_place_environment,
        environment.SetPlaceEnvironment,
        free,
        ("F2.1",),
    ),
    _sync(
        Meta("seasons:reorder", "Reorder the seasons of a world", G.WORLDS),
        environment.reorder_world_seasons,
        environment.ReorderSeasons,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("seasons:edit", "Reshape one season of a world", G.WORLDS),
        environment.edit_world_season,
        environment.EditSeason,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("seasons:calendar", "Set a world's axial tilt, year and day", G.WORLDS),
        environment.set_world_calendar,
        environment.SetWorldCalendar,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("calendar:adopt", "Make an astronomy record keep a calendar", G.WORLDS),
        environment.adopt_world_calendar,
        environment.CalendarTarget,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("calendar:drop", "Let an astronomy record stop keeping a calendar", G.WORLDS),
        environment.drop_world_calendar,
        environment.CalendarTarget,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("calendar:rename", "Rename the months of a calendar", G.WORLDS),
        environment.rename_calendar_months,
        environment.RenameMonths,
        free,
        ("F2.2",),
    ),
)
HAPPENING_ACTIONS = (
    _sync(Meta("event:create", "Set down an event of any kind in a land or town", G.WORLDS), happenings.create_event, happenings.CreateEvent, free, ("S8.8",)),
    _sync(Meta("event:edit", "Edit an event's name, severity, years and seasons", G.WORLDS), happenings.edit_event, happenings.EditEvent, free, ("S8.8",)),
    _sync(
        Meta("event:phase", "Move an event to its beginning, height or aftermath, and hold it", G.WORLDS),
        happenings.set_event_phase,
        happenings.EventPhaseCommand,
        free,
        ("S8.8",),
    ),
    _sync(Meta("event:release", "Let a held event value follow the world again", G.WORLDS), happenings.release_event, happenings.EventRelease, free, ("S8.8",)),
    _sync(
        Meta("event:footprint", "Add or remove a land from an event's reach", G.WORLDS),
        happenings.set_event_footprint,
        happenings.EventFootprint,
        free,
        ("S8.8",),
    ),
    _sync(
        Meta("event:casualties", "Set the toll of an event for one cohort", G.WORLDS),
        happenings.set_event_casualties,
        happenings.EventCasualties,
        free,
        ("S8.8",),
    ),
    _sync(Meta("event:end", "End an event now", G.WORLDS), happenings.end_event, happenings.EventTarget, free, ("S8.8",)),
    _sync(Meta("land:stir", "Wake an eruption or a volcanic earthquake in a land", G.WORLDS), happenings.stir_land, happenings.StirLand, free, ("S6.1",)),
    _sync(Meta("land:river", "Move a river into a neighbouring land", G.WORLDS), happenings.move_river, happenings.MoveRiver, free, ("S6.1",)),
    _sync(Meta("land:shape", "Set and hold a land's desertification and volcanism", G.WORLDS), happenings.shape_land, happenings.ShapeLand, free, ("S6.1",)),
    _sync(Meta("land:release", "Let a held land value follow the world again", G.WORLDS), happenings.release_land, happenings.ReleaseLand, free, ("S6.1",)),
)

CALENDAR_ACTIONS = (
    _sync(
        Meta("seasons:add", "Add a season to a world's year", G.WORLDS),
        calendar.add_season,
        calendar.AddSeason,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("seasons:remove", "Take a season out of a world's year", G.WORLDS),
        calendar.remove_season,
        calendar.SeasonTarget,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("seasons:release", "Stop holding a reshaped season", G.WORLDS),
        calendar.release_season,
        calendar.SeasonTarget,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("seasons:moons", "Set and hold a world's moons and tides", G.WORLDS),
        calendar.set_moons,
        calendar.SetMoons,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("seasons:calendar_release", "Let a world's tilt, day, year, moons or tides follow the heavens again", G.WORLDS),
        calendar.release_calendar,
        calendar.ReleaseCalendar,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("weather:edit", "Change a held weather: its kind, its end or its season", G.WORLDS),
        calendar.edit_weather,
        calendar.EditWeather,
        free,
        ("F2.3",),
    ),
    _sync(
        Meta("year:edit", "Rewrite a notable year", G.WORLDS),
        calendar.edit_notable_year,
        calendar.EditNotableYear,
        free,
        ("F1",),
    ),
    _sync(
        Meta("year:delete", "Strike a notable year from memory", G.WORLDS),
        calendar.delete_notable_year,
        calendar.NotableTarget,
        free,
        ("F1",),
    ),
    _sync(
        Meta("calendar:holy_day", "Add or change a holy day of a calendar", G.WORLDS),
        calendar.set_holy_day,
        calendar.SetHolyDay,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("calendar:holy_day_remove", "Remove a holy day from a calendar", G.WORLDS),
        calendar.remove_holy_day,
        calendar.HolyDayTarget,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("calendar:anchor", "Set the year a calendar counts from", G.WORLDS),
        calendar.set_anchor,
        calendar.SetAnchor,
        free,
        ("F2.2",),
    ),
    _sync(
        Meta("ley:strength", "Set and hold a ley line's strength", G.WORLDS),
        calendar.set_ley_strength,
        calendar.LeyStrength,
        free,
        ("F2.6",),
    ),
    _sync(
        Meta("ley:dissolve", "Unmake a ley line", G.WORLDS),
        calendar.dissolve_ley,
        calendar.LeyLineTarget,
        free,
        ("F2.6",),
    ),
    _sync(
        Meta("ley:work", "Set or release a work's ties to the ley", G.WORLDS),
        calendar.set_ley_work,
        calendar.LeyWork,
        free,
        ("F2.6",),
    ),
)

MECHANIC_ACTIONS = (
    _sync(Meta("lever:pin", "Pin a field so that no mechanic can change it", G.SETTINGS), levers.pin_field, levers.PinField, free, ("J.16c",)),
    _sync(Meta("lever:unpin", "Release a pinned field", G.SETTINGS), levers.unpin_field, levers.UnpinField, free, ("J.16c",)),
    _sync(
        Meta("lever:suppress", "Suppress a mechanic on a record for some epochs", G.SETTINGS),
        levers.suppress_mechanic,
        levers.SuppressMechanic,
        free,
        ("J.16c",),
    ),
    _sync(
        Meta("lever:unsuppress", "Let a suppressed mechanic act again", G.SETTINGS),
        levers.unsuppress_mechanic,
        levers.UnsuppressMechanic,
        free,
        ("J.16c",),
    ),
    _sync(Meta("lever:run", "Run a mechanic now", G.SETTINGS), levers.run_mechanic, levers.RunMechanic, free, ("J.16c",)),
    _sync(Meta("lever:set", "Set a value a mechanic owns", G.SETTINGS), levers.set_field, levers.SetField, free, ("J.16c",)),
    _sync(Meta("modifier:add", "Add a modifier to a record", G.SETTINGS), levers.add_player_modifier, levers.AddModifier, free, ("F9", "J.16c")),
    _sync(Meta("modifier:remove", "Remove a modifier", G.SETTINGS), levers.remove_player_modifier, levers.RemoveModifier, free, ("F9", "J.16c")),
    _sync(Meta("incident:annotate", "Keep a note beside an incident", G.SETTINGS), levers.annotate_incident, levers.AnnotateIncident, free, ("F10",)),
    _sync(
        Meta("modifier:create", "Create a modifier of any source on a record", G.SETTINGS),
        modifiers.create_modifier,
        modifiers.CreateModifier,
        free,
        ("F9", "J.16c"),
    ),
    _sync(Meta("modifier:edit", "Edit a modifier", G.SETTINGS), modifiers.edit_modifier, modifiers.EditModifier, free, ("F9", "J.16c")),
    _sync(Meta("modifier:hold", "Hold a modifier so the engine keeps it", G.SETTINGS), modifiers.hold_modifier, modifiers.HoldModifier, free, ("F9", "J.16c")),
    _sync(Meta("modifier:release", "Release a held modifier", G.SETTINGS), modifiers.release_modifier, modifiers.HoldModifier, free, ("F9", "J.16c")),
    _sync(Meta("incident:create", "Write an incident into history", G.SETTINGS), incidents.create_incident, incidents.CreateIncident, free, ("F10",)),
    _sync(Meta("incident:edit", "Rewrite an incident", G.SETTINGS), incidents.edit_incident, incidents.EditIncident, free, ("F10",)),
    _sync(
        Meta("incident:roles", "Set who acted, who was struck and who watched", G.SETTINGS),
        incidents.set_incident_roles,
        incidents.SetIncidentRoles,
        free,
        ("F10",),
    ),
    _sync(Meta("incident:link_cause", "Link an incident to its cause", G.SETTINGS), incidents.link_cause, incidents.LinkCause, free, ("F10",)),
    _sync(Meta("incident:unlink_cause", "Cut an incident from its cause", G.SETTINGS), incidents.unlink_cause, incidents.IncidentRef, free, ("F10",)),
    _sync(Meta("incident:delete", "Strike an incident from history", G.SETTINGS), incidents.delete_incident, incidents.IncidentRef, free, ("F10",)),
    _sync(
        Meta("profile:set", "Set and hold any value of a record's profile", G.SETTINGS),
        profiles.set_profile_value,
        profiles.SetProfileValue,
        free,
        ("J.16c",),
    ),
    _sync(
        Meta("profile:release", "Let a held profile value follow the world again", G.SETTINGS),
        profiles.release_profile_value,
        profiles.ReleaseProfileValue,
        free,
        ("J.16c",),
    ),
)


def finish_cost_text(rules: Rules) -> str:
    return f"{rules.construction.finish_cost} essence"


S72 = ("S7.2",)
STRUCTURE_ACTIONS = (
    _sync(Meta("structure:commission", "Commission a structure", G.SOCIETY), structures.commission, structures.Commission, free, S72),
    _sync(Meta("structure:fund", "Fund a structure under construction", G.SOCIETY), structures.fund, structures.Fund, free, S72),
    _sync(Meta("structure:finish", "Finish a structure at once", G.SOCIETY), structures.finish, structures.StructureTarget, finish_cost_text, S72),
    _sync(Meta("structure:abandon", "Abandon a structure under construction", G.SOCIETY), structures.abandon, structures.Abandon, free, S72),
    _sync(Meta("structure:staff", "Staff a structure or release its staff", G.SOCIETY), structures.staff, structures.Staff, free, S72),
    _sync(Meta("structure:damage", "Damage a structure", G.SOCIETY), structures.damage, structures.Damage, free, S72),
    _sync(Meta("structure:repair", "Repair a structure", G.SOCIETY), structures.repair, structures.StructureTarget, free, S72),
    _sync(Meta("structure:edit", "Edit, hold or release a structure's values", G.SOCIETY), structures.edit, structures.EditStructure, free, S72),
    _sync(Meta("structure_design:create", "Draw up a new structure design", G.SOCIETY), structures.create_design, structures.CreateDesign, free, S72),
    _sync(Meta("structure_design:edit", "Edit, hold or release a structure design", G.SOCIETY), structures.edit_design, structures.EditDesign, free, S72),
    _sync(Meta("structure_design:retire", "Retire or restore a structure design", G.SOCIETY), structures.retire_design, structures.RetireDesign, free, S72),
)
ROUTE_ACTIONS = (
    _sync(
        Meta("trade_route:found", "Lay out a new trade route: its ends, way of travel, master and toll", G.SOCIETY),
        routes.found_route,
        routes.FoundRoute,
        free,
        ("S6.4",),
    ),
    _sync(Meta("trade_route:edit", "Set and hold any value of a trade route", G.SOCIETY), routes.edit_route, routes.EditRoute, free, ("S6.4",)),
    _sync(Meta("trade_route:delete", "Strike a trade route from the world", G.SOCIETY), routes.delete_route, routes.RouteTarget, free, ("S6.4",)),
    _sync(Meta("trade_route:toll_stop", "Raise or hold a toll in a land on a route", G.SOCIETY), routes.toll_stop, routes.TollStop, free, ("S6.4",)),
    _sync(Meta("trade_route:toll_remove", "Forbid any toll in a land on a route", G.SOCIETY), routes.toll_remove, routes.TollTarget, free, ("S6.4",)),
    _sync(Meta("resource:pact", "Bind a sentient resource and its keeper by a pact", G.SOCIETY), routes.strike_pact, routes.StrikePact, free, ("S6.3",)),
    _sync(Meta("resource:pact_terms", "Change what a sentient resource's pact asks", G.SOCIETY), routes.pact_terms, routes.PactTerms, free, ("S6.3",)),
    _sync(Meta("resource:pact_end", "Release a sentient resource's pact", G.SOCIETY), routes.end_pact, routes.PactTarget, free, ("S6.3",)),
)


RUMOUR_ACTIONS = (
    _sync(Meta("rumour:plant", "Whisper a rumour into a community", G.MEMORY), rumours.plant_rumour, rumours.PlantRumour, free, ("F11",)),
    _sync(Meta("rumour:edit", "Set how true a rumour runs, or let it fade", G.MEMORY), rumours.edit_rumour, rumours.EditRumour, free, ("F11",)),
    _sync(Meta("rumour:suppress", "Silence a rumour", G.MEMORY), rumours.suppress_rumour, rumours.SuppressRumour, free, ("F11",)),
)
MADE_ACTIONS = (
    _sync(Meta("item:transfer", "Give an item into new hands", G.BEYOND), made_things.transfer_item, made_things.TransferItem, free, ("S7.1",)),
    _sync(Meta("item:deed", "Add a deed to an item's history", G.BEYOND), made_things.add_deed, made_things.AddDeed, free, ("S7.1",)),
    _sync(Meta("item:deed_remove", "Strike a deed from an item's story", G.BEYOND), made_things.remove_deed, made_things.DeedTarget, free, ("S7.1",)),
    _sync(
        Meta("item:content", "Write knowledge into a book or scrape it out", G.BEYOND), made_things.set_content, made_things.BookContent, free, ("S7.1", "S8.4")
    ),
    _sync(Meta("art:commission", "Commission an artwork", G.SOCIETY), made_things.commission_artwork, made_things.CommissionArtwork, free, ("S7.4",)),
    _sync(Meta("art:canonise", "Set an artwork among the classics, or strike it out", G.SOCIETY), made_things.canonise, made_things.Canonise, free, ("S7.4",)),
)
FOUNDATION_ACTIONS = (
    _sync(Meta("war:incite", "Lay a war at a god's feet, or clear the blame", G.WARFARE), foundations.set_incitement, foundations.WarIncitement, free, ("W0",)),
    _sync(
        Meta("world:date_golden_age", "Set when a world's golden age began", G.WORLDS),
        foundations.set_golden_age_date,
        foundations.GoldenAgeDate,
        free,
        ("W0",),
    ),
    _sync(Meta("structure:dedicate", "Dedicate a structure to a god", G.SONS), foundations.dedicate_structure, foundations.Dedicate, free, ("S7.2",)),
    _sync(
        Meta("structure:undedicate", "Lift a structure's dedication", G.SONS), foundations.undedicate_structure, foundations.StructureTarget, free, ("S7.2",)
    ),
    _sync(Meta("son:anchor", "Anchor a god's existence", G.SONS), foundations.set_anchor, foundations.SonAnchor, free, ("S7.2", "W0")),
    _sync(Meta("son:clear_anchor", "Cut a god loose from their anchor", G.SONS), foundations.clear_anchor, foundations.SonTarget, free, ("W0",)),
    _sync(
        Meta("foundation:hold", "Hold or release a war's blame, a golden age, a dedication or an anchor", G.SETTINGS),
        foundations.hold_foundation,
        foundations.HoldFoundation,
        free,
        ("J.16c",),
    ),
)

PLACE_ACTIONS = (
    _sync(Meta("place:create", "Bring forth a place of a chosen kind", G.WORLDS), places.create_place, places.CreatePlace, free, ("S6.2",)),
    _sync(Meta("place:edit", "Set or hold a place's kind, sacredness or mystery", G.WORLDS), places.edit_place, places.EditPlace, free, ("S6.2",)),
    _sync(
        Meta("place:release", "Let a held value of a place follow the world again", G.WORLDS), places.release_place, places.ReleasePlace, free, ("S6.2", "F2.1")
    ),
    _sync(Meta("place:secret", "Hide a secret in a place", G.WORLDS), places.hide_secret, places.HideSecret, free, ("S6.2",)),
    _sync(Meta("place:secret_edit", "Reshape, seal or hold a place's secret", G.WORLDS), places.edit_secret, places.EditSecret, free, ("S6.2",)),
    _sync(Meta("place:reveal", "Reveal a place's secret or break its seal", G.WORLDS), places.reveal_secret, places.RevealSecret, free, ("S6.2",)),
    _sync(Meta("place:secret_delete", "Erase a place's secret", G.WORLDS), places.delete_secret, places.SecretTarget, free, ("S6.2",)),
    _sync(
        Meta("pilgrimage:clear", "Take a pilgrimage site off the pilgrims' roads", G.COSMOS), places.clear_pilgrimage_site, places.SiteTarget, free, ("S6.2",)
    ),
)
ACTIONS: tuple[ActionSpec, ...] = (
    *ROUTE_ACTIONS,
    *STRUCTURE_ACTIONS,
    *FOUNDATION_ACTIONS,
    *WILDS_ACTIONS,
    *LORE_ACTIONS,
    *RUMOUR_ACTIONS,
    *MADE_ACTIONS,
    *CREATOR_ACTIONS,
    *SON_ACTIONS,
    *GOD_POWER_ACTIONS,
    *DEATH_ACTIONS,
    *MESSAGE_ACTIONS,
    *INTERVENTION_ACTIONS,
    *ENTITY_ACTIONS,
    *DIPLOMACY_ACTIONS,
    *CANON_ACTIONS,
    *COSMIC_ACTIONS,
    *WORLD_ACTIONS,
    *FOREIGN_GOD_ACTIONS,
    *GOAL_ACTIONS,
    *SETTING_ACTIONS,
    *SETTLEMENT_ACTIONS,
    *SOCIETY_ACTIONS,
    *CIVILIZATION_ACTIONS,
    *HERO_ACTIONS,
    *WARFARE_ACTIONS,
    *CREATURE_ACTIONS,
    *BEYOND_ACTIONS,
    *PANTHEON_ACTIONS,
    *MEMORY_ACTIONS,
    *COSMIC_ORDER_ACTIONS,
    *DIVINE_ACTIONS,
    *LANGUAGE_ACTIONS,
    *HORIZON_ACTIONS,
    *WORLD_LAYER_ACTIONS,
    *ENGINE_CONTROL_ACTIONS,
    *FATE_ACTIONS,
    *LIFE_CYCLE_ACTIONS,
    *MECHANIC_ACTIONS,
    *ENVIRONMENT_ACTIONS,
    *PLACE_ACTIONS,
    *HAPPENING_ACTIONS,
    *CALENDAR_ACTIONS,
    *REGION_ACTIONS,
    *ECONOMY_ACTIONS,
    *BODY_ACTIONS,
    *MIND_ACTIONS,
    *DIVINITY_ACTIONS,
    *COSMOGRAPHY_ACTIONS,
    *PHYSICS_ACTIONS,
)
ACTIONS_BY_ID: dict[str, ActionSpec] = {spec.id: spec for spec in ACTIONS}


def action(action_id: str) -> ActionSpec:
    found = ACTIONS_BY_ID.get(action_id)
    if found is None:
        raise NotFoundError(f"No such action: {action_id}.")
    return found


def describe(rules: Rules) -> list[ActionDescriptor]:
    return [
        ActionDescriptor(
            id=spec.id,
            title=spec.title,
            group=spec.group,
            mode=spec.mode,
            cost=spec.cost(rules),
            confirmation=spec.confirmation.value if spec.confirmation is not None else None,
            rows=list(spec.rows),
            input_schema=spec.input_model.model_json_schema(),
        )
        for spec in ACTIONS
    ]


async def run_ledgered(scope: PlayerScope, action_id: str, payload: dict[str, Any]) -> ActionOutcome:
    spec = action(action_id)
    if spec.sync is None:
        raise NotFoundError(f"{action_id} runs as a job.")
    return await spec.sync(scope, spec.input_model.model_validate(payload))


async def run_job(runtime: PlayerRuntime, rules: Rules, action_id: str, payload: dict[str, Any]) -> ActionOutcome:
    spec = action(action_id)
    if spec.job is None:
        raise NotFoundError(f"{action_id} is not a job.")
    return await spec.job(runtime, rules, spec.input_model.model_validate(payload))
