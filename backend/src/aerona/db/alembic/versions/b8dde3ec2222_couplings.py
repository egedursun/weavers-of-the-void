import sqlalchemy as sa
from alembic import op

revision = "b8dde3ec2222"
down_revision = "1fdb2645b06e"
branch_labels = None
depends_on = None


LAW_OLD = (
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
)
LAW_NEW = (*LAW_OLD, "closed_season", "protected_waters", "catch_quota", "gear_ban")
OFFICE_OLD = (
    "ruler",
    "heir_designate",
    "regent",
    "chancellor",
    "marshal",
    "treasurer",
    "high_judge",
    "spymaster",
    "governor",
    "ambassador",
    "herald",
    "chaplain",
    "court_scholar",
    "head_of_state",
    "head_of_government",
    "minister",
    "general",
    "admiral",
    "speaker",
    "chief_scientist",
    "jester",
)
OFFICE_NEW = (*OFFICE_OLD, "warden")
ACCOUNT_OLD = ("official_chronicle", "folk_memory", "foreign_account", "gospel", "epic", "inscription", "founding_myth")
ACCOUNT_NEW = (*ACCOUNT_OLD, "elder_memory")
RETYPED = (
    ("accounts", "kind", ACCOUNT_OLD, ACCOUNT_NEW),
    ("law_proposals", "kind", LAW_OLD, LAW_NEW),
    ("law_profiles", "kind", LAW_OLD, LAW_NEW),
    ("offices", "kind", OFFICE_OLD, OFFICE_NEW),
    ("claims", "office", OFFICE_OLD, OFFICE_NEW),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, old, new in RETYPED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(before, column), type_=enum_of(after, column), existing_nullable=False)


def upgrade() -> None:
    op.create_table(
        "loop_signals",
        sa.Column(
            "loop",
            sa.Enum(
                *(
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
                ),
                name="loop",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_loop_signals_epoch_min")),
        sa.CheckConstraint("subject >= 0", name=op.f("ck_loop_signals_subject_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_loop_signals_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("loop", "holder_node_id", "subject", "epoch", name=op.f("pk_loop_signals")),
    )
    retype(forward=True)
    op.create_table(
        "carrion_pulses",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("carrion", sa.Integer(), nullable=False),
        sa.Column("scavenged", sa.Integer(), nullable=False),
        sa.Column("preserved", sa.Boolean(), nullable=False),
        sa.Column(
            "rest",
            sa.Enum("rotting", "mummified", "frozen", "drifting", "floating", name="rest", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("kept", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("carrion >= 0", name=op.f("ck_carrion_pulses_carrion_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_carrion_pulses_epoch_min")),
        sa.CheckConstraint("scavenged >= 0", name=op.f("ck_carrion_pulses_scavenged_min")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_carrion_pulses_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_carrion_pulses")),
    )
    op.create_table(
        "deep_seals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("structure", "rite", "divine", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("decay", sa.Integer(), nullable=False),
        sa.Column("sealer_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("broken_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("decay BETWEEN 0 AND 100", name=op.f("ck_deep_seals_decay_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_deep_seals_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_deep_seals_strength_range")),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_deep_seals_place_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sealer_node_id"], ["nodes.id"], name=op.f("fk_deep_seals_sealer_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deep_seals")),
    )
    with op.batch_alter_table("deep_seals", schema=None) as batch_op:
        batch_op.create_index("ix_deep_seals_place", ["place_entity_id"], unique=False)

    op.create_table(
        "novelty_stocks",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("novelty", sa.Integer(), nullable=False),
        sa.Column("adoption", sa.Integer(), nullable=False),
        sa.Column("peak_epoch", sa.Integer(), nullable=True),
        sa.Column("revivals", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("adoption BETWEEN 0 AND 100", name=op.f("ck_novelty_stocks_adoption_range")),
        sa.CheckConstraint("novelty BETWEEN 0 AND 100", name=op.f("ck_novelty_stocks_novelty_range")),
        sa.CheckConstraint("revivals >= 0", name=op.f("ck_novelty_stocks_revivals_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_novelty_stocks_updated_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_novelty_stocks_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_novelty_stocks")),
    )
    op.create_table(
        "rite_components",
        sa.Column("rite_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "component",
            sa.Enum(
                "spoken",
                "gestured",
                "inscribed",
                "sung",
                "danced",
                "material",
                "mental",
                name="component",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["rite_entity_id"], ["entities.id"], name=op.f("fk_rite_components_rite_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rite_entity_id", "component", name=op.f("pk_rite_components")),
    )
    op.create_table(
        "sign_origins",
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "cause",
            sa.Enum("deafness", "silence_vow", "hunting_silence", "mutilation", name="cause", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_sign_origins_since_epoch_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_sign_origins_community_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_sign_origins_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("language_entity_id", name=op.f("pk_sign_origins")),
    )
    op.create_table(
        "sociolects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("class", "caste", "guild", "court", "cant", "sailors", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("secret", sa.Boolean(), nullable=False),
        sa.Column("salience", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("faded_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("prestige BETWEEN -100 AND 100", name=op.f("ck_sociolects_prestige_range")),
        sa.CheckConstraint("salience BETWEEN 0 AND 100", name=op.f("ck_sociolects_salience_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_sociolects_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_sociolects_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_sociolects_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sociolects")),
    )
    with op.batch_alter_table("sociolects", schema=None) as batch_op:
        batch_op.create_index("ix_sociolects_holder", ["holder_entity_id"], unique=False)
        batch_op.create_index("ix_sociolects_language", ["language_entity_id"], unique=False)

    op.create_table(
        "teachings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_node_id", sa.Integer(), nullable=False),
        sa.Column("learner_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "song",
                "art_form",
                "rite",
                "technique",
                "true_name",
                "prophecy",
                "treasure",
                "language",
                "account",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum("taught", "blocked", "sold", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_teachings_epoch_min")),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_teachings_fidelity_range")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_teachings_price_min")),
        sa.ForeignKeyConstraint(["learner_entity_id"], ["entities.id"], name=op.f("fk_teachings_learner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_teachings_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["teacher_node_id"], ["nodes.id"], name=op.f("fk_teachings_teacher_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teachings")),
    )
    with op.batch_alter_table("teachings", schema=None) as batch_op:
        batch_op.create_index("ix_teachings_learner", ["learner_entity_id"], unique=False)
        batch_op.create_index("ix_teachings_teacher", ["teacher_node_id"], unique=False)

    op.create_table(
        "field_agreements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "parley", "truce", "surrender", "exchange", "safe_conduct", "fraternisation", name="kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "state", sa.Enum("kept", "ended", "broken", "repudiated", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("commander_entity_id", sa.Integer(), nullable=True),
        sa.Column("counterpart_entity_id", sa.Integer(), nullable=True),
        sa.Column("place_entity_id", sa.Integer(), nullable=True),
        sa.Column("term_epoch", sa.Integer(), nullable=True),
        sa.Column("honour", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_field_agreements_epoch_min")),
        sa.CheckConstraint("honour BETWEEN -100 AND 100", name=op.f("ck_field_agreements_honour_range")),
        sa.ForeignKeyConstraint(["commander_entity_id"], ["entities.id"], name=op.f("fk_field_agreements_commander_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["counterpart_entity_id"], ["entities.id"], name=op.f("fk_field_agreements_counterpart_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_field_agreements_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_field_agreements_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_agreements")),
    )
    with op.batch_alter_table("field_agreements", schema=None) as batch_op:
        batch_op.create_index("ix_field_agreements_war", ["war_id"], unique=False)

    op.create_table(
        "captive_restraints",
        sa.Column("captive_id", sa.Integer(), nullable=False),
        sa.Column(
            "restraint", sa.Enum("gag", "bound_hands", "blindfold", name="restraint", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.ForeignKeyConstraint(["captive_id"], ["captives.id"], name=op.f("fk_captive_restraints_captive_id_captives"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("captive_id", "restraint", name=op.f("pk_captive_restraints")),
    )
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sinecure", sa.Boolean(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_table("loop_signals")
    op.execute("DELETE FROM accounts WHERE kind = 'elder_memory'")
    op.execute("DELETE FROM law_proposals WHERE kind IN ('closed_season', 'protected_waters', 'catch_quota', 'gear_ban')")
    op.execute(
        "DELETE FROM entities WHERE id IN (SELECT law_entity_id FROM law_profiles WHERE kind IN ('closed_season', 'protected_waters', 'catch_quota', 'gear_ban'))"
    )
    op.execute("DELETE FROM offices WHERE kind = 'warden'")
    op.execute("UPDATE claims SET office = 'ruler' WHERE office = 'warden'")
    retype(forward=False)
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.drop_column("sinecure")

    op.drop_table("captive_restraints")
    with op.batch_alter_table("field_agreements", schema=None) as batch_op:
        batch_op.drop_index("ix_field_agreements_war")

    op.drop_table("field_agreements")
    with op.batch_alter_table("teachings", schema=None) as batch_op:
        batch_op.drop_index("ix_teachings_teacher")
        batch_op.drop_index("ix_teachings_learner")

    op.drop_table("teachings")
    with op.batch_alter_table("sociolects", schema=None) as batch_op:
        batch_op.drop_index("ix_sociolects_language")
        batch_op.drop_index("ix_sociolects_holder")

    op.drop_table("sociolects")
    op.drop_table("sign_origins")
    op.drop_table("rite_components")
    op.drop_table("novelty_stocks")
    with op.batch_alter_table("deep_seals", schema=None) as batch_op:
        batch_op.drop_index("ix_deep_seals_place")

    op.drop_table("deep_seals")
    op.drop_table("carrion_pulses")
