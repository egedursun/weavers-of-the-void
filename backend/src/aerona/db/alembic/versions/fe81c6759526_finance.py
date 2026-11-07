import sqlalchemy as sa
from alembic import op

revision = "fe81c6759526"
down_revision = "c313c215601c"
branch_labels = None
depends_on = None

COMMODITIES = (
    "grain",
    "livestock",
    "fish",
    "fodder",
    "timber",
    "fuel",
    "bread",
    "ore",
    "stone",
    "cloth",
    "tools",
    "weapons",
    "armour",
    "mounts",
    "siege_materiel",
    "medicine",
    "luxuries",
    "incense",
    "sacred_goods",
    "magical_reagents",
)

POLICIES = (
    "tariff",
    "subsidy",
    "embargo",
)

STATES = (
    "normal",
    "strained",
    "default",
    "restructuring",
)

STATUSES = (
    "hoarding",
    "sold",
    "bust",
)


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def node_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], ["nodes.id"], name=op.f(f"fk_{table}_{column}_nodes"), ondelete="CASCADE")


def at_least(table: str, *columns: str) -> list[sa.CheckConstraint]:
    return [sa.CheckConstraint(f"{column} >= 0", name=op.f(f"ck_{table}_{column}_min")) for column in columns]


def percent(table: str, *columns: str) -> list[sa.CheckConstraint]:
    return [sa.CheckConstraint(f"{column} BETWEEN 0 AND 100", name=op.f(f"ck_{table}_{column}_range")) for column in columns]


def upgrade() -> None:
    op.create_table(
        "trade_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issuer_node_id", sa.Integer(), nullable=False),
        sa.Column("kind", enum(POLICIES, "kind"), nullable=False),
        sa.Column("commodity", enum(COMMODITIES, "commodity"), nullable=True),
        sa.Column("partner_node_id", sa.Integer(), nullable=True),
        sa.Column("rate_pct", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        *percent("trade_policies", "rate_pct"),
        *at_least("trade_policies", "since_epoch"),
        node_fk("trade_policies", "issuer_node_id"),
        node_fk("trade_policies", "partner_node_id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trade_policies")),
    )
    with op.batch_alter_table("trade_policies", schema=None) as batch_op:
        batch_op.create_index("ix_trade_policies_issuer", ["issuer_node_id"], unique=False)
    op.create_table(
        "credit_profiles",
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("state", enum(STATES, "state"), nullable=False),
        sa.Column("interest_pct", sa.Integer(), nullable=False),
        sa.Column("reserves", sa.Integer(), nullable=False),
        sa.Column("defaults", sa.Integer(), nullable=False),
        sa.Column("restructured_until", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        *percent("credit_profiles", "rating", "interest_pct"),
        *at_least("credit_profiles", "reserves", "defaults", "epoch"),
        node_fk("credit_profiles", "subject_node_id"),
        sa.PrimaryKeyConstraint("subject_node_id", name=op.f("pk_credit_profiles")),
    )
    op.create_table(
        "speculations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_node_id", sa.Integer(), nullable=False),
        sa.Column("market_node_id", sa.Integer(), nullable=False),
        sa.Column("commodity", enum(COMMODITIES, "commodity"), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("status", enum(STATUSES, "status"), nullable=False),
        sa.Column("opened_epoch", sa.Integer(), nullable=False),
        sa.Column("settled_epoch", sa.Integer(), nullable=True),
        sa.Column("gain", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        *at_least("speculations", "units", "price", "opened_epoch"),
        node_fk("speculations", "merchant_node_id"),
        node_fk("speculations", "market_node_id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_speculations")),
    )
    with op.batch_alter_table("speculations", schema=None) as batch_op:
        batch_op.create_index("ix_speculations_merchant", ["merchant_node_id"], unique=False)
        batch_op.create_index("ix_speculations_market", ["market_node_id"], unique=False)
    op.create_table(
        "economic_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_node_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("output", sa.Integer(), nullable=False),
        sa.Column("price_index", sa.Integer(), nullable=False),
        sa.Column("trade_balance", sa.Integer(), nullable=False),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("debt_ratio", sa.Integer(), nullable=False),
        sa.Column("unemployment", sa.Integer(), nullable=False),
        sa.Column("market_access", sa.Integer(), nullable=False),
        sa.Column("black_market", sa.Integer(), nullable=False),
        sa.Column("living", sa.JSON(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        *at_least("economic_indicators", "epoch", "output", "price_index", "debt_ratio", "black_market"),
        *percent("economic_indicators", "unemployment", "market_access"),
        node_fk("economic_indicators", "subject_node_id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_economic_indicators")),
        sa.UniqueConstraint("subject_node_id", "epoch", name="uq_economic_indicators_subject_epoch"),
    )
    with op.batch_alter_table("economic_indicators", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_economic_indicators_subject_node_id"), ["subject_node_id"], unique=False)
    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.add_column(sa.Column("market_access", sa.Integer(), server_default="100", nullable=False))
        batch_op.add_column(sa.Column("black_market", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint(batch_op.f("ck_community_industry_market_access_range"), "market_access BETWEEN 0 AND 100")
        batch_op.create_check_constraint(batch_op.f("ck_community_industry_black_market_min"), "black_market >= 0")


def downgrade() -> None:
    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_community_industry_black_market_min"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_community_industry_market_access_range"), type_="check")
        batch_op.drop_column("black_market")
        batch_op.drop_column("market_access")
    with op.batch_alter_table("economic_indicators", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_economic_indicators_subject_node_id"))
    op.drop_table("economic_indicators")
    with op.batch_alter_table("speculations", schema=None) as batch_op:
        batch_op.drop_index("ix_speculations_market")
        batch_op.drop_index("ix_speculations_merchant")
    op.drop_table("speculations")
    op.drop_table("credit_profiles")
    with op.batch_alter_table("trade_policies", schema=None) as batch_op:
        batch_op.drop_index("ix_trade_policies_issuer")
    op.drop_table("trade_policies")
