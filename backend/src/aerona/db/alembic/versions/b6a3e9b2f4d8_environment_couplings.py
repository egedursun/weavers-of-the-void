import sqlalchemy as sa
from alembic import op

revision = "b6a3e9b2f4d8"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None

OLD_TRADITION_KINDS = (
    "festival",
    "fast",
    "funeral_rite",
    "initiation",
    "marriage_rite",
    "coming_of_age",
    "taboo",
    "offering",
    "pilgrimage",
    "hospitality_law",
    "duel_custom",
    "mourning",
    "harvest_rite",
    "war_dance",
    "scar_rite",
    "ancestor_feast",
)
NEW_TRADITION_KINDS = (*OLD_TRADITION_KINDS, "siesta", "night_vigil")


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of("kind", OLD_TRADITION_KINDS), type_=enum_of("kind", NEW_TRADITION_KINDS), existing_nullable=False)
        batch_op.add_column(sa.Column("season_position", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("calendar_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("notable_year_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("in_season", sa.Boolean(), nullable=True))
        batch_op.create_check_constraint(batch_op.f("ck_tradition_profiles_season_position_min"), "season_position >= 0")
        batch_op.create_foreign_key(
            batch_op.f("fk_tradition_profiles_calendar_entity_id_entities"), "entities", ["calendar_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_tradition_profiles_notable_year_id_notable_years"), "notable_years", ["notable_year_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("settlement_infrastructure", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bridges", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("irrigation", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_check_constraint(batch_op.f("ck_settlement_infrastructure_bridges_range"), "bridges BETWEEN 0 AND 5")
        batch_op.create_check_constraint(batch_op.f("ck_settlement_infrastructure_irrigation_range"), "irrigation BETWEEN 0 AND 5")
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("calendar_locked", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("market_prices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("swing", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("outbreaks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("season_factor", sa.Integer(), nullable=False, server_default="100"))
        batch_op.create_check_constraint(batch_op.f("ck_outbreaks_season_factor_min"), "season_factor >= 0")
    op.create_table(
        "structure_ley",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("attuned", sa.Boolean(), nullable=False),
        sa.Column("on_ley_line", sa.Boolean(), nullable=False),
        sa.Column("at_nexus", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_structure_ley_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_structure_ley")),
    )


def downgrade() -> None:
    op.drop_table("structure_ley")
    with op.batch_alter_table("outbreaks", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_outbreaks_season_factor_min"), type_="check")
        batch_op.drop_column("season_factor")
    with op.batch_alter_table("market_prices", schema=None) as batch_op:
        batch_op.drop_column("swing")
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.drop_column("calendar_locked")
    with op.batch_alter_table("settlement_infrastructure", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_settlement_infrastructure_irrigation_range"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_settlement_infrastructure_bridges_range"), type_="check")
        batch_op.drop_column("irrigation")
        batch_op.drop_column("bridges")
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_tradition_profiles_notable_year_id_notable_years"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_tradition_profiles_calendar_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("ck_tradition_profiles_season_position_min"), type_="check")
        batch_op.drop_column("in_season")
        batch_op.drop_column("notable_year_id")
        batch_op.drop_column("calendar_entity_id")
        batch_op.drop_column("season_position")
        batch_op.alter_column("kind", existing_type=enum_of("kind", NEW_TRADITION_KINDS), type_=enum_of("kind", OLD_TRADITION_KINDS), existing_nullable=False)
