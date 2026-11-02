import sqlalchemy as sa
from alembic import op

revision = "4b446c7e3bbb"
down_revision = "e5a91c3d7b20"
branch_labels = None
depends_on = None


OLD_STARS_STAR_TYPE = (
    "yellow_dwarf",
    "red_giant",
    "blue_giant",
    "binary",
    "white_dwarf",
    "dead_star",
    "black_sun",
    "broken_star",
    "pulsar",
    "star_remnant",
    "reborn_star",
)
NEW_STARS_STAR_TYPE = (
    "yellow_dwarf",
    "red_giant",
    "blue_giant",
    "binary",
    "white_dwarf",
    "dead_star",
    "black_sun",
    "broken_star",
    "pulsar",
    "star_remnant",
    "reborn_star",
    "blue_star",
    "blue_white_star",
    "white_star",
    "yellow_white_star",
    "orange_dwarf",
    "red_dwarf",
    "brown_dwarf",
    "yellow_giant",
    "red_supergiant",
    "blue_supergiant",
    "hypergiant",
    "wolf_rayet",
    "protostar",
    "carbon_star",
    "neutron_star",
    "magnetar",
    "black_hole",
    "variable_star",
    "trinary",
    "chained_star",
    "watching_star",
)
OLD_WORLDS_WORLD_TYPE = (
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
)
NEW_WORLDS_WORLD_TYPE = (
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
)
OLD_SKY_EVENTS_KIND = ("eclipse", "comet", "alignment", "supernova", "black_sun", "void_storm")
NEW_SKY_EVENTS_KIND = ("eclipse", "comet", "alignment", "supernova", "black_sun", "void_storm", "flare")
OLD_ROUTES_METHOD = (
    "ancient_gate",
    "space_fold",
    "light_sail",
    "cosmic_mount",
    "dream_journey",
    "river_of_dead",
    "divine_bridge",
    "slingshot_orbit",
    "swallowed",
)
NEW_ROUTES_METHOD = (
    "ancient_gate",
    "space_fold",
    "light_sail",
    "cosmic_mount",
    "dream_journey",
    "river_of_dead",
    "divine_bridge",
    "slingshot_orbit",
    "swallowed",
    "wormhole",
)
OLD_ROUTES_CLOSURE = ("sealed", "severed", "forgotten", "collapsed", "snapped")
NEW_ROUTES_CLOSURE = ("sealed", "severed", "forgotten", "collapsed", "snapped", "scorched")
OLD_HORIZON_INTUITIONS_METHOD = (
    "ancient_gate",
    "space_fold",
    "light_sail",
    "cosmic_mount",
    "dream_journey",
    "river_of_dead",
    "divine_bridge",
    "slingshot_orbit",
    "swallowed",
)
NEW_HORIZON_INTUITIONS_METHOD = (
    "ancient_gate",
    "space_fold",
    "light_sail",
    "cosmic_mount",
    "dream_journey",
    "river_of_dead",
    "divine_bridge",
    "slingshot_orbit",
    "swallowed",
    "wormhole",
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("stars", schema=None) as batch_op:
        batch_op.alter_column(
            "star_type", existing_type=enum_of(OLD_STARS_STAR_TYPE, "star_type"), type_=enum_of(NEW_STARS_STAR_TYPE, "star_type"), existing_nullable=False
        )
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.alter_column(
            "world_type",
            existing_type=enum_of(OLD_WORLDS_WORLD_TYPE, "world_type"),
            type_=enum_of(NEW_WORLDS_WORLD_TYPE, "world_type"),
            existing_nullable=False,
        )
    with op.batch_alter_table("sky_events", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of(OLD_SKY_EVENTS_KIND, "kind"), type_=enum_of(NEW_SKY_EVENTS_KIND, "kind"), existing_nullable=False)
    with op.batch_alter_table("routes", schema=None) as batch_op:
        batch_op.alter_column("method", existing_type=enum_of(OLD_ROUTES_METHOD, "method"), type_=enum_of(NEW_ROUTES_METHOD, "method"), existing_nullable=False)
        batch_op.alter_column(
            "closure", existing_type=enum_of(OLD_ROUTES_CLOSURE, "closure"), type_=enum_of(NEW_ROUTES_CLOSURE, "closure"), existing_nullable=True
        )
    with op.batch_alter_table("horizon_intuitions", schema=None) as batch_op:
        batch_op.alter_column(
            "method",
            existing_type=enum_of(OLD_HORIZON_INTUITIONS_METHOD, "method"),
            type_=enum_of(NEW_HORIZON_INTUITIONS_METHOD, "method"),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("stars", schema=None) as batch_op:
        batch_op.alter_column(
            "star_type", existing_type=enum_of(NEW_STARS_STAR_TYPE, "star_type"), type_=enum_of(OLD_STARS_STAR_TYPE, "star_type"), existing_nullable=False
        )
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.alter_column(
            "world_type",
            existing_type=enum_of(NEW_WORLDS_WORLD_TYPE, "world_type"),
            type_=enum_of(OLD_WORLDS_WORLD_TYPE, "world_type"),
            existing_nullable=False,
        )
    with op.batch_alter_table("sky_events", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of(NEW_SKY_EVENTS_KIND, "kind"), type_=enum_of(OLD_SKY_EVENTS_KIND, "kind"), existing_nullable=False)
    with op.batch_alter_table("routes", schema=None) as batch_op:
        batch_op.alter_column("method", existing_type=enum_of(NEW_ROUTES_METHOD, "method"), type_=enum_of(OLD_ROUTES_METHOD, "method"), existing_nullable=False)
        batch_op.alter_column(
            "closure", existing_type=enum_of(NEW_ROUTES_CLOSURE, "closure"), type_=enum_of(OLD_ROUTES_CLOSURE, "closure"), existing_nullable=True
        )
    with op.batch_alter_table("horizon_intuitions", schema=None) as batch_op:
        batch_op.alter_column(
            "method",
            existing_type=enum_of(NEW_HORIZON_INTUITIONS_METHOD, "method"),
            type_=enum_of(OLD_HORIZON_INTUITIONS_METHOD, "method"),
            existing_nullable=True,
        )
