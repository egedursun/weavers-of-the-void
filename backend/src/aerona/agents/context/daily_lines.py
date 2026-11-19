from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, spoken
from aerona.db.tables.daily_life import CareCustomRow, DomesticServiceRow, HouseworkRow, LeisurePursuitRow, SpaceNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.engine.body.customs import people_of
from aerona.engine.customs.time_budgets import budget_of

BUDGET_KEYS = ("work", "housework", "care", "rest", "sleep", "worship", "learning", "leisure", "travel", "service", "art")


async def budget_line(scope: Scope, me: EntityRow) -> str | None:
    budget = await budget_of(scope.session, me)
    if budget is None:
        return None
    profile = await scope.session.get(MortalProfileRow, me.id)
    stage = spoken(profile.life_stage) if profile is not None else "adult"
    shares = ", ".join(f"{spoken(key)} {getattr(budget, key)}" for key in BUDGET_KEYS if getattr(budget, key))
    return f"how your class spends its days at your stage of life ({stage}), out of 100: {shares}"


async def mortal_daily_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    line = await budget_line(scope, me)
    if line is not None:
        found.append(line)
    for duty in await session.scalars(select(HouseworkRow).where(HouseworkRow.doer_node_id == me.id).order_by(HouseworkRow.duty)):
        household = await session.get(HouseholdRow, duty.household_id)
        where = f" for {household.name}" if household is not None else ""
        found.append(f"you keep the duty of {spoken(duty.duty)}{where} (load {duty.load} of 100)")
    service = await session.get(DomesticServiceRow, me.id)
    if service is not None:
        household = await session.get(HouseholdRow, service.household_id)
        found.append(f"you serve {household.name if household else 'a household'} on terms of {spoken(service.terms)}, wage {service.wage}")
    for pursuit in await session.scalars(select(LeisurePursuitRow).where(LeisurePursuitRow.holder_node_id == me.id).order_by(LeisurePursuitRow.kind)):
        venue = f" at {await named(scope, pursuit.venue_node_id)}" if pursuit.venue_node_id is not None else ""
        found.append(f"you give free time to {spoken(pursuit.kind)}{venue} (share {pursuit.share})")
    folk = await people_of(session, me)
    if folk is None:
        return found
    care = await session.get(CareCustomRow, folk.id)
    if care is not None:
        found.append(
            f"your people wash {spoken(care.wash_frequency)} ({spoken(care.wash_place)}), "
            f"keep cleanliness {care.cleanliness} and grooming {care.grooming} of 100, "
            f"and handle waste by {spoken(care.waste_handling)}"
        )
    norms = await session.get(SpaceNormRow, folk.id)
    if norms is not None:
        found.append(f"your people keep {an(spoken(norms.distance))} distance, touch {spoken(norms.touch)}, and the posture {spoken(norms.posture)}")
    for pursuit in await session.scalars(select(LeisurePursuitRow).where(LeisurePursuitRow.holder_node_id == folk.id).order_by(LeisurePursuitRow.kind)):
        found.append(f"your people give free time to {spoken(pursuit.kind)} (share {pursuit.share})")
    return found
