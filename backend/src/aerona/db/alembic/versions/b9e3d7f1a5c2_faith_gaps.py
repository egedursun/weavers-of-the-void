import sqlalchemy as sa
from alembic import op

revision = "b9e3d7f1a5c2"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None

OLD_RITES = ("burial", "burning", "exposure", "none")
NEW_RITES = ("burial", "burning", "exposure", "nameless", "none")
OLD_EFFECTS = (
    "damage",
    "heal",
    "weather_change",
    "curse",
    "bless",
    "ward",
    "scry",
    "bind",
    "summon",
    "raise_dead",
    "fertility",
    "harvest_blessing",
)
NEW_EFFECTS = (*OLD_EFFECTS, "seal_soul", "unseal_soul", "exorcise")
WIDENED = (
    ("spirit_profiles", "rite", OLD_RITES, NEW_RITES, False),
    ("soul_judgements", "rite", OLD_RITES, NEW_RITES, False),
    ("rite_effects", "effect", OLD_EFFECTS, NEW_EFFECTS, False),
    ("item_enchantments", "effect", OLD_EFFECTS, NEW_EFFECTS, False),
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rebirth_path", enum_of("rebirth_path", ("people", "house", "merit")), nullable=False, server_default="people"))
    with op.batch_alter_table("cult_offices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("cult_tenets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=200), nullable=True))
    with op.batch_alter_table("heresies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("relics", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("spirit_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("seal_strength", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_check_constraint(op.f("ck_spirit_profiles_seal_strength_range"), "seal_strength BETWEEN 0 AND 100")
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.add_column(sa.Column("closed", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("possessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("host_values", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("funeral_rite", enum_of("funeral_rite", NEW_RITES), nullable=True))
    for table, column in (
        ("cult_doctrines", "rebirth_path"),
        ("cult_offices", "locked"),
        ("heresies", "locked"),
        ("relics", "locked"),
        ("spirit_profiles", "seal_strength"),
        ("afterlife_strata", "closed"),
        ("possessions", "host_values"),
        ("possessions", "locked"),
    ):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.drop_column("funeral_rite")
    with op.batch_alter_table("possessions", schema=None) as batch_op:
        batch_op.drop_column("locked")
        batch_op.drop_column("host_values")
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.drop_column("closed")
    with op.batch_alter_table("spirit_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_spirit_profiles_seal_strength_range"), type_="check")
        batch_op.drop_column("seal_strength")
    with op.batch_alter_table("relics", schema=None) as batch_op:
        batch_op.drop_column("locked")
    with op.batch_alter_table("heresies", schema=None) as batch_op:
        batch_op.drop_column("locked")
    with op.batch_alter_table("cult_tenets", schema=None) as batch_op:
        batch_op.drop_column("name")
    with op.batch_alter_table("cult_offices", schema=None) as batch_op:
        batch_op.drop_column("locked")
    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.drop_column("rebirth_path")
    widen(False)
