import sqlalchemy as sa
from alembic import op

revision = "62954d40b909"
down_revision = "4676154cc03c"
branch_labels = None
depends_on = None


BELIEFSOURCE_OLD = ("observation", "message", "rumour", "spy", "scout", "records", "deception")
BELIEFSOURCE_NEW = (
    "observation",
    "message",
    "rumour",
    "spy",
    "scout",
    "records",
    "deception",
    "network",
    "foresight",
    "mind_reading",
    "intrusion",
    "surveillance",
    "made_mind_report",
)
BELIEFSOURCE_RENAMED = ()
BIASEDDECISION_OLD = ("raid", "peace", "surrender", "scheme", "belief", "conversion", "migration", "god_goal")
BIASEDDECISION_NEW = (
    "raid",
    "peace",
    "surrender",
    "scheme",
    "belief",
    "conversion",
    "migration",
    "god_goal",
    "war",
    "retreat",
    "trade",
    "alliance",
    "succession",
    "law",
    "research",
)
BIASEDDECISION_RENAMED = ()
METHODKIND_OLD = (
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
    "spun_fibre",
    "vat_culture",
    "bioreactor",
)
METHODKIND_NEW = (
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
)
METHODKIND_RENAMED = (("spun_fibre", "fibre_from_life"),)
TISSUEMATERIAL_OLD = ("flesh", "hide", "scale", "chitin", "feather", "bone", "wood", "stone", "crystal", "metal", "ice", "fire", "steam", "void_stuff")
TISSUEMATERIAL_NEW = (
    "soft_tissue",
    "hide",
    "plates",
    "shell",
    "plumage",
    "rigid",
    "fibrous",
    "frozen",
    "vapour",
    "mineral",
    "metallic",
    "crystalline",
    "gel",
    "energy",
    "insubstantial",
)
TISSUEMATERIAL_RENAMED = (
    ("flesh", "soft_tissue"),
    ("scale", "plates"),
    ("chitin", "shell"),
    ("feather", "plumage"),
    ("bone", "rigid"),
    ("wood", "fibrous"),
    ("stone", "mineral"),
    ("crystal", "crystalline"),
    ("metal", "metallic"),
    ("ice", "frozen"),
    ("fire", "energy"),
    ("steam", "vapour"),
    ("void_stuff", "insubstantial"),
)
DIVINEWOUNDKIND_OLD = ("severed_domain", "shattered_manifestation", "stolen_name", "void_wound")
DIVINEWOUNDKIND_NEW = (
    "severed_domain",
    "shattered_manifestation",
    "stolen_name",
    "void_wound",
    "drained_essence",
    "lost_worshippers",
    "bound",
    "split_aspect",
    "forgotten_name",
)
DIVINEWOUNDKIND_RENAMED = ()
EPOCHSTEPKIND_OLD = (
    "completion",
    "backup",
    "distribution",
    "naming",
    "fate_judgment",
    "chronicle",
    "voices",
    "council",
    "epoch_words",
    "local_gods",
    "transition",
    "world_birth",
    "network_repair",
    "prune",
    "images",
    "localisation",
    "background",
)
EPOCHSTEPKIND_NEW = (
    "backup",
    "distribution",
    "fate_judgment",
    "chronicle",
    "voices",
    "council",
    "epoch_words",
    "local_gods",
    "transition",
    "world_birth",
    "network_repair",
    "prune",
    "images",
    "localisation",
    "background",
)
EPOCHSTEPKIND_RENAMED = ()
GROUPKIND_OLD = ("household", "court", "circle", "warband", "crew")
GROUPKIND_NEW = ("household", "court", "circle", "warband", "crew", "cell", "band", "team")
GROUPKIND_RENAMED = ()
IDEASOURCE_OLD = ("ideology", "doctrine", "theory", "book", "teacher", "divine", "player")
IDEASOURCE_NEW = ("ideology", "doctrine", "theory", "book", "teacher", "divine", "player", "network", "made_mind")
IDEASOURCE_RENAMED = ()
INSPIRATIONKIND_OLD = ("masterwork_fever", "research_insight", "heroic_resolve")
INSPIRATIONKIND_NEW = ("masterwork_fever", "research_insight", "heroic_resolve", "artistic_vision", "technical_breakthrough", "spiritual_insight")
INSPIRATIONKIND_RENAMED = ()
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
    "stitch_route",
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
    "weave_bond",
    "pray_to_creator",
    "harvest_resource",
    "gift",
    "holy_world",
    "interworld_treaty",
    "foreign_god_war",
    "open_cosmic_bed",
    "stitch_leak",
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
    "weave_chimera",
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
ACTIONKIND_RENAMED = (("stitch_route", "repair_route"), ("weave_bond", "make_bond"), ("stitch_leak", "close_leak"), ("weave_chimera", "make_chimera"))
LONGPLANKIND_OLD = ("ecological_transformation", "bloodline", "conversion", "wonder", "forecast")
LONGPLANKIND_NEW = (
    "ecological_transformation",
    "bloodline",
    "conversion",
    "wonder",
    "forecast",
    "network",
    "megastructure",
    "programme",
    "realm",
    "line",
    "reform",
    "exploration",
)
LONGPLANKIND_RENAMED = ()
LOREKIND_OLD = ("technique", "site", "map", "prophecy")
LOREKIND_NEW = ("technique", "site", "map", "prophecy", "true_name", "weakness", "pattern", "source")
LOREKIND_RENAMED = ()
MEDIUM_OLD = ("envoy", "letter", "herald", "signal_fire", "dream", "bird", "magic_sending", "network")
MEDIUM_NEW = ("envoy", "letter", "herald", "signal_fire", "dream", "bird", "magic_sending", "network", "mind_link", "broadcast")
MEDIUM_RENAMED = ()
FACET_OLD = (
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
    "tolerance_of_strangeness",
    "humour",
    "sense_of_duty",
    "greed",
)
FACET_NEW = (
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
)
FACET_RENAMED = (("tolerance_of_strangeness", "tolerance_of_difference"),)
ENERGYKIND_OLD = ("muscle", "water", "wind", "heat", "magic", "divine")
ENERGYKIND_NEW = (
    "muscle",
    "water",
    "wind",
    "heat",
    "magic",
    "divine",
    "fuel",
    "electric",
    "stored",
    "solar",
    "geothermal",
    "tidal",
    "fission",
    "fusion",
    "stellar",
    "source",
    "feed",
    "belief",
    "void",
)
ENERGYKIND_RENAMED = ()
MODIFIERSOURCE_OLD = (
    "injury",
    "condition",
    "trait",
    "law",
    "tradition",
    "artwork",
    "doctrine",
    "treaty",
    "structure",
    "wonder",
    "terrain",
    "weather",
    "season",
    "natural_law",
    "god_power",
    "blessing",
    "perk",
    "curse",
    "dominion",
    "phenomenon",
    "cosmos",
    "rift",
    "god_death",
    "player",
    "suppression",
    "pin",
)
MODIFIERSOURCE_NEW = (
    "injury",
    "condition",
    "trait",
    "law",
    "tradition",
    "artwork",
    "doctrine",
    "treaty",
    "structure",
    "wonder",
    "terrain",
    "weather",
    "season",
    "natural_law",
    "law_grammar",
    "god_power",
    "blessing",
    "perk",
    "curse",
    "dominion",
    "phenomenon",
    "cosmos",
    "rift",
    "god_death",
    "player",
    "suppression",
    "pin",
)
MODIFIERSOURCE_RENAMED = ()
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
    "web_spinner",
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
PERKKIND_RENAMED = (("web_spinner", "network_builder"),)
NEEDKIND_OLD = (
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
)
NEEDKIND_NEW = (
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
)
NEEDKIND_RENAMED = ()
PASSIONKIND_OLD = ("love", "loyalty", "hatred", "devotion")
PASSIONKIND_NEW = (
    "love",
    "loyalty",
    "hatred",
    "devotion",
    "ambition",
    "envy",
    "grief",
    "curiosity",
    "fear",
    "shame",
    "pride",
    "jealousy",
    "admiration",
    "obsession",
)
PASSIONKIND_RENAMED = ()
PREFERENCEKIND_OLD = (
    "material",
    "food",
    "drink",
    "creature",
    "plant",
    "colour",
    "shape",
    "art_form",
    "artwork_subject",
    "season",
    "weather",
    "terrain",
    "activity",
    "craft",
    "deity_aspect",
    "looks",
)
PREFERENCEKIND_NEW = (
    "material",
    "food",
    "drink",
    "creature",
    "plant",
    "colour",
    "shape",
    "art_form",
    "artwork_subject",
    "season",
    "weather",
    "terrain",
    "activity",
    "craft",
    "deity_aspect",
    "looks",
    "technology",
    "made_thing",
    "power",
    "source",
    "living_line",
    "network",
    "sound",
    "scent",
    "texture",
    "story_form",
    "game",
    "place_kind",
    "profession",
)
PREFERENCEKIND_RENAMED = ()
SETUPKIND_OLD = ("prophecy", "omen", "dream", "foresight", "thread", "portent")
SETUPKIND_NEW = ("prophecy", "omen", "dream", "foresight", "incident_arc", "portent")
SETUPKIND_RENAMED = (("thread", "incident_arc"),)
TRADEPOLICYKIND_OLD = ("tariff", "subsidy", "embargo")
TRADEPOLICYKIND_NEW = ("tariff", "subsidy", "embargo", "quota", "licence", "price_control", "free_trade", "export_ban", "sanction")
TRADEPOLICYKIND_RENAMED = ()
TURNCOUNTER_OLD = (
    "season_order",
    "weather_shaping",
    "sibling_messages",
    "narrative_bonds",
    "prayers",
    "free_living_creation",
    "free_land_creation",
    "anchor_chosen",
    "words_coined",
    "gifts",
    "holy_world",
    "leak_stitched",
    "take_life",
    "intrigue",
    "outer_bargain",
    "harvests",
    "discoveries",
    "claims",
    "worship_changes",
    "learning",
    "prophecies",
    "commander_appointments",
    "adoptions",
    "explorations",
    "resurrection_rites",
    "languages_founded",
    "cultures_created",
    "land_rewards",
    "laws_enacted",
    "officers_appointed",
    "taxes_set",
    "treaties_proposed",
    "oaths_sworn",
    "faction_acts",
)
TURNCOUNTER_NEW = (
    "season_order",
    "weather_shaping",
    "sibling_messages",
    "narrative_bonds",
    "prayers",
    "free_living_creation",
    "free_land_creation",
    "anchor_chosen",
    "words_coined",
    "gifts",
    "holy_world",
    "leak_closed",
    "take_life",
    "intrigue",
    "outer_bargain",
    "harvests",
    "discoveries",
    "claims",
    "worship_changes",
    "learning",
    "prophecies",
    "commander_appointments",
    "adoptions",
    "explorations",
    "resurrection_rites",
    "languages_founded",
    "cultures_created",
    "land_rewards",
    "laws_enacted",
    "officers_appointed",
    "taxes_set",
    "treaties_proposed",
    "oaths_sworn",
    "faction_acts",
)
TURNCOUNTER_RENAMED = (("leak_stitched", "leak_closed"),)
POWERSTATE_OLD = ("latent", "emerging", "active", "strained", "burned_out", "suppressed", "lost")
POWERSTATE_NEW = ("latent", "emerging", "active", "strained", "exhausted", "suppressed", "lost")
POWERSTATE_RENAMED = (("burned_out", "exhausted"),)
CLIMATEERA_OLD = ("temperate", "drought", "rain", "ice_age", "scorching")
CLIMATEERA_NEW = ("temperate", "drought", "rain", "ice_age", "scorching", "hothouse", "snowball", "variable", "wet_cold")
CLIMATEERA_RENAMED = ()
COUNCILMOTION_OLD = (
    "none",
    "against_doomsday",
    "joint_blessing",
    "condemn_rebel",
    "call_for_peace",
    "war_on_foreign_god",
    "divide_worlds",
    "outlaw_rite",
    "punish_son",
    "bless_hero",
    "holy_world",
    "cosmic_truce",
    "petition_creator",
    "appoint_office",
)
COUNCILMOTION_NEW = (
    "none",
    "against_doomsday",
    "joint_blessing",
    "condemn_rebel",
    "call_for_peace",
    "war_on_foreign_god",
    "divide_worlds",
    "outlaw_rite",
    "punish_son",
    "bless_hero",
    "holy_world",
    "cosmic_truce",
    "petition_creator",
    "appoint_office",
    "reassign_world",
    "outlaw_power",
    "outlaw_source",
    "admit_member",
    "expel_member",
    "recognise_god",
    "essence_tithe",
    "set_council_rules",
    "regulate_made_minds",
    "regulate_powers",
    "regulate_living_craft",
)
COUNCILMOTION_RENAMED = ()
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
    "void_pirates",
    "peoples_army",
    "holy_guard",
    "mercenary_army",
    "dialect",
    "primitive_language",
    "currency",
    "eclipse_prophecy",
    "cosmic_travel_resource",
    "golem",
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
    "domesticated",
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
ENGINEKIND_RENAMED = (("void_pirates", "route_raiders"),)
FOREIGNGODPOWEREFFECT_OLD = ("shield", "caller", "thief", "destroyer", "fertile", "reviving", "deathless", "sharp_tongued")
FOREIGNGODPOWEREFFECT_NEW = ("shield", "caller", "thief", "destroyer", "fertile", "reviving", "deathless", "persuasion")
FOREIGNGODPOWEREFFECT_RENAMED = (("sharp_tongued", "persuasion"),)
POWEREFFECT_OLD = (
    "cheap_creation",
    "duel_master",
    "essence_spring",
    "worshipped",
    "tireless",
    "untouchable",
    "dream_whisper",
    "war_father",
    "harvester",
    "seer",
    "reviving",
    "bounty_giver",
    "curser",
)
POWEREFFECT_NEW = (
    "cheap_creation",
    "duel_master",
    "essence_spring",
    "worshipped",
    "tireless",
    "untouchable",
    "dream_sending",
    "war_leader",
    "harvester",
    "seer",
    "reviving",
    "bounty_giver",
    "curser",
)
POWEREFFECT_RENAMED = (("war_father", "war_leader"), ("dream_whisper", "dream_sending"))
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
)
TRAITKIND_RENAMED = ()
ACCOUNTKIND_OLD = ("official_chronicle", "folk_memory", "foreign_account", "gospel", "epic", "inscription", "founding_myth", "elder_memory")
ACCOUNTKIND_NEW = (
    "official_chronicle",
    "folk_memory",
    "foreign_account",
    "gospel",
    "epic",
    "inscription",
    "founding_myth",
    "elder_memory",
    "record",
    "testimony",
)
ACCOUNTKIND_RENAMED = ()
ACCOUNTMEDIUM_OLD = ("artwork", "book", "oral", "inscription")
ACCOUNTMEDIUM_NEW = ("artwork", "book", "oral", "inscription", "record", "performance", "mind_state")
ACCOUNTMEDIUM_RENAMED = ()
STRATUMKIND_OLD = ("paradise", "plain", "torment", "oblivion", "warrior_hall", "ancestor_hall")
STRATUMKIND_NEW = ("reward", "common", "punishment", "dissolution", "by_manner_of_death", "by_line")
STRATUMKIND_RENAMED = (
    ("paradise", "reward"),
    ("plain", "common"),
    ("torment", "punishment"),
    ("oblivion", "dissolution"),
    ("warrior_hall", "by_manner_of_death"),
    ("ancestor_hall", "by_line"),
)
HERALDRYHOLDERKIND_OLD = ("house", "polity", "title", "army", "guild")
HERALDRYHOLDERKIND_NEW = ("house", "polity", "title", "army", "guild", "company", "order", "people")
HERALDRYHOLDERKIND_RENAMED = ()
BLUEPRINTKIND_OLD = ("vessel", "siege_engine", "structure", "artifact_pattern")
BLUEPRINTKIND_NEW = ("vessel", "siege_engine", "structure", "artifact_pattern", "made_body", "augment", "line", "network", "rite_pattern")
BLUEPRINTKIND_RENAMED = ()
CHALLENGEKIND_OLD = ("disaster", "climate", "invasion", "plague", "famine")
CHALLENGEKIND_NEW = (
    "disaster",
    "climate",
    "invasion",
    "plague",
    "famine",
    "collapse",
    "secession",
    "technological_shock",
    "source_depletion",
    "runaway",
    "revelation",
    "migration_wave",
)
CHALLENGEKIND_RENAMED = ()
COMMANDERTRAIT_OLD = (
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
)
COMMANDERTRAIT_NEW = (
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
    "forest_fighter",
    "desert_fighter",
    "marsh_fighter",
    "sky_commander",
    "space_commander",
    "artillerist",
    "ambusher",
    "logistician",
    "underground_fighter",
    "amphibious_commander",
    "siege_defender",
    "skirmisher",
    "armoured_commander",
    "disciplinarian",
    "signals_commander",
    "night_fighter",
)
COMMANDERTRAIT_RENAMED = ()
COMMONSKIND_OLD = ("pasture", "woods", "fishery")
COMMONSKIND_NEW = ("pasture", "woods", "fishery", "water", "hunting_ground", "quarry", "spectrum", "orbits", "source_ground")
COMMONSKIND_RENAMED = ()
CRIMEKIND_OLD = (
    "theft",
    "blasphemy",
    "treason",
    "murder",
    "desertion",
    "witchcraft",
    "mind_theft",
    "unlicensed_copying",
    "forced_edit",
    "erasure",
    "machine_seizure",
    "impersonation",
    "mind_compulsion",
)
CRIMEKIND_NEW = (
    "theft",
    "burglary",
    "robbery",
    "fraud",
    "embezzlement",
    "counterfeiting",
    "smuggling",
    "poaching",
    "arson",
    "vandalism",
    "trespass",
    "receiving",
    "murder",
    "manslaughter",
    "assault",
    "kidnapping",
    "trafficking",
    "sexual_violence",
    "threats",
    "duelling",
    "riot",
    "sedition",
    "banditry",
    "piracy",
    "rebellion",
    "vagrancy",
    "unlawful_assembly",
    "desertion",
    "mutiny",
    "cowardice",
    "looting",
    "war_crimes",
    "treason",
    "espionage",
    "bribery",
    "corruption",
    "usurpation",
    "contempt_of_court",
    "perjury",
    "election_fraud",
    "tax_evasion",
    "customs_fraud",
    "debasement",
    "unlicensed_trade",
    "quarantine_breach",
    "well_poisoning",
    "tainted_goods",
    "unlawful_pollution",
    "union_offence",
    "sumptuary_breach",
    "forbidden_food",
    "intoxication",
    "taboo_breach",
    "purity_breach",
    "blasphemy",
    "heresy",
    "sacrilege",
    "desecration",
    "forbidden_rite",
    "witchcraft",
    "oathbreaking",
    "unlicensed_power",
    "false_claim",
    "forged_line",
    "heir_murder",
    "mind_theft",
    "unlicensed_copying",
    "forced_edit",
    "erasure",
    "machine_seizure",
    "impersonation",
    "mind_compulsion",
)
CRIMEKIND_RENAMED = ()
TRIALKIND_OLD = ("judge", "jury", "combat", "ordeal")
TRIALKIND_NEW = (
    "judge",
    "jury",
    "combat",
    "ordeal",
    "council",
    "arbitration",
    "oracle",
    "divine_judgement",
    "assembly",
    "inquisition",
    "mediation",
    "made_judge",
)
TRIALKIND_RENAMED = ()
FANATICISMKIND_OLD = ("inquisition", "iconoclasm", "crusade")
FANATICISMKIND_NEW = (
    "inquisition",
    "iconoclasm",
    "crusade",
    "purge",
    "forced_conversion",
    "martyrdom",
    "mortification",
    "book_burning",
    "persecution",
    "millenarian_flight",
)
FANATICISMKIND_RENAMED = ()
HOLDINGKIND_OLD = ("temple", "land", "relic", "holy_place", "monastery")
HOLDINGKIND_NEW = ("temple", "land", "relic", "holy_place", "monastery", "network", "shares", "lines")
HOLDINGKIND_RENAMED = ()
HONOURMODEL_OLD = ("dignity", "honour", "face")
HONOURMODEL_NEW = ("dignity", "honour", "face", "none")
HONOURMODEL_RENAMED = ()
DATINGSYSTEMKIND_OLD = ("regnal", "founding", "religious", "celestial_cycle")
DATINGSYSTEMKIND_NEW = ("regnal", "founding", "religious", "celestial_cycle", "creation", "event", "cycle_count")
DATINGSYSTEMKIND_RENAMED = ()
DESIGNKIND_OLD = ("vessel", "skyship", "siege_engine", "land_vehicle", "spacecraft")
DESIGNKIND_NEW = (
    "vessel",
    "skyship",
    "siege_engine",
    "land_vehicle",
    "spacecraft",
    "air_vehicle",
    "underwater_vessel",
    "living_vessel",
    "made_body",
    "weapon_system",
)
DESIGNKIND_RENAMED = ()
AFTERLIFEMODEL_OLD = ("judged_realms", "common_realm", "warrior_hall", "ancestor_hall", "rebirth", "wandering", "union", "oblivion")
AFTERLIFEMODEL_NEW = ("judged_realms", "common_realm", "realm_by_death", "realm_of_line", "rebirth", "wandering", "union", "oblivion")
AFTERLIFEMODEL_RENAMED = (("warrior_hall", "realm_by_death"), ("ancestor_hall", "realm_of_line"))
ERADEED_OLD = ("first_technique", "first_institution", "great_victory", "wonder", "great_person", "defeat", "famine")
ERADEED_NEW = (
    "first_technique",
    "first_institution",
    "great_victory",
    "wonder",
    "great_person",
    "defeat",
    "famine",
    "first_network",
    "first_made_mind",
    "first_line",
    "revelation",
    "collapse",
)
ERADEED_RENAMED = ()
EVENTPHASE_OLD = ("onset", "peak", "aftermath")
EVENTPHASE_NEW = ("onset", "peak", "aftermath", "memory")
EVENTPHASE_RENAMED = ()
FACTIONKIND_OLD = (
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
    "workers_union",
    "engineers_society",
    "financiers",
    "veterans",
)
FACTIONKIND_NEW = (
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
)
FACTIONKIND_RENAMED = (("void_pirates", "route_raiders"),)
FEUDPARTY_OLD = ("house", "community")
FEUDPARTY_NEW = ("house", "community", "people")
FEUDPARTY_RENAMED = ()
FEUDSTATUS_OLD = ("active", "mediated", "faded", "ended")
FEUDSTATUS_NEW = ("active", "mediated", "faded", "ended", "settled", "outlawed", "extinguished")
FEUDSTATUS_RENAMED = ()
GATHERINGKIND_OLD = (
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
    "examination",
    "election",
    "rally",
    "strike",
    "convention",
    "launch",
    "broadcast",
    "testing",
)
GATHERINGKIND_NEW = (
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
    "examination",
    "election",
    "rally",
    "strike",
    "convention",
    "launch",
    "broadcast",
    "testing",
    "exhibition",
    "trade_fair",
    "summit_of_gods",
    "network_gathering",
    "realm_gathering",
    "mourning",
    "initiation",
    "sport_match",
)
GATHERINGKIND_RENAMED = ()
IMPURITYSOURCE_OLD = (
    "the_dead",
    "birth",
    "bodily_fluids",
    "food",
    "species",
    "profession",
    "outsiders",
    "place",
    "object",
    "act",
    "made_thing",
    "taboo",
    "wound",
)
IMPURITYSOURCE_NEW = (
    "the_dead",
    "birth",
    "bodily_fluids",
    "food",
    "species",
    "profession",
    "outsiders",
    "place",
    "object",
    "act",
    "made_thing",
    "taboo",
    "wound",
    "augment",
    "designed_body",
)
IMPURITYSOURCE_RENAMED = ()
CURSEKIND_OLD = ("none", "bloodthirst", "misfortune", "wasting", "madness", "betrayal")
CURSEKIND_NEW = (
    "none",
    "bloodthirst",
    "misfortune",
    "wasting",
    "madness",
    "betrayal",
    "barrenness",
    "transformation",
    "sleep",
    "silence",
    "hunger",
    "forgetting",
    "restlessness",
    "line_curse",
    "place_curse",
    "compulsion",
    "aging",
    "exposure",
)
CURSEKIND_RENAMED = ()
LEGACYKIND_OLD = ("martial_style", "aesthetic", "funeral_rite", "belief", "value", "innovation", "art_form")
LEGACYKIND_NEW = ("martial_style", "aesthetic", "funeral_rite", "belief", "value", "innovation", "art_form", "technique", "law", "institution", "language")
LEGACYKIND_RENAMED = ()
MAGICSITEKIND_OLD = ("source", "school_seat", "ward", "gateway")
MAGICSITEKIND_NEW = ("source", "school_seat", "ward", "gateway", "tide_point", "depletion_scar")
MAGICSITEKIND_RENAMED = ()
MARRIAGEEND_OLD = ("death", "divorce", "annulment", "war")
MARRIAGEEND_NEW = ("death", "divorce", "annulment", "war", "term")
MARRIAGEEND_RENAMED = ()
MISHAPKIND_OLD = ("illness", "crop_failure", "child_death", "livestock_death", "accident", "bad_luck")
MISHAPKIND_NEW = (
    "illness",
    "crop_failure",
    "child_death",
    "livestock_death",
    "accident",
    "bad_luck",
    "fall",
    "crush",
    "cut",
    "burn",
    "scald",
    "drowning",
    "beast",
    "tool",
    "machine",
    "vehicle",
    "collapse",
    "house_fire",
    "poisoning",
    "choking",
    "exposure",
    "lightning",
    "sport",
    "brawl",
    "lost_way",
    "stores_spoiled",
    "goods_lost",
    "purse_lost",
    "theft_suffered",
    "tool_broken",
    "near_miss",
)
MISHAPKIND_RENAMED = ()
MISHAPATTRIBUTION_OLD = ("chance", "known_cause", "witchcraft", "curse", "god", "spirit", "ancestor", "omen", "fate", "enemy_scheme", "impurity", "broken_oath")
MISHAPATTRIBUTION_NEW = (
    "chance",
    "known_cause",
    "witchcraft",
    "curse",
    "god",
    "spirit",
    "ancestor",
    "omen",
    "fate",
    "enemy_scheme",
    "impurity",
    "broken_oath",
    "made_mind",
    "hidden_people",
)
MISHAPATTRIBUTION_RENAMED = ()
NORMSITUATION_OLD = (
    "funeral",
    "feast",
    "wedding",
    "court",
    "temple",
    "market",
    "battle",
    "duel",
    "hospitality",
    "mourning",
    "sacred_day",
    "stranger",
    "superior",
)
NORMSITUATION_NEW = (
    "funeral",
    "feast",
    "wedding",
    "court",
    "temple",
    "market",
    "battle",
    "duel",
    "hospitality",
    "mourning",
    "sacred_day",
    "outsider",
    "superior",
    "network_space",
    "realm",
    "workplace",
    "council",
    "encounter_with_made_mind",
    "encounter_with_gifted",
    "encounter_with_hidden",
)
NORMSITUATION_RENAMED = (("stranger", "outsider"),)
NORMBEHAVIOUR_OLD = (
    "jest",
    "boast",
    "insult",
    "flattery",
    "flirting",
    "gifts",
    "quarrels",
    "blows",
    "weapons_carried",
    "fine_dress",
    "plain_speech",
    "forbidden_food",
    "secrets",
)
NORMBEHAVIOUR_NEW = (
    "jest",
    "boast",
    "insult",
    "flattery",
    "flirting",
    "gifts",
    "quarrels",
    "blows",
    "weapons_carried",
    "fine_dress",
    "plain_speech",
    "forbidden_food",
    "secrets",
    "augment_display",
    "power_display",
    "data_sharing",
    "copy_disclosure",
)
NORMBEHAVIOUR_RENAMED = ()
OATHKIND_OLD = ("fealty", "vengeance", "celibacy", "pilgrimage", "protection", "silence", "sworn_kinship")
OATHKIND_NEW = (
    "fealty",
    "vengeance",
    "celibacy",
    "pilgrimage",
    "protection",
    "silence",
    "sworn_kinship",
    "service",
    "poverty",
    "nonviolence",
    "fidelity",
    "secrecy",
)
OATHKIND_RENAMED = ()
SECRETKIND_OLD = ("hidden_resource", "buried_relic", "sealed_spirit", "lost_knowledge", "lost_rite", "underworld_entrance")
SECRETKIND_NEW = (
    "hidden_resource",
    "buried_relic",
    "sealed_spirit",
    "lost_knowledge",
    "lost_rite",
    "underworld_entrance",
    "hidden_people",
    "dormant_mind",
    "sealed_realm",
)
SECRETKIND_RENAMED = ()
AGEKIND_OLD = ("normal", "golden", "dark", "heroic")
AGEKIND_NEW = ("normal", "golden", "dark", "heroic", "rising", "declining", "transforming", "stagnant")
AGEKIND_RENAMED = ()
PREPAREDNESSKIND_OLD = ("levee", "firebreak", "stockpile", "drill", "watchtower", "seawall")
PREPAREDNESSKIND_NEW = (
    "levee",
    "firebreak",
    "stockpile",
    "drill",
    "watchtower",
    "seawall",
    "quarantine_plan",
    "shelters",
    "warning_network",
    "evacuation_routes",
    "ward",
    "reserves_of_energy",
)
PREPAREDNESSKIND_RENAMED = ()
PRESSUREKIND_OLD = ("hunger", "insecurity", "overcrowding", "poverty", "impiety", "humiliation", "stagnation")
PRESSUREKIND_NEW = (
    "hunger",
    "insecurity",
    "overcrowding",
    "poverty",
    "impiety",
    "humiliation",
    "stagnation",
    "pollution",
    "unemployment",
    "oppression",
    "disease_burden",
    "purposelessness",
)
PRESSUREKIND_RENAMED = ()
RACKETKIND_OLD = ("protection", "smuggling", "gambling", "fencing", "kidnapping", "counterfeiting")
RACKETKIND_NEW = (
    "protection",
    "smuggling",
    "gambling",
    "fencing",
    "kidnapping",
    "counterfeiting",
    "fraud",
    "extortion",
    "trafficking",
    "intoxicants",
    "data_theft",
    "loan_sharking",
    "arms",
)
RACKETKIND_RENAMED = ()
REGISTRYKIND_OLD = ("land_title", "debt", "sale", "dowry", "indenture")
REGISTRYKIND_NEW = ("land_title", "debt", "sale", "dowry", "indenture", "patent", "pattern", "mind_state", "line", "company", "birth", "death", "citizenship")
REGISTRYKIND_RENAMED = ()
SUMMONFORM_OLD = ("spirit", "beast", "undead")
SUMMONFORM_NEW = ("spirit", "beast", "undead", "person", "made_thing", "outer_being", "aspect", "phenomenon", "double")
SUMMONFORM_RENAMED = ()
ROUTECLOSURE_OLD = ("sealed", "severed", "forgotten", "collapsed", "snapped", "scorched")
ROUTECLOSURE_NEW = ("sealed", "severed", "forgotten", "worn", "collapsed", "snapped", "scorched")
ROUTECLOSURE_RENAMED = ()
SERVITORROLE_OLD = ("messenger", "guard", "judge", "host", "spy")
SERVITORROLE_NEW = ("messenger", "guard", "judge", "host", "spy", "agent", "avenger", "guide_of_souls", "worshipper", "warden", "scribe")
SERVITORROLE_RENAMED = ()
SIZETIER_OLD = ("hamlet", "village", "town", "city", "metropolis")
SIZETIER_NEW = ("hamlet", "village", "town", "city", "metropolis", "megalopolis", "world_city")
SIZETIER_RENAMED = ()
SHOTKIND_OLD = ("round", "chain", "grape", "fire")
SHOTKIND_NEW = ("round", "chain", "grape", "fire", "solid", "spread", "incendiary", "explosive", "piercing", "guided", "energy")
SHOTKIND_RENAMED = ()
SIGNALKIND_OLD = ("fire_beacon", "mirror_tower", "post_station", "sending_stone")
SIGNALKIND_NEW = ("beacon_chain", "optical_relay", "courier_post", "bound_pair", "wire_station", "radio_station", "mind_link_station", "grown_node")
SIGNALKIND_RENAMED = (("fire_beacon", "beacon_chain"), ("mirror_tower", "optical_relay"), ("post_station", "courier_post"), ("sending_stone", "bound_pair"))
SOUNDCHANGEKIND_OLD = ("shift", "lenition", "vowel_shift", "merger", "loss")
SOUNDCHANGEKIND_NEW = ("shift", "lenition", "vowel_shift", "merger", "loss", "metathesis", "epenthesis", "assimilation", "palatalisation", "tonogenesis")
SOUNDCHANGEKIND_RENAMED = ()
SPECIESCLASS_OLD = ("animal", "plant", "fungus", "vermin")
SPECIESCLASS_NEW = ("animal", "plant", "fungus", "vermin", "microbe", "mineral", "gaseous", "energy", "made", "colonial", "hybrid")
SPECIESCLASS_RENAMED = ()
EVOLVEDTRAIT_OLD = ("size", "speed", "armour", "venom", "camouflage", "cold_tolerance", "intelligence", "fecundity", "wariness")
EVOLVEDTRAIT_NEW = (
    "size",
    "speed",
    "armour",
    "venom",
    "camouflage",
    "cold_tolerance",
    "intelligence",
    "fecundity",
    "wariness",
    "heat_tolerance",
    "drought_tolerance",
    "keen_senses",
)
EVOLVEDTRAIT_RENAMED = ()
STORYTELLERPROFILE_OLD = ("steady", "rising", "cyclic", "chaotic")
STORYTELLERPROFILE_NEW = ("steady", "rising", "cyclic", "chaotic", "slow_burn", "episodic")
STORYTELLERPROFILE_RENAMED = ()
TAXKIND_OLD = ("land", "poll", "trade", "consumption", "tithe")
TAXKIND_NEW = (
    "land",
    "poll",
    "trade",
    "consumption",
    "tithe",
    "income",
    "property",
    "inheritance",
    "wealth",
    "company",
    "labour_levy",
    "in_kind",
    "licence",
    "seigniorage",
    "pollution",
    "excise",
)
TAXKIND_RENAMED = ()
TRANSPORTKIND_OLD = ("pack_animals", "wagons", "river_boats", "ships")
TRANSPORTKIND_NEW = (
    "porters",
    "pack_animals",
    "animal_carts",
    "rail",
    "road_motor",
    "river_and_canal",
    "sea",
    "air",
    "pipeline",
    "orbital_lift",
    "space",
    "teleport",
    "living",
    "rite",
    "network",
)
TRANSPORTKIND_RENAMED = (("wagons", "animal_carts"), ("river_boats", "river_and_canal"), ("ships", "sea"))
SUBJECTKIND_OLD = ("vassal", "tributary", "march", "personal_union", "client", "colony", "protectorate")
SUBJECTKIND_NEW = ("vassal", "tributary", "march", "personal_union", "client", "colony", "protectorate", "enclave", "mandate", "associated_state")
SUBJECTKIND_RENAMED = ()
QUESTAIM_OLD = ("dead_star", "sealed_gate", "archive", "expel_outer", "hunt", "thread", "relic", "knowledge", "vengeance")
QUESTAIM_NEW = (
    "find",
    "restore",
    "destroy",
    "free",
    "bind",
    "reach",
    "learn",
    "return",
    "protect",
    "avenge",
    "hunt",
    "deliver",
    "reconcile",
    "prove",
    "resolve",
)
QUESTAIM_RENAMED = (
    ("dead_star", "restore"),
    ("sealed_gate", "free"),
    ("archive", "find"),
    ("expel_outer", "destroy"),
    ("thread", "resolve"),
    ("relic", "find"),
    ("knowledge", "learn"),
    ("vengeance", "avenge"),
)
NOTABLEYEARKIND_OLD = ("hunger", "plenty", "weather", "pestilence")
NOTABLEYEARKIND_NEW = ("hunger", "plenty", "weather", "pestilence", "disaster", "discovery", "contact", "omen")
NOTABLEYEARKIND_RENAMED = ()
PERENNIALKIND_OLD = ("orchard", "vineyard", "grove", "timber")
PERENNIALKIND_NEW = ("orchard", "vineyard", "grove", "timber", "plantation", "forest_garden")
PERENNIALKIND_RENAMED = ()
AIDKIND_OLD = ("goods", "healers", "labour")
AIDKIND_NEW = ("goods", "healers", "labour", "money", "credit", "food", "shelter", "medicine", "soldiers", "knowledge")
AIDKIND_RENAMED = ()
RIFTCAUSE_OLD = ("rite_backlash", "leak_peak", "convergence", "god", "being", "phenomenon", "creator")
RIFTCAUSE_NEW = ("rite_backlash", "leak_peak", "convergence", "god", "being", "phenomenon", "creator", "made_realm_gate")
RIFTCAUSE_RENAMED = ()
ROOMCONTENTKIND_OLD = ("item", "spirit", "beast", "trap")
ROOMCONTENTKIND_NEW = ("item", "spirit", "beast", "trap", "mind", "relic", "realm_gate")
ROOMCONTENTKIND_RENAMED = ()
BINDINGKIND_OLD = ("none", "place", "item", "structure", "beast", "person")
BINDINGKIND_NEW = ("none", "place", "item", "structure", "beast", "person", "realm", "network", "line")
BINDINGKIND_RENAMED = ()
CARRIERKIND_OLD = ("wagons", "pack_animals", "porters", "barges", "ships", "sky_barges")
CARRIERKIND_NEW = (
    "porters",
    "pack_animals",
    "animal_carts",
    "rail",
    "road_motor",
    "river_and_canal",
    "sea",
    "air",
    "pipeline",
    "orbital_lift",
    "space",
    "teleport",
    "living",
    "rite",
    "network",
)
CARRIERKIND_RENAMED = (("wagons", "animal_carts"), ("barges", "river_and_canal"), ("ships", "sea"), ("sky_barges", "air"))
VEHICLEKIND_OLD = ("gate", "ship", "mount", "bridge")
VEHICLEKIND_NEW = ("gate", "ship", "mount", "bridge", "rail", "road_vehicle", "aircraft", "teleport", "living", "rift", "on_foot")
VEHICLEKIND_RENAMED = ()
URBANSERVICE_OLD = ("water", "faith", "watch", "healing", "market", "school", "bath", "fire")
URBANSERVICE_NEW = (
    "water",
    "faith",
    "watch",
    "healing",
    "market",
    "school",
    "bath",
    "fire",
    "sanitation",
    "transport",
    "communication",
    "power",
    "courts",
    "welfare",
    "granary",
    "parks",
    "library",
    "burial",
    "depot",
    "administration",
    "entertainment",
)
URBANSERVICE_RENAMED = ()
SPYOWNERKIND_OLD = ("polity", "faction", "cult", "community")
SPYOWNERKIND_NEW = ("polity", "faction", "cult", "community", "company", "made_mind")
SPYOWNERKIND_RENAMED = ()
BUILDERKIND_OLD = ("community", "polity", "faction", "cult", "patron", "god")
BUILDERKIND_NEW = ("community", "polity", "faction", "cult", "patron", "god", "company", "made_mind")
BUILDERKIND_RENAMED = ()
THOUGHTKIND_OLD = (
    "married",
    "child_born",
    "saw_kin_die",
    "lost_spouse",
    "lost_child",
    "betrayed",
    "was_insulted",
    "was_gifted",
    "was_saved",
    "was_cheated",
    "won_battle",
    "defeated",
    "won_duel",
    "lost_duel",
    "was_wounded",
    "was_maimed",
    "lost_limb_but_lived",
    "was_healed",
    "fell_ill",
    "witnessed_atrocity",
    "was_captured",
    "was_freed",
    "killed_foe",
    "rose_in_rank",
    "fell_in_rank",
    "gained_renown",
    "was_shamed",
    "was_punished",
    "was_conquered",
    "prayed_answered",
    "prayer_ignored",
    "saw_miracle",
    "felt_god_near",
    "alien_dominion",
    "lost_faith",
    "found_faith",
    "saw_desecration",
    "touched_by_a_god",
    "admired_great_work",
    "heard_great_music",
    "attended_feast",
    "made_masterwork",
    "learned_something",
    "taught_apprentice",
    "took_idea_to_heart",
    "ate_fine_food",
    "went_hungry",
    "went_thirsty",
    "drank_well",
    "slept_well",
    "exhausted",
    "lived_in_comfort",
    "lived_in_squalor",
    "felt_hale",
    "felt_unwell",
    "felt_safe",
    "felt_unsafe",
    "among_kin",
    "missed_kin",
    "among_friends",
    "felt_lonely",
    "lost_pet",
    "comforted_by_pet",
    "loved",
    "longed_for_love",
    "had_peace_and_quiet",
    "crowded",
    "respected",
    "overlooked",
    "belonged",
    "adrift",
    "felt_purpose",
    "lacked_purpose",
    "prayed_in_peace",
    "faith_unmet",
    "learned_nothing",
    "made_something",
    "nothing_made",
    "saw_beauty",
    "surrounded_by_ugliness",
    "walked_in_nature",
    "cut_off_from_nature",
    "had_adventure",
    "restless",
    "tested_in_combat",
    "blade_rusting",
    "prospered",
    "wanted_for_money",
    "enjoyed_leisure",
    "bored",
    "lived_in_order",
    "lived_in_disorder",
    "relived_memory",
    "mourned",
    "made_peace_with_loss",
    "had_nightmare",
    "had_good_dream",
    "dreamed_of_longing",
    "received_visitation",
    "sent_by_the_creator",
    "liked_surroundings",
    "disliked_surroundings",
    "proud_of_home",
    "ashamed_of_home",
    "enjoyed_favourite",
    "endured_a_dislike",
    "acted_on_conscience",
    "acted_against_conscience",
    "kin_shamed",
    "shame_restored",
    "dream_progress",
    "dream_fulfilled",
    "dream_shattered",
    "want_fulfilled",
    "fear_near",
    "inspired",
    "inspiration_lost",
    "disillusioned",
    "made_a_friend",
    "lost_a_friend",
    "laughed_together",
    "was_comforted",
    "was_flattered",
    "quarrelled",
    "reconciled",
    "fell_in_love",
    "heartbroken",
    "jealous",
    "brawled",
    "was_threatened",
    "confided_in",
    "won_contest",
    "lost_contest",
    "was_persuaded",
    "rose_in_standing",
    "lost_standing",
    "passion_stirred",
    "passion_broke",
)
THOUGHTKIND_NEW = (
    "married",
    "child_born",
    "saw_kin_die",
    "lost_spouse",
    "lost_child",
    "betrayed",
    "was_insulted",
    "was_gifted",
    "was_saved",
    "was_cheated",
    "won_battle",
    "defeated",
    "won_duel",
    "lost_duel",
    "was_wounded",
    "was_maimed",
    "lost_limb_but_lived",
    "was_healed",
    "fell_ill",
    "witnessed_atrocity",
    "was_captured",
    "was_freed",
    "killed_foe",
    "rose_in_rank",
    "fell_in_rank",
    "gained_renown",
    "was_shamed",
    "was_punished",
    "was_conquered",
    "prayed_answered",
    "prayer_ignored",
    "saw_miracle",
    "felt_god_near",
    "alien_dominion",
    "lost_faith",
    "found_faith",
    "saw_desecration",
    "touched_by_a_god",
    "admired_great_work",
    "heard_great_music",
    "attended_feast",
    "made_masterwork",
    "learned_something",
    "taught_apprentice",
    "took_idea_to_heart",
    "ate_fine_food",
    "went_hungry",
    "went_thirsty",
    "drank_well",
    "slept_well",
    "exhausted",
    "lived_in_comfort",
    "lived_in_squalor",
    "felt_hale",
    "felt_unwell",
    "felt_safe",
    "felt_unsafe",
    "among_kin",
    "missed_kin",
    "among_friends",
    "felt_lonely",
    "lost_pet",
    "comforted_by_pet",
    "loved",
    "longed_for_love",
    "had_peace_and_quiet",
    "crowded",
    "respected",
    "overlooked",
    "belonged",
    "adrift",
    "felt_purpose",
    "lacked_purpose",
    "prayed_in_peace",
    "faith_unmet",
    "learned_nothing",
    "felt_free",
    "felt_constrained",
    "found_answers",
    "kept_in_ignorance",
    "felt_stimulated",
    "felt_dulled",
    "felt_lasting",
    "feared_ending",
    "well_kept",
    "neglected",
    "made_something",
    "nothing_made",
    "saw_beauty",
    "surrounded_by_ugliness",
    "walked_in_nature",
    "cut_off_from_nature",
    "had_adventure",
    "restless",
    "tested_in_combat",
    "blade_rusting",
    "prospered",
    "wanted_for_money",
    "enjoyed_leisure",
    "bored",
    "lived_in_order",
    "lived_in_disorder",
    "relived_memory",
    "mourned",
    "made_peace_with_loss",
    "had_nightmare",
    "had_good_dream",
    "dreamed_of_longing",
    "received_visitation",
    "sent_by_the_creator",
    "liked_surroundings",
    "disliked_surroundings",
    "proud_of_home",
    "ashamed_of_home",
    "enjoyed_favourite",
    "endured_a_dislike",
    "acted_on_conscience",
    "acted_against_conscience",
    "kin_shamed",
    "shame_restored",
    "dream_progress",
    "dream_fulfilled",
    "dream_shattered",
    "want_fulfilled",
    "fear_near",
    "inspired",
    "inspiration_lost",
    "disillusioned",
    "made_a_friend",
    "lost_a_friend",
    "laughed_together",
    "was_comforted",
    "was_flattered",
    "quarrelled",
    "reconciled",
    "fell_in_love",
    "heartbroken",
    "jealous",
    "brawled",
    "was_threatened",
    "confided_in",
    "won_contest",
    "lost_contest",
    "was_persuaded",
    "rose_in_standing",
    "lost_standing",
    "passion_stirred",
    "passion_broke",
)
THOUGHTKIND_RENAMED = ()
RETYPED = (
    ("beliefs", "source", "source", BELIEFSOURCE_OLD, BELIEFSOURCE_NEW, BELIEFSOURCE_RENAMED, False),
    ("bias_weights", "last_decision", "last_decision", BIASEDDECISION_OLD, BIASEDDECISION_NEW, BIASEDDECISION_RENAMED, True),
    ("community_methods", "method", "method", METHODKIND_OLD, METHODKIND_NEW, METHODKIND_RENAMED, False),
    ("production_runs", "method", "method", METHODKIND_OLD, METHODKIND_NEW, METHODKIND_RENAMED, True),
    ("creature_anatomy", "skin", "skin", TISSUEMATERIAL_OLD, TISSUEMATERIAL_NEW, TISSUEMATERIAL_RENAMED, False),
    ("creature_anatomy", "bone", "bone", TISSUEMATERIAL_OLD, TISSUEMATERIAL_NEW, TISSUEMATERIAL_RENAMED, False),
    ("divine_wounds", "kind", "kind", DIVINEWOUNDKIND_OLD, DIVINEWOUNDKIND_NEW, DIVINEWOUNDKIND_RENAMED, False),
    ("epoch_steps", "step", "step", EPOCHSTEPKIND_OLD, EPOCHSTEPKIND_NEW, EPOCHSTEPKIND_RENAMED, False),
    ("group_ranks", "group_kind", "group_kind", GROUPKIND_OLD, GROUPKIND_NEW, GROUPKIND_RENAMED, False),
    ("incubating_ideas", "source", "source", IDEASOURCE_OLD, IDEASOURCE_NEW, IDEASOURCE_RENAMED, False),
    ("inspirations", "kind", "kind", INSPIRATIONKIND_OLD, INSPIRATIONKIND_NEW, INSPIRATIONKIND_RENAMED, False),
    ("ledger_entries", "action_kind", "action_kind", ACTIONKIND_OLD, ACTIONKIND_NEW, ACTIONKIND_RENAMED, False),
    ("action_records", "kind", "kind", ACTIONKIND_OLD, ACTIONKIND_NEW, ACTIONKIND_RENAMED, False),
    ("long_plans", "kind", "kind", LONGPLANKIND_OLD, LONGPLANKIND_NEW, LONGPLANKIND_RENAMED, False),
    ("lore_trades", "kind", "kind", LOREKIND_OLD, LOREKIND_NEW, LOREKIND_RENAMED, False),
    ("messages", "medium", "medium", MEDIUM_OLD, MEDIUM_NEW, MEDIUM_RENAMED, True),
    ("mind_facets", "facet", "facet", FACET_OLD, FACET_NEW, FACET_RENAMED, False),
    ("mind_profiles", "upkeep_energy", "upkeep_energy", ENERGYKIND_OLD, ENERGYKIND_NEW, ENERGYKIND_RENAMED, True),
    ("modifiers", "source_kind", "source_kind", MODIFIERSOURCE_OLD, MODIFIERSOURCE_NEW, MODIFIERSOURCE_RENAMED, False),
    ("mortal_perks", "perk", "perk", PERKKIND_OLD, PERKKIND_NEW, PERKKIND_RENAMED, False),
    ("needs", "need", "need", NEEDKIND_OLD, NEEDKIND_NEW, NEEDKIND_RENAMED, False),
    ("passions", "kind", "kind", PASSIONKIND_OLD, PASSIONKIND_NEW, PASSIONKIND_RENAMED, False),
    ("preferences", "kind", "kind", PREFERENCEKIND_OLD, PREFERENCEKIND_NEW, PREFERENCEKIND_RENAMED, False),
    ("setups", "kind", "kind", SETUPKIND_OLD, SETUPKIND_NEW, SETUPKIND_RENAMED, False),
    ("trade_policies", "kind", "kind", TRADEPOLICYKIND_OLD, TRADEPOLICYKIND_NEW, TRADEPOLICYKIND_RENAMED, False),
    ("turn_counters", "counter", "counter", TURNCOUNTER_OLD, TURNCOUNTER_NEW, TURNCOUNTER_RENAMED, False),
    ("powers", "state", "state", POWERSTATE_OLD, POWERSTATE_NEW, POWERSTATE_RENAMED, False),
    ("worlds", "climate_era", "climate_era", CLIMATEERA_OLD, CLIMATEERA_NEW, CLIMATEERA_RENAMED, True),
    ("climate_orders", "era", "era", CLIMATEERA_OLD, CLIMATEERA_NEW, CLIMATEERA_RENAMED, False),
    ("council_rulings", "motion", "motion", COUNCILMOTION_OLD, COUNCILMOTION_NEW, COUNCILMOTION_RENAMED, False),
    ("entities", "engine_kind", "engine_kind", ENGINEKIND_OLD, ENGINEKIND_NEW, ENGINEKIND_RENAMED, True),
    ("foreign_god_powers", "effect", "effect", FOREIGNGODPOWEREFFECT_OLD, FOREIGNGODPOWEREFFECT_NEW, FOREIGNGODPOWEREFFECT_RENAMED, False),
    ("son_powers", "effect", "effect", POWEREFFECT_OLD, POWEREFFECT_NEW, POWEREFFECT_RENAMED, False),
    ("traits", "trait", "trait", TRAITKIND_OLD, TRAITKIND_NEW, TRAITKIND_RENAMED, False),
    ("accounts", "kind", "kind", ACCOUNTKIND_OLD, ACCOUNTKIND_NEW, ACCOUNTKIND_RENAMED, False),
    ("accounts", "medium", "medium", ACCOUNTMEDIUM_OLD, ACCOUNTMEDIUM_NEW, ACCOUNTMEDIUM_RENAMED, False),
    ("afterlife_strata", "kind", "kind", STRATUMKIND_OLD, STRATUMKIND_NEW, STRATUMKIND_RENAMED, False),
    ("arms", "holder_kind", "holder_kind", HERALDRYHOLDERKIND_OLD, HERALDRYHOLDERKIND_NEW, HERALDRYHOLDERKIND_RENAMED, False),
    ("blueprints", "kind", "kind", BLUEPRINTKIND_OLD, BLUEPRINTKIND_NEW, BLUEPRINTKIND_RENAMED, False),
    ("challenges", "kind", "kind", CHALLENGEKIND_OLD, CHALLENGEKIND_NEW, CHALLENGEKIND_RENAMED, False),
    ("commander_traits", "trait", "trait", COMMANDERTRAIT_OLD, COMMANDERTRAIT_NEW, COMMANDERTRAIT_RENAMED, False),
    ("commons", "kind", "kind", COMMONSKIND_OLD, COMMONSKIND_NEW, COMMONSKIND_RENAMED, False),
    ("crime_cases", "crime", "crime", CRIMEKIND_OLD, CRIMEKIND_NEW, CRIMEKIND_RENAMED, False),
    ("precedents", "crime", "crime", CRIMEKIND_OLD, CRIMEKIND_NEW, CRIMEKIND_RENAMED, False),
    ("sentences", "crime", "crime", CRIMEKIND_OLD, CRIMEKIND_NEW, CRIMEKIND_RENAMED, False),
    ("crime_cases", "trial", "trial", TRIALKIND_OLD, TRIALKIND_NEW, TRIALKIND_RENAMED, True),
    ("cult_doctrines", "fanaticism", "fanaticism", FANATICISMKIND_OLD, FANATICISMKIND_NEW, FANATICISMKIND_RENAMED, True),
    ("cult_holdings", "kind", "kind", HOLDINGKIND_OLD, HOLDINGKIND_NEW, HOLDINGKIND_RENAMED, False),
    ("culture_honour", "model", "model", HONOURMODEL_OLD, HONOURMODEL_NEW, HONOURMODEL_RENAMED, False),
    ("dating_systems", "kind", "kind", DATINGSYSTEMKIND_OLD, DATINGSYSTEMKIND_NEW, DATINGSYSTEMKIND_RENAMED, False),
    ("designs", "kind", "kind", DESIGNKIND_OLD, DESIGNKIND_NEW, DESIGNKIND_RENAMED, False),
    ("doctrine_afterlives", "model", "model", AFTERLIFEMODEL_OLD, AFTERLIFEMODEL_NEW, AFTERLIFEMODEL_RENAMED, False),
    ("era_deeds", "deed", "deed", ERADEED_OLD, ERADEED_NEW, ERADEED_RENAMED, False),
    ("event_casualties", "phase", "phase", EVENTPHASE_OLD, EVENTPHASE_NEW, EVENTPHASE_RENAMED, False),
    ("event_profiles", "phase", "phase", EVENTPHASE_OLD, EVENTPHASE_NEW, EVENTPHASE_RENAMED, False),
    ("faction_profiles", "kind", "kind", FACTIONKIND_OLD, FACTIONKIND_NEW, FACTIONKIND_RENAMED, False),
    ("feuds", "party", "party", FEUDPARTY_OLD, FEUDPARTY_NEW, FEUDPARTY_RENAMED, False),
    ("feuds", "status", "status", FEUDSTATUS_OLD, FEUDSTATUS_NEW, FEUDSTATUS_RENAMED, False),
    ("gatherings", "kind", "kind", GATHERINGKIND_OLD, GATHERINGKIND_NEW, GATHERINGKIND_RENAMED, False),
    ("impurity_sources", "source", "source", IMPURITYSOURCE_OLD, IMPURITYSOURCE_NEW, IMPURITYSOURCE_RENAMED, False),
    ("purity", "source", "source", IMPURITYSOURCE_OLD, IMPURITYSOURCE_NEW, IMPURITYSOURCE_RENAMED, True),
    ("item_profiles", "curse", "curse", CURSEKIND_OLD, CURSEKIND_NEW, CURSEKIND_RENAMED, False),
    ("legacy_traits", "kind", "kind", LEGACYKIND_OLD, LEGACYKIND_NEW, LEGACYKIND_RENAMED, False),
    ("magic_sites", "kind", "kind", MAGICSITEKIND_OLD, MAGICSITEKIND_NEW, MAGICSITEKIND_RENAMED, False),
    ("marriages", "cause_end", "cause_end", MARRIAGEEND_OLD, MARRIAGEEND_NEW, MARRIAGEEND_RENAMED, True),
    ("mishaps", "kind", "kind", MISHAPKIND_OLD, MISHAPKIND_NEW, MISHAPKIND_RENAMED, False),
    ("mishaps", "attribution", "attribution", MISHAPATTRIBUTION_OLD, MISHAPATTRIBUTION_NEW, MISHAPATTRIBUTION_RENAMED, True),
    ("norm_changes", "situation", "situation", NORMSITUATION_OLD, NORMSITUATION_NEW, NORMSITUATION_RENAMED, False),
    ("social_norms", "situation", "situation", NORMSITUATION_OLD, NORMSITUATION_NEW, NORMSITUATION_RENAMED, False),
    ("norm_changes", "behaviour", "behaviour", NORMBEHAVIOUR_OLD, NORMBEHAVIOUR_NEW, NORMBEHAVIOUR_RENAMED, False),
    ("social_norms", "behaviour", "behaviour", NORMBEHAVIOUR_OLD, NORMBEHAVIOUR_NEW, NORMBEHAVIOUR_RENAMED, False),
    ("oaths", "kind", "kind", OATHKIND_OLD, OATHKIND_NEW, OATHKIND_RENAMED, False),
    ("place_secrets", "kind", "kind", SECRETKIND_OLD, SECRETKIND_NEW, SECRETKIND_RENAMED, False),
    ("polity_eras", "age", "age", AGEKIND_OLD, AGEKIND_NEW, AGEKIND_RENAMED, False),
    ("preparedness", "kind", "kind", PREPAREDNESSKIND_OLD, PREPAREDNESSKIND_NEW, PREPAREDNESSKIND_RENAMED, False),
    ("pressures", "pressure", "pressure", PRESSUREKIND_OLD, PRESSUREKIND_NEW, PRESSUREKIND_RENAMED, False),
    ("rackets", "racket", "racket", RACKETKIND_OLD, RACKETKIND_NEW, RACKETKIND_RENAMED, False),
    ("registries", "kind", "kind", REGISTRYKIND_OLD, REGISTRYKIND_NEW, REGISTRYKIND_RENAMED, False),
    ("rite_effects", "summon_form", "summon_form", SUMMONFORM_OLD, SUMMONFORM_NEW, SUMMONFORM_RENAMED, True),
    ("routes", "closure", "closure", ROUTECLOSURE_OLD, ROUTECLOSURE_NEW, ROUTECLOSURE_RENAMED, True),
    ("servitors", "role", "role", SERVITORROLE_OLD, SERVITORROLE_NEW, SERVITORROLE_RENAMED, False),
    ("settlement_history", "size_tier", "size_tier", SIZETIER_OLD, SIZETIER_NEW, SIZETIER_RENAMED, False),
    ("settlement_profiles", "size_tier", "size_tier", SIZETIER_OLD, SIZETIER_NEW, SIZETIER_RENAMED, False),
    ("structure_designs", "min_tier", "min_tier", SIZETIER_OLD, SIZETIER_NEW, SIZETIER_RENAMED, True),
    ("ship_states", "shot", "shot", SHOTKIND_OLD, SHOTKIND_NEW, SHOTKIND_RENAMED, False),
    ("signal_links", "kind", "kind", SIGNALKIND_OLD, SIGNALKIND_NEW, SIGNALKIND_RENAMED, False),
    ("sound_changes", "kind", "kind", SOUNDCHANGEKIND_OLD, SOUNDCHANGEKIND_NEW, SOUNDCHANGEKIND_RENAMED, False),
    ("species_profiles", "species_class", "species_class", SPECIESCLASS_OLD, SPECIESCLASS_NEW, SPECIESCLASS_RENAMED, False),
    ("species_traits", "trait", "trait", EVOLVEDTRAIT_OLD, EVOLVEDTRAIT_NEW, EVOLVEDTRAIT_RENAMED, False),
    ("storytellers", "profile", "profile", STORYTELLERPROFILE_OLD, STORYTELLERPROFILE_NEW, STORYTELLERPROFILE_RENAMED, False),
    ("tax_policies", "kind", "kind", TAXKIND_OLD, TAXKIND_NEW, TAXKIND_RENAMED, False),
    ("transport_fleets", "kind", "kind", TRANSPORTKIND_OLD, TRANSPORTKIND_NEW, TRANSPORTKIND_RENAMED, False),
    ("vassalages", "kind", "kind", SUBJECTKIND_OLD, SUBJECTKIND_NEW, SUBJECTKIND_RENAMED, False),
    ("legendary_quests", "kind", "kind", QUESTAIM_OLD, QUESTAIM_NEW, QUESTAIM_RENAMED, False),
    ("hero_quests", "kind", "kind", QUESTAIM_OLD, QUESTAIM_NEW, QUESTAIM_RENAMED, False),
    ("notable_years", "kind", "kind", NOTABLEYEARKIND_OLD, NOTABLEYEARKIND_NEW, NOTABLEYEARKIND_RENAMED, False),
    ("perennials", "kind", "kind", PERENNIALKIND_OLD, PERENNIALKIND_NEW, PERENNIALKIND_RENAMED, False),
    ("relief_aid", "kind", "kind", AIDKIND_OLD, AIDKIND_NEW, AIDKIND_RENAMED, False),
    ("rifts", "cause", "cause", RIFTCAUSE_OLD, RIFTCAUSE_NEW, RIFTCAUSE_RENAMED, False),
    ("room_contents", "kind", "kind", ROOMCONTENTKIND_OLD, ROOMCONTENTKIND_NEW, ROOMCONTENTKIND_RENAMED, False),
    ("spirit_profiles", "binding", "binding", BINDINGKIND_OLD, BINDINGKIND_NEW, BINDINGKIND_RENAMED, False),
    ("transport_assets", "kind", "kind", CARRIERKIND_OLD, CARRIERKIND_NEW, CARRIERKIND_RENAMED, False),
    ("vessel_profiles", "kind", "kind", VEHICLEKIND_OLD, VEHICLEKIND_NEW, VEHICLEKIND_RENAMED, False),
    ("district_services", "service", "service", URBANSERVICE_OLD, URBANSERVICE_NEW, URBANSERVICE_RENAMED, False),
    ("spy_networks", "owner_kind", "owner_kind", SPYOWNERKIND_OLD, SPYOWNERKIND_NEW, SPYOWNERKIND_RENAMED, False),
    ("structure_profiles", "builder_kind", "builder_kind", BUILDERKIND_OLD, BUILDERKIND_NEW, BUILDERKIND_RENAMED, True),
    ("thoughts", "kind", "kind", THOUGHTKIND_OLD, THOUGHTKIND_NEW, THOUGHTKIND_RENAMED, False),
)

SERVITOR_RANKS = ("herald", "guardian", "angel", "fury", "psychopomp", "choir")
LEGACY_ROLES = (("angel", "agent"), ("fury", "avenger"), ("psychopomp", "guide_of_souls"), ("choir", "worshipper"), ("guardian", "guard"))


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


def map_ranks() -> None:
    for rank, role in LEGACY_ROLES:
        op.execute(sa.text("UPDATE servitors SET role = :role WHERE role = 'messenger' AND rank = :rank").bindparams(role=role, rank=rank))


F3_UPDATES = (
    ("legendary_quests", "target_kind", "route", "kind", "free"),
    ("legendary_quests", "target_kind", "knowledge", "kind", "find"),
    ("legendary_quests", "target_kind", "outer_being", "kind", "destroy"),
    ("hero_quests", "target_kind", "species", "kind", "hunt"),
    ("hero_quests", "target_kind", "incident_arc", "kind", "resolve"),
    ("hero_quests", "target_kind", "item", "kind", "find"),
    ("hero_quests", "target_kind", "knowledge", "kind", "learn"),
    ("afterlife_strata", "valence", "reward", "kind", "reward"),
    ("afterlife_strata", "permanence", "eternal", "kind", "reward"),
    ("afterlife_strata", "admission", "by_deeds", "kind", "reward"),
    ("afterlife_strata", "activity", "rest", "kind", "reward"),
    ("afterlife_strata", "contact", "by_rite", "kind", "reward"),
    ("afterlife_strata", "valence", "neutral", "kind", "common"),
    ("afterlife_strata", "permanence", "eternal", "kind", "common"),
    ("afterlife_strata", "admission", "all", "kind", "common"),
    ("afterlife_strata", "activity", "rest", "kind", "common"),
    ("afterlife_strata", "contact", "open", "kind", "common"),
    ("afterlife_strata", "valence", "punishment", "kind", "punishment"),
    ("afterlife_strata", "permanence", "until_judgement", "kind", "punishment"),
    ("afterlife_strata", "admission", "by_deeds", "kind", "punishment"),
    ("afterlife_strata", "activity", "struggle", "kind", "punishment"),
    ("afterlife_strata", "contact", "closed", "kind", "punishment"),
    ("afterlife_strata", "valence", "neutral", "kind", "dissolution"),
    ("afterlife_strata", "permanence", "fading", "kind", "dissolution"),
    ("afterlife_strata", "admission", "all", "kind", "dissolution"),
    ("afterlife_strata", "activity", "dissolution", "kind", "dissolution"),
    ("afterlife_strata", "contact", "closed", "kind", "dissolution"),
    ("afterlife_strata", "valence", "reward", "kind", "by_manner_of_death"),
    ("afterlife_strata", "permanence", "eternal", "kind", "by_manner_of_death"),
    ("afterlife_strata", "admission", "by_manner_of_death", "kind", "by_manner_of_death"),
    ("afterlife_strata", "activity", "struggle", "kind", "by_manner_of_death"),
    ("afterlife_strata", "contact", "by_rite", "kind", "by_manner_of_death"),
    ("afterlife_strata", "valence", "reward", "kind", "by_line"),
    ("afterlife_strata", "permanence", "eternal", "kind", "by_line"),
    ("afterlife_strata", "admission", "by_line", "kind", "by_line"),
    ("afterlife_strata", "activity", "reunion", "kind", "by_line"),
    ("afterlife_strata", "contact", "open", "kind", "by_line"),
)
F3_ATTACKS = (
    ("breath", "fire", "breath", "heat", "near", 0),
    ("breath", "frost", "breath", "cold", "near", 0),
    ("breath", "venom_gas", "breath", "venom", "near", 0),
    ("breath", "web", "spray", "entangle", "near", 0),
    ("breath", "steam", "breath", "heat", "near", 0),
    ("gaze", "terror", "gaze", "fear", "sight", 0),
    ("gaze", "petrify", "gaze", "stillness", "sight", 1),
    ("gaze", "sleep", "gaze", "sleep", "sight", 0),
    ("gaze", "madness", "gaze", "confusion", "sight", 0),
)


def map_attacks() -> None:
    for column, legacy, delivery, effect, reach, permanent in F3_ATTACKS:
        op.execute(
            sa.text(
                "INSERT INTO creature_attacks (node_id, delivery, effect, range, recharge, permanent, locked) "
                f"SELECT node_id, :delivery, :effect, :reach, 0, :permanent, '[]' FROM creature_anatomy WHERE {column} = :legacy"
            ).bindparams(delivery=delivery, effect=effect, reach=reach, permanent=permanent, legacy=legacy)
        )


def map_typed_models() -> None:
    for table, column, value, key, legacy in F3_UPDATES:
        op.execute(sa.text(f"UPDATE {table} SET {column} = :value WHERE {key} = :legacy").bindparams(value=value, legacy=legacy))


def map_elements() -> None:
    op.execute(
        "INSERT INTO dimension_aspects (dimension_id, form, element, strength, locked) "
        "SELECT id, NULL, element, 50, '[]' FROM dimensions WHERE element IS NOT NULL"
    )


def upgrade() -> None:
    retype(True)
    op.create_table(
        "council_procedures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quorum_pct", sa.Integer(), nullable=False),
        sa.Column(
            "voting_rule",
            sa.Enum(
                "unanimity", "majority", "weighted_by_standing", "weighted_by_rank", name="voting_rule", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("creator_veto", sa.Boolean(), nullable=False),
        sa.Column("term_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_council_procedures")),
    )
    op.create_table(
        "creator_chosen",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "favour",
            sa.Enum("renown", "protection", "long_life", "gift", "foresight", name="favour", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_creator_chosen_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_creator_chosen")),
    )
    op.create_table(
        "creature_attacks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column(
            "delivery",
            sa.Enum(
                "breath",
                "spit",
                "spray",
                "emanation",
                "gaze",
                "voice",
                "touch",
                "spores",
                "bite",
                "sting",
                name="delivery",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "effect",
            sa.Enum(
                "heat",
                "cold",
                "corrosion",
                "shock",
                "venom",
                "force",
                "entangle",
                "fear",
                "stillness",
                "sleep",
                "confusion",
                "charm",
                "drain",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("range", sa.Enum("touch", "near", "far", "sight", name="range", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("recharge", sa.Integer(), nullable=False),
        sa.Column("permanent", sa.Boolean(), nullable=False),
        sa.Column("last_used_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("recharge >= 0", name=op.f("ck_creature_attacks_recharge_min")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_creature_attacks_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creature_attacks")),
    )
    with op.batch_alter_table("creature_attacks", schema=None) as batch_op:
        batch_op.create_index("ix_creature_attacks_node", ["node_id"], unique=False)

    op.create_table(
        "divine_council_seats",
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "seat", sa.Enum("by_right", "invited", "by_pact", "recognised", name="seat", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("excluded_until", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_divine_council_seats_god_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("god_node_id", name=op.f("pk_divine_council_seats")),
    )
    op.create_table(
        "divine_powers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "verb",
            sa.Enum(
                "grant",
                "bless",
                "curse",
                "create",
                "destroy",
                "shape",
                "reveal",
                "conceal",
                "summon",
                "bind",
                "free",
                "heal",
                "harm",
                "raise",
                "inspire",
                "terrify",
                "protect",
                "guide",
                "judge",
                "transform",
                "foresee",
                "hasten",
                "slow",
                "multiply",
                "still",
                "wake",
                "remember",
                "erase",
                name="verb",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "object",
            sa.Enum(
                "stat",
                "need",
                "skill",
                "value",
                "trait",
                "commodity",
                "species",
                "line",
                "structure",
                "weather",
                "source",
                "power",
                "mind",
                "truth",
                "law",
                "memory",
                "incident",
                name="object",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(length=200), nullable=True),
        sa.Column(
            "scope",
            sa.Enum("person", "community", "region", "world", "system", "dimension", name="scope", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("mode", sa.Enum("passive", "triggered", "active", name="mode", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column(
            "cost",
            sa.Enum("essence", "attention", "standing", "domain", "sacrifice", name="cost", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("cost_amount", sa.Integer(), nullable=False),
        sa.Column("cooldown", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("domains", sa.JSON(), nullable=False),
        sa.Column(
            "son_preset",
            sa.Enum(
                "cheap_creation",
                "duel_master",
                "essence_spring",
                "worshipped",
                "tireless",
                "untouchable",
                "dream_sending",
                "war_leader",
                "harvester",
                "seer",
                "reviving",
                "bounty_giver",
                "curser",
                name="son_preset",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "foreign_preset",
            sa.Enum(
                "shield",
                "caller",
                "thief",
                "destroyer",
                "fertile",
                "reviving",
                "deathless",
                "persuasion",
                name="foreign_preset",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("last_used_epoch", sa.Integer(), nullable=True),
        sa.Column("granted_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("cooldown >= 0", name=op.f("ck_divine_powers_cooldown_min")),
        sa.CheckConstraint("cost_amount >= 0", name=op.f("ck_divine_powers_cost_amount_min")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_divine_powers_strength_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_divine_powers_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_divine_powers")),
    )
    with op.batch_alter_table("divine_powers", schema=None) as batch_op:
        batch_op.create_index("ix_divine_powers_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "fortune_profiles",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("fortune", sa.Integer(), nullable=False),
        sa.Column("streak", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("fortune BETWEEN -100 AND 100", name=op.f("ck_fortune_profiles_fortune_range")),
        sa.CheckConstraint("streak BETWEEN -100 AND 100", name=op.f("ck_fortune_profiles_streak_range")),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_fortune_profiles_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_fortune_profiles")),
    )
    op.create_table(
        "fortune_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "blessing",
                "curse",
                "charm",
                "divine_favour",
                "divine_disfavour",
                "fate_power",
                "natural_law",
                "oath_kept",
                "oath_broken",
                "place",
                "day",
                "price_paid",
                "care",
                name="kind",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("giver_node_id", sa.Integer(), nullable=True),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("strength BETWEEN -100 AND 100", name=op.f("ck_fortune_sources_strength_range")),
        sa.ForeignKeyConstraint(["giver_node_id"], ["nodes.id"], name=op.f("fk_fortune_sources_giver_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_fortune_sources_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fortune_sources")),
    )
    with op.batch_alter_table("fortune_sources", schema=None) as batch_op:
        batch_op.create_index("ix_fortune_sources_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "pantheon_ties",
        sa.Column("god_node_id", sa.Integer(), nullable=False),
        sa.Column("other_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "tie",
            sa.Enum(
                "elder",
                "younger",
                "partner",
                "kin",
                "ruler_of",
                "servant_of",
                "rival",
                "ally",
                name="tie",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("god_node_id <> other_node_id", name=op.f("ck_pantheon_ties_two_gods")),
        sa.ForeignKeyConstraint(["god_node_id"], ["nodes.id"], name=op.f("fk_pantheon_ties_god_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["other_node_id"], ["nodes.id"], name=op.f("fk_pantheon_ties_other_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("god_node_id", "other_node_id", name=op.f("pk_pantheon_ties")),
    )
    with op.batch_alter_table("pantheon_ties", schema=None) as batch_op:
        batch_op.create_index("ix_pantheon_ties_other", ["other_node_id"], unique=False)

    op.create_table(
        "source_trust",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum(
                "observation",
                "message",
                "rumour",
                "spy",
                "scout",
                "records",
                "deception",
                "network",
                "foresight",
                "mind_reading",
                "intrusion",
                "surveillance",
                "made_mind_report",
                name="source",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("trust", sa.Integer(), nullable=False),
        sa.Column("right", sa.Integer(), nullable=False),
        sa.Column("wrong", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("trust BETWEEN 0 AND 100", name=op.f("ck_source_trust_trust_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_source_trust_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "source", name=op.f("pk_source_trust")),
    )
    op.create_table(
        "technology_profiles",
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "family",
            sa.Enum(
                "agriculture",
                "materials",
                "energy",
                "transport",
                "communication",
                "medicine",
                "warfare",
                "computation",
                "life",
                "construction",
                "administration",
                "space",
                "mind",
                name="family",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 10", name=op.f("ck_technology_profiles_level_range")),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_technology_profiles_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("holder_node_id", "family", name=op.f("pk_technology_profiles")),
    )
    op.create_table(
        "dimension_aspects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dimension_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "fire",
                "water",
                "air",
                "earth",
                "plant",
                "animal",
                "body",
                "mind",
                "image",
                "spirit",
                "time",
                "void",
                "death",
                "light",
                "space",
                "force",
                "sound",
                "emotion",
                "fate",
                "machine",
                "information",
                name="form",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "element",
            sa.Enum(
                "fire",
                "water",
                "earth",
                "air",
                "void",
                "light",
                "shadow",
                "ice",
                "lightning",
                "metal",
                "wood",
                name="element",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("(form IS NULL) <> (element IS NULL)", name=op.f("ck_dimension_aspects_form_or_element")),
        sa.CheckConstraint("strength BETWEEN 0 AND 100", name=op.f("ck_dimension_aspects_strength_range")),
        sa.ForeignKeyConstraint(["dimension_id"], ["dimensions.id"], name=op.f("fk_dimension_aspects_dimension_id_dimensions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dimension_aspects")),
    )
    with op.batch_alter_table("dimension_aspects", schema=None) as batch_op:
        batch_op.create_index("ix_dimension_aspects_dimension", ["dimension_id"], unique=False)

    op.create_table(
        "fortune_laws",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "law",
            sa.Enum("causes_only", "personal", "divine", "belief_shaped", name="law", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_fortune_laws_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_fortune_laws")),
    )
    op.create_table(
        "horror_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column(
            "target",
            sa.Enum(
                "light",
                "sound",
                "weather",
                "time",
                "memory",
                "language",
                "sleep",
                "bodies",
                "minds",
                "the_dead",
                "place",
                "law",
                name="target",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "effect",
            sa.Enum("suppress", "invert", "distort", "multiply", "take", "reveal", "mark", name="effect", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "scope", sa.Enum("person", "community", "region", "world", name="scope", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column(
            "sense",
            sa.Enum("seen", "heard", "felt", "dreamed", "absent", "not_perceived", name="sense", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum("outer_being", "rift", "phenomenon", "god", "made_thing", "unknown", name="source", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("source_node_id", sa.Integer(), nullable=True),
        sa.Column("subject_node_id", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("sanity_cost", sa.Integer(), nullable=False),
        sa.Column("leak", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["source_node_id"], ["nodes.id"], name=op.f("fk_horror_events_source_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_node_id"], ["nodes.id"], name=op.f("fk_horror_events_subject_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_horror_events_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_horror_events")),
    )
    with op.batch_alter_table("horror_events", schema=None) as batch_op:
        batch_op.create_index("ix_horror_events_world", ["world_id"], unique=False)

    op.create_table(
        "journey_encounters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=True),
        sa.Column(
            "environment",
            sa.Enum("sea", "land", "air", "space", "rift", "network", name="environment", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "effect",
            sa.Enum(
                "attack",
                "hazard",
                "delay",
                "straying",
                "find",
                "toll",
                "sickness",
                "desertion",
                name="effect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("loss_pct", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("loss_pct BETWEEN 0 AND 100", name=op.f("ck_journey_encounters_loss_pct_range")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name=op.f("ck_journey_encounters_weight_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_journey_encounters_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_journey_encounters")),
    )
    with op.batch_alter_table("journey_encounters", schema=None) as batch_op:
        batch_op.create_index("ix_journey_encounters_env", ["environment"], unique=False)
        batch_op.create_index(batch_op.f("ix_journey_encounters_world_id"), ["world_id"], unique=False)

    op.create_table(
        "pantheon_structures",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column(
            "structure",
            sa.Enum(
                "council",
                "family",
                "court",
                "rivals",
                "single_high_god",
                "dual",
                "loose",
                name="structure",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("head_node_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["head_node_id"], ["nodes.id"], name=op.f("fk_pantheon_structures_head_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_pantheon_structures_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", name=op.f("pk_pantheon_structures")),
    )
    op.create_table(
        "subsystem_tensions",
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("subsystem", sa.String(length=120), nullable=False),
        sa.Column("tension", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("tension BETWEEN 0 AND 100", name=op.f("ck_subsystem_tensions_tension_range")),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_subsystem_tensions_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("world_id", "subsystem", name=op.f("pk_subsystem_tensions")),
    )
    op.create_table(
        "council_violations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruling_id", sa.Integer(), nullable=True),
        sa.Column("violator_node_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column(
            "step",
            sa.Enum("censure", "sanction", "exclusion", "duel", "divine_war", name="step", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["ruling_id"], ["council_rulings.id"], name=op.f("fk_council_violations_ruling_id_council_rulings"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["violator_node_id"], ["nodes.id"], name=op.f("fk_council_violations_violator_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_council_violations")),
    )
    with op.batch_alter_table("council_violations", schema=None) as batch_op:
        batch_op.create_index("ix_council_violations_violator", ["violator_node_id"], unique=False)

    op.create_table(
        "cohort_mishap_rates",
        sa.Column("community_entity_id", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("injured", sa.Integer(), nullable=False),
        sa.Column("dead", sa.Integer(), nullable=False),
        sa.Column("rate_pct", sa.Integer(), nullable=False),
        sa.Column("by_exposure", sa.JSON(), nullable=False),
        sa.CheckConstraint("dead >= 0", name=op.f("ck_cohort_mishap_rates_dead_min")),
        sa.CheckConstraint("injured >= 0", name=op.f("ck_cohort_mishap_rates_injured_min")),
        sa.ForeignKeyConstraint(["community_entity_id"], ["entities.id"], name=op.f("fk_cohort_mishap_rates_community_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("community_entity_id", "epoch", name=op.f("pk_cohort_mishap_rates")),
    )
    op.create_table(
        "constitutions",
        sa.Column("polity_entity_id", sa.Integer(), nullable=False),
        sa.Column("ideology_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "selectorate",
            sa.Enum(
                "tribe",
                "nobles",
                "council",
                "army",
                "priests",
                "citizens",
                "party",
                "shareholders",
                "algorithm",
                name="selectorate",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("offices", sa.Integer(), nullable=False),
        sa.Column("rights", sa.Integer(), nullable=False),
        sa.Column("written_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("offices >= 0", name=op.f("ck_constitutions_offices_count")),
        sa.CheckConstraint("rights BETWEEN 0 AND 100", name=op.f("ck_constitutions_rights_range")),
        sa.ForeignKeyConstraint(["ideology_entity_id"], ["entities.id"], name=op.f("fk_constitutions_ideology_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["polity_entity_id"], ["entities.id"], name=op.f("fk_constitutions_polity_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("polity_entity_id", name=op.f("pk_constitutions")),
    )
    with op.batch_alter_table("constitutions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_constitutions_ideology_entity_id"), ["ideology_entity_id"], unique=False)

    op.create_table(
        "covenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "duty",
            sa.Enum(
                "worship",
                "peace",
                "offerings",
                "keep_law",
                "protect_the_weak",
                "seek_knowledge",
                name="duty",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "promise",
            sa.Enum("protection", "plenty", "guidance", "presence", "long_life", name="promise", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "seal_sign",
            sa.Enum(
                "wrath",
                "grace",
                "silence",
                "dream",
                "omen",
                "warning",
                "revelation",
                "visitation",
                "mark",
                "wonder",
                "withdrawal",
                "test",
                "reward",
                "covenant_offer",
                name="seal_sign",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "state", sa.Enum("offered", "sealed", "kept", "broken", "ended", name="state", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("until_epoch", sa.Integer(), nullable=True),
        sa.Column("breaches", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("breaches >= 0", name=op.f("ck_covenants_breaches_min")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_covenants_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_covenants")),
    )
    with op.batch_alter_table("covenants", schema=None) as batch_op:
        batch_op.create_index("ix_covenants_people", ["people_entity_id"], unique=False)

    op.create_table(
        "creator_depictions",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "nature",
            sa.Enum("maker", "judge", "absent_one", "source", "many_faced", "unknowable", name="nature", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "aspect",
            sa.Enum(
                "sea",
                "fire",
                "earth",
                "sky",
                "storm",
                "death",
                "life",
                "dream",
                "time",
                "light",
                "shadow",
                "war",
                "craft",
                "knowledge",
                "love",
                "trickery",
                "hunt",
                "plants",
                "bone",
                "blood",
                "sound",
                "stone",
                "ice",
                "madness",
                "trade",
                "road",
                "plague",
                "harvest",
                "moon",
                "sun",
                "star",
                "lies",
                "oath",
                "memory",
                "hunger",
                "glass",
                "salt",
                "ash",
                "border",
                "sleep",
                "technology",
                "machines",
                "cities",
                "industry",
                "information",
                "space",
                "science",
                name="aspect",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_creator_depictions_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_creator_depictions")),
    )
    op.create_table(
        "creator_standing",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("awe", sa.Integer(), nullable=False),
        sa.Column("love", sa.Integer(), nullable=False),
        sa.Column("dread", sa.Integer(), nullable=False),
        sa.Column("gratitude", sa.Integer(), nullable=False),
        sa.Column("resentment", sa.Integer(), nullable=False),
        sa.Column("ignorance", sa.Integer(), nullable=False),
        sa.Column(
            "stance",
            sa.Enum("worship", "reverence", "indifference", "fear", "rejection", "denial", name="stance", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "heresy",
            sa.Enum(
                "none",
                "anti_god",
                "rival_creator",
                "denial",
                "many_creators",
                "absent_creator",
                name="heresy",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("awe BETWEEN 0 AND 100", name=op.f("ck_creator_standing_awe_range")),
        sa.CheckConstraint("dread BETWEEN 0 AND 100", name=op.f("ck_creator_standing_dread_range")),
        sa.CheckConstraint("gratitude BETWEEN 0 AND 100", name=op.f("ck_creator_standing_gratitude_range")),
        sa.CheckConstraint("ignorance BETWEEN 0 AND 100", name=op.f("ck_creator_standing_ignorance_range")),
        sa.CheckConstraint("love BETWEEN 0 AND 100", name=op.f("ck_creator_standing_love_range")),
        sa.CheckConstraint("resentment BETWEEN 0 AND 100", name=op.f("ck_creator_standing_resentment_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_creator_standing_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_creator_standing")),
    )
    op.create_table(
        "law_theories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column("law_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "believed_operator",
            sa.Enum(
                "forbid",
                "require",
                "multiply",
                "set",
                "invert",
                "bind_to_condition",
                name="believed_operator",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("believed_value", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("adapted_epochs", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_law_theories_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_law_theories_law_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_law_theories")),
    )
    with op.batch_alter_table("law_theories", schema=None) as batch_op:
        batch_op.create_index("ix_law_theories_holder", ["holder_node_id"], unique=False)
        batch_op.create_index("ix_law_theories_law", ["law_entity_id"], unique=False)

    op.create_table(
        "natural_law_exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("law_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.Enum("person", "line", "people", "kind", "place", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False
        ),
        sa.Column("node_id", sa.Integer(), nullable=True),
        sa.Column(
            "entity_type",
            sa.Enum(
                "region",
                "place",
                "resource",
                "settlement",
                "species",
                "people",
                "mortal",
                "item",
                "structure",
                "language",
                "legend",
                "tradition",
                "cult",
                "faction",
                "celestial",
                "artwork",
                "law",
                "spirit",
                "knowledge",
                "prophecy",
                "event",
                "vessel",
                "outer_being",
                "army",
                "natural_law",
                "trade_route",
                "disease",
                "polity",
                "house",
                "treaty",
                "title",
                "ideology",
                "rite",
                "beast",
                "theory",
                "art_form",
                "phenomenon",
                "cosmic_being",
                "vehicle_type",
                "unit_type",
                "equipment_model",
                "dish",
                "building_type",
                "network",
                name="entity_type",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["law_entity_id"], ["entities.id"], name=op.f("fk_natural_law_exceptions_law_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], name=op.f("fk_natural_law_exceptions_node_id_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_natural_law_exceptions")),
    )
    with op.batch_alter_table("natural_law_exceptions", schema=None) as batch_op:
        batch_op.create_index("ix_natural_law_exceptions_law", ["law_entity_id"], unique=False)

    op.create_table(
        "outer_heralds",
        sa.Column("herald_node_id", sa.Integer(), nullable=False),
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column("zeal", sa.Integer(), nullable=False),
        sa.Column("bound_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["herald_node_id"], ["nodes.id"], name=op.f("fk_outer_heralds_herald_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_heralds_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("herald_node_id", name=op.f("pk_outer_heralds")),
    )
    with op.batch_alter_table("outer_heralds", schema=None) as batch_op:
        batch_op.create_index("ix_outer_heralds_being", ["outer_entity_id"], unique=False)

    op.create_table(
        "outer_pacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column("holder_node_id", sa.Integer(), nullable=False),
        sa.Column(
            "price",
            sa.Enum("sanity", "years", "memory", "name", "service", "offering", name="price", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("power_id", sa.Integer(), nullable=True),
        sa.Column("struck_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["holder_node_id"], ["nodes.id"], name=op.f("fk_outer_pacts_holder_node_id_nodes"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_pacts_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["power_id"], ["powers.id"], name=op.f("fk_outer_pacts_power_id_powers"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outer_pacts")),
    )
    with op.batch_alter_table("outer_pacts", schema=None) as batch_op:
        batch_op.create_index("ix_outer_pacts_being", ["outer_entity_id"], unique=False)
        batch_op.create_index("ix_outer_pacts_holder", ["holder_node_id"], unique=False)

    op.create_table(
        "outer_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "goal",
            sa.Enum(
                "feed", "enter", "be_worshipped", "unmake_law", "gain_name", "open_rift", name="goal", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("target_node_id", sa.Integer(), nullable=True),
        sa.Column("state", sa.Enum("active", "achieved", "thwarted", name="state", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("sign_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_plans_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["nodes.id"], name=op.f("fk_outer_plans_target_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outer_plans")),
    )
    with op.batch_alter_table("outer_plans", schema=None) as batch_op:
        batch_op.create_index("ix_outer_plans_being", ["outer_entity_id"], unique=False)

    op.create_table(
        "outer_relations",
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column("other_entity_id", sa.Integer(), nullable=False),
        sa.Column("relation", sa.Enum("rival", "ignore", "feeds_on", name="relation", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("outer_entity_id <> other_entity_id", name=op.f("ck_outer_relations_two_beings")),
        sa.ForeignKeyConstraint(["other_entity_id"], ["entities.id"], name=op.f("fk_outer_relations_other_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_relations_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("outer_entity_id", "other_entity_id", name=op.f("pk_outer_relations")),
    )
    with op.batch_alter_table("outer_relations", schema=None) as batch_op:
        batch_op.create_index("ix_outer_relations_other", ["other_entity_id"], unique=False)

    op.create_table(
        "outer_seals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column("sealer_node_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.Enum("seal", "banish", name="kind", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("sealed_epoch", sa.Integer(), nullable=False),
        sa.Column("broken_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_seals_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sealer_node_id"], ["nodes.id"], name=op.f("fk_outer_seals_sealer_node_id_nodes"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outer_seals")),
    )
    with op.batch_alter_table("outer_seals", schema=None) as batch_op:
        batch_op.create_index("ix_outer_seals_being", ["outer_entity_id"], unique=False)

    op.create_table(
        "regional_tensions",
        sa.Column("region_entity_id", sa.Integer(), nullable=False),
        sa.Column("world_id", sa.Integer(), nullable=False),
        sa.Column("tension", sa.Integer(), nullable=False),
        sa.Column("crisis", sa.Boolean(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("tension BETWEEN 0 AND 100", name=op.f("ck_regional_tensions_tension_range")),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_regional_tensions_region_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], name=op.f("fk_regional_tensions_world_id_worlds"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("region_entity_id", name=op.f("pk_regional_tensions")),
    )
    with op.batch_alter_table("regional_tensions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_regional_tensions_world_id"), ["world_id"], unique=False)

    op.create_table(
        "relation_components",
        sa.Column("entity_a_id", sa.Integer(), nullable=False),
        sa.Column("entity_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "component",
            sa.Enum(
                "trade",
                "kinship",
                "faith",
                "war_memory",
                "help",
                "insult",
                "rivalry",
                "language",
                "values",
                name="component",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("updated_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("entity_a_id < entity_b_id", name=op.f("ck_relation_components_ordered_pair")),
        sa.CheckConstraint("value BETWEEN -100 AND 100", name=op.f("ck_relation_components_value_range")),
        sa.ForeignKeyConstraint(["entity_a_id"], ["entities.id"], name=op.f("fk_relation_components_entity_a_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_b_id"], ["entities.id"], name=op.f("fk_relation_components_entity_b_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("entity_a_id", "entity_b_id", "component", name=op.f("pk_relation_components")),
    )
    with op.batch_alter_table("relation_components", schema=None) as batch_op:
        batch_op.create_index("ix_relation_components_b", ["entity_b_id"], unique=False)

    op.create_table(
        "syncretisms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("foreign_god_id", sa.Integer(), nullable=False),
        sa.Column("son_id", sa.Integer(), nullable=False),
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column("dominant_node_id", sa.Integer(), nullable=True),
        sa.Column("since_epoch", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dominant_node_id"], ["nodes.id"], name=op.f("fk_syncretisms_dominant_node_id_nodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["foreign_god_id"], ["foreign_gods.id"], name=op.f("fk_syncretisms_foreign_god_id_foreign_gods"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_syncretisms_people_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["son_id"], ["sons.id"], name=op.f("fk_syncretisms_son_id_sons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_syncretisms")),
    )
    with op.batch_alter_table("syncretisms", schema=None) as batch_op:
        batch_op.create_index("ix_syncretisms_people", ["people_entity_id"], unique=False)

    op.create_table(
        "union_customs",
        sa.Column("people_entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "form",
            sa.Enum("pair", "plural", "group", "serial", "contract", "posthumous", "none", name="form", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "purpose",
            sa.Enum(
                "kinship", "alliance", "inheritance", "love", "faith", "labour", "status", name="purpose", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "residence",
            sa.Enum(
                "with_first_family", "with_second_family", "new_household", "separate", name="residence", native_enum=False, create_constraint=True, length=40
            ),
            nullable=False,
        ),
        sa.Column(
            "descent",
            sa.Enum(
                "through_first",
                "through_second",
                "through_both",
                "chosen",
                "by_house_rule",
                name="descent",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "exchange",
            sa.Enum("to_one_family", "from_one_family", "mutual", "none", name="exchange", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "arrangement",
            sa.Enum("arranged", "chosen", "both_consent", name="arrangement", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "dissolution",
            sa.Enum("none", "by_either", "by_court", "by_custom", name="dissolution", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "endogamy",
            sa.Enum("none", "people", "class", "caste", "faith", "house", name="endogamy", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column(
            "exogamy",
            sa.Enum("none", "people", "class", "caste", "faith", "house", name="exogamy", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("term_epochs", sa.Integer(), nullable=False),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("term_epochs BETWEEN 1 AND 100", name=op.f("ck_union_customs_term_epochs_range")),
        sa.ForeignKeyConstraint(["people_entity_id"], ["entities.id"], name=op.f("fk_union_customs_people_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("people_entity_id", name=op.f("pk_union_customs")),
    )
    op.create_table(
        "outer_incursions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outer_entity_id", sa.Integer(), nullable=False),
        sa.Column("rift_id", sa.Integer(), nullable=True),
        sa.Column("region_entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "stage",
            sa.Enum("probing", "breach", "manifestation", "receding", name="stage", native_enum=False, create_constraint=True, length=40),
            nullable=False,
        ),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("started_epoch", sa.Integer(), nullable=False),
        sa.Column("ended_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["outer_entity_id"], ["entities.id"], name=op.f("fk_outer_incursions_outer_entity_id_entities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_entity_id"], ["entities.id"], name=op.f("fk_outer_incursions_region_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rift_id"], ["rifts.id"], name=op.f("fk_outer_incursions_rift_id_rifts"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outer_incursions")),
    )
    with op.batch_alter_table("outer_incursions", schema=None) as batch_op:
        batch_op.create_index("ix_outer_incursions_being", ["outer_entity_id"], unique=False)

    op.create_table(
        "rift_controls",
        sa.Column("rift_id", sa.Integer(), nullable=False),
        sa.Column("claimant_entity_id", sa.Integer(), nullable=True),
        sa.Column("work", sa.Enum("none", "sealing", "stabilising", "gate", name="work", native_enum=False, create_constraint=True, length=40), nullable=False),
        sa.Column("toll", sa.Integer(), nullable=False),
        sa.Column("adapted", sa.Integer(), nullable=False),
        sa.Column("claimed_epoch", sa.Integer(), nullable=True),
        sa.Column("locked", sa.JSON(), nullable=False),
        sa.CheckConstraint("adapted BETWEEN 0 AND 100", name=op.f("ck_rift_controls_adapted_range")),
        sa.CheckConstraint("toll >= 0", name=op.f("ck_rift_controls_toll_min")),
        sa.ForeignKeyConstraint(["claimant_entity_id"], ["entities.id"], name=op.f("fk_rift_controls_claimant_entity_id_entities"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rift_id"], ["rifts.id"], name=op.f("fk_rift_controls_rift_id_rifts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rift_id", name=op.f("pk_rift_controls")),
    )
    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "valence",
                sa.Enum("reward", "neutral", "punishment", "mixed", name="valence", native_enum=False, create_constraint=True, length=40),
                server_default="neutral",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "permanence",
                sa.Enum("eternal", "until_rebirth", "until_judgement", "fading", name="permanence", native_enum=False, create_constraint=True, length=40),
                server_default="eternal",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "admission",
                sa.Enum(
                    "by_deeds",
                    "by_faith",
                    "by_manner_of_death",
                    "by_line",
                    "by_rites",
                    "by_choice",
                    "all",
                    name="admission",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="all",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "activity",
                sa.Enum(
                    "rest", "service", "struggle", "reunion", "learning", "dissolution", name="activity", native_enum=False, create_constraint=True, length=40
                ),
                server_default="rest",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "contact",
                sa.Enum("open", "by_rite", "closed", name="contact", native_enum=False, create_constraint=True, length=40),
                server_default="by_rite",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("ruler_node_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_afterlife_strata_ruler_node_id_nodes"), "nodes", ["ruler_node_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("celestial_readings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("visible", sa.Boolean(), server_default="1", nullable=False))

    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.add_column(sa.Column("fuel", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("electric", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("stored", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("solar", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("geothermal", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("tidal", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("fission", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("fusion", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("stellar", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("source", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("feed", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("belief", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("void", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("council_rulings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "voting_rule",
                sa.Enum(
                    "unanimity",
                    "majority",
                    "weighted_by_standing",
                    "weighted_by_rank",
                    name="voting_rule",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )

    map_attacks()
    with op.batch_alter_table("creature_anatomy", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_creature_anatomy_gaze"), type_="check")
        batch_op.drop_column("gaze")
        batch_op.drop_constraint(op.f("ck_creature_anatomy_breath"), type_="check")
        batch_op.drop_column("breath")

    map_elements()
    with op.batch_alter_table("dimensions", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_dimensions_element"), type_="check")
        batch_op.drop_constraint(op.f("ck_dimensions_element_on_elemental"), type_="check")
        batch_op.drop_column("element")

    with op.batch_alter_table("dwellings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenure",
                sa.Enum("owned", "rented", "granted", "squatted", name="tenure", native_enum=False, create_constraint=True, length=40),
                server_default="owned",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "heating",
                sa.Enum(
                    "muscle",
                    "water",
                    "wind",
                    "heat",
                    "magic",
                    "divine",
                    "fuel",
                    "electric",
                    "stored",
                    "solar",
                    "geothermal",
                    "tidal",
                    "fission",
                    "fusion",
                    "stellar",
                    "source",
                    "feed",
                    "belief",
                    "void",
                    name="heating",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "light",
                sa.Enum(
                    "muscle",
                    "water",
                    "wind",
                    "heat",
                    "magic",
                    "divine",
                    "fuel",
                    "electric",
                    "stored",
                    "solar",
                    "geothermal",
                    "tidal",
                    "fission",
                    "fusion",
                    "stellar",
                    "source",
                    "feed",
                    "belief",
                    "void",
                    name="light",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("crowding", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("feuds", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "level",
                sa.Enum("insult", "blood", "raid", "war", name="level", native_enum=False, create_constraint=True, length=40),
                server_default="blood",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("mediator_node_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_feuds_mediator_node_id_nodes"), "nodes", ["mediator_node_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("hero_quests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "target_kind",
                sa.Enum(
                    "star",
                    "route",
                    "knowledge",
                    "outer_being",
                    "species",
                    "item",
                    "person",
                    "place",
                    "incident_arc",
                    name="target_kind",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="person",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "obstacle",
                sa.Enum(
                    "distance",
                    "guardian",
                    "riddle",
                    "rival",
                    "law",
                    "concealment",
                    "danger_of_place",
                    "cost",
                    name="obstacle",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="distance",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "reward",
                sa.Enum(
                    "renown",
                    "power",
                    "knowledge",
                    "item",
                    "standing",
                    "office",
                    "cure",
                    "peace",
                    name="reward",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="renown",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "scale",
                sa.Enum("personal", "legendary", name="scale", native_enum=False, create_constraint=True, length=40),
                server_default="personal",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("locked", sa.JSON(), server_default="[]", nullable=False))

    with op.batch_alter_table("households", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "form",
                sa.Enum(
                    "nuclear",
                    "extended",
                    "stem",
                    "joint",
                    "polygamous",
                    "communal",
                    "single",
                    "institutional",
                    "mixed",
                    "chosen",
                    name="form",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="nuclear",
                nullable=False,
            )
        )

    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.add_column(sa.Column("supplies", sa.Integer(), server_default="100", nullable=False))
        batch_op.add_column(sa.Column("births", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("deaths", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(
            sa.Column(
                "arrival", sa.Enum("settlers", "refugees", "invaders", name="arrival", native_enum=False, create_constraint=True, length=40), nullable=True
            )
        )

    with op.batch_alter_table("legendary_quests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "target_kind",
                sa.Enum(
                    "star",
                    "route",
                    "knowledge",
                    "outer_being",
                    "species",
                    "item",
                    "person",
                    "place",
                    "incident_arc",
                    name="target_kind",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="star",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "obstacle",
                sa.Enum(
                    "distance",
                    "guardian",
                    "riddle",
                    "rival",
                    "law",
                    "concealment",
                    "danger_of_place",
                    "cost",
                    name="obstacle",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="distance",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "reward",
                sa.Enum(
                    "renown",
                    "power",
                    "knowledge",
                    "item",
                    "standing",
                    "office",
                    "cure",
                    "peace",
                    name="reward",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="renown",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "scale",
                sa.Enum("personal", "legendary", name="scale", native_enum=False, create_constraint=True, length=40),
                server_default="legendary",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("locked", sa.JSON(), server_default="[]", nullable=False))

    with op.batch_alter_table("mishaps", schema=None) as batch_op:
        batch_op.add_column(sa.Column("severity", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("died", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("witnesses", sa.JSON(), server_default="[]", nullable=False))

    with op.batch_alter_table("natural_law_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "target",
                sa.Enum(
                    "stat",
                    "life",
                    "death",
                    "magic",
                    "war",
                    "harvest",
                    "travel",
                    "language",
                    "disaster",
                    "material",
                    "light",
                    "weight",
                    "season",
                    "dreams",
                    "oaths",
                    "made_minds",
                    "copies",
                    "powers",
                    "sources",
                    "concealment",
                    "living_craft",
                    "realms",
                    name="target",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "operator",
                sa.Enum(
                    "forbid", "require", "multiply", "set", "invert", "bind_to_condition", name="operator", native_enum=False, create_constraint=True, length=40
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("key", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("value", sa.Integer(), server_default="100", nullable=False))
        batch_op.add_column(
            sa.Column(
                "condition",
                sa.Enum(
                    "always",
                    "at_war",
                    "at_peace",
                    "cold_season",
                    "doom_rising",
                    "author_worshipped",
                    "author_forgotten",
                    name="condition",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                server_default="always",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("until_epoch", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("suspended", sa.Boolean(), server_default="0", nullable=False))

    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.add_column(sa.Column("witness_node_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "penalty",
                sa.Enum("shame", "fine", "exile", "outlawry", "curse", name="penalty", native_enum=False, create_constraint=True, length=40),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(batch_op.f("fk_oaths_witness_node_id_nodes"), "nodes", ["witness_node_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("outer_being_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unfed_epochs", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(
            sa.Column(
                "fate",
                sa.Enum("active", "sealed", "banished", "starved", "destroyed", name="fate", native_enum=False, create_constraint=True, length=40),
                server_default="active",
                nullable=False,
            )
        )

    with op.batch_alter_table("prophecy_conditions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("retold", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("forged", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("rival_entity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f("fk_prophecy_conditions_rival_entity_id_entities"), "entities", ["rival_entity_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("resource_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "extraction",
                sa.Enum(
                    "mining",
                    "quarrying",
                    "logging",
                    "fishing",
                    "herding",
                    "farming",
                    "gathering",
                    "drilling",
                    "pumping",
                    "dredging",
                    "deep_sea",
                    "atmospheric",
                    "asteroid",
                    "stellar",
                    "source_harvest",
                    "salvage",
                    "living_harvest",
                    "distillation",
                    name="extraction",
                    native_enum=False,
                    create_constraint=True,
                    length=40,
                ),
                nullable=True,
            )
        )

    map_ranks()
    with op.batch_alter_table("servitors", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_servitors_rank"), type_="check")
        batch_op.drop_column("rank")

    with op.batch_alter_table("storytellers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("palette", sa.JSON(), server_default="{}", nullable=False))
        batch_op.add_column(sa.Column("target_points", sa.JSON(), server_default="[]", nullable=False))

    with op.batch_alter_table("time_budgets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("learning", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("care", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("art", sa.Integer(), server_default="0", nullable=False))

    with op.batch_alter_table("world_attention", schema=None) as batch_op:
        batch_op.add_column(sa.Column("far_epochs", sa.Integer(), server_default="0", nullable=False))

    map_typed_models()


def downgrade() -> None:
    with op.batch_alter_table("world_attention", schema=None) as batch_op:
        batch_op.drop_column("far_epochs")

    with op.batch_alter_table("time_budgets", schema=None) as batch_op:
        batch_op.drop_column("art")
        batch_op.drop_column("care")
        batch_op.drop_column("learning")

    with op.batch_alter_table("storytellers", schema=None) as batch_op:
        batch_op.drop_column("target_points")
        batch_op.drop_column("palette")

    with op.batch_alter_table("servitors", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rank", enum_of(SERVITOR_RANKS, "rank"), server_default="herald", nullable=False))

    with op.batch_alter_table("resource_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_resource_profiles_extraction"), type_="check")
        batch_op.drop_column("extraction")

    with op.batch_alter_table("prophecy_conditions", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_prophecy_conditions_rival_entity_id_entities"), type_="foreignkey")
        batch_op.drop_column("rival_entity_id")
        batch_op.drop_column("forged")
        batch_op.drop_column("retold")

    with op.batch_alter_table("outer_being_profiles", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_outer_being_profiles_fate"), type_="check")
        batch_op.drop_column("fate")
        batch_op.drop_column("unfed_epochs")

    with op.batch_alter_table("oaths", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_oaths_witness_node_id_nodes"), type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_oaths_penalty"), type_="check")
        batch_op.drop_column("penalty")
        batch_op.drop_column("witness_node_id")

    with op.batch_alter_table("natural_law_profiles", schema=None) as batch_op:
        batch_op.drop_column("suspended")
        batch_op.drop_column("until_epoch")
        batch_op.drop_constraint(op.f("ck_natural_law_profiles_condition"), type_="check")
        batch_op.drop_column("condition")
        batch_op.drop_column("value")
        batch_op.drop_column("key")
        batch_op.drop_constraint(op.f("ck_natural_law_profiles_operator"), type_="check")
        batch_op.drop_column("operator")
        batch_op.drop_constraint(op.f("ck_natural_law_profiles_target"), type_="check")
        batch_op.drop_column("target")

    with op.batch_alter_table("mishaps", schema=None) as batch_op:
        batch_op.drop_column("witnesses")
        batch_op.drop_column("died")
        batch_op.drop_column("severity")

    with op.batch_alter_table("legendary_quests", schema=None) as batch_op:
        batch_op.drop_column("locked")
        batch_op.drop_constraint(op.f("ck_legendary_quests_scale"), type_="check")
        batch_op.drop_column("scale")
        batch_op.drop_constraint(op.f("ck_legendary_quests_reward"), type_="check")
        batch_op.drop_column("reward")
        batch_op.drop_constraint(op.f("ck_legendary_quests_obstacle"), type_="check")
        batch_op.drop_column("obstacle")
        batch_op.drop_constraint(op.f("ck_legendary_quests_target_kind"), type_="check")
        batch_op.drop_column("target_kind")

    with op.batch_alter_table("journeys", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_journeys_arrival"), type_="check")
        batch_op.drop_column("arrival")
        batch_op.drop_column("deaths")
        batch_op.drop_column("births")
        batch_op.drop_column("supplies")

    with op.batch_alter_table("households", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_households_form"), type_="check")
        batch_op.drop_column("form")

    with op.batch_alter_table("hero_quests", schema=None) as batch_op:
        batch_op.drop_column("locked")
        batch_op.drop_constraint(op.f("ck_hero_quests_scale"), type_="check")
        batch_op.drop_column("scale")
        batch_op.drop_constraint(op.f("ck_hero_quests_reward"), type_="check")
        batch_op.drop_column("reward")
        batch_op.drop_constraint(op.f("ck_hero_quests_obstacle"), type_="check")
        batch_op.drop_column("obstacle")
        batch_op.drop_constraint(op.f("ck_hero_quests_target_kind"), type_="check")
        batch_op.drop_column("target_kind")

    with op.batch_alter_table("feuds", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_feuds_mediator_node_id_nodes"), type_="foreignkey")
        batch_op.drop_column("mediator_node_id")
        batch_op.drop_constraint(op.f("ck_feuds_level"), type_="check")
        batch_op.drop_column("level")

    with op.batch_alter_table("dwellings", schema=None) as batch_op:
        batch_op.drop_column("crowding")
        batch_op.drop_constraint(op.f("ck_dwellings_light"), type_="check")
        batch_op.drop_column("light")
        batch_op.drop_constraint(op.f("ck_dwellings_heating"), type_="check")
        batch_op.drop_column("heating")
        batch_op.drop_constraint(op.f("ck_dwellings_tenure"), type_="check")
        batch_op.drop_column("tenure")

    with op.batch_alter_table("dimensions", schema=None) as batch_op:
        batch_op.create_check_constraint("element_on_elemental", "element IS NULL OR dimension_kind = 'elemental'")
        batch_op.add_column(
            sa.Column(
                "element", enum_of(("fire", "water", "earth", "air", "void", "light", "shadow", "ice", "lightning", "metal", "wood"), "element"), nullable=True
            )
        )

    with op.batch_alter_table("creature_anatomy", schema=None) as batch_op:
        batch_op.add_column(sa.Column("breath", enum_of(("fire", "frost", "venom_gas", "web", "steam"), "breath"), nullable=True))
        batch_op.add_column(sa.Column("gaze", enum_of(("terror", "petrify", "sleep", "madness"), "gaze"), nullable=True))

    with op.batch_alter_table("council_rulings", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_council_rulings_voting_rule"), type_="check")
        batch_op.drop_column("voting_rule")

    with op.batch_alter_table("community_industry", schema=None) as batch_op:
        batch_op.drop_column("void")
        batch_op.drop_column("belief")
        batch_op.drop_column("feed")
        batch_op.drop_column("source")
        batch_op.drop_column("stellar")
        batch_op.drop_column("fusion")
        batch_op.drop_column("fission")
        batch_op.drop_column("tidal")
        batch_op.drop_column("geothermal")
        batch_op.drop_column("solar")
        batch_op.drop_column("stored")
        batch_op.drop_column("electric")
        batch_op.drop_column("fuel")

    with op.batch_alter_table("celestial_readings", schema=None) as batch_op:
        batch_op.drop_column("visible")

    with op.batch_alter_table("afterlife_strata", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_afterlife_strata_ruler_node_id_nodes"), type_="foreignkey")
        batch_op.drop_column("ruler_node_id")
        batch_op.drop_constraint(op.f("ck_afterlife_strata_contact"), type_="check")
        batch_op.drop_column("contact")
        batch_op.drop_constraint(op.f("ck_afterlife_strata_activity"), type_="check")
        batch_op.drop_column("activity")
        batch_op.drop_constraint(op.f("ck_afterlife_strata_admission"), type_="check")
        batch_op.drop_column("admission")
        batch_op.drop_constraint(op.f("ck_afterlife_strata_permanence"), type_="check")
        batch_op.drop_column("permanence")
        batch_op.drop_constraint(op.f("ck_afterlife_strata_valence"), type_="check")
        batch_op.drop_column("valence")

    op.drop_table("rift_controls")
    with op.batch_alter_table("outer_incursions", schema=None) as batch_op:
        batch_op.drop_index("ix_outer_incursions_being")

    op.drop_table("outer_incursions")
    op.drop_table("union_customs")
    with op.batch_alter_table("syncretisms", schema=None) as batch_op:
        batch_op.drop_index("ix_syncretisms_people")

    op.drop_table("syncretisms")
    with op.batch_alter_table("relation_components", schema=None) as batch_op:
        batch_op.drop_index("ix_relation_components_b")

    op.drop_table("relation_components")
    with op.batch_alter_table("regional_tensions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_regional_tensions_world_id"))

    op.drop_table("regional_tensions")
    with op.batch_alter_table("outer_seals", schema=None) as batch_op:
        batch_op.drop_index("ix_outer_seals_being")

    op.drop_table("outer_seals")
    with op.batch_alter_table("outer_relations", schema=None) as batch_op:
        batch_op.drop_index("ix_outer_relations_other")

    op.drop_table("outer_relations")
    with op.batch_alter_table("outer_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_outer_plans_being")

    op.drop_table("outer_plans")
    with op.batch_alter_table("outer_pacts", schema=None) as batch_op:
        batch_op.drop_index("ix_outer_pacts_holder")
        batch_op.drop_index("ix_outer_pacts_being")

    op.drop_table("outer_pacts")
    with op.batch_alter_table("outer_heralds", schema=None) as batch_op:
        batch_op.drop_index("ix_outer_heralds_being")

    op.drop_table("outer_heralds")
    with op.batch_alter_table("natural_law_exceptions", schema=None) as batch_op:
        batch_op.drop_index("ix_natural_law_exceptions_law")

    op.drop_table("natural_law_exceptions")
    with op.batch_alter_table("law_theories", schema=None) as batch_op:
        batch_op.drop_index("ix_law_theories_law")
        batch_op.drop_index("ix_law_theories_holder")

    op.drop_table("law_theories")
    op.drop_table("creator_standing")
    op.drop_table("creator_depictions")
    with op.batch_alter_table("covenants", schema=None) as batch_op:
        batch_op.drop_index("ix_covenants_people")

    op.drop_table("covenants")
    with op.batch_alter_table("constitutions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_constitutions_ideology_entity_id"))

    op.drop_table("constitutions")
    op.drop_table("cohort_mishap_rates")
    with op.batch_alter_table("council_violations", schema=None) as batch_op:
        batch_op.drop_index("ix_council_violations_violator")

    op.drop_table("council_violations")
    op.drop_table("subsystem_tensions")
    op.drop_table("pantheon_structures")
    with op.batch_alter_table("journey_encounters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_journey_encounters_world_id"))
        batch_op.drop_index("ix_journey_encounters_env")

    op.drop_table("journey_encounters")
    with op.batch_alter_table("horror_events", schema=None) as batch_op:
        batch_op.drop_index("ix_horror_events_world")

    op.drop_table("horror_events")
    op.drop_table("fortune_laws")
    with op.batch_alter_table("dimension_aspects", schema=None) as batch_op:
        batch_op.drop_index("ix_dimension_aspects_dimension")

    op.drop_table("dimension_aspects")
    op.drop_table("technology_profiles")
    op.drop_table("source_trust")
    with op.batch_alter_table("pantheon_ties", schema=None) as batch_op:
        batch_op.drop_index("ix_pantheon_ties_other")

    op.drop_table("pantheon_ties")
    with op.batch_alter_table("fortune_sources", schema=None) as batch_op:
        batch_op.drop_index("ix_fortune_sources_holder")

    op.drop_table("fortune_sources")
    op.drop_table("fortune_profiles")
    with op.batch_alter_table("divine_powers", schema=None) as batch_op:
        batch_op.drop_index("ix_divine_powers_holder")

    op.drop_table("divine_powers")
    op.drop_table("divine_council_seats")
    with op.batch_alter_table("creature_attacks", schema=None) as batch_op:
        batch_op.drop_index("ix_creature_attacks_node")

    op.drop_table("creature_attacks")
    op.drop_table("creator_chosen")
    op.drop_table("council_procedures")
    retype(False)
