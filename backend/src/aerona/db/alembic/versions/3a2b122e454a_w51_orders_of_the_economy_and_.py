import sqlalchemy as sa
from alembic import op

revision = "3a2b122e454a"
down_revision = "40f493adbbbe"
branch_labels = None
depends_on = None


FACTIONKIND_OLD = (
    "merchant_guild",
    "craft_guild",
    "priesthood",
    "warrior_order",
    "noble_council",
    "peasant_league",
    "rebels",
    "bandits",
    "pirates",
    "assassins",
    "scholars_academy",
    "secret_society",
    "mercenary_company",
    "interworld_federation",
    "wandering_market",
    "route_raiders",
    "social_circle",
    "mage_order",
    "estate",
    "party",
    "movement",
    "chartered_company",
    "holy_order",
    "crime_family",
    "thieves_guild",
    "smuggling_ring",
    "pirate_confederacy",
    "art_movement",
    "club",
    "league",
    "workers_union",
    "engineers_society",
    "financiers",
    "veterans",
)
FACTIONKIND_NEW = (*FACTIONKIND_OLD, "worker_body")

LAWKIND_OLD = (
    "succession_rule",
    "inheritance_split",
    "land_tenure",
    "slavery",
    "serfdom",
    "tax_rate",
    "tithe",
    "tolls",
    "debt_law",
    "penal_code",
    "levy_law",
    "conscription",
    "standing_army",
    "veteran_pension",
    "ransom_custom",
    "marriage_law",
    "sumptuary",
    "guild_charter",
    "foreigner_rights",
    "religious_tolerance",
    "worship_ban",
    "censorship",
    "blood_feud",
    "quarantine",
    "burial_law",
    "sanitation",
    "fair_market",
    "magic_ban",
    "licensed_magic",
    "rite_restrictions",
    "franchise",
    "constitution",
    "custom",
    "labour_law",
    "environment_law",
    "data_privacy",
    "weapons_law",
    "intellectual_property",
    "machine_law",
    "space_law",
    "closed_season",
    "protected_waters",
    "catch_quota",
    "gear_ban",
    "mind_status",
    "copy_law",
    "copy_succession",
    "erasure_law",
    "augment_law",
    "network_law",
    "surveillance_law",
    "provision_law",
    "power_law",
    "source_law",
    "living_craft_law",
    "clone_law",
    "clone_status",
    "germline_law",
    "designed_status",
)
LAWKIND_NEW = (*LAWKIND_OLD, "competition_law")

TREATYKIND_OLD = (
    "peace",
    "truce",
    "alliance_defensive",
    "alliance_offensive",
    "non_aggression",
    "vassalage",
    "tribute",
    "marriage_pact",
    "trade_pact",
    "condotta",
    "guarantee",
    "interworld",
    "coalition",
    "divine_pact",
    "naval_limit",
)
TREATYKIND_NEW = (*TREATYKIND_OLD, "arms_limit")

MOVEMENTCAUSE_OLD = (
    "abolition",
    "independence",
    "revival",
    "land_reform",
    "franchise",
    "peace",
)
MOVEMENTCAUSE_NEW = (*MOVEMENTCAUSE_OLD, "conservation")

THOUGHTKIND_OLD = (
    "married",
    "child_born",
    "saw_kin_die",
    "lost_spouse",
    "lost_child",
    "betrayed",
    "was_insulted",
    "was_gifted",
    "was_saved",
    "was_cheated",
    "won_battle",
    "defeated",
    "won_duel",
    "lost_duel",
    "was_wounded",
    "was_maimed",
    "lost_limb_but_lived",
    "was_healed",
    "fell_ill",
    "witnessed_atrocity",
    "was_captured",
    "was_freed",
    "killed_foe",
    "rose_in_rank",
    "fell_in_rank",
    "gained_renown",
    "was_shamed",
    "was_punished",
    "was_conquered",
    "prayed_answered",
    "prayer_ignored",
    "saw_miracle",
    "felt_god_near",
    "alien_dominion",
    "lost_faith",
    "found_faith",
    "saw_desecration",
    "touched_by_a_god",
    "admired_great_work",
    "heard_great_music",
    "attended_feast",
    "made_masterwork",
    "learned_something",
    "taught_apprentice",
    "took_idea_to_heart",
    "ate_fine_food",
    "went_hungry",
    "went_thirsty",
    "drank_well",
    "slept_well",
    "exhausted",
    "lived_in_comfort",
    "lived_in_squalor",
    "felt_hale",
    "felt_unwell",
    "felt_safe",
    "felt_unsafe",
    "among_kin",
    "missed_kin",
    "among_friends",
    "felt_lonely",
    "lost_pet",
    "comforted_by_pet",
    "loved",
    "longed_for_love",
    "had_peace_and_quiet",
    "crowded",
    "respected",
    "overlooked",
    "belonged",
    "adrift",
    "felt_purpose",
    "lacked_purpose",
    "prayed_in_peace",
    "faith_unmet",
    "learned_nothing",
    "felt_free",
    "felt_constrained",
    "found_answers",
    "kept_in_ignorance",
    "felt_stimulated",
    "felt_dulled",
    "felt_lasting",
    "feared_ending",
    "well_kept",
    "neglected",
    "made_something",
    "nothing_made",
    "saw_beauty",
    "surrounded_by_ugliness",
    "walked_in_nature",
    "cut_off_from_nature",
    "had_adventure",
    "restless",
    "tested_in_combat",
    "blade_rusting",
    "prospered",
    "wanted_for_money",
    "enjoyed_leisure",
    "bored",
    "lived_in_order",
    "lived_in_disorder",
    "relived_memory",
    "mourned",
    "made_peace_with_loss",
    "had_nightmare",
    "had_good_dream",
    "dreamed_of_longing",
    "received_visitation",
    "sent_by_the_creator",
    "liked_surroundings",
    "disliked_surroundings",
    "proud_of_home",
    "ashamed_of_home",
    "enjoyed_favourite",
    "endured_a_dislike",
    "acted_on_conscience",
    "acted_against_conscience",
    "kin_shamed",
    "shame_restored",
    "dream_progress",
    "dream_fulfilled",
    "dream_shattered",
    "want_fulfilled",
    "fear_near",
    "inspired",
    "inspiration_lost",
    "disillusioned",
    "made_a_friend",
    "lost_a_friend",
    "laughed_together",
    "was_comforted",
    "was_flattered",
    "quarrelled",
    "reconciled",
    "fell_in_love",
    "heartbroken",
    "jealous",
    "brawled",
    "was_threatened",
    "confided_in",
    "won_contest",
    "lost_contest",
    "was_persuaded",
    "rose_in_standing",
    "lost_standing",
    "passion_stirred",
    "passion_broke",
)
THOUGHTKIND_NEW = (*THOUGHTKIND_OLD, "caught_feeling")

CLAUSEKIND_OLD = (
    "call_to_arms",
    "tribute",
    "cession",
    "hostage",
    "marriage",
    "trade_rights",
    "tolls_waived",
    "religious_freedom",
    "demilitarised",
    "champion",
    "extradition",
    "wergild",
    "non_aggression",
    "route_control",
    "resource_demand",
    "research_agreement",
    "fleet_limit",
    "autonomous_weapons_ban",
    "mind_seizure_ban",
    "soldier_copy_ban",
    "replicator_weapon_ban",
    "civil_network_shield",
    "civil_host_shield",
    "no_mind_compulsion",
    "no_plague_powers",
    "no_designed_disease",
)
CLAUSEKIND_NEW = (*CLAUSEKIND_OLD, "mass_weapon_limit")

BALANCELOOP_OLD = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
    "kind_prestige",
    "kind_substitution",
    "policy_grievance",
    "housework_burden",
    "cure_resistance",
    "weather_grievance",
)
BALANCELOOP_NEW = (*BALANCELOOP_OLD, "collectivisation_reversal", "cartel_cheating", "mutual_deterrence")

HARMCAUSE_OLD = (
    "battle",
    "duel",
    "punishment",
    "torture",
    "accident",
    "monster",
    "disaster",
    "curse",
    "magic_backlash",
    "god",
    "poison",
    "quest",
    "escape",
    "sacrifice",
    "age",
    "player",
    "exposure",
    "ritual",
    "bombardment",
    "industrial",
    "crash",
    "radiation",
    "decompression",
    "experiment",
    "power",
)
HARMCAUSE_NEW = (*HARMCAUSE_OLD, "body")

ENTITYTYPE_OLD = (
    "region",
    "place",
    "resource",
    "settlement",
    "species",
    "people",
    "mortal",
    "item",
    "structure",
    "language",
    "legend",
    "tradition",
    "cult",
    "faction",
    "celestial",
    "artwork",
    "law",
    "spirit",
    "knowledge",
    "prophecy",
    "event",
    "vessel",
    "outer_being",
    "army",
    "natural_law",
    "trade_route",
    "disease",
    "polity",
    "house",
    "treaty",
    "title",
    "ideology",
    "rite",
    "beast",
    "theory",
    "art_form",
    "phenomenon",
    "cosmic_being",
    "vehicle_type",
    "unit_type",
    "equipment_model",
    "dish",
    "building_type",
    "network",
)
ENTITYTYPE_NEW = (*ENTITYTYPE_OLD, "league")
RETYPED = (
    ("organisation_kinds", "base", "base", FACTIONKIND_OLD, FACTIONKIND_NEW, False),
    ("faction_profiles", "kind", "kind", FACTIONKIND_OLD, FACTIONKIND_NEW, False),
    ("law_profiles", "kind", "kind", LAWKIND_OLD, LAWKIND_NEW, False),
    ("law_proposals", "kind", "kind", LAWKIND_OLD, LAWKIND_NEW, False),
    ("treaty_profiles", "kind", "kind", TREATYKIND_OLD, TREATYKIND_NEW, False),
    ("movement_profiles", "cause", "cause", MOVEMENTCAUSE_OLD, MOVEMENTCAUSE_NEW, False),
    ("thoughts", "kind", "kind", THOUGHTKIND_OLD, THOUGHTKIND_NEW, False),
    ("treaty_clauses", "kind", "kind", CLAUSEKIND_OLD, CLAUSEKIND_NEW, False),
    ("loop_signals", "loop", "loop", BALANCELOOP_OLD, BALANCELOOP_NEW, False),
    ("injuries", "cause_kind", "cause_kind", HARMCAUSE_OLD, HARMCAUSE_NEW, False),
    ("conditions", "source", "source", HARMCAUSE_OLD, HARMCAUSE_NEW, False),
    ("entities", "entity_type", "entity_type", ENTITYTYPE_OLD, ENTITYTYPE_NEW, False),
    ("son_powers", "param_entity_type", "param_entity_type", ENTITYTYPE_OLD, ENTITYTYPE_NEW, True),
    ("natural_law_exceptions", "entity_type", "entity_type", ENTITYTYPE_OLD, ENTITYTYPE_NEW, True),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, name, old, new, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        gone = ", ".join(f"'{value}'" for value in new if value not in old)
        if not forward and nullable:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})")
        elif not forward:
            op.execute(f"DELETE FROM {table} WHERE {column} IN ({gone})")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(after, name), existing_nullable=nullable)


def upgrade() -> None:
    retype(True)
    op.create_table(
        "cartels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("leader_node_id", sa.Integer(), nullable=True),
        sa.Column("members", sa.JSON(), nullable=False),
        sa.Column("markets", sa.JSON(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "aim", sa.Enum("price", "quota", "territory", "bid_rigging", name="aim", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("agreed_price", sa.Integer(), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=False),
        sa.Column("secrecy", sa.Integer(), nullable=False),
        sa.Column("discipline", sa.Integer(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("broken_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("agreed_price >= 0", name=op.f("ck_cartels_agreed_price_min")),
        sa.CheckConstraint("discipline BETWEEN 0 AND 100", name=op.f("ck_cartels_discipline_range")),
        sa.CheckConstraint("formed_epoch >= 0", name=op.f("ck_cartels_formed_epoch_min")),
        sa.CheckConstraint("quota >= 0", name=op.f("ck_cartels_quota_min")),
        sa.CheckConstraint("secrecy BETWEEN 0 AND 100", name=op.f("ck_cartels_secrecy_range")),
        sa.ForeignKeyConstraint(["leader_node_id"], ["nodes.id"], name=op.f("fk_cartels_leader_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cartels")),
    )
    with op.batch_alter_table("cartels", schema=None) as batch_op:
        batch_op.create_index("ix_cartels_commodity", ["commodity"], unique=False)

    op.create_table(
        "honour_kinds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conferrer_node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("privileges", sa.JSON(), nullable=False),
        sa.Column("holder_limit", sa.Integer(), nullable=False),
        sa.Column("hereditary", sa.Boolean(), nullable=False),
        sa.Column("worth", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("holder_limit >= 0", name=op.f("ck_honour_kinds_holder_limit_min")),
        sa.CheckConstraint("rank BETWEEN 1 AND 10", name=op.f("ck_honour_kinds_rank_range")),
        sa.CheckConstraint("worth BETWEEN 0 AND 100", name=op.f("ck_honour_kinds_worth_range")),
        sa.ForeignKeyConstraint(["conferrer_node_id"], ["nodes.id"], name=op.f("fk_honour_kinds_conferrer_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_honour_kinds")),
    )
    with op.batch_alter_table("honour_kinds", schema=None) as batch_op:
        batch_op.create_index("ix_honour_kinds_conferrer", ["conferrer_node_id"], unique=False)

    op.create_table(
        "referendums",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "subject",
            sa.Enum(
                "law",
                "constitution",
                "independence",
                "union",
                "treaty",
                "war",
                "transition",
                "recall",
                "faith",
                name="subject",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "caller",
            sa.Enum("ruler", "assembly", "petition", "league", "god", name="caller", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("called_by_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "franchise",
            sa.Enum("nobles", "landholders", "citizens", "free", "all", name="franchise", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("binding", sa.Boolean(), nullable=False),
        sa.Column("threshold_pct", sa.Integer(), nullable=False),
        sa.Column("yes_spending", sa.Integer(), nullable=False),
        sa.Column("no_spending", sa.Integer(), nullable=False),
        sa.Column("yes_pct", sa.Integer(), nullable=False),
        sa.Column("turnout_pct", sa.Integer(), nullable=False),
        sa.Column("fraud", sa.Integer(), nullable=False),
        sa.Column(
            "result", sa.Enum("pending", "passed", "failed", "void", name="result", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("ignored", sa.Boolean(), nullable=False),
        sa.Column("called_epoch", sa.Integer(), nullable=False),
        sa.Column("held_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("called_epoch >= 0", name=op.f("ck_referendums_called_epoch_min")),
        sa.CheckConstraint("fraud BETWEEN 0 AND 100", name=op.f("ck_referendums_fraud_range")),
        sa.CheckConstraint("no_spending >= 0", name=op.f("ck_referendums_no_spending_min")),
        sa.CheckConstraint("threshold_pct BETWEEN 0 AND 100", name=op.f("ck_referendums_threshold_pct_range")),
        sa.CheckConstraint("turnout_pct BETWEEN 0 AND 100", name=op.f("ck_referendums_turnout_pct_range")),
        sa.CheckConstraint("yes_pct BETWEEN 0 AND 100", name=op.f("ck_referendums_yes_pct_range")),
        sa.CheckConstraint("yes_spending >= 0", name=op.f("ck_referendums_yes_spending_min")),
        sa.ForeignKeyConstraint(["called_by_node_id"], ["nodes.id"], name=op.f("fk_referendums_called_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_referendums_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_referendums_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referendums")),
    )
    with op.batch_alter_table("referendums", schema=None) as batch_op:
        batch_op.create_index("ix_referendums_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "worker_bodies",
        sa.Column("faction_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "craft_union",
                "industrial_union",
                "general_union",
                "companion_society",
                "mutual_aid",
                "worker_cooperative",
                "made_mind_collective",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("trades", sa.JSON(), nullable=False),
        sa.Column("works", sa.JSON(), nullable=False),
        sa.Column("members", sa.Integer(), nullable=False),
        sa.Column("dues", sa.Integer(), nullable=False),
        sa.Column("fund", sa.Integer(), nullable=False),
        sa.Column("solidarity", sa.Integer(), nullable=False),
        sa.Column(
            "standing",
            sa.Enum("banned", "tolerated", "recognised", "compulsory", name="standing", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dues >= 0", name=op.f("ck_worker_bodies_dues_min")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_worker_bodies_founded_epoch_min")),
        sa.CheckConstraint("fund >= 0", name=op.f("ck_worker_bodies_fund_min")),
        sa.CheckConstraint("members >= 0", name=op.f("ck_worker_bodies_members_min")),
        sa.CheckConstraint("solidarity BETWEEN 0 AND 100", name=op.f("ck_worker_bodies_solidarity_range")),
        sa.ForeignKeyConstraint(["faction_node_id"], ["nodes.id"], name=op.f("fk_worker_bodies_faction_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_node_id", name=op.f("pk_worker_bodies")),
    )
    op.create_table(
        "agentless_conditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "age",
                "diet",
                "exposure",
                "heredity",
                "injury_aftermath",
                "strain",
                "unknown",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "system",
            sa.Enum(
                "breath",
                "circulation",
                "digestion",
                "regulation",
                "nerves",
                "immunity",
                "reproduction",
                "structure",
                "none",
                name="system",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "manifests",
            sa.Enum(
                "chronic_illness",
                "paranoia",
                "visions",
                "rage",
                "melancholy",
                "addiction",
                "age_blindness",
                "age_deafness",
                "withered_limb",
                "endless_hunger",
                "possession",
                "void_taint",
                "chosen_mark",
                "divine_brand",
                "nightmares",
                "comatose",
                "cognitive_decline",
                "malnutrition",
                name="manifests",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("course", sa.Enum("stable", "worsening", "episodic", name="course", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("onset_pct", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("onset_pct BETWEEN 0 AND 100", name=op.f("ck_agentless_conditions_onset_pct_range")),
        sa.CheckConstraint("severity BETWEEN 1 AND 5", name=op.f("ck_agentless_conditions_severity_range")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_agentless_conditions_weight_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_agentless_conditions_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agentless_conditions")),
    )
    with op.batch_alter_table("agentless_conditions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_agentless_conditions_world_id"), ["world_id"], unique=False)

    op.create_table(
        "conservation_movements",
        sa.Column("movement_entity_id", sa.Integer(), nullable=False),
        sa.Column("aims", sa.JSON(), nullable=False),
        sa.Column("cohort_support", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["movement_entity_id"], ["entities.id"], name=op.f("fk_conservation_movements_movement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("movement_entity_id", name=op.f("pk_conservation_movements")),
    )
    op.create_table(
        "conurbations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("core_entity_id", sa.Integer(), nullable=False),
        sa.Column("members", sa.JSON(), nullable=False),
        sa.Column(
            "governance",
            sa.Enum("one_council", "federated_councils", "ruled_by_core", name="governance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("imposed_laws", sa.JSON(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("split_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["core_entity_id"], ["entities.id"], name=op.f("fk_conurbations_core_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conurbations")),
    )
    with op.batch_alter_table("conurbations", schema=None) as batch_op:
        batch_op.create_index("ix_conurbations_core", ["core_entity_id"], unique=False)

    op.create_table(
        "creature_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("lair_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "form",
            sa.Enum("pack", "herd", "colony", "hive", "troop", "flock", "solitary_range", name="form", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("leader_node_id", sa.Integer(), nullable=True),
        sa.Column("leader_since_epoch", sa.Integer(), nullable=False),
        sa.Column("ranks", sa.Integer(), nullable=False),
        sa.Column("territory", sa.JSON(), nullable=False),
        sa.Column("rivals", sa.JSON(), nullable=False),
        sa.Column("hunger", sa.Integer(), nullable=False),
        sa.Column("aim", sa.Enum("raid", "withdraw", "guard", "grow", name="aim", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column("aim_until_epoch", sa.Integer(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("hunger BETWEEN 0 AND 100", name=op.f("ck_creature_groups_hunger_range")),
        sa.CheckConstraint("ranks BETWEEN 0 AND 10", name=op.f("ck_creature_groups_ranks_range")),
        sa.CheckConstraint("size >= 0", name=op.f("ck_creature_groups_size_min")),
        sa.ForeignKeyConstraint(["lair_node_id"], ["nodes.id"], name=op.f("fk_creature_groups_lair_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_node_id"], ["nodes.id"], name=op.f("fk_creature_groups_leader_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_creature_groups_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_creature_groups_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creature_groups")),
    )
    with op.batch_alter_table("creature_groups", schema=None) as batch_op:
        batch_op.create_index("ix_creature_groups_region", ["region_entity_id"], unique=False)
        batch_op.create_index("ix_creature_groups_species", ["species_entity_id"], unique=False)

    op.create_table(
        "deterrence_postures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("toward_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "posture",
            sa.Enum(
                "none",
                "declared",
                "ambiguous",
                "first_use",
                "retaliation_only",
                "shared_with_league",
                name="posture",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("credibility", sa.Integer(), nullable=False),
        sa.Column("declared_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("credibility BETWEEN 0 AND 100", name=op.f("ck_deterrence_postures_credibility_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_deterrence_postures_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["toward_entity_id"], ["entities.id"], name=op.f("fk_deterrence_postures_toward_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deterrence_postures")),
    )
    with op.batch_alter_table("deterrence_postures", schema=None) as batch_op:
        batch_op.create_index("ix_deterrence_postures_holder", ["holder_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_deterrence_postures_toward_entity_id"), ["toward_entity_id"], unique=False)

    op.create_table(
        "divine_conceptions",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "count",
            sa.Enum("one", "one_above_many", "many", "pairs", "all_is_divine", "none", name="count", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("nearness", sa.Enum("distant", "present", "within", name="nearness", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "personhood",
            sa.Enum("persons", "forces", "principle", "mixed", name="personhood", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "creator_place",
            sa.Enum("acknowledged", "unknown", "denied", "rival", name="creator_place", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strain", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strain BETWEEN 0 AND 100", name=op.f("ck_divine_conceptions_strain_range")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_divine_conceptions_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cult_entity_id", name=op.f("pk_divine_conceptions")),
    )
    op.create_table(
        "feeling_spread",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.Column("feelings", sa.JSON(), nullable=False),
        sa.Column(
            "leading",
            sa.Enum(
                "joy",
                "contentment",
                "pride",
                "love",
                "gratitude",
                "relief",
                "hope",
                "awe",
                "amusement",
                "fear",
                "anxiety",
                "anger",
                "rage",
                "grief",
                "sadness",
                "shame",
                "guilt",
                "envy",
                "jealousy",
                "disgust",
                "loneliness",
                "boredom",
                "despair",
                "longing",
                name="leading",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], name=op.f("fk_feeling_spread_household_id_households"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_feeling_spread_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feeling_spread")),
    )
    with op.batch_alter_table("feeling_spread", schema=None) as batch_op:
        batch_op.create_index("ix_feeling_spread_household", ["household_id"], unique=False)
        batch_op.create_index("ix_feeling_spread_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "fertility_means",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "means",
            sa.Enum(
                "prevention",
                "remedy_for_barrenness",
                "ending_pregnancy",
                "assisted_conception",
                "surrogacy",
                "made_birth",
                name="means",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("source", sa.Enum("folk", "medicine", "rite", "power", name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("reliability", sa.Integer(), nullable=False),
        sa.Column("risk", sa.Integer(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum("forbidden", "discouraged", "tolerated", "accepted", "honoured", name="stance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("use_pct", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("reliability BETWEEN 0 AND 100", name=op.f("ck_fertility_means_reliability_range")),
        sa.CheckConstraint("risk BETWEEN 0 AND 100", name=op.f("ck_fertility_means_risk_range")),
        sa.CheckConstraint("use_pct BETWEEN 0 AND 100", name=op.f("ck_fertility_means_use_pct_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_fertility_means_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "means", name=op.f("pk_fertility_means")),
    )
    op.create_table(
        "fertility_uses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_entity_id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "means",
            sa.Enum(
                "prevention",
                "remedy_for_barrenness",
                "ending_pregnancy",
                "assisted_conception",
                "surrogacy",
                "made_birth",
                name="means",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("hidden", sa.Boolean(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_fertility_uses_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_entity_id"], ["entities.id"], name=op.f("fk_fertility_uses_user_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fertility_uses")),
    )
    with op.batch_alter_table("fertility_uses", schema=None) as batch_op:
        batch_op.create_index("ix_fertility_uses_user", ["user_entity_id"], unique=False)

    op.create_table(
        "god_readings",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "reading", sa.Enum("true", "servant", "demon", "unknown", name="reading", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_god_readings_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_god_readings_god_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cult_entity_id", "god_node_id", name=op.f("pk_god_readings")),
    )
    op.create_table(
        "grave_goods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dead_entity_id", sa.Integer(), nullable=False),
        sa.Column("grave_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "custom",
            sa.Enum(
                "burial",
                "cremation",
                "exposure",
                "preservation",
                "water",
                "consumption",
                "storage",
                "return_to_maker",
                "release",
                "none_needed",
                name="custom",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("goods_value", sa.Integer(), nullable=False),
        sa.Column(
            "guard",
            sa.Enum("none", "hidden", "sealed", "guarded", "trapped", "cursed", "warded", name="guard", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("placed_epoch", sa.Integer(), nullable=False),
        sa.Column("robbed_epoch", sa.Integer(), nullable=True),
        sa.Column("robber_node_id", sa.Integer(), nullable=True),
        sa.Column("found_epoch", sa.Integer(), nullable=True),
        sa.Column("finder_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("goods_value BETWEEN 0 AND 100", name=op.f("ck_grave_goods_goods_value_range")),
        sa.ForeignKeyConstraint(["dead_entity_id"], ["entities.id"], name=op.f("fk_grave_goods_dead_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finder_node_id"], ["nodes.id"], name=op.f("fk_grave_goods_finder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grave_entity_id"], ["entities.id"], name=op.f("fk_grave_goods_grave_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["robber_node_id"], ["nodes.id"], name=op.f("fk_grave_goods_robber_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grave_goods")),
        sa.UniqueConstraint("dead_entity_id", name=op.f("uq_grave_goods_dead_entity_id")),
    )
    with op.batch_alter_table("grave_goods", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_grave_goods_grave_entity_id"), ["grave_entity_id"], unique=False)

    op.create_table(
        "insolvency_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("debtor_node_id", sa.Integer(), nullable=False),
        sa.Column("creditors", sa.JSON(), nullable=False),
        sa.Column("owed", sa.Integer(), nullable=False),
        sa.Column("assets", sa.Integer(), nullable=False),
        sa.Column(
            "path",
            sa.Enum(
                "liquidation",
                "restructuring",
                "rescue_by_owner",
                "rescue_by_polity",
                "seizure_by_creditor",
                name="path",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("court_node_id", sa.Integer(), nullable=True),
        sa.Column("stage", sa.Enum("filed", "claims", "settled", "closed", name="stage", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("recovered_pct", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("assets >= 0", name=op.f("ck_insolvency_cases_assets_min")),
        sa.CheckConstraint("owed >= 0", name=op.f("ck_insolvency_cases_owed_min")),
        sa.CheckConstraint("recovered_pct BETWEEN 0 AND 100", name=op.f("ck_insolvency_cases_recovered_pct_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_insolvency_cases_started_epoch_min")),
        sa.ForeignKeyConstraint(["court_node_id"], ["nodes.id"], name=op.f("fk_insolvency_cases_court_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["debtor_node_id"], ["entities.id"], name=op.f("fk_insolvency_cases_debtor_node_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insolvency_cases")),
    )
    with op.batch_alter_table("insolvency_cases", schema=None) as batch_op:
        batch_op.create_index("ix_insolvency_cases_debtor", ["debtor_node_id"], unique=False)

    op.create_table(
        "interpretations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "event", sa.Enum("parley", "treaty", "trial", "trade", "sermon", name="event", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("event_node_id", sa.Integer(), nullable=True),
        sa.Column("first_party_id", sa.Integer(), nullable=False),
        sa.Column("second_party_id", sa.Integer(), nullable=False),
        sa.Column("interpreter_node_id", sa.Integer(), nullable=True),
        sa.Column("first_language_id", sa.Integer(), nullable=True),
        sa.Column("second_language_id", sa.Integer(), nullable=True),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column(
            "fault",
            sa.Enum(
                "none",
                "lost_meaning",
                "wrong_term",
                "softened",
                "hardened",
                "slanted",
                "invented",
                name="fault",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("favoured_party_id", sa.Integer(), nullable=True),
        sa.Column("found", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_interpretations_fidelity_range")),
        sa.ForeignKeyConstraint(["event_node_id"], ["entities.id"], name=op.f("fk_interpretations_event_node_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["favoured_party_id"], ["entities.id"], name=op.f("fk_interpretations_favoured_party_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["first_language_id"], ["entities.id"], name=op.f("fk_interpretations_first_language_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["first_party_id"], ["entities.id"], name=op.f("fk_interpretations_first_party_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interpreter_node_id"], ["nodes.id"], name=op.f("fk_interpretations_interpreter_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["second_language_id"], ["entities.id"], name=op.f("fk_interpretations_second_language_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["second_party_id"], ["entities.id"], name=op.f("fk_interpretations_second_party_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interpretations")),
    )
    with op.batch_alter_table("interpretations", schema=None) as batch_op:
        batch_op.create_index("ix_interpretations_event", ["event_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interpretations_interpreter_node_id"), ["interpreter_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interpretations_second_party_id"), ["second_party_id"], unique=False)

    op.create_table(
        "kin_dynamics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.Column("house_entity_id", sa.Integer(), nullable=True),
        sa.Column("tension", sa.Integer(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("tension BETWEEN 0 AND 100", name=op.f("ck_kin_dynamics_tension_range")),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_kin_dynamics_house_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], name=op.f("fk_kin_dynamics_household_id_households"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kin_dynamics")),
    )
    with op.batch_alter_table("kin_dynamics", schema=None) as batch_op:
        batch_op.create_index("ix_kin_dynamics_house", ["house_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_kin_dynamics_household_id"), ["household_id"], unique=False)

    op.create_table(
        "labour_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hirer_node_id", sa.Integer(), nullable=False),
        sa.Column("body_node_id", sa.Integer(), nullable=True),
        sa.Column("worker_node_id", sa.Integer(), nullable=True),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "trade",
            sa.Enum(
                "farming",
                "herding",
                "fishing",
                "mining",
                "crafting",
                "trade",
                "soldiering",
                "clergy",
                "scholarship",
                "building",
                "service",
                "idle",
                name="trade",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("wage", sa.Integer(), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False),
        sa.Column("safety", sa.Integer(), nullable=False),
        sa.Column("rest", sa.Integer(), nullable=False),
        sa.Column("keep", sa.Integer(), nullable=False),
        sa.Column("term_epochs", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("proposed", "bargaining", "agreed", "broken", "expired", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("hours BETWEEN 0 AND 168", name=op.f("ck_labour_contracts_hours_range")),
        sa.CheckConstraint("keep BETWEEN 0 AND 100", name=op.f("ck_labour_contracts_keep_range")),
        sa.CheckConstraint("rest BETWEEN 0 AND 100", name=op.f("ck_labour_contracts_rest_range")),
        sa.CheckConstraint("safety BETWEEN 0 AND 100", name=op.f("ck_labour_contracts_safety_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_labour_contracts_started_epoch_min")),
        sa.CheckConstraint("term_epochs >= 1", name=op.f("ck_labour_contracts_term_epochs_min")),
        sa.CheckConstraint("wage BETWEEN 0 AND 400", name=op.f("ck_labour_contracts_wage_range")),
        sa.ForeignKeyConstraint(["body_node_id"], ["nodes.id"], name=op.f("fk_labour_contracts_body_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hirer_node_id"], ["nodes.id"], name=op.f("fk_labour_contracts_hirer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_labour_contracts_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_node_id"], ["nodes.id"], name=op.f("fk_labour_contracts_worker_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labour_contracts")),
    )
    with op.batch_alter_table("labour_contracts", schema=None) as batch_op:
        batch_op.create_index("ix_labour_contracts_body", ["body_node_id"], unique=False)
        batch_op.create_index("ix_labour_contracts_hirer", ["hirer_node_id"], unique=False)

    op.create_table(
        "labour_disputes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("body_node_id", sa.Integer(), nullable=True),
        sa.Column("hirer_node_id", sa.Integer(), nullable=True),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "trade",
            sa.Enum(
                "farming",
                "herding",
                "fishing",
                "mining",
                "crafting",
                "trade",
                "soldiering",
                "clergy",
                "scholarship",
                "building",
                "service",
                "idle",
                name="trade",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "demand",
            sa.Enum("wage", "hours", "safety", "rest", "keep", "recognition", name="demand", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "act",
            sa.Enum(
                "strike", "go_slow", "lockout", "boycott", "occupation_of_works", "sabotage", name="act", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("workers_out", sa.Integer(), nullable=False),
        sa.Column("body_losses", sa.Integer(), nullable=False),
        sa.Column("hirer_losses", sa.Integer(), nullable=False),
        sa.Column("injured", sa.Integer(), nullable=False),
        sa.Column("strikebreakers", sa.Boolean(), nullable=False),
        sa.Column("mediator_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "outcome", sa.Enum("ongoing", "won", "lost", "settled", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("body_losses >= 0", name=op.f("ck_labour_disputes_body_losses_min")),
        sa.CheckConstraint("hirer_losses >= 0", name=op.f("ck_labour_disputes_hirer_losses_min")),
        sa.CheckConstraint("injured >= 0", name=op.f("ck_labour_disputes_injured_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_labour_disputes_started_epoch_min")),
        sa.CheckConstraint("workers_out >= 0", name=op.f("ck_labour_disputes_workers_out_min")),
        sa.ForeignKeyConstraint(["body_node_id"], ["nodes.id"], name=op.f("fk_labour_disputes_body_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hirer_node_id"], ["nodes.id"], name=op.f("fk_labour_disputes_hirer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mediator_node_id"], ["nodes.id"], name=op.f("fk_labour_disputes_mediator_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_labour_disputes_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_labour_disputes")),
    )
    with op.batch_alter_table("labour_disputes", schema=None) as batch_op:
        batch_op.create_index("ix_labour_disputes_body", ["body_node_id"], unique=False)
        batch_op.create_index("ix_labour_disputes_hirer", ["hirer_node_id"], unique=False)
        batch_op.create_index("ix_labour_disputes_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "leader_cults",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("leader_node_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("promoters", sa.JSON(), nullable=False),
        sa.Column("instruments", sa.JSON(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("sincerity", sa.Integer(), nullable=False),
        sa.Column(
            "fate",
            sa.Enum("living", "passed_on", "faded", "became_faith", "torn_down", name="fate", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("heir_node_id", sa.Integer(), nullable=True),
        sa.Column("faith_entity_id", sa.Integer(), nullable=True),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("begun_epoch >= 0", name=op.f("ck_leader_cults_begun_epoch_min")),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_leader_cults_intensity_range")),
        sa.CheckConstraint("sincerity BETWEEN 0 AND 100", name=op.f("ck_leader_cults_sincerity_range")),
        sa.ForeignKeyConstraint(["faith_entity_id"], ["entities.id"], name=op.f("fk_leader_cults_faith_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["heir_node_id"], ["nodes.id"], name=op.f("fk_leader_cults_heir_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_node_id"], ["nodes.id"], name=op.f("fk_leader_cults_leader_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_leader_cults_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leader_cults")),
    )
    with op.batch_alter_table("leader_cults", schema=None) as batch_op:
        batch_op.create_index("ix_leader_cults_leader", ["leader_node_id"], unique=False)
        batch_op.create_index("ix_leader_cults_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "league_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "organ",
            sa.Enum("assembly", "council", "court", "secretariat", "force", name="organ", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "admit",
                "expel",
                "sanction",
                "common_tariff",
                "common_force",
                "ruling",
                "budget",
                "mediation",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("proposer_node_id", sa.Integer(), nullable=True),
        sa.Column("rate_pct", sa.Integer(), nullable=False),
        sa.Column("votes_for", sa.Integer(), nullable=False),
        sa.Column("votes_against", sa.Integer(), nullable=False),
        sa.Column(
            "outcome", sa.Enum("pending", "passed", "failed", "vetoed", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_league_decisions_epoch_min")),
        sa.CheckConstraint("rate_pct BETWEEN 0 AND 100", name=op.f("ck_league_decisions_rate_pct_range")),
        sa.CheckConstraint("votes_against >= 0", name=op.f("ck_league_decisions_votes_against_min")),
        sa.CheckConstraint("votes_for >= 0", name=op.f("ck_league_decisions_votes_for_min")),
        sa.ForeignKeyConstraint(["league_entity_id"], ["entities.id"], name=op.f("fk_league_decisions_league_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_node_id"], ["nodes.id"], name=op.f("fk_league_decisions_proposer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_league_decisions_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_league_decisions")),
    )
    with op.batch_alter_table("league_decisions", schema=None) as batch_op:
        batch_op.create_index("ix_league_decisions_league", ["league_entity_id"], unique=False)

    op.create_table(
        "league_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "standing",
            sa.Enum("founder", "member", "observer", "suspended", "expelled", name="standing", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("dues_paid", sa.Integer(), nullable=False),
        sa.Column("veto", sa.Boolean(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("defiance", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dues_paid >= 0", name=op.f("ck_league_members_dues_paid_min")),
        sa.CheckConstraint("joined_epoch >= 0", name=op.f("ck_league_members_joined_epoch_min")),
        sa.ForeignKeyConstraint(["league_entity_id"], ["entities.id"], name=op.f("fk_league_members_league_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_league_members_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_league_members")),
        sa.UniqueConstraint("league_entity_id", "polity_entity_id", name="uq_league_members_pair"),
    )
    with op.batch_alter_table("league_members", schema=None) as batch_op:
        batch_op.create_index("ix_league_members_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "market_structures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("sellers", sa.JSON(), nullable=False),
        sa.Column("small_sellers_pct", sa.Integer(), nullable=False),
        sa.Column("concentration", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum("many_sellers", "few_sellers", "one_seller", "one_buyer", "few_buyers", name="form", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("barriers", sa.JSON(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("concentration BETWEEN 0 AND 100", name=op.f("ck_market_structures_concentration_range")),
        sa.CheckConstraint("small_sellers_pct BETWEEN 0 AND 100", name=op.f("ck_market_structures_small_sellers_pct_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_market_structures_updated_epoch_min")),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_market_structures_market_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_structures")),
        sa.UniqueConstraint("market_entity_id", "commodity", name="uq_market_structures_good"),
    )
    with op.batch_alter_table("market_structures", schema=None) as batch_op:
        batch_op.create_index("ix_market_structures_market", ["market_entity_id"], unique=False)

    op.create_table(
        "mass_weapons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "harm",
            sa.Enum(
                "blast",
                "fire",
                "poison",
                "disease",
                "radiation",
                "swarm",
                "field",
                "rite",
                "divine_relic",
                name="harm",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("reach", sa.Enum("settlement", "region", "world", name="reach", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "stage", sa.Enum("sought", "building", "ready", "tested", name="stage", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("readiness", sa.Integer(), nullable=False),
        sa.Column("seen_by", sa.JSON(), nullable=False),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("tested_epoch", sa.Integer(), nullable=True),
        sa.Column("used_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("begun_epoch >= 0", name=op.f("ck_mass_weapons_begun_epoch_min")),
        sa.CheckConstraint("count >= 0", name=op.f("ck_mass_weapons_count_min")),
        sa.CheckConstraint("readiness BETWEEN 0 AND 100", name=op.f("ck_mass_weapons_readiness_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_mass_weapons_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mass_weapons")),
    )
    with op.batch_alter_table("mass_weapons", schema=None) as batch_op:
        batch_op.create_index("ix_mass_weapons_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "municipal_services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "service",
            sa.Enum(
                "refuse",
                "lighting",
                "water_distribution",
                "street_cleaning",
                "night_watch",
                "burial_ground",
                "market_inspection",
                name="service",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("provider_node_id", sa.Integer(), nullable=True),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("budget", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("failed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("budget >= 0", name=op.f("ck_municipal_services_budget_min")),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_municipal_services_cost_min")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_municipal_services_quality_range")),
        sa.ForeignKeyConstraint(["provider_node_id"], ["nodes.id"], name=op.f("fk_municipal_services_provider_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["settlement_entity_id"], ["entities.id"], name=op.f("fk_municipal_services_settlement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_municipal_services")),
    )
    with op.batch_alter_table("municipal_services", schema=None) as batch_op:
        batch_op.create_index("ix_municipal_services_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "occupation_regimes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("occupier_entity_id", sa.Integer(), nullable=False),
        sa.Column("owner_polity_id", sa.Integer(), nullable=True),
        sa.Column(
            "rule",
            sa.Enum(
                "military", "civil_by_occupier", "local_puppet", "annexation", "protectorate", name="rule", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("administrators", sa.JSON(), nullable=False),
        sa.Column("imposed_laws", sa.JSON(), nullable=False),
        sa.Column("tax_pct", sa.Integer(), nullable=False),
        sa.Column("levy_pct", sa.Integer(), nullable=False),
        sa.Column("labour_pct", sa.Integer(), nullable=False),
        sa.Column("settlers", sa.Integer(), nullable=False),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("ending", sa.Enum("liberated", "annexed", "withdrawn", name="ending", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("begun_epoch >= 0", name=op.f("ck_occupation_regimes_begun_epoch_min")),
        sa.CheckConstraint("labour_pct BETWEEN 0 AND 100", name=op.f("ck_occupation_regimes_labour_pct_range")),
        sa.CheckConstraint("levy_pct BETWEEN 0 AND 100", name=op.f("ck_occupation_regimes_levy_pct_range")),
        sa.CheckConstraint("settlers >= 0", name=op.f("ck_occupation_regimes_settlers_min")),
        sa.CheckConstraint("tax_pct BETWEEN 0 AND 100", name=op.f("ck_occupation_regimes_tax_pct_range")),
        sa.ForeignKeyConstraint(["occupier_entity_id"], ["entities.id"], name=op.f("fk_occupation_regimes_occupier_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_polity_id"], ["entities.id"], name=op.f("fk_occupation_regimes_owner_polity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_occupation_regimes_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occupation_regimes")),
    )
    with op.batch_alter_table("occupation_regimes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_occupation_regimes_occupier_entity_id"), ["occupier_entity_id"], unique=False)
        batch_op.create_index("ix_occupation_regimes_region", ["region_entity_id"], unique=False)

    op.create_table(
        "orbital_control",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("contested_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_orbital_control_strength_range")),
        sa.ForeignKeyConstraint(
            ["contested_by_entity_id"], ["entities.id"], name=op.f("fk_orbital_control_contested_by_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_orbital_control_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_orbital_control_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orbital_control")),
    )
    with op.batch_alter_table("orbital_control", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_orbital_control_holder_entity_id"), ["holder_entity_id"], unique=False)
        batch_op.create_index("ix_orbital_control_world", ["world_id"], unique=True)

    op.create_table(
        "org_cliques",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("leader_node_id", sa.Integer(), nullable=True),
        sa.Column("members", sa.JSON(), nullable=False),
        sa.Column("aim", sa.Enum("strategy", "head", "split", "merger", name="aim", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "aim_strategy",
            sa.Enum(
                "grow",
                "hold",
                "specialise",
                "diversify",
                "expand_abroad",
                "integrate_up",
                "integrate_down",
                "lobby",
                "research",
                "withdraw",
                name="aim_strategy",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("aim_node_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_org_cliques_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_org_cliques_strength_range")),
        sa.ForeignKeyConstraint(["aim_node_id"], ["nodes.id"], name=op.f("fk_org_cliques_aim_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_node_id"], ["nodes.id"], name=op.f("fk_org_cliques_leader_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_node_id"], ["entities.id"], name=op.f("fk_org_cliques_org_node_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_cliques")),
    )
    with op.batch_alter_table("org_cliques", schema=None) as batch_op:
        batch_op.create_index("ix_org_cliques_org", ["org_node_id"], unique=False)

    op.create_table(
        "org_governance",
        sa.Column("org_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "decision_body",
            sa.Enum(
                "founder",
                "head",
                "board",
                "chapter",
                "assembly_of_members",
                "council_of_elders",
                "shareholders_meeting",
                "made_mind",
                "none",
                name="decision_body",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "head_selection",
            sa.Enum(
                "appointed_by_owner",
                "elected_by_body",
                "elected_by_members",
                "inherited",
                "seniority",
                "lot",
                "divination",
                "purchase",
                name="head_selection",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("head_node_id", sa.Integer(), nullable=True),
        sa.Column("term_epochs", sa.Integer(), nullable=False),
        sa.Column("term_ends_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "vote_basis",
            sa.Enum("one_member_one_vote", "by_share", "by_rank", "by_seniority", name="vote_basis", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("quorum_pct", sa.Integer(), nullable=False),
        sa.Column(
            "strategy",
            sa.Enum(
                "grow",
                "hold",
                "specialise",
                "diversify",
                "expand_abroad",
                "integrate_up",
                "integrate_down",
                "lobby",
                "research",
                "withdraw",
                name="strategy",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("quorum_pct BETWEEN 0 AND 100", name=op.f("ck_org_governance_quorum_pct_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_org_governance_since_epoch_min")),
        sa.CheckConstraint("term_epochs >= 1", name=op.f("ck_org_governance_term_epochs_min")),
        sa.CheckConstraint("trust BETWEEN 0 AND 100", name=op.f("ck_org_governance_trust_range")),
        sa.ForeignKeyConstraint(["head_node_id"], ["nodes.id"], name=op.f("fk_org_governance_head_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_node_id"], ["entities.id"], name=op.f("fk_org_governance_org_node_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("org_node_id", name=op.f("pk_org_governance")),
    )
    op.create_table(
        "org_mergers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("acquirer_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "merger",
                "friendly_acquisition",
                "hostile_takeover",
                "buyout",
                "absorption_by_polity",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("share_offer_pct", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("bid", "resisted", "agreed", "closed", "blocked", "withdrawn", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("friendly_buyer_node_id", sa.Integer(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("price >= 0", name=op.f("ck_org_mergers_price_min")),
        sa.CheckConstraint("share_offer_pct BETWEEN 0 AND 100", name=op.f("ck_org_mergers_share_offer_pct_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_org_mergers_started_epoch_min")),
        sa.ForeignKeyConstraint(["acquirer_node_id"], ["nodes.id"], name=op.f("fk_org_mergers_acquirer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["friendly_buyer_node_id"], ["nodes.id"], name=op.f("fk_org_mergers_friendly_buyer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["entities.id"], name=op.f("fk_org_mergers_target_node_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_mergers")),
    )
    with op.batch_alter_table("org_mergers", schema=None) as batch_op:
        batch_op.create_index("ix_org_mergers_acquirer", ["acquirer_node_id"], unique=False)
        batch_op.create_index("ix_org_mergers_target", ["target_node_id"], unique=False)

    op.create_table(
        "org_seats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_node_id", sa.Integer(), nullable=False),
        sa.Column("member_node_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("vote_weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_org_seats_since_epoch_min")),
        sa.CheckConstraint("vote_weight BETWEEN 0 AND 100", name=op.f("ck_org_seats_vote_weight_range")),
        sa.ForeignKeyConstraint(["member_node_id"], ["nodes.id"], name=op.f("fk_org_seats_member_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_node_id"], ["entities.id"], name=op.f("fk_org_seats_org_node_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_seats")),
        sa.UniqueConstraint("org_node_id", "member_node_id", name="uq_org_seats_member"),
    )
    with op.batch_alter_table("org_seats", schema=None) as batch_op:
        batch_op.create_index("ix_org_seats_member", ["member_node_id"], unique=False)

    op.create_table(
        "price_wars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("aggressor_node_id", sa.Integer(), nullable=False),
        sa.Column("targets", sa.JSON(), nullable=False),
        sa.Column("market_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "commodity",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("cut_pct", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column(
            "outcome", sa.Enum("ongoing", "won", "lost", "called_off", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cut_pct BETWEEN 0 AND 100", name=op.f("ck_price_wars_cut_pct_range")),
        sa.CheckConstraint("losses >= 0", name=op.f("ck_price_wars_losses_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_price_wars_started_epoch_min")),
        sa.ForeignKeyConstraint(["aggressor_node_id"], ["nodes.id"], name=op.f("fk_price_wars_aggressor_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_price_wars_market_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_wars")),
    )
    with op.batch_alter_table("price_wars", schema=None) as batch_op:
        batch_op.create_index("ix_price_wars_market", ["market_entity_id"], unique=False)

    op.create_table(
        "protected_areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("site_entity_id", sa.Integer(), nullable=True),
        sa.Column("protector_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "basis",
            sa.Enum("law", "faith", "custom", "charter", "divine_decree", name="basis", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("banned_uses", sa.JSON(), nullable=False),
        sa.Column("wardens", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("poaching", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("lifted_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("poaching BETWEEN 0 AND 100", name=op.f("ck_protected_areas_poaching_range")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_protected_areas_strength_range")),
        sa.CheckConstraint("wardens >= 0", name=op.f("ck_protected_areas_wardens_min")),
        sa.ForeignKeyConstraint(["protector_node_id"], ["nodes.id"], name=op.f("fk_protected_areas_protector_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_protected_areas_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_entity_id"], ["entities.id"], name=op.f("fk_protected_areas_site_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_protected_areas")),
    )
    with op.batch_alter_table("protected_areas", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_protected_areas_protector_node_id"), ["protector_node_id"], unique=False)
        batch_op.create_index("ix_protected_areas_region", ["region_entity_id"], unique=False)

    op.create_table(
        "reckonings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("fallen_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "fallen_government",
            sa.Enum(
                "chiefdom",
                "monarchy",
                "theocracy",
                "oligarchy",
                "republic",
                "tribal_confederation",
                "empire",
                "hive_council",
                "god_realm",
                "occupation",
                "junta",
                "corporate_state",
                "technocracy",
                "federation",
                "commune",
                "machine_rule",
                "colonial_administration",
                name="fallen_government",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("fallen_epoch", sa.Integer(), nullable=False),
        sa.Column("opened_by_node_id", sa.Integer(), nullable=True),
        sa.Column("resistance", sa.Integer(), nullable=False),
        sa.Column("victims_pressure", sa.Integer(), nullable=False),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fallen_epoch >= 0", name=op.f("ck_reckonings_fallen_epoch_min")),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_reckonings_opened_epoch_min")),
        sa.CheckConstraint("resistance BETWEEN 0 AND 100", name=op.f("ck_reckonings_resistance_range")),
        sa.CheckConstraint("victims_pressure BETWEEN 0 AND 100", name=op.f("ck_reckonings_victims_pressure_range")),
        sa.ForeignKeyConstraint(["fallen_node_id"], ["nodes.id"], name=op.f("fk_reckonings_fallen_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opened_by_node_id"], ["nodes.id"], name=op.f("fk_reckonings_opened_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_reckonings_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reckonings")),
    )
    with op.batch_alter_table("reckonings", schema=None) as batch_op:
        batch_op.create_index("ix_reckonings_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "restorations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fallen_polity_id", sa.Integer(), nullable=False),
        sa.Column("claimant_node_id", sa.Integer(), nullable=True),
        sa.Column("territories", sa.JSON(), nullable=False),
        sa.Column("bases", sa.JSON(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("memory", "movement", "rising", "restored", "failed", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("memory", sa.Integer(), nullable=False),
        sa.Column("restored_polity_id", sa.Integer(), nullable=True),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("begun_epoch >= 0", name=op.f("ck_restorations_begun_epoch_min")),
        sa.CheckConstraint("memory BETWEEN 0 AND 100", name=op.f("ck_restorations_memory_range")),
        sa.ForeignKeyConstraint(["claimant_node_id"], ["nodes.id"], name=op.f("fk_restorations_claimant_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fallen_polity_id"], ["entities.id"], name=op.f("fk_restorations_fallen_polity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restored_polity_id"], ["entities.id"], name=op.f("fk_restorations_restored_polity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restorations")),
    )
    with op.batch_alter_table("restorations", schema=None) as batch_op:
        batch_op.create_index("ix_restorations_fallen", ["fallen_polity_id"], unique=False)

    op.create_table(
        "sea_waves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "origin",
            sa.Enum("quake", "eruption", "slide", "storm", "impact", "divine", name="origin", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("origin_region_id", sa.Integer(), nullable=True),
        sa.Column("sea_region_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("cause_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_sea_waves_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_sea_waves_strength_range")),
        sa.ForeignKeyConstraint(["cause_node_id"], ["nodes.id"], name=op.f("fk_sea_waves_cause_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_region_id"], ["entities.id"], name=op.f("fk_sea_waves_origin_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sea_region_id"], ["entities.id"], name=op.f("fk_sea_waves_sea_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_sea_waves_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sea_waves")),
    )
    with op.batch_alter_table("sea_waves", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sea_waves_sea_region_id"), ["sea_region_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sea_waves_world_id"), ["world_id"], unique=False)

    op.create_table(
        "species_protections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "basis",
            sa.Enum("law", "faith", "custom", "charter", "divine_decree", name="basis", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("measures", sa.JSON(), nullable=False),
        sa.Column("endangered_at_start", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("recovered_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_species_protections_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_protections_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_species_protections")),
    )
    with op.batch_alter_table("species_protections", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_species_protections_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index("ix_species_protections_species", ["species_entity_id"], unique=False)

    op.create_table(
        "stock_exchanges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column("network_node_id", sa.Integer(), nullable=True),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("listing_fee", sa.Integer(), nullable=False),
        sa.Column("margin_pct", sa.Integer(), nullable=False),
        sa.Column("members", sa.JSON(), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_stock_exchanges_founded_epoch_min")),
        sa.CheckConstraint("listing_fee >= 0", name=op.f("ck_stock_exchanges_listing_fee_min")),
        sa.CheckConstraint("margin_pct BETWEEN 0 AND 100", name=op.f("ck_stock_exchanges_margin_pct_range")),
        sa.CheckConstraint("mood BETWEEN -100 AND 100", name=op.f("ck_stock_exchanges_mood_range")),
        sa.ForeignKeyConstraint(["network_node_id"], ["nodes.id"], name=op.f("fk_stock_exchanges_network_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_stock_exchanges_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_stock_exchanges_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_exchanges")),
    )
    with op.batch_alter_table("stock_exchanges", schema=None) as batch_op:
        batch_op.create_index("ix_stock_exchanges_owner", ["owner_node_id"], unique=False)
        batch_op.create_index("ix_stock_exchanges_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "wave_warnings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "sight",
                "lore",
                "almanac",
                "instrument",
                "network_of_observers",
                "model",
                "network",
                "power",
                "divination",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("by_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_wave_warnings_epoch_min")),
        sa.CheckConstraint("until_epoch >= 0", name=op.f("ck_wave_warnings_until_epoch_min")),
        sa.ForeignKeyConstraint(["by_node_id"], ["nodes.id"], name=op.f("fk_wave_warnings_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_wave_warnings_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wave_warnings")),
    )
    with op.batch_alter_table("wave_warnings", schema=None) as batch_op:
        batch_op.create_index("ix_wave_warnings_region", ["region_entity_id"], unique=False)

    op.create_table(
        "collaborations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("regime_id", sa.Integer(), nullable=False),
        sa.Column("collaborator_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "administration", "police", "informing", "trade", "militia", "propaganda", name="kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("reward", sa.Integer(), nullable=False),
        sa.Column("exposure", sa.Integer(), nullable=False),
        sa.Column("fate", sa.Enum("serving", "killed", "ended", name="fate", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("exposure BETWEEN 0 AND 100", name=op.f("ck_collaborations_exposure_range")),
        sa.CheckConstraint("reward >= 0", name=op.f("ck_collaborations_reward_min")),
        sa.ForeignKeyConstraint(["collaborator_node_id"], ["nodes.id"], name=op.f("fk_collaborations_collaborator_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regime_id"], ["occupation_regimes.id"], name=op.f("fk_collaborations_regime_id_occupation_regimes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collaborations")),
    )
    with op.batch_alter_table("collaborations", schema=None) as batch_op:
        batch_op.create_index("ix_collaborations_node", ["collaborator_node_id"], unique=False)
        batch_op.create_index("ix_collaborations_regime", ["regime_id"], unique=False)

    op.create_table(
        "departures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("office_id", sa.Integer(), nullable=True),
        sa.Column(
            "office_kind",
            sa.Enum(
                "ruler",
                "heir_designate",
                "regent",
                "chancellor",
                "marshal",
                "treasurer",
                "high_judge",
                "spymaster",
                "governor",
                "ambassador",
                "herald",
                "chaplain",
                "court_scholar",
                "head_of_state",
                "head_of_government",
                "minister",
                "general",
                "admiral",
                "speaker",
                "chief_scientist",
                "jester",
                "warden",
                name="office_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("org_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "abdication",
                "retirement",
                "resignation",
                "withdrawal_to_religion",
                "exile_by_choice",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("in_favour_of_node_id", sa.Integer(), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("years_held", sa.Integer(), nullable=False),
        sa.Column("standing", sa.Integer(), nullable=False),
        sa.Column("returned_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_departures_epoch_min")),
        sa.CheckConstraint("standing BETWEEN 0 AND 100", name=op.f("ck_departures_standing_range")),
        sa.CheckConstraint("years_held >= 0", name=op.f("ck_departures_years_held_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_departures_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["in_favour_of_node_id"], ["nodes.id"], name=op.f("fk_departures_in_favour_of_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["office_id"], ["offices.id"], name=op.f("fk_departures_office_id_offices"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_node_id"], ["nodes.id"], name=op.f("fk_departures_org_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_departures_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departures")),
    )
    with op.batch_alter_table("departures", schema=None) as batch_op:
        batch_op.create_index("ix_departures_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_departures_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "elder_sway",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dynamic_id", sa.Integer(), nullable=False),
        sa.Column("elder_node_id", sa.Integer(), nullable=False),
        sa.Column("sway", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_elder_sway_since_epoch_min")),
        sa.CheckConstraint("sway BETWEEN 0 AND 100", name=op.f("ck_elder_sway_sway_range")),
        sa.ForeignKeyConstraint(["dynamic_id"], ["kin_dynamics.id"], name=op.f("fk_elder_sway_dynamic_id_kin_dynamics"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["elder_node_id"], ["nodes.id"], name=op.f("fk_elder_sway_elder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_elder_sway")),
    )
    with op.batch_alter_table("elder_sway", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_elder_sway_dynamic_id"), ["dynamic_id"], unique=False)
        batch_op.create_index("ix_elder_sway_elder", ["elder_node_id"], unique=False)

    op.create_table(
        "honours_held",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.Column("conferred_by_node_id", sa.Integer(), nullable=True),
        sa.Column("deed_incident_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("revoked_epoch", sa.Integer(), nullable=True),
        sa.Column("sold", sa.Boolean(), nullable=False),
        sa.Column("inherited", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_honours_held_epoch_min")),
        sa.ForeignKeyConstraint(["conferred_by_node_id"], ["nodes.id"], name=op.f("fk_honours_held_conferred_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deed_incident_id"], ["incidents.id"], name=op.f("fk_honours_held_deed_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_honours_held_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kind_id"], ["honour_kinds.id"], name=op.f("fk_honours_held_kind_id_honour_kinds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_honours_held")),
    )
    with op.batch_alter_table("honours_held", schema=None) as batch_op:
        batch_op.create_index("ix_honours_held_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_honours_held_kind", ["kind_id"], unique=False)

    op.create_table(
        "interworld_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attacker_entity_id", sa.Integer(), nullable=False),
        sa.Column("defender_entity_id", sa.Integer(), nullable=True),
        sa.Column("from_world_id", sa.Integer(), nullable=False),
        sa.Column("target_world_id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("army_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "stage",
            sa.Enum("gathering", "transit", "supremacy", "landing", "holding", "withdrawn", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("carriers", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("forces", sa.Integer(), nullable=False),
        sa.Column("transit_left", sa.Integer(), nullable=False),
        sa.Column("supply_hops", sa.Integer(), nullable=False),
        sa.Column("supply", sa.Integer(), nullable=False),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity >= 0", name=op.f("ck_interworld_campaigns_capacity_min")),
        sa.CheckConstraint("carriers >= 0", name=op.f("ck_interworld_campaigns_carriers_min")),
        sa.CheckConstraint("forces >= 0", name=op.f("ck_interworld_campaigns_forces_min")),
        sa.CheckConstraint("supply BETWEEN 0 AND 100", name=op.f("ck_interworld_campaigns_supply_range")),
        sa.CheckConstraint("supply_hops >= 0", name=op.f("ck_interworld_campaigns_supply_hops_min")),
        sa.CheckConstraint("transit_left >= 0", name=op.f("ck_interworld_campaigns_transit_left_min")),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_interworld_campaigns_army_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["attacker_entity_id"], ["entities.id"], name=op.f("fk_interworld_campaigns_attacker_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["defender_entity_id"], ["entities.id"], name=op.f("fk_interworld_campaigns_defender_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_world_id"], ["worlds.id"], name=op.f("fk_interworld_campaigns_from_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_interworld_campaigns_route_id_routes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_world_id"], ["worlds.id"], name=op.f("fk_interworld_campaigns_target_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interworld_campaigns")),
    )
    with op.batch_alter_table("interworld_campaigns", schema=None) as batch_op:
        batch_op.create_index("ix_interworld_campaigns_attacker", ["attacker_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interworld_campaigns_defender_entity_id"), ["defender_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interworld_campaigns_target_world_id"), ["target_world_id"], unique=False)

    op.create_table(
        "interworld_migrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("from_world_id", sa.Integer(), nullable=False),
        sa.Column("to_world_id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column(
            "cause",
            sa.Enum(
                "flight",
                "land_hunger",
                "faith_call",
                "exile",
                "labour_draw",
                "world_dying",
                "resettlement",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("reception", sa.Enum("welcome", "quota", "refusal", name="reception", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("per_epoch", sa.Integer(), nullable=False),
        sa.Column("moved", sa.Integer(), nullable=False),
        sa.Column("arrived", sa.Integer(), nullable=False),
        sa.Column("waiting", sa.Integer(), nullable=False),
        sa.Column("journey_ids", sa.JSON(), nullable=False),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("arrived >= 0", name=op.f("ck_interworld_migrations_arrived_min")),
        sa.CheckConstraint("moved >= 0", name=op.f("ck_interworld_migrations_moved_min")),
        sa.CheckConstraint("per_epoch >= 0", name=op.f("ck_interworld_migrations_per_epoch_min")),
        sa.CheckConstraint("waiting >= 0", name=op.f("ck_interworld_migrations_waiting_min")),
        sa.ForeignKeyConstraint(
            ["community_entity_id"], ["entities.id"], name=op.f("fk_interworld_migrations_community_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["from_world_id"], ["worlds.id"], name=op.f("fk_interworld_migrations_from_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_interworld_migrations_route_id_routes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_world_id"], ["worlds.id"], name=op.f("fk_interworld_migrations_to_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interworld_migrations")),
    )
    with op.batch_alter_table("interworld_migrations", schema=None) as batch_op:
        batch_op.create_index("ix_interworld_migrations_community", ["community_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interworld_migrations_to_world_id"), ["to_world_id"], unique=False)

    op.create_table(
        "kin_blends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dynamic_id", sa.Integer(), nullable=False),
        sa.Column("member_node_id", sa.Integer(), nullable=False),
        sa.Column("joined_by_node_id", sa.Integer(), nullable=True),
        sa.Column("standing", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("standing BETWEEN 0 AND 100", name=op.f("ck_kin_blends_standing_range")),
        sa.ForeignKeyConstraint(["dynamic_id"], ["kin_dynamics.id"], name=op.f("fk_kin_blends_dynamic_id_kin_dynamics"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["joined_by_node_id"], ["nodes.id"], name=op.f("fk_kin_blends_joined_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_node_id"], ["nodes.id"], name=op.f("fk_kin_blends_member_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kin_blends")),
    )
    with op.batch_alter_table("kin_blends", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_kin_blends_dynamic_id"), ["dynamic_id"], unique=False)
        batch_op.create_index("ix_kin_blends_member", ["member_node_id"], unique=False)

    op.create_table(
        "kin_disownings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dynamic_id", sa.Integer(), nullable=False),
        sa.Column("disowner_node_id", sa.Integer(), nullable=False),
        sa.Column("disowned_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum("disobedience", "marriage", "faith", "crime", "rivalry", name="reason", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("reversible", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("reconciled_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["disowned_node_id"], ["nodes.id"], name=op.f("fk_kin_disownings_disowned_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["disowner_node_id"], ["nodes.id"], name=op.f("fk_kin_disownings_disowner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dynamic_id"], ["kin_dynamics.id"], name=op.f("fk_kin_disownings_dynamic_id_kin_dynamics"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kin_disownings")),
    )
    with op.batch_alter_table("kin_disownings", schema=None) as batch_op:
        batch_op.create_index("ix_kin_disownings_disowned", ["disowned_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_kin_disownings_dynamic_id"), ["dynamic_id"], unique=False)

    op.create_table(
        "kin_favours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dynamic_id", sa.Integer(), nullable=False),
        sa.Column("parent_node_id", sa.Integer(), nullable=False),
        sa.Column("child_node_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_kin_favours_strength_range")),
        sa.ForeignKeyConstraint(["child_node_id"], ["nodes.id"], name=op.f("fk_kin_favours_child_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dynamic_id"], ["kin_dynamics.id"], name=op.f("fk_kin_favours_dynamic_id_kin_dynamics"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_node_id"], ["nodes.id"], name=op.f("fk_kin_favours_parent_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kin_favours")),
    )
    with op.batch_alter_table("kin_favours", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_kin_favours_child_node_id"), ["child_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_kin_favours_dynamic_id"), ["dynamic_id"], unique=False)
        batch_op.create_index("ix_kin_favours_parent", ["parent_node_id"], unique=False)

    op.create_table(
        "kin_rivalries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dynamic_id", sa.Integer(), nullable=False),
        sa.Column("first_node_id", sa.Integer(), nullable=False),
        sa.Column("second_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum("inheritance", "favour", "office", "love", "standing", name="cause", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("heat", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("heat BETWEEN 0 AND 100", name=op.f("ck_kin_rivalries_heat_range")),
        sa.ForeignKeyConstraint(["dynamic_id"], ["kin_dynamics.id"], name=op.f("fk_kin_rivalries_dynamic_id_kin_dynamics"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["first_node_id"], ["nodes.id"], name=op.f("fk_kin_rivalries_first_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_node_id"], ["nodes.id"], name=op.f("fk_kin_rivalries_second_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kin_rivalries")),
    )
    with op.batch_alter_table("kin_rivalries", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_kin_rivalries_dynamic_id"), ["dynamic_id"], unique=False)
        batch_op.create_index("ix_kin_rivalries_first", ["first_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_kin_rivalries_second_node_id"), ["second_node_id"], unique=False)

    op.create_table(
        "monetary_authorities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("issuer_node_id", sa.Integer(), nullable=True),
        sa.Column("coin_entity_id", sa.Integer(), nullable=True),
        sa.Column("independence", sa.Integer(), nullable=False),
        sa.Column(
            "aim",
            sa.Enum(
                "stable_value", "cheap_credit", "fund_the_state", "peg", "growth", "none", name="aim", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column("effective_rate", sa.Integer(), nullable=False),
        sa.Column("reserve_requirement_pct", sa.Integer(), nullable=False),
        sa.Column("peg_currency_id", sa.Integer(), nullable=True),
        sa.Column(
            "peg_good",
            sa.Enum(
                "grain",
                "livestock",
                "fish",
                "fodder",
                "timber",
                "fuel",
                "bread",
                "ore",
                "stone",
                "cloth",
                "tools",
                "weapons",
                "armour",
                "mounts",
                "siege_materiel",
                "medicine",
                "luxuries",
                "incense",
                "sacred_goods",
                "magical_reagents",
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="peg_good",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("lender_of_last_resort", sa.Boolean(), nullable=False),
        sa.Column("reserves", sa.Integer(), nullable=False),
        sa.Column("peg_reserves", sa.Integer(), nullable=False),
        sa.Column("peg_broken_epoch", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("effective_rate BETWEEN 0 AND 100", name=op.f("ck_monetary_authorities_effective_rate_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_monetary_authorities_founded_epoch_min")),
        sa.CheckConstraint("independence BETWEEN 0 AND 100", name=op.f("ck_monetary_authorities_independence_range")),
        sa.CheckConstraint("peg_reserves >= 0", name=op.f("ck_monetary_authorities_peg_reserves_min")),
        sa.CheckConstraint("rate BETWEEN 0 AND 100", name=op.f("ck_monetary_authorities_rate_range")),
        sa.CheckConstraint("reserve_requirement_pct BETWEEN 0 AND 100", name=op.f("ck_monetary_authorities_reserve_requirement_pct_range")),
        sa.CheckConstraint("reserves >= 0", name=op.f("ck_monetary_authorities_reserves_min")),
        sa.ForeignKeyConstraint(["coin_entity_id"], ["entities.id"], name=op.f("fk_monetary_authorities_coin_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["currency_id"], ["currencies.id"], name=op.f("fk_monetary_authorities_currency_id_currencies"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_monetary_authorities_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issuer_node_id"], ["nodes.id"], name=op.f("fk_monetary_authorities_issuer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["peg_currency_id"], ["currencies.id"], name=op.f("fk_monetary_authorities_peg_currency_id_currencies"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monetary_authorities")),
        sa.UniqueConstraint("currency_id", name=op.f("uq_monetary_authorities_currency_id")),
    )
    with op.batch_alter_table("monetary_authorities", schema=None) as batch_op:
        batch_op.create_index("ix_monetary_authorities_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_monetary_authorities_issuer", ["issuer_node_id"], unique=False)

    op.create_table(
        "occupation_measures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("regime_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "measure",
            sa.Enum(
                "curfew",
                "hostages",
                "collective_punishment",
                "deportation",
                "requisition",
                "ban_on_gathering",
                "amnesty_offer",
                name="measure",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_occupation_measures_strength_range")),
        sa.ForeignKeyConstraint(["regime_id"], ["occupation_regimes.id"], name=op.f("fk_occupation_measures_regime_id_occupation_regimes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_occupation_measures_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occupation_measures")),
    )
    with op.batch_alter_table("occupation_measures", schema=None) as batch_op:
        batch_op.create_index("ix_occupation_measures_regime", ["regime_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_occupation_measures_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "org_research",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "technique",
            sa.Enum(
                "phalanx_drill",
                "horse_archery",
                "siegecraft",
                "fortification",
                "logistics",
                "herbalism",
                "surgery",
                "amputation",
                "prosthetics",
                "quarantine",
                "inoculation",
                "irrigation",
                "crop_rotation",
                "terracing",
                "plough",
                "selective_breeding",
                "bronze",
                "iron",
                "steel",
                "skysteel",
                "arch",
                "dome",
                "aqueduct",
                "fortress",
                "alphabet",
                "paper",
                "printing",
                "cryptography",
                "calendar",
                "navigation_stars",
                "eclipse_prediction",
                "sailing",
                "shipwrighting",
                "coinage",
                "banking",
                "warding",
                "summoning",
                "sky_sailing",
                "necromancy",
                "alchemy",
                "astronomy_instruments",
                "cartography",
                "oral_law",
                "written_law",
                "codified_law",
                "bureaucracy",
                "census",
                "postal_service",
                "diplomatic_corps",
                "standing_army_admin",
                "double_entry",
                "joint_stock",
                "insurance",
                "guilds",
                "universities",
                "hospitals",
                "printing_press",
                "organised_clergy",
                "monasticism",
                "theology_schools",
                "logic",
                "natural_philosophy",
                "empiricism",
                "humanist_ideals",
                "examinations",
                "drainage",
                "gunpowder",
                "firearms",
                "cannon",
                "star_forts",
                "volley_drill",
                "steam_power",
                "coke_smelting",
                "machine_tools",
                "railways",
                "steamships",
                "factory_production",
                "industrial_chemistry",
                "canned_food",
                "vaccines",
                "electricity",
                "telegraph",
                "telephone",
                "electric_light",
                "refrigeration",
                "combustion_engine",
                "aviation",
                "computation",
                "radio",
                "mass_media",
                "antibiotics",
                "green_revolution",
                "nuclear_power",
                "nuclear_weapons",
                "rocketry",
                "genetic_engineering",
                "artificial_minds",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("design_id", sa.Integer(), nullable=True),
        sa.Column("budget", sa.Integer(), nullable=False),
        sa.Column("staff", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("secrecy", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("done_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("budget >= 0", name=op.f("ck_org_research_budget_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_org_research_progress_range")),
        sa.CheckConstraint("secrecy BETWEEN 0 AND 100", name=op.f("ck_org_research_secrecy_range")),
        sa.CheckConstraint("staff >= 0", name=op.f("ck_org_research_staff_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_org_research_started_epoch_min")),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], name=op.f("fk_org_research_design_id_designs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_node_id"], ["entities.id"], name=op.f("fk_org_research_org_node_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_research")),
    )
    with op.batch_alter_table("org_research", schema=None) as batch_op:
        batch_op.create_index("ix_org_research_org", ["org_node_id"], unique=False)

    op.create_table(
        "reckoning_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reckoning_id", sa.Integer(), nullable=False),
        sa.Column("accused_node_id", sa.Integer(), nullable=False),
        sa.Column("incident_ids", sa.JSON(), nullable=False),
        sa.Column(
            "measure",
            sa.Enum(
                "tribunal",
                "truth_inquiry",
                "office_bar",
                "amnesty",
                "amnesty_for_confession",
                "restitution",
                "reparation_to_victims",
                "memorial",
                "record_opening",
                name="measure",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.Enum(
                "pending", "convicted", "acquitted", "pardoned", "confessed", "barred", name="outcome", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_reckoning_cases_epoch_min")),
        sa.ForeignKeyConstraint(["accused_node_id"], ["nodes.id"], name=op.f("fk_reckoning_cases_accused_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reckoning_id"], ["reckonings.id"], name=op.f("fk_reckoning_cases_reckoning_id_reckonings"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reckoning_cases")),
    )
    with op.batch_alter_table("reckoning_cases", schema=None) as batch_op:
        batch_op.create_index("ix_reckoning_cases_accused", ["accused_node_id"], unique=False)
        batch_op.create_index("ix_reckoning_cases_reckoning", ["reckoning_id"], unique=False)

    op.create_table(
        "reckoning_measures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reckoning_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "measure",
            sa.Enum(
                "tribunal",
                "truth_inquiry",
                "office_bar",
                "amnesty",
                "amnesty_for_confession",
                "restitution",
                "reparation_to_victims",
                "memorial",
                "record_opening",
                name="measure",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("scope", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Enum("planned", "active", "done", name="stage", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("admin_taken", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("admin_taken >= 0", name=op.f("ck_reckoning_measures_admin_taken_min")),
        sa.CheckConstraint("scope BETWEEN 0 AND 100", name=op.f("ck_reckoning_measures_scope_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_reckoning_measures_started_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_reckoning_measures_strength_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_reckoning_measures_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reckoning_id"], ["reckonings.id"], name=op.f("fk_reckoning_measures_reckoning_id_reckonings"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reckoning_measures")),
    )
    with op.batch_alter_table("reckoning_measures", schema=None) as batch_op:
        batch_op.create_index("ix_reckoning_measures_reckoning", ["reckoning_id"], unique=False)

    op.create_table(
        "sea_wave_coasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wave_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("delay", sa.Integer(), nullable=False),
        sa.Column("warned", sa.Boolean(), nullable=False),
        sa.Column("dead", sa.Integer(), nullable=False),
        sa.Column("salted", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dead >= 0", name=op.f("ck_sea_wave_coasts_dead_min")),
        sa.CheckConstraint("delay >= 0", name=op.f("ck_sea_wave_coasts_delay_min")),
        sa.CheckConstraint("height BETWEEN 0 AND 100", name=op.f("ck_sea_wave_coasts_height_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_sea_wave_coasts_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wave_id"], ["sea_waves.id"], name=op.f("fk_sea_wave_coasts_wave_id_sea_waves"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sea_wave_coasts")),
    )
    with op.batch_alter_table("sea_wave_coasts", schema=None) as batch_op:
        batch_op.create_index("ix_sea_wave_coasts_region", ["region_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sea_wave_coasts_wave_id"), ["wave_id"], unique=False)

    op.create_table(
        "war_remnants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("orbit_world_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "buried_charges",
                "poisoned_ground",
                "fallout",
                "wreck_field",
                "unquiet_dead",
                "cursed_ground",
                "abandoned_machines",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("density", sa.Integer(), nullable=False),
        sa.Column("decay_per_epoch", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("weapon_id", sa.Integer(), nullable=True),
        sa.Column("cleared", sa.Integer(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cleared BETWEEN 0 AND 100", name=op.f("ck_war_remnants_cleared_range")),
        sa.CheckConstraint("decay_per_epoch >= 0", name=op.f("ck_war_remnants_decay_per_epoch_min")),
        sa.CheckConstraint("density BETWEEN 0 AND 100", name=op.f("ck_war_remnants_density_range")),
        sa.ForeignKeyConstraint(["orbit_world_id"], ["worlds.id"], name=op.f("fk_war_remnants_orbit_world_id_worlds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_war_remnants_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_war_remnants_war_id_wars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["weapon_id"], ["mass_weapons.id"], name=op.f("fk_war_remnants_weapon_id_mass_weapons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_war_remnants")),
    )
    with op.batch_alter_table("war_remnants", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_war_remnants_orbit_world_id"), ["orbit_world_id"], unique=False)
        batch_op.create_index("ix_war_remnants_region", ["region_entity_id"], unique=False)

    op.create_table(
        "issued_securities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("issuer_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("share", "bond", "annuity", "note", "future", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("face_value", sa.Integer(), nullable=False),
        sa.Column("coupon_pct", sa.Integer(), nullable=False),
        sa.Column("maturity_epoch", sa.Integer(), nullable=True),
        sa.Column("exchange_id", sa.Integer(), nullable=True),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("belief", sa.Integer(), nullable=False),
        sa.Column("bubble", sa.Boolean(), nullable=False),
        sa.Column("listed_epoch", sa.Integer(), nullable=False),
        sa.Column("defaulted_epoch", sa.Integer(), nullable=True),
        sa.Column("delisted_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_issued_securities_amount_min")),
        sa.CheckConstraint("belief BETWEEN 0 AND 100", name=op.f("ck_issued_securities_belief_range")),
        sa.CheckConstraint("coupon_pct BETWEEN 0 AND 100", name=op.f("ck_issued_securities_coupon_pct_range")),
        sa.CheckConstraint("face_value >= 0", name=op.f("ck_issued_securities_face_value_min")),
        sa.CheckConstraint("listed_epoch >= 0", name=op.f("ck_issued_securities_listed_epoch_min")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_issued_securities_price_min")),
        sa.ForeignKeyConstraint(["exchange_id"], ["stock_exchanges.id"], name=op.f("fk_issued_securities_exchange_id_stock_exchanges"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issuer_node_id"], ["nodes.id"], name=op.f("fk_issued_securities_issuer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], name=op.f("fk_issued_securities_loan_id_loans"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_issued_securities")),
    )
    with op.batch_alter_table("issued_securities", schema=None) as batch_op:
        batch_op.create_index("ix_issued_securities_exchange", ["exchange_id"], unique=False)
        batch_op.create_index("ix_issued_securities_issuer", ["issuer_node_id"], unique=False)

    op.create_table(
        "land_use_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("ring", sa.Integer(), nullable=True),
        sa.Column(
            "rule",
            sa.Enum(
                "allowed_uses",
                "banned_uses",
                "height_limit",
                "density_limit",
                "build_material",
                "fire_spacing",
                "frontage_rule",
                "green_share",
                name="rule",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("maker", sa.Enum("council", "ruler", "guild", "faith", name="maker", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("maker_node_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("enforcement", sa.Integer(), nullable=False),
        sa.Column("evasion", sa.Integer(), nullable=False),
        sa.Column("set_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("enforcement BETWEEN 0 AND 100", name=op.f("ck_land_use_rules_enforcement_range")),
        sa.CheckConstraint("evasion BETWEEN 0 AND 100", name=op.f("ck_land_use_rules_evasion_range")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_land_use_rules_strength_range")),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], name=op.f("fk_land_use_rules_district_id_districts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maker_node_id"], ["nodes.id"], name=op.f("fk_land_use_rules_maker_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_land_use_rules_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_land_use_rules")),
    )
    with op.batch_alter_table("land_use_rules", schema=None) as batch_op:
        batch_op.create_index("ix_land_use_rules_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "monetary_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("authority_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column(
            "aim",
            sa.Enum(
                "stable_value", "cheap_credit", "fund_the_state", "peg", "growth", "none", name="aim", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("supply", sa.Integer(), nullable=False),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_monetary_rates_epoch_min")),
        sa.CheckConstraint("rate BETWEEN 0 AND 100", name=op.f("ck_monetary_rates_rate_range")),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["monetary_authorities.id"], name=op.f("fk_monetary_rates_authority_id_monetary_authorities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monetary_rates")),
    )
    with op.batch_alter_table("monetary_rates", schema=None) as batch_op:
        batch_op.create_index("ix_monetary_rates_authority", ["authority_id"], unique=False)

    op.create_table(
        "polity_leagues",
        sa.Column("league_entity_id", sa.Integer(), nullable=False),
        sa.Column("aims", sa.JSON(), nullable=False),
        sa.Column("seat_entity_id", sa.Integer(), nullable=True),
        sa.Column("dues_pct", sa.Integer(), nullable=False),
        sa.Column(
            "vote_basis",
            sa.Enum(
                "one_member_one_vote", "by_population", "by_dues", "by_veto_holders", name="vote_basis", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("organs", sa.JSON(), nullable=False),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("common_tariff_pct", sa.Integer(), nullable=False),
        sa.Column("authority_id", sa.Integer(), nullable=True),
        sa.Column("charter_treaty_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("common_tariff_pct BETWEEN 0 AND 100", name=op.f("ck_polity_leagues_common_tariff_pct_range")),
        sa.CheckConstraint("depth BETWEEN 0 AND 100", name=op.f("ck_polity_leagues_depth_range")),
        sa.CheckConstraint("dues_pct BETWEEN 0 AND 100", name=op.f("ck_polity_leagues_dues_pct_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_polity_leagues_founded_epoch_min")),
        sa.CheckConstraint("treasury >= 0", name=op.f("ck_polity_leagues_treasury_min")),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["monetary_authorities.id"], name=op.f("fk_polity_leagues_authority_id_monetary_authorities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["charter_treaty_id"], ["entities.id"], name=op.f("fk_polity_leagues_charter_treaty_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["league_entity_id"], ["entities.id"], name=op.f("fk_polity_leagues_league_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seat_entity_id"], ["entities.id"], name=op.f("fk_polity_leagues_seat_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("league_entity_id", name=op.f("pk_polity_leagues")),
    )
    op.create_table(
        "security_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("security_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("bought_price", sa.Integer(), nullable=False),
        sa.Column("on_margin", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_security_holdings_amount_min")),
        sa.CheckConstraint("bought_price >= 0", name=op.f("ck_security_holdings_bought_price_min")),
        sa.CheckConstraint("on_margin >= 0", name=op.f("ck_security_holdings_on_margin_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_security_holdings_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["security_id"], ["issued_securities.id"], name=op.f("fk_security_holdings_security_id_issued_securities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_holdings")),
    )
    with op.batch_alter_table("security_holdings", schema=None) as batch_op:
        batch_op.create_index("ix_security_holdings_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_security_holdings_security", ["security_id"], unique=False)

    op.create_table(
        "security_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("security_id", sa.Integer(), nullable=False),
        sa.Column("issuer_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_security_prices_epoch_min")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_security_prices_price_min")),
        sa.CheckConstraint("volume >= 0", name=op.f("ck_security_prices_volume_min")),
        sa.ForeignKeyConstraint(["issuer_node_id"], ["nodes.id"], name=op.f("fk_security_prices_issuer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["security_id"], ["issued_securities.id"], name=op.f("fk_security_prices_security_id_issued_securities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_prices")),
    )
    with op.batch_alter_table("security_prices", schema=None) as batch_op:
        batch_op.create_index("ix_security_prices_issuer", ["issuer_node_id"], unique=False)
        batch_op.create_index("ix_security_prices_security", ["security_id"], unique=False)

    with op.batch_alter_table("conditions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "cause",
                sa.Enum(
                    "age",
                    "diet",
                    "exposure",
                    "heredity",
                    "injury_aftermath",
                    "strain",
                    "unknown",
                    name="cause",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("kind_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_conditions_kind_id"), ["kind_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_conditions_kind_id_agentless_conditions"), "agentless_conditions", ["kind_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("conditions", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_conditions_kind_id_agentless_conditions"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_conditions_kind_id"))
        batch_op.drop_column("kind_id")
        batch_op.drop_column("cause")

    with op.batch_alter_table("security_prices", schema=None) as batch_op:
        batch_op.drop_index("ix_security_prices_security")
        batch_op.drop_index("ix_security_prices_issuer")

    op.drop_table("security_prices")
    with op.batch_alter_table("security_holdings", schema=None) as batch_op:
        batch_op.drop_index("ix_security_holdings_security")
        batch_op.drop_index("ix_security_holdings_holder")

    op.drop_table("security_holdings")
    op.drop_table("polity_leagues")
    with op.batch_alter_table("monetary_rates", schema=None) as batch_op:
        batch_op.drop_index("ix_monetary_rates_authority")

    op.drop_table("monetary_rates")
    with op.batch_alter_table("land_use_rules", schema=None) as batch_op:
        batch_op.drop_index("ix_land_use_rules_settlement")

    op.drop_table("land_use_rules")
    with op.batch_alter_table("issued_securities", schema=None) as batch_op:
        batch_op.drop_index("ix_issued_securities_issuer")
        batch_op.drop_index("ix_issued_securities_exchange")

    op.drop_table("issued_securities")
    with op.batch_alter_table("war_remnants", schema=None) as batch_op:
        batch_op.drop_index("ix_war_remnants_region")
        batch_op.drop_index(batch_op.f("ix_war_remnants_orbit_world_id"))

    op.drop_table("war_remnants")
    with op.batch_alter_table("sea_wave_coasts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sea_wave_coasts_wave_id"))
        batch_op.drop_index("ix_sea_wave_coasts_region")

    op.drop_table("sea_wave_coasts")
    with op.batch_alter_table("reckoning_measures", schema=None) as batch_op:
        batch_op.drop_index("ix_reckoning_measures_reckoning")

    op.drop_table("reckoning_measures")
    with op.batch_alter_table("reckoning_cases", schema=None) as batch_op:
        batch_op.drop_index("ix_reckoning_cases_reckoning")
        batch_op.drop_index("ix_reckoning_cases_accused")

    op.drop_table("reckoning_cases")
    with op.batch_alter_table("org_research", schema=None) as batch_op:
        batch_op.drop_index("ix_org_research_org")

    op.drop_table("org_research")
    with op.batch_alter_table("occupation_measures", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_occupation_measures_region_entity_id"))
        batch_op.drop_index("ix_occupation_measures_regime")

    op.drop_table("occupation_measures")
    with op.batch_alter_table("monetary_authorities", schema=None) as batch_op:
        batch_op.drop_index("ix_monetary_authorities_issuer")
        batch_op.drop_index("ix_monetary_authorities_holder")

    op.drop_table("monetary_authorities")
    with op.batch_alter_table("kin_rivalries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_kin_rivalries_second_node_id"))
        batch_op.drop_index("ix_kin_rivalries_first")
        batch_op.drop_index(batch_op.f("ix_kin_rivalries_dynamic_id"))

    op.drop_table("kin_rivalries")
    with op.batch_alter_table("kin_favours", schema=None) as batch_op:
        batch_op.drop_index("ix_kin_favours_parent")
        batch_op.drop_index(batch_op.f("ix_kin_favours_dynamic_id"))
        batch_op.drop_index(batch_op.f("ix_kin_favours_child_node_id"))

    op.drop_table("kin_favours")
    with op.batch_alter_table("kin_disownings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_kin_disownings_dynamic_id"))
        batch_op.drop_index("ix_kin_disownings_disowned")

    op.drop_table("kin_disownings")
    with op.batch_alter_table("kin_blends", schema=None) as batch_op:
        batch_op.drop_index("ix_kin_blends_member")
        batch_op.drop_index(batch_op.f("ix_kin_blends_dynamic_id"))

    op.drop_table("kin_blends")
    with op.batch_alter_table("interworld_migrations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_interworld_migrations_to_world_id"))
        batch_op.drop_index("ix_interworld_migrations_community")

    op.drop_table("interworld_migrations")
    with op.batch_alter_table("interworld_campaigns", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_interworld_campaigns_target_world_id"))
        batch_op.drop_index(batch_op.f("ix_interworld_campaigns_defender_entity_id"))
        batch_op.drop_index("ix_interworld_campaigns_attacker")

    op.drop_table("interworld_campaigns")
    with op.batch_alter_table("honours_held", schema=None) as batch_op:
        batch_op.drop_index("ix_honours_held_kind")
        batch_op.drop_index("ix_honours_held_holder")

    op.drop_table("honours_held")
    with op.batch_alter_table("elder_sway", schema=None) as batch_op:
        batch_op.drop_index("ix_elder_sway_elder")
        batch_op.drop_index(batch_op.f("ix_elder_sway_dynamic_id"))

    op.drop_table("elder_sway")
    with op.batch_alter_table("departures", schema=None) as batch_op:
        batch_op.drop_index("ix_departures_polity")
        batch_op.drop_index("ix_departures_holder")

    op.drop_table("departures")
    with op.batch_alter_table("collaborations", schema=None) as batch_op:
        batch_op.drop_index("ix_collaborations_regime")
        batch_op.drop_index("ix_collaborations_node")

    op.drop_table("collaborations")
    with op.batch_alter_table("wave_warnings", schema=None) as batch_op:
        batch_op.drop_index("ix_wave_warnings_region")

    op.drop_table("wave_warnings")
    with op.batch_alter_table("stock_exchanges", schema=None) as batch_op:
        batch_op.drop_index("ix_stock_exchanges_settlement")
        batch_op.drop_index("ix_stock_exchanges_owner")

    op.drop_table("stock_exchanges")
    with op.batch_alter_table("species_protections", schema=None) as batch_op:
        batch_op.drop_index("ix_species_protections_species")
        batch_op.drop_index(batch_op.f("ix_species_protections_holder_node_id"))

    op.drop_table("species_protections")
    with op.batch_alter_table("sea_waves", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sea_waves_world_id"))
        batch_op.drop_index(batch_op.f("ix_sea_waves_sea_region_id"))

    op.drop_table("sea_waves")
    with op.batch_alter_table("restorations", schema=None) as batch_op:
        batch_op.drop_index("ix_restorations_fallen")

    op.drop_table("restorations")
    with op.batch_alter_table("reckonings", schema=None) as batch_op:
        batch_op.drop_index("ix_reckonings_polity")

    op.drop_table("reckonings")
    with op.batch_alter_table("protected_areas", schema=None) as batch_op:
        batch_op.drop_index("ix_protected_areas_region")
        batch_op.drop_index(batch_op.f("ix_protected_areas_protector_node_id"))

    op.drop_table("protected_areas")
    with op.batch_alter_table("price_wars", schema=None) as batch_op:
        batch_op.drop_index("ix_price_wars_market")

    op.drop_table("price_wars")
    with op.batch_alter_table("org_seats", schema=None) as batch_op:
        batch_op.drop_index("ix_org_seats_member")

    op.drop_table("org_seats")
    with op.batch_alter_table("org_mergers", schema=None) as batch_op:
        batch_op.drop_index("ix_org_mergers_target")
        batch_op.drop_index("ix_org_mergers_acquirer")

    op.drop_table("org_mergers")
    op.drop_table("org_governance")
    with op.batch_alter_table("org_cliques", schema=None) as batch_op:
        batch_op.drop_index("ix_org_cliques_org")

    op.drop_table("org_cliques")
    with op.batch_alter_table("orbital_control", schema=None) as batch_op:
        batch_op.drop_index("ix_orbital_control_world")
        batch_op.drop_index(batch_op.f("ix_orbital_control_holder_entity_id"))

    op.drop_table("orbital_control")
    with op.batch_alter_table("occupation_regimes", schema=None) as batch_op:
        batch_op.drop_index("ix_occupation_regimes_region")
        batch_op.drop_index(batch_op.f("ix_occupation_regimes_occupier_entity_id"))

    op.drop_table("occupation_regimes")
    with op.batch_alter_table("municipal_services", schema=None) as batch_op:
        batch_op.drop_index("ix_municipal_services_settlement")

    op.drop_table("municipal_services")
    with op.batch_alter_table("mass_weapons", schema=None) as batch_op:
        batch_op.drop_index("ix_mass_weapons_holder")

    op.drop_table("mass_weapons")
    with op.batch_alter_table("market_structures", schema=None) as batch_op:
        batch_op.drop_index("ix_market_structures_market")

    op.drop_table("market_structures")
    with op.batch_alter_table("league_members", schema=None) as batch_op:
        batch_op.drop_index("ix_league_members_polity")

    op.drop_table("league_members")
    with op.batch_alter_table("league_decisions", schema=None) as batch_op:
        batch_op.drop_index("ix_league_decisions_league")

    op.drop_table("league_decisions")
    with op.batch_alter_table("leader_cults", schema=None) as batch_op:
        batch_op.drop_index("ix_leader_cults_polity")
        batch_op.drop_index("ix_leader_cults_leader")

    op.drop_table("leader_cults")
    with op.batch_alter_table("labour_disputes", schema=None) as batch_op:
        batch_op.drop_index("ix_labour_disputes_settlement")
        batch_op.drop_index("ix_labour_disputes_hirer")
        batch_op.drop_index("ix_labour_disputes_body")

    op.drop_table("labour_disputes")
    with op.batch_alter_table("labour_contracts", schema=None) as batch_op:
        batch_op.drop_index("ix_labour_contracts_hirer")
        batch_op.drop_index("ix_labour_contracts_body")

    op.drop_table("labour_contracts")
    with op.batch_alter_table("kin_dynamics", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_kin_dynamics_household_id"))
        batch_op.drop_index("ix_kin_dynamics_house")

    op.drop_table("kin_dynamics")
    with op.batch_alter_table("interpretations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_interpretations_second_party_id"))
        batch_op.drop_index(batch_op.f("ix_interpretations_interpreter_node_id"))
        batch_op.drop_index("ix_interpretations_event")

    op.drop_table("interpretations")
    with op.batch_alter_table("insolvency_cases", schema=None) as batch_op:
        batch_op.drop_index("ix_insolvency_cases_debtor")

    op.drop_table("insolvency_cases")
    with op.batch_alter_table("grave_goods", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_grave_goods_grave_entity_id"))

    op.drop_table("grave_goods")
    op.drop_table("god_readings")
    with op.batch_alter_table("fertility_uses", schema=None) as batch_op:
        batch_op.drop_index("ix_fertility_uses_user")

    op.drop_table("fertility_uses")
    op.drop_table("fertility_means")
    with op.batch_alter_table("feeling_spread", schema=None) as batch_op:
        batch_op.drop_index("ix_feeling_spread_settlement")
        batch_op.drop_index("ix_feeling_spread_household")

    op.drop_table("feeling_spread")
    op.drop_table("divine_conceptions")
    with op.batch_alter_table("deterrence_postures", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_deterrence_postures_toward_entity_id"))
        batch_op.drop_index("ix_deterrence_postures_holder")

    op.drop_table("deterrence_postures")
    with op.batch_alter_table("creature_groups", schema=None) as batch_op:
        batch_op.drop_index("ix_creature_groups_species")
        batch_op.drop_index("ix_creature_groups_region")

    op.drop_table("creature_groups")
    with op.batch_alter_table("conurbations", schema=None) as batch_op:
        batch_op.drop_index("ix_conurbations_core")

    op.drop_table("conurbations")
    op.drop_table("conservation_movements")
    with op.batch_alter_table("agentless_conditions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_agentless_conditions_world_id"))

    op.drop_table("agentless_conditions")
    op.drop_table("worker_bodies")
    with op.batch_alter_table("referendums", schema=None) as batch_op:
        batch_op.drop_index("ix_referendums_holder")

    op.drop_table("referendums")
    with op.batch_alter_table("honour_kinds", schema=None) as batch_op:
        batch_op.drop_index("ix_honour_kinds_conferrer")

    op.drop_table("honour_kinds")
    with op.batch_alter_table("cartels", schema=None) as batch_op:
        batch_op.drop_index("ix_cartels_commodity")

    op.drop_table("cartels")
    retype(False)
