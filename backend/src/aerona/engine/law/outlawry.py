from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.law import HUNTING
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import OutlawRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.engine.belonging.refuge import sheltered
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.law.prisons import imprison
from aerona.engine.mind.book import best_skill
from aerona.engine.mortal.standing import add_renown
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.records import death_path


@dataclass
class OutlawTally:
    declared: int = 0
    caught: int = 0
    escaped: int = 0
    heroes: int = 0


async def declare_outlaw(ctx: TickContext, mortal: EntityRow, polity_id: int | None, *, bounty: int | None = None) -> OutlawRow | None:
    if held(mortal.id) or await ctx.session.get(OutlawRow, mortal.id) is not None:
        return None
    row = OutlawRow(
        mortal_entity_id=mortal.id,
        polity_entity_id=polity_id,
        bounty=bounty if bounty is not None else ctx.rules.outlaws.bounty,
        renown=0,
        declared_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "law.outlawed", roles={IncidentRole.ACCUSED: mortal.id, IncidentRole.AUTHORITY: row.polity_entity_id}, place=mortal.location_id)
    return row


async def post_bounty(ctx: TickContext, row: OutlawRow, poster: EntityRow, amount: int) -> bool:
    if amount <= 0 or held(row.mortal_entity_id) or "private_bounty" in row.locked or not await take_coin(ctx.session, ctx.rules, poster, amount):
        return False
    row.private_bounty += amount
    return True


async def is_outlaw(ctx: TickContext, mortal_id: int) -> bool:
    return await ctx.session.get(OutlawRow, mortal_id) is not None


async def hunter_for(ctx: TickContext, row: OutlawRow) -> tuple[EntityRow, int] | None:
    if row.polity_entity_id is None:
        return None
    towns = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == row.polity_entity_id)))
    folk = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != row.mortal_entity_id,
            await present_among(ctx.session, towns),
        )
        .order_by(EntityRow.id)
    )
    best: tuple[EntityRow, int] | None = None
    for mortal in list(folk):
        if held(mortal.id) or await is_outlaw(ctx, mortal.id):
            continue
        skill = await best_skill(ctx.session, mortal.id, HUNTING)
        if skill >= ctx.rules.outlaws.hunter_skill and (best is None or skill > best[1]):
            best = (mortal, skill)
    return best


async def pay_bounty(ctx: TickContext, row: OutlawRow, hunter: EntityRow) -> None:
    realm = await ctx.session.get(EntityRow, row.polity_entity_id) if row.polity_entity_id is not None else None
    if realm is not None and await take_coin(ctx.session, ctx.rules, realm, row.bounty):
        await give_coin(ctx.session, ctx.rules, hunter, row.bounty)
    await give_coin(ctx.session, ctx.rules, hunter, row.private_bounty)


async def caught(ctx: TickContext, row: OutlawRow, outlaw: EntityRow, hunter: EntityRow, tally: OutlawTally) -> None:
    await pay_bounty(ctx, row, hunter)
    await ctx.session.delete(row)
    await ctx.session.flush()
    jailed = await imprison(ctx, outlaw)
    if jailed is None:
        await death_path(ctx, outlaw, f"hunted down for the bounty by {hunter.name}", None, "bounty", forced=True, manner=DeathCause.EXECUTION)
    tally.caught += 1
    await record(
        ctx,
        "law.bounty_claimed" if jailed is not None else "law.bounty_killed",
        roles={IncidentRole.ACTOR: hunter.id, IncidentRole.TARGET: outlaw.id, IncidentRole.AUTHORITY: row.polity_entity_id},
        facts={"bounty": row.bounty, "private_bounty": row.private_bounty},
        place=outlaw.location_id,
    )


async def shelter(ctx: TickContext, row: OutlawRow, outlaw: EntityRow, tally: OutlawTally) -> None:
    table = ctx.rules.outlaws
    if "renown" not in row.locked:
        row.renown = clamp_int(row.renown + table.escape_renown, 0, PERCENT)
    tally.escaped += 1
    if row.renown < table.hero_at:
        return
    await add_renown(ctx.session, outlaw.id, table.escape_renown, ctx.epoch, rules=ctx.rules)
    town = await ctx.session.get(SettlementProfileRow, outlaw.location_id or -1)
    if town is not None and "unrest" not in (town.locked or []) and not held(town.settlement_entity_id):
        town.unrest = clamp_int(town.unrest + table.hero_unrest, 0, PERCENT)
    tally.heroes += 1


async def hunt_outlaws(ctx: TickContext, tally: OutlawTally) -> None:
    rows = await ctx.session.scalars(select(OutlawRow).where(OutlawRow.declared_epoch < ctx.epoch).order_by(OutlawRow.mortal_entity_id))
    for row in list(rows):
        outlaw = await living_entity(ctx.session, row.mortal_entity_id)
        if outlaw is None:
            await ctx.session.delete(row)
            continue
        if held(outlaw.id, row.polity_entity_id) or await sheltered(ctx.session, outlaw.id):
            continue
        found = await hunter_for(ctx, row)
        chance = round_half_up(ctx.rules.outlaws.hunt_pct * found[1] / PERCENT) if found is not None else 0
        if found is not None and ctx.rng(f"law.hunt.{row.mortal_entity_id}").chance(chance):
            await caught(ctx, row, outlaw, found[0], tally)
        else:
            await shelter(ctx, row, outlaw, tally)
    await ctx.session.flush()


async def band_candidates(ctx: TickContext) -> dict[int, list[OutlawRow]]:
    found: dict[int, list[OutlawRow]] = {}
    for row in await ctx.session.scalars(select(OutlawRow).where(OutlawRow.polity_entity_id.is_not(None)).order_by(OutlawRow.mortal_entity_id)):
        if row.polity_entity_id is not None and not held(row.mortal_entity_id, row.polity_entity_id):
            found.setdefault(row.polity_entity_id, []).append(row)
    return {polity: rows for polity, rows in found.items() if len(rows) >= ctx.rules.outlaws.band_at}
