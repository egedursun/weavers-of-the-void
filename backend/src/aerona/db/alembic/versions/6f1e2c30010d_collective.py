import sqlalchemy as sa
from alembic import op

revision = "6f1e2c30010d"
down_revision = "1dc131e7184d"
branch_labels = None
depends_on = None


OLD_COLLECTIONS = (
    "war",
    "battle",
    "siege",
    "duel",
    "abduction",
    "beast_attack",
    "raid",
    "persecution",
    "purge",
    "insurrection",
    "coup",
    "succession_crisis",
    "occupation",
    "journey",
    "pilgrimage",
    "competition",
    "performance",
    "procession",
    "ceremony",
    "wedding",
    "funeral",
    "coronation",
    "feast",
    "tournament",
    "hunt",
    "council",
    "summit",
    "plague",
    "famine",
    "migration",
    "founding",
    "theft",
    "investigation",
    "trial",
    "conversion_wave",
    "schism",
    "excavation",
    "heroquest",
)
NEW_COLLECTIONS = (*OLD_COLLECTIONS, "riot", "panic", "movement", "storylet")
OLD_SECRETS = (
    "affair",
    "illegitimate_child",
    "murder",
    "heresy",
    "secret_cult_membership",
    "debt",
    "crime",
    "cowardice_in_battle",
    "hidden_condition",
    "false_identity",
    "deal_with_outer_being",
    "true_parentage",
    "broken_oath",
    "ecosabotage",
    "broken_cipher",
)
NEW_SECRETS = (*OLD_SECRETS, "true_history")
COLUMNS = (
    ("incident_collections", "kind", OLD_COLLECTIONS, NEW_COLLECTIONS),
    ("secrets", "kind", OLD_SECRETS, NEW_SECRETS),
)


def widen(table: str, column: str, old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=sa.Enum(*old, name=column, native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name=column, native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    for table, column, old, new in COLUMNS:
        widen(table, column, old, new)
    op.create_table(
        "storylet_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "storylet",
            sa.Enum(
                "lost_heir",
                "hoarded_store",
                "beast_demand",
                "forbidden_text",
                "defiled_site",
                "wedding_challenge",
                "dying_ruler",
                "insulted_envoy",
                name="storylet",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("cast", sa.JSON(), nullable=False),
        sa.Column("status", sa.Enum("open", "resolved", "expired", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("chooser_node_id", sa.Integer(), nullable=True),
        sa.Column("choice", sa.Integer(), nullable=True),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("follows_run_id", sa.Integer(), nullable=True),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("due_epoch", sa.Integer(), nullable=True),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_storylet_runs_opened_epoch_min")),
        sa.ForeignKeyConstraint(["chooser_node_id"], ["nodes.id"], name=op.f("fk_storylet_runs_chooser_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_storylet_runs_collection_id_incident_collections"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["follows_run_id"], ["storylet_runs.id"], name=op.f("fk_storylet_runs_follows_run_id_storylet_runs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_storylet_runs_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_storylet_runs")),
    )
    with op.batch_alter_table("storylet_runs", schema=None) as batch_op:
        batch_op.create_index("ix_storylet_runs_world", ["world_id", "storylet"], unique=False)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("author_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "official_chronicle",
                "folk_memory",
                "foreign_account",
                "gospel",
                "epic",
                "inscription",
                "founding_myth",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "medium", sa.Enum("artwork", "book", "oral", "inscription", name="medium", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("structure_entity_id", sa.Integer(), nullable=True),
        sa.Column("artwork_entity_id", sa.Integer(), nullable=True),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column("credence", sa.Integer(), nullable=False),
        sa.Column("revised_from_id", sa.Integer(), nullable=True),
        sa.Column("defaced", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("credence BETWEEN 0 AND 100", name=op.f("ck_accounts_credence_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_accounts_epoch_min")),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_accounts_fidelity_range")),
        sa.ForeignKeyConstraint(["artwork_entity_id"], ["entities.id"], name=op.f("fk_accounts_artwork_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["author_node_id"], ["nodes.id"], name=op.f("fk_accounts_author_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_accounts_collection_id_incident_collections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_accounts_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revised_from_id"], ["accounts.id"], name=op.f("fk_accounts_revised_from_id_accounts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_accounts_structure_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_accounts_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.create_index("ix_accounts_collection", ["collection_id"], unique=False)
        batch_op.create_index("ix_accounts_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "arms",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "holder_kind",
            sa.Enum("house", "polity", "title", "army", "guild", name="holder_kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "field",
            sa.Enum("gold", "silver", "red", "blue", "green", "black", "purple", "orange", name="field", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "division",
            sa.Enum(
                "plain",
                "per_pale",
                "per_fess",
                "per_bend",
                "quarterly",
                "chevron",
                "bordure",
                name="division",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "second",
            sa.Enum("gold", "silver", "red", "blue", "green", "black", "purple", "orange", name="second", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column(
            "charge",
            sa.Enum(
                "none",
                "beast",
                "bird",
                "tree",
                "tower",
                "sword",
                "crown",
                "star",
                "sun",
                "moon",
                "eye",
                "hand",
                "wheel",
                "wave",
                "flame",
                "key",
                name="charge",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "charge_tincture",
            sa.Enum(
                "gold",
                "silver",
                "red",
                "blue",
                "green",
                "black",
                "purple",
                "orange",
                name="charge_tincture",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("motto", sa.String(length=200), nullable=True),
        sa.Column("parent_entity_id", sa.Integer(), nullable=True),
        sa.Column("quartered_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_arms_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_arms_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_entity_id"], ["entities.id"], name=op.f("fk_arms_parent_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quartered_entity_id"], ["entities.id"], name=op.f("fk_arms_quartered_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_arms")),
    )
    op.create_table(
        "commemorations",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("pride", sa.Boolean(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("last_observed_epoch", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_commemorations_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_commemorations_strength_range")),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_commemorations_collection_id_incident_collections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_commemorations_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "collection_id", name=op.f("pk_commemorations")),
    )
    op.create_table(
        "component_wear",
        sa.Column("vessel_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "component",
            sa.Enum(
                "hull",
                "propulsion",
                "hold",
                "quarters",
                "armour",
                "weapon",
                "ward",
                "navigation",
                "frame",
                "counterweight",
                name="component",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("wear", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("wear BETWEEN 0 AND 100", name=op.f("ck_component_wear_wear_range")),
        sa.ForeignKeyConstraint(["vessel_entity_id"], ["entities.id"], name=op.f("fk_component_wear_vessel_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vessel_entity_id", "component", name=op.f("pk_component_wear")),
    )
    op.create_table(
        "crowd_moods",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("anger", sa.Integer(), nullable=False),
        sa.Column("anxiety", sa.Integer(), nullable=False),
        sa.Column("fervour", sa.Integer(), nullable=False),
        sa.Column("deterrence", sa.Integer(), nullable=False),
        sa.Column("agitation", sa.Integer(), nullable=False),
        sa.Column(
            "last_trigger",
            sa.Enum(
                "price_spike",
                "execution",
                "sermon",
                "omen",
                "rumour",
                "fire",
                "plague",
                "beast",
                "eclipse",
                "miracle",
                "famine",
                "unpaid_wages",
                name="last_trigger",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("agitation BETWEEN 0 AND 100", name=op.f("ck_crowd_moods_agitation_range")),
        sa.CheckConstraint("anger BETWEEN 0 AND 100", name=op.f("ck_crowd_moods_anger_range")),
        sa.CheckConstraint("anxiety BETWEEN 0 AND 100", name=op.f("ck_crowd_moods_anxiety_range")),
        sa.CheckConstraint("deterrence BETWEEN 0 AND 100", name=op.f("ck_crowd_moods_deterrence_range")),
        sa.CheckConstraint("fervour BETWEEN 0 AND 100", name=op.f("ck_crowd_moods_fervour_range")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_crowd_moods_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_crowd_moods")),
    )
    op.create_table(
        "dating_systems",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("regnal", "founding", "religious", "celestial_cycle", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("anchor_year", sa.Integer(), nullable=False),
        sa.Column("anchor_node_id", sa.Integer(), nullable=True),
        sa.Column("label_node_id", sa.Integer(), nullable=True),
        sa.Column("cycle_years", sa.Integer(), nullable=False),
        sa.Column("reformed_epoch", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("anchor_year >= 0", name=op.f("ck_dating_systems_anchor_year_min")),
        sa.CheckConstraint("cycle_years >= 0", name=op.f("ck_dating_systems_cycle_years_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_dating_systems_since_epoch_min")),
        sa.ForeignKeyConstraint(["anchor_node_id"], ["nodes.id"], name=op.f("fk_dating_systems_anchor_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_dating_systems_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["label_node_id"], ["nodes.id"], name=op.f("fk_dating_systems_label_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_dating_systems")),
    )
    op.create_table(
        "demographic_transitions",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("fertility_pct", sa.Integer(), nullable=False),
        sa.Column("elder_share", sa.Integer(), nullable=False),
        sa.Column("urban_share", sa.Integer(), nullable=False),
        sa.Column("literacy", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("elder_share BETWEEN 0 AND 100", name=op.f("ck_demographic_transitions_elder_share_range")),
        sa.CheckConstraint("fertility_pct BETWEEN 0 AND 200", name=op.f("ck_demographic_transitions_fertility_pct_range")),
        sa.CheckConstraint("literacy BETWEEN 0 AND 100", name=op.f("ck_demographic_transitions_literacy_range")),
        sa.CheckConstraint("urban_share BETWEEN 0 AND 100", name=op.f("ck_demographic_transitions_urban_share_range")),
        sa.ForeignKeyConstraint(
            ["community_entity_id"], ["entities.id"], name=op.f("fk_demographic_transitions_community_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("community_entity_id", name=op.f("pk_demographic_transitions")),
    )
    op.create_table(
        "designs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("vessel", "skyship", "siege_engine", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "hull",
            sa.Enum(
                "raft",
                "boat",
                "galley",
                "longship",
                "cog",
                "carrack",
                "warship",
                "light_sailer",
                "bone_hull",
                "generation_ship",
                "skyship",
                "living_ship",
                name="hull",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("designer_entity_id", sa.Integer(), nullable=True),
        sa.Column("parent_design_id", sa.Integer(), nullable=True),
        sa.Column("mass", sa.Integer(), nullable=False),
        sa.Column("speed", sa.Integer(), nullable=False),
        sa.Column("range", sa.Integer(), nullable=False),
        sa.Column("seaworthiness", sa.Integer(), nullable=False),
        sa.Column("cargo", sa.Integer(), nullable=False),
        sa.Column("armament", sa.Integer(), nullable=False),
        sa.Column("crew", sa.Integer(), nullable=False),
        sa.Column("obsolete", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("armament >= 0", name=op.f("ck_designs_armament_min")),
        sa.CheckConstraint("cargo >= 0", name=op.f("ck_designs_cargo_min")),
        sa.CheckConstraint("crew >= 0", name=op.f("ck_designs_crew_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_designs_epoch_min")),
        sa.CheckConstraint("mass >= 0", name=op.f("ck_designs_mass_min")),
        sa.CheckConstraint("range >= 0", name=op.f("ck_designs_range_min")),
        sa.CheckConstraint("seaworthiness BETWEEN 0 AND 100", name=op.f("ck_designs_seaworthiness_range")),
        sa.CheckConstraint("speed >= 0", name=op.f("ck_designs_speed_min")),
        sa.ForeignKeyConstraint(["designer_entity_id"], ["entities.id"], name=op.f("fk_designs_designer_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_designs_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_design_id"], ["designs.id"], name=op.f("fk_designs_parent_design_id_designs"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_designs")),
    )
    with op.batch_alter_table("designs", schema=None) as batch_op:
        batch_op.create_index("ix_designs_owner", ["owner_entity_id", "kind"], unique=False)

    op.create_table(
        "diasporas",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("host_entity_id", sa.Integer(), nullable=False),
        sa.Column("home_entity_id", sa.Integer(), nullable=True),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.Column("ties", sa.Integer(), nullable=False),
        sa.Column("remittance", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("population >= 0", name=op.f("ck_diasporas_population_min")),
        sa.CheckConstraint("remittance >= 0", name=op.f("ck_diasporas_remittance_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_diasporas_since_epoch_min")),
        sa.CheckConstraint("ties BETWEEN 0 AND 100", name=op.f("ck_diasporas_ties_range")),
        sa.ForeignKeyConstraint(["home_entity_id"], ["entities.id"], name=op.f("fk_diasporas_home_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_entity_id"], ["entities.id"], name=op.f("fk_diasporas_host_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_diasporas_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "host_entity_id", name=op.f("pk_diasporas")),
    )
    op.create_table(
        "generations",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("generation_epoch", sa.Integer(), nullable=False),
        sa.Column("formative", sa.JSON(), nullable=False),
        sa.Column("value_shifts", sa.JSON(), nullable=False),
        sa.Column("alive", sa.Integer(), nullable=False),
        sa.Column("passed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("alive >= 0", name=op.f("ck_generations_alive_min")),
        sa.CheckConstraint("generation_epoch >= 0", name=op.f("ck_generations_generation_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_generations_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "generation_epoch", name=op.f("pk_generations")),
    )
    op.create_table(
        "learning_biases",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("prestige_pct", sa.Integer(), nullable=False),
        sa.Column("conformity_pct", sa.Integer(), nullable=False),
        sa.Column("content_pct", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("conformity_pct BETWEEN 0 AND 100", name=op.f("ck_learning_biases_conformity_pct_range")),
        sa.CheckConstraint("content_pct BETWEEN 0 AND 100", name=op.f("ck_learning_biases_content_pct_range")),
        sa.CheckConstraint("prestige_pct BETWEEN 0 AND 100", name=op.f("ck_learning_biases_prestige_pct_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_learning_biases_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_learning_biases")),
    )
    op.create_table(
        "learning_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_entity_id", sa.Integer(), nullable=False),
        sa.Column("model_entity_id", sa.Integer(), nullable=True),
        sa.Column("bias", sa.Enum("prestige", "conformity", "content", name="bias", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("shift", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_learning_events_epoch_min")),
        sa.ForeignKeyConstraint(["learner_entity_id"], ["entities.id"], name=op.f("fk_learning_events_learner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_entity_id"], ["entities.id"], name=op.f("fk_learning_events_model_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_events")),
    )
    with op.batch_alter_table("learning_events", schema=None) as batch_op:
        batch_op.create_index("ix_learning_events_learner", ["learner_entity_id", "epoch"], unique=False)

    op.create_table(
        "memory_strikes",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("by_entity_id", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_memory_strikes_since_epoch_min")),
        sa.ForeignKeyConstraint(["by_entity_id"], ["entities.id"], name=op.f("fk_memory_strikes_by_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_memory_strikes_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "by_entity_id", name=op.f("pk_memory_strikes")),
    )
    op.create_table(
        "movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "act",
            sa.Enum(
                "riot",
                "panic",
                "lynching",
                "conversion",
                "revolt",
                "strike",
                "procession",
                "revival",
                name="act",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "trigger",
            sa.Enum(
                "price_spike",
                "execution",
                "sermon",
                "omen",
                "rumour",
                "fire",
                "plague",
                "beast",
                "eclipse",
                "miracle",
                "famine",
                "unpaid_wages",
                name="trigger",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("members", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("leader_entity_id", sa.Integer(), nullable=True),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("faction_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("members >= 0", name=op.f("ck_movements_members_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_movements_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_movements_strength_range")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_movements_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_movements_faction_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_entity_id"], ["entities.id"], name=op.f("fk_movements_leader_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_movements_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movements")),
    )
    with op.batch_alter_table("movements", schema=None) as batch_op:
        batch_op.create_index("ix_movements_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "norm_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "situation",
            sa.Enum(
                "funeral",
                "feast",
                "wedding",
                "court",
                "temple",
                "market",
                "battle",
                "duel",
                "hospitality",
                "mourning",
                "sacred_day",
                "stranger",
                "superior",
                name="situation",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "behaviour",
            sa.Enum(
                "jest",
                "boast",
                "insult",
                "flattery",
                "flirting",
                "gifts",
                "quarrels",
                "blows",
                "weapons_carried",
                "fine_dress",
                "plain_speech",
                "forbidden_food",
                "secrets",
                name="behaviour",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "before",
            sa.Enum(
                "required",
                "admirable",
                "acceptable",
                "frowned_upon",
                "shameful",
                "unthinkable",
                name="before",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "after",
            sa.Enum(
                "required",
                "admirable",
                "acceptable",
                "frowned_upon",
                "shameful",
                "unthinkable",
                name="after",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("cause", sa.String(length=80), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_norm_changes_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_norm_changes_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_norm_changes")),
    )
    with op.batch_alter_table("norm_changes", schema=None) as batch_op:
        batch_op.create_index("ix_norm_changes_holder", ["holder_entity_id", "epoch"], unique=False)

    op.create_table(
        "role_norms",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("office", "profession", "combat", "priesthood", "inheritance", name="role", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "eligibility",
            sa.Enum(
                "any",
                "female_only",
                "male_only",
                "female_preferred",
                "male_preferred",
                name="eligibility",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("min_age", sa.Integer(), nullable=False),
        sa.Column("classes", sa.JSON(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum(
                "required",
                "admirable",
                "acceptable",
                "frowned_upon",
                "shameful",
                "unthinkable",
                name="stance",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("min_age BETWEEN 0 AND 200", name=op.f("ck_role_norms_min_age_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_role_norms_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_role_norms_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "role", name=op.f("pk_role_norms")),
    )
    op.create_table(
        "sex_ratios",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("males_per_hundred", sa.Integer(), nullable=False),
        sa.Column("widows", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("males_per_hundred BETWEEN 0 AND 1000", name=op.f("ck_sex_ratios_males_per_hundred_range")),
        sa.CheckConstraint("widows >= 0", name=op.f("ck_sex_ratios_widows_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_sex_ratios_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", name=op.f("pk_sex_ratios")),
    )
    op.create_table(
        "social_norms",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "situation",
            sa.Enum(
                "funeral",
                "feast",
                "wedding",
                "court",
                "temple",
                "market",
                "battle",
                "duel",
                "hospitality",
                "mourning",
                "sacred_day",
                "stranger",
                "superior",
                name="situation",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "behaviour",
            sa.Enum(
                "jest",
                "boast",
                "insult",
                "flattery",
                "flirting",
                "gifts",
                "quarrels",
                "blows",
                "weapons_carried",
                "fine_dress",
                "plain_speech",
                "forbidden_food",
                "secrets",
                name="behaviour",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "stance",
            sa.Enum(
                "required",
                "admirable",
                "acceptable",
                "frowned_upon",
                "shameful",
                "unthinkable",
                name="stance",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_social_norms_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_social_norms_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "situation", "behaviour", name=op.f("pk_social_norms")),
    )
    op.create_table(
        "account_stances",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "stance", sa.Enum("glorify", "vilify", "omit", "neutral", name="stance", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_account_stances_account_id_accounts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_account_stances_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_id", "node_id", name=op.f("pk_account_stances")),
    )
    with op.batch_alter_table("account_stances", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_account_stances_node_id"), ["node_id"], unique=False)

    op.create_table(
        "cascades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column(
            "trigger",
            sa.Enum(
                "price_spike",
                "execution",
                "sermon",
                "omen",
                "rumour",
                "fire",
                "plague",
                "beast",
                "eclipse",
                "miracle",
                "famine",
                "unpaid_wages",
                name="trigger",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "act",
            sa.Enum(
                "riot",
                "panic",
                "lynching",
                "conversion",
                "revolt",
                "strike",
                "procession",
                "revival",
                name="act",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("participants", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column(
            "outcome", sa.Enum("fizzled", "mob", "panic", "movement", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("deaths", sa.Integer(), nullable=False),
        sa.Column("fled", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("deaths >= 0", name=op.f("ck_cascades_deaths_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_cascades_epoch_min")),
        sa.CheckConstraint("participants >= 0", name=op.f("ck_cascades_participants_min")),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_cascades_share_range")),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_cascades_collection_id_incident_collections"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], name=op.f("fk_cascades_district_id_districts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_cascades_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cascades")),
    )
    with op.batch_alter_table("cascades", schema=None) as batch_op:
        batch_op.create_index("ix_cascades_settlement", ["settlement_entity_id", "epoch"], unique=False)

    op.create_table(
        "design_components",
        sa.Column("design_id", sa.Integer(), nullable=False),
        sa.Column(
            "component",
            sa.Enum(
                "hull",
                "propulsion",
                "hold",
                "quarters",
                "armour",
                "weapon",
                "ward",
                "navigation",
                "frame",
                "counterweight",
                name="component",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("material_id", sa.Integer(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_design_components_quality_range")),
        sa.CheckConstraint("size BETWEEN 0 AND 10", name=op.f("ck_design_components_size_range")),
        sa.ForeignKeyConstraint(["design_id"], ["designs.id"], name=op.f("fk_design_components_design_id_designs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["world_materials.id"], name=op.f("fk_design_components_material_id_world_materials"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("design_id", "component", name=op.f("pk_design_components")),
    )
    op.create_table(
        "founding_myths",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("credence", sa.Integer(), nullable=False),
        sa.Column("debunked_epoch", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("credence BETWEEN 0 AND 100", name=op.f("ck_founding_myths_credence_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_founding_myths_since_epoch_min")),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name=op.f("fk_founding_myths_account_id_accounts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_founding_myths_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_founding_myths")),
    )
    op.create_table(
        "lost_lands",
        sa.Column("claimant_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("lost_epoch", sa.Integer(), nullable=False),
        sa.Column("claimed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("lost_epoch >= 0", name=op.f("ck_lost_lands_lost_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_lost_lands_strength_range")),
        sa.ForeignKeyConstraint(["claimant_entity_id"], ["entities.id"], name=op.f("fk_lost_lands_claimant_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_lost_lands_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("claimant_entity_id", "region_entity_id", name=op.f("pk_lost_lands")),
    )
    op.create_table(
        "mobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column(
            "act",
            sa.Enum(
                "riot",
                "panic",
                "lynching",
                "conversion",
                "revolt",
                "strike",
                "procession",
                "revival",
                name="act",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("anger", sa.Integer(), nullable=False),
        sa.Column(
            "target",
            sa.Enum(
                "district", "granary", "scapegoat", "gate", "temple", "palace", "workshop", name="target", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("leader_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.Enum("gathering", "rampaging", "dispersed", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("ended_by", sa.Enum("fatigue", "force", "concession", name="ended_by", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column("damage", sa.Integer(), nullable=False),
        sa.Column("cascade_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("anger BETWEEN 0 AND 100", name=op.f("ck_mobs_anger_range")),
        sa.CheckConstraint("damage >= 0", name=op.f("ck_mobs_damage_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_mobs_since_epoch_min")),
        sa.CheckConstraint("size >= 0", name=op.f("ck_mobs_size_min")),
        sa.ForeignKeyConstraint(["cascade_id"], ["cascades.id"], name=op.f("fk_mobs_cascade_id_cascades"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], name=op.f("fk_mobs_district_id_districts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_entity_id"], ["entities.id"], name=op.f("fk_mobs_leader_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_mobs_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_mobs_target_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mobs")),
    )
    with op.batch_alter_table("mobs", schema=None) as batch_op:
        batch_op.create_index("ix_mobs_settlement", ["settlement_entity_id"], unique=False)

    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("design_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_vessel_profiles_design_id_designs"), "designs", ["design_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    for table, column, old, new in COLUMNS:
        widen(table, column, new, old)
    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_design_id_designs"), type_="foreignkey")
        batch_op.drop_column("design_id")

    with op.batch_alter_table("mobs", schema=None) as batch_op:
        batch_op.drop_index("ix_mobs_settlement")

    op.drop_table("mobs")
    op.drop_table("lost_lands")
    op.drop_table("founding_myths")
    op.drop_table("design_components")
    with op.batch_alter_table("cascades", schema=None) as batch_op:
        batch_op.drop_index("ix_cascades_settlement")

    op.drop_table("cascades")
    with op.batch_alter_table("account_stances", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_account_stances_node_id"))

    op.drop_table("account_stances")
    op.drop_table("social_norms")
    op.drop_table("sex_ratios")
    op.drop_table("role_norms")
    with op.batch_alter_table("norm_changes", schema=None) as batch_op:
        batch_op.drop_index("ix_norm_changes_holder")

    op.drop_table("norm_changes")
    with op.batch_alter_table("movements", schema=None) as batch_op:
        batch_op.drop_index("ix_movements_settlement")

    op.drop_table("movements")
    op.drop_table("memory_strikes")
    with op.batch_alter_table("learning_events", schema=None) as batch_op:
        batch_op.drop_index("ix_learning_events_learner")

    op.drop_table("learning_events")
    op.drop_table("learning_biases")
    op.drop_table("generations")
    op.drop_table("diasporas")
    with op.batch_alter_table("designs", schema=None) as batch_op:
        batch_op.drop_index("ix_designs_owner")

    op.drop_table("designs")
    op.drop_table("demographic_transitions")
    op.drop_table("dating_systems")
    op.drop_table("crowd_moods")
    op.drop_table("component_wear")
    op.drop_table("commemorations")
    op.drop_table("arms")
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_index("ix_accounts_holder")
        batch_op.drop_index("ix_accounts_collection")

    op.drop_table("accounts")
    with op.batch_alter_table("storylet_runs", schema=None) as batch_op:
        batch_op.drop_index("ix_storylet_runs_world")

    op.drop_table("storylet_runs")
