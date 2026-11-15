import sqlalchemy as sa
from alembic import op

revision = "a0be25fe960c"
down_revision = "6ac942d7db59"
branch_labels = None
depends_on = None

OLD_SCENARIOS = ("doom_far", "one_faith", "lost_star", "many_worlds", "long_peace", "cosmic_power", "loyal_pantheon", "new_horizons")
NEW_SCENARIOS = (
    *OLD_SCENARIOS,
    "golden_age",
    "age_of_wonders",
    "bridge_the_galaxies",
    "age_of_learning",
    "teeming_life",
    "creators_faithful",
    "custom",
)
OLD_ACHIEVEMENTS = (
    "second_sky",
    "constellation",
    "prophecy_fulfilled",
    "return_from_death",
    "fathers_hand",
    "babel",
    "crowded_world",
    "first_prayer",
    "creators_cult",
    "interstellar_traveller",
    "saga_completed",
    "god_of_epochs",
    "ancient",
    "crowded_pantheon",
    "first_explorers",
    "sensed_world",
    "weapons_silent",
)
KEPT_ACHIEVEMENTS = tuple(key for key in OLD_ACHIEVEMENTS if key != "fathers_hand")
NEW_ACHIEVEMENTS = (
    *KEPT_ACHIEVEMENTS,
    "creators_hand",
    "peopled_skies",
    "moons_in_orbit",
    "rekindled_star",
    "many_galaxies",
    "galaxy_clusters",
    "many_dimensions",
    "rifts_opened",
    "cosmic_beings",
    "across_the_galaxies",
    "trade_between_galaxies",
    "many_kinds_of_life",
    "beasts_of_the_wild",
    "spirits_abroad",
    "species_awakened",
    "many_peoples",
    "settled_lands",
    "realms_rise",
    "empire",
    "golden_age",
    "height_of_civilization",
    "treaties_signed",
    "trade_routes",
    "many_faiths",
    "one_god_many_peoples",
    "mortal_made_divine",
    "mighty_son",
    "other_gods",
    "store_of_knowledge",
    "theories",
    "works_of_art",
    "arts",
    "legends",
    "traditions",
    "rule_of_law",
    "wonders",
    "collections",
    "heroes_returned",
    "vessels",
    "creator_at_work",
    "master_of_levers",
    "miracles",
)
METRICS = (
    "worlds",
    "inhabited_worlds",
    "moons",
    "stars",
    "reborn_stars",
    "dead_stars",
    "galaxies",
    "clusters",
    "dimensions",
    "open_rifts",
    "cosmic_beings",
    "far_voyages",
    "far_trade_routes",
    "species",
    "beasts",
    "spirits",
    "awakened_species",
    "peoples",
    "population",
    "settlements",
    "polities",
    "empires",
    "golden_ages",
    "highest_civ_tier",
    "treaties",
    "trade_routes",
    "languages",
    "cults",
    "creator_worshippers",
    "prayers_to_creator",
    "fulfilled_prophecies",
    "largest_faith",
    "ascended_mortals",
    "living_sons",
    "highest_son_level",
    "resurrections",
    "suppressed_rebellions",
    "foreign_gods",
    "knowledge",
    "theories",
    "artworks",
    "art_forms",
    "legends",
    "traditions",
    "laws",
    "wonders",
    "museums",
    "completed_sagas",
    "heroquests_won",
    "arrived_journeys",
    "discoveries",
    "sensed_worlds",
    "vessels",
    "ongoing_wars",
    "warless_peoples",
    "epoch",
    "doom_percent",
    "creator_deeds",
    "levers_used",
    "miracles",
)
TARGETS = {"doom_far": 20, "one_faith": 3, "lost_star": 1, "many_worlds": 5, "long_peace": 5, "cosmic_power": 4, "loyal_pantheon": 10, "new_horizons": 8}
POINTS = {
    "doom_far": 300,
    "one_faith": 250,
    "lost_star": 200,
    "many_worlds": 250,
    "long_peace": 200,
    "cosmic_power": 300,
    "loyal_pantheon": 250,
    "new_horizons": 250,
}


def key_type(values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name="key", native_enum=False, create_constraint=True, length=40)


def plain_type(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def upgrade() -> None:
    with op.batch_alter_table("achievements", schema=None) as batch_op:
        batch_op.alter_column(
            "key",
            existing_type=key_type(OLD_ACHIEVEMENTS),
            type_=key_type((*OLD_ACHIEVEMENTS, *NEW_ACHIEVEMENTS[len(KEPT_ACHIEVEMENTS) :])),
            existing_nullable=False,
        )
    op.execute("UPDATE achievements SET key = 'creators_hand' WHERE key = 'fathers_hand'")
    with op.batch_alter_table("achievements", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "key",
            existing_type=key_type((*OLD_ACHIEVEMENTS, *NEW_ACHIEVEMENTS[len(KEPT_ACHIEVEMENTS) :])),
            type_=key_type(NEW_ACHIEVEMENTS),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("tier", sa.Integer(), nullable=False, server_default="1"))
        batch_op.drop_constraint("pk_achievements", type_="primary")
        batch_op.create_primary_key("pk_achievements", ["key", "tier"])
        batch_op.create_check_constraint("tier_range", "tier BETWEEN 1 AND 3")

    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.drop_index("ux_scenarios_running_key", sqlite_where=sa.text("status = 'running'"))
        batch_op.alter_column("key", existing_type=key_type(OLD_SCENARIOS), type_=key_type(NEW_SCENARIOS), existing_nullable=False)
        batch_op.add_column(sa.Column("tier", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("target", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("deadline_epoch", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("held", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("metric", plain_type("metric", METRICS), nullable=True))
        batch_op.add_column(sa.Column("comparator", plain_type("comparator", ("at_least", "at_most")), nullable=True))
        batch_op.add_column(sa.Column("basis", plain_type("basis", ("total", "gained")), nullable=True))
        batch_op.add_column(sa.Column("hold_epochs", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("title", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("baseline_value", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("points", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("awarded_points", sa.Integer(), nullable=False, server_default="0"))
    for key, target in TARGETS.items():
        op.execute(sa.text("UPDATE scenarios SET target = :target, points = :points WHERE key = :key").bindparams(target=target, points=POINTS[key], key=key))
        op.execute(sa.text("UPDATE scenarios SET awarded_points = :points WHERE key = :key AND points_awarded").bindparams(points=POINTS[key], key=key))
    op.execute("UPDATE scenarios SET baseline_value = baseline_count WHERE key = 'lost_star'")
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.drop_column("baseline_count")
        batch_op.drop_column("points_awarded")
        batch_op.create_check_constraint("custom_has_measure", "key <> 'custom' OR (metric IS NOT NULL AND comparator IS NOT NULL AND basis IS NOT NULL)")
        batch_op.create_check_constraint("deadline_after_start", "deadline_epoch IS NULL OR deadline_epoch > start_epoch")
        batch_op.create_check_constraint("tier_min", "tier >= 1")
        batch_op.create_check_constraint("target_min", "target >= 0")
        batch_op.create_check_constraint("hold_epochs_min", "hold_epochs >= 0")
        batch_op.create_check_constraint("points_min", "points >= 0")
        batch_op.create_check_constraint("awarded_points_min", "awarded_points >= 0")
        batch_op.create_check_constraint("title_length", "title IS NULL OR length(title) <= 200")
        batch_op.create_index("ux_scenarios_running_key", ["key"], unique=True, sqlite_where=sa.text("status = 'running' AND key <> 'custom'"))


def downgrade() -> None:
    op.execute(
        "DELETE FROM scenarios WHERE key NOT IN ('doom_far', 'one_faith', 'lost_star', 'many_worlds', 'long_peace', 'cosmic_power', 'loyal_pantheon', 'new_horizons')"
    )
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.drop_index("ux_scenarios_running_key", sqlite_where=sa.text("status = 'running' AND key <> 'custom'"))
        batch_op.drop_constraint(op.f("ck_scenarios_custom_has_measure"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_deadline_after_start"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_tier_min"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_target_min"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_hold_epochs_min"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_points_min"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_awarded_points_min"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_title_length"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_metric"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_comparator"), type_="check")
        batch_op.drop_constraint(op.f("ck_scenarios_basis"), type_="check")
        batch_op.add_column(sa.Column("points_awarded", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("baseline_count", sa.Integer(), nullable=True))
    op.execute("UPDATE scenarios SET points_awarded = awarded_points > 0")
    op.execute("UPDATE scenarios SET baseline_count = baseline_value WHERE key = 'lost_star'")
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        for column in (
            "awarded_points",
            "points",
            "baseline_value",
            "title",
            "hold_epochs",
            "basis",
            "comparator",
            "metric",
            "held",
            "deadline_epoch",
            "target",
            "tier",
        ):
            batch_op.drop_column(column)
        batch_op.alter_column("key", existing_type=key_type(NEW_SCENARIOS), type_=key_type(OLD_SCENARIOS), existing_nullable=False)
        batch_op.create_index("ux_scenarios_running_key", ["key"], unique=True, sqlite_where=sa.text("status = 'running'"))

    op.execute(f"DELETE FROM achievements WHERE tier > 1 OR key NOT IN ({', '.join(repr(key) for key in (*KEPT_ACHIEVEMENTS, 'creators_hand'))})")
    with op.batch_alter_table("achievements", schema=None, recreate="always") as batch_op:
        batch_op.drop_constraint(op.f("ck_achievements_tier_range"), type_="check")
        batch_op.drop_constraint("pk_achievements", type_="primary")
        batch_op.create_primary_key("pk_achievements", ["key"])
        batch_op.drop_column("tier")
        batch_op.alter_column("key", existing_type=key_type(NEW_ACHIEVEMENTS), type_=key_type((*NEW_ACHIEVEMENTS, "fathers_hand")), existing_nullable=False)
    op.execute("UPDATE achievements SET key = 'fathers_hand' WHERE key = 'creators_hand'")
    with op.batch_alter_table("achievements", schema=None) as batch_op:
        batch_op.alter_column("key", existing_type=key_type((*NEW_ACHIEVEMENTS, "fathers_hand")), type_=key_type(OLD_ACHIEVEMENTS), existing_nullable=False)
