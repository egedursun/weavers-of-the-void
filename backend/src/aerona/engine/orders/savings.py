from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.orders import HoardRow, SavingRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.mind import Attribute
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.orders import HoardState, SavingForm
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.eras.effects import era_techniques
from aerona.engine.mind.split import MIDPOINT, attributes_of
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.war import ongoing_wars

WEALTH = "wealth"


@dataclass
class SavingTally:
    saved: int = 0
    hoarded: int = 0
    deposited: int = 0
    invested: int = 0
    lost: int = 0
    found: int = 0
    spent: int = 0


async def insecurity_of(ctx: TickContext, town_id: int | None) -> int:
    if town_id is None:
        return PERCENT
    profile = await ctx.session.get(SettlementProfileRow, town_id)
    disorder = (PERCENT - profile.public_order + profile.crime) // 2 if profile is not None else PERCENT // 2
    war = ctx.rules.saving.war_insecurity if await ongoing_wars(ctx.session, town_id) else 0
    return clamp_int(disorder + war, 0, PERCENT)


async def bank_in(ctx: TickContext, town_id: int | None) -> EntityRow | None:
    if town_id is None or Technique.BANKING not in await era_techniques(ctx.session, town_id):
        return None
    found = await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.FACTION,
            EntityRow.engine_kind == EngineKind.MERCHANT_GUILD,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == town_id,
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found


async def share_for(ctx: TickContext, household: HouseholdRow) -> int:
    table = ctx.rules.saving
    patience = (await attributes_of(ctx.session, household.head_node_id)).get(Attribute.PATIENCE, MIDPOINT) if household.head_node_id is not None else MIDPOINT
    return clamp_int(table.base_share + (patience - MIDPOINT) * table.patience_pct // MIDPOINT, 0, PERCENT)


async def form_for(ctx: TickContext, household: HouseholdRow) -> SavingForm:
    if await insecurity_of(ctx, household.settlement_node_id) >= ctx.rules.saving.insecure_from:
        return SavingForm.HOARD
    if await bank_in(ctx, household.settlement_node_id) is not None:
        return SavingForm.DEPOSIT
    return SavingForm.INVESTMENT


async def saving_of(ctx: TickContext, household: HouseholdRow) -> SavingRow:
    row = await ctx.session.get(SavingRow, household.id)
    if row is None:
        row = SavingRow(household_id=household.id, share_pct=await share_for(ctx, household), updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def bury(ctx: TickContext, household: HouseholdRow, amount: int) -> None:
    place = household.settlement_node_id
    if place is None:
        return
    hoard = await ctx.session.scalar(
        select(HoardRow)
        .where(HoardRow.holder_node_id == household.head_node_id, HoardRow.place_entity_id == place, HoardRow.state == HoardState.HIDDEN)
        .limit(1)
    )
    if hoard is None:
        hoard = HoardRow(holder_node_id=household.head_node_id, place_entity_id=place, hidden_epoch=ctx.epoch, locked=[])
        ctx.session.add(hoard)
    if "amount" not in hoard.locked:
        hoard.amount += amount


async def put_by(ctx: TickContext, household: HouseholdRow, row: SavingRow, tally: SavingTally) -> None:
    if WEALTH in (household.locked or []):
        return
    amount = min(household.wealth, round_half_up(max(0, household.income - household.expenses) * row.share_pct / PERCENT))
    if amount <= 0:
        return
    form = row.form if "form" in row.locked else await form_for(ctx, household)
    row.form = form
    household.wealth -= amount
    if form is SavingForm.HOARD:
        await bury(ctx, household, amount)
        tally.hoarded += amount
    elif form is SavingForm.DEPOSIT and (bank := await bank_in(ctx, household.settlement_node_id)) is not None:
        await give_coin(ctx.session, ctx.rules, bank, amount)
        tally.deposited += amount
    else:
        town = await ctx.session.get(SettlementProfileRow, household.settlement_node_id) if household.settlement_node_id is not None else None
        if town is not None and "investment_pool" not in town.locked:
            town.investment_pool += amount
        tally.invested += amount
    if "saved" not in row.locked:
        row.saved += amount
    row.updated_epoch = ctx.epoch
    tally.saved += 1


async def keep_hoards(ctx: TickContext, tally: SavingTally) -> None:
    for hoard in list(await ctx.session.scalars(select(HoardRow).where(HoardRow.state == HoardState.HIDDEN).order_by(HoardRow.id))):
        if "state" in hoard.locked or held(hoard.place_entity_id):
            continue
        owner = await ctx.session.get(EntityRow, hoard.holder_node_id) if hoard.holder_node_id is not None else None
        if owner is None or owner.status is not EntityStatus.CANON:
            hoard.state = HoardState.LOST
            tally.lost += 1
            continue
        household = await ctx.session.scalar(select(HouseholdRow).where(HouseholdRow.head_node_id == owner.id).limit(1))
        if household is not None and WEALTH not in (household.locked or []) and household.income < household.expenses and household.wealth <= 0:
            household.wealth += hoard.amount
            hoard.state = HoardState.SPENT
            tally.spent += 1


async def unearth_hoards(ctx: TickContext, place_ids: list[int], finder: EntityRow) -> int:
    found = 0
    for hoard in list(
        await ctx.session.scalars(select(HoardRow).where(HoardRow.state == HoardState.LOST, HoardRow.place_entity_id.in_(place_ids)).order_by(HoardRow.id))
    ):
        if "state" in hoard.locked or held(finder.id):
            continue
        hoard.state, hoard.found_by_node_id, hoard.found_epoch = HoardState.FOUND, finder.id, ctx.epoch
        await give_coin(ctx.session, ctx.rules, finder, hoard.amount)
        await record(
            ctx,
            "saving.hoard_found",
            roles={IncidentRole.ACTOR: finder.id, IncidentRole.PLACE: hoard.place_entity_id},
            facts={"amount": hoard.amount},
            steps=(StepDraft(StepAction.DISCOVER, actor=finder.id, amount=hoard.amount, unit=FactUnit.COIN, outcome=StepOutcome.SUCCESS),),
            place=hoard.place_entity_id,
        )
        found += hoard.amount
    return found


async def dig_for_hoards(ctx: TickContext, tally: SavingTally) -> None:
    places = sorted(set(await ctx.session.scalars(select(HoardRow.place_entity_id).where(HoardRow.state == HoardState.LOST))))
    for place_id in places:
        town = await ctx.session.get(EntityRow, place_id)
        if town is None or town.status is not EntityStatus.CANON or held(town.id):
            continue
        if ctx.rng(seed_of("hoard.find", town.id, ctx.epoch)).chance(ctx.rules.saving.find_chance):
            tally.found += await unearth_hoards(ctx, [town.id], town)


async def keep_savings(ctx: TickContext, tally: SavingTally) -> None:
    for household in list(await ctx.session.scalars(select(HouseholdRow).order_by(HouseholdRow.id))):
        if household.head_node_id is not None and held(household.head_node_id):
            continue
        row = await saving_of(ctx, household)
        if "share_pct" not in row.locked:
            row.share_pct = await share_for(ctx, household)
        await put_by(ctx, household, row, tally)
    await keep_hoards(ctx, tally)
    await dig_for_hoards(ctx, tally)
    await ctx.session.flush()
