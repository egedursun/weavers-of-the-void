from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.intimacy_shapes import PATH_COST_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import ChildRecognitionRow, LegitimacyRuleRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intimacy import ChildLegitimacy, LegitimacyPath
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.intimacy.legitimacy import legitimacy_of, rule_for
from aerona.engine.mortal.kin import children_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules


@dataclass
class RecognitionTally:
    recognised: int = 0


def recognition_cost(rules: Rules, rule: LegitimacyRuleRow) -> int:
    paid = rules.unions_and_birth.recognition_cost if rule.path is LegitimacyPath.PAYMENT else 0
    return round_half_up(rule.cost * PATH_COST_PCT[rule.path] / PERCENT) + paid


async def recognise(ctx: TickContext, sponsor: EntityRow, child: EntityRow, rule: LegitimacyRuleRow) -> int:
    cost = recognition_cost(ctx.rules, rule)
    await shift_points(ctx.session, sponsor, -cost)
    ctx.session.add(ChildRecognitionRow(child_node_id=child.id, path=rule.path, sponsor_node_id=sponsor.id, recognized_epoch=ctx.epoch, locked=[]))
    await record(
        ctx, "birth.recognition", roles={IncidentRole.ACTOR: sponsor.id, IncidentRole.SUBJECT: child.id}, facts={"path": rule.path}, place=sponsor.location_id
    )
    return cost


async def recognise_heirs(ctx: TickContext) -> RecognitionTally:
    tally = RecognitionTally()
    parents = select(BondRow.source_node_id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.state == BondState.ACTIVE).distinct()
    recognised = set(await ctx.session.scalars(select(ChildRecognitionRow.child_node_id)))
    for parent_id in sorted(set(await ctx.session.scalars(parents))):
        parent = await living_entity(ctx.session, parent_id)
        if parent is None or parent.entity_type is not EntityType.MORTAL or held(parent.id):
            continue
        children = [child for child_id in await children_of(ctx.session, parent.id) if (child := await living_entity(ctx.session, child_id)) is not None]
        standing = {child.id: await legitimacy_of(ctx.session, child) for child in children}
        if not children or any(value is ChildLegitimacy.FULL for value in standing.values()):
            continue
        for child in sorted(children, key=lambda item: item.id):
            rule = await rule_for(ctx.session, child)
            if child.id in recognised or held(child.id) or child.status is not EntityStatus.CANON or rule is None or rule.path is LegitimacyPath.NONE:
                continue
            if await points_of(ctx.session, parent) < recognition_cost(ctx.rules, rule):
                continue
            await recognise(ctx, parent, child, rule)
            recognised.add(child.id)
            tally.recognised += 1
            break
    return tally
