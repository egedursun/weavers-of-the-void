from dataclasses import asdict

from aerona.engine.city_rules.tend import tend_cities
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "settlement.population",
    "table.conurbations",
    "table.districts",
    "table.entities",
    "table.land_use_rules",
    "table.municipal_services",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.structure_profiles",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conurbations",
    "table.districts",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.land_use_rules",
    "table.law_jurisdictions",
    "table.municipal_services",
    "table.node_births",
    "table.settlement_profiles",
)
async def city_rules(ctx: TickContext) -> None:
    for key, value in asdict(await tend_cities(ctx)).items():
        ctx.count(f"city_rules_{key}", value)


PHASES = (Phase("city_rules", city_rules),)
