from alembic import op

revision = "5d0b7e3a9c21"
down_revision = "3ca6d1cc6955"
branch_labels = None
depends_on = None

RENAMED = {"bone": "calcified_tissue", "great_bone": "great_beast_tissue", "godflesh": "divine_tissue", "salt": "halite"}
TEXT_COLUMNS = (
    ("item_profiles", "material"),
    ("vessel_profiles", "hull_material"),
    ("vessel_profiles", "fabric_material"),
    ("army_units", "material"),
    ("inspirations", "material"),
)

JSON_KEY_COLUMNS = (("region_environment", "mineral_layers"),)


def move(mapping: dict[str, str]) -> None:
    for was, now in mapping.items():
        for table, column in TEXT_COLUMNS:
            op.execute(f"UPDATE {table} SET {column} = '{now}' WHERE {column} = '{was}'")
        for table, column in JSON_KEY_COLUMNS:
            op.execute(f"UPDATE {table} SET {column} = replace({column}, '\"{was}\"', '\"{now}\"') WHERE {column} LIKE '%\"{was}\"%'")
        op.execute(f"UPDATE OR IGNORE preferences SET target = '{now}' WHERE kind = 'material' AND target = '{was}'")
        op.execute(f"DELETE FROM preferences WHERE kind = 'material' AND target = '{was}'")


def upgrade() -> None:
    move(RENAMED)


def downgrade() -> None:
    move({now: was for was, now in RENAMED.items()})
