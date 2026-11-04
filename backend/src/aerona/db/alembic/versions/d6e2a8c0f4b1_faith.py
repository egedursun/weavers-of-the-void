import sqlalchemy as sa
from alembic import op

revision = "d6e2a8c0f4b1"
down_revision = "c4d0f6a8b2e3"
branch_labels = None
depends_on = None

LAWS = ("none", "immortality", "short_life", "dead_return", "magic_price", "war_ban", "bounty", "drought", "sea_ban", "one_language", "disasters")
WIDENED = (("entities", "natural_law", LAWS, (*LAWS, "souls_reincarnate"), True),)


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
        "afterlife_strata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("realm_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "paradise", "plain", "torment", "oblivion", "warrior_hall", "ancestor_hall", name="kind", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("son_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("population >= 0", name=op.f("ck_afterlife_strata_population_min")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_afterlife_strata_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["realm_entity_id"], ["entities.id"], name=op.f("fk_afterlife_strata_realm_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_afterlife_strata_son_id_sons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_afterlife_strata")),
    )
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.create_index("ix_afterlife_strata_realm", ["realm_entity_id"], unique=False)

    op.create_table(
        "cult_doctrines",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "judgement",
            sa.Enum("deeds", "faith", "rite", "favour", "none", name="judgement", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("orthodoxy", sa.Integer(), nullable=False),
        sa.Column("tithe_rate", sa.Integer(), nullable=False),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("clergy_count", sa.Integer(), nullable=False),
        sa.Column("clergy_quality", sa.Integer(), nullable=False),
        sa.Column("liturgical_language_id", sa.Integer(), nullable=True),
        sa.Column("parent_cult_id", sa.Integer(), nullable=True),
        sa.Column("doctrinal_distance", sa.Integer(), nullable=False),
        sa.Column("zeal_parts", sa.JSON(), nullable=False),
        sa.Column(
            "fanaticism",
            sa.Enum("inquisition", "iconoclasm", "crusade", name="fanaticism", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("fanaticism_epoch", sa.Integer(), nullable=True),
        sa.Column("excommunicated", sa.JSON(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("clergy_count >= 0", name=op.f("ck_cult_doctrines_clergy_count_min")),
        sa.CheckConstraint("clergy_quality BETWEEN 0 AND 100", name=op.f("ck_cult_doctrines_clergy_quality_range")),
        sa.CheckConstraint("orthodoxy BETWEEN 0 AND 100", name=op.f("ck_cult_doctrines_orthodoxy_range")),
        sa.CheckConstraint("tithe_rate BETWEEN 0 AND 100", name=op.f("ck_cult_doctrines_tithe_rate_range")),
        sa.CheckConstraint("treasury >= 0", name=op.f("ck_cult_doctrines_treasury_min")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_cult_doctrines_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["liturgical_language_id"], ["entities.id"], name=op.f("fk_cult_doctrines_liturgical_language_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["parent_cult_id"], ["entities.id"], name=op.f("fk_cult_doctrines_parent_cult_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("cult_entity_id", name=op.f("pk_cult_doctrines")),
    )
    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_cult_doctrines_parent_cult_id"), ["parent_cult_id"], unique=False)

    op.create_table(
        "cult_holdings",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column("holding_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("temple", "land", "relic", "holy_place", "monastery", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_cult_holdings_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holding_entity_id"], ["entities.id"], name=op.f("fk_cult_holdings_holding_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cult_entity_id", "holding_entity_id", name=op.f("pk_cult_holdings")),
    )
    with op.batch_alter_table("cult_holdings", schema=None) as batch_op:
        batch_op.create_index("ix_cult_holdings_holding", ["holding_entity_id"], unique=False)

    op.create_table(
        "cult_offices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("high_priest", "priest", "monk", "inquisitor", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("holder_entity_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_cult_offices_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_cult_offices_holder_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cult_offices")),
    )
    with op.batch_alter_table("cult_offices", schema=None) as batch_op:
        batch_op.create_index("ix_cult_offices_cult", ["cult_entity_id", "kind"], unique=False)
        batch_op.create_index("ix_cult_offices_holder", ["holder_entity_id"], unique=False)

    op.create_table(
        "cult_tenets",
        sa.Column("cult_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "tenet",
            sa.Enum(
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
                "divine_kingship",
                "dietary_law",
                "sacred_species",
                "pilgrimage_duty",
                "souls_rest",
                name="tenet",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target", sa.String(length=120), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("revealed_by_son_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_cult_tenets_cult_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revealed_by_son_id"], ["sons.id"], name=op.f("fk_cult_tenets_revealed_by_son_id_sons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("cult_entity_id", "tenet", name=op.f("pk_cult_tenets")),
    )
    op.create_table(
        "heresies",
        sa.Column("heresy_entity_id", sa.Integer(), nullable=False),
        sa.Column("parent_entity_id", sa.Integer(), nullable=False),
        sa.Column("distance", sa.Integer(), nullable=False),
        sa.Column("declared_epoch", sa.Integer(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False),
        sa.Column("tolerated", sa.Boolean(), nullable=False),
        sa.CheckConstraint("distance BETWEEN 0 AND 100", name=op.f("ck_heresies_distance_range")),
        sa.ForeignKeyConstraint(["heresy_entity_id"], ["entities.id"], name=op.f("fk_heresies_heresy_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_entity_id"], ["entities.id"], name=op.f("fk_heresies_parent_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("heresy_entity_id", name=op.f("pk_heresies")),
    )
    with op.batch_alter_table("heresies", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_heresies_parent_entity_id"), ["parent_entity_id"], unique=False)

    op.create_table(
        "possessions",
        sa.Column("host_entity_id", sa.Integer(), nullable=False),
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.CheckConstraint("stress BETWEEN 0 AND 100", name=op.f("ck_possessions_stress_range")),
        sa.ForeignKeyConstraint(["host_entity_id"], ["entities.id"], name=op.f("fk_possessions_host_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_possessions_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("host_entity_id", name=op.f("pk_possessions")),
    )
    with op.batch_alter_table("possessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_possessions_spirit_entity_id"), ["spirit_entity_id"], unique=False)

    op.create_table(
        "reincarnations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("past_mortal_id", sa.Integer(), nullable=True),
        sa.Column("newborn_entity_id", sa.Integer(), nullable=True),
        sa.Column("community_entity_id", sa.Integer(), nullable=True),
        sa.Column("gate", sa.Enum("tenet", "natural_law", "rite", "god", name="gate", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("memory_pct", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_reincarnations_community_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["newborn_entity_id"], ["entities.id"], name=op.f("fk_reincarnations_newborn_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["past_mortal_id"], ["entities.id"], name=op.f("fk_reincarnations_past_mortal_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_reincarnations_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reincarnations")),
    )
    with op.batch_alter_table("reincarnations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_reincarnations_newborn_entity_id"), ["newborn_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_reincarnations_spirit_entity_id"), ["spirit_entity_id"], unique=False)

    op.create_table(
        "relics",
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column("saint_entity_id", sa.Integer(), nullable=True),
        sa.Column("cult_entity_id", sa.Integer(), nullable=True),
        sa.Column("shrine_entity_id", sa.Integer(), nullable=True),
        sa.Column("sanctity", sa.Integer(), nullable=False),
        sa.Column("pilgrims", sa.Integer(), nullable=False),
        sa.Column("canonised_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("pilgrims >= 0", name=op.f("ck_relics_pilgrims_min")),
        sa.CheckConstraint("sanctity BETWEEN 0 AND 100", name=op.f("ck_relics_sanctity_range")),
        sa.ForeignKeyConstraint(["cult_entity_id"], ["entities.id"], name=op.f("fk_relics_cult_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_relics_item_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saint_entity_id"], ["entities.id"], name=op.f("fk_relics_saint_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shrine_entity_id"], ["entities.id"], name=op.f("fk_relics_shrine_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("item_entity_id", name=op.f("pk_relics")),
    )
    with op.batch_alter_table("relics", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_relics_cult_entity_id"), ["cult_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_relics_saint_entity_id"), ["saint_entity_id"], unique=False)

    op.create_table(
        "soul_judgements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=True),
        sa.Column(
            "doctrine",
            sa.Enum("deeds", "faith", "rite", "favour", "none", name="doctrine", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stratum_id", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rite", sa.Enum("burial", "burning", "exposure", "none", name="rite", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("reason", sa.String(length=480), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_soul_judgements_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_soul_judgements_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stratum_id"], ["afterlife_strata.id"], name=op.f("fk_soul_judgements_stratum_id_afterlife_strata"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_soul_judgements")),
    )
    with op.batch_alter_table("soul_judgements", schema=None) as batch_op:
        batch_op.create_index("ix_soul_judgements_spirit", ["spirit_entity_id"], unique=False)

    op.create_table(
        "spirit_profiles",
        sa.Column("spirit_entity_id", sa.Integer(), nullable=False),
        sa.Column("origin_mortal_id", sa.Integer(), nullable=True),
        sa.Column("imprint", sa.JSON(), nullable=False),
        sa.Column("traits", sa.JSON(), nullable=False),
        sa.Column("deeds", sa.JSON(), nullable=False),
        sa.Column(
            "binding",
            sa.Enum("none", "place", "item", "structure", "beast", "person", name="binding", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("bound_entity_id", sa.Integer(), nullable=True),
        sa.Column("memory_strength", sa.Integer(), nullable=False),
        sa.Column("veneration", sa.Integer(), nullable=False),
        sa.Column(
            "alignment", sa.Enum("guardian", "neutral", "vengeful", name="alignment", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "state",
            sa.Enum("wandering", "judged", "in_realm", "reborn", "consumed", "released", name="state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stratum_id", sa.Integer(), nullable=True),
        sa.Column("rite", sa.Enum("burial", "burning", "exposure", "none", name="rite", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("patron_son_id", sa.Integer(), nullable=True),
        sa.Column("sealed", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("memory_strength BETWEEN 0 AND 100", name=op.f("ck_spirit_profiles_memory_strength_range")),
        sa.CheckConstraint("veneration BETWEEN 0 AND 100", name=op.f("ck_spirit_profiles_veneration_range")),
        sa.ForeignKeyConstraint(["bound_entity_id"], ["entities.id"], name=op.f("fk_spirit_profiles_bound_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_mortal_id"], ["entities.id"], name=op.f("fk_spirit_profiles_origin_mortal_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patron_son_id"], ["sons.id"], name=op.f("fk_spirit_profiles_patron_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spirit_entity_id"], ["entities.id"], name=op.f("fk_spirit_profiles_spirit_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stratum_id"], ["afterlife_strata.id"], name=op.f("fk_spirit_profiles_stratum_id_afterlife_strata"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("spirit_entity_id", name=op.f("pk_spirit_profiles")),
    )
    with op.batch_alter_table("spirit_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_spirit_profiles_origin_mortal_id"), ["origin_mortal_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_spirit_profiles_stratum_id"), ["stratum_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("spirit_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_spirit_profiles_stratum_id"))
        batch_op.drop_index(batch_op.f("ix_spirit_profiles_origin_mortal_id"))

    op.drop_table("spirit_profiles")
    with op.batch_alter_table("soul_judgements", schema=None) as batch_op:
        batch_op.drop_index("ix_soul_judgements_spirit")

    op.drop_table("soul_judgements")
    with op.batch_alter_table("relics", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_relics_saint_entity_id"))
        batch_op.drop_index(batch_op.f("ix_relics_cult_entity_id"))

    op.drop_table("relics")
    with op.batch_alter_table("reincarnations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reincarnations_spirit_entity_id"))
        batch_op.drop_index(batch_op.f("ix_reincarnations_newborn_entity_id"))

    op.drop_table("reincarnations")
    with op.batch_alter_table("possessions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_possessions_spirit_entity_id"))

    op.drop_table("possessions")
    with op.batch_alter_table("heresies", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_heresies_parent_entity_id"))

    op.drop_table("heresies")
    op.drop_table("cult_tenets")
    with op.batch_alter_table("cult_offices", schema=None) as batch_op:
        batch_op.drop_index("ix_cult_offices_holder")
        batch_op.drop_index("ix_cult_offices_cult")

    op.drop_table("cult_offices")
    with op.batch_alter_table("cult_holdings", schema=None) as batch_op:
        batch_op.drop_index("ix_cult_holdings_holding")

    op.drop_table("cult_holdings")
    with op.batch_alter_table("cult_doctrines", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_cult_doctrines_parent_cult_id"))

    op.drop_table("cult_doctrines")
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.drop_index("ix_afterlife_strata_realm")

    op.drop_table("afterlife_strata")
    widen(False)
