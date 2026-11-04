import sqlalchemy as sa
from alembic import op

revision = "e3c5a7b9d1f2"
down_revision = "d7f9b1c3e5a8"
branch_labels = None
depends_on = None

OLD_TREASURY_ENTRIES = ("tax", "tolls", "investment", "garrison", "walls", "building", "festival", "alms", "fire", "plunder", "grant", "loan")
NEW_TREASURY_ENTRIES = (*OLD_TREASURY_ENTRIES, "upkeep")
WIDENED = (
    ("settlement_treasury", "entry", OLD_TREASURY_ENTRIES, NEW_TREASURY_ENTRIES, False),
    ("polity_treasury", "entry", OLD_TREASURY_ENTRIES, NEW_TREASURY_ENTRIES, False),
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
        "structure_designs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "base_kind",
            sa.Enum(
                "temple",
                "shrine",
                "monastery",
                "necropolis",
                "library",
                "school",
                "observatory",
                "academy",
                "hospital",
                "wall",
                "gate",
                "tower",
                "citadel",
                "watchtower",
                "fort",
                "palace",
                "court",
                "prison",
                "market",
                "harbour",
                "warehouse",
                "granary",
                "caravanserai",
                "bank",
                "forge",
                "mill",
                "tannery",
                "mine",
                "quarry",
                "shipyard",
                "workshop",
                "alchemist_lab",
                "road",
                "bridge",
                "aqueduct",
                "sewer",
                "canal",
                "irrigation",
                "dam",
                "monument",
                "tomb",
                "arena",
                "theatre",
                "wonder",
                "cosmic_gate",
                "cosmic_archive",
                name="base_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "staff_class",
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
                name="staff_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "staff_scale", sa.Enum("none", "few", "some", "many", name="staff_scale", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("scale", sa.Enum("minor", "major", "grand", "wonder", name="scale", native_enum=False, create_constraint=True, length=40), nullable=True),
        sa.Column(
            "upkeep_commodity",
            sa.Enum(
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
                name="upkeep_commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "min_tier",
            sa.Enum("hamlet", "village", "town", "city", "metropolis", name="min_tier", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("ley", sa.Boolean(), nullable=True),
        sa.Column("capacity_pct", sa.Integer(), nullable=False),
        sa.Column("cost_pct", sa.Integer(), nullable=False),
        sa.Column("upkeep_pct", sa.Integer(), nullable=False),
        sa.Column("function_pct", sa.Integer(), nullable=False),
        sa.Column("staff_pct", sa.Integer(), nullable=False),
        sa.Column("creator_son_id", sa.Integer(), nullable=True),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity_pct BETWEEN 0 AND 1000", name=op.f("ck_structure_designs_capacity_pct_range")),
        sa.CheckConstraint("cost_pct BETWEEN 1 AND 1000", name=op.f("ck_structure_designs_cost_pct_range")),
        sa.CheckConstraint("function_pct BETWEEN 0 AND 300", name=op.f("ck_structure_designs_function_pct_range")),
        sa.CheckConstraint("staff_pct BETWEEN 0 AND 1000", name=op.f("ck_structure_designs_staff_pct_range")),
        sa.CheckConstraint("upkeep_pct BETWEEN 0 AND 1000", name=op.f("ck_structure_designs_upkeep_pct_range")),
        sa.ForeignKeyConstraint(["creator_son_id"], ["sons.id"], name=op.f("fk_structure_designs_creator_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_structure_designs_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_structure_designs")),
    )
    with op.batch_alter_table("structure_designs", schema=None) as batch_op:
        batch_op.create_index("ix_structure_designs_world", ["world_id"], unique=False)

    op.create_table(
        "constructions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column("site_entity_id", sa.Integer(), nullable=True),
        sa.Column("builder_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "temple",
                "shrine",
                "monastery",
                "necropolis",
                "library",
                "school",
                "observatory",
                "academy",
                "hospital",
                "wall",
                "gate",
                "tower",
                "citadel",
                "watchtower",
                "fort",
                "palace",
                "court",
                "prison",
                "market",
                "harbour",
                "warehouse",
                "granary",
                "caravanserai",
                "bank",
                "forge",
                "mill",
                "tannery",
                "mine",
                "quarry",
                "shipyard",
                "workshop",
                "alchemist_lab",
                "road",
                "bridge",
                "aqueduct",
                "sewer",
                "canal",
                "irrigation",
                "dam",
                "monument",
                "tomb",
                "arena",
                "theatre",
                "wonder",
                "cosmic_gate",
                "cosmic_archive",
                name="structure_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("design_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("active", "finished", "abandoned", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("funds", sa.Integer(), nullable=False),
        sa.Column("workers", sa.Integer(), nullable=False),
        sa.Column("materials_pct", sa.Integer(), nullable=False),
        sa.Column("stalled_epochs", sa.Integer(), nullable=False),
        sa.Column("generations", sa.Integer(), nullable=False),
        sa.Column("player", sa.Boolean(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("finished_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost >= 1", name=op.f("ck_constructions_cost_min")),
        sa.CheckConstraint("funds >= 0", name=op.f("ck_constructions_funds_min")),
        sa.CheckConstraint("generations >= 0", name=op.f("ck_constructions_generations_min")),
        sa.CheckConstraint("materials_pct BETWEEN 0 AND 100", name=op.f("ck_constructions_materials_pct_range")),
        sa.CheckConstraint("progress >= 0", name=op.f("ck_constructions_progress_min")),
        sa.CheckConstraint("stalled_epochs >= 0", name=op.f("ck_constructions_stalled_epochs_min")),
        sa.CheckConstraint("workers >= 0", name=op.f("ck_constructions_workers_min")),
        sa.ForeignKeyConstraint(["builder_entity_id"], ["nodes.id"], name=op.f("fk_constructions_builder_entity_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["design_id"], ["structure_designs.id"], name=op.f("fk_constructions_design_id_structure_designs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_entity_id"], ["entities.id"], name=op.f("fk_constructions_site_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_constructions_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_constructions")),
    )
    with op.batch_alter_table("constructions", schema=None) as batch_op:
        batch_op.create_index("ix_constructions_site", ["site_entity_id"], unique=False)
        batch_op.create_index("ix_constructions_structure", ["structure_entity_id"], unique=False)

    op.create_table(
        "structure_profiles",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "temple",
                "shrine",
                "monastery",
                "necropolis",
                "library",
                "school",
                "observatory",
                "academy",
                "hospital",
                "wall",
                "gate",
                "tower",
                "citadel",
                "watchtower",
                "fort",
                "palace",
                "court",
                "prison",
                "market",
                "harbour",
                "warehouse",
                "granary",
                "caravanserai",
                "bank",
                "forge",
                "mill",
                "tannery",
                "mine",
                "quarry",
                "shipyard",
                "workshop",
                "alchemist_lab",
                "road",
                "bridge",
                "aqueduct",
                "sewer",
                "canal",
                "irrigation",
                "dam",
                "monument",
                "tomb",
                "arena",
                "theatre",
                "wonder",
                "cosmic_gate",
                "cosmic_archive",
                name="structure_kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("design_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Integer(), nullable=False),
        sa.Column(
            "construction_state",
            sa.Enum("planned", "building", "complete", "damaged", "ruined", name="construction_state", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("fire_resistance", sa.Integer(), nullable=False),
        sa.Column("host_entity_id", sa.Integer(), nullable=True),
        sa.Column("builder_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "builder_kind",
            sa.Enum("community", "polity", "faction", "cult", "patron", "god", name="builder_kind", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column("architect_entity_id", sa.Integer(), nullable=True),
        sa.Column("dedicated_son_id", sa.Integer(), nullable=True),
        sa.Column(
            "aesthetic",
            sa.Enum(
                "austere", "ornate", "geometric", "natural", "macabre", "celestial", name="aesthetic", native_enum=False, create_constraint=True, length=40
            ),
            nullable=True,
        ),
        sa.Column("on_ley_line", sa.Boolean(), nullable=False),
        sa.Column("anchor", sa.Boolean(), nullable=False),
        sa.Column("effect_pct", sa.Integer(), nullable=False),
        sa.Column("staff_pct", sa.Integer(), nullable=False),
        sa.Column("upkeep_coin", sa.Integer(), nullable=False),
        sa.Column("upkeep_goods", sa.Integer(), nullable=False),
        sa.Column("unpaid_epochs", sa.Integer(), nullable=False),
        sa.Column("built_epoch", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("capacity >= 0", name=op.f("ck_structure_profiles_capacity_min")),
        sa.CheckConstraint("condition BETWEEN 0 AND 100", name=op.f("ck_structure_profiles_condition_range")),
        sa.CheckConstraint("effect_pct BETWEEN 0 AND 100", name=op.f("ck_structure_profiles_effect_pct_range")),
        sa.CheckConstraint("fire_resistance BETWEEN 0 AND 100", name=op.f("ck_structure_profiles_fire_resistance_range")),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name=op.f("ck_structure_profiles_level_range")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_structure_profiles_progress_range")),
        sa.CheckConstraint("staff_pct BETWEEN 0 AND 100", name=op.f("ck_structure_profiles_staff_pct_range")),
        sa.CheckConstraint("unpaid_epochs >= 0", name=op.f("ck_structure_profiles_unpaid_epochs_min")),
        sa.CheckConstraint("upkeep_coin >= 0", name=op.f("ck_structure_profiles_upkeep_coin_min")),
        sa.CheckConstraint("upkeep_goods >= 0", name=op.f("ck_structure_profiles_upkeep_goods_min")),
        sa.ForeignKeyConstraint(["architect_entity_id"], ["entities.id"], name=op.f("fk_structure_profiles_architect_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["builder_entity_id"], ["nodes.id"], name=op.f("fk_structure_profiles_builder_entity_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dedicated_son_id"], ["sons.id"], name=op.f("fk_structure_profiles_dedicated_son_id_sons"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["design_id"], ["structure_designs.id"], name=op.f("fk_structure_profiles_design_id_structure_designs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_entity_id"], ["entities.id"], name=op.f("fk_structure_profiles_host_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_structure_profiles_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", name=op.f("pk_structure_profiles")),
    )
    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.create_index("ix_structure_profiles_host", ["host_entity_id"], unique=False)
        batch_op.create_index("ix_structure_profiles_kind", ["kind"], unique=False)

    op.create_table(
        "structure_staff",
        sa.Column("structure_entity_id", sa.Integer(), nullable=False),
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
        sa.Column("community_entity_id", sa.Integer(), nullable=True),
        sa.Column("required", sa.Integer(), nullable=False),
        sa.Column("allocated", sa.Integer(), nullable=False),
        sa.Column("held", sa.Boolean(), nullable=False),
        sa.CheckConstraint("allocated >= 0", name=op.f("ck_structure_staff_allocated_min")),
        sa.CheckConstraint("required >= 0", name=op.f("ck_structure_staff_required_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_structure_staff_community_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["structure_entity_id"], ["entities.id"], name=op.f("fk_structure_staff_structure_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("structure_entity_id", "social_class", name=op.f("pk_structure_staff")),
    )
    with op.batch_alter_table("structure_staff", schema=None) as batch_op:
        batch_op.create_index("ix_structure_staff_community", ["community_entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("structure_staff", schema=None) as batch_op:
        batch_op.drop_index("ix_structure_staff_community")

    op.drop_table("structure_staff")
    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_structure_profiles_kind")
        batch_op.drop_index("ix_structure_profiles_host")

    op.drop_table("structure_profiles")
    with op.batch_alter_table("constructions", schema=None) as batch_op:
        batch_op.drop_index("ix_constructions_structure")
        batch_op.drop_index("ix_constructions_site")

    op.drop_table("constructions")
    with op.batch_alter_table("structure_designs", schema=None) as batch_op:
        batch_op.drop_index("ix_structure_designs_world")

    op.drop_table("structure_designs")
    widen(False)
