import sqlalchemy as sa
from alembic import op

revision = "acc2e62332ed"
down_revision = "a4c2e8f1b7d3"
branch_labels = None
depends_on = None


WIDENED = (
    ("natural_law_profiles", "scope", "scope", False, ("cosmos", "world", "region"), ("cosmos", "dimension", "world", "region")),
    (
        "modifiers",
        "source_kind",
        "source_kind",
        False,
        (
            "injury",
            "condition",
            "trait",
            "law",
            "tradition",
            "artwork",
            "doctrine",
            "treaty",
            "structure",
            "wonder",
            "terrain",
            "weather",
            "season",
            "natural_law",
            "god_power",
            "blessing",
            "perk",
            "curse",
            "dominion",
            "phenomenon",
            "god_death",
            "player",
            "suppression",
            "pin",
        ),
        (
            "injury",
            "condition",
            "trait",
            "law",
            "tradition",
            "artwork",
            "doctrine",
            "treaty",
            "structure",
            "wonder",
            "terrain",
            "weather",
            "season",
            "natural_law",
            "god_power",
            "blessing",
            "perk",
            "curse",
            "dominion",
            "phenomenon",
            "cosmos",
            "rift",
            "god_death",
            "player",
            "suppression",
            "pin",
        ),
    ),
    (
        "nodes",
        "kind",
        "node_kind",
        False,
        ("entity", "son", "creator", "foreign_god", "world", "star"),
        ("entity", "son", "creator", "foreign_god", "world", "star", "galaxy", "cluster", "dimension"),
    ),
    (
        "entities",
        "entity_type",
        "entity_type",
        False,
        (
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
            "title",
            "ideology",
            "rite",
            "beast",
            "theory",
            "art_form",
        ),
        (
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
            "title",
            "ideology",
            "rite",
            "beast",
            "theory",
            "art_form",
            "phenomenon",
            "cosmic_being",
        ),
    ),
    (
        "son_powers",
        "param_entity_type",
        "param_entity_type",
        True,
        (
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
            "title",
            "ideology",
            "rite",
            "beast",
            "theory",
            "art_form",
        ),
        (
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
            "title",
            "ideology",
            "rite",
            "beast",
            "theory",
            "art_form",
            "phenomenon",
            "cosmic_being",
        ),
    ),
    (
        "entity_flags",
        "flag",
        "flag",
        False,
        (
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
        ),
        (
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
        ),
    ),
    (
        "routes",
        "method",
        "method",
        False,
        (
            "ancient_gate",
            "space_fold",
            "light_sail",
            "cosmic_mount",
            "dream_journey",
            "river_of_dead",
            "divine_bridge",
            "slingshot_orbit",
            "swallowed",
            "wormhole",
        ),
        (
            "ancient_gate",
            "space_fold",
            "light_sail",
            "cosmic_mount",
            "dream_journey",
            "river_of_dead",
            "divine_bridge",
            "slingshot_orbit",
            "swallowed",
            "wormhole",
            "void_ark",
            "galactic_gate",
            "filament_lane",
            "dimensional_rift",
            "planar_door",
        ),
    ),
    (
        "horizon_intuitions",
        "method",
        "method",
        True,
        (
            "ancient_gate",
            "space_fold",
            "light_sail",
            "cosmic_mount",
            "dream_journey",
            "river_of_dead",
            "divine_bridge",
            "slingshot_orbit",
            "swallowed",
            "wormhole",
        ),
        (
            "ancient_gate",
            "space_fold",
            "light_sail",
            "cosmic_mount",
            "dream_journey",
            "river_of_dead",
            "divine_bridge",
            "slingshot_orbit",
            "swallowed",
            "wormhole",
            "void_ark",
            "galactic_gate",
            "filament_lane",
            "dimensional_rift",
            "planar_door",
        ),
    ),
)


def widen(old: bool) -> None:
    for table, column, name, nullable, narrow, wide in WIDENED:
        before, after = (wide, narrow) if old else (narrow, wide)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                column,
                existing_type=sa.Enum(*before, name=name, native_enum=False, create_constraint=True, length=40),
                type_=sa.Enum(*after, name=name, native_enum=False, create_constraint=True, length=40),
                existing_nullable=nullable,
            )


def upgrade() -> None:
    widen(old=False)
    op.create_table(
        "dimensions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "dimension_kind",
            sa.Enum(
                "prime",
                "parallel",
                "mirror",
                "pocket",
                "bubble_universe",
                "brane",
                "higher_dimensional",
                "antimatter",
                "quantum_branch",
                "time_reversed",
                "compactified",
                "astral",
                "ethereal",
                "dream",
                "shadow",
                "spirit",
                "fey",
                "elemental",
                "celestial",
                "infernal",
                "abyssal",
                "limbo",
                "far_realm",
                "clockwork",
                "chaos",
                "underworld",
                "divine_domain",
                "void_between",
                name="dimension_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "element",
            sa.Enum(
                "fire",
                "water",
                "earth",
                "air",
                "void",
                "light",
                "shadow",
                "ice",
                "lightning",
                "metal",
                "wood",
                name="element",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("parent_dimension_id", sa.Integer(), nullable=True),
        sa.Column("veil", sa.Integer(), nullable=False),
        sa.Column("stability", sa.Integer(), nullable=False),
        sa.Column("time_factor", sa.Float(), nullable=False),
        sa.Column("magic", sa.Integer(), nullable=False),
        sa.Column("hostility", sa.Integer(), nullable=False),
        sa.Column("sanity_drain", sa.Integer(), nullable=False),
        sa.Column("leak", sa.Integer(), nullable=False),
        sa.Column("causality", sa.Enum("strict", "loose", "broken", name="causality", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "discovery",
            sa.Enum("known", "legend", "unknown", "forgotten", name="discovery", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("ruler_node_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("element IS NULL OR dimension_kind = 'elemental'", name=op.f("ck_dimensions_element_on_elemental")),
        sa.CheckConstraint("hostility BETWEEN 0 AND 100", name=op.f("ck_dimensions_hostility_range")),
        sa.CheckConstraint("leak BETWEEN 0 AND 100", name=op.f("ck_dimensions_leak_range")),
        sa.CheckConstraint("magic BETWEEN 0 AND 100", name=op.f("ck_dimensions_magic_range")),
        sa.CheckConstraint("parent_dimension_id IS NULL OR parent_dimension_id <> id", name=op.f("ck_dimensions_not_own_parent")),
        sa.CheckConstraint("sanity_drain >= 0", name=op.f("ck_dimensions_sanity_drain_min")),
        sa.CheckConstraint("stability BETWEEN 0 AND 100", name=op.f("ck_dimensions_stability_range")),
        sa.CheckConstraint("time_factor > 0", name=op.f("ck_dimensions_time_factor_positive")),
        sa.CheckConstraint("veil BETWEEN 0 AND 100", name=op.f("ck_dimensions_veil_range")),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_dimensions_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_dimension_id"], ["dimensions.id"], name=op.f("fk_dimensions_parent_dimension_id_dimensions"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dimensions")),
    )
    with op.batch_alter_table("dimensions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_dimensions_parent_dimension_id"), ["parent_dimension_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_dimensions_ruler_node_id"), ["ruler_node_id"], unique=False)

    op.create_table(
        "galaxy_clusters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "cluster_kind",
            sa.Enum(
                "galaxy_group",
                "local_group",
                "poor_cluster",
                "rich_cluster",
                "supercluster",
                "filament",
                "wall",
                "void",
                "crown_cluster",
                "drowned_cluster",
                "forge_cluster",
                "dream_cluster",
                "mirror_cluster",
                name="cluster_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("parent_cluster_id", sa.Integer(), nullable=True),
        sa.Column("dimension_id", sa.Integer(), nullable=True),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("medium_heat", sa.Integer(), nullable=False),
        sa.Column("expansion", sa.Integer(), nullable=False),
        sa.Column(
            "discovery",
            sa.Enum("known", "legend", "unknown", "forgotten", name="discovery", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("expansion BETWEEN 0 AND 100", name=op.f("ck_galaxy_clusters_expansion_range")),
        sa.CheckConstraint("medium_heat BETWEEN 0 AND 100", name=op.f("ck_galaxy_clusters_medium_heat_range")),
        sa.CheckConstraint("parent_cluster_id IS NULL OR dimension_id IS NULL", name=op.f("ck_galaxy_clusters_one_place")),
        sa.CheckConstraint("parent_cluster_id IS NULL OR parent_cluster_id <> id", name=op.f("ck_galaxy_clusters_not_own_parent")),
        sa.CheckConstraint("radius > 0", name=op.f("ck_galaxy_clusters_radius_positive")),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], name=op.f("fk_galaxy_clusters_dimension_id_dimensions"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_galaxy_clusters_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_cluster_id"], ["galaxy_clusters.id"], name=op.f("fk_galaxy_clusters_parent_cluster_id_galaxy_clusters"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_galaxy_clusters")),
    )
    with op.batch_alter_table("galaxy_clusters", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_galaxy_clusters_dimension_id"), ["dimension_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_galaxy_clusters_parent_cluster_id"), ["parent_cluster_id"], unique=False)

    op.create_table(
        "galaxies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "galaxy_type",
            sa.Enum(
                "spiral",
                "barred_spiral",
                "grand_design_spiral",
                "flocculent_spiral",
                "lenticular",
                "elliptical",
                "giant_elliptical",
                "dwarf_elliptical",
                "dwarf_spheroidal",
                "irregular",
                "dwarf_irregular",
                "ring",
                "peculiar",
                "starburst",
                "active",
                "quasar_host",
                "low_surface_brightness",
                "ultra_diffuse",
                "living",
                "dead",
                "shattered",
                "forged",
                "dreaming",
                "mirror",
                "crowned",
                "hollow",
                "ember",
                "veiled",
                name="galaxy_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("cluster_id", sa.Integer(), nullable=True),
        sa.Column("dimension_id", sa.Integer(), nullable=True),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("arm_count", sa.Integer(), nullable=False),
        sa.Column(
            "nucleus",
            sa.Enum("none", "dormant", "active", "quasar", "devoured", name="nucleus", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("star_formation", sa.Integer(), nullable=False),
        sa.Column("metallicity", sa.Integer(), nullable=False),
        sa.Column(
            "age_stage",
            sa.Enum("forming", "young", "mature", "old", "dying", "dead", name="age_stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("leak", sa.Integer(), nullable=False),
        sa.Column(
            "discovery",
            sa.Enum("known", "legend", "unknown", "forgotten", name="discovery", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("patron_son_id", sa.Integer(), nullable=True),
        sa.Column("merging_with_galaxy_id", sa.Integer(), nullable=True),
        sa.Column("merge_progress", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("arm_count >= 0", name=op.f("ck_galaxies_arm_count_min")),
        sa.CheckConstraint("cluster_id IS NULL OR dimension_id IS NULL", name=op.f("ck_galaxies_one_place")),
        sa.CheckConstraint("leak BETWEEN 0 AND 100", name=op.f("ck_galaxies_leak_range")),
        sa.CheckConstraint("merge_progress BETWEEN 0 AND 100", name=op.f("ck_galaxies_merge_progress_range")),
        sa.CheckConstraint("merging_with_galaxy_id IS NULL OR merging_with_galaxy_id <> id", name=op.f("ck_galaxies_not_own_merger")),
        sa.CheckConstraint("metallicity BETWEEN 0 AND 100", name=op.f("ck_galaxies_metallicity_range")),
        sa.CheckConstraint("radius > 0", name=op.f("ck_galaxies_radius_positive")),
        sa.CheckConstraint("star_formation BETWEEN 0 AND 100", name=op.f("ck_galaxies_star_formation_range")),
        sa.ForeignKeyConstraint(["cluster_id"], ["galaxy_clusters.id"], name=op.f("fk_galaxies_cluster_id_galaxy_clusters"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], name=op.f("fk_galaxies_dimension_id_dimensions"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["nodes.id"], name=op.f("fk_galaxies_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merging_with_galaxy_id"], ["galaxies.id"], name=op.f("fk_galaxies_merging_with_galaxy_id_galaxies"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patron_son_id"], ["sons.id"], name=op.f("fk_galaxies_patron_son_id_sons"), ondelete="SET NULL", use_alter=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_galaxies")),
    )
    with op.batch_alter_table("galaxies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_galaxies_cluster_id"), ["cluster_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_galaxies_dimension_id"), ["dimension_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_galaxies_patron_son_id"), ["patron_son_id"], unique=False)

    op.create_table(
        "galactic_structures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("galaxy_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "spiral_arm",
                "bar",
                "bulge",
                "core",
                "halo",
                "emission_nebula",
                "reflection_nebula",
                "dark_nebula",
                "planetary_nebula",
                "supernova_remnant",
                "stellar_nursery",
                "open_cluster",
                "globular_cluster",
                "stellar_stream",
                "dust_lane",
                "superbubble",
                "star_graveyard",
                "ley_spiral",
                "sealed_vault",
                "gods_forge",
                "dead_light_drift",
                "singing_nebula",
                "rift_scar",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("ended_epoch IS NULL OR ended_epoch >= created_epoch", name=op.f("ck_galactic_structures_ends_after_start")),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_galactic_structures_intensity_range")),
        sa.CheckConstraint("radius > 0", name=op.f("ck_galactic_structures_radius_positive")),
        sa.ForeignKeyConstraint(["galaxy_id"], ["galaxies.id"], name=op.f("fk_galactic_structures_galaxy_id_galaxies"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_galactic_structures")),
    )
    with op.batch_alter_table("galactic_structures", schema=None) as batch_op:
        batch_op.create_index("ix_galactic_structures_galaxy", ["galaxy_id"], unique=False)

    op.create_table(
        "galactic_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "core_outburst",
                "gamma_ray_burst",
                "starburst",
                "tidal_stripping",
                "merger_begun",
                "merger_completed",
                "hypervelocity_star",
                "nebula_collapse",
                "galactic_dimming",
                "awakening",
                "shrouding",
                "severing",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("galaxy_id", sa.Integer(), nullable=False),
        sa.Column("other_galaxy_id", sa.Integer(), nullable=True),
        sa.Column("structure_id", sa.Integer(), nullable=True),
        sa.Column("star_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("caused_by_node_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_galactic_events_epoch_min")),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_galactic_events_intensity_range")),
        sa.CheckConstraint("until_epoch IS NULL OR until_epoch >= epoch", name=op.f("ck_galactic_events_until_after_start")),
        sa.ForeignKeyConstraint(["caused_by_node_id"], ["nodes.id"], name=op.f("fk_galactic_events_caused_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["galaxy_id"], ["galaxies.id"], name=op.f("fk_galactic_events_galaxy_id_galaxies"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["other_galaxy_id"], ["galaxies.id"], name=op.f("fk_galactic_events_other_galaxy_id_galaxies"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_galactic_events_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["structure_id"], ["galactic_structures.id"], name=op.f("fk_galactic_events_structure_id_galactic_structures"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_galactic_events")),
    )
    with op.batch_alter_table("galactic_events", schema=None) as batch_op:
        batch_op.create_index("ix_galactic_events_galaxy_epoch", ["galaxy_id", "epoch"], unique=False)

    op.create_table(
        "celestial_readings",
        sa.Column("celestial_entity_id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("reading", sa.Enum("good", "evil", "neutral", name="reading", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_celestial_readings_epoch_min")),
        sa.ForeignKeyConstraint(["celestial_entity_id"], ["entities.id"], name=op.f("fk_celestial_readings_celestial_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_celestial_readings_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("celestial_entity_id", "people_entity_id", name=op.f("pk_celestial_readings")),
    )
    with op.batch_alter_table("celestial_readings", schema=None) as batch_op:
        batch_op.create_index("ix_celestial_readings_people", ["people_entity_id"], unique=False)

    op.create_table(
        "dimensional_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "incursion",
                "convergence",
                "veil_thinning",
                "planar_alignment",
                "bleed",
                "schism",
                "collapse",
                "echo",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("dimension_id", sa.Integer(), nullable=False),
        sa.Column("other_dimension_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("subject_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("caused_by_node_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.CheckConstraint("epoch >= 1", name=op.f("ck_dimensional_events_epoch_min")),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_dimensional_events_intensity_range")),
        sa.CheckConstraint("other_dimension_id IS NULL OR other_dimension_id <> dimension_id", name=op.f("ck_dimensional_events_two_dimensions")),
        sa.CheckConstraint("until_epoch IS NULL OR until_epoch >= epoch", name=op.f("ck_dimensional_events_until_after_start")),
        sa.ForeignKeyConstraint(["caused_by_node_id"], ["nodes.id"], name=op.f("fk_dimensional_events_caused_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], name=op.f("fk_dimensional_events_dimension_id_dimensions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["other_dimension_id"], ["dimensions.id"], name=op.f("fk_dimensional_events_other_dimension_id_dimensions"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_dimensional_events_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"], name=op.f("fk_dimensional_events_subject_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_dimensional_events_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dimensional_events")),
    )
    with op.batch_alter_table("dimensional_events", schema=None) as batch_op:
        batch_op.create_index("ix_dimensional_events_dimension_epoch", ["dimension_id", "epoch"], unique=False)

    op.create_table(
        "phenomenon_footprints",
        sa.Column("phenomenon_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_phenomenon_footprints_intensity_range")),
        sa.ForeignKeyConstraint(
            ["phenomenon_entity_id"], ["entities.id"], name=op.f("fk_phenomenon_footprints_phenomenon_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_phenomenon_footprints_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("phenomenon_entity_id", "region_entity_id", name=op.f("pk_phenomenon_footprints")),
    )
    with op.batch_alter_table("phenomenon_footprints", schema=None) as batch_op:
        batch_op.create_index("ix_phenomenon_footprints_region", ["region_entity_id"], unique=False)

    op.create_table(
        "phenomenon_profiles",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "eternal_storm",
                "time_slip",
                "leak_wound",
                "ley_nexus_flare",
                "god_corpse_aura",
                "living_fog",
                "crystal_bloom",
                "dead_zone",
                "mirror_lake",
                "gravity_well",
                "singing_stones",
                "aurora_permanent",
                "ghost_road",
                "blight",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("growth", sa.Integer(), nullable=False),
        sa.Column("containment", sa.Integer(), nullable=False),
        sa.Column(
            "cause",
            sa.Enum(
                "rite_backlash",
                "god_death",
                "law_conflict",
                "sky_event",
                "leak_peak",
                "battlefield",
                "rift",
                "divine",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("cause_node_id", sa.Integer(), nullable=True),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("containment BETWEEN 0 AND 100", name=op.f("ck_phenomenon_profiles_containment_range")),
        sa.CheckConstraint("formed_epoch >= 1", name=op.f("ck_phenomenon_profiles_formed_epoch_min")),
        sa.CheckConstraint("growth BETWEEN -100 AND 100", name=op.f("ck_phenomenon_profiles_growth_range")),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_phenomenon_profiles_intensity_range")),
        sa.ForeignKeyConstraint(["cause_node_id"], ["nodes.id"], name=op.f("fk_phenomenon_profiles_cause_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_phenomenon_profiles_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_phenomenon_profiles")),
    )
    with op.batch_alter_table("phenomenon_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_phenomenon_profiles_kind"), ["kind"], unique=False)

    op.create_table(
        "rifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("dimension_id", sa.Integer(), nullable=False),
        sa.Column("target_world_id", sa.Integer(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("stability", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("opening", "open", "closing", "sealed", "collapsed", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "cause",
            sa.Enum(
                "rite_backlash",
                "leak_peak",
                "convergence",
                "god",
                "being",
                "phenomenon",
                "creator",
                name="cause",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("opened_by_node_id", sa.Integer(), nullable=True),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("sealed_epoch", sa.Integer(), nullable=True),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("opened_epoch >= 1", name=op.f("ck_rifts_opened_epoch_min")),
        sa.CheckConstraint("sealed_epoch IS NULL OR sealed_epoch >= opened_epoch", name=op.f("ck_rifts_sealed_after_open")),
        sa.CheckConstraint("size BETWEEN 0 AND 100", name=op.f("ck_rifts_size_range")),
        sa.CheckConstraint("stability BETWEEN 0 AND 100", name=op.f("ck_rifts_stability_range")),
        sa.CheckConstraint("target_world_id IS NULL OR target_world_id <> world_id", name=op.f("ck_rifts_two_worlds")),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], name=op.f("fk_rifts_dimension_id_dimensions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by_node_id"], ["nodes.id"], name=op.f("fk_rifts_opened_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_rifts_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name=op.f("fk_rifts_route_id_routes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_world_id"], ["worlds.id"], name=op.f("fk_rifts_target_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_rifts_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rifts")),
    )
    with op.batch_alter_table("rifts", schema=None) as batch_op:
        batch_op.create_index("ix_rifts_dimension", ["dimension_id"], unique=False)
        batch_op.create_index("ix_rifts_world_state", ["world_id", "state"], unique=False)

    op.create_table(
        "cosmic_being_profiles",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "being_kind",
            sa.Enum(
                "planar_native",
                "dimension_walker",
                "rift_spawn",
                "higher_dimensional",
                "star_eater",
                "nebula_mind",
                "galactic_leviathan",
                "void_shepherd",
                "echo",
                "time_wanderer",
                "cosmic_titan",
                "veil_warden",
                "plane_sovereign",
                "swarm_intelligence",
                "living_constellation",
                name="being_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("home_dimension_id", sa.Integer(), nullable=True),
        sa.Column("galaxy_id", sa.Integer(), nullable=True),
        sa.Column(
            "scale",
            sa.Enum("world", "system", "galaxy", "cluster", "dimension", name="scale", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("might", sa.Integer(), nullable=False),
        sa.Column(
            "phase",
            sa.Enum("dormant", "roaming", "manifest", "incursion", "bound", "banished", name="phase", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "agenda",
            sa.Enum(
                "feed",
                "explore",
                "conquer",
                "guard",
                "trade",
                "flee",
                "seek_worship",
                "unmake",
                "mend",
                name="agenda",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("bound_by_node_id", sa.Integer(), nullable=True),
        sa.Column("rift_id", sa.Integer(), nullable=True),
        sa.Column("target_world_id", sa.Integer(), nullable=True),
        sa.Column("mirrored_entity_id", sa.Integer(), nullable=True),
        sa.Column("manifest_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("manifest_epochs >= 0", name=op.f("ck_cosmic_being_profiles_manifest_epochs_min")),
        sa.CheckConstraint("might BETWEEN 0 AND 100", name=op.f("ck_cosmic_being_profiles_might_range")),
        sa.ForeignKeyConstraint(["bound_by_node_id"], ["nodes.id"], name=op.f("fk_cosmic_being_profiles_bound_by_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_cosmic_being_profiles_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["galaxy_id"], ["galaxies.id"], name=op.f("fk_cosmic_being_profiles_galaxy_id_galaxies"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["home_dimension_id"], ["dimensions.id"], name=op.f("fk_cosmic_being_profiles_home_dimension_id_dimensions"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["mirrored_entity_id"], ["entities.id"], name=op.f("fk_cosmic_being_profiles_mirrored_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["rift_id"], ["rifts.id"], name=op.f("fk_cosmic_being_profiles_rift_id_rifts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_world_id"], ["worlds.id"], name=op.f("fk_cosmic_being_profiles_target_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_cosmic_being_profiles")),
    )
    with op.batch_alter_table("cosmic_being_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_cosmic_being_profiles_being_kind"), ["being_kind"], unique=False)
        batch_op.create_index(batch_op.f("ix_cosmic_being_profiles_galaxy_id"), ["galaxy_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_cosmic_being_profiles_home_dimension_id"), ["home_dimension_id"], unique=False)

    with op.batch_alter_table("cosmos", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "apocalypse_variant",
                sa.Enum(
                    "ruin",
                    "world_war",
                    "outer_descent",
                    "twilight_of_gods",
                    "dimensional_collapse",
                    "galactic_death",
                    name="apocalypse_variant",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )

    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cargo", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column("passengers", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column("convoy", sa.Integer(), nullable=False, server_default=sa.text("'1'")))
        batch_op.add_column(sa.Column("escorts", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(
            sa.Column(
                "scope",
                sa.Enum(
                    "system",
                    "stellar",
                    "galactic",
                    "intergalactic",
                    "intercluster",
                    "interdimensional",
                    name="scope",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.add_column(sa.Column("leak", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(
            sa.Column(
                "current",
                sa.Enum("none", "warm", "cold", name="current", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default=sa.text("'none'"),
            )
        )
        batch_op.add_column(sa.Column("temperature_shift", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("rainfall_shift", sa.Integer(), nullable=False, server_default=sa.text("'0'")))

    with op.batch_alter_table("routes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("capacity", sa.Integer(), nullable=False, server_default=sa.text("'100'")))
        batch_op.add_column(sa.Column("traffic", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("toll_controller_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("toll_pct", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("piracy", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("wear", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("window_every", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("window_offset", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.create_foreign_key(
            batch_op.f("fk_routes_toll_controller_entity_id_entities"), "entities", ["toll_controller_entity_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("stars", schema=None) as batch_op:
        batch_op.add_column(sa.Column("galaxy_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("structure_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "galactic_zone",
                sa.Enum(
                    "core",
                    "bulge",
                    "bar",
                    "inner_disc",
                    "arm",
                    "interarm",
                    "outer_disc",
                    "halo",
                    "rim",
                    "intergalactic",
                    name="galactic_zone",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=False,
                server_default=sa.text("'outer_disc'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "age_stage",
                sa.Enum("young", "main", "old", "dying", "dead", "reborn", name="age_stage", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default=sa.text("'main'"),
            )
        )
        batch_op.add_column(sa.Column("lifecycle_clock", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("stability", sa.Integer(), nullable=False, server_default=sa.text("'70'")))
        batch_op.add_column(sa.Column("radiation", sa.Integer(), nullable=False, server_default=sa.text("'20'")))
        batch_op.add_column(sa.Column("sacredness", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("patron_son_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.create_index(batch_op.f("ix_stars_galaxy_id"), ["galaxy_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_stars_patron_son_id"), ["patron_son_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_stars_structure_id"), ["structure_id"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_stars_structure_id_galactic_structures"), "galactic_structures", ["structure_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(batch_op.f("fk_stars_patron_son_id_sons"), "sons", ["patron_son_id"], ["id"], ondelete="SET NULL", use_alter=True)
        batch_op.create_foreign_key(batch_op.f("fk_stars_galaxy_id_galaxies"), "galaxies", ["galaxy_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("galaxy_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dimension_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("magnetism", sa.Integer(), nullable=False, server_default=sa.text("'50'")))
        batch_op.add_column(sa.Column("radiation", sa.Integer(), nullable=False, server_default=sa.text("'10'")))
        batch_op.add_column(sa.Column("biosphere_health", sa.Integer(), nullable=False, server_default=sa.text("'80'")))
        batch_op.add_column(
            sa.Column(
                "age_stage",
                sa.Enum("young", "mature", "old", "dying", name="age_stage", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default=sa.text("'mature'"),
            )
        )
        batch_op.add_column(sa.Column("mood", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.create_index(batch_op.f("ix_worlds_dimension_id"), ["dimension_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_worlds_galaxy_id"), ["galaxy_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_worlds_galaxy_id_galaxies"), "galaxies", ["galaxy_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_worlds_dimension_id_dimensions"), "dimensions", ["dimension_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("worlds", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_worlds_dimension_id_dimensions"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_worlds_galaxy_id_galaxies"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_worlds_galaxy_id"))
        batch_op.drop_index(batch_op.f("ix_worlds_dimension_id"))
        batch_op.drop_column("locked")
        batch_op.drop_column("mood")
        batch_op.drop_column("age_stage")
        batch_op.drop_column("biosphere_health")
        batch_op.drop_column("radiation")
        batch_op.drop_column("magnetism")
        batch_op.drop_column("dimension_id")
        batch_op.drop_column("galaxy_id")

    with op.batch_alter_table("stars", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_stars_galaxy_id_galaxies"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_stars_patron_son_id_sons"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_stars_structure_id_galactic_structures"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_stars_structure_id"))
        batch_op.drop_index(batch_op.f("ix_stars_patron_son_id"))
        batch_op.drop_index(batch_op.f("ix_stars_galaxy_id"))
        batch_op.drop_column("locked")
        batch_op.drop_column("patron_son_id")
        batch_op.drop_column("sacredness")
        batch_op.drop_column("radiation")
        batch_op.drop_column("stability")
        batch_op.drop_column("lifecycle_clock")
        batch_op.drop_column("age_stage")
        batch_op.drop_column("galactic_zone")
        batch_op.drop_column("structure_id")
        batch_op.drop_column("galaxy_id")

    with op.batch_alter_table("routes", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_routes_toll_controller_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("window_offset")
        batch_op.drop_column("window_every")
        batch_op.drop_column("wear")
        batch_op.drop_column("piracy")
        batch_op.drop_column("toll_pct")
        batch_op.drop_column("toll_controller_entity_id")
        batch_op.drop_column("traffic")
        batch_op.drop_column("capacity")

    with op.batch_alter_table("region_environment", schema=None) as batch_op:
        batch_op.drop_column("rainfall_shift")
        batch_op.drop_column("temperature_shift")
        batch_op.drop_column("current")
        batch_op.drop_column("leak")

    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.drop_column("locked")
        batch_op.drop_column("scope")
        batch_op.drop_column("escorts")
        batch_op.drop_column("convoy")
        batch_op.drop_column("passengers")
        batch_op.drop_column("cargo")

    with op.batch_alter_table("cosmos", schema=None) as batch_op:
        batch_op.drop_column("apocalypse_variant")

    with op.batch_alter_table("cosmic_being_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_cosmic_being_profiles_home_dimension_id"))
        batch_op.drop_index(batch_op.f("ix_cosmic_being_profiles_galaxy_id"))
        batch_op.drop_index(batch_op.f("ix_cosmic_being_profiles_being_kind"))

    op.drop_table("cosmic_being_profiles")
    with op.batch_alter_table("rifts", schema=None) as batch_op:
        batch_op.drop_index("ix_rifts_world_state")
        batch_op.drop_index("ix_rifts_dimension")

    op.drop_table("rifts")
    with op.batch_alter_table("phenomenon_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_phenomenon_profiles_kind"))

    op.drop_table("phenomenon_profiles")
    with op.batch_alter_table("phenomenon_footprints", schema=None) as batch_op:
        batch_op.drop_index("ix_phenomenon_footprints_region")

    op.drop_table("phenomenon_footprints")
    with op.batch_alter_table("dimensional_events", schema=None) as batch_op:
        batch_op.drop_index("ix_dimensional_events_dimension_epoch")

    op.drop_table("dimensional_events")
    with op.batch_alter_table("celestial_readings", schema=None) as batch_op:
        batch_op.drop_index("ix_celestial_readings_people")

    op.drop_table("celestial_readings")
    with op.batch_alter_table("galactic_events", schema=None) as batch_op:
        batch_op.drop_index("ix_galactic_events_galaxy_epoch")

    op.drop_table("galactic_events")
    with op.batch_alter_table("galactic_structures", schema=None) as batch_op:
        batch_op.drop_index("ix_galactic_structures_galaxy")

    op.drop_table("galactic_structures")
    with op.batch_alter_table("galaxies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_galaxies_patron_son_id"))
        batch_op.drop_index(batch_op.f("ix_galaxies_dimension_id"))
        batch_op.drop_index(batch_op.f("ix_galaxies_cluster_id"))

    op.drop_table("galaxies")
    with op.batch_alter_table("galaxy_clusters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_galaxy_clusters_parent_cluster_id"))
        batch_op.drop_index(batch_op.f("ix_galaxy_clusters_dimension_id"))

    op.drop_table("galaxy_clusters")
    with op.batch_alter_table("dimensions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dimensions_ruler_node_id"))
        batch_op.drop_index(batch_op.f("ix_dimensions_parent_dimension_id"))

    op.drop_table("dimensions")
    widen(old=True)
