import sqlalchemy as sa
from alembic import op

import aerona.db.types

revision = "c42218f12748"
down_revision = "44a44cbafc29"
branch_labels = None
depends_on = None

EVENT_KINDS = {
    "battle": "fought_us",
    "muharebe": "fought_us",
    "invasion": "fought_us",
    "istila": "fought_us",
    "tribute revolt": "fought_us",
    "debt war": "fought_us",
    "conquest": "conquered_us",
    "fetih": "conquered_us",
    "victory": "humiliated_me",
    "trade": "traded_with",
    "ticaret": "traded_with",
    "barter": "traded_with",
    "first contact": "traded_with",
    "uneasy first contact": "ill_will",
    "distance from the homeland": "ill_will",
    "peace": "made_peace",
    "exhaustion peace": "made_peace",
    "white peace": "made_peace",
    "peace miracle": "divine_will",
    "alliance": "allied_with",
    "ittifak": "allied_with",
    "interworld alliance": "allied_with",
    "interworld treaty": "allied_with",
    "marriage": "married_into",
    "evlilik": "married_into",
    "tribute": "demanded_tribute",
    "debt turned to tribute": "demanded_tribute",
    "tribute ended": "freed_us",
    "ransom": "freed_us",
    "tribute forgiven": "gifted_me",
    "debt forgiven": "gifted_me",
    "debt written off": "gifted_me",
    "loan": "gifted_me",
    "debt paid": "kept_oath",
    "unpaid debt": "cheated_us",
    "broke an oath": "broke_oath",
    "betrayal": "betrayed_me",
    "caught spies": "spied_on_us",
    "resource seized": "harmed_me",
    "adoption": "goodwill",
}
DECAYS = {
    "fought_us": 10,
    "conquered_us": 3,
    "humiliated_me": 7,
    "traded_with": 15,
    "ill_will": 12,
    "made_peace": 10,
    "divine_will": 0,
    "allied_with": 8,
    "married_into": 4,
    "demanded_tribute": 8,
    "freed_us": 4,
    "gifted_me": 15,
    "kept_oath": 8,
    "cheated_us": 10,
    "broke_oath": 6,
    "betrayed_me": 5,
    "spied_on_us": 12,
    "harmed_me": 12,
    "goodwill": 12,
}
MAGNITUDE_LIMIT = 100
DECAY_SCALE_PCT = 40
PERCENT = 100


def migrate_relation_events() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT entity_a_id, entity_b_id, epoch, event, delta FROM community_relation_events ORDER BY id")).fetchall()
    memories = sa.table(
        "memories",
        sa.column("holder_node_id", sa.Integer),
        sa.column("subject_node_id", sa.Integer),
        sa.column("kind", sa.String),
        sa.column("magnitude", sa.Integer),
        sa.column("decay_pct", sa.Integer),
        sa.column("epoch", sa.Integer),
        sa.column("note", sa.String),
    )
    batch = []
    for first, second, epoch, event, delta in rows:
        if not delta:
            continue
        kind = EVENT_KINDS.get(str(event).strip().lower(), "goodwill" if delta > 0 else "ill_will")
        size = max(-MAGNITUDE_LIMIT, min(MAGNITUDE_LIMIT, int(delta)))
        for holder, subject in ((first, second), (second, first)):
            batch.append(
                {
                    "holder_node_id": holder,
                    "subject_node_id": subject,
                    "kind": kind,
                    "magnitude": size,
                    "decay_pct": round(DECAYS[kind] * DECAY_SCALE_PCT / PERCENT),
                    "epoch": max(0, int(epoch)),
                    "note": str(event)[:120],
                }
            )
    if batch:
        op.bulk_insert(memories, batch)


def upgrade() -> None:
    op.create_table(
        "minds",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "holder",
            sa.Enum("culture", "doctrine", "agenda", "personal", "divine", "community", name="holder", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("career_ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_minds_updated_epoch_min")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_minds_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_minds")),
    )
    op.create_table(
        "needs",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "need",
            sa.Enum(
                "sustenance", "safety", "belonging", "status", "purpose", "faith", "pleasure", name="need", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_needs_value_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_needs_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "need", name=op.f("pk_needs")),
    )
    op.create_table(
        "personality_values",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                name="axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value BETWEEN -100 AND 100", name=op.f("ck_personality_values_value_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_personality_values_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "axis", name=op.f("pk_personality_values")),
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
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
            nullable=False,
        ),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("peak", sa.Integer(), nullable=False),
        sa.Column("last_used_epoch", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("backfill", "birth", "practice", "teaching", "player", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.CheckConstraint("level BETWEEN 0 AND 100", name=op.f("ck_skills_level_range")),
        sa.CheckConstraint("peak BETWEEN 0 AND 100", name=op.f("ck_skills_peak_range")),
        sa.CheckConstraint("xp >= 0", name=op.f("ck_skills_xp_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_skills_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_skills_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("holder_node_id", "skill", "subject_node_id", name="uq_skills_holder_skill_subject"),
    )
    with op.batch_alter_table("skills", schema=None) as batch_op:
        batch_op.create_index("ix_skills_skill_level", ["skill", "level"], unique=False)

    op.create_table(
        "traits",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "trait",
            sa.Enum(
                "brave",
                "craven",
                "wrathful",
                "patient",
                "cruel",
                "kind",
                "ambitious",
                "content",
                "greedy",
                "generous",
                "honest",
                "deceitful",
                "zealous",
                "cynical",
                "paranoid",
                "trusting",
                "lustful",
                "chaste",
                "gluttonous",
                "ascetic",
                "scholarly",
                "illiterate_proud",
                "gregarious",
                "reclusive",
                "vengeful",
                "forgiving",
                "stubborn",
                "fickle",
                "just",
                "arbitrary",
                "humble",
                "proud",
                "curious",
                "incurious",
                "melancholic",
                "sanguine",
                "iron_willed",
                "impressionable",
                "cunning_tactician",
                "reckless",
                name="trait",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "birth",
                "inherited",
                "experience",
                "condition",
                "education",
                "divine",
                "player",
                name="source",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_traits_epoch_min")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_traits_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_traits_source_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("node_id", "trait", name=op.f("pk_traits")),
    )
    with op.batch_alter_table("traits", schema=None) as batch_op:
        batch_op.create_index("ix_traits_trait", ["trait"], unique=False)

    op.create_table(
        "culture_values",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                name="axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value BETWEEN -100 AND 100", name=op.f("ck_culture_values_value_range")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_culture_values_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "axis", name=op.f("pk_culture_values")),
    )
    op.create_table(
        "pressures",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "pressure",
            sa.Enum(
                "hunger",
                "insecurity",
                "overcrowding",
                "poverty",
                "impiety",
                "humiliation",
                "stagnation",
                name="pressure",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_pressures_value_range")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_pressures_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_id", "pressure", name=op.f("pk_pressures")),
    )
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
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
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.Column("decay_pct", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.Column("event_entity_id", sa.Integer(), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("inherited_from_node_id", sa.Integer(), nullable=True),
        sa.Column("created_at", aerona.db.types.UtcDateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("decay_pct BETWEEN 0 AND 100", name=op.f("ck_memories_decay_pct_range")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_memories_epoch_min")),
        sa.CheckConstraint("magnitude BETWEEN -100 AND 100", name=op.f("ck_memories_magnitude_range")),
        sa.ForeignKeyConstraint(["event_entity_id"], ["entities.id"], name=op.f("fk_memories_event_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_memories_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_memories_incident_id_incidents"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inherited_from_node_id"], ["nodes.id"], name=op.f("fk_memories_inherited_from_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_memories_subject_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memories")),
    )
    with op.batch_alter_table("memories", schema=None) as batch_op:
        batch_op.create_index("ix_memories_holder_subject", ["holder_node_id", "subject_node_id"], unique=False)
        batch_op.create_index("ix_memories_subject", ["subject_node_id"], unique=False)

    migrate_relation_events()
    with op.batch_alter_table("community_relation_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_community_relation_events_pair"))

    op.drop_table("community_relation_events")


def downgrade() -> None:
    op.create_table(
        "community_relation_events",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("entity_a_id", sa.INTEGER(), nullable=False),
        sa.Column("entity_b_id", sa.INTEGER(), nullable=False),
        sa.Column("epoch", sa.INTEGER(), nullable=False),
        sa.Column("event", sa.VARCHAR(length=120), nullable=False),
        sa.Column("delta", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(["entity_a_id"], ["entities.id"], name=op.f("fk_community_relation_events_entity_a_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_b_id"], ["entities.id"], name=op.f("fk_community_relation_events_entity_b_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_community_relation_events")),
    )
    with op.batch_alter_table("community_relation_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_community_relation_events_pair"), ["entity_a_id", "entity_b_id", "epoch"], unique=False)

    with op.batch_alter_table("memories", schema=None) as batch_op:
        batch_op.drop_index("ix_memories_subject")
        batch_op.drop_index("ix_memories_holder_subject")

    op.drop_table("memories")
    op.drop_table("pressures")
    op.drop_table("culture_values")
    with op.batch_alter_table("traits", schema=None) as batch_op:
        batch_op.drop_index("ix_traits_trait")

    op.drop_table("traits")
    with op.batch_alter_table("skills", schema=None) as batch_op:
        batch_op.drop_index("ix_skills_skill_level")

    op.drop_table("skills")
    op.drop_table("personality_values")
    op.drop_table("needs")
    op.drop_table("minds")
