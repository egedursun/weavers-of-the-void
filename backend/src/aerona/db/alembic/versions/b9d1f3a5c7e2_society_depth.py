import sqlalchemy as sa
from alembic import op

revision = "b9d1f3a5c7e2"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_standing",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "social_class",
            sa.Enum(
                "farmer",
                "artisan",
                "merchant",
                "priest",
                "warrior",
                "scribe",
                "noble",
                "serf_or_slave",
                "outcast",
                "monastic",
                name="social_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("fed_pct", sa.Integer(), nullable=False),
        sa.Column("needs_met_pct", sa.Integer(), nullable=False),
        sa.Column("luxury_pct", sa.Integer(), nullable=False),
        sa.Column("wealth", sa.Integer(), nullable=False),
        sa.Column("income", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fed_pct BETWEEN 0 AND 100", name=op.f("ck_class_standing_fed_pct_range")),
        sa.CheckConstraint("luxury_pct BETWEEN 0 AND 1000", name=op.f("ck_class_standing_luxury_pct_range")),
        sa.CheckConstraint("needs_met_pct BETWEEN 0 AND 100", name=op.f("ck_class_standing_needs_met_pct_range")),
        sa.CheckConstraint("wealth >= 0", name=op.f("ck_class_standing_wealth_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_class_standing_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "social_class", name=op.f("pk_class_standing")),
    )
    with op.batch_alter_table("class_standing", schema=None) as batch_op:
        batch_op.create_index("ix_class_standing_community", ["community_entity_id"], unique=False)

    op.create_table(
        "community_needs",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "social_class",
            sa.Enum(
                "farmer",
                "artisan",
                "merchant",
                "priest",
                "warrior",
                "scribe",
                "noble",
                "serf_or_slave",
                "outcast",
                "monastic",
                name="social_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
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
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("wanted", sa.Integer(), nullable=False),
        sa.Column("got", sa.Integer(), nullable=False),
        sa.Column("held_pct", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("got >= 0", name=op.f("ck_community_needs_got_min")),
        sa.CheckConstraint("held_pct IS NULL OR held_pct BETWEEN 0 AND 100", name=op.f("ck_community_needs_held_pct_range")),
        sa.CheckConstraint("wanted >= 0", name=op.f("ck_community_needs_wanted_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_community_needs_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "social_class", "commodity", name=op.f("pk_community_needs")),
    )
    with op.batch_alter_table("community_needs", schema=None) as batch_op:
        batch_op.create_index("ix_community_needs_community", ["community_entity_id"], unique=False)

    op.create_table(
        "corvee_levies",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("share_pct", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("by_hand", sa.Boolean(), nullable=False),
        sa.CheckConstraint("share_pct BETWEEN 0 AND 100", name=op.f("ck_corvee_levies_share_pct_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_corvee_levies_since_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_corvee_levies_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_corvee_levies_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("community_entity_id", name=op.f("pk_corvee_levies")),
    )
    op.create_table(
        "culture_drift_causes",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "god",
                "ruler",
                "neighbours",
                "ideology",
                "war_fought",
                "war_won",
                "war_lost",
                "plague",
                "famine",
                "trade",
                "conquest",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
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
                name="axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["community_entity_id"], ["entities.id"], name=op.f("fk_culture_drift_causes_community_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("community_entity_id", "cause", "axis", name=op.f("pk_culture_drift_causes")),
    )
    with op.batch_alter_table("culture_drift_causes", schema=None) as batch_op:
        batch_op.create_index("ix_culture_drift_causes_community", ["community_entity_id"], unique=False)

    op.create_table(
        "drift_impositions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "god",
                "ruler",
                "neighbours",
                "ideology",
                "war_fought",
                "war_won",
                "war_lost",
                "plague",
                "famine",
                "trade",
                "conquest",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
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
                name="axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("epochs_left", sa.Integer(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("amount BETWEEN -100 AND 100", name=op.f("ck_drift_impositions_amount_range")),
        sa.CheckConstraint("epochs_left >= 1", name=op.f("ck_drift_impositions_epochs_left_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_drift_impositions_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drift_impositions")),
    )
    with op.batch_alter_table("drift_impositions", schema=None) as batch_op:
        batch_op.create_index("ix_drift_impositions_community", ["community_entity_id"], unique=False)

    op.create_table(
        "labour_reasons",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "job",
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
                "idle",
                name="job",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Enum(
                "class", "price", "structure", "resource", "no_structure", "corvee", "held", name="reason", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("workers", sa.Integer(), nullable=False),
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
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "workshop",
            sa.Enum(
                "market",
                "granary",
                "warehouse",
                "mine",
                "lumber_camp",
                "fishery",
                "charcoal_kiln",
                "forge",
                "tannery",
                "mill",
                "brewery",
                "weavery",
                "stable",
                "mason_yard",
                "shipyard",
                "siege_yard",
                "alchemist",
                "shrine_workshop",
                "mint",
                name="workshop",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("price_pct", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("price_pct >= 0", name=op.f("ck_labour_reasons_price_pct_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_labour_reasons_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "job", "reason", name=op.f("pk_labour_reasons")),
    )
    with op.batch_alter_table("labour_reasons", schema=None) as batch_op:
        batch_op.create_index("ix_labour_reasons_community", ["community_entity_id"], unique=False)

    op.create_table(
        "mobility_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "event", sa.Enum("ennobled", "enslaved", "freed", "ruined", name="event", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=True),
        sa.Column("house_entity_id", sa.Integer(), nullable=True),
        sa.Column("other_entity_id", sa.Integer(), nullable=True),
        sa.Column("by_hand", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_mobility_events_count_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_mobility_events_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_mobility_events_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_mobility_events_house_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_mobility_events_mortal_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["other_entity_id"], ["entities.id"], name=op.f("fk_mobility_events_other_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mobility_events")),
    )
    with op.batch_alter_table("mobility_events", schema=None) as batch_op:
        batch_op.create_index("ix_mobility_events_community", ["community_entity_id"], unique=False)

    op.create_table(
        "polity_loyalty",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("member_entity_id", sa.Integer(), nullable=False),
        sa.Column("value_distance", sa.Integer(), nullable=False),
        sa.Column("grievances", sa.Integer(), nullable=False),
        sa.Column("benefits", sa.Integer(), nullable=False),
        sa.Column("satisfaction", sa.Integer(), nullable=False),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("parts", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("benefits >= 0", name=op.f("ck_polity_loyalty_benefits_min")),
        sa.CheckConstraint("grievances >= 0", name=op.f("ck_polity_loyalty_grievances_min")),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_polity_loyalty_loyalty_range")),
        sa.CheckConstraint("value_distance >= 0", name=op.f("ck_polity_loyalty_value_distance_min")),
        sa.ForeignKeyConstraint(["member_entity_id"], ["entities.id"], name=op.f("fk_polity_loyalty_member_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_loyalty_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "member_entity_id", name=op.f("pk_polity_loyalty")),
    )
    with op.batch_alter_table("polity_loyalty", schema=None) as batch_op:
        batch_op.create_index("ix_polity_loyalty_member", ["member_entity_id"], unique=False)

    with op.batch_alter_table("community_labour", schema=None) as batch_op:
        batch_op.add_column(sa.Column("held", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("community_societies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("gini", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_check_constraint(op.f("ck_community_societies_gini_range"), "gini BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("community_societies", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_community_societies_gini_range"), type_="check")
        batch_op.drop_column("gini")

    with op.batch_alter_table("community_labour", schema=None) as batch_op:
        batch_op.drop_column("held")

    with op.batch_alter_table("polity_loyalty", schema=None) as batch_op:
        batch_op.drop_index("ix_polity_loyalty_member")

    op.drop_table("polity_loyalty")
    with op.batch_alter_table("mobility_events", schema=None) as batch_op:
        batch_op.drop_index("ix_mobility_events_community")

    op.drop_table("mobility_events")
    with op.batch_alter_table("labour_reasons", schema=None) as batch_op:
        batch_op.drop_index("ix_labour_reasons_community")

    op.drop_table("labour_reasons")
    with op.batch_alter_table("drift_impositions", schema=None) as batch_op:
        batch_op.drop_index("ix_drift_impositions_community")

    op.drop_table("drift_impositions")
    with op.batch_alter_table("culture_drift_causes", schema=None) as batch_op:
        batch_op.drop_index("ix_culture_drift_causes_community")

    op.drop_table("culture_drift_causes")
    op.drop_table("corvee_levies")
    with op.batch_alter_table("community_needs", schema=None) as batch_op:
        batch_op.drop_index("ix_community_needs_community")

    op.drop_table("community_needs")
    with op.batch_alter_table("class_standing", schema=None) as batch_op:
        batch_op.drop_index("ix_class_standing_community")

    op.drop_table("class_standing")
