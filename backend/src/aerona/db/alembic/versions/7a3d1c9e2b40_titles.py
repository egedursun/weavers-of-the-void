import sqlalchemy as sa
from alembic import op

revision = "7a3d1c9e2b40"
down_revision = "5c2e8a1f9d47"
branch_labels = None
depends_on = None

TYPES = (
    "region",
    "place",
    "resource",
    "settlement",
    "species",
    "people",
    "mortal",
    "item",
    "structure",
    "language",
    "legend",
    "tradition",
    "cult",
    "faction",
    "celestial",
    "artwork",
    "law",
    "spirit",
    "knowledge",
    "prophecy",
    "event",
    "vessel",
    "outer_being",
    "army",
    "natural_law",
    "trade_route",
    "disease",
    "polity",
    "house",
    "treaty",
    "ideology",
    "rite",
    "beast",
)
BASES = ("inheritance", "marriage", "conquest", "divine", "fabricated")
FACTIONS = (
    "merchant_guild",
    "craft_guild",
    "priesthood",
    "warrior_order",
    "noble_council",
    "peasant_league",
    "rebels",
    "bandits",
    "pirates",
    "assassins",
    "scholars_academy",
    "secret_society",
    "mercenary_company",
    "interworld_federation",
    "wandering_market",
    "void_pirates",
    "social_circle",
    "mage_order",
)
WIDENED = (
    ("faction_profiles", "kind", FACTIONS, (*FACTIONS, "estate", "party", "movement", "chartered_company", "holy_order"), False),
    ("entities", "entity_type", TYPES, (*TYPES, "title"), False),
    ("son_powers", "param_entity_type", TYPES, (*TYPES, "title"), True),
    ("claims", "basis", BASES, (*BASES, "de_jure"), False),
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
    op.create_table(
        "de_jure_links",
        sa.Column("title_entity_id", sa.Integer(), nullable=False),
        sa.Column("member_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_de_jure_links_since_epoch_min")),
        sa.ForeignKeyConstraint(["member_entity_id"], ["entities.id"], name=op.f("fk_de_jure_links_member_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["title_entity_id"], ["entities.id"], name=op.f("fk_de_jure_links_title_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_entity_id", "member_entity_id", name=op.f("pk_de_jure_links")),
    )
    with op.batch_alter_table("de_jure_links", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_de_jure_links_member_entity_id"), ["member_entity_id"], unique=False)

    op.create_table(
        "title_holders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "tenure",
            sa.Enum("founded", "inherited", "created", "usurped", "granted", "restored", name="tenure", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_title_holders_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_title_holders_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["title_entity_id"], ["entities.id"], name=op.f("fk_title_holders_title_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_title_holders")),
    )
    with op.batch_alter_table("title_holders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_title_holders_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index("ix_title_holders_title", ["title_entity_id"], unique=False)

    op.create_table(
        "title_profiles",
        sa.Column("title_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "rank",
            sa.Enum(
                "lordship",
                "county",
                "duchy",
                "kingdom",
                "empire",
                "see",
                "archsee",
                "high_seat",
                "captaincy",
                "guildmastership",
                name="rank",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("de_jure_liege_entity_id", sa.Integer(), nullable=True),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("succession_law_entity_id", sa.Integer(), nullable=True),
        sa.Column("capital_entity_id", sa.Integer(), nullable=True),
        sa.Column("emblem", sa.String(length=120), nullable=True),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("regalia", sa.JSON(), nullable=False),
        sa.Column("drift", sa.JSON(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("destroyed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_title_profiles_created_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_title_profiles_prestige_range")),
        sa.ForeignKeyConstraint(["capital_entity_id"], ["entities.id"], name=op.f("fk_title_profiles_capital_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["de_jure_liege_entity_id"], ["entities.id"], name=op.f("fk_title_profiles_de_jure_liege_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_title_profiles_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_title_profiles_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["succession_law_entity_id"], ["entities.id"], name=op.f("fk_title_profiles_succession_law_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["title_entity_id"], ["entities.id"], name=op.f("fk_title_profiles_title_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_entity_id", name=op.f("pk_title_profiles")),
    )
    with op.batch_alter_table("title_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_title_profiles_de_jure_liege_entity_id"), ["de_jure_liege_entity_id"], unique=False)
        batch_op.create_index("ix_title_profiles_holder", ["holder_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_title_profiles_polity_entity_id"), ["polity_entity_id"], unique=False)

    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.add_column(sa.Column("title_entity_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_claims_title_entity_id"), ["title_entity_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_claims_title_entity_id_entities"), "entities", ["title_entity_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "company_profiles",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("route_entity_id", sa.Integer(), nullable=True),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "commodity",
            sa.Enum(
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("dividend_pct", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("chartered_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("chartered_epoch >= 0", name=op.f("ck_company_profiles_chartered_epoch_min")),
        sa.CheckConstraint("dividend_pct BETWEEN 0 AND 100", name=op.f("ck_company_profiles_dividend_pct_range")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_company_profiles_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_company_profiles_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_company_profiles_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_company_profiles_route_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_company_profiles")),
    )
    with op.batch_alter_table("company_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_company_profiles_polity_entity_id"), ["polity_entity_id"], unique=False)
    op.create_table(
        "company_shares",
        sa.Column("company_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_company_shares_share_range")),
        sa.ForeignKeyConstraint(["company_entity_id"], ["entities.id"], name=op.f("fk_company_shares_company_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_company_shares_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("company_entity_id", "holder_node_id", name=op.f("pk_company_shares")),
    )
    with op.batch_alter_table("company_shares", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_company_shares_holder_node_id"), ["holder_node_id"], unique=False)
    op.create_table(
        "estate_privileges",
        sa.Column("estate_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "privilege",
            sa.Enum(
                "tax_exemption", "monopoly", "council_seat", "arms", "judicial_immunity", name="privilege", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("granted_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("granted_epoch >= 0", name=op.f("ck_estate_privileges_granted_epoch_min")),
        sa.ForeignKeyConstraint(["estate_entity_id"], ["entities.id"], name=op.f("fk_estate_privileges_estate_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("estate_entity_id", "privilege", name=op.f("pk_estate_privileges")),
    )
    op.create_table(
        "estate_profiles",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "social_class",
            sa.Enum(
                "farmer",
                "artisan",
                "merchant",
                "priest",
                "warrior",
                "scribe",
                "noble",
                "serf_or_slave",
                "outcast",
                "monastic",
                name="social_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("influence", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("influence BETWEEN 0 AND 100", name=op.f("ck_estate_profiles_influence_range")),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_estate_profiles_loyalty_range")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_estate_profiles_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_estate_profiles_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_estate_profiles")),
    )
    with op.batch_alter_table("estate_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_estate_profiles_polity", ["polity_entity_id"], unique=False)
    op.create_table(
        "guild_secrets",
        sa.Column("guild_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "technique",
            sa.Enum(
                "phalanx_drill",
                "horse_archery",
                "siegecraft",
                "fortification",
                "logistics",
                "herbalism",
                "surgery",
                "amputation",
                "prosthetics",
                "quarantine",
                "inoculation",
                "irrigation",
                "crop_rotation",
                "terracing",
                "plough",
                "selective_breeding",
                "bronze",
                "iron",
                "steel",
                "skysteel",
                "arch",
                "dome",
                "aqueduct",
                "fortress",
                "alphabet",
                "paper",
                "printing",
                "cryptography",
                "calendar",
                "navigation_stars",
                "eclipse_prediction",
                "sailing",
                "shipwrighting",
                "coinage",
                "banking",
                "warding",
                "summoning",
                "sky_sailing",
                "necromancy",
                "alchemy",
                "astronomy_instruments",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_guild_secrets_since_epoch_min")),
        sa.ForeignKeyConstraint(["guild_entity_id"], ["entities.id"], name=op.f("fk_guild_secrets_guild_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("guild_entity_id", "technique", name=op.f("pk_guild_secrets")),
    )
    op.create_table(
        "holy_order_profiles",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("fortress_entity_id", sa.Integer(), nullable=True),
        sa.Column("tithe_share", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("tithe_share BETWEEN 0 AND 100", name=op.f("ck_holy_order_profiles_tithe_share_range")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_holy_order_profiles_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_holy_order_profiles_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fortress_entity_id"], ["entities.id"], name=op.f("fk_holy_order_profiles_fortress_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_holy_order_profiles")),
    )
    with op.batch_alter_table("holy_order_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_holy_order_profiles_cult_entity_id"), ["cult_entity_id"], unique=False)
    op.create_table(
        "movement_profiles",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum("abolition", "independence", "revival", "land_reform", "franchise", name="cause", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("support", sa.Integer(), nullable=False),
        sa.Column("is_party", sa.Boolean(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("support BETWEEN 0 AND 100", name=op.f("ck_movement_profiles_support_range")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_movement_profiles_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_movement_profiles_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_movement_profiles_target_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_movement_profiles")),
    )
    with op.batch_alter_table("movement_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_movement_profiles_polity", ["polity_entity_id"], unique=False)
    op.create_table(
        "movement_support",
        sa.Column("movement_entity_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_movement_support_share_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_movement_support_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["movement_entity_id"], ["entities.id"], name=op.f("fk_movement_support_movement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movement_entity_id", "community_entity_id", name=op.f("pk_movement_support")),
    )
    with op.batch_alter_table("movement_support", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_movement_support_community_entity_id"), ["community_entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("movement_support", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_movement_support_community_entity_id"))
    op.drop_table("movement_support")
    with op.batch_alter_table("movement_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_movement_profiles_polity")
    op.drop_table("movement_profiles")
    with op.batch_alter_table("holy_order_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_holy_order_profiles_cult_entity_id"))
    op.drop_table("holy_order_profiles")
    op.drop_table("guild_secrets")
    with op.batch_alter_table("estate_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_estate_profiles_polity")
    op.drop_table("estate_profiles")
    op.drop_table("estate_privileges")
    with op.batch_alter_table("company_shares", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_company_shares_holder_node_id"))
    op.drop_table("company_shares")
    with op.batch_alter_table("company_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_company_profiles_polity_entity_id"))
    op.drop_table("company_profiles")
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_claims_title_entity_id_entities"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_claims_title_entity_id"))
        batch_op.drop_column("title_entity_id")

    with op.batch_alter_table("title_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_title_profiles_polity_entity_id"))
        batch_op.drop_index("ix_title_profiles_holder")
        batch_op.drop_index(batch_op.f("ix_title_profiles_de_jure_liege_entity_id"))

    op.drop_table("title_profiles")
    with op.batch_alter_table("title_holders", schema=None) as batch_op:
        batch_op.drop_index("ix_title_holders_title")
        batch_op.drop_index(batch_op.f("ix_title_holders_holder_node_id"))

    op.drop_table("title_holders")
    with op.batch_alter_table("de_jure_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_de_jure_links_member_entity_id"))

    op.drop_table("de_jure_links")
    widen(False)
