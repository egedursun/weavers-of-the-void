from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import ChildRecognitionRow, LegitimacyRuleRow
from aerona.domain.enums.intimacy import ChildLegitimacy, ParentUnion
from aerona.engine.body.customs import people_of
from aerona.engine.mortal.kin import parents_of, partners_of
from aerona.engine.mortal.kinship import marriage_between

STANDING_ORDER = {ChildLegitimacy.FULL: 0, ChildLegitimacy.PARTIAL: 1, ChildLegitimacy.NONE: 2}


async def parent_union(session: AsyncSession, child_id: int) -> ParentUnion:
    parents = sorted(await parents_of(session, child_id))
    if len(parents) < 2:
        return ParentUnion.UNKNOWN
    first, second = parents[0], parents[1]
    if await marriage_between(session, first, second) is not None:
        return ParentUnion.WED
    others = (set(await partners_of(session, first)) | set(await partners_of(session, second))) - {first, second}
    return ParentUnion.OUTSIDE_UNION if others else ParentUnion.UNWED


async def rule_for(session: AsyncSession, child: EntityRow) -> LegitimacyRuleRow | None:
    folk = await people_of(session, child)
    if folk is None:
        return None
    return await session.get(LegitimacyRuleRow, (folk.id, await parent_union(session, child.id)))


async def legitimacy_of(session: AsyncSession, child: EntityRow) -> ChildLegitimacy:
    rule = await rule_for(session, child)
    if rule is None or rule.standing is ChildLegitimacy.FULL:
        return ChildLegitimacy.FULL
    if await session.get(ChildRecognitionRow, child.id) is not None:
        return ChildLegitimacy.FULL
    return rule.standing


async def legitimate_heirs(session: AsyncSession, heirs: list[EntityRow]) -> list[EntityRow]:
    standing = {heir.id: await legitimacy_of(session, heir) for heir in heirs}
    kept = [heir for heir in heirs if standing[heir.id] is not ChildLegitimacy.NONE]
    if not kept:
        return []
    best = min(STANDING_ORDER[standing[heir.id]] for heir in kept)
    return [heir for heir in kept if STANDING_ORDER[standing[heir.id]] == best]
