import sqlalchemy as sa
from alembic import op

revision = "a8c0e2f4b6d9"
down_revision = "b4d6f8a0c2e4"
branch_labels = None
depends_on = None

OLD_ROUTE_AIMS = (
    "conquer_region",
    "seize_settlement",
    "press_claim",
    "convert",
    "tribute",
    "vassalise",
    "liberate",
    "destroy_cult",
    "seize_resource",
    "seize_nexus",
    "humiliate",
    "revenge",
    "loot",
    "change_government",
)
NEW_ROUTE_AIMS = (*OLD_ROUTE_AIMS, "seize_route")
OLD_ROUTE_CLAUSES = (
    "call_to_arms",
    "tribute",
    "cession",
    "hostage",
    "marriage",
    "trade_rights",
    "tolls_waived",
    "religious_freedom",
    "demilitarised",
    "champion",
    "extradition",
    "wergild",
    "non_aggression",
)
NEW_ROUTE_CLAUSES = (*OLD_ROUTE_CLAUSES, "route_control", "resource_demand")
WIDENED = (
    ("war_aims", "kind", OLD_ROUTE_AIMS, NEW_ROUTE_AIMS, False),
    ("treaty_clauses", "kind", OLD_ROUTE_CLAUSES, NEW_ROUTE_CLAUSES, False),
)
DANGER_COLUMNS = ("danger_bandits", "danger_beasts", "danger_weather", "danger_sea")
COMMODITIES = (
    "grain",
    "livestock",
    "fish",
    "fodder",
    "timber",
    "fuel",
    "bread",
    "ore",
    "stone",
    "cloth",
    "tools",
    "weapons",
    "armour",
    "mounts",
    "siege_materiel",
    "medicine",
    "luxuries",
    "incense",
    "sacred_goods",
    "magical_reagents",
)
LOSSES = ("bandits", "sea", "beasts", "weather")


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    with op.batch_alter_table("trade_route_profiles", schema=None) as batch_op:
        for column in DANGER_COLUMNS:
            batch_op.add_column(sa.Column(column, sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("season_pct", sa.Integer(), nullable=False, server_default="100"))
        batch_op.add_column(sa.Column("chokepoint", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("closed_by_son_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(op.f("fk_trade_route_profiles_closed_by_son_id_sons"), "sons", ["closed_by_son_id"], ["id"], ondelete="SET NULL")
        for column in DANGER_COLUMNS:
            batch_op.create_check_constraint(op.f(f"ck_trade_route_profiles_{column}_range"), f"{column} BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_trade_route_profiles_season_pct_range"), "season_pct BETWEEN 0 AND 100")
    with op.batch_alter_table("trade_route_tolls", schema=None) as batch_op:
        batch_op.add_column(sa.Column("controller_held", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("polity_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(op.f("fk_trade_route_tolls_polity_entity_id_entities"), "entities", ["polity_entity_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "trade_route_losses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("commodity", enum_of("commodity", COMMODITIES), nullable=False),
        sa.Column("cause", enum_of("cause", LOSSES), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("culprit_entity_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("units >= 0", name=op.f("ck_trade_route_losses_units_min")),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_trade_route_losses_route_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["culprit_entity_id"], ["entities.id"], name=op.f("fk_trade_route_losses_culprit_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trade_route_losses")),
    )
    with op.batch_alter_table("trade_route_losses", schema=None) as batch_op:
        batch_op.create_index("ix_trade_route_losses_route", ["route_entity_id", "epoch"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("trade_route_losses", schema=None) as batch_op:
        batch_op.drop_index("ix_trade_route_losses_route")
    op.drop_table("trade_route_losses")
    with op.batch_alter_table("trade_route_tolls", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_trade_route_tolls_polity_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("polity_entity_id")
        batch_op.drop_column("controller_held")
    with op.batch_alter_table("trade_route_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_trade_route_profiles_season_pct_range"), type_="check")
        batch_op.drop_constraint(op.f("fk_trade_route_profiles_closed_by_son_id_sons"), type_="foreignkey")
        batch_op.drop_column("closed_by_son_id")
        for column in DANGER_COLUMNS:
            batch_op.drop_constraint(op.f(f"ck_trade_route_profiles_{column}_range"), type_="check")
        for column in ("locked", "chokepoint", "season_pct", *reversed(DANGER_COLUMNS)):
            batch_op.drop_column(column)
    widen(False)
