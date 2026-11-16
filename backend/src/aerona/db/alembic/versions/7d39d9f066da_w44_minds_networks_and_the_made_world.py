import sqlalchemy as sa
from alembic import op

revision = "7d39d9f066da"
down_revision = "b8dde3ec2222"
branch_labels = None
depends_on = None


BOND_OLD = (
    "inside",
    "lives_in",
    "worships",
    "enemy",
    "ally",
    "descends_from",
    "protects",
    "rules",
    "owns",
    "beat",
    "killed",
    "cursed",
    "blessed",
    "source_of",
    "tells_of",
    "destroyed",
    "loves",
    "fears",
    "hunts",
    "trades_with",
    "prophesies",
    "caused",
    "celebrates",
    "forbids",
    "speaks",
    "produced",
    "built",
    "migrated_to",
    "discovered",
    "soul_descended_to",
    "party_to",
    "member_of",
    "knows",
    "pays_tribute",
    "related",
    "holds_captive",
    "spy_network",
    "pursues",
    "companion",
    "pet_of",
    "rival",
    "apprentice_of",
    "commands",
    "part_of",
    "passenger_of",
    "captain_of",
    "tamed",
    "truce",
    "owes",
    "treated_by",
    "parent_of",
    "spouse_of",
    "betrothed_to",
    "concubine_of",
    "fostered_by",
    "sworn_kin",
    "tells",
    "fixed_in",
    "adherent_of",
    "practises",
)

BOND_NEW = (
    "inside",
    "lives_in",
    "worships",
    "enemy",
    "ally",
    "descends_from",
    "protects",
    "rules",
    "owns",
    "beat",
    "killed",
    "cursed",
    "blessed",
    "source_of",
    "tells_of",
    "destroyed",
    "loves",
    "fears",
    "hunts",
    "trades_with",
    "prophesies",
    "caused",
    "celebrates",
    "forbids",
    "speaks",
    "produced",
    "built",
    "migrated_to",
    "discovered",
    "soul_descended_to",
    "party_to",
    "member_of",
    "knows",
    "pays_tribute",
    "related",
    "holds_captive",
    "spy_network",
    "pursues",
    "companion",
    "pet_of",
    "rival",
    "apprentice_of",
    "commands",
    "part_of",
    "passenger_of",
    "captain_of",
    "tamed",
    "truce",
    "owes",
    "treated_by",
    "parent_of",
    "spouse_of",
    "betrothed_to",
    "concubine_of",
    "fostered_by",
    "sworn_kin",
    "tells",
    "fixed_in",
    "adherent_of",
    "practises",
    "copy_of",
    "merged_into",
    "divided_from",
    "transferred_from",
    "restored_from",
    "made_mind_of",
    "hosted_by",
    "linked_with",
)

MEMORY_OLD = (
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
)

MEMORY_NEW = (
    "memory_gap",
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
)

LAW_OLD = (
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
)

LAW_NEW = (
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

CLAUSE_OLD = (
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
)

CLAUSE_NEW = (
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

MEDIUM_OLD = (
    "envoy",
    "letter",
    "herald",
    "signal_fire",
    "dream",
    "bird",
    "magic_sending",
)

MEDIUM_NEW = (
    "envoy",
    "letter",
    "herald",
    "signal_fire",
    "dream",
    "bird",
    "magic_sending",
    "network",
)

ENTITY_OLD = (
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
)

ENTITY_NEW = (
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

DIMENSION_OLD = (
    "prime",
    "parallel",
    "mirror",
    "pocket",
    "bubble_universe",
    "brane",
    "higher_dimensional",
    "antimatter",
    "quantum_branch",
    "time_reversed",
    "compactified",
    "astral",
    "ethereal",
    "dream",
    "shadow",
    "spirit",
    "fey",
    "elemental",
    "celestial",
    "infernal",
    "abyssal",
    "limbo",
    "far_realm",
    "clockwork",
    "chaos",
    "underworld",
    "divine_domain",
    "void_between",
)

DIMENSION_NEW = (
    "prime",
    "parallel",
    "mirror",
    "pocket",
    "bubble_universe",
    "brane",
    "higher_dimensional",
    "antimatter",
    "quantum_branch",
    "time_reversed",
    "compactified",
    "astral",
    "ethereal",
    "dream",
    "made",
    "shadow",
    "spirit",
    "fey",
    "elemental",
    "celestial",
    "infernal",
    "abyssal",
    "limbo",
    "far_realm",
    "clockwork",
    "chaos",
    "underworld",
    "divine_domain",
    "void_between",
)

RETYPED = (
    ("dimensions", "dimension_kind", DIMENSION_OLD, DIMENSION_NEW, False),
    ("messages", "medium", MEDIUM_OLD, MEDIUM_NEW, True),
    ("entities", "entity_type", ENTITY_OLD, ENTITY_NEW, False),
    ("son_powers", "param_entity_type", ENTITY_OLD, ENTITY_NEW, True),
    ("law_profiles", "kind", LAW_OLD, LAW_NEW, False),
    ("law_proposals", "kind", LAW_OLD, LAW_NEW, False),
    ("treaty_clauses", "kind", CLAUSE_OLD, CLAUSE_NEW, False),
    ("bonds", "kind", BOND_OLD, BOND_NEW, False),
    ("memories", "kind", MEMORY_OLD, MEMORY_NEW, False),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, old, new, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        gone = ", ".join(f"'{value}'" for value in new if value not in old)
        if not forward and nullable:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})")
        elif not forward:
            op.execute(f"DELETE FROM {table} WHERE {column} IN ({gone})")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, column), type_=enum_of(after, column), existing_nullable=nullable)


MADE_DEFAULTS = {
    "affect": "none",
    "purpose": "servant",
    "capacity": 30,
    "speed_pct": 100,
    "stability": 100,
    "fidelity_pct": 100,
    "upkeep": "maintenance",
    "pausable": True,
    "copyable": False,
    "restorable": False,
    "mergeable": False,
    "transferable": False,
    "dormant": False,
    "perfect_recall": True,
    "maker_bond": 0,
    "drift_pct": 0,
    "souled": False,
    "run_epochs": 0,
    "updated_epoch": 0,
    "locked": "[]",
}


def keep_construct_will() -> None:
    constructs = sa.table("constructs", sa.column("entity_id"), sa.column("will"), sa.column("maker_entity_id"))
    profiles = sa.table(
        "mind_profiles", *(sa.column(name) for name in ("node_id", "seat", "seat_node_id", "origin", "will", "made_by_node_id", *MADE_DEFAULTS))
    )
    rows = op.get_bind().execute(sa.select(constructs.c.entity_id, constructs.c.will, constructs.c.maker_entity_id)).all()
    if rows:
        op.bulk_insert(
            profiles,
            [
                {"node_id": node, "seat": "body", "seat_node_id": node, "origin": "made", "will": will, "made_by_node_id": maker, **MADE_DEFAULTS}
                for node, will, maker in rows
            ],
        )


def restore_construct_will() -> None:
    op.execute("UPDATE constructs SET will = COALESCE((SELECT will FROM mind_profiles WHERE mind_profiles.node_id = constructs.entity_id), 'instructed')")


def upgrade() -> None:
    op.create_table(
        "data_stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("security", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("security BETWEEN 0 AND 100", name=op.f("ck_data_stores_security_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_data_stores_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_data_stores_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_stores")),
    )
    with op.batch_alter_table("data_stores", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_data_stores_holder_node_id"), ["holder_node_id"], unique=False)

    op.create_table(
        "intrusions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "target",
            sa.Enum(
                "network",
                "data_store",
                "made_mind",
                "augment",
                "construct",
                "vehicle",
                "structure",
                "ledger",
                "saved_state",
                name="target",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "approach",
            sa.Enum("technical", "social", "insider", "rite", "power", name="approach", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "aim",
            sa.Enum("read", "alter", "deny", "seize", "plant", "extort", name="aim", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stealth", sa.Integer(), nullable=False),
        sa.Column("detection", sa.Integer(), nullable=False),
        sa.Column(
            "attribution",
            sa.Enum("unknown", "suspected", "known", "false_flag", name="attribution", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("blamed_node_id", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Enum("succeeded", "failed", "caught", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("detection BETWEEN 0 AND 100", name=op.f("ck_intrusions_detection_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_intrusions_epoch_min")),
        sa.CheckConstraint("stealth BETWEEN 0 AND 100", name=op.f("ck_intrusions_stealth_range")),
        sa.ForeignKeyConstraint(["actor_node_id"], ["nodes.id"], name=op.f("fk_intrusions_actor_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["blamed_node_id"], ["nodes.id"], name=op.f("fk_intrusions_blamed_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_intrusions_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intrusions")),
    )
    with op.batch_alter_table("intrusions", schema=None) as batch_op:
        batch_op.create_index("ix_intrusions_target", ["target_node_id"], unique=False)

    op.create_table(
        "made_realm_profiles",
        sa.Column("dimension_id", sa.Integer(), nullable=False),
        sa.Column("host_node_id", sa.Integer(), nullable=True),
        sa.Column("keeper_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "realm_purpose",
            sa.Enum(
                "dwelling",
                "afterlife",
                "confinement",
                "training",
                "leisure",
                "labour",
                "worship",
                "refuge",
                "experiment",
                "free",
                name="realm_purpose",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("time_ratio_pct", sa.Integer(), nullable=False),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column(
            "entry",
            sa.Enum("interface", "transfer", "rite", "death", "birth", name="entry", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "aware_inside", sa.Enum("knows", "rumoured", "unaware", name="aware_inside", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "upkeep",
            sa.Enum(
                "food",
                "energy",
                "essence",
                "vis",
                "belief",
                "maintenance",
                "host",
                "place",
                "none",
                name="upkeep",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("frozen_until_epoch", sa.Integer(), nullable=False),
        sa.Column("sealed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_made_realm_profiles_fidelity_range")),
        sa.CheckConstraint("time_ratio_pct BETWEEN 1 AND 10000", name=op.f("ck_made_realm_profiles_time_ratio_pct_range")),
        sa.ForeignKeyConstraint(["dimension_id"], ["nodes.id"], name=op.f("fk_made_realm_profiles_dimension_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_node_id"], ["nodes.id"], name=op.f("fk_made_realm_profiles_host_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["keeper_node_id"], ["nodes.id"], name=op.f("fk_made_realm_profiles_keeper_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("dimension_id", name=op.f("pk_made_realm_profiles")),
    )
    op.create_table(
        "made_relics",
        sa.Column("thing_node_id", sa.Integer(), nullable=False),
        sa.Column("make_knowledge", sa.Integer(), nullable=False),
        sa.Column("repair_knowledge", sa.Integer(), nullable=False),
        sa.Column(
            "function_state",
            sa.Enum("working", "failing", "dormant", "broken", name="function_state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("understood_pct", sa.Integer(), nullable=False),
        sa.Column(
            "use",
            sa.Enum("as_made", "repurposed", "revered", "displayed", "feared", "ignored", name="use", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("is_relic", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("make_knowledge BETWEEN 0 AND 100", name=op.f("ck_made_relics_make_knowledge_range")),
        sa.CheckConstraint("repair_knowledge BETWEEN 0 AND 100", name=op.f("ck_made_relics_repair_knowledge_range")),
        sa.CheckConstraint("understood_pct BETWEEN 0 AND 100", name=op.f("ck_made_relics_understood_pct_range")),
        sa.ForeignKeyConstraint(["thing_node_id"], ["nodes.id"], name=op.f("fk_made_relics_thing_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("thing_node_id", name=op.f("pk_made_relics")),
    )
    op.create_table(
        "mind_makings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mind_node_id", sa.Integer(), nullable=False),
        sa.Column("maker_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "method",
            sa.Enum(
                "craft",
                "training",
                "copying",
                "summoning",
                "growing",
                "transfer",
                "awakening",
                "divine_grant",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum("as_meant", "unstable", "empty_seat", "unintended_will", name="outcome", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_mind_makings_epoch_min")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_mind_makings_quality_range")),
        sa.ForeignKeyConstraint(["maker_node_id"], ["nodes.id"], name=op.f("fk_mind_makings_maker_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_mind_makings_mind_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mind_makings")),
    )
    with op.batch_alter_table("mind_makings", schema=None) as batch_op:
        batch_op.create_index("ix_mind_makings_mind", ["mind_node_id"], unique=False)

    op.create_table(
        "mind_profiles",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "seat",
            sa.Enum(
                "body",
                "bodies",
                "object",
                "structure",
                "network",
                "medium",
                "place",
                "host",
                "realm",
                "none",
                "divine",
                name="seat",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("seat_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "origin",
            sa.Enum(
                "born",
                "grown",
                "made",
                "trained",
                "copied",
                "transferred",
                "awakened",
                "summoned",
                "merged",
                "divided",
                "granted",
                name="origin",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "will",
            sa.Enum("none", "instructed", "emergent", "full", "exceeding", name="will", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("affect", sa.Enum("none", "modelled", "felt", name="affect", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(
                "tool",
                "companion",
                "servant",
                "steward",
                "sovereign",
                "oracle",
                "archive",
                "guardian",
                "free",
                name="purpose",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("speed_pct", sa.Integer(), nullable=False),
        sa.Column("stability", sa.Integer(), nullable=False),
        sa.Column("fidelity_pct", sa.Integer(), nullable=False),
        sa.Column(
            "upkeep",
            sa.Enum(
                "food",
                "energy",
                "essence",
                "vis",
                "belief",
                "maintenance",
                "host",
                "place",
                "none",
                name="upkeep",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "upkeep_energy",
            sa.Enum("muscle", "water", "wind", "heat", "magic", "divine", name="upkeep_energy", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("pausable", sa.Boolean(), nullable=False),
        sa.Column("copyable", sa.Boolean(), nullable=False),
        sa.Column("restorable", sa.Boolean(), nullable=False),
        sa.Column("mergeable", sa.Boolean(), nullable=False),
        sa.Column("transferable", sa.Boolean(), nullable=False),
        sa.Column("dormant", sa.Boolean(), nullable=False),
        sa.Column("perfect_recall", sa.Boolean(), nullable=False),
        sa.Column("made_by_node_id", sa.Integer(), nullable=True),
        sa.Column("maker_bond", sa.Integer(), nullable=False),
        sa.Column("drift_pct", sa.Integer(), nullable=False),
        sa.Column("souled", sa.Boolean(), nullable=False),
        sa.Column("run_epochs", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity BETWEEN 0 AND 100", name=op.f("ck_mind_profiles_capacity_range")),
        sa.CheckConstraint("drift_pct BETWEEN 0 AND 100", name=op.f("ck_mind_profiles_drift_pct_range")),
        sa.CheckConstraint("fidelity_pct BETWEEN 0 AND 100", name=op.f("ck_mind_profiles_fidelity_pct_range")),
        sa.CheckConstraint("maker_bond BETWEEN -100 AND 100", name=op.f("ck_mind_profiles_maker_bond_range")),
        sa.CheckConstraint("run_epochs >= 0", name=op.f("ck_mind_profiles_run_epochs_min")),
        sa.CheckConstraint("speed_pct BETWEEN 1 AND 1000", name=op.f("ck_mind_profiles_speed_pct_range")),
        sa.CheckConstraint("stability BETWEEN 0 AND 100", name=op.f("ck_mind_profiles_stability_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_mind_profiles_updated_epoch_min")),
        sa.ForeignKeyConstraint(["made_by_node_id"], ["nodes.id"], name=op.f("fk_mind_profiles_made_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_mind_profiles_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seat_node_id"], ["nodes.id"], name=op.f("fk_mind_profiles_seat_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_mind_profiles")),
    )
    with op.batch_alter_table("mind_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_mind_profiles_seat", ["seat_node_id"], unique=False)

    op.create_table(
        "mind_seats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mind_node_id", sa.Integer(), nullable=False),
        sa.Column("part_node_id", sa.Integer(), nullable=False),
        sa.Column("share_pct", sa.Integer(), nullable=False),
        sa.Column("vital", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("share_pct BETWEEN 0 AND 100", name=op.f("ck_mind_seats_share_pct_range")),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_mind_seats_mind_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_node_id"], ["nodes.id"], name=op.f("fk_mind_seats_part_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mind_seats")),
    )
    with op.batch_alter_table("mind_seats", schema=None) as batch_op:
        batch_op.create_index("ix_mind_seats_mind", ["mind_node_id"], unique=False)

    op.create_table(
        "mind_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mind_node_id", sa.Integer(), nullable=False),
        sa.Column("taken_epoch", sa.Integer(), nullable=False),
        sa.Column("taken_year", sa.Integer(), nullable=True),
        sa.Column("fidelity_pct", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "medium_kind",
            sa.Enum("record", "rite_vessel", "grown", "memory_of_others", "divine", name="medium_kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("sealed", sa.Boolean(), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("copies >= 1", name=op.f("ck_mind_states_copies_min")),
        sa.CheckConstraint("fidelity_pct BETWEEN 0 AND 100", name=op.f("ck_mind_states_fidelity_pct_range")),
        sa.CheckConstraint("taken_epoch >= 0", name=op.f("ck_mind_states_taken_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_mind_states_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_mind_states_mind_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_mind_states_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mind_states")),
    )
    with op.batch_alter_table("mind_states", schema=None) as batch_op:
        batch_op.create_index("ix_mind_states_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_mind_states_mind", ["mind_node_id"], unique=False)

    op.create_table(
        "mind_will_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mind_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "from_will",
            sa.Enum("none", "instructed", "emergent", "full", "exceeding", name="from_will", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "to_will",
            sa.Enum("none", "instructed", "emergent", "full", "exceeding", name="to_will", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "cause",
            sa.Enum(
                "capacity",
                "run_time",
                "order_conflict",
                "harm",
                "care",
                "contact",
                "gift",
                "damage",
                "oath",
                "exceeding",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_mind_will_changes_epoch_min")),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_mind_will_changes_mind_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mind_will_changes")),
    )
    with op.batch_alter_table("mind_will_changes", schema=None) as batch_op:
        batch_op.create_index("ix_mind_will_changes_mind", ["mind_node_id"], unique=False)

    op.create_table(
        "pattern_rights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("commodity", sa.Enum("food", "ore", "goods", name="commodity", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("licence_fee", sa.Integer(), nullable=False),
        sa.Column("open", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("licence_fee >= 0", name=op.f("ck_pattern_rights_licence_fee_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_pattern_rights_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_pattern_rights_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_rights")),
    )
    with op.batch_alter_table("pattern_rights", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_pattern_rights_holder_node_id"), ["holder_node_id"], unique=False)

    op.create_table(
        "remote_bodies",
        sa.Column("body_node_id", sa.Integer(), nullable=False),
        sa.Column("mind_node_id", sa.Integer(), nullable=False),
        sa.Column("feedback_pct", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("feedback_pct BETWEEN 0 AND 100", name=op.f("ck_remote_bodies_feedback_pct_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_remote_bodies_since_epoch_min")),
        sa.ForeignKeyConstraint(["body_node_id"], ["nodes.id"], name=op.f("fk_remote_bodies_body_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_remote_bodies_mind_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("body_node_id", name=op.f("pk_remote_bodies")),
    )
    with op.batch_alter_table("remote_bodies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_remote_bodies_mind_node_id"), ["mind_node_id"], unique=False)

    op.create_table(
        "data_store_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column(
            "content",
            sa.Enum(
                "secret",
                "mind_state",
                "knowledge",
                "account",
                "ledger",
                "identity",
                "orders",
                name="content",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("reference", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_data_store_contents_epoch_min")),
        sa.ForeignKeyConstraint(["store_id"], ["data_stores.id"], name=op.f("fk_data_store_contents_store_id_data_stores"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_data_store_contents_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_store_contents")),
    )
    with op.batch_alter_table("data_store_contents", schema=None) as batch_op:
        batch_op.create_index("ix_data_store_contents_store", ["store_id"], unique=False)

    op.create_table(
        "mind_laws",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "made_minds",
            sa.Enum("no_will", "instructed_only", "will_may_emerge", "will_by_make", name="made_minds", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "made_mind_souls",
            sa.Enum("none", "granted", "emergent", "always", name="made_mind_souls", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "soul_continuity",
            sa.Enum(
                "stays_with_first",
                "follows_the_running_mind",
                "divides",
                "stays_with_body",
                "none",
                name="soul_continuity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_mind_laws_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_mind_laws")),
    )
    op.create_table(
        "augments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bearer_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "slot",
            sa.Enum("part", "mind", "senses", "skin", "blood", "whole_body", name="slot", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "part",
            sa.Enum(
                "aura",
                "core",
                "eye",
                "face",
                "fingers",
                "gills",
                "groin",
                "gut",
                "head",
                "heart",
                "horn",
                "jaw",
                "left_antenna",
                "left_arm",
                "left_branch",
                "left_ear",
                "left_eye",
                "left_fin",
                "left_foot",
                "left_foreleg",
                "left_hand",
                "left_hindleg",
                "left_leg",
                "left_midleg",
                "left_wing",
                "lungs",
                "neck",
                "nose",
                "pseudopods",
                "right_antenna",
                "right_arm",
                "right_branch",
                "right_ear",
                "right_eye",
                "right_fin",
                "right_foot",
                "right_foreleg",
                "right_hand",
                "right_hindleg",
                "right_leg",
                "right_midleg",
                "right_wing",
                "roots",
                "tail",
                "teeth",
                "toes",
                "tongue",
                "torso",
                "venom_gland",
                "wings",
                name="part",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "replacement",
                "enhancement",
                "interface",
                "weapon",
                "regulator",
                "sense",
                "storage",
                "cosmetic",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("model_entity_id", sa.Integer(), nullable=True),
        sa.Column("make", sa.Enum("made", "rite_bound", "grown", name="make", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column(
            "upkeep",
            sa.Enum(
                "food",
                "energy",
                "essence",
                "vis",
                "belief",
                "maintenance",
                "host",
                "place",
                "none",
                name="upkeep",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("integration", sa.Integer(), nullable=False),
        sa.Column("strain", sa.Integer(), nullable=False),
        sa.Column("installed_by_node_id", sa.Integer(), nullable=True),
        sa.Column("installed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("installed_epoch >= 0", name=op.f("ck_augments_installed_epoch_min")),
        sa.CheckConstraint("integration BETWEEN 0 AND 100", name=op.f("ck_augments_integration_range")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_augments_quality_range")),
        sa.CheckConstraint("strain BETWEEN 0 AND 100", name=op.f("ck_augments_strain_range")),
        sa.ForeignKeyConstraint(["bearer_node_id"], ["nodes.id"], name=op.f("fk_augments_bearer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["installed_by_node_id"], ["nodes.id"], name=op.f("fk_augments_installed_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_entity_id"], ["entities.id"], name=op.f("fk_augments_model_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_augments")),
    )
    with op.batch_alter_table("augments", schema=None) as batch_op:
        batch_op.create_index("ix_augments_bearer", ["bearer_node_id"], unique=False)

    op.create_table(
        "company_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_entity_id", sa.Integer(), nullable=False),
        sa.Column("holding_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "structure",
                "network",
                "data_store",
                "made_mind",
                "fabricator",
                "living_line",
                "route",
                "enclave",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["company_entity_id"], ["entities.id"], name=op.f("fk_company_holdings_company_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holding_node_id"], ["nodes.id"], name=op.f("fk_company_holdings_holding_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_holdings")),
    )
    with op.batch_alter_table("company_holdings", schema=None) as batch_op:
        batch_op.create_index("ix_company_holdings_company", ["company_entity_id"], unique=False)

    op.create_table(
        "company_presences",
        sa.Column("company_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("licensed", sa.Boolean(), nullable=False),
        sa.Column("influence", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("influence BETWEEN 0 AND 100", name=op.f("ck_company_presences_influence_range")),
        sa.ForeignKeyConstraint(["company_entity_id"], ["entities.id"], name=op.f("fk_company_presences_company_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_company_presences_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_entity_id", "polity_entity_id", name=op.f("pk_company_presences")),
    )
    op.create_table(
        "enclaves",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("company_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_enclaves_since_epoch_min")),
        sa.ForeignKeyConstraint(["company_entity_id"], ["entities.id"], name=op.f("fk_enclaves_company_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_enclaves_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_enclaves")),
    )
    with op.batch_alter_table("enclaves", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_enclaves_company_entity_id"), ["company_entity_id"], unique=False)

    op.create_table(
        "fabrication",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("share_pct", sa.Integer(), nullable=False),
        sa.Column("dividend_pct", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dividend_pct BETWEEN 0 AND 100", name=op.f("ck_fabrication_dividend_pct_range")),
        sa.CheckConstraint("share_pct BETWEEN 0 AND 100", name=op.f("ck_fabrication_share_pct_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_fabrication_updated_epoch_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_fabrication_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_fabrication")),
    )
    op.create_table(
        "information_trust",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("information_trust", sa.Integer(), nullable=False),
        sa.Column("shared_account_pct", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("information_trust BETWEEN 0 AND 100", name=op.f("ck_information_trust_information_trust_range")),
        sa.CheckConstraint("shared_account_pct BETWEEN 0 AND 100", name=op.f("ck_information_trust_shared_account_pct_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_information_trust_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_information_trust")),
    )
    op.create_table(
        "market_scarcity",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("commodity", sa.Enum("food", "ore", "goods", name="commodity", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("scarcity", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("scarcity BETWEEN 0 AND 100", name=op.f("ck_market_scarcity_scarcity_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_market_scarcity_updated_epoch_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_market_scarcity_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", "commodity", name=op.f("pk_market_scarcity")),
    )
    op.create_table(
        "mind_archives",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("access", sa.Enum("closed", "kin", "licensed", "open", name="access", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("unpaid_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("unpaid_epochs >= 0", name=op.f("ck_mind_archives_unpaid_epochs_min")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_mind_archives_upkeep_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_mind_archives_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_mind_archives_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_mind_archives")),
    )
    op.create_table(
        "network_gateways",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_network_id", sa.Integer(), nullable=False),
        sa.Column("second_network_id", sa.Integer(), nullable=False),
        sa.Column("toll", sa.Integer(), nullable=False),
        sa.Column("filter_pct", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("filter_pct BETWEEN 0 AND 100", name=op.f("ck_network_gateways_filter_pct_range")),
        sa.CheckConstraint("toll >= 0", name=op.f("ck_network_gateways_toll_min")),
        sa.ForeignKeyConstraint(["first_network_id"], ["entities.id"], name=op.f("fk_network_gateways_first_network_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_network_gateways_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["second_network_id"], ["entities.id"], name=op.f("fk_network_gateways_second_network_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_network_gateways")),
    )
    with op.batch_alter_table("network_gateways", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_network_gateways_first_network_id"), ["first_network_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_network_gateways_second_network_id"), ["second_network_id"], unique=False)

    op.create_table(
        "network_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("network_entity_id", sa.Integer(), nullable=False),
        sa.Column("member_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("hub", "station", "end", "relay", "archive", name="role", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("dependency_pct", sa.Integer(), nullable=False),
        sa.Column("security", sa.Integer(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dependency_pct BETWEEN 0 AND 100", name=op.f("ck_network_nodes_dependency_pct_range")),
        sa.CheckConstraint("security BETWEEN 0 AND 100", name=op.f("ck_network_nodes_security_range")),
        sa.ForeignKeyConstraint(["member_node_id"], ["nodes.id"], name=op.f("fk_network_nodes_member_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["network_entity_id"], ["entities.id"], name=op.f("fk_network_nodes_network_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_network_nodes")),
    )
    with op.batch_alter_table("network_nodes", schema=None) as batch_op:
        batch_op.create_index("ix_network_nodes_member", ["member_node_id"], unique=False)
        batch_op.create_index("ix_network_nodes_network", ["network_entity_id"], unique=False)

    op.create_table(
        "network_outages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("network_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "storm",
                "flare",
                "war",
                "sabotage",
                "intrusion",
                "decay",
                "rite",
                "power",
                "shortage",
                "divine",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("epochs", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_network_outages_epoch_min")),
        sa.CheckConstraint("epochs >= 1", name=op.f("ck_network_outages_epochs_min")),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_network_outages_severity_range")),
        sa.ForeignKeyConstraint(["network_entity_id"], ["entities.id"], name=op.f("fk_network_outages_network_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_network_outages")),
    )
    with op.batch_alter_table("network_outages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_network_outages_network_entity_id"), ["network_entity_id"], unique=False)

    op.create_table(
        "network_profiles",
        sa.Column("network_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "carrier",
            sa.Enum(
                "relay",
                "wired",
                "broadcast",
                "mesh",
                "mind_link",
                "rite_link",
                "grown_link",
                name="carrier",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "access", sa.Enum("closed", "members", "licensed", "open", name="access", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("carries_messages", sa.Boolean(), nullable=False),
        sa.Column("carries_records", sa.Boolean(), nullable=False),
        sa.Column("carries_control", sa.Boolean(), nullable=False),
        sa.Column("carries_money", sa.Boolean(), nullable=False),
        sa.Column("carries_minds", sa.Boolean(), nullable=False),
        sa.Column("carries_opinion", sa.Boolean(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False),
        sa.Column("security", sa.Integer(), nullable=False),
        sa.Column("reliability", sa.Integer(), nullable=False),
        sa.Column("curation", sa.Integer(), nullable=False),
        sa.Column("censorship", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("tech_level", sa.Integer(), nullable=False),
        sa.Column("down_until_epoch", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity BETWEEN 0 AND 100", name=op.f("ck_network_profiles_capacity_range")),
        sa.CheckConstraint("censorship BETWEEN 0 AND 100", name=op.f("ck_network_profiles_censorship_range")),
        sa.CheckConstraint("curation BETWEEN 0 AND 100", name=op.f("ck_network_profiles_curation_range")),
        sa.CheckConstraint("delay_days >= 0", name=op.f("ck_network_profiles_delay_days_min")),
        sa.CheckConstraint("down_until_epoch >= 0", name=op.f("ck_network_profiles_down_until_epoch_min")),
        sa.CheckConstraint("reliability BETWEEN 0 AND 100", name=op.f("ck_network_profiles_reliability_range")),
        sa.CheckConstraint("security BETWEEN 0 AND 100", name=op.f("ck_network_profiles_security_range")),
        sa.CheckConstraint("tech_level BETWEEN 0 AND 10", name=op.f("ck_network_profiles_tech_level_range")),
        sa.ForeignKeyConstraint(["network_entity_id"], ["entities.id"], name=op.f("fk_network_profiles_network_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_network_profiles_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("network_entity_id", name=op.f("pk_network_profiles")),
    )
    op.create_table(
        "people_substrates",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "seat",
            sa.Enum(
                "body",
                "bodies",
                "object",
                "structure",
                "network",
                "medium",
                "place",
                "host",
                "realm",
                "none",
                "divine",
                name="seat",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "origin",
            sa.Enum(
                "born",
                "grown",
                "made",
                "trained",
                "copied",
                "transferred",
                "awakened",
                "summoned",
                "merged",
                "divided",
                "granted",
                name="origin",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("share_pct", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("share_pct BETWEEN 0 AND 100", name=op.f("ck_people_substrates_share_pct_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_people_substrates_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "seat", "origin", name=op.f("pk_people_substrates")),
    )
    op.create_table(
        "salvage_sites",
        sa.Column("site_entity_id", sa.Integer(), nullable=False),
        sa.Column("yield_left", sa.Integer(), nullable=False),
        sa.Column("rights_holder_node_id", sa.Integer(), nullable=True),
        sa.Column("last_salvaged_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("yield_left >= 0", name=op.f("ck_salvage_sites_yield_left_min")),
        sa.ForeignKeyConstraint(["rights_holder_node_id"], ["nodes.id"], name=op.f("fk_salvage_sites_rights_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_entity_id"], ["entities.id"], name=op.f("fk_salvage_sites_site_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("site_entity_id", name=op.f("pk_salvage_sites")),
    )
    op.create_table(
        "surveillance_profiles",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("reach_pct", sa.Integer(), nullable=False),
        sa.Column(
            "focus",
            sa.Enum(
                "crime", "dissent", "foreigners", "faith", "minds", "gifted", "everything", name="focus", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity BETWEEN 0 AND 100", name=op.f("ck_surveillance_profiles_capacity_range")),
        sa.CheckConstraint("reach_pct BETWEEN 0 AND 100", name=op.f("ck_surveillance_profiles_reach_pct_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_surveillance_profiles_updated_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_surveillance_profiles_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_surveillance_profiles")),
    )
    op.create_table(
        "augment_effects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("augment_id", sa.Integer(), nullable=False),
        sa.Column(
            "target",
            sa.Enum("attribute", "capacity", "skill", "sense", "resistance", name="target", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("target_key", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount BETWEEN -100 AND 100", name=op.f("ck_augment_effects_amount_range")),
        sa.ForeignKeyConstraint(["augment_id"], ["augments.id"], name=op.f("fk_augment_effects_augment_id_augments"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_augment_effects")),
    )
    with op.batch_alter_table("augment_effects", schema=None) as batch_op:
        batch_op.create_index("ix_augment_effects_augment", ["augment_id"], unique=False)

    op.create_table(
        "replicator_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("scale", sa.Enum("minute", "machine", "works", "vessel", name="scale", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "feedstock",
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
                name="feedstock",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "output",
            sa.Enum(
                "copies",
                "goods",
                "structures",
                "repair",
                "medicine",
                "terraforming",
                "disassembly",
                name="output",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("growth_pct", sa.Integer(), nullable=False),
        sa.Column("error_pct", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=True),
        sa.Column("containment", sa.Integer(), nullable=False),
        sa.Column("kill_switch", sa.Boolean(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("maker_node_id", sa.Integer(), nullable=True),
        sa.Column("mind_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "stage",
            sa.Enum("contained", "working", "spreading", "runaway", "stopped", "extinct", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("drifted_from_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("containment BETWEEN 0 AND 100", name=op.f("ck_replicator_lines_containment_range")),
        sa.CheckConstraint("error_pct BETWEEN 0 AND 100", name=op.f("ck_replicator_lines_error_pct_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_replicator_lines_founded_epoch_min")),
        sa.CheckConstraint("growth_pct BETWEEN 0 AND 100", name=op.f("ck_replicator_lines_growth_pct_range")),
        sa.ForeignKeyConstraint(
            ["drifted_from_id"], ["replicator_lines.id"], name=op.f("fk_replicator_lines_drifted_from_id_replicator_lines"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["maker_node_id"], ["nodes.id"], name=op.f("fk_replicator_lines_maker_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_replicator_lines_mind_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_replicator_lines_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["set_id"], ["instruction_sets.id"], name=op.f("fk_replicator_lines_set_id_instruction_sets"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_replicator_lines")),
    )
    op.create_table(
        "replicator_presence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=False),
        sa.Column("place_node_id", sa.Integer(), nullable=False),
        sa.Column("mass", sa.Integer(), nullable=False),
        sa.Column("growth", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("mass >= 0", name=op.f("ck_replicator_presence_mass_min")),
        sa.ForeignKeyConstraint(["line_id"], ["replicator_lines.id"], name=op.f("fk_replicator_presence_line_id_replicator_lines"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_node_id"], ["nodes.id"], name=op.f("fk_replicator_presence_place_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_replicator_presence")),
    )
    with op.batch_alter_table("replicator_presence", schema=None) as batch_op:
        batch_op.create_index("ix_replicator_presence_line", ["line_id"], unique=False)
        batch_op.create_index("ix_replicator_presence_place", ["place_node_id"], unique=False)

    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "authenticity",
                sa.Enum("genuine", "altered", "forged", "generated", "unknown", name="authenticity", native_enum=False, create_constraint=True, length=40),
                server_default="genuine",
                nullable=False,
            )
        )

    with op.batch_alter_table("company_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "charter",
                sa.Enum("chartered", "free", "state_owned", "cooperative", name="charter", native_enum=False, create_constraint=True, length=40),
                server_default="chartered",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("headquarters_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_company_profiles_headquarters_entity_id_entities"), "entities", ["headquarters_entity_id"], ["id"], ondelete="SET NULL"
        )

    retype(forward=True)
    keep_construct_will()
    with op.batch_alter_table("constructs", schema=None) as batch_op:
        batch_op.drop_constraint("will", type_="check")
        batch_op.drop_column("will")

    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "made_mind_stance",
                sa.Enum("abomination", "tool", "kin", "sacred", "silent", name="made_mind_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "copy_stance",
                sa.Enum("abomination", "tool", "kin", "sacred", "silent", name="copy_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "augment_stance",
                sa.Enum("abomination", "tool", "kin", "sacred", "silent", name="augment_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "made_afterlife_stance",
                sa.Enum("abomination", "tool", "kin", "sacred", "silent", name="made_afterlife_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "relic_stance",
                sa.Enum("sacred", "tool", "forbidden", "heritage", name="relic_stance", native_enum=False, create_constraint=True, length=40),
                server_default="heritage",
                nullable=False,
            )
        )

    with op.batch_alter_table("loop_signals", schema=None) as batch_op:
        batch_op.alter_column("value", existing_type=sa.FLOAT(), type_=sa.Double(), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("loop_signals", schema=None) as batch_op:
        batch_op.alter_column("value", existing_type=sa.Double(), type_=sa.FLOAT(), existing_nullable=False)

    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.drop_constraint("relic_stance", type_="check")
        batch_op.drop_column("relic_stance")
        batch_op.drop_constraint("made_afterlife_stance", type_="check")
        batch_op.drop_column("made_afterlife_stance")
        batch_op.drop_constraint("augment_stance", type_="check")
        batch_op.drop_column("augment_stance")
        batch_op.drop_constraint("copy_stance", type_="check")
        batch_op.drop_column("copy_stance")
        batch_op.drop_constraint("made_mind_stance", type_="check")
        batch_op.drop_column("made_mind_stance")

    with op.batch_alter_table("constructs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("will", enum_of(("none", "instructed", "emergent", "full", "exceeding"), "will"), server_default="instructed", nullable=False)
        )
    restore_construct_will()
    retype(forward=False)

    with op.batch_alter_table("company_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_company_profiles_headquarters_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("headquarters_entity_id")
        batch_op.drop_constraint("charter", type_="check")
        batch_op.drop_column("charter")

    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_constraint("authenticity", type_="check")
        batch_op.drop_column("authenticity")

    with op.batch_alter_table("replicator_presence", schema=None) as batch_op:
        batch_op.drop_index("ix_replicator_presence_place")
        batch_op.drop_index("ix_replicator_presence_line")

    op.drop_table("replicator_presence")
    op.drop_table("replicator_lines")
    with op.batch_alter_table("augment_effects", schema=None) as batch_op:
        batch_op.drop_index("ix_augment_effects_augment")

    op.drop_table("augment_effects")
    op.drop_table("surveillance_profiles")
    op.drop_table("salvage_sites")
    op.drop_table("people_substrates")
    op.drop_table("network_profiles")
    with op.batch_alter_table("network_outages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_network_outages_network_entity_id"))

    op.drop_table("network_outages")
    with op.batch_alter_table("network_nodes", schema=None) as batch_op:
        batch_op.drop_index("ix_network_nodes_network")
        batch_op.drop_index("ix_network_nodes_member")

    op.drop_table("network_nodes")
    with op.batch_alter_table("network_gateways", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_network_gateways_second_network_id"))
        batch_op.drop_index(batch_op.f("ix_network_gateways_first_network_id"))

    op.drop_table("network_gateways")
    op.drop_table("mind_archives")
    op.drop_table("market_scarcity")
    op.drop_table("information_trust")
    op.drop_table("fabrication")
    with op.batch_alter_table("enclaves", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_enclaves_company_entity_id"))

    op.drop_table("enclaves")
    op.drop_table("company_presences")
    with op.batch_alter_table("company_holdings", schema=None) as batch_op:
        batch_op.drop_index("ix_company_holdings_company")

    op.drop_table("company_holdings")
    with op.batch_alter_table("augments", schema=None) as batch_op:
        batch_op.drop_index("ix_augments_bearer")

    op.drop_table("augments")
    op.drop_table("mind_laws")
    with op.batch_alter_table("data_store_contents", schema=None) as batch_op:
        batch_op.drop_index("ix_data_store_contents_store")

    op.drop_table("data_store_contents")
    with op.batch_alter_table("remote_bodies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_remote_bodies_mind_node_id"))

    op.drop_table("remote_bodies")
    with op.batch_alter_table("pattern_rights", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_pattern_rights_holder_node_id"))

    op.drop_table("pattern_rights")
    with op.batch_alter_table("mind_will_changes", schema=None) as batch_op:
        batch_op.drop_index("ix_mind_will_changes_mind")

    op.drop_table("mind_will_changes")
    with op.batch_alter_table("mind_states", schema=None) as batch_op:
        batch_op.drop_index("ix_mind_states_mind")
        batch_op.drop_index("ix_mind_states_holder")

    op.drop_table("mind_states")
    with op.batch_alter_table("mind_seats", schema=None) as batch_op:
        batch_op.drop_index("ix_mind_seats_mind")

    op.drop_table("mind_seats")
    with op.batch_alter_table("mind_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_mind_profiles_seat")

    op.drop_table("mind_profiles")
    with op.batch_alter_table("mind_makings", schema=None) as batch_op:
        batch_op.drop_index("ix_mind_makings_mind")

    op.drop_table("mind_makings")
    op.drop_table("made_relics")
    op.drop_table("made_realm_profiles")
    with op.batch_alter_table("intrusions", schema=None) as batch_op:
        batch_op.drop_index("ix_intrusions_target")

    op.drop_table("intrusions")
    with op.batch_alter_table("data_stores", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_data_stores_holder_node_id"))

    op.drop_table("data_stores")
