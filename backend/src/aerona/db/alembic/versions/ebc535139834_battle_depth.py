import sqlalchemy as sa
from alembic import op

revision = "ebc535139834"
down_revision = "e5f9b3a7c2d1"
branch_labels = None
depends_on = None


OLD_TACTICS = (
    "hold_line",
    "frontal_assault",
    "double_envelopment",
    "feigned_retreat",
    "flank_cavalry",
    "missile_attrition",
    "shield_wall",
    "wedge",
    "night_raid",
    "ambush",
    "skirmish_harass",
    "river_defence",
    "siege_assault",
)
NEW_TACTICS = (*OLD_TACTICS, "feint")
TACTIC_COLUMNS = (
    ("army_profiles", "tactic", True),
    ("learned_tactics", "tactic", False),
    ("battles", "tactics_attacker", True),
    ("battles", "tactics_defender", True),
)


def tactics(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    for table, column, nullable in TACTIC_COLUMNS:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*old, name=column, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*new, name=column, native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    tactics(OLD_TACTICS, NEW_TACTICS)
    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contact_seasons", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organisation", sa.Integer(), nullable=False, server_default="100"))
        batch_op.add_column(sa.Column("discipline", sa.Integer(), nullable=False, server_default="30"))
        batch_op.add_column(sa.Column("ammunition", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column(
                "morale_state",
                sa.Enum(
                    "steady", "shaken", "wavering", "routing", "broken", "rallied", name="morale_state", native_enum=False, create_constraint=True, length=40
                ),
                nullable=False,
                server_default="steady",
            )
        )
        batch_op.add_column(
            sa.Column(
                "formation",
                sa.Enum("line", "column", "wedge", "square", "loose", "shieldwall", name="formation", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="line",
            )
        )
        batch_op.add_column(sa.Column("missing", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("battle_stacks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("killed", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("walking", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("stretcher", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("captured", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("missing", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("deserted", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("reserve", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("organisation", sa.Integer(), nullable=False, server_default="100"))
        batch_op.add_column(sa.Column("ammunition_spent", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column(
                "formation",
                sa.Enum("line", "column", "wedge", "square", "loose", "shieldwall", name="formation", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "morale_state",
                sa.Enum(
                    "steady", "shaken", "wavering", "routing", "broken", "rallied", name="morale_state", native_enum=False, create_constraint=True, length=40
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("target_class", sa.Enum("soft", "hard", name="target_class", native_enum=False, create_constraint=True, length=40), nullable=True)
        )

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("width", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("reserves_committed", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("command_collapsed_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("planned_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("trap_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("feint", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("salvaged", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key(batch_op.f("fk_battles_planned_entity_id_entities"), "entities", ["planned_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_battles_trap_entity_id_entities"), "entities", ["trap_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(
            batch_op.f("fk_battles_command_collapsed_entity_id_entities"), "entities", ["command_collapsed_entity_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("unit_designs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reach", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("volleys", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("accuracy", sa.Integer(), nullable=False, server_default="40"))
        batch_op.add_column(sa.Column("piercing", sa.Integer(), nullable=False, server_default="20"))

    op.execute("UPDATE army_units SET discipline = 20, ammunition = 0, formation = 'line' WHERE kind = 'levy'")
    op.execute("UPDATE army_units SET discipline = 40, ammunition = 0, formation = 'line' WHERE kind = 'spearmen'")
    op.execute("UPDATE army_units SET discipline = 60, ammunition = 0, formation = 'line' WHERE kind = 'heavy_infantry'")
    op.execute("UPDATE army_units SET discipline = 65, ammunition = 0, formation = 'shieldwall' WHERE kind = 'shield_wall'")
    op.execute("UPDATE army_units SET discipline = 60, ammunition = 0, formation = 'square' WHERE kind = 'pikemen'")
    op.execute("UPDATE army_units SET discipline = 35, ammunition = 9, formation = 'loose' WHERE kind = 'skirmishers'")
    op.execute("UPDATE army_units SET discipline = 25, ammunition = 0, formation = 'line' WHERE kind = 'berserkers'")
    op.execute("UPDATE army_units SET discipline = 70, ammunition = 0, formation = 'line' WHERE kind = 'temple_guard'")
    op.execute("UPDATE army_units SET discipline = 30, ammunition = 9, formation = 'loose' WHERE kind = 'slingers'")
    op.execute("UPDATE army_units SET discipline = 45, ammunition = 9, formation = 'loose' WHERE kind = 'archers'")
    op.execute("UPDATE army_units SET discipline = 50, ammunition = 9, formation = 'loose' WHERE kind = 'crossbowmen'")
    op.execute("UPDATE army_units SET discipline = 50, ammunition = 9, formation = 'wedge' WHERE kind = 'horse_archers'")
    op.execute("UPDATE army_units SET discipline = 35, ammunition = 9, formation = 'loose' WHERE kind = 'javelineers'")
    op.execute("UPDATE army_units SET discipline = 45, ammunition = 9, formation = 'wedge' WHERE kind = 'light_cavalry'")
    op.execute("UPDATE army_units SET discipline = 65, ammunition = 0, formation = 'wedge' WHERE kind = 'heavy_cavalry'")
    op.execute("UPDATE army_units SET discipline = 40, ammunition = 9, formation = 'wedge' WHERE kind = 'beast_riders'")
    op.execute("UPDATE army_units SET discipline = 45, ammunition = 9, formation = 'wedge' WHERE kind = 'chariots'")
    op.execute("UPDATE army_units SET discipline = 15, ammunition = 0, formation = 'wedge' WHERE kind = 'war_beasts'")
    op.execute("UPDATE army_units SET discipline = 30, ammunition = 0, formation = 'wedge' WHERE kind = 'bound_beasts'")
    op.execute("UPDATE army_units SET discipline = 50, ammunition = 9, formation = 'wedge' WHERE kind = 'sky_mounts'")
    op.execute("UPDATE army_units SET discipline = 45, ammunition = 0, formation = 'loose' WHERE kind = 'sappers'")
    op.execute("UPDATE army_units SET discipline = 50, ammunition = 9, formation = 'loose' WHERE kind = 'siege_engines'")
    op.execute("UPDATE army_units SET discipline = 55, ammunition = 9, formation = 'loose' WHERE kind = 'war_mages'")
    op.execute("UPDATE army_units SET discipline = 55, ammunition = 9, formation = 'loose' WHERE kind = 'priests'")
    op.execute("UPDATE army_units SET discipline = 50, ammunition = 9, formation = 'loose' WHERE kind = 'necromancers'")
    op.execute("UPDATE army_units SET discipline = 45, ammunition = 9, formation = 'line' WHERE kind = 'galleys'")
    op.execute("UPDATE army_units SET discipline = 50, ammunition = 9, formation = 'line' WHERE kind = 'longships'")
    op.execute("UPDATE army_units SET discipline = 60, ammunition = 9, formation = 'line' WHERE kind = 'warships'")
    op.execute("UPDATE army_units SET discipline = 40, ammunition = 0, formation = 'line' WHERE kind = 'fire_ships'")
    op.execute("UPDATE army_units SET discipline = 60, ammunition = 9, formation = 'line' WHERE kind = 'skyships'")
    op.execute("UPDATE army_units SET discipline = 95, ammunition = 0, formation = 'line' WHERE kind = 'golems'")
    op.execute("UPDATE army_units SET discipline = 20, ammunition = 9, formation = 'line' WHERE kind = 'void_spawn'")
    op.execute("UPDATE army_units SET discipline = 80, ammunition = 0, formation = 'line' WHERE kind = 'ghost_host'")


def downgrade() -> None:
    tactics(NEW_TACTICS, OLD_TACTICS)
    with op.batch_alter_table("unit_designs", schema=None) as batch_op:
        batch_op.drop_column("piercing")
        batch_op.drop_column("accuracy")
        batch_op.drop_column("volleys")
        batch_op.drop_column("reach")

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_battles_command_collapsed_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_battles_trap_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_battles_planned_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("salvaged")
        batch_op.drop_column("feint")
        batch_op.drop_column("trap_entity_id")
        batch_op.drop_column("planned_entity_id")
        batch_op.drop_column("command_collapsed_entity_id")
        batch_op.drop_column("reserves_committed")
        batch_op.drop_column("width")

    with op.batch_alter_table("battle_stacks", schema=None) as batch_op:
        batch_op.drop_column("target_class")
        batch_op.drop_column("morale_state")
        batch_op.drop_column("formation")
        batch_op.drop_column("ammunition_spent")
        batch_op.drop_column("organisation")
        batch_op.drop_column("reserve")
        batch_op.drop_column("deserted")
        batch_op.drop_column("missing")
        batch_op.drop_column("captured")
        batch_op.drop_column("stretcher")
        batch_op.drop_column("walking")
        batch_op.drop_column("killed")

    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.drop_column("missing")
        batch_op.drop_column("formation")
        batch_op.drop_column("morale_state")
        batch_op.drop_column("ammunition")
        batch_op.drop_column("discipline")
        batch_op.drop_column("organisation")

    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.drop_column("contact_seasons")
