import sqlalchemy as sa
from alembic import op

revision = "b9d4f2a6c8e1"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None


OLD_BONDS = (
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
)
OLD_TRAITS = (
    "flying",
    "venomous",
    "soul_eater",
    "radiant",
    "fissiparous",
    "hive_mind",
    "stoneskin",
    "time_rewinder",
    "shapeshifter",
    "mind_reader",
    "armoured",
    "burrowing",
    "aquatic",
    "amphibious",
    "pack_hunter",
    "ambush_predator",
    "regenerating",
    "poisonous_flesh",
    "fire_breathing",
    "cold_breathing",
    "echolocation",
    "camouflage",
    "swarm_breeder",
    "long_lived",
    "mimic",
    "spirit_sight",
    "iron_eating",
    "crop_pest",
    "plague_bearer",
    "sacred_animal",
)
NEW_TRAITS = (*OLD_TRAITS, "horned", "tailed")
OLD_CAUSES = (
    "battle",
    "duel",
    "punishment",
    "torture",
    "accident",
    "monster",
    "disaster",
    "curse",
    "magic_backlash",
    "god",
    "poison",
    "quest",
    "escape",
    "sacrifice",
    "age",
    "player",
)
NEW_CAUSES = (*OLD_CAUSES, "exposure")
BODY_PARTS = (
    "aura",
    "core",
    "eye",
    "face",
    "fingers",
    "gills",
    "groin",
    "gut",
    "head",
    "heart",
    "horn",
    "jaw",
    "left_antenna",
    "left_arm",
    "left_branch",
    "left_ear",
    "left_eye",
    "left_fin",
    "left_foot",
    "left_foreleg",
    "left_hand",
    "left_hindleg",
    "left_leg",
    "left_midleg",
    "left_wing",
    "lungs",
    "neck",
    "nose",
    "pseudopods",
    "right_antenna",
    "right_arm",
    "right_branch",
    "right_ear",
    "right_eye",
    "right_fin",
    "right_foot",
    "right_foreleg",
    "right_hand",
    "right_hindleg",
    "right_leg",
    "right_midleg",
    "right_wing",
    "roots",
    "tail",
    "tongue",
    "torso",
    "venom_gland",
    "wings",
)
FULL_FUNCTIONS = ("vital", "cognition", "hearing", "sight")
EMPTY_FUNCTIONS = ("venom", "horn", "tail")
PART_TABLES = (("injuries", False), ("conditions", True), ("prostheses", False))
NEW_BONDS = (*OLD_BONDS, "parent_of", "spouse_of", "betrothed_to", "concubine_of", "fostered_by", "sworn_kin")


def enum_of(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="kind", native_enum=False, create_constraint=True, length=40)


def bond_indexes() -> list[tuple[str, str]]:
    rows = op.get_bind().execute(sa.text("SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'bonds' AND sql IS NOT NULL"))
    return [(row[0], row[1]) for row in rows]


def change_bond_kinds(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    indexes = bond_indexes()
    with op.batch_alter_table("bonds", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum_of(old), type_=enum_of(new), existing_nullable=False)
    for name, sql in indexes:
        op.execute(sa.text(f'DROP INDEX IF EXISTS "{name}"'))
        op.execute(sa.text(sql))


def named_enum(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def body_upgrade() -> None:
    with op.batch_alter_table("entity_traits", schema=None) as batch_op:
        batch_op.alter_column("trait", existing_type=named_enum("trait", OLD_TRAITS), type_=named_enum("trait", NEW_TRAITS), existing_nullable=False)
    for table, column in (("injuries", "cause_kind"), ("conditions", "source")):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=named_enum(column, OLD_CAUSES), type_=named_enum(column, NEW_CAUSES), existing_nullable=False)
    for table, nullable in PART_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column("part", existing_type=sa.String(length=120), type_=named_enum("part", BODY_PARTS), existing_nullable=nullable)
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        for column in FULL_FUNCTIONS:
            batch_op.add_column(sa.Column(column, sa.Integer(), nullable=False, server_default="100"))
        for column in EMPTY_FUNCTIONS:
            batch_op.add_column(sa.Column(column, sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        for column in (*FULL_FUNCTIONS, *EMPTY_FUNCTIONS):
            batch_op.alter_column(column, server_default=None)
            batch_op.create_check_constraint(op.f(f"ck_bodies_{column}_range"), f"{column} BETWEEN 0 AND 100")


def body_downgrade() -> None:
    with op.batch_alter_table("bodies", schema=None) as batch_op:
        for column in (*FULL_FUNCTIONS, *EMPTY_FUNCTIONS):
            batch_op.drop_constraint(op.f(f"ck_bodies_{column}_range"), type_="check")
            batch_op.drop_column(column)
    for table, nullable in PART_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column("part", existing_type=named_enum("part", BODY_PARTS), type_=sa.String(length=120), existing_nullable=nullable)
    op.execute(sa.text("DELETE FROM injuries WHERE cause_kind = 'exposure'"))
    op.execute(sa.text("DELETE FROM conditions WHERE source = 'exposure'"))
    for table, column in (("injuries", "cause_kind"), ("conditions", "source")):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=named_enum(column, NEW_CAUSES), type_=named_enum(column, OLD_CAUSES), existing_nullable=False)
    op.execute(sa.text("DELETE FROM entity_traits WHERE trait IN ('horned', 'tailed')"))
    with op.batch_alter_table("entity_traits", schema=None) as batch_op:
        batch_op.alter_column("trait", existing_type=named_enum("trait", NEW_TRAITS), type_=named_enum("trait", OLD_TRAITS), existing_nullable=False)


def upgrade() -> None:
    change_bond_kinds(OLD_BONDS, NEW_BONDS)
    body_upgrade()
    op.create_table(
        "marriages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_id", sa.Integer(), nullable=False),
        sa.Column("second_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("monogamous", "plural", "political", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("treaty_id", sa.Integer(), nullable=True),
        sa.Column("start_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "cause_end", sa.Enum("death", "divorce", "annulment", "war", name="cause_end", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("forced", sa.Boolean(), nullable=False),
        sa.CheckConstraint("start_epoch >= 0", name=op.f("ck_marriages_start_epoch_min")),
        sa.ForeignKeyConstraint(["first_id"], ["entities.id"], name=op.f("fk_marriages_first_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_id"], ["entities.id"], name=op.f("fk_marriages_second_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["treaty_id"], ["entities.id"], name=op.f("fk_marriages_treaty_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_marriages")),
    )
    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.create_index("ix_marriages_first", ["first_id"], unique=False)
        batch_op.create_index("ix_marriages_second", ["second_id"], unique=False)

    op.create_table(
        "mortal_equipment",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("wielded_main_id", sa.Integer(), nullable=True),
        sa.Column("wielded_off_id", sa.Integer(), nullable=True),
        sa.Column("armour_body_id", sa.Integer(), nullable=True),
        sa.Column("armour_head_id", sa.Integer(), nullable=True),
        sa.Column("mount_id", sa.Integer(), nullable=True),
        sa.Column("focus_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["armour_body_id"], ["entities.id"], name=op.f("fk_mortal_equipment_armour_body_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["armour_head_id"], ["entities.id"], name=op.f("fk_mortal_equipment_armour_head_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_mortal_equipment_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["focus_id"], ["entities.id"], name=op.f("fk_mortal_equipment_focus_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mount_id"], ["entities.id"], name=op.f("fk_mortal_equipment_mount_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wielded_main_id"], ["entities.id"], name=op.f("fk_mortal_equipment_wielded_main_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wielded_off_id"], ["entities.id"], name=op.f("fk_mortal_equipment_wielded_off_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_mortal_equipment")),
    )
    op.create_table(
        "mortal_profiles",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "life_stage",
            sa.Enum("infant", "child", "youth", "adult", "elder", "ancient", name="life_stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("fertility", sa.Integer(), nullable=False),
        sa.Column("health", sa.Integer(), nullable=False),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.Column("wealth", sa.Integer(), nullable=False),
        sa.Column("renown", sa.Integer(), nullable=False),
        sa.Column("honour", sa.Integer(), nullable=False),
        sa.Column("infamy", sa.Integer(), nullable=False),
        sa.Column("legitimacy", sa.Integer(), nullable=True),
        sa.Column("education", sa.Integer(), nullable=False),
        sa.Column("polity_id", sa.Integer(), nullable=True),
        sa.Column("loyalty_liege", sa.Integer(), nullable=False),
        sa.Column("loyalty_community", sa.Integer(), nullable=False),
        sa.Column("loyalty_god", sa.Integer(), nullable=False),
        sa.Column(
            "career",
            sa.Enum(
                "stay", "army", "office", "apprentice", "vows", "trade", "wander", "bandit", name="career", native_enum=False, create_constraint=True, length=40
            ),
            nullable=True,
        ),
        sa.Column(
            "last_break",
            sa.Enum("rage", "flight", "despair", "zeal", "vice", "revelation", name="last_break", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("last_break_epoch", sa.Integer(), nullable=True),
        sa.Column(
            "cause_of_death",
            sa.Enum(
                "old_age",
                "wounds",
                "battle",
                "duel",
                "execution",
                "murder",
                "monster",
                "disease",
                "childbirth",
                "famine",
                "accident",
                "disaster",
                "exposure",
                "curse",
                "magic",
                "divine",
                "poison",
                "sacrifice",
                "hardship",
                "despair",
                "unknown",
                name="cause_of_death",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("death_place_id", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("education BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_education_range")),
        sa.CheckConstraint("fertility BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_fertility_range")),
        sa.CheckConstraint("health BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_health_range")),
        sa.CheckConstraint("honour BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_honour_range")),
        sa.CheckConstraint("infamy BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_infamy_range")),
        sa.CheckConstraint("legitimacy IS NULL OR legitimacy BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_legitimacy_range")),
        sa.CheckConstraint("loyalty_community BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_loyalty_community_range")),
        sa.CheckConstraint("loyalty_god BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_loyalty_god_range")),
        sa.CheckConstraint("loyalty_liege BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_loyalty_liege_range")),
        sa.CheckConstraint("renown BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_renown_range")),
        sa.CheckConstraint("stress BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_stress_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_mortal_profiles_updated_epoch_min")),
        sa.CheckConstraint("wealth BETWEEN 0 AND 100", name=op.f("ck_mortal_profiles_wealth_range")),
        sa.ForeignKeyConstraint(["death_place_id"], ["entities.id"], name=op.f("fk_mortal_profiles_death_place_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_mortal_profiles_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_id"], ["entities.id"], name=op.f("fk_mortal_profiles_polity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_mortal_profiles")),
    )
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_mortal_profiles_polity", ["polity_id"], unique=False)


def downgrade() -> None:
    body_downgrade()
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_mortal_profiles_polity")

    op.drop_table("mortal_profiles")
    op.drop_table("mortal_equipment")
    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.drop_index("ix_marriages_second")
        batch_op.drop_index("ix_marriages_first")

    op.drop_table("marriages")
    op.execute(sa.text("DELETE FROM bonds WHERE kind IN ('parent_of', 'spouse_of', 'betrothed_to', 'concubine_of', 'fostered_by', 'sworn_kin')"))
    change_bond_kinds(NEW_BONDS, OLD_BONDS)
