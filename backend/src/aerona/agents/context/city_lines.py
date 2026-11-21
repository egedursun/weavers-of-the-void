from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.city_rules import ConurbationRow, LandUseRuleRow, MunicipalServiceRow
from aerona.db.tables.entities import EntityRow


async def mortal_city_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = me.location_id
    if town is None:
        return []
    session = scope.session
    found: list[str] = []
    for rule in await session.scalars(select(LandUseRuleRow).where(LandUseRuleRow.settlement_entity_id == town).order_by(LandUseRuleRow.id)):
        found.append(f"rule {rule.id}: {spoken(rule.rule)}, strength {rule.strength}, enforcement {rule.enforcement}, evasion {rule.evasion}")
    for service in await session.scalars(select(MunicipalServiceRow).where(MunicipalServiceRow.settlement_entity_id == town).order_by(MunicipalServiceRow.id)):
        state = "failed" if service.failed_epoch is not None else f"budget {service.budget}, quality {service.quality}"
        found.append(f"service {service.id}: {spoken(service.service)}, {state}")
    for city in await session.scalars(select(ConurbationRow).where(ConurbationRow.split_epoch.is_(None)).order_by(ConurbationRow.id)):
        if town == city.core_entity_id or town in (city.members or []):
            quarters = ", ".join([await named(scope, member) for member in city.members or []])
            found.append(f"your town is part of the city around {await named(scope, city.core_entity_id)} with {quarters}, under {spoken(city.governance)}")
    return found
