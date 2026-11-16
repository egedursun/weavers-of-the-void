import sqlalchemy as sa
from alembic import op

revision = "c4a1e9d2f7b3"
down_revision = "7d39d9f066da"
branch_labels = None
depends_on = None

CRIME_OLD = ("theft", "blasphemy", "treason", "murder", "desertion", "witchcraft")
CRIME_NEW = (*CRIME_OLD, "mind_theft", "unlicensed_copying", "forced_edit", "erasure", "machine_seizure", "impersonation")
MODALITY_OLD = ("vocal", "sign", "scent", "colour", "telepathic")
MODALITY_NEW = (*MODALITY_OLD, "data")
FIND_OLD = ("nothing", "artifact", "book", "technique", "regalia", "route_map")
FIND_NEW = (*FIND_OLD, "waking")
RETYPED = (
    ("crime_cases", "crime", CRIME_OLD, CRIME_NEW, None),
    ("precedents", "crime", CRIME_OLD, CRIME_NEW, None),
    ("sentences", "crime", CRIME_OLD, CRIME_NEW, None),
    ("language_profiles", "modality", MODALITY_OLD, MODALITY_NEW, "vocal"),
    ("excavation_stages", "find", FIND_OLD, FIND_NEW, "nothing"),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, old, new, fallback in RETYPED:
        before, after = (old, new) if forward else (new, old)
        gone = ", ".join(f"'{value}'" for value in new if value not in old)
        if not forward and fallback is not None:
            op.execute(f"UPDATE {table} SET {column} = '{fallback}' WHERE {column} IN ({gone})")
        elif not forward:
            op.execute(f"DELETE FROM {table} WHERE {column} IN ({gone})")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, column), type_=enum_of(after, column), existing_nullable=False)


def upgrade() -> None:
    with op.batch_alter_table("currencies", schema=None) as batch_op:
        batch_op.alter_column("metal", nullable=True)
    retype(True)


def downgrade() -> None:
    retype(False)
    op.execute("UPDATE currencies SET metal = 'silver' WHERE metal IS NULL")
    with op.batch_alter_table("currencies", schema=None) as batch_op:
        batch_op.alter_column("metal", nullable=False)
