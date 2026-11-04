import sqlalchemy as sa
from alembic import op

revision = "5b1d3f7a9c21"
down_revision = "5b1d3f7a9c20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feuds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_entity_id", sa.Integer(), nullable=False),
        sa.Column("second_entity_id", sa.Integer(), nullable=False),
        sa.Column("party", sa.Enum("house", "community", name="party", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("grievance", sa.Integer(), nullable=False),
        sa.Column("generations", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum("active", "mediated", "faded", "ended", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("cause", sa.String(length=240), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("last_epoch", sa.Integer(), nullable=True),
        sa.Column("last_action", sa.String(length=120), nullable=True),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("generations >= 0", name=op.f("ck_feuds_generations_min")),
        sa.CheckConstraint("grievance BETWEEN 0 AND 100", name=op.f("ck_feuds_grievance_range")),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name=op.f("ck_feuds_intensity_range")),
        sa.ForeignKeyConstraint(["first_entity_id"], ["entities.id"], name=op.f("fk_feuds_first_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_entity_id"], ["entities.id"], name=op.f("fk_feuds_second_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feuds")),
    )
    with op.batch_alter_table("feuds", schema=None) as batch_op:
        batch_op.create_index("ix_feuds_first", ["first_entity_id"], unique=False)
        batch_op.create_index("ix_feuds_second", ["second_entity_id"], unique=False)

    op.create_table(
        "learned_tactics",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "tactic",
            sa.Enum(
                "hold_line",
                "frontal_assault",
                "double_envelopment",
                "feigned_retreat",
                "flank_cavalry",
                "missile_attrition",
                "shield_wall",
                "wedge",
                "night_raid",
                "ambush",
                "skirmish_harass",
                "river_defence",
                "siege_assault",
                name="tactic",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_learned_tactics_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "tactic", name=op.f("pk_learned_tactics")),
    )
    op.create_table(
        "unit_designs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "base_kind",
            sa.Enum(
                "levy",
                "spearmen",
                "heavy_infantry",
                "shield_wall",
                "pikemen",
                "skirmishers",
                "berserkers",
                "temple_guard",
                "slingers",
                "archers",
                "crossbowmen",
                "horse_archers",
                "javelineers",
                "light_cavalry",
                "heavy_cavalry",
                "beast_riders",
                "chariots",
                "war_beasts",
                "bound_beasts",
                "sky_mounts",
                "sappers",
                "siege_engines",
                "war_mages",
                "priests",
                "necromancers",
                "galleys",
                "longships",
                "warships",
                "fire_ships",
                "skyships",
                "golems",
                "void_spawn",
                "ghost_host",
                name="base_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "family",
            sa.Enum(
                "infantry",
                "missile",
                "mounted",
                "beast",
                "engineer",
                "magic",
                "naval",
                "exotic",
                name="family",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("melee", sa.Integer(), nullable=False),
        sa.Column("missile", sa.Integer(), nullable=False),
        sa.Column("defence", sa.Integer(), nullable=False),
        sa.Column("speed", sa.Integer(), nullable=False),
        sa.Column("mass", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column(
            "armour",
            sa.Enum("none", "hide", "padded", "mail", "scale", "plate", "enchanted", name="armour", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("shield", sa.Enum("none", "small", "large", "tower", name="shield", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("terror", sa.Integer(), nullable=False),
        sa.Column("counters_charge", sa.Boolean(), nullable=False),
        sa.Column("flying", sa.Boolean(), nullable=False),
        sa.Column(
            "social_class",
            sa.Enum(
                "farmer",
                "artisan",
                "merchant",
                "priest",
                "warrior",
                "scribe",
                "noble",
                "serf_or_slave",
                "outcast",
                "monastic",
                name="social_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("owner_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_unit_designs_cost_min")),
        sa.CheckConstraint("defence BETWEEN 0 AND 100", name=op.f("ck_unit_designs_defence_range")),
        sa.CheckConstraint("mass >= 0", name=op.f("ck_unit_designs_mass_min")),
        sa.CheckConstraint("melee BETWEEN 0 AND 100", name=op.f("ck_unit_designs_melee_range")),
        sa.CheckConstraint("missile BETWEEN 0 AND 100", name=op.f("ck_unit_designs_missile_range")),
        sa.CheckConstraint("speed >= 0", name=op.f("ck_unit_designs_speed_min")),
        sa.CheckConstraint("terror BETWEEN 0 AND 100", name=op.f("ck_unit_designs_terror_range")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_unit_designs_upkeep_min")),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_unit_designs_owner_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_unit_designs")),
    )
    op.create_table(
        "army_officers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("army_entity_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "commander", "sub_commander", "quartermaster", "standard_bearer", "surgeon", name="role", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("office_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_army_officers_army_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_army_officers_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["office_id"], ["offices.id"], name=op.f("fk_army_officers_office_id_offices"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_army_officers")),
    )
    with op.batch_alter_table("army_officers", schema=None) as batch_op:
        batch_op.create_index("ix_army_officers_army", ["army_entity_id"], unique=False)
        batch_op.create_index("ix_army_officers_mortal", ["mortal_entity_id"], unique=False)

    op.create_table(
        "mercenary_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employer_entity_id", sa.Integer(), nullable=False),
        sa.Column("company_entity_id", sa.Integer(), nullable=True),
        sa.Column("army_entity_id", sa.Integer(), nullable=True),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("soldiers", sa.Integer(), nullable=False),
        sa.Column("pay_per_season", sa.Integer(), nullable=False),
        sa.Column("seasons_left", sa.Integer(), nullable=False),
        sa.Column("loyalty", sa.Integer(), nullable=False),
        sa.Column("unpaid_seasons", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Enum("active", "unpaid", "turned", "ended", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("loyalty BETWEEN 0 AND 100", name=op.f("ck_mercenary_contracts_loyalty_range")),
        sa.CheckConstraint("pay_per_season >= 0", name=op.f("ck_mercenary_contracts_pay_per_season_min")),
        sa.CheckConstraint("seasons_left >= 0", name=op.f("ck_mercenary_contracts_seasons_left_min")),
        sa.CheckConstraint("soldiers >= 0", name=op.f("ck_mercenary_contracts_soldiers_min")),
        sa.CheckConstraint("unpaid_seasons >= 0", name=op.f("ck_mercenary_contracts_unpaid_seasons_min")),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_mercenary_contracts_army_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_entity_id"], ["entities.id"], name=op.f("fk_mercenary_contracts_company_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employer_entity_id"], ["entities.id"], name=op.f("fk_mercenary_contracts_employer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_mercenary_contracts_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mercenary_contracts")),
    )
    with op.batch_alter_table("mercenary_contracts", schema=None) as batch_op:
        batch_op.create_index("ix_mercenary_contracts_employer", ["employer_entity_id"], unique=False)

    op.create_table(
        "peace_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "cession",
                "vassalage",
                "hostage",
                "reparations",
                "tribute",
                "liberty",
                "throne",
                "break_cult",
                "open_temples",
                "government",
                "marriage",
                "demilitarised",
                "trade_concession",
                "captive_release",
                "champion",
                "white_peace",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("beneficiary_entity_id", sa.Integer(), nullable=True),
        sa.Column("obligor_entity_id", sa.Integer(), nullable=True),
        sa.Column("treaty_entity_id", sa.Integer(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=240), nullable=True),
        sa.ForeignKeyConstraint(["beneficiary_entity_id"], ["entities.id"], name=op.f("fk_peace_terms_beneficiary_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["obligor_entity_id"], ["entities.id"], name=op.f("fk_peace_terms_obligor_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["treaty_entity_id"], ["entities.id"], name=op.f("fk_peace_terms_treaty_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_peace_terms_war_id_wars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peace_terms")),
    )
    with op.batch_alter_table("peace_terms", schema=None) as batch_op:
        batch_op.create_index("ix_peace_terms_war", ["war_id"], unique=False)

    op.create_table(
        "battle_casualties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("battle_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("side_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "fate", sa.Enum("killed", "wounded", "maimed", "captured", name="fate", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("harm", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=240), nullable=True),
        sa.ForeignKeyConstraint(["battle_id"], ["battles.id"], name=op.f("fk_battle_casualties_battle_id_battles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_battle_casualties_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["side_entity_id"], ["entities.id"], name=op.f("fk_battle_casualties_side_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_battle_casualties")),
    )
    with op.batch_alter_table("battle_casualties", schema=None) as batch_op:
        batch_op.create_index("ix_battle_casualties_battle", ["battle_id"], unique=False)

    op.create_table(
        "battle_stacks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("battle_id", sa.Integer(), nullable=False),
        sa.Column("side_entity_id", sa.Integer(), nullable=False),
        sa.Column("army_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "levy",
                "spearmen",
                "heavy_infantry",
                "shield_wall",
                "pikemen",
                "skirmishers",
                "berserkers",
                "temple_guard",
                "slingers",
                "archers",
                "crossbowmen",
                "horse_archers",
                "javelineers",
                "light_cavalry",
                "heavy_cavalry",
                "beast_riders",
                "chariots",
                "war_beasts",
                "bound_beasts",
                "sky_mounts",
                "sappers",
                "siege_engines",
                "war_mages",
                "priests",
                "necromancers",
                "galleys",
                "longships",
                "warships",
                "fire_ships",
                "skyships",
                "golems",
                "void_spawn",
                "ghost_host",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("start", sa.Integer(), nullable=False),
        sa.Column("lost", sa.Integer(), nullable=False),
        sa.Column("wounded", sa.Integer(), nullable=False),
        sa.Column("routed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_battle_stacks_army_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["battle_id"], ["battles.id"], name=op.f("fk_battle_stacks_battle_id_battles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["side_entity_id"], ["entities.id"], name=op.f("fk_battle_stacks_side_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_battle_stacks")),
    )
    with op.batch_alter_table("battle_stacks", schema=None) as batch_op:
        batch_op.create_index("ix_battle_stacks_battle", ["battle_id"], unique=False)

    op.create_table(
        "spy_agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("network_id", sa.Integer(), nullable=False),
        sa.Column("mortal_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "cover", sa.Enum("merchant", "priest", "envoy", "beggar", name="cover", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("skill", sa.Integer(), nullable=False),
        sa.Column("exposure", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "caught", "turned", "dead", "retired", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("exposure BETWEEN 0 AND 100", name=op.f("ck_spy_agents_exposure_range")),
        sa.CheckConstraint("skill BETWEEN 0 AND 100", name=op.f("ck_spy_agents_skill_range")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_spy_agents_mortal_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["network_id"], ["spy_networks.id"], name=op.f("fk_spy_agents_network_id_spy_networks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_spy_agents")),
    )
    with op.batch_alter_table("spy_agents", schema=None) as batch_op:
        batch_op.create_index("ix_spy_agents_network", ["network_id"], unique=False)

    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tactic",
                sa.Enum(
                    "hold_line",
                    "frontal_assault",
                    "double_envelopment",
                    "feigned_retreat",
                    "flank_cavalry",
                    "missile_attrition",
                    "shield_wall",
                    "wedge",
                    "night_raid",
                    "ambush",
                    "skirmish_harass",
                    "river_defence",
                    "siege_assault",
                    name="tactic",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("drill", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("fodder_days", sa.Integer(), nullable=False, server_default="90"))
        batch_op.add_column(sa.Column("mutiny", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("battle_region_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_army_profiles_battle_region_id_entities"), "entities", ["battle_region_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.add_column(sa.Column("design_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(batch_op.f("fk_army_units_design_id_unit_designs"), "unit_designs", ["design_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tactic_factors", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("morale", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("magic", sa.JSON(), nullable=False, server_default="{}"))

    with op.batch_alter_table("captive_cohorts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("language_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(
            batch_op.f("fk_captive_cohorts_language_entity_id_entities"), "entities", ["language_entity_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("captives", schema=None) as batch_op:
        batch_op.add_column(sa.Column("loyalty", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("married_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(batch_op.f("fk_captives_married_entity_id_entities"), "entities", ["married_entity_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("occupations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.add_column(sa.Column("wall_material", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("relief_army_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("choice", sa.Enum("mercy", "sack", "raze", name="choice", native_enum=False, create_constraint=True, length=40), nullable=True)
        )
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(batch_op.f("fk_sieges_relief_army_id_entities"), "entities", ["relief_army_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("spy_networks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_kind",
                sa.Enum("polity", "faction", "cult", "community", name="owner_kind", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="community",
            )
        )
        batch_op.add_column(sa.Column("side_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("revealed_aims", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("warned_epoch", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(batch_op.f("fk_spy_networks_side_entity_id_entities"), "entities", ["side_entity_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "hull_class",
                sa.Enum(
                    "raft",
                    "boat",
                    "galley",
                    "longship",
                    "cog",
                    "carrack",
                    "warship",
                    "light_sailer",
                    "bone_hull",
                    "generation_ship",
                    "skyship",
                    "living_ship",
                    name="hull_class",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=False,
                server_default="boat",
            )
        )
        batch_op.add_column(sa.Column("hull_material", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("fabric_material", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("condition", sa.Integer(), nullable=False, server_default="100"))
        batch_op.add_column(sa.Column("armament", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("seaworthiness", sa.Integer(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("cargo_capacity", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("crew", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("seamanship", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("captain_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("home_port_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("crew_community_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("region_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("fleet_army_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("legend_entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("renown", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column(
                "status",
                sa.Enum("docked", "afloat", "damaged", "wrecked", "ghost", name="status", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default="docked",
            )
        )
        batch_op.add_column(sa.Column("voyages", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("updated_epoch", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key(batch_op.f("fk_vessel_profiles_region_entity_id_entities"), "entities", ["region_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_vessel_profiles_legend_entity_id_entities"), "entities", ["legend_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(
            batch_op.f("fk_vessel_profiles_fleet_army_entity_id_entities"), "entities", ["fleet_army_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_vessel_profiles_home_port_entity_id_entities"), "entities", ["home_port_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_vessel_profiles_crew_community_entity_id_entities"), "entities", ["crew_community_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(batch_op.f("fk_vessel_profiles_captain_entity_id_entities"), "entities", ["captain_entity_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("war_aims", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.add_column(sa.Column("locked", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("wars", schema=None) as batch_op:
        batch_op.drop_column("locked")

    with op.batch_alter_table("war_aims", schema=None) as batch_op:
        batch_op.drop_column("locked")

    with op.batch_alter_table("vessel_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_captain_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_crew_community_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_home_port_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_fleet_army_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_legend_entity_id_entities"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_vessel_profiles_region_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("updated_epoch")
        batch_op.drop_column("voyages")
        batch_op.drop_column("status")
        batch_op.drop_column("renown")
        batch_op.drop_column("legend_entity_id")
        batch_op.drop_column("fleet_army_entity_id")
        batch_op.drop_column("region_entity_id")
        batch_op.drop_column("crew_community_entity_id")
        batch_op.drop_column("home_port_entity_id")
        batch_op.drop_column("captain_entity_id")
        batch_op.drop_column("seamanship")
        batch_op.drop_column("crew")
        batch_op.drop_column("cargo_capacity")
        batch_op.drop_column("seaworthiness")
        batch_op.drop_column("armament")
        batch_op.drop_column("condition")
        batch_op.drop_column("fabric_material")
        batch_op.drop_column("hull_material")
        batch_op.drop_column("hull_class")

    with op.batch_alter_table("spy_networks", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_spy_networks_side_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("warned_epoch")
        batch_op.drop_column("revealed_aims")
        batch_op.drop_column("side_entity_id")
        batch_op.drop_column("owner_kind")

    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_sieges_relief_army_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("choice")
        batch_op.drop_column("relief_army_id")
        batch_op.drop_column("wall_material")

    with op.batch_alter_table("occupations", schema=None) as batch_op:
        batch_op.drop_column("locked")

    with op.batch_alter_table("captives", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_captives_married_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("married_entity_id")
        batch_op.drop_column("loyalty")

    with op.batch_alter_table("captive_cohorts", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_captive_cohorts_language_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("language_entity_id")

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.drop_column("magic")
        batch_op.drop_column("morale")
        batch_op.drop_column("tactic_factors")

    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_army_units_design_id_unit_designs"), type_="foreignkey")
        batch_op.drop_column("locked")
        batch_op.drop_column("design_id")

    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_army_profiles_battle_region_id_entities"), type_="foreignkey")
        batch_op.drop_column("battle_region_id")
        batch_op.drop_column("mutiny")
        batch_op.drop_column("fodder_days")
        batch_op.drop_column("drill")
        batch_op.drop_column("tactic")

    with op.batch_alter_table("spy_agents", schema=None) as batch_op:
        batch_op.drop_index("ix_spy_agents_network")

    op.drop_table("spy_agents")
    with op.batch_alter_table("battle_stacks", schema=None) as batch_op:
        batch_op.drop_index("ix_battle_stacks_battle")

    op.drop_table("battle_stacks")
    with op.batch_alter_table("battle_casualties", schema=None) as batch_op:
        batch_op.drop_index("ix_battle_casualties_battle")

    op.drop_table("battle_casualties")
    with op.batch_alter_table("peace_terms", schema=None) as batch_op:
        batch_op.drop_index("ix_peace_terms_war")

    op.drop_table("peace_terms")
    with op.batch_alter_table("mercenary_contracts", schema=None) as batch_op:
        batch_op.drop_index("ix_mercenary_contracts_employer")

    op.drop_table("mercenary_contracts")
    with op.batch_alter_table("army_officers", schema=None) as batch_op:
        batch_op.drop_index("ix_army_officers_mortal")
        batch_op.drop_index("ix_army_officers_army")

    op.drop_table("army_officers")
    op.drop_table("unit_designs")
    op.drop_table("learned_tactics")
    with op.batch_alter_table("feuds", schema=None) as batch_op:
        batch_op.drop_index("ix_feuds_second")
        batch_op.drop_index("ix_feuds_first")

    op.drop_table("feuds")
