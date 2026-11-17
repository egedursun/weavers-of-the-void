import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import sqlite

revision = "b8b83d201915"
down_revision = "62954d40b909"
branch_labels = None
depends_on = None


G5_BUILT_INS = (
    ("hut", "Hut", "hut", 1, 25, 1, 0),
    ("longhouse", "Longhouse", "house", 3, 40, 2, 0),
    ("townhouse", "Townhouse", "townhouse", 4, 55, 4, 0),
    ("manor", "Manor", "manor", 10, 72, 8, 0),
    ("palace", "Palace", "manor", 30, 90, 18, 0),
    ("tent", "Tent", "hut", 1, 20, 1, 1),
    ("cave", "Cave", "hut", 2, 15, 0, 0),
    ("ship", "Ship", "ship_berth", 2, 35, 3, 1),
    ("tower", "Tower", "townhouse", 6, 60, 6, 0),
    ("apartment", "Apartment", "apartment", 2, 50, 3, 0),
)
G5_POTENTIAL = (("perception", "intuition"), ("wisdom", "patience"))


def seed_built_in_dwellings() -> None:
    for key, name, level, rooms, quality, upkeep, mobile in G5_BUILT_INS:
        op.execute(
            sa.text(
                "INSERT INTO dwelling_kinds (name, built_in, created_epoch, retired, locked, category, rooms, quality, upkeep, mobile, built_in_key) "
                "SELECT :name, 1, 0, 0, '[]', :level, :rooms, :quality, :upkeep, :mobile, :key "
                "WHERE NOT EXISTS (SELECT 1 FROM dwelling_kinds WHERE built_in_key = :key)"
            ).bindparams(name=name, level=level, rooms=rooms, quality=quality, upkeep=upkeep, mobile=mobile, key=key)
        )


def map_dwellings_forward() -> None:
    seed_built_in_dwellings()
    op.execute("UPDATE dwellings SET dwelling_kind_id = (SELECT id FROM dwelling_kinds WHERE built_in_key = dwellings.kind)")
    op.execute("UPDATE household_aggregates SET dwelling_kind_id = (SELECT id FROM dwelling_kinds WHERE built_in_key = household_aggregates.dwelling_kind)")
    for old, new in G5_POTENTIAL:
        op.execute(
            sa.text(
                "UPDATE genomes SET potential = json_remove(json_set(potential, '$.' || :new, json_extract(potential, '$.' || :old)), '$.' || :old) "
                "WHERE json_extract(potential, '$.' || :old) IS NOT NULL"
            ).bindparams(old=old, new=new)
        )
    op.execute("UPDATE genomes SET potential = json_remove(potential, '$.beauty') WHERE json_extract(potential, '$.beauty') IS NOT NULL")


def map_dwellings_back() -> None:
    op.execute(
        "UPDATE dwellings SET kind = COALESCE((SELECT built_in_key FROM dwelling_kinds WHERE dwelling_kinds.id = dwellings.dwelling_kind_id "
        "AND built_in_key IS NOT NULL), 'hut')"
    )
    op.execute(
        "UPDATE household_aggregates SET dwelling_kind = COALESCE((SELECT built_in_key FROM dwelling_kinds "
        "WHERE dwelling_kinds.id = household_aggregates.dwelling_kind_id AND built_in_key IS NOT NULL), 'hut')"
    )
    for old, new in G5_POTENTIAL:
        op.execute(
            sa.text(
                "UPDATE genomes SET potential = json_remove(json_set(potential, '$.' || :old, json_extract(potential, '$.' || :new)), '$.' || :new) "
                "WHERE json_extract(potential, '$.' || :new) IS NOT NULL"
            ).bindparams(old=old, new=new)
        )


APOCALYPSEVARIANT_OLD = ("ruin", "world_war", "outer_descent", "twilight_of_gods", "dimensional_collapse", "galactic_death")
APOCALYPSEVARIANT_NEW = ("ruin", "world_war", "outer_descent", "end_of_the_gods", "dimensional_collapse", "galactic_death")
APOCALYPSEVARIANT_RENAMED = (("twilight_of_gods", "end_of_the_gods"),)
ANIMALROLE_OLD = ("food", "labour", "mount", "war", "guard", "companion", "sacrifice", "magic", "pest_control")
ANIMALROLE_NEW = (
    "draft",
    "mount",
    "dairy",
    "fibre",
    "meat",
    "guard",
    "hunting",
    "war",
    "companion",
    "sacred",
    "pest_control",
    "messenger",
    "sensing",
    "entertainment",
    "reagent_source",
)
ANIMALROLE_RENAMED = (("food", "meat"), ("labour", "draft"), ("sacrifice", "sacred"), ("magic", "reagent_source"))
CONTESTKIND_OLD = ("riddle_game", "flyting", "debate", "game_of_skill", "trial_of_wisdom", "song_contest", "storytelling")
CONTESTKIND_NEW = ("riddle_game", "insult_contest", "debate", "game_of_skill", "trial_of_wisdom", "song_contest", "storytelling")
CONTESTKIND_RENAMED = (("flyting", "insult_contest"),)
CONTESTSTAKE_OLD = ("honour", "bride", "wager", "office", "captive", "divine_favour")
CONTESTSTAKE_NEW = ("honour", "union", "wager", "office", "captive", "divine_favour")
CONTESTSTAKE_RENAMED = (("bride", "union"),)
TEMPERAMENT_OLD = ("placid", "skittish", "curious", "fierce", "cunning", "abductor")
TEMPERAMENT_NEW = ("placid", "skittish", "curious", "fierce", "cunning", "seizes_prey")
TEMPERAMENT_RENAMED = (("abductor", "seizes_prey"),)
MATERIALKIND_OLD = (
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
    "mud_brick",
    "fired_brick",
    "dressed_stone",
    "rubble",
    "lime_mortar",
    "hydraulic_concrete",
    "thatch",
    "tile",
)
MATERIALKIND_NEW = (
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
    "great_bone",
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
    "mud_brick",
    "fired_brick",
    "dressed_stone",
    "rubble",
    "lime_mortar",
    "hydraulic_concrete",
    "thatch",
    "tile",
)
MATERIALKIND_RENAMED = (("dragonbone", "great_bone"),)
LOCUS_OLD = (
    "height",
    "build",
    "skin",
    "hair_colour",
    "hair_texture",
    "eye_colour",
    "face",
    "voice",
    "longevity",
    "fertility",
    "disease_resistance",
    "madness",
    "colour_blindness",
    "giant_blood",
    "divine_blood",
    "curse_marker",
    "gift_elemental_fire",
    "gift_elemental_water",
    "gift_earth",
    "gift_storm",
    "gift_life",
    "gift_death",
    "gift_mind",
    "gift_illusion",
    "gift_divination",
    "gift_warding",
    "gift_binding",
    "gift_summoning",
    "gift_blood",
    "gift_void",
)
LOCUS_NEW = (
    "height",
    "build",
    "skin",
    "hair_colour",
    "hair_texture",
    "eye_colour",
    "face",
    "voice",
    "proportions",
    "markings",
    "muscle",
    "stamina",
    "agility",
    "metabolism",
    "cold_tolerance",
    "heat_tolerance",
    "lung_capacity",
    "bone_density",
    "wound_healing",
    "ageing_pace",
    "pain_sense",
    "sight",
    "hearing",
    "smell",
    "taste",
    "night_vision",
    "excitability",
    "sociability",
    "risk_appetite",
    "attention",
    "stress_response",
    "memory",
    "spatial_sense",
    "language_ease",
    "number_sense",
    "musical_ear",
    "coordination",
    "longevity",
    "fertility",
    "disease_resistance",
    "madness",
    "colour_blindness",
    "giant_blood",
    "divine_blood",
    "curse_marker",
    "gift_elemental_fire",
    "gift_elemental_water",
    "gift_earth",
    "gift_storm",
    "gift_life",
    "gift_death",
    "gift_mind",
    "gift_illusion",
    "gift_divination",
    "gift_warding",
    "gift_binding",
    "gift_summoning",
    "gift_blood",
    "gift_void",
)
LOCUS_RENAMED = ()
ACTIONKIND_OLD = (
    "create_entity",
    "revelation",
    "summon_son",
    "bear_child",
    "command",
    "absolute_command",
    "bless_essence",
    "bless_hp",
    "bless_stat",
    "bless_existence",
    "add_star",
    "ascend",
    "lightning",
    "chain",
    "exile_son",
    "suppress_rebellion",
    "suppress_failed",
    "forgive",
    "answer_prayer",
    "chat",
    "resurrect_son",
    "kill_son",
    "take_life",
    "resurrect_mortal",
    "deify",
    "demote",
    "grant_power",
    "choose_prophet",
    "manifestation",
    "lineage_curse",
    "lift_lineage_curse",
    "convert",
    "wrath",
    "world_wrath",
    "drain_essence",
    "devour",
    "harvest_community",
    "kill_foreign_god",
    "canon_restore",
    "canon_strike",
    "edit_record",
    "edit_creator",
    "merge_records",
    "archive_record",
    "create_world",
    "birth_world",
    "forget_world",
    "remember_world",
    "exile_entity",
    "pardon",
    "ignite_star",
    "hang_star",
    "extinguish_star",
    "rekindle_star",
    "seal_gate",
    "sever_route",
    "repair_route",
    "reveal_route",
    "recall_journey",
    "cleanse_leak",
    "sky_event",
    "spirit_cloak",
    "legendary_quest",
    "miracle",
    "disaster",
    "teach_knowledge",
    "advance_knowledge",
    "set_knowledge_level",
    "assign_mechanics",
    "syncretize_faith",
    "birth_creole",
    "curse",
    "dream",
    "influence",
    "declare_chosen",
    "incite_war",
    "transform",
    "destroy",
    "covenant",
    "change_anchor",
    "challenge",
    "speak_to_sibling",
    "make_bond",
    "pray_to_creator",
    "harvest_resource",
    "gift",
    "holy_world",
    "interworld_treaty",
    "foreign_god_war",
    "open_cosmic_bed",
    "close_leak",
    "outer_bargain",
    "rebel",
    "convene_council",
    "awaken_peoples",
    "set_passions",
    "push_reputation",
    "found_language",
    "coin_words",
    "produce",
    "build",
    "create_culture",
    "discover_resource",
    "claim",
    "found_settlement",
    "establish_trade",
    "declare_war",
    "worship",
    "develop_knowledge",
    "learn",
    "diplomacy",
    "adventure",
    "discover_route",
    "explore_land",
    "resurrection_rite",
    "build_ship",
    "set_out",
    "tame",
    "make_chimera",
    "bind_spirit",
    "search_ruins",
    "sabotage",
    "preach",
    "defy_god",
    "deny_god",
    "prophesy",
    "escape",
    "pay_ransom",
    "rescue_captive",
    "raise_army",
    "appoint_commander",
    "build_spy_network",
    "barter",
    "lend",
    "repay",
    "adopt",
    "network_repair",
    "ledger_undo",
    "sibling_scheme",
    "scatter_bones",
    "move_to_world",
    "reorder_seasons",
    "shape_weather",
    "sever_ley",
    "reshape_land",
    "foreign_god_talk",
    "write_plan",
    "abandon_settlement",
    "apocalypse",
    "awaken_species",
    "betrayal",
    "bless_army",
    "cosmic_archive",
    "cosmic_plague",
    "creator_sign",
    "crown_ruler",
    "cultural_contact",
    "designate_heir",
    "disband_army",
    "dissolve_faction",
    "end_blood_feud",
    "epoch_star",
    "ethnogenesis",
    "evaluate_goals",
    "force_battle",
    "foreign_god_land",
    "forget_legend",
    "forgive_debt",
    "forgive_tribute",
    "found_faction",
    "found_market",
    "fulfil_prophecy",
    "golden_age",
    "grant_independence",
    "grant_victory",
    "horror_event",
    "hunt",
    "impose_tribute",
    "incite_uprising",
    "introduce_species",
    "lay_spirit_to_rest",
    "megafauna_trail",
    "mint_coin",
    "mirror_birth",
    "mutate_species",
    "order_exodus",
    "order_feeding",
    "outer_cult",
    "planet_act",
    "pour_essence",
    "raise_hero",
    "raise_notable",
    "recall_hero",
    "reclaim_colony",
    "regenerate_map",
    "resettle_ruin",
    "reveal_previous_creation",
    "revive_legend",
    "set_doom_clock",
    "set_immortal",
    "set_route_danger",
    "set_sanity",
    "set_son_relation",
    "set_tier",
    "shape_society",
    "shelter_from_ruin",
    "soul_descent",
    "soul_harvest",
    "spare_prey",
    "spawn_pirates",
    "split_people",
    "summon_outer_being",
    "time_echo",
    "train_apprentice",
    "wake_foreign_god",
    "edit_language",
    "regenerate_signature",
    "add_epoch_words",
    "discard_intuition",
    "rejudge_fate",
    "retry_fate",
    "override_verdict",
    "retry_voices",
    "audit_chronicle",
    "retry_births",
    "edit_historian_view",
    "delete_historian_view",
    "maintenance",
    "dissolve_community",
    "raze_structure",
    "write_fate",
    "commemorate",
    "revive_world",
    "appoint_guardian",
    "set_abundance",
    "seed_place",
    "declare_pilgrimage_site",
    "order_end",
    "hide_secret",
    "reveal_secret",
    "sanctify_place",
    "raise_nexus",
    "lay_siege",
    "offer_peace",
    "design_unit",
    "other",
    "enact_law",
    "appoint_officer",
    "set_tax",
    "propose_treaty",
    "accept_treaty",
    "break_treaty",
    "swear_oath",
    "release_oath",
    "bless_bloodline",
    "steer_faction",
)
ACTIONKIND_NEW = (
    "create_entity",
    "revelation",
    "summon_son",
    "bear_child",
    "command",
    "absolute_command",
    "bless_essence",
    "bless_hp",
    "bless_stat",
    "bless_existence",
    "add_star",
    "ascend",
    "lightning",
    "chain",
    "exile_son",
    "suppress_rebellion",
    "suppress_failed",
    "forgive",
    "answer_prayer",
    "chat",
    "resurrect_son",
    "kill_son",
    "take_life",
    "resurrect_mortal",
    "deify",
    "demote",
    "grant_power",
    "choose_prophet",
    "manifestation",
    "lineage_curse",
    "lift_lineage_curse",
    "convert",
    "wrath",
    "world_wrath",
    "drain_essence",
    "devour",
    "harvest_community",
    "kill_foreign_god",
    "canon_restore",
    "canon_strike",
    "edit_record",
    "edit_creator",
    "merge_records",
    "archive_record",
    "create_world",
    "birth_world",
    "forget_world",
    "remember_world",
    "exile_entity",
    "pardon",
    "ignite_star",
    "hang_star",
    "extinguish_star",
    "rekindle_star",
    "seal_gate",
    "sever_route",
    "repair_route",
    "reveal_route",
    "recall_journey",
    "cleanse_leak",
    "sky_event",
    "spirit_cloak",
    "legendary_quest",
    "miracle",
    "disaster",
    "teach_knowledge",
    "advance_knowledge",
    "set_knowledge_level",
    "assign_mechanics",
    "syncretize_faith",
    "birth_creole",
    "curse",
    "dream",
    "influence",
    "declare_chosen",
    "incite_war",
    "transform",
    "destroy",
    "covenant",
    "change_anchor",
    "challenge",
    "speak_to_sibling",
    "make_bond",
    "pray_to_creator",
    "harvest_resource",
    "gift",
    "holy_world",
    "interworld_treaty",
    "foreign_god_war",
    "open_cosmic_bed",
    "close_leak",
    "outer_bargain",
    "rebel",
    "convene_council",
    "awaken_peoples",
    "set_passions",
    "push_reputation",
    "found_language",
    "coin_words",
    "produce",
    "build",
    "create_culture",
    "discover_resource",
    "claim",
    "found_settlement",
    "establish_trade",
    "declare_war",
    "worship",
    "develop_knowledge",
    "learn",
    "diplomacy",
    "adventure",
    "discover_route",
    "explore_land",
    "resurrection_rite",
    "build_ship",
    "set_out",
    "tame",
    "merge_species",
    "bind_spirit",
    "search_ruins",
    "sabotage",
    "preach",
    "defy_god",
    "deny_god",
    "prophesy",
    "escape",
    "pay_ransom",
    "rescue_captive",
    "raise_army",
    "appoint_commander",
    "build_spy_network",
    "barter",
    "lend",
    "repay",
    "adopt",
    "network_repair",
    "ledger_undo",
    "sibling_scheme",
    "hinder_return",
    "move_to_world",
    "reorder_seasons",
    "shape_weather",
    "sever_ley",
    "reshape_land",
    "foreign_god_talk",
    "write_plan",
    "abandon_settlement",
    "apocalypse",
    "awaken_species",
    "betrayal",
    "bless_army",
    "cosmic_archive",
    "cosmic_plague",
    "creator_sign",
    "crown_ruler",
    "cultural_contact",
    "designate_heir",
    "disband_army",
    "dissolve_faction",
    "end_blood_feud",
    "epoch_star",
    "ethnogenesis",
    "evaluate_goals",
    "force_battle",
    "foreign_god_land",
    "forget_legend",
    "forgive_debt",
    "forgive_tribute",
    "found_faction",
    "found_market",
    "fulfil_prophecy",
    "golden_age",
    "grant_independence",
    "grant_victory",
    "horror_event",
    "hunt",
    "impose_tribute",
    "incite_uprising",
    "introduce_species",
    "lay_spirit_to_rest",
    "megafauna_trail",
    "mint_coin",
    "mirror_birth",
    "mutate_species",
    "order_exodus",
    "order_feeding",
    "outer_cult",
    "planet_act",
    "pour_essence",
    "raise_hero",
    "raise_notable",
    "recall_hero",
    "reclaim_colony",
    "regenerate_map",
    "resettle_ruin",
    "reveal_previous_creation",
    "revive_legend",
    "set_doom_clock",
    "set_immortal",
    "set_route_danger",
    "set_sanity",
    "set_son_relation",
    "set_tier",
    "shape_society",
    "shelter_from_ruin",
    "soul_descent",
    "soul_harvest",
    "spare_prey",
    "spawn_pirates",
    "split_people",
    "summon_outer_being",
    "time_echo",
    "train_apprentice",
    "wake_foreign_god",
    "edit_language",
    "regenerate_signature",
    "add_epoch_words",
    "discard_intuition",
    "rejudge_fate",
    "retry_fate",
    "override_verdict",
    "retry_voices",
    "audit_chronicle",
    "retry_births",
    "edit_historian_view",
    "delete_historian_view",
    "maintenance",
    "dissolve_community",
    "raze_structure",
    "write_fate",
    "commemorate",
    "revive_world",
    "appoint_guardian",
    "set_abundance",
    "seed_place",
    "declare_pilgrimage_site",
    "order_end",
    "hide_secret",
    "reveal_secret",
    "sanctify_place",
    "raise_nexus",
    "lay_siege",
    "offer_peace",
    "design_unit",
    "other",
    "enact_law",
    "appoint_officer",
    "set_tax",
    "propose_treaty",
    "accept_treaty",
    "break_treaty",
    "swear_oath",
    "release_oath",
    "bless_bloodline",
    "steer_faction",
)
ACTIONKIND_RENAMED = (
    ("stitch_route", "repair_route"),
    ("weave_bond", "make_bond"),
    ("stitch_leak", "close_leak"),
    ("weave_chimera", "make_chimera"),
    ("scatter_bones", "hinder_return"),
    ("make_chimera", "merge_species"),
)
BALANCELOOP_OLD = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
)
BALANCELOOP_NEW = (
    "war_weariness",
    "overextension",
    "soil_exhaustion",
    "toll_diversion",
    "comfort_zeal",
    "endemic_immunity",
    "god_neglect",
    "predator_prey",
    "debasement",
    "wonder_envy",
    "regency",
    "mill_riots",
    "tyranny_concessions",
    "glacial_thaw",
    "courier_networks",
    "storyteller_pacing",
    "squalor_disease",
    "great_person_envy",
    "impact_preparation",
    "heroquest_schism",
    "gentrification",
    "precedent_drift",
    "keystone_hunting",
    "malthusian",
    "salinisation",
    "theodicy",
    "monsoon_migration",
    "redistribution_collapse",
    "novelty_drain",
    "kind_prestige",
    "kind_substitution",
)
BALANCELOOP_RENAMED = ()
PERKKIND_OLD = (
    "silver_tongue",
    "peacemaker",
    "well_connected",
    "envoys_patience",
    "beloved",
    "hardened",
    "swift_blade",
    "iron_nerve",
    "battle_eye",
    "warlord",
    "ledger_mind",
    "steady_hand",
    "prudent",
    "builder",
    "granary_keeper",
    "shadow_step",
    "keen_ear",
    "mask",
    "network_builder",
    "cold_eye",
    "quick_study",
    "deep_memory",
    "lucid",
    "sages_insight",
    "polymath",
    "devout",
    "serene",
    "faithful_voice",
    "visionary",
    "hallowed",
    "sure_hands",
    "inventive",
    "tireless",
    "eye_for_beauty",
    "masters_touch",
    "good_company",
    "carefree",
    "reveller",
    "charming",
    "joyful_spirit",
)
PERKKIND_NEW = (
    "persuasive",
    "peacemaker",
    "well_connected",
    "patient_envoy",
    "beloved",
    "hardened",
    "fast_striker",
    "steady_under_fear",
    "reads_the_field",
    "commander",
    "reckoner",
    "steady_hand",
    "prudent",
    "builder",
    "provisioner",
    "unseen",
    "keen_ear",
    "dissembler",
    "network_builder",
    "unmoved",
    "quick_study",
    "deep_memory",
    "lucid",
    "insightful",
    "polymath",
    "devout",
    "serene",
    "faithful_voice",
    "visionary",
    "hallowed",
    "sure_hands",
    "inventive",
    "tireless",
    "aesthete",
    "master_craft",
    "good_company",
    "carefree",
    "reveller",
    "charming",
    "joyful_spirit",
)
PERKKIND_RENAMED = (
    ("silver_tongue", "persuasive"),
    ("swift_blade", "fast_striker"),
    ("iron_nerve", "steady_under_fear"),
    ("battle_eye", "reads_the_field"),
    ("warlord", "commander"),
    ("ledger_mind", "reckoner"),
    ("granary_keeper", "provisioner"),
    ("shadow_step", "unseen"),
    ("mask", "dissembler"),
    ("cold_eye", "unmoved"),
    ("masters_touch", "master_craft"),
    ("eye_for_beauty", "aesthete"),
    ("sages_insight", "insightful"),
    ("envoys_patience", "patient_envoy"),
)
TRANSFORMKIND_OLD = (
    "deification",
    "mantling",
    "spirit_rising",
    "reincarnation",
    "possession",
    "local_god",
    "beast_curse",
    "curse_lifted",
    "uplift",
    "city_state",
    "secession",
    "theocracy",
    "title_raised",
    "realm_from_title",
    "manifestation",
    "legend_fixed",
    "artwork_remembered",
    "event_phenomenon",
    "god_corpse",
    "construct",
    "beast_promotion",
    "language_death",
    "language_revival",
    "theory_settled",
    "tradition_codified",
    "fall",
    "restoration",
    "loss_of_sapience",
    "ethnoreligious",
    "nation_building",
    "house_people",
    "pocket_world",
    "world_soul",
    "star_god",
    "sacralisation",
    "secularisation",
    "progenitor",
    "outer_entry",
    "corruption",
    "colossal_corpse",
)
TRANSFORMKIND_NEW = (
    "deification",
    "mantling",
    "spirit_rising",
    "reincarnation",
    "possession",
    "local_god",
    "beast_curse",
    "curse_lifted",
    "uplift",
    "city_state",
    "secession",
    "theocracy",
    "title_raised",
    "realm_from_title",
    "manifestation",
    "legend_fixed",
    "artwork_remembered",
    "event_phenomenon",
    "dead_god",
    "construct",
    "beast_promotion",
    "language_death",
    "language_revival",
    "theory_settled",
    "tradition_codified",
    "fall",
    "restoration",
    "loss_of_sapience",
    "ethnoreligious",
    "nation_building",
    "house_people",
    "pocket_world",
    "world_soul",
    "star_god",
    "sacralisation",
    "secularisation",
    "progenitor",
    "outer_entry",
    "corruption",
    "colossal_corpse",
)
TRANSFORMKIND_RENAMED = (("god_corpse", "dead_god"),)
GAMECATEGORY_OLD = ("board", "dice", "cards", "ball", "wrestling")
GAMECATEGORY_NEW = ("board", "chance", "card", "ball", "racing", "combat_sport", "athletic", "hunting_sport", "wit", "team", "spectacle", "gambling", "network")
GAMECATEGORY_RENAMED = (("dice", "chance"), ("cards", "card"), ("wrestling", "combat_sport"))
WORLDEND_OLD = ("shattered", "swallowed", "frozen_dead", "sunk_into_void", "forgotten", "transfigured")
WORLDEND_NEW = ("shattered", "consumed", "frozen_dead", "sunk_into_void", "forgotten", "transfigured")
WORLDEND_RENAMED = (("swallowed", "consumed"),)
CHRONICLEKIND_OLD = (
    "creation",
    "speech",
    "challenge",
    "prayer",
    "order",
    "fate",
    "death",
    "birth",
    "system",
    "message",
    "creator_hand",
    "world",
    "engine_raw",
    "knowledge",
    "resource",
    "culture",
    "trade",
    "exploration",
    "diplomacy",
    "production",
    "language",
    "miracle",
    "civilization",
    "creator_reputation",
    "construction",
    "existence",
    "dream",
    "star",
    "divine_sign",
    "climate",
    "cosmic",
    "debt",
    "foreign_god",
    "world_age",
    "council",
    "previous_creation",
    "sky",
    "gift",
    "worship",
    "world_birth",
    "prophecy",
    "covenant",
    "army",
    "ascension",
    "migration",
    "legendary_quest",
    "war",
    "war_of_gods",
    "cosmic_law",
    "horror",
    "outer_being",
    "immortality",
    "rebellion",
    "apocalypse",
    "resurrection",
    "lineage",
    "disaster",
    "adventure",
    "intrigue",
    "rescue",
    "chimera",
    "escape",
    "domestication",
    "age_change",
    "expedition",
    "spirit",
    "curse",
    "denial",
    "ransom",
    "prohibition",
)
CHRONICLEKIND_NEW = (
    "creation",
    "speech",
    "challenge",
    "prayer",
    "order",
    "fate",
    "death",
    "birth",
    "system",
    "message",
    "creator_hand",
    "world",
    "engine_raw",
    "knowledge",
    "resource",
    "culture",
    "trade",
    "exploration",
    "diplomacy",
    "production",
    "language",
    "miracle",
    "civilization",
    "creator_reputation",
    "construction",
    "existence",
    "dream",
    "star",
    "divine_sign",
    "climate",
    "cosmic",
    "debt",
    "foreign_god",
    "world_age",
    "council",
    "previous_creation",
    "sky",
    "gift",
    "worship",
    "world_birth",
    "prophecy",
    "covenant",
    "army",
    "ascension",
    "migration",
    "legendary_quest",
    "war",
    "war_of_gods",
    "cosmic_law",
    "horror",
    "outer_being",
    "immortality",
    "rebellion",
    "apocalypse",
    "resurrection",
    "lineage",
    "disaster",
    "adventure",
    "intrigue",
    "rescue",
    "merged_species",
    "escape",
    "domestication",
    "age_change",
    "expedition",
    "spirit",
    "curse",
    "denial",
    "ransom",
    "prohibition",
)
CHRONICLEKIND_RENAMED = (("chimera", "merged_species"),)
ENGINEKIND_OLD = (
    "war",
    "battle",
    "siege",
    "magic_storm",
    "earthquake",
    "flood",
    "plague",
    "drought",
    "storm",
    "famine",
    "uprising",
    "migration",
    "temple",
    "wall",
    "library",
    "school",
    "observatory",
    "cosmic_archive",
    "wonder",
    "rebels",
    "merchant_guild",
    "priests_council",
    "warrior_band",
    "interworld_federation",
    "wandering_market",
    "route_raiders",
    "peoples_army",
    "holy_guard",
    "mercenary_army",
    "dialect",
    "primitive_language",
    "currency",
    "eclipse_prophecy",
    "cosmic_travel_resource",
    "golem",
    "domesticated",
    "chimera",
    "descended_soul",
    "mirror_birth",
    "apprentice",
    "comet",
    "ascension_myth",
    "god_corpse",
    "god_shade",
    "resurrection_order",
    "ghost_ship",
    "colony",
    "festival_of_note",
    "coronation",
    "wedding",
    "massacre",
    "sack",
    "fire",
    "eruption",
    "riot",
    "schism_council",
    "eclipse_watch",
)
ENGINEKIND_NEW = (
    "war",
    "battle",
    "siege",
    "magic_storm",
    "earthquake",
    "flood",
    "plague",
    "drought",
    "storm",
    "famine",
    "uprising",
    "migration",
    "temple",
    "wall",
    "library",
    "school",
    "observatory",
    "cosmic_archive",
    "wonder",
    "rebels",
    "merchant_guild",
    "priests_council",
    "warrior_band",
    "interworld_federation",
    "wandering_market",
    "route_raiders",
    "peoples_army",
    "holy_guard",
    "mercenary_army",
    "dialect",
    "primitive_language",
    "currency",
    "eclipse_prophecy",
    "cosmic_travel_resource",
    "animated_work",
    "domesticated",
    "merged_species",
    "descended_soul",
    "mirror_birth",
    "apprentice",
    "comet",
    "ascension_myth",
    "dead_god",
    "god_shade",
    "resurrection_order",
    "ghost_ship",
    "colony",
    "festival_of_note",
    "coronation",
    "wedding",
    "massacre",
    "sack",
    "fire",
    "eruption",
    "riot",
    "schism_council",
    "eclipse_watch",
)
ENGINEKIND_RENAMED = (("god_corpse", "dead_god"), ("golem", "animated_work"), ("chimera", "merged_species"))
MORTALROLE_OLD = (
    "ruler",
    "hero",
    "warrior",
    "knight",
    "hunter",
    "chosen",
    "seer",
    "priest",
    "sage",
    "healer",
    "artisan",
    "merchant",
    "scribe",
    "farmer",
    "explorer",
    "captain",
    "bandit",
    "saint",
    "apprentice",
    "commoner",
    "officer",
    "spy",
    "scientist",
    "engineer",
    "pilot",
    "physician",
    "journalist",
    "executive",
)
MORTALROLE_NEW = (
    "ruler",
    "hero",
    "warrior",
    "sworn_warrior",
    "hunter",
    "chosen",
    "seer",
    "priest",
    "sage",
    "healer",
    "artisan",
    "merchant",
    "scribe",
    "farmer",
    "explorer",
    "captain",
    "bandit",
    "saint",
    "apprentice",
    "commoner",
    "officer",
    "spy",
    "scientist",
    "engineer",
    "pilot",
    "physician",
    "journalist",
    "executive",
)
MORTALROLE_RENAMED = (("knight", "sworn_warrior"),)
TRAITKIND_OLD = (
    "brave",
    "craven",
    "wrathful",
    "patient",
    "cruel",
    "kind",
    "ambitious",
    "content",
    "greedy",
    "generous",
    "honest",
    "deceitful",
    "zealous",
    "cynical",
    "paranoid",
    "trusting",
    "lustful",
    "chaste",
    "gluttonous",
    "ascetic",
    "scholarly",
    "illiterate_proud",
    "gregarious",
    "reclusive",
    "vengeful",
    "forgiving",
    "stubborn",
    "fickle",
    "just",
    "arbitrary",
    "humble",
    "proud",
    "curious",
    "incurious",
    "melancholic",
    "sanguine",
    "iron_willed",
    "impressionable",
    "cunning_tactician",
    "reckless",
    "cautious",
    "diligent",
    "slothful",
    "loyal",
    "disloyal",
    "obedient",
    "defiant",
    "playful",
    "dour",
    "charming",
    "awkward",
    "eloquent",
    "tongue_tied",
    "tactful",
    "blunt",
    "discreet",
    "gossiping",
    "hospitable",
    "inhospitable",
    "cooperative",
    "competitive",
    "affectionate",
    "aloof",
    "courteous",
    "rude",
    "shrewd",
    "gullible",
    "imaginative",
    "literal_minded",
    "methodical",
    "scatterbrained",
    "perceptive",
    "oblivious",
    "wise",
    "foolish",
    "sceptical",
    "credulous",
    "contemplative",
    "impulsive",
    "disciplined",
    "undisciplined",
    "frugal",
    "spendthrift",
    "orderly",
    "disorderly",
    "honourable",
    "unscrupulous",
    "modest",
    "vain",
    "compassionate",
    "callous",
    "calm",
    "anxious",
    "optimistic",
    "pessimistic",
    "passionate",
    "detached",
    "jealous",
    "secure",
    "sentimental",
    "unsentimental",
    "mystic",
    "worldly",
    "tolerant",
    "intolerant",
    "reverent",
    "irreverent",
    "adventurous",
    "homebound",
    "idealistic",
    "pragmatic",
    "perfectionist",
    "careless",
    "glory_seeking",
    "unassuming",
    "dutiful",
    "self_serving",
    "resilient",
    "fragile",
    "stoic",
    "volatile",
    "brooding",
    "carefree",
    "bloodthirsty",
    "peaceable",
    "gallant",
    "ruthless",
    "vigilant",
    "complacent",
)
TRAITKIND_NEW = (
    "brave",
    "craven",
    "wrathful",
    "patient",
    "cruel",
    "kind",
    "ambitious",
    "content",
    "greedy",
    "generous",
    "honest",
    "deceitful",
    "zealous",
    "cynical",
    "paranoid",
    "trusting",
    "lustful",
    "chaste",
    "gluttonous",
    "ascetic",
    "scholarly",
    "illiterate_proud",
    "gregarious",
    "reclusive",
    "vengeful",
    "forgiving",
    "stubborn",
    "fickle",
    "just",
    "arbitrary",
    "humble",
    "proud",
    "curious",
    "incurious",
    "melancholic",
    "sanguine",
    "iron_willed",
    "impressionable",
    "cunning_tactician",
    "reckless",
    "cautious",
    "diligent",
    "slothful",
    "loyal",
    "disloyal",
    "obedient",
    "defiant",
    "playful",
    "dour",
    "charming",
    "awkward",
    "eloquent",
    "tongue_tied",
    "tactful",
    "blunt",
    "discreet",
    "gossiping",
    "hospitable",
    "inhospitable",
    "cooperative",
    "competitive",
    "affectionate",
    "aloof",
    "courteous",
    "rude",
    "shrewd",
    "gullible",
    "imaginative",
    "literal_minded",
    "methodical",
    "scatterbrained",
    "perceptive",
    "oblivious",
    "wise",
    "foolish",
    "sceptical",
    "credulous",
    "contemplative",
    "impulsive",
    "disciplined",
    "undisciplined",
    "frugal",
    "spendthrift",
    "orderly",
    "disorderly",
    "honourable",
    "unscrupulous",
    "modest",
    "vain",
    "compassionate",
    "callous",
    "calm",
    "anxious",
    "optimistic",
    "pessimistic",
    "passionate",
    "detached",
    "jealous",
    "secure",
    "sentimental",
    "unsentimental",
    "mystic",
    "worldly",
    "tolerant",
    "intolerant",
    "reverent",
    "irreverent",
    "adventurous",
    "homebound",
    "idealistic",
    "pragmatic",
    "perfectionist",
    "careless",
    "glory_seeking",
    "unassuming",
    "dutiful",
    "self_serving",
    "resilient",
    "fragile",
    "stoic",
    "volatile",
    "brooding",
    "carefree",
    "bloodthirsty",
    "peaceable",
    "gallant",
    "ruthless",
    "vigilant",
    "complacent",
    "hardy",
    "nimble",
    "sharp_sighted",
    "retentive",
    "numerate",
    "musical",
)
TRAITKIND_RENAMED = ()
HERALDICCHARGE_OLD = (
    "none",
    "beast",
    "bird",
    "tree",
    "tower",
    "sword",
    "crown",
    "star",
    "sun",
    "moon",
    "eye",
    "hand",
    "wheel",
    "wave",
    "flame",
    "key",
    "crossed_swords",
    "axe",
    "bow",
    "spear",
    "shield",
    "target",
    "fist",
    "arm",
    "flag",
    "castle",
    "column",
    "laurel",
    "fleur_de_lis",
    "cross",
    "cross_patty",
    "crosslet",
    "annulet",
    "mascle",
    "lozenge",
    "hexagon",
    "triangle",
    "estoile",
    "sparkles",
    "moon_star",
    "eclipse",
    "sunrise",
    "bell",
    "infinity",
    "orbit",
    "atom",
    "galaxy",
    "rocket",
    "hand_heart",
    "helping_hand",
    "heart",
    "handshake",
    "droplet",
    "snowflake",
    "flower",
    "blossom",
    "rose",
    "feather",
    "gem",
    "shell",
    "pine",
    "grove",
    "palm",
    "shrub",
    "sprout",
    "leaf",
    "clover",
    "wheat",
    "grapes",
    "apple",
    "cherries",
    "house",
    "hearth",
    "egg",
    "book",
    "open_book",
    "scroll",
    "quill",
    "telescope",
    "dividers",
    "compass",
    "brain",
    "hourglass",
    "globe",
    "coins",
    "ship",
    "sailboat",
    "anchor",
    "amphora",
    "barrel",
    "scales",
    "gavel",
    "temple",
    "lock",
    "mountain",
    "peak",
    "fish",
    "rabbit",
    "squirrel",
    "snail",
    "turtle",
    "cat",
    "dog",
    "rat",
    "prawn",
    "worm",
    "paw",
    "wind",
    "tornado",
    "lightning",
    "cloud",
    "rainbow",
    "skull",
    "bone",
    "ghost",
    "die",
    "wand",
    "mask",
    "masks",
    "tent",
    "king",
    "queen",
    "bishop",
    "pawn",
    "pyramid",
    "medal",
    "rosette",
    "trophy",
    "hammer",
    "anvil",
    "cog",
    "pickaxe",
    "shovel",
    "shears",
    "spool",
    "wall",
    "palette",
    "music",
    "brush",
    "lute",
    "drum",
    "goblet",
    "tankard",
    "bridge",
    "lighthouse",
    "torch",
    "wing",
    "footprints",
    "dna",
)
HERALDICCHARGE_NEW = (
    "none",
    "beast",
    "bird",
    "tree",
    "tower",
    "sword",
    "crown",
    "star",
    "sun",
    "moon",
    "eye",
    "hand",
    "wheel",
    "wave",
    "flame",
    "key",
    "crossed_swords",
    "axe",
    "bow",
    "spear",
    "shield",
    "target",
    "fist",
    "arm",
    "flag",
    "castle",
    "column",
    "laurel",
    "fleur_de_lis",
    "cross",
    "cross_patty",
    "crosslet",
    "annulet",
    "mascle",
    "lozenge",
    "hexagon",
    "triangle",
    "estoile",
    "sparkles",
    "moon_star",
    "eclipse",
    "sunrise",
    "bell",
    "infinity",
    "orbit",
    "atom",
    "galaxy",
    "rocket",
    "hand_heart",
    "helping_hand",
    "heart",
    "handshake",
    "droplet",
    "snowflake",
    "flower",
    "blossom",
    "rose",
    "feather",
    "gem",
    "shell",
    "pine",
    "grove",
    "palm",
    "shrub",
    "sprout",
    "leaf",
    "clover",
    "wheat",
    "grapes",
    "apple",
    "cherries",
    "house",
    "hearth",
    "egg",
    "book",
    "open_book",
    "scroll",
    "quill",
    "telescope",
    "dividers",
    "compass",
    "brain",
    "hourglass",
    "globe",
    "coins",
    "ship",
    "sailboat",
    "anchor",
    "amphora",
    "barrel",
    "scales",
    "gavel",
    "temple",
    "lock",
    "mountain",
    "peak",
    "fish",
    "rabbit",
    "squirrel",
    "snail",
    "turtle",
    "cat",
    "dog",
    "rat",
    "prawn",
    "worm",
    "paw",
    "wind",
    "tornado",
    "lightning",
    "cloud",
    "rainbow",
    "skull",
    "bone",
    "ghost",
    "die",
    "wand",
    "mask",
    "masks",
    "tent",
    "ruler_piece",
    "consort_piece",
    "bishop",
    "pawn",
    "pyramid",
    "medal",
    "rosette",
    "trophy",
    "hammer",
    "anvil",
    "cog",
    "pickaxe",
    "shovel",
    "shears",
    "spool",
    "wall",
    "palette",
    "music",
    "brush",
    "lute",
    "drum",
    "goblet",
    "tankard",
    "bridge",
    "lighthouse",
    "torch",
    "wing",
    "footprints",
    "dna",
)
HERALDICCHARGE_RENAMED = (("king", "ruler_piece"), ("queen", "consort_piece"))
ARTMODE_OLD = (
    "music",
    "poetry",
    "dance",
    "theatre",
    "painting",
    "sculpture",
    "architecture_style",
    "textile",
    "calligraphy",
    "song",
    "epic_poem",
    "play",
    "statue",
    "fresco",
    "tapestry",
    "mosaic",
    "book",
    "carving",
    "architecture_ornament",
)
ARTMODE_NEW = (
    "verbal",
    "musical",
    "movement",
    "flat_image",
    "solid_image",
    "built",
    "worn",
    "culinary",
    "scent",
    "light",
    "recorded",
    "interactive",
    "landscape",
    "body",
    "ritual_performance",
    "textile_image",
    "made_mind_art",
)
ARTMODE_RENAMED = (
    ("song", "musical"),
    ("epic_poem", "verbal"),
    ("play", "ritual_performance"),
    ("statue", "solid_image"),
    ("fresco", "flat_image"),
    ("tapestry", "textile_image"),
    ("mosaic", "flat_image"),
    ("book", "verbal"),
    ("dance", "movement"),
    ("music", "musical"),
    ("carving", "solid_image"),
    ("architecture_ornament", "built"),
    ("poetry", "verbal"),
    ("theatre", "ritual_performance"),
    ("painting", "flat_image"),
    ("sculpture", "solid_image"),
    ("architecture_style", "built"),
    ("textile", "textile_image"),
    ("calligraphy", "flat_image"),
)
SEX_OLD = ("female", "male")
SEX_NEW = ("female", "male", "other")
SEX_RENAMED = ()
PRESERVATIONMETHOD_OLD = ("none", "salted", "iced", "magic")
PRESERVATIONMETHOD_NEW = (
    "none",
    "drying",
    "smoking",
    "curing",
    "pickling",
    "fermenting",
    "chilling",
    "freezing",
    "sealing",
    "canning",
    "irradiating",
    "by_working",
    "living",
)
PRESERVATIONMETHOD_RENAMED = (("salted", "curing"), ("iced", "chilling"), ("magic", "by_working"))
CLERGYFUNCTION_OLD = ("high_priest", "priest", "monk", "inquisitor")
CLERGYFUNCTION_NEW = ("leader", "celebrant", "ascetic", "guardian_of_doctrine", "teacher", "healer", "seer", "keeper_of_sites", "missionary", "judge", "scribe")
CLERGYFUNCTION_RENAMED = (("high_priest", "leader"), ("priest", "celebrant"), ("monk", "ascetic"), ("inquisitor", "guardian_of_doctrine"))
TENETKIND_OLD = (
    "pacifism",
    "holy_war",
    "asceticism",
    "sacred_suffering",
    "purity_of_body",
    "ancestor_veneration",
    "human_sacrifice",
    "animal_sacrifice",
    "celibate_clergy",
    "proselytism",
    "exclusivity",
    "syncretic_openness",
    "monastic_learning",
    "anti_magic",
    "sanctified_magic",
    "judgement_by_deeds",
    "judgement_by_faith",
    "reincarnation",
    "martyrdom_glory",
    "divine_kingship",
    "dietary_law",
    "sacred_species",
    "pilgrimage_duty",
    "souls_rest",
    "void_communion",
    "feeding_the_hunger",
    "whispered_secrets",
    "hidden_god",
)
TENETKIND_NEW = (
    "pacifism",
    "holy_war",
    "asceticism",
    "sacred_suffering",
    "purity_of_body",
    "ancestor_veneration",
    "human_sacrifice",
    "animal_sacrifice",
    "celibate_clergy",
    "proselytism",
    "exclusivity",
    "syncretic_openness",
    "monastic_learning",
    "anti_magic",
    "sanctified_magic",
    "judgement_by_deeds",
    "judgement_by_faith",
    "reincarnation",
    "martyrdom_glory",
    "divine_rule",
    "dietary_law",
    "sacred_species",
    "pilgrimage_duty",
    "souls_rest",
    "void_communion",
    "feeding_the_hunger",
    "whispered_secrets",
    "hidden_god",
)
TENETKIND_RENAMED = (("divine_kingship", "divine_rule"),)
VEHICLEFRAME_OLD = (
    "riding_mount",
    "pack_mount",
    "travois",
    "sledge",
    "handcart",
    "cart",
    "wagon",
    "covered_wagon",
    "carriage",
    "chariot",
    "war_wagon",
    "beast_carrier",
    "rail_car",
    "locomotive",
    "steam_carriage",
    "motor_car",
    "motor_truck",
    "motorcycle",
    "armoured_car",
    "tank",
    "walker",
    "crawler",
    "construct_walker",
    "construct_carrier",
    "battering_ram",
    "siege_tower",
    "mantlet",
    "catapult",
    "trebuchet",
    "ballista",
    "bombard",
    "field_gun",
    "mortar",
    "rocket_battery",
    "raft",
    "canoe",
    "rowboat",
    "boat",
    "river_barge",
    "sailboat",
    "galley",
    "longship",
    "cog",
    "carrack",
    "galleon",
    "frigate",
    "warship",
    "ship_of_the_line",
    "steamship",
    "ironclad",
    "battleship",
    "submarine",
    "living_ship",
    "fire_ship",
    "balloon",
    "airship",
    "glider",
    "ornithopter",
    "sky_sailer",
    "skyship",
    "flying_carriage",
    "aeroplane",
    "rotorcraft",
    "flying_car",
    "flying_construct",
    "orbital_lander",
    "shuttle",
    "solar_sailer",
    "starship",
    "generation_ship",
    "void_ark",
    "cloud_skimmer",
    "aerostat",
    "deep_submersible",
    "burrower",
    "planar_vessel",
    "hovercraft",
    "amphibious_carrier",
    "landing_craft",
    "amphibious_raft",
    "tunnel_cart",
    "mine_train",
    "delving_construct",
    "deep_crawler",
    "diving_bell",
    "attack_submarine",
    "gas_harvester",
    "deep_diver",
    "rift_skiff",
    "planar_ark",
    "divine_vessel",
    "space_fighter",
    "freighter",
    "mining_barge",
    "corvette",
    "dreadnought",
    "jet_fighter",
    "bomber",
    "drone",
    "trireme",
    "coastal_trader",
    "catamaran",
    "fleet_carrier",
    "hover_tank",
    "bicycle",
    "rickshaw",
    "palanquin",
    "tram",
    "maglev",
    "bus",
    "tractor",
    "apc",
    "self_propelled_gun",
    "missile_carrier",
    "motorboat",
    "hydrofoil",
    "container_ship",
    "tanker",
    "destroyer",
    "cruiser",
    "icebreaker",
    "vtol",
    "spaceplane",
    "escape_pod",
    "space_tug",
    "mothership",
    "battle_mech",
    "bioship",
)
VEHICLEFRAME_NEW = (
    "riding_mount",
    "pack_mount",
    "travois",
    "sledge",
    "handcart",
    "cart",
    "wagon",
    "covered_wagon",
    "carriage",
    "chariot",
    "war_wagon",
    "beast_carrier",
    "rail_car",
    "locomotive",
    "steam_carriage",
    "motor_car",
    "motor_truck",
    "motorcycle",
    "armoured_car",
    "tank",
    "walker",
    "crawler",
    "construct_walker",
    "construct_carrier",
    "battering_ram",
    "siege_tower",
    "mantlet",
    "catapult",
    "trebuchet",
    "ballista",
    "bombard",
    "field_gun",
    "mortar",
    "rocket_battery",
    "raft",
    "canoe",
    "rowboat",
    "boat",
    "river_barge",
    "sailboat",
    "galley",
    "longship",
    "cog",
    "carrack",
    "galleon",
    "frigate",
    "warship",
    "ship_of_the_line",
    "steamship",
    "ironclad",
    "battleship",
    "submarine",
    "living_ship",
    "fire_ship",
    "balloon",
    "airship",
    "glider",
    "ornithopter",
    "sky_sailer",
    "skyship",
    "flying_carriage",
    "aeroplane",
    "rotorcraft",
    "flying_car",
    "flying_construct",
    "orbital_lander",
    "shuttle",
    "solar_sailer",
    "starship",
    "generation_ship",
    "void_ark",
    "cloud_skimmer",
    "aerostat",
    "deep_submersible",
    "burrower",
    "planar_vessel",
    "hovercraft",
    "amphibious_carrier",
    "landing_craft",
    "amphibious_raft",
    "tunnel_cart",
    "mine_train",
    "delving_construct",
    "deep_crawler",
    "diving_bell",
    "attack_submarine",
    "gas_harvester",
    "deep_diver",
    "rift_skiff",
    "planar_ark",
    "divine_vessel",
    "space_fighter",
    "freighter",
    "mining_barge",
    "corvette",
    "dreadnought",
    "jet_fighter",
    "bomber",
    "drone",
    "trireme",
    "coastal_trader",
    "catamaran",
    "fleet_carrier",
    "hover_tank",
    "bicycle",
    "rickshaw",
    "palanquin",
    "tram",
    "maglev",
    "bus",
    "tractor",
    "apc",
    "self_propelled_gun",
    "missile_carrier",
    "motorboat",
    "hydrofoil",
    "container_ship",
    "tanker",
    "destroyer",
    "cruiser",
    "icebreaker",
    "vtol",
    "spaceplane",
    "escape_pod",
    "space_tug",
    "carrier_vessel",
    "battle_mech",
    "bioship",
)
VEHICLEFRAME_RENAMED = (("mothership", "carrier_vessel"),)
COOKINGMETHOD_OLD = (
    "raw",
    "boiled",
    "stewed",
    "steamed",
    "roasted",
    "grilled",
    "baked",
    "fried",
    "smoked",
    "dried",
    "cured",
    "pickled",
    "fermented",
    "braised",
    "simmered",
    "ground",
    "pressed",
    "synthesised",
    "printed",
    "vat_grown",
    "freeze_dried",
    "irradiated",
    "conjured",
)
COOKINGMETHOD_NEW = (
    "raw",
    "boiled",
    "stewed",
    "steamed",
    "roasted",
    "grilled",
    "baked",
    "fried",
    "smoked",
    "dried",
    "cured",
    "pickled",
    "fermented",
    "braised",
    "simmered",
    "ground",
    "pressed",
    "synthesised",
    "printed",
    "vat_grown",
    "freeze_dried",
    "irradiated",
    "conjured",
    "infused",
    "distilled",
    "churned",
    "sprouted",
    "alkali_treated",
    "cultured",
    "cured_with_mineral",
    "aged",
    "extruded",
    "pressure_cooked",
)
COOKINGMETHOD_RENAMED = ()
ENTITYFLAG_OLD = (
    "disaster",
    "dormant",
    "lost",
    "dead_language",
    "decipherable",
    "previous_creation",
    "ruin",
    "rebuilt",
    "remnant",
    "void",
    "cursed",
    "godless",
    "seeking_god",
    "empire",
    "federation",
    "independent",
    "colony",
    "pioneer",
    "golden_age",
    "immortal",
    "chimera",
    "mutation",
    "mutant",
    "mutated",
    "discovery",
    "native",
    "revelation",
    "soul_descended",
    "soul_bound",
    "soul_harvester",
    "crossed_to_the_dead",
    "wonder",
    "chosen",
    "manifested",
    "born_of_belief",
    "corrupted_memory",
    "fairy_tale",
    "name_from_language",
    "fixed_name",
    "species_became_people",
    "original_resource",
    "cosmic_monopoly",
    "outer_cult",
    "whisper_source",
    "nameless",
    "escaped",
    "megafauna",
    "invasive",
    "worships_planet",
    "worships_star",
    "worships_galaxy",
    "planet_closed",
    "burned",
    "cosmic_plague",
    "mirror",
    "mirror_born",
    "oathbreaker",
    "exile",
    "omen",
    "time_echo",
    "two_timed",
    "empty_tomb",
    "resurrection_complete",
    "protected_from_disaster",
    "mechanics_weighed",
    "depleting",
    "syncretic",
    "returned_to_old_god",
    "revived_language",
    "on_watch",
    "mocked",
    "protected_from_ruin",
    "spared_soul",
    "ghost",
    "wizard",
    "age_changer",
    "time_returned",
    "legendary",
    "prophet",
    "bloodline_curse",
    "essence_drained",
    "returned_from_death",
    "saw_the_creator",
    "deified",
    "protected",
    "depleted",
    "agent_selected",
    "capital",
    "abandoned",
    "dissolved",
    "desolate",
    "razed",
    "fell_in_battle",
    "died_in_siege",
    "died_in_disaster",
    "died_of_plague",
    "slain_in_captivity",
    "doomed",
    "fate_shielded",
    "commemoration",
    "estranged_by_plague",
    "endangered",
    "extinct",
    "pilgrimage_site",
    "repealed",
    "merged",
    "disbanded",
    "assimilated",
    "forgotten",
    "swallowed",
    "designed_people",
)
ENTITYFLAG_NEW = (
    "disaster",
    "dormant",
    "lost",
    "dead_language",
    "decipherable",
    "previous_creation",
    "ruin",
    "rebuilt",
    "remnant",
    "void",
    "cursed",
    "godless",
    "seeking_god",
    "empire",
    "federation",
    "independent",
    "colony",
    "pioneer",
    "golden_age",
    "immortal",
    "merged_species",
    "mutation",
    "mutant",
    "mutated",
    "discovery",
    "native",
    "revelation",
    "soul_descended",
    "soul_bound",
    "soul_harvester",
    "crossed_to_the_dead",
    "wonder",
    "chosen",
    "manifested",
    "born_of_belief",
    "corrupted_memory",
    "fairy_tale",
    "name_from_language",
    "fixed_name",
    "species_became_people",
    "designed_people",
    "original_resource",
    "cosmic_monopoly",
    "outer_cult",
    "whisper_source",
    "nameless",
    "escaped",
    "megafauna",
    "invasive",
    "worships_planet",
    "worships_star",
    "worships_galaxy",
    "planet_closed",
    "burned",
    "cosmic_plague",
    "mirror",
    "mirror_born",
    "oathbreaker",
    "exile",
    "omen",
    "time_echo",
    "two_timed",
    "empty_tomb",
    "resurrection_complete",
    "protected_from_disaster",
    "mechanics_weighed",
    "depleting",
    "syncretic",
    "returned_to_old_god",
    "revived_language",
    "on_watch",
    "mocked",
    "protected_from_ruin",
    "spared_soul",
    "ghost",
    "wizard",
    "age_changer",
    "time_returned",
    "legendary",
    "prophet",
    "bloodline_curse",
    "essence_drained",
    "returned_from_death",
    "saw_the_creator",
    "deified",
    "protected",
    "depleted",
    "agent_selected",
    "capital",
    "abandoned",
    "dissolved",
    "desolate",
    "razed",
    "fell_in_battle",
    "died_in_siege",
    "died_in_disaster",
    "died_of_plague",
    "slain_in_captivity",
    "doomed",
    "fate_shielded",
    "commemoration",
    "estranged_by_plague",
    "endangered",
    "extinct",
    "pilgrimage_site",
    "repealed",
    "merged",
    "disbanded",
    "assimilated",
    "forgotten",
    "lost_in_disaster",
)
ENTITYFLAG_RENAMED = (("swallowed", "lost_in_disaster"), ("chimera", "merged_species"))
TRAVELMETHOD_OLD = (
    "ancient_gate",
    "space_fold",
    "light_sail",
    "cosmic_mount",
    "dream_journey",
    "river_of_dead",
    "divine_bridge",
    "slingshot_orbit",
    "swallowed",
    "wormhole",
    "void_ark",
    "galactic_gate",
    "filament_lane",
    "dimensional_rift",
    "planar_door",
    "rocketry",
)
TRAVELMETHOD_NEW = (
    "ancient_gate",
    "space_fold",
    "light_sail",
    "carrier_mount",
    "dream_journey",
    "death_current",
    "divine_bridge",
    "slingshot_orbit",
    "carried_within",
    "wormhole",
    "void_ark",
    "galactic_gate",
    "filament_lane",
    "dimensional_rift",
    "planar_door",
    "rocketry",
)
TRAVELMETHOD_RENAMED = (("cosmic_mount", "carrier_mount"), ("river_of_dead", "death_current"), ("swallowed", "carried_within"))
KINSHIPDESCENT_OLD = ("patrilineal", "matrilineal", "bilateral", "double", "ambilineal")
KINSHIPDESCENT_NEW = ("through_first_line", "through_second_line", "bilateral", "double", "ambilineal")
KINSHIPDESCENT_RENAMED = (("patrilineal", "through_first_line"), ("matrilineal", "through_second_line"))
RESIDENCERULE_OLD = ("patrilocal", "matrilocal", "neolocal", "avunculocal")
RESIDENCERULE_NEW = ("with_first_family", "with_second_family", "new_household", "with_kin_of_the_first_line")
RESIDENCERULE_RENAMED = (
    ("patrilocal", "with_first_family"),
    ("matrilocal", "with_second_family"),
    ("neolocal", "new_household"),
    ("avunculocal", "with_kin_of_the_first_line"),
)
KINTERMSYSTEM_OLD = ("distinct", "parallel_as_siblings", "all_as_siblings")
KINTERMSYSTEM_NEW = ("generational", "lineal", "bifurcate_merging", "bifurcate_collateral", "cross_parallel", "descriptive")
KINTERMSYSTEM_RENAMED = (("distinct", "lineal"), ("parallel_as_siblings", "bifurcate_merging"), ("all_as_siblings", "generational"))
CULTIVATIONMETHOD_OLD = ("selective_breeding", "cultivation", "shaping", "engineering", "synthesis", "binding", "cloning", "chimera", "induction")
CULTIVATIONMETHOD_NEW = ("selective_breeding", "cultivation", "shaping", "engineering", "synthesis", "binding", "cloning", "merging", "induction")
CULTIVATIONMETHOD_RENAMED = (("chimera", "merging"),)
DIET_OLD = (
    "omnivore",
    "herbivore",
    "carnivore",
    "piscivore",
    "scavenger",
    "sanguivore",
    "lithovore",
    "essence_feeder",
    "phototroph",
    "filter",
    "photosynthetic",
    "mineral",
    "soul",
    "void",
)
DIET_NEW = ("herbivore", "carnivore", "omnivore", "scavenger", "filter", "photosynthetic", "mineral", "soul", "void", "piscivore", "sanguivore")
DIET_RENAMED = (("lithovore", "mineral"), ("essence_feeder", "soul"), ("phototroph", "photosynthetic"))
FUNERALCUSTOM_OLD = (
    "burial",
    "cremation",
    "sky_burial",
    "sea_burial",
    "entombment",
    "ancestor_shrine",
    "endocannibalism",
    "reanimation",
    "soul_binding",
    "burning",
    "exposure",
    "nameless",
    "none",
)
FUNERALCUSTOM_NEW = (
    "burial",
    "cremation",
    "sky_burial",
    "sea_burial",
    "entombment",
    "ancestor_shrine",
    "endocannibalism",
    "reanimation",
    "soul_binding",
    "nameless",
    "none",
)
FUNERALCUSTOM_RENAMED = (("burning", "cremation"), ("exposure", "sky_burial"))
INHERITANCECUSTOM_OLD = ("gavelkind", "primogeniture", "ultimogeniture", "matrilineal", "elective", "by_merit")
INHERITANCECUSTOM_NEW = ("equal_shares", "primogeniture", "ultimogeniture", "through_second_line", "elective", "by_merit")
INHERITANCECUSTOM_RENAMED = (("matrilineal", "through_second_line"), ("gavelkind", "equal_shares"))
PHENOMENONKIND_OLD = (
    "eternal_storm",
    "time_slip",
    "leak_wound",
    "ley_nexus_flare",
    "god_corpse_aura",
    "living_fog",
    "crystal_bloom",
    "dead_zone",
    "mirror_lake",
    "gravity_well",
    "singing_stones",
    "aurora_permanent",
    "ghost_road",
    "blight",
)
PHENOMENONKIND_NEW = (
    "lasting_storm",
    "time_distortion",
    "outside_opening",
    "power_surge",
    "divine_residue",
    "moving_fog",
    "mineral_growth",
    "barren_ground",
    "distant_view",
    "gravity_anomaly",
    "sounding_ground",
    "lasting_lights",
    "path_of_the_dead",
    "blight",
)
PHENOMENONKIND_RENAMED = (
    ("eternal_storm", "lasting_storm"),
    ("time_slip", "time_distortion"),
    ("leak_wound", "outside_opening"),
    ("ley_nexus_flare", "power_surge"),
    ("god_corpse_aura", "divine_residue"),
    ("living_fog", "moving_fog"),
    ("crystal_bloom", "mineral_growth"),
    ("dead_zone", "barren_ground"),
    ("mirror_lake", "distant_view"),
    ("gravity_well", "gravity_anomaly"),
    ("singing_stones", "sounding_ground"),
    ("aurora_permanent", "lasting_lights"),
    ("ghost_road", "path_of_the_dead"),
)
PLACEKIND_OLD = (
    "mountain",
    "peak",
    "pass",
    "forest",
    "grove",
    "river",
    "ford",
    "lake",
    "spring",
    "cave",
    "cavern_system",
    "ruin",
    "island",
    "swamp",
    "well",
    "valley",
    "cliff",
    "volcano",
    "crater",
    "battlefield",
    "burial_ground",
    "lair",
    "nexus",
    "shrine_site",
    "god_corpse",
    "mine_site",
    "harbour_site",
    "crossroads",
    "wreck_site",
    "megastructure_ruin",
    "anomaly",
    "debris_field",
    "reef",
    "glacier",
    "dunes",
    "canyon",
    "oasis",
    "geyser",
)
PLACEKIND_NEW = (
    "mountain",
    "peak",
    "pass",
    "forest",
    "grove",
    "river",
    "ford",
    "lake",
    "spring",
    "cave",
    "cavern_system",
    "ruin",
    "island",
    "swamp",
    "well",
    "valley",
    "cliff",
    "volcano",
    "crater",
    "battlefield",
    "burial_ground",
    "lair",
    "nexus",
    "shrine_site",
    "dead_god_site",
    "mine_site",
    "harbour_site",
    "crossroads",
    "wreck_site",
    "megastructure_ruin",
    "anomaly",
    "debris_field",
    "reef",
    "glacier",
    "dunes",
    "canyon",
    "oasis",
    "geyser",
)
PLACEKIND_RENAMED = (("god_corpse", "dead_god_site"),)
GOVERNMENTKIND_OLD = (
    "chiefdom",
    "monarchy",
    "theocracy",
    "oligarchy",
    "republic",
    "tribal_confederation",
    "empire",
    "hive_council",
    "god_kingdom",
    "occupation",
    "junta",
    "corporate_state",
    "technocracy",
    "federation",
    "commune",
    "machine_rule",
    "colonial_administration",
)
GOVERNMENTKIND_NEW = (
    "chiefdom",
    "monarchy",
    "theocracy",
    "oligarchy",
    "republic",
    "tribal_confederation",
    "empire",
    "hive_council",
    "god_realm",
    "occupation",
    "junta",
    "corporate_state",
    "technocracy",
    "federation",
    "commune",
    "machine_rule",
    "colonial_administration",
)
GOVERNMENTKIND_RENAMED = (("god_kingdom", "god_realm"),)
SOILKIND_OLD = ("thin", "loam", "clay", "sand", "volcanic", "peat", "salt", "ash", "crystal", "bone")
SOILKIND_NEW = (
    "thin",
    "loam",
    "clay",
    "sand",
    "volcanic",
    "peat",
    "saline",
    "tephra",
    "crystalline",
    "calcareous",
    "laterite",
    "permafrost",
    "regolith",
    "artificial",
)
SOILKIND_RENAMED = (("salt", "saline"), ("ash", "tephra"), ("crystal", "crystalline"), ("bone", "calcareous"))
REGISTRYKIND_OLD = ("land_title", "debt", "sale", "dowry", "indenture", "patent", "pattern", "mind_state", "line", "company", "birth", "death", "citizenship")
REGISTRYKIND_NEW = (
    "land_title",
    "debt",
    "sale",
    "union_portion",
    "indenture",
    "patent",
    "pattern",
    "mind_state",
    "line",
    "company",
    "birth",
    "death",
    "citizenship",
)
REGISTRYKIND_RENAMED = (("dowry", "union_portion"),)
CIRCLEKIND_OLD = ("drinking_hall", "poets_circle", "hunting_lodge", "secret_society", "study_circle", "prayer_circle", "music_circle", "craft_circle")
CIRCLEKIND_NEW = ("drinking_circle", "poets_circle", "hunting_circle", "secret_society", "study_circle", "prayer_circle", "music_circle", "craft_circle")
CIRCLEKIND_RENAMED = (("drinking_hall", "drinking_circle"), ("hunting_lodge", "hunting_circle"))
TITLETIER_OLD = ("lordship", "county", "duchy", "kingdom", "empire", "see", "archsee", "high_seat", "captaincy", "guildmastership")
TITLETIER_NEW = ("local", "district", "regional", "realm", "imperial", "faith_local", "faith_high", "faith_supreme", "military", "guild")
TITLETIER_RENAMED = (
    ("lordship", "local"),
    ("county", "district"),
    ("duchy", "regional"),
    ("kingdom", "realm"),
    ("empire", "imperial"),
    ("see", "faith_local"),
    ("archsee", "faith_high"),
    ("high_seat", "faith_supreme"),
    ("captaincy", "military"),
    ("guildmastership", "guild"),
)
UNIONEXCHANGE_OLD = ("to_one_family", "from_one_family", "mutual", "none")
UNIONEXCHANGE_NEW = ("to_one_family", "from_one_family", "mutual", "service", "none")
UNIONEXCHANGE_RENAMED = ()
PARTNERSCOPE_OLD = ("none", "people", "class", "caste", "faith", "house")
PARTNERSCOPE_NEW = ("none", "people", "class", "caste", "faith", "house", "line", "moiety")
PARTNERSCOPE_RENAMED = ()
MATERIALORIGIN_OLD = ("catalog", "god_remains", "dead_star", "beast", "leak_crystal", "research", "divine")
MATERIALORIGIN_NEW = ("catalog", "dead_god", "star", "beast", "rift", "research", "god_gift")
MATERIALORIGIN_RENAMED = (("god_remains", "dead_god"), ("dead_star", "star"), ("leak_crystal", "rift"), ("divine", "god_gift"))
LEGENDARCHETYPE_OLD = (
    "hero_quest",
    "monster",
    "trickster",
    "creation",
    "flood",
    "betrayal",
    "lost_paradise",
    "chosen_one",
    "cursed_line",
    "return_of_the_king",
    "haunted_place",
)
LEGENDARCHETYPE_NEW = (
    "hero_quest",
    "monster",
    "trickster",
    "creation",
    "world_disaster",
    "betrayal",
    "lost_golden_age",
    "chosen_one",
    "cursed_line",
    "return_of_a_ruler",
    "haunted_place",
    "founding",
    "exile",
    "transformation",
    "bargain",
    "sacrifice",
    "rivalry",
    "discovery",
    "deception",
    "union",
    "ascent",
    "fall",
)
LEGENDARCHETYPE_RENAMED = (("flood", "world_disaster"), ("lost_paradise", "lost_golden_age"), ("return_of_the_king", "return_of_a_ruler"))
BEINGKIND_OLD = (
    "planar_native",
    "dimension_walker",
    "rift_spawn",
    "higher_dimensional",
    "star_eater",
    "nebula_mind",
    "galactic_leviathan",
    "void_shepherd",
    "echo",
    "time_wanderer",
    "cosmic_titan",
    "veil_warden",
    "plane_sovereign",
    "swarm_intelligence",
    "living_constellation",
)
BEINGKIND_NEW = (
    "planar_native",
    "dimension_traveller",
    "rift_born",
    "higher_dimensional",
    "star_feeder",
    "cloud_mind",
    "galaxy_scale_being",
    "void_keeper",
    "mirrored_double",
    "time_traveller",
    "system_scale_being",
    "boundary_keeper",
    "dimension_ruler",
    "swarm_intelligence",
    "star_pattern_mind",
)
BEINGKIND_RENAMED = (
    ("dimension_walker", "dimension_traveller"),
    ("rift_spawn", "rift_born"),
    ("star_eater", "star_feeder"),
    ("nebula_mind", "cloud_mind"),
    ("galactic_leviathan", "galaxy_scale_being"),
    ("void_shepherd", "void_keeper"),
    ("echo", "mirrored_double"),
    ("time_wanderer", "time_traveller"),
    ("cosmic_titan", "system_scale_being"),
    ("veil_warden", "boundary_keeper"),
    ("plane_sovereign", "dimension_ruler"),
    ("living_constellation", "star_pattern_mind"),
)
TRADITIONFUNCTION_OLD = (
    "festival",
    "fast",
    "funeral_rite",
    "initiation",
    "marriage_rite",
    "coming_of_age",
    "taboo",
    "offering",
    "pilgrimage",
    "hospitality_law",
    "duel_custom",
    "mourning",
    "harvest_rite",
    "war_dance",
    "scar_rite",
    "ancestor_feast",
    "siesta",
    "night_vigil",
)
TRADITIONFUNCTION_NEW = (
    "festival",
    "fast",
    "rite_of_passage",
    "taboo",
    "offering",
    "pilgrimage",
    "hospitality",
    "duel_custom",
    "mourning",
    "seasonal_rite",
    "martial_display",
    "body_marking",
    "ancestral_rite",
    "rest_custom",
    "vigil",
    "gift_custom",
    "purification",
    "commemoration",
    "competition",
)
TRADITIONFUNCTION_RENAMED = (
    ("siesta", "rest_custom"),
    ("war_dance", "martial_display"),
    ("scar_rite", "body_marking"),
    ("ancestor_feast", "ancestral_rite"),
    ("night_vigil", "vigil"),
    ("harvest_rite", "seasonal_rite"),
    ("hospitality_law", "hospitality"),
    ("funeral_rite", "rite_of_passage"),
    ("initiation", "rite_of_passage"),
    ("marriage_rite", "rite_of_passage"),
    ("coming_of_age", "rite_of_passage"),
)
RETYPED = (
    ("ages", "variant", "variant", APOCALYPSEVARIANT_OLD, APOCALYPSEVARIANT_NEW, APOCALYPSEVARIANT_RENAMED, True),
    ("cosmos", "apocalypse_variant", "apocalypse_variant", APOCALYPSEVARIANT_OLD, APOCALYPSEVARIANT_NEW, APOCALYPSEVARIANT_RENAMED, True),
    ("species_use_kinds", "base_use", "base_use", ANIMALROLE_OLD, ANIMALROLE_NEW, ANIMALROLE_RENAMED, False),
    ("species_uses", "use", "use", ANIMALROLE_OLD, ANIMALROLE_NEW, ANIMALROLE_RENAMED, False),
    ("contests", "kind", "kind", CONTESTKIND_OLD, CONTESTKIND_NEW, CONTESTKIND_RENAMED, False),
    ("contests", "stake", "stake", CONTESTSTAKE_OLD, CONTESTSTAKE_NEW, CONTESTSTAKE_RENAMED, False),
    ("creature_anatomy", "temperament", "temperament", TEMPERAMENT_OLD, TEMPERAMENT_NEW, TEMPERAMENT_RENAMED, False),
    ("living_profiles", "temperament", "temperament", TEMPERAMENT_OLD, TEMPERAMENT_NEW, TEMPERAMENT_RENAMED, True),
    ("creature_anatomy", "hoards", "hoards", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("power_source_resistances", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("constructs", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, False),
    ("currencies", "metal", "metal", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("place_secrets", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("production_runs", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("structure_designs", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("trade_flows", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("world_materials", "base_kind", "base_kind", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("community_stocks", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("equipment_models", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("node_materials", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("replicator_lines", "feedstock", "feedstock", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, False),
    ("resource_profiles", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("resource_profiles", "byproduct_material", "byproduct_material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("structure_design_sections", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("structure_sections", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, True),
    ("prostheses", "material", "material", MATERIALKIND_OLD, MATERIALKIND_NEW, MATERIALKIND_RENAMED, False),
    ("house_resemblances", "locus", "locus", LOCUS_OLD, LOCUS_NEW, LOCUS_RENAMED, False),
    ("ledger_entries", "action_kind", "action_kind", ACTIONKIND_OLD, ACTIONKIND_NEW, ACTIONKIND_RENAMED, False),
    ("action_records", "kind", "kind", ACTIONKIND_OLD, ACTIONKIND_NEW, ACTIONKIND_RENAMED, False),
    ("loop_signals", "loop", "loop", BALANCELOOP_OLD, BALANCELOOP_NEW, BALANCELOOP_RENAMED, False),
    ("mortal_perks", "perk", "perk", PERKKIND_OLD, PERKKIND_NEW, PERKKIND_RENAMED, False),
    ("transform_prospects", "kind", "kind", TRANSFORMKIND_OLD, TRANSFORMKIND_NEW, TRANSFORMKIND_RENAMED, False),
    ("transformations", "kind", "kind", TRANSFORMKIND_OLD, TRANSFORMKIND_NEW, TRANSFORMKIND_RENAMED, False),
    ("games", "kind", "kind", GAMECATEGORY_OLD, GAMECATEGORY_NEW, GAMECATEGORY_RENAMED, False),
    ("world_ends", "state", "state", WORLDEND_OLD, WORLDEND_NEW, WORLDEND_RENAMED, False),
    ("chronicle", "kind", "kind", CHRONICLEKIND_OLD, CHRONICLEKIND_NEW, CHRONICLEKIND_RENAMED, False),
    ("entities", "engine_kind", "engine_kind", ENGINEKIND_OLD, ENGINEKIND_NEW, ENGINEKIND_RENAMED, True),
    ("entities", "mortal_role", "mortal_role", MORTALROLE_OLD, MORTALROLE_NEW, MORTALROLE_RENAMED, True),
    ("traits", "trait", "trait", TRAITKIND_OLD, TRAITKIND_NEW, TRAITKIND_RENAMED, False),
    ("arms", "charge", "charge", HERALDICCHARGE_OLD, HERALDICCHARGE_NEW, HERALDICCHARGE_RENAMED, False),
    ("arms", "charge_two", "charge_two", HERALDICCHARGE_OLD, HERALDICCHARGE_NEW, HERALDICCHARGE_RENAMED, False),
    ("arms", "charge_three", "charge_three", HERALDICCHARGE_OLD, HERALDICCHARGE_NEW, HERALDICCHARGE_RENAMED, False),
    ("arms", "supporter", "supporter", HERALDICCHARGE_OLD, HERALDICCHARGE_NEW, HERALDICCHARGE_RENAMED, False),
    ("arms", "crest", "crest", HERALDICCHARGE_OLD, HERALDICCHARGE_NEW, HERALDICCHARGE_RENAMED, False),
    ("art_form_profiles", "discipline", "discipline", ARTMODE_OLD, ARTMODE_NEW, ARTMODE_RENAMED, False),
    ("artwork_profiles", "medium", "medium", ARTMODE_OLD, ARTMODE_NEW, ARTMODE_RENAMED, False),
    ("community_cohorts", "sex", "sex", SEX_OLD, SEX_NEW, SEX_RENAMED, False),
    ("event_casualties", "sex", "sex", SEX_OLD, SEX_NEW, SEX_RENAMED, False),
    ("convoys", "preservation", "preservation", PRESERVATIONMETHOD_OLD, PRESERVATIONMETHOD_NEW, PRESERVATIONMETHOD_RENAMED, False),
    ("cult_offices", "kind", "kind", CLERGYFUNCTION_OLD, CLERGYFUNCTION_NEW, CLERGYFUNCTION_RENAMED, False),
    ("cult_tenets", "tenet", "tenet", TENETKIND_OLD, TENETKIND_NEW, TENETKIND_RENAMED, False),
    ("designs", "frame", "frame", VEHICLEFRAME_OLD, VEHICLEFRAME_NEW, VEHICLEFRAME_RENAMED, True),
    ("vessel_profiles", "frame", "frame", VEHICLEFRAME_OLD, VEHICLEFRAME_NEW, VEHICLEFRAME_RENAMED, False),
    ("dishes", "method", "method", COOKINGMETHOD_OLD, COOKINGMETHOD_NEW, COOKINGMETHOD_RENAMED, False),
    ("entity_flags", "flag", "flag", ENTITYFLAG_OLD, ENTITYFLAG_NEW, ENTITYFLAG_RENAMED, False),
    ("horizon_intuitions", "method", "method", TRAVELMETHOD_OLD, TRAVELMETHOD_NEW, TRAVELMETHOD_RENAMED, True),
    ("routes", "method", "method", TRAVELMETHOD_OLD, TRAVELMETHOD_NEW, TRAVELMETHOD_RENAMED, False),
    ("kinship_systems", "descent", "descent", KINSHIPDESCENT_OLD, KINSHIPDESCENT_NEW, KINSHIPDESCENT_RENAMED, False),
    ("kinship_systems", "residence", "residence", RESIDENCERULE_OLD, RESIDENCERULE_NEW, RESIDENCERULE_RENAMED, False),
    ("kinship_systems", "cousin_terms", "cousin_terms", KINTERMSYSTEM_OLD, KINTERMSYSTEM_NEW, KINTERMSYSTEM_RENAMED, False),
    ("living_lines", "method", "method", CULTIVATIONMETHOD_OLD, CULTIVATIONMETHOD_NEW, CULTIVATIONMETHOD_RENAMED, False),
    ("people_biology", "diet", "diet", DIET_OLD, DIET_NEW, DIET_RENAMED, False),
    ("species_profiles", "diet", "diet", DIET_OLD, DIET_NEW, DIET_RENAMED, False),
    ("people_culture", "funeral_rite", "funeral_rite", FUNERALCUSTOM_OLD, FUNERALCUSTOM_NEW, FUNERALCUSTOM_RENAMED, False),
    ("soul_judgements", "rite", "rite", FUNERALCUSTOM_OLD, FUNERALCUSTOM_NEW, FUNERALCUSTOM_RENAMED, False),
    ("spirit_profiles", "rite", "rite", FUNERALCUSTOM_OLD, FUNERALCUSTOM_NEW, FUNERALCUSTOM_RENAMED, False),
    ("tradition_profiles", "funeral_rite", "funeral_rite", FUNERALCUSTOM_OLD, FUNERALCUSTOM_NEW, FUNERALCUSTOM_RENAMED, True),
    ("people_culture", "inheritance", "inheritance", INHERITANCECUSTOM_OLD, INHERITANCECUSTOM_NEW, INHERITANCECUSTOM_RENAMED, False),
    ("phenomenon_profiles", "kind", "kind", PHENOMENONKIND_OLD, PHENOMENONKIND_NEW, PHENOMENONKIND_RENAMED, False),
    ("place_profiles", "kind", "kind", PLACEKIND_OLD, PLACEKIND_NEW, PLACEKIND_RENAMED, False),
    ("polity_profiles", "government", "government", GOVERNMENTKIND_OLD, GOVERNMENTKIND_NEW, GOVERNMENTKIND_RENAMED, False),
    ("region_environment", "soil", "soil", SOILKIND_OLD, SOILKIND_NEW, SOILKIND_RENAMED, False),
    ("registries", "kind", "kind", REGISTRYKIND_OLD, REGISTRYKIND_NEW, REGISTRYKIND_RENAMED, False),
    ("social_circles", "kind", "kind", CIRCLEKIND_OLD, CIRCLEKIND_NEW, CIRCLEKIND_RENAMED, False),
    ("title_profiles", "rank", "rank", TITLETIER_OLD, TITLETIER_NEW, TITLETIER_RENAMED, False),
    ("union_customs", "exchange", "exchange", UNIONEXCHANGE_OLD, UNIONEXCHANGE_NEW, UNIONEXCHANGE_RENAMED, False),
    ("union_customs", "endogamy", "endogamy", PARTNERSCOPE_OLD, PARTNERSCOPE_NEW, PARTNERSCOPE_RENAMED, False),
    ("union_customs", "exogamy", "exogamy", PARTNERSCOPE_OLD, PARTNERSCOPE_NEW, PARTNERSCOPE_RENAMED, False),
    ("world_materials", "origin", "origin", MATERIALORIGIN_OLD, MATERIALORIGIN_NEW, MATERIALORIGIN_RENAMED, False),
    ("legend_profiles", "archetype", "archetype", LEGENDARCHETYPE_OLD, LEGENDARCHETYPE_NEW, LEGENDARCHETYPE_RENAMED, False),
    ("cosmic_being_profiles", "being_kind", "being_kind", BEINGKIND_OLD, BEINGKIND_NEW, BEINGKIND_RENAMED, False),
    ("tradition_profiles", "kind", "kind", TRADITIONFUNCTION_OLD, TRADITIONFUNCTION_NEW, TRADITIONFUNCTION_RENAMED, False),
)


def enum_of(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=40)


def alter(table: str, column: str, name: str, before: tuple[str, ...], after: tuple[str, ...], *, nullable: bool) -> None:
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column(column, existing_type=enum_of(before, name), type_=enum_of(after, name), existing_nullable=nullable)


def retype(forward: bool) -> None:
    for table, column, name, old, new, renamed, nullable in RETYPED:
        before, after = (old, new) if forward else (new, old)
        wide = tuple(dict.fromkeys((*before, *after)))
        alter(table, column, name, before, wide, nullable=nullable)
        for first, second in renamed:
            source, target = (first, second) if forward else (second, first)
            op.execute(sa.text(f"UPDATE {table} SET {column} = :target WHERE {column} = :source").bindparams(target=target, source=source))
        gone = ", ".join(f"'{value}'" for value in wide if value not in after)
        if gone:
            op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IN ({gone})" if nullable else f"DELETE FROM {table} WHERE {column} IN ({gone})")
        alter(table, column, name, wide, after, nullable=nullable)


COPY_COLUMNS = ("species_entity_id", "product", "commodity", "material", "world_material_id", "rate")
PRODUCT_PARTS = {
    "meat": "flesh",
    "hide": "hide",
    "bone": "bone",
    "ivory": "tusk",
    "chitin": "shell",
    "venom": "venom",
    "silk": "fibre",
    "wool": "fibre",
    "milk": "milk",
    "feathers": "feathers",
    "magic_reagents": "reagent",
    "dragonbone": "bone",
    "eggs": "eggs",
    "grain": "seed",
    "tuber": "root",
    "fibre": "fibre",
    "dye": "dye",
    "timber": "wood",
    "fruit": "fruit",
    "herb": "leaf",
    "brew_base": "seed",
    "reagent": "reagent",
    "poison": "toxin",
}


def copy_products(source: str, target: str) -> None:
    columns = ", ".join(COPY_COLUMNS)
    extra = ", locked" if target == "species_products" else ""
    value = ", '[]'" if target == "species_products" else ""
    op.execute(f"INSERT INTO {target} ({columns}{extra}) SELECT {columns}{value} FROM {source}")


def named_checks(table: str) -> set[str]:
    return {str(check["name"]) for check in sa.inspect(op.get_bind()).get_check_constraints(table)}


def upgrade() -> None:
    op.execute("CREATE TABLE aes_culture AS SELECT people_entity_id AS id, aesthetic FROM people_culture")
    op.execute("CREATE TABLE aes_structure AS SELECT structure_entity_id AS id, aesthetic FROM structure_profiles WHERE aesthetic IS NOT NULL")
    op.execute("CREATE TABLE g4c_marriage AS SELECT id, kind FROM marriages")
    op.execute("CREATE TABLE g4c_culture AS SELECT people_entity_id AS id, marriage, endogamous FROM people_culture")
    op.execute("CREATE TABLE g4c_kin AS SELECT people_entity_id AS id, preference, payment, payment_value FROM kinship_systems")
    op.execute(
        "CREATE TABLE g4b_passage AS SELECT tradition_entity_id AS id, kind FROM tradition_profiles WHERE kind IN ('funeral_rite', 'initiation', 'marriage_rite', 'coming_of_age')"
    )
    retype(True)
    op.execute("UPDATE entities SET subtype = 'animated work' WHERE subtype = 'golem'")
    op.execute("UPDATE entities SET subtype = 'merged species' WHERE subtype = 'chimera'")
    op.execute("UPDATE ledger_entries SET tool = 'hinder_return' WHERE tool = 'scatter_bones'")
    op.execute("UPDATE ledger_entries SET tool = 'sibling:hinder_return' WHERE tool = 'sibling:scatter'")
    op.execute("UPDATE ledger_entries SET tool = 'species:merge' WHERE tool = 'species:chimera'")
    op.execute("UPDATE chronicle SET template_key = 'creatures.species_merged' WHERE template_key = 'creatures.chimera_woven'")
    op.execute("UPDATE chronicle SET template_key = 'tools.mortal.species_merged' WHERE template_key = 'tools.mortal.chimera'")
    op.execute("UPDATE chronicle SET template_key = 'gods.death.return_hindered' WHERE template_key = 'gods.death.scatter'")
    op.execute(
        "UPDATE law_profiles SET params = json_remove(json_set(params, '$.merging', json_extract(params, '$.chimera')), '$.chimera') WHERE kind = 'living_craft_law' AND json_extract(params, '$.chimera') IS NOT NULL"
    )
    op.execute("UPDATE OR IGNORE preferences SET target = 'musical' WHERE kind = 'art_form' AND target = 'song'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'verbal' WHERE kind = 'art_form' AND target = 'epic_poem'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'ritual_performance' WHERE kind = 'art_form' AND target = 'play'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'solid_image' WHERE kind = 'art_form' AND target = 'statue'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'fresco'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'textile_image' WHERE kind = 'art_form' AND target = 'tapestry'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'mosaic'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'verbal' WHERE kind = 'art_form' AND target = 'book'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'movement' WHERE kind = 'art_form' AND target = 'dance'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'musical' WHERE kind = 'art_form' AND target = 'music'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'solid_image' WHERE kind = 'art_form' AND target = 'carving'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'built' WHERE kind = 'art_form' AND target = 'architecture_ornament'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'verbal' WHERE kind = 'art_form' AND target = 'poetry'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'ritual_performance' WHERE kind = 'art_form' AND target = 'theatre'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'painting'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'solid_image' WHERE kind = 'art_form' AND target = 'sculpture'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'built' WHERE kind = 'art_form' AND target = 'architecture_style'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'textile_image' WHERE kind = 'art_form' AND target = 'textile'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'flat_image' WHERE kind = 'art_form' AND target = 'calligraphy'")
    op.execute(
        "DELETE FROM preferences WHERE kind = 'art_form' AND target IN ('song', 'epic_poem', 'play', 'statue', 'fresco', 'tapestry', 'mosaic', 'book', 'dance', 'music', 'carving', 'architecture_ornament', 'poetry', 'theatre', 'painting', 'sculpture', 'architecture_style', 'textile', 'calligraphy')"
    )
    op.execute(
        "UPDATE afterlife_strata SET criteria = replace(replace(criteria, '\"burning\"', '\"cremation\"'), '\"exposure\"', '\"sky_burial\"') WHERE criteria IS NOT NULL"
    )
    op.execute("UPDATE entities SET subtype = 'sworn warrior' WHERE subtype = 'knight'")
    op.execute("UPDATE entities SET subtype = 'ascetic' WHERE subtype = 'monk'")
    op.create_table(
        "kind_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "concept",
            sa.Enum(
                "good",
                "dish",
                "drink",
                "cuisine",
                "garment",
                "colour_term",
                "scent",
                "emblem_system",
                "furnishing",
                "tool",
                "instrument",
                "music_tradition",
                "game",
                "substance",
                "profession",
                "rank",
                "organisation",
                "dwelling",
                "production_method",
                "divine_office",
                "realm",
                "trait",
                "tenet",
                "fear",
                "dream_reading",
                "aim",
                name="concept",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("kind_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum("makes", "uses", "favours", "forbids", "blesses", name="stance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column(
            "spread",
            sa.Enum(
                "invented",
                "trade",
                "contact",
                "conquest",
                "migration",
                "decree",
                "divine",
                "genesis",
                name="spread",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_kind_holdings_since_epoch_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_kind_holdings_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_kind_holdings_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kind_holdings")),
        sa.UniqueConstraint("concept", "kind_id", "holder_node_id", name="uq_kind_holdings_kind_holder"),
    )
    with op.batch_alter_table("kind_holdings", schema=None) as batch_op:
        batch_op.create_index("ix_kind_holdings_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_kind_holdings_kind", ["concept", "kind_id"], unique=False)

    op.create_table(
        "aim_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "rule_a_realm",
                "found_a_house",
                "master_a_craft",
                "create_a_masterwork",
                "become_a_legend",
                "raise_a_family",
                "see_the_world",
                "achieve_holiness",
                "gain_wealth",
                "avenge_kin",
                "know_a_truth",
                "defeat_a_beast",
                "serve_a_god",
                "live_in_peace",
                "find_love",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "need",
            sa.Enum(
                "sustenance",
                "safety",
                "belonging",
                "status",
                "purpose",
                "faith",
                "pleasure",
                "drink",
                "rest",
                "comfort",
                "health",
                "family",
                "friends",
                "romance",
                "solitude",
                "learning",
                "creating",
                "beauty",
                "nature",
                "adventure",
                "fighting",
                "wealth",
                "order",
                "autonomy",
                "knowledge",
                "stimulation",
                "continuity",
                "upkeep",
                name="need",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("pull", sa.Integer(), nullable=False),
        sa.Column(
            "value_axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="value_axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("value_weight", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_aim_kinds_created_epoch_min")),
        sa.CheckConstraint("pull BETWEEN 0 AND 100", name=op.f("ck_aim_kinds_pull_range")),
        sa.CheckConstraint("value_weight BETWEEN -100 AND 100", name=op.f("ck_aim_kinds_value_weight_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["aim_kinds.id"], name=op.f("fk_aim_kinds_derived_from_id_aim_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_aim_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_aim_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aim_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_aim_kinds_built_in_key"),
    )
    with op.batch_alter_table("aim_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_aim_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_aim_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "colour_terms",
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "dark",
                "light",
                "red",
                "yellow",
                "green",
                "blue",
                "brown",
                "purple",
                "pink",
                "orange",
                "grey",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("rarity", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_colour_terms_created_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_colour_terms_prestige_range")),
        sa.CheckConstraint("rarity BETWEEN 0 AND 100", name=op.f("ck_colour_terms_rarity_range")),
        sa.CheckConstraint("stage BETWEEN 1 AND 11", name=op.f("ck_colour_terms_stage_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["colour_terms.id"], name=op.f("fk_colour_terms_derived_from_id_colour_terms"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_colour_terms_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_colour_terms_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_colour_terms")),
    )
    with op.batch_alter_table("colour_terms", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_colour_terms_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_colour_terms_world_id"), ["world_id"], unique=False)

    op.create_table(
        "cuisines",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "grain",
                "root_and_tuber",
                "vegetable",
                "legume",
                "fruit",
                "nut_and_seed",
                "oil_and_fat",
                "sweetener",
                "seasoning",
                "mineral_seasoning",
                "meat",
                "fish_and_seafood",
                "dairy",
                "eggs",
                "insects",
                "fungi",
                "algae",
                "offal_and_blood",
                "fodder",
                "drink_base",
                "stimulant",
                "intoxicant",
                "medicine",
                "fibre",
                "textile",
                "hide_and_leather",
                "timber",
                "fuel",
                "ore",
                "metal",
                "stone",
                "clay_and_ceramic",
                "glass",
                "chemical",
                "dye_and_pigment",
                "scent_material",
                "reagent",
                "tools",
                "weapons",
                "armour",
                "garments",
                "furnishings",
                "containers",
                "instruments",
                "ornaments",
                "books_and_records",
                "machines",
                "parts",
                "energy_store",
                "data",
                "living_goods",
                "sacred_goods",
                "luxuries",
                "livestock",
                "mounts",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "signature_method",
            sa.Enum(
                "raw",
                "boiled",
                "stewed",
                "steamed",
                "roasted",
                "grilled",
                "baked",
                "fried",
                "smoked",
                "dried",
                "cured",
                "pickled",
                "fermented",
                "braised",
                "simmered",
                "ground",
                "pressed",
                "synthesised",
                "printed",
                "vat_grown",
                "freeze_dried",
                "irradiated",
                "conjured",
                "infused",
                "distilled",
                "churned",
                "sprouted",
                "alkali_treated",
                "cultured",
                "cured_with_mineral",
                "aged",
                "extruded",
                "pressure_cooked",
                name="signature_method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "taboo_category",
            sa.Enum(
                "grain",
                "root_and_tuber",
                "vegetable",
                "legume",
                "fruit",
                "nut_and_seed",
                "oil_and_fat",
                "sweetener",
                "seasoning",
                "mineral_seasoning",
                "meat",
                "fish_and_seafood",
                "dairy",
                "eggs",
                "insects",
                "fungi",
                "algae",
                "offal_and_blood",
                "fodder",
                "drink_base",
                "stimulant",
                "intoxicant",
                "medicine",
                "fibre",
                "textile",
                "hide_and_leather",
                "timber",
                "fuel",
                "ore",
                "metal",
                "stone",
                "clay_and_ceramic",
                "glass",
                "chemical",
                "dye_and_pigment",
                "scent_material",
                "reagent",
                "tools",
                "weapons",
                "armour",
                "garments",
                "furnishings",
                "containers",
                "instruments",
                "ornaments",
                "books_and_records",
                "machines",
                "parts",
                "energy_store",
                "data",
                "living_goods",
                "sacred_goods",
                "luxuries",
                "livestock",
                "mounts",
                name="taboo_category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("etiquette", sa.Integer(), nullable=False),
        sa.Column("meals_per_day", sa.Integer(), nullable=False),
        sa.Column("feasting", sa.Integer(), nullable=False),
        sa.Column("sweet", sa.Integer(), nullable=False),
        sa.Column("sour", sa.Integer(), nullable=False),
        sa.Column("saline", sa.Integer(), nullable=False),
        sa.Column("bitter", sa.Integer(), nullable=False),
        sa.Column("savoury", sa.Integer(), nullable=False),
        sa.Column("pungent", sa.Integer(), nullable=False),
        sa.Column("cooling", sa.Integer(), nullable=False),
        sa.Column("numbing", sa.Integer(), nullable=False),
        sa.Column("smoky", sa.Integer(), nullable=False),
        sa.Column("fermented", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("bitter BETWEEN 0 AND 100", name=op.f("ck_cuisines_bitter_range")),
        sa.CheckConstraint("cooling BETWEEN 0 AND 100", name=op.f("ck_cuisines_cooling_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_cuisines_created_epoch_min")),
        sa.CheckConstraint("etiquette BETWEEN 0 AND 100", name=op.f("ck_cuisines_etiquette_range")),
        sa.CheckConstraint("feasting BETWEEN 0 AND 100", name=op.f("ck_cuisines_feasting_range")),
        sa.CheckConstraint("fermented BETWEEN 0 AND 100", name=op.f("ck_cuisines_fermented_range")),
        sa.CheckConstraint("meals_per_day BETWEEN 1 AND 8", name=op.f("ck_cuisines_meals_per_day_range")),
        sa.CheckConstraint("numbing BETWEEN 0 AND 100", name=op.f("ck_cuisines_numbing_range")),
        sa.CheckConstraint("pungent BETWEEN 0 AND 100", name=op.f("ck_cuisines_pungent_range")),
        sa.CheckConstraint("saline BETWEEN 0 AND 100", name=op.f("ck_cuisines_saline_range")),
        sa.CheckConstraint("savoury BETWEEN 0 AND 100", name=op.f("ck_cuisines_savoury_range")),
        sa.CheckConstraint("smoky BETWEEN 0 AND 100", name=op.f("ck_cuisines_smoky_range")),
        sa.CheckConstraint("sour BETWEEN 0 AND 100", name=op.f("ck_cuisines_sour_range")),
        sa.CheckConstraint("sweet BETWEEN 0 AND 100", name=op.f("ck_cuisines_sweet_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["cuisines.id"], name=op.f("fk_cuisines_derived_from_id_cuisines"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_cuisines_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_cuisines_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cuisines")),
    )
    with op.batch_alter_table("cuisines", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_cuisines_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_cuisines_world_id"), ["world_id"], unique=False)

    op.create_table(
        "divine_office_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "the_dead",
                "thresholds",
                "the_sky",
                "oaths",
                "messages",
                "the_hunt",
                "judgement",
                "memory",
                "making",
                "healing",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("income_pct", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_divine_office_kinds_created_epoch_min")),
        sa.CheckConstraint("income_pct BETWEEN 0 AND 500", name=op.f("ck_divine_office_kinds_income_pct_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["divine_office_kinds.id"], name=op.f("fk_divine_office_kinds_derived_from_id_divine_office_kinds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_divine_office_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_divine_office_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_office_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_divine_office_kinds_built_in_key"),
    )
    with op.batch_alter_table("divine_office_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_divine_office_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_divine_office_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "drink_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "water",
                "infusion",
                "fermented",
                "distilled",
                "pressed",
                "milk_based",
                "broth",
                "stimulant_brew",
                "intoxicant",
                "medicinal",
                "ritual",
                "synthesised",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "daily", "hospitality", "feast", "rite", "medicine", "trade", "bond_making", name="role", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("stimulation", sa.Integer(), nullable=False),
        sa.Column("nourishment", sa.Integer(), nullable=False),
        sa.Column("water_safety", sa.Integer(), nullable=False),
        sa.Column("keeps", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("dependence", sa.Integer(), nullable=False),
        sa.Column(
            "legality",
            sa.Enum("free", "licensed", "restricted", "forbidden", name="legality", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_drink_kinds_created_epoch_min")),
        sa.CheckConstraint("dependence BETWEEN 0 AND 100", name=op.f("ck_drink_kinds_dependence_range")),
        sa.CheckConstraint("keeps >= 0", name=op.f("ck_drink_kinds_keeps_min")),
        sa.CheckConstraint("nourishment BETWEEN 0 AND 100", name=op.f("ck_drink_kinds_nourishment_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_drink_kinds_prestige_range")),
        sa.CheckConstraint("stimulation BETWEEN 0 AND 100", name=op.f("ck_drink_kinds_stimulation_range")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_drink_kinds_strength_range")),
        sa.CheckConstraint("water_safety BETWEEN 0 AND 100", name=op.f("ck_drink_kinds_water_safety_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["drink_kinds.id"], name=op.f("fk_drink_kinds_derived_from_id_drink_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_drink_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_drink_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drink_kinds")),
    )
    with op.batch_alter_table("drink_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_drink_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_drink_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "dwelling_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "hut",
                "cottage",
                "house",
                "townhouse",
                "manor",
                "apartment",
                "tenement",
                "tower_block",
                "arcology_unit",
                "habitat_module",
                "ship_berth",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("upkeep", sa.Integer(), nullable=False),
        sa.Column("mobile", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_dwelling_kinds_created_epoch_min")),
        sa.CheckConstraint("mobile BETWEEN 0 AND 1", name=op.f("ck_dwelling_kinds_mobile_range")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_dwelling_kinds_quality_range")),
        sa.CheckConstraint("rooms >= 1", name=op.f("ck_dwelling_kinds_rooms_min")),
        sa.CheckConstraint("upkeep >= 0", name=op.f("ck_dwelling_kinds_upkeep_min")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["dwelling_kinds.id"], name=op.f("fk_dwelling_kinds_derived_from_id_dwelling_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_dwelling_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_dwelling_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dwelling_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_dwelling_kinds_built_in_key"),
    )
    with op.batch_alter_table("dwelling_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_dwelling_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_dwelling_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "emblem_systems",
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "heraldry",
                "seal",
                "banner",
                "totem",
                "badge",
                "monogram",
                "mark",
                "glyph",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("complexity", sa.Integer(), nullable=False),
        sa.Column("legibility", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("complexity BETWEEN 0 AND 100", name=op.f("ck_emblem_systems_complexity_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_emblem_systems_created_epoch_min")),
        sa.CheckConstraint("legibility BETWEEN 0 AND 100", name=op.f("ck_emblem_systems_legibility_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_emblem_systems_prestige_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["emblem_systems.id"], name=op.f("fk_emblem_systems_derived_from_id_emblem_systems"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_emblem_systems_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_emblem_systems_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emblem_systems")),
    )
    with op.batch_alter_table("emblem_systems", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_emblem_systems_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_emblem_systems_world_id"), ["world_id"], unique=False)

    op.create_table(
        "fear_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "death",
                "war",
                "plague",
                "beasts",
                "losing_a_child",
                "poverty",
                "shame",
                "dark",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("grip", sa.Integer(), nullable=False),
        sa.Column(
            "facet",
            sa.Enum(
                "anxiety",
                "anger",
                "depression",
                "self_consciousness",
                "vulnerability",
                "cheerfulness",
                "excitement_seeking",
                "emotional_stability",
                "friendliness",
                "gregariousness",
                "assertiveness",
                "trust",
                "altruism",
                "modesty",
                "politeness",
                "cooperation",
                "vanity",
                "envy",
                "gratitude",
                "ambition",
                "perseverance",
                "orderliness",
                "discipline",
                "thoroughness",
                "activity_level",
                "caution",
                "imagination",
                "curiosity",
                "abstraction",
                "artistic_inclination",
                "tolerance_of_difference",
                "humour",
                "sense_of_duty",
                "greed",
                name="facet",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("facet_weight", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_fear_kinds_created_epoch_min")),
        sa.CheckConstraint("facet_weight BETWEEN 0 AND 100", name=op.f("ck_fear_kinds_facet_weight_range")),
        sa.CheckConstraint("grip BETWEEN 0 AND 100", name=op.f("ck_fear_kinds_grip_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["fear_kinds.id"], name=op.f("fk_fear_kinds_derived_from_id_fear_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_fear_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_fear_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fear_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_fear_kinds_built_in_key"),
    )
    with op.batch_alter_table("fear_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fear_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_fear_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "furnishing_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "sleeping",
                "seating",
                "storage",
                "table",
                "lighting",
                "heating",
                "cooking_vessel",
                "tableware",
                "household_textile",
                "decoration",
                "sanitation",
                "shrine",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("comfort", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("comfort BETWEEN 0 AND 100", name=op.f("ck_furnishing_kinds_comfort_range")),
        sa.CheckConstraint("cost BETWEEN 0 AND 1000", name=op.f("ck_furnishing_kinds_cost_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_furnishing_kinds_created_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_furnishing_kinds_prestige_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["furnishing_kinds.id"], name=op.f("fk_furnishing_kinds_derived_from_id_furnishing_kinds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_furnishing_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_furnishing_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_furnishing_kinds")),
    )
    with op.batch_alter_table("furnishing_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_furnishing_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_furnishing_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "garment_kinds",
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "body_wrap",
                "upper",
                "lower",
                "full_body",
                "outer_layer",
                "head",
                "face_covering",
                "feet",
                "hands",
                "undergarment",
                "fastening",
                "ornament",
                "uniform",
                "ritual_dress",
                "work_protection",
                "environment_suit",
                "body_marking",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "wearing_rule",
            sa.Enum(
                "anyone",
                "by_role",
                "by_class",
                "by_age",
                "by_faith",
                "by_rank",
                "by_gender_as_the_culture_holds",
                name="wearing_rule",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("layer", sa.Integer(), nullable=False),
        sa.Column("warmth", sa.Integer(), nullable=False),
        sa.Column("protection", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column("status_signal", sa.Integer(), nullable=False),
        sa.Column("modesty", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("fashion", sa.Integer(), nullable=False),
        sa.Column("novelty", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cost BETWEEN 0 AND 1000", name=op.f("ck_garment_kinds_cost_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_garment_kinds_created_epoch_min")),
        sa.CheckConstraint("fashion BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_fashion_range")),
        sa.CheckConstraint("layer BETWEEN 0 AND 5", name=op.f("ck_garment_kinds_layer_range")),
        sa.CheckConstraint("modesty BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_modesty_range")),
        sa.CheckConstraint("novelty BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_novelty_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_prestige_range")),
        sa.CheckConstraint("protection BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_protection_range")),
        sa.CheckConstraint("status_signal BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_status_signal_range")),
        sa.CheckConstraint("warmth BETWEEN 0 AND 100", name=op.f("ck_garment_kinds_warmth_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["garment_kinds.id"], name=op.f("fk_garment_kinds_derived_from_id_garment_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_garment_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_garment_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_garment_kinds")),
    )
    with op.batch_alter_table("garment_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_garment_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_garment_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "good_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "grain",
                "root_and_tuber",
                "vegetable",
                "legume",
                "fruit",
                "nut_and_seed",
                "oil_and_fat",
                "sweetener",
                "seasoning",
                "mineral_seasoning",
                "meat",
                "fish_and_seafood",
                "dairy",
                "eggs",
                "insects",
                "fungi",
                "algae",
                "offal_and_blood",
                "fodder",
                "drink_base",
                "stimulant",
                "intoxicant",
                "medicine",
                "fibre",
                "textile",
                "hide_and_leather",
                "timber",
                "fuel",
                "ore",
                "metal",
                "stone",
                "clay_and_ceramic",
                "glass",
                "chemical",
                "dye_and_pigment",
                "scent_material",
                "reagent",
                "tools",
                "weapons",
                "armour",
                "garments",
                "furnishings",
                "containers",
                "instruments",
                "ornaments",
                "books_and_records",
                "machines",
                "parts",
                "energy_store",
                "data",
                "living_goods",
                "sacred_goods",
                "luxuries",
                "livestock",
                "mounts",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("perishability", sa.Integer(), nullable=False),
        sa.Column("bulk", sa.Integer(), nullable=False),
        sa.Column("base_value", sa.Integer(), nullable=False),
        sa.Column("nourishment", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("sacred", sa.Integer(), nullable=False),
        sa.Column(
            "stocked_as",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="stocked_as",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.Enum("species", "material", "deposit", "method", "making", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "cargo_class",
            sa.Enum(
                "perishable",
                "livestock",
                "bulk",
                "fine",
                "liquid",
                "gas",
                "hazardous",
                "passengers",
                "living",
                "saved_minds",
                "relics",
                name="cargo_class",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "tax_class",
            sa.Enum("exempt", "staple", "ordinary", "luxury", "strategic", name="tax_class", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "legality",
            sa.Enum("free", "licensed", "restricted", "forbidden", name="legality", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("taboo", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("base_value >= 0", name=op.f("ck_good_kinds_base_value_min")),
        sa.CheckConstraint("bulk BETWEEN 0 AND 100", name=op.f("ck_good_kinds_bulk_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_good_kinds_created_epoch_min")),
        sa.CheckConstraint("nourishment BETWEEN 0 AND 100", name=op.f("ck_good_kinds_nourishment_range")),
        sa.CheckConstraint("perishability >= 0", name=op.f("ck_good_kinds_perishability_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_good_kinds_prestige_range")),
        sa.CheckConstraint("sacred BETWEEN 0 AND 100", name=op.f("ck_good_kinds_sacred_range")),
        sa.CheckConstraint("taboo BETWEEN 0 AND 100", name=op.f("ck_good_kinds_taboo_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["good_kinds.id"], name=op.f("fk_good_kinds_derived_from_id_good_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_good_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_good_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_good_kinds")),
    )
    with op.batch_alter_table("good_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_good_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index("ix_good_kinds_stocked_as", ["stocked_as"], unique=False)
        batch_op.create_index(batch_op.f("ix_good_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "instrument_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "string",
                "wind",
                "percussion",
                "voice",
                "keyboard",
                "electronic",
                "made",
                "living",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "ensemble_role",
            sa.Enum("lead", "accompaniment", "rhythm", "drone", "solo", name="ensemble_role", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("range_span", sa.Integer(), nullable=False),
        sa.Column("loudness", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_instrument_kinds_created_epoch_min")),
        sa.CheckConstraint("loudness BETWEEN 0 AND 100", name=op.f("ck_instrument_kinds_loudness_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_instrument_kinds_prestige_range")),
        sa.CheckConstraint("range_span BETWEEN 0 AND 100", name=op.f("ck_instrument_kinds_range_span_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["instrument_kinds.id"], name=op.f("fk_instrument_kinds_derived_from_id_instrument_kinds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_instrument_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_instrument_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_instrument_kinds")),
    )
    with op.batch_alter_table("instrument_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_instrument_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_instrument_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "music_traditions",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "solo",
                "chorus",
                "ensemble",
                "call_and_response",
                "layered",
                "improvised",
                "notated",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("scale_steps", sa.Integer(), nullable=False),
        sa.Column("rhythm_complexity", sa.Integer(), nullable=False),
        sa.Column("ensemble_size", sa.Integer(), nullable=False),
        sa.Column("rite_weight", sa.Integer(), nullable=False),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_music_traditions_created_epoch_min")),
        sa.CheckConstraint("ensemble_size BETWEEN 1 AND 500", name=op.f("ck_music_traditions_ensemble_size_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_music_traditions_prestige_range")),
        sa.CheckConstraint("rhythm_complexity BETWEEN 0 AND 100", name=op.f("ck_music_traditions_rhythm_complexity_range")),
        sa.CheckConstraint("rite_weight BETWEEN 0 AND 100", name=op.f("ck_music_traditions_rite_weight_range")),
        sa.CheckConstraint("scale_steps BETWEEN 2 AND 48", name=op.f("ck_music_traditions_scale_steps_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["music_traditions.id"], name=op.f("fk_music_traditions_derived_from_id_music_traditions"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_music_traditions_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_music_traditions_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_music_traditions")),
    )
    with op.batch_alter_table("music_traditions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_music_traditions_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_music_traditions_world_id"), ["world_id"], unique=False)

    op.create_table(
        "organisation_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "trade",
                "craft",
                "faith",
                "war",
                "learning",
                "rule",
                "crime",
                "mutual_aid",
                "leisure",
                "secrecy",
                "politics",
                "exploration",
                "making",
                "care",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "base",
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
                "route_raiders",
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
                "workers_union",
                "engineers_society",
                "financiers",
                "veterans",
                name="base",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "ownership",
            sa.Enum("members", "shareholders", "founder", "state", "faith", "none", name="ownership", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "membership",
            sa.Enum(
                "open",
                "by_trade",
                "by_birth",
                "by_oath",
                "by_invitation",
                "by_purchase",
                "by_power",
                name="membership",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "scale", sa.Enum("band", "company", "organisation", "network", name="scale", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "legal_form",
            sa.Enum("chartered", "licensed", "customary", "outlawed", "secret", name="legal_form", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "governance",
            sa.Enum("leader", "council", "assembly", "hereditary", "made_mind", name="governance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("cohesion", sa.Integer(), nullable=False),
        sa.Column("secrecy", sa.Integer(), nullable=False),
        sa.Column("foundable", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cohesion BETWEEN 0 AND 100", name=op.f("ck_organisation_kinds_cohesion_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_organisation_kinds_created_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_organisation_kinds_prestige_range")),
        sa.CheckConstraint("secrecy BETWEEN 0 AND 100", name=op.f("ck_organisation_kinds_secrecy_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["organisation_kinds.id"], name=op.f("fk_organisation_kinds_derived_from_id_organisation_kinds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_organisation_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_organisation_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisation_kinds")),
    )
    with op.batch_alter_table("organisation_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_organisation_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_organisation_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "production_method_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "farming",
                "fishing",
                "logging",
                "mining",
                "milling",
                "weaving",
                "smelting",
                "tanning",
                "brewing",
                "distilling",
                "masonry",
                "charcoal",
                "preserving",
                "lighting",
                "butchery",
                "dairy",
                "pressing",
                "milking",
                "shearing",
                "egg_laying",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "base",
            sa.Enum(
                "hand_sickle",
                "ox_plough",
                "irrigated_terraces",
                "crop_rotation",
                "divine_harvest",
                "line_and_net",
                "fish_weirs",
                "deep_sea_fleets",
                "axe_felling",
                "water_sawmill",
                "pick_and_shovel",
                "fire_setting",
                "pumped_shafts",
                "earth_shaping",
                "hand_quern",
                "watermill",
                "windmill",
                "hand_loom",
                "water_frame",
                "bloomery",
                "blast_furnace",
                "divine_forge",
                "pit_tanning",
                "oil_curing",
                "open_vat",
                "cellar_brewing",
                "herbal_still",
                "arcane_alembic",
                "hand_chisel",
                "water_saw",
                "clamp_kiln",
                "retort_kiln",
                "salting",
                "smoking",
                "drying",
                "icing",
                "magic_keeping",
                "tallow_candles",
                "oil_lamps",
                "glow_moss",
                "magic_light",
                "home_slaughter",
                "shambles",
                "hand_churning",
                "cave_ageing",
                "treading",
                "screw_press",
                "hand_milking",
                "penned_milking",
                "hand_shearing",
                "iron_shears",
                "gathered_eggs",
                "kept_flocks",
                "cultured_crops",
                "grown_timber",
                "fibre_from_life",
                "vat_culture",
                "bioreactor",
                "motor_tractors",
                "hydroponics",
                "grown_draught",
                "trawlers",
                "chainsaws",
                "electric_drills",
                "deep_boring",
                "roller_mill",
                "tidal_mill",
                "power_loom",
                "electric_loom",
                "electric_arc",
                "geothermal_furnace",
                "star_forge",
                "fusion_foundry",
                "void_furnace",
                "chemical_tanning",
                "steam_brewery",
                "column_still",
                "source_distillery",
                "power_saw",
                "gas_retort",
                "canning",
                "refrigeration_halls",
                "gas_lamps",
                "electric_lights",
                "solar_lanterns",
                "cell_lamps",
                "belief_glow",
                "packing_house",
                "creamery",
                "hydraulic_press",
                "milking_machines",
                "power_shears",
                "incubators",
                name="base",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("output_pct", sa.Integer(), nullable=False),
        sa.Column("quality_bonus", sa.Integer(), nullable=False),
        sa.Column("labour_pct", sa.Integer(), nullable=False),
        sa.Column("energy_need", sa.Integer(), nullable=False),
        sa.Column("tool_wear", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_production_method_kinds_created_epoch_min")),
        sa.CheckConstraint("energy_need BETWEEN 0 AND 100", name=op.f("ck_production_method_kinds_energy_need_range")),
        sa.CheckConstraint("labour_pct BETWEEN 0 AND 500", name=op.f("ck_production_method_kinds_labour_pct_range")),
        sa.CheckConstraint("output_pct BETWEEN 0 AND 500", name=op.f("ck_production_method_kinds_output_pct_range")),
        sa.CheckConstraint("quality_bonus BETWEEN -50 AND 50", name=op.f("ck_production_method_kinds_quality_bonus_range")),
        sa.CheckConstraint("tool_wear BETWEEN 0 AND 20", name=op.f("ck_production_method_kinds_tool_wear_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"],
            ["production_method_kinds.id"],
            name=op.f("fk_production_method_kinds_derived_from_id_production_method_kinds"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_production_method_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_production_method_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_production_method_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_production_method_kinds_built_in_key"),
    )
    with op.batch_alter_table("production_method_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_production_method_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_production_method_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "profession_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "food_production",
                "crafting",
                "trade",
                "transport",
                "care",
                "healing",
                "learning",
                "faith",
                "rule_and_administration",
                "law",
                "war",
                "security",
                "art_and_entertainment",
                "service",
                "building",
                "extraction",
                "science_and_engineering",
                "information",
                "making_minds",
                "living_craft",
                "magic",
                "exploration",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "base",
            sa.Enum(
                "soldier",
                "rider",
                "smith",
                "builder",
                "weaver",
                "healer",
                "scholar",
                "priest",
                "sorcerer",
                "merchant",
                "diplomat",
                "hunter",
                "sailor",
                "commander",
                "engineer",
                "scientist",
                "pilot",
                "technician",
                "programmer",
                "mechanic",
                "miner",
                "farmer",
                "artist",
                "administrator",
                "spacer",
                name="base",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "job",
            sa.Enum(
                "farming",
                "herding",
                "fishing",
                "mining",
                "crafting",
                "trade",
                "soldiering",
                "clergy",
                "scholarship",
                "building",
                "service",
                "idle",
                name="job",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("income", sa.Integer(), nullable=False),
        sa.Column("purity", sa.Integer(), nullable=False),
        sa.Column("mishap_exposure", sa.Integer(), nullable=False),
        sa.Column("skill_need", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_profession_kinds_created_epoch_min")),
        sa.CheckConstraint("income BETWEEN 0 AND 100", name=op.f("ck_profession_kinds_income_range")),
        sa.CheckConstraint("mishap_exposure BETWEEN 0 AND 100", name=op.f("ck_profession_kinds_mishap_exposure_range")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_profession_kinds_prestige_range")),
        sa.CheckConstraint("purity BETWEEN 0 AND 100", name=op.f("ck_profession_kinds_purity_range")),
        sa.CheckConstraint("skill_need BETWEEN 0 AND 100", name=op.f("ck_profession_kinds_skill_need_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["profession_kinds.id"], name=op.f("fk_profession_kinds_derived_from_id_profession_kinds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_profession_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_profession_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profession_kinds")),
    )
    with op.batch_alter_table("profession_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_profession_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_profession_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "rank_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
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
                "worker",
                "professional",
                "official",
                "citizen",
                "unemployed",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("standing", sa.Integer(), nullable=False),
        sa.Column("privilege", sa.Integer(), nullable=False),
        sa.Column("duty", sa.Integer(), nullable=False),
        sa.Column("mobility", sa.Integer(), nullable=False),
        sa.Column("purity", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_rank_kinds_created_epoch_min")),
        sa.CheckConstraint("duty BETWEEN 0 AND 100", name=op.f("ck_rank_kinds_duty_range")),
        sa.CheckConstraint("mobility BETWEEN 0 AND 100", name=op.f("ck_rank_kinds_mobility_range")),
        sa.CheckConstraint("privilege BETWEEN 0 AND 100", name=op.f("ck_rank_kinds_privilege_range")),
        sa.CheckConstraint("purity BETWEEN 0 AND 100", name=op.f("ck_rank_kinds_purity_range")),
        sa.CheckConstraint("standing BETWEEN 0 AND 100", name=op.f("ck_rank_kinds_standing_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["rank_kinds.id"], name=op.f("fk_rank_kinds_derived_from_id_rank_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_rank_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_rank_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rank_kinds")),
    )
    with op.batch_alter_table("rank_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_rank_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_rank_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "reading_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "unread",
                "omen_of_war",
                "omen_of_plenty",
                "omen_of_death",
                "omen_of_favour",
                "warning",
                "call_to_journey",
                "call_to_love",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("valence", sa.Integer(), nullable=False),
        sa.Column(
            "value_axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="value_axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("lean", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_reading_kinds_created_epoch_min")),
        sa.CheckConstraint("lean BETWEEN -20 AND 20", name=op.f("ck_reading_kinds_lean_range")),
        sa.CheckConstraint("valence BETWEEN -100 AND 100", name=op.f("ck_reading_kinds_valence_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["reading_kinds.id"], name=op.f("fk_reading_kinds_derived_from_id_reading_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_reading_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_reading_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reading_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_reading_kinds_built_in_key"),
    )
    with op.batch_alter_table("reading_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_reading_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_reading_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "realm_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "seat_of_gods",
                "abode_of_dead",
                "dream",
                "sacred_site",
                "prison",
                "garden",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("danger", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_realm_kinds_created_epoch_min")),
        sa.CheckConstraint("danger BETWEEN 0 AND 100", name=op.f("ck_realm_kinds_danger_range")),
        sa.CheckConstraint("steps BETWEEN 0 AND 10", name=op.f("ck_realm_kinds_steps_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["realm_kinds.id"], name=op.f("fk_realm_kinds_derived_from_id_realm_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_realm_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_realm_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_realm_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_realm_kinds_built_in_key"),
    )
    with op.batch_alter_table("realm_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_realm_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_realm_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "scent_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "burned",
                "worn",
                "anointed",
                "household",
                "ritual",
                "medicinal",
                "signal",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("prestige", sa.Integer(), nullable=False),
        sa.Column("rite_weight", sa.Integer(), nullable=False),
        sa.Column("trade_value", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_scent_kinds_created_epoch_min")),
        sa.CheckConstraint("prestige BETWEEN 0 AND 100", name=op.f("ck_scent_kinds_prestige_range")),
        sa.CheckConstraint("rite_weight BETWEEN 0 AND 100", name=op.f("ck_scent_kinds_rite_weight_range")),
        sa.CheckConstraint("trade_value BETWEEN 0 AND 1000", name=op.f("ck_scent_kinds_trade_value_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["scent_kinds.id"], name=op.f("fk_scent_kinds_derived_from_id_scent_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_scent_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_scent_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scent_kinds")),
    )
    with op.batch_alter_table("scent_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_scent_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_scent_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "substance_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "stimulant",
                "depressant",
                "hallucinogen",
                "analgesic",
                "euphoriant",
                "power_substance",
                "medicinal",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("potency", sa.Integer(), nullable=False),
        sa.Column("dependence", sa.Integer(), nullable=False),
        sa.Column("harm", sa.Integer(), nullable=False),
        sa.Column("rite_weight", sa.Integer(), nullable=False),
        sa.Column("trade_value", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_substance_kinds_created_epoch_min")),
        sa.CheckConstraint("dependence BETWEEN 0 AND 100", name=op.f("ck_substance_kinds_dependence_range")),
        sa.CheckConstraint("harm BETWEEN 0 AND 100", name=op.f("ck_substance_kinds_harm_range")),
        sa.CheckConstraint("potency BETWEEN 0 AND 100", name=op.f("ck_substance_kinds_potency_range")),
        sa.CheckConstraint("rite_weight BETWEEN 0 AND 100", name=op.f("ck_substance_kinds_rite_weight_range")),
        sa.CheckConstraint("trade_value BETWEEN 0 AND 1000", name=op.f("ck_substance_kinds_trade_value_range")),
        sa.ForeignKeyConstraint(
            ["derived_from_id"], ["substance_kinds.id"], name=op.f("fk_substance_kinds_derived_from_id_substance_kinds"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_substance_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_substance_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_substance_kinds")),
    )
    with op.batch_alter_table("substance_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_substance_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_substance_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "tenet_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.Enum("doctrine", "ideology", "idea", name="category", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "value_axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="value_axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("value_delta", sa.Integer(), nullable=False),
        sa.Column(
            "second_axis",
            sa.Enum(
                "honour",
                "tradition",
                "hierarchy",
                "martial",
                "piety",
                "purity",
                "kinship",
                "mercy",
                "knowledge",
                "wealth",
                "nature",
                "superstition",
                "xenophilia",
                "death",
                "law",
                "loyalty",
                "family",
                "friendship",
                "truth",
                "craftsmanship",
                "artwork",
                "competition",
                "perseverance_value",
                "leisure",
                name="second_axis",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("second_delta", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_tenet_kinds_created_epoch_min")),
        sa.CheckConstraint("second_delta BETWEEN -50 AND 50", name=op.f("ck_tenet_kinds_second_delta_range")),
        sa.CheckConstraint("value_delta BETWEEN -50 AND 50", name=op.f("ck_tenet_kinds_value_delta_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["tenet_kinds.id"], name=op.f("fk_tenet_kinds_derived_from_id_tenet_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_tenet_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_tenet_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenet_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_tenet_kinds_built_in_key"),
    )
    with op.batch_alter_table("tenet_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tenet_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_tenet_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "tool_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "cutting",
                "digging",
                "lifting",
                "measuring",
                "writing",
                "fire_making",
                "crafting",
                "medical",
                "navigation",
                "computing",
                "farming",
                "fishing",
                "hunting",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
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
                "firearms",
                "piloting",
                "driving",
                "mechanics",
                "electronics",
                "computing",
                "science",
                "administration",
                name="skill",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("craft_bonus", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Integer(), nullable=False),
        sa.Column("wear", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("craft_bonus BETWEEN 0 AND 100", name=op.f("ck_tool_kinds_craft_bonus_range")),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_tool_kinds_created_epoch_min")),
        sa.CheckConstraint("quality BETWEEN 0 AND 100", name=op.f("ck_tool_kinds_quality_range")),
        sa.CheckConstraint("wear BETWEEN 0 AND 100", name=op.f("ck_tool_kinds_wear_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["tool_kinds.id"], name=op.f("fk_tool_kinds_derived_from_id_tool_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_tool_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_tool_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_kinds")),
    )
    with op.batch_alter_table("tool_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tool_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_tool_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "trait_kinds",
        sa.Column("derived_from_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "strength",
                "agility",
                "mind",
                "resilience",
                "fertility",
                "danger",
                "magic",
                "charm",
                "divinity",
                "longevity",
                name="category",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("built_in_key", sa.String(length=120), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column("origin_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("built_in", sa.Boolean(), nullable=False),
        sa.Column("created_epoch", sa.Integer(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("created_epoch >= 0", name=op.f("ck_trait_kinds_created_epoch_min")),
        sa.CheckConstraint("strength BETWEEN -100 AND 100", name=op.f("ck_trait_kinds_strength_range")),
        sa.ForeignKeyConstraint(["derived_from_id"], ["trait_kinds.id"], name=op.f("fk_trait_kinds_derived_from_id_trait_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_node_id"], ["nodes.id"], name=op.f("fk_trait_kinds_origin_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_trait_kinds_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trait_kinds")),
        sa.UniqueConstraint("built_in_key", name="uq_trait_kinds_built_in_key"),
    )
    with op.batch_alter_table("trait_kinds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_trait_kinds_origin_node_id"), ["origin_node_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_trait_kinds_world_id"), ["world_id"], unique=False)

    op.create_table(
        "colour_meanings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("colour_term_id", sa.Integer(), nullable=False),
        sa.Column("culture_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "meaning",
            sa.Enum("mourning", "rank", "sacred", "danger", "joy", "faction", "none", name="meaning", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("since_epoch >= 0", name=op.f("ck_colour_meanings_since_epoch_min")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_colour_meanings_weight_range")),
        sa.ForeignKeyConstraint(["colour_term_id"], ["colour_terms.id"], name=op.f("fk_colour_meanings_colour_term_id_colour_terms"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["culture_node_id"], ["nodes.id"], name=op.f("fk_colour_meanings_culture_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_colour_meanings")),
        sa.UniqueConstraint("colour_term_id", "culture_node_id", "meaning", name="uq_colour_meanings_term_culture_meaning"),
    )
    with op.batch_alter_table("colour_meanings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_colour_meanings_colour_term_id"), ["colour_term_id"], unique=False)
        batch_op.create_index("ix_colour_meanings_culture", ["culture_node_id"], unique=False)

    op.create_table(
        "dish_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dish_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "raw",
                "boiled",
                "stewed",
                "steamed",
                "roasted",
                "grilled",
                "baked",
                "fried",
                "smoked",
                "dried",
                "cured",
                "pickled",
                "fermented",
                "braised",
                "simmered",
                "ground",
                "pressed",
                "synthesised",
                "printed",
                "vat_grown",
                "freeze_dried",
                "irradiated",
                "conjured",
                "infused",
                "distilled",
                "churned",
                "sprouted",
                "alkali_treated",
                "cultured",
                "cured_with_mineral",
                "aged",
                "extruded",
                "pressure_cooked",
                name="method",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("duration BETWEEN 0 AND 1000", name=op.f("ck_dish_steps_duration_range")),
        sa.CheckConstraint("step >= 1", name=op.f("ck_dish_steps_step_min")),
        sa.ForeignKeyConstraint(["dish_id"], ["dishes.id"], name=op.f("fk_dish_steps_dish_id_dishes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dish_steps")),
        sa.UniqueConstraint("dish_id", "step", name="uq_dish_steps_dish_step"),
    )
    with op.batch_alter_table("dish_steps", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_dish_steps_dish_id"), ["dish_id"], unique=False)

    op.create_table(
        "species_products",
        sa.Column("species_entity_id", sa.Integer(), nullable=False),
        sa.Column("product", sa.String(length=120), nullable=False),
        sa.Column(
            "commodity",
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
                "meat",
                "milk",
                "cheese",
                "fruit",
                "tubers",
                "coal",
                "peat",
                "dung",
                "fibre",
                "dye",
                "herbs",
                "brew_base",
                "poison",
                "eggs",
                "wool",
                name="commodity",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
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
                "great_bone",
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
                "mud_brick",
                "fired_brick",
                "dressed_stone",
                "rubble",
                "lime_mortar",
                "hydraulic_concrete",
                "thatch",
                "tile",
                name="material",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("world_material_id", sa.Integer(), nullable=True),
        sa.Column("rate", sa.Integer(), nullable=False),
        sa.Column(
            "part",
            sa.Enum(
                "flesh",
                "hide",
                "bone",
                "tusk",
                "shell",
                "venom",
                "fibre",
                "milk",
                "eggs",
                "feathers",
                "reagent",
                "seed",
                "root",
                "fruit",
                "leaf",
                "wood",
                "sap",
                "dye",
                "toxin",
                name="part",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("good_kind_id", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("rate >= 0", name=op.f("ck_species_products_rate_min")),
        sa.ForeignKeyConstraint(["good_kind_id"], ["good_kinds.id"], name=op.f("fk_species_products_good_kind_id_good_kinds"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_products_species_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["world_material_id"], ["world_materials.id"], name=op.f("fk_species_products_world_material_id_world_materials"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("species_entity_id", "product", name=op.f("pk_species_products")),
    )
    op.execute(
        "INSERT INTO kind_holdings (concept, kind_id, holder_node_id, stance, strength, spread, since_epoch, locked) SELECT 'game', f.game_id, f.people_entity_id, CASE WHEN g.origin_entity_id = f.people_entity_id THEN 'makes' ELSE 'uses' END, f.popularity, 'invented', f.adopted_epoch, '[]' FROM game_followings f JOIN games g ON g.id = f.game_id"
    )
    op.drop_table("game_followings")
    copy_products("species_yields", "species_products")
    for product, part in PRODUCT_PARTS.items():
        op.execute(sa.text("UPDATE species_products SET part = :part WHERE product = :product").bindparams(part=part, product=product))
    op.drop_table("species_yields")
    with op.batch_alter_table("arms", schema=None) as batch_op:
        batch_op.add_column(sa.Column("emblem_system_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_arms_emblem_system_id"), ["emblem_system_id"], unique=False)
        batch_op.create_foreign_key(batch_op.f("fk_arms_emblem_system_id_emblem_systems"), "emblem_systems", ["emblem_system_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("community_dishes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("short_epochs", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("community_methods", schema=None) as batch_op:
        batch_op.add_column(sa.Column("method_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_community_methods_method_kind_id_production_method_kinds"),
            "production_method_kinds",
            ["method_kind_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("cosmic_offices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("office_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_cosmic_offices_office_kind_id_divine_office_kinds"), "divine_office_kinds", ["office_kind_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("currencies", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "form",
                sa.Enum(
                    "coin",
                    "commodity",
                    "token",
                    "paper",
                    "ledger",
                    "network",
                    "reputation",
                    "energy",
                    "essence_backed",
                    "labour_hours",
                    "gift_tally",
                    name="form",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="coin",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "backing",
                sa.Enum("metal", "commodity", "decree", "trust", "source", name="backing", native_enum=False, create_constraint=True, length=40),
                server_default="metal",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("convertible", sa.Boolean(), server_default="1", nullable=False))
        batch_op.add_column(
            sa.Column(
                "issuer_kind",
                sa.Enum("community", "polity", "bank", "temple", "company", name="issuer_kind", native_enum=False, create_constraint=True, length=40),
                server_default="community",
                nullable=False,
            )
        )

    with op.batch_alter_table("dish_ingredients", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.Enum(
                    "base",
                    "protein",
                    "fat",
                    "seasoning",
                    "garnish",
                    "binder",
                    "liquid",
                    "leavening",
                    "preservative",
                    "colouring",
                    name="role",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="base",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("good_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_dish_ingredients_good_kind_id_good_kinds"), "good_kinds", ["good_kind_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("dishes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("built_in", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("derived_from_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "category",
                sa.Enum(
                    "daily_meal",
                    "snack",
                    "feast",
                    "rite",
                    "ration",
                    "remedy",
                    "travel_food",
                    "famine_food",
                    name="category",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="daily_meal",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("prep_skill", sa.Integer(), server_default="20", nullable=False))
        batch_op.add_column(sa.Column("sweet", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("sour", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("saline", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("bitter", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("savoury", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("pungent", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("cooling", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("numbing", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("smoky", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("fermented", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_foreign_key(batch_op.f("fk_dishes_derived_from_id_dishes"), "dishes", ["derived_from_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("world_material_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_districts_world_material_id_world_materials"), "world_materials", ["world_material_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("dreams", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reading_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_dreams_reading_kind_id_reading_kinds"), "reading_kinds", ["reading_kind_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("dwellings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("dwelling_kind_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_dwellings_dwelling_kind_id"), ["dwelling_kind_id"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_dwellings_dwelling_kind_id_dwelling_kinds"), "dwelling_kinds", ["dwelling_kind_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.drop_constraint(batch_op.f("ck_dwellings_kind"), type_="check")

    with op.batch_alter_table("fears", schema=None) as batch_op:
        batch_op.add_column(sa.Column("fear_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_fears_fear_kind_id_fear_kinds"), "fear_kinds", ["fear_kind_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.add_column(sa.Column("built_in", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("retired", sa.Boolean(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("derived_from_id", sa.Integer(), nullable=True))
        batch_op.add_column(
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
                    "firearms",
                    "piloting",
                    "driving",
                    "mechanics",
                    "electronics",
                    "computing",
                    "science",
                    "administration",
                    name="skill",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("chance_share", sa.Integer(), server_default="30", nullable=False))
        batch_op.add_column(sa.Column("violence", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("team_size", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("betting", sa.Integer(), server_default="10", nullable=False))
        batch_op.add_column(sa.Column("spectators", sa.Integer(), server_default="20", nullable=False))
        batch_op.add_column(sa.Column("prestige", sa.Integer(), server_default="10", nullable=False))
        batch_op.add_column(sa.Column("world_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f("ix_games_world_id"), ["world_id"], unique=False)
        batch_op.drop_constraint(batch_op.f("fk_games_origin_entity_id_entities"), type_="foreignkey")
        batch_op.create_foreign_key(batch_op.f("fk_games_derived_from_id_games"), "games", ["derived_from_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_games_origin_entity_id_nodes"), "nodes", ["origin_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(batch_op.f("fk_games_world_id_worlds"), "worlds", ["world_id"], ["id"], ondelete="CASCADE")
        batch_op.drop_constraint(op.f("ck_games_rule"), type_="check")
        batch_op.drop_column("rule")

    with op.batch_alter_table("heroquests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("realm_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_heroquests_realm_kind_id_realm_kinds"), "realm_kinds", ["realm_kind_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("household_aggregates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("dwelling_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_household_aggregates_dwelling_kind_id_dwelling_kinds"), "dwelling_kinds", ["dwelling_kind_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.drop_constraint(batch_op.f("ck_household_aggregates_dwelling_kind"), type_="check")
    map_dwellings_forward()
    with op.batch_alter_table("dwellings", schema=None) as batch_op:
        batch_op.drop_column("kind")
    with op.batch_alter_table("household_aggregates", schema=None) as batch_op:
        batch_op.drop_column("dwelling_kind")

    with op.batch_alter_table("kinship_systems", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "first_side",
                sa.Enum("female", "male", "other", name="first_side", native_enum=False, create_constraint=True, length=40),
                server_default="male",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "adoption",
                sa.Enum("heir", "ward", "foster", "sponsor", "blood_bond", "chosen_kin", name="adoption", native_enum=False, create_constraint=True, length=40),
                server_default="foster",
                nullable=False,
            )
        )
        batch_op.alter_column("levirate", new_column_name="sibling_union_first")
        batch_op.alter_column("sororate", new_column_name="sibling_union_second")
        batch_op.drop_constraint(op.f("ck_kinship_systems_payment"), type_="check")
        batch_op.drop_column("payment")
        batch_op.drop_constraint(op.f("ck_kinship_systems_preference"), type_="check")
        batch_op.drop_column("preference")
        batch_op.drop_constraint(op.f("ck_kinship_systems_payment_value_min"), type_="check")
        batch_op.drop_column("payment_value")

    with op.batch_alter_table("life_dreams", schema=None) as batch_op:
        batch_op.add_column(sa.Column("aim_kind_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_life_dreams_aim_kind_id_aim_kinds"), "aim_kinds", ["aim_kind_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "form",
                sa.Enum(
                    "pair", "plural", "group", "serial", "contract", "posthumous", "none", name="form", native_enum=False, create_constraint=True, length=40
                ),
                server_default="pair",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "purpose",
                sa.Enum(
                    "kinship",
                    "alliance",
                    "inheritance",
                    "love",
                    "faith",
                    "labour",
                    "status",
                    name="purpose",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="kinship",
                nullable=False,
            )
        )
        batch_op.drop_constraint(op.f("ck_marriages_kind"), type_="check")
        batch_op.drop_column("kind")

    with op.batch_alter_table("people_culture", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ornament", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("geometry", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("colour", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("scale", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("symmetry", sa.Integer(), server_default="50", nullable=False))
        batch_op.add_column(sa.Column("motif_sources", sa.JSON(), server_default="[]", nullable=False))
        batch_op.drop_column("endogamous")
        batch_op.drop_constraint(op.f("ck_people_culture_aesthetic"), type_="check")
        batch_op.drop_column("aesthetic")
        batch_op.drop_constraint(op.f("ck_people_culture_marriage"), type_="check")
        batch_op.drop_column("marriage")

    with op.batch_alter_table("settlement_infrastructure", schema=None) as batch_op:
        batch_op.add_column(sa.Column("walls_world_material_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f("fk_settlement_infrastructure_walls_world_material_id_world_materials"),
            "world_materials",
            ["walls_world_material_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("style_ornament", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("style_geometry", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("style_colour", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("style_scale", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("style_symmetry", sa.Integer(), nullable=True))
        if "ck_structure_profiles_aesthetic" in named_checks("structure_profiles"):
            batch_op.drop_constraint(op.f("ck_structure_profiles_aesthetic"), type_="check")
        batch_op.drop_column("aesthetic")

    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "stage",
                sa.Enum("birth", "naming", "coming_of_age", "union", "elderhood", "death", name="stage", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )

    with op.batch_alter_table("union_customs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "plural_side",
                sa.Enum("first", "second", "either", name="plural_side", native_enum=False, create_constraint=True, length=40),
                server_default="either",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("exchange_value", sa.Integer(), server_default="10", nullable=False))
        batch_op.add_column(
            sa.Column(
                "kin_match",
                sa.Enum("none", "cross_cousin", "parallel_cousin", name="kin_match", native_enum=False, create_constraint=True, length=40),
                server_default="none",
                nullable=False,
            )
        )
    op.execute(
        "UPDATE tradition_profiles SET stage = (SELECT CASE g4b_passage.kind WHEN 'funeral_rite' THEN 'death' WHEN 'marriage_rite' THEN 'union' ELSE 'coming_of_age' END FROM g4b_passage WHERE g4b_passage.id = tradition_profiles.tradition_entity_id) WHERE tradition_entity_id IN (SELECT id FROM g4b_passage)"
    )
    op.execute("DROP TABLE g4b_passage")
    op.execute("UPDATE marriages SET form = 'plural' WHERE id IN (SELECT id FROM g4c_marriage WHERE kind = 'plural')")
    op.execute("UPDATE marriages SET purpose = 'alliance' WHERE id IN (SELECT id FROM g4c_marriage WHERE kind = 'political')")
    op.execute("CREATE TABLE g4c_new AS SELECT id FROM g4c_culture WHERE id NOT IN (SELECT people_entity_id FROM union_customs)")
    op.execute(
        "INSERT INTO union_customs (people_entity_id, form, purpose, residence, descent, exchange, arrangement, dissolution, endogamy, exogamy, term_epochs, locked) SELECT id, 'pair', 'kinship', 'new_household', 'through_both', 'none', 'both_consent', 'by_custom', 'none', 'none', 4, '[]' FROM g4c_new"
    )
    op.execute(
        "UPDATE union_customs SET residence = 'with_first_family' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT people_entity_id FROM kinship_systems WHERE residence = 'with_first_family')"
    )
    op.execute(
        "UPDATE union_customs SET residence = 'with_second_family' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT people_entity_id FROM kinship_systems WHERE residence = 'with_second_family')"
    )
    op.execute(
        "UPDATE union_customs SET residence = 'with_second_family' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT people_entity_id FROM kinship_systems WHERE residence = 'with_kin_of_the_first_line')"
    )
    op.execute(
        "UPDATE union_customs SET descent = 'through_first' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT people_entity_id FROM kinship_systems WHERE descent = 'through_first_line')"
    )
    op.execute(
        "UPDATE union_customs SET descent = 'through_second' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT people_entity_id FROM kinship_systems WHERE descent = 'through_second_line')"
    )
    op.execute(
        "UPDATE union_customs SET descent = 'chosen' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT people_entity_id FROM kinship_systems WHERE descent = 'ambilineal')"
    )
    op.execute(
        "UPDATE union_customs SET form = 'group' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT id FROM g4c_culture WHERE marriage = 'group')"
    )
    op.execute(
        "UPDATE union_customs SET form = 'plural' WHERE people_entity_id IN (SELECT id FROM g4c_new) AND people_entity_id IN (SELECT id FROM g4c_culture WHERE marriage NOT IN ('monogamy', 'group'))"
    )
    op.execute(
        "UPDATE union_customs SET plural_side = 'first' WHERE form = 'plural' AND locked NOT LIKE '%\"plural_side\"%' AND people_entity_id IN (SELECT id FROM g4c_culture WHERE marriage IN ('plural_first_side', 'polygyny'))"
    )
    op.execute(
        "UPDATE union_customs SET plural_side = 'second' WHERE form = 'plural' AND locked NOT LIKE '%\"plural_side\"%' AND people_entity_id IN (SELECT id FROM g4c_culture WHERE marriage IN ('plural_second_side', 'polyandry'))"
    )
    op.execute(
        "UPDATE union_customs SET endogamy = 'people' WHERE endogamy = 'none' AND locked NOT LIKE '%\"endogamy\"%' AND people_entity_id IN (SELECT id FROM g4c_culture WHERE endogamous = 1)"
    )
    op.execute(
        "UPDATE union_customs SET exogamy = 'line' WHERE exogamy IN ('none', 'house') AND locked NOT LIKE '%\"exogamy\"%' AND people_entity_id IN (SELECT id FROM g4c_kin WHERE preference = 'clan_exogamy')"
    )
    op.execute(
        "UPDATE union_customs SET exogamy = 'moiety' WHERE exogamy IN ('none', 'house') AND locked NOT LIKE '%\"exogamy\"%' AND people_entity_id IN (SELECT id FROM g4c_kin WHERE preference = 'moiety_exogamy')"
    )
    op.execute("UPDATE union_customs SET kin_match = 'cross_cousin' WHERE people_entity_id IN (SELECT id FROM g4c_kin WHERE preference = 'cross_cousin')")
    op.execute(
        "UPDATE union_customs SET exchange = 'service' WHERE exchange IN ('none', 'to_one_family') AND locked NOT LIKE '%\"exchange\"%' AND people_entity_id IN (SELECT id FROM g4c_kin WHERE payment IN ('service', 'bride_service'))"
    )
    op.execute(
        "UPDATE union_customs SET exchange = 'to_one_family' WHERE exchange IN ('none', 'to_one_family') AND locked NOT LIKE '%\"exchange\"%' AND people_entity_id IN (SELECT id FROM g4c_kin WHERE payment IN ('to_one_family', 'bride_price'))"
    )
    op.execute(
        "UPDATE union_customs SET exchange = 'from_one_family' WHERE exchange IN ('none', 'to_one_family') AND locked NOT LIKE '%\"exchange\"%' AND people_entity_id IN (SELECT id FROM g4c_kin WHERE payment IN ('from_one_family', 'dowry'))"
    )
    op.execute(
        "UPDATE people_culture SET ornament = 15, geometry = 55, colour = 20, scale = 45, symmetry = 65 WHERE people_entity_id IN (SELECT id FROM aes_culture WHERE aesthetic = 'austere')"
    )
    op.execute(
        "UPDATE people_culture SET ornament = 90, geometry = 50, colour = 80, scale = 60, symmetry = 60 WHERE people_entity_id IN (SELECT id FROM aes_culture WHERE aesthetic = 'ornate')"
    )
    op.execute(
        "UPDATE people_culture SET ornament = 50, geometry = 90, colour = 45, scale = 55, symmetry = 85 WHERE people_entity_id IN (SELECT id FROM aes_culture WHERE aesthetic = 'geometric')"
    )
    op.execute(
        "UPDATE people_culture SET ornament = 40, geometry = 10, colour = 55, scale = 40, symmetry = 30 WHERE people_entity_id IN (SELECT id FROM aes_culture WHERE aesthetic = 'natural')"
    )
    op.execute(
        "UPDATE people_culture SET ornament = 60, geometry = 40, colour = 25, scale = 50, symmetry = 45 WHERE people_entity_id IN (SELECT id FROM aes_culture WHERE aesthetic = 'macabre')"
    )
    op.execute(
        "UPDATE people_culture SET ornament = 60, geometry = 65, colour = 70, scale = 80, symmetry = 70 WHERE people_entity_id IN (SELECT id FROM aes_culture WHERE aesthetic = 'celestial')"
    )
    op.execute(
        "UPDATE union_customs SET exchange_value = (SELECT payment_value FROM g4c_kin WHERE g4c_kin.id = union_customs.people_entity_id) WHERE people_entity_id IN (SELECT id FROM g4c_kin)"
    )
    op.execute("DROP TABLE g4c_new")
    op.execute("DROP TABLE g4c_marriage")
    op.execute("DROP TABLE g4c_culture")
    op.execute("DROP TABLE g4c_kin")
    op.execute(
        "UPDATE structure_profiles SET style_ornament = 15, style_geometry = 55, style_colour = 20, style_scale = 45, style_symmetry = 65 WHERE structure_entity_id IN (SELECT id FROM aes_structure WHERE aesthetic = 'austere')"
    )
    op.execute(
        "UPDATE structure_profiles SET style_ornament = 90, style_geometry = 50, style_colour = 80, style_scale = 60, style_symmetry = 60 WHERE structure_entity_id IN (SELECT id FROM aes_structure WHERE aesthetic = 'ornate')"
    )
    op.execute(
        "UPDATE structure_profiles SET style_ornament = 50, style_geometry = 90, style_colour = 45, style_scale = 55, style_symmetry = 85 WHERE structure_entity_id IN (SELECT id FROM aes_structure WHERE aesthetic = 'geometric')"
    )
    op.execute(
        "UPDATE structure_profiles SET style_ornament = 40, style_geometry = 10, style_colour = 55, style_scale = 40, style_symmetry = 30 WHERE structure_entity_id IN (SELECT id FROM aes_structure WHERE aesthetic = 'natural')"
    )
    op.execute(
        "UPDATE structure_profiles SET style_ornament = 60, style_geometry = 40, style_colour = 25, style_scale = 50, style_symmetry = 45 WHERE structure_entity_id IN (SELECT id FROM aes_structure WHERE aesthetic = 'macabre')"
    )
    op.execute(
        "UPDATE structure_profiles SET style_ornament = 60, style_geometry = 65, style_colour = 70, style_scale = 80, style_symmetry = 70 WHERE structure_entity_id IN (SELECT id FROM aes_structure WHERE aesthetic = 'celestial')"
    )
    op.execute("UPDATE legacy_traits SET key = '15,55,20,45,65' WHERE kind = 'aesthetic' AND key = 'austere'")
    op.execute("UPDATE legacy_traits SET key = '90,50,80,60,60' WHERE kind = 'aesthetic' AND key = 'ornate'")
    op.execute("UPDATE legacy_traits SET key = '50,90,45,55,85' WHERE kind = 'aesthetic' AND key = 'geometric'")
    op.execute("UPDATE legacy_traits SET key = '40,10,55,40,30' WHERE kind = 'aesthetic' AND key = 'natural'")
    op.execute("UPDATE legacy_traits SET key = '60,40,25,50,45' WHERE kind = 'aesthetic' AND key = 'macabre'")
    op.execute("UPDATE legacy_traits SET key = '60,65,70,80,70' WHERE kind = 'aesthetic' AND key = 'celestial'")
    op.execute("DROP TABLE aes_culture")
    op.execute("DROP TABLE aes_structure")
    op.execute("UPDATE species_products SET product = 'great_bone' WHERE product = 'dragonbone'")


def downgrade() -> None:
    op.execute("UPDATE species_products SET product = 'dragonbone' WHERE product = 'great_bone'")
    op.execute("CREATE TABLE aes_family (name VARCHAR, o INTEGER, g INTEGER, c INTEGER, s INTEGER, y INTEGER)")
    op.execute("INSERT INTO aes_family VALUES ('austere', 15, 55, 20, 45, 65)")
    op.execute("INSERT INTO aes_family VALUES ('ornate', 90, 50, 80, 60, 60)")
    op.execute("INSERT INTO aes_family VALUES ('geometric', 50, 90, 45, 55, 85)")
    op.execute("INSERT INTO aes_family VALUES ('natural', 40, 10, 55, 40, 30)")
    op.execute("INSERT INTO aes_family VALUES ('macabre', 60, 40, 25, 50, 45)")
    op.execute("INSERT INTO aes_family VALUES ('celestial', 60, 65, 70, 80, 70)")
    op.execute(
        "CREATE TABLE aes_people AS SELECT people_entity_id AS id, ornament AS o, geometry AS g, colour AS c, scale AS s, symmetry AS y FROM people_culture"
    )
    op.execute(
        "CREATE TABLE aes_works AS SELECT structure_entity_id AS id, style_ornament AS o, style_geometry AS g, style_colour AS c, style_scale AS s, style_symmetry AS y FROM structure_profiles WHERE style_ornament IS NOT NULL"
    )
    op.execute("CREATE TABLE g4c_mback AS SELECT id, form, purpose FROM marriages")
    op.execute(
        "CREATE TABLE g4c_back AS SELECT people_entity_id AS id, form, plural_side, endogamy, exogamy, kin_match, exchange, exchange_value FROM union_customs"
    )
    op.execute("UPDATE union_customs SET exchange = 'to_one_family' WHERE exchange = 'service'")
    op.execute("UPDATE union_customs SET exogamy = 'house' WHERE exogamy IN ('line', 'moiety')")
    op.execute("UPDATE union_customs SET endogamy = 'house' WHERE endogamy IN ('line', 'moiety')")
    op.execute("CREATE TABLE g4b_stage AS SELECT tradition_entity_id AS id, stage FROM tradition_profiles WHERE stage IS NOT NULL")
    op.execute("UPDATE entities SET subtype = 'golem' WHERE subtype = 'animated work'")
    op.execute("UPDATE entities SET subtype = 'chimera' WHERE subtype = 'merged species'")
    op.execute("UPDATE ledger_entries SET tool = 'scatter_bones' WHERE tool = 'hinder_return'")
    op.execute("UPDATE ledger_entries SET tool = 'sibling:scatter' WHERE tool = 'sibling:hinder_return'")
    op.execute("UPDATE ledger_entries SET tool = 'species:chimera' WHERE tool = 'species:merge'")
    op.execute("UPDATE chronicle SET template_key = 'creatures.chimera_woven' WHERE template_key = 'creatures.species_merged'")
    op.execute("UPDATE chronicle SET template_key = 'tools.mortal.chimera' WHERE template_key = 'tools.mortal.species_merged'")
    op.execute("UPDATE chronicle SET template_key = 'gods.death.scatter' WHERE template_key = 'gods.death.return_hindered'")
    op.execute(
        "UPDATE law_profiles SET params = json_remove(json_set(params, '$.chimera', json_extract(params, '$.merging')), '$.merging') WHERE kind = 'living_craft_law' AND json_extract(params, '$.merging') IS NOT NULL"
    )
    op.execute("UPDATE OR IGNORE preferences SET target = 'song' WHERE kind = 'art_form' AND target = 'musical'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'epic_poem' WHERE kind = 'art_form' AND target = 'verbal'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'play' WHERE kind = 'art_form' AND target = 'ritual_performance'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'statue' WHERE kind = 'art_form' AND target = 'solid_image'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'fresco' WHERE kind = 'art_form' AND target = 'flat_image'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'tapestry' WHERE kind = 'art_form' AND target = 'textile_image'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'dance' WHERE kind = 'art_form' AND target = 'movement'")
    op.execute("UPDATE OR IGNORE preferences SET target = 'architecture_ornament' WHERE kind = 'art_form' AND target = 'built'")
    op.execute(
        "UPDATE afterlife_strata SET criteria = replace(replace(criteria, '\"cremation\"', '\"burning\"'), '\"sky_burial\"', '\"exposure\"') WHERE criteria IS NOT NULL"
    )
    with op.batch_alter_table("union_customs", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_union_customs_kin_match"), type_="check")
        batch_op.drop_column("kin_match")
        batch_op.drop_column("exchange_value")
        batch_op.drop_constraint(op.f("ck_union_customs_plural_side"), type_="check")
        batch_op.drop_column("plural_side")

    with op.batch_alter_table("tradition_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_tradition_profiles_stage"), type_="check")
        batch_op.drop_column("stage")

    with op.batch_alter_table("structure_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("aesthetic", sa.VARCHAR(length=40), nullable=True))
        batch_op.drop_column("style_symmetry")
        batch_op.drop_column("style_scale")
        batch_op.drop_column("style_colour")
        batch_op.drop_column("style_geometry")
        batch_op.drop_column("style_ornament")

    with op.batch_alter_table("settlement_infrastructure", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_settlement_infrastructure_walls_world_material_id_world_materials"), type_="foreignkey")
        batch_op.drop_column("walls_world_material_id")

    with op.batch_alter_table("people_culture", schema=None) as batch_op:
        batch_op.add_column(sa.Column("marriage", sa.VARCHAR(length=40), server_default="monogamy", nullable=False))
        batch_op.create_check_constraint(op.f("ck_people_culture_marriage"), "marriage IN ('monogamy', 'polygyny', 'polyandry', 'group')")
        batch_op.add_column(sa.Column("aesthetic", sa.VARCHAR(length=40), server_default="austere", nullable=False))
        batch_op.create_check_constraint(
            op.f("ck_people_culture_aesthetic"), "aesthetic IN ('austere', 'ornate', 'geometric', 'natural', 'macabre', 'celestial')"
        )
        batch_op.add_column(sa.Column("endogamous", sa.BOOLEAN(), server_default="0", nullable=False))
        batch_op.drop_column("motif_sources")
        batch_op.drop_column("symmetry")
        batch_op.drop_column("scale")
        batch_op.drop_column("colour")
        batch_op.drop_column("geometry")
        batch_op.drop_column("ornament")

    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kind", sa.VARCHAR(length=40), server_default="monogamous", nullable=False))
        batch_op.create_check_constraint(op.f("ck_marriages_kind"), "kind IN ('monogamous', 'plural', 'political')")
        batch_op.drop_constraint(op.f("ck_marriages_purpose"), type_="check")
        batch_op.drop_column("purpose")
        batch_op.drop_constraint(op.f("ck_marriages_form"), type_="check")
        batch_op.drop_column("form")

    with op.batch_alter_table("life_dreams", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_life_dreams_aim_kind_id_aim_kinds"), type_="foreignkey")
        batch_op.drop_column("aim_kind_id")

    with op.batch_alter_table("kinship_systems", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payment_value", sa.INTEGER(), server_default="10", nullable=False))
        batch_op.create_check_constraint(op.f("ck_kinship_systems_payment_value_min"), "payment_value >= 0")
        batch_op.add_column(sa.Column("preference", sa.VARCHAR(length=40), server_default="none", nullable=False))
        batch_op.create_check_constraint(op.f("ck_kinship_systems_preference"), "preference IN ('none', 'cross_cousin', 'clan_exogamy', 'moiety_exogamy')")
        batch_op.add_column(sa.Column("payment", sa.VARCHAR(length=40), server_default="none", nullable=False))
        batch_op.create_check_constraint(op.f("ck_kinship_systems_payment"), "payment IN ('none', 'bride_price', 'dowry', 'bride_service')")
        batch_op.alter_column("sibling_union_second", new_column_name="sororate")
        batch_op.alter_column("sibling_union_first", new_column_name="levirate")
        batch_op.drop_constraint(op.f("ck_kinship_systems_adoption"), type_="check")
        batch_op.drop_column("adoption")
        batch_op.drop_constraint(op.f("ck_kinship_systems_first_side"), type_="check")
        batch_op.drop_column("first_side")

    with op.batch_alter_table("household_aggregates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("dwelling_kind", sa.VARCHAR(length=40), server_default="hut", nullable=False))
        batch_op.create_check_constraint(
            op.f("ck_household_aggregates_dwelling_kind"),
            "dwelling_kind IN ('hut', 'longhouse', 'townhouse', 'manor', 'palace', 'tent', 'cave', 'ship', 'tower', 'apartment')",
        )
        batch_op.drop_constraint(batch_op.f("fk_household_aggregates_dwelling_kind_id_dwelling_kinds"), type_="foreignkey")

    with op.batch_alter_table("heroquests", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_heroquests_realm_kind_id_realm_kinds"), type_="foreignkey")
        batch_op.drop_column("realm_kind_id")

    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rule", sa.VARCHAR(length=40), server_default="strategy", nullable=False))
        batch_op.create_check_constraint(op.f("ck_games_rule"), "rule IN ('strategy', 'chance', 'physical')")
        batch_op.drop_constraint(batch_op.f("fk_games_world_id_worlds"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_games_origin_entity_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_games_derived_from_id_games"), type_="foreignkey")
        batch_op.create_foreign_key(batch_op.f("fk_games_origin_entity_id_entities"), "entities", ["origin_entity_id"], ["id"], ondelete="SET NULL")
        batch_op.drop_index(batch_op.f("ix_games_world_id"))
        batch_op.drop_column("description")
        batch_op.drop_column("world_id")
        batch_op.drop_column("prestige")
        batch_op.drop_column("spectators")
        batch_op.drop_column("betting")
        batch_op.drop_column("team_size")
        batch_op.drop_column("violence")
        batch_op.drop_column("chance_share")
        batch_op.drop_constraint(op.f("ck_games_skill"), type_="check")
        batch_op.drop_column("skill")
        batch_op.drop_column("derived_from_id")
        batch_op.drop_column("retired")
        batch_op.drop_column("built_in")

    with op.batch_alter_table("fears", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_fears_fear_kind_id_fear_kinds"), type_="foreignkey")
        batch_op.drop_column("fear_kind_id")

    with op.batch_alter_table("dwellings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kind", sa.VARCHAR(length=40), server_default="hut", nullable=False))
        batch_op.create_check_constraint(
            op.f("ck_dwellings_kind"), "kind IN ('hut', 'longhouse', 'townhouse', 'manor', 'palace', 'tent', 'cave', 'ship', 'tower', 'apartment')"
        )
        batch_op.drop_constraint(batch_op.f("fk_dwellings_dwelling_kind_id_dwelling_kinds"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_dwellings_dwelling_kind_id"))
    map_dwellings_back()
    with op.batch_alter_table("dwellings", schema=None) as batch_op:
        batch_op.drop_column("dwelling_kind_id")
    with op.batch_alter_table("household_aggregates", schema=None) as batch_op:
        batch_op.drop_column("dwelling_kind_id")

    with op.batch_alter_table("dreams", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_dreams_reading_kind_id_reading_kinds"), type_="foreignkey")
        batch_op.drop_column("reading_kind_id")

    with op.batch_alter_table("districts", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_districts_world_material_id_world_materials"), type_="foreignkey")
        batch_op.drop_column("world_material_id")

    with op.batch_alter_table("dishes", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_dishes_derived_from_id_dishes"), type_="foreignkey")
        batch_op.drop_column("fermented")
        batch_op.drop_column("smoky")
        batch_op.drop_column("numbing")
        batch_op.drop_column("cooling")
        batch_op.drop_column("pungent")
        batch_op.drop_column("savoury")
        batch_op.drop_column("bitter")
        batch_op.drop_column("saline")
        batch_op.drop_column("sour")
        batch_op.drop_column("sweet")
        batch_op.drop_column("prep_skill")
        batch_op.drop_constraint(op.f("ck_dishes_category"), type_="check")
        batch_op.drop_column("category")
        batch_op.drop_column("derived_from_id")
        batch_op.drop_column("built_in")

    with op.batch_alter_table("dish_ingredients", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_dish_ingredients_good_kind_id_good_kinds"), type_="foreignkey")
        batch_op.drop_column("good_kind_id")
        batch_op.drop_constraint(op.f("ck_dish_ingredients_role"), type_="check")
        batch_op.drop_column("role")

    with op.batch_alter_table("currencies", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_currencies_issuer_kind"), type_="check")
        batch_op.drop_column("issuer_kind")
        batch_op.drop_column("convertible")
        batch_op.drop_constraint(op.f("ck_currencies_backing"), type_="check")
        batch_op.drop_column("backing")
        batch_op.drop_constraint(op.f("ck_currencies_form"), type_="check")
        batch_op.drop_column("form")

    with op.batch_alter_table("cosmic_offices", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_cosmic_offices_office_kind_id_divine_office_kinds"), type_="foreignkey")
        batch_op.drop_column("office_kind_id")

    with op.batch_alter_table("community_methods", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_community_methods_method_kind_id_production_method_kinds"), type_="foreignkey")
        batch_op.drop_column("method_kind_id")

    with op.batch_alter_table("community_dishes", schema=None) as batch_op:
        batch_op.drop_column("short_epochs")

    with op.batch_alter_table("arms", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_arms_emblem_system_id_emblem_systems"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_arms_emblem_system_id"))
        batch_op.drop_column("emblem_system_id")

    op.create_table(
        "species_yields",
        sa.Column("species_entity_id", sa.INTEGER(), nullable=False),
        sa.Column("product", sa.VARCHAR(length=120), nullable=False),
        sa.Column("commodity", sa.VARCHAR(length=40), nullable=True),
        sa.Column("material", sa.VARCHAR(length=40), nullable=True),
        sa.Column("rate", sa.INTEGER(), nullable=False),
        sa.Column("world_material_id", sa.INTEGER(), nullable=True),
        sa.CheckConstraint(
            "commodity IN ('grain', 'livestock', 'fish', 'fodder', 'timber', 'fuel', 'bread', 'ore', 'stone', 'cloth', 'tools', 'weapons', 'armour', 'mounts', 'siege_materiel', 'medicine', 'luxuries', 'incense', 'sacred_goods', 'magical_reagents', 'meat', 'milk', 'cheese', 'fruit', 'tubers', 'coal', 'peat', 'dung', 'fibre', 'dye', 'herbs', 'brew_base', 'poison', 'eggs', 'wool')",
            name=op.f("ck_species_yields_commodity"),
        ),
        sa.CheckConstraint(
            "material IN ('wood','bone','hide','leather','cloth','stone','flint','obsidian','copper','tin','bronze','iron','steel','silver','gold','glass','crystal','ivory','chitin','dragonbone','star_metal','void_glass','godflesh','living_wood','salt','amber','lead','skysteel','sulfur','clay','gems','mud_brick','fired_brick','dressed_stone','rubble','lime_mortar','hydraulic_concrete','thatch','tile')",
            name=op.f("ck_species_yields_material"),
        ),
        sa.CheckConstraint("rate >= 0", name=op.f("ck_species_yields_rate_min")),
        sa.ForeignKeyConstraint(["species_entity_id"], ["entities.id"], name=op.f("fk_species_yields_species_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["world_material_id"], ["world_materials.id"], name=op.f("fk_species_yields_world_material_id_world_materials"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("species_entity_id", "product", name=op.f("pk_species_yields")),
    )
    op.create_table(
        "game_followings",
        sa.Column("people_entity_id", sa.INTEGER(), nullable=False),
        sa.Column("game_id", sa.INTEGER(), nullable=False),
        sa.Column("popularity", sa.INTEGER(), nullable=False),
        sa.Column("adopted_epoch", sa.INTEGER(), nullable=False),
        sa.Column("locked", sqlite.JSON(), nullable=False),
        sa.CheckConstraint("adopted_epoch >= 0", name=op.f("ck_game_followings_adopted_epoch_min")),
        sa.CheckConstraint("popularity BETWEEN 0 AND 100", name=op.f("ck_game_followings_popularity_range")),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], name=op.f("fk_game_followings_game_id_games"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_game_followings_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", "game_id", name=op.f("pk_game_followings")),
    )
    op.execute(
        "INSERT INTO game_followings (people_entity_id, game_id, popularity, adopted_epoch, locked) SELECT holder_node_id, kind_id, strength, since_epoch, '[]' FROM kind_holdings WHERE concept = 'game' AND holder_node_id IN (SELECT id FROM entities)"
    )
    copy_products("species_products", "species_yields")
    op.drop_table("species_products")
    with op.batch_alter_table("dish_steps", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dish_steps_dish_id"))

    op.drop_table("dish_steps")
    with op.batch_alter_table("colour_meanings", schema=None) as batch_op:
        batch_op.drop_index("ix_colour_meanings_culture")
        batch_op.drop_index(batch_op.f("ix_colour_meanings_colour_term_id"))

    op.drop_table("colour_meanings")
    with op.batch_alter_table("trait_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_trait_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_trait_kinds_origin_node_id"))

    op.drop_table("trait_kinds")
    with op.batch_alter_table("tool_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tool_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_tool_kinds_origin_node_id"))

    op.drop_table("tool_kinds")
    with op.batch_alter_table("tenet_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tenet_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_tenet_kinds_origin_node_id"))

    op.drop_table("tenet_kinds")
    with op.batch_alter_table("substance_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_substance_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_substance_kinds_origin_node_id"))

    op.drop_table("substance_kinds")
    with op.batch_alter_table("scent_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_scent_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_scent_kinds_origin_node_id"))

    op.drop_table("scent_kinds")
    with op.batch_alter_table("realm_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_realm_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_realm_kinds_origin_node_id"))

    op.drop_table("realm_kinds")
    with op.batch_alter_table("reading_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reading_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_reading_kinds_origin_node_id"))

    op.drop_table("reading_kinds")
    with op.batch_alter_table("rank_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_rank_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_rank_kinds_origin_node_id"))

    op.drop_table("rank_kinds")
    with op.batch_alter_table("profession_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_profession_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_profession_kinds_origin_node_id"))

    op.drop_table("profession_kinds")
    with op.batch_alter_table("production_method_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_production_method_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_production_method_kinds_origin_node_id"))

    op.drop_table("production_method_kinds")
    with op.batch_alter_table("organisation_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_organisation_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_organisation_kinds_origin_node_id"))

    op.drop_table("organisation_kinds")
    with op.batch_alter_table("music_traditions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_music_traditions_world_id"))
        batch_op.drop_index(batch_op.f("ix_music_traditions_origin_node_id"))

    op.drop_table("music_traditions")
    with op.batch_alter_table("instrument_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_instrument_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_instrument_kinds_origin_node_id"))

    op.drop_table("instrument_kinds")
    with op.batch_alter_table("good_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_good_kinds_world_id"))
        batch_op.drop_index("ix_good_kinds_stocked_as")
        batch_op.drop_index(batch_op.f("ix_good_kinds_origin_node_id"))

    op.drop_table("good_kinds")
    with op.batch_alter_table("garment_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_garment_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_garment_kinds_origin_node_id"))

    op.drop_table("garment_kinds")
    with op.batch_alter_table("furnishing_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_furnishing_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_furnishing_kinds_origin_node_id"))

    op.drop_table("furnishing_kinds")
    with op.batch_alter_table("fear_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fear_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_fear_kinds_origin_node_id"))

    op.drop_table("fear_kinds")
    with op.batch_alter_table("emblem_systems", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_emblem_systems_world_id"))
        batch_op.drop_index(batch_op.f("ix_emblem_systems_origin_node_id"))

    op.drop_table("emblem_systems")
    with op.batch_alter_table("dwelling_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dwelling_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_dwelling_kinds_origin_node_id"))

    op.drop_table("dwelling_kinds")
    with op.batch_alter_table("drink_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_drink_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_drink_kinds_origin_node_id"))

    op.drop_table("drink_kinds")
    with op.batch_alter_table("divine_office_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_divine_office_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_divine_office_kinds_origin_node_id"))

    op.drop_table("divine_office_kinds")
    with op.batch_alter_table("cuisines", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_cuisines_world_id"))
        batch_op.drop_index(batch_op.f("ix_cuisines_origin_node_id"))

    op.drop_table("cuisines")
    with op.batch_alter_table("colour_terms", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_colour_terms_world_id"))
        batch_op.drop_index(batch_op.f("ix_colour_terms_origin_node_id"))

    op.drop_table("colour_terms")
    with op.batch_alter_table("aim_kinds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_aim_kinds_world_id"))
        batch_op.drop_index(batch_op.f("ix_aim_kinds_origin_node_id"))

    op.drop_table("aim_kinds")
    with op.batch_alter_table("kind_holdings", schema=None) as batch_op:
        batch_op.drop_index("ix_kind_holdings_kind")
        batch_op.drop_index("ix_kind_holdings_holder")

    op.drop_table("kind_holdings")
    retype(False)
    op.execute(
        "UPDATE tradition_profiles SET kind = (SELECT CASE g4b_stage.stage WHEN 'death' THEN 'funeral_rite' WHEN 'union' THEN 'marriage_rite' ELSE 'coming_of_age' END FROM g4b_stage WHERE g4b_stage.id = tradition_profiles.tradition_entity_id) WHERE tradition_entity_id IN (SELECT id FROM g4b_stage)"
    )
    op.execute("DROP TABLE g4b_stage")
    op.execute("UPDATE marriages SET kind = 'plural' WHERE id IN (SELECT id FROM g4c_mback WHERE form IN ('plural', 'group'))")
    op.execute("UPDATE marriages SET kind = 'political' WHERE id IN (SELECT id FROM g4c_mback WHERE purpose = 'alliance')")
    op.execute("UPDATE people_culture SET marriage = 'group' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE form = 'group')")
    op.execute(
        "UPDATE people_culture SET marriage = 'polygyny' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE form = 'plural' AND plural_side != 'second')"
    )
    op.execute(
        "UPDATE people_culture SET marriage = 'polyandry' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE form = 'plural' AND plural_side = 'second')"
    )
    op.execute("UPDATE people_culture SET endogamous = 1 WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE endogamy = 'people')")
    op.execute("UPDATE kinship_systems SET preference = 'clan_exogamy' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE exogamy = 'line')")
    op.execute("UPDATE kinship_systems SET preference = 'moiety_exogamy' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE exogamy = 'moiety')")
    op.execute(
        "UPDATE kinship_systems SET preference = 'cross_cousin' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE kin_match = 'cross_cousin' AND exogamy NOT IN ('line', 'moiety'))"
    )
    op.execute("UPDATE kinship_systems SET payment = 'bride_service' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE exchange = 'service')")
    op.execute("UPDATE kinship_systems SET payment = 'bride_price' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE exchange = 'to_one_family')")
    op.execute("UPDATE kinship_systems SET payment = 'dowry' WHERE people_entity_id IN (SELECT id FROM g4c_back WHERE exchange = 'from_one_family')")
    op.execute(
        "UPDATE kinship_systems SET payment_value = (SELECT exchange_value FROM g4c_back WHERE g4c_back.id = kinship_systems.people_entity_id) WHERE people_entity_id IN (SELECT id FROM g4c_back)"
    )
    op.execute("DROP TABLE g4c_mback")
    op.execute("DROP TABLE g4c_back")
    op.execute("UPDATE legacy_traits SET key = 'austere' WHERE kind = 'aesthetic' AND key = '15,55,20,45,65'")
    op.execute("UPDATE legacy_traits SET key = 'ornate' WHERE kind = 'aesthetic' AND key = '90,50,80,60,60'")
    op.execute("UPDATE legacy_traits SET key = 'geometric' WHERE kind = 'aesthetic' AND key = '50,90,45,55,85'")
    op.execute("UPDATE legacy_traits SET key = 'natural' WHERE kind = 'aesthetic' AND key = '40,10,55,40,30'")
    op.execute("UPDATE legacy_traits SET key = 'macabre' WHERE kind = 'aesthetic' AND key = '60,40,25,50,45'")
    op.execute("UPDATE legacy_traits SET key = 'celestial' WHERE kind = 'aesthetic' AND key = '60,65,70,80,70'")
    op.execute(
        "UPDATE people_culture SET aesthetic = (SELECT f.name FROM aes_family f, aes_people b WHERE b.id = people_culture.people_entity_id ORDER BY abs(f.o-b.o)+abs(f.g-b.g)+abs(f.c-b.c)+abs(f.s-b.s)+abs(f.y-b.y) LIMIT 1) WHERE people_entity_id IN (SELECT id FROM aes_people)"
    )
    op.execute(
        "UPDATE structure_profiles SET aesthetic = (SELECT f.name FROM aes_family f, aes_works b WHERE b.id = structure_profiles.structure_entity_id ORDER BY abs(f.o-b.o)+abs(f.g-b.g)+abs(f.c-b.c)+abs(f.s-b.s)+abs(f.y-b.y) LIMIT 1) WHERE structure_entity_id IN (SELECT id FROM aes_works)"
    )
    op.execute("DROP TABLE aes_family")
    op.execute("DROP TABLE aes_people")
    op.execute("DROP TABLE aes_works")
