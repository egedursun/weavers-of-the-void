import sqlalchemy as sa
from alembic import op

revision = "c3f1a7d9e5b2"
down_revision = "9b4e2f6a1c83"
branch_labels = None
depends_on = None

TREATIES = (
    "peace",
    "truce",
    "alliance_defensive",
    "alliance_offensive",
    "non_aggression",
    "vassalage",
    "tribute",
    "marriage_pact",
    "trade_pact",
    "condotta",
    "guarantee",
    "interworld",
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    before, after = (TREATIES, (*TREATIES, "coalition")) if forward else ((*TREATIES, "coalition"), TREATIES)
    with op.batch_alter_table("treaty_profiles", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of("kind", before), type_=enum_of("kind", after), existing_nullable=False)


def upgrade() -> None:
    widen(True)
    op.create_table(
        "crises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("demander_entity_id", sa.Integer(), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "demand",
            sa.Enum("cede_region", "release_vassal", "convert", "pay", name="demand", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("escalation", sa.Integer(), nullable=False),
        sa.Column(
            "state", sa.Enum("escalating", "backed_down", "conceded", "war", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_crises_amount_min")),
        sa.CheckConstraint("escalation >= 0", name=op.f("ck_crises_escalation_min")),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_crises_opened_epoch_min")),
        sa.ForeignKeyConstraint(["demander_entity_id"], ["entities.id"], name=op.f("fk_crises_demander_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_crises_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_crises_target_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crises")),
    )
    with op.batch_alter_table("crises", schema=None) as batch_op:
        batch_op.create_index("ix_crises_demander", ["demander_entity_id", "state"], unique=False)
        batch_op.create_index(batch_op.f("ix_crises_target_entity_id"), ["target_entity_id"], unique=False)

    op.create_table(
        "diplomacy_profiles",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("relations", sa.Integer(), nullable=False),
        sa.Column("strain", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity >= 0", name=op.f("ck_diplomacy_profiles_capacity_min")),
        sa.CheckConstraint("relations >= 0", name=op.f("ck_diplomacy_profiles_relations_min")),
        sa.CheckConstraint("strain >= 0", name=op.f("ck_diplomacy_profiles_strain_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_diplomacy_profiles_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_diplomacy_profiles")),
    )
    op.create_table(
        "polity_regard",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("subject_entity_id", sa.Integer(), nullable=False),
        sa.Column("threat", sa.Integer(), nullable=False),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("threat BETWEEN 0 AND 100", name=op.f("ck_polity_regard_threat_range")),
        sa.CheckConstraint("trust BETWEEN 0 AND 100", name=op.f("ck_polity_regard_trust_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_polity_regard_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"], name=op.f("fk_polity_regard_subject_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "subject_entity_id", name=op.f("pk_polity_regard")),
    )
    with op.batch_alter_table("polity_regard", schema=None) as batch_op:
        batch_op.create_index("ix_polity_regard_subject", ["subject_entity_id"], unique=False)

    op.create_table(
        "spheres",
        sa.Column("power_entity_id", sa.Integer(), nullable=False),
        sa.Column("client_entity_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_spheres_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_spheres_strength_range")),
        sa.ForeignKeyConstraint(["client_entity_id"], ["entities.id"], name=op.f("fk_spheres_client_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["power_entity_id"], ["entities.id"], name=op.f("fk_spheres_power_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("power_entity_id", "client_entity_id", name=op.f("pk_spheres")),
    )
    with op.batch_alter_table("spheres", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_spheres_client_entity_id"), ["client_entity_id"], unique=False)

    op.create_table(
        "crisis_backers",
        sa.Column("crisis_id", sa.Integer(), nullable=False),
        sa.Column("backer_entity_id", sa.Integer(), nullable=False),
        sa.Column("side", sa.Enum("demander", "target", name="side", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("promised", sa.Integer(), nullable=False),
        sa.Column("swing", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("promised BETWEEN 0 AND 100", name=op.f("ck_crisis_backers_promised_range")),
        sa.ForeignKeyConstraint(["backer_entity_id"], ["entities.id"], name=op.f("fk_crisis_backers_backer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crisis_id"], ["crises.id"], name=op.f("fk_crisis_backers_crisis_id_crises"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("crisis_id", "backer_entity_id", name=op.f("pk_crisis_backers")),
    )
    with op.batch_alter_table("crisis_backers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_crisis_backers_backer_entity_id"), ["backer_entity_id"], unique=False)

    with op.batch_alter_table("vassalages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "kind",
                sa.Enum(
                    "vassal",
                    "tributary",
                    "march",
                    "personal_union",
                    "client",
                    "colony",
                    "protectorate",
                    name="kind",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="vassal",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("liberty", sa.Integer(), server_default="20", nullable=False))
        batch_op.add_column(sa.Column("private_war", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("coinage", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("confirm_succession", sa.Boolean(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("confirmed_ruler_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_vassalages_confirmed_ruler_entity_id_entities"), "entities", ["confirmed_ruler_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_check_constraint(batch_op.f("ck_vassalages_liberty_range"), "liberty BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("vassalages", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_vassalages_confirmed_ruler_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("ck_vassalages_liberty_range"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_vassalages_kind"), type_="check")
        batch_op.drop_column("confirmed_ruler_entity_id")
        batch_op.drop_column("confirm_succession")
        batch_op.drop_column("coinage")
        batch_op.drop_column("private_war")
        batch_op.drop_column("liberty")
        batch_op.drop_column("kind")

    with op.batch_alter_table("crisis_backers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_crisis_backers_backer_entity_id"))

    op.drop_table("crisis_backers")
    with op.batch_alter_table("spheres", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_spheres_client_entity_id"))

    op.drop_table("spheres")
    with op.batch_alter_table("polity_regard", schema=None) as batch_op:
        batch_op.drop_index("ix_polity_regard_subject")

    op.drop_table("polity_regard")
    op.drop_table("diplomacy_profiles")
    with op.batch_alter_table("crises", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_crises_target_entity_id"))
        batch_op.drop_index("ix_crises_demander")

    op.drop_table("crises")
    widen(False)
