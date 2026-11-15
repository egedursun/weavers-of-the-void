import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "6ac942d7db59"
down_revision = "8ad812bbd71a"
branch_labels = None
depends_on = None

MOTIONS = frozenset(
    {
        "none",
        "against_doomsday",
        "joint_blessing",
        "condemn_rebel",
        "call_for_peace",
        "war_on_foreign_god",
        "divide_worlds",
        "outlaw_rite",
        "punish_son",
        "bless_hero",
        "holy_world",
        "cosmic_truce",
        "petition_creator",
        "appoint_office",
    }
)
LEGACY_ENUMS = json.loads((Path(__file__).resolve().parents[3] / "migration" / "legacy" / "schema_map.json").read_text(encoding="utf-8"))["enums"]
MOTION_ALIASES: dict[str, str] = LEGACY_ENUMS["council_motion"]
CALLERS = frozenset({"creator", "fate"})
SAYING_LABELS = {
    "proverb": "Proverb",
    "lullaby": "Lullaby",
    "prayer": "Prayer",
    "malediction": "Malediction",
    "folk_song": "Folk song",
    "oath": "Oath",
    "tongue_twister": "Tongue twister",
    "hymn": "Hymn",
}
SAYING_ALIASES: dict[str, str] = LEGACY_ENUMS["saying_kind"]
ENTITY_TYPES = frozenset(
    {
        "region",
        "place",
        "resource",
        "settlement",
        "species",
        "people",
        "mortal",
        "item",
        "structure",
        "language",
        "legend",
        "tradition",
        "cult",
        "faction",
        "celestial",
        "artwork",
        "law",
        "spirit",
        "knowledge",
        "prophecy",
        "event",
        "vessel",
        "outer_being",
        "army",
        "natural_law",
        "trade_route",
        "disease",
        "polity",
        "house",
        "treaty",
        "title",
        "ideology",
        "rite",
        "beast",
        "theory",
        "art_form",
        "phenomenon",
        "cosmic_being",
        "vehicle_type",
        "unit_type",
        "equipment_model",
        "dish",
        "building_type",
    }
)
GROUNDS = {
    "terrain": frozenset(
        {
            "plain",
            "steppe",
            "forest",
            "jungle",
            "marsh",
            "hills",
            "mountains",
            "high_pass",
            "desert",
            "tundra",
            "ice_sheet",
            "volcanic",
            "coast",
            "island",
            "river_valley",
            "canyon",
            "underground",
            "crystal_field",
            "flesh",
            "void_shore",
            "ruin_field",
            "urban",
            "sea",
        }
    ),
    "soil": frozenset({"thin", "loam", "clay", "sand", "volcanic", "peat", "salt", "ash", "crystal", "bone"}),
    "climate": frozenset({"frozen", "cold", "temperate", "warm", "hot", "searing"}),
}
DANGER_SOURCES = frozenset({"beasts", "bandits", "monsters", "phenomena", "disease", "avalanche", "quicksand", "volcanic"})
DEPTH_TABLES = ("dimensions", "galaxy_clusters", "galaxies", "stars", "worlds", "creator", "foreign_gods", "entities")


def loaded(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def typed_minutes(minutes: dict[str, Any]) -> dict[str, Any]:
    said = str(minutes.get("decision") or "")
    motion = MOTION_ALIASES.get(said, said)
    notes = list(minutes.get("notes") or [])
    known = motion in MOTIONS
    caller = str(minutes.get("convened_by") or "")
    return {
        **minutes,
        "convened_by": caller if caller in CALLERS else "creator",
        "decision": motion if known else "none",
        "notes": notes if known or not said else [said, *notes],
    }


def saying_label(form: str) -> str:
    return SAYING_LABELS.get(SAYING_ALIASES.get(form, form), form)


def labelled_sayings(depth: dict[str, Any]) -> dict[str, Any]:
    sayings = [{**item, "form": saying_label(str(item.get("form") or ""))} for item in depth.get("sayings") or []]
    return {**depth, "sayings": sayings}


def sound_ground(snapshot: dict[str, Any]) -> bool:
    return all(snapshot.get(field) in values for field, values in GROUNDS.items()) and snapshot.get("danger_source") in {None, *DANGER_SOURCES}


def kept_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    political = {key: control for key, control in (data.get("political") or {}).items() if control.get("ruler_type") in ENTITY_TYPES}
    ground = {key: snapshot for key, snapshot in (data.get("ground") or {}).items() if sound_ground(snapshot)}
    return {**data, "political": political, "ground": ground}


def upgrade() -> None:
    connection = op.get_bind()
    for row_id, minutes in connection.execute(sa.text("SELECT id, minutes FROM councils")).all():
        connection.execute(
            sa.text("UPDATE councils SET minutes = :minutes WHERE id = :id"), {"minutes": json.dumps(typed_minutes(loaded(minutes))), "id": row_id}
        )
    for table in DEPTH_TABLES:
        for row_id, depth in connection.execute(sa.text(f"SELECT id, depth FROM {table} WHERE depth LIKE '%sayings%'")).all():
            found = loaded(depth)
            if isinstance(found, dict):
                connection.execute(sa.text(f"UPDATE {table} SET depth = :depth WHERE id = :id"), {"depth": json.dumps(labelled_sayings(found)), "id": row_id})
    for epoch, world_id, data in connection.execute(sa.text("SELECT epoch, world_id, data FROM map_snapshots")).all():
        connection.execute(
            sa.text("UPDATE map_snapshots SET data = :data WHERE epoch = :epoch AND world_id = :world_id"),
            {"data": json.dumps(kept_snapshot(loaded(data))), "epoch": epoch, "world_id": world_id},
        )


def downgrade() -> None:
    pass
