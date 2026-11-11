import sqlalchemy as sa
from alembic import op

revision = "10f7d9846da8"
down_revision = "f15cb9ca02d5"
branch_labels = None
depends_on = None


DISTRICTS_BEFORE = (
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
)
DISTRICTS_AFTER = (*DISTRICTS_BEFORE, "residential", "civic_quarter", "gardens")
STRUCTURES_BEFORE = (
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
    "fountain",
    "park",
    "slaughterhouse",
)
STRUCTURES_AFTER = (*STRUCTURES_BEFORE, "almshouse")
WIDENED = (
    ("districts", "kind", "kind", False, DISTRICTS_BEFORE, DISTRICTS_AFTER),
    ("district_designs", "base_kind", "base_kind", False, DISTRICTS_BEFORE, DISTRICTS_AFTER),
    ("mandates", "district", "district", True, DISTRICTS_BEFORE, DISTRICTS_AFTER),
    ("structure_profiles", "kind", "structure_kind", False, STRUCTURES_BEFORE, STRUCTURES_AFTER),
    ("constructions", "kind", "structure_kind", False, STRUCTURES_BEFORE, STRUCTURES_AFTER),
    ("structure_designs", "base_kind", "base_kind", False, STRUCTURES_BEFORE, STRUCTURES_AFTER),
)


def widen(forward: bool) -> None:
    for table, column, name, nullable, earlier, later in WIDENED:
        before, after = (earlier, later) if forward else (later, earlier)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*before, name=name, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*after, name=name, native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    widen(True)
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hex_q", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("hex_r", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.execute("DELETE FROM districts WHERE kind IN ('residential', 'civic_quarter', 'gardens')")
    op.execute("DELETE FROM district_designs WHERE base_kind IN ('residential', 'civic_quarter', 'gardens')")
    op.execute("UPDATE mandates SET district = NULL WHERE district IN ('residential', 'civic_quarter', 'gardens')")
    op.execute("DELETE FROM structure_profiles WHERE kind = 'almshouse'")
    op.execute("DELETE FROM constructions WHERE kind = 'almshouse'")
    op.execute("DELETE FROM structure_designs WHERE base_kind = 'almshouse'")
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.drop_column("hex_r")
        batch_op.drop_column("hex_q")
    widen(False)
