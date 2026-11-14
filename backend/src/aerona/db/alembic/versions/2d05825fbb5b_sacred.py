import sqlalchemy as sa
from alembic import op

revision = "2d05825fbb5b"
down_revision = "40759d04fa80"
branch_labels = None
depends_on = None

PLAN_OLD = ("ecological_transformation", "bloodline", "conversion", "wonder")
PLAN_NEW = ("ecological_transformation", "bloodline", "conversion", "wonder", "forecast")


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    old, new = (PLAN_OLD, PLAN_NEW) if forward else (PLAN_NEW, PLAN_OLD)
    with op.batch_alter_table("long_plans", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of(old, "kind"), type_=enum_of(new, "kind"), existing_nullable=False)


def upgrade() -> None:
    retype(forward=True)
    op.create_table(
        "emotion_harvests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "emotion",
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
                name="emotion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("essence", sa.Integer(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_emotion_harvests_count_min")),
        sa.CheckConstraint("essence >= 0", name=op.f("ck_emotion_harvests_essence_min")),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_emotion_harvests_god_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emotion_harvests")),
    )
    with op.batch_alter_table("emotion_harvests", schema=None) as batch_op:
        batch_op.create_index("ix_emotion_harvests_god_epoch", ["god_node_id", "epoch"], unique=False)

    op.create_table(
        "god_feedings",
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "emotion",
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
                name="emotion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("harvested", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("harvested >= 0", name=op.f("ck_god_feedings_harvested_min")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_god_feedings_weight_range")),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_god_feedings_god_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("god_node_id", "emotion", name=op.f("pk_god_feedings")),
    )
    op.create_table(
        "divination_systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("augury", "haruspicy", "astrology", "oracle", "lots", "dream_reading", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "validity",
            sa.Enum("god_answers", "seer_gift", "natural_law", "noise", name="validity", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.Column("diviners", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("diviners >= 0", name=op.f("ck_divination_systems_diviners_min")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_divination_systems_founded_epoch_min")),
        sa.CheckConstraint("trust BETWEEN 0 AND 100", name=op.f("ck_divination_systems_trust_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_divination_systems_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divination_systems")),
    )
    with op.batch_alter_table("divination_systems", schema=None) as batch_op:
        batch_op.create_index("ix_divination_systems_people", ["people_entity_id"], unique=False)

    op.create_table(
        "doctrine_afterlives",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "model",
            sa.Enum(
                "judged_realms",
                "common_realm",
                "warrior_hall",
                "ancestor_hall",
                "rebirth",
                "wandering",
                "union",
                "oblivion",
                name="model",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("aligned", sa.Boolean(), nullable=False),
        sa.Column("aligned_by_node_id", sa.Integer(), nullable=True),
        sa.Column("shocks", sa.Integer(), nullable=False),
        sa.Column("testimonies", sa.Integer(), nullable=False),
        sa.Column("doubt", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("doubt BETWEEN 0 AND 100", name=op.f("ck_doctrine_afterlives_doubt_range")),
        sa.CheckConstraint("shocks >= 0", name=op.f("ck_doctrine_afterlives_shocks_min")),
        sa.CheckConstraint("testimonies >= 0", name=op.f("ck_doctrine_afterlives_testimonies_min")),
        sa.ForeignKeyConstraint(["aligned_by_node_id"], ["nodes.id"], name=op.f("fk_doctrine_afterlives_aligned_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_doctrine_afterlives_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cult_entity_id", name=op.f("pk_doctrine_afterlives")),
    )
    op.create_table(
        "doctrine_sacraments",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("birth_blessing", "initiation", "marriage", "last_rites", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "protection", sa.Enum("routing", "possession", "unrest", name="protection", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_doctrine_sacraments_strength_range")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_doctrine_sacraments_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cult_entity_id", "kind", name=op.f("pk_doctrine_sacraments")),
    )
    op.create_table(
        "faith_climates",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("piety_drift", sa.Integer(), nullable=False),
        sa.Column("literacy_pull", sa.Integer(), nullable=False),
        sa.Column("science_pull", sa.Integer(), nullable=False),
        sa.Column("prosperity_pull", sa.Integer(), nullable=False),
        sa.Column("city_pull", sa.Integer(), nullable=False),
        sa.Column("silence_pull", sa.Integer(), nullable=False),
        sa.Column("disaster_push", sa.Integer(), nullable=False),
        sa.Column("miracle_push", sa.Integer(), nullable=False),
        sa.Column("war_push", sa.Integer(), nullable=False),
        sa.Column("dominion_push", sa.Integer(), nullable=False),
        sa.Column("silent_epochs", sa.Integer(), nullable=False),
        sa.Column("godless", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("city_pull BETWEEN -100 AND 100", name=op.f("ck_faith_climates_city_pull_range")),
        sa.CheckConstraint("disaster_push BETWEEN -100 AND 100", name=op.f("ck_faith_climates_disaster_push_range")),
        sa.CheckConstraint("dominion_push BETWEEN -100 AND 100", name=op.f("ck_faith_climates_dominion_push_range")),
        sa.CheckConstraint("literacy_pull BETWEEN -100 AND 100", name=op.f("ck_faith_climates_literacy_pull_range")),
        sa.CheckConstraint("miracle_push BETWEEN -100 AND 100", name=op.f("ck_faith_climates_miracle_push_range")),
        sa.CheckConstraint("piety_drift BETWEEN -100 AND 100", name=op.f("ck_faith_climates_piety_drift_range")),
        sa.CheckConstraint("prosperity_pull BETWEEN -100 AND 100", name=op.f("ck_faith_climates_prosperity_pull_range")),
        sa.CheckConstraint("science_pull BETWEEN -100 AND 100", name=op.f("ck_faith_climates_science_pull_range")),
        sa.CheckConstraint("silence_pull BETWEEN -100 AND 100", name=op.f("ck_faith_climates_silence_pull_range")),
        sa.CheckConstraint("silent_epochs >= 0", name=op.f("ck_faith_climates_silent_epochs_min")),
        sa.CheckConstraint("war_push BETWEEN -100 AND 100", name=op.f("ck_faith_climates_war_push_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_faith_climates_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", name=op.f("pk_faith_climates")),
    )
    op.create_table(
        "forecast_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_entity_id", sa.Integer(), nullable=False),
        sa.Column("subject_entity_id", sa.Integer(), nullable=True),
        sa.Column("archive", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("forecast_psi", sa.Integer(), nullable=False),
        sa.Column("actual_psi", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("disruption", sa.Integer(), nullable=False),
        sa.Column("disrupted_by_node_id", sa.Integer(), nullable=True),
        sa.Column("built_epoch", sa.Integer(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accuracy BETWEEN 0 AND 100", name=op.f("ck_forecast_models_accuracy_range")),
        sa.CheckConstraint("actual_psi BETWEEN 0 AND 100", name=op.f("ck_forecast_models_actual_psi_range")),
        sa.CheckConstraint("archive >= 0", name=op.f("ck_forecast_models_archive_min")),
        sa.CheckConstraint("disruption BETWEEN 0 AND 100", name=op.f("ck_forecast_models_disruption_range")),
        sa.CheckConstraint("forecast_psi BETWEEN 0 AND 100", name=op.f("ck_forecast_models_forecast_psi_range")),
        sa.CheckConstraint("horizon >= 0", name=op.f("ck_forecast_models_horizon_min")),
        sa.ForeignKeyConstraint(["disrupted_by_node_id"], ["nodes.id"], name=op.f("fk_forecast_models_disrupted_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_entity_id"], ["entities.id"], name=op.f("fk_forecast_models_order_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["long_plans.id"], name=op.f("fk_forecast_models_plan_id_long_plans"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"], name=op.f("fk_forecast_models_subject_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_forecast_models")),
    )
    with op.batch_alter_table("forecast_models", schema=None) as batch_op:
        batch_op.create_index("ix_forecast_models_order", ["order_entity_id"], unique=False)
        batch_op.create_index("ix_forecast_models_subject", ["subject_entity_id"], unique=False)

    op.create_table(
        "genius_loci",
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("place_entity_id", sa.Integer(), nullable=True),
        sa.Column("community_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "river",
                "spring",
                "lake",
                "well",
                "shore",
                "grove",
                "forest",
                "mountain",
                "cave",
                "crossroads",
                "wilds",
                "field",
                "city",
                "hearth",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("temperament", sa.Integer(), nullable=False),
        sa.Column("contentment", sa.Integer(), nullable=False),
        sa.Column("offerings", sa.Integer(), nullable=False),
        sa.Column("owed", sa.Integer(), nullable=False),
        sa.Column("favour", sa.Integer(), nullable=False),
        sa.Column(
            "offended",
            sa.Enum("pollution", "clearing", "unpaid", "taboo", name="offended", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("last_offering_epoch", sa.Integer(), nullable=True),
        sa.Column("bound_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("contentment BETWEEN 0 AND 100", name=op.f("ck_genius_loci_contentment_range")),
        sa.CheckConstraint("favour BETWEEN 0 AND 100", name=op.f("ck_genius_loci_favour_range")),
        sa.CheckConstraint("offerings >= 0", name=op.f("ck_genius_loci_offerings_min")),
        sa.CheckConstraint("owed >= 0", name=op.f("ck_genius_loci_owed_min")),
        sa.CheckConstraint("temperament BETWEEN 0 AND 100", name=op.f("ck_genius_loci_temperament_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_genius_loci_community_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_genius_loci_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_genius_loci_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("spirit_entity_id", name=op.f("pk_genius_loci")),
    )
    with op.batch_alter_table("genius_loci", schema=None) as batch_op:
        batch_op.create_index("ix_genius_loci_community", ["community_entity_id"], unique=False)
        batch_op.create_index("ix_genius_loci_place", ["place_entity_id"], unique=False)

    op.create_table(
        "mystics",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("seeker", "visionary", "revered", "persecuted", "founder", "lapsed", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("visions", sa.Integer(), nullable=False),
        sa.Column("genuine_visions", sa.Integer(), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False),
        sa.Column("answered_by_node_id", sa.Integer(), nullable=True),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("founded_entity_id", sa.Integer(), nullable=True),
        sa.Column("reverence", sa.Integer(), nullable=False),
        sa.Column("persecution", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("last_vision_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("followers >= 0", name=op.f("ck_mystics_followers_min")),
        sa.CheckConstraint("genuine_visions >= 0", name=op.f("ck_mystics_genuine_visions_min")),
        sa.CheckConstraint("persecution BETWEEN 0 AND 100", name=op.f("ck_mystics_persecution_range")),
        sa.CheckConstraint("reverence BETWEEN 0 AND 100", name=op.f("ck_mystics_reverence_range")),
        sa.CheckConstraint("visions >= 0", name=op.f("ck_mystics_visions_min")),
        sa.ForeignKeyConstraint(["answered_by_node_id"], ["nodes.id"], name=op.f("fk_mystics_answered_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_mystics_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["founded_entity_id"], ["entities.id"], name=op.f("fk_mystics_founded_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_mystics_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_mystics")),
    )
    with op.batch_alter_table("mystics", schema=None) as batch_op:
        batch_op.create_index("ix_mystics_cult", ["cult_entity_id"], unique=False)

    op.create_table(
        "petitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("petitioner_node_id", sa.Integer(), nullable=False),
        sa.Column("office_spirit_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("healing", "harvest", "fertility", "safe_passage", "prosperity", "suit", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("defendant_spirit_id", sa.Integer(), nullable=True),
        sa.Column("bribe", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("filed", "delayed", "granted", "denied", "appealed", "dismissed", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("filed_epoch", sa.Integer(), nullable=False),
        sa.Column("due_epoch", sa.Integer(), nullable=False),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("appealed_to_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bribe >= 0", name=op.f("ck_petitions_bribe_min")),
        sa.CheckConstraint("filed_epoch >= 0", name=op.f("ck_petitions_filed_epoch_min")),
        sa.ForeignKeyConstraint(["appealed_to_id"], ["entities.id"], name=op.f("fk_petitions_appealed_to_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["defendant_spirit_id"], ["entities.id"], name=op.f("fk_petitions_defendant_spirit_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["office_spirit_id"], ["entities.id"], name=op.f("fk_petitions_office_spirit_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["petitioner_node_id"], ["nodes.id"], name=op.f("fk_petitions_petitioner_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_petitions")),
    )
    with op.batch_alter_table("petitions", schema=None) as batch_op:
        batch_op.create_index("ix_petitions_office", ["office_spirit_id", "status"], unique=False)
        batch_op.create_index("ix_petitions_petitioner", ["petitioner_node_id"], unique=False)

    op.create_table(
        "sacraments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("birth_blessing", "initiation", "marriage", "last_rites", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("priest_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("missed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_sacraments_epoch_min")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_sacraments_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_sacraments_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["priest_entity_id"], ["entities.id"], name=op.f("fk_sacraments_priest_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sacraments")),
    )
    with op.batch_alter_table("sacraments", schema=None) as batch_op:
        batch_op.create_index("ix_sacraments_cult", ["cult_entity_id"], unique=False)
        batch_op.create_index("ix_sacraments_mortal", ["mortal_entity_id", "kind"], unique=False)

    op.create_table(
        "spirit_offices",
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "rank",
            sa.Enum("hearth", "local", "city", "province", "ministry", name="rank", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("superior_spirit_id", sa.Integer(), nullable=True),
        sa.Column("overseer_node_id", sa.Integer(), nullable=True),
        sa.Column("jurisdiction_entity_id", sa.Integer(), nullable=True),
        sa.Column("merit", sa.Integer(), nullable=False),
        sa.Column("corruption", sa.Integer(), nullable=False),
        sa.Column("resolved", sa.Integer(), nullable=False),
        sa.Column("neglected", sa.Integer(), nullable=False),
        sa.Column("dismissed", sa.Boolean(), nullable=False),
        sa.Column("appointed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("corruption BETWEEN 0 AND 100", name=op.f("ck_spirit_offices_corruption_range")),
        sa.CheckConstraint("merit >= 0", name=op.f("ck_spirit_offices_merit_min")),
        sa.CheckConstraint("neglected >= 0", name=op.f("ck_spirit_offices_neglected_min")),
        sa.CheckConstraint("resolved >= 0", name=op.f("ck_spirit_offices_resolved_min")),
        sa.ForeignKeyConstraint(
            ["jurisdiction_entity_id"], ["entities.id"], name=op.f("fk_spirit_offices_jurisdiction_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["overseer_node_id"], ["nodes.id"], name=op.f("fk_spirit_offices_overseer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_spirit_offices_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superior_spirit_id"], ["entities.id"], name=op.f("fk_spirit_offices_superior_spirit_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("spirit_entity_id", name=op.f("pk_spirit_offices")),
    )
    with op.batch_alter_table("spirit_offices", schema=None) as batch_op:
        batch_op.create_index("ix_spirit_offices_jurisdiction", ["jurisdiction_entity_id"], unique=False)
        batch_op.create_index("ix_spirit_offices_overseer", ["overseer_node_id"], unique=False)
        batch_op.create_index("ix_spirit_offices_superior", ["superior_spirit_id"], unique=False)

    op.create_table(
        "theodicy_crises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "cause", sa.Enum("plague", "famine", "defeat", "disaster", name="cause", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("suffering", sa.Integer(), nullable=False),
        sa.Column("answered", sa.Boolean(), nullable=False),
        sa.Column(
            "resolution",
            sa.Enum(
                "pending",
                "answered",
                "argued",
                "new_doctrine",
                "conversion",
                "secular_drift",
                name="resolution",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("theologian_entity_id", sa.Integer(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_theodicy_crises_started_epoch_min")),
        sa.CheckConstraint("suffering BETWEEN 0 AND 100", name=op.f("ck_theodicy_crises_suffering_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_theodicy_crises_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_theodicy_crises_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_theodicy_crises_god_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["theologian_entity_id"], ["entities.id"], name=op.f("fk_theodicy_crises_theologian_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_theodicy_crises")),
    )
    with op.batch_alter_table("theodicy_crises", schema=None) as batch_op:
        batch_op.create_index("ix_theodicy_crises_community", ["community_entity_id"], unique=False)
        batch_op.create_index("ix_theodicy_crises_cult", ["cult_entity_id"], unique=False)

    op.create_table(
        "visions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mystic_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("vision", "union", "voice", "trance", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("sender_node_id", sa.Integer(), nullable=True),
        sa.Column("genuine", sa.Boolean(), nullable=False),
        sa.Column("awe", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("awe BETWEEN 0 AND 100", name=op.f("ck_visions_awe_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_visions_epoch_min")),
        sa.ForeignKeyConstraint(["mystic_entity_id"], ["entities.id"], name=op.f("fk_visions_mystic_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_node_id"], ["nodes.id"], name=op.f("fk_visions_sender_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visions")),
    )
    with op.batch_alter_table("visions", schema=None) as batch_op:
        batch_op.create_index("ix_visions_mystic", ["mystic_entity_id", "epoch"], unique=False)

    op.create_table(
        "divinations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("diviner_entity_id", sa.Integer(), nullable=True),
        sa.Column("client_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "question",
            sa.Enum("battle", "war", "wedding", "coronation", "harvest", name="question", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "verdict", sa.Enum("auspicious", "inauspicious", "unclear", name="verdict", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "true_verdict",
            sa.Enum("auspicious", "inauspicious", "unclear", name="true_verdict", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("heeded", sa.Boolean(), nullable=False),
        sa.Column("swayed_by_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_divinations_epoch_min")),
        sa.ForeignKeyConstraint(["client_entity_id"], ["entities.id"], name=op.f("fk_divinations_client_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["diviner_entity_id"], ["entities.id"], name=op.f("fk_divinations_diviner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["swayed_by_node_id"], ["nodes.id"], name=op.f("fk_divinations_swayed_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["system_id"], ["divination_systems.id"], name=op.f("fk_divinations_system_id_divination_systems"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divinations")),
    )
    with op.batch_alter_table("divinations", schema=None) as batch_op:
        batch_op.create_index("ix_divinations_client", ["client_entity_id", "epoch"], unique=False)
        batch_op.create_index("ix_divinations_system", ["system_id"], unique=False)

    op.create_table(
        "millenarian_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("prophet_entity_id", sa.Integer(), nullable=True),
        sa.Column("prophecy_entity_id", sa.Integer(), nullable=True),
        sa.Column("movement_id", sa.Integer(), nullable=True),
        sa.Column(
            "stage",
            sa.Enum(
                "stirring", "gathering", "vigil", "marching", "redated", "sect", "dispersed", name="stage", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("end_epoch", sa.Integer(), nullable=False),
        sa.Column("members", sa.Integer(), nullable=False),
        sa.Column("conviction", sa.Integer(), nullable=False),
        sa.Column("given_up", sa.Integer(), nullable=False),
        sa.Column("idle_share", sa.Integer(), nullable=False),
        sa.Column("attacks", sa.Integer(), nullable=False),
        sa.Column("dates_set", sa.Integer(), nullable=False),
        sa.Column("sect_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("attacks >= 0", name=op.f("ck_millenarian_movements_attacks_min")),
        sa.CheckConstraint("conviction BETWEEN 0 AND 100", name=op.f("ck_millenarian_movements_conviction_range")),
        sa.CheckConstraint("dates_set >= 0", name=op.f("ck_millenarian_movements_dates_set_min")),
        sa.CheckConstraint("given_up >= 0", name=op.f("ck_millenarian_movements_given_up_min")),
        sa.CheckConstraint("idle_share BETWEEN 0 AND 100", name=op.f("ck_millenarian_movements_idle_share_range")),
        sa.CheckConstraint("members >= 0", name=op.f("ck_millenarian_movements_members_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_millenarian_movements_since_epoch_min")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_millenarian_movements_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["movement_id"], ["movements.id"], name=op.f("fk_millenarian_movements_movement_id_movements"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["prophecy_entity_id"], ["entities.id"], name=op.f("fk_millenarian_movements_prophecy_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["prophet_entity_id"], ["entities.id"], name=op.f("fk_millenarian_movements_prophet_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sect_entity_id"], ["entities.id"], name=op.f("fk_millenarian_movements_sect_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["settlement_entity_id"], ["entities.id"], name=op.f("fk_millenarian_movements_settlement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_millenarian_movements")),
    )
    with op.batch_alter_table("millenarian_movements", schema=None) as batch_op:
        batch_op.create_index("ix_millenarian_movements_cult", ["cult_entity_id"], unique=False)
        batch_op.create_index("ix_millenarian_movements_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "foresights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seer_node_id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "predicate",
            sa.Enum(
                "dies",
                "falls",
                "born_in",
                "sky_event",
                "war_between",
                "ruler_of",
                "within_epochs",
                name="predicate",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("due_epoch", sa.Integer(), nullable=False),
        sa.Column("certainty", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum("power", "divination", "god", name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("divination_id", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.Enum("pending", "fulfilled", "failed", "clouded", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("checked_epoch", sa.Integer(), nullable=True),
        sa.Column("made_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("certainty BETWEEN 0 AND 100", name=op.f("ck_foresights_certainty_range")),
        sa.CheckConstraint("horizon >= 0", name=op.f("ck_foresights_horizon_min")),
        sa.CheckConstraint("made_epoch >= 0", name=op.f("ck_foresights_made_epoch_min")),
        sa.ForeignKeyConstraint(["divination_id"], ["divinations.id"], name=op.f("fk_foresights_divination_id_divinations"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seer_node_id"], ["nodes.id"], name=op.f("fk_foresights_seer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_foresights_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_foresights")),
    )
    with op.batch_alter_table("foresights", schema=None) as batch_op:
        batch_op.create_index("ix_foresights_due", ["status", "due_epoch"], unique=False)
        batch_op.create_index("ix_foresights_seer", ["seer_node_id", "status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("foresights", schema=None) as batch_op:
        batch_op.drop_index("ix_foresights_seer")
        batch_op.drop_index("ix_foresights_due")

    op.drop_table("foresights")
    with op.batch_alter_table("millenarian_movements", schema=None) as batch_op:
        batch_op.drop_index("ix_millenarian_movements_settlement")
        batch_op.drop_index("ix_millenarian_movements_cult")

    op.drop_table("millenarian_movements")
    with op.batch_alter_table("divinations", schema=None) as batch_op:
        batch_op.drop_index("ix_divinations_system")
        batch_op.drop_index("ix_divinations_client")

    op.drop_table("divinations")
    with op.batch_alter_table("visions", schema=None) as batch_op:
        batch_op.drop_index("ix_visions_mystic")

    op.drop_table("visions")
    with op.batch_alter_table("theodicy_crises", schema=None) as batch_op:
        batch_op.drop_index("ix_theodicy_crises_cult")
        batch_op.drop_index("ix_theodicy_crises_community")

    op.drop_table("theodicy_crises")
    with op.batch_alter_table("spirit_offices", schema=None) as batch_op:
        batch_op.drop_index("ix_spirit_offices_superior")
        batch_op.drop_index("ix_spirit_offices_overseer")
        batch_op.drop_index("ix_spirit_offices_jurisdiction")

    op.drop_table("spirit_offices")
    with op.batch_alter_table("sacraments", schema=None) as batch_op:
        batch_op.drop_index("ix_sacraments_mortal")
        batch_op.drop_index("ix_sacraments_cult")

    op.drop_table("sacraments")
    with op.batch_alter_table("petitions", schema=None) as batch_op:
        batch_op.drop_index("ix_petitions_petitioner")
        batch_op.drop_index("ix_petitions_office")

    op.drop_table("petitions")
    with op.batch_alter_table("mystics", schema=None) as batch_op:
        batch_op.drop_index("ix_mystics_cult")

    op.drop_table("mystics")
    with op.batch_alter_table("genius_loci", schema=None) as batch_op:
        batch_op.drop_index("ix_genius_loci_place")
        batch_op.drop_index("ix_genius_loci_community")

    op.drop_table("genius_loci")
    with op.batch_alter_table("forecast_models", schema=None) as batch_op:
        batch_op.drop_index("ix_forecast_models_subject")
        batch_op.drop_index("ix_forecast_models_order")

    op.drop_table("forecast_models")
    op.drop_table("faith_climates")
    op.drop_table("doctrine_sacraments")
    op.drop_table("doctrine_afterlives")
    with op.batch_alter_table("divination_systems", schema=None) as batch_op:
        batch_op.drop_index("ix_divination_systems_people")

    op.drop_table("divination_systems")
    op.drop_table("god_feedings")
    with op.batch_alter_table("emotion_harvests", schema=None) as batch_op:
        batch_op.drop_index("ix_emotion_harvests_god_epoch")

    op.drop_table("emotion_harvests")
    retype(forward=False)
