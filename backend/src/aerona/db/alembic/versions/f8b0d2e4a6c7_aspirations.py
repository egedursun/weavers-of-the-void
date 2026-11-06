import sqlalchemy as sa
from alembic import op

revision = "f8b0d2e4a6c7"
down_revision = "e7a9c1d3f5b6"
branch_labels = None
depends_on = None

OLD_THOUGHTS = (
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
    "liked_surroundings",
    "disliked_surroundings",
    "enjoyed_favourite",
    "endured_a_dislike",
    "acted_on_conscience",
    "acted_against_conscience",
    "kin_shamed",
    "shame_restored",
)
NEW_THOUGHTS = (
    *OLD_THOUGHTS,
    "dream_progress",
    "dream_fulfilled",
    "dream_shattered",
    "want_fulfilled",
    "fear_near",
    "inspired",
    "inspiration_lost",
    "disillusioned",
)
OLD_SOURCES = (
    "injury",
    "condition",
    "trait",
    "law",
    "tradition",
    "artwork",
    "doctrine",
    "treaty",
    "structure",
    "wonder",
    "terrain",
    "weather",
    "season",
    "natural_law",
    "god_power",
    "blessing",
    "curse",
    "dominion",
    "phenomenon",
    "god_death",
    "player",
    "suppression",
    "pin",
)
NEW_SOURCES = (*OLD_SOURCES, "perk")
GOALS = (
    "rule_a_realm",
    "found_a_house",
    "master_a_craft",
    "create_a_masterwork",
    "become_a_legend",
    "raise_a_family",
    "see_the_world",
    "achieve_holiness",
    "gain_wealth",
    "avenge_kin",
    "know_a_truth",
    "defeat_a_beast",
    "serve_a_god",
    "live_in_peace",
    "find_love",
)
DREAM_STATES = (
    "pursuing",
    "fulfilled",
    "failed",
)
WANTS = (
    "marry",
    "gain_office",
    "fine_weapon",
    "visit_a_shrine",
    "learn_a_skill",
    "gain_wealth",
    "have_a_child",
    "travel",
    "win_glory",
    "make_peace",
    "avenge",
    "find_a_teacher",
)
FEARS = (
    "death",
    "war",
    "plague",
    "beasts",
    "losing_a_child",
    "poverty",
    "shame",
    "dark",
)
FOCUSES = (
    "diplomacy",
    "martial",
    "stewardship",
    "intrigue",
    "learning",
    "piety",
    "craft",
    "leisure",
)
PERKS = (
    "silver_tongue",
    "peacemaker",
    "well_connected",
    "envoys_patience",
    "beloved",
    "hardened",
    "swift_blade",
    "iron_nerve",
    "battle_eye",
    "warlord",
    "ledger_mind",
    "steady_hand",
    "prudent",
    "builder",
    "granary_keeper",
    "shadow_step",
    "keen_ear",
    "mask",
    "web_spinner",
    "cold_eye",
    "quick_study",
    "deep_memory",
    "lucid",
    "sages_insight",
    "polymath",
    "devout",
    "serene",
    "faithful_voice",
    "visionary",
    "hallowed",
    "sure_hands",
    "inventive",
    "tireless",
    "eye_for_beauty",
    "masters_touch",
    "good_company",
    "carefree",
    "reveller",
    "charming",
    "joyful_spirit",
)
INSPIRATIONS = (
    "masterwork_fever",
    "research_insight",
    "heroic_resolve",
)
INSPIRATION_STATES = (
    "burning",
    "fulfilled",
    "failed",
)


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def node_fk(table: str, column: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], ["nodes.id"], name=op.f(f"fk_{table}_{column}_nodes"), ondelete=ondelete)


def upgrade() -> None:
    with op.batch_alter_table("thoughts", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum(OLD_THOUGHTS, "kind"), type_=enum(NEW_THOUGHTS, "kind"), existing_nullable=False)
    with op.batch_alter_table("modifiers", schema=None) as batch_op:
        batch_op.alter_column("source_kind", existing_type=enum(OLD_SOURCES, "source_kind"), type_=enum(NEW_SOURCES, "source_kind"), existing_nullable=False)
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("focus", enum(FOCUSES, "focus"), nullable=True))
        batch_op.add_column(sa.Column("conviction", sa.Integer(), server_default="50", nullable=False))
        batch_op.create_check_constraint(op.f("ck_mortal_profiles_conviction_range"), "conviction BETWEEN 0 AND 100")
    op.create_table(
        "life_dreams",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("goal", enum(GOALS, "goal"), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("milestones", sa.JSON(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("state", enum(DREAM_STATES, "state"), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_life_dreams_progress_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_life_dreams_started_epoch_min")),
        node_fk("life_dreams", "holder_node_id", "CASCADE"),
        node_fk("life_dreams", "target_node_id", "SET NULL"),
        sa.PrimaryKeyConstraint("holder_node_id", name=op.f("pk_life_dreams")),
    )
    op.create_table(
        "wants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(WANTS, "kind"), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("fulfilled_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_wants_epoch_min")),
        node_fk("wants", "holder_node_id", "CASCADE"),
        node_fk("wants", "target_node_id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wants")),
    )
    with op.batch_alter_table("wants", schema=None) as batch_op:
        batch_op.create_index("ix_wants_holder", ["holder_node_id"], unique=False)
    op.create_table(
        "fears",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(FEARS, "kind"), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_fears_strength_range")),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_fears_since_epoch_min")),
        node_fk("fears", "holder_node_id", "CASCADE"),
        node_fk("fears", "target_node_id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fears")),
        sa.UniqueConstraint("holder_node_id", "kind", name="uq_fears_holder_kind"),
    )
    op.create_table(
        "mortal_perks",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("perk", enum(PERKS, "perk"), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_mortal_perks_epoch_min")),
        node_fk("mortal_perks", "holder_node_id", "CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "perk", name=op.f("pk_mortal_perks")),
    )
    op.create_table(
        "inspirations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(INSPIRATIONS, "kind"), nullable=False),
        sa.Column("material", sa.String(length=120), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("deadline_epoch", sa.Integer(), nullable=False),
        sa.Column("state", enum(INSPIRATION_STATES, "state"), nullable=False),
        sa.Column("result_node_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_inspirations_started_epoch_min")),
        node_fk("inspirations", "holder_node_id", "CASCADE"),
        node_fk("inspirations", "result_node_id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inspirations")),
    )
    with op.batch_alter_table("inspirations", schema=None) as batch_op:
        batch_op.create_index("ix_inspirations_holder", ["holder_node_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("inspirations", schema=None) as batch_op:
        batch_op.drop_index("ix_inspirations_holder")
    op.drop_table("inspirations")
    op.drop_table("mortal_perks")
    op.drop_table("fears")
    with op.batch_alter_table("wants", schema=None) as batch_op:
        batch_op.drop_index("ix_wants_holder")
    op.drop_table("wants")
    op.drop_table("life_dreams")
    with op.batch_alter_table("mortal_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_mortal_profiles_conviction_range"), type_="check")
        batch_op.drop_column("conviction")
        batch_op.drop_column("focus")
    op.execute("DELETE FROM modifiers WHERE source_kind = 'perk'")
    with op.batch_alter_table("modifiers", schema=None) as batch_op:
        batch_op.alter_column("source_kind", existing_type=enum(NEW_SOURCES, "source_kind"), type_=enum(OLD_SOURCES, "source_kind"), existing_nullable=False)
    op.execute("DELETE FROM thoughts WHERE kind IN (" + ", ".join(repr(kind) for kind in NEW_THOUGHTS[len(OLD_THOUGHTS) :]) + ")")
    with op.batch_alter_table("thoughts", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum(NEW_THOUGHTS, "kind"), type_=enum(OLD_THOUGHTS, "kind"), existing_nullable=False)
