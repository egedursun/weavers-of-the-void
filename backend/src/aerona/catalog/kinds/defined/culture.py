from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.culture import CurseKind, ItemCategory, LanguageRegister, RumourChannel, SpeakerKind, SummonForm, TraditionFunction

CURSE_KIND = total(
    CurseKind,
    {
        CurseKind.NONE: Defined(
            "None",
            checked_by=("engine.folkways.purity.cursed_bearer", "engine.lore.items.item_year", "engine.phases.made_things.afflict"),
            used_by=(
                "db.tables.culture.ItemProfileRow",
                "engine.ecology.beasts.trophy",
                "engine.faith.works.bones_of",
                "engine.lore.creation.seed_item",
                "engine.lore.items.profile_of",
            ),
        ),
        CurseKind.BLOODTHIRST: Defined(
            "Bloodthirst", checked_by=("catalog.life.interconnect.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.MISFORTUNE: Defined(
            "Misfortune", checked_by=("catalog.life.interconnect.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.curse_for",)
        ),
        CurseKind.WASTING: Defined(
            "Wasting", checked_by=("catalog.life.interconnect.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.MADNESS: Defined(
            "Madness", checked_by=("catalog.life.interconnect.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.BETRAYAL: Defined(
            "Betrayal", checked_by=("catalog.life.interconnect.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.BARRENNESS: Defined(
            "Barrenness", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.barren", "engine.lore.items.CURSES")
        ),
        CurseKind.TRANSFORMATION: Defined(
            "Transformation", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.transform", "engine.lore.items.CURSES")
        ),
        CurseKind.SLEEP: Defined(
            "Sleep", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.sleep", "engine.lore.items.CURSES")
        ),
        CurseKind.SILENCE: Defined(
            "Silence", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.silence", "engine.lore.items.CURSES")
        ),
        CurseKind.HUNGER: Defined(
            "Hunger", checked_by=("catalog.life.interconnect.CURSE_RULES",), used_by=("engine.lore.curse_kinds.hunger", "engine.lore.items.CURSES")
        ),
        CurseKind.FORGETTING: Defined(
            "Forgetting", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.forget", "engine.lore.items.CURSES")
        ),
        CurseKind.RESTLESSNESS: Defined(
            "Restlessness", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.wander", "engine.lore.items.CURSES")
        ),
        CurseKind.LINE_CURSE: Defined(
            "Line curse", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.curse_line", "engine.lore.items.CURSES")
        ),
        CurseKind.PLACE_CURSE: Defined(
            "Place curse", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.curse_place", "engine.lore.items.CURSES")
        ),
        CurseKind.COMPULSION: Defined(
            "Compulsion", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.compel", "engine.lore.items.CURSES")
        ),
        CurseKind.AGING: Defined(
            "Aging", checked_by=("catalog.life.interconnect.CURSE_RULES",), used_by=("engine.lore.curse_kinds.age", "engine.lore.items.CURSES")
        ),
        CurseKind.EXPOSURE: Defined(
            "Exposure", checked_by=(), used_by=("catalog.life.interconnect.CURSE_RULES", "engine.lore.curse_kinds.lay_bare", "engine.lore.items.CURSES")
        ),
    },
)

ITEM_CATEGORY = total(
    ItemCategory,
    {
        ItemCategory.WEAPON: Defined("Weapon", checked_by=(), used_by=()),
        ItemCategory.ARMOUR: Defined("Armour", checked_by=(), used_by=()),
        ItemCategory.SHIELD: Defined("Shield", checked_by=(), used_by=()),
        ItemCategory.TOOL: Defined("Tool", checked_by=(), used_by=()),
        ItemCategory.JEWELLERY: Defined("Jewellery", checked_by=(), used_by=()),
        ItemCategory.SACRED_RELIC: Defined("Sacred relic", checked_by=(), used_by=()),
        ItemCategory.INSTRUMENT: Defined("Instrument", checked_by=(), used_by=()),
        ItemCategory.BOOK: Defined("Book", checked_by=(), used_by=()),
    },
)

LANGUAGE_REGISTER = total(
    LanguageRegister,
    {
        LanguageRegister.COURT: Defined(
            "Court", checked_by=(), used_by=("engine.lore.language.derive_registers", "engine.lore.names.misreadings", "engine.polity.accords.misread")
        ),
        LanguageRegister.COMMON: Defined("Common", checked_by=(), used_by=("engine.lore.language.derive_registers", "engine.lore.language.register_barrier")),
        LanguageRegister.LITURGICAL: Defined(
            "Liturgical", checked_by=(), used_by=("engine.lore.language.derive_registers", "engine.phases.religion_spread.preaching_barrier")
        ),
        LanguageRegister.TRADE: Defined(
            "Trade",
            checked_by=(),
            used_by=("engine.demography.tongues.trade_barrier", "engine.demography.tongues.trade_tongue", "engine.lore.language.derive_registers"),
        ),
    },
)

RUMOUR_CHANNEL = total(
    RumourChannel,
    {
        RumourChannel.WITNESS: Defined(
            "Seen with their own eyes",
            checked_by=("engine.lore.rumours.atrocity_heard",),
            used_by=("db.tables.culture.RumourRow", "engine.lore.rumours.seed", "tools.mortal.events.recount"),
        ),
        RumourChannel.ROUTE: Defined("Down the trade road", checked_by=("engine.lore.rumours.CHANCES",), used_by=("engine.lore.rumours.Links.of",)),
        RumourChannel.PILGRIMAGE: Defined("From pilgrims", checked_by=("engine.lore.rumours.CHANCES",), used_by=("engine.lore.rumours.Links.of",)),
        RumourChannel.JOURNEY: Defined("Brought by travellers", checked_by=("engine.lore.rumours.CHANCES",), used_by=("engine.lore.rumours.Links.of",)),
        RumourChannel.SPY: Defined(
            "Reported by spies", checked_by=("engine.lore.rumours.CHANCES", "engine.lore.rumours.fidelity_after"), used_by=("engine.lore.rumours.Links.of",)
        ),
        RumourChannel.CURRENT: Defined("Carried by the current", checked_by=("engine.lore.rumours.CHANCES",), used_by=("engine.lore.rumours.Links.of",)),
        RumourChannel.PLANTED: Defined("Planted by you", checked_by=(), used_by=("engine.lore.rumours.plant", "tools.son.events.retell_event")),
    },
)

SPEAKER_KIND = total(
    SpeakerKind,
    {
        SpeakerKind.NATIVE: Defined("Native", checked_by=(), used_by=("engine.climes.crossings.speak_lingua", "engine.phases.lore.cohorts")),
        SpeakerKind.SECOND: Defined(
            "Second",
            checked_by=("engine.phases.language_death.living_speakers", "engine.phases.lore.cohorts", "engine.tongues.pidgins.creolise"),
            used_by=(
                "engine.climes.crossings.speak_lingua",
                "engine.lore.language.learn_second",
                "engine.tongues.policy.suppress",
                "services.player.culture.SpeakerTarget",
                "services.player.lore.Speakers",
            ),
        ),
        SpeakerKind.LITURGICAL: Defined(
            "Liturgical", checked_by=(), used_by=("engine.phases.lore.cohorts", "engine.tongues.policy.liturgy", "tools.mortal.ways_of_rule.TongueInput")
        ),
    },
)

SUMMON_FORM = total(
    SummonForm,
    {
        SummonForm.SPIRIT: Defined("Spirit", checked_by=(), used_by=()),
        SummonForm.BEAST: Defined("Beast", checked_by=("engine.lore.rites.do_summon",), used_by=()),
        SummonForm.UNDEAD: Defined("Undead", checked_by=("engine.lore.rites.do_summon",), used_by=()),
        SummonForm.PERSON: Defined("Person", checked_by=(), used_by=()),
        SummonForm.MADE_THING: Defined("Made thing", checked_by=(), used_by=()),
        SummonForm.OUTER_BEING: Defined("Outer being", checked_by=(), used_by=()),
        SummonForm.ASPECT: Defined("Aspect", checked_by=(), used_by=()),
        SummonForm.PHENOMENON: Defined("Phenomenon", checked_by=(), used_by=()),
        SummonForm.DOUBLE: Defined("Double", checked_by=(), used_by=()),
    },
)

TRADITION_FUNCTION = total(
    TraditionFunction,
    {
        TraditionFunction.FESTIVAL: Defined(
            "Festival",
            checked_by=("engine.gatherings.occasions.festivals", "engine.lore.calendar_rites.SEASON_OF", "engine.phases.lore.DEFIED_BY"),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.cosmos.features.festival",
                "engine.ecology.totems.found_totem",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.backfill.backfill_traditions",
                "engine.lore.traditions.FEASTS",
                "engine.lore.traditions.commemorate",
                "engine.lore.traditions.profile_of",
                "engine.lore.traditions.remember_miracles",
                "engine.mind.feelings.FEASTS",
                "engine.phases.lore.CREED_DEFIES",
                "tools.mortal.production.seed_culture",
                "tools.son.creation_effects.seed_lore_kinds",
            ),
        ),
        TraditionFunction.FAST: Defined(
            "Fast",
            checked_by=("engine.lore.calendar_rites.SEASON_OF",),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.folkways.nutrition.derive_diet",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.calendar_rites.fast_season",
                "engine.lore.calendar_rites.found_fast",
                "engine.phases.lore.CREED_DEFIES",
            ),
        ),
        TraditionFunction.RITE_OF_PASSAGE: Defined(
            "Rite of passage",
            checked_by=(
                "catalog.lore.tradition_spec",
                "engine.faith.backfill.funeral_rites",
                "engine.faith.judgement.funeral_custom",
                "engine.lore.backfill.backfill_traditions",
                "engine.lore.calendar_rites.SEASON_OF",
                "engine.lore.creation.seed_tradition",
                "engine.phases.lore.defied",
                "tools.son.creation_effects.keep_rite",
            ),
            used_by=(
                "catalog.lore.STAGES",
                "catalog.lore.TRADITIONS",
                "engine.body.customs.SEER_RITES",
                "engine.demography.rites.rite_tradition",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.traditions.FEASTS",
                "engine.phases.lore.CREED_DEFIES",
                "tools.son.creation_effects.keep_rite",
            ),
        ),
        TraditionFunction.TABOO: Defined(
            "Taboo",
            checked_by=(
                "engine.lore.traditions._taboos",
                "engine.lore.traditions.profile_of",
                "engine.lore.traditions.taboo_keepers",
                "engine.mind.preferences.kept_taboo",
            ),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.taboos.forbidden",
                "engine.lore.taboos.violated",
                "engine.lore.taboos.winter_rest",
                "engine.mind.preferences.make_taboos",
                "engine.phases.lore.CREED_DEFIES",
                "engine.tongues.meaning.holy",
                "engine.tongues.meaning.lift_names",
            ),
        ),
        TraditionFunction.OFFERING: Defined(
            "Offering",
            checked_by=("engine.lore.calendar_rites.SEASON_OF", "engine.phases.lore.DEFIED_BY"),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.body.customs.SEER_RITES",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.traditions.GIFTS",
                "engine.phases.lore.CREED_DEFIES",
            ),
        ),
        TraditionFunction.PILGRIMAGE: Defined(
            "Pilgrimage",
            checked_by=("engine.lore.calendar_rites.SEASON_OF", "engine.phases.lore.DEFIED_BY"),
            used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS", "engine.lore.traditions.GIFTS", "engine.phases.lore.CREED_DEFIES"),
        ),
        TraditionFunction.HOSPITALITY: Defined(
            "Hospitality",
            checked_by=("engine.environment.dangers._bandits", "engine.phases.lore.DEFIED_BY"),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.gatherings.hold.massacre_chance",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.taboos.guest_killed",
                "engine.phases.lore.CREED_DEFIES",
            ),
        ),
        TraditionFunction.DUEL_CUSTOM: Defined(
            "Duel custom",
            checked_by=("engine.phases.lore.DEFIED_BY",),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.phases.lore.CREED_DEFIES",
                "engine.phases.vendettas.honour_duels",
            ),
        ),
        TraditionFunction.MOURNING: Defined(
            "Mourning",
            checked_by=("engine.lore.calendar_rites.SEASON_OF", "engine.lore.traditions.commemorate"),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.traditions.commemorate",
                "engine.lore.traditions.remember_years",
                "engine.mind.grief.MOURNING_TRADITIONS",
            ),
        ),
        TraditionFunction.SEASONAL_RITE: Defined(
            "Seasonal rite",
            checked_by=("engine.lore.calendar_rites.SEASON_OF",),
            used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS", "engine.lore.traditions.FEASTS", "engine.mind.feelings.FEASTS"),
        ),
        TraditionFunction.MARTIAL_DISPLAY: Defined(
            "Martial display",
            checked_by=("engine.lore.calendar_rites.SEASON_OF",),
            used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS", "engine.phases.lore.CREED_DEFIES"),
        ),
        TraditionFunction.BODY_MARKING: Defined(
            "Body marking",
            checked_by=("engine.phases.lore.DEFIED_BY",),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.body.customs.SEER_RITES",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.traditions.SCARRING",
                "engine.phases.lore.CREED_DEFIES",
            ),
        ),
        TraditionFunction.ANCESTRAL_RITE: Defined(
            "Ancestral rite",
            checked_by=("engine.lore.calendar_rites.SEASON_OF", "engine.phases.lore.DEFIED_BY"),
            used_by=(
                "catalog.lore.TRADITIONS",
                "engine.lore.backfill.TRADITION_WORDS",
                "engine.lore.traditions.FEASTS",
                "engine.mind.feelings.FEASTS",
                "engine.phases.lore.CREED_DEFIES",
            ),
        ),
        TraditionFunction.REST_CUSTOM: Defined(
            "Rest custom",
            checked_by=("engine.lore.calendar_rites.SEASON_OF", "engine.lore.calendar_rites.SLEEP_BODIES", "engine.lore.calendar_rites.SLEEP_NAMES"),
            used_by=("catalog.lore.TRADITIONS", "engine.lore.calendar_rites.SLEEP_CUSTOMS", "engine.lore.calendar_rites.found_sleep_customs"),
        ),
        TraditionFunction.VIGIL: Defined(
            "Vigil",
            checked_by=("engine.lore.calendar_rites.SEASON_OF", "engine.lore.calendar_rites.SLEEP_BODIES", "engine.lore.calendar_rites.SLEEP_NAMES"),
            used_by=("catalog.lore.TRADITIONS", "engine.lore.calendar_rites.SLEEP_CUSTOMS", "engine.lore.calendar_rites.found_sleep_customs"),
        ),
        TraditionFunction.GIFT_CUSTOM: Defined(
            "Gift custom", checked_by=("engine.lore.calendar_rites.SEASON_OF",), used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS")
        ),
        TraditionFunction.PURIFICATION: Defined(
            "Purification", checked_by=("engine.lore.calendar_rites.SEASON_OF",), used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS")
        ),
        TraditionFunction.COMMEMORATION: Defined(
            "Commemoration", checked_by=("engine.lore.calendar_rites.SEASON_OF",), used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS")
        ),
        TraditionFunction.COMPETITION: Defined(
            "Competition", checked_by=("engine.lore.calendar_rites.SEASON_OF",), used_by=("catalog.lore.TRADITIONS", "engine.lore.backfill.TRADITION_WORDS")
        ),
    },
)
