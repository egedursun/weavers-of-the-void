from alembic import op

revision = "c0a1d9e4f7b2"
down_revision = "54ff7cd7fe11"
branch_labels = None
depends_on = None

OLD_ROLES = ("leader", "member", "victim", "witness", "host", "guest", "winner", "loser", "founder", "accused", "finder", "place")
NEW_ROLES = (*OLD_ROLES, "product")
CONSTRAINT = "ck_collection_members_role"


def allowed(values: tuple[str, ...]) -> str:
    return "role IN (" + ", ".join(f"'{value}'" for value in values) + ")"


def replace_check(values: tuple[str, ...]) -> None:
    with op.batch_alter_table("collection_members", schema=None, recreate="always") as batch_op:
        batch_op.drop_constraint(op.f(CONSTRAINT), type_="check")
        batch_op.create_check_constraint(op.f(CONSTRAINT), allowed(values))


def upgrade() -> None:
    replace_check(NEW_ROLES)


def downgrade() -> None:
    op.execute("UPDATE collection_members SET role = 'member' WHERE role = 'product'")
    replace_check(OLD_ROLES)
