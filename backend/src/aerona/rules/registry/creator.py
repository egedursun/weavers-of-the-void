from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CreatorRules:
    spread_interest_pct: int = rule(
        5, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of the world's mean spread of learning a Creator who loves knowledge counts as discovery (%)"
    )
    cult_faith_per_essence: int = rule(4, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "Every this much cult faith gives the god 1 essence")
    cult_faith_per_apocalypse_push: int = rule(25, 1, 1000, RuleGroup.APOCALYPSE, "Every this much cult faith pushes the apocalypse back by 1")
    cult_apocalypse_push_cap: int = rule(5, 0, 100, RuleGroup.APOCALYPSE, "Maximum apocalypse push-back by the cult in one epoch")
    wrath_threshold: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Threshold at which the Creator's wrath overflows")
    content_threshold: int = rule(55, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Contentment at which the Creator sends down grace")
    wrath_sign_chance: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "The wrathful Creator's punishment descends (%)")
    content_sign_chance: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "The content Creator's grace descends (%)")
    silence_sign_chance: int = rule(50, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "The indifferent Creator falls silent (sign %)")
    loneliness_sign_chance: int = rule(50, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "The lonely Creator sends a dream (%)")
    start_contentment: int = rule(50, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Creator's starting contentment")
    start_wrath: int = rule(20, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Creator's starting wrath")
    start_attention: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Creator's starting attention")
    start_loneliness: int = rule(30, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Creator's starting loneliness")
    label_wrathful: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, 'Wrath at which the mood counts as "wrathful"')
    label_silent: int = rule(20, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, 'Attention at which the mood counts as "distant and silent" (at most)')
    label_lonely: int = rule(70, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, 'Loneliness at which the mood counts as "lonely"')
    label_content: int = rule(55, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, 'Contentment at which the mood counts as "content"')
    label_restless: int = rule(45, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, 'Wrath at which the mood counts as "restless"')
    cult_population_per_faith: int = rule(2000, 1, 10000000, RuleGroup.CREATOR_AND_ESSENCE, "Worshipping population giving 1 faith in the cult (at full piety)")
    cult_default_piety: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Piety assumed for a cult worshipper with unknown piety")
    cult_followers_per_faith: int = rule(50, 1, 10000000, RuleGroup.CREATOR_AND_ESSENCE, "Followers giving 1 faith in the cult")
    cult_faith_per_mortal: int = rule(2, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Faith of each mortal who worships the Creator")
    wrath_keep_pct: int = rule(82, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of wrath kept from epoch to epoch (%)")
    wrath_godless_max: int = rule(
        4,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Maximum contribution of godless communities to wrath (per epoch; saturates toward this cap as the godless share grows)",
    )
    wrath_godless_half_pct: int = rule(
        10, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "When this percentage of communities are godless, the godlessness contribution is half the cap"
    )
    wrath_rebel_max: int = rule(
        8,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Maximum contribution of rebel sons to wrath (per epoch; saturates toward this cap as the number of rebels grows)",
    )
    wrath_rebel_half: int = rule(1, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "With this many rebel sons the rebellion contribution is half the cap")
    wrath_war_max: int = rule(
        10, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Maximum contribution of ongoing community wars to wrath (per epoch; saturates toward this cap as war grows)"
    )
    wrath_war_half_pct: int = rule(
        100, 1, 10000, RuleGroup.CREATOR_AND_ESSENCE, "When ongoing wars are at this percentage of the world's war cap, the war contribution is half the cap"
    )
    wrath_apocalypse_divisor: int = rule(
        12, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Doomsday clock contribution to wrath: clock (% of threshold) / this number"
    )
    content_keep_pct: int = rule(82, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of contentment kept from epoch to epoch (%)")
    content_cult_max: int = rule(
        12, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Maximum contribution of the cult to contentment (per epoch; saturates toward this cap as the cult grows)"
    )
    content_cult_half: int = rule(10, 1, 10000, RuleGroup.CREATOR_AND_ESSENCE, "With this many cult worshippers the cult contribution is half the cap")
    content_new_life_max: int = rule(
        5,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Maximum contribution of new living beings to contentment (per epoch; saturates toward this cap as births grow)",
    )
    content_new_life_half: int = rule(
        25, 1, 10000, RuleGroup.CREATOR_AND_ESSENCE, "When this many new living beings are born in an epoch the life contribution is half the cap"
    )
    content_action: int = rule(5, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Contribution to contentment of an epoch in which the god acted")
    content_passion_max: int = rule(12, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Most contentment an epoch that answers the god's passions can bring")
    content_passion_half: int = rule(5, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Matching events in an epoch that bring half of the passion contentment")
    mood_opposition_pct: int = rule(
        2, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Wrath and contentment soothe each other: each decreases every epoch by this percentage of the other"
    )
    attention_keep_pct: int = rule(80, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of attention kept from epoch to epoch (%)")
    attention_per_action: int = rule(6, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Contribution of each of the god's actions to attention")
    attention_action_cap: int = rule(30, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Maximum contribution of actions to attention in one epoch")
    loneliness_keep_pct: int = rule(85, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of loneliness kept from epoch to epoch (%)")
    loneliness_son_threshold: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "If there are fewer active sons than this, the Creator grows lonely")
    loneliness_few_sons: int = rule(8, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Loneliness contribution per epoch of having few sons")
    loneliness_cult_relief: int = rule(4, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch decrease of loneliness for a Creator who has a cult")
    loneliness_no_cult: int = rule(6, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch loneliness increase for a Creator without a cult")
    loneliness_unanswered_cap: int = rule(10, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Maximum contribution of unanswered prayers to loneliness (1 per prayer)")
    unanswered_window_epochs: int = rule(
        8, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "Unanswered prayers older than this many epochs no longer add to the Creator's loneliness"
    )
    unanswered_decay_keep_pct: int = rule(
        75, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share (%) of an unanswered prayer's weight on loneliness kept for each epoch it waits"
    )
    wrath_disaster_severity: int = rule(80, 0, 300, RuleGroup.CREATOR_AND_ESSENCE, "Disaster severity of a wrath punishment (%)")
    wrath_event_severity_base: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Base severity of a wrath-punishment event")
    wrath_event_severity_die: int = rule(30, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "Severity die of a wrath-punishment event")
    wrath_discharge: int = rule(25, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Drop in wrath after a punishment descends")
    indifferent_threshold: int = rule(20, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Below this attention the Creator falls silent")
    indifferent_loyalty_loss: int = rule(4, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Loyalty loss of the silent Creator's sons")
    indifferent_ambition_gain: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Ambition gain of the silent Creator's sons")
    lonely_threshold: int = rule(70, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Loneliness at which the Creator sends a dream")
    lonely_discharge: int = rule(20, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Drop in loneliness after sending a dream")
    estranged_turn_chance: int = rule(8, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "A community estranged from its sons turns to the Creator (%)")
    estranged_content_threshold: int = rule(60, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Creator contentment that attracts the estranged more strongly")
    estranged_content_bonus_pct: int = rule(7, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Contribution of a content Creator to attracting the estranged (%)")
    prayer_faith_gain: int = rule(10, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Faith gain of a mortal whose prayer is answered")
    prayer_essence_per_stat: int = rule(3, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "Every this much essence given to a prayer adds 1 to stats")
    prayer_loneliness_relief: int = rule(10, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Loneliness reduction from answering a prayer")
    prayer_contentment: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Contribution of answering a prayer to contentment")
    sign_candidates: int = rule(4, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "The target of a spontaneous sign is picked by dice from this many best candidates")
    sign_exclusion_epochs: int = rule(
        3,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "A place struck by a spontaneous sign is not picked again for this many epochs (can still be picked if no candidate remains)",
    )
    wrath_battle_max: int = rule(4, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Most the epoch's battles and sieges add to wrath (saturates)")
    wrath_battle_half: int = rule(2, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "With this many battles the battle contribution is half the cap")
    wrath_blood_max: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Most the epoch's killings add to wrath (saturates)")
    wrath_blood_half: int = rule(2, 1, 1000, RuleGroup.CREATOR_AND_ESSENCE, "With this many killings the blood contribution is half the cap")
    wrath_leak_max: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Most the mean leak of the worlds adds to wrath (saturates)")
    wrath_leak_half: int = rule(15, 1, 100, RuleGroup.CREATOR_AND_ESSENCE, "At this mean leak the leak contribution is half the cap")
    temperament_wave: int = rule(
        8, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Per-epoch swing of the Creator's temperament (plus or minus; temperament pushes wrath and pulls contentment)"
    )
    temperament_keep_pct: int = rule(80, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of the temperament kept from epoch to epoch (%)")
    temperament_content_pct: int = rule(25, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of the temperament reflected inversely on contentment (%)")
    mood_jitter: int = rule(5, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Random per-epoch stir of wrath and contentment (plus or minus)")
    content_discharge: int = rule(15, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Drop in contentment after grace descends")
