from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

PEOPLE_SECTION = "section-people-profile"
FOUNDING_SURFACE = "FoundPeople"
BACKFILL = "peoples.depth_backfill: every people's body, size, traits, diet, immunities, tongues, funeral rite and battle record derived as if always so"
BIOLOGY = (PeopleBiologyRow.__tablename__,)
CULTURE = (PeopleCultureRow.__tablename__,)

PEOPLE_MECHANICS = (
    Mechanic(
        key="people_kin",
        spec_item="S4.1",
        title="Body plan, size, natural traits and diet of a people",
        subsystem=Subsystem.DEMOGRAPHY,
        phases=("population_growth", "labour_allocation", "campaigns", "people_cycles"),
        surface=Surface(drawer=PEOPLE_SECTION),
        backfill=BACKFILL,
        fields=("body_plan", "size_class", "traits", "diet", "staple", "edible"),
        tables=BIOLOGY,
        exposure=Exposure.CONTEXT,
        targets=("people", "settlement", "mortal"),
        couplings=(
            Coupling(Subsystem.ECONOMY, "big bodies and odd diets eat more of the land's food", EdgeKind.MODIFIER, "biology.food_need_pct"),
            Coupling(Subsystem.DEMOGRAPHY, "large folk crowd a land sooner, burrowers and hives later", EdgeKind.MODIFIER, "biology.footprint_pct"),
            Coupling(Subsystem.ECONOMY, "the body sets which work a people does well", EdgeKind.MODIFIER, "biology.labour_pct"),
            Coupling(Subsystem.WAR, "size, form and natural gifts weigh in every battle", EdgeKind.MODIFIER, "biology.battle_pct"),
            Coupling(Subsystem.WAR, "who can ride, who is the mount, who flies and who swims sets the levy", EdgeKind.RULE_SWITCH, "biology.naval_pct"),
        ),
    ),
    Mechanic(
        key="people_climate_immunity",
        spec_item="S4.1",
        title="Climate acclimatisation and the immunity of a homeland",
        subsystem=Subsystem.ENVIRONMENT,
        phases=("campaigns", "famine_migration", "epidemics", "people_cycles"),
        surface=Surface(drawer=PEOPLE_SECTION),
        backfill=BACKFILL,
        fields=("acclimatised", "immunities"),
        tables=BIOLOGY,
        targets=("people", "settlement"),
        couplings=(
            Coupling(Subsystem.WAR, "cold peoples suffer heat attrition in southern campaigns", EdgeKind.RULE_SWITCH, "biology.climate_tolerance_bands"),
            Coupling(Subsystem.DEMOGRAPHY, "migrants shun lands of a foreign climate", EdgeKind.MODIFIER, "biology.climate_penalty_pct"),
            Coupling(Subsystem.DEMOGRAPHY, "diseases of the homeland kill fewer of its own folk", EdgeKind.MODIFIER, "biology.homeland_immunity_pct"),
        ),
    ),
    Mechanic(
        key="folk_customs",
        spec_item="S4.1",
        title="Marriage, endogamy, inheritance, funeral rites and taste",
        subsystem=Subsystem.CULTURE,
        phases=("love_and_rivalry", "house_cycles", "institution_cycles", "polity_cycles", "mortal_aging", "artwork_cycles", "epidemics", "people_cycles"),
        surface=Surface(drawer=PEOPLE_SECTION),
        backfill=BACKFILL,
        templates=("peoples.funeral_rite",),
        fields=("marriage", "endogamous", "inheritance", "funeral_rite", "funeral_rite_id", "aesthetic"),
        tables=CULTURE,
        exposure=Exposure.CONTEXT,
        targets=("people", "settlement", "mortal"),
        couplings=(
            Coupling(Subsystem.SOCIAL, "the marriage custom sets how many spouses each may take", EdgeKind.RULE_SWITCH, "customs.polygyny_spouses"),
            Coupling(Subsystem.SOCIAL, "an endogamous people resists assimilation", EdgeKind.MODIFIER, "customs.endogamy_assimilation_pct"),
            Coupling(Subsystem.POLITY, "inheritance custom becomes the law of the throne and splits the estate", EdgeKind.RULE_SWITCH),
            Coupling(Subsystem.FAITH, "funeral rites call ancestors, raise the dead or leave restless ghosts", EdgeKind.MODIFIER, "customs.funeral_pct"),
            Coupling(Subsystem.DEMOGRAPHY, "how the dead are handled spreads or stops disease", EdgeKind.MODIFIER, "customs.funeral_pct"),
            Coupling(Subsystem.CULTURE, "art in the people's favoured media moves its values further", EdgeKind.MODIFIER, "customs.aesthetic_fit_pct"),
        ),
    ),
    Mechanic(
        key="martial_tradition",
        spec_item="S4.1",
        title="A way of war that wins is kept; one that loses is traded for the victor's",
        subsystem=Subsystem.WAR,
        phases=("people_cycles", "campaigns"),
        surface=Surface(drawer=PEOPLE_SECTION),
        backfill=BACKFILL,
        templates=("peoples.martial_style",),
        fields=("martial_style", "martial_record"),
        tables=CULTURE,
        exposure=Exposure.CONTEXT,
        targets=("people", "army"),
        couplings=(
            Coupling(Subsystem.WAR, "net victories hold the way of war against land and knowledge", EdgeKind.RULE_SWITCH, "customs.martial_hold_wins"),
            Coupling(Subsystem.WAR, "a seasoned way of war fights harder", EdgeKind.MODIFIER, "biology.martial_mastery_pct"),
        ),
    ),
    Mechanic(
        key="folk_tongues_towns",
        spec_item="S4.1",
        title="Trade and liturgical tongues, urbanisation and the founding of peoples",
        subsystem=Subsystem.LANGUAGE,
        phases=("people_cycles", "trade_flow", "knowledge_diffusion", "language_cycles", "famine_migration", "spontaneous_births", "population_growth"),
        surface=Surface(drawer=PEOPLE_SECTION, chart=FOUNDING_SURFACE),
        backfill=BACKFILL,
        fields=("trade_language", "liturgical_language", "urbanisation"),
        tables=CULTURE,
        targets=("people", "settlement"),
        couplings=(
            Coupling(Subsystem.ECONOMY, "a shared trade tongue widens a route", EdgeKind.MODIFIER, "customs.trade_tongue_pct"),
            Coupling(Subsystem.KNOWLEDGE, "a shared trade tongue carries knowledge further", EdgeKind.MODIFIER, "customs.trade_tongue_diffusion_pct"),
            Coupling(Subsystem.DEMOGRAPHY, "urban peoples found towns and crowd into them", EdgeKind.MODIFIER, "customs.urban_found_pct"),
            Coupling(Subsystem.SOCIAL, "urbanisation moves farmers into the trades", EdgeKind.FLOW, "customs.urban_class_pct"),
        ),
    ),
)
