import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import sqlite

revision = "7527af03f013"
down_revision = "b8b83d201915"
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


ACTKIND_OLD = (
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
    "forced_labour",
    "selling_offices",
    "poaching",
    "enclosing",
)
ACTKIND_NEW = (
    "execution",
    "mutilation",
    "betrayal",
    "mercy_to_enemy",
    "sacrifice_of_people",
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
    "forced_labour",
    "selling_offices",
    "poaching",
    "enclosing",
)
ACTKIND_RENAMED = (("human_sacrifice", "sacrifice_of_people"),)
TENETKIND_OLD = (
    "pacifism",
    "holy_war",
    "asceticism",
    "sacred_suffering",
    "purity_of_body",
    "ancestor_veneration",
    "human_sacrifice",
    "animal_sacrifice",
    "celibate_clergy",
    "proselytism",
    "exclusivity",
    "syncretic_openness",
    "monastic_learning",
    "anti_magic",
    "sanctified_magic",
    "judgement_by_deeds",
    "judgement_by_faith",
    "reincarnation",
    "martyrdom_glory",
    "divine_rule",
    "dietary_law",
    "sacred_species",
    "pilgrimage_duty",
    "souls_rest",
    "void_communion",
    "feeding_the_hunger",
    "whispered_secrets",
    "hidden_god",
)
TENETKIND_NEW = (
    "pacifism",
    "holy_war",
    "asceticism",
    "sacred_suffering",
    "purity_of_body",
    "ancestor_veneration",
    "sacrifice_of_people",
    "animal_sacrifice",
    "celibate_clergy",
    "proselytism",
    "exclusivity",
    "syncretic_openness",
    "monastic_learning",
    "anti_magic",
    "sanctified_magic",
    "judgement_by_deeds",
    "judgement_by_faith",
    "reincarnation",
    "martyrdom_glory",
    "divine_rule",
    "dietary_law",
    "sacred_species",
    "pilgrimage_duty",
    "souls_rest",
    "void_communion",
    "feeding_the_hunger",
    "whispered_secrets",
    "hidden_god",
)
TENETKIND_RENAMED = (("human_sacrifice", "sacrifice_of_people"),)
INCIDENTROLE_OLD = ("subject", "actor", "target", "witness", "place")
INCIDENTROLE_NEW = (
    "subject",
    "actor",
    "co_actor",
    "target",
    "victim",
    "beneficiary",
    "opponent",
    "ally",
    "leader",
    "member",
    "giver",
    "receiver",
    "buyer",
    "seller",
    "lender",
    "borrower",
    "maker",
    "owner",
    "heir",
    "predecessor",
    "successor",
    "accuser",
    "accused",
    "judge",
    "advocate",
    "teacher",
    "learner",
    "healer",
    "patient",
    "parent",
    "child",
    "spouse",
    "officiant",
    "host",
    "guest",
    "envoy",
    "mediator",
    "authority",
    "patron",
    "instrument",
    "product",
    "origin",
    "destination",
    "place",
    "witness",
    "teller",
)
INCIDENTROLE_RENAMED = ()
RETYPED = (
    ("creator_taboos", "act", "act", ACTKIND_OLD, ACTKIND_NEW, ACTKIND_RENAMED, False),
    ("culture_ethics", "act", "act", ACTKIND_OLD, ACTKIND_NEW, ACTKIND_RENAMED, False),
    ("geasa", "act", "act", ACTKIND_OLD, ACTKIND_NEW, ACTKIND_RENAMED, False),
    ("deeds", "act", "act", ACTKIND_OLD, ACTKIND_NEW, ACTKIND_RENAMED, True),
    ("tradition_profiles", "taboo_act", "taboo_act", ACTKIND_OLD, ACTKIND_NEW, ACTKIND_RENAMED, True),
    ("cult_tenets", "tenet", "tenet", TENETKIND_OLD, TENETKIND_NEW, TENETKIND_RENAMED, False),
    ("incident_participants", "role", "role", INCIDENTROLE_OLD, INCIDENTROLE_NEW, INCIDENTROLE_RENAMED, False),
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


def merge_built_in(table: str, concept: str, former: str, key: str) -> None:
    bind = op.get_bind()
    old = bind.execute(sa.text(f"SELECT id FROM {table} WHERE built_in_key = :key"), {"key": former}).scalar()
    new = bind.execute(sa.text(f"SELECT id FROM {table} WHERE built_in_key = :key"), {"key": key}).scalar()
    if old is None or new is None:
        return
    for (child,) in bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'table'")).all():
        for link in bind.execute(sa.text(f"PRAGMA foreign_key_list('{child}')")).all():
            if link[2] == table and link[4] == "id":
                bind.execute(sa.text(f"UPDATE OR IGNORE {child} SET {link[3]} = :new WHERE {link[3]} = :old"), {"new": new, "old": old})
    moved = {"new": new, "old": old, "concept": concept}
    bind.execute(sa.text("UPDATE OR IGNORE kind_holdings SET kind_id = :new WHERE concept = :concept AND kind_id = :old"), moved)
    bind.execute(sa.text("DELETE FROM kind_holdings WHERE concept = :concept AND kind_id = :old"), moved)
    bind.execute(sa.text(f"DELETE FROM {table} WHERE id = :old"), {"old": old})


def upgrade() -> None:
    retype(True)
    op.execute("UPDATE afterlife_strata SET criteria = replace(criteria, '\"human_sacrifice\"', '\"sacrifice_of_people\"')")
    merge_built_in("production_method_kinds", "production_method", "spun_fibre", "fibre_from_life")
    op.execute("UPDATE production_method_kinds SET built_in_key = 'fibre_from_life' WHERE built_in_key = 'spun_fibre'")
    op.execute("UPDATE production_method_kinds SET name = 'Cultured fibre' WHERE built_in_key = 'fibre_from_life' AND name = 'Spun fibre'")
    merge_built_in("tenet_kinds", "tenet", "doctrine.divine_kingship", "doctrine.divine_rule")
    op.execute("UPDATE tenet_kinds SET built_in_key = 'doctrine.divine_rule' WHERE built_in_key = 'doctrine.divine_kingship'")
    op.execute("UPDATE tenet_kinds SET name = 'Divine rule' WHERE built_in_key = 'doctrine.divine_rule' AND name = 'Divine kingship'")
    merge_built_in("tenet_kinds", "tenet", "doctrine.human_sacrifice", "doctrine.sacrifice_of_people")
    op.execute("UPDATE tenet_kinds SET built_in_key = 'doctrine.sacrifice_of_people' WHERE built_in_key = 'doctrine.human_sacrifice'")
    op.execute("UPDATE tenet_kinds SET name = 'Sacrifice of people' WHERE built_in_key = 'doctrine.sacrifice_of_people' AND name = 'Human sacrifice'")
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
        "state_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("table_name", sa.String(length=120), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=120), nullable=False),
        sa.Column("last_change_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_state_checkpoints")),
    )
    with op.batch_alter_table("state_checkpoints", schema=None) as batch_op:
        batch_op.create_index("ix_state_checkpoints_epoch", ["epoch", "table_name"], unique=False)

    op.create_table(
        "incident_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=True),
        sa.Column("number", sa.Float(), nullable=True),
        sa.Column(
            "unit",
            sa.Enum(
                "count",
                "people",
                "coin",
                "wealth_points",
                "percent",
                "hp",
                "severity",
                "years",
                "seasons",
                "days",
                "hours",
                "distance",
                "area",
                "mass",
                "tons",
                "essence",
                "renown",
                "standing",
                "knowledge",
                "strength",
                "speed",
                "temperature",
                "energy",
                "none",
                name="unit",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("enum_name", sa.String(length=120), nullable=True),
        sa.Column("enum_value", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.CheckConstraint("(enum_name IS NULL) = (enum_value IS NULL)", name=op.f("ck_incident_facts_enum_named")),
        sa.CheckConstraint(
            "(node_id IS NOT NULL) + (number IS NOT NULL) + (enum_value IS NOT NULL) + (name IS NOT NULL) = 1", name=op.f("ck_incident_facts_one_value")
        ),
        sa.CheckConstraint("position >= 0", name=op.f("ck_incident_facts_position_min")),
        sa.CheckConstraint("unit IS NULL OR number IS NOT NULL", name=op.f("ck_incident_facts_unit_with_number")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_incident_facts_incident_id_incidents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_incident_facts_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_facts")),
    )
    with op.batch_alter_table("incident_facts", schema=None) as batch_op:
        batch_op.create_index("ix_incident_facts_incident_key", ["incident_id", "key"], unique=False)
        batch_op.create_index("ix_incident_facts_node", ["node_id"], unique=False)

    op.create_table(
        "incident_names",
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_incident_names_epoch_min")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_incident_names_incident_id_incidents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_incident_names_language_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("incident_id", name=op.f("pk_incident_names")),
    )
    op.create_table(
        "incident_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=True),
        sa.Column("parent_step_id", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("day", sa.Integer(), nullable=True),
        sa.Column("hour", sa.Integer(), nullable=True),
        sa.Column("actor_node_id", sa.Integer(), nullable=True),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "close",
                "strike",
                "thrust",
                "cut",
                "shoot",
                "throw",
                "cast",
                "feint",
                "block",
                "parry",
                "dodge",
                "grapple",
                "throw_down",
                "choke",
                "lock",
                "bite",
                "disarm",
                "charge",
                "trample",
                "fall",
                "rise",
                "flee",
                "pursue",
                "yield",
                "spare",
                "finish",
                "rescue",
                "carry_off",
                "deploy",
                "advance",
                "hold",
                "volley",
                "wheel",
                "flank",
                "rout",
                "rally",
                "reinforce",
                "withdraw",
                "encircle",
                "breach",
                "storm",
                "undermine",
                "bombard",
                "sortie",
                "surrender",
                "pillage",
                "take_captives",
                "take_standard",
                "manoeuvre",
                "take_position",
                "fire",
                "ram",
                "board",
                "repel",
                "ignite",
                "extinguish",
                "flood",
                "pump",
                "repair_underway",
                "jettison",
                "launch_craft",
                "raise_shield",
                "lose_shield",
                "vent",
                "lose_power",
                "crash",
                "explode",
                "sink",
                "strike_colours",
                "escape",
                "drift",
                "fall_ill",
                "worsen",
                "ease",
                "recover",
                "examine",
                "treat",
                "operate",
                "set_bone",
                "suture",
                "amputate",
                "fit_prosthesis",
                "go_into_labour",
                "give_birth",
                "lose_child",
                "name_child",
                "age",
                "die",
                "return_to_life",
                "gather",
                "prepare",
                "shape",
                "assemble",
                "temper",
                "inscribe",
                "enchant",
                "test",
                "flaw",
                "finish_work",
                "sign_work",
                "repair",
                "break",
                "copy",
                "forge",
                "lay_foundation",
                "raise",
                "complete",
                "collapse",
                "offer",
                "bargain",
                "agree",
                "pay",
                "deliver",
                "default",
                "seize_goods",
                "smuggle",
                "levy",
                "toll",
                "lend",
                "repay",
                "give",
                "return_gift",
                "hire",
                "work",
                "strike_work",
                "dismiss",
                "buy_freedom",
                "accuse",
                "investigate",
                "find_evidence",
                "testify",
                "plead",
                "judge",
                "sentence",
                "punish",
                "pardon",
                "appeal",
                "decree",
                "proclaim",
                "vote",
                "count_votes",
                "appoint",
                "swear",
                "break_oath",
                "negotiate",
                "propose",
                "counter",
                "sign",
                "refuse",
                "threaten",
                "insult",
                "apologise",
                "persuade",
                "convert",
                "teach",
                "learn",
                "write",
                "read",
                "translate",
                "forge_record",
                "reveal",
                "conceal",
                "deceive",
                "discover",
                "spread_word",
                "pray",
                "sacrifice",
                "perform_rite",
                "invoke",
                "answer",
                "deny",
                "manifest",
                "possess",
                "exorcise",
                "curse",
                "bless",
                "foresee",
                "draw_power",
                "use_power",
                "backlash",
                "bind",
                "release",
                "depart",
                "travel",
                "rest",
                "lose_way",
                "meet_danger",
                "cross",
                "enter",
                "leave",
                "arrive",
                "settle",
                "found",
                "abandon",
                "return",
                "meet",
                "court",
                "marry",
                "separate",
                "adopt",
                "foster",
                "inherit",
                "succeed",
                "crown",
                "depose",
                "betray",
                "reconcile",
                "befriend",
                "quarrel",
                "feud",
                "avenge",
                "mourn",
                "celebrate",
                "host",
                "serve_food",
                "compete",
                "score",
                "win",
                "lose",
                "perform",
                "honour",
                "shame",
                "begin",
                "spread",
                "peak",
                "wane",
                "end",
                "erupt",
                "quake",
                "flood_land",
                "burn_land",
                "blow",
                "freeze",
                "dry",
                "bloom",
                "migrate",
                "die_out",
                "appear",
                "collide",
                "collapse_body",
                "open",
                "connect",
                "intrude",
                "copy_mind",
                "save_mind",
                "restore_mind",
                "transfer_mind",
                "merge_minds",
                "awaken",
                "link_minds",
                "unlink",
                name="action",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "instrument_kind",
            sa.Enum(
                "item",
                "equipment_model",
                "vehicle_weapon",
                "vehicle",
                "structure",
                "creature",
                "power",
                "rite",
                "tool_kind",
                "substance",
                "text",
                "network",
                "body",
                "none",
                name="instrument_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("instrument_node_id", sa.Integer(), nullable=True),
        sa.Column("instrument_key", sa.String(length=120), nullable=True),
        sa.Column(
            "locus_kind",
            sa.Enum(
                "body_part",
                "vehicle_section",
                "structure_section",
                "room",
                "district",
                "settlement",
                "region",
                "route",
                "sea",
                "sky",
                "orbit",
                "realm",
                "network_node",
                "none",
                name="locus_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("locus_key", sa.String(length=120), nullable=True),
        sa.Column("locus_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "damage_type",
            sa.Enum(
                "cut",
                "pierce",
                "blunt",
                "fire",
                "cold",
                "venom",
                "magic",
                "void",
                "holy",
                "ballistic",
                "explosive",
                "energy",
                "electric",
                "radiation",
                "chemical",
                "sonic",
                "psychic",
                name="damage_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column(
            "unit",
            sa.Enum(
                "count",
                "people",
                "coin",
                "wealth_points",
                "percent",
                "hp",
                "severity",
                "years",
                "seasons",
                "days",
                "hours",
                "distance",
                "area",
                "mass",
                "tons",
                "essence",
                "renown",
                "standing",
                "knowledge",
                "strength",
                "speed",
                "temperature",
                "energy",
                "none",
                name="unit",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "outcome",
            sa.Enum(
                "success",
                "partial",
                "failure",
                "missed",
                "blocked",
                "parried",
                "dodged",
                "glanced",
                "absorbed",
                "wounded",
                "broken",
                "severed",
                "downed",
                "killed",
                "damaged",
                "disabled",
                "destroyed",
                "captured",
                "escaped",
                "yielded",
                "accepted",
                "refused",
                "delayed",
                "interrupted",
                "reversed",
                "no_effect",
                name="outcome",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("record_table", sa.String(length=120), nullable=True),
        sa.Column("record_key", sa.String(length=120), nullable=True),
        sa.CheckConstraint("position >= 0", name=op.f("ck_incident_steps_position_min")),
        sa.CheckConstraint("round IS NULL OR round >= 0", name=op.f("ck_incident_steps_round_not_negative")),
        sa.CheckConstraint("unit IS NULL OR amount IS NOT NULL", name=op.f("ck_incident_steps_unit_with_amount")),
        sa.ForeignKeyConstraint(["actor_node_id"], ["nodes.id"], name=op.f("fk_incident_steps_actor_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_incident_steps_incident_id_incidents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_node_id"], ["nodes.id"], name=op.f("fk_incident_steps_instrument_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["locus_node_id"], ["nodes.id"], name=op.f("fk_incident_steps_locus_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_step_id"], ["incident_steps.id"], name=op.f("fk_incident_steps_parent_step_id_incident_steps"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_incident_steps_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_steps")),
    )
    with op.batch_alter_table("incident_steps", schema=None) as batch_op:
        batch_op.create_index("ix_incident_steps_actor", ["actor_node_id"], unique=False)
        batch_op.create_index("ix_incident_steps_incident_position", ["incident_id", "position"], unique=False)
        batch_op.create_index("ix_incident_steps_moment", ["year", "season", "day", "hour"], unique=False)
        batch_op.create_index("ix_incident_steps_target", ["target_node_id"], unique=False)

    op.create_table(
        "incident_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("fact_key", sa.String(length=120), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=120), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("source_incident_id", sa.Integer(), nullable=True),
        sa.Column("op", sa.Enum("add", "multiply", name="op", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.CheckConstraint("position >= 0", name=op.f("ck_incident_terms_position_min")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_incident_terms_incident_id_incidents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_incident_id"], ["incidents.id"], name=op.f("fk_incident_terms_source_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_incident_terms_source_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_terms")),
    )
    with op.batch_alter_table("incident_terms", schema=None) as batch_op:
        batch_op.create_index("ix_incident_terms_incident", ["incident_id", "fact_key"], unique=False)

    op.create_table(
        "incident_step_states",
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "prone",
                "risen",
                "disarmed",
                "stunned",
                "unconscious",
                "bleeding",
                "burning",
                "blinded",
                "restrained",
                "fleeing",
                "yielded",
                "captured",
                "freed",
                "hidden",
                "revealed",
                "exhausted",
                "possessed",
                "flooding",
                "breached",
                "depressurised",
                "adrift",
                "disabled",
                "aground",
                "grounded",
                "shielded",
                "unshielded",
                "cut_off",
                "encircled",
                "routed",
                "rallied",
                name="state",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_incident_step_states_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["incident_steps.id"], name=op.f("fk_incident_step_states_step_id_incident_steps"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("step_id", "node_id", "state", name=op.f("pk_incident_step_states")),
    )
    with op.batch_alter_table("incident_step_states", schema=None) as batch_op:
        batch_op.create_index("ix_incident_step_states_node", ["node_id"], unique=False)

    op.create_table(
        "rumour_distortions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rumour_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "distortion",
            sa.Enum(
                "doer_swapped",
                "target_swapped",
                "amount_changed",
                "outcome_changed",
                "cause_changed",
                "place_changed",
                "moment_changed",
                "step_added",
                "step_dropped",
                "role_changed",
                name="distortion",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "subject",
                "actor",
                "co_actor",
                "target",
                "victim",
                "beneficiary",
                "opponent",
                "ally",
                "leader",
                "member",
                "giver",
                "receiver",
                "buyer",
                "seller",
                "lender",
                "borrower",
                "maker",
                "owner",
                "heir",
                "predecessor",
                "successor",
                "accuser",
                "accused",
                "judge",
                "advocate",
                "teacher",
                "learner",
                "healer",
                "patient",
                "parent",
                "child",
                "spouse",
                "officiant",
                "host",
                "guest",
                "envoy",
                "mediator",
                "authority",
                "patron",
                "instrument",
                "product",
                "origin",
                "destination",
                "place",
                "witness",
                "teller",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("fact_key", sa.String(length=120), nullable=True),
        sa.Column("step_id", sa.Integer(), nullable=True),
        sa.Column("told_node_id", sa.Integer(), nullable=True),
        sa.Column("told_number", sa.Float(), nullable=True),
        sa.Column("told_enum_value", sa.String(length=120), nullable=True),
        sa.Column("told_year", sa.Integer(), nullable=True),
        sa.Column("told_incident_id", sa.Integer(), nullable=True),
        sa.Column(
            "told_action",
            sa.Enum(
                "close",
                "strike",
                "thrust",
                "cut",
                "shoot",
                "throw",
                "cast",
                "feint",
                "block",
                "parry",
                "dodge",
                "grapple",
                "throw_down",
                "choke",
                "lock",
                "bite",
                "disarm",
                "charge",
                "trample",
                "fall",
                "rise",
                "flee",
                "pursue",
                "yield",
                "spare",
                "finish",
                "rescue",
                "carry_off",
                "deploy",
                "advance",
                "hold",
                "volley",
                "wheel",
                "flank",
                "rout",
                "rally",
                "reinforce",
                "withdraw",
                "encircle",
                "breach",
                "storm",
                "undermine",
                "bombard",
                "sortie",
                "surrender",
                "pillage",
                "take_captives",
                "take_standard",
                "manoeuvre",
                "take_position",
                "fire",
                "ram",
                "board",
                "repel",
                "ignite",
                "extinguish",
                "flood",
                "pump",
                "repair_underway",
                "jettison",
                "launch_craft",
                "raise_shield",
                "lose_shield",
                "vent",
                "lose_power",
                "crash",
                "explode",
                "sink",
                "strike_colours",
                "escape",
                "drift",
                "fall_ill",
                "worsen",
                "ease",
                "recover",
                "examine",
                "treat",
                "operate",
                "set_bone",
                "suture",
                "amputate",
                "fit_prosthesis",
                "go_into_labour",
                "give_birth",
                "lose_child",
                "name_child",
                "age",
                "die",
                "return_to_life",
                "gather",
                "prepare",
                "shape",
                "assemble",
                "temper",
                "inscribe",
                "enchant",
                "test",
                "flaw",
                "finish_work",
                "sign_work",
                "repair",
                "break",
                "copy",
                "forge",
                "lay_foundation",
                "raise",
                "complete",
                "collapse",
                "offer",
                "bargain",
                "agree",
                "pay",
                "deliver",
                "default",
                "seize_goods",
                "smuggle",
                "levy",
                "toll",
                "lend",
                "repay",
                "give",
                "return_gift",
                "hire",
                "work",
                "strike_work",
                "dismiss",
                "buy_freedom",
                "accuse",
                "investigate",
                "find_evidence",
                "testify",
                "plead",
                "judge",
                "sentence",
                "punish",
                "pardon",
                "appeal",
                "decree",
                "proclaim",
                "vote",
                "count_votes",
                "appoint",
                "swear",
                "break_oath",
                "negotiate",
                "propose",
                "counter",
                "sign",
                "refuse",
                "threaten",
                "insult",
                "apologise",
                "persuade",
                "convert",
                "teach",
                "learn",
                "write",
                "read",
                "translate",
                "forge_record",
                "reveal",
                "conceal",
                "deceive",
                "discover",
                "spread_word",
                "pray",
                "sacrifice",
                "perform_rite",
                "invoke",
                "answer",
                "deny",
                "manifest",
                "possess",
                "exorcise",
                "curse",
                "bless",
                "foresee",
                "draw_power",
                "use_power",
                "backlash",
                "bind",
                "release",
                "depart",
                "travel",
                "rest",
                "lose_way",
                "meet_danger",
                "cross",
                "enter",
                "leave",
                "arrive",
                "settle",
                "found",
                "abandon",
                "return",
                "meet",
                "court",
                "marry",
                "separate",
                "adopt",
                "foster",
                "inherit",
                "succeed",
                "crown",
                "depose",
                "betray",
                "reconcile",
                "befriend",
                "quarrel",
                "feud",
                "avenge",
                "mourn",
                "celebrate",
                "host",
                "serve_food",
                "compete",
                "score",
                "win",
                "lose",
                "perform",
                "honour",
                "shame",
                "begin",
                "spread",
                "peak",
                "wane",
                "end",
                "erupt",
                "quake",
                "flood_land",
                "burn_land",
                "blow",
                "freeze",
                "dry",
                "bloom",
                "migrate",
                "die_out",
                "appear",
                "collide",
                "collapse_body",
                "open",
                "connect",
                "intrude",
                "copy_mind",
                "save_mind",
                "restore_mind",
                "transfer_mind",
                "merge_minds",
                "awaken",
                "link_minds",
                "unlink",
                name="told_action",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "told_outcome",
            sa.Enum(
                "success",
                "partial",
                "failure",
                "missed",
                "blocked",
                "parried",
                "dodged",
                "glanced",
                "absorbed",
                "wounded",
                "broken",
                "severed",
                "downed",
                "killed",
                "damaged",
                "disabled",
                "destroyed",
                "captured",
                "escaped",
                "yielded",
                "accepted",
                "refused",
                "delayed",
                "interrupted",
                "reversed",
                "no_effect",
                name="told_outcome",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_rumour_distortions_epoch_min")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_rumour_distortions_position_min")),
        sa.ForeignKeyConstraint(["rumour_id"], ["rumours.id"], name=op.f("fk_rumour_distortions_rumour_id_rumours"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["incident_steps.id"], name=op.f("fk_rumour_distortions_step_id_incident_steps"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["told_incident_id"], ["incidents.id"], name=op.f("fk_rumour_distortions_told_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["told_node_id"], ["nodes.id"], name=op.f("fk_rumour_distortions_told_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rumour_distortions")),
    )
    with op.batch_alter_table("rumour_distortions", schema=None) as batch_op:
        batch_op.create_index("ix_rumour_distortions_rumour", ["rumour_id"], unique=False)

    op.create_table(
        "state_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("day", sa.Integer(), nullable=True),
        sa.Column("hour", sa.Integer(), nullable=True),
        sa.Column("table_name", sa.String(length=120), nullable=False),
        sa.Column("row_key", sa.Text(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.Enum("insert", "update", "delete", name="operation", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("field", sa.String(length=120), nullable=True),
        sa.Column("before_number", sa.Float(), nullable=True),
        sa.Column("after_number", sa.Float(), nullable=True),
        sa.Column("before_text", sa.Text(), nullable=True),
        sa.Column("after_text", sa.Text(), nullable=True),
        sa.Column("before_node_id", sa.Integer(), nullable=True),
        sa.Column("after_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "actor_kind",
            sa.Enum(
                "creator", "son", "mortal", "foreign_god", "fate", "engine", "system", name="actor_kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("actor_node_id", sa.Integer(), nullable=True),
        sa.Column("phase", sa.String(length=120), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("step_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_state_changes_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["step_id"], ["incident_steps.id"], name=op.f("fk_state_changes_step_id_incident_steps"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_state_changes")),
    )
    with op.batch_alter_table("state_changes", schema=None) as batch_op:
        batch_op.create_index("ix_state_changes_epoch", ["epoch", "id"], unique=False)
        batch_op.create_index("ix_state_changes_incident", ["incident_id"], unique=False)
        batch_op.create_index("ix_state_changes_node", ["node_id", "epoch"], unique=False)
        batch_op.create_index("ix_state_changes_row", ["table_name", "row_key", "id"], unique=False)

    op.create_table(
        "state_change_terms",
        sa.Column("change_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=120), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("source_incident_id", sa.Integer(), nullable=True),
        sa.Column("op", sa.Enum("add", "multiply", name="op", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["change_id"], ["state_changes.id"], name=op.f("fk_state_change_terms_change_id_state_changes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_incident_id"], ["incidents.id"], name=op.f("fk_state_change_terms_source_incident_id_incidents"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("change_id", "position", name=op.f("pk_state_change_terms")),
    )
    op.drop_table("epoch_year_cursors")
    with op.batch_alter_table("expedition_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("step_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_expedition_logs_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_expedition_logs_step_id_incident_steps"), "incident_steps", ["step_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("expeditions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_expeditions_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("formation_histories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_formation_histories_incident_id"), ["incident_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_formation_histories_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("incident_participants", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "witness_mode",
                sa.Enum("saw", "heard", "took_part", "was_told", name="witness_mode", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("fidelity", sa.Integer(), nullable=True))

    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("season", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("day", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("hour", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("origin_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("destination_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "tier",
                sa.Enum("line", "account", "steps", name="tier", native_enum=False, create_constraint=True, length=40),
                server_default="line",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("locked", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
        batch_op.create_index("ix_incidents_moment", ["world_id", "year", "season", "day", "hour"], unique=False)
        batch_op.create_index("ix_incidents_place", ["place_entity_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_incidents_origin_entity_id_entities"), "entities", ["origin_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(
            batch_op.f("fk_incidents_destination_entity_id_entities"), "entities", ["destination_entity_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("injuries", schema=None) as batch_op:
        batch_op.add_column(sa.Column("step_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "instrument_kind",
                sa.Enum(
                    "item",
                    "equipment_model",
                    "vehicle_weapon",
                    "vehicle",
                    "structure",
                    "creature",
                    "power",
                    "rite",
                    "tool_kind",
                    "substance",
                    "text",
                    "network",
                    "body",
                    "none",
                    name="instrument_kind",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("instrument_key", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("instrument_node_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_injuries_step_id"), ["step_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_injuries_instrument_node_id_nodes"), "nodes", ["instrument_node_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_injuries_step_id_incident_steps"), "incident_steps", ["step_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("item_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_item_history_incident_id"), ["incident_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_item_history_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_journeys_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("memories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("step_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_memories_step_id_incident_steps"), "incident_steps", ["step_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("settlement_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_settlement_history_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("sound_changes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_sound_changes_incident_id"), ["incident_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_sound_changes_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("trait_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_trait_history_incident_id"), ["incident_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_trait_history_incident_id_incidents"), "incidents", ["incident_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.drop_column("armament")


def downgrade() -> None:
    op.execute("UPDATE afterlife_strata SET criteria = replace(criteria, '\"sacrifice_of_people\"', '\"human_sacrifice\"')")
    op.execute("UPDATE tenet_kinds SET built_in_key = 'doctrine.human_sacrifice' WHERE built_in_key = 'doctrine.sacrifice_of_people'")
    op.execute("UPDATE tenet_kinds SET name = 'Human sacrifice' WHERE built_in_key = 'doctrine.human_sacrifice' AND name = 'Sacrifice of people'")
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
    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("armament", sqlite.JSON(), server_default=sa.text("'[]'"), nullable=False))

    with op.batch_alter_table("trait_history", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_trait_history_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_trait_history_incident_id"))
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("sound_changes", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_sound_changes_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_sound_changes_incident_id"))
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("settlement_history", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_settlement_history_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("memories", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_memories_step_id_incident_steps"), type_="foreignkey")
        batch_op.drop_column("step_id")

    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_journeys_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("item_history", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_item_history_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_item_history_incident_id"))
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("injuries", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_injuries_step_id_incident_steps"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_injuries_instrument_node_id_nodes"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_injuries_step_id"))
        batch_op.drop_column("instrument_node_id")
        batch_op.drop_column("instrument_key")
        batch_op.drop_constraint(op.f("ck_injuries_instrument_kind"), type_="check")
        batch_op.drop_column("instrument_kind")
        batch_op.drop_column("step_id")

    with op.batch_alter_table("incidents", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_incidents_destination_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_incidents_origin_entity_id_entities"), type_="foreignkey")
        batch_op.drop_index("ix_incidents_place")
        batch_op.drop_index("ix_incidents_moment")
        batch_op.drop_column("locked")
        batch_op.drop_constraint(op.f("ck_incidents_tier"), type_="check")
        batch_op.drop_column("tier")
        batch_op.drop_column("destination_entity_id")
        batch_op.drop_column("origin_entity_id")
        batch_op.drop_column("hour")
        batch_op.drop_column("day")
        batch_op.drop_column("season")

    with op.batch_alter_table("incident_participants", schema=None) as batch_op:
        batch_op.drop_column("fidelity")
        batch_op.drop_constraint(op.f("ck_incident_participants_witness_mode"), type_="check")
        batch_op.drop_column("witness_mode")

    with op.batch_alter_table("formation_histories", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_formation_histories_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_formation_histories_incident_id"))
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("expeditions", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_expeditions_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_column("incident_id")

    with op.batch_alter_table("expedition_logs", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_expedition_logs_step_id_incident_steps"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_expedition_logs_incident_id_incidents"), type_="foreignkey")
        batch_op.drop_column("step_id")
        batch_op.drop_column("incident_id")

    op.create_table(
        "epoch_year_cursors",
        sa.Column("epoch", sa.INTEGER(), nullable=False),
        sa.Column("last_year", sa.INTEGER(), nullable=False),
        sa.PrimaryKeyConstraint("epoch", name=op.f("pk_epoch_year_cursors")),
    )
    op.drop_table("state_change_terms")
    with op.batch_alter_table("state_changes", schema=None) as batch_op:
        batch_op.drop_index("ix_state_changes_row")
        batch_op.drop_index("ix_state_changes_node")
        batch_op.drop_index("ix_state_changes_incident")
        batch_op.drop_index("ix_state_changes_epoch")

    op.drop_table("state_changes")
    with op.batch_alter_table("rumour_distortions", schema=None) as batch_op:
        batch_op.drop_index("ix_rumour_distortions_rumour")

    op.drop_table("rumour_distortions")
    with op.batch_alter_table("incident_step_states", schema=None) as batch_op:
        batch_op.drop_index("ix_incident_step_states_node")

    op.drop_table("incident_step_states")
    with op.batch_alter_table("incident_terms", schema=None) as batch_op:
        batch_op.drop_index("ix_incident_terms_incident")

    op.drop_table("incident_terms")
    with op.batch_alter_table("incident_steps", schema=None) as batch_op:
        batch_op.drop_index("ix_incident_steps_target")
        batch_op.drop_index("ix_incident_steps_moment")
        batch_op.drop_index("ix_incident_steps_incident_position")
        batch_op.drop_index("ix_incident_steps_actor")

    op.drop_table("incident_steps")
    op.drop_table("incident_names")
    with op.batch_alter_table("incident_facts", schema=None) as batch_op:
        batch_op.drop_index("ix_incident_facts_node")
        batch_op.drop_index("ix_incident_facts_incident_key")

    op.drop_table("incident_facts")
    with op.batch_alter_table("state_checkpoints", schema=None) as batch_op:
        batch_op.drop_index("ix_state_checkpoints_epoch")

    op.drop_table("state_checkpoints")
    retype(False)
