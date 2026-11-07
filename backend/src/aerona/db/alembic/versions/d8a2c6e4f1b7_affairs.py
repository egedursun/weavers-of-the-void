import sqlalchemy as sa
from alembic import op

revision = "d8a2c6e4f1b7"
down_revision = "c3f1a7d9e5b2"
branch_labels = None
depends_on = None

OFFICES = (
    "ruler",
    "heir_designate",
    "regent",
    "chancellor",
    "marshal",
    "treasurer",
    "high_judge",
    "spymaster",
    "governor",
    "ambassador",
    "herald",
)
LAWS = (
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
)
AREAS = ("succession", "property", "fiscal", "penal", "military", "social", "public_health", "magic")
WIDENED = (
    ("offices", "kind", OFFICES, (*OFFICES, "chaplain"), False),
    ("claims", "office", OFFICES, (*OFFICES, "chaplain"), False),
    ("law_profiles", "kind", LAWS, (*LAWS, "franchise", "constitution"), False),
    ("law_proposals", "kind", LAWS, (*LAWS, "franchise", "constitution"), False),
    ("law_profiles", "area", AREAS, (*AREAS, "constitutional"), False),
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
        "council_seats",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("votes", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("seats >= 0", name=op.f("ck_council_seats_seats_min")),
        sa.CheckConstraint("votes BETWEEN 0 AND 100", name=op.f("ck_council_seats_votes_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_council_seats_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_council_seats_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "holder_node_id", name=op.f("pk_council_seats")),
    )
    with op.batch_alter_table("council_seats", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_council_seats_holder_node_id"), ["holder_node_id"], unique=False)

    op.create_table(
        "elections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("turnout", sa.Integer(), nullable=False),
        sa.Column("winner_node_id", sa.Integer(), nullable=True),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.CheckConstraint("seats >= 0", name=op.f("ck_elections_seats_min")),
        sa.CheckConstraint("turnout BETWEEN 0 AND 100", name=op.f("ck_elections_turnout_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_elections_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_node_id"], ["nodes.id"], name=op.f("fk_elections_winner_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_elections")),
    )
    with op.batch_alter_table("elections", schema=None) as batch_op:
        batch_op.create_index("ix_elections_polity", ["polity_entity_id", "epoch"], unique=False)

    op.create_table(
        "mandates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("issuer_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("produce", "export_ban", "build", "famine_relief", "curfew", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=True),
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "district",
            sa.Enum(
                "farmland",
                "market",
                "craft_quarter",
                "temple_quarter",
                "harbour",
                "citadel",
                "slums",
                "palace",
                "foreign_quarter",
                "necropolis",
                name="district",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("issued_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum("active", "met", "failed", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_mandates_amount_min")),
        sa.CheckConstraint("issued_epoch >= 0", name=op.f("ck_mandates_issued_epoch_min")),
        sa.ForeignKeyConstraint(["issuer_node_id"], ["nodes.id"], name=op.f("fk_mandates_issuer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_mandates_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_mandates_settlement_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mandates")),
    )
    with op.batch_alter_table("mandates", schema=None) as batch_op:
        batch_op.create_index("ix_mandates_polity", ["polity_entity_id", "state"], unique=False)
        batch_op.create_index(batch_op.f("ix_mandates_settlement_entity_id"), ["settlement_entity_id"], unique=False)

    op.create_table(
        "noble_demands",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "want", sa.Enum("dwelling", "fine_goods", "office", "honour", name="want", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("met", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_noble_demands_since_epoch_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_noble_demands_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", "want", name=op.f("pk_noble_demands")),
    )
    op.create_table(
        "policy_approval",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
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
        sa.Column("approval", sa.Integer(), nullable=False),
        sa.Column("parts", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("approval BETWEEN -100 AND 100", name=op.f("ck_policy_approval_approval_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_policy_approval_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "social_class", name=op.f("pk_policy_approval")),
    )
    op.create_table(
        "tax_policies",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("land", "poll", "trade", "consumption", "tithe", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column("farmed", sa.Boolean(), nullable=False),
        sa.Column("efficiency", sa.Integer(), nullable=False),
        sa.Column("take", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("efficiency BETWEEN 0 AND 100", name=op.f("ck_tax_policies_efficiency_range")),
        sa.CheckConstraint("rate BETWEEN 0 AND 50", name=op.f("ck_tax_policies_rate_range")),
        sa.CheckConstraint("take >= 0", name=op.f("ck_tax_policies_take_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_tax_policies_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "kind", name=op.f("pk_tax_policies")),
    )
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "task",
                sa.Enum(
                    "improve_relations",
                    "train_troops",
                    "collect_taxes",
                    "disrupt_schemes",
                    "convert_province",
                    "purge_corruption",
                    name="task",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("task_target_node_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("diligence", sa.Integer(), server_default="50", nullable=False))
        batch_op.create_foreign_key(batch_op.f("fk_offices_task_target_node_id_nodes"), "nodes", ["task_target_node_id"], ["id"], ondelete="SET NULL")
        batch_op.create_check_constraint(batch_op.f("ck_offices_diligence_range"), "diligence BETWEEN 0 AND 100")

    with op.batch_alter_table("polity_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("corruption", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(batch_op.f("ck_polity_profiles_corruption_range"), "corruption BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("polity_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_polity_profiles_corruption_range"), type_="check")
        batch_op.drop_column("corruption")

    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_offices_task_target_node_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("ck_offices_diligence_range"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_offices_task"), type_="check")
        batch_op.drop_column("diligence")
        batch_op.drop_column("task_target_node_id")
        batch_op.drop_column("task")

    op.drop_table("tax_policies")
    op.drop_table("policy_approval")
    op.drop_table("noble_demands")
    with op.batch_alter_table("mandates", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_mandates_settlement_entity_id"))
        batch_op.drop_index("ix_mandates_polity")

    op.drop_table("mandates")
    with op.batch_alter_table("elections", schema=None) as batch_op:
        batch_op.drop_index("ix_elections_polity")

    op.drop_table("elections")
    with op.batch_alter_table("council_seats", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_council_seats_holder_node_id"))

    op.drop_table("council_seats")
    widen(False)
