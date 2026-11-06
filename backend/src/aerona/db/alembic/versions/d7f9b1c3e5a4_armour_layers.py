import sqlalchemy as sa
from alembic import op

revision = "d7f9b1c3e5a4"
down_revision = "c6e8a0b2d4f3"
branch_labels = None
depends_on = None

OLD_CLASSES = (
    "blade",
    "longblade",
    "axe",
    "spear",
    "polearm",
    "mace",
    "bow",
    "crossbow",
    "sling",
    "throwing",
    "staff",
    "armour",
    "shield",
    "helmet",
    "crown",
    "sceptre",
    "seal",
    "ring",
    "standard",
    "holy_relic",
    "idol",
    "prayer_book",
    "book",
    "scroll",
    "map",
    "astrolabe",
    "tool",
    "instrument",
    "mirror",
    "vessel_object",
    "prosthesis",
    "key",
    "jewel",
    "currency",
)
NEW_CLASSES = (*OLD_CLASSES, "padding", "cloak")


def classes(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.alter_column(
            "item_class",
            existing_type=sa.Enum(*old, name="item_class", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name="item_class", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    classes(OLD_CLASSES, NEW_CLASSES)
    with op.batch_alter_table("mortal_equipment", schema=None) as batch_op:
        batch_op.add_column(sa.Column("armour_under_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("armour_cover_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(op.f("fk_mortal_equipment_armour_under_id_entities"), "entities", ["armour_under_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(op.f("fk_mortal_equipment_armour_cover_id_entities"), "entities", ["armour_cover_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("mortal_equipment", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_mortal_equipment_armour_cover_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(op.f("fk_mortal_equipment_armour_under_id_entities"), type_="foreignkey")
        batch_op.drop_column("armour_cover_id")
        batch_op.drop_column("armour_under_id")
    classes(NEW_CLASSES, OLD_CLASSES)
