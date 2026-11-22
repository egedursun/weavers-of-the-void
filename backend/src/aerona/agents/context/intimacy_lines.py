from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.catalog.life.agents import MORTAL_INTIMACY_LINES_OATH_KINDS
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.db.tables.intimacy import IntimacyNormRow, LegitimacyRuleRow, ReproductiveCourseRow, RestraintCustomRow
from aerona.db.tables.polity import OathRow
from aerona.domain.enums.intimacy import ChildLegitimacy, LegitimacyPath, NormStance
from aerona.domain.enums.polity import OathStatus
from aerona.engine.body.customs import people_of
from aerona.engine.intimacy.legitimacy import legitimacy_of
from aerona.engine.mortal.kin import children_of


async def norm_lines(scope: Scope, folk_id: int) -> list[str]:
    found: list[str] = []
    norms = list(await scope.session.scalars(select(IntimacyNormRow).where(IntimacyNormRow.people_entity_id == folk_id).order_by(IntimacyNormRow.context)))
    marked = [row for row in norms if row.stance is not NormStance.TOLERATED]
    if marked:
        found.append("your people hold relations " + "; ".join(f"{spoken(row.context)} {spoken(row.stance)}" for row in marked))
    customs = await scope.session.scalars(select(RestraintCustomRow).where(RestraintCustomRow.people_entity_id == folk_id).order_by(RestraintCustomRow.id))
    for custom in customs:
        found.append(f"your people ask restraint of {spoken(custom.role)} ({spoken(custom.occasion)}, strength {custom.strength} of 100)")
    course = await scope.session.get(ReproductiveCourseRow, folk_id)
    if course is not None:
        found.append(
            f"among your people a birth is attended by {spoken(course.attendant)} at {spoken(course.birth_place)} after {course.gestation_months} months, "
            f"and the time after it is kept by {spoken(course.postnatal)}"
        )
    for rule in await scope.session.scalars(
        select(LegitimacyRuleRow)
        .where(LegitimacyRuleRow.people_entity_id == folk_id, LegitimacyRuleRow.standing != ChildLegitimacy.FULL)
        .order_by(LegitimacyRuleRow.parent_union)
    ):
        way = f", changed by {spoken(rule.path)} for {rule.cost} of wealth" if rule.path is not LegitimacyPath.NONE else ""
        found.append(f"a child of parents {spoken(rule.parent_union)} stands {spoken(rule.standing)}{way}")
    return found


async def means_lines(scope: Scope, people_id: int, me: EntityRow) -> list[str]:
    found: list[str] = []
    for row in await scope.session.scalars(select(FertilityMeansRow).where(FertilityMeansRow.people_entity_id == people_id).order_by(FertilityMeansRow.means)):
        found.append(
            f"your people know {spoken(row.means)} by {spoken(row.source)}: reliability {row.reliability}, risk {row.risk}, held {spoken(row.stance)}, "
            f"used by {row.use_pct} percent"
        )
    for use in await scope.session.scalars(select(FertilityUseRow).where(FertilityUseRow.user_entity_id == me.id).order_by(FertilityUseRow.id)):
        manner = ", and it has come to light" if use.exposed else " in secret" if use.hidden else " openly"
        found.append(f"you use {spoken(use.means)}{manner}")
    return found


async def mortal_intimacy_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    folk = await people_of(scope.session, me)
    if folk is not None:
        found.extend(await norm_lines(scope, folk.id))
        found.extend(await means_lines(scope, folk.id, me))
    vows = [
        spoken(kind)
        for kind in await scope.session.scalars(
            select(OathRow.kind)
            .where(OathRow.swearer_entity_id == me.id, OathRow.status == OathStatus.SWORN, OathRow.kind.in_(MORTAL_INTIMACY_LINES_OATH_KINDS))
            .order_by(OathRow.kind)
            .distinct()
        )
    ]
    if vows:
        found.append(f"you keep a vow of {' and '.join(vows)}")
    for child_id in await children_of(scope.session, me.id):
        child = await scope.session.get(EntityRow, child_id)
        standing = await legitimacy_of(scope.session, child) if child is not None else ChildLegitimacy.FULL
        if standing is not ChildLegitimacy.FULL:
            found.append(f"your child {await named(scope, child_id)} stands {spoken(standing)} among your people")
    return found
