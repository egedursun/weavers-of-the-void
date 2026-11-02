from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CosmicHorrorRules:
    alignment_route_danger: int = rule(15, 0, 100, RuleGroup.COSMIC_HORROR, "Route danger increase when the stars align")
    apocalypse_leak: int = rule(4, 0, 50, RuleGroup.COSMIC_HORROR, "Contribution to leak when the apocalypse reaches its threshold (per epoch)")
    horror_event_divisor: int = rule(250, 10, 10000, RuleGroup.COSMIC_HORROR, "Horror event chance: leak / this number")
    young_cap: int = rule(25, 0, 100, RuleGroup.COSMIC_HORROR, "Initial leak cap on a young world")
    young_cap_growth: int = rule(8, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch increase of the leak cap on a young world")
    repair_threshold: int = rule(20, 0, 100, RuleGroup.COSMIC_HORROR, "Leak at which the fabric starts repairing itself")
    repair_divisor: int = rule(4, 1, 100, RuleGroup.COSMIC_HORROR, "Repair: \u22121 for every this many points above the threshold")
    source_cap: int = rule(
        12,
        0,
        100,
        RuleGroup.COSMIC_HORROR,
        "Most one counted leak source (forbidden knowledge, gates, godless, addicted, outer cults) adds per epoch (0: unlimited)",
    )
    outer_being_threshold: int = rule(85, 1, 100, RuleGroup.COSMIC_HORROR, "Leak at which an Outer Being appears")
    calling_threshold: int = rule(50, 0, 100, RuleGroup.APOCALYPSE, "Average leak at which the apocalypse turns into the Calling")
    madness_chance: int = rule(30, 0, 100, RuleGroup.COSMIC_HORROR, "Madness event in a community whose sanity collapses (%)")
    whisperers_chance: int = rule(50, 0, 100, RuleGroup.COSMIC_HORROR, "Madness turns into an outer cult (%)")
    outer_being_chance: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "An Outer Being appears when the threshold is exceeded (%)")
    forbidden_knowledge_leak: int = rule(4, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of each community knowing forbidden knowledge")
    gate_leak: int = rule(2, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of each open gate, swallowing or dream route")
    dead_star_leak: int = rule(3, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of a dead, black or broken star")
    godless_leak: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of each godless community")
    addicted_leak: int = rule(2, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of each addicted community")
    outer_cult_leak: int = rule(3, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of each outer cult")
    outer_being_leak: int = rule(5, 0, 50, RuleGroup.COSMIC_HORROR, "Leak contribution of each Outer Being")
    worshipper_repair: int = rule(
        50, 0, 1000, RuleGroup.COSMIC_HORROR, "Leak repair by each worshipping community (percentage points; total limited by worshipper_cap)"
    )
    worshipper_cap: int = rule(
        5,
        0,
        100,
        RuleGroup.COSMIC_HORROR,
        "Cap of repair coming from the number of worshipping communities (a crowded world cannot repair the fabric infinitely; the rest comes from the worshipper ratio)",
    )
    priest_cap: int = rule(3, 0, 100, RuleGroup.COSMIC_HORROR, "Cap of repair by communities with a strong priest class (1 per community)")
    worshipper_ratio_repair: int = rule(3, 0, 50, RuleGroup.COSMIC_HORROR, "Repair from the worshipper ratio (if everyone worships)")
    temple_cap: int = rule(3, 0, 50, RuleGroup.COSMIC_HORROR, "Maximum leak repair by temples (1 per temple)")
    priest_min_pct: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Minimum priest-class share that repairs leak (%)")
    fabric_self_repair: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Spontaneous repair of the fabric each epoch")
    repair_full_at: int = rule(
        12,
        1,
        100,
        RuleGroup.COSMIC_HORROR,
        "Repair by worship, temples and priests reaches full strength at this leak; below it, it decreases proportionally to leak (an untorn fabric is not repaired)",
    )
    young_growth_pct: int = rule(50, 0, 100, RuleGroup.COSMIC_HORROR, "Remaining share of leak growth on a young world (%)")
    warning_1: int = rule(30, 0, 100, RuleGroup.COSMIC_HORROR, "Leak at which the first leak warning arrives")
    warning_2: int = rule(60, 0, 100, RuleGroup.COSMIC_HORROR, 'Leak at which the "geometry is breaking" warning arrives')
    default_sanity: int = rule(70, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity assumed for a community with no recorded sanity")
    leak_erosion_divisor: int = rule(20, 1, 1000, RuleGroup.COSMIC_HORROR, "Sanity erosion: leak / this number")
    forbidden_erosion: int = rule(6, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity loss of those who know forbidden knowledge")
    outer_being_erosion: int = rule(4, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity loss on a world with an Outer Being")
    medicine_repair: int = rule(3, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity repair for those who know medicine")
    priest_repair_divisor: int = rule(5, 1, 100, RuleGroup.COSMIC_HORROR, "Sanity repair: priest share / this number")
    worship_repair: int = rule(1, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity repair of someone who worships a god")
    sanity_self_repair: int = rule(1, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch spontaneous sanity repair")
    clouding_threshold: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity at which the mind starts to cloud")
    madness_threshold: int = rule(20, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity at which madness begins")
    madness_population_loss_pct: int = rule(6, 0, 100, RuleGroup.COSMIC_HORROR, "Population lost in a madness epidemic (%)")
    whisperers_power: int = rule(3, 1, 12, RuleGroup.COSMIC_HORROR, "Power level of the Whisperers cult")
    whisperers_min_followers: int = rule(50, 1, 100000, RuleGroup.COSMIC_HORROR, "Minimum followers of the Whisperers")
    whisperers_default_population: int = rule(
        1000, 1, 1000000, RuleGroup.COSMIC_HORROR, "Population assumed for a people with no recorded population (for the Whisperers)"
    )
    whisperers_share_pct: int = rule(5, 0, 100, RuleGroup.COSMIC_HORROR, "Share of the people passing to the Whisperers (%)")
    whisperers_zealotry: int = rule(85, 0, 100, RuleGroup.COSMIC_HORROR, "Zealotry of the Whisperers")
    whisperers_influence: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "Influence of the Whisperers")
    whisperers_sanity: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity of the Whisperers")
    madness_son_essence_divisor: int = rule(
        15, 1, 1000, RuleGroup.COSMIC_HORROR, "Per-epoch essence of a son with the Madness domain: average leak / this number"
    )
    madness_son_existence_gain: int = rule(1, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch existence gain of a son with the Madness domain")
    outer_being_power: int = rule(10, 1, 12, RuleGroup.COSMIC_HORROR, "Power level of an Outer Being")
    outer_being_size_base: int = rule(60, 0, 100, RuleGroup.COSMIC_HORROR, "Base size of an Outer Being")
    outer_being_size_die: int = rule(40, 1, 100, RuleGroup.COSMIC_HORROR, "Die added to an Outer Being's size")
    outer_being_interest_base: int = rule(30, 0, 100, RuleGroup.COSMIC_HORROR, "Base interest of an Outer Being")
    outer_being_interest_die: int = rule(40, 1, 100, RuleGroup.COSMIC_HORROR, "Die added to an Outer Being's interest")
    outer_being_influence_base: int = rule(50, 0, 100, RuleGroup.COSMIC_HORROR, "Base influence of an Outer Being")
    outer_being_influence_die: int = rule(50, 1, 100, RuleGroup.COSMIC_HORROR, "Die added to an Outer Being's influence")
    outer_being_entry_leak_drop: int = rule(20, 0, 100, RuleGroup.COSMIC_HORROR, "Leak drop when an Outer Being enters")
    default_interest: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "Interest assumed for an Outer Being with no recorded interest")
    interest_die: int = rule(11, 1, 100, RuleGroup.COSMIC_HORROR, "Per-epoch interest die of an Outer Being")
    interest_decay: int = rule(4, 0, 100, RuleGroup.COSMIC_HORROR, "Subtracted from an Outer Being's interest each epoch")
    outer_being_victims: int = rule(3, 0, 100, RuleGroup.COSMIC_HORROR, "Neighbours whose sanity an Outer Being gnaws each epoch")
    outer_being_size_per_victim: int = rule(
        25, 0, 100, RuleGroup.COSMIC_HORROR, "Each this much Outer Being size adds one more gnawed neighbour (0 = size has no reach)"
    )
    outer_being_sanity_divisor: int = rule(10, 1, 1000, RuleGroup.COSMIC_HORROR, "Neighbour's sanity loss: interest / this number")
    outer_being_mutation_divisor: int = rule(300, 1, 100000, RuleGroup.COSMIC_HORROR, "Mutation chance of a neighbouring species: interest / this number")
    apocalypse_event_divisor: int = rule(
        6, 1, 1000, RuleGroup.COSMIC_HORROR, "Apocalypse contribution to horror event chance: (clock / threshold) / this number"
    )
    alignment_leak: int = rule(8, 0, 100, RuleGroup.COSMIC_HORROR, "Leak increase of every world when the stars align")
    sky_eye_sanity_loss: int = rule(10, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity taken away by the Eye in the sky")
    silence_word_loss_pct: int = rule(20, 0, 100, RuleGroup.COSMIC_HORROR, "Share of words forgotten in a wave of silence (%)")
    reverse_rain_souls: int = rule(4, 0, 100, RuleGroup.COSMIC_HORROR, "Maximum souls rising to the sky in reverse rain")
    void_min_regions: int = rule(5, 1, 1000, RuleGroup.COSMIC_HORROR, "Minimum regions on a world for the void to be able to swallow a region")
    dimming_brightness_loss: int = rule(20, 0, 100, RuleGroup.COSMIC_HORROR, "Brightness the dimming drinks from the star of the haunted world")
    whispers_knowledge_level: int = rule(2, 1, 12, RuleGroup.COSMIC_HORROR, "Level of the forbidden knowledge the whispers from beyond teach")
    whispers_knowledge_power: int = rule(4, 1, 12, RuleGroup.COSMIC_HORROR, "Power level of the forbidden knowledge the whispers from beyond teach")
    whispers_sanity_loss: int = rule(12, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity the listener of the whispers from beyond loses")
    son_default_sanity: int = rule(80, 0, 100, RuleGroup.COSMIC_HORROR, "Sanity of a son with no recorded sanity")
    son_leak_erosion_divisor: int = rule(25, 1, 1000, RuleGroup.COSMIC_HORROR, "Son sanity erosion: leak of the world they stand on / this number")
    son_outer_erosion: int = rule(3, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity loss of a son on a world with an Outer Being")
    son_bargain_erosion: int = rule(4, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity loss of a son for each bargain struck with an Outer Being")
    son_forbidden_erosion: int = rule(
        2, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity loss of a son for each community worshipping them that knows forbidden knowledge"
    )
    son_madness_resistance_pct: int = rule(50, 0, 100, RuleGroup.COSMIC_HORROR, "Share of sanity erosion suffered by a son of a madness domain (%)")
    son_sanity_repair: int = rule(2, 0, 100, RuleGroup.COSMIC_HORROR, "Per-epoch sanity recovery of a son")
    son_clouding_threshold: int = rule(40, 0, 100, RuleGroup.COSMIC_HORROR, "Son sanity at which their mind clouds")
    son_madness_threshold: int = rule(15, 0, 100, RuleGroup.COSMIC_HORROR, "Son sanity at which madness begins")
    mad_son_max_tool_actions: int = rule(
        1, 0, 20, RuleGroup.COSMIC_HORROR, "A son below the madness threshold cannot use a tool that costs more action points than this"
    )
