import sqlalchemy as sa
from alembic import op

revision = "e7a9c1d3f5b6"
down_revision = "d5f7b9c1e3a4"
branch_labels = None
depends_on = None

OLD_ACTS = (
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
)
NEW_ACTS = (
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
)
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
)
NEW_THOUGHTS = (
    *OLD_THOUGHTS,
    "liked_surroundings",
    "disliked_surroundings",
    "enjoyed_favourite",
    "endured_a_dislike",
    "acted_on_conscience",
    "acted_against_conscience",
    "kin_shamed",
    "shame_restored",
)
PREFERENCES = (
    "material",
    "food",
    "drink",
    "creature",
    "plant",
    "colour",
    "shape",
    "art_form",
    "artwork_subject",
    "season",
    "weather",
    "terrain",
    "activity",
    "craft",
    "deity_aspect",
)
STANCES = (
    "required",
    "admirable",
    "acceptable",
    "frowned_upon",
    "shameful",
    "unthinkable",
)
MODELS = (
    "dignity",
    "honour",
    "face",
)


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.alter_column("taboo_act", existing_type=enum(OLD_ACTS, "taboo_act"), type_=enum(NEW_ACTS, "taboo_act"), existing_nullable=True)
    with op.batch_alter_table("thoughts", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum(OLD_THOUGHTS, "kind"), type_=enum(NEW_THOUGHTS, "kind"), existing_nullable=False)
    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("colour", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("shape", sa.String(length=120), nullable=True))
    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(PREFERENCES, "kind"), nullable=False),
        sa.Column("target", sa.String(length=120), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN -100 AND 100", name=op.f("ck_preferences_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_preferences_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_preferences_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_preferences")),
        sa.UniqueConstraint("holder_node_id", "kind", "target", name="uq_preferences_holder_kind_target"),
    )
    with op.batch_alter_table("preferences", schema=None) as batch_op:
        batch_op.create_index("ix_preferences_holder", ["holder_node_id"], unique=False)
    op.create_table(
        "culture_ethics",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("act", enum(NEW_ACTS, "act"), nullable=False),
        sa.Column("stance", enum(STANCES, "stance"), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_culture_ethics_since_epoch_min")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_culture_ethics_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "act", name=op.f("pk_culture_ethics")),
    )
    op.create_table(
        "culture_honour",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("model", enum(MODELS, "model"), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_culture_honour_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_culture_honour")),
    )


def downgrade() -> None:
    op.drop_table("culture_honour")
    op.drop_table("culture_ethics")
    with op.batch_alter_table("preferences", schema=None) as batch_op:
        batch_op.drop_index("ix_preferences_holder")
    op.drop_table("preferences")
    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.drop_column("shape")
        batch_op.drop_column("colour")
    op.execute("DELETE FROM thoughts WHERE kind IN (" + ", ".join(repr(kind) for kind in NEW_THOUGHTS[len(OLD_THOUGHTS) :]) + ")")
    with op.batch_alter_table("thoughts", schema=None) as batch_op:
        batch_op.alter_column("kind", existing_type=enum(NEW_THOUGHTS, "kind"), type_=enum(OLD_THOUGHTS, "kind"), existing_nullable=False)
    op.execute("UPDATE tradition_profiles SET taboo_act = NULL WHERE taboo_act NOT IN (" + ", ".join(repr(act) for act in OLD_ACTS) + ")")
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.alter_column("taboo_act", existing_type=enum(NEW_ACTS, "taboo_act"), type_=enum(OLD_ACTS, "taboo_act"), existing_nullable=True)
