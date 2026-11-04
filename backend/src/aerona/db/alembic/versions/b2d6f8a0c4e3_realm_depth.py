import sqlalchemy as sa
from alembic import op

revision = "b2d6f8a0c4e3"
down_revision = "a1c5e7f9b3d2"
branch_labels = None
depends_on = None

LOCKED = ("polity_members", "polity_territories", "offices", "claims")


def upgrade() -> None:
    with op.batch_alter_table("polity_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tier_strain", sa.Integer(), nullable=False, server_default="0"))
    for table in LOCKED:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("target_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("title", sa.String(length=120), nullable=True))
        batch_op.create_foreign_key(op.f("fk_offices_target_entity_id_entities"), "entities", ["target_entity_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.add_column(sa.Column("backer_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(op.f("fk_claims_backer_entity_id_entities"), "entities", ["backer_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index(op.f("ix_claims_backer_entity_id"), ["backer_entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.drop_index(op.f("ix_claims_backer_entity_id"))
        batch_op.drop_constraint(op.f("fk_claims_backer_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("backer_entity_id")
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_offices_target_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("title")
        batch_op.drop_column("target_entity_id")
    for table in LOCKED:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("locked")
    with op.batch_alter_table("polity_profiles", schema=None) as batch_op:
        batch_op.drop_column("tier_strain")
