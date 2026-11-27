from aerona.constants.units import PERCENT
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.departures import DepartureCondition, DepartureKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.departures.book import DepartureTally, conditions_of, open_departures, seat_name
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.mortal.life import years_to_step
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import set_ruler
from aerona.engine.primitives.maturity import past_office_age
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

WEAK_STABILITY = 30
RETURNING = frozenset({DepartureKind.ABDICATION, DepartureKind.RESIGNATION, DepartureKind.EXILE_BY_CHOICE, DepartureKind.WITHDRAWAL_TO_RELIGION})


async def weak_seat(ctx: TickContext, row: DepartureRow) -> bool:
    office = await ctx.session.get(OfficeRow, row.office_id) if row.office_id is not None else None
    if office is not None:
        if office.holder_entity_id is None:
            return True
        realm = await ctx.session.get(PolityProfileRow, office.polity_entity_id)
        return office.kind is OfficeKind.RULER and realm is not None and realm.stability < WEAK_STABILITY
    org = await ctx.session.get(OrgGovernanceRow, row.org_node_id) if row.org_node_id is not None else None
    return org is not None and org.head_node_id is None


async def return_to(ctx: TickContext, row: DepartureRow, holder: EntityRow) -> bool:
    office = await ctx.session.get(OfficeRow, row.office_id) if row.office_id is not None else None
    why = f"{holder.name} came back to the office they had left"
    if (office is None or office.kind is not OfficeKind.RULER) and past_office_age(ctx.rules, holder, years_to_step(ctx.environment)):
        return False
    if office is not None and office.kind is OfficeKind.RULER:
        realm = (await RealmBook.load(ctx.session)).realms.get(office.polity_entity_id)
        if realm is None or not set_ruler(ctx, realm, holder.id, why):
            return False
    elif office is not None:
        if "holder_entity_id" in (office.locked or []):
            return False
        office.holder_entity_id, office.since_epoch = holder.id, ctx.epoch
    else:
        org = await ctx.session.get(OrgGovernanceRow, row.org_node_id) if row.org_node_id is not None else None
        if org is None or "head_node_id" in (org.locked or []):
            return False
        org.head_node_id = holder.id
    row.returned_epoch = ctx.epoch
    await record(
        ctx,
        "office.returned",
        roles={IncidentRole.ACTOR: holder.id, IncidentRole.SUBJECT: row.polity_entity_id or row.org_node_id},
        facts={"kind": row.kind, "seat": seat_name(row.office_kind)},
    )
    return True


async def pay_pension(ctx: TickContext, row: DepartureRow, holder: EntityRow, tally: DepartureTally) -> None:
    if DepartureCondition.PENSION not in conditions_of(row) or row.polity_entity_id is None:
        return
    realm = await ctx.session.get(EntityRow, row.polity_entity_id)
    if realm is None or held(realm.id):
        return
    if await take_coin(ctx.session, ctx.rules, realm, ctx.rules.departures.pension):
        await give_coin(ctx.session, ctx.rules, holder, ctx.rules.departures.pension)
        tally.pensions += 1


async def rally(ctx: TickContext, row: DepartureRow, tally: DepartureTally) -> None:
    if row.kind is not DepartureKind.ABDICATION or row.standing < ctx.rules.departures.rally_standing or row.polity_entity_id is None:
        return
    realm = await ctx.session.get(PolityProfileRow, row.polity_entity_id)
    if realm is None or held(row.polity_entity_id) or "stability" in (realm.locked or []):
        return
    realm.stability = clamp_int(realm.stability - ctx.rules.departures.rally_stability_loss, 0, PERCENT)
    tally.rallies += 1


async def tend_departed(ctx: TickContext, tally: DepartureTally) -> None:
    table = ctx.rules.departures
    for row in await open_departures(ctx.session):
        holder = await living_entity(ctx.session, row.holder_node_id)
        if holder is None or held(holder.id):
            continue
        await pay_pension(ctx, row, holder, tally)
        await rally(ctx, row, tally)
        if "standing" not in (row.locked or []):
            row.standing = clamp_int(row.standing - table.standing_decay, 0, PERCENT)
        tempted = row.kind in RETURNING and await weak_seat(ctx, row) and ctx.rng(f"departures.return.{row.id}.{ctx.epoch}").chance(table.return_chance_pct)
        if tempted and await return_to(ctx, row, holder):
            tally.returned += 1
