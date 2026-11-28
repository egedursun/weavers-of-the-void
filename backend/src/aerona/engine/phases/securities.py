from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.securities.tend import tend_securities


@reads(
    "faction.wealth",
    "settlement.population",
    "table.company_shares",
    "table.credit_profiles",
    "table.currencies",
    "table.entities",
    "table.hidden_truths",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.issued_securities",
    "table.loans",
    "table.long_plans",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.security_holdings",
    "table.security_prices",
    "table.stock_exchanges",
    "table.truth_keepers",
    "table.war_sides",
    "table.wars",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.company_shares",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.issued_securities",
    "table.loans",
    "table.security_holdings",
    "table.security_prices",
    "table.stock_exchanges",
)
async def securities(ctx: TickContext) -> None:
    for key, value in asdict(await tend_securities(ctx)).items():
        ctx.count(f"securities_{key}", value)


PHASES = (Phase("securities", securities),)
