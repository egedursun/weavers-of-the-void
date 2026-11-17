from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import DebtRemedy
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.war import DebtStatus, WarCause
from aerona.engine.context import TickContext
from aerona.engine.economy.debt_law import DebtLaw, bind_debtor, coin_weight, debt_law_of, jail_debtor, jubilee_due
from aerona.engine.gods.economy import depletion_price, mechanics_of, shift_reserve
from aerona.engine.gods.queries import owners_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.stats import headcount, set_stats, stat, stat_or
from aerona.engine.primitives.strength import military_strength
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war, impose_tribute
from aerona.rules.registry import Rules

WEALTH_KEY = "wealth"
PROSPERITY_KEY = "prosperity"
ABUNDANCE_KEY = "abundance"
VALUE_KEY = "value"
DOUBLE = 2


@dataclass
class MarketTally:
    endings: dict[str, int] = field(default_factory=dict)


async def close_debt(ctx: TickContext, bond: BondRow, reason: str, status: DebtStatus = DebtStatus.FORGIVEN) -> None:
    bond.debt_status = status
    await BondRepository(ctx.session).deactivate(bond, ctx.epoch, reason)


def debt_words(bond: BondRow) -> str:
    return f"{bond.debt_amount or 0} {bond.debt_what or 'silver'}"


async def debt_ended(
    ctx: TickContext,
    key: str,
    bond: BondRow,
    debtor: EntityRow,
    creditor: EntityRow,
    *,
    others: Mapping[IncidentRole, int | None] | None = None,
    numbers: Mapping[str, int] | None = None,
) -> None:
    await record(
        ctx,
        f"market.{key}",
        roles={IncidentRole.BORROWER: debtor.id, IncidentRole.LENDER: creditor.id, **(others or {})},
        facts={
            "owed": bond.debt_amount or 0,
            "what": bond.debt_what or "silver",
            "overdue": max(0, ctx.epoch - (bond.debt_due_epoch or ctx.epoch)),
            **(numbers or {}),
        },
    )


async def _seizable(session: AsyncSession, debtor_id: int) -> EntityRow | None:
    owned = [await living_entity(session, bond.target_node_id) for bond in await active_bonds(session, [BondKind.OWNS], sources=[debtor_id])]
    resources = [item for item in owned if item is not None and item.entity_type is EntityType.RESOURCE]
    return max(resources, key=lambda item: (stat_or(item, VALUE_KEY, 0), -item.id), default=None)


async def wipe_at_jubilee(ctx: TickContext, bond: BondRow, debtor: EntityRow, creditor: EntityRow) -> None:
    await close_debt(ctx, bond, "wiped at the jubilee")
    await change_relation(ctx, debtor.id, creditor.id, ctx.rules.market.jubilee_relation, MemoryKind.GIFTED_ME, note="debt wiped at the jubilee")
    await debt_ended(ctx, "debt_jubilee", bond, debtor, creditor)


async def by_debt_law(ctx: TickContext, bond: BondRow, debtor: EntityRow, creditor: EntityRow, law: DebtLaw | None) -> str | None:
    table = ctx.rules.market
    owed = debt_words(bond)
    if law is not None and law.remedy is DebtRemedy.JUBILEE and jubilee_due(ctx, bond, law):
        await wipe_at_jubilee(ctx, bond, debtor, creditor)
        return "jubilee"
    if await relation(ctx.session, ctx.rules, creditor.id, debtor.id) >= table.debt_forgive_relation:
        await close_debt(ctx, bond, "forgiven")
        await change_relation(ctx, creditor.id, debtor.id, table.debt_forgive_gain, MemoryKind.GIFTED_ME, note="debt forgiven")
        await debt_ended(ctx, "debt_forgiven", bond, debtor, creditor)
        return "forgiven"
    if law is not None and law.remedy is DebtRemedy.BONDAGE:
        bound = await bind_debtor(ctx, debtor, creditor)
        await close_debt(ctx, bond, "paid in bondage", DebtStatus.REPAID)
        await change_relation(ctx, debtor.id, creditor.id, -table.debt_grudge, MemoryKind.HARMED_ME, note="bound for a debt")
        await debt_ended(ctx, "debt_bondage", bond, debtor, creditor, numbers={"bound": bound})
        return "bondage"
    if law is not None and law.remedy is DebtRemedy.PRISON:
        jailed = await jail_debtor(ctx, debtor, creditor, owed)
        if jailed is not None:
            await close_debt(ctx, bond, "debtor imprisoned")
            await change_relation(ctx, debtor.id, creditor.id, -table.debt_grudge, MemoryKind.HARMED_ME, note="jailed for a debt")
            await debt_ended(ctx, "debt_prison", bond, debtor, creditor, others={IncidentRole.ACCUSED: jailed.id})
            return "prison"
    return None


async def end_debt(ctx: TickContext, bond: BondRow, debtor: EntityRow, creditor: EntityRow) -> str | None:
    table = ctx.rules.market
    overdue_for = ctx.epoch - (bond.debt_due_epoch or ctx.epoch)
    owed = debt_words(bond)
    rng = ctx.rng(f"debt_end.{bond.id}")
    if overdue_for >= table.debt_expiry:
        await close_debt(ctx, bond, "lapsed")
        await debt_ended(ctx, "debt_lapsed", bond, debtor, creditor)
        return "lapsed"
    lawful = await by_debt_law(ctx, bond, debtor, creditor, await debt_law_of(ctx, debtor, creditor))
    if lawful is not None:
        return lawful
    weight = await coin_weight(ctx, bond)
    subject = await BondRepository(ctx.session).active_between(debtor.id, creditor.id, [BondKind.PAYS_TRIBUTE])
    stronger = await military_strength(ctx.session, ctx.rules, creditor) > await military_strength(ctx.session, ctx.rules, debtor)
    if stronger and not subject and rng.chance(round(table.debt_tribute_chance * weight)):
        await close_debt(ctx, bond, "turned to tribute")
        await impose_tribute(ctx, debtor, creditor, None, f"in return for the unpaid debt of {owed}")
        await change_relation(ctx, creditor.id, debtor.id, -table.debt_grudge, MemoryKind.DEMANDED_TRIBUTE, note="debt turned to tribute")
        await debt_ended(ctx, "debt_tribute", bond, debtor, creditor)
        return "tribute"
    resource = await _seizable(ctx.session, debtor.id)
    if resource is not None and rng.chance(round(table.debt_seize_chance * weight)):
        bonds = BondRepository(ctx.session)
        await bonds.close_between(debtor.id, resource.id, [BondKind.OWNS], ctx.epoch, "seized for a debt")
        await bonds.connect(BondDraft(creditor.id, resource.id, BondKind.OWNS, ctx.epoch, f"seized for the unpaid debt of {debtor.name}"))
        await close_debt(ctx, bond, "resource seized")
        await change_relation(ctx, creditor.id, debtor.id, -table.debt_grudge, MemoryKind.HARMED_ME, note="resource seized")
        await debt_ended(ctx, "debt_seized", bond, debtor, creditor, others={IncidentRole.INSTRUMENT: resource.id})
        return "seized"
    if rng.chance(round(table.debt_war_chance * weight)) and await declare_war(ctx, creditor.id, debtor.id, f"the unpaid debt of {owed}", cause=WarCause.DEBT):
        await close_debt(ctx, bond, "turned to war")
        await change_relation(ctx, creditor.id, debtor.id, -table.debt_grudge, MemoryKind.FOUGHT_US, note="debt war")
        await debt_ended(ctx, "debt_war", bond, debtor, creditor)
        return "war"
    return None


async def debt_endings(ctx: TickContext, tally: MarketTally) -> None:
    table = ctx.rules.market
    closed = 0
    for bond in sorted(await active_bonds(ctx.session, [BondKind.OWES]), key=lambda item: item.id):
        if closed >= table.debt_ending_cap:
            break
        if bond.debt_due_epoch is None or ctx.epoch - bond.debt_due_epoch < table.debt_patience:
            if not await jubilee_now(ctx, bond, tally):
                continue
            closed += 1
            continue
        debtor, creditor = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if debtor is None or creditor is None:
            continue
        ending = await end_debt(ctx, bond, debtor, creditor)
        if ending is not None:
            closed += 1
            tally.endings[ending] = tally.endings.get(ending, 0) + 1


async def jubilee_now(ctx: TickContext, bond: BondRow, tally: MarketTally) -> bool:
    debtor, creditor = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
    if debtor is None or creditor is None:
        return False
    law = await debt_law_of(ctx, debtor, creditor)
    if law is None or law.remedy is not DebtRemedy.JUBILEE or not jubilee_due(ctx, bond, law):
        return False
    await wipe_at_jubilee(ctx, bond, debtor, creditor)
    tally.endings["jubilee"] = tally.endings.get("jubilee", 0) + 1
    return True


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
    await shift_reserve(ctx.session, resource, -stat_or(resource, ABUNDANCE_KEY, 0))
    await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETING)
    if ResourceMechanic.DEPLETION_PRICE in await mechanics_of(ctx.session, resource):
        await depletion_price(ctx, resource)
    await add_flag(ctx.session, resource.id, EntityFlag.DEPLETED, ctx.epoch)
    owners = await owners_of(ctx.session, resource.id)
    for owner in owners:
        for key in (PROSPERITY_KEY, WEALTH_KEY):
            if stat(owner, key) is not None:
                set_stats(owner, **{key: clamp_int(stat_or(owner, key, 0) - table.depletion_loss, 0, PERCENT)})
    await record(
        ctx,
        "market.exhausted",
        roles={IncidentRole.SUBJECT: resource.id, IncidentRole.OWNER: [owner.id for owner in owners]},
        facts={"loss": table.depletion_loss},
        place=resource.location_id,
    )


async def _refill(ctx: TickContext, resource: EntityRow) -> bool:
    table = ctx.rules.market
    clawback = min(table.depleted_clawback, ctx.rules.world_effects.resource_regen)
    await shift_reserve(ctx.session, resource, -clawback)
    abundance = stat_or(resource, ABUNDANCE_KEY, 0)
    if abundance < table.refill_abundance:
        return False
    await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETED)
    await remove_flag(ctx.session, resource.id, EntityFlag.DEPLETING)
    await record(ctx, "market.refilled", roles={IncidentRole.SUBJECT: resource.id}, facts={"abundance": abundance}, place=resource.location_id)
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
                await record(
                    ctx,
                    "market.depleting",
                    roles={IncidentRole.SUBJECT: resource.id},
                    facts={"abundance": abundance, "demand": load},
                    place=resource.location_id,
                )
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
    "table.captives",
    "table.community_cohorts",
    "table.community_societies",
    "table.currencies",
    "table.entities",
    "table.entity_flags",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.nodes",
    "table.polity_members",
    "table.settlement_profiles",
)
@writes(
    "resource.abundance",
    "resource.value",
    "settlement.prosperity",
    "table.bonds",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_cohorts",
    "table.community_societies",
    "table.entities",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.settlement_profiles",
)
async def market(ctx: TickContext) -> None:
    tally = MarketTally()
    await debt_endings(ctx, tally)
    await resource_market(ctx)
    for ending, count in tally.endings.items():
        ctx.count(f"debt_{ending}", count)


async def write_off_debt(session: AsyncSession, rules: Rules, bond_id: int) -> str:
    bond = await session.get(BondRow, bond_id)
    if bond is None or bond.kind is not BondKind.OWES or bond.state is not BondState.ACTIVE:
        raise ValidationFailedError("No open debt was found.")
    ctx = await manual_context(session, "write_off_debt", rules, key=str(bond_id))
    debtor, creditor = await session.get(EntityRow, bond.source_node_id), await session.get(EntityRow, bond.target_node_id)
    await close_debt(ctx, bond, "written off by the Creator")
    if debtor is not None and creditor is not None and debtor.status is EntityStatus.CANON and creditor.status is EntityStatus.CANON:
        await change_relation(ctx, creditor.id, debtor.id, rules.market.debt_forgive_gain, MemoryKind.GIFTED_ME, note="debt written off")
    written = await record(
        ctx,
        "market.written_off",
        roles={IncidentRole.BORROWER: bond.source_node_id, IncidentRole.LENDER: bond.target_node_id},
        facts={"owed": bond.debt_amount or 0, "what": bond.debt_what or "silver"},
    )
    return written.text


async def run_market(session: AsyncSession, rules: Rules) -> None:
    await market(await manual_context(session, "market", rules))


PHASES = (Phase("market", market),)
