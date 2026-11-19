from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.book import realm_of


async def policy_line(scope: Scope, policy: PopulationPolicyRow) -> str:
    instruments = await scope.session.scalars(
        select(PopulationInstrumentRow).where(PopulationInstrumentRow.policy_id == policy.id).order_by(PopulationInstrumentRow.instrument)
    )
    ways = ", ".join(f"{spoken(row.instrument)} {row.strength}" for row in instruments) or "no instruments yet"
    aimed = f", aimed at {await named(scope, policy.target_node_id)}" if policy.target_node_id is not None else ""
    return (
        f"{await named(scope, policy.holder_node_id)} aims to {spoken(policy.aim)}{aimed} by {ways}; "
        f"strength {policy.strength}, enforcement {policy.enforcement} of 100, {policy.baseline} people when it began"
    )


async def mortal_population_lines(scope: Scope, me: EntityRow) -> list[str]:
    holders: list[int] = []
    folk = await people_of(scope.session, me)
    if folk is not None:
        holders.append(folk.id)
    realm = await realm_of(scope.session, me.location_id) if me.location_id is not None else None
    if realm is not None:
        holders.append(realm)
    if me.location_id is not None:
        holders.append(me.location_id)
    found: list[str] = []
    for policy in await scope.session.scalars(
        select(PopulationPolicyRow).where(PopulationPolicyRow.holder_node_id.in_(sorted(set(holders)))).order_by(PopulationPolicyRow.id)
    ):
        found.append(await policy_line(scope, policy))
    return found
