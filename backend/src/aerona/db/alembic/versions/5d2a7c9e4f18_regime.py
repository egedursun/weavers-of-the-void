import sqlalchemy as sa
from alembic import op

revision = "5d2a7c9e4f18"
down_revision = "3b8e1f4c7d20"
branch_labels = None
depends_on = None

TECHNIQUES = (
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
    "cartography",
    "oral_law",
    "written_law",
    "codified_law",
    "bureaucracy",
    "census",
    "postal_service",
    "diplomatic_corps",
    "standing_army_admin",
    "double_entry",
    "joint_stock",
    "insurance",
    "guilds",
    "universities",
    "hospitals",
    "printing_press",
    "organised_clergy",
    "monasticism",
    "theology_schools",
    "logic",
    "natural_philosophy",
    "empiricism",
    "humanist_ideals",
)
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
    "usury",
    "infanticide",
    "abandoning_elders",
    "forced_labour",
)
ENTRIES = ("tax", "tolls", "investment", "garrison", "walls", "building", "festival", "alms", "fire", "plunder", "grant", "loan", "upkeep")
GATHERINGS = (
    "feast",
    "wedding",
    "funeral",
    "coronation",
    "tournament",
    "hunt",
    "pilgrimage",
    "council",
    "summit",
    "festival",
    "fair",
    "games",
    "performance",
    "trial",
    "execution",
    "procession",
    "milestone",
    "wake",
)
WIDENED = (
    ("gatherings", "kind", GATHERINGS, (*GATHERINGS, "examination"), False),
    ("creator_taboos", "act", ACTS, (*ACTS, "selling_offices"), False),
    ("culture_ethics", "act", ACTS, (*ACTS, "selling_offices"), False),
    ("geasa", "act", ACTS, (*ACTS, "selling_offices"), False),
    ("deeds", "act", ACTS, (*ACTS, "selling_offices"), True),
    ("tradition_profiles", "taboo_act", ACTS, (*ACTS, "selling_offices"), True),
    ("artifact_studies", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("guild_secrets", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("holder_techniques", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("institutions", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("research_boosts", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("research_focus", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("research_incidents", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), True),
    ("research_progress", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), False),
    ("excavation_stages", "technique", TECHNIQUES, (*TECHNIQUES, "examinations"), True),
    ("polity_treasury", "entry", ENTRIES, (*ENTRIES, "office_sale"), False),
    ("settlement_treasury", "entry", ENTRIES, (*ENTRIES, "office_sale"), False),
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
        "academic_freedom",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("orthodoxy_node_id", sa.Integer(), nullable=True),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 100", name=op.f("ck_academic_freedom_level_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_academic_freedom_updated_epoch_min")),
        sa.ForeignKeyConstraint(["orthodoxy_node_id"], ["nodes.id"], name=op.f("fk_academic_freedom_orthodoxy_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_academic_freedom_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_academic_freedom")),
    )
    op.create_table(
        "breeding_plans",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("house_entity_id", sa.Integer(), nullable=False),
        sa.Column("locus", sa.String(length=200), nullable=True),
        sa.Column("allele", sa.String(length=200), nullable=True),
        sa.Column("target_share", sa.Integer(), nullable=False),
        sa.Column("claim_polity_id", sa.Integer(), nullable=True),
        sa.Column("matches", sa.Integer(), nullable=False),
        sa.Column("love_matches", sa.Integer(), nullable=False),
        sa.Column("barren", sa.Integer(), nullable=False),
        sa.Column("concealed", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("barren >= 0", name=op.f("ck_breeding_plans_barren_min")),
        sa.CheckConstraint("concealed >= 0", name=op.f("ck_breeding_plans_concealed_min")),
        sa.CheckConstraint("love_matches >= 0", name=op.f("ck_breeding_plans_love_matches_min")),
        sa.CheckConstraint("matches >= 0", name=op.f("ck_breeding_plans_matches_min")),
        sa.CheckConstraint("target_share BETWEEN 0 AND 100", name=op.f("ck_breeding_plans_target_share_range")),
        sa.ForeignKeyConstraint(["claim_polity_id"], ["entities.id"], name=op.f("fk_breeding_plans_claim_polity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_breeding_plans_house_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["long_plans.id"], name=op.f("fk_breeding_plans_plan_id_long_plans"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", name=op.f("pk_breeding_plans")),
    )
    with op.batch_alter_table("breeding_plans", schema=None) as batch_op:
        batch_op.create_index("ix_breeding_plans_house", ["house_entity_id"], unique=False)

    op.create_table(
        "coalition_members",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("reward", sa.Integer(), nullable=False),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_coalition_members_loyalty_range")),
        sa.CheckConstraint("reward BETWEEN 0 AND 100", name=op.f("ck_coalition_members_reward_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_coalition_members_since_epoch_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_coalition_members_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_coalition_members_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "mortal_entity_id", name=op.f("pk_coalition_members")),
    )
    with op.batch_alter_table("coalition_members", schema=None) as batch_op:
        batch_op.create_index("ix_coalition_members_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("examination", "master", "doctor", "ordination", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("granter_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "skill",
            sa.Enum(
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
                "cryptography",
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
                name="skill",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_credentials_epoch_min")),
        sa.ForeignKeyConstraint(["granter_node_id"], ["nodes.id"], name=op.f("fk_credentials_granter_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_credentials_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credentials")),
    )
    with op.batch_alter_table("credentials", schema=None) as batch_op:
        batch_op.create_index("ix_credentials_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "exam_sittings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("candidates", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Integer(), nullable=False),
        sa.Column("mark", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("candidates >= 0", name=op.f("ck_exam_sittings_candidates_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_exam_sittings_epoch_min")),
        sa.CheckConstraint("mark BETWEEN 0 AND 100", name=op.f("ck_exam_sittings_mark_range")),
        sa.CheckConstraint("passed >= 0", name=op.f("ck_exam_sittings_passed_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_exam_sittings_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_sittings")),
    )
    with op.batch_alter_table("exam_sittings", schema=None) as batch_op:
        batch_op.create_index("ix_exam_sittings_polity", ["polity_entity_id", "epoch"], unique=False)

    op.create_table(
        "examinations",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=False),
        sa.Column("pass_mark", sa.Integer(), nullable=False),
        sa.Column("demand", sa.Integer(), nullable=False),
        sa.Column("last_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("demand BETWEEN 0 AND 100", name=op.f("ck_examinations_demand_range")),
        sa.CheckConstraint("interval BETWEEN 1 AND 100", name=op.f("ck_examinations_interval_range")),
        sa.CheckConstraint("pass_mark BETWEEN 0 AND 100", name=op.f("ck_examinations_pass_mark_range")),
        sa.CheckConstraint("quota >= 0", name=op.f("ck_examinations_quota_min")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_examinations_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_examinations")),
    )
    op.create_table(
        "lineage_segments",
        sa.Column("house_entity_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Enum("lineage", "clan", "tribe", name="level", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("tribe_entity_id", sa.Integer(), nullable=True),
        sa.Column("backs_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_lineage_segments_since_epoch_min")),
        sa.ForeignKeyConstraint(["backs_entity_id"], ["entities.id"], name=op.f("fk_lineage_segments_backs_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_lineage_segments_house_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tribe_entity_id"], ["entities.id"], name=op.f("fk_lineage_segments_tribe_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("house_entity_id", name=op.f("pk_lineage_segments")),
    )
    with op.batch_alter_table("lineage_segments", schema=None) as batch_op:
        batch_op.create_index("ix_lineage_segments_tribe", ["tribe_entity_id"], unique=False)

    op.create_table(
        "patronage_ties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patron_node_id", sa.Integer(), nullable=False),
        sa.Column("client_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("household", "retainer", "official", "commander", name="role", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_patronage_ties_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_patronage_ties_strength_range")),
        sa.ForeignKeyConstraint(["client_entity_id"], ["entities.id"], name=op.f("fk_patronage_ties_client_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patron_node_id"], ["nodes.id"], name=op.f("fk_patronage_ties_patron_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patronage_ties")),
    )
    with op.batch_alter_table("patronage_ties", schema=None) as batch_op:
        batch_op.create_index("ix_patronage_ties_client", ["client_entity_id"], unique=False)
        batch_op.create_index("ix_patronage_ties_patron", ["patron_node_id"], unique=False)

    op.create_table(
        "power_bases",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("holdings", sa.Integer(), nullable=False),
        sa.Column("troops", sa.Integer(), nullable=False),
        sa.Column("offices", sa.Integer(), nullable=False),
        sa.Column("wealth", sa.Integer(), nullable=False),
        sa.Column("popularity", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("threat", sa.Integer(), nullable=False),
        sa.Column(
            "stance", sa.Enum("loyal", "defiant", "extorting", "plotting", name="stance", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("holdings >= 0", name=op.f("ck_power_bases_holdings_min")),
        sa.CheckConstraint("offices >= 0", name=op.f("ck_power_bases_offices_min")),
        sa.CheckConstraint("popularity BETWEEN 0 AND 100", name=op.f("ck_power_bases_popularity_range")),
        sa.CheckConstraint("threat BETWEEN 0 AND 100", name=op.f("ck_power_bases_threat_range")),
        sa.CheckConstraint("total >= 0", name=op.f("ck_power_bases_total_min")),
        sa.CheckConstraint("troops >= 0", name=op.f("ck_power_bases_troops_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_power_bases_updated_epoch_min")),
        sa.CheckConstraint("wealth >= 0", name=op.f("ck_power_bases_wealth_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_power_bases_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_power_bases_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_power_bases")),
    )
    op.create_table(
        "regimes",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "selectorate",
            sa.Enum("tribe", "nobles", "council", "army", "priests", "citizens", name="selectorate", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("selectorate_size", sa.Integer(), nullable=False),
        sa.Column("coalition_size", sa.Integer(), nullable=False),
        sa.Column("coalition_loyalty", sa.Integer(), nullable=False),
        sa.Column("public_share", sa.Integer(), nullable=False),
        sa.Column("traditional", sa.Integer(), nullable=False),
        sa.Column("charismatic", sa.Integer(), nullable=False),
        sa.Column("rational", sa.Integer(), nullable=False),
        sa.Column("founder_entity_id", sa.Integer(), nullable=True),
        sa.Column("ruler_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "routinisation",
            sa.Enum("none", "pending", "dynasty", "institution", "schism", name="routinisation", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("crisis_epoch", sa.Integer(), nullable=True),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("extraction", sa.Integer(), nullable=False),
        sa.Column("institutions", sa.Integer(), nullable=False),
        sa.Column(
            "leadership", sa.Enum("achieved", "ascribed", "state", name="leadership", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("rotation", sa.Boolean(), nullable=False),
        sa.Column("parallel_guard", sa.Boolean(), nullable=False),
        sa.Column("loyalty_promotion", sa.Boolean(), nullable=False),
        sa.Column("hostages", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("charismatic BETWEEN 0 AND 100", name=op.f("ck_regimes_charismatic_range")),
        sa.CheckConstraint("coalition_loyalty BETWEEN 0 AND 100", name=op.f("ck_regimes_coalition_loyalty_range")),
        sa.CheckConstraint("coalition_size >= 0", name=op.f("ck_regimes_coalition_size_min")),
        sa.CheckConstraint("extraction BETWEEN 0 AND 200", name=op.f("ck_regimes_extraction_range")),
        sa.CheckConstraint("horizon BETWEEN 0 AND 100", name=op.f("ck_regimes_horizon_range")),
        sa.CheckConstraint("institutions BETWEEN 0 AND 100", name=op.f("ck_regimes_institutions_range")),
        sa.CheckConstraint("public_share BETWEEN 0 AND 100", name=op.f("ck_regimes_public_share_range")),
        sa.CheckConstraint("rational BETWEEN 0 AND 100", name=op.f("ck_regimes_rational_range")),
        sa.CheckConstraint("selectorate_size >= 0", name=op.f("ck_regimes_selectorate_size_min")),
        sa.CheckConstraint("traditional BETWEEN 0 AND 100", name=op.f("ck_regimes_traditional_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_regimes_updated_epoch_min")),
        sa.ForeignKeyConstraint(["founder_entity_id"], ["entities.id"], name=op.f("fk_regimes_founder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_regimes_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ruler_entity_id"], ["entities.id"], name=op.f("fk_regimes_ruler_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_regimes")),
    )
    op.create_table(
        "school_lineages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("doctrine_entity_id", sa.Integer(), nullable=True),
        sa.Column("founder_entity_id", sa.Integer(), nullable=True),
        sa.Column("rival_id", sa.Integer(), nullable=True),
        sa.Column("persecuted", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_school_lineages_since_epoch_min")),
        sa.ForeignKeyConstraint(["doctrine_entity_id"], ["entities.id"], name=op.f("fk_school_lineages_doctrine_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["founder_entity_id"], ["entities.id"], name=op.f("fk_school_lineages_founder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rival_id"], ["school_lineages.id"], name=op.f("fk_school_lineages_rival_id_school_lineages"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_school_lineages")),
    )
    with op.batch_alter_table("school_lineages", schema=None) as batch_op:
        batch_op.create_index("ix_school_lineages_doctrine", ["doctrine_entity_id"], unique=False)

    op.create_table(
        "school_members",
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("master_entity_id", sa.Integer(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("generation >= 0", name=op.f("ck_school_members_generation_min")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_school_members_since_epoch_min")),
        sa.ForeignKeyConstraint(["master_entity_id"], ["entities.id"], name=op.f("fk_school_members_master_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_school_members_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["school_lineages.id"], name=op.f("fk_school_members_school_id_school_lineages"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("school_id", "mortal_entity_id", name=op.f("pk_school_members")),
    )
    with op.batch_alter_table("school_members", schema=None) as batch_op:
        batch_op.create_index("ix_school_members_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "venal_offices",
        sa.Column("office_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("buyer_entity_id", sa.Integer(), nullable=True),
        sa.Column("sinecure", sa.Boolean(), nullable=False),
        sa.Column("recouped", sa.Integer(), nullable=False),
        sa.Column("sold_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("price >= 0", name=op.f("ck_venal_offices_price_min")),
        sa.CheckConstraint("recouped >= 0", name=op.f("ck_venal_offices_recouped_min")),
        sa.CheckConstraint("sold_epoch >= 0", name=op.f("ck_venal_offices_sold_epoch_min")),
        sa.ForeignKeyConstraint(["buyer_entity_id"], ["entities.id"], name=op.f("fk_venal_offices_buyer_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["office_id"], ["offices.id"], name=op.f("fk_venal_offices_office_id_offices"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("office_id", name=op.f("pk_venal_offices")),
    )


def downgrade() -> None:
    op.drop_table("venal_offices")
    with op.batch_alter_table("school_members", schema=None) as batch_op:
        batch_op.drop_index("ix_school_members_mortal")

    op.drop_table("school_members")
    with op.batch_alter_table("school_lineages", schema=None) as batch_op:
        batch_op.drop_index("ix_school_lineages_doctrine")

    op.drop_table("school_lineages")
    op.drop_table("regimes")
    op.drop_table("power_bases")
    with op.batch_alter_table("patronage_ties", schema=None) as batch_op:
        batch_op.drop_index("ix_patronage_ties_patron")
        batch_op.drop_index("ix_patronage_ties_client")

    op.drop_table("patronage_ties")
    with op.batch_alter_table("lineage_segments", schema=None) as batch_op:
        batch_op.drop_index("ix_lineage_segments_tribe")

    op.drop_table("lineage_segments")
    op.drop_table("examinations")
    with op.batch_alter_table("exam_sittings", schema=None) as batch_op:
        batch_op.drop_index("ix_exam_sittings_polity")

    op.drop_table("exam_sittings")
    with op.batch_alter_table("credentials", schema=None) as batch_op:
        batch_op.drop_index("ix_credentials_mortal")

    op.drop_table("credentials")
    with op.batch_alter_table("coalition_members", schema=None) as batch_op:
        batch_op.drop_index("ix_coalition_members_mortal")

    op.drop_table("coalition_members")
    with op.batch_alter_table("breeding_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_breeding_plans_house")

    op.drop_table("breeding_plans")
    op.drop_table("academic_freedom")
    widen(False)
