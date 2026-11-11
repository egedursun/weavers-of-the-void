import sqlalchemy as sa
from alembic import op

revision = "ab9de8333d80"
down_revision = "fe8a761cd391"
branch_labels = None
depends_on = None


OLD_ROLES = ("messenger", "guard", "judge", "host")
WIDENED = (("servitors", "role", "role", OLD_ROLES, (*OLD_ROLES, "spy"), False),)


def widen(forward: bool) -> None:
    for table, column, name, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*before, name=name, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*after, name=name, native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    widen(True)
    op.create_table(
        "assassinations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("victim_entity_id", sa.Integer(), nullable=True),
        sa.Column("killer_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "method",
            sa.Enum("blade", "poison", "accident", "disease", "curse", name="method", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("recognised", sa.Boolean(), nullable=False),
        sa.Column("examiner_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_assassinations_epoch_min")),
        sa.ForeignKeyConstraint(["examiner_entity_id"], ["entities.id"], name=op.f("fk_assassinations_examiner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["killer_entity_id"], ["entities.id"], name=op.f("fk_assassinations_killer_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["victim_entity_id"], ["entities.id"], name=op.f("fk_assassinations_victim_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assassinations")),
    )
    with op.batch_alter_table("assassinations", schema=None) as batch_op:
        batch_op.create_index("ix_assassinations_victim", ["victim_entity_id"], unique=False)

    op.create_table(
        "defections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defector_entity_id", sa.Integer(), nullable=False),
        sa.Column("from_entity_id", sa.Integer(), nullable=True),
        sa.Column("to_entity_id", sa.Integer(), nullable=True),
        sa.Column("secrets", sa.Integer(), nullable=False),
        sa.Column("protected", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_defections_epoch_min")),
        sa.CheckConstraint("secrets >= 0", name=op.f("ck_defections_secrets_min")),
        sa.ForeignKeyConstraint(["defector_entity_id"], ["entities.id"], name=op.f("fk_defections_defector_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_entity_id"], ["entities.id"], name=op.f("fk_defections_from_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_entity_id"], ["entities.id"], name=op.f("fk_defections_to_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_defections")),
    )
    with op.batch_alter_table("defections", schema=None) as batch_op:
        batch_op.create_index("ix_defections_defector", ["defector_entity_id"], unique=False)

    op.create_table(
        "jurisdictions",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("claimant_entity_id", sa.Integer(), nullable=False),
        sa.Column("claim", sa.Enum("clergy", "guild", "foreign", name="claim", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_jurisdictions_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_jurisdictions_strength_range")),
        sa.ForeignKeyConstraint(["claimant_entity_id"], ["entities.id"], name=op.f("fk_jurisdictions_claimant_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_jurisdictions_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "claimant_entity_id", "claim", name=op.f("pk_jurisdictions")),
    )
    op.create_table(
        "legal_systems",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "system",
            sa.Enum("customary", "codified", "religious", "precedent", "oracle", "mixed", name="system", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_legal_systems_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_legal_systems_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_legal_systems")),
    )
    op.create_table(
        "mole_hunts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("spymaster_entity_id", sa.Integer(), nullable=True),
        sa.Column("suspect_entity_id", sa.Integer(), nullable=True),
        sa.Column("mole", sa.Boolean(), nullable=False),
        sa.Column(
            "outcome", sa.Enum("caught", "cleared", "purged", "defected", name="outcome", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_mole_hunts_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_mole_hunts_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spymaster_entity_id"], ["entities.id"], name=op.f("fk_mole_hunts_spymaster_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suspect_entity_id"], ["entities.id"], name=op.f("fk_mole_hunts_suspect_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mole_hunts")),
    )
    with op.batch_alter_table("mole_hunts", schema=None) as batch_op:
        batch_op.create_index("ix_mole_hunts_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "outlaws",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("bounty", sa.Integer(), nullable=False),
        sa.Column("renown", sa.Integer(), nullable=False),
        sa.Column("declared_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bounty >= 0", name=op.f("ck_outlaws_bounty_min")),
        sa.CheckConstraint("declared_epoch >= 0", name=op.f("ck_outlaws_declared_epoch_min")),
        sa.CheckConstraint("renown BETWEEN 0 AND 100", name=op.f("ck_outlaws_renown_range")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_outlaws_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_outlaws_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_outlaws")),
    )
    op.create_table(
        "prisons",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("food", sa.Integer(), nullable=False),
        sa.Column("crowding", sa.Integer(), nullable=False),
        sa.Column("cruelty", sa.Integer(), nullable=False),
        sa.Column("gang_strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("crowding BETWEEN 0 AND 100", name=op.f("ck_prisons_crowding_range")),
        sa.CheckConstraint("cruelty BETWEEN 0 AND 100", name=op.f("ck_prisons_cruelty_range")),
        sa.CheckConstraint("food BETWEEN 0 AND 100", name=op.f("ck_prisons_food_range")),
        sa.CheckConstraint("gang_strength BETWEEN 0 AND 100", name=op.f("ck_prisons_gang_strength_range")),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_prisons_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_prisons")),
    )
    op.create_table(
        "registries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("land_title", "debt", "sale", "dowry", "indenture", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("owner_entity_id", sa.Integer(), nullable=True),
        sa.Column("counterparty_entity_id", sa.Integer(), nullable=True),
        sa.Column("subject_entity_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("registered_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_registries_amount_min")),
        sa.CheckConstraint("registered_epoch >= 0", name=op.f("ck_registries_registered_epoch_min")),
        sa.ForeignKeyConstraint(["counterparty_entity_id"], ["entities.id"], name=op.f("fk_registries_counterparty_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_registries_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_registries_owner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"], name=op.f("fk_registries_subject_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registries")),
    )
    with op.batch_alter_table("registries", schema=None) as batch_op:
        batch_op.create_index("ix_registries_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "appeals",
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column(
            "from_court",
            sa.Enum("local", "provincial", "high", "religious", name="from_court", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "to_court",
            sa.Enum("local", "provincial", "high", "religious", name="to_court", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("filed_epoch", sa.Integer(), nullable=False),
        sa.Column("decided_epoch", sa.Integer(), nullable=True),
        sa.Column("reversed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fee >= 0", name=op.f("ck_appeals_fee_min")),
        sa.CheckConstraint("filed_epoch >= 0", name=op.f("ck_appeals_filed_epoch_min")),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_appeals_case_id_crime_cases"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("case_id", name=op.f("pk_appeals")),
    )
    op.create_table(
        "pardons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("granter_entity_id", sa.Integer(), nullable=True),
        sa.Column("pardoned_entity_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("amnesty", sa.Boolean(), nullable=False),
        sa.Column("corrupt", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_pardons_epoch_min")),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_pardons_case_id_crime_cases"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["granter_entity_id"], ["entities.id"], name=op.f("fk_pardons_granter_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pardoned_entity_id"], ["entities.id"], name=op.f("fk_pardons_pardoned_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pardons")),
    )
    with op.batch_alter_table("pardons", schema=None) as batch_op:
        batch_op.create_index("ix_pardons_granter", ["granter_entity_id"], unique=False)

    op.create_table(
        "precedents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "crime",
            sa.Enum("theft", "blasphemy", "treason", "murder", "desertion", name="crime", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "verdict", sa.Enum("guilty", "acquitted", "fled", "dropped", name="verdict", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "court", sa.Enum("local", "provincial", "high", "religious", name="court", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("authority", sa.Integer(), nullable=False),
        sa.Column("overturned", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("authority BETWEEN 0 AND 100", name=op.f("ck_precedents_authority_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_precedents_epoch_min")),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_precedents_case_id_crime_cases"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_precedents_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_precedents")),
    )
    with op.batch_alter_table("precedents", schema=None) as batch_op:
        batch_op.create_index("ix_precedents_holder", ["holder_entity_id", "crime"], unique=False)

    op.create_table(
        "prisoners",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("prison_entity_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("gang_rank", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("gang_rank BETWEEN 0 AND 100", name=op.f("ck_prisoners_gang_rank_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_prisoners_since_epoch_min")),
        sa.CheckConstraint("term >= 0", name=op.f("ck_prisoners_term_min")),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_prisoners_case_id_crime_cases"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_prisoners_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prison_entity_id"], ["entities.id"], name=op.f("fk_prisoners_prison_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_prisoners")),
    )
    with op.batch_alter_table("prisoners", schema=None) as batch_op:
        batch_op.create_index("ix_prisoners_prison", ["prison_entity_id"], unique=False)

    op.create_table(
        "spy_cells",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("network_id", sa.Integer(), nullable=False),
        sa.Column("handler_entity_id", sa.Integer(), nullable=True),
        sa.Column("safe_house_entity_id", sa.Integer(), nullable=True),
        sa.Column("dead_drops", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dead_drops >= 0", name=op.f("ck_spy_cells_dead_drops_min")),
        sa.ForeignKeyConstraint(["handler_entity_id"], ["entities.id"], name=op.f("fk_spy_cells_handler_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["network_id"], ["spy_networks.id"], name=op.f("fk_spy_cells_network_id_spy_networks"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["safe_house_entity_id"], ["entities.id"], name=op.f("fk_spy_cells_safe_house_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_spy_cells")),
    )
    with op.batch_alter_table("spy_cells", schema=None) as batch_op:
        batch_op.create_index("ix_spy_cells_network", ["network_id"], unique=False)

    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("advocate_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "court",
                sa.Enum("local", "provincial", "high", "religious", name="court", native_enum=False, create_constraint=True, length=40),
                server_default="local",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "oracle_answer",
                sa.Enum("guilty", "acquitted", "fled", "dropped", name="oracle_answer", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(batch_op.f("fk_crime_cases_advocate_entity_id_entities"), "entities", ["advocate_entity_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("spy_agents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "motive",
                sa.Enum("money", "ideology", "compromise", "ego", name="motive", native_enum=False, create_constraint=True, length=40),
                server_default="money",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("loyalty", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("cell_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_spy_agents_cell_id_spy_cells"), "spy_cells", ["cell_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("spy_agents", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_spy_agents_cell_id_spy_cells"), type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_spy_agents_motive"), type_="check")
        batch_op.drop_column("cell_id")
        batch_op.drop_column("loyalty")
        batch_op.drop_column("motive")

    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_crime_cases_advocate_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_crime_cases_court"), type_="check")
        batch_op.drop_constraint(op.f("ck_crime_cases_oracle_answer"), type_="check")
        batch_op.drop_column("oracle_answer")
        batch_op.drop_column("court")
        batch_op.drop_column("advocate_entity_id")

    with op.batch_alter_table("spy_cells", schema=None) as batch_op:
        batch_op.drop_index("ix_spy_cells_network")

    op.drop_table("spy_cells")
    with op.batch_alter_table("prisoners", schema=None) as batch_op:
        batch_op.drop_index("ix_prisoners_prison")

    op.drop_table("prisoners")
    with op.batch_alter_table("precedents", schema=None) as batch_op:
        batch_op.drop_index("ix_precedents_holder")

    op.drop_table("precedents")
    with op.batch_alter_table("pardons", schema=None) as batch_op:
        batch_op.drop_index("ix_pardons_granter")

    op.drop_table("pardons")
    op.drop_table("appeals")
    with op.batch_alter_table("registries", schema=None) as batch_op:
        batch_op.drop_index("ix_registries_holder")

    op.drop_table("registries")
    op.drop_table("prisons")
    op.drop_table("outlaws")
    with op.batch_alter_table("mole_hunts", schema=None) as batch_op:
        batch_op.drop_index("ix_mole_hunts_polity")

    op.drop_table("mole_hunts")
    op.drop_table("legal_systems")
    op.drop_table("jurisdictions")
    with op.batch_alter_table("defections", schema=None) as batch_op:
        batch_op.drop_index("ix_defections_defector")

    op.drop_table("defections")
    with op.batch_alter_table("assassinations", schema=None) as batch_op:
        batch_op.drop_index("ix_assassinations_victim")

    op.drop_table("assassinations")
    widen(False)
