import sqlalchemy as sa
from alembic import op

revision = "db8ecba2c2c1"
down_revision = "fbb6a76c09e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creature_anatomy",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("limbs", sa.Integer(), nullable=False),
        sa.Column("heads", sa.Integer(), nullable=False),
        sa.Column("wings", sa.Integer(), nullable=False),
        sa.Column("tails", sa.Integer(), nullable=False),
        sa.Column(
            "skin",
            sa.Enum(
                "flesh",
                "hide",
                "scale",
                "chitin",
                "feather",
                "bone",
                "wood",
                "stone",
                "crystal",
                "metal",
                "ice",
                "fire",
                "steam",
                "void_stuff",
                name="skin",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "bone",
            sa.Enum(
                "flesh",
                "hide",
                "scale",
                "chitin",
                "feather",
                "bone",
                "wood",
                "stone",
                "crystal",
                "metal",
                "ice",
                "fire",
                "steam",
                "void_stuff",
                name="bone",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "breath", sa.Enum("fire", "frost", "venom_gas", "web", "steam", name="breath", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column(
            "bite",
            sa.Enum(
                "snake_venom",
                "drink_dependence",
                "drug_dependence",
                "lycanthropy",
                "vampirism",
                "divine_blessing",
                "void_taint",
                "possession",
                "trauma",
                "hunger_curse",
                name="bite",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("gaze", sa.Enum("terror", "petrify", "sleep", "madness", name="gaze", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column(
            "temperament",
            sa.Enum("placid", "skittish", "curious", "fierce", "cunning", "abductor", name="temperament", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "hoards",
            sa.Enum(
                "wood",
                "bone",
                "hide",
                "leather",
                "cloth",
                "stone",
                "flint",
                "obsidian",
                "copper",
                "tin",
                "bronze",
                "iron",
                "steel",
                "silver",
                "gold",
                "glass",
                "crystal",
                "ivory",
                "chitin",
                "dragonbone",
                "star_metal",
                "void_glass",
                "godflesh",
                "living_wood",
                "salt",
                "amber",
                "lead",
                "skysteel",
                "sulfur",
                "clay",
                "gems",
                name="hoards",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "hates", sa.Enum("fire", "iron", "noise", "water", "holy_ground", name="hates", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("awakening", sa.Enum("deep_mining", "desecration", name="awakening", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column(
            "habitat", sa.Enum("land", "water", "sky", "deep", "void", name="habitat", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("generated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("heads >= 1", name=op.f("ck_creature_anatomy_heads_min")),
        sa.CheckConstraint("limbs >= 0", name=op.f("ck_creature_anatomy_limbs_min")),
        sa.CheckConstraint("tails >= 0", name=op.f("ck_creature_anatomy_tails_min")),
        sa.CheckConstraint("wings >= 0", name=op.f("ck_creature_anatomy_wings_min")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_creature_anatomy_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_creature_anatomy")),
    )


def downgrade() -> None:
    op.drop_table("creature_anatomy")
