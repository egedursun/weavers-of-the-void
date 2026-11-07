import sqlalchemy as sa
from alembic import op

revision = "9b4e2f6a1c83"
down_revision = "7a3d1c9e2b40"
branch_labels = None
depends_on = None

ORIGINS = ("gift", "rescue", "war_support", "succession_support", "scheme_aid")
DEMANDS = ("marriage", "step_down", "support")
WIDENED = (
    ("favours", "origin", ORIGINS, (*ORIGINS, "vote"), False),
    ("hooks", "last_demand", DEMANDS, (*DEMANDS, "vote", "law"), True),
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    op.create_table(
        "crime_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "crime",
            sa.Enum("theft", "blasphemy", "treason", "murder", "desertion", name="crime", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("culprit_entity_id", sa.Integer(), nullable=True),
        sa.Column("accused_entity_id", sa.Integer(), nullable=True),
        sa.Column("investigator_entity_id", sa.Integer(), nullable=True),
        sa.Column("judge_entity_id", sa.Integer(), nullable=True),
        sa.Column("stage", sa.Enum("investigation", "trial", "closed", name="stage", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("trial", sa.Enum("judge", "jury", "combat", "ordeal", name="trial", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column("evidence", sa.Integer(), nullable=False),
        sa.Column("tortured", sa.Boolean(), nullable=False),
        sa.Column("forged", sa.Boolean(), nullable=False),
        sa.Column(
            "verdict", sa.Enum("guilty", "acquitted", "fled", "dropped", name="verdict", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("wrongful", sa.Boolean(), nullable=False),
        sa.Column("penalty", sa.String(length=120), nullable=True),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("evidence BETWEEN 0 AND 100", name=op.f("ck_crime_cases_evidence_range")),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_crime_cases_opened_epoch_min")),
        sa.ForeignKeyConstraint(["accused_entity_id"], ["entities.id"], name=op.f("fk_crime_cases_accused_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["culprit_entity_id"], ["entities.id"], name=op.f("fk_crime_cases_culprit_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["investigator_entity_id"], ["entities.id"], name=op.f("fk_crime_cases_investigator_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["judge_entity_id"], ["entities.id"], name=op.f("fk_crime_cases_judge_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_crime_cases_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_crime_cases_settlement_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crime_cases")),
    )
    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.create_index("ix_crime_cases_accused", ["accused_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_crime_cases_culprit_entity_id"), ["culprit_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_crime_cases_investigator_entity_id"), ["investigator_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_crime_cases_judge_entity_id"), ["judge_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_crime_cases_polity_entity_id"), ["polity_entity_id"], unique=False)
        batch_op.create_index("ix_crime_cases_settlement", ["settlement_entity_id", "stage"], unique=False)

    op.create_table(
        "law_proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                "magic_ban",
                "licensed_magic",
                "rite_restrictions",
                "custom",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("champion_node_id", sa.Integer(), nullable=True),
        sa.Column("law_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "basis", sa.Enum("custom", "decree", "divine", "council", name="basis", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("support", sa.Integer(), nullable=False),
        sa.Column("opposition", sa.Integer(), nullable=False),
        sa.Column("stalled_epochs", sa.Integer(), nullable=False),
        sa.Column(
            "state", sa.Enum("debating", "passed", "failed", "withdrawn", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "last_event",
            sa.Enum("debate", "riot", "compromise", "obstruction", name="last_event", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("amended", sa.Boolean(), nullable=False),
        sa.Column("proposed_epoch", sa.Integer(), nullable=False),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("opposition BETWEEN 0 AND 100", name=op.f("ck_law_proposals_opposition_range")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_law_proposals_progress_range")),
        sa.CheckConstraint("proposed_epoch >= 0", name=op.f("ck_law_proposals_proposed_epoch_min")),
        sa.CheckConstraint("stalled_epochs >= 0", name=op.f("ck_law_proposals_stalled_epochs_min")),
        sa.CheckConstraint("support BETWEEN 0 AND 100", name=op.f("ck_law_proposals_support_range")),
        sa.ForeignKeyConstraint(["champion_node_id"], ["nodes.id"], name=op.f("fk_law_proposals_champion_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_law_proposals_law_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_law_proposals_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_law_proposals")),
    )
    with op.batch_alter_table("law_proposals", schema=None) as batch_op:
        batch_op.create_index("ix_law_proposals_champion", ["champion_node_id"], unique=False)
        batch_op.create_index("ix_law_proposals_polity", ["polity_entity_id", "state"], unique=False)

    op.create_table(
        "case_witnesses",
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("witness_entity_id", sa.Integer(), nullable=False),
        sa.Column("testimony", sa.Enum("accuses", "shields", "silent", name="testimony", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("reliability", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("reliability BETWEEN 0 AND 100", name=op.f("ck_case_witnesses_reliability_range")),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_case_witnesses_case_id_crime_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["witness_entity_id"], ["entities.id"], name=op.f("fk_case_witnesses_witness_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("case_id", "witness_entity_id", name=op.f("pk_case_witnesses")),
    )
    with op.batch_alter_table("case_witnesses", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_case_witnesses_witness_entity_id"), ["witness_entity_id"], unique=False)

    op.create_table(
        "proposal_stances",
        sa.Column("proposal_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("stance", sa.Enum("support", "oppose", "obstruct", name="stance", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("hooked", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_proposal_stances_weight_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_proposal_stances_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["law_proposals.id"], name=op.f("fk_proposal_stances_proposal_id_law_proposals"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("proposal_id", "node_id", name=op.f("pk_proposal_stances")),
    )
    with op.batch_alter_table("proposal_stances", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_proposal_stances_node_id"), ["node_id"], unique=False)

    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.add_column(sa.Column("case_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_sentences_case_id"), ["case_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_sentences_case_id_crime_cases"), "crime_cases", ["case_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_sentences_case_id_crime_cases"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_sentences_case_id"))
        batch_op.drop_column("case_id")

    with op.batch_alter_table("proposal_stances", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_proposal_stances_node_id"))

    op.drop_table("proposal_stances")
    with op.batch_alter_table("case_witnesses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_case_witnesses_witness_entity_id"))

    op.drop_table("case_witnesses")
    with op.batch_alter_table("law_proposals", schema=None) as batch_op:
        batch_op.drop_index("ix_law_proposals_polity")
        batch_op.drop_index("ix_law_proposals_champion")

    op.drop_table("law_proposals")
    with op.batch_alter_table("crime_cases", schema=None) as batch_op:
        batch_op.drop_index("ix_crime_cases_settlement")
        batch_op.drop_index(batch_op.f("ix_crime_cases_polity_entity_id"))
        batch_op.drop_index(batch_op.f("ix_crime_cases_judge_entity_id"))
        batch_op.drop_index(batch_op.f("ix_crime_cases_investigator_entity_id"))
        batch_op.drop_index(batch_op.f("ix_crime_cases_culprit_entity_id"))
        batch_op.drop_index("ix_crime_cases_accused")

    op.drop_table("crime_cases")
    widen(False)
