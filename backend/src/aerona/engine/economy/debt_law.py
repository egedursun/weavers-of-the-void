from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import DebtRemedy, LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.context import TickContext
from aerona.engine.demography.bound import move_people, sync_bound_share
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.services.war import take_captive

REMEDIES = frozenset(item.value for item in DebtRemedy)
FREE_CLASSES = (SocialClass.FARMER, SocialClass.ARTISAN, SocialClass.MERCHANT)


@dataclass(frozen=True)
class DebtLaw:
    remedy: DebtRemedy
    jubilee_epochs: int


async def debt_law_of(ctx: TickContext, debtor: EntityRow, creditor: EntityRow) -> DebtLaw | None:
    for holder in (debtor, creditor):
        for node in (holder.id, holder.location_id):
            if node is None:
                continue
            remedy = await law_param(ctx.session, node, LawKind.DEBT_LAW, "remedy")
            if remedy is None or str(remedy) not in REMEDIES:
                continue
            epochs = await law_param(ctx.session, node, LawKind.DEBT_LAW, "jubilee_epochs")
            return DebtLaw(DebtRemedy(str(remedy)), int(epochs) if isinstance(epochs, int) and not isinstance(epochs, bool) else 1)
    return None


async def coin_weight(ctx: TickContext, bond: BondRow) -> float:
    if bond.debt_currency_id is None:
        return 1.0
    coin = await ctx.session.get(CurrencyRow, bond.debt_currency_id)
    if coin is None:
        return 1.0
    return max(0.0, 1 - (PERCENT - coin.trust) / PERCENT * ctx.rules.market.currency_trust_pct / PERCENT)


def jubilee_due(ctx: TickContext, bond: BondRow, law: DebtLaw) -> bool:
    return ctx.epoch - bond.epoch >= max(1, law.jubilee_epochs)


async def bind_debtor(ctx: TickContext, debtor: EntityRow, creditor: EntityRow) -> int:
    table = ctx.rules.market
    add_prosperity(ctx.rules, creditor, table.bondage_labour_gain)
    if debtor.entity_type is EntityType.MORTAL:
        if debtor.social_class is SocialClass.SERF_OR_SLAVE:
            return 0
        debtor.social_class = SocialClass.SERF_OR_SLAVE
        return 1
    rows = await cohorts_of(ctx.session, debtor.id)
    bound = 0
    for source in FREE_CLASSES:
        bound += await move_people(ctx, debtor, rows, source=source, target=SocialClass.SERF_OR_SLAVE, share=table.bondage_share_pct / PERCENT)
    sync_bound_share(await ctx.session.get(CommunitySocietyRow, debtor.id), rows)
    return bound


async def notable_of(ctx: TickContext, debtor: EntityRow) -> EntityRow | None:
    if debtor.entity_type is EntityType.MORTAL:
        return debtor
    held = select(CaptiveRow.captive_entity_id).where(CaptiveRow.status == CaptiveStatus.HELD)
    statement = (
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await folk_of(ctx.session, debtor),
            EntityRow.id.not_in(held),
        )
        .order_by(EntityRow.importance.desc().nulls_last(), EntityRow.id)
        .limit(1)
    )
    found: EntityRow | None = await ctx.session.scalar(statement)
    return found


async def jail_debtor(ctx: TickContext, debtor: EntityRow, creditor: EntityRow, owed: str) -> EntityRow | None:
    notable = await notable_of(ctx, debtor)
    if notable is None or notable.id == creditor.id:
        return None
    await take_captive(ctx, creditor, notable, None, description=f"held in debtors' prison for {owed}", home_id=debtor.id)
    town = await ctx.session.get(SettlementProfileRow, debtor.id)
    if town is not None and "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest + ctx.rules.market.prison_unrest, 0, PERCENT)
    return notable
