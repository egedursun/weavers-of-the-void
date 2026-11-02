import sqlalchemy as sa
from alembic import op

revision = "069aeb7ac3ec"
down_revision = "26caa21842b3"
branch_labels = None
depends_on = None


OLD_CAUSES = (
    "hostility",
    "uprising",
    "tribute_revolt",
    "incited",
    "declared",
    "betrayal",
    "conquest_journey",
    "foreign_god",
)
NEW_CAUSES = (
    "hostility",
    "uprising",
    "tribute_revolt",
    "incited",
    "declared",
    "betrayal",
    "conquest_journey",
    "foreign_god",
    "independence",
    "vendetta",
    "grudge",
    "divine_grudge",
    "rivalry",
    "debt",
    "espionage",
    "sabotage",
    "envy",
    "schism",
    "beast",
    "resource",
)
ENEMY_ONLY = "kind = 'enemy' OR (war_cause IS NULL AND incited_by_son_id IS NULL)"


def cause_type(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="cause", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "war_cause",
                sa.Enum(
                    "hostility",
                    "uprising",
                    "tribute_revolt",
                    "incited",
                    "declared",
                    "betrayal",
                    "conquest_journey",
                    "foreign_god",
                    "independence",
                    "vendetta",
                    "grudge",
                    "divine_grudge",
                    "rivalry",
                    "debt",
                    "espionage",
                    "sabotage",
                    "envy",
                    "schism",
                    "beast",
                    "resource",
                    name="war_cause",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("incited_by_son_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_bonds_incited_by_son_id_sons"), "sons", ["incited_by_son_id"], ["id"], ondelete="SET NULL")
        batch_op.create_check_constraint(op.f("ck_bonds_war_cause_only_on_enemy"), ENEMY_ONLY)
    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.alter_column("cause", existing_type=cause_type(OLD_CAUSES), type_=cause_type(NEW_CAUSES), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.alter_column("cause", existing_type=cause_type(NEW_CAUSES), type_=cause_type(OLD_CAUSES), existing_nullable=False)
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_bonds_war_cause_only_on_enemy"), type_="check")
        batch_op.drop_constraint(batch_op.f("fk_bonds_incited_by_son_id_sons"), type_="foreignkey")
        batch_op.drop_column("incited_by_son_id")
        batch_op.drop_column("war_cause")
