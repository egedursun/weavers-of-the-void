from alembic import op

revision = "a7c3e9f1b5d2"
down_revision = "f3a8c1d5e9b2"
branch_labels = None
depends_on = None

TABLE = "incident_participants"
BY_NODE = "ix_incident_participants_node_id"
BY_NODE_AND_INCIDENT = "ix_incident_participants_node_id_incident_id"


def upgrade() -> None:
    op.create_index(BY_NODE_AND_INCIDENT, TABLE, ["node_id", "incident_id"])
    op.drop_index(BY_NODE, table_name=TABLE)


def downgrade() -> None:
    op.create_index(BY_NODE, TABLE, ["node_id"])
    op.drop_index(BY_NODE_AND_INCIDENT, table_name=TABLE)
