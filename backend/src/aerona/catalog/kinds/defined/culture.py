from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.culture import CurseKind, ItemCategory, LanguageRegister, RumourChannel, SpeakerKind, SummonForm, Technique, TraditionFunction

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
            "Bloodthirst",
            checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.phases.made_things.afflict"),
            used_by=("engine.lore.items.CURSES",),
        ),
        CurseKind.MISFORTUNE: Defined(
            "Misfortune",
            checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.phases.made_things.afflict"),
            used_by=("engine.lore.items.curse_for",),
        ),
        CurseKind.WASTING: Defined(
            "Wasting", checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.MADNESS: Defined(
            "Madness", checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.BETRAYAL: Defined(
            "Betrayal", checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.phases.made_things.afflict"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.BARRENNESS: Defined(
            "Barrenness",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.TRANSFORMATION: Defined(
            "Transformation",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.SLEEP: Defined(
            "Sleep", checked_by=("engine.lore.curse_kinds.WIDER_CURSES",), used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES")
        ),
        CurseKind.SILENCE: Defined(
            "Silence",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.HUNGER: Defined(
            "Hunger", checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.curse_kinds.WIDER_CURSES"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.FORGETTING: Defined(
            "Forgetting",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.RESTLESSNESS: Defined(
            "Restlessness",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.LINE_CURSE: Defined(
            "Line curse",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.PLACE_CURSE: Defined(
            "Place curse",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.COMPULSION: Defined(
            "Compulsion",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
        ),
        CurseKind.AGING: Defined(
            "Aging", checked_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.curse_kinds.WIDER_CURSES"), used_by=("engine.lore.items.CURSES",)
        ),
        CurseKind.EXPOSURE: Defined(
            "Exposure",
            checked_by=("engine.lore.curse_kinds.WIDER_CURSES",),
            used_by=("engine.interconnect.catalog_lore.CURSE_RULES", "engine.lore.items.CURSES"),
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

TECHNIQUE = total(
    Technique,
    {
        Technique.PHALANX_DRILL: Defined(
            "Phalanx drill",
            checked_by=(),
            used_by=("catalog.techniques.TECHNIQUES", "catalog.techniques.UNIT_TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.HORSE_ARCHERY: Defined(
            "Horse archery", checked_by=(), used_by=("catalog.civics.TRIGGERS", "catalog.techniques.TECHNIQUES", "catalog.techniques.UNIT_TECHNIQUES")
        ),
        Technique.SIEGECRAFT: Defined(
            "Siegecraft",
            checked_by=(),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
                "engine.crafts.chemistry.RECIPES",
            ),
        ),
        Technique.FORTIFICATION: Defined(
            "Fortification",
            checked_by=("catalog.discovery.STRUCTURE_SUPERSEDED",),
            used_by=(
                "catalog.civics.TRIGGERS",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "engine.settlement.life.permitted",
                "engine.structures.needs.TECHNIQUE_GATES",
            ),
        ),
        Technique.LOGISTICS: Defined("Logistics", checked_by=(), used_by=("catalog.techniques.TECHNIQUES", "engine.military.logistics.advance")),
        Technique.HERBALISM: Defined(
            "Herbalism",
            checked_by=(),
            used_by=(
                "catalog.civics.TRIGGERS",
                "catalog.facets.FACETS",
                "catalog.law_depth.MEDICINE_TECHNIQUES",
                "catalog.medicine.MEDICINE",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.body.afflictions.other_cures",
                "engine.crafts.chemistry.RECIPES",
            ),
        ),
        Technique.SURGERY: Defined(
            "Surgery",
            checked_by=(),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.law_depth.MEDICINE_TECHNIQUES",
                "catalog.medicine.MEDICINE",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.AMPUTATION: Defined("Amputation", checked_by=(), used_by=("catalog.techniques.TECHNIQUES", "engine.body.healing.HealingWorld.care_for")),
        Technique.PROSTHETICS: Defined(
            "Prosthetics",
            checked_by=(),
            used_by=("catalog.discovery.ITEM_CLASSES", "catalog.medicine.MEDICINE", "catalog.techniques.TECHNIQUES", "engine.body.healing.fit_prosthesis"),
        ),
        Technique.QUARANTINE: Defined(
            "Quarantine", checked_by=(), used_by=("catalog.civics.TRIGGERS", "catalog.techniques.TECHNIQUES", "engine.polity.governance.law_effects")
        ),
        Technique.INOCULATION: Defined("Inoculation", checked_by=("engine.disease.book.DiseaseBook.load",), used_by=("catalog.techniques.TECHNIQUES",)),
        Technique.IRRIGATION: Defined(
            "Irrigation",
            checked_by=("engine.economy.extraction.craft_factor",),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.means.LIFTS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.environment.works.backfill_irrigation",
                "engine.settlement.life.waterside_of",
            ),
        ),
        Technique.CROP_ROTATION: Defined(
            "Crop rotation",
            checked_by=("engine.economy.extraction.craft_factor",),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.crafts.chemistry.RECIPES",
            ),
        ),
        Technique.TERRACING: Defined(
            "Terracing",
            checked_by=("engine.economy.extraction.craft_factor",),
            used_by=("catalog.facets.FACETS", "catalog.means.LIFTS", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.PLOUGH: Defined(
            "Plough",
            checked_by=("catalog.civics.SOCIAL_CHANGE", "engine.economy.extraction.craft_factor"),
            used_by=("catalog.methods.METHODS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.SELECTIVE_BREEDING: Defined(
            "Selective breeding",
            checked_by=("engine.economy.extraction.craft_factor",),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.BRONZE: Defined(
            "Bronze",
            checked_by=(),
            used_by=(
                "catalog.discovery.ITEM_MATERIALS",
                "catalog.eras.ERA_MARKERS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
                "engine.economy.refining.MATERIAL_TECHNIQUES",
            ),
        ),
        Technique.IRON: Defined(
            "Iron",
            checked_by=(),
            used_by=(
                "catalog.discovery.ITEM_CLASSES",
                "catalog.discovery.ITEM_MATERIALS",
                "catalog.eras.ERA_MARKERS",
                "catalog.means.LIFTS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
                "engine.economy.refining.MATERIAL_TECHNIQUES",
            ),
        ),
        Technique.STEEL: Defined(
            "Steel",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=(
                "catalog.discovery.ITEM_CLASSES",
                "catalog.discovery.ITEM_MATERIALS",
                "catalog.eras.ERA_MARKERS",
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
                "engine.crafts.clocks.LADDER",
                "engine.economy.refining.MATERIAL_TECHNIQUES",
            ),
        ),
        Technique.SKYSTEEL: Defined(
            "Skysteel",
            checked_by=("catalog.discovery.DANGEROUS_TECHNIQUES",),
            used_by=(
                "catalog.discovery.ITEM_MATERIALS",
                "catalog.techniques.TECHNIQUES",
                "engine.economy.refining.MATERIAL_TECHNIQUES",
                "engine.economy.refining.forged_material",
            ),
        ),
        Technique.ARCH: Defined(
            "Arch",
            checked_by=(),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.gatherings.STAGE_TECHNIQUES",
                "catalog.means.BUILDING",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.settlement.life.permitted",
                "engine.sites.digs.LOST_TECHNIQUES",
                "engine.structures.needs.TECHNIQUE_GATES",
            ),
        ),
        Technique.DOME: Defined(
            "Dome",
            checked_by=(),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.settlement.life.permitted",
                "engine.structures.needs.TECHNIQUE_GATES",
            ),
        ),
        Technique.AQUEDUCT: Defined(
            "Aqueduct",
            checked_by=("catalog.discovery.STRUCTURE_SUPERSEDED",),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.means.BUILDING",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.crafts.clocks.LADDER",
                "engine.settlement.life.permitted",
                "engine.structures.needs.TECHNIQUE_GATES",
            ),
        ),
        Technique.FORTRESS: Defined(
            "Fortress",
            checked_by=("catalog.discovery.STRUCTURE_SUPERSEDED",),
            used_by=("catalog.civics.TRIGGERS", "catalog.techniques.TECHNIQUES", "engine.settlement.life.permitted"),
        ),
        Technique.ALPHABET: Defined(
            "Alphabet",
            checked_by=(),
            used_by=(
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.communication.signals.KIND_TECHNIQUES",
                "engine.crafts.numbers.SCHOOLING",
                "engine.demography.peoples.culture_for",
                "engine.folk_knowledge.seed.transmission_of",
            ),
        ),
        Technique.PAPER: Defined(
            "Paper",
            checked_by=("engine.means.media.medium_for",),
            used_by=(
                "catalog.discovery.ITEM_CLASSES",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "engine.communication.signals.KIND_TECHNIQUES",
                "engine.lore.research.read_books",
                "engine.phases.culture_exchange._diffuse_direction",
            ),
        ),
        Technique.PRINTING: Defined(
            "Printing",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=(
                "catalog.facets.FACETS",
                "catalog.money.MONEY_FORMS",
                "catalog.techniques.TECHNIQUES",
                "engine.communication.opinion.voice",
                "engine.couplings.registers.sociolects",
                "engine.lore.art.art_year",
                "engine.lore.printing.PRINTED",
            ),
        ),
        Technique.CRYPTOGRAPHY: Defined(
            "Cryptography",
            checked_by=(),
            used_by=("catalog.techniques.TECHNIQUES", "engine.communication.ciphers.tend_ciphers", "engine.communication.signals.KIND_TECHNIQUES"),
        ),
        Technique.CALENDAR: Defined(
            "Calendar",
            checked_by=(),
            used_by=(
                "catalog.civics.TRIGGERS",
                "catalog.techniques.TECHNIQUES",
                "engine.collective.dating.reform",
                "engine.crafts.clocks.LADDER",
                "engine.lore.traditions.celebrate",
            ),
        ),
        Technique.NAVIGATION_STARS: Defined(
            "Navigation stars",
            checked_by=("engine.economy.routes.spoken_capacity",),
            used_by=("catalog.facets.FACETS", "catalog.means.AIDS", "catalog.techniques.TECHNIQUES", "engine.crafts.clocks.LADDER"),
        ),
        Technique.ECLIPSE_PREDICTION: Defined(
            "Eclipse prediction",
            checked_by=(),
            used_by=(
                "catalog.civics.TRIGGERS",
                "catalog.techniques.TECHNIQUES",
                "engine.climes.shifts.SKY_READING",
                "engine.cosmos.impacts.foreseers",
                "engine.phases.sky._eclipse",
            ),
        ),
        Technique.SAILING: Defined(
            "Sailing",
            checked_by=(),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.civics.TRIGGERS",
                "catalog.facets.FACETS",
                "catalog.means.AIDS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.SHIPWRIGHTING: Defined("Shipwrighting", checked_by=(), used_by=("catalog.techniques.TECHNIQUES", "catalog.vehicles.FAMILY_TECHNIQUES")),
        Technique.COINAGE: Defined(
            "Coinage",
            checked_by=(),
            used_by=(
                "catalog.discovery.ITEM_CLASSES",
                "catalog.money.MONEY_FORMS",
                "catalog.taxes.TAXES",
                "catalog.techniques.TECHNIQUES",
                "engine.economy.money.mint",
            ),
        ),
        Technique.BANKING: Defined(
            "Banking",
            checked_by=(
                "catalog.civics.SOCIAL_CHANGE",
                "catalog.discovery.STRUCTURE_SUPERSEDED",
                "engine.orders.exchange.banking_between",
                "engine.orders.savings.bank_in",
            ),
            used_by=(
                "catalog.civics.CAPABILITIES",
                "catalog.civics.LAW_GATES",
                "catalog.civics.TRIGGERS",
                "catalog.techniques.INSTITUTIONS",
                "catalog.techniques.TECHNIQUES",
                "engine.economy.money.banks",
                "engine.phases.factions.FINANCE",
            ),
        ),
        Technique.WARDING: Defined(
            "Warding",
            checked_by=(),
            used_by=(
                "catalog.gatherings.STAGE_TECHNIQUES",
                "catalog.preservation.PRESERVATION",
                "catalog.techniques.TECHNIQUES",
                "engine.lore.rites.SCHOOL_TECHNIQUES",
                "engine.sites.digs.LOST_TECHNIQUES",
            ),
        ),
        Technique.SUMMONING: Defined(
            "Summoning",
            checked_by=("catalog.discovery.DANGEROUS_TECHNIQUES",),
            used_by=("catalog.carriers.CARRIERS", "catalog.techniques.TECHNIQUES", "catalog.techniques.UNIT_TECHNIQUES", "engine.lore.rites.SCHOOL_TECHNIQUES"),
        ),
        Technique.SKY_SAILING: Defined(
            "Sky sailing", checked_by=(), used_by=("catalog.techniques.TECHNIQUES", "catalog.techniques.UNIT_TECHNIQUES", "catalog.vehicles.FAMILY_TECHNIQUES")
        ),
        Technique.NECROMANCY: Defined(
            "Necromancy",
            checked_by=("catalog.civics.SOCIAL_CHANGE", "catalog.discovery.DANGEROUS_TECHNIQUES"),
            used_by=("catalog.techniques.TECHNIQUES", "engine.lore.rites.SCHOOL_TECHNIQUES"),
        ),
        Technique.ALCHEMY: Defined(
            "Alchemy",
            checked_by=("engine.lore.dangers.accidents",),
            used_by=(
                "catalog.discovery.ITEM_CLASSES",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
                "engine.communication.signals.KIND_TECHNIQUES",
                "engine.crafts.chemistry.RECIPES",
                "engine.sites.digs.LOST_TECHNIQUES",
            ),
        ),
        Technique.ASTRONOMY_INSTRUMENTS: Defined(
            "Astronomy instruments",
            checked_by=("catalog.discovery.STRUCTURE_SUPERSEDED", "engine.economy.routes.spoken_capacity"),
            used_by=(
                "catalog.discovery.ITEM_CLASSES",
                "catalog.facets.FACETS",
                "catalog.means.AIDS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "catalog.vehicles.FAMILY_TECHNIQUES",
                "engine.climes.shifts.SKY_READING",
                "engine.crafts.aids.LENSES",
                "engine.crafts.clocks.LADDER",
                "engine.sites.digs.LOST_TECHNIQUES",
            ),
        ),
        Technique.CARTOGRAPHY: Defined(
            "Cartography",
            checked_by=("engine.environment.knowledge.cartographers",),
            used_by=(
                "catalog.civics.CAPABILITIES",
                "catalog.civics.TRIGGERS",
                "catalog.discovery.ITEM_CLASSES",
                "catalog.facets.FACETS",
                "catalog.gatherings.STAGE_TECHNIQUES",
                "catalog.means.AIDS",
                "catalog.techniques.TECHNIQUES",
                "engine.sites.digs.LOST_TECHNIQUES",
            ),
        ),
        Technique.ORAL_LAW: Defined("Oral law", checked_by=(), used_by=("catalog.techniques.TECHNIQUES", "engine.polity.trials.weigh")),
        Technique.WRITTEN_LAW: Defined(
            "Written law",
            checked_by=(),
            used_by=(
                "catalog.civics.GOVERNMENT_GATES",
                "catalog.civics.LAW_GATES",
                "catalog.civics.OFFICE_GATES",
                "catalog.civics.TENET_GATES",
                "catalog.civics.TRIGGERS",
                "catalog.facets.FACETS",
                "catalog.law_depth.CODE_TECHNIQUES",
                "catalog.taxes.TAXES",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.polity.formation.LITERATE_RULE",
                "engine.regime.learning.license_holders",
                "engine.regime.rule.LAW_TECHNIQUES",
                "engine.regime.rule.charisma_turned",
                "engine.sites.digs.LOST_TECHNIQUES",
            ),
        ),
        Technique.CODIFIED_LAW: Defined(
            "Codified law",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=(
                "catalog.civics.LAW_GATES",
                "catalog.civics.PRIVILEGE_GATES",
                "catalog.civics.TRIGGERS",
                "catalog.law_depth.CODE_TECHNIQUES",
                "catalog.techniques.TECHNIQUES",
                "engine.regime.rule.LAW_TECHNIQUES",
            ),
        ),
        Technique.BUREAUCRACY: Defined(
            "Bureaucracy",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=(
                "catalog.civics.GOVERNMENT_GATES",
                "catalog.facets.FACETS",
                "catalog.taxes.TAXES",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.crafts.numbers.SCHOOLING",
                "engine.polity.revenue.breed_corruption",
                "engine.regime.patronage.institutional_strength",
                "engine.regime.rule.charisma_turned",
                "engine.regime.rule.legitimacy_targets",
            ),
        ),
        Technique.CENSUS: Defined(
            "Census",
            checked_by=(),
            used_by=("catalog.taxes.TAXES", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES", "engine.sacred.foresight.counts"),
        ),
        Technique.POSTAL_SERVICE: Defined(
            "Postal service",
            checked_by=("engine.lore.research_depth.draw_options",),
            used_by=("catalog.techniques.TECHNIQUES", "engine.communication.post.posted", "engine.networks.backfill.post_relays"),
        ),
        Technique.DIPLOMATIC_CORPS: Defined("Diplomatic corps", checked_by=(), used_by=("catalog.civics.OFFICE_GATES", "catalog.techniques.TECHNIQUES")),
        Technique.STANDING_ARMY_ADMIN: Defined("Standing army admin", checked_by=(), used_by=("catalog.civics.LAW_GATES", "catalog.techniques.TECHNIQUES")),
        Technique.DOUBLE_ENTRY: Defined(
            "Double entry",
            checked_by=(),
            used_by=(
                "catalog.civics.TENET_GATES",
                "catalog.civics.TRIGGERS",
                "catalog.money.MONEY_FORMS",
                "catalog.taxes.TAXES",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.crafts.numbers.SCHOOLING",
            ),
        ),
        Technique.JOINT_STOCK: Defined(
            "Joint stock",
            checked_by=("catalog.civics.SOCIAL_CHANGE", "engine.economy.routes.spoken_capacity"),
            used_by=("catalog.taxes.TAXES", "catalog.techniques.TECHNIQUES", "engine.phases.factions.FINANCE"),
        ),
        Technique.INSURANCE: Defined(
            "Insurance", checked_by=("engine.economy.routes.carry",), used_by=("catalog.techniques.TECHNIQUES", "engine.crafts.insurance.knows_insurance")
        ),
        Technique.GUILDS: Defined(
            "Guilds",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=(
                "catalog.civics.LAW_GATES",
                "catalog.civics.PRIVILEGE_GATES",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "engine.lore.blueprints.trade_designs",
            ),
        ),
        Technique.UNIVERSITIES: Defined(
            "Universities",
            checked_by=("catalog.civics.CAPABILITY_INSTITUTIONS", "catalog.civics.SOCIAL_CHANGE", "catalog.discovery.STRUCTURE_SUPERSEDED"),
            used_by=("catalog.techniques.TECHNIQUES", "engine.crafts.numbers.SCHOOLING"),
        ),
        Technique.HOSPITALS: Defined(
            "Hospitals",
            checked_by=("catalog.discovery.STRUCTURE_SUPERSEDED", "engine.disease.book.DiseaseBook.load"),
            used_by=("catalog.civics.TRIGGERS", "catalog.facets.FACETS", "catalog.medicine.MEDICINE", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.PRINTING_PRESS: Defined(
            "Printing press",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=("catalog.eras.ERA_MARKERS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES", "engine.lore.printing.PRINTED"),
        ),
        Technique.ORGANISED_CLERGY: Defined(
            "Organised clergy",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=(
                "catalog.civics.CAPABILITIES",
                "catalog.civics.GOVERNMENT_GATES",
                "catalog.taxes.TAXES",
                "catalog.techniques.TECHNIQUES",
                "engine.crafts.clocks.LADDER",
                "engine.regime.learning.ordain",
            ),
        ),
        Technique.MONASTICISM: Defined(
            "Monasticism",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=("catalog.techniques.TECHNIQUES", "engine.lore.research.read_books", "engine.sacred.mysteries.contemplative"),
        ),
        Technique.THEOLOGY_SCHOOLS: Defined("Theology schools", checked_by=(), used_by=("catalog.techniques.TECHNIQUES", "engine.faith.zeal.zeal_parts")),
        Technique.LOGIC: Defined(
            "Logic",
            checked_by=(),
            used_by=(
                "catalog.civics.CAPABILITIES",
                "catalog.civics.OFFICE_GATES",
                "catalog.civics.TENET_GATES",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.crafts.numbers.keep_numbers",
            ),
        ),
        Technique.NATURAL_PHILOSOPHY: Defined(
            "Natural philosophy", checked_by=("engine.lore.research.thought_factor",), used_by=("catalog.facets.FACETS", "catalog.techniques.TECHNIQUES")
        ),
        Technique.EMPIRICISM: Defined(
            "Empiricism",
            checked_by=("catalog.civics.SOCIAL_CHANGE", "engine.lore.research.thought_factor"),
            used_by=("catalog.facets.FACETS", "catalog.medicine.MEDICINE", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.HUMANIST_IDEALS: Defined(
            "Humanist ideals",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=("catalog.civics.LAW_GATES", "catalog.civics.TENET_GATES", "catalog.facets.FACETS", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.EXAMINATIONS: Defined(
            "Examinations",
            checked_by=("catalog.civics.SOCIAL_CHANGE",),
            used_by=("catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES", "engine.regime.learning.exam_row"),
        ),
        Technique.DRAINAGE: Defined(
            "Drainage",
            checked_by=("engine.agrarian.soil.field_work",),
            used_by=("catalog.facets.FACETS", "catalog.means.LIFTS", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.GUNPOWDER: Defined(
            "Gunpowder",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.ERA_MARKERS",
                "catalog.eras.POWDER",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.FIREARMS: Defined(
            "Firearms",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.POWDER",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.CANNON: Defined(
            "Cannon",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.POWDER",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
            ),
        ),
        Technique.STAR_FORTS: Defined(
            "Star forts",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.POWDER", "catalog.eras.TECHNIQUE_ERAS", "catalog.facets.FACETS", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.VOLLEY_DRILL: Defined(
            "Volley drill",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.POWDER", "catalog.eras.TECHNIQUE_ERAS", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.STEAM_POWER: Defined(
            "Steam power",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.ERA_MARKERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.means.LIFTS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.phases.factions.ENGINEERING",
            ),
        ),
        Technique.COKE_SMELTING: Defined(
            "Coke smelting",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.MACHINE_TOOLS: Defined(
            "Machine tools",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.military.sabotage.has_machines",
                "engine.phases.factions.ENGINEERING",
            ),
        ),
        Technique.RAILWAYS: Defined(
            "Railways",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.cosmos.routes.VEHICLE_TECHNIQUES",
                "engine.phases.factions.ENGINEERING",
            ),
        ),
        Technique.STEAMSHIPS: Defined(
            "Steamships",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.FACTORY_PRODUCTION: Defined(
            "Factory production",
            checked_by=("catalog.eras.ERA_EFFECTS", "engine.phases.factions.industrial_kinds"),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.facets.FACETS", "catalog.techniques.TECHNIQUES", "engine.orders.putting_out.work_put_out"),
        ),
        Technique.INDUSTRIAL_CHEMISTRY: Defined(
            "Industrial chemistry",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.medicine.MEDICINE",
                "catalog.methods.METHODS",
                "catalog.taxes.TAXES",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.CANNED_FOOD: Defined(
            "Canned food",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.methods.METHODS", "catalog.preservation.PRESERVATION", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.VACCINES: Defined(
            "Vaccines",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.medicine.MEDICINE", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.ELECTRICITY: Defined(
            "Electricity",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.ERA_MARKERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.money.MONEY_FORMS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.TELEGRAPH: Defined(
            "Telegraph",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.communication.signals.KIND_TECHNIQUES",
            ),
        ),
        Technique.TELEPHONE: Defined(
            "Telephone", checked_by=("catalog.eras.ERA_EFFECTS",), used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.techniques.TECHNIQUES")
        ),
        Technique.ELECTRIC_LIGHT: Defined(
            "Electric light",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.facets.FACETS", "catalog.methods.METHODS", "catalog.techniques.TECHNIQUES"),
        ),
        Technique.REFRIGERATION: Defined(
            "Refrigeration",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.preservation.PRESERVATION",
                "catalog.techniques.TECHNIQUES",
            ),
        ),
        Technique.COMBUSTION_ENGINE: Defined(
            "Combustion engine",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.cosmos.routes.VEHICLE_TECHNIQUES",
            ),
        ),
        Technique.AVIATION: Defined(
            "Aviation",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.cosmos.routes.VEHICLE_TECHNIQUES",
            ),
        ),
        Technique.COMPUTATION: Defined(
            "Computation",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.ERA_MARKERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.money.MONEY_FORMS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.RADIO: Defined(
            "Radio",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.techniques.TECHNIQUES",
                "catalog.techniques.UNIT_TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.agrarian.lands.commons_kinds",
                "engine.communication.signals.KIND_TECHNIQUES",
            ),
        ),
        Technique.MASS_MEDIA: Defined(
            "Mass media",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.ANTIBIOTICS: Defined(
            "Antibiotics",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.medicine.MEDICINE", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.GREEN_REVOLUTION: Defined(
            "Green revolution",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.facets.FACETS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.NUCLEAR_POWER: Defined(
            "Nuclear power",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.eras.ERA_MARKERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.facets.FACETS",
                "catalog.methods.METHODS",
                "catalog.preservation.PRESERVATION",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
            ),
        ),
        Technique.NUCLEAR_WEAPONS: Defined(
            "Nuclear weapons",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=("catalog.eras.TECHNIQUE_ERAS", "catalog.techniques.TECHNIQUES", "catalog.technology.FAMILY_TECHNIQUES"),
        ),
        Technique.ROCKETRY: Defined(
            "Rocketry",
            checked_by=("catalog.eras.ERA_EFFECTS", "engine.eras.progress.finish"),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.methods.METHODS",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.agrarian.lands.commons_kinds",
            ),
        ),
        Technique.GENETIC_ENGINEERING: Defined(
            "Genetic engineering",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.medicine.MEDICINE",
                "catalog.methods.METHODS",
                "catalog.preservation.PRESERVATION",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.communication.signals.KIND_TECHNIQUES",
                "engine.cosmos.routes.VEHICLE_TECHNIQUES",
                "engine.living.lines.CRAFTS",
            ),
        ),
        Technique.ARTIFICIAL_MINDS: Defined(
            "Artificial minds",
            checked_by=("catalog.eras.ERA_EFFECTS",),
            used_by=(
                "catalog.carriers.CARRIERS",
                "catalog.eras.TECHNIQUE_ERAS",
                "catalog.medicine.MEDICINE",
                "catalog.techniques.TECHNIQUES",
                "catalog.technology.FAMILY_TECHNIQUES",
                "engine.communication.signals.KIND_TECHNIQUES",
                "engine.cosmos.routes.VEHICLE_TECHNIQUES",
                "engine.polity.trials.trial_open",
            ),
        ),
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
