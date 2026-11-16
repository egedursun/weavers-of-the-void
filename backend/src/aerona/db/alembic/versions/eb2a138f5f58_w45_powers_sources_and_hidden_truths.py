import sqlalchemy as sa
from alembic import op

revision = "eb2a138f5f58"
down_revision = "c4a1e9d2f7b3"
branch_labels = None
depends_on = None


SPELLTECHNIQUE_OLD = ("create", "perceive", "transform", "destroy", "control", "bind", "summon", "ward")
SPELLTECHNIQUE_NEW = (*SPELLTECHNIQUE_OLD, "drain", "mimic")
SPELLFORM_OLD = ("fire", "water", "air", "earth", "plant", "animal", "body", "mind", "image", "spirit", "time", "void", "death", "light")
SPELLFORM_NEW = (*SPELLFORM_OLD, "space", "force", "sound", "emotion", "fate", "machine", "information")
RITEEFFECTKIND_OLD = (
    "damage",
    "heal",
    "weather_change",
    "curse",
    "bless",
    "ward",
    "scry",
    "bind",
    "summon",
    "raise_dead",
    "fertility",
    "harvest_blessing",
    "seal_soul",
    "unseal_soul",
    "exorcise",
    "dispel",
    "longevity",
)
RITEEFFECTKIND_NEW = (
    *RITEEFFECTKIND_OLD,
    "move_target",
    "move_self",
    "push",
    "shape_matter",
    "read_record",
    "seize_machine",
    "alter_record",
    "sense_emotion",
    "sway_emotion",
    "turn_fortune",
    "drain_life",
    "drain_power",
    "copy_power",
    "project_self",
    "possess",
    "change_form",
    "conceal",
    "nullify",
    "hasten",
    "slow",
    "age",
    "renew",
    "foresee",
)
FORESIGHTSOURCE_OLD = ("power", "divination", "god")
FORESIGHTSOURCE_NEW = (*FORESIGHTSOURCE_OLD, "made_oracle")
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
)
LAWKIND_NEW = (*LAWKIND_OLD, "power_law", "source_law")
GATHERINGKIND_OLD = (
    "feast",
    "wedding",
    "funeral",
    "coronation",
    "tournament",
    "hunt",
    "pilgrimage",
    "council",
    "summit",
    "festival",
    "fair",
    "games",
    "performance",
    "trial",
    "execution",
    "procession",
    "milestone",
    "wake",
    "examination",
    "election",
    "rally",
    "strike",
    "convention",
    "launch",
    "broadcast",
)
GATHERINGKIND_NEW = (*GATHERINGKIND_OLD, "testing")
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
)
CLAUSEKIND_NEW = (*CLAUSEKIND_OLD, "no_mind_compulsion", "no_plague_powers")
UNITKIND_OLD = (
    "levy",
    "line_infantry",
    "heavy_infantry",
    "shield_infantry",
    "pike_infantry",
    "light_infantry",
    "shock_infantry",
    "guard_infantry",
    "marines",
    "slingers",
    "archers",
    "crossbow_infantry",
    "javelineers",
    "gunners",
    "grenadiers",
    "light_cavalry",
    "heavy_cavalry",
    "mounted_archers",
    "mounted_gunners",
    "beast_riders",
    "sky_riders",
    "chariots",
    "vehicle_crew",
    "siege_crew",
    "artillery_crew",
    "naval_crew",
    "sky_crew",
    "void_crew",
    "war_beasts",
    "bound_beasts",
    "sappers",
    "engineers",
    "battle_casters",
    "support_casters",
    "summoners",
    "constructs",
    "summoned_host",
    "mechanised_infantry",
    "special_forces",
    "partisans",
    "peacekeepers",
    "medics",
    "drone_operators",
    "signals_troops",
    "powered_troopers",
    "drop_troops",
    "pilots",
)
UNITKIND_NEW = (*UNITKIND_OLD, "gifted", "dampeners", "detectors")
CRIMEKIND_OLD = (
    "theft",
    "blasphemy",
    "treason",
    "murder",
    "desertion",
    "witchcraft",
    "mind_theft",
    "unlicensed_copying",
    "forced_edit",
    "erasure",
    "machine_seizure",
    "impersonation",
)
CRIMEKIND_NEW = (*CRIMEKIND_OLD, "mind_compulsion")
MEMORYKIND_OLD = (
    "harmed_me",
    "killed_kin",
    "saved_me",
    "betrayed_me",
    "kept_oath",
    "broke_oath",
    "maimed_me",
    "humiliated_me",
    "gifted_me",
    "converted_me",
    "conquered_us",
    "freed_us",
    "famine_aid",
    "desecrated_holy",
    "married_into",
    "fought_us",
    "traded_with",
    "allied_with",
    "made_peace",
    "demanded_tribute",
    "cheated_us",
    "spied_on_us",
    "envied",
    "failed_to_heal",
    "taught_me",
    "held_captive",
    "lamented",
    "divine_will",
    "goodwill",
    "ill_will",
    "long_history",
    "dreads",
    "formative",
    "stole_faithful",
    "aided_chosen",
    "memory_gap",
)
MEMORYKIND_NEW = (*MEMORYKIND_OLD, "compelled_me")
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
)
HARMCAUSE_NEW = (*HARMCAUSE_OLD, "power")
RETYPED = (
    ("rite_grammar", "technique", "technique", SPELLTECHNIQUE_OLD, SPELLTECHNIQUE_NEW, False),
    ("vis_stocks", "form", "form", SPELLFORM_OLD, SPELLFORM_NEW, False),
    ("law_upkeep", "vis_form", "vis_form", SPELLFORM_OLD, SPELLFORM_NEW, True),
    ("longevity", "form", "form", SPELLFORM_OLD, SPELLFORM_NEW, False),
    ("rite_grammar", "form", "form", SPELLFORM_OLD, SPELLFORM_NEW, False),
    ("item_enchantments", "effect", "effect", RITEEFFECTKIND_OLD, RITEEFFECTKIND_NEW, False),
    ("rite_effects", "effect", "effect", RITEEFFECTKIND_OLD, RITEEFFECTKIND_NEW, False),
    ("foresights", "source", "source", FORESIGHTSOURCE_OLD, FORESIGHTSOURCE_NEW, False),
    ("law_profiles", "kind", "kind", LAWKIND_OLD, LAWKIND_NEW, False),
    ("law_proposals", "kind", "kind", LAWKIND_OLD, LAWKIND_NEW, False),
    ("gatherings", "kind", "kind", GATHERINGKIND_OLD, GATHERINGKIND_NEW, False),
    ("treaty_clauses", "kind", "kind", CLAUSEKIND_OLD, CLAUSEKIND_NEW, False),
    ("unit_designs", "base_kind", "base_kind", UNITKIND_OLD, UNITKIND_NEW, False),
    ("army_units", "kind", "kind", UNITKIND_OLD, UNITKIND_NEW, False),
    ("battle_stacks", "kind", "kind", UNITKIND_OLD, UNITKIND_NEW, False),
    ("crime_cases", "crime", "crime", CRIMEKIND_OLD, CRIMEKIND_NEW, False),
    ("precedents", "crime", "crime", CRIMEKIND_OLD, CRIMEKIND_NEW, False),
    ("sentences", "crime", "crime", CRIMEKIND_OLD, CRIMEKIND_NEW, False),
    ("memories", "kind", "kind", MEMORYKIND_OLD, MEMORYKIND_NEW, False),
    ("conditions", "source", "source", HARMCAUSE_OLD, HARMCAUSE_NEW, False),
    ("injuries", "cause_kind", "cause_kind", HARMCAUSE_OLD, HARMCAUSE_NEW, False),
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
        "magic_systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "structure",
            sa.Enum("rite", "innate", "granted", "bonded", "crafted", "mixed", name="structure", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("predictability", sa.Integer(), nullable=False),
        sa.Column("prevalence", sa.Integer(), nullable=False),
        sa.Column("cost_severity", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.Enum("overt", "subtle", "hidden", name="visibility", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "access",
            sa.Enum(
                "anyone", "gifted", "trained", "granted", "bloodline", "bonded", "made", name="access", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "learnability",
            sa.Enum("anyone", "gifted_only", "granted_only", "cannot_be_taught", name="learnability", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost_severity BETWEEN 0 AND 100", name=op.f("ck_magic_systems_cost_severity_range")),
        sa.CheckConstraint("predictability BETWEEN 0 AND 100", name=op.f("ck_magic_systems_predictability_range")),
        sa.CheckConstraint("prevalence BETWEEN 0 AND 100", name=op.f("ck_magic_systems_prevalence_range")),
        sa.ForeignKeyConstraint(["scope_node_id"], ["nodes.id"], name=op.f("fk_magic_systems_scope_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_magic_systems")),
    )
    with op.batch_alter_table("magic_systems", schema=None) as batch_op:
        batch_op.create_index("ix_magic_systems_scope", ["scope_node_id"], unique=False)

    op.create_table(
        "power_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "drawn_from",
            sa.Enum(
                "self",
                "others",
                "place",
                "sky",
                "surroundings",
                "made_things",
                "patron",
                "bond",
                "story",
                "void",
                "substance",
                "life",
                "death",
                "dream",
                "emotion",
                name="drawn_from",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "renewal",
            sa.Enum(
                "rest",
                "time",
                "season",
                "sky_cycle",
                "worship",
                "feeding",
                "taking",
                "vows_kept",
                "return_to_place",
                "none",
                name="renewal",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "access",
            sa.Enum(
                "anyone", "gifted", "trained", "granted", "bloodline", "bonded", "made", name="access", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("visibility", sa.Enum("overt", "subtle", "hidden", name="visibility", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("stability", sa.Integer(), nullable=False),
        sa.Column(
            "built_in",
            sa.Enum("ley", "divine", "blood", "soul", "reagent", "void", name="built_in", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("stability BETWEEN 0 AND 100", name=op.f("ck_power_sources_stability_range")),
        sa.ForeignKeyConstraint(["scope_node_id"], ["nodes.id"], name=op.f("fk_power_sources_scope_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_sources")),
    )
    with op.batch_alter_table("power_sources", schema=None) as batch_op:
        batch_op.create_index("ix_power_sources_scope", ["scope_node_id"], unique=False)

    op.create_table(
        "magic_system_grammar",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column(
            "technique",
            sa.Enum(
                "create",
                "perceive",
                "transform",
                "destroy",
                "control",
                "bind",
                "summon",
                "ward",
                "drain",
                "mimic",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                "space",
                "force",
                "sound",
                "emotion",
                "fate",
                "machine",
                "information",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["system_id"], ["magic_systems.id"], name=op.f("fk_magic_system_grammar_system_id_magic_systems"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_magic_system_grammar")),
        sa.UniqueConstraint("system_id", "technique", "form", name="uq_magic_system_grammar"),
    )
    with op.batch_alter_table("magic_system_grammar", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_magic_system_grammar_system_id"), ["system_id"], unique=False)

    op.create_table(
        "magic_system_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_system_id", sa.Integer(), nullable=False),
        sa.Column("second_system_id", sa.Integer(), nullable=False),
        sa.Column(
            "relation",
            sa.Enum("opposes", "complements", "same_root", "unaware", name="relation", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["first_system_id"], ["magic_systems.id"], name=op.f("fk_magic_system_links_first_system_id_magic_systems"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["second_system_id"], ["magic_systems.id"], name=op.f("fk_magic_system_links_second_system_id_magic_systems"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_magic_system_links")),
        sa.UniqueConstraint("first_system_id", "second_system_id", name="uq_magic_system_links"),
    )
    with op.batch_alter_table("magic_system_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_magic_system_links_first_system_id"), ["first_system_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_magic_system_links_second_system_id"), ["second_system_id"], unique=False)

    op.create_table(
        "magic_system_restrictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "only_in_place",
                "only_at_time",
                "only_against",
                "spoken_vow",
                "price_each_use",
                "never_on_self",
                "forbidden_act",
                "must_be_seen",
                "must_be_unseen",
                "must_touch",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("detail", sa.String(length=120), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["system_id"], ["magic_systems.id"], name=op.f("fk_magic_system_restrictions_system_id_magic_systems"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_magic_system_restrictions")),
    )
    with op.batch_alter_table("magic_system_restrictions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_magic_system_restrictions_system_id"), ["system_id"], unique=False)

    op.create_table(
        "magic_system_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_magic_system_sources_source_id_power_sources"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["system_id"], ["magic_systems.id"], name=op.f("fk_magic_system_sources_system_id_magic_systems"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_magic_system_sources")),
        sa.UniqueConstraint("system_id", "source_id", name="uq_magic_system_sources"),
    )
    with op.batch_alter_table("magic_system_sources", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_magic_system_sources_source_id"), ["source_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_magic_system_sources_system_id"), ["system_id"], unique=False)

    op.create_table(
        "power_source_costs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "cost",
            sa.Enum(
                "essence",
                "hp",
                "fatigue",
                "strain",
                "lifespan",
                "memory",
                "emotion",
                "sanity",
                "reagent",
                "material",
                "vis",
                "belief",
                "renown",
                "oath_standing",
                "debt",
                "soul",
                "time",
                "surroundings",
                "luck",
                "warping",
                "none",
                name="cost",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_power_source_costs_weight_range")),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_power_source_costs_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_source_costs")),
        sa.UniqueConstraint("source_id", "cost", name="uq_power_source_costs"),
    )
    with op.batch_alter_table("power_source_costs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_source_costs_source_id"), ["source_id"], unique=False)

    op.create_table(
        "power_source_hazards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "hazard",
            sa.Enum(
                "injury",
                "madness",
                "leak",
                "escape",
                "depletion",
                "warping",
                "burnout",
                "dependency",
                "attention",
                name="hazard",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_power_source_hazards_weight_range")),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_power_source_hazards_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_source_hazards")),
        sa.UniqueConstraint("source_id", "hazard", name="uq_power_source_hazards"),
    )
    with op.batch_alter_table("power_source_hazards", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_source_hazards_source_id"), ["source_id"], unique=False)

    op.create_table(
        "power_source_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_source_id", sa.Integer(), nullable=False),
        sa.Column("second_source_id", sa.Integer(), nullable=False),
        sa.Column(
            "relation",
            sa.Enum("suppresses", "amplifies", "converts_into", "conflicts", name="relation", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_power_source_interactions_strength_range")),
        sa.ForeignKeyConstraint(
            ["first_source_id"], ["power_sources.id"], name=op.f("fk_power_source_interactions_first_source_id_power_sources"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["second_source_id"], ["power_sources.id"], name=op.f("fk_power_source_interactions_second_source_id_power_sources"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_source_interactions")),
        sa.UniqueConstraint("first_source_id", "second_source_id", name="uq_power_source_interactions"),
    )
    with op.batch_alter_table("power_source_interactions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_source_interactions_first_source_id"), ["first_source_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_power_source_interactions_second_source_id"), ["second_source_id"], unique=False)

    op.create_table(
        "power_source_knowledge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("learned_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 100", name=op.f("ck_power_source_knowledge_level_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_power_source_knowledge_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_power_source_knowledge_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_source_knowledge")),
        sa.UniqueConstraint("source_id", "holder_node_id", name="uq_power_source_knowledge"),
    )
    with op.batch_alter_table("power_source_knowledge", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_source_knowledge_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_power_source_knowledge_source_id"), ["source_id"], unique=False)

    op.create_table(
        "power_source_resistances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "resistance",
            sa.Enum(
                "will",
                "discipline",
                "faith",
                "sanctity",
                "material",
                "dampener",
                "distance",
                "counter_source",
                "none",
                name="resistance",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "material",
            sa.Enum(
                "wood",
                "bone",
                "hide",
                "leather",
                "cloth",
                "stone",
                "flint",
                "obsidian",
                "copper",
                "tin",
                "bronze",
                "iron",
                "steel",
                "silver",
                "gold",
                "glass",
                "crystal",
                "ivory",
                "chitin",
                "dragonbone",
                "star_metal",
                "void_glass",
                "godflesh",
                "living_wood",
                "salt",
                "amber",
                "lead",
                "skysteel",
                "sulfur",
                "clay",
                "gems",
                "mud_brick",
                "fired_brick",
                "dressed_stone",
                "rubble",
                "lime_mortar",
                "hydraulic_concrete",
                "thatch",
                "tile",
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_power_source_resistances_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_source_resistances")),
        sa.UniqueConstraint("source_id", "resistance", name="uq_power_source_resistances"),
    )
    with op.batch_alter_table("power_source_resistances", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_source_resistances_source_id"), ["source_id"], unique=False)

    op.create_table(
        "powers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column(
            "technique",
            sa.Enum(
                "create",
                "perceive",
                "transform",
                "destroy",
                "control",
                "bind",
                "summon",
                "ward",
                "drain",
                "mimic",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                "space",
                "force",
                "sound",
                "emotion",
                "fate",
                "machine",
                "information",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("range_km", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("on_others", sa.Boolean(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("control", sa.Integer(), nullable=False),
        sa.Column(
            "origin",
            sa.Enum(
                "born",
                "awakened",
                "exposure",
                "granted",
                "bonded",
                "discipline",
                "made",
                "grown",
                "bloodline",
                "held",
                name="origin",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.Enum(
                "latent",
                "emerging",
                "active",
                "strained",
                "burned_out",
                "suppressed",
                "lost",
                name="state",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("visibility", sa.Enum("overt", "subtle", "hidden", name="visibility", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strain", sa.Integer(), nullable=False),
        sa.Column("strain_cap", sa.Integer(), nullable=False),
        sa.Column("granted_by_node_id", sa.Integer(), nullable=True),
        sa.Column("item_node_id", sa.Integer(), nullable=True),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column("gained_epoch", sa.Integer(), nullable=False),
        sa.Column("last_used_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("control BETWEEN 0 AND 100", name=op.f("ck_powers_control_range")),
        sa.CheckConstraint("duration_days >= 0", name=op.f("ck_powers_duration_days_min")),
        sa.CheckConstraint("range_km >= 0", name=op.f("ck_powers_range_km_min")),
        sa.CheckConstraint("strain >= 0", name=op.f("ck_powers_strain_min")),
        sa.CheckConstraint("strain_cap >= 1", name=op.f("ck_powers_strain_cap_min")),
        sa.CheckConstraint("strength BETWEEN 1 AND 10", name=op.f("ck_powers_strength_range")),
        sa.ForeignKeyConstraint(["granted_by_node_id"], ["nodes.id"], name=op.f("fk_powers_granted_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_powers_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_node_id"], ["nodes.id"], name=op.f("fk_powers_item_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_powers_source_id_power_sources"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["system_id"], ["magic_systems.id"], name=op.f("fk_powers_system_id_magic_systems"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_powers")),
    )
    with op.batch_alter_table("powers", schema=None) as batch_op:
        batch_op.create_index("ix_powers_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "source_tides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("cycle", sa.Enum("season", "sky", "epoch", "authored", name="cycle", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("amplitude", sa.Integer(), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amplitude BETWEEN 0 AND 100", name=op.f("ck_source_tides_amplitude_range")),
        sa.CheckConstraint("period >= 1", name=op.f("ck_source_tides_period_min")),
        sa.CheckConstraint("phase >= 0", name=op.f("ck_source_tides_phase_min")),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_source_tides_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_tides")),
    )
    with op.batch_alter_table("source_tides", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_source_tides_source_id"), ["source_id"], unique=False)

    op.create_table(
        "power_restrictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("power_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "only_in_place",
                "only_at_time",
                "only_against",
                "spoken_vow",
                "price_each_use",
                "never_on_self",
                "forbidden_act",
                "must_be_seen",
                "must_be_unseen",
                "must_touch",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("ref_node_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(length=120), nullable=True),
        sa.Column("strength_gain_pct", sa.Integer(), nullable=False),
        sa.Column("broken", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength_gain_pct BETWEEN 0 AND 100", name=op.f("ck_power_restrictions_strength_gain_pct_range")),
        sa.ForeignKeyConstraint(["power_id"], ["powers.id"], name=op.f("fk_power_restrictions_power_id_powers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ref_node_id"], ["nodes.id"], name=op.f("fk_power_restrictions_ref_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_restrictions")),
    )
    with op.batch_alter_table("power_restrictions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_restrictions_power_id"), ["power_id"], unique=False)

    op.create_table(
        "power_spans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("power_id", sa.Integer(), nullable=True),
        sa.Column("user_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "effect",
            sa.Enum(
                "damage",
                "heal",
                "weather_change",
                "curse",
                "bless",
                "ward",
                "scry",
                "bind",
                "summon",
                "raise_dead",
                "fertility",
                "harvest_blessing",
                "seal_soul",
                "unseal_soul",
                "exorcise",
                "dispel",
                "longevity",
                "move_target",
                "move_self",
                "push",
                "shape_matter",
                "read_record",
                "seize_machine",
                "alter_record",
                "sense_emotion",
                "sway_emotion",
                "turn_fortune",
                "drain_life",
                "drain_power",
                "copy_power",
                "project_self",
                "possess",
                "change_form",
                "conceal",
                "nullify",
                "hasten",
                "slow",
                "age",
                "renew",
                "foresee",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("prior", sa.Integer(), nullable=False),
        sa.Column("began_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("until_epoch >= 0", name=op.f("ck_power_spans_until_epoch_min")),
        sa.ForeignKeyConstraint(["power_id"], ["powers.id"], name=op.f("fk_power_spans_power_id_powers"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_power_spans_target_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_node_id"], ["nodes.id"], name=op.f("fk_power_spans_user_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_spans")),
    )
    with op.batch_alter_table("power_spans", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_spans_target_node_id"), ["target_node_id"], unique=False)
        batch_op.create_index("ix_power_spans_until", ["until_epoch"], unique=False)
        batch_op.create_index(batch_op.f("ix_power_spans_user_node_id"), ["user_node_id"], unique=False)

    op.create_table(
        "power_triggers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("power_id", sa.Integer(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum("stress", "emotion", "danger", "will", "contact", "place", "time", name="trigger", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["power_id"], ["powers.id"], name=op.f("fk_power_triggers_power_id_powers"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_triggers")),
        sa.UniqueConstraint("power_id", "trigger", name="uq_power_triggers"),
    )
    with op.batch_alter_table("power_triggers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_triggers_power_id"), ["power_id"], unique=False)

    op.create_table(
        "gifted_attitudes",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "attitude",
            sa.Enum("honoured", "feared", "persecuted", "regulated", "ordinary", name="attitude", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("gifted_share", sa.Integer(), nullable=False),
        sa.Column("registered_share", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("gifted_share BETWEEN 0 AND 100", name=op.f("ck_gifted_attitudes_gifted_share_range")),
        sa.CheckConstraint("registered_share BETWEEN 0 AND 100", name=op.f("ck_gifted_attitudes_registered_share_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_gifted_attitudes_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_gifted_attitudes")),
    )
    op.create_table(
        "hidden_truths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "existence",
                "nature",
                "presence",
                "power",
                "event",
                "origin",
                "awakening",
                "programme",
                "cosmic",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "hidden_from",
            sa.Enum(
                "everyone",
                "a_people",
                "a_polity",
                "the_uninitiated",
                "a_world",
                "the_cosmos",
                name="hidden_from",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("scope_node_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("by_oath", sa.Boolean(), nullable=False),
        sa.Column("by_law", sa.Boolean(), nullable=False),
        sa.Column("by_memory_removal", sa.Boolean(), nullable=False),
        sa.Column("by_cover_story", sa.Boolean(), nullable=False),
        sa.Column("by_discrediting", sa.Boolean(), nullable=False),
        sa.Column("by_isolation", sa.Boolean(), nullable=False),
        sa.Column("by_passing", sa.Boolean(), nullable=False),
        sa.Column("by_silencing", sa.Boolean(), nullable=False),
        sa.Column("by_neglect", sa.Boolean(), nullable=False),
        sa.Column("by_nature", sa.Boolean(), nullable=False),
        sa.Column("sanity_cost", sa.Integer(), nullable=False),
        sa.Column("accord_entity_id", sa.Integer(), nullable=True),
        sa.Column("revealed", sa.Boolean(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("tended_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("sanity_cost BETWEEN 0 AND 100", name=op.f("ck_hidden_truths_sanity_cost_range")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_hidden_truths_strength_range")),
        sa.ForeignKeyConstraint(["accord_entity_id"], ["entities.id"], name=op.f("fk_hidden_truths_accord_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scope_node_id"], ["nodes.id"], name=op.f("fk_hidden_truths_scope_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_hidden_truths_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hidden_truths")),
    )
    with op.batch_alter_table("hidden_truths", schema=None) as batch_op:
        batch_op.create_index("ix_hidden_truths_subject", ["subject_node_id"], unique=False)

    op.create_table(
        "power_registry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("licensed", sa.Boolean(), nullable=False),
        sa.Column("conscripted", sa.Boolean(), nullable=False),
        sa.Column("registered_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_power_registry_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_power_registry_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_power_registry")),
        sa.UniqueConstraint("polity_entity_id", "holder_node_id", name="uq_power_registry"),
    )
    with op.batch_alter_table("power_registry", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_power_registry_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_power_registry_polity_entity_id"), ["polity_entity_id"], unique=False)

    op.create_table(
        "source_density",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("density", sa.Integer(), nullable=False),
        sa.Column("base_density", sa.Integer(), nullable=False),
        sa.Column("renewal_pct", sa.Integer(), nullable=False),
        sa.Column("last_drawn_epoch", sa.Integer(), nullable=True),
        sa.Column("depleted", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("base_density BETWEEN 0 AND 100", name=op.f("ck_source_density_base_density_range")),
        sa.CheckConstraint("density BETWEEN 0 AND 100", name=op.f("ck_source_density_density_range")),
        sa.CheckConstraint("renewal_pct BETWEEN 0 AND 100", name=op.f("ck_source_density_renewal_pct_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_source_density_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_source_density_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_density")),
        sa.UniqueConstraint("region_entity_id", "source_id", name="uq_source_density"),
    )
    with op.batch_alter_table("source_density", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_source_density_region_entity_id"), ["region_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_source_density_source_id"), ["source_id"], unique=False)

    op.create_table(
        "source_laws",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Enum("free", "licensed", "banned", name="level", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_source_laws_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_source_laws_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_laws")),
        sa.UniqueConstraint("polity_entity_id", "source_id", name="uq_source_laws"),
    )
    with op.batch_alter_table("source_laws", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_source_laws_polity_entity_id"), ["polity_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_source_laws_source_id"), ["source_id"], unique=False)

    op.create_table(
        "source_stances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum("sacred", "tool", "forbidden", "suspect", "silent", name="stance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_source_stances_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["power_sources.id"], name=op.f("fk_source_stances_source_id_power_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_stances")),
        sa.UniqueConstraint("cult_entity_id", "source_id", name="uq_source_stances"),
    )
    with op.batch_alter_table("source_stances", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_source_stances_cult_entity_id"), ["cult_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_source_stances_source_id"), ["source_id"], unique=False)

    op.create_table(
        "breaches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("truth_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "overt_use",
                "witness",
                "defector",
                "investigator",
                "accident",
                "war",
                "record_leak",
                "intrusion",
                "revelation_by_god",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("witnesses", sa.Integer(), nullable=False),
        sa.Column("witness_node_ids", sa.JSON(), nullable=False),
        sa.Column("place_node_id", sa.Integer(), nullable=True),
        sa.Column("spread", sa.Integer(), nullable=False),
        sa.Column(
            "response",
            sa.Enum(
                "none",
                "cover_story",
                "memory_removal",
                "discrediting",
                "law",
                "silencing",
                name="response",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.CheckConstraint("spread BETWEEN 0 AND 100", name=op.f("ck_breaches_spread_range")),
        sa.CheckConstraint("witnesses >= 0", name=op.f("ck_breaches_witnesses_min")),
        sa.ForeignKeyConstraint(["place_node_id"], ["nodes.id"], name=op.f("fk_breaches_place_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["truth_id"], ["hidden_truths.id"], name=op.f("fk_breaches_truth_id_hidden_truths"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_breaches")),
    )
    with op.batch_alter_table("breaches", schema=None) as batch_op:
        batch_op.create_index("ix_breaches_truth", ["truth_id"], unique=False)

    op.create_table(
        "public_knowledge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("truth_id", sa.Integer(), nullable=False),
        sa.Column("population_node_id", sa.Integer(), nullable=False),
        sa.Column("know_pct", sa.Integer(), nullable=False),
        sa.Column("believe_pct", sa.Integer(), nullable=False),
        sa.Column(
            "attitude",
            sa.Enum(
                "unknown",
                "rumoured",
                "denied",
                "feared",
                "revered",
                "accepted",
                "exploited",
                name="attitude",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("revealed_epoch", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("believe_pct BETWEEN 0 AND 100", name=op.f("ck_public_knowledge_believe_pct_range")),
        sa.CheckConstraint("know_pct BETWEEN 0 AND 100", name=op.f("ck_public_knowledge_know_pct_range")),
        sa.ForeignKeyConstraint(["population_node_id"], ["nodes.id"], name=op.f("fk_public_knowledge_population_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["truth_id"], ["hidden_truths.id"], name=op.f("fk_public_knowledge_truth_id_hidden_truths"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_public_knowledge")),
        sa.UniqueConstraint("truth_id", "population_node_id", name="uq_public_knowledge"),
    )
    with op.batch_alter_table("public_knowledge", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_public_knowledge_population_node_id"), ["population_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_public_knowledge_truth_id"), ["truth_id"], unique=False)

    op.create_table(
        "truth_keepers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("truth_id", sa.Integer(), nullable=False),
        sa.Column("keeper_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("enforcer", "guardian", "member", "patron", name="role", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["keeper_node_id"], ["nodes.id"], name=op.f("fk_truth_keepers_keeper_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["truth_id"], ["hidden_truths.id"], name=op.f("fk_truth_keepers_truth_id_hidden_truths"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_truth_keepers")),
        sa.UniqueConstraint("truth_id", "keeper_node_id", name="uq_truth_keepers"),
    )
    with op.batch_alter_table("truth_keepers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_truth_keepers_keeper_node_id"), ["keeper_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_truth_keepers_truth_id"), ["truth_id"], unique=False)

    op.create_table(
        "truth_seekers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("truth_id", sa.Integer(), nullable=False),
        sa.Column("seeker_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "aim",
            sa.Enum(
                "expose", "exploit", "destroy_the_hidden", "join_the_hidden", "understand", name="aim", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("began_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_truth_seekers_progress_range")),
        sa.ForeignKeyConstraint(["seeker_node_id"], ["nodes.id"], name=op.f("fk_truth_seekers_seeker_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["truth_id"], ["hidden_truths.id"], name=op.f("fk_truth_seekers_truth_id_hidden_truths"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_truth_seekers")),
        sa.UniqueConstraint("truth_id", "seeker_node_id", name="uq_truth_seekers"),
    )
    with op.batch_alter_table("truth_seekers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_truth_seekers_seeker_node_id"), ["seeker_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_truth_seekers_truth_id"), ["truth_id"], unique=False)

    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "power_stance",
                sa.Enum("sacred", "tool", "forbidden", "suspect", "silent", name="power_stance", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="silent",
            )
        )

    with op.batch_alter_table("equipment_models", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "power_effect",
                sa.Enum(
                    "amplify",
                    "dampen",
                    "awaken",
                    "stabilise",
                    "extend_range",
                    "shield",
                    "detect",
                    name="power_effect",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )

    with op.batch_alter_table("foresights", schema=None) as batch_op:
        batch_op.add_column(sa.Column("power_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("strain_cost", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key(batch_op.f("fk_foresights_power_id_powers"), "powers", ["power_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("house_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "bloodline_rule",
                sa.Enum("none", "eldest", "all_children", "skipped", name="bloodline_rule", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="none",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("house_profiles", schema=None) as batch_op:
        batch_op.drop_constraint("bloodline_rule", type_="check")
        batch_op.drop_column("bloodline_rule")

    with op.batch_alter_table("foresights", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_foresights_power_id_powers"), type_="foreignkey")
        batch_op.drop_column("strain_cost")
        batch_op.drop_column("power_id")

    with op.batch_alter_table("equipment_models", schema=None) as batch_op:
        batch_op.drop_constraint("power_effect", type_="check")
        batch_op.drop_column("power_effect")

    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.drop_constraint("power_stance", type_="check")
        batch_op.drop_column("power_stance")

    with op.batch_alter_table("truth_seekers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_truth_seekers_truth_id"))
        batch_op.drop_index(batch_op.f("ix_truth_seekers_seeker_node_id"))

    op.drop_table("truth_seekers")
    with op.batch_alter_table("truth_keepers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_truth_keepers_truth_id"))
        batch_op.drop_index(batch_op.f("ix_truth_keepers_keeper_node_id"))

    op.drop_table("truth_keepers")
    with op.batch_alter_table("public_knowledge", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_public_knowledge_truth_id"))
        batch_op.drop_index(batch_op.f("ix_public_knowledge_population_node_id"))

    op.drop_table("public_knowledge")
    with op.batch_alter_table("breaches", schema=None) as batch_op:
        batch_op.drop_index("ix_breaches_truth")

    op.drop_table("breaches")
    with op.batch_alter_table("source_stances", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_source_stances_source_id"))
        batch_op.drop_index(batch_op.f("ix_source_stances_cult_entity_id"))

    op.drop_table("source_stances")
    with op.batch_alter_table("source_laws", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_source_laws_source_id"))
        batch_op.drop_index(batch_op.f("ix_source_laws_polity_entity_id"))

    op.drop_table("source_laws")
    with op.batch_alter_table("source_density", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_source_density_source_id"))
        batch_op.drop_index(batch_op.f("ix_source_density_region_entity_id"))

    op.drop_table("source_density")
    with op.batch_alter_table("power_registry", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_registry_polity_entity_id"))
        batch_op.drop_index(batch_op.f("ix_power_registry_holder_node_id"))

    op.drop_table("power_registry")
    with op.batch_alter_table("hidden_truths", schema=None) as batch_op:
        batch_op.drop_index("ix_hidden_truths_subject")

    op.drop_table("hidden_truths")
    op.drop_table("gifted_attitudes")
    with op.batch_alter_table("power_triggers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_triggers_power_id"))

    op.drop_table("power_triggers")
    with op.batch_alter_table("power_spans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_spans_user_node_id"))
        batch_op.drop_index("ix_power_spans_until")
        batch_op.drop_index(batch_op.f("ix_power_spans_target_node_id"))

    op.drop_table("power_spans")
    with op.batch_alter_table("power_restrictions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_restrictions_power_id"))

    op.drop_table("power_restrictions")
    with op.batch_alter_table("source_tides", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_source_tides_source_id"))

    op.drop_table("source_tides")
    with op.batch_alter_table("powers", schema=None) as batch_op:
        batch_op.drop_index("ix_powers_holder")

    op.drop_table("powers")
    with op.batch_alter_table("power_source_resistances", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_source_resistances_source_id"))

    op.drop_table("power_source_resistances")
    with op.batch_alter_table("power_source_knowledge", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_source_knowledge_source_id"))
        batch_op.drop_index(batch_op.f("ix_power_source_knowledge_holder_node_id"))

    op.drop_table("power_source_knowledge")
    with op.batch_alter_table("power_source_interactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_source_interactions_second_source_id"))
        batch_op.drop_index(batch_op.f("ix_power_source_interactions_first_source_id"))

    op.drop_table("power_source_interactions")
    with op.batch_alter_table("power_source_hazards", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_source_hazards_source_id"))

    op.drop_table("power_source_hazards")
    with op.batch_alter_table("power_source_costs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_power_source_costs_source_id"))

    op.drop_table("power_source_costs")
    with op.batch_alter_table("magic_system_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_magic_system_sources_system_id"))
        batch_op.drop_index(batch_op.f("ix_magic_system_sources_source_id"))

    op.drop_table("magic_system_sources")
    with op.batch_alter_table("magic_system_restrictions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_magic_system_restrictions_system_id"))

    op.drop_table("magic_system_restrictions")
    with op.batch_alter_table("magic_system_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_magic_system_links_second_system_id"))
        batch_op.drop_index(batch_op.f("ix_magic_system_links_first_system_id"))

    op.drop_table("magic_system_links")
    with op.batch_alter_table("magic_system_grammar", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_magic_system_grammar_system_id"))

    op.drop_table("magic_system_grammar")
    with op.batch_alter_table("power_sources", schema=None) as batch_op:
        batch_op.drop_index("ix_power_sources_scope")

    op.drop_table("power_sources")
    with op.batch_alter_table("magic_systems", schema=None) as batch_op:
        batch_op.drop_index("ix_magic_systems_scope")

    op.drop_table("magic_systems")
    retype(False)
