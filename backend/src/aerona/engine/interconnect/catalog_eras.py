from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

S = Subsystem
E = EdgeKind
DRAWER = "section-tech-eras"

ERAS_MECHANICS = (
    Mechanic(
        key="technology_eras",
        spec_item="F44",
        title="Technology eras: techniques of powder, steam, electricity, information and the advanced age change work, sickness, war, messages and doom",
        subsystem=S.KNOWLEDGE,
        phases=(
            "tech_eras",
            "resource_economy",
            "refining",
            "trade_flow",
            "cosmic_trade",
            "research_cycles",
            "rite_cycles",
            "campaigns",
            "correspondence",
            "public_opinion",
            "industry_aftermath",
            "doom_clock",
            "epidemics",
            "travel",
        ),
        surface=Surface(drawer=DRAWER, chart="chart-tech-eras"),
        backfill="tech_eras: towns and peoples with no knowledge yet start at the world's starting era from the next epoch",
        templates=(),
        fields=("era", "channels"),
        tables=(HolderLevelRow.__tablename__, HolderTechniqueRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("settlement", "people", "polity", "mortal"),
        couplings=(
            Coupling(S.ECONOMY, "steam, factories, electricity and nuclear power raise industry", E.MODIFIER, "eras.factory_pct"),
            Coupling(
                S.POLITY,
                "factories, engines and banking raise unions of workers, societies of engineers and exchanges of financiers",
                E.TRIGGER,
                "factions.engineers_min_professional_pct",
            ),
            Coupling(S.ECONOMY, "fertilisers, bred crops and genetic engineering raise harvests", E.MODIFIER, "eras.green_pct"),
            Coupling(S.ECONOMY, "canning and refrigeration spare goods on the road", E.MODIFIER, "eras.refrigeration_pct"),
            Coupling(S.DEMOGRAPHY, "vaccines, antibiotics and genetic engineering spare the sick", E.MODIFIER, "eras.antibiotics_pct"),
            Coupling(S.WAR, "gunpowder, firearms, cannon and drill strengthen missiles", E.MODIFIER, "eras.firearms_pct"),
            Coupling(S.WAR, "star forts strengthen walls", E.MODIFIER, "eras.star_forts_pct"),
            Coupling(S.WAR, "railways, engines and aircraft move armies farther", E.MODIFIER, "eras.railway_regions"),
            Coupling(S.SOCIAL, "telegraph, telephone and radio carry messages farther", E.MODIFIER, "eras.telegraph_hops"),
            Coupling(S.SOCIAL, "radio and mass media move opinion faster", E.MODIFIER, "eras.media_pct"),
            Coupling(S.FAITH, "computation and mass media quicken secularisation", E.MODIFIER, "eras.media_secular_pct"),
            Coupling(S.FAITH, "power rites weaken where electricity runs", E.MODIFIER, "eras.electricity_rite_pct"),
            Coupling(S.KNOWLEDGE, "electric light, computation and artificial minds quicken research", E.MODIFIER, "eras.computation_pct"),
            Coupling(S.ENVIRONMENT, "steam, coke, factories, chemistry and engines foul the air", E.MODIFIER, "eras.factory_pollution_pct"),
            Coupling(S.COSMOS, "nuclear weapons, nuclear power and artificial minds feed the doom clock", E.FLOW, "eras.nuclear_doom"),
            Coupling(S.COSMOS, "steamships and rockets widen the routes between seas and worlds", E.MODIFIER, "eras.rocketry_pct"),
        ),
    ),
    Mechanic(
        key="tech_programmes",
        spec_item="F44",
        title="Technique programmes: a realm plans, builds and tests its way to a dangerous technique, paid by its treasury and set back by spies",
        subsystem=S.KNOWLEDGE,
        phases=("tech_eras", "espionage"),
        surface=Surface(drawer=DRAWER, chart="chart-tech-programmes"),
        backfill="tech_eras: realms whose capitals reach a dangerous technique begin programmes from the next epoch",
        templates=("programmes.building", "programmes.testing", "programmes.complete"),
        fields=("progress", "stage", "visibility", "sabotaged"),
        tables=(TechProgrammeRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("sabotage_programme", "join_programme"),
        targets=("polity",),
        couplings=(
            Coupling(S.ECONOMY, "each epoch of work costs the treasury", E.FLOW, "programmes.treasury_cost"),
            Coupling(S.KNOWLEDGE, "scientists, engineers and computers speed the work", E.MODIFIER, "programmes.specialist_progress"),
            Coupling(S.WAR, "a rival's spies set the programme back", E.TRIGGER, "programmes.sabotage_chance"),
            Coupling(S.SOCIAL, "each new stage is heard abroad", E.TRIGGER, "programmes.rumour_magnitude"),
            Coupling(S.COSMOS, "rocketry opens a route to another world", E.TRIGGER, "programmes.base_years"),
        ),
    ),
)
