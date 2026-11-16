import sqlalchemy as sa
from alembic import op

revision = "4676154cc03c"
down_revision = "f19c2a7d4e60"
branch_labels = None
depends_on = None


LAWKIND_OLD = (
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
    "fair_market",
    "magic_ban",
    "licensed_magic",
    "rite_restrictions",
    "franchise",
    "constitution",
    "custom",
    "labour_law",
    "environment_law",
    "data_privacy",
    "weapons_law",
    "intellectual_property",
    "machine_law",
    "space_law",
    "closed_season",
    "protected_waters",
    "catch_quota",
    "gear_ban",
    "mind_status",
    "copy_law",
    "copy_succession",
    "erasure_law",
    "augment_law",
    "network_law",
    "surveillance_law",
    "provision_law",
    "power_law",
    "source_law",
)
LAWKIND_NEW = (*LAWKIND_OLD, "living_craft_law", "clone_law", "clone_status", "germline_law", "designed_status")
LANGUAGEMODALITY_OLD = ("vocal", "sign", "scent", "colour", "telepathic", "data")
LANGUAGEMODALITY_NEW = (*LANGUAGEMODALITY_OLD, "chemical")
METHODKIND_OLD = (
    "hand_sickle",
    "ox_plough",
    "irrigated_terraces",
    "crop_rotation",
    "divine_harvest",
    "line_and_net",
    "fish_weirs",
    "deep_sea_fleets",
    "axe_felling",
    "water_sawmill",
    "pick_and_shovel",
    "fire_setting",
    "pumped_shafts",
    "earth_shaping",
    "hand_quern",
    "watermill",
    "windmill",
    "hand_loom",
    "water_frame",
    "bloomery",
    "blast_furnace",
    "divine_forge",
    "pit_tanning",
    "oil_curing",
    "open_vat",
    "cellar_brewing",
    "herbal_still",
    "arcane_alembic",
    "hand_chisel",
    "water_saw",
    "clamp_kiln",
    "retort_kiln",
    "salting",
    "smoking",
    "drying",
    "icing",
    "magic_keeping",
    "tallow_candles",
    "oil_lamps",
    "glow_moss",
    "magic_light",
    "home_slaughter",
    "shambles",
    "hand_churning",
    "cave_ageing",
    "treading",
    "screw_press",
    "hand_milking",
    "penned_milking",
    "hand_shearing",
    "iron_shears",
    "gathered_eggs",
    "kept_flocks",
)
METHODKIND_NEW = (*METHODKIND_OLD, "cultured_crops", "grown_timber", "spun_fibre", "vat_culture", "bioreactor")
BONDKIND_OLD = (
    "inside",
    "lives_in",
    "worships",
    "enemy",
    "ally",
    "descends_from",
    "protects",
    "rules",
    "owns",
    "beat",
    "killed",
    "cursed",
    "blessed",
    "source_of",
    "tells_of",
    "destroyed",
    "loves",
    "fears",
    "hunts",
    "trades_with",
    "prophesies",
    "caused",
    "celebrates",
    "forbids",
    "speaks",
    "produced",
    "built",
    "migrated_to",
    "discovered",
    "soul_descended_to",
    "party_to",
    "member_of",
    "knows",
    "pays_tribute",
    "related",
    "holds_captive",
    "spy_network",
    "pursues",
    "companion",
    "pet_of",
    "rival",
    "apprentice_of",
    "commands",
    "part_of",
    "passenger_of",
    "captain_of",
    "tamed",
    "truce",
    "owes",
    "treated_by",
    "parent_of",
    "spouse_of",
    "betrothed_to",
    "concubine_of",
    "fostered_by",
    "sworn_kin",
    "tells",
    "fixed_in",
    "adherent_of",
    "practises",
    "copy_of",
    "merged_into",
    "divided_from",
    "transferred_from",
    "restored_from",
    "made_mind_of",
    "hosted_by",
    "linked_with",
)
BONDKIND_NEW = (*BONDKIND_OLD, "clone_of")
CLAUSEKIND_OLD = (
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
    "route_control",
    "resource_demand",
    "research_agreement",
    "fleet_limit",
    "autonomous_weapons_ban",
    "mind_seizure_ban",
    "soldier_copy_ban",
    "replicator_weapon_ban",
    "civil_network_shield",
    "civil_host_shield",
    "no_mind_compulsion",
    "no_plague_powers",
)
CLAUSEKIND_NEW = (*CLAUSEKIND_OLD, "no_designed_disease")
CURESOURCE_OLD = ("knowledge", "granted")
CURESOURCE_NEW = (*CURESOURCE_OLD, "cultured")
ENTITYFLAG_OLD = (
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
    "worships_star",
    "worships_galaxy",
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
ENTITYFLAG_NEW = (*ENTITYFLAG_OLD, "designed_people")
RETYPED = (
    ("law_profiles", "kind", "kind", LAWKIND_OLD, LAWKIND_NEW, False),
    ("law_proposals", "kind", "kind", LAWKIND_OLD, LAWKIND_NEW, False),
    ("language_profiles", "modality", "modality", LANGUAGEMODALITY_OLD, LANGUAGEMODALITY_NEW, False),
    ("community_methods", "method", "method", METHODKIND_OLD, METHODKIND_NEW, False),
    ("production_runs", "method", "method", METHODKIND_OLD, METHODKIND_NEW, True),
    ("bonds", "kind", "kind", BONDKIND_OLD, BONDKIND_NEW, False),
    ("treaty_clauses", "kind", "kind", CLAUSEKIND_OLD, CLAUSEKIND_NEW, False),
    ("disease_cures", "source", "source", CURESOURCE_OLD, CURESOURCE_NEW, False),
    ("entity_flags", "flag", "flag", ENTITYFLAG_OLD, ENTITYFLAG_NEW, False),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, name, old, new, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        gone = ", ".join(f"'{value}'" for value in new if value not in old)
        if not forward and nullable:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})")
        elif not forward:
            op.execute(f"DELETE FROM {table} WHERE {column} IN ({gone})")
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(after, name), existing_nullable=nullable)


def upgrade() -> None:
    retype(True)
    op.create_table(
        "gene_banks",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("unpaid_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("unpaid_epochs >= 0", name=op.f("ck_gene_banks_unpaid_epochs_min")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_gene_banks_upkeep_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_gene_banks_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_gene_banks_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_gene_banks")),
    )
    op.create_table(
        "living_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "selective_breeding",
                "cultivation",
                "shaping",
                "engineering",
                "synthesis",
                "binding",
                "cloning",
                "chimera",
                "induction",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.Enum(
                "as_meant", "unstable", "sterile", "side_effects", "non_viable", "escaped", name="outcome", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("stability", sa.Integer(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("drift_pct", sa.Integer(), nullable=False),
        sa.Column(
            "fertility",
            sa.Enum("sterile", "breeds_true", "breeds_wild", "needs_maker", name="fertility", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "metabolism",
            sa.Enum(
                "feeding", "light", "chemical", "host", "source", "partner", "dormant", name="metabolism", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("owner_node_id", sa.Integer(), nullable=True),
        sa.Column("maker_node_id", sa.Integer(), nullable=True),
        sa.Column("species_entity_id", sa.Integer(), nullable=True),
        sa.Column("drifted_from_id", sa.Integer(), nullable=True),
        sa.Column("licensed", sa.Boolean(), nullable=False),
        sa.Column("escaped", sa.Boolean(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("drift_pct BETWEEN 0 AND 100", name=op.f("ck_living_lines_drift_pct_range")),
        sa.CheckConstraint("generation >= 0", name=op.f("ck_living_lines_generation_min")),
        sa.CheckConstraint("stability BETWEEN 0 AND 100", name=op.f("ck_living_lines_stability_range")),
        sa.ForeignKeyConstraint(["drifted_from_id"], ["living_lines.id"], name=op.f("fk_living_lines_drifted_from_id_living_lines"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["maker_node_id"], ["nodes.id"], name=op.f("fk_living_lines_maker_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_living_lines_owner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_living_lines_species_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_living_lines")),
    )
    with op.batch_alter_table("living_lines", schema=None) as batch_op:
        batch_op.create_index("ix_living_lines_owner", ["owner_node_id"], unique=False)

    op.create_table(
        "gene_bank_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_entity_id", sa.Integer(), nullable=False),
        sa.Column("organism_node_id", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("taken_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_gene_bank_samples_quality_range")),
        sa.ForeignKeyConstraint(
            ["bank_entity_id"], ["gene_banks.structure_entity_id"], name=op.f("fk_gene_bank_samples_bank_entity_id_gene_banks"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organism_node_id"], ["nodes.id"], name=op.f("fk_gene_bank_samples_organism_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gene_bank_samples")),
        sa.UniqueConstraint("bank_entity_id", "organism_node_id", name="uq_gene_bank_samples"),
    )
    with op.batch_alter_table("gene_bank_samples", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_gene_bank_samples_bank_entity_id"), ["bank_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_gene_bank_samples_organism_node_id"), ["organism_node_id"], unique=False)

    op.create_table(
        "living_line_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=False),
        sa.Column("organism_node_id", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["line_id"], ["living_lines.id"], name=op.f("fk_living_line_sources_line_id_living_lines"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organism_node_id"], ["nodes.id"], name=op.f("fk_living_line_sources_organism_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_living_line_sources")),
        sa.UniqueConstraint("line_id", "organism_node_id", name="uq_living_line_sources"),
    )
    with op.batch_alter_table("living_line_sources", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_living_line_sources_line_id"), ["line_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_living_line_sources_organism_node_id"), ["organism_node_id"], unique=False)

    op.create_table(
        "living_line_traits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=False),
        sa.Column(
            "trait",
            sa.Enum(
                "yield",
                "hardiness",
                "climate_tolerance",
                "disease_resistance",
                "strength",
                "speed",
                "size",
                "regeneration",
                "lifespan",
                "docility",
                "potency",
                "fibre",
                "venom",
                "flight",
                "aquatic",
                "void_hardy",
                "gift",
                "nervous_system",
                "sapience",
                name="trait",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("side_effect", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN -100 AND 100", name=op.f("ck_living_line_traits_strength_range")),
        sa.ForeignKeyConstraint(["line_id"], ["living_lines.id"], name=op.f("fk_living_line_traits_line_id_living_lines"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_living_line_traits")),
        sa.UniqueConstraint("line_id", "trait", name="uq_living_line_traits"),
    )
    with op.batch_alter_table("living_line_traits", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_living_line_traits_line_id"), ["line_id"], unique=False)

    op.create_table(
        "living_profiles",
        sa.Column("thing_node_id", sa.Integer(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=True),
        sa.Column(
            "metabolism",
            sa.Enum(
                "feeding", "light", "chemical", "host", "source", "partner", "dormant", name="metabolism", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "feed_commodity",
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
                name="feed_commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("feed_per_season", sa.Integer(), nullable=False),
        sa.Column(
            "growth_stage",
            sa.Enum("seed", "young", "grown", "prime", "old", "dying", "dead", name="growth_stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("size_pct", sa.Integer(), nullable=False),
        sa.Column("regeneration", sa.Integer(), nullable=False),
        sa.Column("health", sa.Integer(), nullable=False),
        sa.Column(
            "temperament",
            sa.Enum("placid", "skittish", "curious", "fierce", "cunning", "abductor", name="temperament", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("bonded_to_node_id", sa.Integer(), nullable=True),
        sa.Column("bond", sa.Integer(), nullable=False),
        sa.Column(
            "fertility",
            sa.Enum("sterile", "breeds_true", "breeds_wild", "needs_maker", name="fertility", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("lifespan_years", sa.Integer(), nullable=False),
        sa.Column("age_seasons", sa.Integer(), nullable=False),
        sa.Column("designed_by_node_id", sa.Integer(), nullable=True),
        sa.Column("planted_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("age_seasons >= 0", name=op.f("ck_living_profiles_age_seasons_min")),
        sa.CheckConstraint("bond BETWEEN 0 AND 100", name=op.f("ck_living_profiles_bond_range")),
        sa.CheckConstraint("feed_per_season >= 0", name=op.f("ck_living_profiles_feed_per_season_min")),
        sa.CheckConstraint("health BETWEEN 0 AND 100", name=op.f("ck_living_profiles_health_range")),
        sa.CheckConstraint("lifespan_years >= 0", name=op.f("ck_living_profiles_lifespan_years_min")),
        sa.CheckConstraint("regeneration BETWEEN 0 AND 100", name=op.f("ck_living_profiles_regeneration_range")),
        sa.CheckConstraint("size_pct BETWEEN 0 AND 400", name=op.f("ck_living_profiles_size_pct_range")),
        sa.ForeignKeyConstraint(["bonded_to_node_id"], ["nodes.id"], name=op.f("fk_living_profiles_bonded_to_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["designed_by_node_id"], ["nodes.id"], name=op.f("fk_living_profiles_designed_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["line_id"], ["living_lines.id"], name=op.f("fk_living_profiles_line_id_living_lines"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thing_node_id"], ["nodes.id"], name=op.f("fk_living_profiles_thing_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("thing_node_id", name=op.f("pk_living_profiles")),
    )
    with op.batch_alter_table("living_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_living_profiles_line", ["line_id"], unique=False)

    op.create_table(
        "symbionts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("host_node_id", sa.Integer(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=True),
        sa.Column("mind_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "placement",
            sa.Enum("skin", "blood", "organ", "nerve", "mind", name="placement", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "relation",
            sa.Enum("mutual", "commensal", "parasitic", "controlling", name="relation", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_symbionts_strength_range")),
        sa.ForeignKeyConstraint(["host_node_id"], ["nodes.id"], name=op.f("fk_symbionts_host_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["line_id"], ["living_lines.id"], name=op.f("fk_symbionts_line_id_living_lines"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mind_node_id"], ["nodes.id"], name=op.f("fk_symbionts_mind_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_symbionts")),
    )
    with op.batch_alter_table("symbionts", schema=None) as batch_op:
        batch_op.create_index("ix_symbionts_host", ["host_node_id"], unique=False)

    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "living_craft_stance",
                sa.Enum("abomination", "permitted", "sacred_duty", "silent", name="living_craft_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "germline_stance",
                sa.Enum("abomination", "permitted", "sacred_duty", "silent", name="germline_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "clone_stance",
                sa.Enum("abomination", "permitted", "sacred_duty", "silent", name="clone_stance", native_enum=False, create_constraint=True, length=40),
                server_default="silent",
                nullable=False,
            )
        )

    with op.batch_alter_table("disease_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("designed_line_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("target_node_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_disease_profiles_designed_line_id_living_lines"), "living_lines", ["designed_line_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(batch_op.f("fk_disease_profiles_target_node_id_nodes"), "nodes", ["target_node_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("perennials", schema=None) as batch_op:
        batch_op.add_column(sa.Column("line_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_perennials_line_id_living_lines"), "living_lines", ["line_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("perennials", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_perennials_line_id_living_lines"), type_="foreignkey")
        batch_op.drop_column("line_id")

    with op.batch_alter_table("disease_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_disease_profiles_target_node_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_disease_profiles_designed_line_id_living_lines"), type_="foreignkey")
        batch_op.drop_column("target_node_id")
        batch_op.drop_column("designed_line_id")

    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.drop_constraint("clone_stance", type_="check")
        batch_op.drop_constraint("germline_stance", type_="check")
        batch_op.drop_constraint("living_craft_stance", type_="check")
        batch_op.drop_column("clone_stance")
        batch_op.drop_column("germline_stance")
        batch_op.drop_column("living_craft_stance")

    with op.batch_alter_table("symbionts", schema=None) as batch_op:
        batch_op.drop_index("ix_symbionts_host")

    op.drop_table("symbionts")
    with op.batch_alter_table("living_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_living_profiles_line")

    op.drop_table("living_profiles")
    with op.batch_alter_table("living_line_traits", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_living_line_traits_line_id"))

    op.drop_table("living_line_traits")
    with op.batch_alter_table("living_line_sources", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_living_line_sources_organism_node_id"))
        batch_op.drop_index(batch_op.f("ix_living_line_sources_line_id"))

    op.drop_table("living_line_sources")
    with op.batch_alter_table("gene_bank_samples", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_gene_bank_samples_organism_node_id"))
        batch_op.drop_index(batch_op.f("ix_gene_bank_samples_bank_entity_id"))

    op.drop_table("gene_bank_samples")
    with op.batch_alter_table("living_lines", schema=None) as batch_op:
        batch_op.drop_index("ix_living_lines_owner")

    op.drop_table("living_lines")
    op.drop_table("gene_banks")
    retype(False)
