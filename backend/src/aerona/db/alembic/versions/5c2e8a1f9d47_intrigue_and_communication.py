import sqlalchemy as sa
from alembic import op

revision = "5c2e8a1f9d47"
down_revision = "18f9896a5251"
branch_labels = None
depends_on = None

INTENTS = ("friendship", "alliance", "love", "threat", "mockery", "warning", "bargain", "prayer", "answer", "chat", "dream", "command")
OFFICES = ("ruler", "heir_designate", "regent", "chancellor", "marshal", "treasurer", "high_judge", "spymaster", "governor", "ambassador")
LAWS = (
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
    "blood_feud",
    "quarantine",
    "burial_law",
    "sanitation",
    "magic_ban",
    "licensed_magic",
    "rite_restrictions",
    "custom",
)
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
)
SKILLS = (
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
)
WIDENED = (
    ("messages", "intent", INTENTS, (*INTENTS, "dispatch"), False),
    ("offices", "kind", OFFICES, (*OFFICES, "herald"), False),
    ("claims", "office", OFFICES, (*OFFICES, "herald"), False),
    ("law_profiles", "kind", LAWS, (*LAWS, "censorship"), False),
    ("holder_techniques", "technique", TECHNIQUES, (*TECHNIQUES, "cryptography"), False),
    ("research_progress", "technique", TECHNIQUES, (*TECHNIQUES, "cryptography"), False),
    ("skills", "skill", SKILLS, (*SKILLS, "cryptography"), False),
    ("reputations", "skill", SKILLS, (*SKILLS, "cryptography"), True),
    ("deeds", "skill", SKILLS, (*SKILLS, "cryptography"), True),
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
        "beliefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column("attribute", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("as_of_epoch", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "observation", "message", "rumour", "spy", "scout", "records", "deception", name="source", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("false", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("as_of_epoch >= 0", name=op.f("ck_beliefs_as_of_epoch_min")),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100", name=op.f("ck_beliefs_confidence_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_beliefs_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_beliefs_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beliefs")),
    )
    with op.batch_alter_table("beliefs", schema=None) as batch_op:
        batch_op.create_index("ix_beliefs_holder_subject", ["holder_node_id", "subject_node_id"], unique=False)

    op.create_table(
        "ciphers",
        sa.Column("owner_node_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("broken_by", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.JSON(), nullable=False),
        sa.Column("break_known", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_ciphers_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_ciphers_strength_range")),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_ciphers_owner_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("owner_node_id", name=op.f("pk_ciphers")),
    )
    op.create_table(
        "favours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owed_by_node_id", sa.Integer(), nullable=False),
        sa.Column("owed_to_node_id", sa.Integer(), nullable=False),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column(
            "origin",
            sa.Enum("gift", "rescue", "war_support", "succession_support", "scheme_aid", name="origin", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("called_epoch", sa.Integer(), nullable=True),
        sa.Column("honoured", sa.Boolean(), nullable=True),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_favours_created_epoch_min")),
        sa.CheckConstraint("magnitude BETWEEN 0 AND 100", name=op.f("ck_favours_magnitude_range")),
        sa.ForeignKeyConstraint(["owed_by_node_id"], ["nodes.id"], name=op.f("fk_favours_owed_by_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owed_to_node_id"], ["nodes.id"], name=op.f("fk_favours_owed_to_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favours")),
    )
    with op.batch_alter_table("favours", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_favours_owed_by_node_id"), ["owed_by_node_id"], unique=False)
        batch_op.create_index("ix_favours_owed_to", ["owed_to_node_id"], unique=False)

    op.create_table(
        "identities",
        sa.Column("mortal_node_id", sa.Integer(), nullable=False),
        sa.Column("false_name", sa.String(length=200), nullable=False),
        sa.Column("cover_role", sa.String(length=120), nullable=True),
        sa.Column("community_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "reason", sa.Enum("spy", "blood_curse", "exile", "impostor", name="reason", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("exposure", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("exposed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("exposure BETWEEN 0 AND 100", name=op.f("ck_identities_exposure_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_identities_since_epoch_min")),
        sa.ForeignKeyConstraint(["community_node_id"], ["nodes.id"], name=op.f("fk_identities_community_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_node_id"], ["nodes.id"], name=op.f("fk_identities_mortal_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_node_id", name=op.f("pk_identities")),
    )
    op.create_table(
        "public_opinion",
        sa.Column("community_node_id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "subject", sa.Enum("ruler", "law", "war", "god", "ideology", name="subject", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("approval", sa.Integer(), nullable=False),
        sa.Column("censored", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("approval BETWEEN -100 AND 100", name=op.f("ck_public_opinion_approval_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_public_opinion_epoch_min")),
        sa.ForeignKeyConstraint(["community_node_id"], ["nodes.id"], name=op.f("fk_public_opinion_community_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_public_opinion_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_node_id", "subject_node_id", name=op.f("pk_public_opinion")),
    )
    with op.batch_alter_table("public_opinion", schema=None) as batch_op:
        batch_op.create_index("ix_public_opinion_subject", ["subject_node_id"], unique=False)

    op.create_table(
        "schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("agents", sa.JSON(), nullable=False),
        sa.Column("power", sa.Integer(), nullable=False),
        sa.Column("secrecy", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column(
            "phase",
            sa.Enum(
                "recruit",
                "prepare",
                "execute",
                "succeeded",
                "failed",
                "exposed",
                "abandoned",
                name="phase",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("discovered_by", sa.JSON(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("power >= 0", name=op.f("ck_schemes_power_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_schemes_progress_range")),
        sa.CheckConstraint("secrecy BETWEEN 0 AND 100", name=op.f("ck_schemes_secrecy_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_schemes_started_epoch_min")),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_schemes_owner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_schemes_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schemes")),
    )
    with op.batch_alter_table("schemes", schema=None) as batch_op:
        batch_op.create_index("ix_schemes_owner", ["owner_node_id"], unique=False)
        batch_op.create_index("ix_schemes_target", ["target_node_id"], unique=False)

    op.create_table(
        "secrets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "affair",
                "illegitimate_child",
                "murder",
                "heresy",
                "secret_cult_membership",
                "debt",
                "crime",
                "cowardice_in_battle",
                "hidden_condition",
                "false_identity",
                "deal_with_outer_being",
                "true_parentage",
                "broken_oath",
                "ecosabotage",
                "broken_cipher",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("about_node_id", sa.Integer(), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("known_by", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("exposed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_secrets_created_epoch_min")),
        sa.CheckConstraint("severity BETWEEN 0 AND 100", name=op.f("ck_secrets_severity_range")),
        sa.ForeignKeyConstraint(["about_node_id"], ["nodes.id"], name=op.f("fk_secrets_about_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_secrets_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_secrets")),
    )
    with op.batch_alter_table("secrets", schema=None) as batch_op:
        batch_op.create_index("ix_secrets_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "true_names",
        sa.Column("bearer_node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("language_node_id", sa.Integer(), nullable=True),
        sa.Column("known_by", sa.JSON(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_true_names_since_epoch_min")),
        sa.ForeignKeyConstraint(["bearer_node_id"], ["nodes.id"], name=op.f("fk_true_names_bearer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_node_id"], ["nodes.id"], name=op.f("fk_true_names_language_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("bearer_node_id", name=op.f("pk_true_names")),
    )
    op.create_table(
        "hooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Enum("weak", "strong", name="strength", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "source",
            sa.Enum("secret", "debt", "favour", "hostage", "true_name", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("secret_id", sa.Integer(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("used_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "last_demand", sa.Enum("marriage", "step_down", "support", name="last_demand", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_hooks_created_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_hooks_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["secret_id"], ["secrets.id"], name=op.f("fk_hooks_secret_id_secrets"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_hooks_target_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hooks")),
    )
    with op.batch_alter_table("hooks", schema=None) as batch_op:
        batch_op.create_index("ix_hooks_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_hooks_target", ["target_node_id"], unique=False)

    op.create_table(
        "signal_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("fire_beacon", "mirror_tower", "post_station", "sending_stone", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("from_region_id", sa.Integer(), nullable=False),
        sa.Column("to_region_id", sa.Integer(), nullable=False),
        sa.Column("item_node_id", sa.Integer(), nullable=True),
        sa.Column("state", sa.Enum("active", "captured", "burned", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_signal_links_since_epoch_min")),
        sa.ForeignKeyConstraint(["from_region_id"], ["entities.id"], name=op.f("fk_signal_links_from_region_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_node_id"], ["nodes.id"], name=op.f("fk_signal_links_item_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_node_id"], ["nodes.id"], name=op.f("fk_signal_links_owner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_region_id"], ["entities.id"], name=op.f("fk_signal_links_to_region_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_links")),
    )
    with op.batch_alter_table("signal_links", schema=None) as batch_op:
        batch_op.create_index("ix_signal_links_owner", ["owner_node_id"], unique=False)

    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "medium",
                sa.Enum(
                    "envoy",
                    "letter",
                    "herald",
                    "signal_fire",
                    "dream",
                    "bird",
                    "magic_sending",
                    name="medium",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "content",
                sa.Enum(
                    "proposal",
                    "demand",
                    "threat",
                    "insult",
                    "gift_notice",
                    "declaration",
                    "report",
                    "plea",
                    "intelligence",
                    name="content",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "state",
                sa.Enum("under_way", "delivered", "intercepted", "lost", name="state", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("language_node_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("envoy_node_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "envoy_fate",
                sa.Enum("received", "insulted", "imprisoned", "killed", name="envoy_fate", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("intercepted_by_node_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("arrival_epoch", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("forged", sa.Boolean(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("misread", sa.Boolean(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("enciphered", sa.Boolean(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.create_foreign_key(batch_op.f("fk_messages_language_node_id_nodes"), "nodes", ["language_node_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_messages_intercepted_by_node_id_nodes"), "nodes", ["intercepted_by_node_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_messages_envoy_node_id_nodes"), "nodes", ["envoy_node_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_messages_envoy_node_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_messages_intercepted_by_node_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_messages_language_node_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("ck_messages_medium"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_messages_content"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_messages_state"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_messages_envoy_fate"), type_="check")
        batch_op.drop_column("locked")
        batch_op.drop_column("enciphered")
        batch_op.drop_column("misread")
        batch_op.drop_column("forged")
        batch_op.drop_column("arrival_epoch")
        batch_op.drop_column("payload")
        batch_op.drop_column("intercepted_by_node_id")
        batch_op.drop_column("envoy_fate")
        batch_op.drop_column("envoy_node_id")
        batch_op.drop_column("language_node_id")
        batch_op.drop_column("state")
        batch_op.drop_column("content")
        batch_op.drop_column("medium")

    with op.batch_alter_table("signal_links", schema=None) as batch_op:
        batch_op.drop_index("ix_signal_links_owner")

    op.drop_table("signal_links")
    with op.batch_alter_table("hooks", schema=None) as batch_op:
        batch_op.drop_index("ix_hooks_target")
        batch_op.drop_index("ix_hooks_holder")

    op.drop_table("hooks")
    op.drop_table("true_names")
    with op.batch_alter_table("secrets", schema=None) as batch_op:
        batch_op.drop_index("ix_secrets_holder")

    op.drop_table("secrets")
    with op.batch_alter_table("schemes", schema=None) as batch_op:
        batch_op.drop_index("ix_schemes_target")
        batch_op.drop_index("ix_schemes_owner")

    op.drop_table("schemes")
    with op.batch_alter_table("public_opinion", schema=None) as batch_op:
        batch_op.drop_index("ix_public_opinion_subject")

    op.drop_table("public_opinion")
    op.drop_table("identities")
    with op.batch_alter_table("favours", schema=None) as batch_op:
        batch_op.drop_index("ix_favours_owed_to")
        batch_op.drop_index(batch_op.f("ix_favours_owed_by_node_id"))

    op.drop_table("favours")
    op.drop_table("ciphers")
    with op.batch_alter_table("beliefs", schema=None) as batch_op:
        batch_op.drop_index("ix_beliefs_holder_subject")

    op.drop_table("beliefs")
    widen(False)
