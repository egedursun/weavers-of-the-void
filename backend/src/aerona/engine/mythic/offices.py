from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.kind_concepts.nature import DUTY_DOMAINS, DUTY_FORMS
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import DomainActivityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mythic import CosmicOfficeRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import AfterlifeState
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mythic import CosmicOffice, OfficeChoice
from aerona.domain.enums.nature_kinds import OfficeDuty
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.kinds.nature import office_duty
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import shift_stat, stat


@dataclass
class OfficeTally:
    active: int = 0
    neglected: int = 0
    income: int = 0


async def offices(ctx: TickContext) -> list[CosmicOfficeRow]:
    rows = {row.office: row for row in await ctx.session.scalars(select(CosmicOfficeRow))}
    for office in CosmicOffice:
        if office not in rows:
            rows[office] = CosmicOfficeRow(office=office, holder_node_id=None, chosen_by=OfficeChoice.CREATOR, neglect=0, duty=0, locked=[])
            ctx.session.add(rows[office])
    return [rows[office] for office in CosmicOffice]


async def active(ctx: TickContext, node_id: int | None) -> bool:
    if node_id is None:
        return False
    son = await ctx.session.get(SonRow, node_id)
    if son is not None:
        return son.status is SonStatus.ACTIVE
    foreign = await ctx.session.get(ForeignGodRow, node_id)
    if foreign is not None:
        return foreign.status is ForeignGodStatus.AWAKE
    return await ctx.session.get(CreatorRow, node_id) is not None


async def office_power(ctx: TickContext, god_id: int | None, form: SpellForm) -> float:
    table = ctx.rules.cosmic_offices
    factor = 1.0
    for row in await ctx.session.scalars(select(CosmicOfficeRow)):
        duty, _ = await office_duty(ctx.session, row)
        if form not in DUTY_FORMS[duty]:
            continue
        factor *= max(0.0, 1 - row.neglect * table.neglect_effect_pct / PERCENT / PERCENT / 2)
        if god_id is not None and row.holder_node_id == god_id:
            factor *= 1 + table.rite_access / PERCENT
    return factor


async def give_essence(ctx: TickContext, god_id: int, amount: int) -> int:
    son = await ctx.session.get(SonRow, god_id)
    if son is not None:
        son.essence += amount
        return amount
    creator = await ctx.session.get(CreatorRow, god_id)
    if creator is not None:
        creator.essence += amount
        return amount
    return 0


async def income_of(ctx: TickContext, row: CosmicOfficeRow) -> int:
    duty, share = await office_duty(ctx.session, row)
    total = await ctx.session.scalar(
        select(func.coalesce(func.sum(DomainActivityRow.essence), 0)).where(
            DomainActivityRow.epoch == ctx.epoch, DomainActivityRow.domain.in_(list(DUTY_DOMAINS[duty]))
        )
    )
    return round_half_up(int(total or 0) * ctx.rules.cosmic_offices.income_pct / PERCENT * share / PERCENT)


DUTY_TOWNS = frozenset(
    {OfficeDuty.THE_SKY, OfficeDuty.OATHS, OfficeDuty.MESSAGES, OfficeDuty.JUDGEMENT, OfficeDuty.MEMORY, OfficeDuty.MAKING, OfficeDuty.HEALING}
)
UNREST_DUTIES = frozenset({OfficeDuty.OATHS, OfficeDuty.JUDGEMENT})
PIETY_DUTIES = frozenset({OfficeDuty.THE_SKY, OfficeDuty.MESSAGES, OfficeDuty.MEMORY})


async def neglect_towns(ctx: TickContext, duty: OfficeDuty, weight: float) -> None:
    table = ctx.rules.office_duties
    for community in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if held(community.id):
            continue
        if duty in UNREST_DUTIES:
            town = await ctx.session.get(SettlementProfileRow, community.id)
            if town is not None and "unrest" not in town.locked:
                town.unrest = clamp_int(town.unrest + round_half_up(table.unrest * weight), 0, PERCENT)
        elif duty in PIETY_DUTIES:
            shift_stat(community, "piety", -round_half_up(table.piety_loss * weight), 0, high=PERCENT)
        else:
            shift_stat(community, "prosperity", -round_half_up(table.prosperity_loss * weight), 0, high=PERCENT)


async def neglected(ctx: TickContext, row: CosmicOfficeRow) -> None:
    table = ctx.rules.cosmic_offices
    weight = row.neglect / PERCENT * table.neglect_effect_pct / PERCENT
    duty, _ = await office_duty(ctx.session, row)
    if duty in DUTY_TOWNS:
        await neglect_towns(ctx, duty, weight)
    elif duty is OfficeDuty.THE_DEAD:
        wandering = set(await ctx.session.scalars(select(SpiritProfileRow.spirit_entity_id).where(SpiritProfileRow.state == AfterlifeState.WANDERING)))
        for spirit in await canon(ctx.session, [EntityType.SPIRIT]):
            if spirit.id in wandering and not held(spirit.id) and stat(spirit, "unrest") is not None:
                shift_stat(spirit, "unrest", round_half_up(table.spirit_unrest * weight), 0, high=PERCENT)
    elif duty is OfficeDuty.THRESHOLDS:
        for route in await ctx.session.scalars(select(RouteRow)):
            route.danger = clamp_int(route.danger + round_half_up(table.route_danger * weight), 0, PERCENT)
    elif duty is OfficeDuty.THE_HUNT:
        for beast in await canon(ctx.session, [EntityType.BEAST]):
            if not held(beast.id) and stat(beast, "strength") is not None:
                shift_stat(beast, "strength", round_half_up(table.beast_strength * weight), 0, high=PERCENT)


async def tend_offices(ctx: TickContext, tally: OfficeTally) -> None:
    table = ctx.rules.cosmic_offices
    for row in await offices(ctx):
        working = await active(ctx, row.holder_node_id) and (row.holder_node_id is None or not held(row.holder_node_id))
        if working and row.holder_node_id is not None:
            tally.active += 1
            if "duty" not in row.locked:
                row.duty = clamp_int(row.duty + table.duty_gain, 0, PERCENT)
            if "neglect" not in row.locked:
                row.neglect = clamp_int(row.neglect - table.neglect_gain, 0, PERCENT)
            tally.income += await give_essence(ctx, row.holder_node_id, await income_of(ctx, row))
            continue
        tally.neglected += 1
        if "neglect" not in row.locked:
            row.neglect = clamp_int(row.neglect + table.neglect_gain, 0, PERCENT)
        if "duty" not in row.locked:
            row.duty = clamp_int(row.duty - table.duty_gain, 0, PERCENT)
        if row.neglect:
            await neglected(ctx, row)
    await ctx.session.flush()


async def appoint(ctx: TickContext, office: CosmicOffice, holder_id: int | None, chosen_by: OfficeChoice) -> CosmicOfficeRow:
    row = next(item for item in await offices(ctx) if item.office is office)
    row.holder_node_id, row.chosen_by, row.since_epoch = holder_id, chosen_by, ctx.epoch if holder_id is not None else None
    await ctx.session.flush()
    return row


async def vacant_office(ctx: TickContext) -> CosmicOffice | None:
    open_rows = [row for row in await offices(ctx) if row.holder_node_id is None and "holder_node_id" not in row.locked]
    return max(open_rows, key=lambda row: (row.neglect, list(CosmicOffice).index(row.office) * -1)).office if open_rows else None


async def conquer_offices(ctx: TickContext, winner_id: int, loser_id: int, stream: str) -> CosmicOffice | None:
    held_by_loser = [row for row in await offices(ctx) if row.holder_node_id == loser_id and "holder_node_id" not in row.locked]
    if not held_by_loser or not ctx.rng(f"{stream}.office").chance(ctx.rules.cosmic_offices.conquest_pct):
        return None
    row = held_by_loser[0]
    row.holder_node_id, row.chosen_by, row.since_epoch = winner_id, OfficeChoice.CONQUEST, ctx.epoch
    await note(
        ctx, f"The office of {spoken(row.office)} passed by conquest.", key="mythic.office_conquered", ids=[winner_id, loser_id], kind=ChronicleKind.CHALLENGE
    )
    return row.office
