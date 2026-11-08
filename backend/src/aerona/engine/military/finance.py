from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow, LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import MercenaryContractRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.military import ContractStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin, wealth_points
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.services.community_relations import change_relation


async def current_war_of(ctx: TickContext, owner_id: int) -> WarRow | None:
    statement = (
        select(WarRow)
        .join(WarSideRow, WarSideRow.war_id == WarRow.id)
        .where(WarSideRow.entity_id == owner_id, WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        .order_by(WarRow.id)
        .limit(1)
    )
    found: WarRow | None = await ctx.session.scalar(statement)
    return found


async def lender_for(ctx: TickContext, owner: EntityRow) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.FACTION,
            EntityRow.engine_kind == EngineKind.MERCHANT_GUILD,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == owner.world_id,
            EntityRow.id != owner.id,
        )
        .order_by(EntityRow.id)
    )
    lent = wealth_points(ctx.rules, ctx.rules.war_finance.war_loan_principal // 2)
    guilds = [guild for guild in await ctx.session.scalars(statement) if (stat(guild, "wealth") or 0) >= lent]
    return max(guilds, key=lambda guild: (stat(guild, "wealth") or 0, -guild.id), default=None)


async def war_credit(ctx: TickContext, owner: EntityRow, realm: PolityProfileRow, polity_id: int) -> bool:
    table = ctx.rules.war_finance
    war = await current_war_of(ctx, owner.id)
    lender = await lender_for(ctx, owner)
    if lender is not None:
        open_loan = await ctx.session.scalar(
            select(LoanRow.id).where(LoanRow.borrower_entity_id == polity_id, LoanRow.status == LoanStatus.OPEN, LoanRow.purpose == "war").limit(1)
        )
        if open_loan is None:
            ctx.session.add(
                LoanRow(
                    lender_entity_id=lender.id,
                    borrower_entity_id=polity_id,
                    principal=table.war_loan_principal,
                    interest_pct=ctx.rules.banking.interest_pct,
                    issued_epoch=ctx.epoch,
                    due_epoch=ctx.epoch + ctx.rules.banking.term_epochs,
                    status=LoanStatus.OPEN,
                    purpose="war",
                    war_id=war.id if war is not None else None,
                )
            )
            shift_stat(lender, "wealth", -wealth_points(ctx.rules, table.war_loan_principal // 2))
            realm.war_chest += table.war_loan_principal
            await ctx.chronicle(
                ChronicleKind.DEBT,
                f"{owner.name} borrowed from {lender.name} to keep its soldiers paid.",
                template_key="war.loan",
                entity_ids=(owner.id, lender.id),
                feed_category=FeedCategory.WAR,
            )
            ctx.count("war_loans")
            return True
    return await debase(ctx, owner, realm)


async def debase(ctx: TickContext, owner: EntityRow, realm: PolityProfileRow) -> bool:
    table = ctx.rules.war_finance
    society = await ctx.session.get(CommunitySocietyRow, owner.id)
    currency = await ctx.session.get(CurrencyRow, society.currency_id) if society is not None and society.currency_id is not None else None
    if currency is None or currency.purity <= table.debase_purity:
        return False
    currency.purity = clamp_int(currency.purity - table.debase_purity, 0, PERCENT)
    currency.trust = clamp_int(currency.trust - table.debase_trust, 0, PERCENT)
    currency.supply += round_half_up(currency.supply * table.debase_supply_pct / PERCENT)
    currency.debased_epoch = ctx.epoch
    realm.war_chest += table.war_loan_principal // 2
    await ctx.chronicle(
        ChronicleKind.TRADE,
        f"{owner.name} clipped its coin to pay its soldiers; {currency.name} is worth less and prices climb.",
        template_key="war.debasement",
        entity_ids=(owner.id,),
        feed_category=FeedCategory.WAR,
    )
    ctx.count("war_debasements")
    return True


async def pay_contracts(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.war_finance
    found = {"paid": 0, "unpaid": 0, "turned": 0, "ended": 0}
    rows = await ctx.session.scalars(select(MercenaryContractRow).where(MercenaryContractRow.status.in_([ContractStatus.ACTIVE, ContractStatus.UNPAID])))
    for row in list(rows):
        employer = await living_entity(ctx.session, row.employer_entity_id)
        army = await living_entity(ctx.session, row.army_entity_id)
        if employer is None or army is None:
            row.status = ContractStatus.ENDED
            found["ended"] += 1
            continue
        if "seasons_left" not in row.locked:
            row.seasons_left = max(0, row.seasons_left - ctx.rules.campaigns.seasons_per_war_epoch)
        pay = row.pay_per_season * max(1, ctx.rules.campaigns.seasons_per_war_epoch)
        if await take_coin(ctx.session, ctx.rules, employer, pay):
            company = await living_entity(ctx.session, row.company_entity_id)
            if company is not None:
                give_coin(ctx.rules, company, pay)
            row.unpaid_seasons = 0
            row.status = ContractStatus.ACTIVE
            found["paid"] += 1
        else:
            row.unpaid_seasons += 1
            if "loyalty" not in row.locked:
                row.loyalty = clamp_int(row.loyalty - table.mercenary_loyalty_loss, 0, PERCENT)
            row.status = ContractStatus.UNPAID
            found["unpaid"] += 1
            if row.loyalty <= table.mercenary_turn_loyalty:
                await turn_company(ctx, row, army, employer)
                found["turned"] += 1
                continue
        if row.seasons_left <= 0:
            row.status = ContractStatus.ENDED
            found["ended"] += 1
    return found


async def turn_company(ctx: TickContext, row: MercenaryContractRow, army: EntityRow, employer: EntityRow) -> None:
    row.status = ContractStatus.TURNED
    army_row = await ctx.session.get(ArmyRow, army.id)
    war = await current_war_of(ctx, employer.id)
    enemy_id = None
    if war is not None:
        sides = list(await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None))))
        mine = next((side.side for side in sides if side.entity_id == employer.id), None)
        enemy_id = next((side.entity_id for side in sides if side.side is not mine), None)
    if army_row is not None:
        army_row.owner_entity_id = enemy_id or row.company_entity_id or army_row.owner_entity_id
    if row.company_entity_id is not None:
        await change_relation(ctx, row.company_entity_id, employer.id, -ctx.rules.war_finance.mercenary_loyalty_loss, MemoryKind.CHEATED_US, note="left unpaid")
    await ctx.chronicle(
        ChronicleKind.WAR,
        f"{army.name}, left unpaid by {employer.name}, broke its contract and turned its swords elsewhere.",
        template_key="war.mercenaries_turned",
        entity_ids=(army.id, employer.id),
        feed_category=FeedCategory.WAR,
    )


def mercenary_pay(rules_pay_per_100: int, soldiers: int) -> int:
    return round_half_up(soldiers * rules_pay_per_100 / PERCENT)
