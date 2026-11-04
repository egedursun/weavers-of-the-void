import sqlalchemy as sa
from alembic import op

revision = "b7b4f0c3a5e9"
down_revision = "b6a3e9b2f4d8"
branch_labels = None
depends_on = None

DANGER_SOURCES = ("beasts", "bandits", "monsters", "phenomena", "disease", "avalanche", "quicksand", "volcanic")
DANGER_ORIGINS = ("derived", "player", "divine")
MEMORY_KINDS = ("battle", "massacre", "sack", "disaster", "plague", "famine", "god_death", "saint_burial", "miracle")
MEMORY_ORIGINS = ("derived", "player")
HAZARDS = ("avalanche", "spring_flood", "wildfire", "whiteout")


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sacredness", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(op.f("ck_region_environment_sacredness_range"), "sacredness BETWEEN 0 AND 100")

    op.create_table(
        "region_dangers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("source", enum_of("source", DANGER_SOURCES), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("origin", enum_of("origin", DANGER_ORIGINS), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("son_id", sa.Integer(), nullable=True),
        sa.Column("held", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_region_dangers_strength_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_region_dangers_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_region_dangers_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_region_dangers_source_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_region_dangers_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_region_dangers")),
        sa.UniqueConstraint("region_entity_id", "source", name="one_danger_per_source"),
    )
    with op.batch_alter_table("region_dangers", schema=None) as batch_op:
        batch_op.create_index("ix_region_dangers_world", ["world_id"], unique=False)

    op.create_table(
        "region_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum_of("kind", MEMORY_KINDS), nullable=False),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("origin", enum_of("origin", MEMORY_ORIGINS), nullable=False),
        sa.Column("held", sa.Boolean(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_region_memories_epoch_min")),
        sa.CheckConstraint("magnitude BETWEEN 0 AND 100", name=op.f("ck_region_memories_magnitude_range")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_region_memories_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_region_memories_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_region_memories_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_region_memories_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_region_memories")),
        sa.UniqueConstraint("region_entity_id", "source_key", name="one_memory_per_source"),
    )
    with op.batch_alter_table("region_memories", schema=None) as batch_op:
        batch_op.create_index("ix_region_memories_world", ["world_id"], unique=False)

    op.create_table(
        "polity_map_knowledge",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("held", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 100", name=op.f("ck_polity_map_knowledge_level_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_map_knowledge_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_polity_map_knowledge_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "region_entity_id", name=op.f("pk_polity_map_knowledge")),
    )
    with op.batch_alter_table("polity_map_knowledge", schema=None) as batch_op:
        batch_op.create_index("ix_polity_map_knowledge_region", ["region_entity_id"], unique=False)

    op.create_table(
        "region_hazards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("hazard", enum_of("hazard", HAZARDS), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season_name", sa.String(length=120), nullable=True),
        sa.Column("deaths", sa.Integer(), nullable=False),
        sa.Column("injured", sa.Integer(), nullable=False),
        sa.Column("soldiers_lost", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("deaths >= 0", name=op.f("ck_region_hazards_deaths_min")),
        sa.CheckConstraint("injured >= 0", name=op.f("ck_region_hazards_injured_min")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_region_hazards_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_region_hazards_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_region_hazards_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_region_hazards")),
    )
    with op.batch_alter_table("region_hazards", schema=None) as batch_op:
        batch_op.create_index("ix_region_hazards_region", ["region_entity_id", "epoch"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("region_hazards", schema=None) as batch_op:
        batch_op.drop_index("ix_region_hazards_region")
    op.drop_table("region_hazards")
    with op.batch_alter_table("polity_map_knowledge", schema=None) as batch_op:
        batch_op.drop_index("ix_polity_map_knowledge_region")
    op.drop_table("polity_map_knowledge")
    with op.batch_alter_table("region_memories", schema=None) as batch_op:
        batch_op.drop_index("ix_region_memories_world")
    op.drop_table("region_memories")
    with op.batch_alter_table("region_dangers", schema=None) as batch_op:
        batch_op.drop_index("ix_region_dangers_world")
    op.drop_table("region_dangers")
    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_region_environment_sacredness_range"), type_="check")
        batch_op.drop_column("sacredness")
