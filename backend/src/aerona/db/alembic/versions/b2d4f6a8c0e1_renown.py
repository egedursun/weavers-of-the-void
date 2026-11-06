import sqlalchemy as sa
from alembic import op

revision = "b2d4f6a8c0e1"
down_revision = "a1c3e5f7b9d2"
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
)

SKILLS = (
    "blade",
    "spear",
    "axe",
    "blunt",
    "bow",
    "sling",
    "throwing",
    "shield",
    "unarmed",
    "riding",
    "mounted_combat",
    "siegecraft",
    "naval_combat",
    "beast_handling",
    "tactics",
    "strategy",
    "logistics",
    "leadership",
    "intimidation",
    "oratory",
    "negotiation",
    "intrigue",
    "etiquette",
    "deception",
    "teaching",
    "smithing",
    "carpentry",
    "masonry",
    "weaving",
    "pottery",
    "jewelling",
    "shipwright",
    "engineering",
    "alchemy",
    "lore",
    "medicine",
    "surgery",
    "astronomy",
    "law",
    "theology",
    "languages",
    "writing",
    "accounting",
    "hunting",
    "tracking",
    "foraging",
    "sailing",
    "navigation",
    "mountaineering",
    "swimming",
    "ritual",
    "prophecy",
    "spellcraft",
    "spirit_speaking",
)

AXES = (
    "heroism",
    "honour",
    "cruelty",
    "piety",
    "generosity",
    "wisdom",
    "trickery",
    "skill_renown",
    "troublemaker",
)

CLAIMS = (
    "true",
    "shared",
    "false",
)

STATUSES = (
    "standing",
    "verified",
    "exposed",
)

LORE = (
    "technique",
    "site",
    "map",
    "prophecy",
)

PRICES = (
    "wealth",
    "favour",
    "renown",
)


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def node_fk(table: str, column: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], ["nodes.id"], name=op.f(f"fk_{table}_{column}_nodes"), ondelete=ondelete)


def upgrade() -> None:
    op.create_table(
        "reputations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column("community_node_id", sa.Integer(), nullable=False),
        sa.Column("axis", enum(AXES, "axis"), nullable=False),
        sa.Column("skill", enum(SKILLS, "skill"), nullable=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("heard_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_reputations_value_range")),
        sa.CheckConstraint("heard_epoch >= 0", name=op.f("ck_reputations_heard_epoch_min")),
        node_fk("reputations", "subject_node_id", "CASCADE"),
        node_fk("reputations", "community_node_id", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reputations")),
        sa.UniqueConstraint("subject_node_id", "community_node_id", "axis", "skill", name="uq_reputations_subject_community_axis"),
    )
    with op.batch_alter_table("reputations", schema=None) as batch_op:
        batch_op.create_index("ix_reputations_community", ["community_node_id"], unique=False)
    op.create_table(
        "ruler_currencies",
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("piety", sa.Integer(), nullable=False),
        sa.Column("dread", sa.Integer(), nullable=False),
        sa.Column("tyranny", sa.Integer(), nullable=False),
        sa.Column("silenced_until", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_ruler_currencies_prestige_range")),
        sa.CheckConstraint("piety BETWEEN 0 AND 100", name=op.f("ck_ruler_currencies_piety_range")),
        sa.CheckConstraint("dread BETWEEN 0 AND 100", name=op.f("ck_ruler_currencies_dread_range")),
        sa.CheckConstraint("tyranny BETWEEN 0 AND 100", name=op.f("ck_ruler_currencies_tyranny_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_ruler_currencies_updated_epoch_min")),
        node_fk("ruler_currencies", "subject_node_id", "CASCADE"),
        sa.PrimaryKeyConstraint("subject_node_id", name=op.f("pk_ruler_currencies")),
    )
    op.create_table(
        "deeds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doer_node_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("act", enum(ACTS, "act"), nullable=True),
        sa.Column("axis", enum(AXES, "axis"), nullable=False),
        sa.Column("skill", enum(SKILLS, "skill"), nullable=True),
        sa.Column("place_node_id", sa.Integer(), nullable=True),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("witnesses", sa.Integer(), nullable=False),
        sa.Column("token", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("magnitude BETWEEN 0 AND 100", name=op.f("ck_deeds_magnitude_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_deeds_epoch_min")),
        node_fk("deeds", "doer_node_id", "CASCADE"),
        node_fk("deeds", "place_node_id", "SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_deeds_incident_id_incidents"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deeds")),
    )
    with op.batch_alter_table("deeds", schema=None) as batch_op:
        batch_op.create_index("ix_deeds_doer", ["doer_node_id"], unique=False)
        batch_op.create_index("ix_deeds_incident", ["incident_id"], unique=False)
    op.create_table(
        "deed_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deed_id", sa.Integer(), nullable=False),
        sa.Column("claimant_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(CLAIMS, "kind"), nullable=False),
        sa.Column("status", enum(STATUSES, "status"), nullable=False),
        sa.Column("credited", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("settled_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_deed_claims_epoch_min")),
        sa.ForeignKeyConstraint(["deed_id"], ["deeds.id"], name=op.f("fk_deed_claims_deed_id_deeds"), ondelete="CASCADE"),
        node_fk("deed_claims", "claimant_node_id", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deed_claims")),
        sa.UniqueConstraint("deed_id", "claimant_node_id", name="uq_deed_claims_deed_claimant"),
    )
    with op.batch_alter_table("deed_claims", schema=None) as batch_op:
        batch_op.create_index("ix_deed_claims_claimant", ["claimant_node_id"], unique=False)
    op.create_table(
        "lore_trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_node_id", sa.Integer(), nullable=False),
        sa.Column("buyer_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(LORE, "kind"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("price", enum(PRICES, "price"), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_lore_trades_epoch_min")),
        sa.CheckConstraint("value >= 0", name=op.f("ck_lore_trades_value_min")),
        node_fk("lore_trades", "seller_node_id", "CASCADE"),
        node_fk("lore_trades", "buyer_node_id", "CASCADE"),
        node_fk("lore_trades", "subject_node_id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lore_trades")),
    )
    with op.batch_alter_table("lore_trades", schema=None) as batch_op:
        batch_op.create_index("ix_lore_trades_buyer", ["buyer_node_id"], unique=False)
        batch_op.create_index("ix_lore_trades_seller", ["seller_node_id"], unique=False)


def downgrade() -> None:
    for table, indexes in (
        ("lore_trades", ("ix_lore_trades_seller", "ix_lore_trades_buyer")),
        ("deed_claims", ("ix_deed_claims_claimant",)),
        ("deeds", ("ix_deeds_incident", "ix_deeds_doer")),
        ("ruler_currencies", ()),
        ("reputations", ("ix_reputations_community",)),
    ):
        if indexes:
            with op.batch_alter_table(table, schema=None) as batch_op:
                for index in indexes:
                    batch_op.drop_index(index)
        op.drop_table(table)
