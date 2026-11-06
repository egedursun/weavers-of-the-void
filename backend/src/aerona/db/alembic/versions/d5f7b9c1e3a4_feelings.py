import sqlalchemy as sa
from alembic import op

revision = "d5f7b9c1e3a4"
down_revision = "c4e6a8b0d2f3"
branch_labels = None
depends_on = None

OLD_MEMORIES = (
    "harmed_me",
    "killed_kin",
    "saved_me",
    "betrayed_me",
    "kept_oath",
    "broke_oath",
    "maimed_me",
    "humiliated_me",
    "gifted_me",
    "converted_me",
    "conquered_us",
    "freed_us",
    "famine_aid",
    "desecrated_holy",
    "married_into",
    "fought_us",
    "traded_with",
    "allied_with",
    "made_peace",
    "demanded_tribute",
    "cheated_us",
    "spied_on_us",
    "envied",
    "failed_to_heal",
    "taught_me",
    "held_captive",
    "lamented",
    "divine_will",
    "goodwill",
    "ill_will",
    "long_history",
    "dreads",
)
NEW_MEMORIES = (*OLD_MEMORIES, "formative")
OLD_NEEDS = (
    "sustenance",
    "safety",
    "belonging",
    "status",
    "purpose",
    "faith",
    "pleasure",
)
NEW_NEEDS = (
    *OLD_NEEDS,
    "drink",
    "rest",
    "comfort",
    "health",
    "family",
    "friends",
    "romance",
    "solitude",
    "learning",
    "creating",
    "beauty",
    "nature",
    "adventure",
    "fighting",
    "wealth",
    "order",
)
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
)
NEW_CONDITIONS = (*OLD_CONDITIONS, "nightmares")
THOUGHTS = (
    "married",
    "child_born",
    "saw_kin_die",
    "lost_spouse",
    "lost_child",
    "betrayed",
    "was_insulted",
    "was_gifted",
    "was_saved",
    "was_cheated",
    "won_battle",
    "defeated",
    "won_duel",
    "lost_duel",
    "was_wounded",
    "was_maimed",
    "lost_limb_but_lived",
    "was_healed",
    "fell_ill",
    "witnessed_atrocity",
    "was_captured",
    "was_freed",
    "killed_foe",
    "rose_in_rank",
    "fell_in_rank",
    "gained_renown",
    "was_shamed",
    "was_punished",
    "was_conquered",
    "prayed_answered",
    "prayer_ignored",
    "saw_miracle",
    "lost_faith",
    "found_faith",
    "saw_desecration",
    "touched_by_a_god",
    "admired_great_work",
    "heard_great_music",
    "attended_feast",
    "made_masterwork",
    "learned_something",
    "taught_apprentice",
    "took_idea_to_heart",
    "ate_fine_food",
    "went_hungry",
    "went_thirsty",
    "drank_well",
    "slept_well",
    "exhausted",
    "lived_in_comfort",
    "lived_in_squalor",
    "felt_hale",
    "felt_unwell",
    "felt_safe",
    "felt_unsafe",
    "among_kin",
    "missed_kin",
    "among_friends",
    "felt_lonely",
    "loved",
    "longed_for_love",
    "had_peace_and_quiet",
    "crowded",
    "respected",
    "overlooked",
    "belonged",
    "adrift",
    "felt_purpose",
    "lacked_purpose",
    "prayed_in_peace",
    "faith_unmet",
    "learned_nothing",
    "made_something",
    "nothing_made",
    "saw_beauty",
    "surrounded_by_ugliness",
    "walked_in_nature",
    "cut_off_from_nature",
    "had_adventure",
    "restless",
    "tested_in_combat",
    "blade_rusting",
    "prospered",
    "wanted_for_money",
    "enjoyed_leisure",
    "bored",
    "lived_in_order",
    "lived_in_disorder",
    "relived_memory",
    "mourned",
    "made_peace_with_loss",
    "had_nightmare",
    "had_good_dream",
    "dreamed_of_longing",
    "received_visitation",
    "sent_by_the_creator",
)
EMOTIONS = (
    "joy",
    "contentment",
    "pride",
    "love",
    "gratitude",
    "relief",
    "hope",
    "awe",
    "amusement",
    "fear",
    "anxiety",
    "anger",
    "rage",
    "grief",
    "sadness",
    "shame",
    "guilt",
    "envy",
    "jealousy",
    "disgust",
    "loneliness",
    "boredom",
    "despair",
    "longing",
)
MOODS = (
    "elated",
    "content",
    "fine",
    "uneasy",
    "unhappy",
    "miserable",
    "broken",
)
STAGES = (
    "shock",
    "mourning",
    "acceptance",
    "complicated",
)
DREAMS = (
    "ordinary",
    "nightmare",
    "longing",
    "prophetic",
    "visitation",
    "shared",
)
READINGS = (
    "unread",
    "omen_of_war",
    "omen_of_plenty",
    "omen_of_death",
    "omen_of_favour",
    "warning",
    "call_to_journey",
    "call_to_love",
)
RETYPED = (
    ("memories", "kind", OLD_MEMORIES, NEW_MEMORIES),
    ("needs", "need", OLD_NEEDS, NEW_NEEDS),
    ("conditions", "kind", OLD_CONDITIONS, NEW_CONDITIONS),
)


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(table: str, column: str, old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum(old, column), type_=enum(new, column), existing_nullable=False)


def upgrade() -> None:
    for table, column, old, new in RETYPED:
        retype(table, column, old, new)
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mood", enum(MOODS, "mood"), server_default="fine", nullable=False))
        batch_op.add_column(sa.Column("mood_score", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(op.f("ck_mortal_profiles_mood_score_range"), "mood_score BETWEEN -100 AND 100")
    op.create_table(
        "thoughts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(THOUGHTS, "kind"), nullable=False),
        sa.Column("emotion", enum(EMOTIONS, "emotion"), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("decay_pct", sa.Integer(), nullable=False),
        sa.Column("memory_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_thoughts_intensity_range")),
        sa.CheckConstraint("decay_pct BETWEEN 0 AND 100", name=op.f("ck_thoughts_decay_pct_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_thoughts_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_thoughts_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_thoughts_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], name=op.f("fk_thoughts_memory_id_memories"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_thoughts")),
    )
    with op.batch_alter_table("thoughts", schema=None) as batch_op:
        batch_op.create_index("ix_thoughts_holder", ["holder_node_id", "epoch"], unique=False)
    op.create_table(
        "griefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mourner_node_id", sa.Integer(), nullable=False),
        sa.Column("deceased_node_id", sa.Integer(), nullable=False),
        sa.Column("stage", enum(STAGES, "stage"), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("stage_epoch", sa.Integer(), nullable=False),
        sa.Column("length_epochs", sa.Integer(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_griefs_strength_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_griefs_started_epoch_min")),
        sa.CheckConstraint("length_epochs >= 1", name=op.f("ck_griefs_length_epochs_min")),
        sa.ForeignKeyConstraint(["mourner_node_id"], ["nodes.id"], name=op.f("fk_griefs_mourner_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deceased_node_id"], ["nodes.id"], name=op.f("fk_griefs_deceased_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_griefs")),
        sa.UniqueConstraint("mourner_node_id", "deceased_node_id", name="uq_griefs_mourner_deceased"),
    )
    op.create_table(
        "dreams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dreamer_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(DREAMS, "kind"), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("thought_id", sa.Integer(), nullable=True),
        sa.Column("sender_node_id", sa.Integer(), nullable=True),
        sa.Column("partner_node_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("reading", enum(READINGS, "reading"), nullable=False),
        sa.Column("reader_node_id", sa.Integer(), nullable=True),
        sa.Column("reading_true", sa.Boolean(), nullable=True),
        sa.Column("recurring", sa.Boolean(), nullable=False),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_dreams_intensity_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_dreams_epoch_min")),
        sa.ForeignKeyConstraint(["dreamer_node_id"], ["nodes.id"], name=op.f("fk_dreams_dreamer_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thought_id"], ["thoughts.id"], name=op.f("fk_dreams_thought_id_thoughts"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_node_id"], ["nodes.id"], name=op.f("fk_dreams_sender_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_node_id"], ["nodes.id"], name=op.f("fk_dreams_partner_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_dreams_world_id_worlds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], name=op.f("fk_dreams_message_id_messages"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reader_node_id"], ["nodes.id"], name=op.f("fk_dreams_reader_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dreams")),
    )
    with op.batch_alter_table("dreams", schema=None) as batch_op:
        batch_op.create_index("ix_dreams_dreamer", ["dreamer_node_id", "epoch"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("dreams", schema=None) as batch_op:
        batch_op.drop_index("ix_dreams_dreamer")
    op.drop_table("dreams")
    op.drop_table("griefs")
    with op.batch_alter_table("thoughts", schema=None) as batch_op:
        batch_op.drop_index("ix_thoughts_holder")
    op.drop_table("thoughts")
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_mortal_profiles_mood_score_range"), type_="check")
        batch_op.drop_column("mood_score")
        batch_op.drop_column("mood")
    op.execute("DELETE FROM memories WHERE kind = 'formative'")
    op.execute("DELETE FROM needs WHERE need IN (" + ", ".join(repr(need) for need in NEW_NEEDS[len(OLD_NEEDS) :]) + ")")
    op.execute("DELETE FROM conditions WHERE kind = 'nightmares'")
    for table, column, old, new in RETYPED:
        retype(table, column, new, old)
