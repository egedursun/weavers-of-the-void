import sqlalchemy as sa
from alembic import op

revision = "0d554b5d77ad"
down_revision = "4eb7d40871b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "body_marks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "tattoo",
                "scar",
                "piercing",
                "shaping",
                "filed_teeth",
                "cosmetic",
                "jewellery",
                "brand",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "meaning",
            sa.Enum(
                "status",
                "clan",
                "deed",
                "age_set",
                "marriage",
                "mourning",
                "protection",
                "crime",
                name="meaning",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("placed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("placed_epoch >= 0", name=op.f("ck_body_marks_placed_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_body_marks_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_body_marks")),
    )
    with op.batch_alter_table("body_marks", schema=None) as batch_op:
        batch_op.create_index("ix_body_marks_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "name_forms",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum("birth", "secret", "deed", "initiation", "marriage", "vow", "ascension", name="form", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("given_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("given_epoch >= 0", name=op.f("ck_name_forms_given_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_name_forms_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "form", name=op.f("pk_name_forms")),
    )
    op.create_table(
        "age_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("initiated_from", sa.Integer(), nullable=False),
        sa.Column("initiated_to", sa.Integer(), nullable=True),
        sa.Column(
            "grade",
            sa.Enum("children", "youths", "warriors", "junior_elders", "senior_elders", name="grade", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("promoted_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("initiated_from >= 0", name=op.f("ck_age_sets_initiated_from_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_age_sets_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_age_sets")),
    )
    with op.batch_alter_table("age_sets", schema=None) as batch_op:
        batch_op.create_index("ix_age_sets_people", ["people_entity_id"], unique=False)

    op.create_table(
        "border_controls",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("delay", sa.Integer(), nullable=False),
        sa.Column("enforcement", sa.Integer(), nullable=False),
        sa.Column("corruption", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("corruption BETWEEN 0 AND 100", name=op.f("ck_border_controls_corruption_range")),
        sa.CheckConstraint("delay >= 0", name=op.f("ck_border_controls_delay_min")),
        sa.CheckConstraint("enforcement BETWEEN 0 AND 100", name=op.f("ck_border_controls_enforcement_range")),
        sa.CheckConstraint("fee >= 0", name=op.f("ck_border_controls_fee_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_border_controls_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_border_controls")),
    )
    op.create_table(
        "commutes",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("distance", sa.Integer(), nullable=False),
        sa.Column("labour_lost", sa.Integer(), nullable=False),
        sa.Column("worker_camp", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("distance BETWEEN 0 AND 100", name=op.f("ck_commutes_distance_range")),
        sa.CheckConstraint("labour_lost BETWEEN 0 AND 100", name=op.f("ck_commutes_labour_lost_range")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_commutes_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_commutes")),
    )
    op.create_table(
        "cooperatives",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum("mill", "boats", "irrigation", "insurance", "burial", "credit", name="purpose", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("pool", sa.Integer(), nullable=False),
        sa.Column("members", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("members >= 0", name=op.f("ck_cooperatives_members_min")),
        sa.CheckConstraint("pool >= 0", name=op.f("ck_cooperatives_pool_min")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_cooperatives_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_cooperatives")),
    )
    op.create_table(
        "intoxicant_customs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "intoxicant",
            sa.Enum("brew", "wine", "spirits", "smoke", "leaf", "fungus", "essence", name="intoxicant", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "use", sa.Enum("daily", "feast", "rite", "mourning", "forbidden", name="use", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("acceptance", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("acceptance BETWEEN 0 AND 100", name=op.f("ck_intoxicant_customs_acceptance_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_intoxicant_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "intoxicant", name=op.f("pk_intoxicant_customs")),
    )
    op.create_table(
        "mark_customs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "tattoo",
                "scar",
                "piercing",
                "shaping",
                "filed_teeth",
                "cosmetic",
                "jewellery",
                "brand",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "meaning",
            sa.Enum(
                "status",
                "clan",
                "deed",
                "age_set",
                "marriage",
                "mourning",
                "protection",
                "crime",
                name="meaning",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_mark_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "kind", name=op.f("pk_mark_customs")),
    )
    op.create_table(
        "measure_standards",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("standard", sa.Boolean(), nullable=False),
        sa.Column("adopted_epoch", sa.Integer(), nullable=False),
        sa.Column("fraud", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fraud BETWEEN 0 AND 100", name=op.f("ck_measure_standards_fraud_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_measure_standards_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_measure_standards")),
    )
    op.create_table(
        "membership_categories",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "citizen", "subject", "resident_foreigner", "protected_minority", "bound", name="category", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("rights", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_membership_categories_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "category", name=op.f("pk_membership_categories")),
    )
    op.create_table(
        "memberships",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "citizen", "subject", "resident_foreigner", "protected_minority", "bound", name="category", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "path",
            sa.Enum(
                "descent",
                "birthplace",
                "residence",
                "conversion",
                "service",
                "purchase",
                "grant",
                name="path",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_memberships_since_epoch_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_memberships_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_memberships_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_memberships")),
    )
    with op.batch_alter_table("memberships", schema=None) as batch_op:
        batch_op.create_index("ix_memberships_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "naming_customs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "pattern", sa.Enum("given", "parent", "clan", "teknonym", name="pattern", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("secret_names", sa.Boolean(), nullable=False),
        sa.Column("taboo_epochs", sa.Integer(), nullable=False),
        sa.Column("rename_on_initiation", sa.Boolean(), nullable=False),
        sa.Column("rename_on_marriage", sa.Boolean(), nullable=False),
        sa.Column("rename_on_vow", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("taboo_epochs >= 0", name=op.f("ck_naming_customs_taboo_epochs_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_naming_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_naming_customs")),
    )
    op.create_table(
        "poor_relief",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("granary", "alms", "workhouse", "parish", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("budget", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("budget >= 0", name=op.f("ck_poor_relief_budget_min")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_poor_relief_reach_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_poor_relief_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_poor_relief")),
    )
    op.create_table(
        "revivals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("dominant_entity_id", sa.Integer(), nullable=True),
        sa.Column("aim", sa.Enum("restore", "synthesise", "adopt", name="aim", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("steady", "stress", "distortion", "revitalisation", "new_steady", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "goal",
            sa.Enum("revive_language", "restore_god", "expel_foreigners", "adopt_ways", name="goal", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("prophet_node_id", sa.Integer(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_revivals_started_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_revivals_strength_range")),
        sa.ForeignKeyConstraint(["dominant_entity_id"], ["entities.id"], name=op.f("fk_revivals_dominant_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_revivals_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prophet_node_id"], ["nodes.id"], name=op.f("fk_revivals_prophet_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_revivals")),
    )
    with op.batch_alter_table("revivals", schema=None) as batch_op:
        batch_op.create_index("ix_revivals_people", ["people_entity_id"], unique=False)

    op.create_table(
        "taverns",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("keeper_node_id", sa.Integer(), nullable=True),
        sa.Column("patrons", sa.Integer(), nullable=False),
        sa.Column("brawls", sa.Integer(), nullable=False),
        sa.Column("lodging", sa.Integer(), nullable=False),
        sa.Column("rumours", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("brawls >= 0", name=op.f("ck_taverns_brawls_min")),
        sa.CheckConstraint("lodging >= 0", name=op.f("ck_taverns_lodging_min")),
        sa.CheckConstraint("patrons >= 0", name=op.f("ck_taverns_patrons_min")),
        sa.CheckConstraint("rumours >= 0", name=op.f("ck_taverns_rumours_min")),
        sa.ForeignKeyConstraint(["keeper_node_id"], ["nodes.id"], name=op.f("fk_taverns_keeper_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_taverns_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_taverns")),
    )
    op.create_table(
        "time_budgets",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
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
                "worker",
                "professional",
                "official",
                "citizen",
                "unemployed",
                name="social_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("work", sa.Integer(), nullable=False),
        sa.Column("rest", sa.Integer(), nullable=False),
        sa.Column("worship", sa.Integer(), nullable=False),
        sa.Column("leisure", sa.Integer(), nullable=False),
        sa.Column("travel", sa.Integer(), nullable=False),
        sa.Column("service", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("leisure BETWEEN 0 AND 100", name=op.f("ck_time_budgets_leisure_range")),
        sa.CheckConstraint("rest BETWEEN 0 AND 100", name=op.f("ck_time_budgets_rest_range")),
        sa.CheckConstraint("service BETWEEN 0 AND 100", name=op.f("ck_time_budgets_service_range")),
        sa.CheckConstraint("travel BETWEEN 0 AND 100", name=op.f("ck_time_budgets_travel_range")),
        sa.CheckConstraint("work BETWEEN 0 AND 100", name=op.f("ck_time_budgets_work_range")),
        sa.CheckConstraint("worship BETWEEN 0 AND 100", name=op.f("ck_time_budgets_worship_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_time_budgets_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "social_class", name=op.f("pk_time_budgets")),
    )
    op.create_table(
        "welfare_houses",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("patron_node_id", sa.Integer(), nullable=True),
        sa.Column("inmates", sa.Integer(), nullable=False),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("inmates >= 0", name=op.f("ck_welfare_houses_inmates_min")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_welfare_houses_upkeep_min")),
        sa.ForeignKeyConstraint(["patron_node_id"], ["nodes.id"], name=op.f("fk_welfare_houses_patron_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_welfare_houses_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_welfare_houses")),
    )
    op.create_table(
        "age_set_members",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("age_set_id", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["age_set_id"], ["age_sets.id"], name=op.f("fk_age_set_members_age_set_id_age_sets"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_age_set_members_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_age_set_members")),
    )
    with op.batch_alter_table("age_set_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_age_set_members_age_set_id"), ["age_set_id"], unique=False)

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("witness", "trace", "document", "confession", "divination", "magic", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("points_to_node_id", sa.Integer(), nullable=True),
        sa.Column("reliability", sa.Integer(), nullable=False),
        sa.Column("forged", sa.Boolean(), nullable=False),
        sa.Column("found_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("found_epoch >= 0", name=op.f("ck_evidence_found_epoch_min")),
        sa.CheckConstraint("reliability BETWEEN 0 AND 100", name=op.f("ck_evidence_reliability_range")),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_evidence_case_id_crime_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["points_to_node_id"], ["nodes.id"], name=op.f("fk_evidence_points_to_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
    )
    with op.batch_alter_table("evidence", schema=None) as batch_op:
        batch_op.create_index("ix_evidence_case", ["case_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("evidence", schema=None) as batch_op:
        batch_op.drop_index("ix_evidence_case")

    op.drop_table("evidence")
    with op.batch_alter_table("age_set_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_age_set_members_age_set_id"))

    op.drop_table("age_set_members")
    op.drop_table("welfare_houses")
    op.drop_table("time_budgets")
    op.drop_table("taverns")
    with op.batch_alter_table("revivals", schema=None) as batch_op:
        batch_op.drop_index("ix_revivals_people")

    op.drop_table("revivals")
    op.drop_table("poor_relief")
    op.drop_table("naming_customs")
    with op.batch_alter_table("memberships", schema=None) as batch_op:
        batch_op.drop_index("ix_memberships_polity")

    op.drop_table("memberships")
    op.drop_table("membership_categories")
    op.drop_table("measure_standards")
    op.drop_table("mark_customs")
    op.drop_table("intoxicant_customs")
    op.drop_table("cooperatives")
    op.drop_table("commutes")
    op.drop_table("border_controls")
    with op.batch_alter_table("age_sets", schema=None) as batch_op:
        batch_op.drop_index("ix_age_sets_people")

    op.drop_table("age_sets")
    op.drop_table("name_forms")
    with op.batch_alter_table("body_marks", schema=None) as batch_op:
        batch_op.drop_index("ix_body_marks_holder")

    op.drop_table("body_marks")
