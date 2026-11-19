from dataclasses import dataclass
from enum import StrEnum


class Remedy(StrEnum):
    REPAIR = "repair"
    REPORT = "report"


class GenericCheck(StrEnum):
    BOUNDED = "bounded"
    ENUM_VALUES = "enum_values"
    REFERENCES = "references"
    LOCKED_NAMES = "locked_names"
    ONE_ROW_PER_THING = "one_row_per_thing"
    PAST_EPOCHS = "past_epochs"
    NODE_ID_LISTS = "node_id_lists"
    TREASURY = "treasury"


@dataclass(frozen=True)
class GenericSpec:
    text: str
    remedy: Remedy
    resolution: str


@dataclass(frozen=True)
class InvariantSpec:
    key: str
    table: str
    text: str
    remedy: Remedy
    resolution: str


GENERIC: dict[GenericCheck, GenericSpec] = {
    GenericCheck.BOUNDED: GenericSpec(
        "a number kept within its declared range stays within it",
        Remedy.REPAIR,
        "clamped into its range",
    ),
    GenericCheck.ENUM_VALUES: GenericSpec(
        "an enum column holds one of its declared values",
        Remedy.REPORT,
        "set to the column's default, or the row removed when it has none",
    ),
    GenericCheck.REFERENCES: GenericSpec(
        "a reference to another row points at a row that exists",
        Remedy.REPAIR,
        "kept by the database's foreign keys, which are always on",
    ),
    GenericCheck.LOCKED_NAMES: GenericSpec(
        "a list of held values names only columns of its row",
        Remedy.REPORT,
        "the names that are not columns are dropped from the list",
    ),
    GenericCheck.ONE_ROW_PER_THING: GenericSpec(
        "a profile keeps one row per thing",
        Remedy.REPAIR,
        "kept by the primary key, which is the thing itself",
    ),
    GenericCheck.PAST_EPOCHS: GenericSpec(
        "an epoch that records a past moment is never later than the current epoch",
        Remedy.REPAIR,
        "set back to the current epoch",
    ),
    GenericCheck.NODE_ID_LISTS: GenericSpec(
        "a list of node ids names only nodes that exist",
        Remedy.REPAIR,
        "the ids of nodes that are gone are dropped from the list",
    ),
    GenericCheck.TREASURY: GenericSpec(
        "a treasury amount is moved only through the purse",
        Remedy.REPAIR,
        "kept at the source by scripts/check_coin_units.py",
    ),
}

TYPED: tuple[InvariantSpec, ...] = (
    InvariantSpec("living_captor", "captives", "a captive still held is held by a living captor", Remedy.REPAIR, "released"),
    InvariantSpec("order_target", "instruction_orders", "an order that acts on a target has a target", Remedy.REPAIR, "lapsed"),
    InvariantSpec("maker_not_self", "constructs", "a construct is not its own maker or its own soul", Remedy.REPAIR, "the self reference cleared"),
    InvariantSpec("living_ruler", "bonds", "a ruler who still rules is alive and in the world", Remedy.REPAIR, "the rule closed"),
    InvariantSpec("covenant_people", "covenants", "a covenant with the Creator is kept by a people", Remedy.REPORT, "the covenant struck"),
    InvariantSpec("seat_god", "divine_council_seats", "a seat on the council of the gods is held by a god", Remedy.REPORT, "the seat taken away"),
    InvariantSpec("tie_gods", "pantheon_ties", "a tie within a pantheon joins two gods", Remedy.REPORT, "the tie undone"),
    InvariantSpec("syncretism_kinds", "syncretisms", "a joining of gods names a son, a foreign god and a people", Remedy.REPORT, "the joining undone"),
    InvariantSpec("money_metal", "currencies", "only coin and commodity money are made of metal", Remedy.REPAIR, "the metal cleared"),
    InvariantSpec("material_source", "world_materials", "a substance's source is a thing of the kind its origin names", Remedy.REPAIR, "the source cleared"),
    InvariantSpec("holding_kind", "kind_holdings", "a holding of a kind of thing names a kind of its own concept", Remedy.REPAIR, "the holding dropped"),
    InvariantSpec("kind_lineage", "good_kinds", "a kind of thing derives from another kind of its concept, not itself", Remedy.REPAIR, "the lineage cut"),
    InvariantSpec(
        "kind_ranges", "good_kinds", "each property of a kind of thing lies within the range its concept allows", Remedy.REPAIR, "brought into range"
    ),
    InvariantSpec(
        "genome_alleles", "genomes", "every allele a genome carries is an allele of its locus", Remedy.REPAIR, "set to the common allele of the locus"
    ),
    InvariantSpec(
        "fact_schema", "incident_facts", "every fact of a happening is one its kind declares, of the declared type and unit", Remedy.REPAIR, "the fact dropped"
    ),
    InvariantSpec(
        "kind_known", "incidents", "every happening is of a kind the catalogue declares", Remedy.REPAIR, "retired to its successor kind, its old key kept"
    ),
    InvariantSpec("step_nesting", "incident_steps", "a step nests only inside another step of the same happening", Remedy.REPAIR, "the nesting cleared"),
    InvariantSpec("step_action", "incident_steps", "every step of a happening is an action its kind declares", Remedy.REPORT, "the step dropped"),
    InvariantSpec("moment_after_cause", "incidents", "a happening is never earlier than its cause", Remedy.REPAIR, "moved to the moment of its cause"),
    InvariantSpec(
        "genesis_at_start", "incidents", "the making of the cosmos happens at the very start of its first age", Remedy.REPAIR, "moved to the first year"
    ),
    InvariantSpec(
        "moment_after_births",
        "incidents",
        "a happening is never earlier than the coming into being of everyone and everything that takes part in it",
        Remedy.REPAIR,
        "moved to the moment its latest-born participant came into being",
    ),
    InvariantSpec(
        "birth_dated", "node_births", "every thing a record brings into being knows the moment it came into being", Remedy.REPAIR, "dated by that record"
    ),
    InvariantSpec(
        "step_moment_order", "incident_steps", "a step is never earlier than the step before it", Remedy.REPAIR, "moved to the moment of the step before"
    ),
    InvariantSpec(
        "kin_head_member", "kin_groups", "the head of a kin group is one of its members", Remedy.REPAIR, "the head cleared for the kin to choose again"
    ),
    InvariantSpec(
        "kin_member_rule",
        "kin_group_members",
        "a member of a kin group joined by descent descends from its people or is adopted",
        Remedy.REPAIR,
        "marked as adopted",
    ),
    InvariantSpec("time_shares", "time_budgets", "the shares of a time budget sum to 100", Remedy.REPAIR, "scaled to 100, the remainder to work"),
    InvariantSpec(
        "child_ages",
        "child_standing",
        "the ages of naming, personhood, work, responsibility and marriage rise in that order",
        Remedy.REPAIR,
        "the ages are put in order",
    ),
    InvariantSpec("youth_years", "youth_group_members", "every member of a youth group is within the years of youth", Remedy.REPAIR, "the grown member leaves"),
    InvariantSpec("practice_holder", "facet_practices", "a practice is kept by a people or a town", Remedy.REPAIR, "the practice of anything else is struck"),
    InvariantSpec(
        "instrument_policy",
        "population_instruments",
        "an instrument belongs to its policy and to the holder of that policy",
        Remedy.REPAIR,
        "the instrument returns to its policy's holder",
    ),
    InvariantSpec(
        "remains_rite",
        "people_culture",
        "a people keeps its dead by a treatment its funeral rite allows, unless the treatment is held as an exception",
        Remedy.REPAIR,
        "the people turns to the first treatment its rite allows",
    ),
    InvariantSpec(
        "endowment_capture",
        "endowments",
        "an endowment is captured only by a trustee that is a faction or a realm",
        Remedy.REPAIR,
        "an endowment held captive by any other trustee serves its beneficiary again",
    ),
    InvariantSpec(
        "stage_builder",
        "public_work_stages",
        "a finished stage belongs to the realm that builds its works",
        Remedy.REPAIR,
        "the stage returns to the realm of its works",
    ),
    InvariantSpec(
        "folk_class_kind",
        "folk_classes",
        "a class points at an existing world kind that fits its domain, and a class of a domain without kinds points at none",
        Remedy.REPAIR,
        "a class that points at nothing fitting is struck",
    ),
    InvariantSpec(
        "numerology_keys",
        "number_systems",
        "every number a people reads lies below its base and every reading is a known one",
        Remedy.REPAIR,
        "readings of numbers beyond the base or of unknown kinds are dropped",
    ),
    InvariantSpec(
        "speech_venue", "speeches", "a speech is given at a venue its town has", Remedy.REPAIR, "a speech at a venue the town lacks is moved to the square"
    ),
    InvariantSpec(
        "media_reach",
        "media_items",
        "an item reaches no further than its outlet, and a record of an event has a subject",
        Remedy.REPAIR,
        "the reach is cut to the outlet's; a record of nothing is struck",
    ),
    InvariantSpec(
        "works_place", "public_works", "public works lie on routes, regions and towns of their builder", Remedy.REPAIR, "works on another's ground are struck"
    ),
    InvariantSpec(
        "lease_owner", "leases", "the owner of a lease holds the thing it leases", Remedy.REPAIR, "the lease of a thing its owner does not hold is void"
    ),
    InvariantSpec(
        "policy_holder",
        "population_policies",
        "a policy on numbers is held by a realm, people, faction, cult, town, god or son",
        Remedy.REPAIR,
        "the stray policy is struck",
    ),
    InvariantSpec(
        "norm_sexes",
        "intimacy_norms",
        "a norm on relations between beings of any sexes exists only where the people's biology declares fixed sexes",
        Remedy.REPAIR,
        "the norm is struck",
    ),
    InvariantSpec(
        "upbringing_shares",
        "socialization",
        "the weights of the ways a people raises its children sum to 100",
        Remedy.REPAIR,
        "scaled to 100, the remainder to example",
    ),
    InvariantSpec(
        "witness_present",
        "incident_participants",
        "one who saw or took part stood within the place, unless it moved afterwards",
        Remedy.REPAIR,
        "the witness dropped",
    ),
    InvariantSpec(
        "witness_mode",
        "incident_participants",
        "a witness always says how it knows the happening",
        Remedy.REPAIR,
        "set down as one who saw it within the place, or heard of it from elsewhere",
    ),
    InvariantSpec(
        "keeper_mortal",
        "record_keepers",
        "the chronicle and each people's history are kept by a mortal",
        Remedy.REPAIR,
        "the seat is freed for the world to choose a living mortal",
    ),
    InvariantSpec("change_in_scope", "state_changes", "every change the engine made belongs to a happening", Remedy.REPAIR, "linked to the phase that made it"),
    InvariantSpec(
        "checkpoint_holds", "state_checkpoints", "the past rebuilt from the changes equals each checkpoint", Remedy.REPAIR, "the checkpoint taken again"
    ),
)

DERIVED_REASONS: dict[str, str] = {
    "profile": "a profile keyed by the thing it describes; every column is covered by the generic checks",
    "columns": "every column is covered by the generic checks; it states no rule across rows",
    "free_json": "it holds a free-form JSON record whose shape its one writer keeps; its other columns are covered by the generic checks",
}
