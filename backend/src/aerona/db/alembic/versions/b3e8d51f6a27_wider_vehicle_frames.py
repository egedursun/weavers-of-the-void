import sqlalchemy as sa
from alembic import op

revision = "b3e8d51f6a27"
down_revision = "9d1e4b7c3a52"
branch_labels = None
depends_on = None

FRAMES_OLD = (
    "riding_mount",
    "pack_mount",
    "travois",
    "sledge",
    "handcart",
    "cart",
    "wagon",
    "covered_wagon",
    "carriage",
    "chariot",
    "war_wagon",
    "beast_carrier",
    "rail_car",
    "locomotive",
    "steam_carriage",
    "motor_car",
    "motor_truck",
    "motorcycle",
    "armoured_car",
    "tank",
    "walker",
    "crawler",
    "construct_walker",
    "construct_carrier",
    "battering_ram",
    "siege_tower",
    "mantlet",
    "catapult",
    "trebuchet",
    "ballista",
    "bombard",
    "field_gun",
    "mortar",
    "rocket_battery",
    "raft",
    "canoe",
    "rowboat",
    "boat",
    "river_barge",
    "sailboat",
    "galley",
    "longship",
    "cog",
    "carrack",
    "galleon",
    "frigate",
    "warship",
    "ship_of_the_line",
    "steamship",
    "ironclad",
    "battleship",
    "submarine",
    "living_ship",
    "fire_ship",
    "balloon",
    "airship",
    "glider",
    "ornithopter",
    "sky_sailer",
    "skyship",
    "flying_carriage",
    "aeroplane",
    "rotorcraft",
    "flying_car",
    "flying_construct",
    "orbital_lander",
    "shuttle",
    "solar_sailer",
    "starship",
    "generation_ship",
    "void_ark",
    "cloud_skimmer",
    "aerostat",
    "deep_submersible",
    "burrower",
    "planar_vessel",
)
FRAMES_ADDED = (
    "hovercraft",
    "amphibious_carrier",
    "landing_craft",
    "amphibious_raft",
    "tunnel_cart",
    "mine_train",
    "delving_construct",
    "deep_crawler",
    "diving_bell",
    "attack_submarine",
    "gas_harvester",
    "deep_diver",
    "rift_skiff",
    "planar_ark",
    "divine_vessel",
    "space_fighter",
    "freighter",
    "mining_barge",
    "corvette",
    "dreadnought",
    "jet_fighter",
    "bomber",
    "drone",
    "trireme",
    "coastal_trader",
    "catamaran",
    "fleet_carrier",
    "hover_tank",
)
FRAMES = (*FRAMES_OLD, *FRAMES_ADDED)
FRAME_COLUMNS = (("designs", True), ("vessel_profiles", False))


def enum_of(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="frame", native_enum=False, create_constraint=True, length=40)


def retype(before: tuple[str, ...], after: tuple[str, ...]) -> None:
    for table, nullable in FRAME_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column("frame", existing_type=enum_of(before), type_=enum_of(after), existing_nullable=nullable)


def upgrade() -> None:
    retype(FRAMES_OLD, FRAMES)


def downgrade() -> None:
    bind = op.get_bind()
    for table, nullable in FRAME_COLUMNS:
        fallback = "NULL" if nullable else "'boat'"
        bind.execute(
            sa.text(f"UPDATE {table} SET frame = {fallback} WHERE frame IN :added").bindparams(sa.bindparam("added", expanding=True)),
            {"added": list(FRAMES_ADDED)},
        )
    retype(FRAMES, FRAMES_OLD)
