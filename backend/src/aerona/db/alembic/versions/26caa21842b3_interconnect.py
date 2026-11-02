import sqlalchemy as sa
from alembic import op

import aerona.db.types

revision = "26caa21842b3"
down_revision = "c7d2f4a8e915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "modifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column("target_key", sa.String(length=120), nullable=False),
        sa.Column("op", sa.Enum("add", "multiply", name="op", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=False),
        sa.Column(
            "source_kind",
            sa.Enum(
                "injury",
                "condition",
                "trait",
                "law",
                "tradition",
                "artwork",
                "doctrine",
                "treaty",
                "structure",
                "wonder",
                "terrain",
                "weather",
                "season",
                "natural_law",
                "god_power",
                "blessing",
                "curse",
                "dominion",
                "phenomenon",
                "god_death",
                "player",
                "suppression",
                "pin",
                name="source_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("stacking_group", sa.String(length=120), nullable=True),
        sa.Column("start_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column("decay_pct", sa.Integer(), nullable=True),
        sa.Column("reason_key", sa.String(length=120), nullable=False),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("decay_pct IS NULL OR decay_pct BETWEEN 0 AND 100", name=op.f("ck_modifiers_decay_pct_range")),
        sa.CheckConstraint("end_epoch IS NULL OR end_epoch >= start_epoch", name=op.f("ck_modifiers_ends_after_start")),
        sa.CheckConstraint("start_epoch >= 0", name=op.f("ck_modifiers_start_epoch_min")),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_modifiers_source_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_modifiers_target_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modifiers")),
    )
    with op.batch_alter_table("modifiers", schema=None) as batch_op:
        batch_op.create_index("ix_modifiers_source", ["source_kind", "source_node_id"], unique=False)
        batch_op.create_index("ix_modifiers_target_key", ["target_node_id", "target_key"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=120), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("place_entity_id", sa.Integer(), nullable=True),
        sa.Column("cause_incident_id", sa.Integer(), nullable=True),
        sa.Column("chronicle_id", sa.Integer(), nullable=True),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_incidents_epoch_min")),
        sa.CheckConstraint("magnitude >= 0", name=op.f("ck_incidents_magnitude_min")),
        sa.ForeignKeyConstraint(["cause_incident_id"], ["incidents.id"], name=op.f("fk_incidents_cause_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chronicle_id"], ["chronicle.id"], name=op.f("fk_incidents_chronicle_id_chronicle"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_incidents_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_incidents_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint("chronicle_id", name=op.f("uq_incidents_chronicle_id")),
    )
    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.create_index("ix_incidents_cause", ["cause_incident_id"], unique=False)
        batch_op.create_index("ix_incidents_epoch_kind", ["epoch", "kind"], unique=False)

    op.create_table(
        "incident_participants",
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("subject", "actor", "target", "witness", "place", name="role", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_incident_participants_incident_id_incidents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_incident_participants_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("incident_id", "node_id", "role", name=op.f("pk_incident_participants")),
    )
    with op.batch_alter_table("incident_participants", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_incident_participants_node_id"), ["node_id"], unique=False)

    op.execute(
        "INSERT INTO incidents (kind, epoch, year, world_id, chronicle_id, magnitude, created_at) "
        "SELECT COALESCE(template_key, kind), epoch, year, world_id, id, 0, created_at FROM chronicle ORDER BY id"
    )
    op.execute(
        "INSERT INTO incident_participants (incident_id, node_id, role, position) "
        "SELECT incidents.id, chronicle_entities.entity_id, 'subject', chronicle_entities.position "
        "FROM chronicle_entities JOIN incidents ON incidents.chronicle_id = chronicle_entities.chronicle_id"
    )
    op.execute(
        "INSERT INTO incident_participants (incident_id, node_id, role, position) "
        "SELECT incidents.id, chronicle.son_id, 'actor', 0 FROM chronicle JOIN incidents ON incidents.chronicle_id = chronicle.id "
        "WHERE chronicle.son_id IS NOT NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("incident_participants", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_incident_participants_node_id"))

    op.drop_table("incident_participants")
    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.drop_index("ix_incidents_epoch_kind")
        batch_op.drop_index("ix_incidents_cause")

    op.drop_table("incidents")
    with op.batch_alter_table("modifiers", schema=None) as batch_op:
        batch_op.drop_index("ix_modifiers_target_key")
        batch_op.drop_index("ix_modifiers_source")

    op.drop_table("modifiers")
