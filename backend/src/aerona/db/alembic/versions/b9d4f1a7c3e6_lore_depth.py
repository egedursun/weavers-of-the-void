import sqlalchemy as sa
from alembic import op

revision = "b9d4f1a7c3e6"
down_revision = "a7c3e9d1f5b2"
branch_labels = None
depends_on = None

OLD_DEEDS = ("made", "owned", "kill", "battle", "coronation", "lost", "theft", "burial", "broken", "repaired", "enchanted")
NEW_DEEDS = (*OLD_DEEDS, "given", "captured")
SLOTS = ", ".join(f"'{slot}'" for slot in ("sowing", "harvest", "midwinter", "campaign", "holy_day"))


def deeds(old: tuple[str, ...], new: tuple[str, ...]) -> None:
    with op.batch_alter_table("item_history", schema=None) as batch_op:
        batch_op.alter_column(
            "deed",
            existing_type=sa.Enum(*old, name="deed", native_enum=False, create_constraint=True, length=40),
            type_=sa.Enum(*new, name="deed", native_enum=False, create_constraint=True, length=40),
            existing_nullable=False,
        )


def upgrade() -> None:
    deeds(OLD_DEEDS, NEW_DEEDS)
    op.create_table(
        "custom_kinds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column(
            "catalog",
            sa.Enum(
                "technique",
                "tenet",
                "tradition_kind",
                "archetype",
                "item_class",
                "rite_effect",
                name="catalog",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("base", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=480), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_custom_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_custom_kinds")),
    )
    with op.batch_alter_table("custom_kinds", schema=None) as batch_op:
        batch_op.create_index("ix_custom_kinds_catalog", ["catalog", "base"], unique=False)
        batch_op.create_index(batch_op.f("ix_custom_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "holder_custom_techniques",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("secret", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_holder_custom_techniques_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kind_id"], ["custom_kinds.id"], name=op.f("fk_holder_custom_techniques_kind_id_custom_kinds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "kind_id", name=op.f("pk_holder_custom_techniques")),
    )
    with op.batch_alter_table("holder_custom_techniques", schema=None) as batch_op:
        batch_op.create_index("ix_holder_custom_techniques_kind", ["kind_id"], unique=False)

    op.create_table(
        "ideology_custom_tenets",
        sa.Column("ideology_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ideology_entity_id"], ["entities.id"], name=op.f("fk_ideology_custom_tenets_ideology_entity_id_entities"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["kind_id"], ["custom_kinds.id"], name=op.f("fk_ideology_custom_tenets_kind_id_custom_kinds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ideology_entity_id", "kind_id", name=op.f("pk_ideology_custom_tenets")),
    )
    op.create_table(
        "language_registers",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "register", sa.Enum("court", "common", "liturgical", "trade", name="register", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("language_entity_id", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_language_registers_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_entity_id"], ["entities.id"], name=op.f("fk_language_registers_language_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "register", name=op.f("pk_language_registers")),
    )
    with op.batch_alter_table("language_registers", schema=None) as batch_op:
        batch_op.create_index("ix_language_registers_language", ["language_entity_id"], unique=False)

    op.create_table(
        "research_progress",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "technique",
            sa.Enum(
                "phalanx_drill",
                "horse_archery",
                "siegecraft",
                "fortification",
                "logistics",
                "herbalism",
                "surgery",
                "amputation",
                "prosthetics",
                "quarantine",
                "inoculation",
                "irrigation",
                "crop_rotation",
                "terracing",
                "plough",
                "selective_breeding",
                "bronze",
                "iron",
                "steel",
                "skysteel",
                "arch",
                "dome",
                "aqueduct",
                "fortress",
                "alphabet",
                "paper",
                "printing",
                "calendar",
                "navigation_stars",
                "eclipse_prediction",
                "sailing",
                "shipwrighting",
                "coinage",
                "banking",
                "warding",
                "summoning",
                "sky_sailing",
                "necromancy",
                "alchemy",
                "astronomy_instruments",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_research_progress_progress_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_research_progress_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_entity_id", "technique", name=op.f("pk_research_progress")),
    )
    op.create_table(
        "tradition_effects",
        sa.Column("tradition_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "effect",
            sa.Enum(
                "cohesion",
                "satisfaction",
                "piety",
                "value",
                "fertility",
                "martial",
                "placation",
                "harvest",
                "safety",
                "food_saved",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target", sa.String(length=120), nullable=False),
        sa.Column("magnitude", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tradition_entity_id"], ["entities.id"], name=op.f("fk_tradition_effects_tradition_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tradition_entity_id", "effect", "target", name=op.f("pk_tradition_effects")),
    )
    op.create_table(
        "rumours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("carrier_entity_id", sa.Integer(), nullable=False),
        sa.Column("source_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "channel",
            sa.Enum("witness", "route", "pilgrimage", "journey", "spy", "planted", name="channel", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("fidelity", sa.Integer(), nullable=False),
        sa.Column("hops", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("lingered", sa.Integer(), nullable=False),
        sa.Column("acted", sa.Boolean(), nullable=False),
        sa.Column("legend_entity_id", sa.Integer(), nullable=True),
        sa.Column("planted", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fidelity BETWEEN 0 AND 100", name=op.f("ck_rumours_fidelity_range")),
        sa.CheckConstraint("hops >= 0", name=op.f("ck_rumours_hops_min")),
        sa.CheckConstraint("lingered >= 0", name=op.f("ck_rumours_lingered_min")),
        sa.ForeignKeyConstraint(["carrier_entity_id"], ["entities.id"], name=op.f("fk_rumours_carrier_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_rumours_incident_id_incidents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["legend_entity_id"], ["entities.id"], name=op.f("fk_rumours_legend_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], name=op.f("fk_rumours_source_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rumours")),
        sa.UniqueConstraint("incident_id", "carrier_entity_id", name="one_rumour_per_carrier"),
    )
    with op.batch_alter_table("rumours", schema=None) as batch_op:
        batch_op.create_index("ix_rumours_carrier", ["carrier_entity_id"], unique=False)
        batch_op.create_index("ix_rumours_epoch", ["epoch"], unique=False)

    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("canon", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("rite_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("forbidden_by", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("custom_class_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("secondary_materials", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(sa.Column("bound_spirit_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_item_profiles_bound_spirit_entity_id_entities"), "entities", ["bound_spirit_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_item_profiles_custom_class_id_custom_kinds"), "custom_kinds", ["custom_class_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("legend_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("custom_archetype_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_legend_profiles_custom_archetype_id_custom_kinds"), "custom_kinds", ["custom_archetype_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("prophecy_conditions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "consequence_kind",
                sa.Enum("rule", "fall", "death", "war", "birth", "omen", name="consequence_kind", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("consequence_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_prophecy_conditions_consequence_entity_id_entities"), "entities", ["consequence_entity_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.drop_column("consequence")

    with op.batch_alter_table("rite_effects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "damage_type",
                sa.Enum(
                    "cut",
                    "pierce",
                    "blunt",
                    "fire",
                    "cold",
                    "venom",
                    "magic",
                    "void",
                    "holy",
                    name="damage_type",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "summon_form", sa.Enum("spirit", "beast", "undead", name="summon_form", native_enum=False, create_constraint=True, length=40), nullable=True
            )
        )
        batch_op.add_column(sa.Column("custom_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_rite_effects_custom_kind_id_custom_kinds"), "custom_kinds", ["custom_kind_id"], ["id"], ondelete="SET NULL")

    op.execute(sa.text(f"UPDATE tradition_profiles SET calendar_slot = NULL WHERE calendar_slot NOT IN ({SLOTS})"))
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("custom_kind_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "taboo_act",
                sa.Enum(
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
                    name="taboo_act",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.alter_column(
            "calendar_slot",
            existing_type=sa.VARCHAR(length=120),
            type_=sa.Enum("sowing", "harvest", "midwinter", "campaign", "holy_day", name="calendar_slot", native_enum=False, create_constraint=True, length=40),
            existing_nullable=True,
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_tradition_profiles_custom_kind_id_custom_kinds"), "custom_kinds", ["custom_kind_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_tradition_profiles_custom_kind_id_custom_kinds"), type_="foreignkey")
        batch_op.alter_column(
            "calendar_slot",
            existing_type=sa.Enum(
                "sowing", "harvest", "midwinter", "campaign", "holy_day", name="calendar_slot", native_enum=False, create_constraint=True, length=40
            ),
            type_=sa.VARCHAR(length=120),
            existing_nullable=True,
        )
        batch_op.drop_column("taboo_act")
        batch_op.drop_column("custom_kind_id")

    with op.batch_alter_table("rite_effects", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_rite_effects_custom_kind_id_custom_kinds"), type_="foreignkey")
        batch_op.drop_column("custom_kind_id")
        batch_op.drop_column("summon_form")
        batch_op.drop_column("damage_type")

    with op.batch_alter_table("prophecy_conditions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("consequence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.drop_constraint(batch_op.f("fk_prophecy_conditions_consequence_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("consequence_entity_id")
        batch_op.drop_column("consequence_kind")

    with op.batch_alter_table("legend_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_legend_profiles_custom_archetype_id_custom_kinds"), type_="foreignkey")
        batch_op.drop_column("custom_archetype_id")

    with op.batch_alter_table("artwork_profiles", schema=None) as batch_op:
        batch_op.drop_column("canon")

    with op.batch_alter_table("rite_profiles", schema=None) as batch_op:
        batch_op.drop_column("forbidden_by")

    with op.batch_alter_table("item_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_item_profiles_custom_class_id_custom_kinds"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_item_profiles_bound_spirit_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("bound_spirit_entity_id")
        batch_op.drop_column("secondary_materials")
        batch_op.drop_column("custom_class_id")

    with op.batch_alter_table("rumours", schema=None) as batch_op:
        batch_op.drop_index("ix_rumours_epoch")
        batch_op.drop_index("ix_rumours_carrier")

    op.drop_table("rumours")
    op.drop_table("tradition_effects")
    op.drop_table("research_progress")
    with op.batch_alter_table("language_registers", schema=None) as batch_op:
        batch_op.drop_index("ix_language_registers_language")

    op.drop_table("language_registers")
    op.drop_table("ideology_custom_tenets")
    with op.batch_alter_table("holder_custom_techniques", schema=None) as batch_op:
        batch_op.drop_index("ix_holder_custom_techniques_kind")

    op.drop_table("holder_custom_techniques")
    with op.batch_alter_table("custom_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_custom_kinds_world_id"))
        batch_op.drop_index("ix_custom_kinds_catalog")

    op.drop_table("custom_kinds")
    op.execute(sa.text("DELETE FROM item_history WHERE deed IN ('given', 'captured')"))
    deeds(NEW_DEEDS, OLD_DEEDS)
