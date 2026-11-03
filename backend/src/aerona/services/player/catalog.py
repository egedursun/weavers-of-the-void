from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from aerona.core.errors import NotFoundError
from aerona.rules.registry import Rules
from aerona.services.player import (
    assignments,
    beyond,
    body,
    canon,
    celestial_depth,
    cheats,
    civilization,
    cosmic,
    cosmic_orders,
    creation,
    creator,
    creatures,
    curation,
    death,
    diplomacy,
    divine,
    engine_control,
    environment,
    fate_controls,
    foreign_gods,
    goals,
    god_power,
    heroes,
    horizon,
    interventions,
    knowledge,
    language_contact,
    languages,
    levers,
    life_cycles,
    living_stats,
    market,
    mechanics,
    memory,
    messages,
    mind,
    native_faith,
    pantheon,
    relations,
    settings,
    settlements,
    society,
    son_tools,
    warfare,
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
    _sync(Meta("thread:open", "Open a story thread", G.CANON), canon.open_thread, canon.OpenThread, free, ("ACT-175",)),
    _sync(Meta("thread:close", "Close a story thread", G.CANON), canon.close_thread, canon.CloseThread, free, ("ACT-176",)),
    _sync(Meta("thread:advance", "Move a story thread forward", G.CANON), canon.advance_thread, canon.AdvanceThread, free, ("LLM-069",)),
    _sync(Meta("epoch:edit", "Rewrite an epoch's name or narrative", G.CANON), canon.edit_epoch, canon.EditEpoch, free, ("LLM-076",)),
    _sync(Meta("fact:add", "Add a canon fact", G.CANON), canon.add_fact, canon.AddFact, free, ("ACT-177",)),
    _sync(Meta("fact:remove", "Retire a canon fact", G.CANON), canon.remove_fact, canon.FactTarget, free, ("ACT-178",)),
    _sync(Meta("belief:edit", "Edit a people's belief", G.CANON), canon.edit_belief, canon.EditBelief, free, ("ACT-179",)),
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
        Meta("route", "Sever, stitch or reveal a route", G.COSMOS),
        cosmic.route_action,
        cosmic.RouteCommand,
        lambda rules: f"sever {rules.beyond.sever_route_cost}, stitch {rules.beyond.restitch_route_cost}, reveal {rules.travel.reveal_route_cost} essence",
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
    _sync(Meta("community:mint", "Order a coin minted", G.SOCIETY), society.mint, society.SocietyTarget, free, ()),
    _sync(Meta("community:work", "Commission a work", G.SOCIETY), society.raise_work, society.Work, free, ()),
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
    _sync(Meta("faction:found", "Found a faction", G.SOCIETY), heroes.found_faction, heroes.Faction, free, ()),
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
    _sync(Meta("species:chimera", "Weave a chimera", G.CREATURES), creatures.chimera, creatures.Chimera, free, ()),
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

HORIZON_ACTIONS = (
    _sync(
        Meta("intuition:discard", "Let a sensed world stay a legend", G.COSMOS),
        horizon.discard_intuition,
        horizon.IntuitionTarget,
        free,
        ("EXP-017", "EXP-018"),
    ),
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
    _sync(Meta("faith:syncretize", "Weave a community's faith with an old god", G.FOREIGN_GODS), native_faith.weave, native_faith.Syncretism, free, ()),
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
    _sync(Meta("body:set", "Set or hold a capacity, armour or body value", G.ENTITIES), body.set_body_value, body.SetBodyValue, free, ("F4.3", "F4.5")),
    _sync(Meta("body:unlock", "Let a held body value follow the body again", G.ENTITIES), body.unlock_body_value, body.UnlockBodyValue, free, ("F4.5",)),
    _sync(Meta("body:customs", "Set how a people reads scars", G.SOCIETY), body.set_customs, body.SetCustoms, free, ("F4.5",)),
    _sync(Meta("body:customs_unlock", "Let a people's reading of scars change again", G.SOCIETY), body.unlock_customs, body.UnlockCustoms, free, ("F4.5",)),
    _sync(Meta("body:cohort", "Set the maimed of a community", G.SOCIETY), body.set_cohort, body.SetCohort, free, ("F4.5",)),
)

MIND_ACTIONS = (
    _sync(Meta("mind:values", "Set and hold values or a culture", G.ENTITIES), mind.set_values, mind.SetValues, free, ("F5",)),
    _sync(Meta("mind:lock", "Hold a part of a mind as it is", G.ENTITIES), mind.lock_mind, mind.LockMind, free, ("F5", "F8")),
    _sync(Meta("mind:unlock", "Let a held part of a mind change again", G.ENTITIES), mind.unlock_mind, mind.LockMind, free, ("F5", "F8")),
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
        Meta("environment:set", "Set or hold a value of a region's environment", G.WORLDS),
        environment.set_region_environment,
        environment.SetRegionEnvironment,
        free,
        ("F2.1", "F2.4"),
    ),
    _sync(
        Meta("environment:unlock", "Let a held environment value follow the world again", G.WORLDS),
        environment.unlock_region_environment,
        environment.UnlockRegionEnvironment,
        free,
        ("F2.1",),
    ),
    _sync(
        Meta("environment:scar", "Scar or heal a region's land", G.WORLDS),
        environment.set_region_scar,
        environment.SetScar,
        free,
        ("F2.1",),
    ),
    _sync(
        Meta("environment:mineral", "Set the richness of a mineral seam", G.WORLDS),
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
    _sync(Meta("modifier:add", "Add a modifier to a record", G.SETTINGS), levers.add_player_modifier, levers.AddModifier, free, ("F9", "J.16c")),
    _sync(Meta("modifier:remove", "Remove a modifier", G.SETTINGS), levers.remove_player_modifier, levers.RemoveModifier, free, ("F9", "J.16c")),
)
ACTIONS: tuple[ActionSpec, ...] = (
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
    *BODY_ACTIONS,
    *MIND_ACTIONS,
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
