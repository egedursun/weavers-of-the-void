from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import FieldAgreementRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyOfficerRow
from aerona.db.tables.warfare import ArmyRow, CaptiveRow, SiegeRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.couplings import FieldAgreementKind, FieldAgreementState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.military import ArmyRole
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.war import CaptiveStatus, SiegeStatus, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or

KEPT = FieldAgreementState.KEPT


async def commander_of(ctx: TickContext, army_id: int) -> EntityRow | None:
    army = await ctx.session.get(ArmyRow, army_id)
    if army is not None and army.commander_entity_id is not None:
        led = await living_entity(ctx.session, army.commander_entity_id)
        if led is not None:
            return led
    officer = await ctx.session.scalar(
        select(ArmyOfficerRow.mortal_entity_id)
        .where(ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.role == ArmyRole.COMMANDER, ArmyOfficerRow.until_epoch.is_(None))
        .limit(1)
    )
    return await living_entity(ctx.session, officer) if officer is not None else None


async def standing(ctx: TickContext, war_id: int, first: int, second: int, kinds: tuple[FieldAgreementKind, ...]) -> FieldAgreementRow | None:
    return await ctx.session.scalar(
        select(FieldAgreementRow)
        .where(
            FieldAgreementRow.war_id == war_id,
            FieldAgreementRow.kind.in_(kinds),
            FieldAgreementRow.state == KEPT,
            (FieldAgreementRow.commander_entity_id.in_((first, second))) | (FieldAgreementRow.place_entity_id.in_((first, second))),
        )
        .limit(1)
    )


async def agree(
    ctx: TickContext,
    war_id: int | None,
    kind: FieldAgreementKind,
    *,
    commander: int | None,
    counterpart: int | None,
    place: int | None,
    term: int | None,
    honour: int,
) -> FieldAgreementRow:
    row = FieldAgreementRow(
        war_id=war_id,
        kind=kind,
        state=KEPT,
        commander_entity_id=commander,
        counterpart_entity_id=counterpart,
        place_entity_id=place,
        term_epoch=term,
        honour=clamp_int(honour, -PERCENT, PERCENT),
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def parley(ctx: TickContext, war: WarRow, sides: tuple[EntityRow, EntityRow], armies: tuple[int, int]) -> bool:
    table = ctx.rules.field_diplomacy
    first, second = await commander_of(ctx, armies[0]), await commander_of(ctx, armies[1])
    if first is None or second is None or held(first.id, second.id):
        return False
    if await standing(ctx, war.id, first.id, second.id, (FieldAgreementKind.TRUCE,)) is not None:
        return True
    if not ctx.rng(f"parley.{war.id}.{war.battles}.{ctx.epoch}").chance(table.parley_chance):
        return False
    margin = stat_or(first, "charisma", 0) - stat_or(second, "charisma", 0)
    averted = abs(margin) <= table.parley_margin
    kind = FieldAgreementKind.TRUCE if averted else FieldAgreementKind.PARLEY
    await agree(
        ctx,
        war.id,
        kind,
        commander=first.id,
        counterpart=second.id,
        place=sides[1].id,
        term=ctx.epoch + table.truce_epochs if averted else ctx.epoch,
        honour=margin,
    )
    text = f"{first.name} and {second.name} parleyed before battle" + (" and agreed a truce." if averted else "; the parley failed and they fought.")
    await note(ctx, text, key="parley.held", ids=[first.id, second.id, sides[0].id, sides[1].id])
    return averted


async def offer_terms(ctx: TickContext, siege: SiegeRow) -> FieldAgreementRow | None:
    known = await standing(ctx, siege.war_id, siege.besieged_entity_id, siege.besieged_entity_id, (FieldAgreementKind.SURRENDER,))
    if known is not None:
        return known
    row = await agree(
        ctx,
        siege.war_id,
        FieldAgreementKind.SURRENDER,
        commander=None,
        counterpart=siege.besieger_entity_id,
        place=siege.besieged_entity_id,
        term=None,
        honour=ctx.rules.field_diplomacy.surrender_honour,
    )
    await agree(
        ctx,
        siege.war_id,
        FieldAgreementKind.SAFE_CONDUCT,
        commander=None,
        counterpart=siege.besieger_entity_id,
        place=siege.besieged_entity_id,
        term=ctx.epoch + 1,
        honour=0,
    )
    return row


async def under_terms(ctx: TickContext, war_id: int, place_id: int) -> FieldAgreementRow | None:
    return await ctx.session.scalar(
        select(FieldAgreementRow)
        .where(FieldAgreementRow.war_id == war_id, FieldAgreementRow.place_entity_id == place_id, FieldAgreementRow.kind == FieldAgreementKind.SURRENDER)
        .limit(1)
    )


async def break_terms(ctx: TickContext, row: FieldAgreementRow, breaker_id: int) -> None:
    if row.state is not KEPT:
        return
    row.state = FieldAgreementState.BROKEN
    row.ended_epoch = ctx.epoch
    victim = row.place_entity_id or row.counterpart_entity_id or breaker_id
    await judged(ctx, breaker_id, victim, ActKind.OATHBREAKING)
    if victim != breaker_id:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=victim,
            subject_id=breaker_id,
            kind=MemoryKind.BETRAYED_ME,
            magnitude=-ctx.rules.field_diplomacy.broken_memory,
            epoch=ctx.epoch,
        )
    await note(ctx, "Terms given in the field were broken.", key="parley.broken", ids=[node for node in (breaker_id, victim) if node])


async def exchanges(ctx: TickContext, war: WarRow, sides: list[int]) -> int:
    if len(sides) < 2:
        return 0
    held_by = {
        side: list(
            await ctx.session.scalars(
                select(CaptiveRow).where(CaptiveRow.war_id == war.id, CaptiveRow.captor_entity_id == side, CaptiveRow.status == CaptiveStatus.HELD)
            )
        )
        for side in sides
    }
    first, second = sides[0], sides[1]
    if not held_by[first] or not held_by[second] or not ctx.rng(f"exchange.{war.id}.{ctx.epoch}").chance(ctx.rules.field_diplomacy.exchange_chance):
        return 0
    freed = 0
    for captive in [*held_by[first], *held_by[second]]:
        if held(captive.captive_entity_id) or "status" in captive.locked:
            continue
        captive.status = CaptiveStatus.RANSOMED
        freed += 1
    await agree(ctx, war.id, FieldAgreementKind.EXCHANGE, commander=None, counterpart=None, place=first, term=ctx.epoch, honour=freed)
    await note(ctx, "Captives and the dead were exchanged between the lines.", key="parley.exchange", ids=[first, second])
    return freed


async def fraternise(ctx: TickContext, war: WarRow, siege: SiegeRow) -> bool:
    table = ctx.rules.field_diplomacy
    if siege.rounds < table.fraternise_rounds or await standing(
        ctx, war.id, siege.besieged_entity_id, siege.besieged_entity_id, (FieldAgreementKind.FRATERNISATION,)
    ):
        return False
    await agree(
        ctx,
        war.id,
        FieldAgreementKind.FRATERNISATION,
        commander=None,
        counterpart=siege.besieger_entity_id,
        place=siege.besieged_entity_id,
        term=ctx.epoch + 1,
        honour=0,
    )
    for side in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None))):
        if "weariness" not in side.locked and not held(side.entity_id):
            side.weariness = clamp_percent(side.weariness + table.fraternise_weariness)
    return True


async def lapse(ctx: TickContext, row: FieldAgreementRow, war: WarRow | None) -> None:
    if row.state is not KEPT or "state" in row.locked:
        return
    commander = await ctx.session.get(EntityRow, row.commander_entity_id) if row.commander_entity_id is not None else None
    over = war is None or war.status is WarStatus.ENDED
    expired = row.term_epoch is not None and row.term_epoch < ctx.epoch
    gone = commander is not None and commander.status is not EntityStatus.CANON
    if row.kind is FieldAgreementKind.SURRENDER and not gone:
        return
    if over or expired or gone:
        row.state = FieldAgreementState.ENDED
        row.ended_epoch = ctx.epoch


@reads("table.army_officers", "table.captives", "table.field_agreements", "table.sieges", "table.war_sides", "table.wars")
@writes("table.captives", "table.field_agreements", "table.memories", "table.war_sides")
async def field_diplomacy(ctx: TickContext) -> None:
    wars = {row.id: row for row in await ctx.session.scalars(select(WarRow))}
    for row in list(await ctx.session.scalars(select(FieldAgreementRow).where(FieldAgreementRow.state == KEPT).order_by(FieldAgreementRow.id))):
        await lapse(ctx, row, wars.get(row.war_id) if row.war_id is not None else None)
    for war in sorted(wars.values(), key=lambda item: item.id):
        if war.status is not WarStatus.ONGOING:
            continue
        sides = list(
            await ctx.session.scalars(
                select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None)).order_by(WarSideRow.entity_id)
            )
        )
        if held(*sides):
            continue
        ctx.count("field_exchanges", await exchanges(ctx, war, sides))
        for siege in await ctx.session.scalars(select(SiegeRow).where(SiegeRow.war_id == war.id, SiegeRow.status == SiegeStatus.ONGOING)):
            if await fraternise(ctx, war, siege):
                ctx.count("fraternisations")
    await ctx.session.flush()
