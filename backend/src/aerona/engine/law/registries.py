from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.law_depth import OWED, PAID_IN_WORK, REGISTRY_TEXT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import RegistryRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.law.records import record_events
from aerona.engine.law.systems import realm_code, written_code
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.justice import community_ruler
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or


@dataclass
class RegistryTally:
    titled: int = 0
    enforced: int = 0
    settled: int = 0
    disputes: int = 0
    recorded: int = 0


async def register(
    ctx: TickContext,
    holder_id: int,
    kind: RegistryKind,
    *,
    owner_id: int | None,
    counterparty_id: int | None,
    subject_id: int | None = None,
    amount: int = 0,
) -> RegistryRow:
    row = RegistryRow(
        holder_entity_id=holder_id,
        kind=kind,
        owner_entity_id=owner_id,
        counterparty_entity_id=counterparty_id,
        subject_entity_id=subject_id,
        amount=amount,
        registered_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def title_of(ctx: TickContext, town_id: int) -> RegistryRow | None:
    rows = await ctx.session.scalars(
        select(RegistryRow)
        .where(RegistryRow.kind == RegistryKind.LAND_TITLE, RegistryRow.subject_entity_id == town_id)
        .order_by(RegistryRow.id.desc())
        .limit(1)
    )
    return rows.first()


async def dispute(ctx: TickContext, title: RegistryRow, claimant: EntityRow, town_id: int, tally: RegistryTally) -> None:
    table = ctx.rules.registries
    owner = await living_entity(ctx.session, title.owner_entity_id) if title.owner_entity_id is not None else None
    if "owner_entity_id" not in title.locked:
        title.owner_entity_id = claimant.id
    if owner is None:
        return
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=owner.id,
        subject_id=claimant.id,
        kind=MemoryKind.BETRAYED_ME,
        magnitude=-table.dispute_grudge,
        epoch=ctx.epoch,
        note="took a registered title to land",
    )
    town = await ctx.session.get(SettlementProfileRow, town_id)
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest + table.dispute_unrest, 0, PERCENT)
    tally.disputes += 1
    await note(
        ctx, f"{owner.name} disputed the land of {claimant.name}, whose title the court now records.", key="law.land_dispute", ids=[owner.id, claimant.id]
    )


async def title_towns(ctx: TickContext, tally: RegistryTally) -> None:
    members = await ctx.session.execute(select(PolityMemberRow.polity_entity_id, PolityMemberRow.member_entity_id).order_by(PolityMemberRow.member_entity_id))
    for polity_id, town_id in list(members):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.entity_type is not EntityType.SETTLEMENT or town.status is not EntityStatus.CANON or held(polity_id, town_id):
            continue
        if not await written_code(ctx.session, [polity_id, town_id]):
            continue
        ruler = await community_ruler(ctx.session, town_id)
        if ruler is None:
            continue
        title = await title_of(ctx, town_id)
        if title is None:
            if ctx.rng(f"law.title.{town_id}").chance(ctx.rules.registries.title_pct):
                await register(ctx, polity_id, RegistryKind.LAND_TITLE, owner_id=ruler.id, counterparty_id=None, subject_id=town_id)
                tally.titled += 1
        elif title.owner_entity_id != ruler.id:
            await dispute(ctx, title, ruler, town_id, tally)


async def collect(ctx: TickContext, row: RegistryRow, owner: EntityRow, debtor: EntityRow | None, coded: bool) -> int:
    table = ctx.rules.registries
    due = max(1, round_half_up(row.amount * table.enforce_pct / PERCENT))
    if not coded and (
        debtor is None or stat_or(owner, "strength", 0) <= stat_or(debtor, "strength", 0) or not ctx.rng(f"law.debt.{row.id}").chance(table.unregistered_pct)
    ):
        return 0
    if row.kind not in PAID_IN_WORK and (debtor is None or not await take_coin(ctx.session, ctx.rules, debtor, due)):
        return 0
    await give_coin(ctx.session, ctx.rules, owner, due)
    return min(due, row.amount)


async def enforce(ctx: TickContext, tally: RegistryTally) -> None:
    rows = await ctx.session.scalars(
        select(RegistryRow).where(RegistryRow.kind.in_(list(OWED)), RegistryRow.registered_epoch < ctx.epoch).order_by(RegistryRow.id)
    )
    for row in list(rows):
        owner = await living_entity(ctx.session, row.owner_entity_id) if row.owner_entity_id is not None else None
        debtor = await living_entity(ctx.session, row.counterparty_entity_id) if row.counterparty_entity_id is not None else None
        if owner is None or held(row.holder_entity_id, owner.id, row.counterparty_entity_id) or "amount" in row.locked:
            continue
        paid = await collect(ctx, row, owner, debtor, await realm_code(ctx.session, row.holder_entity_id))
        if paid <= 0:
            continue
        row.amount = max(0, row.amount - paid)
        tally.enforced += 1
        if row.amount == 0:
            await ctx.session.delete(row)
            tally.settled += 1
            who = debtor.name if debtor is not None else "the debtor"
            await note(
                ctx,
                f"The {REGISTRY_TEXT[row.kind]} owed by {who} to {owner.name} was settled.",
                key="law.settled",
                ids=[owner.id],
                kind=ChronicleKind.CIVILIZATION,
            )
    await ctx.session.flush()


async def keep_registries(ctx: TickContext, tally: RegistryTally) -> None:
    await title_towns(ctx, tally)
    await enforce(ctx, tally)
    tally.recorded += await record_events(ctx)
