import sqlalchemy as sa
from alembic import op

revision = "c7a4e2f91b38"
down_revision = "b3e8d51f6a27"
branch_labels = None
depends_on = None

TYPES_OLD = (
    "region",
    "place",
    "resource",
    "settlement",
    "species",
    "people",
    "mortal",
    "item",
    "structure",
    "language",
    "legend",
    "tradition",
    "cult",
    "faction",
    "celestial",
    "artwork",
    "law",
    "spirit",
    "knowledge",
    "prophecy",
    "event",
    "vessel",
    "outer_being",
    "army",
    "natural_law",
    "trade_route",
    "disease",
    "polity",
    "house",
    "treaty",
    "title",
    "ideology",
    "rite",
    "beast",
    "theory",
    "art_form",
    "phenomenon",
    "cosmic_being",
)
TYPES_ADDED = (
    "vehicle_type",
    "unit_type",
    "equipment_model",
    "dish",
    "building_type",
)
TYPES = (*TYPES_OLD, *TYPES_ADDED)
TYPE_COLUMNS = (("entities", "entity_type", False), ("son_powers", "param_entity_type", True))
KIND_TABLES = ("designs", "unit_designs", "equipment_models", "dishes", "structure_designs")


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    for table, column, nullable in TYPE_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, column), type_=enum_of(after, column), existing_nullable=nullable)


def upgrade() -> None:
    retype(TYPES_OLD, TYPES)
    for table in KIND_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("entity_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(f"fk_{table}_entity_id_entities", "entities", ["entity_id"], ["id"], ondelete="CASCADE")
            batch_op.create_unique_constraint(f"uq_{table}_entity_id", ["entity_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in KIND_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f"uq_{table}_entity_id", type_="unique")
            batch_op.drop_constraint(f"fk_{table}_entity_id_entities", type_="foreignkey")
            batch_op.drop_column("entity_id")
    bind.execute(
        sa.text("DELETE FROM nodes WHERE id IN (SELECT id FROM entities WHERE entity_type IN :added)").bindparams(sa.bindparam("added", expanding=True)),
        {"added": list(TYPES_ADDED)},
    )
    retype(TYPES, TYPES_OLD)
