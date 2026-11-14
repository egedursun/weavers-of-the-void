import sqlalchemy as sa
from alembic import op

revision = "a75b504d83b5"
down_revision = "a7d2e9c4b1f6"
branch_labels = None
depends_on = None

UNITS_BEFORE = (
    "levy",
    "line_infantry",
    "heavy_infantry",
    "shield_infantry",
    "pike_infantry",
    "light_infantry",
    "shock_infantry",
    "guard_infantry",
    "marines",
    "slingers",
    "archers",
    "crossbowmen",
    "javelineers",
    "gunners",
    "grenadiers",
    "light_cavalry",
    "heavy_cavalry",
    "mounted_archers",
    "mounted_gunners",
    "beast_riders",
    "sky_riders",
    "chariots",
    "vehicle_crew",
    "siege_crew",
    "artillery_crew",
    "naval_crew",
    "sky_crew",
    "void_crew",
    "war_beasts",
    "bound_beasts",
    "sappers",
    "engineers",
    "battle_casters",
    "support_casters",
    "summoners",
    "constructs",
    "summoned_host",
    "mechanised_infantry",
    "special_forces",
    "partisans",
    "peacekeepers",
    "medics",
    "drone_operators",
    "signals_troops",
    "powered_troopers",
    "drop_troops",
    "pilots",
)
CREWS_BEFORE = (
    "gunners",
    "topmen",
    "marines",
    "officers",
    "rowers",
)
RENAMES = (("crossbowmen", "crossbow_infantry", UNITS_BEFORE), ("topmen", "riggers", CREWS_BEFORE))
COLUMNS = (
    ("army_units", "kind", "kind", "crossbowmen"),
    ("unit_designs", "base_kind", "base_kind", "crossbowmen"),
    ("battle_stacks", "kind", "kind", "crossbowmen"),
    ("ship_crews", "station", "station", "topmen"),
)


def kinds(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def switch(forward: bool) -> None:
    for old, new, before in RENAMES:
        after = tuple(new if value == old else value for value in before)
        start, end = (before, after) if forward else (after, before)
        source, target = (old, new) if forward else (new, old)
        both = (*start, target)
        for table, column, name, renamed in COLUMNS:
            if renamed != old:
                continue
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.alter_column(column, existing_type=kinds(start, name), type_=kinds(both, name), existing_nullable=False)
            op.execute(sa.text(f"UPDATE {table} SET {column} = :target WHERE {column} = :source").bindparams(source=source, target=target))
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.alter_column(column, existing_type=kinds(both, name), type_=kinds(end, name), existing_nullable=False)
        op.execute(
            sa.text("UPDATE army_templates SET composition = REPLACE(composition, :source, :target)").bindparams(source=f'"{source}"', target=f'"{target}"')
        )


def upgrade() -> None:
    switch(True)


def downgrade() -> None:
    switch(False)
