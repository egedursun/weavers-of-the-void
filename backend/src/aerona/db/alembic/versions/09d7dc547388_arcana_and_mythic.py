import sqlalchemy as sa
from alembic import op

revision = "09d7dc547388"
down_revision = "3c7d9e21b4a6"
branch_labels = None
depends_on = None

OLD_PACKAGES = (
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
)
NEW_PACKAGES = (*OLD_PACKAGES, "warping", "vis_dependence", "geas_doom", "soul_trapped")
OLD_CONDITIONS = (
    "chronic_illness",
    "paranoia",
    "visions",
    "rage",
    "melancholy",
    "addiction",
    "age_blindness",
    "age_deafness",
    "withered_limb",
    "endless_hunger",
    "possession",
    "void_taint",
    "chosen_mark",
    "divine_brand",
    "nightmares",
)
NEW_CONDITIONS = (*OLD_CONDITIONS, "comatose")
OLD_EFFECTS = (
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
    "seal_soul",
    "unseal_soul",
    "exorcise",
)
NEW_EFFECTS = (*OLD_EFFECTS, "dispel", "longevity")
OLD_COLLECTIONS = (
    "war",
    "battle",
    "siege",
    "duel",
    "abduction",
    "beast_attack",
    "raid",
    "persecution",
    "purge",
    "insurrection",
    "coup",
    "succession_crisis",
    "occupation",
    "journey",
    "pilgrimage",
    "competition",
    "performance",
    "procession",
    "ceremony",
    "wedding",
    "funeral",
    "coronation",
    "feast",
    "tournament",
    "hunt",
    "council",
    "summit",
    "plague",
    "famine",
    "migration",
    "founding",
    "theft",
    "investigation",
    "trial",
    "conversion_wave",
    "schism",
    "excavation",
)
NEW_COLLECTIONS = (*OLD_COLLECTIONS, "heroquest")
OLD_PLOTS = (
    "murder",
    "abduct",
    "seduce",
    "sway",
    "fabricate_claim",
    "fabricate_hook",
    "steal_relic",
    "coup",
    "poison_well",
    "frame",
    "elope",
    "convert_secretly",
    "sabotage_wedding",
    "free_prisoner",
    "ecosabotage",
    "learn_true_name",
    "forge_letter",
)
NEW_PLOTS = (*OLD_PLOTS, "geas_trap")
OLD_GOALS = (
    "be_worshipped",
    "found_realm",
    "destroy_rival",
    "spread_domain",
    "win_war",
    "acquire_relic",
    "raise_hero",
    "awaken_god",
    "defeat_foreign_god",
    "reconcile",
    "rebel",
    "hold_thrones",
)
NEW_GOALS = (*OLD_GOALS, "prevent_mantling", "sponsor_mantling")
OLD_MOTIONS = (
    "none",
    "against_doomsday",
    "joint_blessing",
    "condemn_rebel",
    "call_for_peace",
    "war_on_foreign_god",
    "divide_worlds",
    "outlaw_rite",
    "punish_son",
    "bless_hero",
    "holy_world",
    "cosmic_truce",
    "petition_creator",
)
NEW_MOTIONS = (*OLD_MOTIONS, "appoint_office")


def widen(table: str, column: str, old: tuple[str, ...], new: tuple[str, ...], *, nullable: bool) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=sa.Enum(*old, name=column, native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name=column, native_enum=False, create_constraint=True, length=40),
            existing_nullable=nullable,
        )


COLUMNS = (
    ("afflictions", "package", OLD_PACKAGES, NEW_PACKAGES, False),
    ("conditions", "kind", OLD_CONDITIONS, NEW_CONDITIONS, False),
    ("creature_anatomy", "bite", OLD_PACKAGES, NEW_PACKAGES, True),
    ("rite_effects", "effect", OLD_EFFECTS, NEW_EFFECTS, False),
    ("item_enchantments", "effect", OLD_EFFECTS, NEW_EFFECTS, False),
    ("incident_collections", "kind", OLD_COLLECTIONS, NEW_COLLECTIONS, False),
    ("schemes", "kind", OLD_PLOTS, NEW_PLOTS, False),
    ("son_goals", "kind", OLD_GOALS, NEW_GOALS, False),
    ("council_rulings", "motion", OLD_MOTIONS, NEW_MOTIONS, False),
)


def upgrade() -> None:
    for table, column, old, new, nullable in COLUMNS:
        widen(table, column, old, new, nullable=nullable)
    op.create_table(
        "cosmic_offices",
        sa.Column(
            "office",
            sa.Enum("dead", "gates", "stars", "oaths", "herald", "hunt", name="office", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "chosen_by",
            sa.Enum("council", "creator", "conquest", "mantling", name="chosen_by", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=True),
        sa.Column("neglect", sa.Integer(), nullable=False),
        sa.Column("duty", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("duty BETWEEN 0 AND 100", name=op.f("ck_cosmic_offices_duty_range")),
        sa.CheckConstraint("neglect BETWEEN 0 AND 100", name=op.f("ck_cosmic_offices_neglect_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_cosmic_offices_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("office", name=op.f("pk_cosmic_offices")),
    )
    op.create_table(
        "vis_stocks",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_vis_stocks_amount_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_vis_stocks_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "form", name=op.f("pk_vis_stocks")),
    )
    op.create_table(
        "warping",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("stage >= 0", name=op.f("ck_warping_stage_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_warping_updated_epoch_min")),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_warping_value_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_warping_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_warping")),
    )
    op.create_table(
        "geasa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bearer_entity_id", sa.Integer(), nullable=False),
        sa.Column("layer_node_id", sa.Integer(), nullable=True),
        sa.Column("layer", sa.Enum("seer", "god", "rite", name="layer", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("mode", sa.Enum("taboo", "duty", name="mode", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "act",
            sa.Enum(
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
                name="act",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("state", sa.Enum("kept", "broken", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("favour", sa.Integer(), nullable=False),
        sa.Column("laid_epoch", sa.Integer(), nullable=False),
        sa.Column("last_kept_epoch", sa.Integer(), nullable=False),
        sa.Column("broken_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("favour BETWEEN 0 AND 100", name=op.f("ck_geasa_favour_range")),
        sa.CheckConstraint("laid_epoch >= 0", name=op.f("ck_geasa_laid_epoch_min")),
        sa.ForeignKeyConstraint(["bearer_entity_id"], ["entities.id"], name=op.f("fk_geasa_bearer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["layer_node_id"], ["nodes.id"], name=op.f("fk_geasa_layer_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_geasa")),
    )
    with op.batch_alter_table("geasa", schema=None) as batch_op:
        batch_op.create_index("ix_geasa_act", ["act"], unique=False)
        batch_op.create_index("ix_geasa_bearer", ["bearer_entity_id"], unique=False)

    op.create_table(
        "heroquests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quester_entity_id", sa.Integer(), nullable=False),
        sa.Column("legend_entity_id", sa.Integer(), nullable=True),
        sa.Column("god_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "realm", sa.Enum("palace", "dead", "dream", "sacred_site", name="realm", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("place_entity_id", sa.Integer(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column("deviated", sa.Boolean(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("questing", "succeeded", "failed", "trapped", "broken", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "boon",
            sa.Enum(
                "blessing",
                "item",
                "rite",
                "lifted_curse",
                "renewed_land",
                "favour",
                "true_name",
                "title",
                name="boon",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("interference", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("start_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_heroquests_fidelity_range")),
        sa.CheckConstraint("interference BETWEEN 0 AND 100", name=op.f("ck_heroquests_interference_range")),
        sa.CheckConstraint("start_epoch >= 0", name=op.f("ck_heroquests_start_epoch_min")),
        sa.CheckConstraint("step >= 0", name=op.f("ck_heroquests_step_min")),
        sa.CheckConstraint("steps >= 1", name=op.f("ck_heroquests_steps_min")),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_heroquests_collection_id_incident_collections"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_heroquests_god_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legend_entity_id"], ["entities.id"], name=op.f("fk_heroquests_legend_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_heroquests_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quester_entity_id"], ["entities.id"], name=op.f("fk_heroquests_quester_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_heroquests")),
    )
    with op.batch_alter_table("heroquests", schema=None) as batch_op:
        batch_op.create_index("ix_heroquests_quester", ["quester_entity_id"], unique=False)
        batch_op.create_index("ix_heroquests_state", ["state"], unique=False)

    op.create_table(
        "lab_texts",
        sa.Column("book_entity_id", sa.Integer(), nullable=False),
        sa.Column("rite_entity_id", sa.Integer(), nullable=False),
        sa.Column("author_entity_id", sa.Integer(), nullable=True),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_lab_texts_epoch_min")),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_lab_texts_fidelity_range")),
        sa.ForeignKeyConstraint(["author_entity_id"], ["entities.id"], name=op.f("fk_lab_texts_author_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["book_entity_id"], ["entities.id"], name=op.f("fk_lab_texts_book_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_lab_texts_rite_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("book_entity_id", name=op.f("pk_lab_texts")),
    )
    with op.batch_alter_table("lab_texts", schema=None) as batch_op:
        batch_op.create_index("ix_lab_texts_rite", ["rite_entity_id"], unique=False)

    op.create_table(
        "law_upkeep",
        sa.Column("law_entity_id", sa.Integer(), nullable=False),
        sa.Column("caster_node_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.Enum("authored", "enchantment", name="source", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("essence_upkeep", sa.Integer(), nullable=False),
        sa.Column(
            "vis_form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                name="vis_form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("vis_upkeep", sa.Integer(), nullable=False),
        sa.Column("dispel_resistance", sa.Integer(), nullable=False),
        sa.Column("unpaid_epochs", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dispel_resistance BETWEEN 0 AND 100", name=op.f("ck_law_upkeep_dispel_resistance_range")),
        sa.CheckConstraint("essence_upkeep >= 0", name=op.f("ck_law_upkeep_essence_upkeep_min")),
        sa.CheckConstraint("unpaid_epochs >= 0", name=op.f("ck_law_upkeep_unpaid_epochs_min")),
        sa.CheckConstraint("vis_upkeep >= 0", name=op.f("ck_law_upkeep_vis_upkeep_min")),
        sa.ForeignKeyConstraint(["caster_node_id"], ["nodes.id"], name=op.f("fk_law_upkeep_caster_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_law_upkeep_law_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("law_entity_id", name=op.f("pk_law_upkeep")),
    )
    with op.batch_alter_table("law_upkeep", schema=None) as batch_op:
        batch_op.create_index("ix_law_upkeep_caster", ["caster_node_id"], unique=False)

    op.create_table(
        "longevity",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("dose", sa.Integer(), nullable=False),
        sa.Column("dependence", sa.Integer(), nullable=False),
        sa.Column("years_gained", sa.Integer(), nullable=False),
        sa.Column("lapsed_epochs", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("dependence BETWEEN 0 AND 100", name=op.f("ck_longevity_dependence_range")),
        sa.CheckConstraint("dose >= 0", name=op.f("ck_longevity_dose_min")),
        sa.CheckConstraint("lapsed_epochs >= 0", name=op.f("ck_longevity_lapsed_epochs_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_longevity_since_epoch_min")),
        sa.CheckConstraint("years_gained >= 0", name=op.f("ck_longevity_years_gained_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_longevity_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_longevity")),
    )
    op.create_table(
        "mantlings",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=True),
        sa.Column("deeds", sa.Integer(), nullable=False),
        sa.Column("worship", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("walking", "ascended", "replaced", "blocked", "failed", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("deeds >= 0", name=op.f("ck_mantlings_deeds_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_mantlings_progress_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_mantlings_since_epoch_min")),
        sa.CheckConstraint("worship >= 0", name=op.f("ck_mantlings_worship_min")),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_mantlings_god_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_mantlings_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_mantlings")),
    )
    with op.batch_alter_table("mantlings", schema=None) as batch_op:
        batch_op.create_index("ix_mantlings_god", ["god_node_id"], unique=False)

    op.create_table(
        "rite_grammar",
        sa.Column("rite_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "technique",
            sa.Enum(
                "create",
                "perceive",
                "transform",
                "destroy",
                "control",
                "bind",
                "summon",
                "ward",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("range", sa.Enum("touch", "sight", "region", "world", name="range", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "duration",
            sa.Enum("instant", "season", "epoch", "permanent", name="duration", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "target", sa.Enum("one", "group", "structure", "region", name="target", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("paradigm_entity_id", sa.Integer(), nullable=True),
        sa.Column("myth_entity_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("difficulty >= 0", name=op.f("ck_rite_grammar_difficulty_min")),
        sa.ForeignKeyConstraint(["myth_entity_id"], ["entities.id"], name=op.f("fk_rite_grammar_myth_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["paradigm_entity_id"], ["entities.id"], name=op.f("fk_rite_grammar_paradigm_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_rite_grammar_rite_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rite_entity_id", name=op.f("pk_rite_grammar")),
    )
    op.create_table(
        "servitors",
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "rank",
            sa.Enum("herald", "guardian", "angel", "fury", "psychopomp", "choir", name="rank", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("origin", sa.Enum("made", "raised", "summoned", name="origin", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("role", sa.Enum("messenger", "guard", "judge", "host", name="role", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("post_entity_id", sa.Integer(), nullable=True),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("fallen_to_node_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_servitors_loyalty_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_servitors_since_epoch_min")),
        sa.ForeignKeyConstraint(["fallen_to_node_id"], ["nodes.id"], name=op.f("fk_servitors_fallen_to_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_servitors_god_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_entity_id"], ["entities.id"], name=op.f("fk_servitors_post_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_servitors_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("spirit_entity_id", name=op.f("pk_servitors")),
    )
    with op.batch_alter_table("servitors", schema=None) as batch_op:
        batch_op.create_index("ix_servitors_god", ["god_node_id"], unique=False)

    op.create_table(
        "heroquest_members",
        sa.Column("heroquest_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_heroquest_members_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["heroquest_id"], ["heroquests.id"], name=op.f("fk_heroquest_members_heroquest_id_heroquests"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("heroquest_id", "entity_id", name=op.f("pk_heroquest_members")),
    )
    with op.batch_alter_table("item_enchantments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("charges", sa.Integer(), server_default="3", nullable=False))
        batch_op.add_column(sa.Column("capacity", sa.Integer(), server_default="3", nullable=False))
        batch_op.add_column(
            sa.Column(
                "recharge",
                sa.Enum("site", "vis", "moon", "none", name="recharge", native_enum=False, create_constraint=True, length=40),
                server_default="vis",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("overuse", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    for table, column, old, new, nullable in COLUMNS:
        added = ", ".join(f"'{value}'" for value in new if value not in old)
        if nullable:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({added})")
        else:
            op.execute(f"DELETE FROM {table} WHERE {column} IN ({added})")
        widen(table, column, new, old, nullable=nullable)
    with op.batch_alter_table("item_enchantments", schema=None) as batch_op:
        batch_op.drop_column("overuse")
        batch_op.drop_column("recharge")
        batch_op.drop_column("capacity")
        batch_op.drop_column("charges")

    op.drop_table("heroquest_members")
    with op.batch_alter_table("servitors", schema=None) as batch_op:
        batch_op.drop_index("ix_servitors_god")

    op.drop_table("servitors")
    op.drop_table("rite_grammar")
    with op.batch_alter_table("mantlings", schema=None) as batch_op:
        batch_op.drop_index("ix_mantlings_god")

    op.drop_table("mantlings")
    op.drop_table("longevity")
    with op.batch_alter_table("law_upkeep", schema=None) as batch_op:
        batch_op.drop_index("ix_law_upkeep_caster")

    op.drop_table("law_upkeep")
    with op.batch_alter_table("lab_texts", schema=None) as batch_op:
        batch_op.drop_index("ix_lab_texts_rite")

    op.drop_table("lab_texts")
    with op.batch_alter_table("heroquests", schema=None) as batch_op:
        batch_op.drop_index("ix_heroquests_state")
        batch_op.drop_index("ix_heroquests_quester")

    op.drop_table("heroquests")
    with op.batch_alter_table("geasa", schema=None) as batch_op:
        batch_op.drop_index("ix_geasa_bearer")
        batch_op.drop_index("ix_geasa_act")

    op.drop_table("geasa")
    op.drop_table("warping")
    op.drop_table("vis_stocks")
    op.drop_table("cosmic_offices")
