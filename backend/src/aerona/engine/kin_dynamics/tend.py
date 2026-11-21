from itertools import pairwise

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinBlendRow, KinDisowningRow, KinDynamicRow, KinRivalryRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, OfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kin_dynamics import DisownReason, RivalryCause
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.kin_dynamics.acts import disown, favour, reconcile, rival, split_house
from aerona.engine.kin_dynamics.book import KinTally, children_of, dynamic_of, parents_of
from aerona.engine.kin_dynamics.heirs import disowned_by, favoured_by, leaves_a_choice
from aerona.engine.lifecycle.succession import designate_heir
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

STEERING = 50
RC = RivalryCause
HEAT_PCT = total(RivalryCause, {RC.INHERITANCE: 150, RC.FAVOUR: 100, RC.OFFICE: 120, RC.LOVE: 130, RC.STANDING: 80})


async def form_favour(ctx: TickContext, dynamic: KinDynamicRow, head: EntityRow, tally: KinTally) -> None:
    table = ctx.rules.kin_dynamics
    children = [child for child in await children_of(ctx.session, head.id) if child not in await disowned_by(ctx.session, head.id) and not held(child)]
    if len(children) < 2 or not ctx.rng(f"kin.favour.{head.id}.{ctx.epoch}").chance(table.favour_chance_pct):
        return
    chosen = ctx.rng(f"kin.favour.who.{head.id}.{ctx.epoch}").pick(children)
    await favour(ctx, dynamic, head.id, chosen, tally)
    for sibling in children:
        if sibling != chosen and ctx.rng(f"kin.rival.{chosen}.{sibling}.{ctx.epoch}").chance(table.rivalry_from_favour_pct):
            await rival(ctx, dynamic, chosen, sibling, RivalryCause.FAVOUR, tally=tally)


async def designate(ctx: TickContext, head: EntityRow, house: int, tally: KinTally) -> None:
    if not await active_bonds(ctx.session, [BondKind.RULES], sources=[head.id]) or not await leaves_a_choice(ctx.session, head):
        return
    chosen = next(iter(await favoured_by(ctx.session, head.id, ctx.rules.kin_dynamics.favour_inheritance_pct)), None)
    current = await ctx.session.get(DesignatedHeirRow, head.id)
    if chosen is None or held(chosen) or (current is not None and current.heir_entity_id == chosen):
        return
    heir = await living_entity(ctx.session, chosen)
    if heir is not None and heir.entity_type is EntityType.MORTAL:
        await designate_heir(ctx, head.id, heir.id)
        tally.designated += 1
        dynamic = await dynamic_of(ctx, house=house)
        for passed in await children_of(ctx.session, head.id):
            if passed != heir.id and not held(passed):
                await rival(ctx, dynamic, heir.id, passed, RivalryCause.INHERITANCE, tally=tally)


async def office_rivals(ctx: TickContext, dynamic: KinDynamicRow, head: EntityRow, tally: KinTally) -> None:
    children = await children_of(ctx.session, head.id)
    if len(children) < 2:
        return
    offices = list(await ctx.session.execute(select(OfficeRow.holder_entity_id, OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id.in_(children))))
    by_realm: dict[int, list[int]] = {}
    for holder, realm in offices:
        if holder is not None:
            by_realm.setdefault(realm, []).append(holder)
    for holders in by_realm.values():
        ranked = sorted(set(holders))
        for first, second in pairwise(ranked):
            if not held(first) and not held(second):
                await rival(ctx, dynamic, first, second, RivalryCause.OFFICE, tally=tally)


async def heat_rivalries(ctx: TickContext, dynamic: KinDynamicRow, tally: KinTally) -> None:
    table = ctx.rules.kin_dynamics
    query = select(KinRivalryRow).where(KinRivalryRow.dynamic_id == dynamic.id, KinRivalryRow.ended_epoch.is_(None)).order_by(KinRivalryRow.id)
    for row in list(await ctx.session.scalars(query)):
        first, second = await living_entity(ctx.session, row.first_node_id), await living_entity(ctx.session, row.second_node_id)
        if first is None or second is None:
            row.ended_epoch = ctx.epoch
            continue
        if held(first.id) or held(second.id):
            continue
        if "heat" not in (row.locked or []):
            row.heat = clamp_int(row.heat + table.heat_step * HEAT_PCT[row.cause] // PERCENT, 0, PERCENT)
        await change_relation(ctx, first.id, second.id, -table.relation_loss, MemoryKind.HARMED_ME, note="rivalry within the family")
        if row.heat < table.split_threshold:
            continue
        if first.id in await parents_of(ctx.session, second.id) or second.id in await parents_of(ctx.session, first.id):
            parent, child = (first, second) if first.id in await parents_of(ctx.session, second.id) else (second, first)
            await disown(ctx, dynamic, parent.id, child, DisownReason.RIVALRY, tally=tally)
            row.ended_epoch = ctx.epoch
        else:
            await split_house(ctx, dynamic, row, second, tally)


async def mend(ctx: TickContext, dynamic: KinDynamicRow, tally: KinTally) -> None:
    query = select(KinDisowningRow).where(KinDisowningRow.dynamic_id == dynamic.id, KinDisowningRow.reconciled_epoch.is_(None)).order_by(KinDisowningRow.id)
    for row in list(await ctx.session.scalars(query)):
        if not held(row.disowned_node_id) and ctx.rng(f"kin.mend.{row.id}.{ctx.epoch}").chance(ctx.rules.kin_dynamics.reconcile_chance_pct):
            await reconcile(ctx, row, tally)


async def blend(ctx: TickContext, dynamic: KinDynamicRow, head: EntityRow, members: set[int], tally: KinTally) -> None:
    table = ctx.rules.kin_dynamics
    own = set(await children_of(ctx.session, head.id))
    spouses = {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.SPOUSE_OF], sources=[head.id])}
    spouses |= {bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.SPOUSE_OF], targets=[head.id])}
    known = set(await ctx.session.scalars(select(KinBlendRow.member_node_id).where(KinBlendRow.dynamic_id == dynamic.id)))
    for spouse in sorted(spouses):
        for child in await children_of(ctx.session, spouse):
            if child in own or child in known or child not in members or held(child):
                continue
            ctx.session.add(
                KinBlendRow(
                    dynamic_id=dynamic.id, member_node_id=child, joined_by_node_id=spouse, standing=table.step_standing, since_epoch=ctx.epoch, locked=[]
                )
            )
            known.add(child)
            tally.blends += 1
            for sibling in sorted(own):
                if table.step_standing < STEERING and ctx.rng(f"kin.step.{child}.{sibling}.{ctx.epoch}").chance(table.rivalry_from_favour_pct):
                    await rival(ctx, dynamic, child, sibling, RivalryCause.STANDING, tally=tally)


async def sway(ctx: TickContext, dynamic: KinDynamicRow, head: EntityRow, tally: KinTally) -> None:
    table = ctx.rules.kin_dynamics
    query = select(ElderSwayRow).where(ElderSwayRow.dynamic_id == dynamic.id, ElderSwayRow.ended_epoch.is_(None))
    row = await ctx.session.scalar(query.order_by(ElderSwayRow.id).limit(1))
    if row is None:
        elder = next(iter([parent for parent in await parents_of(ctx.session, head.id) if await living_entity(ctx.session, parent) is not None]), None)
        if elder is None or held(elder):
            return
        row = ElderSwayRow(dynamic_id=dynamic.id, elder_node_id=elder, sway=table.elder_sway, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
        tally.elders += 1
    if await living_entity(ctx.session, row.elder_node_id) is None:
        row.ended_epoch = ctx.epoch
        return
    if row.sway >= STEERING:
        grandchildren = await children_of(ctx.session, head.id)
        chosen = ctx.rng(f"kin.elder.{row.id}.{ctx.epoch}").pick_or_none(grandchildren)
        if chosen is not None:
            await favour(ctx, dynamic, head.id, chosen, tally, strength=row.sway)
            tally.steered += 1
            await record(
                ctx,
                "kin.elder_steered",
                roles={IncidentRole.ACTOR: row.elder_node_id, IncidentRole.SUBJECT: head.id, IncidentRole.TARGET: chosen},
                facts={"sway": row.sway},
            )
    if "sway" not in (row.locked or []):
        row.sway = clamp_int(row.sway - table.sway_decay, 0, PERCENT)
    if row.sway < table.overthrow_below and ctx.rng(f"kin.overthrow.{row.id}.{ctx.epoch}").chance(table.overthrow_chance_pct):
        row.ended_epoch = ctx.epoch
        await record(ctx, "kin.elder_overthrown", roles={IncidentRole.ACTOR: head.id, IncidentRole.TARGET: row.elder_node_id}, facts={"sway": row.sway})


async def tend_kin(ctx: TickContext) -> KinTally:
    tally = KinTally()
    for profile in list(await ctx.session.scalars(select(HouseProfileRow).order_by(HouseProfileRow.house_entity_id))):
        head = await living_entity(ctx.session, profile.head_entity_id) if profile.head_entity_id is not None else None
        if head is None or held(profile.house_entity_id) or held(head.id):
            continue
        dynamic = await dynamic_of(ctx, house=profile.house_entity_id)
        members = set(await ctx.session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == profile.house_entity_id)))
        await form_favour(ctx, dynamic, head, tally)
        await designate(ctx, head, profile.house_entity_id, tally)
        await office_rivals(ctx, dynamic, head, tally)
        await heat_rivalries(ctx, dynamic, tally)
        await mend(ctx, dynamic, tally)
        await blend(ctx, dynamic, head, members, tally)
        await sway(ctx, dynamic, head, tally)
    return tally
