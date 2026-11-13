import sqlalchemy as sa
from alembic import op

revision = "40759d04fa80"
down_revision = "d4f2a8c61e97"
branch_labels = None
depends_on = None

PLOT_OLD = (
    "murder",
    "abduct",
    "seduce",
    "sway",
    "fabricate_claim",
    "fabricate_hook",
    "steal_relic",
    "coup",
    "poison_well",
    "frame",
    "elope",
    "convert_secretly",
    "sabotage_wedding",
    "free_prisoner",
    "ecosabotage",
    "learn_true_name",
    "forge_letter",
    "geas_trap",
)
PLOT_NEW = (
    "murder",
    "abduct",
    "seduce",
    "sway",
    "fabricate_claim",
    "fabricate_hook",
    "steal_relic",
    "coup",
    "poison_well",
    "frame",
    "elope",
    "convert_secretly",
    "sabotage_wedding",
    "free_prisoner",
    "ecosabotage",
    "learn_true_name",
    "forge_letter",
    "geas_trap",
    "hide_fleet",
)
CLAUSE_OLD = (
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
    "route_control",
    "resource_demand",
    "research_agreement",
)
CLAUSE_NEW = (
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
    "route_control",
    "resource_demand",
    "research_agreement",
    "fleet_limit",
)
TREATY_OLD = (
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
    "coalition",
    "divine_pact",
)
TREATY_NEW = (
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
    "coalition",
    "divine_pact",
    "naval_limit",
)
COLUMNS = (
    ("schemes", "kind", PLOT_OLD, PLOT_NEW),
    ("treaty_clauses", "kind", CLAUSE_OLD, CLAUSE_NEW),
    ("treaty_profiles", "kind", TREATY_OLD, TREATY_NEW),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, before, after in COLUMNS:
        old, new = (before, after) if forward else (after, before)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(old, column), type_=enum_of(new, column), existing_nullable=False)


def upgrade() -> None:
    retype(forward=True)
    op.create_table(
        "admiralties",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("admiral_entity_id", sa.Integer(), nullable=True),
        sa.Column("budget_share", sa.Integer(), nullable=False),
        sa.Column("requested", sa.Integer(), nullable=False),
        sa.Column("influence", sa.Integer(), nullable=False),
        sa.Column("tonnage", sa.Integer(), nullable=False),
        sa.Column("limit_tonnage", sa.Integer(), nullable=True),
        sa.Column("concealed", sa.Integer(), nullable=False),
        sa.Column("commissioned", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("budget_share BETWEEN 0 AND 100", name=op.f("ck_admiralties_budget_share_range")),
        sa.CheckConstraint("commissioned >= 0", name=op.f("ck_admiralties_commissioned_min")),
        sa.CheckConstraint("concealed >= 0", name=op.f("ck_admiralties_concealed_min")),
        sa.CheckConstraint("influence BETWEEN 0 AND 100", name=op.f("ck_admiralties_influence_range")),
        sa.CheckConstraint("requested BETWEEN 0 AND 100", name=op.f("ck_admiralties_requested_range")),
        sa.CheckConstraint("tonnage >= 0", name=op.f("ck_admiralties_tonnage_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_admiralties_updated_epoch_min")),
        sa.ForeignKeyConstraint(["admiral_entity_id"], ["entities.id"], name=op.f("fk_admiralties_admiral_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_admiralties_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_admiralties")),
    )
    op.create_table(
        "army_operations",
        sa.Column("army_entity_id", sa.Integer(), nullable=False),
        sa.Column("offensive_seasons", sa.Integer(), nullable=False),
        sa.Column("need", sa.Integer(), nullable=False),
        sa.Column("delivered", sa.Integer(), nullable=False),
        sa.Column("organisation", sa.Integer(), nullable=False),
        sa.Column("culminated", sa.Boolean(), nullable=False),
        sa.Column("culminated_epoch", sa.Integer(), nullable=True),
        sa.Column("pause_seasons", sa.Integer(), nullable=False),
        sa.Column("foresight", sa.Integer(), nullable=False),
        sa.Column("standing", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("delivered >= 0", name=op.f("ck_army_operations_delivered_min")),
        sa.CheckConstraint("foresight >= 0", name=op.f("ck_army_operations_foresight_min")),
        sa.CheckConstraint("need >= 0", name=op.f("ck_army_operations_need_min")),
        sa.CheckConstraint("offensive_seasons >= 0", name=op.f("ck_army_operations_offensive_seasons_min")),
        sa.CheckConstraint("organisation BETWEEN 0 AND 100", name=op.f("ck_army_operations_organisation_range")),
        sa.CheckConstraint("pause_seasons >= 0", name=op.f("ck_army_operations_pause_seasons_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_army_operations_updated_epoch_min")),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_army_operations_army_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("army_entity_id", name=op.f("pk_army_operations")),
    )
    op.create_table(
        "depots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("structure_entity_id", sa.Integer(), nullable=True),
        sa.Column("supplies", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("field", sa.Boolean(), nullable=False),
        sa.Column("cut", sa.Boolean(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity >= 0", name=op.f("ck_depots_capacity_min")),
        sa.CheckConstraint("founded_epoch >= 0", name=op.f("ck_depots_founded_epoch_min")),
        sa.CheckConstraint("supplies >= 0", name=op.f("ck_depots_supplies_min")),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_depots_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_depots_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_depots_structure_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_depots")),
    )
    with op.batch_alter_table("depots", schema=None) as batch_op:
        batch_op.create_index("ix_depots_owner", ["owner_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_depots_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "echelons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("army_entity_id", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "level",
            sa.Enum("army_group", "army", "corps", "division", "brigade", name="level", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("commander_entity_id", sa.Integer(), nullable=True),
        sa.Column("hq_region_entity_id", sa.Integer(), nullable=True),
        sa.Column("staff", sa.Integer(), nullable=False),
        sa.Column("command_range", sa.Integer(), nullable=False),
        sa.Column("command_points", sa.Integer(), nullable=False),
        sa.Column("points_spent", sa.Integer(), nullable=False),
        sa.Column(
            "order",
            sa.Enum("attack", "manoeuvre", "resupply", "hold", "standing", name="order", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("in_range", sa.Boolean(), nullable=False),
        sa.Column("formed_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("command_points >= 0", name=op.f("ck_echelons_command_points_min")),
        sa.CheckConstraint("command_range >= 0", name=op.f("ck_echelons_command_range_min")),
        sa.CheckConstraint("formed_epoch >= 0", name=op.f("ck_echelons_formed_epoch_min")),
        sa.CheckConstraint("points_spent >= 0", name=op.f("ck_echelons_points_spent_min")),
        sa.CheckConstraint("staff BETWEEN 0 AND 100", name=op.f("ck_echelons_staff_range")),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_echelons_army_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["commander_entity_id"], ["entities.id"], name=op.f("fk_echelons_commander_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hq_region_entity_id"], ["entities.id"], name=op.f("fk_echelons_hq_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_echelons_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["echelons.id"], name=op.f("fk_echelons_parent_id_echelons"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_echelons")),
    )
    with op.batch_alter_table("echelons", schema=None) as batch_op:
        batch_op.create_index("ix_echelons_army", ["army_entity_id"], unique=False)
        batch_op.create_index("ix_echelons_owner", ["owner_entity_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_echelons_parent_id"), ["parent_id"], unique=False)

    op.create_table(
        "expeditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("leader_entity_id", sa.Integer(), nullable=True),
        sa.Column("sponsor_node_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "ground", sa.Enum("site", "wilds", "underworld", "realm", name="ground", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "status", sa.Enum("underway", "camped", "returned", "lost", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("legs_done", sa.Integer(), nullable=False),
        sa.Column("legs_total", sa.Integer(), nullable=False),
        sa.Column("provisions", sa.Integer(), nullable=False),
        sa.Column("light", sa.Integer(), nullable=False),
        sa.Column("tools", sa.Integer(), nullable=False),
        sa.Column("medicine", sa.Integer(), nullable=False),
        sa.Column("darkness", sa.Integer(), nullable=False),
        sa.Column("danger", sa.Integer(), nullable=False),
        sa.Column("found", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("danger BETWEEN 0 AND 100", name=op.f("ck_expeditions_danger_range")),
        sa.CheckConstraint("darkness BETWEEN 0 AND 100", name=op.f("ck_expeditions_darkness_range")),
        sa.CheckConstraint("found >= 0", name=op.f("ck_expeditions_found_min")),
        sa.CheckConstraint("legs_done >= 0", name=op.f("ck_expeditions_legs_done_min")),
        sa.CheckConstraint("legs_total >= 1", name=op.f("ck_expeditions_legs_total_min")),
        sa.CheckConstraint("light >= 0", name=op.f("ck_expeditions_light_min")),
        sa.CheckConstraint("medicine >= 0", name=op.f("ck_expeditions_medicine_min")),
        sa.CheckConstraint("provisions >= 0", name=op.f("ck_expeditions_provisions_min")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_expeditions_started_epoch_min")),
        sa.CheckConstraint("tools >= 0", name=op.f("ck_expeditions_tools_min")),
        sa.ForeignKeyConstraint(["leader_entity_id"], ["entities.id"], name=op.f("fk_expeditions_leader_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sponsor_node_id"], ["nodes.id"], name=op.f("fk_expeditions_sponsor_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_expeditions_target_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expeditions")),
    )
    with op.batch_alter_table("expeditions", schema=None) as batch_op:
        batch_op.create_index("ix_expeditions_leader", ["leader_entity_id"], unique=False)
        batch_op.create_index("ix_expeditions_target", ["target_entity_id"], unique=False)

    op.create_table(
        "ship_crews",
        sa.Column("vessel_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "station",
            sa.Enum("gunners", "topmen", "marines", "officers", "rowers", name="station", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("skill", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("count >= 0", name=op.f("ck_ship_crews_count_min")),
        sa.CheckConstraint("skill BETWEEN 0 AND 100", name=op.f("ck_ship_crews_skill_range")),
        sa.ForeignKeyConstraint(["vessel_entity_id"], ["entities.id"], name=op.f("fk_ship_crews_vessel_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vessel_entity_id", "station", name=op.f("pk_ship_crews")),
    )
    op.create_table(
        "ship_states",
        sa.Column("vessel_entity_id", sa.Integer(), nullable=False),
        sa.Column("heading", sa.Integer(), nullable=False),
        sa.Column("wind_from", sa.Integer(), nullable=False),
        sa.Column(
            "point_of_sail",
            sa.Enum(
                "in_irons", "close_hauled", "reaching", "running", "under_oars", name="point_of_sail", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("tacks", sa.Integer(), nullable=False),
        sa.Column("shot", sa.Enum("round", "chain", "grape", "fire", name="shot", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("leak", sa.Integer(), nullable=False),
        sa.Column("fire", sa.Integer(), nullable=False),
        sa.Column("magazine", sa.Boolean(), nullable=False),
        sa.Column("rate_of_fire", sa.Integer(), nullable=False),
        sa.Column("rower_fatigue", sa.Integer(), nullable=False),
        sa.Column("raked", sa.Integer(), nullable=False),
        sa.Column("struck", sa.Boolean(), nullable=False),
        sa.Column("prize_of_entity_id", sa.Integer(), nullable=True),
        sa.Column("prize_crew", sa.Integer(), nullable=False),
        sa.Column("prize_money", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fire BETWEEN 0 AND 100", name=op.f("ck_ship_states_fire_range")),
        sa.CheckConstraint("heading BETWEEN 0 AND 7", name=op.f("ck_ship_states_heading_range")),
        sa.CheckConstraint("leak BETWEEN 0 AND 100", name=op.f("ck_ship_states_leak_range")),
        sa.CheckConstraint("prize_crew >= 0", name=op.f("ck_ship_states_prize_crew_min")),
        sa.CheckConstraint("prize_money >= 0", name=op.f("ck_ship_states_prize_money_min")),
        sa.CheckConstraint("raked >= 0", name=op.f("ck_ship_states_raked_min")),
        sa.CheckConstraint("rate_of_fire BETWEEN 0 AND 100", name=op.f("ck_ship_states_rate_of_fire_range")),
        sa.CheckConstraint("rower_fatigue BETWEEN 0 AND 100", name=op.f("ck_ship_states_rower_fatigue_range")),
        sa.CheckConstraint("tacks >= 0", name=op.f("ck_ship_states_tacks_min")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_ship_states_updated_epoch_min")),
        sa.CheckConstraint("wind_from BETWEEN 0 AND 7", name=op.f("ck_ship_states_wind_from_range")),
        sa.ForeignKeyConstraint(["prize_of_entity_id"], ["entities.id"], name=op.f("fk_ship_states_prize_of_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vessel_entity_id"], ["entities.id"], name=op.f("fk_ship_states_vessel_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vessel_entity_id", name=op.f("pk_ship_states")),
    )
    op.create_table(
        "expedition_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("member_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("leg", sa.Integer(), nullable=False),
        sa.Column(
            "event",
            sa.Enum(
                "setout",
                "leg",
                "room",
                "camp",
                "ambush",
                "exposure",
                "affliction",
                "virtue",
                "quirk",
                "fallen",
                "return",
                "loss",
                name="event",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("provisions_used", sa.Integer(), nullable=False),
        sa.Column("light_used", sa.Integer(), nullable=False),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.Column(
            "resolve",
            sa.Enum(
                "steady",
                "paranoid",
                "hopeless",
                "selfish",
                "abusive",
                "courageous",
                "focused",
                "stalwart",
                name="resolve",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "quirk",
            sa.Enum(
                "fears_dark",
                "dark_sighted",
                "knows_ways",
                "eats_anything",
                "hardy",
                "frail",
                "jumpy",
                "steady_nerves",
                "keen_eyed",
                "homesick",
                "restless",
                "light_fingered",
                name="quirk",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_expedition_logs_epoch_min")),
        sa.CheckConstraint("leg >= 0", name=op.f("ck_expedition_logs_leg_min")),
        sa.CheckConstraint("light_used >= 0", name=op.f("ck_expedition_logs_light_used_min")),
        sa.CheckConstraint("provisions_used >= 0", name=op.f("ck_expedition_logs_provisions_used_min")),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], name=op.f("fk_expedition_logs_expedition_id_expeditions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_entity_id"], ["entities.id"], name=op.f("fk_expedition_logs_member_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expedition_logs")),
    )
    with op.batch_alter_table("expedition_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_expedition_logs_expedition_id"), ["expedition_id"], unique=False)

    op.create_table(
        "expedition_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("scout", "guide", "healer", "fighter", "scholar", "porter", name="role", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.Column(
            "resolve",
            sa.Enum(
                "steady",
                "paranoid",
                "hopeless",
                "selfish",
                "abusive",
                "courageous",
                "focused",
                "stalwart",
                name="resolve",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("cold", sa.Integer(), nullable=False),
        sa.Column("wet", sa.Integer(), nullable=False),
        sa.Column("hunger", sa.Integer(), nullable=False),
        sa.Column("fatigue", sa.Integer(), nullable=False),
        sa.Column("fallen", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cold BETWEEN 0 AND 100", name=op.f("ck_expedition_members_cold_range")),
        sa.CheckConstraint("fatigue BETWEEN 0 AND 100", name=op.f("ck_expedition_members_fatigue_range")),
        sa.CheckConstraint("hunger BETWEEN 0 AND 100", name=op.f("ck_expedition_members_hunger_range")),
        sa.CheckConstraint("stress BETWEEN 0 AND 200", name=op.f("ck_expedition_members_stress_range")),
        sa.CheckConstraint("wet BETWEEN 0 AND 100", name=op.f("ck_expedition_members_wet_range")),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], name=op.f("fk_expedition_members_expedition_id_expeditions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_expedition_members_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expedition_members")),
        sa.UniqueConstraint("expedition_id", "mortal_entity_id", name="uq_expedition_members_mortal"),
    )
    with op.batch_alter_table("expedition_members", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_expedition_members_expedition_id"), ["expedition_id"], unique=False)
        batch_op.create_index("ix_expedition_members_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "quirks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "fears_dark",
                "dark_sighted",
                "knows_ways",
                "eats_anything",
                "hardy",
                "frail",
                "jumpy",
                "steady_nerves",
                "keen_eyed",
                "homesick",
                "restless",
                "light_fingered",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("source_entity_id", sa.Integer(), nullable=True),
        sa.Column("expedition_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("gained_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("gained_epoch >= 0", name=op.f("ck_quirks_gained_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 1 AND 3", name=op.f("ck_quirks_strength_range")),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], name=op.f("fk_quirks_expedition_id_expeditions"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_quirks_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], name=op.f("fk_quirks_source_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quirks")),
        sa.UniqueConstraint("mortal_entity_id", "kind", name="uq_quirks_mortal_kind"),
    )
    with op.batch_alter_table("quirks", schema=None) as batch_op:
        batch_op.create_index("ix_quirks_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "supply_flows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("army_entity_id", sa.Integer(), nullable=False),
        sa.Column("depot_id", sa.Integer(), nullable=True),
        sa.Column("produced", sa.Integer(), nullable=False),
        sa.Column("shipped", sa.Integer(), nullable=False),
        sa.Column("lost", sa.Integer(), nullable=False),
        sa.Column("delivered", sa.Integer(), nullable=False),
        sa.Column("need", sa.Integer(), nullable=False),
        sa.Column("throughput", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("delivered >= 0", name=op.f("ck_supply_flows_delivered_min")),
        sa.CheckConstraint("lost >= 0", name=op.f("ck_supply_flows_lost_min")),
        sa.CheckConstraint("need >= 0", name=op.f("ck_supply_flows_need_min")),
        sa.CheckConstraint("produced >= 0", name=op.f("ck_supply_flows_produced_min")),
        sa.CheckConstraint("shipped >= 0", name=op.f("ck_supply_flows_shipped_min")),
        sa.CheckConstraint("throughput >= 0", name=op.f("ck_supply_flows_throughput_min")),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_supply_flows_army_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depot_id"], ["depots.id"], name=op.f("fk_supply_flows_depot_id_depots"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_supply_flows_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supply_flows")),
    )
    with op.batch_alter_table("supply_flows", schema=None) as batch_op:
        batch_op.create_index("ix_supply_flows_army", ["army_entity_id"], unique=False)
        batch_op.create_index("ix_supply_flows_owner_epoch", ["owner_entity_id", "epoch"], unique=False)

    op.create_table(
        "theatres",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column("front_region_entity_id", sa.Integer(), nullable=True),
        sa.Column("marshal_entity_id", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("believed_threat", sa.Integer(), nullable=False),
        sa.Column("true_threat", sa.Integer(), nullable=False),
        sa.Column("reserves", sa.Integer(), nullable=False),
        sa.Column("levies", sa.Integer(), nullable=False),
        sa.Column("transport", sa.Integer(), nullable=False),
        sa.Column("misjudged", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("believed_threat BETWEEN 0 AND 100", name=op.f("ck_theatres_believed_threat_range")),
        sa.CheckConstraint("levies >= 0", name=op.f("ck_theatres_levies_min")),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name=op.f("ck_theatres_priority_range")),
        sa.CheckConstraint("reserves >= 0", name=op.f("ck_theatres_reserves_min")),
        sa.CheckConstraint("transport >= 0", name=op.f("ck_theatres_transport_min")),
        sa.CheckConstraint("true_threat BETWEEN 0 AND 100", name=op.f("ck_theatres_true_threat_range")),
        sa.CheckConstraint("updated_epoch >= 0", name=op.f("ck_theatres_updated_epoch_min")),
        sa.ForeignKeyConstraint(["front_region_entity_id"], ["entities.id"], name=op.f("fk_theatres_front_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marshal_entity_id"], ["entities.id"], name=op.f("fk_theatres_marshal_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_theatres_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_theatres_war_id_wars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_theatres")),
        sa.UniqueConstraint("owner_entity_id", "war_id", name="uq_theatres_owner_war"),
    )
    with op.batch_alter_table("theatres", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_theatres_owner_entity_id"), ["owner_entity_id"], unique=False)

    op.create_table(
        "transport_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("depot_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("wagons", "pack_animals", "porters", "barges", "ships", "sky_barges", name="kind", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity >= 0", name=op.f("ck_transport_assets_capacity_min")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_transport_assets_condition_range")),
        sa.CheckConstraint("count >= 0", name=op.f("ck_transport_assets_count_min")),
        sa.ForeignKeyConstraint(["depot_id"], ["depots.id"], name=op.f("fk_transport_assets_depot_id_depots"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_transport_assets_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transport_assets")),
        sa.UniqueConstraint("owner_entity_id", "kind", name="uq_transport_assets_owner_kind"),
    )
    with op.batch_alter_table("transport_assets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_transport_assets_owner_entity_id"), ["owner_entity_id"], unique=False)

    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.add_column(sa.Column("echelon_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_army_units_echelon_id"), ["echelon_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_army_units_echelon_id_echelons"), "echelons", ["echelon_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM schemes WHERE kind = 'hide_fleet'"))
    bind.execute(sa.text("DELETE FROM treaty_clauses WHERE kind = 'fleet_limit'"))
    bind.execute(sa.text("UPDATE treaty_profiles SET kind = 'non_aggression' WHERE kind = 'naval_limit'"))
    retype(forward=False)
    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_army_units_echelon_id_echelons"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_army_units_echelon_id"))
        batch_op.drop_column("echelon_id")

    with op.batch_alter_table("transport_assets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transport_assets_owner_entity_id"))

    op.drop_table("transport_assets")
    with op.batch_alter_table("theatres", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_theatres_owner_entity_id"))

    op.drop_table("theatres")
    with op.batch_alter_table("supply_flows", schema=None) as batch_op:
        batch_op.drop_index("ix_supply_flows_owner_epoch")
        batch_op.drop_index("ix_supply_flows_army")

    op.drop_table("supply_flows")
    with op.batch_alter_table("quirks", schema=None) as batch_op:
        batch_op.drop_index("ix_quirks_mortal")

    op.drop_table("quirks")
    with op.batch_alter_table("expedition_members", schema=None) as batch_op:
        batch_op.drop_index("ix_expedition_members_mortal")
        batch_op.drop_index(batch_op.f("ix_expedition_members_expedition_id"))

    op.drop_table("expedition_members")
    with op.batch_alter_table("expedition_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_expedition_logs_expedition_id"))

    op.drop_table("expedition_logs")
    op.drop_table("ship_states")
    op.drop_table("ship_crews")
    with op.batch_alter_table("expeditions", schema=None) as batch_op:
        batch_op.drop_index("ix_expeditions_target")
        batch_op.drop_index("ix_expeditions_leader")

    op.drop_table("expeditions")
    with op.batch_alter_table("echelons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_echelons_parent_id"))
        batch_op.drop_index("ix_echelons_owner")
        batch_op.drop_index("ix_echelons_army")

    op.drop_table("echelons")
    with op.batch_alter_table("depots", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_depots_region_entity_id"))
        batch_op.drop_index("ix_depots_owner")

    op.drop_table("depots")
    op.drop_table("army_operations")
    op.drop_table("admiralties")
