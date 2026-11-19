from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.childhood import TECHNIQUE_WEIGHTS, ChildStandingRow, InfantCareRow, PedagogyRow, SocializationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.body.customs import people_of
from aerona.engine.mortal.kin import children_of

GROWING = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH})
CHIEF_WAYS = 3


async def young_children(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    for child_id in await children_of(scope.session, me.id):
        child = await scope.session.get(EntityRow, child_id)
        profile = await scope.session.get(MortalProfileRow, child_id)
        if child is not None and profile is not None and child.status is EntityStatus.CANON and profile.life_stage in GROWING:
            found.append(f"{await named(scope, child_id)} ({spoken(profile.life_stage)}, schooling {profile.education} of 100)")
    return found


async def mortal_childhood_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    folk = await people_of(session, me)
    if folk is not None:
        care = await session.get(InfantCareRow, folk.id)
        if care is not None:
            found.append(
                f"your people feed infants {spoken(care.feeding)}, wean them at {care.weaning_age}, keep them {spoken(care.carry)}, "
                f"let them sleep {spoken(care.sleeping)}, and leave their care to {spoken(care.carer)}"
            )
        standing = await session.get(ChildStandingRow, folk.id)
        if standing is not None:
            shield = "; children are protected from punishment" if standing.protected else ""
            found.append(
                f"among your people a child is named at {standing.naming_age}, counts as a person at {standing.personhood_age}, "
                f"works from {standing.work_age}, answers to the law from {standing.responsibility_age} and may wed from {standing.marriage_age}; "
                f"{standing.labour_share} of 100 of children's time goes to work{shield}"
            )
        upbringing = await session.get(SocializationRow, folk.id)
        if upbringing is not None:
            ways = sorted(TECHNIQUE_WEIGHTS, key=lambda name: -getattr(upbringing, name))[:CHIEF_WAYS]
            found.append("your people raise children chiefly by " + ", ".join(f"{spoken(name)} {getattr(upbringing, name)}" for name in ways))
        taught = await session.scalar(select(PedagogyRow).where(PedagogyRow.holder_node_id == folk.id).order_by(PedagogyRow.id).limit(1))
        if taught is not None:
            found.append(f"your people's tradition teaches by {spoken(taught.theory)}, depth {taught.depth} of 100")
    children = await young_children(scope, me)
    if children:
        found.append(f"your growing children: {', '.join(children)}")
    return found
