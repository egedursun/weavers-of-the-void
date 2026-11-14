import sqlalchemy as sa
from alembic import op

revision = "0a3a6bd53c20"
down_revision = "a75b504d83b5"
branch_labels = None
depends_on = None

OFFICES_BEFORE = (
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
    "chaplain",
    "court_scholar",
    "head_of_state",
    "head_of_government",
    "minister",
    "general",
    "admiral",
    "speaker",
    "chief_scientist",
)
OFFICES_AFTER = (*OFFICES_BEFORE, "jester")
WIDENED = (("offices", "kind", "kind", False), ("claims", "office", "office", False))


def widen(forward: bool) -> None:
    before, after = (OFFICES_BEFORE, OFFICES_AFTER) if forward else (OFFICES_AFTER, OFFICES_BEFORE)
    for table, column, name, nullable in WIDENED:
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
        "held_identities",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "layer",
            sa.Enum(
                "people",
                "faith",
                "class",
                "locality",
                "house",
                "profession",
                "generation",
                "polity",
                "circle",
                name="layer",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("value_node_id", sa.Integer(), nullable=True),
        sa.Column("value_label", sa.String(length=200), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("salience", sa.Integer(), nullable=False),
        sa.Column(
            "driver",
            sa.Enum(
                "baseline",
                "holy_war",
                "famine",
                "invasion",
                "strike",
                "rhetoric",
                "segregation",
                "crossing",
                "god",
                name="driver",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("salience BETWEEN 0 AND 100", name=op.f("ck_held_identities_salience_range")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_held_identities_strength_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_held_identities_updated_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_held_identities_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["value_node_id"], ["nodes.id"], name=op.f("fk_held_identities_value_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("holder_entity_id", "layer", name=op.f("pk_held_identities")),
    )
    with op.batch_alter_table("held_identities", schema=None) as batch_op:
        batch_op.create_index("ix_held_identities_value", ["value_node_id"], unique=False)

    op.create_table(
        "peer_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
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
        sa.Column(
            "play",
            sa.Enum("games", "mock_fights", "imitation", "riding", "archery", "songs", name="play", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("children", sa.Integer(), nullable=False),
        sa.Column("cohesion", sa.Integer(), nullable=False),
        sa.Column("deprived", sa.Boolean(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("dissolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("children >= 0", name=op.f("ck_peer_groups_children_min")),
        sa.CheckConstraint("cohesion BETWEEN 0 AND 100", name=op.f("ck_peer_groups_cohesion_range")),
        sa.CheckConstraint("formed_epoch >= 0", name=op.f("ck_peer_groups_formed_epoch_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_peer_groups_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peer_groups")),
    )
    with op.batch_alter_table("peer_groups", schema=None) as batch_op:
        batch_op.create_index("ix_peer_groups_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "sanctuaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fugitive_entity_id", sa.Integer(), nullable=False),
        sa.Column("host_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("temple", "hospitality", "asylum", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "fugitive_kind",
            sa.Enum("outlaw", "accused", "defector", name="fugitive_kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("pursuer_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "state",
            sa.Enum("sheltered", "negotiating", "besieged", "violated", "ended", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("granted_epoch", sa.Integer(), nullable=False),
        sa.Column("siege_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fee >= 0", name=op.f("ck_sanctuaries_fee_min")),
        sa.CheckConstraint("granted_epoch >= 0", name=op.f("ck_sanctuaries_granted_epoch_min")),
        sa.CheckConstraint("siege_epochs >= 0", name=op.f("ck_sanctuaries_siege_epochs_min")),
        sa.ForeignKeyConstraint(["fugitive_entity_id"], ["entities.id"], name=op.f("fk_sanctuaries_fugitive_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_entity_id"], ["entities.id"], name=op.f("fk_sanctuaries_host_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pursuer_entity_id"], ["entities.id"], name=op.f("fk_sanctuaries_pursuer_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sanctuaries")),
    )
    with op.batch_alter_table("sanctuaries", schema=None) as batch_op:
        batch_op.create_index("ix_sanctuaries_fugitive", ["fugitive_entity_id"], unique=False)
        batch_op.create_index("ix_sanctuaries_host", ["host_entity_id"], unique=False)

    op.create_table(
        "sanctuary_laws",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("restricted", sa.Boolean(), nullable=False),
        sa.Column("fee_pct", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fee_pct BETWEEN 0 AND 100", name=op.f("ck_sanctuary_laws_fee_pct_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_sanctuary_laws_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_sanctuary_laws")),
    )
    op.create_table(
        "satires",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("satirist_entity_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("work_entity_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.Enum("jester", "artwork", "mortal", "god", name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("bite", sa.Integer(), nullable=False),
        sa.Column("tolerated", sa.Boolean(), nullable=False),
        sa.Column("punished", sa.Boolean(), nullable=False),
        sa.Column("judged", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bite BETWEEN 0 AND 100", name=op.f("ck_satires_bite_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_satires_epoch_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_satires_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["satirist_entity_id"], ["entities.id"], name=op.f("fk_satires_satirist_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_satires_target_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_entity_id"], ["entities.id"], name=op.f("fk_satires_work_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satires")),
    )
    with op.batch_alter_table("satires", schema=None) as batch_op:
        batch_op.create_index("ix_satires_polity", ["polity_entity_id"], unique=False)
        batch_op.create_index("ix_satires_target", ["target_entity_id"], unique=False)

    op.create_table(
        "peer_members",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("deprived_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("deprived_epochs >= 0", name=op.f("ck_peer_members_deprived_epochs_min")),
        sa.CheckConstraint("joined_epoch >= 0", name=op.f("ck_peer_members_joined_epoch_min")),
        sa.ForeignKeyConstraint(["group_id"], ["peer_groups.id"], name=op.f("fk_peer_members_group_id_peer_groups"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_peer_members_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "mortal_entity_id", name=op.f("pk_peer_members")),
    )
    with op.batch_alter_table("peer_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_peer_members_mortal_entity_id"), ["mortal_entity_id"], unique=False)


def downgrade() -> None:
    op.execute("DELETE FROM offices WHERE kind = 'jester'")
    op.execute("DELETE FROM claims WHERE office = 'jester'")
    widen(False)
    with op.batch_alter_table("peer_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_peer_members_mortal_entity_id"))

    op.drop_table("peer_members")
    with op.batch_alter_table("satires", schema=None) as batch_op:
        batch_op.drop_index("ix_satires_target")
        batch_op.drop_index("ix_satires_polity")

    op.drop_table("satires")
    op.drop_table("sanctuary_laws")
    with op.batch_alter_table("sanctuaries", schema=None) as batch_op:
        batch_op.drop_index("ix_sanctuaries_host")
        batch_op.drop_index("ix_sanctuaries_fugitive")

    op.drop_table("sanctuaries")
    with op.batch_alter_table("peer_groups", schema=None) as batch_op:
        batch_op.drop_index("ix_peer_groups_settlement")

    op.drop_table("peer_groups")
    with op.batch_alter_table("held_identities", schema=None) as batch_op:
        batch_op.drop_index("ix_held_identities_value")

    op.drop_table("held_identities")
