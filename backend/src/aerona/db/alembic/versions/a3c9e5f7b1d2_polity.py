import sqlalchemy as sa
from alembic import op

revision = "a3c9e5f7b1d2"
down_revision = "f2b8d4c6a1e9"
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
)
NEW_ENTITY_TYPES = (*OLD_ENTITY_TYPES, "polity", "house", "treaty")
WIDENED = (
    ("entities", "entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, False),
    ("son_powers", "param_entity_type", OLD_ENTITY_TYPES, NEW_ENTITY_TYPES, True),
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
        "claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claimant_entity_id", sa.Integer(), nullable=False),
        sa.Column("house_entity_id", sa.Integer(), nullable=True),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "office",
            sa.Enum(
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
                name="office",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column(
            "basis",
            sa.Enum("inheritance", "marriage", "conquest", "divine", "fabricated", name="basis", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("pressed", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_claims_strength_range")),
        sa.ForeignKeyConstraint(["claimant_entity_id"], ["entities.id"], name=op.f("fk_claims_claimant_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_claims_house_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_claims_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claims")),
    )
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.create_index("ix_claims_claimant", ["claimant_entity_id"], unique=False)
        batch_op.create_index("ix_claims_polity", ["polity_entity_id"], unique=False)

    op.create_table(
        "heirlooms",
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column("house_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_heirlooms_house_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_heirlooms_item_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_entity_id", name=op.f("pk_heirlooms")),
    )
    with op.batch_alter_table("heirlooms", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_heirlooms_house_entity_id"), ["house_entity_id"], unique=False)

    op.create_table(
        "house_members",
        sa.Column("house_entity_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("by_marriage", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_house_members_house_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_house_members_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("house_entity_id", "mortal_entity_id", name=op.f("pk_house_members")),
    )
    with op.batch_alter_table("house_members", schema=None) as batch_op:
        batch_op.create_index("ix_house_members_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "house_profiles",
        sa.Column("house_entity_id", sa.Integer(), nullable=False),
        sa.Column("founder_entity_id", sa.Integer(), nullable=True),
        sa.Column("head_entity_id", sa.Integer(), nullable=True),
        sa.Column("parent_house_id", sa.Integer(), nullable=True),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("divine_son_id", sa.Integer(), nullable=True),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("wealth", sa.Integer(), nullable=False),
        sa.Column("motto", sa.String(length=120), nullable=True),
        sa.Column("emblem", sa.JSON(), nullable=False),
        sa.Column("traits", sa.JSON(), nullable=False),
        sa.Column("seats", sa.JSON(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("extinct_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_house_profiles_prestige_range")),
        sa.CheckConstraint("wealth >= 0", name=op.f("ck_house_profiles_wealth_min")),
        sa.ForeignKeyConstraint(["divine_son_id"], ["sons.id"], name=op.f("fk_house_profiles_divine_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["founder_entity_id"], ["entities.id"], name=op.f("fk_house_profiles_founder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["head_entity_id"], ["entities.id"], name=op.f("fk_house_profiles_head_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["house_entity_id"], ["entities.id"], name=op.f("fk_house_profiles_house_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_house_id"], ["entities.id"], name=op.f("fk_house_profiles_parent_house_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_house_profiles_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("house_entity_id", name=op.f("pk_house_profiles")),
    )
    op.create_table(
        "law_jurisdictions",
        sa.Column("law_entity_id", sa.Integer(), nullable=False),
        sa.Column("node_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "jurisdiction", sa.Enum("polity", "settlement", "cult", name="jurisdiction", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_law_jurisdictions_law_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_entity_id"], ["entities.id"], name=op.f("fk_law_jurisdictions_node_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("law_entity_id", "node_entity_id", name=op.f("pk_law_jurisdictions")),
    )
    with op.batch_alter_table("law_jurisdictions", schema=None) as batch_op:
        batch_op.create_index("ix_law_jurisdictions_node", ["node_entity_id"], unique=False)

    op.create_table(
        "law_profiles",
        sa.Column("law_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "area",
            sa.Enum(
                "succession",
                "property",
                "fiscal",
                "penal",
                "military",
                "social",
                "public_health",
                "magic",
                name="area",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("enforcement", sa.Integer(), nullable=False),
        sa.Column(
            "legitimacy_basis",
            sa.Enum("custom", "decree", "divine", "council", name="legitimacy_basis", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("conflict", sa.Integer(), nullable=False),
        sa.Column("enacted_epoch", sa.Integer(), nullable=False),
        sa.Column("enacted_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("conflict BETWEEN 0 AND 100", name=op.f("ck_law_profiles_conflict_range")),
        sa.CheckConstraint("enforcement BETWEEN 0 AND 100", name=op.f("ck_law_profiles_enforcement_range")),
        sa.ForeignKeyConstraint(["enacted_by_entity_id"], ["entities.id"], name=op.f("fk_law_profiles_enacted_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_law_profiles_law_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("law_entity_id", name=op.f("pk_law_profiles")),
    )
    with op.batch_alter_table("law_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_law_profiles_kind", ["kind"], unique=False)

    op.create_table(
        "oaths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("swearer_entity_id", sa.Integer(), nullable=False),
        sa.Column("recipient_node_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "fealty",
                "vengeance",
                "celibacy",
                "pilgrimage",
                "protection",
                "silence",
                "blood_brotherhood",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("witness_son_id", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.Enum("sworn", "kept", "broken", "fulfilled", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("sworn_epoch", sa.Integer(), nullable=False),
        sa.Column("deadline_epoch", sa.Integer(), nullable=True),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["recipient_node_id"], ["nodes.id"], name=op.f("fk_oaths_recipient_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["swearer_entity_id"], ["entities.id"], name=op.f("fk_oaths_swearer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["witness_son_id"], ["sons.id"], name=op.f("fk_oaths_witness_son_id_sons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oaths")),
    )
    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.create_index("ix_oaths_recipient", ["recipient_node_id"], unique=False)
        batch_op.create_index("ix_oaths_swearer", ["swearer_entity_id", "status"], unique=False)

    op.create_table(
        "offices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("holder_entity_id", sa.Integer(), nullable=True),
        sa.Column("appointed_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("powers", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["appointed_by_entity_id"], ["entities.id"], name=op.f("fk_offices_appointed_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_offices_holder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_offices_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_offices_region_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_offices")),
    )
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.create_index("ix_offices_holder", ["holder_entity_id"], unique=False)
        batch_op.create_index("ix_offices_polity", ["polity_entity_id", "kind"], unique=False)

    op.create_table(
        "polity_members",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("member_entity_id", sa.Integer(), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("autonomy", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["member_entity_id"], ["entities.id"], name=op.f("fk_polity_members_member_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_members_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "member_entity_id", name=op.f("pk_polity_members")),
    )
    with op.batch_alter_table("polity_members", schema=None) as batch_op:
        batch_op.create_index("ix_polity_members_member", ["member_entity_id"], unique=False)

    op.create_table(
        "polity_profiles",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "government",
            sa.Enum(
                "chiefdom",
                "monarchy",
                "theocracy",
                "oligarchy",
                "republic",
                "tribal_confederation",
                "empire",
                "hive_council",
                "god_kingdom",
                "occupation",
                name="government",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "decision_rule",
            sa.Enum("autocratic", "council", "assembly", "divine", name="decision_rule", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("legitimacy", sa.Integer(), nullable=False),
        sa.Column("stability", sa.Integer(), nullable=False),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("debt", sa.Integer(), nullable=False),
        sa.Column("war_chest", sa.Integer(), nullable=False),
        sa.Column("administration", sa.Integer(), nullable=False),
        sa.Column("overextension", sa.Integer(), nullable=False),
        sa.Column("war_weariness", sa.Integer(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column(
            "standing",
            sa.Enum("hegemon", "great_power", "minor_power", "client", name="standing", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("core_entity_id", sa.Integer(), nullable=True),
        sa.Column("capital_entity_id", sa.Integer(), nullable=True),
        sa.Column("state_religion_id", sa.Integer(), nullable=True),
        sa.Column("ideology_entity_id", sa.Integer(), nullable=True),
        sa.Column("patron_son_id", sa.Integer(), nullable=True),
        sa.Column("emblem", sa.JSON(), nullable=False),
        sa.Column("legitimacy_parts", sa.JSON(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("administration >= 0", name=op.f("ck_polity_profiles_administration_min")),
        sa.CheckConstraint("debt >= 0", name=op.f("ck_polity_profiles_debt_min")),
        sa.CheckConstraint("legitimacy BETWEEN 0 AND 100", name=op.f("ck_polity_profiles_legitimacy_range")),
        sa.CheckConstraint("overextension BETWEEN 0 AND 1000", name=op.f("ck_polity_profiles_overextension_range")),
        sa.CheckConstraint("stability BETWEEN 0 AND 100", name=op.f("ck_polity_profiles_stability_range")),
        sa.CheckConstraint("tier >= 0", name=op.f("ck_polity_profiles_tier_min")),
        sa.CheckConstraint("war_chest >= 0", name=op.f("ck_polity_profiles_war_chest_min")),
        sa.CheckConstraint("war_weariness BETWEEN 0 AND 100", name=op.f("ck_polity_profiles_war_weariness_range")),
        sa.ForeignKeyConstraint(["capital_entity_id"], ["entities.id"], name=op.f("fk_polity_profiles_capital_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["core_entity_id"], ["entities.id"], name=op.f("fk_polity_profiles_core_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ideology_entity_id"], ["entities.id"], name=op.f("fk_polity_profiles_ideology_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patron_son_id"], ["sons.id"], name=op.f("fk_polity_profiles_patron_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_profiles_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["state_religion_id"], ["entities.id"], name=op.f("fk_polity_profiles_state_religion_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_polity_profiles")),
    )
    with op.batch_alter_table("polity_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_polity_profiles_core_entity_id"), ["core_entity_id"], unique=False)

    op.create_table(
        "polity_territories",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("control", sa.Integer(), nullable=False),
        sa.Column("province", sa.String(length=120), nullable=True),
        sa.CheckConstraint("control BETWEEN 0 AND 100", name=op.f("ck_polity_territories_control_range")),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_territories_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_polity_territories_region_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", "region_entity_id", name=op.f("pk_polity_territories")),
    )
    with op.batch_alter_table("polity_territories", schema=None) as batch_op:
        batch_op.create_index("ix_polity_territories_region", ["region_entity_id"], unique=False)

    op.create_table(
        "polity_treasury",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_polity_treasury_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_polity_treasury")),
    )
    with op.batch_alter_table("polity_treasury", schema=None) as batch_op:
        batch_op.create_index("ix_polity_treasury_polity", ["polity_entity_id", "epoch"], unique=False)

    op.create_table(
        "treaty_clauses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("treaty_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("obligor_node_id", sa.Integer(), nullable=True),
        sa.Column("beneficiary_node_id", sa.Integer(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("last_kept_epoch", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["beneficiary_node_id"], ["nodes.id"], name=op.f("fk_treaty_clauses_beneficiary_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["obligor_node_id"], ["nodes.id"], name=op.f("fk_treaty_clauses_obligor_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["treaty_entity_id"], ["entities.id"], name=op.f("fk_treaty_clauses_treaty_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_treaty_clauses")),
    )
    with op.batch_alter_table("treaty_clauses", schema=None) as batch_op:
        batch_op.create_index("ix_treaty_clauses_treaty", ["treaty_entity_id"], unique=False)

    op.create_table(
        "treaty_parties",
        sa.Column("treaty_entity_id", sa.Integer(), nullable=False),
        sa.Column("party_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("signatory", "overlord", "vassal", "guarantor", name="role", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.ForeignKeyConstraint(["party_node_id"], ["nodes.id"], name=op.f("fk_treaty_parties_party_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["treaty_entity_id"], ["entities.id"], name=op.f("fk_treaty_parties_treaty_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("treaty_entity_id", "party_node_id", name=op.f("pk_treaty_parties")),
    )
    with op.batch_alter_table("treaty_parties", schema=None) as batch_op:
        batch_op.create_index("ix_treaty_parties_party", ["party_node_id"], unique=False)

    op.create_table(
        "vassalages",
        sa.Column("vassal_entity_id", sa.Integer(), nullable=False),
        sa.Column("overlord_entity_id", sa.Integer(), nullable=False),
        sa.Column("treaty_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("tribute_pct", sa.Integer(), nullable=False),
        sa.Column("levy_pct", sa.Integer(), nullable=False),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.CheckConstraint("levy_pct BETWEEN 0 AND 100", name=op.f("ck_vassalages_levy_pct_range")),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_vassalages_loyalty_range")),
        sa.CheckConstraint("tribute_pct BETWEEN 0 AND 100", name=op.f("ck_vassalages_tribute_pct_range")),
        sa.ForeignKeyConstraint(["overlord_entity_id"], ["entities.id"], name=op.f("fk_vassalages_overlord_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["treaty_entity_id"], ["entities.id"], name=op.f("fk_vassalages_treaty_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vassal_entity_id"], ["entities.id"], name=op.f("fk_vassalages_vassal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vassal_entity_id", name=op.f("pk_vassalages")),
    )
    with op.batch_alter_table("vassalages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_vassalages_overlord_entity_id"), ["overlord_entity_id"], unique=False)

    op.create_table(
        "office_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("office_id", sa.Integer(), nullable=False),
        sa.Column("holder_entity_id", sa.Integer(), nullable=True),
        sa.Column("from_epoch", sa.Integer(), nullable=False),
        sa.Column("to_epoch", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_office_history_holder_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["office_id"], ["offices.id"], name=op.f("fk_office_history_office_id_offices"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_office_history")),
    )
    with op.batch_alter_table("office_history", schema=None) as batch_op:
        batch_op.create_index("ix_office_history_office", ["office_id"], unique=False)

    op.create_table(
        "treaty_breaches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("treaty_entity_id", sa.Integer(), nullable=False),
        sa.Column("clause_id", sa.Integer(), nullable=True),
        sa.Column("breaker_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["breaker_node_id"], ["nodes.id"], name=op.f("fk_treaty_breaches_breaker_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clause_id"], ["treaty_clauses.id"], name=op.f("fk_treaty_breaches_clause_id_treaty_clauses"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_treaty_breaches_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["treaty_entity_id"], ["entities.id"], name=op.f("fk_treaty_breaches_treaty_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_treaty_breaches")),
    )
    with op.batch_alter_table("treaty_breaches", schema=None) as batch_op:
        batch_op.create_index("ix_treaty_breaches_treaty", ["treaty_entity_id"], unique=False)

    op.create_table(
        "treaty_profiles",
        sa.Column("treaty_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "peace",
                "truce",
                "alliance_defensive",
                "alliance_offensive",
                "non_aggression",
                "vassalage",
                "tribute",
                "marriage_pact",
                "trade_pact",
                "condotta",
                "guarantee",
                "interworld",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "status", sa.Enum("in_force", "fulfilled", "broken", "expired", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("signed_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("witness_son_id", sa.Integer(), nullable=True),
        sa.Column("oath_id", sa.Integer(), nullable=True),
        sa.Column("source_bond_id", sa.Integer(), nullable=True),
        sa.Column("renewals", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["oath_id"], ["oaths.id"], name=op.f("fk_treaty_profiles_oath_id_oaths"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_bond_id"], ["bonds.id"], name=op.f("fk_treaty_profiles_source_bond_id_bonds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["treaty_entity_id"], ["entities.id"], name=op.f("fk_treaty_profiles_treaty_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["witness_son_id"], ["sons.id"], name=op.f("fk_treaty_profiles_witness_son_id_sons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("treaty_entity_id", name=op.f("pk_treaty_profiles")),
    )
    with op.batch_alter_table("treaty_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_treaty_profiles_source_bond_id"), ["source_bond_id"], unique=False)
        batch_op.create_index("ix_treaty_profiles_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("treaty_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_treaty_profiles_status")
        batch_op.drop_index(batch_op.f("ix_treaty_profiles_source_bond_id"))

    op.drop_table("treaty_profiles")
    with op.batch_alter_table("treaty_breaches", schema=None) as batch_op:
        batch_op.drop_index("ix_treaty_breaches_treaty")

    op.drop_table("treaty_breaches")
    with op.batch_alter_table("office_history", schema=None) as batch_op:
        batch_op.drop_index("ix_office_history_office")

    op.drop_table("office_history")
    with op.batch_alter_table("vassalages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_vassalages_overlord_entity_id"))

    op.drop_table("vassalages")
    with op.batch_alter_table("treaty_parties", schema=None) as batch_op:
        batch_op.drop_index("ix_treaty_parties_party")

    op.drop_table("treaty_parties")
    with op.batch_alter_table("treaty_clauses", schema=None) as batch_op:
        batch_op.drop_index("ix_treaty_clauses_treaty")

    op.drop_table("treaty_clauses")
    with op.batch_alter_table("polity_treasury", schema=None) as batch_op:
        batch_op.drop_index("ix_polity_treasury_polity")

    op.drop_table("polity_treasury")
    with op.batch_alter_table("polity_territories", schema=None) as batch_op:
        batch_op.drop_index("ix_polity_territories_region")

    op.drop_table("polity_territories")
    with op.batch_alter_table("polity_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_polity_profiles_core_entity_id"))

    op.drop_table("polity_profiles")
    with op.batch_alter_table("polity_members", schema=None) as batch_op:
        batch_op.drop_index("ix_polity_members_member")

    op.drop_table("polity_members")
    with op.batch_alter_table("offices", schema=None) as batch_op:
        batch_op.drop_index("ix_offices_polity")
        batch_op.drop_index("ix_offices_holder")

    op.drop_table("offices")
    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.drop_index("ix_oaths_swearer")
        batch_op.drop_index("ix_oaths_recipient")

    op.drop_table("oaths")
    with op.batch_alter_table("law_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_law_profiles_kind")

    op.drop_table("law_profiles")
    with op.batch_alter_table("law_jurisdictions", schema=None) as batch_op:
        batch_op.drop_index("ix_law_jurisdictions_node")

    op.drop_table("law_jurisdictions")
    op.drop_table("house_profiles")
    with op.batch_alter_table("house_members", schema=None) as batch_op:
        batch_op.drop_index("ix_house_members_mortal")

    op.drop_table("house_members")
    with op.batch_alter_table("heirlooms", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_heirlooms_house_entity_id"))

    op.drop_table("heirlooms")
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.drop_index("ix_claims_polity")
        batch_op.drop_index("ix_claims_claimant")

    op.drop_table("claims")
    op.execute("DELETE FROM entities WHERE entity_type IN ('polity', 'house', 'treaty')")
    widen(False)
