import sqlalchemy as sa
from alembic import op

revision = "c728db1bc3e7"
down_revision = "6217b56bb2ff"
branch_labels = None
depends_on = None


G5_BUILT_INS = (
    ("hut", "Hut", "hut", 1, 25, 1, 0),
    ("longhouse", "Longhouse", "house", 3, 40, 2, 0),
    ("townhouse", "Townhouse", "townhouse", 4, 55, 4, 0),
    ("manor", "Manor", "manor", 10, 72, 8, 0),
    ("palace", "Palace", "manor", 30, 90, 18, 0),
    ("tent", "Tent", "hut", 1, 20, 1, 1),
    ("cave", "Cave", "hut", 2, 15, 0, 0),
    ("ship", "Ship", "ship_berth", 2, 35, 3, 1),
    ("tower", "Tower", "townhouse", 6, 60, 6, 0),
    ("apartment", "Apartment", "apartment", 2, 50, 3, 0),
)
G5_POTENTIAL = (("perception", "intuition"), ("wisdom", "patience"))


def seed_built_in_dwellings() -> None:
    for key, name, level, rooms, quality, upkeep, mobile in G5_BUILT_INS:
        op.execute(
            sa.text(
                "INSERT INTO dwelling_kinds (name, built_in, created_epoch, retired, locked, category, rooms, quality, upkeep, mobile, built_in_key) "
                "SELECT :name, 1, 0, 0, '[]', :level, :rooms, :quality, :upkeep, :mobile, :key "
                "WHERE NOT EXISTS (SELECT 1 FROM dwelling_kinds WHERE built_in_key = :key)"
            ).bindparams(name=name, level=level, rooms=rooms, quality=quality, upkeep=upkeep, mobile=mobile, key=key)
        )


def map_dwellings_forward() -> None:
    seed_built_in_dwellings()
    op.execute("UPDATE dwellings SET dwelling_kind_id = (SELECT id FROM dwelling_kinds WHERE built_in_key = dwellings.kind)")
    op.execute("UPDATE household_aggregates SET dwelling_kind_id = (SELECT id FROM dwelling_kinds WHERE built_in_key = household_aggregates.dwelling_kind)")
    for old, new in G5_POTENTIAL:
        op.execute(
            sa.text(
                "UPDATE genomes SET potential = json_remove(json_set(potential, '$.' || :new, json_extract(potential, '$.' || :old)), '$.' || :old) "
                "WHERE json_extract(potential, '$.' || :old) IS NOT NULL"
            ).bindparams(old=old, new=new)
        )
    op.execute("UPDATE genomes SET potential = json_remove(potential, '$.beauty') WHERE json_extract(potential, '$.beauty') IS NOT NULL")


def map_dwellings_back() -> None:
    op.execute(
        "UPDATE dwellings SET kind = COALESCE((SELECT built_in_key FROM dwelling_kinds WHERE dwelling_kinds.id = dwellings.dwelling_kind_id "
        "AND built_in_key IS NOT NULL), 'hut')"
    )
    op.execute(
        "UPDATE household_aggregates SET dwelling_kind = COALESCE((SELECT built_in_key FROM dwelling_kinds "
        "WHERE dwelling_kinds.id = household_aggregates.dwelling_kind_id AND built_in_key IS NOT NULL), 'hut')"
    )
    for old, new in G5_POTENTIAL:
        op.execute(
            sa.text(
                "UPDATE genomes SET potential = json_remove(json_set(potential, '$.' || :old, json_extract(potential, '$.' || :new)), '$.' || :new) "
                "WHERE json_extract(potential, '$.' || :new) IS NOT NULL"
            ).bindparams(old=old, new=new)
        )


BALANCELOOP_OLD = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
    "kind_prestige",
    "kind_substitution",
)
BALANCELOOP_NEW = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
    "kind_prestige",
    "kind_substitution",
    "policy_grievance",
    "housework_burden",
)
BALANCELOOP_RENAMED = ()
PROFESSION_OLD = (
    "soldier",
    "rider",
    "smith",
    "builder",
    "weaver",
    "healer",
    "scholar",
    "priest",
    "sorcerer",
    "merchant",
    "diplomat",
    "hunter",
    "sailor",
    "commander",
    "engineer",
    "scientist",
    "pilot",
    "technician",
    "programmer",
    "mechanic",
    "miner",
    "farmer",
    "artist",
    "administrator",
    "spacer",
)
PROFESSION_NEW = (
    "soldier",
    "rider",
    "smith",
    "builder",
    "weaver",
    "healer",
    "scholar",
    "priest",
    "sorcerer",
    "merchant",
    "diplomat",
    "hunter",
    "sailor",
    "commander",
    "engineer",
    "scientist",
    "pilot",
    "technician",
    "programmer",
    "mechanic",
    "miner",
    "farmer",
    "artist",
    "administrator",
    "spacer",
    "death_worker",
)
PROFESSION_RENAMED = ()
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
    "clone_of",
)
BONDKIND_NEW = (
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
    "godparent_of",
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
    "clone_of",
)
BONDKIND_RENAMED = ()
RETYPED = (
    ("loop_signals", "loop", "loop", BALANCELOOP_OLD, BALANCELOOP_NEW, BALANCELOOP_RENAMED, False),
    ("profession_kinds", "base", "base", PROFESSION_OLD, PROFESSION_NEW, PROFESSION_RENAMED, True),
    ("mortal_profiles", "profession", "profession", PROFESSION_OLD, PROFESSION_NEW, PROFESSION_RENAMED, True),
    ("bonds", "kind", "kind", BONDKIND_OLD, BONDKIND_NEW, BONDKIND_RENAMED, False),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def alter(table: str, column: str, name: str, before: tuple[str, ...], after: tuple[str, ...], *, nullable: bool) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(after, name), existing_nullable=nullable)


def retype(forward: bool) -> None:
    for table, column, name, old, new, renamed, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        wide = tuple(dict.fromkeys((*before, *after)))
        alter(table, column, name, before, wide, nullable=nullable)
        for first, second in renamed:
            source, target = (first, second) if forward else (second, first)
            op.execute(sa.text(f"UPDATE {table} SET {column} = :target WHERE {column} = :source").bindparams(target=target, source=source))
        gone = ", ".join(f"'{value}'" for value in wide if value not in after)
        if gone:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})" if nullable else f"DELETE FROM {table} WHERE {column} IN ({gone})")
        alter(table, column, name, wide, after, nullable=nullable)


COPY_COLUMNS = ("species_entity_id", "product", "commodity", "material", "world_material_id", "rate")
PRODUCT_PARTS = {
    "meat": "flesh",
    "hide": "hide",
    "bone": "bone",
    "ivory": "tusk",
    "chitin": "shell",
    "venom": "venom",
    "silk": "fibre",
    "wool": "fibre",
    "milk": "milk",
    "feathers": "feathers",
    "magic_reagents": "reagent",
    "dragonbone": "bone",
    "eggs": "eggs",
    "grain": "seed",
    "tuber": "root",
    "fibre": "fibre",
    "dye": "dye",
    "timber": "wood",
    "fruit": "fruit",
    "herb": "leaf",
    "brew_base": "seed",
    "reagent": "reagent",
    "poison": "toxin",
}


def copy_products(source: str, target: str) -> None:
    columns = ", ".join(COPY_COLUMNS)
    extra = ", locked" if target == "species_products" else ""
    value = ", '[]'" if target == "species_products" else ""
    op.execute(f"INSERT INTO {target} ({columns}{extra}) SELECT {columns}{value} FROM {source}")


def upgrade() -> None:
    retype(True)
    op.execute("UPDATE entities SET subtype = 'animated work' WHERE subtype = 'golem'")
    op.execute("UPDATE entities SET subtype = 'merged species' WHERE subtype = 'chimera'")
    op.execute("UPDATE ledger_entries SET tool = 'hinder_return' WHERE tool = 'scatter_bones'")
    op.execute("UPDATE ledger_entries SET tool = 'sibling:hinder_return' WHERE tool = 'sibling:scatter'")
    op.execute("UPDATE ledger_entries SET tool = 'species:merge' WHERE tool = 'species:chimera'")
    op.execute("UPDATE chronicle SET template_key = 'creatures.species_merged' WHERE template_key = 'creatures.chimera_woven'")
    op.execute("UPDATE chronicle SET template_key = 'tools.mortal.species_merged' WHERE template_key = 'tools.mortal.chimera'")
    op.execute("UPDATE chronicle SET template_key = 'gods.death.return_hindered' WHERE template_key = 'gods.death.scatter'")
    op.execute("UPDATE chronicle SET template_key = 'transform.dead_god' WHERE template_key = 'transform.god_corpse'")
    op.execute(
        "UPDATE law_profiles SET params = json_remove(json_set(params, '$.merging', json_extract(params, '$.chimera')), '$.chimera') WHERE kind = 'living_craft_law' AND json_extract(params, '$.chimera') IS NOT NULL"
    )
    op.execute("UPDATE OR IGNORE preferences SET target = 'musical' WHERE kind = 'art_form' AND target = 'song'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'verbal' WHERE kind = 'art_form' AND target = 'epic_poem'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'ritual_performance' WHERE kind = 'art_form' AND target = 'play'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'solid_image' WHERE kind = 'art_form' AND target = 'statue'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'fresco'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'textile_image' WHERE kind = 'art_form' AND target = 'tapestry'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'mosaic'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'verbal' WHERE kind = 'art_form' AND target = 'book'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'movement' WHERE kind = 'art_form' AND target = 'dance'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'musical' WHERE kind = 'art_form' AND target = 'music'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'solid_image' WHERE kind = 'art_form' AND target = 'carving'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'built' WHERE kind = 'art_form' AND target = 'architecture_ornament'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'verbal' WHERE kind = 'art_form' AND target = 'poetry'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'ritual_performance' WHERE kind = 'art_form' AND target = 'theatre'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'painting'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'solid_image' WHERE kind = 'art_form' AND target = 'sculpture'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'built' WHERE kind = 'art_form' AND target = 'architecture_style'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'textile_image' WHERE kind = 'art_form' AND target = 'textile'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'calligraphy'")
    op.execute(
        "DELETE FROM preferences WHERE kind = 'art_form' AND target IN ('song', 'epic_poem', 'play', 'statue', 'fresco', 'tapestry', 'mosaic', 'book', 'dance', 'music', 'carving', 'architecture_ornament', 'poetry', 'theatre', 'painting', 'sculpture', 'architecture_style', 'textile', 'calligraphy')"
    )
    op.execute(
        "UPDATE afterlife_strata SET criteria = replace(replace(criteria, '\"burning\"', '\"cremation\"'), '\"exposure\"', '\"sky_burial\"') WHERE criteria IS NOT NULL"
    )
    op.execute("UPDATE entities SET subtype = 'sworn warrior' WHERE subtype = 'knight'")
    op.execute("UPDATE entities SET subtype = 'ascetic' WHERE subtype = 'monk'")
    op.create_table(
        "child_recognitions",
        sa.Column("child_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "path",
            sa.Enum("recognition", "adoption", "payment", "rite", "none", name="path", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("sponsor_node_id", sa.Integer(), nullable=True),
        sa.Column("recognized_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("recognized_epoch >= 0", name=op.f("ck_child_recognitions_recognized_epoch_min")),
        sa.ForeignKeyConstraint(["child_node_id"], ["nodes.id"], name=op.f("fk_child_recognitions_child_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_node_id"], ["nodes.id"], name=op.f("fk_child_recognitions_sponsor_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("child_node_id", name=op.f("pk_child_recognitions")),
    )
    op.create_table(
        "endowments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("founder_node_id", sa.Integer(), nullable=False),
        sa.Column("beneficiary_node_id", sa.Integer(), nullable=False),
        sa.Column("trustee_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "purpose",
            sa.Enum(
                "relief",
                "learning",
                "worship",
                "health",
                "works",
                "art",
                "kin",
                "memory",
                "research",
                name="purpose",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "capital_kind",
            sa.Enum("land", "coin", "shares", "rents", name="capital_kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("capital", sa.Integer(), nullable=False),
        sa.Column("income", sa.Integer(), nullable=False),
        sa.Column("skimmed", sa.Integer(), nullable=False),
        sa.Column(
            "terms", sa.Enum("perpetual", "for_a_term", "conditional", name="terms", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("ends_epoch", sa.Integer(), nullable=True),
        sa.Column("sheltered", sa.Boolean(), nullable=False),
        sa.Column(
            "state", sa.Enum("serving", "captured", "confiscated", "ended", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("outlived", sa.Boolean(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capital >= 0", name=op.f("ck_endowments_capital_min")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_endowments_founded_epoch_min")),
        sa.CheckConstraint("income >= 0", name=op.f("ck_endowments_income_min")),
        sa.CheckConstraint("skimmed >= 0", name=op.f("ck_endowments_skimmed_min")),
        sa.ForeignKeyConstraint(["beneficiary_node_id"], ["nodes.id"], name=op.f("fk_endowments_beneficiary_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["founder_node_id"], ["nodes.id"], name=op.f("fk_endowments_founder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trustee_node_id"], ["nodes.id"], name=op.f("fk_endowments_trustee_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_endowments")),
    )
    with op.batch_alter_table("endowments", schema=None) as batch_op:
        batch_op.create_index("ix_endowments_beneficiary", ["beneficiary_node_id"], unique=False)
        batch_op.create_index("ix_endowments_founder", ["founder_node_id"], unique=False)

    op.create_table(
        "leases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=False),
        sa.Column("lessee_node_id", sa.Integer(), nullable=False),
        sa.Column("thing_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "thing",
            sa.Enum(
                "land",
                "dwelling",
                "structure",
                "vessel",
                "vehicle",
                "item",
                "made_mind",
                "animal",
                name="thing",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("rent", sa.Integer(), nullable=False),
        sa.Column("term_epochs", sa.Integer(), nullable=False),
        sa.Column("upkeep", sa.Enum("owner", "lessee", "shared", name="upkeep", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("on_default", sa.Enum("eviction", "court", "debt", name="on_default", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("signed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("rent >= 0", name=op.f("ck_leases_rent_min")),
        sa.CheckConstraint("signed_epoch >= 0", name=op.f("ck_leases_signed_epoch_min")),
        sa.CheckConstraint("term_epochs >= 1", name=op.f("ck_leases_term_epochs_min")),
        sa.ForeignKeyConstraint(["lessee_node_id"], ["nodes.id"], name=op.f("fk_leases_lessee_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_leases_owner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thing_node_id"], ["nodes.id"], name=op.f("fk_leases_thing_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leases")),
    )
    with op.batch_alter_table("leases", schema=None) as batch_op:
        batch_op.create_index("ix_leases_lessee", ["lessee_node_id"], unique=False)
        batch_op.create_index("ix_leases_owner", ["owner_node_id"], unique=False)

    op.create_table(
        "leisure_pursuits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "conversation",
                "games",
                "sport",
                "music",
                "crafts",
                "collecting",
                "reading",
                "excursion",
                "tourism",
                "drinking",
                "worship_extra",
                "rest",
                "media",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("venue_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_leisure_pursuits_share_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_leisure_pursuits_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venue_node_id"], ["nodes.id"], name=op.f("fk_leisure_pursuits_venue_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leisure_pursuits")),
        sa.UniqueConstraint("holder_node_id", "kind", name="uq_leisure_pursuits_holder_kind"),
    )
    with op.batch_alter_table("leisure_pursuits", schema=None) as batch_op:
        batch_op.create_index("ix_leisure_pursuits_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_leisure_pursuits_venue", ["venue_node_id"], unique=False)

    op.create_table(
        "pedagogy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "theory",
            sa.Enum(
                "rote",
                "dialectic",
                "apprenticeship",
                "discovery",
                "ritual_transmission",
                "examination",
                "network_learning",
                "mind_transfer",
                name="theory",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("founder_node_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("depth BETWEEN 0 AND 100", name=op.f("ck_pedagogy_depth_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_pedagogy_founded_epoch_min")),
        sa.ForeignKeyConstraint(["founder_node_id"], ["nodes.id"], name=op.f("fk_pedagogy_founder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_pedagogy_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pedagogy")),
    )
    with op.batch_alter_table("pedagogy", schema=None) as batch_op:
        batch_op.create_index("ix_pedagogy_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "population_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "aim",
            sa.Enum(
                "grow",
                "hold",
                "shrink",
                "rebalance_age",
                "rebalance_class",
                "settle_land",
                "empty_land",
                "keep_kind",
                "mix_kinds",
                "none",
                name="aim",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("enforcement", sa.Integer(), nullable=False),
        sa.Column("baseline", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("reviewed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("baseline >= 0", name=op.f("ck_population_policies_baseline_min")),
        sa.CheckConstraint("enforcement BETWEEN 0 AND 100", name=op.f("ck_population_policies_enforcement_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_population_policies_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_population_policies_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_population_policies_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_population_policies_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_population_policies")),
    )
    with op.batch_alter_table("population_policies", schema=None) as batch_op:
        batch_op.create_index("ix_population_policies_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "professions_of_value",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("acts_against", sa.Integer(), nullable=False),
        sa.Column("gap", sa.Integer(), nullable=False),
        sa.Column("knowers", sa.Integer(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("last_act_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("acts_against >= 0", name=op.f("ck_professions_of_value_acts_against_min")),
        sa.CheckConstraint("gap BETWEEN 0 AND 100", name=op.f("ck_professions_of_value_gap_range")),
        sa.CheckConstraint("knowers >= 0", name=op.f("ck_professions_of_value_knowers_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_professions_of_value_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_professions_of_value_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professions_of_value")),
        sa.UniqueConstraint("holder_node_id", "axis", name="uq_professions_of_value_holder_axis"),
    )
    with op.batch_alter_table("professions_of_value", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_professions_of_value_holder_node_id"), ["holder_node_id"], unique=False)

    op.create_table(
        "domestic_service",
        sa.Column("servant_node_id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("terms", sa.Enum("wage", "board", "bound", name="terms", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("wage", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_domestic_service_since_epoch_min")),
        sa.CheckConstraint("wage >= 0", name=op.f("ck_domestic_service_wage_min")),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], name=op.f("fk_domestic_service_household_id_households"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["servant_node_id"], ["nodes.id"], name=op.f("fk_domestic_service_servant_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("servant_node_id", name=op.f("pk_domestic_service")),
    )
    with op.batch_alter_table("domestic_service", schema=None) as batch_op:
        batch_op.create_index("ix_domestic_service_household", ["household_id"], unique=False)

    op.create_table(
        "housework",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column(
            "duty",
            sa.Enum(
                "food",
                "water",
                "fuel",
                "cleaning",
                "textiles",
                "childcare",
                "eldercare",
                "animals",
                "repairs",
                name="duty",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("doer_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "doer_role",
            sa.Enum(
                "head",
                "spouse",
                "heir",
                "dependent",
                "carer",
                "servant",
                "ward",
                "lodger",
                name="doer_role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("load", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("load BETWEEN 0 AND 100", name=op.f("ck_housework_load_range")),
        sa.ForeignKeyConstraint(["doer_node_id"], ["nodes.id"], name=op.f("fk_housework_doer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], name=op.f("fk_housework_household_id_households"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_housework")),
        sa.UniqueConstraint("household_id", "duty", "doer_node_id", name="uq_housework_household_duty_doer"),
    )
    with op.batch_alter_table("housework", schema=None) as batch_op:
        batch_op.create_index("ix_housework_doer", ["doer_node_id"], unique=False)
        batch_op.create_index("ix_housework_household", ["household_id"], unique=False)

    op.create_table(
        "population_instruments",
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column(
            "instrument",
            sa.Enum(
                "birth_reward",
                "birth_tax",
                "union_law",
                "child_limit",
                "child_support",
                "inheritance_rule",
                "settlement_grant",
                "migration_permit",
                "migration_ban",
                "expulsion",
                "resettlement",
                "recruitment_abroad",
                "health_campaign",
                "faith_teaching",
                "made_birth",
                name="instrument",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_population_instruments_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_population_instruments_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["population_policies.id"], name=op.f("fk_population_instruments_policy_id_population_policies"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("policy_id", "instrument", name=op.f("pk_population_instruments")),
    )
    with op.batch_alter_table("population_instruments", schema=None) as batch_op:
        batch_op.create_index("ix_population_instruments_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "star_activity",
        sa.Column("star_id", sa.Integer(), nullable=False),
        sa.Column("cycle_years", sa.Integer(), nullable=False),
        sa.Column("phase", sa.Integer(), nullable=False),
        sa.Column("flare_rate", sa.Integer(), nullable=False),
        sa.Column("storm_rate", sa.Integer(), nullable=False),
        sa.Column("wind", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cycle_years >= 1", name=op.f("ck_star_activity_cycle_years_min")),
        sa.CheckConstraint("flare_rate BETWEEN 0 AND 100", name=op.f("ck_star_activity_flare_rate_range")),
        sa.CheckConstraint("phase BETWEEN 0 AND 99", name=op.f("ck_star_activity_phase_range")),
        sa.CheckConstraint("storm_rate BETWEEN 0 AND 100", name=op.f("ck_star_activity_storm_rate_range")),
        sa.CheckConstraint("wind BETWEEN 0 AND 100", name=op.f("ck_star_activity_wind_range")),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_star_activity_star_id_stars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("star_id", name=op.f("pk_star_activity")),
    )
    op.create_table(
        "space_weather_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("star_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "flare",
                "particle_storm",
                "field_storm",
                "field_reversal",
                "cosmic_ray_burst",
                "wind_surge",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("dose", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dose BETWEEN 0 AND 100", name=op.f("ck_space_weather_events_dose_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_space_weather_events_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_space_weather_events_strength_range")),
        sa.ForeignKeyConstraint(["star_id"], ["stars.id"], name=op.f("fk_space_weather_events_star_id_stars"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_space_weather_events_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_space_weather_events")),
    )
    with op.batch_alter_table("space_weather_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_space_weather_events_star_id"), ["star_id"], unique=False)
        batch_op.create_index("ix_space_weather_events_world", ["world_id"], unique=False)

    op.create_table(
        "world_fields",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("shielding", sa.Integer(), nullable=False),
        sa.Column("surface_dose", sa.Integer(), nullable=False),
        sa.Column("compass_error", sa.Integer(), nullable=False),
        sa.Column("aurora_reach", sa.Integer(), nullable=False),
        sa.Column("reversal_epoch", sa.Integer(), nullable=True),
        sa.Column("reversal_left", sa.Integer(), nullable=False),
        sa.Column("shift", sa.Integer(), nullable=False),
        sa.Column("shift_left", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("aurora_reach BETWEEN 0 AND 100", name=op.f("ck_world_fields_aurora_reach_range")),
        sa.CheckConstraint("compass_error BETWEEN 0 AND 100", name=op.f("ck_world_fields_compass_error_range")),
        sa.CheckConstraint("reversal_left >= 0", name=op.f("ck_world_fields_reversal_left_min")),
        sa.CheckConstraint("shielding BETWEEN 0 AND 100", name=op.f("ck_world_fields_shielding_range")),
        sa.CheckConstraint("shift BETWEEN -100 AND 100", name=op.f("ck_world_fields_shift_range")),
        sa.CheckConstraint("shift_left >= 0", name=op.f("ck_world_fields_shift_left_min")),
        sa.CheckConstraint("surface_dose BETWEEN 0 AND 100", name=op.f("ck_world_fields_surface_dose_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_world_fields_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_world_fields")),
    )
    op.create_table(
        "body_systems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "system",
            sa.Enum(
                "breath",
                "circulation",
                "digestion",
                "regulation",
                "nerves",
                "immunity",
                "reproduction",
                "structure",
                "none",
                name="system",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("present", sa.Boolean(), nullable=False),
        sa.Column("air_need", sa.Integer(), nullable=False),
        sa.Column("gravity_max", sa.Integer(), nullable=False),
        sa.Column("cold_min", sa.Integer(), nullable=False),
        sa.Column("heat_max", sa.Integer(), nullable=False),
        sa.Column("diet_range", sa.Integer(), nullable=False),
        sa.Column("sleep_need", sa.Integer(), nullable=False),
        sa.Column("toxin_tolerance", sa.Integer(), nullable=False),
        sa.Column("strained", sa.Boolean(), nullable=False),
        sa.Column("failed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("air_need BETWEEN 0 AND 100", name=op.f("ck_body_systems_air_need_range")),
        sa.CheckConstraint("cold_min BETWEEN 0 AND 100", name=op.f("ck_body_systems_cold_min_range")),
        sa.CheckConstraint("diet_range BETWEEN 0 AND 100", name=op.f("ck_body_systems_diet_range_range")),
        sa.CheckConstraint("gravity_max BETWEEN 0 AND 100", name=op.f("ck_body_systems_gravity_max_range")),
        sa.CheckConstraint("heat_max BETWEEN 0 AND 100", name=op.f("ck_body_systems_heat_max_range")),
        sa.CheckConstraint("sleep_need BETWEEN 0 AND 100", name=op.f("ck_body_systems_sleep_need_range")),
        sa.CheckConstraint("toxin_tolerance BETWEEN 0 AND 100", name=op.f("ck_body_systems_toxin_tolerance_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_body_systems_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_body_systems")),
        sa.UniqueConstraint("holder_entity_id", "system", name="uq_body_systems_holder_system"),
    )
    with op.batch_alter_table("body_systems", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_body_systems_holder_entity_id"), ["holder_entity_id"], unique=False)

    op.create_table(
        "care_customs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "wash_frequency",
            sa.Enum("none", "by_rite", "seasonal", "weekly", "daily", name="wash_frequency", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "wash_place",
            sa.Enum("home", "bath_house", "river", "rite", name="wash_place", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("grooming", sa.Integer(), nullable=False),
        sa.Column("cleanliness", sa.Integer(), nullable=False),
        sa.Column(
            "waste_handling",
            sa.Enum(
                "none", "pits", "carried_out", "sewers", "burned", "composted", name="waste_handling", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cleanliness BETWEEN 0 AND 100", name=op.f("ck_care_customs_cleanliness_range")),
        sa.CheckConstraint("grooming BETWEEN 0 AND 100", name=op.f("ck_care_customs_grooming_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_care_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_care_customs")),
    )
    op.create_table(
        "child_standing",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("naming_age", sa.Integer(), nullable=False),
        sa.Column("personhood_age", sa.Integer(), nullable=False),
        sa.Column("work_age", sa.Integer(), nullable=False),
        sa.Column("responsibility_age", sa.Integer(), nullable=False),
        sa.Column("marriage_age", sa.Integer(), nullable=False),
        sa.Column("labour_share", sa.Integer(), nullable=False),
        sa.Column("protected", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("labour_share BETWEEN 0 AND 100", name=op.f("ck_child_standing_labour_share_range")),
        sa.CheckConstraint("marriage_age BETWEEN 0 AND 100", name=op.f("ck_child_standing_marriage_age_range")),
        sa.CheckConstraint("naming_age BETWEEN 0 AND 100", name=op.f("ck_child_standing_naming_age_range")),
        sa.CheckConstraint("personhood_age BETWEEN 0 AND 100", name=op.f("ck_child_standing_personhood_age_range")),
        sa.CheckConstraint("responsibility_age BETWEEN 0 AND 100", name=op.f("ck_child_standing_responsibility_age_range")),
        sa.CheckConstraint("work_age BETWEEN 0 AND 100", name=op.f("ck_child_standing_work_age_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_child_standing_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_child_standing")),
    )
    op.create_table(
        "coasts",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "cliff", "beach", "delta", "marsh", "reef", "ice_shelf", "fjord", "lagoon", name="form", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("harbour_silting", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("harbour_silting BETWEEN 0 AND 100", name=op.f("ck_coasts_harbour_silting_range")),
        sa.CheckConstraint("progress BETWEEN -100 AND 100", name=op.f("ck_coasts_progress_range")),
        sa.CheckConstraint("rate BETWEEN -100 AND 100", name=op.f("ck_coasts_rate_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_coasts_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_coasts")),
    )
    op.create_table(
        "death_work",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "washer",
                "preparer",
                "keeper_of_remains",
                "officiant",
                "mourner",
                "record_keeper",
                "carrier",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("standing", sa.Enum("honoured", "plain", "avoided", name="standing", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("purity", sa.Integer(), nullable=False),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("workers", sa.Integer(), nullable=False),
        sa.Column("guild_node_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fee >= 0", name=op.f("ck_death_work_fee_min")),
        sa.CheckConstraint("purity BETWEEN 0 AND 100", name=op.f("ck_death_work_purity_range")),
        sa.CheckConstraint("workers >= 0", name=op.f("ck_death_work_workers_min")),
        sa.ForeignKeyConstraint(["guild_node_id"], ["nodes.id"], name=op.f("fk_death_work_guild_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_death_work_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_death_work")),
        sa.UniqueConstraint("people_entity_id", "role", name="uq_death_work_people_role"),
    )
    with op.batch_alter_table("death_work", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_death_work_people_entity_id"), ["people_entity_id"], unique=False)

    op.create_table(
        "disease_agents",
        sa.Column("disease_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "agent",
            sa.Enum(
                "virus",
                "bacterium",
                "fungus",
                "parasite",
                "prion",
                "toxin",
                "deficiency",
                "spirit",
                "curse",
                "made",
                "unknown",
                name="agent",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("survival_water", sa.Integer(), nullable=False),
        sa.Column("survival_soil", sa.Integer(), nullable=False),
        sa.Column("survival_objects", sa.Integer(), nullable=False),
        sa.Column("survival_cold", sa.Integer(), nullable=False),
        sa.Column("reservoir_species_id", sa.Integer(), nullable=True),
        sa.Column(
            "overused_cure",
            sa.Enum(
                "rest_and_care",
                "herbal",
                "antimicrobial",
                "antiparasitic",
                "antitoxin",
                "nutritional",
                "rite",
                "exorcism",
                "power",
                "designed",
                name="overused_cure",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("overuse", sa.Integer(), nullable=False),
        sa.Column("identified", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("overuse BETWEEN 0 AND 100", name=op.f("ck_disease_agents_overuse_range")),
        sa.CheckConstraint("survival_cold BETWEEN 0 AND 100", name=op.f("ck_disease_agents_survival_cold_range")),
        sa.CheckConstraint("survival_objects BETWEEN 0 AND 100", name=op.f("ck_disease_agents_survival_objects_range")),
        sa.CheckConstraint("survival_soil BETWEEN 0 AND 100", name=op.f("ck_disease_agents_survival_soil_range")),
        sa.CheckConstraint("survival_water BETWEEN 0 AND 100", name=op.f("ck_disease_agents_survival_water_range")),
        sa.ForeignKeyConstraint(["disease_entity_id"], ["entities.id"], name=op.f("fk_disease_agents_disease_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reservoir_species_id"], ["entities.id"], name=op.f("fk_disease_agents_reservoir_species_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("disease_entity_id", name=op.f("pk_disease_agents")),
    )
    op.create_table(
        "facet_practices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "facet",
            sa.Enum(
                "prehistory",
                "marine_industries",
                "animal_by_products",
                "agricultural_science",
                "floriculture",
                "meat_packing",
                "confectionery",
                "cannibalism",
                "non_alcoholic_beverages",
                "beverage_industries",
                "stimulant_leaves",
                "leather_industry",
                "cordage",
                "knots_and_lashings",
                "felted_fabrics",
                "paper_industry",
                "clothing",
                "normal_garb",
                "clothing_manufacture",
                "ornament",
                "jewellery_manufacture",
                "woodworking",
                "ceramics",
                "stone_tools",
                "masonry",
                "tall_frame_building",
                "carpentry",
                "electrical_installation",
                "other_building_trades",
                "heating_and_lighting",
                "lifts_and_building_machines",
                "public_utilities",
                "parks",
                "other_facilities",
                "electric_power",
                "fission_and_fusion",
                "elastic_materials",
                "synthetic_materials",
                "paints_and_dyes",
                "fertilizers",
                "soap_and_cleaners",
                "explosives",
                "capital_goods",
                "hardware",
                "machine_industries",
                "electrical_supplies",
                "making_heating_and_lighting",
                "optics",
                "rail_equipment",
                "aircraft_industry",
                "machines",
                "electrical_machines",
                "household_machines",
                "weight_moving_machines",
                "computing",
                "other_hardware",
                "appliances",
                "apparatus",
                "division_of_labour",
                "railways",
                "navigation",
                "aircraft",
                "aviation",
                "airfields",
                "music",
                "musical_instruments",
                "spectacles",
                "status_by_sex",
                "union_payments",
                "nuptials",
                "celibacy",
                "plural_unions",
                "clans",
                "moieties",
                "forms_of_government",
                "offences_against_persons",
                "union_offences",
                "property_offences",
                "offences_against_the_state",
                "military_engineering",
                "ordnance",
                "military_vehicles",
                "military_aircraft",
                "special_military_equipment",
                "healing_rites",
                "spiritual_healers",
                "medical_personnel",
                "suicide",
                "dying",
                "cult_of_the_dead",
                "asceticism",
                "logic",
                "philosophy",
                "scientific_method",
                "humanistic_study",
                "vocational_education",
                "teachers",
                "life_stages",
                "coming_of_age",
                "roles_by_sex",
                name="facet",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 100", name=op.f("ck_facet_practices_level_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_facet_practices_since_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_facet_practices_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_facet_practices")),
        sa.UniqueConstraint("community_entity_id", "facet", name="uq_facet_practices_community_facet"),
    )
    with op.batch_alter_table("facet_practices", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_facet_practices_community_entity_id"), ["community_entity_id"], unique=False)

    op.create_table(
        "folk_knowledge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "weather",
                "sky",
                "matter",
                "land",
                "waters",
                "plants",
                "animals",
                "body",
                "illness",
                "mind",
                "society",
                "number",
                "time",
                name="domain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column(
            "holders", sa.Enum("elders", "specialists", "everyone", name="holders", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "transmission",
            sa.Enum("oral", "written", "apprenticeship", "rite", name="transmission", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accuracy BETWEEN 0 AND 100", name=op.f("ck_folk_knowledge_accuracy_range")),
        sa.CheckConstraint("depth BETWEEN 0 AND 100", name=op.f("ck_folk_knowledge_depth_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_folk_knowledge_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_folk_knowledge")),
        sa.UniqueConstraint("people_entity_id", "domain", name="uq_folk_knowledge_people_domain"),
    )
    with op.batch_alter_table("folk_knowledge", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_folk_knowledge_people_entity_id"), ["people_entity_id"], unique=False)

    op.create_table(
        "humour_styles",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "wordplay",
                "teasing",
                "satire",
                "absurd",
                "bodily",
                "irony",
                "storytelling",
                "ritual_clowning",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("mock_rulers", sa.Boolean(), nullable=False),
        sa.Column("mock_gods", sa.Boolean(), nullable=False),
        sa.Column("mock_kin", sa.Boolean(), nullable=False),
        sa.Column("mock_strangers", sa.Boolean(), nullable=False),
        sa.Column("offence_threshold", sa.Integer(), nullable=False),
        sa.Column("directness", sa.Integer(), nullable=False),
        sa.Column("silence", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("directness BETWEEN 0 AND 100", name=op.f("ck_humour_styles_directness_range")),
        sa.CheckConstraint("offence_threshold BETWEEN 0 AND 100", name=op.f("ck_humour_styles_offence_threshold_range")),
        sa.CheckConstraint("silence BETWEEN 0 AND 100", name=op.f("ck_humour_styles_silence_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_humour_styles_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_humour_styles")),
    )
    op.create_table(
        "infant_care",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "feeding",
            sa.Enum(
                "by_birth_parent",
                "by_other_nurse",
                "animal_milk",
                "prepared_food",
                "made_food",
                "none_needed",
                name="feeding",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("weaning_age", sa.Integer(), nullable=False),
        sa.Column("carry", sa.Enum("carried", "cradled", "left_tended", name="carry", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "sleeping",
            sa.Enum("with_parent", "with_siblings", "apart", "communal", name="sleeping", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "carer", sa.Enum("kin", "specialist", "community", "made_mind", name="carer", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "carer_role",
            sa.Enum(
                "parent",
                "child",
                "sibling",
                "grandparent",
                "grandchild",
                "parent_sibling_first_line",
                "parent_sibling_second_line",
                "sibling_child",
                "cousin_parallel",
                "cousin_cross",
                "parent_in_law",
                "child_in_law",
                "sibling_in_law",
                "co_spouse",
                "chosen_kin",
                "godparent",
                "sworn_kin",
                name="carer_role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weaning_age BETWEEN 0 AND 100", name=op.f("ck_infant_care_weaning_age_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_infant_care_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_infant_care")),
    )
    op.create_table(
        "intimacy_norms",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "context",
            sa.Enum(
                "before_union",
                "within_union",
                "outside_union",
                "between_any_sexes",
                "with_kin",
                "with_made_minds",
                "with_other_kinds",
                name="context",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "stance",
            sa.Enum("forbidden", "discouraged", "tolerated", "accepted", "honoured", name="stance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("enforcer", sa.Enum("kin", "faith", "law", "none", name="enforcer", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "sanction",
            sa.Enum("shaming", "fine", "shunning", "exile", "none", name="sanction", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("kin_scope", sa.Enum("close", "extended", "group", name="kin_scope", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_intimacy_norms_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "context", name=op.f("pk_intimacy_norms")),
    )
    op.create_table(
        "kin_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "lineage",
                "clan",
                "phratry",
                "moiety",
                "kindred",
                "ramage",
                "house",
                "localized_group",
                "age_linked_group",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "membership", sa.Enum("descent", "residence", "choice", name="membership", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("exogamy", sa.Integer(), nullable=False),
        sa.Column("head_node_id", sa.Integer(), nullable=True),
        sa.Column("land_region_id", sa.Integer(), nullable=True),
        sa.Column("shrine_entity_id", sa.Integer(), nullable=True),
        sa.Column("council_size", sa.Integer(), nullable=False),
        sa.Column("house_entity_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("council_size >= 0", name=op.f("ck_kin_groups_council_size_min")),
        sa.CheckConstraint("exogamy BETWEEN 0 AND 100", name=op.f("ck_kin_groups_exogamy_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_kin_groups_founded_epoch_min")),
        sa.ForeignKeyConstraint(["head_node_id"], ["nodes.id"], name=op.f("fk_kin_groups_head_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_kin_groups_house_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["land_region_id"], ["entities.id"], name=op.f("fk_kin_groups_land_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_kin_groups_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shrine_entity_id"], ["entities.id"], name=op.f("fk_kin_groups_shrine_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kin_groups")),
    )
    with op.batch_alter_table("kin_groups", schema=None) as batch_op:
        batch_op.create_index("ix_kin_groups_head", ["head_node_id"], unique=False)
        batch_op.create_index("ix_kin_groups_people", ["people_entity_id"], unique=False)

    op.create_table(
        "kin_role_duties",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "parent",
                "child",
                "sibling",
                "grandparent",
                "grandchild",
                "parent_sibling_first_line",
                "parent_sibling_second_line",
                "sibling_child",
                "cousin_parallel",
                "cousin_cross",
                "parent_in_law",
                "child_in_law",
                "sibling_in_law",
                "co_spouse",
                "chosen_kin",
                "godparent",
                "sworn_kin",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "duty",
            sa.Enum(
                "support",
                "raise",
                "teach",
                "protect",
                "avenge",
                "marry_to",
                "inherit_from",
                "mourn",
                "host",
                "obey",
                "joke_with",
                "avoid",
                name="duty",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_kin_role_duties_strength_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_kin_role_duties_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "role", "duty", name=op.f("pk_kin_role_duties")),
    )
    op.create_table(
        "legitimacy_rules",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "parent_union",
            sa.Enum("wed", "unwed", "outside_union", "unknown", name="parent_union", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("standing", sa.Enum("full", "partial", "none", name="standing", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "path",
            sa.Enum("recognition", "adoption", "payment", "rite", "none", name="path", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost BETWEEN 0 AND 100", name=op.f("ck_legitimacy_rules_cost_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_legitimacy_rules_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "parent_union", name=op.f("pk_legitimacy_rules")),
    )
    op.create_table(
        "local_climates",
        sa.Column("place_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cause", sa.Enum("valley", "slope", "water", "forest", "built", name="cause", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("heat_shift", sa.Integer(), nullable=False),
        sa.Column("humidity_shift", sa.Integer(), nullable=False),
        sa.Column("wind_shift", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("heat_shift BETWEEN -50 AND 50", name=op.f("ck_local_climates_heat_shift_range")),
        sa.CheckConstraint("humidity_shift BETWEEN -50 AND 50", name=op.f("ck_local_climates_humidity_shift_range")),
        sa.CheckConstraint("wind_shift BETWEEN -50 AND 50", name=op.f("ck_local_climates_wind_shift_range")),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_local_climates_place_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("place_entity_id", name=op.f("pk_local_climates")),
    )
    op.create_table(
        "observation_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "weather",
                "sky",
                "matter",
                "land",
                "waters",
                "plants",
                "animals",
                "body",
                "illness",
                "mind",
                "society",
                "number",
                "time",
                name="domain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "method",
            sa.Enum(
                "sight",
                "lore",
                "almanac",
                "instrument",
                "network_of_observers",
                "model",
                "network",
                "power",
                "divination",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accuracy BETWEEN 0 AND 100", name=op.f("ck_observation_methods_accuracy_range")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_observation_methods_reach_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_observation_methods_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observation_methods")),
        sa.UniqueConstraint("people_entity_id", "domain", "method", name="uq_observation_methods_people_domain_method"),
    )
    with op.batch_alter_table("observation_methods", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_observation_methods_people_entity_id"), ["people_entity_id"], unique=False)

    op.create_table(
        "plant_anatomy",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "tree",
                "shrub",
                "herb",
                "grass",
                "vine",
                "succulent",
                "aquatic",
                "moss_like",
                "fungus_like",
                "colonial",
                "made",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "reproduction",
            sa.Enum(
                "wind_seed", "animal_seed", "spore", "runner", "cutting", "made", name="reproduction", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("lifespan_years", sa.Integer(), nullable=False),
        sa.Column("growth_months", sa.Integer(), nullable=False),
        sa.Column("first_harvest_years", sa.Integer(), nullable=False),
        sa.Column("domesticated", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("first_harvest_years >= 0", name=op.f("ck_plant_anatomy_first_harvest_years_min")),
        sa.CheckConstraint("growth_months BETWEEN 1 AND 12", name=op.f("ck_plant_anatomy_growth_months_range")),
        sa.CheckConstraint("lifespan_years >= 1", name=op.f("ck_plant_anatomy_lifespan_years_min")),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_plant_anatomy_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("species_entity_id", name=op.f("pk_plant_anatomy")),
    )
    op.create_table(
        "plant_parts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "part",
            sa.Enum(
                "root",
                "tuber",
                "stem",
                "wood",
                "bark",
                "leaf",
                "flower",
                "fruit",
                "seed",
                "sap",
                "fibre",
                "spore",
                name="part",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
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
            nullable=True,
        ),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_plant_parts_share_range")),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_plant_parts_species_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plant_parts")),
        sa.UniqueConstraint("species_entity_id", "part", name="uq_plant_parts_species_part"),
    )
    with op.batch_alter_table("plant_parts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_plant_parts_species_entity_id"), ["species_entity_id"], unique=False)

    op.create_table(
        "public_works",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("place_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "road",
                "bridge",
                "canal",
                "rail_line",
                "aqueduct",
                "dam",
                "drainage",
                "harbour_works",
                "walls",
                "granary_system",
                "sewer",
                "power_line",
                "network_line",
                "terraforming_stage",
                "megastructure_stage",
                "grown_works",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "labour",
            sa.Enum("paid", "corvee", "bound", "made_minds", "constructs", name="labour", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stages", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("budget", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("building", "finished", "failed", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("begun_epoch", sa.Integer(), nullable=False),
        sa.Column("finished_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("begun_epoch >= 0", name=op.f("ck_public_works_begun_epoch_min")),
        sa.CheckConstraint("budget >= 0", name=op.f("ck_public_works_budget_min")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_public_works_condition_range")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_public_works_progress_range")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_public_works_quality_range")),
        sa.CheckConstraint("stage BETWEEN 0 AND 20", name=op.f("ck_public_works_stage_range")),
        sa.CheckConstraint("stages BETWEEN 1 AND 20", name=op.f("ck_public_works_stages_range")),
        sa.ForeignKeyConstraint(["place_node_id"], ["nodes.id"], name=op.f("fk_public_works_place_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_public_works_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_public_works")),
    )
    with op.batch_alter_table("public_works", schema=None) as batch_op:
        batch_op.create_index("ix_public_works_place", ["place_node_id"], unique=False)
        batch_op.create_index("ix_public_works_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "record_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "written",
                "printed",
                "image",
                "sound",
                "moving_image",
                "signal",
                "network",
                "living",
                "crafted",
                "mental",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column("durability", sa.Integer(), nullable=False),
        sa.Column("copy_cost", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("technique_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "material",
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
                "great_bone",
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
                "mud_brick",
                "fired_brick",
                "dressed_stone",
                "rubble",
                "lime_mortar",
                "hydraulic_concrete",
                "thatch",
                "tile",
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("copy_cost >= 0", name=op.f("ck_record_media_copy_cost_min")),
        sa.CheckConstraint("durability BETWEEN 0 AND 100", name=op.f("ck_record_media_durability_range")),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_record_media_fidelity_range")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_record_media_reach_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_record_media_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["technique_entity_id"], ["entities.id"], name=op.f("fk_record_media_technique_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_media")),
    )
    with op.batch_alter_table("record_media", schema=None) as batch_op:
        batch_op.create_index("ix_record_media_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "region_cryosphere",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("ice_months", sa.Integer(), nullable=False),
        sa.Column("ice_thickness", sa.Integer(), nullable=False),
        sa.Column("frozen_depth", sa.Integer(), nullable=False),
        sa.Column("thaw_months", sa.Integer(), nullable=False),
        sa.Column("snowpack", sa.Integer(), nullable=False),
        sa.Column("melt_month", sa.Integer(), nullable=False),
        sa.Column("glacier_extent", sa.Integer(), nullable=False),
        sa.Column("glacier_trend", sa.Integer(), nullable=False),
        sa.Column("ice_shift", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("frozen_depth BETWEEN 0 AND 100", name=op.f("ck_region_cryosphere_frozen_depth_range")),
        sa.CheckConstraint("glacier_extent BETWEEN 0 AND 100", name=op.f("ck_region_cryosphere_glacier_extent_range")),
        sa.CheckConstraint("glacier_trend BETWEEN -100 AND 100", name=op.f("ck_region_cryosphere_glacier_trend_range")),
        sa.CheckConstraint("ice_months BETWEEN 0 AND 12", name=op.f("ck_region_cryosphere_ice_months_range")),
        sa.CheckConstraint("ice_shift BETWEEN -12 AND 12", name=op.f("ck_region_cryosphere_ice_shift_range")),
        sa.CheckConstraint("ice_thickness BETWEEN 0 AND 100", name=op.f("ck_region_cryosphere_ice_thickness_range")),
        sa.CheckConstraint("melt_month BETWEEN 0 AND 11", name=op.f("ck_region_cryosphere_melt_month_range")),
        sa.CheckConstraint("snowpack BETWEEN 0 AND 100", name=op.f("ck_region_cryosphere_snowpack_range")),
        sa.CheckConstraint("thaw_months BETWEEN 0 AND 12", name=op.f("ck_region_cryosphere_thaw_months_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_region_cryosphere_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_region_cryosphere")),
    )
    op.create_table(
        "reproductive_courses",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "cycle_custom",
            sa.Enum("seclusion", "purity_rules", "none", name="cycle_custom", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("gestation_months", sa.Integer(), nullable=False),
        sa.Column("risk", sa.Integer(), nullable=False),
        sa.Column(
            "chief_complication",
            sa.Enum(
                "position",
                "bleeding",
                "fever",
                "early",
                "late",
                "multiple",
                "none",
                name="chief_complication",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "postnatal",
            sa.Enum(
                "rest_period",
                "seclusion",
                "kin_care",
                "specialist_care",
                "rite",
                "none",
                name="postnatal",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("rest_months", sa.Integer(), nullable=False),
        sa.Column(
            "attendant",
            sa.Enum("kin", "specialist", "healer", "made_mind", "none", name="attendant", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "birth_place",
            sa.Enum("home", "birth_house", "sacred_site", "apart", "anywhere", name="birth_place", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("gestation_months BETWEEN 1 AND 240", name=op.f("ck_reproductive_courses_gestation_months_range")),
        sa.CheckConstraint("rest_months >= 0", name=op.f("ck_reproductive_courses_rest_months_min")),
        sa.CheckConstraint("risk BETWEEN 0 AND 100", name=op.f("ck_reproductive_courses_risk_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_reproductive_courses_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_reproductive_courses")),
    )
    op.create_table(
        "restraint_customs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("clergy", "ascetic", "warrior", "ruler", "everyone", name="role", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "occasion",
            sa.Enum("always", "before_battle", "season", "rite", name="occasion", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_restraint_customs_strength_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_restraint_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restraint_customs")),
    )
    with op.batch_alter_table("restraint_customs", schema=None) as batch_op:
        batch_op.create_index("ix_restraint_customs_people", ["people_entity_id"], unique=False)

    op.create_table(
        "sediment_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_region_id", sa.Integer(), nullable=False),
        sa.Column("sink_region_id", sa.Integer(), nullable=False),
        sa.Column(
            "carrier", sa.Enum("river", "wind", "ice", "wave", "slope", name="carrier", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "kind", sa.Enum("silt", "sand", "gravel", "volcanic", "organic", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("load", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("load BETWEEN 0 AND 100", name=op.f("ck_sediment_flows_load_range")),
        sa.ForeignKeyConstraint(["sink_region_id"], ["entities.id"], name=op.f("fk_sediment_flows_sink_region_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_region_id"], ["entities.id"], name=op.f("fk_sediment_flows_source_region_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sediment_flows")),
    )
    with op.batch_alter_table("sediment_flows", schema=None) as batch_op:
        batch_op.create_index("ix_sediment_flows_sink", ["sink_region_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sediment_flows_source_region_id"), ["source_region_id"], unique=False)

    op.create_table(
        "sensitivities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "to_food",
                "to_plant",
                "to_animal",
                "to_material",
                "to_substance",
                "to_light",
                "to_sound",
                "to_power",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "trigger_commodity",
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
                name="trigger_commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("trigger_entity_id", sa.Integer(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_sensitivities_severity_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_sensitivities_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trigger_entity_id"], ["entities.id"], name=op.f("fk_sensitivities_trigger_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sensitivities")),
    )
    with op.batch_alter_table("sensitivities", schema=None) as batch_op:
        batch_op.create_index("ix_sensitivities_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "shops",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("structure_entity_id", sa.Integer(), nullable=True),
        sa.Column("keeper_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "stall",
                "shop",
                "house_trade",
                "peddler",
                "market_hall",
                "warehouse_outlet",
                "order_house",
                "network_store",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("margin", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("credit", sa.Integer(), nullable=False),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("credit >= 0", name=op.f("ck_shops_credit_min")),
        sa.CheckConstraint("margin BETWEEN 0 AND 200", name=op.f("ck_shops_margin_range")),
        sa.CheckConstraint("opened_epoch >= 0", name=op.f("ck_shops_opened_epoch_min")),
        sa.CheckConstraint("stock >= 0", name=op.f("ck_shops_stock_min")),
        sa.ForeignKeyConstraint(["keeper_node_id"], ["nodes.id"], name=op.f("fk_shops_keeper_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_shops_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_shops_structure_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shops")),
    )
    with op.batch_alter_table("shops", schema=None) as batch_op:
        batch_op.create_index("ix_shops_keeper", ["keeper_node_id"], unique=False)
        batch_op.create_index("ix_shops_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "socialization",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("example", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.Integer(), nullable=False),
        sa.Column("praise", sa.Integer(), nullable=False),
        sa.Column("shame", sa.Integer(), nullable=False),
        sa.Column("punishment", sa.Integer(), nullable=False),
        sa.Column("ritual_ordeal", sa.Integer(), nullable=False),
        sa.Column("storytelling", sa.Integer(), nullable=False),
        sa.Column("play", sa.Integer(), nullable=False),
        sa.Column("apprenticeship", sa.Integer(), nullable=False),
        sa.Column("schooling", sa.Integer(), nullable=False),
        sa.Column("peer_group", sa.Integer(), nullable=False),
        sa.Column("age_set", sa.Integer(), nullable=False),
        sa.Column("aim_independence", sa.Integer(), nullable=False),
        sa.Column("aim_obedience", sa.Integer(), nullable=False),
        sa.Column("aim_aggression", sa.Integer(), nullable=False),
        sa.Column("aim_restraint", sa.Integer(), nullable=False),
        sa.Column("aim_cooperation", sa.Integer(), nullable=False),
        sa.Column("aim_piety", sa.Integer(), nullable=False),
        sa.Column("aim_craft", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("age_set BETWEEN 0 AND 100", name=op.f("ck_socialization_age_set_range")),
        sa.CheckConstraint("aim_aggression BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_aggression_range")),
        sa.CheckConstraint("aim_cooperation BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_cooperation_range")),
        sa.CheckConstraint("aim_craft BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_craft_range")),
        sa.CheckConstraint("aim_independence BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_independence_range")),
        sa.CheckConstraint("aim_obedience BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_obedience_range")),
        sa.CheckConstraint("aim_piety BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_piety_range")),
        sa.CheckConstraint("aim_restraint BETWEEN 0 AND 100", name=op.f("ck_socialization_aim_restraint_range")),
        sa.CheckConstraint("apprenticeship BETWEEN 0 AND 100", name=op.f("ck_socialization_apprenticeship_range")),
        sa.CheckConstraint("example BETWEEN 0 AND 100", name=op.f("ck_socialization_example_range")),
        sa.CheckConstraint("instruction BETWEEN 0 AND 100", name=op.f("ck_socialization_instruction_range")),
        sa.CheckConstraint("peer_group BETWEEN 0 AND 100", name=op.f("ck_socialization_peer_group_range")),
        sa.CheckConstraint("play BETWEEN 0 AND 100", name=op.f("ck_socialization_play_range")),
        sa.CheckConstraint("praise BETWEEN 0 AND 100", name=op.f("ck_socialization_praise_range")),
        sa.CheckConstraint("punishment BETWEEN 0 AND 100", name=op.f("ck_socialization_punishment_range")),
        sa.CheckConstraint("ritual_ordeal BETWEEN 0 AND 100", name=op.f("ck_socialization_ritual_ordeal_range")),
        sa.CheckConstraint("schooling BETWEEN 0 AND 100", name=op.f("ck_socialization_schooling_range")),
        sa.CheckConstraint("shame BETWEEN 0 AND 100", name=op.f("ck_socialization_shame_range")),
        sa.CheckConstraint("storytelling BETWEEN 0 AND 100", name=op.f("ck_socialization_storytelling_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_socialization_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_socialization")),
    )
    op.create_table(
        "space_norms",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("distance", sa.Enum("close", "arm", "wide", name="distance", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "touch", sa.Enum("open", "kin_only", "sparing", "forbidden", name="touch", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "posture",
            sa.Enum("stand", "sit_floor", "sit_raised", "kneel", "recline", name="posture", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_space_norms_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_space_norms")),
    )
    op.create_table(
        "speeches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("speaker_node_id", sa.Integer(), nullable=False),
        sa.Column("place_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "venue",
            sa.Enum("assembly", "court", "temple", "square", "school", "camp", "outlet", name="venue", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "aim",
            sa.Enum("persuade", "teach", "mock", "mourn", "rally", "defend", "accuse", name="aim", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("audience_node_id", sa.Integer(), nullable=True),
        sa.Column("skill", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("effect", sa.Integer(), nullable=False),
        sa.Column("heard", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("effect BETWEEN -100 AND 100", name=op.f("ck_speeches_effect_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_speeches_epoch_min")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_speeches_reach_range")),
        sa.CheckConstraint("skill BETWEEN 0 AND 100", name=op.f("ck_speeches_skill_range")),
        sa.ForeignKeyConstraint(["audience_node_id"], ["nodes.id"], name=op.f("fk_speeches_audience_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_speeches_place_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_node_id"], ["nodes.id"], name=op.f("fk_speeches_speaker_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_speeches")),
    )
    with op.batch_alter_table("speeches", schema=None) as batch_op:
        batch_op.create_index("ix_speeches_place", ["place_entity_id"], unique=False)
        batch_op.create_index("ix_speeches_speaker", ["speaker_node_id"], unique=False)

    op.create_table(
        "state_enterprises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "sector",
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
                name="sector",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "form",
            sa.Enum(
                "monopoly",
                "royal_works",
                "state_company",
                "licence_holder",
                "arsenal",
                "mint",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "management", sa.Enum("official", "company", "made_mind", name="management", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("manager_node_id", sa.Integer(), nullable=True),
        sa.Column("output", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Integer(), nullable=False),
        sa.Column("corruption", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("corruption BETWEEN 0 AND 100", name=op.f("ck_state_enterprises_corruption_range")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_state_enterprises_founded_epoch_min")),
        sa.CheckConstraint("output >= 0", name=op.f("ck_state_enterprises_output_min")),
        sa.CheckConstraint("revenue >= 0", name=op.f("ck_state_enterprises_revenue_min")),
        sa.ForeignKeyConstraint(["manager_node_id"], ["nodes.id"], name=op.f("fk_state_enterprises_manager_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_state_enterprises_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_state_enterprises")),
    )
    with op.batch_alter_table("state_enterprises", schema=None) as batch_op:
        batch_op.create_index("ix_state_enterprises_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "supply_tiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market_entity_id", sa.Integer(), nullable=False),
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
            nullable=True,
        ),
        sa.Column("tier", sa.Enum("producer", "wholesale", "retail", name="tier", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("margin", sa.Integer(), nullable=False),
        sa.Column("cornered", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("margin BETWEEN 0 AND 200", name=op.f("ck_supply_tiers_margin_range")),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_supply_tiers_share_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_supply_tiers_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_entity_id"], ["entities.id"], name=op.f("fk_supply_tiers_market_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supply_tiers")),
    )
    with op.batch_alter_table("supply_tiers", schema=None) as batch_op:
        batch_op.create_index("ix_supply_tiers_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_supply_tiers_market", ["market_entity_id"], unique=False)

    op.create_table(
        "weather_works",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("downwind_region_id", sa.Integer(), nullable=True),
        sa.Column(
            "method",
            sa.Enum(
                "rite", "power", "seeding", "diversion", "made_structure", "living_craft", name="method", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("aim", sa.Enum("rain", "dry", "calm", "cold", "warm", name="aim", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("epochs_left", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_weather_works_cost_min")),
        sa.CheckConstraint("epochs_left >= 0", name=op.f("ck_weather_works_epochs_left_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_weather_works_strength_range")),
        sa.ForeignKeyConstraint(["downwind_region_id"], ["entities.id"], name=op.f("fk_weather_works_downwind_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_weather_works_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_weather_works_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weather_works")),
    )
    with op.batch_alter_table("weather_works", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_weather_works_holder_node_id"), ["holder_node_id"], unique=False)
        batch_op.create_index("ix_weather_works_region", ["region_entity_id"], unique=False)

    op.create_table(
        "youth_standing",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("youth_from", sa.Integer(), nullable=False),
        sa.Column("youth_to", sa.Integer(), nullable=False),
        sa.Column(
            "place",
            sa.Enum(
                "youth_house",
                "household",
                "school",
                "service",
                "apprenticeship",
                "wandering",
                name="place",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("freedom", sa.Integer(), nullable=False),
        sa.Column("duty", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("duty BETWEEN 0 AND 100", name=op.f("ck_youth_standing_duty_range")),
        sa.CheckConstraint("freedom BETWEEN 0 AND 100", name=op.f("ck_youth_standing_freedom_range")),
        sa.CheckConstraint("youth_from BETWEEN 0 AND 200", name=op.f("ck_youth_standing_youth_from_range")),
        sa.CheckConstraint("youth_to BETWEEN 0 AND 200", name=op.f("ck_youth_standing_youth_to_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_youth_standing_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_youth_standing")),
    )
    op.create_table(
        "folk_classes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "domain",
            sa.Enum(
                "weather",
                "sky",
                "matter",
                "land",
                "waters",
                "plants",
                "animals",
                "body",
                "illness",
                "mind",
                "society",
                "number",
                "time",
                name="domain",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("grouped_node_id", sa.Integer(), nullable=True),
        sa.Column("material_id", sa.Integer(), nullable=True),
        sa.Column(
            "taken_as",
            sa.Enum(
                "food",
                "medicine",
                "poison",
                "danger",
                "harmless",
                "curse",
                "omen",
                "sacred",
                name="taken_as",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("misclassified", sa.Boolean(), nullable=False),
        sa.Column("learned_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("learned_epoch >= 0", name=op.f("ck_folk_classes_learned_epoch_min")),
        sa.ForeignKeyConstraint(["grouped_node_id"], ["nodes.id"], name=op.f("fk_folk_classes_grouped_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["world_materials.id"], name=op.f("fk_folk_classes_material_id_world_materials"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_folk_classes_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_folk_classes")),
    )
    with op.batch_alter_table("folk_classes", schema=None) as batch_op:
        batch_op.create_index("ix_folk_classes_grouped", ["grouped_node_id"], unique=False)
        batch_op.create_index("ix_folk_classes_people", ["people_entity_id", "domain"], unique=False)

    op.create_table(
        "kin_group_members",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("member_node_id", sa.Integer(), nullable=False),
        sa.Column("adopted", sa.Boolean(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("joined_epoch >= 0", name=op.f("ck_kin_group_members_joined_epoch_min")),
        sa.ForeignKeyConstraint(["group_id"], ["kin_groups.id"], name=op.f("fk_kin_group_members_group_id_kin_groups"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_node_id"], ["nodes.id"], name=op.f("fk_kin_group_members_member_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "member_node_id", name=op.f("pk_kin_group_members")),
    )
    with op.batch_alter_table("kin_group_members", schema=None) as batch_op:
        batch_op.create_index("ix_kin_group_members_member", ["member_node_id"], unique=False)

    op.create_table(
        "media_outlets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=False),
        sa.Column("seat_entity_id", sa.Integer(), nullable=False),
        sa.Column("medium_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="stance",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("lean", sa.Integer(), nullable=False),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.Column("censored", sa.Boolean(), nullable=False),
        sa.Column(
            "funding",
            sa.Enum("sales", "patronage", "advertising", "state", name="funding", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("revenue", sa.Integer(), nullable=False),
        sa.Column("staff", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_media_outlets_founded_epoch_min")),
        sa.CheckConstraint("lean BETWEEN -100 AND 100", name=op.f("ck_media_outlets_lean_range")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_media_outlets_reach_range")),
        sa.CheckConstraint("revenue >= 0", name=op.f("ck_media_outlets_revenue_min")),
        sa.CheckConstraint("staff >= 0", name=op.f("ck_media_outlets_staff_min")),
        sa.CheckConstraint("trust BETWEEN 0 AND 100", name=op.f("ck_media_outlets_trust_range")),
        sa.ForeignKeyConstraint(["medium_id"], ["record_media.id"], name=op.f("fk_media_outlets_medium_id_record_media"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_media_outlets_owner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seat_entity_id"], ["entities.id"], name=op.f("fk_media_outlets_seat_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_outlets")),
    )
    with op.batch_alter_table("media_outlets", schema=None) as batch_op:
        batch_op.create_index("ix_media_outlets_owner", ["owner_node_id"], unique=False)
        batch_op.create_index("ix_media_outlets_seat", ["seat_entity_id"], unique=False)

    op.create_table(
        "public_work_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("works_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column(
            "labour",
            sa.Enum("paid", "corvee", "bound", "made_minds", "constructs", name="labour", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("spent", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("done_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("done_epoch >= 0", name=op.f("ck_public_work_stages_done_epoch_min")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_public_work_stages_quality_range")),
        sa.CheckConstraint("spent >= 0", name=op.f("ck_public_work_stages_spent_min")),
        sa.CheckConstraint("stage BETWEEN 1 AND 20", name=op.f("ck_public_work_stages_stage_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_public_work_stages_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["works_id"], ["public_works.id"], name=op.f("fk_public_work_stages_works_id_public_works"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_public_work_stages")),
    )
    with op.batch_alter_table("public_work_stages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_public_work_stages_polity_entity_id"), ["polity_entity_id"], unique=False)
        batch_op.create_index("ix_public_work_stages_works", ["works_id", "stage"], unique=False)

    op.create_table(
        "shop_goods",
        sa.Column("shop_id", sa.Integer(), nullable=False),
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
        sa.Column("keeper_node_id", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["keeper_node_id"], ["nodes.id"], name=op.f("fk_shop_goods_keeper_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], name=op.f("fk_shop_goods_shop_id_shops"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shop_id", "commodity", name=op.f("pk_shop_goods")),
    )
    with op.batch_alter_table("shop_goods", schema=None) as batch_op:
        batch_op.create_index("ix_shop_goods_keeper", ["keeper_node_id"], unique=False)

    op.create_table(
        "youth_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(
                "sport",
                "service",
                "courtship",
                "defence",
                "faith",
                "mischief",
                "crime",
                "politics",
                name="purpose",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("leader_node_id", sa.Integer(), nullable=True),
        sa.Column("standing", sa.Integer(), nullable=False),
        sa.Column("age_set_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_youth_groups_founded_epoch_min")),
        sa.CheckConstraint("standing BETWEEN 0 AND 100", name=op.f("ck_youth_groups_standing_range")),
        sa.ForeignKeyConstraint(["age_set_id"], ["age_sets.id"], name=op.f("fk_youth_groups_age_set_id_age_sets"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_node_id"], ["nodes.id"], name=op.f("fk_youth_groups_leader_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_youth_groups_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_youth_groups")),
    )
    with op.batch_alter_table("youth_groups", schema=None) as batch_op:
        batch_op.create_index("ix_youth_groups_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "media_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outlet_id", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "news",
                "opinion",
                "record_of_event",
                "entertainment",
                "instruction",
                "promotion",
                "devotion",
                "official",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject_incident_id", sa.Integer(), nullable=True),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("slant", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accuracy BETWEEN 0 AND 100", name=op.f("ck_media_items_accuracy_range")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_media_items_condition_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_media_items_epoch_min")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_media_items_reach_range")),
        sa.CheckConstraint("slant BETWEEN -100 AND 100", name=op.f("ck_media_items_slant_range")),
        sa.ForeignKeyConstraint(["outlet_id"], ["media_outlets.id"], name=op.f("fk_media_items_outlet_id_media_outlets"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_media_items_owner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_incident_id"], ["incidents.id"], name=op.f("fk_media_items_subject_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_media_items_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_items")),
    )
    with op.batch_alter_table("media_items", schema=None) as batch_op:
        batch_op.create_index("ix_media_items_outlet", ["outlet_id"], unique=False)
        batch_op.create_index("ix_media_items_owner", ["owner_node_id"], unique=False)

    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
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
            nullable=True,
        ),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column(
            "medium",
            sa.Enum("crier", "sign", "display", "patronage", "gift", "media", name="medium", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("accuracy BETWEEN 0 AND 100", name=op.f("ck_promotions_accuracy_range")),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_promotions_cost_min")),
        sa.CheckConstraint("reach BETWEEN 0 AND 100", name=op.f("ck_promotions_reach_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_promotions_started_epoch_min")),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], name=op.f("fk_promotions_brand_id_brands"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_promotions_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promotions")),
    )
    with op.batch_alter_table("promotions", schema=None) as batch_op:
        batch_op.create_index("ix_promotions_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "youth_group_members",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("member_node_id", sa.Integer(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("joined_epoch >= 0", name=op.f("ck_youth_group_members_joined_epoch_min")),
        sa.ForeignKeyConstraint(["group_id"], ["youth_groups.id"], name=op.f("fk_youth_group_members_group_id_youth_groups"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_node_id"], ["nodes.id"], name=op.f("fk_youth_group_members_member_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "member_node_id", name=op.f("pk_youth_group_members")),
    )
    with op.batch_alter_table("youth_group_members", schema=None) as batch_op:
        batch_op.create_index("ix_youth_group_members_member", ["member_node_id"], unique=False)

    with op.batch_alter_table("biology_variants", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sleeps", sa.Boolean(), server_default="1", nullable=False))

    with op.batch_alter_table("fossil_beds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("layer", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(
            sa.Column(
                "preservation",
                sa.Enum("rock", "amber", "ice", "bog", "tar", "ash", "dry", name="preservation", native_enum=False, create_constraint=True, length=40),
                server_default="rock",
                nullable=False,
            )
        )

    with op.batch_alter_table("number_systems", schema=None) as batch_op:
        batch_op.add_column(sa.Column("numerology", sa.JSON(), server_default="{}", nullable=False))

    with op.batch_alter_table("people_culture", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "remains_treatment",
                sa.Enum(
                    "burial",
                    "cremation",
                    "exposure",
                    "preservation",
                    "water",
                    "consumption",
                    "storage",
                    "return_to_maker",
                    "release",
                    "none_needed",
                    name="remains_treatment",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="burial",
                nullable=False,
            )
        )

    with op.batch_alter_table("time_budgets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "life_stage",
                sa.Enum("infant", "child", "youth", "adult", "elder", "ancient", name="life_stage", native_enum=False, create_constraint=True, length=40),
                server_default="adult",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("housework", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("sleep", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("time_budgets", recreate="always") as batch_op:
        batch_op.drop_constraint("pk_time_budgets", type_="primary")
        batch_op.create_primary_key("pk_time_budgets", ["people_entity_id", "social_class", "life_stage"])


def downgrade() -> None:
    op.execute("DELETE FROM time_budgets WHERE life_stage != 'adult'")
    with op.batch_alter_table("time_budgets", recreate="always") as batch_op:
        batch_op.drop_constraint("pk_time_budgets", type_="primary")
        batch_op.create_primary_key("pk_time_budgets", ["people_entity_id", "social_class"])
    op.execute("UPDATE entities SET subtype = 'golem' WHERE subtype = 'animated work'")
    op.execute("UPDATE entities SET subtype = 'chimera' WHERE subtype = 'merged species'")
    op.execute("UPDATE ledger_entries SET tool = 'scatter_bones' WHERE tool = 'hinder_return'")
    op.execute("UPDATE ledger_entries SET tool = 'sibling:scatter' WHERE tool = 'sibling:hinder_return'")
    op.execute("UPDATE ledger_entries SET tool = 'species:chimera' WHERE tool = 'species:merge'")
    op.execute("UPDATE chronicle SET template_key = 'creatures.chimera_woven' WHERE template_key = 'creatures.species_merged'")
    op.execute("UPDATE chronicle SET template_key = 'tools.mortal.chimera' WHERE template_key = 'tools.mortal.species_merged'")
    op.execute("UPDATE chronicle SET template_key = 'gods.death.scatter' WHERE template_key = 'gods.death.return_hindered'")
    op.execute("UPDATE chronicle SET template_key = 'transform.god_corpse' WHERE template_key = 'transform.dead_god'")
    op.execute(
        "UPDATE law_profiles SET params = json_remove(json_set(params, '$.chimera', json_extract(params, '$.merging')), '$.merging') WHERE kind = 'living_craft_law' AND json_extract(params, '$.merging') IS NOT NULL"
    )
    op.execute("UPDATE OR IGNORE preferences SET target = 'song' WHERE kind = 'art_form' AND target = 'musical'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'epic_poem' WHERE kind = 'art_form' AND target = 'verbal'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'play' WHERE kind = 'art_form' AND target = 'ritual_performance'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'statue' WHERE kind = 'art_form' AND target = 'solid_image'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'fresco' WHERE kind = 'art_form' AND target = 'flat_image'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'tapestry' WHERE kind = 'art_form' AND target = 'textile_image'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'dance' WHERE kind = 'art_form' AND target = 'movement'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'architecture_ornament' WHERE kind = 'art_form' AND target = 'built'")
    op.execute(
        "UPDATE afterlife_strata SET criteria = replace(replace(criteria, '\"cremation\"', '\"burning\"'), '\"sky_burial\"', '\"exposure\"') WHERE criteria IS NOT NULL"
    )
    with op.batch_alter_table("time_budgets", schema=None) as batch_op:
        batch_op.drop_column("sleep")
        batch_op.drop_column("housework")
        batch_op.drop_constraint(op.f("ck_time_budgets_life_stage"), type_="check")
        batch_op.drop_column("life_stage")

    with op.batch_alter_table("people_culture", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_people_culture_remains_treatment"), type_="check")
        batch_op.drop_column("remains_treatment")

    with op.batch_alter_table("number_systems", schema=None) as batch_op:
        batch_op.drop_column("numerology")

    with op.batch_alter_table("fossil_beds", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_fossil_beds_preservation"), type_="check")
        batch_op.drop_column("preservation")
        batch_op.drop_column("layer")

    with op.batch_alter_table("biology_variants", schema=None) as batch_op:
        batch_op.drop_column("sleeps")

    with op.batch_alter_table("youth_group_members", schema=None) as batch_op:
        batch_op.drop_index("ix_youth_group_members_member")

    op.drop_table("youth_group_members")
    with op.batch_alter_table("promotions", schema=None) as batch_op:
        batch_op.drop_index("ix_promotions_holder")

    op.drop_table("promotions")
    with op.batch_alter_table("media_items", schema=None) as batch_op:
        batch_op.drop_index("ix_media_items_owner")
        batch_op.drop_index("ix_media_items_outlet")

    op.drop_table("media_items")
    with op.batch_alter_table("youth_groups", schema=None) as batch_op:
        batch_op.drop_index("ix_youth_groups_settlement")

    op.drop_table("youth_groups")
    with op.batch_alter_table("shop_goods", schema=None) as batch_op:
        batch_op.drop_index("ix_shop_goods_keeper")

    op.drop_table("shop_goods")
    with op.batch_alter_table("public_work_stages", schema=None) as batch_op:
        batch_op.drop_index("ix_public_work_stages_works")
        batch_op.drop_index(batch_op.f("ix_public_work_stages_polity_entity_id"))

    op.drop_table("public_work_stages")
    with op.batch_alter_table("media_outlets", schema=None) as batch_op:
        batch_op.drop_index("ix_media_outlets_seat")
        batch_op.drop_index("ix_media_outlets_owner")

    op.drop_table("media_outlets")
    with op.batch_alter_table("kin_group_members", schema=None) as batch_op:
        batch_op.drop_index("ix_kin_group_members_member")

    op.drop_table("kin_group_members")
    with op.batch_alter_table("folk_classes", schema=None) as batch_op:
        batch_op.drop_index("ix_folk_classes_people")
        batch_op.drop_index("ix_folk_classes_grouped")

    op.drop_table("folk_classes")
    op.drop_table("youth_standing")
    with op.batch_alter_table("weather_works", schema=None) as batch_op:
        batch_op.drop_index("ix_weather_works_region")
        batch_op.drop_index(batch_op.f("ix_weather_works_holder_node_id"))

    op.drop_table("weather_works")
    with op.batch_alter_table("supply_tiers", schema=None) as batch_op:
        batch_op.drop_index("ix_supply_tiers_market")
        batch_op.drop_index("ix_supply_tiers_holder")

    op.drop_table("supply_tiers")
    with op.batch_alter_table("state_enterprises", schema=None) as batch_op:
        batch_op.drop_index("ix_state_enterprises_polity")

    op.drop_table("state_enterprises")
    with op.batch_alter_table("speeches", schema=None) as batch_op:
        batch_op.drop_index("ix_speeches_speaker")
        batch_op.drop_index("ix_speeches_place")

    op.drop_table("speeches")
    op.drop_table("space_norms")
    op.drop_table("socialization")
    with op.batch_alter_table("shops", schema=None) as batch_op:
        batch_op.drop_index("ix_shops_settlement")
        batch_op.drop_index("ix_shops_keeper")

    op.drop_table("shops")
    with op.batch_alter_table("sensitivities", schema=None) as batch_op:
        batch_op.drop_index("ix_sensitivities_holder")

    op.drop_table("sensitivities")
    with op.batch_alter_table("sediment_flows", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sediment_flows_source_region_id"))
        batch_op.drop_index("ix_sediment_flows_sink")

    op.drop_table("sediment_flows")
    with op.batch_alter_table("restraint_customs", schema=None) as batch_op:
        batch_op.drop_index("ix_restraint_customs_people")

    op.drop_table("restraint_customs")
    op.drop_table("reproductive_courses")
    op.drop_table("region_cryosphere")
    with op.batch_alter_table("record_media", schema=None) as batch_op:
        batch_op.drop_index("ix_record_media_holder")

    op.drop_table("record_media")
    with op.batch_alter_table("public_works", schema=None) as batch_op:
        batch_op.drop_index("ix_public_works_polity")
        batch_op.drop_index("ix_public_works_place")

    op.drop_table("public_works")
    with op.batch_alter_table("plant_parts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_plant_parts_species_entity_id"))

    op.drop_table("plant_parts")
    op.drop_table("plant_anatomy")
    with op.batch_alter_table("observation_methods", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_observation_methods_people_entity_id"))

    op.drop_table("observation_methods")
    op.drop_table("local_climates")
    op.drop_table("legitimacy_rules")
    op.drop_table("kin_role_duties")
    with op.batch_alter_table("kin_groups", schema=None) as batch_op:
        batch_op.drop_index("ix_kin_groups_people")
        batch_op.drop_index("ix_kin_groups_head")

    op.drop_table("kin_groups")
    op.drop_table("intimacy_norms")
    op.drop_table("infant_care")
    op.drop_table("humour_styles")
    with op.batch_alter_table("folk_knowledge", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_folk_knowledge_people_entity_id"))

    op.drop_table("folk_knowledge")
    with op.batch_alter_table("facet_practices", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_facet_practices_community_entity_id"))

    op.drop_table("facet_practices")
    op.drop_table("disease_agents")
    with op.batch_alter_table("death_work", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_death_work_people_entity_id"))

    op.drop_table("death_work")
    op.drop_table("coasts")
    op.drop_table("child_standing")
    op.drop_table("care_customs")
    with op.batch_alter_table("body_systems", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_body_systems_holder_entity_id"))

    op.drop_table("body_systems")
    op.drop_table("world_fields")
    with op.batch_alter_table("space_weather_events", schema=None) as batch_op:
        batch_op.drop_index("ix_space_weather_events_world")
        batch_op.drop_index(batch_op.f("ix_space_weather_events_star_id"))

    op.drop_table("space_weather_events")
    op.drop_table("star_activity")
    with op.batch_alter_table("population_instruments", schema=None) as batch_op:
        batch_op.drop_index("ix_population_instruments_holder")

    op.drop_table("population_instruments")
    with op.batch_alter_table("housework", schema=None) as batch_op:
        batch_op.drop_index("ix_housework_household")
        batch_op.drop_index("ix_housework_doer")

    op.drop_table("housework")
    with op.batch_alter_table("domestic_service", schema=None) as batch_op:
        batch_op.drop_index("ix_domestic_service_household")

    op.drop_table("domestic_service")
    with op.batch_alter_table("professions_of_value", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_professions_of_value_holder_node_id"))

    op.drop_table("professions_of_value")
    with op.batch_alter_table("population_policies", schema=None) as batch_op:
        batch_op.drop_index("ix_population_policies_holder")

    op.drop_table("population_policies")
    with op.batch_alter_table("pedagogy", schema=None) as batch_op:
        batch_op.drop_index("ix_pedagogy_holder")

    op.drop_table("pedagogy")
    with op.batch_alter_table("leisure_pursuits", schema=None) as batch_op:
        batch_op.drop_index("ix_leisure_pursuits_venue")
        batch_op.drop_index("ix_leisure_pursuits_holder")

    op.drop_table("leisure_pursuits")
    with op.batch_alter_table("leases", schema=None) as batch_op:
        batch_op.drop_index("ix_leases_owner")
        batch_op.drop_index("ix_leases_lessee")

    op.drop_table("leases")
    with op.batch_alter_table("endowments", schema=None) as batch_op:
        batch_op.drop_index("ix_endowments_founder")
        batch_op.drop_index("ix_endowments_beneficiary")

    op.drop_table("endowments")
    op.drop_table("child_recognitions")
    retype(False)
