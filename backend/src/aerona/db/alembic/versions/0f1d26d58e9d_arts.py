import sqlalchemy as sa
from alembic import op

revision = "0f1d26d58e9d"
down_revision = "2d05825fbb5b"
branch_labels = None
depends_on = None


FACTION_NEW = (
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
    "social_circle",
    "mage_order",
    "estate",
    "party",
    "movement",
    "chartered_company",
    "holy_order",
    "crime_family",
    "thieves_guild",
    "smuggling_ring",
    "pirate_confederacy",
    "art_movement",
    "club",
    "league",
)
FACTION_OLD = tuple(value for value in FACTION_NEW if value not in ("art_movement", "club", "league"))
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
    "forge_work",
)
PLOT_OLD = tuple(value for value in PLOT_NEW if value != "forge_work")
TRIGGER_NEW = (
    "price_spike",
    "execution",
    "sermon",
    "omen",
    "rumour",
    "fire",
    "plague",
    "beast",
    "eclipse",
    "miracle",
    "famine",
    "unpaid_wages",
    "lost_match",
)
TRIGGER_OLD = tuple(value for value in TRIGGER_NEW if value != "lost_match")
RETYPED = (
    ("faction_profiles", "kind", FACTION_OLD, FACTION_NEW, False),
    ("schemes", "kind", PLOT_OLD, PLOT_NEW, False),
    ("movements", "trigger", TRIGGER_OLD, TRIGGER_NEW, False),
    ("cascades", "trigger", TRIGGER_OLD, TRIGGER_NEW, False),
    ("crowd_moods", "last_trigger", TRIGGER_OLD, TRIGGER_NEW, True),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def retype(forward: bool) -> None:
    for table, column, before, after, nullable in RETYPED:
        old, new = (before, after) if forward else (after, before)
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(column, existing_type=enum_of(old, column), type_=enum_of(new, column), existing_nullable=nullable)


def upgrade() -> None:
    retype(forward=True)
    op.create_table(
        "art_movements",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("manifesto", sa.JSON(), nullable=False),
        sa.Column("art_form_entity_id", sa.Integer(), nullable=True),
        sa.Column("orthodoxy", sa.Boolean(), nullable=False),
        sa.Column("scandals", sa.Integer(), nullable=False),
        sa.Column("patrons", sa.Integer(), nullable=False),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("patrons >= 0", name=op.f("ck_art_movements_patrons_min")),
        sa.CheckConstraint("scandals >= 0", name=op.f("ck_art_movements_scandals_min")),
        sa.ForeignKeyConstraint(["art_form_entity_id"], ["entities.id"], name=op.f("fk_art_movements_art_form_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_art_movements_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_art_movements")),
    )
    op.create_table(
        "art_prices",
        sa.Column("artwork_entity_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("provenance", sa.Integer(), nullable=False),
        sa.Column("interest", sa.Integer(), nullable=False),
        sa.Column("last_buyer_node_id", sa.Integer(), nullable=True),
        sa.Column("last_sale_epoch", sa.Integer(), nullable=True),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("interest BETWEEN 0 AND 100", name=op.f("ck_art_prices_interest_range")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_art_prices_price_min")),
        sa.CheckConstraint("provenance >= 0", name=op.f("ck_art_prices_provenance_min")),
        sa.ForeignKeyConstraint(["artwork_entity_id"], ["entities.id"], name=op.f("fk_art_prices_artwork_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_buyer_node_id"], ["nodes.id"], name=op.f("fk_art_prices_last_buyer_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("artwork_entity_id", name=op.f("pk_art_prices")),
    )
    op.create_table(
        "art_sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artwork_entity_id", sa.Integer(), nullable=False),
        sa.Column("seller_node_id", sa.Integer(), nullable=True),
        sa.Column("buyer_node_id", sa.Integer(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("fair_place_entity_id", sa.Integer(), nullable=True),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_art_sales_epoch_min")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_art_sales_price_min")),
        sa.ForeignKeyConstraint(["artwork_entity_id"], ["entities.id"], name=op.f("fk_art_sales_artwork_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_node_id"], ["nodes.id"], name=op.f("fk_art_sales_buyer_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fair_place_entity_id"], ["entities.id"], name=op.f("fk_art_sales_fair_place_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_node_id"], ["nodes.id"], name=op.f("fk_art_sales_seller_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_art_sales")),
    )
    with op.batch_alter_table("art_sales", schema=None) as batch_op:
        batch_op.create_index("ix_art_sales_artwork", ["artwork_entity_id", "epoch"], unique=False)

    op.create_table(
        "birth_signs",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("ruling_celestial_entity_id", sa.Integer(), nullable=True),
        sa.Column("dreaded", sa.Boolean(), nullable=False),
        sa.Column("influence", sa.Enum("real", "believed", name="influence", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("fortune", sa.Integer(), nullable=False),
        sa.Column("exposed", sa.Boolean(), nullable=False),
        sa.Column("born_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fortune BETWEEN -20 AND 20", name=op.f("ck_birth_signs_fortune_range")),
        sa.CheckConstraint("season >= 0", name=op.f("ck_birth_signs_season_min")),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_birth_signs_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ruling_celestial_entity_id"], ["entities.id"], name=op.f("fk_birth_signs_ruling_celestial_entity_id_entities"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_birth_signs")),
    )
    op.create_table(
        "canon_works",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("artwork_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "path",
            sa.Enum("renown", "institution", "copying", "teaching", "movement", name="path", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("contested", sa.Boolean(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_canon_works_weight_range")),
        sa.ForeignKeyConstraint(["artwork_entity_id"], ["entities.id"], name=op.f("fk_canon_works_artwork_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_canon_works_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "artwork_entity_id", name=op.f("pk_canon_works")),
    )
    with op.batch_alter_table("canon_works", schema=None) as batch_op:
        batch_op.create_index("ix_canon_works_artwork", ["artwork_entity_id"], unique=False)

    op.create_table(
        "clubs",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("team_game", "racing", "combat", "athletics", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("league_entity_id", sa.Integer(), nullable=True),
        sa.Column("arena_entity_id", sa.Integer(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("fandom", sa.Integer(), nullable=False),
        sa.Column("line", sa.Enum("none", "class", "district", "faith", name="line", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("line_entity_id", sa.Integer(), nullable=True),
        sa.Column("leverage", sa.Integer(), nullable=False),
        sa.Column("bought_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("founded_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fandom BETWEEN 0 AND 100", name=op.f("ck_clubs_fandom_range")),
        sa.CheckConstraint("leverage BETWEEN 0 AND 100", name=op.f("ck_clubs_leverage_range")),
        sa.CheckConstraint("losses >= 0", name=op.f("ck_clubs_losses_min")),
        sa.CheckConstraint("rating BETWEEN 0 AND 100", name=op.f("ck_clubs_rating_range")),
        sa.CheckConstraint("wins >= 0", name=op.f("ck_clubs_wins_min")),
        sa.ForeignKeyConstraint(["arena_entity_id"], ["entities.id"], name=op.f("fk_clubs_arena_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bought_by_entity_id"], ["entities.id"], name=op.f("fk_clubs_bought_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_clubs_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["league_entity_id"], ["entities.id"], name=op.f("fk_clubs_league_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["line_entity_id"], ["entities.id"], name=op.f("fk_clubs_line_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_clubs")),
    )
    with op.batch_alter_table("clubs", schema=None) as batch_op:
        batch_op.create_index("ix_clubs_league", ["league_entity_id"], unique=False)

    op.create_table(
        "collectors",
        sa.Column("holder_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "role", sa.Enum("collector", "dealer", "patron", "connoisseur", name="role", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("taste_form_entity_id", sa.Integer(), nullable=True),
        sa.Column("connoisseurship", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("connoisseurship BETWEEN 0 AND 100", name=op.f("ck_collectors_connoisseurship_range")),
        sa.ForeignKeyConstraint(["holder_entity_id"], ["entities.id"], name=op.f("fk_collectors_holder_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["taste_form_entity_id"], ["entities.id"], name=op.f("fk_collectors_taste_form_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("holder_entity_id", name=op.f("pk_collectors")),
    )
    op.create_table(
        "constructs",
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "material",
            sa.Enum(
                "wood",
                "bone",
                "hide",
                "leather",
                "cloth",
                "stone",
                "flint",
                "obsidian",
                "copper",
                "tin",
                "bronze",
                "iron",
                "steel",
                "silver",
                "gold",
                "glass",
                "crystal",
                "ivory",
                "chitin",
                "dragonbone",
                "star_metal",
                "void_glass",
                "godflesh",
                "living_wood",
                "salt",
                "amber",
                "lead",
                "skysteel",
                "sulfur",
                "clay",
                "gems",
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "power_source",
            sa.Enum("ley", "divine", "blood", "soul", "reagent", "void", name="power_source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("power", sa.Integer(), nullable=False),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("maker_entity_id", sa.Integer(), nullable=True),
        sa.Column("decay", sa.Integer(), nullable=False),
        sa.Column(
            "will",
            sa.Enum("none", "instructed", "emergent", "full", "exceeding", name="will", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("soul_entity_id", sa.Integer(), nullable=True),
        sa.Column("made_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("decay BETWEEN 0 AND 100", name=op.f("ck_constructs_decay_range")),
        sa.CheckConstraint("power BETWEEN 0 AND 100", name=op.f("ck_constructs_power_range")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_constructs_upkeep_min")),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_constructs_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maker_entity_id"], ["entities.id"], name=op.f("fk_constructs_maker_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["soul_entity_id"], ["entities.id"], name=op.f("fk_constructs_soul_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("entity_id", name=op.f("pk_constructs")),
    )
    with op.batch_alter_table("constructs", schema=None) as batch_op:
        batch_op.create_index("ix_constructs_maker", ["maker_entity_id"], unique=False)

    op.create_table(
        "instruction_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "binding",
            sa.Enum(
                "none", "order", "oath", "geas", "seal", "ownership", "lease", "symbiosis", name="binding", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "command_token",
            sa.Enum("none", "item", "word", "bloodline", "office", "network_key", name="command_token", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("token_entity_id", sa.Integer(), nullable=True),
        sa.Column("holder_node_id", sa.Integer(), nullable=True),
        sa.Column("kill_switch", sa.Boolean(), nullable=False),
        sa.Column("kill_token_entity_id", sa.Integer(), nullable=True),
        sa.Column("literalness", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("literalness BETWEEN 0 AND 100", name=op.f("ck_instruction_sets_literalness_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_instruction_sets_holder_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kill_token_entity_id"], ["entities.id"], name=op.f("fk_instruction_sets_kill_token_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_entity_id"], ["entities.id"], name=op.f("fk_instruction_sets_owner_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["token_entity_id"], ["entities.id"], name=op.f("fk_instruction_sets_token_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_instruction_sets")),
    )
    with op.batch_alter_table("instruction_sets", schema=None) as batch_op:
        batch_op.create_index("ix_instruction_sets_owner", ["owner_entity_id"], unique=False)

    op.create_table(
        "leagues",
        sa.Column("faction_entity_id", sa.Integer(), nullable=False),
        sa.Column("polity_entity_id", sa.Integer(), nullable=True),
        sa.Column("champion_entity_id", sa.Integer(), nullable=True),
        sa.Column("season_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["champion_entity_id"], ["entities.id"], name=op.f("fk_leagues_champion_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["faction_entity_id"], ["entities.id"], name=op.f("fk_leagues_faction_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_leagues_polity_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("faction_entity_id", name=op.f("pk_leagues")),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_entity_id", sa.Integer(), nullable=True),
        sa.Column("home_entity_id", sa.Integer(), nullable=False),
        sa.Column("away_entity_id", sa.Integer(), nullable=False),
        sa.Column("winner_entity_id", sa.Integer(), nullable=True),
        sa.Column("stake", sa.Integer(), nullable=False),
        sa.Column("riot", sa.Boolean(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_matches_epoch_min")),
        sa.CheckConstraint("stake >= 0", name=op.f("ck_matches_stake_min")),
        sa.ForeignKeyConstraint(["away_entity_id"], ["entities.id"], name=op.f("fk_matches_away_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_entity_id"], ["entities.id"], name=op.f("fk_matches_home_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["league_entity_id"], ["entities.id"], name=op.f("fk_matches_league_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_entity_id"], ["entities.id"], name=op.f("fk_matches_winner_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matches")),
    )
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.create_index("ix_matches_league", ["league_entity_id", "epoch"], unique=False)

    op.create_table(
        "monster_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("beast_entity_id", sa.Integer(), nullable=False),
        sa.Column("bounty", sa.Integer(), nullable=False),
        sa.Column("hunter_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("posted", "taken", "slain", "failed", "withdrawn", name="status", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("study", sa.Integer(), nullable=False),
        sa.Column("posted_epoch", sa.Integer(), nullable=False),
        sa.Column("closed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bounty >= 0", name=op.f("ck_monster_contracts_bounty_min")),
        sa.CheckConstraint("posted_epoch >= 0", name=op.f("ck_monster_contracts_posted_epoch_min")),
        sa.CheckConstraint("study BETWEEN 0 AND 100", name=op.f("ck_monster_contracts_study_range")),
        sa.ForeignKeyConstraint(["beast_entity_id"], ["entities.id"], name=op.f("fk_monster_contracts_beast_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_monster_contracts_community_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hunter_entity_id"], ["entities.id"], name=op.f("fk_monster_contracts_hunter_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monster_contracts")),
    )
    with op.batch_alter_table("monster_contracts", schema=None) as batch_op:
        batch_op.create_index("ix_monster_contracts_beast", ["beast_entity_id", "status"], unique=False)
        batch_op.create_index("ix_monster_contracts_community", ["community_entity_id"], unique=False)
        batch_op.create_index("ix_monster_contracts_hunter", ["hunter_entity_id"], unique=False)

    op.create_table(
        "bets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("settlement_entity_id", sa.Integer(), nullable=False),
        sa.Column("club_entity_id", sa.Integer(), nullable=False),
        sa.Column("stake", sa.Integer(), nullable=False),
        sa.Column("won", sa.Boolean(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("stake >= 0", name=op.f("ck_bets_stake_min")),
        sa.ForeignKeyConstraint(["club_entity_id"], ["entities.id"], name=op.f("fk_bets_club_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name=op.f("fk_bets_match_id_matches"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_entity_id"], ["entities.id"], name=op.f("fk_bets_settlement_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bets")),
    )
    with op.batch_alter_table("bets", schema=None) as batch_op:
        batch_op.create_index("ix_bets_match", ["match_id"], unique=False)
        batch_op.create_index("ix_bets_settlement", ["settlement_entity_id"], unique=False)

    op.create_table(
        "instruction_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "guard",
                "serve",
                "obey_holder",
                "build",
                "gather",
                "protect",
                "destroy",
                "report",
                "maintain",
                "replicate",
                "hold_still",
                "follow",
                "forbid",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "condition",
            sa.Enum(
                "always",
                "while_maker_lives",
                "until_date",
                "when_attacked",
                "when_token_shown",
                name="condition",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("lapsed", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("priority >= 0", name=op.f("ck_instruction_orders_priority_min")),
        sa.ForeignKeyConstraint(["set_id"], ["instruction_sets.id"], name=op.f("fk_instruction_orders_set_id_instruction_sets"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_instruction_orders_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_instruction_orders")),
    )
    with op.batch_alter_table("instruction_orders", schema=None) as batch_op:
        batch_op.create_index("ix_instruction_orders_set", ["set_id"], unique=False)

    op.create_table(
        "remade",
        sa.Column("mortal_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "lost_function",
            sa.Enum(
                "grasp",
                "fine_manipulation",
                "locomotion",
                "sight",
                "hearing",
                "speech",
                "breath",
                "vital",
                "cognition",
                "reproduction",
                "flight",
                "venom",
                "horn",
                "tail",
                "presence",
                name="lost_function",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "forced_function",
            sa.Enum(
                "grasp",
                "fine_manipulation",
                "locomotion",
                "sight",
                "hearing",
                "speech",
                "breath",
                "vital",
                "cognition",
                "reproduction",
                "flight",
                "venom",
                "horn",
                "tail",
                "presence",
                name="forced_function",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("sentenced_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("bound_to_entity_id", sa.Integer(), nullable=True),
        sa.Column("grievance", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("epoch >= 0", name=op.f("ck_remade_epoch_min")),
        sa.CheckConstraint("grievance BETWEEN 0 AND 100", name=op.f("ck_remade_grievance_range")),
        sa.ForeignKeyConstraint(["bound_to_entity_id"], ["entities.id"], name=op.f("fk_remade_bound_to_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["crime_cases.id"], name=op.f("fk_remade_case_id_crime_cases"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mortal_entity_id"], ["entities.id"], name=op.f("fk_remade_mortal_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sentenced_by_entity_id"], ["entities.id"], name=op.f("fk_remade_sentenced_by_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("mortal_entity_id", name=op.f("pk_remade")),
    )
    with op.batch_alter_table("remade", schema=None) as batch_op:
        batch_op.create_index("ix_remade_sentenced_by", ["sentenced_by_entity_id"], unique=False)

    op.create_table(
        "forgeries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_entity_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("artwork", "relic", "document", "brand", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("forger_entity_id", sa.Integer(), nullable=True),
        sa.Column("original_entity_id", sa.Integer(), nullable=True),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("claim_id", sa.Integer(), nullable=True),
        sa.Column("skill", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("hidden", "exposed", name="status", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("exposed_by_entity_id", sa.Integer(), nullable=True),
        sa.Column("exposed_epoch", sa.Integer(), nullable=True),
        sa.Column("made_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("made_epoch >= 0", name=op.f("ck_forgeries_made_epoch_min")),
        sa.CheckConstraint("skill BETWEEN 0 AND 100", name=op.f("ck_forgeries_skill_range")),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], name=op.f("fk_forgeries_brand_id_brands"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], name=op.f("fk_forgeries_claim_id_claims"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["exposed_by_entity_id"], ["entities.id"], name=op.f("fk_forgeries_exposed_by_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["forger_entity_id"], ["entities.id"], name=op.f("fk_forgeries_forger_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_entity_id"], ["entities.id"], name=op.f("fk_forgeries_item_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_entity_id"], ["entities.id"], name=op.f("fk_forgeries_original_entity_id_entities"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_forgeries")),
    )
    with op.batch_alter_table("forgeries", schema=None) as batch_op:
        batch_op.create_index("ix_forgeries_item", ["item_entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("forgeries", schema=None) as batch_op:
        batch_op.drop_index("ix_forgeries_item")

    op.drop_table("forgeries")
    with op.batch_alter_table("remade", schema=None) as batch_op:
        batch_op.drop_index("ix_remade_sentenced_by")

    op.drop_table("remade")
    with op.batch_alter_table("instruction_orders", schema=None) as batch_op:
        batch_op.drop_index("ix_instruction_orders_set")

    op.drop_table("instruction_orders")
    with op.batch_alter_table("bets", schema=None) as batch_op:
        batch_op.drop_index("ix_bets_settlement")
        batch_op.drop_index("ix_bets_match")

    op.drop_table("bets")
    with op.batch_alter_table("monster_contracts", schema=None) as batch_op:
        batch_op.drop_index("ix_monster_contracts_hunter")
        batch_op.drop_index("ix_monster_contracts_community")
        batch_op.drop_index("ix_monster_contracts_beast")

    op.drop_table("monster_contracts")
    with op.batch_alter_table("matches", schema=None) as batch_op:
        batch_op.drop_index("ix_matches_league")

    op.drop_table("matches")
    op.drop_table("leagues")
    with op.batch_alter_table("instruction_sets", schema=None) as batch_op:
        batch_op.drop_index("ix_instruction_sets_owner")

    op.drop_table("instruction_sets")
    with op.batch_alter_table("constructs", schema=None) as batch_op:
        batch_op.drop_index("ix_constructs_maker")

    op.drop_table("constructs")
    op.drop_table("collectors")
    with op.batch_alter_table("clubs", schema=None) as batch_op:
        batch_op.drop_index("ix_clubs_league")

    op.drop_table("clubs")
    with op.batch_alter_table("canon_works", schema=None) as batch_op:
        batch_op.drop_index("ix_canon_works_artwork")

    op.drop_table("canon_works")
    op.drop_table("birth_signs")
    with op.batch_alter_table("art_sales", schema=None) as batch_op:
        batch_op.drop_index("ix_art_sales_artwork")

    op.drop_table("art_sales")
    op.drop_table("art_prices")
    op.drop_table("art_movements")
    retype(forward=False)
