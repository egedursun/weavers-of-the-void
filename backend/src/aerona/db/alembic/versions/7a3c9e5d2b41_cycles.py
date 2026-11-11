import sqlalchemy as sa
from alembic import op

revision = "7a3c9e5d2b41"
down_revision = "8c4d2e6f1a93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "long_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("author_node_id", sa.Integer(), nullable=True),
        sa.Column("carrier_node_id", sa.Integer(), nullable=True),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("ecological_transformation", "bloodline", "conversion", "wonder", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("step_cost", sa.Integer(), nullable=False),
        sa.Column("secrecy", sa.Integer(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Enum("active", "completed", "abandoned", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("finished_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("progress <= steps", name=op.f("ck_long_plans_progress_within_steps")),
        sa.CheckConstraint("progress >= 0", name=op.f("ck_long_plans_progress_min")),
        sa.CheckConstraint("secrecy BETWEEN 0 AND 100", name=op.f("ck_long_plans_secrecy_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_long_plans_started_epoch_min")),
        sa.CheckConstraint("step_cost >= 0", name=op.f("ck_long_plans_step_cost_min")),
        sa.CheckConstraint("steps >= 1", name=op.f("ck_long_plans_steps_min")),
        sa.ForeignKeyConstraint(["author_node_id"], ["nodes.id"], name=op.f("fk_long_plans_author_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["carrier_node_id"], ["nodes.id"], name=op.f("fk_long_plans_carrier_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_long_plans_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_long_plans_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_long_plans")),
    )
    with op.batch_alter_table("long_plans", schema=None) as batch_op:
        batch_op.create_index("ix_long_plans_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "asabiyya",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("frontier", sa.Integer(), nullable=False),
        sa.Column("luxury_generations", sa.Integer(), nullable=False),
        sa.Column("conflict", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("conflict BETWEEN 0 AND 100", name=op.f("ck_asabiyya_conflict_range")),
        sa.CheckConstraint("frontier >= 0", name=op.f("ck_asabiyya_frontier_min")),
        sa.CheckConstraint("luxury_generations >= 0", name=op.f("ck_asabiyya_luxury_generations_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_asabiyya_updated_epoch_min")),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_asabiyya_value_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_asabiyya_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_asabiyya")),
    )
    op.create_table(
        "camps",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Enum("sedentary", "transhumant", "nomadic", name="mode", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("circuit", sa.JSON(), nullable=False),
        sa.Column("season_index", sa.Integer(), nullable=False),
        sa.Column("herd", sa.Integer(), nullable=False),
        sa.Column("grazing", sa.Integer(), nullable=False),
        sa.Column("water", sa.Integer(), nullable=False),
        sa.Column("last_moved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("grazing BETWEEN 0 AND 100", name=op.f("ck_camps_grazing_range")),
        sa.CheckConstraint("herd >= 0", name=op.f("ck_camps_herd_min")),
        sa.CheckConstraint("season_index >= 0", name=op.f("ck_camps_season_index_min")),
        sa.CheckConstraint("water BETWEEN 0 AND 100", name=op.f("ck_camps_water_range")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_camps_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_camps")),
    )
    op.create_table(
        "ceremonial_circuits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("item_entity_id", sa.Integer(), nullable=True),
        sa.Column("stops", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("passes", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("passes >= 0", name=op.f("ck_ceremonial_circuits_passes_min")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_ceremonial_circuits_position_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_ceremonial_circuits_started_epoch_min")),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_ceremonial_circuits_item_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ceremonial_circuits")),
    )
    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("disaster", "climate", "invasion", "plague", "famine", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column(
            "response", sa.Enum("stagnation", "response", "collapse", name="response", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_challenges_epoch_min")),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_challenges_severity_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_challenges_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_challenges_source_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenges")),
    )
    with op.batch_alter_table("challenges", schema=None) as batch_op:
        batch_op.create_index("ix_challenges_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "confederations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("leader_entity_id", sa.Integer(), nullable=True),
        sa.Column("members", sa.JSON(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("dissolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("formed_epoch >= 0", name=op.f("ck_confederations_formed_epoch_min")),
        sa.ForeignKeyConstraint(["leader_entity_id"], ["entities.id"], name=op.f("fk_confederations_leader_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_confederations")),
    )
    op.create_table(
        "divine_debts",
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("offered", sa.Integer(), nullable=False),
        sa.Column("answered", sa.Integer(), nullable=False),
        sa.Column("last_offering_epoch", sa.Integer(), nullable=True),
        sa.Column("last_answer_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("answered >= 0", name=op.f("ck_divine_debts_answered_min")),
        sa.CheckConstraint("offered >= 0", name=op.f("ck_divine_debts_offered_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_divine_debts_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_divine_debts_god_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("god_node_id", "community_entity_id", name=op.f("pk_divine_debts")),
    )
    with op.batch_alter_table("divine_debts", schema=None) as batch_op:
        batch_op.create_index("ix_divine_debts_community", ["community_entity_id"], unique=False)

    op.create_table(
        "gifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("giver_node_id", sa.Integer(), nullable=False),
        sa.Column("receiver_node_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "occasion",
            sa.Enum(
                "courtesy",
                "feast",
                "circuit",
                "offering",
                "marriage",
                "return",
                "alliance",
                name="occasion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("item_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "state",
            sa.Enum("open", "returned", "refused", "destroyed", "lapsed", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("answers_gift_id", sa.Integer(), nullable=True),
        sa.Column("due_epoch", sa.Integer(), nullable=True),
        sa.Column("settled_epoch", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_gifts_epoch_min")),
        sa.CheckConstraint("giver_node_id <> receiver_node_id", name=op.f("ck_gifts_two_sides")),
        sa.CheckConstraint("value >= 0", name=op.f("ck_gifts_value_min")),
        sa.ForeignKeyConstraint(["answers_gift_id"], ["gifts.id"], name=op.f("fk_gifts_answers_gift_id_gifts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["giver_node_id"], ["nodes.id"], name=op.f("fk_gifts_giver_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_gifts_item_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["receiver_node_id"], ["nodes.id"], name=op.f("fk_gifts_receiver_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gifts")),
    )
    with op.batch_alter_table("gifts", schema=None) as batch_op:
        batch_op.create_index("ix_gifts_giver", ["giver_node_id"], unique=False)
        batch_op.create_index("ix_gifts_receiver", ["receiver_node_id"], unique=False)

    op.create_table(
        "indentures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("employer_node_id", sa.Integer(), nullable=True),
        sa.Column("regime", sa.Enum("indenture", "peonage", name="regime", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("term_epochs", sa.Integer(), nullable=False),
        sa.Column("debt", sa.Integer(), nullable=False),
        sa.Column("exploitation", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_indentures_count_min")),
        sa.CheckConstraint("debt >= 0", name=op.f("ck_indentures_debt_min")),
        sa.CheckConstraint("exploitation BETWEEN 0 AND 100", name=op.f("ck_indentures_exploitation_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_indentures_since_epoch_min")),
        sa.CheckConstraint("term_epochs >= 0", name=op.f("ck_indentures_term_epochs_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_indentures_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employer_node_id"], ["nodes.id"], name=op.f("fk_indentures_employer_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_indentures")),
    )
    with op.batch_alter_table("indentures", schema=None) as batch_op:
        batch_op.create_index("ix_indentures_community", ["community_entity_id"], unique=False)

    op.create_table(
        "kinship_systems",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "descent",
            sa.Enum("patrilineal", "matrilineal", "bilateral", "double", "ambilineal", name="descent", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "residence",
            sa.Enum("patrilocal", "matrilocal", "neolocal", "avunculocal", name="residence", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "descent_group",
            sa.Enum("lineage", "clan", "moiety", "house", name="descent_group", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "cousin_terms",
            sa.Enum("distinct", "parallel_as_siblings", "all_as_siblings", name="cousin_terms", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "preference",
            sa.Enum("none", "cross_cousin", "clan_exogamy", "moiety_exogamy", name="preference", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "payment",
            sa.Enum("none", "bride_price", "dowry", "bride_service", name="payment", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("payment_value", sa.Integer(), nullable=False),
        sa.Column("levirate", sa.Boolean(), nullable=False),
        sa.Column("sororate", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("payment_value >= 0", name=op.f("ck_kinship_systems_payment_value_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_kinship_systems_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_kinship_systems")),
    )
    op.create_table(
        "legacy_traits",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("martial_style", "aesthetic", "funeral_rite", "belief", "value", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("predecessor_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_legacy_traits_since_epoch_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_legacy_traits_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["predecessor_entity_id"], ["entities.id"], name=op.f("fk_legacy_traits_predecessor_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("people_entity_id", "kind", "key", name=op.f("pk_legacy_traits")),
    )
    op.create_table(
        "manumissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column(
            "path", sa.Enum("purchase", "will", "service", "law", "revolt", name="path", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_manumissions_count_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_manumissions_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_manumissions_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manumissions")),
    )
    with op.batch_alter_table("manumissions", schema=None) as batch_op:
        batch_op.create_index("ix_manumissions_community", ["community_entity_id"], unique=False)

    op.create_table(
        "marriage_alliances",
        sa.Column("giver_entity_id", sa.Integer(), nullable=False),
        sa.Column("taker_entity_id", sa.Integer(), nullable=False),
        sa.Column("marriages", sa.Integer(), nullable=False),
        sa.Column("treaty_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("last_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("giver_entity_id <> taker_entity_id", name=op.f("ck_marriage_alliances_two_lines")),
        sa.CheckConstraint("marriages >= 0", name=op.f("ck_marriage_alliances_marriages_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_marriage_alliances_since_epoch_min")),
        sa.ForeignKeyConstraint(["giver_entity_id"], ["entities.id"], name=op.f("fk_marriage_alliances_giver_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["taker_entity_id"], ["entities.id"], name=op.f("fk_marriage_alliances_taker_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["treaty_id"], ["entities.id"], name=op.f("fk_marriage_alliances_treaty_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("giver_entity_id", "taker_entity_id", name=op.f("pk_marriage_alliances")),
    )
    with op.batch_alter_table("marriage_alliances", schema=None) as batch_op:
        batch_op.create_index("ix_marriage_alliances_taker", ["taker_entity_id"], unique=False)

    op.create_table(
        "mortal_castes",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("caste", sa.Enum("worker", "soldier", "breeder", name="caste", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_mortal_castes_since_epoch_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_mortal_castes_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_mortal_castes")),
    )
    op.create_table(
        "people_reproduction",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "system",
            sa.Enum("two_sex", "sequential", "ambisexual", "caste", "asexual", name="system", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("change_age", sa.Integer(), nullable=False),
        sa.Column("breeder_pct", sa.Integer(), nullable=False),
        sa.Column("soldier_pct", sa.Integer(), nullable=False),
        sa.Column("worker_pct", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("breeder_pct BETWEEN 0 AND 100", name=op.f("ck_people_reproduction_breeder_pct_range")),
        sa.CheckConstraint("change_age >= 0", name=op.f("ck_people_reproduction_change_age_min")),
        sa.CheckConstraint("soldier_pct BETWEEN 0 AND 100", name=op.f("ck_people_reproduction_soldier_pct_range")),
        sa.CheckConstraint("worker_pct BETWEEN 0 AND 100", name=op.f("ck_people_reproduction_worker_pct_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_people_reproduction_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_people_reproduction")),
    )
    op.create_table(
        "polity_stress",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("pressure", sa.Integer(), nullable=False),
        sa.Column("immiseration", sa.Integer(), nullable=False),
        sa.Column("elite_overproduction", sa.Integer(), nullable=False),
        sa.Column("fiscal_distress", sa.Integer(), nullable=False),
        sa.Column("psi", sa.Integer(), nullable=False),
        sa.Column("aspirants", sa.Integer(), nullable=False),
        sa.Column("positions", sa.Integer(), nullable=False),
        sa.Column("challenge", sa.Integer(), nullable=False),
        sa.Column(
            "phase",
            sa.Enum("growth", "stagflation", "crisis", "depression", name="phase", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("aspirants >= 0", name=op.f("ck_polity_stress_aspirants_min")),
        sa.CheckConstraint("challenge BETWEEN 0 AND 100", name=op.f("ck_polity_stress_challenge_range")),
        sa.CheckConstraint("elite_overproduction BETWEEN 0 AND 100", name=op.f("ck_polity_stress_elite_overproduction_range")),
        sa.CheckConstraint("fiscal_distress BETWEEN 0 AND 100", name=op.f("ck_polity_stress_fiscal_distress_range")),
        sa.CheckConstraint("immiseration BETWEEN 0 AND 100", name=op.f("ck_polity_stress_immiseration_range")),
        sa.CheckConstraint("positions >= 0", name=op.f("ck_polity_stress_positions_min")),
        sa.CheckConstraint("pressure BETWEEN 0 AND 100", name=op.f("ck_polity_stress_pressure_range")),
        sa.CheckConstraint("psi BETWEEN 0 AND 100", name=op.f("ck_polity_stress_psi_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_polity_stress_updated_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_stress_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_polity_stress")),
    )
    op.create_table(
        "slave_markets",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("sold", sa.Integer(), nullable=False),
        sa.Column("open", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("price >= 0", name=op.f("ck_slave_markets_price_min")),
        sa.CheckConstraint("sold >= 0", name=op.f("ck_slave_markets_sold_min")),
        sa.CheckConstraint("stock >= 0", name=op.f("ck_slave_markets_stock_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_slave_markets_updated_epoch_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_slave_markets_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_slave_markets")),
    )
    op.create_table(
        "stress_readings",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("pressure", sa.Integer(), nullable=False),
        sa.Column("immiseration", sa.Integer(), nullable=False),
        sa.Column("elite_overproduction", sa.Integer(), nullable=False),
        sa.Column("fiscal_distress", sa.Integer(), nullable=False),
        sa.Column("psi", sa.Integer(), nullable=False),
        sa.Column(
            "phase",
            sa.Enum("growth", "stagflation", "crisis", "depression", name="phase", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.CheckConstraint("elite_overproduction BETWEEN 0 AND 100", name=op.f("ck_stress_readings_elite_overproduction_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_stress_readings_epoch_min")),
        sa.CheckConstraint("fiscal_distress BETWEEN 0 AND 100", name=op.f("ck_stress_readings_fiscal_distress_range")),
        sa.CheckConstraint("immiseration BETWEEN 0 AND 100", name=op.f("ck_stress_readings_immiseration_range")),
        sa.CheckConstraint("pressure BETWEEN 0 AND 100", name=op.f("ck_stress_readings_pressure_range")),
        sa.CheckConstraint("psi BETWEEN 0 AND 100", name=op.f("ck_stress_readings_psi_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_stress_readings_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "epoch", name=op.f("pk_stress_readings")),
    )
    with op.batch_alter_table("corvee_levies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("work_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("laboured_epochs", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_foreign_key(batch_op.f("fk_corvee_levies_work_entity_id_entities"), "entities", ["work_entity_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("corvee_levies", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_corvee_levies_work_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("laboured_epochs")
        batch_op.drop_column("work_entity_id")

    op.drop_table("stress_readings")
    op.drop_table("slave_markets")
    op.drop_table("polity_stress")
    op.drop_table("people_reproduction")
    op.drop_table("mortal_castes")
    with op.batch_alter_table("marriage_alliances", schema=None) as batch_op:
        batch_op.drop_index("ix_marriage_alliances_taker")

    op.drop_table("marriage_alliances")
    with op.batch_alter_table("manumissions", schema=None) as batch_op:
        batch_op.drop_index("ix_manumissions_community")

    op.drop_table("manumissions")
    op.drop_table("legacy_traits")
    op.drop_table("kinship_systems")
    with op.batch_alter_table("indentures", schema=None) as batch_op:
        batch_op.drop_index("ix_indentures_community")

    op.drop_table("indentures")
    with op.batch_alter_table("gifts", schema=None) as batch_op:
        batch_op.drop_index("ix_gifts_receiver")
        batch_op.drop_index("ix_gifts_giver")

    op.drop_table("gifts")
    with op.batch_alter_table("divine_debts", schema=None) as batch_op:
        batch_op.drop_index("ix_divine_debts_community")

    op.drop_table("divine_debts")
    op.drop_table("confederations")
    with op.batch_alter_table("challenges", schema=None) as batch_op:
        batch_op.drop_index("ix_challenges_holder")

    op.drop_table("challenges")
    op.drop_table("ceremonial_circuits")
    op.drop_table("camps")
    op.drop_table("asabiyya")
    with op.batch_alter_table("long_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_long_plans_holder")

    op.drop_table("long_plans")
