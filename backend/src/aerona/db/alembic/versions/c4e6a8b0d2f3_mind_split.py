import sqlalchemy as sa
from alembic import op

revision = "c4e6a8b0d2f3"
down_revision = "b3d5f7a9c1e2"
branch_labels = None
depends_on = None

OLD_AXES = (
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
)
NEW_AXES = (*OLD_AXES, "law", "loyalty", "family", "friendship", "truth", "craftsmanship", "artwork", "competition", "perseverance_value", "leisure")
OLD_SOURCES = (
    "birth",
    "inherited",
    "experience",
    "condition",
    "education",
    "divine",
    "player",
)
NEW_SOURCES = (*OLD_SOURCES, "facet")
ATTRIBUTES = (
    "strength",
    "agility",
    "toughness",
    "endurance",
    "recuperation",
    "disease_resistance",
    "analytical_ability",
    "focus",
    "willpower",
    "creativity",
    "intuition",
    "patience",
    "memory",
    "linguistic_ability",
    "spatial_sense",
    "musicality",
    "kinaesthetic_sense",
    "empathy",
    "social_awareness",
)
FACETS = (
    "anxiety",
    "anger",
    "depression",
    "self_consciousness",
    "vulnerability",
    "cheerfulness",
    "excitement_seeking",
    "emotional_stability",
    "friendliness",
    "gregariousness",
    "assertiveness",
    "trust",
    "altruism",
    "modesty",
    "politeness",
    "cooperation",
    "vanity",
    "envy",
    "gratitude",
    "ambition",
    "perseverance",
    "orderliness",
    "discipline",
    "thoroughness",
    "activity_level",
    "caution",
    "imagination",
    "curiosity",
    "abstraction",
    "artistic_inclination",
    "tolerance_of_strangeness",
    "humour",
    "sense_of_duty",
    "greed",
)
IDEAS = (
    "rationalism",
    "mysticism",
    "asceticism",
    "mercy_for_all",
    "martial_creed",
    "rule_of_law",
    "free_spirit",
    "kin_first",
    "honour_code",
    "wanderlust",
    "materialism",
    "reverence_for_nature",
    "craft_devotion",
    "beauty_above_all",
    "egalitarianism",
    "divine_order",
)
IDEA_SOURCES = (
    "ideology",
    "doctrine",
    "theory",
    "book",
    "teacher",
    "divine",
    "player",
)
IDEA_STATES = (
    "incubating",
    "internalised",
    "rejected",
)
AXIS_TABLES = ("culture_values", "personality_values", "culture_drift_causes", "drift_impositions")


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(table: str, column: str, name: str, old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum(old, name), type_=enum(new, name), existing_nullable=False)


def upgrade() -> None:
    for table in AXIS_TABLES:
        retype(table, "axis", "axis", OLD_AXES, NEW_AXES)
    retype("traits", "source", "source", OLD_SOURCES, NEW_SOURCES)
    op.create_table(
        "mind_attributes",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("attribute", enum(ATTRIBUTES, "attribute"), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value BETWEEN 0 AND 100", name=op.f("ck_mind_attributes_value_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_mind_attributes_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "attribute", name=op.f("pk_mind_attributes")),
    )
    op.create_table(
        "mind_facets",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("facet", enum(FACETS, "facet"), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("value BETWEEN -50 AND 50", name=op.f("ck_mind_facets_value_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_mind_facets_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "facet", name=op.f("pk_mind_facets")),
    )
    op.create_table(
        "incubating_ideas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("idea", enum(IDEAS, "idea"), nullable=False),
        sa.Column("source", enum(IDEA_SOURCES, "source"), nullable=False),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("state", enum(IDEA_STATES, "state"), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("finished_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_incubating_ideas_progress_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_incubating_ideas_started_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_incubating_ideas_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_incubating_ideas_source_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incubating_ideas")),
        sa.UniqueConstraint("holder_node_id", "idea", name="uq_incubating_ideas_holder_idea"),
    )
    with op.batch_alter_table("incubating_ideas", schema=None) as batch_op:
        batch_op.create_index("ix_incubating_ideas_state", ["state"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("incubating_ideas", schema=None) as batch_op:
        batch_op.drop_index("ix_incubating_ideas_state")
    op.drop_table("incubating_ideas")
    op.drop_table("mind_facets")
    op.drop_table("mind_attributes")
    op.execute("DELETE FROM traits WHERE source = 'facet'")
    retype("traits", "source", "source", NEW_SOURCES, OLD_SOURCES)
    for table in AXIS_TABLES:
        op.execute(f"DELETE FROM {table} WHERE axis IN ({', '.join(repr(axis) for axis in NEW_AXES[len(OLD_AXES) :])})")
        retype(table, "axis", "axis", NEW_AXES, OLD_AXES)
