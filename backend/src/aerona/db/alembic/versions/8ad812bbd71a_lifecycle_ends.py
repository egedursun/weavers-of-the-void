import sqlalchemy as sa
from alembic import op

revision = "8ad812bbd71a"
down_revision = "4490378d89b2"
branch_labels = None
depends_on = None

OLD_SIGHTS = ("wonder", "baths", "sacred", "battlefield", "city")
NEW_SIGHTS = (*OLD_SIGHTS, "collection", "garden")


def sight_type(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="sight", native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    op.create_table(
        "world_ends",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "shattered",
                "swallowed",
                "frozen_dead",
                "sunk_into_void",
                "forgotten",
                "transfigured",
                name="state",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "cause",
            sa.Enum(
                "impact",
                "divine_wrath",
                "star_giant",
                "star_death",
                "void",
                "oblivion",
                "belief_drift",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "former_type",
            sa.Enum(
                "ordinary",
                "ocean",
                "sand",
                "ice",
                "lava",
                "crystal",
                "living",
                "dead",
                "dream",
                "mirror",
                "gas",
                "ringed",
                "asteroid_belt",
                "tidally_locked",
                "void_pocket",
                "gods_palace",
                "generation_ship",
                "corpse_world",
                "super_earth",
                "ice_giant",
                "hot_giant",
                "iron",
                "carbon",
                "greenhouse",
                "dwarf_planet",
                "chthonian",
                "hycean",
                "jungle",
                "forge",
                "fungal",
                "shattered",
                "hollow",
                "ice_shell",
                "methane",
                name="former_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "new_type",
            sa.Enum(
                "ordinary",
                "ocean",
                "sand",
                "ice",
                "lava",
                "crystal",
                "living",
                "dead",
                "dream",
                "mirror",
                "gas",
                "ringed",
                "asteroid_belt",
                "tidally_locked",
                "void_pocket",
                "gods_palace",
                "generation_ship",
                "corpse_world",
                "super_earth",
                "ice_giant",
                "hot_giant",
                "iron",
                "carbon",
                "greenhouse",
                "dwarf_planet",
                "chthonian",
                "hycean",
                "jungle",
                "forge",
                "fungal",
                "shattered",
                "hollow",
                "ice_shell",
                "methane",
                name="new_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("lives_ended", sa.Integer(), nullable=False),
        sa.Column("homeless", sa.Integer(), nullable=False),
        sa.Column("anchors_lost", sa.Integer(), nullable=False),
        sa.Column("routes_closed", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("anchors_lost >= 0", name=op.f("ck_world_ends_anchors_lost_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_world_ends_epoch_min")),
        sa.CheckConstraint("homeless >= 0", name=op.f("ck_world_ends_homeless_min")),
        sa.CheckConstraint("lives_ended >= 0", name=op.f("ck_world_ends_lives_ended_min")),
        sa.CheckConstraint("routes_closed >= 0", name=op.f("ck_world_ends_routes_closed_min")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_ends_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_ends")),
    )
    op.create_table(
        "fossil_beds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "extinct_species",
                "megafauna",
                "beast",
                "previous_creation",
                "extinct_people",
                name="source",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("source_entity_id", sa.Integer(), nullable=True),
        sa.Column("richness", sa.Integer(), nullable=False),
        sa.Column("frozen", sa.Boolean(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=True),
        sa.Column("laid_epoch", sa.Integer(), nullable=False),
        sa.Column("found_epoch", sa.Integer(), nullable=True),
        sa.Column("finder_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "reading", sa.Enum("unread", "legend", "relic", "deep_time", name="reading", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("laid_epoch >= 0", name=op.f("ck_fossil_beds_laid_epoch_min")),
        sa.CheckConstraint("richness BETWEEN 1 AND 100", name=op.f("ck_fossil_beds_richness_range")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_fossil_beds_disease_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finder_entity_id"], ["entities.id"], name=op.f("fk_fossil_beds_finder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_fossil_beds_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], name=op.f("fk_fossil_beds_source_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_fossil_beds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fossil_beds")),
        sa.UniqueConstraint("source_entity_id", name=op.f("uq_fossil_beds_source_entity_id")),
    )
    with op.batch_alter_table("fossil_beds", schema=None) as batch_op:
        batch_op.create_index("ix_fossil_beds_region", ["region_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_fossil_beds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "gardens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("structure_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "pleasure",
                "physic",
                "monastery",
                "park",
                "hunting_park",
                "sacred_grove",
                "cemetery",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("species", sa.JSON(), nullable=False),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("unpaid_epochs", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_gardens_condition_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_gardens_founded_epoch_min")),
        sa.CheckConstraint("unpaid_epochs >= 0", name=op.f("ck_gardens_unpaid_epochs_min")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_gardens_upkeep_min")),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_gardens_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_gardens_structure_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gardens")),
    )
    with op.batch_alter_table("gardens", schema=None) as batch_op:
        batch_op.create_index("ix_gardens_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "lifecycle_states",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("ideology", "theory", "rite", "disease", "outer_being", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.Enum(
                "active",
                "dormant",
                "extinct",
                "lost",
                "corrupted",
                "eradicated",
                "banished",
                "destroyed",
                name="state",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "cause",
            sa.Enum(
                "living",
                "no_adherents",
                "no_texts",
                "no_practitioners",
                "no_hosts",
                "sealed",
                "revived",
                "rediscovered",
                "reconstructed",
                "rereleased",
                "returned",
                "god_act",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("idle_epochs", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("idle_epochs >= 0", name=op.f("ck_lifecycle_states_idle_epochs_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_lifecycle_states_since_epoch_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_lifecycle_states_updated_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_lifecycle_states_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_lifecycle_states")),
    )
    op.create_table(
        "museum_collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keeper_entity_id", sa.Integer(), nullable=False),
        sa.Column("structure_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("cabinet", "temple_treasury", "royal_collection", "museum", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_museum_collections_founded_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_museum_collections_prestige_range")),
        sa.ForeignKeyConstraint(["keeper_entity_id"], ["entities.id"], name=op.f("fk_museum_collections_keeper_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_museum_collections_structure_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_museum_collections")),
    )
    with op.batch_alter_table("museum_collections", schema=None) as batch_op:
        batch_op.create_index("ix_museum_collections_keeper", ["keeper_entity_id"], unique=False)

    op.create_table(
        "museum_pieces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("artifact", "relic", "fossil", "art", "specimen", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("item_entity_id", sa.Integer(), nullable=True),
        sa.Column("fossil_bed_id", sa.Integer(), nullable=True),
        sa.Column("acquired_epoch", sa.Integer(), nullable=False),
        sa.Column("looted_from_entity_id", sa.Integer(), nullable=True),
        sa.Column("returned_epoch", sa.Integer(), nullable=True),
        sa.Column("returned_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("acquired_epoch >= 0", name=op.f("ck_museum_pieces_acquired_epoch_min")),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["museum_collections.id"], name=op.f("fk_museum_pieces_collection_id_museum_collections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["fossil_bed_id"], ["fossil_beds.id"], name=op.f("fk_museum_pieces_fossil_bed_id_fossil_beds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_museum_pieces_item_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["looted_from_entity_id"], ["entities.id"], name=op.f("fk_museum_pieces_looted_from_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["returned_by_entity_id"], ["entities.id"], name=op.f("fk_museum_pieces_returned_by_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_museum_pieces")),
        sa.UniqueConstraint("fossil_bed_id", name=op.f("uq_museum_pieces_fossil_bed_id")),
        sa.UniqueConstraint("item_entity_id", name=op.f("uq_museum_pieces_item_entity_id")),
    )
    with op.batch_alter_table("museum_pieces", schema=None) as batch_op:
        batch_op.create_index("ix_museum_pieces_collection", ["collection_id"], unique=False)
    with op.batch_alter_table("tourist_flows", schema=None) as batch_op:
        batch_op.alter_column("sight", existing_type=sight_type(OLD_SIGHTS), type_=sight_type(NEW_SIGHTS), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("tourist_flows", schema=None) as batch_op:
        batch_op.alter_column("sight", existing_type=sight_type(NEW_SIGHTS), type_=sight_type(OLD_SIGHTS), existing_nullable=False)
    with op.batch_alter_table("museum_pieces", schema=None) as batch_op:
        batch_op.drop_index("ix_museum_pieces_collection")

    op.drop_table("museum_pieces")
    with op.batch_alter_table("museum_collections", schema=None) as batch_op:
        batch_op.drop_index("ix_museum_collections_keeper")

    op.drop_table("museum_collections")
    op.drop_table("lifecycle_states")
    with op.batch_alter_table("gardens", schema=None) as batch_op:
        batch_op.drop_index("ix_gardens_settlement")

    op.drop_table("gardens")
    with op.batch_alter_table("fossil_beds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fossil_beds_world_id"))
        batch_op.drop_index("ix_fossil_beds_region")

    op.drop_table("fossil_beds")
    op.drop_table("world_ends")
