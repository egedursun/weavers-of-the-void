import sqlalchemy as sa
from alembic import op

revision = "e6b0c1d3f7a8"
down_revision = "d4f8b0c2e6a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "faction_profiles",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "merchant_guild",
                "craft_guild",
                "priesthood",
                "warrior_order",
                "noble_council",
                "peasant_league",
                "rebels",
                "bandits",
                "pirates",
                "assassins",
                "scholars_academy",
                "secret_society",
                "mercenary_company",
                "interworld_federation",
                "wandering_market",
                "void_pirates",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "scale", sa.Enum("band", "company", "organisation", "network", name="scale", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("treasury", sa.Integer(), nullable=False),
        sa.Column("cohesion", sa.Integer(), nullable=False),
        sa.Column("secrecy", sa.Integer(), nullable=False),
        sa.Column("armed", sa.Boolean(), nullable=False),
        sa.Column("reputation", sa.Integer(), nullable=False),
        sa.Column("influence_over", sa.JSON(), nullable=False),
        sa.Column("cohort_share", sa.JSON(), nullable=False),
        sa.Column("home_entity_id", sa.Integer(), nullable=True),
        sa.Column("leader_entity_id", sa.Integer(), nullable=True),
        sa.Column("outlawed", sa.Boolean(), nullable=False),
        sa.Column("chartered_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("monopoly", sa.String(length=120), nullable=True),
        sa.Column("employer_entity_id", sa.Integer(), nullable=True),
        sa.Column("contract_entity_id", sa.Integer(), nullable=True),
        sa.Column("pay", sa.Integer(), nullable=False),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("unpaid_epochs", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cohesion BETWEEN 0 AND 100", name=op.f("ck_faction_profiles_cohesion_range")),
        sa.CheckConstraint("secrecy BETWEEN 0 AND 100", name=op.f("ck_faction_profiles_secrecy_range")),
        sa.CheckConstraint("reputation BETWEEN 0 AND 100", name=op.f("ck_faction_profiles_reputation_range")),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_faction_profiles_loyalty_range")),
        sa.CheckConstraint("treasury >= 0", name=op.f("ck_faction_profiles_treasury_min")),
        sa.CheckConstraint("pay >= 0", name=op.f("ck_faction_profiles_pay_min")),
        sa.CheckConstraint("unpaid_epochs >= 0", name=op.f("ck_faction_profiles_unpaid_epochs_min")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_faction_profiles_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_entity_id"], ["entities.id"], name=op.f("fk_faction_profiles_home_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["leader_entity_id"], ["entities.id"], name=op.f("fk_faction_profiles_leader_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["chartered_by_entity_id"], ["entities.id"], name=op.f("fk_faction_profiles_chartered_by_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["employer_entity_id"], ["entities.id"], name=op.f("fk_faction_profiles_employer_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contract_entity_id"], ["entities.id"], name=op.f("fk_faction_profiles_contract_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_faction_profiles")),
    )
    with op.batch_alter_table("faction_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_faction_profiles_kind", ["kind"], unique=False)
        batch_op.create_index(op.f("ix_faction_profiles_home_entity_id"), ["home_entity_id"], unique=False)
        batch_op.create_index(op.f("ix_faction_profiles_employer_entity_id"), ["employer_entity_id"], unique=False)
    op.create_table(
        "faction_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "lower_taxes",
                "monopoly_on",
                "install_claimant",
                "abolish_law",
                "enact_law",
                "war_on",
                "peace_with",
                "protect_craft",
                "convert_realm",
                "independence",
                "loot",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("target_key", sa.String(length=120), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("achieved_epoch", sa.Integer(), nullable=True),
        sa.Column("set_by_player", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name=op.f("ck_faction_goals_priority_range")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_faction_goals_progress_range")),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_faction_goals_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_faction_goals_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_faction_goals")),
    )
    with op.batch_alter_table("faction_goals", schema=None) as batch_op:
        batch_op.create_index("ix_faction_goals_faction", ["faction_entity_id"], unique=False)
    op.create_table(
        "faction_memberships",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Enum("leader", "officer", "member", "novice", name="rank", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("joined_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_faction_memberships_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_faction_memberships_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", "mortal_entity_id", name=op.f("pk_faction_memberships")),
    )
    with op.batch_alter_table("faction_memberships", schema=None) as batch_op:
        batch_op.create_index("ix_faction_memberships_mortal", ["mortal_entity_id"], unique=False)
    op.create_table(
        "faction_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "lobby",
                "bribe",
                "petition",
                "strike",
                "riot",
                "coup",
                "assassinate",
                "smuggle",
                "raid",
                "fund_war",
                "recruit",
                "schism",
                "suppressed",
                "hired",
                "defected",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("goal_id", sa.Integer(), nullable=True),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_faction_actions_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["faction_goals.id"], name=op.f("fk_faction_actions_goal_id_faction_goals"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_faction_actions_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_faction_actions")),
    )
    with op.batch_alter_table("faction_actions", schema=None) as batch_op:
        batch_op.create_index("ix_faction_actions_faction", ["faction_entity_id", "epoch"], unique=False)


def downgrade() -> None:
    op.drop_table("faction_actions")
    op.drop_table("faction_memberships")
    op.drop_table("faction_goals")
    op.drop_table("faction_profiles")
