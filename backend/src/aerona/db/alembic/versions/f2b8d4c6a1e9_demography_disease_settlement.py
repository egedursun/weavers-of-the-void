import sqlalchemy as sa
from alembic import op

revision = "f2b8d4c6a1e9"
down_revision = "e7a4c1b9d2f3"
branch_labels = None
depends_on = None

OLD_ENTITY_TYPES = (
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
)
NEW_ENTITY_TYPES = (*OLD_ENTITY_TYPES, "disease")
OLD_CLASSES = (
    "farmer",
    "artisan",
    "merchant",
    "priest",
    "warrior",
    "scribe",
)
NEW_CLASSES = (*OLD_CLASSES, "noble", "serf_or_slave", "outcast", "monastic")
NEW_FLAGS = (
    "disaster",
    "dormant",
    "lost",
    "dead_language",
    "decipherable",
    "previous_creation",
    "ruin",
    "rebuilt",
    "remnant",
    "void",
    "cursed",
    "godless",
    "seeking_god",
    "empire",
    "federation",
    "independent",
    "colony",
    "pioneer",
    "golden_age",
    "immortal",
    "chimera",
    "mutation",
    "mutant",
    "mutated",
    "discovery",
    "native",
    "revelation",
    "soul_descended",
    "soul_bound",
    "soul_harvester",
    "crossed_to_the_dead",
    "wonder",
    "chosen",
    "manifested",
    "born_of_belief",
    "corrupted_memory",
    "fairy_tale",
    "name_from_language",
    "fixed_name",
    "species_became_people",
    "original_resource",
    "cosmic_monopoly",
    "outer_cult",
    "whisper_source",
    "nameless",
    "escaped",
    "megafauna",
    "invasive",
    "worships_planet",
    "planet_closed",
    "burned",
    "cosmic_plague",
    "mirror",
    "mirror_born",
    "oathbreaker",
    "exile",
    "omen",
    "time_echo",
    "two_timed",
    "empty_tomb",
    "resurrection_complete",
    "protected_from_disaster",
    "mechanics_weighed",
    "depleting",
    "syncretic",
    "returned_to_old_god",
    "revived_language",
    "on_watch",
    "mocked",
    "protected_from_ruin",
    "spared_soul",
    "ghost",
    "wizard",
    "age_changer",
    "time_returned",
    "legendary",
    "prophet",
    "bloodline_curse",
    "essence_drained",
    "returned_from_death",
    "saw_the_creator",
    "deified",
    "protected",
    "depleted",
    "agent_selected",
    "capital",
    "abandoned",
    "dissolved",
    "desolate",
    "razed",
    "fell_in_battle",
    "died_in_siege",
    "died_in_disaster",
    "died_of_plague",
    "slain_in_captivity",
    "doomed",
    "fate_shielded",
    "commemoration",
    "estranged_by_plague",
    "endangered",
    "extinct",
    "pilgrimage_site",
    "repealed",
    "merged",
    "disbanded",
    "assimilated",
    "forgotten",
    "swallowed",
)
OLD_FLAGS = tuple(flag for flag in NEW_FLAGS if flag != "dormant")
WIDENED = (
    ("entities", "entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, False),
    ("son_powers", "param_entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, True),
    ("entities", "social_class", OLD_CLASSES, NEW_CLASSES, True),
    ("entity_flags", "flag", OLD_FLAGS, NEW_FLAGS, False),
)
SETTLEMENT_WEALTH = " ".join(
    (
        "UPDATE entities SET stats = json_set(stats, '$.wealth', COALESCE(json_extract(stats, '$.prosperity'), 30))",
        "WHERE entity_type = 'settlement' AND json_extract(stats, '$.wealth') IS NULL",
    )
)
NEW_SHARES = ("noble", "serf_or_slave", "outcast", "monastic")


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    op.execute(SETTLEMENT_WEALTH)
    op.create_table(
        "community_cohorts",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("age_band", sa.Enum("child", "adult", "elder", name="age_band", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("sex", sa.Enum("female", "male", name="sex", native_enum=False, create_constraint=True, length=40), nullable=False),
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
        sa.Column(
            "condition",
            sa.Enum("none", "veteran", "sick", "enslaved", "captive", name="condition", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("generation_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_community_cohorts_count_min")),
        sa.CheckConstraint("generation_epoch >= 0", name=op.f("ck_community_cohorts_generation_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_community_cohorts_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "age_band", "sex", "social_class", "condition", name=op.f("pk_community_cohorts")),
    )
    with op.batch_alter_table("community_cohorts", schema=None) as batch_op:
        batch_op.create_index("ix_community_cohorts_community", ["community_entity_id"], unique=False)

    op.create_table(
        "community_labour",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "job",
            sa.Enum(
                "farming",
                "herding",
                "fishing",
                "mining",
                "crafting",
                "trade",
                "soldiering",
                "clergy",
                "scholarship",
                "building",
                "idle",
                name="job",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("workers", sa.Integer(), nullable=False),
        sa.Column("output_pct", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("output_pct BETWEEN 0 AND 1000", name=op.f("ck_community_labour_output_pct_range")),
        sa.CheckConstraint("workers >= 0", name=op.f("ck_community_labour_workers_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_community_labour_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "job", name=op.f("pk_community_labour")),
    )
    op.create_table(
        "disease_cures",
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum("knowledge", "granted", name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_disease_cures_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_disease_cures_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("disease_entity_id", "community_entity_id", name=op.f("pk_disease_cures")),
    )
    op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "farmland",
                "market",
                "craft_quarter",
                "temple_quarter",
                "harbour",
                "citadel",
                "slums",
                "palace",
                "foreign_quarter",
                "necropolis",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("material", sa.Enum("timber", "stone", name="material", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("built_epoch", sa.Integer(), nullable=False),
        sa.Column("built_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("built_by_son_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_districts_condition_range")),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name=op.f("ck_districts_level_range")),
        sa.ForeignKeyConstraint(["built_by_entity_id"], ["entities.id"], name=op.f("fk_districts_built_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["built_by_son_id"], ["sons.id"], name=op.f("fk_districts_built_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_districts_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_districts")),
    )
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.create_index("ix_districts_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "endemic_diseases",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("load", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("load BETWEEN 0 AND 100", name=op.f("ck_endemic_diseases_load_range")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_endemic_diseases_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_endemic_diseases_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", "disease_entity_id", name=op.f("pk_endemic_diseases")),
    )
    with op.batch_alter_table("endemic_diseases", schema=None) as batch_op:
        batch_op.create_index("ix_endemic_diseases_disease", ["disease_entity_id"], unique=False)

    op.create_table(
        "immunities",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("age_band", sa.Enum("child", "adult", "elder", name="age_band", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("immune_pct", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("immune_pct BETWEEN 0 AND 100", name=op.f("ck_immunities_immune_pct_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_immunities_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_immunities_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "disease_entity_id", "age_band", name=op.f("pk_immunities")),
    )
    with op.batch_alter_table("immunities", schema=None) as batch_op:
        batch_op.create_index("ix_immunities_disease", ["disease_entity_id"], unique=False)

    op.create_table(
        "outbreaks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("event_entity_id", sa.Integer(), nullable=True),
        sa.Column("source_outbreak_id", sa.Integer(), nullable=True),
        sa.Column(
            "path",
            sa.Enum("origin", "route", "army", "journey", "siege", "loosed", "mutation", name="path", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("status", sa.Enum("active", "waning", "ended", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("infected", sa.Integer(), nullable=False),
        sa.Column("dead", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("quarantined", sa.Boolean(), nullable=False),
        sa.CheckConstraint("dead >= 0", name=op.f("ck_outbreaks_dead_min")),
        sa.CheckConstraint("infected >= 0", name=op.f("ck_outbreaks_infected_min")),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_outbreaks_severity_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_outbreaks_started_epoch_min")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_outbreaks_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_entity_id"], ["entities.id"], name=op.f("fk_outbreaks_event_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_outbreaks_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_outbreak_id"], ["outbreaks.id"], name=op.f("fk_outbreaks_source_outbreak_id_outbreaks"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbreaks")),
    )
    with op.batch_alter_table("outbreaks", schema=None) as batch_op:
        batch_op.create_index("ix_outbreaks_disease", ["disease_entity_id", "status"], unique=False)
        batch_op.create_index(batch_op.f("ix_outbreaks_event_entity_id"), ["event_entity_id"], unique=False)
        batch_op.create_index("ix_outbreaks_region", ["region_entity_id", "status"], unique=False)

    op.create_table(
        "people_biology",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("maturity_years", sa.Integer(), nullable=False),
        sa.Column("adult_years", sa.Integer(), nullable=False),
        sa.Column("elder_years", sa.Integer(), nullable=False),
        sa.Column("fertility_pct", sa.Integer(), nullable=False),
        sa.Column(
            "acclimatised",
            sa.Enum("frozen", "cold", "temperate", "warm", "hot", "searing", name="acclimatised", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("traits", sa.JSON(), nullable=False),
        sa.Column(
            "staple",
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
                name="staple",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("immunities", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("adult_years >= 1", name=op.f("ck_people_biology_adult_years_min")),
        sa.CheckConstraint("elder_years >= 1", name=op.f("ck_people_biology_elder_years_min")),
        sa.CheckConstraint("fertility_pct BETWEEN 0 AND 500", name=op.f("ck_people_biology_fertility_pct_range")),
        sa.CheckConstraint("maturity_years >= 1", name=op.f("ck_people_biology_maturity_years_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_people_biology_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_people_biology")),
    )
    op.create_table(
        "people_culture",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("cohesion", sa.Integer(), nullable=False),
        sa.Column("literacy", sa.Integer(), nullable=False),
        sa.Column("urbanisation", sa.Integer(), nullable=False),
        sa.Column("liturgical_language_id", sa.Integer(), nullable=True),
        sa.Column("trade_language_id", sa.Integer(), nullable=True),
        sa.Column("staples", sa.JSON(), nullable=False),
        sa.Column(
            "aesthetic",
            sa.Enum(
                "austere", "ornate", "geometric", "natural", "macabre", "celestial", name="aesthetic", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "martial_style",
            sa.Enum(
                "shieldwall",
                "horse_archer",
                "skirmisher",
                "chariot",
                "phalanx",
                "berserker",
                "naval_raider",
                "siege_engineer",
                "war_magic",
                "beast_war",
                name="martial_style",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("funeral_rite_id", sa.Integer(), nullable=True),
        sa.Column(
            "marriage",
            sa.Enum("monogamy", "polygyny", "polyandry", "group", name="marriage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("endogamous", sa.Boolean(), nullable=False),
        sa.Column(
            "inheritance",
            sa.Enum(
                "gavelkind",
                "primogeniture",
                "ultimogeniture",
                "matrilineal",
                "elective",
                "by_merit",
                name="inheritance",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("slavery_lawful", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cohesion BETWEEN 0 AND 100", name=op.f("ck_people_culture_cohesion_range")),
        sa.CheckConstraint("literacy BETWEEN 0 AND 100", name=op.f("ck_people_culture_literacy_range")),
        sa.CheckConstraint("urbanisation BETWEEN 0 AND 100", name=op.f("ck_people_culture_urbanisation_range")),
        sa.ForeignKeyConstraint(["funeral_rite_id"], ["entities.id"], name=op.f("fk_people_culture_funeral_rite_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["liturgical_language_id"], ["entities.id"], name=op.f("fk_people_culture_liturgical_language_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_people_culture_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trade_language_id"], ["entities.id"], name=op.f("fk_people_culture_trade_language_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_people_culture")),
    )
    op.create_table(
        "quarantines",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=False),
        sa.Column("ordered_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("ordered_by_son_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_quarantines_started_epoch_min")),
        sa.ForeignKeyConstraint(["ordered_by_entity_id"], ["entities.id"], name=op.f("fk_quarantines_ordered_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ordered_by_son_id"], ["sons.id"], name=op.f("fk_quarantines_ordered_by_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_quarantines_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_quarantines")),
    )
    op.create_table(
        "settlement_history",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "size_tier",
            sa.Enum("hamlet", "village", "town", "city", "metropolis", name="size_tier", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("public_order", sa.Integer(), nullable=False),
        sa.Column("crime", sa.Integer(), nullable=False),
        sa.Column("unrest", sa.Integer(), nullable=False),
        sa.Column("sanitation", sa.Integer(), nullable=False),
        sa.Column("wealth", sa.Integer(), nullable=False),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["settlement_entity_id"], ["entities.id"], name=op.f("fk_settlement_history_settlement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("settlement_entity_id", "epoch", name=op.f("pk_settlement_history")),
    )
    op.create_table(
        "settlement_infrastructure",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("walls_level", sa.Integer(), nullable=False),
        sa.Column("walls_material", sa.Enum("timber", "stone", name="walls_material", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("walls_condition", sa.Integer(), nullable=False),
        sa.Column("gates", sa.Integer(), nullable=False),
        sa.Column("roads", sa.Integer(), nullable=False),
        sa.Column("water", sa.Enum("none", "well", "cistern", "aqueduct", name="water", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("sewers", sa.Boolean(), nullable=False),
        sa.Column("granary_capacity", sa.Integer(), nullable=False),
        sa.Column("warehouse_capacity", sa.Integer(), nullable=False),
        sa.Column("harbour_capacity", sa.Integer(), nullable=False),
        sa.Column("towers", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("gates BETWEEN 0 AND 20", name=op.f("ck_settlement_infrastructure_gates_range")),
        sa.CheckConstraint("granary_capacity >= 0", name=op.f("ck_settlement_infrastructure_granary_capacity_min")),
        sa.CheckConstraint("harbour_capacity >= 0", name=op.f("ck_settlement_infrastructure_harbour_capacity_min")),
        sa.CheckConstraint("roads BETWEEN 0 AND 5", name=op.f("ck_settlement_infrastructure_roads_range")),
        sa.CheckConstraint("towers BETWEEN 0 AND 20", name=op.f("ck_settlement_infrastructure_towers_range")),
        sa.CheckConstraint("walls_condition BETWEEN 0 AND 100", name=op.f("ck_settlement_infrastructure_walls_condition_range")),
        sa.CheckConstraint("walls_level BETWEEN 0 AND 5", name=op.f("ck_settlement_infrastructure_walls_level_range")),
        sa.CheckConstraint("warehouse_capacity >= 0", name=op.f("ck_settlement_infrastructure_warehouse_capacity_min")),
        sa.ForeignKeyConstraint(
            ["settlement_entity_id"], ["entities.id"], name=op.f("fk_settlement_infrastructure_settlement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_settlement_infrastructure")),
    )
    op.create_table(
        "settlement_profiles",
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "size_tier",
            sa.Enum("hamlet", "village", "town", "city", "metropolis", name="size_tier", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Integer(), nullable=False),
        sa.Column("public_order", sa.Integer(), nullable=False),
        sa.Column("crime", sa.Integer(), nullable=False),
        sa.Column("unrest", sa.Integer(), nullable=False),
        sa.Column("sanitation", sa.Integer(), nullable=False),
        sa.Column("fire_risk", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("militia", sa.Integer(), nullable=False),
        sa.Column("garrison_entity_id", sa.Integer(), nullable=True),
        sa.Column("free_city", sa.Boolean(), nullable=False),
        sa.Column("charter_entity_id", sa.Integer(), nullable=True),
        sa.Column("foreigners", sa.JSON(), nullable=False),
        sa.Column("siege_supplies", sa.Integer(), nullable=False),
        sa.Column("siege_water", sa.Integer(), nullable=False),
        sa.Column("siege_disease", sa.Integer(), nullable=False),
        sa.Column("investment_pool", sa.Integer(), nullable=False),
        sa.Column("construction_capacity", sa.Integer(), nullable=False),
        sa.Column("hauling_capacity", sa.Integer(), nullable=False),
        sa.Column("rationing", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("construction_capacity >= 0", name=op.f("ck_settlement_profiles_construction_capacity_min")),
        sa.CheckConstraint("crime BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_crime_range")),
        sa.CheckConstraint("fire_risk BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_fire_risk_range")),
        sa.CheckConstraint("hauling_capacity >= 0", name=op.f("ck_settlement_profiles_hauling_capacity_min")),
        sa.CheckConstraint("investment_pool >= 0", name=op.f("ck_settlement_profiles_investment_pool_min")),
        sa.CheckConstraint("militia >= 0", name=op.f("ck_settlement_profiles_militia_min")),
        sa.CheckConstraint("public_order BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_public_order_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_prestige_range")),
        sa.CheckConstraint("sanitation BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_sanitation_range")),
        sa.CheckConstraint("siege_supplies >= 0", name=op.f("ck_settlement_profiles_siege_supplies_min")),
        sa.CheckConstraint("siege_water >= 0", name=op.f("ck_settlement_profiles_siege_water_min")),
        sa.CheckConstraint("tax_rate BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_tax_rate_range")),
        sa.CheckConstraint("unrest BETWEEN 0 AND 100", name=op.f("ck_settlement_profiles_unrest_range")),
        sa.ForeignKeyConstraint(["charter_entity_id"], ["entities.id"], name=op.f("fk_settlement_profiles_charter_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["garrison_entity_id"], ["entities.id"], name=op.f("fk_settlement_profiles_garrison_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["settlement_entity_id"], ["entities.id"], name=op.f("fk_settlement_profiles_settlement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("settlement_entity_id", name=op.f("pk_settlement_profiles")),
    )
    op.create_table(
        "settlement_treasury",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "entry",
            sa.Enum(
                "tax",
                "tolls",
                "investment",
                "garrison",
                "walls",
                "building",
                "festival",
                "alms",
                "fire",
                "plunder",
                "grant",
                name="entry",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["settlement_entity_id"], ["entities.id"], name=op.f("fk_settlement_treasury_settlement_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settlement_treasury")),
    )
    with op.batch_alter_table("settlement_treasury", schema=None) as batch_op:
        batch_op.create_index("ix_settlement_treasury_settlement", ["settlement_entity_id", "epoch"], unique=False)

    op.create_table(
        "disease_profiles",
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "vector",
            sa.Enum("air", "water", "touch", "bite", "spirit", "void", "curse", name="vector", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("virulence", sa.Integer(), nullable=False),
        sa.Column("lethality", sa.Integer(), nullable=False),
        sa.Column("chronic_rate", sa.Integer(), nullable=False),
        sa.Column("incubation", sa.Integer(), nullable=False),
        sa.Column("target_functions", sa.JSON(), nullable=False),
        sa.Column(
            "climate_affinity",
            sa.Enum("warm", "wet", "cold", "dry", "any", name="climate_affinity", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("host_species_id", sa.Integer(), nullable=True),
        sa.Column("immunity_epochs", sa.Integer(), nullable=False),
        sa.Column("mutation_rate", sa.Integer(), nullable=False),
        sa.Column("origin_incident_id", sa.Integer(), nullable=True),
        sa.Column("origin_region_id", sa.Integer(), nullable=True),
        sa.Column("parent_disease_id", sa.Integer(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("stigma", sa.Integer(), nullable=False),
        sa.Column("cure_level", sa.Integer(), nullable=False),
        sa.Column("emerged_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("chronic_rate BETWEEN 0 AND 100", name=op.f("ck_disease_profiles_chronic_rate_range")),
        sa.CheckConstraint("cure_level >= 0", name=op.f("ck_disease_profiles_cure_level_min")),
        sa.CheckConstraint("generation >= 0", name=op.f("ck_disease_profiles_generation_min")),
        sa.CheckConstraint("immunity_epochs >= 1", name=op.f("ck_disease_profiles_immunity_epochs_min")),
        sa.CheckConstraint("incubation >= 0", name=op.f("ck_disease_profiles_incubation_min")),
        sa.CheckConstraint("lethality BETWEEN 0 AND 100", name=op.f("ck_disease_profiles_lethality_range")),
        sa.CheckConstraint("mutation_rate BETWEEN 0 AND 100", name=op.f("ck_disease_profiles_mutation_rate_range")),
        sa.CheckConstraint("stigma BETWEEN 0 AND 100", name=op.f("ck_disease_profiles_stigma_range")),
        sa.CheckConstraint("virulence BETWEEN 0 AND 100", name=op.f("ck_disease_profiles_virulence_range")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_disease_profiles_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_species_id"], ["entities.id"], name=op.f("fk_disease_profiles_host_species_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_incident_id"], ["incidents.id"], name=op.f("fk_disease_profiles_origin_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_region_id"], ["entities.id"], name=op.f("fk_disease_profiles_origin_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_disease_id"], ["entities.id"], name=op.f("fk_disease_profiles_parent_disease_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("disease_entity_id", name=op.f("pk_disease_profiles")),
    )
    with op.batch_alter_table("community_societies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("share_noble", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("share_serf_or_slave", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("share_outcast", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("share_monastic", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("satisfaction_noble", sa.Integer(), nullable=False, server_default="55"))
        batch_op.add_column(sa.Column("satisfaction_serf_or_slave", sa.Integer(), nullable=False, server_default="30"))
        batch_op.add_column(sa.Column("satisfaction_outcast", sa.Integer(), nullable=False, server_default="25"))
        batch_op.add_column(sa.Column("satisfaction_monastic", sa.Integer(), nullable=False, server_default="55"))
        batch_op.create_check_constraint(op.f("ck_community_societies_share_noble_range"), "share_noble BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_satisfaction_noble_range"), "satisfaction_noble BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_share_serf_or_slave_range"), "share_serf_or_slave BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_satisfaction_serf_or_slave_range"), "satisfaction_serf_or_slave BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_share_outcast_range"), "share_outcast BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_satisfaction_outcast_range"), "satisfaction_outcast BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_share_monastic_range"), "share_monastic BETWEEN 0 AND 100")
        batch_op.create_check_constraint(op.f("ck_community_societies_satisfaction_monastic_range"), "satisfaction_monastic BETWEEN 0 AND 100")


def downgrade() -> None:
    with op.batch_alter_table("community_societies", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_community_societies_share_noble_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_satisfaction_noble_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_share_serf_or_slave_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_satisfaction_serf_or_slave_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_share_outcast_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_satisfaction_outcast_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_share_monastic_range"), type_="check")
        batch_op.drop_constraint(op.f("ck_community_societies_satisfaction_monastic_range"), type_="check")
        batch_op.drop_column("satisfaction_monastic")
        batch_op.drop_column("satisfaction_outcast")
        batch_op.drop_column("satisfaction_serf_or_slave")
        batch_op.drop_column("satisfaction_noble")
        batch_op.drop_column("share_monastic")
        batch_op.drop_column("share_outcast")
        batch_op.drop_column("share_serf_or_slave")
        batch_op.drop_column("share_noble")

    op.drop_table("disease_profiles")
    with op.batch_alter_table("settlement_treasury", schema=None) as batch_op:
        batch_op.drop_index("ix_settlement_treasury_settlement")

    op.drop_table("settlement_treasury")
    op.drop_table("settlement_profiles")
    op.drop_table("settlement_infrastructure")
    op.drop_table("settlement_history")
    op.drop_table("quarantines")
    op.drop_table("people_culture")
    op.drop_table("people_biology")
    with op.batch_alter_table("outbreaks", schema=None) as batch_op:
        batch_op.drop_index("ix_outbreaks_region")
        batch_op.drop_index(batch_op.f("ix_outbreaks_event_entity_id"))
        batch_op.drop_index("ix_outbreaks_disease")

    op.drop_table("outbreaks")
    with op.batch_alter_table("immunities", schema=None) as batch_op:
        batch_op.drop_index("ix_immunities_disease")

    op.drop_table("immunities")
    with op.batch_alter_table("endemic_diseases", schema=None) as batch_op:
        batch_op.drop_index("ix_endemic_diseases_disease")

    op.drop_table("endemic_diseases")
    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.drop_index("ix_districts_settlement")

    op.drop_table("districts")
    op.drop_table("disease_cures")
    op.drop_table("community_labour")
    with op.batch_alter_table("community_cohorts", schema=None) as batch_op:
        batch_op.drop_index("ix_community_cohorts_community")

    op.drop_table("community_cohorts")
    op.execute("DELETE FROM entity_flags WHERE flag = 'dormant'")
    op.execute("UPDATE entities SET social_class = NULL WHERE social_class IN ('noble', 'serf_or_slave', 'outcast', 'monastic')")
    op.execute("DELETE FROM entities WHERE entity_type = 'disease'")
    widen(False)
