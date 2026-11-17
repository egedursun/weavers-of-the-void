from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.collective import MovementRow
from aerona.db.tables.constructs import RemadeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import Commodity, KnowledgeBranch
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import realm_of_town, town_of

SHIFT = 20
FORMS = ((None, BodyFunction.GRASP), (BodyFunction.SPEECH, None), (BodyFunction.LOCOMOTION, BodyFunction.GRASP))


@dataclass
class RemadeTally:
    labour: int = 0
    revolts: int = 0


async def may_remake(ctx: TickContext, community_id: int | None) -> bool:
    if community_id is None:
        return False
    community = await ctx.session.get(EntityRow, community_id)
    if community is None:
        return False
    table = ctx.rules.punitive_remaking
    knowledge = await KnowledgeMap.load(ctx.session)
    people = await people_id_of(ctx.session, community)
    holders = [holder for holder in (community.id, people) if holder is not None]
    able = False
    for holder in holders:
        if max(knowledge.level(holder, KnowledgeBranch.MAGIC), knowledge.level(holder, KnowledgeBranch.BIOMANCY)) >= table.magic_floor:
            able = True
    if not able:
        return False
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people) if people is not None else {}
    return values.get(ValueAxis.MERCY, 0) <= table.cruel_mercy


async def remake(ctx: TickContext, culprit: EntityRow, case_id: int | None) -> RemadeRow:
    existing = await ctx.session.get(RemadeRow, culprit.id)
    if existing is not None:
        return existing
    lost, forced = ctx.rng(f"remake.{culprit.id}").pick(FORMS)
    town = await town_of(ctx.session, culprit)
    realm = await realm_of_town(ctx.session, town.id) if town is not None else None
    row = RemadeRow(
        mortal_entity_id=culprit.id,
        lost_function=lost,
        forced_function=forced,
        sentenced_by_entity_id=realm,
        case_id=case_id,
        bound_to_entity_id=town.id if town is not None and forced is not None else None,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    if lost is BodyFunction.SPEECH:
        set_stats(culprit, charisma=clamp_int(stat_or(culprit, "charisma", 0) - SHIFT, 0, PERCENT))
    if lost is BodyFunction.LOCOMOTION:
        set_stats(culprit, agility=clamp_int(stat_or(culprit, "agility", 0) - SHIFT, 0, PERCENT))
    if forced is BodyFunction.GRASP:
        set_stats(culprit, strength=clamp_int(stat_or(culprit, "strength", 0) + SHIFT, 0, PERCENT))
    await ctx.session.flush()
    await record(
        ctx,
        "law.remade",
        roles={IncidentRole.ACCUSED: culprit.id, IncidentRole.AUTHORITY: realm},
        facts={"lost": lost, "forced": forced, "bound_to": row.bound_to_entity_id},
        place=town.id if town is not None else None,
    )
    return row


async def rise(ctx: TickContext, town: EntityRow, rows: list[RemadeRow], tally: RemadeTally) -> None:
    ctx.session.add(
        MovementRow(
            settlement_entity_id=town.id,
            act=CollectiveActKind.REVOLT,
            trigger=CollectiveTrigger.EXECUTION,
            members=len(rows),
            strength=SHIFT,
            leader_entity_id=max(rows, key=lambda row: (row.grievance, -row.mortal_entity_id)).mortal_entity_id,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    for row in rows:
        if "grievance" not in row.locked:
            row.grievance //= 2
    tally.revolts += 1
    await record(
        ctx,
        "law.remade_rose",
        roles={IncidentRole.SUBJECT: town.id, IncidentRole.MEMBER: [row.mortal_entity_id for row in rows]},
        facts={"remade": len(rows)},
        place=town.id,
    )


async def keep_remade(ctx: TickContext, tally: RemadeTally) -> None:
    table = ctx.rules.punitive_remaking
    by_town: dict[int, list[RemadeRow]] = {}
    for row in list(await ctx.session.scalars(select(RemadeRow).order_by(RemadeRow.mortal_entity_id))):
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is None or held(mortal.id):
            continue
        if "grievance" not in row.locked:
            row.grievance = clamp_int(row.grievance + table.grievance_step, 0, PERCENT)
        bound = await living_entity(ctx.session, row.bound_to_entity_id)
        if bound is not None and not held(bound.id) and row.forced_function is not None:
            await shift_stock(ctx.session, ctx.rules, bound.id, Commodity.GOODS, table.labour_goods, epoch=ctx.epoch, flow=GoodsFlow.PRODUCTION)
            tally.labour += 1
        town = await town_of(ctx.session, mortal)
        if town is not None:
            by_town.setdefault(town.id, []).append(row)
    for town_id, rows in sorted(by_town.items()):
        town = await living_entity(ctx.session, town_id)
        if town is None or held(town.id) or len(rows) < table.revolt_count:
            continue
        if sum(row.grievance for row in rows) / len(rows) < table.revolt_grievance:
            continue
        rising = await ctx.session.scalar(
            select(MovementRow.id)
            .where(MovementRow.settlement_entity_id == town.id, MovementRow.act == CollectiveActKind.REVOLT, MovementRow.ended_epoch.is_(None))
            .limit(1)
        )
        if rising is None:
            await rise(ctx, town, rows, tally)
    await ctx.session.flush()
