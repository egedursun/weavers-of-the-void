import sqlalchemy as sa
from alembic import op

revision = "c4d0f6a8b2e3"
down_revision = "a3c9e5f7b1d2"
branch_labels = None
depends_on = None

OUTCOMES = ("field_victory", "great_victory", "siege_repulsed", "siege_breached", "siege_starvation")
CAPTIVE_STATUSES = ("held", "ransomed", "escaped", "executed", "turncoat", "rescued", "released")
WIDENED = (
    ("battles", "outcome", OUTCOMES, (*OUTCOMES, "refused"), False),
    ("captives", "status", CAPTIVE_STATUSES, (*CAPTIVE_STATUSES, "ward"), False),
)


def enum_of(name: str, values: tuple[str, ...]) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def widen(forward: bool) -> None:
    for table, column, old, new, nullable in WIDENED:
        before, after = (old, new) if forward else (new, old)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(column, before), type_=enum_of(column, after), existing_nullable=nullable)


def upgrade() -> None:
    widen(True)
    op.create_table(
        "army_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("army_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("from_region_id", sa.Integer(), nullable=True),
        sa.Column("to_region_id", sa.Integer(), nullable=True),
        sa.Column(
            "stance",
            sa.Enum(
                "march", "forage", "entrench", "besiege", "garrison", "raid", "retreat", name="stance", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("supply_days", sa.Integer(), nullable=False),
        sa.Column("attrition", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_army_movements_army_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_region_id"], ["entities.id"], name=op.f("fk_army_movements_from_region_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_region_id"], ["entities.id"], name=op.f("fk_army_movements_to_region_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_army_movements")),
    )
    with op.batch_alter_table("army_movements", schema=None) as batch_op:
        batch_op.create_index("ix_army_movements_army", ["army_entity_id", "epoch"], unique=False)

    op.create_table(
        "army_profiles",
        sa.Column("army_entity_id", sa.Integer(), nullable=False),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "stance",
            sa.Enum(
                "march", "forage", "entrench", "besiege", "garrison", "raid", "retreat", name="stance", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("doctrine", sa.String(length=120), nullable=False),
        sa.Column("supply_days", sa.Integer(), nullable=False),
        sa.Column("supply_line", sa.JSON(), nullable=False),
        sa.Column("cohesion", sa.Integer(), nullable=False),
        sa.Column("war_chest", sa.Integer(), nullable=False),
        sa.Column("disease", sa.Integer(), nullable=False),
        sa.Column("loot", sa.Integer(), nullable=False),
        sa.Column("entrenchment", sa.Integer(), nullable=False),
        sa.Column("forced_march", sa.Boolean(), nullable=False),
        sa.Column("baggage", sa.Integer(), nullable=False),
        sa.Column("blockade_entity_id", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cohesion BETWEEN 0 AND 100", name=op.f("ck_army_profiles_cohesion_range")),
        sa.CheckConstraint("disease BETWEEN 0 AND 100", name=op.f("ck_army_profiles_disease_range")),
        sa.CheckConstraint("entrenchment BETWEEN 0 AND 100", name=op.f("ck_army_profiles_entrenchment_range")),
        sa.CheckConstraint("loot >= 0", name=op.f("ck_army_profiles_loot_min")),
        sa.CheckConstraint("supply_days >= 0", name=op.f("ck_army_profiles_supply_days_min")),
        sa.CheckConstraint("war_chest >= 0", name=op.f("ck_army_profiles_war_chest_min")),
        sa.ForeignKeyConstraint(["blockade_entity_id"], ["entities.id"], name=op.f("fk_army_profiles_blockade_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_army_profiles_army_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_army_profiles_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_army_profiles_target_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("army_entity_id", name=op.f("pk_army_profiles")),
    )
    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_army_profiles_region_entity_id"), ["region_entity_id"], unique=False)

    op.create_table(
        "army_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("army_entity_id", sa.Integer(), nullable=False),
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
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column(
            "armour",
            sa.Enum("none", "hide", "padded", "mail", "scale", "plate", "enchanted", name="armour", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("shield", sa.Enum("none", "small", "large", "tower", name="shield", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("helmet", sa.Boolean(), nullable=False),
        sa.Column("weapons", sa.JSON(), nullable=False),
        sa.Column("material", sa.String(length=120), nullable=True),
        sa.Column("experience", sa.Integer(), nullable=False),
        sa.Column("morale", sa.Integer(), nullable=False),
        sa.Column("fatigue", sa.Integer(), nullable=False),
        sa.Column("wounded", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
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
        sa.Column("origin_entity_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_army_units_condition_range")),
        sa.CheckConstraint("count >= 0", name=op.f("ck_army_units_count_min")),
        sa.CheckConstraint("experience BETWEEN 0 AND 100", name=op.f("ck_army_units_experience_range")),
        sa.CheckConstraint("fatigue BETWEEN 0 AND 100", name=op.f("ck_army_units_fatigue_range")),
        sa.CheckConstraint("morale BETWEEN 0 AND 100", name=op.f("ck_army_units_morale_range")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_army_units_quality_range")),
        sa.CheckConstraint("wounded >= 0", name=op.f("ck_army_units_wounded_min")),
        sa.ForeignKeyConstraint(["army_entity_id"], ["entities.id"], name=op.f("fk_army_units_army_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_entity_id"], ["entities.id"], name=op.f("fk_army_units_origin_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_army_units")),
    )
    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.create_index("ix_army_units_army", ["army_entity_id"], unique=False)

    op.create_table(
        "commander_traits",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "trait",
            sa.Enum(
                "aggressive_assaulter",
                "defensive_genius",
                "cavalry_master",
                "winter_campaigner",
                "hill_fighter",
                "siege_expert",
                "reckless",
                "cautious",
                "inspiring",
                "brutal",
                name="trait",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_commander_traits_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mortal_entity_id", "trait", name=op.f("pk_commander_traits")),
    )
    op.create_table(
        "campaign_fronts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column("first_region_id", sa.Integer(), nullable=False),
        sa.Column("second_region_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("last_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["first_region_id"], ["entities.id"], name=op.f("fk_campaign_fronts_first_region_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["second_region_id"], ["entities.id"], name=op.f("fk_campaign_fronts_second_region_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_campaign_fronts_war_id_wars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_fronts")),
    )
    with op.batch_alter_table("campaign_fronts", schema=None) as batch_op:
        batch_op.create_index("ix_campaign_fronts_war", ["war_id"], unique=False)

    op.create_table(
        "captive_cohorts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("captor_entity_id", sa.Integer(), nullable=False),
        sa.Column("origin_entity_id", sa.Integer(), nullable=True),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
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
            nullable=False,
        ),
        sa.Column(
            "condition",
            sa.Enum("none", "veteran", "sick", "enslaved", "captive", name="condition", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "fate",
            sa.Enum(
                "held",
                "ransomed",
                "enslaved",
                "sacrificed",
                "labour",
                "exchanged",
                "released",
                name="fate",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("settled_epoch", sa.Integer(), nullable=True),
        sa.CheckConstraint("count >= 0", name=op.f("ck_captive_cohorts_count_min")),
        sa.ForeignKeyConstraint(["captor_entity_id"], ["entities.id"], name=op.f("fk_captive_cohorts_captor_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_entity_id"], ["entities.id"], name=op.f("fk_captive_cohorts_origin_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_captive_cohorts_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_captive_cohorts")),
    )
    with op.batch_alter_table("captive_cohorts", schema=None) as batch_op:
        batch_op.create_index("ix_captive_cohorts_captor", ["captor_entity_id"], unique=False)

    op.create_table(
        "occupations",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("occupier_entity_id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("control", sa.Integer(), nullable=False),
        sa.Column("resistance", sa.Integer(), nullable=False),
        sa.CheckConstraint("control BETWEEN 0 AND 100", name=op.f("ck_occupations_control_range")),
        sa.CheckConstraint("resistance BETWEEN 0 AND 100", name=op.f("ck_occupations_resistance_range")),
        sa.ForeignKeyConstraint(["occupier_entity_id"], ["entities.id"], name=op.f("fk_occupations_occupier_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_occupations_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_occupations_war_id_wars"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_occupations")),
    )
    with op.batch_alter_table("occupations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_occupations_occupier_entity_id"), ["occupier_entity_id"], unique=False)

    op.create_table(
        "war_aims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("war_id", sa.Integer(), nullable=False),
        sa.Column("side_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "conquer_region",
                "seize_settlement",
                "press_claim",
                "convert",
                "tribute",
                "vassalise",
                "liberate",
                "destroy_cult",
                "seize_resource",
                "seize_nexus",
                "humiliate",
                "revenge",
                "loot",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("achieved", sa.Integer(), nullable=False),
        sa.CheckConstraint("achieved BETWEEN 0 AND 100", name=op.f("ck_war_aims_achieved_range")),
        sa.ForeignKeyConstraint(["side_entity_id"], ["entities.id"], name=op.f("fk_war_aims_side_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_war_aims_target_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["war_id"], ["wars.id"], name=op.f("fk_war_aims_war_id_wars"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_war_aims")),
    )
    with op.batch_alter_table("war_aims", schema=None) as batch_op:
        batch_op.create_index("ix_war_aims_war", ["war_id"], unique=False)

    op.create_table(
        "spy_networks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=False),
        sa.Column("agents", sa.Integer(), nullable=False),
        sa.Column("agent_ids", sa.JSON(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("exposure", sa.Integer(), nullable=False),
        sa.Column(
            "cover", sa.Enum("merchant", "priest", "envoy", "beggar", name="cover", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("spymaster_entity_id", sa.Integer(), nullable=True),
        sa.Column("bond_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("last_operation", sa.String(length=120), nullable=True),
        sa.Column("last_epoch", sa.Integer(), nullable=True),
        sa.Column("intel", sa.Integer(), nullable=False),
        sa.CheckConstraint("agents >= 0", name=op.f("ck_spy_networks_agents_min")),
        sa.CheckConstraint("depth BETWEEN 0 AND 100", name=op.f("ck_spy_networks_depth_range")),
        sa.CheckConstraint("exposure BETWEEN 0 AND 100", name=op.f("ck_spy_networks_exposure_range")),
        sa.ForeignKeyConstraint(["bond_id"], ["bonds.id"], name=op.f("fk_spy_networks_bond_id_bonds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_spy_networks_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spymaster_entity_id"], ["entities.id"], name=op.f("fk_spy_networks_spymaster_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], name=op.f("fk_spy_networks_target_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_spy_networks")),
    )
    with op.batch_alter_table("spy_networks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_spy_networks_owner_entity_id"), ["owner_entity_id"], unique=False)
        batch_op.create_index("ix_spy_networks_target", ["target_entity_id"], unique=False)

    op.create_table(
        "battle_phases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("battle_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=120), nullable=False),
        sa.Column("attacker_losses", sa.Integer(), nullable=False),
        sa.Column("defender_losses", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=480), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["battle_id"], ["battles.id"], name=op.f("fk_battle_phases_battle_id_battles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_battle_phases")),
    )
    with op.batch_alter_table("battle_phases", schema=None) as batch_op:
        batch_op.create_index("ix_battle_phases_battle", ["battle_id"], unique=False)

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tactics_attacker",
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
                    name="tactics_attacker",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "tactics_defender",
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
                    name="tactics_defender",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "outcome_class",
                sa.Enum(
                    "decisive",
                    "victory",
                    "pyrrhic",
                    "stalemate",
                    "rout",
                    "massacre",
                    "refused",
                    name="outcome_class",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("casualties_by_kind", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("winner_losses", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("loser_losses", sa.Integer(), nullable=False, server_default=sa.text("'0'")))

    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.add_column(sa.Column("walls_level", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("breaches", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("supplies", sa.Integer(), nullable=False, server_default=sa.text("'180'")))
        batch_op.add_column(sa.Column("water", sa.Integer(), nullable=False, server_default=sa.text("'120'")))
        batch_op.add_column(sa.Column("disease_inside", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("disease_outside", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(sa.Column("works", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("sallies", sa.Integer(), nullable=False, server_default=sa.text("'0'")))
        batch_op.add_column(
            sa.Column(
                "starvation",
                sa.Enum("none", "rationing", "famine", "taboo_broken", name="starvation", native_enum=False, create_constraint=True, length=40),
                nullable=False,
                server_default=sa.text("'none'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_action",
                sa.Enum("blockade", "bombard", "mine", "assault", "negotiate", name="last_action", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_defence",
                sa.Enum("sally", "repair", "ration", "seek_relief", name="last_defence", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )

    with op.batch_alter_table("war_sides", schema=None) as batch_op:
        batch_op.add_column(sa.Column("weariness", sa.Integer(), nullable=False, server_default=sa.text("'0'")))


def downgrade() -> None:
    with op.batch_alter_table("war_sides", schema=None) as batch_op:
        batch_op.drop_column("weariness")

    with op.batch_alter_table("sieges", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_sieges_last_defence"), type_="check")
        batch_op.drop_constraint(op.f("ck_sieges_last_action"), type_="check")
        batch_op.drop_constraint(op.f("ck_sieges_starvation"), type_="check")
        batch_op.drop_column("last_defence")
        batch_op.drop_column("last_action")
        batch_op.drop_column("starvation")
        batch_op.drop_column("sallies")
        batch_op.drop_column("works")
        batch_op.drop_column("disease_outside")
        batch_op.drop_column("disease_inside")
        batch_op.drop_column("water")
        batch_op.drop_column("supplies")
        batch_op.drop_column("breaches")
        batch_op.drop_column("walls_level")

    with op.batch_alter_table("battles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_battles_outcome_class"), type_="check")
        batch_op.drop_constraint(op.f("ck_battles_tactics_defender"), type_="check")
        batch_op.drop_constraint(op.f("ck_battles_tactics_attacker"), type_="check")
        batch_op.drop_column("loser_losses")
        batch_op.drop_column("winner_losses")
        batch_op.drop_column("casualties_by_kind")
        batch_op.drop_column("outcome_class")
        batch_op.drop_column("tactics_defender")
        batch_op.drop_column("tactics_attacker")

    with op.batch_alter_table("battle_phases", schema=None) as batch_op:
        batch_op.drop_index("ix_battle_phases_battle")

    op.drop_table("battle_phases")
    with op.batch_alter_table("spy_networks", schema=None) as batch_op:
        batch_op.drop_index("ix_spy_networks_target")
        batch_op.drop_index(batch_op.f("ix_spy_networks_owner_entity_id"))

    op.drop_table("spy_networks")
    with op.batch_alter_table("war_aims", schema=None) as batch_op:
        batch_op.drop_index("ix_war_aims_war")

    op.drop_table("war_aims")
    with op.batch_alter_table("occupations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_occupations_occupier_entity_id"))

    op.drop_table("occupations")
    with op.batch_alter_table("captive_cohorts", schema=None) as batch_op:
        batch_op.drop_index("ix_captive_cohorts_captor")

    op.drop_table("captive_cohorts")
    with op.batch_alter_table("campaign_fronts", schema=None) as batch_op:
        batch_op.drop_index("ix_campaign_fronts_war")

    op.drop_table("campaign_fronts")
    op.drop_table("commander_traits")
    with op.batch_alter_table("army_units", schema=None) as batch_op:
        batch_op.drop_index("ix_army_units_army")

    op.drop_table("army_units")
    with op.batch_alter_table("army_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_army_profiles_region_entity_id"))

    op.drop_table("army_profiles")
    with op.batch_alter_table("army_movements", schema=None) as batch_op:
        batch_op.drop_index("ix_army_movements_army")

    op.drop_table("army_movements")
    widen(False)
