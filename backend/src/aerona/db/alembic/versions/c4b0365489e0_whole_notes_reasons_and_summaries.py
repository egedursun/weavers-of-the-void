import sqlalchemy as sa
from alembic import op

revision = "c4b0365489e0"
down_revision = "0832234d5e32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("battle_casualties", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=240), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("battle_phases", schema=None) as batch_op:
        batch_op.alter_column("summary", existing_type=sa.VARCHAR(length=480), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("castings", schema=None) as batch_op:
        batch_op.alter_column("effect", existing_type=sa.VARCHAR(length=480), type_=sa.Text(), existing_nullable=False)

    with op.batch_alter_table("custom_kinds", schema=None) as batch_op:
        batch_op.alter_column("description", existing_type=sa.VARCHAR(length=480), type_=sa.Text(), existing_nullable=False)

    with op.batch_alter_table("faction_actions", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("feuds", schema=None) as batch_op:
        batch_op.alter_column("cause", existing_type=sa.VARCHAR(length=240), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("loans", schema=None) as batch_op:
        batch_op.alter_column("purpose", existing_type=sa.VARCHAR(length=64), type_=sa.Text(), existing_nullable=False)

    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("office_history", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("peace_terms", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=240), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("polity_treasury", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("region_memories", schema=None) as batch_op:
        batch_op.alter_column("title", existing_type=sa.VARCHAR(length=300), type_=sa.Text(), existing_nullable=False)

    with op.batch_alter_table("settlement_treasury", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("soul_judgements", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=sa.VARCHAR(length=480), type_=sa.Text(), existing_nullable=False)

    with op.batch_alter_table("title_profiles", schema=None) as batch_op:
        batch_op.alter_column("emblem", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("trade_policies", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)

    with op.batch_alter_table("treaty_breaches", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.VARCHAR(length=120), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("treaty_breaches", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("trade_policies", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("title_profiles", schema=None) as batch_op:
        batch_op.alter_column("emblem", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("soul_judgements", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=sa.Text(), type_=sa.VARCHAR(length=480), existing_nullable=False)

    with op.batch_alter_table("settlement_treasury", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("region_memories", schema=None) as batch_op:
        batch_op.alter_column("title", existing_type=sa.Text(), type_=sa.VARCHAR(length=300), existing_nullable=False)

    with op.batch_alter_table("polity_treasury", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("peace_terms", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=240), existing_nullable=True)

    with op.batch_alter_table("office_history", schema=None) as batch_op:
        batch_op.alter_column("reason", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("loans", schema=None) as batch_op:
        batch_op.alter_column("purpose", existing_type=sa.Text(), type_=sa.VARCHAR(length=64), existing_nullable=False)

    with op.batch_alter_table("feuds", schema=None) as batch_op:
        batch_op.alter_column("cause", existing_type=sa.Text(), type_=sa.VARCHAR(length=240), existing_nullable=True)

    with op.batch_alter_table("faction_actions", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=120), existing_nullable=True)

    with op.batch_alter_table("custom_kinds", schema=None) as batch_op:
        batch_op.alter_column("description", existing_type=sa.Text(), type_=sa.VARCHAR(length=480), existing_nullable=False)

    with op.batch_alter_table("castings", schema=None) as batch_op:
        batch_op.alter_column("effect", existing_type=sa.Text(), type_=sa.VARCHAR(length=480), existing_nullable=False)

    with op.batch_alter_table("battle_phases", schema=None) as batch_op:
        batch_op.alter_column("summary", existing_type=sa.Text(), type_=sa.VARCHAR(length=480), existing_nullable=True)

    with op.batch_alter_table("battle_casualties", schema=None) as batch_op:
        batch_op.alter_column("note", existing_type=sa.Text(), type_=sa.VARCHAR(length=240), existing_nullable=True)
