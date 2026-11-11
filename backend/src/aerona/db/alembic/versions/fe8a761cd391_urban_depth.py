import sqlalchemy as sa
from alembic import op

revision = "fe8a761cd391"
down_revision = "3ccb476b4bb5"
branch_labels = None
depends_on = None


NEW_STRUCTURES = ("firehouse", "bathhouse", "kontor", "covenant")
OLD_STRUCTURES = (
    "temple",
    "shrine",
    "monastery",
    "necropolis",
    "library",
    "school",
    "observatory",
    "academy",
    "hospital",
    "wall",
    "gate",
    "tower",
    "citadel",
    "watchtower",
    "fort",
    "palace",
    "court",
    "prison",
    "market",
    "harbour",
    "warehouse",
    "granary",
    "caravanserai",
    "bank",
    "forge",
    "mill",
    "tannery",
    "mine",
    "quarry",
    "shipyard",
    "workshop",
    "alchemist_lab",
    "road",
    "bridge",
    "aqueduct",
    "sewer",
    "canal",
    "irrigation",
    "dam",
    "monument",
    "tomb",
    "arena",
    "theatre",
    "wonder",
    "cosmic_gate",
    "cosmic_archive",
)
NEW_FACTIONS = ("crime_family", "thieves_guild", "smuggling_ring", "pirate_confederacy")
OLD_FACTIONS = (
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
    "estate",
    "party",
    "movement",
    "chartered_company",
    "holy_order",
)
OLD_MANDATES = ("produce", "export_ban", "build", "famine_relief", "curfew")
OLD_LAWS = (
    "succession_rule",
    "inheritance_split",
    "land_tenure",
    "slavery",
    "serfdom",
    "tax_rate",
    "tithe",
    "tolls",
    "debt_law",
    "penal_code",
    "levy_law",
    "conscription",
    "standing_army",
    "veteran_pension",
    "ransom_custom",
    "marriage_law",
    "sumptuary",
    "guild_charter",
    "foreigner_rights",
    "religious_tolerance",
    "worship_ban",
    "censorship",
    "blood_feud",
    "quarantine",
    "burial_law",
    "sanitation",
    "magic_ban",
    "licensed_magic",
    "rite_restrictions",
    "franchise",
    "constitution",
    "custom",
)

WIDENED = (
    ("structure_profiles", "kind", "structure_kind", OLD_STRUCTURES, (*OLD_STRUCTURES, *NEW_STRUCTURES), False),
    ("constructions", "kind", "structure_kind", OLD_STRUCTURES, (*OLD_STRUCTURES, *NEW_STRUCTURES), False),
    ("structure_designs", "base_kind", "base_kind", OLD_STRUCTURES, (*OLD_STRUCTURES, *NEW_STRUCTURES), False),
    ("faction_profiles", "kind", "kind", OLD_FACTIONS, (*OLD_FACTIONS, *NEW_FACTIONS), False),
    ("mandates", "kind", "kind", OLD_MANDATES, (*OLD_MANDATES, "slum_clearance"), False),
    ("law_profiles", "kind", "kind", OLD_LAWS, (*OLD_LAWS, "fair_market"), False),
    ("law_proposals", "kind", "kind", OLD_LAWS, (*OLD_LAWS, "fair_market"), False),
)


def widen(forward: bool) -> None:
    for table, column, name, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*before, name=name, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*after, name=name, native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    widen(True)
    op.create_table(
        "convoys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=True),
        sa.Column("route_entity_id", sa.Integer(), nullable=False),
        sa.Column("cargo", sa.JSON(), nullable=False),
        sa.Column(
            "preservation",
            sa.Enum("none", "salted", "iced", "magic", name="preservation", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("animals", sa.Integer(), nullable=False),
        sa.Column("vehicles", sa.Integer(), nullable=False),
        sa.Column("guards", sa.Integer(), nullable=False),
        sa.Column("passengers", sa.JSON(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("loading", "travelling", "delayed", "arrived", "raided", "lost", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("departed_epoch", sa.Integer(), nullable=False),
        sa.Column("arrived_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("animals >= 0", name=op.f("ck_convoys_animals_min")),
        sa.CheckConstraint("capacity >= 0", name=op.f("ck_convoys_capacity_min")),
        sa.CheckConstraint("departed_epoch >= 0", name=op.f("ck_convoys_departed_epoch_min")),
        sa.CheckConstraint("guards >= 0", name=op.f("ck_convoys_guards_min")),
        sa.CheckConstraint("vehicles >= 0", name=op.f("ck_convoys_vehicles_min")),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_convoys_owner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_convoys_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_entity_id"], ["entities.id"], name=op.f("fk_convoys_route_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_convoys")),
    )
    with op.batch_alter_table("convoys", schema=None) as batch_op:
        batch_op.create_index("ix_convoys_route", ["route_entity_id"], unique=False)

    op.create_table(
        "crime_payroll",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("official_entity_id", sa.Integer(), nullable=False),
        sa.Column("bribe", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bribe >= 0", name=op.f("ck_crime_payroll_bribe_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_crime_payroll_since_epoch_min")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_crime_payroll_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["official_entity_id"], ["entities.id"], name=op.f("fk_crime_payroll_official_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", "official_entity_id", name=op.f("pk_crime_payroll")),
    )
    op.create_table(
        "crime_stances",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("stance", sa.Enum("suppress", "co_opt", name="stance", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_crime_stances_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_crime_stances_strength_range")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_crime_stances_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_crime_stances_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "faction_entity_id", name=op.f("pk_crime_stances")),
    )
    op.create_table(
        "market_plays",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
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
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("play", sa.Enum("corner", "dump", name="play", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_market_plays_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_market_plays_strength_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_market_plays_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_market_plays_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "settlement_entity_id", "commodity", "play", name=op.f("pk_market_plays")),
    )
    with op.batch_alter_table("market_plays", schema=None) as batch_op:
        batch_op.create_index("ix_market_plays_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "order_laws",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "law",
            sa.Enum(
                "spare_members", "no_outer_dealings", "share_discoveries", "keep_secrecy", name="law", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_order_laws_strength_range")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_order_laws_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", "law", name=op.f("pk_order_laws")),
    )
    op.create_table(
        "order_tribunals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("accused_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "law",
            sa.Enum(
                "spare_members", "no_outer_dealings", "share_discoveries", "keep_secrecy", name="law", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "verdict",
            sa.Enum("acquitted", "fined", "expelled", "stripped", name="verdict", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("fine", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_order_tribunals_epoch_min")),
        sa.CheckConstraint("fine >= 0", name=op.f("ck_order_tribunals_fine_min")),
        sa.ForeignKeyConstraint(["accused_entity_id"], ["entities.id"], name=op.f("fk_order_tribunals_accused_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_order_tribunals_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_tribunals")),
    )
    with op.batch_alter_table("order_tribunals", schema=None) as batch_op:
        batch_op.create_index("ix_order_tribunals_faction", ["faction_entity_id"], unique=False)

    op.create_table(
        "rackets",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "racket",
            sa.Enum(
                "protection",
                "smuggling",
                "gambling",
                "fencing",
                "kidnapping",
                "counterfeiting",
                name="racket",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("income", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("income >= 0", name=op.f("ck_rackets_income_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_rackets_since_epoch_min")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_rackets_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_rackets_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", "settlement_entity_id", "racket", name=op.f("pk_rackets")),
    )
    with op.batch_alter_table("rackets", schema=None) as batch_op:
        batch_op.create_index("ix_rackets_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "trading_posts",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=True),
        sa.Column("host_settlement_id", sa.Integer(), nullable=False),
        sa.Column("informants", sa.Integer(), nullable=False),
        sa.Column("goods", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("goods >= 0", name=op.f("ck_trading_posts_goods_min")),
        sa.CheckConstraint("informants >= 0", name=op.f("ck_trading_posts_informants_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_trading_posts_since_epoch_min")),
        sa.ForeignKeyConstraint(["host_settlement_id"], ["entities.id"], name=op.f("fk_trading_posts_host_settlement_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_trading_posts_owner_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_trading_posts_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_trading_posts")),
    )
    with op.batch_alter_table("trading_posts", schema=None) as batch_op:
        batch_op.create_index("ix_trading_posts_owner", ["owner_entity_id"], unique=False)

    op.create_table(
        "transport_fleets",
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("pack_animals", "wagons", "river_boats", "ships", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("age >= 0", name=op.f("ck_transport_fleets_age_min")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_transport_fleets_condition_range")),
        sa.CheckConstraint("count >= 0", name=op.f("ck_transport_fleets_count_min")),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_transport_fleets_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("owner_entity_id", "kind", name=op.f("pk_transport_fleets")),
    )
    op.create_table(
        "district_services",
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column(
            "service",
            sa.Enum(
                "water", "faith", "watch", "healing", "market", "school", "bath", "fire", name="service", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("coverage", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("coverage BETWEEN 0 AND 100", name=op.f("ck_district_services_coverage_range")),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], name=op.f("fk_district_services_district_id_districts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("district_id", "service", name=op.f("pk_district_services")),
    )
    op.create_table(
        "turf",
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_turf_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_turf_strength_range")),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], name=op.f("fk_turf_district_id_districts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_turf_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("district_id", "faction_entity_id", name=op.f("pk_turf")),
    )
    with op.batch_alter_table("turf", schema=None) as batch_op:
        batch_op.create_index("ix_turf_faction", ["faction_entity_id"], unique=False)

    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "housing",
                sa.Enum("hut", "cottage", "house", "townhouse", "manor", name="housing", native_enum=False, create_constraint=True, length=40),
                server_default="house",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("desirability", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("land_value", sa.Integer(), server_default="50", nullable=False))

    with op.batch_alter_table("settlement_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "morphology",
                sa.Enum("organic", "planned", "concentric", name="morphology", native_enum=False, create_constraint=True, length=40),
                server_default="organic",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("homeless", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("district_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_structure_profiles_district_id_districts"), "districts", ["district_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_structure_profiles_district_id_districts"), type_="foreignkey")
        batch_op.drop_column("district_id")

    with op.batch_alter_table("settlement_profiles", schema=None) as batch_op:
        batch_op.drop_column("homeless")
        batch_op.drop_column("morphology")

    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.drop_column("land_value")
        batch_op.drop_column("desirability")
        batch_op.drop_column("housing")

    with op.batch_alter_table("turf", schema=None) as batch_op:
        batch_op.drop_index("ix_turf_faction")

    op.drop_table("turf")
    op.drop_table("district_services")
    op.drop_table("transport_fleets")
    with op.batch_alter_table("trading_posts", schema=None) as batch_op:
        batch_op.drop_index("ix_trading_posts_owner")

    op.drop_table("trading_posts")
    with op.batch_alter_table("rackets", schema=None) as batch_op:
        batch_op.drop_index("ix_rackets_settlement")

    op.drop_table("rackets")
    with op.batch_alter_table("order_tribunals", schema=None) as batch_op:
        batch_op.drop_index("ix_order_tribunals_faction")

    op.drop_table("order_tribunals")
    op.drop_table("order_laws")
    with op.batch_alter_table("market_plays", schema=None) as batch_op:
        batch_op.drop_index("ix_market_plays_settlement")

    op.drop_table("market_plays")
    op.drop_table("crime_stances")
    op.drop_table("crime_payroll")
    with op.batch_alter_table("convoys", schema=None) as batch_op:
        batch_op.drop_index("ix_convoys_route")

    op.drop_table("convoys")
    op.execute("DELETE FROM mandates WHERE kind = 'slum_clearance'")
    op.execute("DELETE FROM law_profiles WHERE kind = 'fair_market'")
    op.execute("DELETE FROM law_proposals WHERE kind = 'fair_market'")
    widen(False)
