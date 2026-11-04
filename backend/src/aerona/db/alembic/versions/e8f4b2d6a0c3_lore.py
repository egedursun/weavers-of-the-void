import sqlalchemy as sa
from alembic import op

revision = "e8f4b2d6a0c3"
down_revision = "d6e2a8c0f4b1"
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
    "disease",
    "polity",
    "house",
    "treaty",
)
NEW_ENTITY_TYPES = (*OLD_ENTITY_TYPES, "ideology", "rite")
OLD_CAUSES = (
    "hostility",
    "uprising",
    "tribute_revolt",
    "incited",
    "declared",
    "betrayal",
    "conquest_journey",
    "foreign_god",
    "independence",
    "vendetta",
    "grudge",
    "divine_grudge",
    "rivalry",
    "debt",
    "espionage",
    "sabotage",
    "envy",
    "schism",
    "beast",
    "resource",
    "trade_route",
)
NEW_CAUSES = (*OLD_CAUSES, "ideology")
OLD_AIMS = (
    "conquer_region",
    "seize_settlement",
    "press_claim",
    "convert",
    "tribute",
    "vassalise",
    "liberate",
    "destroy_cult",
    "seize_resource",
    "seize_nexus",
    "humiliate",
    "revenge",
    "loot",
)
NEW_AIMS = (*OLD_AIMS, "change_government")
WIDENED = (
    ("entities", "entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, False),
    ("son_powers", "param_entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, True),
    ("wars", "cause", OLD_CAUSES, NEW_CAUSES, False),
    ("bonds", "war_cause", OLD_CAUSES, NEW_CAUSES, True),
    ("war_aims", "kind", OLD_AIMS, NEW_AIMS, False),
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
        "artwork_profiles",
        sa.Column("artwork_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "medium",
            sa.Enum(
                "song",
                "epic_poem",
                "play",
                "statue",
                "fresco",
                "tapestry",
                "mosaic",
                "book",
                "dance",
                "music",
                "carving",
                "architecture_ornament",
                name="medium",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("performed", sa.Boolean(), nullable=False),
        sa.Column("author_entity_id", sa.Integer(), nullable=True),
        sa.Column("patron_entity_id", sa.Integer(), nullable=True),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.JSON(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=True),
        sa.Column("translations", sa.JSON(), nullable=False),
        sa.Column("propaganda", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("copies >= 0", name=op.f("ck_artwork_profiles_copies_min")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_artwork_profiles_quality_range")),
        sa.ForeignKeyConstraint(["artwork_entity_id"], ["entities.id"], name=op.f("fk_artwork_profiles_artwork_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_entity_id"], ["entities.id"], name=op.f("fk_artwork_profiles_author_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_artwork_profiles_language_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patron_entity_id"], ["entities.id"], name=op.f("fk_artwork_profiles_patron_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_artwork_profiles_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("artwork_entity_id", name=op.f("pk_artwork_profiles")),
    )
    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_artwork_profiles_subject_node_id"), ["subject_node_id"], unique=False)

    op.create_table(
        "book_contents",
        sa.Column("book_entity_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_entity_id", sa.Integer(), nullable=False),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_book_contents_fidelity_range")),
        sa.ForeignKeyConstraint(["book_entity_id"], ["entities.id"], name=op.f("fk_book_contents_book_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_entity_id"], ["entities.id"], name=op.f("fk_book_contents_knowledge_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("book_entity_id", "knowledge_entity_id", name=op.f("pk_book_contents")),
    )
    op.create_table(
        "castings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rite_entity_id", sa.Integer(), nullable=False),
        sa.Column("caster_entity_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column(
            "backlash",
            sa.Enum("injury", "madness", "leak", "escape", "phenomenon", name="backlash", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("effect", sa.String(length=480), nullable=False),
        sa.ForeignKeyConstraint(["caster_entity_id"], ["entities.id"], name=op.f("fk_castings_caster_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_castings_rite_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_castings_target_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_castings")),
    )
    with op.batch_alter_table("castings", schema=None) as batch_op:
        batch_op.create_index("ix_castings_caster", ["caster_entity_id"], unique=False)
        batch_op.create_index("ix_castings_epoch", ["epoch"], unique=False)

    op.create_table(
        "holder_levels",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "branch",
            sa.Enum(
                "agriculture",
                "metallurgy",
                "seafaring",
                "writing",
                "architecture",
                "medicine",
                "magic",
                "warfare",
                "astronomy",
                "trade",
                "sky_navigation",
                "shipbuilding",
                "gate_lore",
                "pathfinding",
                "void_living",
                "immortality",
                "biomancy",
                "forbidden",
                name="branch",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("practitioners", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("secret", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("level >= 0", name=op.f("ck_holder_levels_level_min")),
        sa.CheckConstraint("practitioners >= 0", name=op.f("ck_holder_levels_practitioners_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_holder_levels_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "branch", name=op.f("pk_holder_levels")),
    )
    with op.batch_alter_table("holder_levels", schema=None) as batch_op:
        batch_op.create_index("ix_holder_levels_branch", ["branch"], unique=False)

    op.create_table(
        "holder_techniques",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
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
        sa.Column("secret", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_holder_techniques_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "technique", name=op.f("pk_holder_techniques")),
    )
    with op.batch_alter_table("holder_techniques", schema=None) as batch_op:
        batch_op.create_index("ix_holder_techniques_technique", ["technique"], unique=False)

    op.create_table(
        "ideology_adherents",
        sa.Column("ideology_entity_id", sa.Integer(), nullable=False),
        sa.Column("adherent_entity_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("state", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_ideology_adherents_strength_range")),
        sa.ForeignKeyConstraint(["adherent_entity_id"], ["entities.id"], name=op.f("fk_ideology_adherents_adherent_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ideology_entity_id"], ["entities.id"], name=op.f("fk_ideology_adherents_ideology_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ideology_entity_id", "adherent_entity_id", name=op.f("pk_ideology_adherents")),
    )
    with op.batch_alter_table("ideology_adherents", schema=None) as batch_op:
        batch_op.create_index("ix_ideology_adherents_adherent", ["adherent_entity_id"], unique=False)

    op.create_table(
        "ideology_profiles",
        sa.Column("ideology_entity_id", sa.Integer(), nullable=False),
        sa.Column("value_delta", sa.JSON(), nullable=False),
        sa.Column("tenets", sa.JSON(), nullable=False),
        sa.Column("founder_entity_id", sa.Integer(), nullable=True),
        sa.Column("appeal", sa.JSON(), nullable=False),
        sa.Column("texts", sa.JSON(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["founder_entity_id"], ["entities.id"], name=op.f("fk_ideology_profiles_founder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ideology_entity_id"], ["entities.id"], name=op.f("fk_ideology_profiles_ideology_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ideology_entity_id", name=op.f("pk_ideology_profiles")),
    )
    op.create_table(
        "ideology_tenets",
        sa.Column("ideology_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "tenet",
            sa.Enum(
                "legalism",
                "restraint",
                "egalitarianism",
                "divine_right",
                "mercantilism",
                "militarism",
                "asceticism",
                "rationalism",
                "nature_harmony",
                "xenophobia",
                "cosmopolitanism",
                "anti_god",
                "creatorism",
                name="tenet",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ideology_entity_id"], ["entities.id"], name=op.f("fk_ideology_tenets_ideology_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ideology_entity_id", "tenet", name=op.f("pk_ideology_tenets")),
    )
    op.create_table(
        "item_enchantments",
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "effect",
            sa.Enum(
                "damage",
                "heal",
                "weather_change",
                "curse",
                "bless",
                "ward",
                "scry",
                "bind",
                "summon",
                "raise_dead",
                "fertility",
                "harvest_blessing",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("rite_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_item_enchantments_item_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_item_enchantments_rite_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("item_entity_id", "effect", name=op.f("pk_item_enchantments")),
    )
    op.create_table(
        "item_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "deed",
            sa.Enum(
                "made",
                "owned",
                "kill",
                "battle",
                "coronation",
                "lost",
                "theft",
                "burial",
                "broken",
                "repaired",
                "enchanted",
                name="deed",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("actor_entity_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=480), nullable=False),
        sa.ForeignKeyConstraint(["actor_entity_id"], ["entities.id"], name=op.f("fk_item_history_actor_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_item_history_item_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_history")),
    )
    with op.batch_alter_table("item_history", schema=None) as batch_op:
        batch_op.create_index("ix_item_history_item", ["item_entity_id", "epoch"], unique=False)

    op.create_table(
        "item_profiles",
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "item_class",
            sa.Enum(
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
                name="item_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("material", sa.String(length=120), nullable=True),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("damage_type", sa.String(length=120), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("coverage", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column(
            "curse",
            sa.Enum("none", "bloodthirst", "misfortune", "wasting", "madness", "betrayal", name="curse", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("renown", sa.Integer(), nullable=False),
        sa.Column("maker_entity_id", sa.Integer(), nullable=True),
        sa.Column("regalia_of_entity_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.Boolean(), nullable=False),
        sa.Column("prosthesis_for", sa.String(length=120), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_item_profiles_condition_range")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_item_profiles_quality_range")),
        sa.CheckConstraint("renown BETWEEN 0 AND 100", name=op.f("ck_item_profiles_renown_range")),
        sa.CheckConstraint("value >= 0", name=op.f("ck_item_profiles_value_min")),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_item_profiles_item_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maker_entity_id"], ["entities.id"], name=op.f("fk_item_profiles_maker_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regalia_of_entity_id"], ["entities.id"], name=op.f("fk_item_profiles_regalia_of_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("item_entity_id", name=op.f("pk_item_profiles")),
    )
    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_item_profiles_regalia_of_entity_id"), ["regalia_of_entity_id"], unique=False)

    op.create_table(
        "language_intelligibility",
        sa.Column("first_entity_id", sa.Integer(), nullable=False),
        sa.Column("second_entity_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("first_entity_id < second_entity_id", name=op.f("ck_language_intelligibility_ordered_pair")),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_language_intelligibility_value_range")),
        sa.ForeignKeyConstraint(["first_entity_id"], ["entities.id"], name=op.f("fk_language_intelligibility_first_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_entity_id"], ["entities.id"], name=op.f("fk_language_intelligibility_second_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("first_entity_id", "second_entity_id", name=op.f("pk_language_intelligibility")),
    )
    op.create_table(
        "language_standing",
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("standardisation", sa.Integer(), nullable=False),
        sa.Column("liturgical", sa.Boolean(), nullable=False),
        sa.Column("lingua_franca", sa.Boolean(), nullable=False),
        sa.Column("prestige_parts", sa.JSON(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_language_standing_prestige_range")),
        sa.CheckConstraint("standardisation BETWEEN 0 AND 100", name=op.f("ck_language_standing_standardisation_range")),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_language_standing_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("language_entity_id", name=op.f("pk_language_standing")),
    )
    op.create_table(
        "prophecy_conditions",
        sa.Column("prophecy_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "predicate",
            sa.Enum(
                "dies",
                "falls",
                "born_in",
                "sky_event",
                "war_between",
                "ruler_of",
                "within_epochs",
                name="predicate",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("deadline_epoch", sa.Integer(), nullable=True),
        sa.Column("consequence", sa.JSON(), nullable=False),
        sa.Column("seer_entity_id", sa.Integer(), nullable=True),
        sa.Column("audience", sa.JSON(), nullable=False),
        sa.Column("pressure", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum("pending", "fulfilled", "failed", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("pressure BETWEEN 0 AND 100", name=op.f("ck_prophecy_conditions_pressure_range")),
        sa.ForeignKeyConstraint(["prophecy_entity_id"], ["entities.id"], name=op.f("fk_prophecy_conditions_prophecy_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seer_entity_id"], ["entities.id"], name=op.f("fk_prophecy_conditions_seer_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("prophecy_entity_id", name=op.f("pk_prophecy_conditions")),
    )
    op.create_table(
        "rite_effects",
        sa.Column("rite_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "effect",
            sa.Enum(
                "damage",
                "heal",
                "weather_change",
                "curse",
                "bless",
                "ward",
                "scry",
                "bind",
                "summon",
                "raise_dead",
                "fertility",
                "harvest_blessing",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("detail", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_rite_effects_rite_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rite_entity_id", "effect", name=op.f("pk_rite_effects")),
    )
    op.create_table(
        "rite_profiles",
        sa.Column("rite_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "school",
            sa.Enum(
                "elemental_fire",
                "elemental_water",
                "earth",
                "storm",
                "life",
                "death",
                "mind",
                "illusion",
                "divination",
                "warding",
                "binding",
                "summoning",
                "blood",
                "void",
                name="school",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum("ley", "divine", "blood", "soul", "reagent", "void", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("cost", sa.JSON(), nullable=False),
        sa.Column("power", sa.Integer(), nullable=False),
        sa.Column("backlash_chance", sa.Integer(), nullable=False),
        sa.Column(
            "backlash",
            sa.Enum("injury", "madness", "leak", "escape", "phenomenon", name="backlash", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("holy", sa.Boolean(), nullable=False),
        sa.Column("heretical", sa.Boolean(), nullable=False),
        sa.Column("inventor_entity_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("backlash_chance BETWEEN 0 AND 100", name=op.f("ck_rite_profiles_backlash_chance_range")),
        sa.CheckConstraint("power BETWEEN 1 AND 10", name=op.f("ck_rite_profiles_power_range")),
        sa.ForeignKeyConstraint(["inventor_entity_id"], ["entities.id"], name=op.f("fk_rite_profiles_inventor_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_rite_profiles_rite_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rite_entity_id", name=op.f("pk_rite_profiles")),
    )
    op.create_table(
        "speaker_cohorts",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("native", "second", "liturgical", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("share BETWEEN 0 AND 100", name=op.f("ck_speaker_cohorts_share_range")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_speaker_cohorts_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_speaker_cohorts_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "language_entity_id", "kind", name=op.f("pk_speaker_cohorts")),
    )
    with op.batch_alter_table("speaker_cohorts", schema=None) as batch_op:
        batch_op.create_index("ix_speaker_cohorts_language", ["language_entity_id"], unique=False)

    op.create_table(
        "tradition_participation",
        sa.Column("tradition_entity_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("participation", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("last_celebrated_epoch", sa.Integer(), nullable=True),
        sa.Column("skipped", sa.Integer(), nullable=False),
        sa.CheckConstraint("participation BETWEEN 0 AND 100", name=op.f("ck_tradition_participation_participation_range")),
        sa.ForeignKeyConstraint(
            ["community_entity_id"], ["entities.id"], name=op.f("fk_tradition_participation_community_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tradition_entity_id"], ["entities.id"], name=op.f("fk_tradition_participation_tradition_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("tradition_entity_id", "community_entity_id", name=op.f("pk_tradition_participation")),
    )
    with op.batch_alter_table("tradition_participation", schema=None) as batch_op:
        batch_op.create_index("ix_tradition_participation_community", ["community_entity_id"], unique=False)

    op.create_table(
        "legend_profiles",
        sa.Column("legend_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "archetype",
            sa.Enum(
                "hero_quest",
                "monster",
                "trickster",
                "creation",
                "flood",
                "betrayal",
                "lost_paradise",
                "chosen_one",
                "cursed_line",
                "return_of_the_king",
                "haunted_place",
                name="archetype",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("credence", sa.Integer(), nullable=False),
        sa.Column("distortion", sa.Integer(), nullable=False),
        sa.Column("source_incident_id", sa.Integer(), nullable=True),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("moral", sa.JSON(), nullable=False),
        sa.Column("tellers", sa.JSON(), nullable=False),
        sa.Column("fixed_in_entity_id", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("credence BETWEEN 0 AND 100", name=op.f("ck_legend_profiles_credence_range")),
        sa.CheckConstraint("distortion BETWEEN 0 AND 100", name=op.f("ck_legend_profiles_distortion_range")),
        sa.ForeignKeyConstraint(["fixed_in_entity_id"], ["entities.id"], name=op.f("fk_legend_profiles_fixed_in_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legend_entity_id"], ["entities.id"], name=op.f("fk_legend_profiles_legend_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_incident_id"], ["incidents.id"], name=op.f("fk_legend_profiles_source_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_legend_profiles_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("legend_entity_id", name=op.f("pk_legend_profiles")),
    )
    op.create_table(
        "tradition_profiles",
        sa.Column("tradition_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "festival",
                "fast",
                "funeral_rite",
                "initiation",
                "marriage_rite",
                "coming_of_age",
                "taboo",
                "offering",
                "pilgrimage",
                "hospitality_law",
                "duel_custom",
                "mourning",
                "harvest_rite",
                "war_dance",
                "scar_rite",
                "ancestor_feast",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("calendar_slot", sa.String(length=120), nullable=True),
        sa.Column("cost", sa.JSON(), nullable=False),
        sa.Column("effects", sa.JSON(), nullable=False),
        sa.Column("taboo_target", sa.String(length=120), nullable=True),
        sa.Column("origin_incident_id", sa.Integer(), nullable=True),
        sa.Column("origin_entity_id", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["origin_entity_id"], ["entities.id"], name=op.f("fk_tradition_profiles_origin_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_incident_id"], ["incidents.id"], name=op.f("fk_tradition_profiles_origin_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tradition_entity_id"], ["entities.id"], name=op.f("fk_tradition_profiles_tradition_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tradition_entity_id", name=op.f("pk_tradition_profiles")),
    )


def downgrade() -> None:
    op.drop_table("tradition_profiles")
    op.drop_table("legend_profiles")
    with op.batch_alter_table("tradition_participation", schema=None) as batch_op:
        batch_op.drop_index("ix_tradition_participation_community")

    op.drop_table("tradition_participation")
    with op.batch_alter_table("speaker_cohorts", schema=None) as batch_op:
        batch_op.drop_index("ix_speaker_cohorts_language")

    op.drop_table("speaker_cohorts")
    op.drop_table("rite_profiles")
    op.drop_table("rite_effects")
    op.drop_table("prophecy_conditions")
    op.drop_table("language_standing")
    op.drop_table("language_intelligibility")
    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_item_profiles_regalia_of_entity_id"))

    op.drop_table("item_profiles")
    with op.batch_alter_table("item_history", schema=None) as batch_op:
        batch_op.drop_index("ix_item_history_item")

    op.drop_table("item_history")
    op.drop_table("item_enchantments")
    op.drop_table("ideology_tenets")
    op.drop_table("ideology_profiles")
    with op.batch_alter_table("ideology_adherents", schema=None) as batch_op:
        batch_op.drop_index("ix_ideology_adherents_adherent")

    op.drop_table("ideology_adherents")
    with op.batch_alter_table("holder_techniques", schema=None) as batch_op:
        batch_op.drop_index("ix_holder_techniques_technique")

    op.drop_table("holder_techniques")
    with op.batch_alter_table("holder_levels", schema=None) as batch_op:
        batch_op.drop_index("ix_holder_levels_branch")

    op.drop_table("holder_levels")
    with op.batch_alter_table("castings", schema=None) as batch_op:
        batch_op.drop_index("ix_castings_epoch")
        batch_op.drop_index("ix_castings_caster")

    op.drop_table("castings")
    op.drop_table("book_contents")
    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_artwork_profiles_subject_node_id"))

    op.drop_table("artwork_profiles")
    widen(False)
