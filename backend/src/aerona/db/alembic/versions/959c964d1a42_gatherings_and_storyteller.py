import sqlalchemy as sa
from alembic import op

revision = "959c964d1a42"
down_revision = "c2e4a6b8d0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "war",
                "battle",
                "siege",
                "duel",
                "abduction",
                "beast_attack",
                "raid",
                "persecution",
                "purge",
                "insurrection",
                "coup",
                "succession_crisis",
                "occupation",
                "journey",
                "pilgrimage",
                "competition",
                "performance",
                "procession",
                "ceremony",
                "wedding",
                "funeral",
                "coronation",
                "feast",
                "tournament",
                "hunt",
                "council",
                "summit",
                "plague",
                "famine",
                "migration",
                "founding",
                "theft",
                "investigation",
                "trial",
                "conversion_wave",
                "schism",
                "excavation",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("start_epoch", sa.Integer(), nullable=False),
        sa.Column("end_epoch", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("source_key", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("start_epoch >= 0", name=op.f("ck_incident_collections_start_epoch_min")),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["incident_collections.id"], name=op.f("fk_incident_collections_parent_id_incident_collections"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_incident_collections_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_collections")),
    )
    with op.batch_alter_table("incident_collections", schema=None) as batch_op:
        batch_op.create_index("ix_incident_collections_kind", ["kind", "start_epoch"], unique=False)
        batch_op.create_index("ix_incident_collections_parent", ["parent_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_incident_collections_source_key"), ["source_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_incident_collections_world_id"), ["world_id"], unique=False)

    op.create_table(
        "tension_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("tension", sa.Integer(), nullable=False),
        sa.Column("target", sa.Integer(), nullable=False),
        sa.Column("boost_pct", sa.Integer(), nullable=False),
        sa.Column("band", sa.Enum("quiet", "in_band", "heated", name="band", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.CheckConstraint("tension BETWEEN 0 AND 100", name=op.f("ck_tension_records_tension_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_tension_records_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tension_records")),
    )
    with op.batch_alter_table("tension_records", schema=None) as batch_op:
        batch_op.create_index("ix_tension_records_world", ["world_id", "epoch"], unique=False)

    op.create_table(
        "collection_members",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "leader",
                "member",
                "victim",
                "witness",
                "host",
                "guest",
                "winner",
                "loser",
                "founder",
                "accused",
                "finder",
                "place",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_collection_members_collection_id_incident_collections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_collection_members_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "node_id", name=op.f("pk_collection_members")),
    )
    with op.batch_alter_table("collection_members", schema=None) as batch_op:
        batch_op.create_index("ix_collection_members_node", ["node_id"], unique=False)

    op.create_table(
        "collection_places",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("place_entity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_collection_places_collection_id_incident_collections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_collection_places_place_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "place_entity_id", name=op.f("pk_collection_places")),
    )
    with op.batch_alter_table("collection_places", schema=None) as batch_op:
        batch_op.create_index("ix_collection_places_place", ["place_entity_id"], unique=False)

    op.create_table(
        "excavations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("survey", "clearing", "digging", "deep_layers", "inner_sanctum", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "stalled", "finished", "collapsed", "abandoned", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("leader_entity_id", sa.Integer(), nullable=True),
        sa.Column("sponsor_node_id", sa.Integer(), nullable=True),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("idle_epochs", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("idle_epochs >= 0", name=op.f("ck_excavations_idle_epochs_min")),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name=op.f("ck_excavations_progress_range")),
        sa.CheckConstraint("started_epoch >= 0", name=op.f("ck_excavations_started_epoch_min")),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_excavations_collection_id_incident_collections"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["leader_entity_id"], ["entities.id"], name=op.f("fk_excavations_leader_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_entity_id"], ["entities.id"], name=op.f("fk_excavations_site_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_node_id"], ["nodes.id"], name=op.f("fk_excavations_sponsor_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_excavations")),
    )
    with op.batch_alter_table("excavations", schema=None) as batch_op:
        batch_op.create_index("ix_excavations_site", ["site_entity_id"], unique=False)

    op.create_table(
        "gatherings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("host_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "feast",
                "wedding",
                "funeral",
                "coronation",
                "tournament",
                "hunt",
                "pilgrimage",
                "council",
                "summit",
                "festival",
                "fair",
                "games",
                "performance",
                "trial",
                "execution",
                "procession",
                "milestone",
                "wake",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "status", sa.Enum("planned", "held", "disrupted", "cancelled", name="status", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "outcome",
            sa.Enum("convivial", "uneventful", "quarrelsome", "violent", "massacre", name="outcome", native_enum=False, create_constraint=True, length=40),
            nullable=True,
        ),
        sa.Column(
            "milestone", sa.Enum("birth", "coming_of_age", "anniversary", name="milestone", native_enum=False, create_constraint=True, length=40), nullable=True
        ),
        sa.Column("place_entity_id", sa.Integer(), nullable=True),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("honoured_node_id", sa.Integer(), nullable=True),
        sa.Column("tradition_entity_id", sa.Integer(), nullable=True),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("by_player", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost >= 0", name=op.f("ck_gatherings_cost_min")),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_gatherings_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_gatherings_prestige_range")),
        sa.CheckConstraint("season >= 0", name=op.f("ck_gatherings_season_min")),
        sa.CheckConstraint("year >= 0", name=op.f("ck_gatherings_year_min")),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_gatherings_collection_id_incident_collections"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["honoured_node_id"], ["nodes.id"], name=op.f("fk_gatherings_honoured_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_node_id"], ["nodes.id"], name=op.f("fk_gatherings_host_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_gatherings_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tradition_entity_id"], ["entities.id"], name=op.f("fk_gatherings_tradition_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_gatherings_world_id_worlds"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gatherings")),
    )
    with op.batch_alter_table("gatherings", schema=None) as batch_op:
        batch_op.create_index("ix_gatherings_host", ["host_node_id", "epoch"], unique=False)
        batch_op.create_index("ix_gatherings_place", ["place_entity_id"], unique=False)

    op.create_table(
        "site_holders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("from_epoch", sa.Integer(), nullable=False),
        sa.Column("to_epoch", sa.Integer(), nullable=True),
        sa.Column("how", sa.String(length=120), nullable=True),
        sa.CheckConstraint("from_epoch >= 0", name=op.f("ck_site_holders_from_epoch_min")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_site_holders_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_entity_id"], ["entities.id"], name=op.f("fk_site_holders_site_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_holders")),
    )
    with op.batch_alter_table("site_holders", schema=None) as batch_op:
        batch_op.create_index("ix_site_holders_site", ["site_entity_id", "from_epoch"], unique=False)

    op.create_table(
        "site_rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_entity_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "gate",
                "hall",
                "stair",
                "cell",
                "chamber",
                "vault",
                "shrine",
                "lair",
                "library",
                "armoury",
                "crypt",
                "laboratory",
                "house",
                "store",
                "heart",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "challenge",
            sa.Enum("none", "trap", "guardian", "puzzle", "hazard", name="challenge", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("cleared_epoch", sa.Integer(), nullable=True),
        sa.Column("cleared_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("difficulty BETWEEN 0 AND 100", name=op.f("ck_site_rooms_difficulty_range")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_site_rooms_position_min")),
        sa.ForeignKeyConstraint(["cleared_by_entity_id"], ["entities.id"], name=op.f("fk_site_rooms_cleared_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_entity_id"], ["entities.id"], name=op.f("fk_site_rooms_site_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_rooms")),
    )
    with op.batch_alter_table("site_rooms", schema=None) as batch_op:
        batch_op.create_index("ix_site_rooms_site", ["site_entity_id", "position"], unique=False)

    op.create_table(
        "storytellers",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "profile", sa.Enum("steady", "rising", "cyclic", "chaotic", name="profile", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("tension", sa.Integer(), nullable=False),
        sa.Column("target", sa.Integer(), nullable=False),
        sa.Column("band", sa.Enum("quiet", "in_band", "heated", name="band", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("boost_pct", sa.Integer(), nullable=False),
        sa.Column("cycle_offset", sa.Integer(), nullable=False),
        sa.Column("spotlight_entity_id", sa.Integer(), nullable=True),
        sa.Column("recent_kinds", sa.JSON(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("boost_pct BETWEEN -100 AND 100", name=op.f("ck_storytellers_boost_pct_range")),
        sa.CheckConstraint("cycle_offset >= 0", name=op.f("ck_storytellers_cycle_offset_min")),
        sa.CheckConstraint("tension BETWEEN 0 AND 100", name=op.f("ck_storytellers_tension_range")),
        sa.ForeignKeyConstraint(["spotlight_entity_id"], ["entities.id"], name=op.f("fk_storytellers_spotlight_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_storytellers_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_storytellers")),
    )
    op.create_table(
        "collection_incidents",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["incident_collections.id"], name=op.f("fk_collection_incidents_collection_id_incident_collections"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_collection_incidents_incident_id_incidents"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "incident_id", name=op.f("pk_collection_incidents")),
    )
    with op.batch_alter_table("collection_incidents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_collection_incidents_incident_id"), ["incident_id"], unique=False)

    op.create_table(
        "excavation_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("excavation_id", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("survey", "clearing", "digging", "deep_layers", "inner_sanctum", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
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
                "cryptography",
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
                "cryptography",
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
                "cartography",
                "oral_law",
                "written_law",
                "codified_law",
                "bureaucracy",
                "census",
                "postal_service",
                "diplomatic_corps",
                "standing_army_admin",
                "double_entry",
                "joint_stock",
                "insurance",
                "guilds",
                "universities",
                "hospitals",
                "printing_press",
                "organised_clergy",
                "monasticism",
                "theology_schools",
                "logic",
                "natural_philosophy",
                "empiricism",
                "humanist_ideals",
                name="technique",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("risk", sa.Enum("none", "curse", "spirit", "collapse", name="risk", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "find",
            sa.Enum("nothing", "artifact", "book", "technique", "regalia", "route_map", name="find", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("find_entity_id", sa.Integer(), nullable=True),
        sa.Column("resolved_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("difficulty BETWEEN 0 AND 100", name=op.f("ck_excavation_stages_difficulty_range")),
        sa.ForeignKeyConstraint(["excavation_id"], ["excavations.id"], name=op.f("fk_excavation_stages_excavation_id_excavations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["find_entity_id"], ["entities.id"], name=op.f("fk_excavation_stages_find_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_excavation_stages")),
    )
    with op.batch_alter_table("excavation_stages", schema=None) as batch_op:
        batch_op.create_index("ix_excavation_stages_dig", ["excavation_id"], unique=False)

    op.create_table(
        "gathering_guests",
        sa.Column("gathering_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "host",
                "guest",
                "honoured",
                "contestant",
                "performer",
                "accused",
                "mourned",
                "wedded",
                "crowned",
                "envoy",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Enum(
                "host",
                "kin",
                "friend",
                "obligation",
                "faith",
                "renown",
                "neighbour",
                "summoned",
                name="reason",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("invited", sa.Boolean(), nullable=False),
        sa.Column("attended", sa.Boolean(), nullable=True),
        sa.Column("harmed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["gathering_id"], ["gatherings.id"], name=op.f("fk_gathering_guests_gathering_id_gatherings"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_gathering_guests_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("gathering_id", "node_id", name=op.f("pk_gathering_guests")),
    )
    with op.batch_alter_table("gathering_guests", schema=None) as batch_op:
        batch_op.create_index("ix_gathering_guests_node", ["node_id"], unique=False)

    op.create_table(
        "room_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("item", "spirit", "beast", "trap", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_room_contents_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["site_rooms.id"], name=op.f("fk_room_contents_room_id_site_rooms"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_contents")),
    )
    with op.batch_alter_table("room_contents", schema=None) as batch_op:
        batch_op.create_index("ix_room_contents_room", ["room_id"], unique=False)

    op.create_table(
        "battlefield_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_entity_id", sa.Integer(), nullable=False),
        sa.Column("feature", sa.Enum("mass_grave", "salvage_field", name="feature", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("battle_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_battlefield_features_strength_range")),
        sa.ForeignKeyConstraint(["battle_id"], ["battles.id"], name=op.f("fk_battlefield_features_battle_id_battles"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["place_entity_id"], ["entities.id"], name=op.f("fk_battlefield_features_place_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_battlefield_features")),
    )
    with op.batch_alter_table("battlefield_features", schema=None) as batch_op:
        batch_op.create_index("ix_battlefield_features_place", ["place_entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("battlefield_features", schema=None) as batch_op:
        batch_op.drop_index("ix_battlefield_features_place")

    op.drop_table("battlefield_features")
    with op.batch_alter_table("room_contents", schema=None) as batch_op:
        batch_op.drop_index("ix_room_contents_room")

    op.drop_table("room_contents")
    with op.batch_alter_table("gathering_guests", schema=None) as batch_op:
        batch_op.drop_index("ix_gathering_guests_node")

    op.drop_table("gathering_guests")
    with op.batch_alter_table("excavation_stages", schema=None) as batch_op:
        batch_op.drop_index("ix_excavation_stages_dig")

    op.drop_table("excavation_stages")
    with op.batch_alter_table("collection_incidents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_collection_incidents_incident_id"))

    op.drop_table("collection_incidents")
    op.drop_table("storytellers")
    with op.batch_alter_table("site_rooms", schema=None) as batch_op:
        batch_op.drop_index("ix_site_rooms_site")

    op.drop_table("site_rooms")
    with op.batch_alter_table("site_holders", schema=None) as batch_op:
        batch_op.drop_index("ix_site_holders_site")

    op.drop_table("site_holders")
    with op.batch_alter_table("gatherings", schema=None) as batch_op:
        batch_op.drop_index("ix_gatherings_place")
        batch_op.drop_index("ix_gatherings_host")

    op.drop_table("gatherings")
    with op.batch_alter_table("excavations", schema=None) as batch_op:
        batch_op.drop_index("ix_excavations_site")

    op.drop_table("excavations")
    with op.batch_alter_table("collection_places", schema=None) as batch_op:
        batch_op.drop_index("ix_collection_places_place")

    op.drop_table("collection_places")
    with op.batch_alter_table("collection_members", schema=None) as batch_op:
        batch_op.drop_index("ix_collection_members_node")

    op.drop_table("collection_members")
    with op.batch_alter_table("tension_records", schema=None) as batch_op:
        batch_op.drop_index("ix_tension_records_world")

    op.drop_table("tension_records")
    with op.batch_alter_table("incident_collections", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_incident_collections_world_id"))
        batch_op.drop_index(batch_op.f("ix_incident_collections_source_key"))
        batch_op.drop_index("ix_incident_collections_parent")
        batch_op.drop_index("ix_incident_collections_kind")

    op.drop_table("incident_collections")
