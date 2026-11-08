import sqlalchemy as sa
from alembic import op

revision = "c7e1a9d3b5f2"
down_revision = "db8ecba2c2c1"
branch_labels = None
depends_on = None

KEPT = ("fealty", "vengeance", "celibacy", "pilgrimage", "protection", "silence")
OLD = "blood_brotherhood"
NEW = "sworn_kinship"
TEXTS = (("blood brotherhood", "sworn kinship"),)


def kinds(*values: str) -> sa.Enum:
    return sa.Enum(*KEPT, *values, name="kind", native_enum=False, create_constraint=True, length=40)


def switch(before: str, after: str) -> None:
    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=kinds(before), type_=kinds(before, after), existing_nullable=False)
    op.execute(sa.text("UPDATE oaths SET kind = :after WHERE kind = :before").bindparams(before=before, after=after))
    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=kinds(before, after), type_=kinds(after), existing_nullable=False)


def retell(pairs: tuple[tuple[str, str], ...]) -> None:
    for old, new in pairs:
        op.execute(sa.text("UPDATE bonds SET description = :new, description_key = :new WHERE description = :old").bindparams(old=old, new=new))


def upgrade() -> None:
    switch(OLD, NEW)
    retell(TEXTS)


def downgrade() -> None:
    switch(NEW, OLD)
    retell(tuple((new, old) for old, new in TEXTS))
