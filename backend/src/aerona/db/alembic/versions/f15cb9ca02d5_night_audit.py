import sqlalchemy as sa
from alembic import op

revision = "f15cb9ca02d5"
down_revision = "ab9de8333d80"
branch_labels = None
depends_on = None


ADDED = ("fountain", "park", "slaughterhouse")
EARLIER = (
    "temple",
    "shrine",
    "monastery",
    "necropolis",
    "library",
    "school",
    "observatory",
    "academy",
    "hospital",
    "wall",
    "gate",
    "tower",
    "citadel",
    "watchtower",
    "fort",
    "palace",
    "court",
    "prison",
    "market",
    "harbour",
    "warehouse",
    "granary",
    "caravanserai",
    "bank",
    "forge",
    "mill",
    "tannery",
    "mine",
    "quarry",
    "shipyard",
    "workshop",
    "alchemist_lab",
    "road",
    "bridge",
    "aqueduct",
    "sewer",
    "canal",
    "irrigation",
    "dam",
    "monument",
    "tomb",
    "arena",
    "theatre",
    "wonder",
    "cosmic_gate",
    "firehouse",
    "bathhouse",
    "kontor",
    "covenant",
    "cosmic_archive",
)
EVERY = (*EARLIER, *ADDED)
WIDENED = (
    ("structure_profiles", "kind", "structure_kind"),
    ("constructions", "kind", "structure_kind"),
    ("structure_designs", "base_kind", "base_kind"),
)


def widen(forward: bool) -> None:
    before, after = (EARLIER, EVERY) if forward else (EVERY, EARLIER)
    for table, column, name in WIDENED:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*before, name=name, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*after, name=name, native_enum=False, create_constraint=True, length=40),
                existing_nullable=False,
            )


def upgrade() -> None:
    widen(True)
    op.create_table(
        "trait_history",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("trait", sa.String(length=120), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_trait_history_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_trait_history_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "trait", "epoch", name=op.f("pk_trait_history")),
    )
    with op.batch_alter_table("outlaws", schema=None) as batch_op:
        batch_op.add_column(sa.Column("private_bounty", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(op.f("ck_outlaws_private_bounty_min"), "private_bounty >= 0")


def downgrade() -> None:
    with op.batch_alter_table("outlaws", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_outlaws_private_bounty_min"), type_="check")
        batch_op.drop_column("private_bounty")

    op.drop_table("trait_history")
    widen(False)
