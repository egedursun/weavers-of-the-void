from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.culture import ItemCategory, LanguageRegister, RumourChannel, SpeakerKind, SummonForm

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
