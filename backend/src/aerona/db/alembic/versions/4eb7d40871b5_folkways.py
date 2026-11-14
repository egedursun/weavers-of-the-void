import sqlalchemy as sa
from alembic import op

revision = "4eb7d40871b5"
down_revision = "662b4859943a"
branch_labels = None
depends_on = None


OLD_CRIMES = ("theft", "blasphemy", "treason", "murder", "desertion")
NEW_CRIMES = (*OLD_CRIMES, "witchcraft")
WIDENED = (
    ("crime_cases", "crime", False),
    ("sentences", "crime", False),
    ("precedents", "crime", False),
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    before, after = (OLD_CRIMES, NEW_CRIMES) if forward else (NEW_CRIMES, OLD_CRIMES)
    for table, column, nullable in WIDENED:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    op.create_table(
        "bias_weights",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "bias",
            sa.Enum(
                "overconfidence",
                "sunk_cost",
                "loss_aversion",
                "confirmation",
                "recency",
                "groupthink",
                "hostile_attribution",
                "optimism",
                "status_quo",
                "availability",
                "anchoring",
                "in_group_favour",
                "authority_deference",
                "scarcity_panic",
                "fatalism",
                "risk_seeking",
                "planning_fallacy",
                "halo",
                "projection",
                name="bias",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column(
            "last_decision",
            sa.Enum(
                "raid",
                "peace",
                "surrender",
                "scheme",
                "belief",
                "conversion",
                "migration",
                "god_goal",
                name="last_decision",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("last_shift", sa.Integer(), nullable=False),
        sa.Column("last_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_bias_weights_weight_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_bias_weights_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "bias", name=op.f("pk_bias_weights")),
    )
    op.create_table(
        "diets",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("staple", sa.Integer(), nullable=False),
        sa.Column("protein", sa.Integer(), nullable=False),
        sa.Column("fat", sa.Integer(), nullable=False),
        sa.Column("fresh", sa.Integer(), nullable=False),
        sa.Column("mineral", sa.Integer(), nullable=False),
        sa.Column("preserved", sa.Integer(), nullable=False),
        sa.Column("special", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("energy BETWEEN 0 AND 100", name=op.f("ck_diets_energy_range")),
        sa.CheckConstraint("fat BETWEEN 0 AND 100", name=op.f("ck_diets_fat_range")),
        sa.CheckConstraint("fresh BETWEEN 0 AND 100", name=op.f("ck_diets_fresh_range")),
        sa.CheckConstraint("mineral BETWEEN 0 AND 100", name=op.f("ck_diets_mineral_range")),
        sa.CheckConstraint("preserved BETWEEN 0 AND 100", name=op.f("ck_diets_preserved_range")),
        sa.CheckConstraint("protein BETWEEN 0 AND 100", name=op.f("ck_diets_protein_range")),
        sa.CheckConstraint("special BETWEEN 0 AND 100", name=op.f("ck_diets_special_range")),
        sa.CheckConstraint("staple BETWEEN 0 AND 100", name=op.f("ck_diets_staple_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_diets_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", name=op.f("pk_diets")),
    )
    op.create_table(
        "nutrition_scores",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "deficiency",
            sa.Enum(
                "energy",
                "protein",
                "fat",
                "fresh",
                "mineral",
                "light",
                "essence",
                "charge",
                name="deficiency",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("childhood", sa.Integer(), nullable=True),
        sa.Column("grown", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("balance BETWEEN 0 AND 100", name=op.f("ck_nutrition_scores_balance_range")),
        sa.CheckConstraint("childhood BETWEEN 0 AND 100", name=op.f("ck_nutrition_scores_childhood_range")),
        sa.CheckConstraint("energy BETWEEN 0 AND 100", name=op.f("ck_nutrition_scores_energy_range")),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name=op.f("ck_nutrition_scores_score_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_nutrition_scores_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", name=op.f("pk_nutrition_scores")),
    )
    op.create_table(
        "charms",
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "power", sa.Enum("protection", "fertility", "luck", "healing", name="power", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("real", sa.Boolean(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_charms_strength_range")),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_charms_item_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_entity_id", name=op.f("pk_charms")),
    )
    op.create_table(
        "impurity_sources",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "the_dead",
                "birth",
                "bodily_fluids",
                "food",
                "species",
                "profession",
                "outsiders",
                "place",
                "object",
                "act",
                "made_thing",
                "taboo",
                "wound",
                name="source",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("lasts", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("lasts >= 1", name=op.f("ck_impurity_sources_lasts_min")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_impurity_sources_weight_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_impurity_sources_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "source", name=op.f("pk_impurity_sources")),
    )
    op.create_table(
        "luck_beliefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "sign",
            sa.Enum("day", "number", "sign", "gesture", "place", "act", "person", name="sign", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "reach",
            sa.Enum("harvest", "health", "birth", "journey", "battle", name="reach", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("lucky", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_luck_beliefs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_luck_beliefs")),
    )
    with op.batch_alter_table("luck_beliefs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_luck_beliefs_people_entity_id"), ["people_entity_id"], unique=False)

    op.create_table(
        "mishaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("victim_node_id", sa.Integer(), nullable=True),
        sa.Column("cause_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "illness",
                "crop_failure",
                "child_death",
                "livestock_death",
                "accident",
                "bad_luck",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("true_cause", sa.String(length=200), nullable=False),
        sa.Column("explained", sa.Boolean(), nullable=False),
        sa.Column(
            "attribution",
            sa.Enum(
                "chance",
                "known_cause",
                "witchcraft",
                "curse",
                "god",
                "spirit",
                "ancestor",
                "omen",
                "fate",
                "enemy_scheme",
                "impurity",
                "broken_oath",
                name="attribution",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "response",
            sa.Enum(
                "nothing",
                "rite",
                "offering",
                "charm",
                "accusation",
                "purification",
                "safety_custom",
                name="response",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_mishaps_epoch_min")),
        sa.ForeignKeyConstraint(["cause_node_id"], ["nodes.id"], name=op.f("fk_mishaps_cause_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_mishaps_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["victim_node_id"], ["nodes.id"], name=op.f("fk_mishaps_victim_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mishaps")),
    )
    with op.batch_alter_table("mishaps", schema=None) as batch_op:
        batch_op.create_index("ix_mishaps_settlement", ["settlement_entity_id", "epoch"], unique=False)

    op.create_table(
        "nutrient_needs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "nutrient",
            sa.Enum(
                "energy",
                "protein",
                "fat",
                "fresh",
                "mineral",
                "light",
                "essence",
                "charge",
                name="nutrient",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_nutrient_needs_weight_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_nutrient_needs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "nutrient", name=op.f("pk_nutrient_needs")),
    )
    op.create_table(
        "purifications",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "time",
                "washing",
                "fasting",
                "offering",
                "rite",
                "confession",
                "payment",
                "ordeal",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epochs", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("success", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_purifications_cost_min")),
        sa.CheckConstraint("epochs >= 0", name=op.f("ck_purifications_epochs_min")),
        sa.CheckConstraint("success BETWEEN 0 AND 100", name=op.f("ck_purifications_success_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_purifications_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "method", name=op.f("pk_purifications")),
    )
    op.create_table(
        "purity_ranks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("standing", sa.Integer(), nullable=False),
        sa.Column("professions", sa.JSON(), nullable=False),
        sa.Column("endogamous", sa.Boolean(), nullable=False),
        sa.Column("commensal", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("standing BETWEEN 0 AND 100", name=op.f("ck_purity_ranks_standing_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_purity_ranks_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purity_ranks")),
        sa.UniqueConstraint("people_entity_id", "name", name="uq_purity_ranks_people_name"),
    )
    with op.batch_alter_table("purity_ranks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_purity_ranks_people_entity_id"), ["people_entity_id"], unique=False)

    op.create_table(
        "witch_hunts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("fervour", sa.Integer(), nullable=False),
        sa.Column("accused", sa.Integer(), nullable=False),
        sa.Column("killed", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accused >= 0", name=op.f("ck_witch_hunts_accused_min")),
        sa.CheckConstraint("fervour BETWEEN 0 AND 100", name=op.f("ck_witch_hunts_fervour_range")),
        sa.CheckConstraint("killed >= 0", name=op.f("ck_witch_hunts_killed_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_witch_hunts_started_epoch_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_witch_hunts_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_witch_hunts")),
    )
    with op.batch_alter_table("witch_hunts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_witch_hunts_settlement_entity_id"), ["settlement_entity_id"], unique=False)

    op.create_table(
        "accusations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column("mishap_id", sa.Integer(), nullable=True),
        sa.Column("hunt_id", sa.Integer(), nullable=True),
        sa.Column("accuser_node_id", sa.Integer(), nullable=True),
        sa.Column("accused_node_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum("pending", "cleared", "punished", "exiled", "killed", name="outcome", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("guilty_in_truth", sa.Boolean(), nullable=False),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_accusations_opened_epoch_min")),
        sa.ForeignKeyConstraint(["accused_node_id"], ["nodes.id"], name=op.f("fk_accusations_accused_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accuser_node_id"], ["nodes.id"], name=op.f("fk_accusations_accuser_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_accusations_case_id_crime_cases"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hunt_id"], ["witch_hunts.id"], name=op.f("fk_accusations_hunt_id_witch_hunts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mishap_id"], ["mishaps.id"], name=op.f("fk_accusations_mishap_id_mishaps"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_accusations_settlement_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accusations")),
    )
    with op.batch_alter_table("accusations", schema=None) as batch_op:
        batch_op.create_index("ix_accusations_accused", ["accused_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_accusations_hunt_id"), ["hunt_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_accusations_settlement_entity_id"), ["settlement_entity_id"], unique=False)

    op.create_table(
        "purity",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum("pure", "impure", "defiled", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "the_dead",
                "birth",
                "bodily_fluids",
                "food",
                "species",
                "profession",
                "outsiders",
                "place",
                "object",
                "act",
                "made_thing",
                "taboo",
                "wound",
                name="source",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("rank_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_purity_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_purity_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rank_id"], ["purity_ranks.id"], name=op.f("fk_purity_rank_id_purity_ranks"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("holder_node_id", name=op.f("pk_purity")),
    )
    with op.batch_alter_table("purity", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_purity_rank_id"), ["rank_id"], unique=False)

    with op.batch_alter_table("incubating_ideas", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "strain",
                sa.Enum("none", "distraction", "focus_loss", "obsession", name="strain", native_enum=False, create_constraint=True, length=40),
                server_default="distraction",
                nullable=False,
            )
        )


def downgrade() -> None:
    widen(False)
    with op.batch_alter_table("incubating_ideas", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_incubating_ideas_strain"), type_="check")
        batch_op.drop_column("strain")

    with op.batch_alter_table("purity", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purity_rank_id"))

    op.drop_table("purity")
    with op.batch_alter_table("accusations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_accusations_settlement_entity_id"))
        batch_op.drop_index(batch_op.f("ix_accusations_hunt_id"))
        batch_op.drop_index("ix_accusations_accused")

    op.drop_table("accusations")
    with op.batch_alter_table("witch_hunts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_witch_hunts_settlement_entity_id"))

    op.drop_table("witch_hunts")
    with op.batch_alter_table("purity_ranks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purity_ranks_people_entity_id"))

    op.drop_table("purity_ranks")
    op.drop_table("purifications")
    op.drop_table("nutrient_needs")
    with op.batch_alter_table("mishaps", schema=None) as batch_op:
        batch_op.drop_index("ix_mishaps_settlement")

    op.drop_table("mishaps")
    with op.batch_alter_table("luck_beliefs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_luck_beliefs_people_entity_id"))

    op.drop_table("luck_beliefs")
    op.drop_table("impurity_sources")
    op.drop_table("charms")
    op.drop_table("nutrition_scores")
    op.drop_table("diets")
    op.drop_table("bias_weights")
