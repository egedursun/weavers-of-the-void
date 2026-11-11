import sqlalchemy as sa
from alembic import op

revision = "3b8e1f4c7d20"
down_revision = "7a3c9e5d2b41"
branch_labels = None
depends_on = None

ACTS = (
    "execution",
    "mutilation",
    "betrayal",
    "mercy_to_enemy",
    "human_sacrifice",
    "trade_with_outsiders",
    "building_temples",
    "burning_books",
    "conquest",
    "raiding",
    "duelling",
    "ransom",
    "taking_captives",
    "oathbreaking",
    "learning",
    "hospitality",
    "winter_fighting",
    "guest_killing",
    "ritual_scarring",
    "killing_kin",
    "killing_outsider",
    "killing_in_war",
    "killing_captive",
    "regicide",
    "duel_to_death",
    "revenge_killing",
    "theft",
    "treason",
    "cowardice",
    "desecration",
    "bribery",
    "suicide",
    "torture",
    "eating_sapients",
    "iconoclasm",
    "conversion_by_force",
    "polygamy",
    "incest",
    "magic_use",
    "blood_magic",
    "void_magic",
    "necromancy",
    "hoarding_in_famine",
    "slavery",
    "adultery",
    "usury",
    "infanticide",
    "abandoning_elders",
)
LEGACIES = ("martial_style", "aesthetic", "funeral_rite", "belief", "value")
WIDENED = (
    ("culture_ethics", "act", ACTS, (*ACTS, "forced_labour"), False),
    ("deeds", "act", ACTS, (*ACTS, "forced_labour"), True),
    ("tradition_profiles", "taboo_act", ACTS, (*ACTS, "forced_labour"), True),
    ("creator_taboos", "act", ACTS, (*ACTS, "forced_labour"), False),
    ("geasa", "act", ACTS, (*ACTS, "forced_labour"), False),
    ("legacy_traits", "kind", LEGACIES, (*LEGACIES, "innovation", "art_form"), False),
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
    with op.batch_alter_table("indentures", schema=None) as batch_op:
        batch_op.add_column(sa.Column("origin_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_indentures_origin_entity_id_entities"), "entities", ["origin_entity_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("manumissions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("standing", sa.Integer(), nullable=False, server_default="40"))
        batch_op.add_column(sa.Column("origin_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(batch_op.f("fk_manumissions_origin_entity_id_entities"), "entities", ["origin_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_check_constraint(op.f("ck_manumissions_standing_range"), "standing BETWEEN 0 AND 100")
    with op.batch_alter_table("manumissions", schema=None) as batch_op:
        batch_op.alter_column("standing", server_default=None)
        batch_op.alter_column("locked", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("manumissions", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_manumissions_standing_range"), type_="check")
        batch_op.drop_constraint(batch_op.f("fk_manumissions_origin_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("origin_entity_id")
        batch_op.drop_column("standing")
    with op.batch_alter_table("indentures", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_indentures_origin_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("origin_entity_id")
    widen(False)
