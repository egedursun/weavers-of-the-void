import sqlalchemy as sa
from alembic import op

revision = "1dc131e7184d"
down_revision = "327eda9835ce"
branch_labels = None
depends_on = None


BEFORE = (
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
    "almshouse",
)
ADDED = (
    "brewery",
    "sawmill",
    "fishery",
    "charcoal_kiln",
    "stables",
    "siege_workshop",
    "mint",
    "tavern",
    "town_hall",
    "guildhall",
    "barracks",
    "orphanage",
    "apothecary",
    "training_ground",
    "museum",
    "plaza",
)
AFTER = (*BEFORE, *ADDED)
WIDENED = (
    ("structure_profiles", "kind", "structure_kind"),
    ("constructions", "kind", "structure_kind"),
    ("structure_designs", "base_kind", "base_kind"),
)


def widen(forward: bool) -> None:
    before, after = (BEFORE, AFTER) if forward else (AFTER, BEFORE)
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


def downgrade() -> None:
    for table, column, _ in WIDENED:
        op.execute(sa.text(f"DELETE FROM {table} WHERE {column} IN ({', '.join(repr(value) for value in ADDED)})"))
    widen(False)
