from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.society import COMMODITY_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import Commodity, ResourceMechanic
from aerona.domain.enums.war import DebtStatus, WarCause
from aerona.engine.context import TickContext
from aerona.engine.gods.economy import depletion_price, mechanics_of
from aerona.engine.gods.queries import owners_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.stats import headcount, set_stats, stat, stat_or
from aerona.engine.primitives.strength import military_strength
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war, impose_tribute
from aerona.rules.registry import Rules

TRADING_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
WEALTH_KEY = "wealth"
PROSPERITY_KEY = "prosperity"
ABUNDANCE_KEY = "abundance"
VALUE_KEY = "value"
NEUTRAL_PRICE = PERCENT
DOUBLE = 2


@dataclass
class MarketTally:
    flows: int = 0
    moved: int = 0
    credit: int = 0
    noted: int = 0
    endings: dict[str, int] = field(default_factory=dict)


def payment_key(entity: EntityRow) -> str | None:
    if stat(entity, WEALTH_KEY) is not None:
        return WEALTH_KEY
    return PROSPERITY_KEY if stat(entity, PROSPERITY_KEY) is not None else None


def commodity_word(commodity: Commodity) -> str:
    return COMMODITY_LABELS[commodity].lower()


async def open_debt(session: AsyncSession, debtor_id: int, creditor_id: int) -> BondRow | None:
    found = await active_bonds(session, [BondKind.OWES], sources=[debtor_id], targets=[creditor_id])
    return found[0] if found else None


async def sell_on_credit(ctx: TickContext, buyer: EntityRow, seller: EntityRow, commodity: Commodity, moved: int, *, tally: MarketTally) -> None:
    table = ctx.rules.market
    if await open_debt(ctx.session, buyer.id, seller.id) is not None:
        return
    amount = max(1, round(moved / table.credit_divisor))
    due = ctx.epoch + table.credit_term
    what = commodity_word(commodity)
    bond = await BondRepository(ctx.session).connect(
        BondDraft(buyer.id, seller.id, BondKind.OWES, ctx.epoch, f"bought {what} on credit", debt_amount=amount, debt_what=what, debt_due_epoch=due)
    )
    bond.debt_status = DebtStatus.OPEN
    tally.credit += 1
    text = f"{buyer.name} bought {what} from {seller.name} on credit and owes {amount} {what}, due Epoch {due}."
    await ctx.chronicle(ChronicleKind.DEBT, text, template_key="market.credit", entity_ids=[buyer.id, seller.id])
    if tally.noted < table.note_cap:
        tally.noted += 1
        await note(
            ctx, f"{buyer.name} bought {what} from {seller.name} on credit.", key="market.credit_note", ids=[buyer.id, seller.id], kind=ChronicleKind.TRADE
        )


async def flow_good(
    ctx: TickContext, pair: tuple[tuple[EntityRow, CommunitySocietyRow], tuple[EntityRow, CommunitySocietyRow]], commodity: Commodity, tally: MarketTally
) -> bool:
    table = ctx.rules.market
    (first, first_row), (second, second_row) = pair
    first_price, second_price = first_row.price(commodity) or NEUTRAL_PRICE, second_row.price(commodity) or NEUTRAL_PRICE
    seller, seller_row, buyer, buyer_row, low, high = (
        (first, first_row, second, second_row, first_price, second_price)
        if first_price <= second_price
        else (second, second_row, first, first_row, second_price, first_price)
    )
    if high * PERCENT < low * table.flow_price_gap_pct:
        return False
    surplus = seller_row.stock(commodity) - table.flow_reserve
    moved = min(table.flow_cap, surplus * table.flow_share_pct // PERCENT) if surplus > 0 else 0
    if moved <= 0:
        return False
    setattr(seller_row, f"stock_{commodity.value}", seller_row.stock(commodity) - moved)
    setattr(buyer_row, f"stock_{commodity.value}", buyer_row.stock(commodity) + moved)
    tally.flows += 1
    tally.moved += moved
    add_prosperity(ctx.rules, seller, table.flow_prosperity)
    key = payment_key(buyer)
    rng = ctx.rng(f"credit.{buyer.id}.{seller.id}.{commodity.value}")
    if key is not None and (stat_or(buyer, key, 0) < table.credit_threshold or rng.chance(table.credit_chance)):
        await sell_on_credit(ctx, buyer, seller, commodity, moved, tally=tally)
    elif key is not None:
        set_stats(buyer, **{key: clamp_int(stat_or(buyer, key, 0) - max(1, round(moved / table.flow_payment_divisor)), 0, PERCENT)})
    if commodity is Commodity.FOOD and high * PERCENT >= low * table.famine_gap_pct and tally.noted < table.note_cap:
        tally.noted += 1
        await note(
            ctx,
            f"{buyer.name} brought grain from {seller.name} in a time of famine.",
            key="market.famine_grain",
            ids=[buyer.id, seller.id],
            kind=ChronicleKind.TRADE,
        )
    return True


async def trade_flow(ctx: TickContext, tally: MarketTally) -> None:
    seen: set[tuple[int, int]] = set()
    for bond in sorted(await active_bonds(ctx.session, [BondKind.TRADES_WITH]), key=lambda item: item.id):
        key = (min(bond.source_node_id, bond.target_node_id), max(bond.source_node_id, bond.target_node_id))
        if key in seen:
            continue
        seen.add(key)
        first, second = await living_entity(ctx.session, key[0]), await living_entity(ctx.session, key[1])
        if first is None or second is None or first.entity_type not in TRADING_TYPES or second.entity_type not in TRADING_TYPES:
            continue
        first_row, second_row = await ctx.session.get(CommunitySocietyRow, first.id), await ctx.session.get(CommunitySocietyRow, second.id)
        if first_row is None or second_row is None:
            continue
        for commodity in Commodity:
            await flow_good(ctx, ((first, first_row), (second, second_row)), commodity, tally)
    if tally.flows:
        await note(
            ctx,
            f"{tally.flows} trade roads carried goods to market: {tally.moved} loads moved from cheap stores to dear ones.",
            key="market.flows",
            kind=ChronicleKind.TRADE,
        )


async def close_debt(ctx: TickContext, bond: BondRow, reason: str, status: DebtStatus = DebtStatus.FORGIVEN) -> None:
    bond.debt_status = status
    await BondRepository(ctx.session).deactivate(bond, ctx.epoch, reason)


def debt_words(bond: BondRow) -> str:
    return f"{bond.debt_amount or 0} {bond.debt_what or 'silver'}"


async def _debt_chronicle(ctx: TickContext, text: str, key: str, ids: list[int], noted: bool = True) -> None:
    await ctx.chronicle(ChronicleKind.DEBT, text, template_key=f"market.{key}", entity_ids=ids)
    if noted:
        await note(ctx, text, key=f"market.{key}_note", ids=ids, kind=ChronicleKind.DEBT)


async def _seizable(session: AsyncSession, debtor_id: int) -> EntityRow | None:
    owned = [await living_entity(session, bond.target_node_id) for bond in await active_bonds(session, [BondKind.OWNS], sources=[debtor_id])]
    resources = [item for item in owned if item is not None and item.entity_type is EntityType.RESOURCE]
    return max(resources, key=lambda item: (stat_or(item, VALUE_KEY, 0), -item.id), default=None)


async def end_debt(ctx: TickContext, bond: BondRow, debtor: EntityRow, creditor: EntityRow) -> str | None:
    table = ctx.rules.market
    overdue_for = ctx.epoch - (bond.debt_due_epoch or ctx.epoch)
    owed = debt_words(bond)
    rng = ctx.rng(f"debt_end.{bond.id}")
    if overdue_for >= table.debt_expiry:
        await close_debt(ctx, bond, "lapsed")
        await _debt_chronicle(
            ctx,
            f"The debt of {owed} {debtor.name} owed to {creditor.name} lapsed; nobody claims it any more.",
            "debt_lapsed",
            [debtor.id, creditor.id],
            noted=False,
        )
        return "lapsed"
    if await relation(ctx.session, ctx.rules, creditor.id, debtor.id) >= table.debt_forgive_relation:
        await close_debt(ctx, bond, "forgiven")
        await change_relation(ctx, creditor.id, debtor.id, table.debt_forgive_gain, MemoryKind.GIFTED_ME, note="debt forgiven")
        await _debt_chronicle(ctx, f"{creditor.name} forgave the debt of {owed} owed by {debtor.name}.", "debt_forgiven", [debtor.id, creditor.id])
        return "forgiven"
    subject = await BondRepository(ctx.session).active_between(debtor.id, creditor.id, [BondKind.PAYS_TRIBUTE])
    stronger = await military_strength(ctx.session, ctx.rules, creditor) > await military_strength(ctx.session, ctx.rules, debtor)
    if stronger and not subject and rng.chance(table.debt_tribute_chance):
        await close_debt(ctx, bond, "turned to tribute")
        await impose_tribute(ctx, debtor, creditor, None, f"in return for the unpaid debt of {owed}")
        await change_relation(ctx, creditor.id, debtor.id, -table.debt_grudge, MemoryKind.DEMANDED_TRIBUTE, note="debt turned to tribute")
        await _debt_chronicle(
            ctx, f"{debtor.name} could not pay its debt of {owed}; {creditor.name} bound it to tribute.", "debt_tribute", [debtor.id, creditor.id]
        )
        return "tribute"
    resource = await _seizable(ctx.session, debtor.id)
    if resource is not None and rng.chance(table.debt_seize_chance):
        bonds = BondRepository(ctx.session)
        await bonds.close_between(debtor.id, resource.id, [BondKind.OWNS], ctx.epoch, "seized for a debt")
        await bonds.connect(BondDraft(creditor.id, resource.id, BondKind.OWNS, ctx.epoch, f"seized for the unpaid debt of {debtor.name}"))
        await close_debt(ctx, bond, "resource seized")
        await change_relation(ctx, creditor.id, debtor.id, -table.debt_grudge, MemoryKind.HARMED_ME, note="resource seized")
        text = f"{creditor.name} seized {debtor.name}'s {resource.name} for the unpaid debt of {owed}."
        await _debt_chronicle(ctx, text, "debt_seized", [debtor.id, creditor.id, resource.id])
        return "seized"
    if rng.chance(table.debt_war_chance) and await declare_war(ctx, creditor.id, debtor.id, f"the unpaid debt of {owed}", cause=WarCause.DEBT):
        await close_debt(ctx, bond, "turned to war")
        await change_relation(ctx, creditor.id, debtor.id, -table.debt_grudge, MemoryKind.FOUGHT_US, note="debt war")
        text = f"The unpaid debt of {owed} turned to war: {creditor.name} declared {debtor.name} its enemy to take it by the sword."
        await _debt_chronicle(ctx, text, "debt_war", [debtor.id, creditor.id])
        return "war"
    return None


async def debt_endings(ctx: TickContext, tally: MarketTally) -> None:
    table = ctx.rules.market
    closed = 0
    for bond in sorted(await active_bonds(ctx.session, [BondKind.OWES]), key=lambda item: item.id):
        if closed >= table.debt_ending_cap:
            break
        if bond.debt_due_epoch is None or ctx.epoch - bond.debt_due_epoch < table.debt_patience:
            continue
        debtor, creditor = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if debtor is None or creditor is None:
            continue
        ending = await end_debt(ctx, bond, debtor, creditor)
        if ending is not None:
            closed += 1
            tally.endings[ending] = tally.endings.get(ending, 0) + 1


async def owner_population(session: AsyncSession) -> dict[int, int]:
    totals: dict[int, int] = {}
    statement = select(BondRow).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    for bond in await session.scalars(statement):
        owner = await living_entity(session, bond.source_node_id)
        if owner is not None:
            totals[bond.target_node_id] = totals.get(bond.target_node_id, 0) + headcount(owner)
    return totals


async def exhaust(ctx: TickContext, resource: EntityRow) -> None:
    table = ctx.rules.market
    set_stats(resource, abundance=0)
    await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETING)
    if ResourceMechanic.DEPLETION_PRICE in await mechanics_of(ctx.session, resource):
        await depletion_price(ctx, resource)
    await add_flag(ctx.session, resource.id, EntityFlag.DEPLETED, ctx.epoch)
    owners = await owners_of(ctx.session, resource.id)
    for owner in owners:
        for key in (PROSPERITY_KEY, WEALTH_KEY):
            if stat(owner, key) is not None:
                set_stats(owner, **{key: clamp_int(stat_or(owner, key, 0) - table.depletion_loss, 0, PERCENT)})
    lost = f"; {', '.join(owner.name for owner in owners)} lost what it gave" if owners else ""
    text = f"{resource.name} was exhausted: its last vein was scraped away{lost}."
    await ctx.chronicle(ChronicleKind.RESOURCE, text, template_key="market.exhausted", entity_ids=[resource.id, *(owner.id for owner in owners)])
    await note(ctx, text, key="market.exhausted_note", ids=[resource.id], kind=ChronicleKind.RESOURCE)


async def _refill(ctx: TickContext, resource: EntityRow) -> bool:
    table = ctx.rules.market
    clawback = min(table.depleted_clawback, ctx.rules.world_effects.resource_regen)
    abundance = clamp_int(stat_or(resource, ABUNDANCE_KEY, 0) - clawback, 0, PERCENT)
    set_stats(resource, abundance=abundance)
    if abundance < table.refill_abundance:
        return False
    await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETED)
    await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETING)
    await note(ctx, f"{resource.name} filled again after long ages; the veins that once ran dry give once more.", key="market.refilled", ids=[resource.id])
    return True


def priced(value: int, abundance: int, owned: bool, rules: Rules) -> int:
    table = rules.market
    if abundance < table.price_scarce_abundance:
        return clamp_int(value + table.price_step, 0, PERCENT)
    if abundance > table.price_plenty_abundance and owned:
        return max(min(value, table.price_floor), value - table.price_step)
    return value


async def resource_market(ctx: TickContext) -> None:
    table = ctx.rules.market
    demand = await owner_population(ctx.session)
    depleted = await flags_by_entity(ctx.session, EntityFlag.DEPLETED)
    depleting = await flags_by_entity(ctx.session, EntityFlag.DEPLETING)
    exhausted = 0
    for resource in await canon(ctx.session, [EntityType.RESOURCE]):
        if resource.id in depleted:
            await _refill(ctx, resource)
            continue
        abundance = stat_or(resource, ABUNDANCE_KEY, 0)
        value = stat(resource, VALUE_KEY)
        if value is not None:
            set_stats(resource, value=priced(value, abundance, resource.id in demand, ctx.rules))
        load = demand.get(resource.id, 0) // table.demand_population
        if abundance <= table.depletion_abundance and load >= table.depletion_demand:
            if resource.id not in depleting:
                await add_flag(ctx.session, resource.id, EntityFlag.DEPLETING, ctx.epoch)
                await note(ctx, f"{resource.name} hit bottom; its owners scrape at it until it is gone.", key="market.depleting", ids=[resource.id])
            elif exhausted < table.depletion_cap and ctx.rng(f"exhaust.{resource.id}").chance(table.depletion_chance):
                await exhaust(ctx, resource)
                exhausted += 1
        elif resource.id in depleting and abundance > table.depletion_abundance * DOUBLE:
            await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETING)
    ctx.count("exhausted", exhausted)


@reads(
    "cult.followers",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "resource.abundance",
    "resource.value",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.community_societies",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
)
@writes(
    "resource.abundance",
    "resource.value",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
@reads(
    "cult.followers",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "resource.abundance",
    "resource.value",
    "settlement.population",
    "settlement.prosperity",
)
@writes("resource.abundance", "resource.value", "settlement.prosperity")
async def market(ctx: TickContext) -> None:
    tally = MarketTally()
    await trade_flow(ctx, tally)
    await debt_endings(ctx, tally)
    await resource_market(ctx)
    ctx.count("flows", tally.flows)
    ctx.count("credit", tally.credit)
    for ending, count in tally.endings.items():
        ctx.count(f"debt_{ending}", count)


async def write_off_debt(session: AsyncSession, rules: Rules, bond_id: int) -> str:
    bond = await session.get(BondRow, bond_id)
    if bond is None or bond.kind is not BondKind.OWES or bond.state is not BondState.ACTIVE:
        raise ValidationFailedError("No open debt was found.")
    ctx = await manual_context(session, "write_off_debt", rules, key=str(bond_id))
    debtor, creditor = await session.get(EntityRow, bond.source_node_id), await session.get(EntityRow, bond.target_node_id)
    await close_debt(ctx, bond, "written off by the Creator")
    names = (debtor.name if debtor else "a debtor", creditor.name if creditor else "a creditor")
    if debtor is not None and creditor is not None and debtor.status is EntityStatus.CANON and creditor.status is EntityStatus.CANON:
        await change_relation(ctx, creditor.id, debtor.id, rules.market.debt_forgive_gain, MemoryKind.GIFTED_ME, note="debt written off")
    text = f"The Creator wrote off the debt of {debt_words(bond)} {names[0]} owed to {names[1]}."
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key="market.written_off", entity_ids=[bond.source_node_id, bond.target_node_id])
    return text


async def run_market(session: AsyncSession, rules: Rules) -> None:
    await market(await manual_context(session, "market", rules))


PHASES = (Phase("market", market),)
