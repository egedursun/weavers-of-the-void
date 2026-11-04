from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, WarRow
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import heirs_by_custom, inheritance_of
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm
from aerona.engine.polity.laws import LawBook, law_param
from aerona.engine.primitives.levies import demobilise
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import headcount, set_stats, shift_stat, stat
from aerona.rules.registry import Rules

LABOUR_STEP = 30
TENURE_CLASSES = {
    "feudal": (SocialClass.NOBLE, SocialClass.FARMER),
    "communal": (SocialClass.FARMER, SocialClass.NOBLE),
    "freehold": (SocialClass.MERCHANT, SocialClass.NOBLE),
}


def nudge(society: CommunitySocietyRow, social_class: SocialClass, amount: int) -> None:
    key = f"satisfaction_{social_class.value}"
    setattr(society, key, clamp_int(getattr(society, key) + amount, 0, PERCENT))


async def tenure_and_serfdom(ctx: TickContext, member_id: int, laws: LawBook) -> None:
    table = ctx.rules.legislation
    society = await ctx.session.get(CommunitySocietyRow, member_id)
    if society is None:
        return
    tenure = laws.in_force(member_id, LawKind.LAND_TENURE)
    if tenure is not None:
        kind = str(tenure.params.get("tenure", "communal"))
        gainer, loser = TENURE_CLASSES.get(kind, TENURE_CLASSES["communal"])
        shift = round_half_up(table.tenure_shift * tenure.enforcement / PERCENT)
        nudge(society, gainer, shift)
        nudge(society, loser, -shift)
        if kind == "freehold":
            place = await living_entity(ctx.session, member_id)
            if place is not None:
                shift_stat(place, "prosperity", table.freehold_prosperity, ctx.rules.society.default_stat)
    serfdom = laws.in_force(member_id, LawKind.SERFDOM)
    if serfdom is None:
        return
    bound = society.share(SocialClass.SERF_OR_SLAVE)
    if bool(serfdom.params.get("allowed")):
        days = int(serfdom.params.get("labour_days", LABOUR_STEP))
        nudge(society, SocialClass.SERF_OR_SLAVE, -table.serf_resentment * days // LABOUR_STEP)
        town = await ctx.session.get(SettlementProfileRow, member_id)
        income = round_half_up(days * bound / PERCENT * table.serf_labour_pct / PERCENT * serfdom.enforcement / PERCENT)
        if town is not None and income > 0 and "treasury" not in town.locked:
            town.treasury += income
        return
    slavery = laws.param(member_id, LawKind.SLAVERY, "status")
    if bound > 0 and slavery in {None, "banned"}:
        freed = round(bound * table.serf_free_pct / PERCENT * serfdom.enforcement / PERCENT, 2)
        society.share_serf_or_slave = round(bound - freed, 2)
        society.share_farmer = round(society.share_farmer + freed, 2)


def feudal_levy(laws: LawBook, node_id: int, rules: Rules) -> float:
    tenure = laws.param(node_id, LawKind.LAND_TENURE, "tenure")
    if tenure != "feudal":
        return 1.0
    return 1 + rules.legislation.feudal_levy_pct / PERCENT * laws.weight(node_id, LawKind.LAND_TENURE)


async def jubilee(ctx: TickContext, realm: Realm, laws: LawBook) -> int:
    table = ctx.rules.legislation
    row = laws.in_force(realm.entity.id, LawKind.DEBT_LAW)
    if row is None or row.params.get("remedy") != "jubilee":
        return 0
    every = max(1, int(row.params.get("jubilee_epochs", 2)))
    if (ctx.epoch - row.enacted_epoch) % every != 0 or ctx.epoch == row.enacted_epoch:
        return 0
    debtors = [realm.entity.id, *realm.members]
    forgiven = 0
    for loan in await ctx.session.scalars(select(LoanRow).where(LoanRow.status == LoanStatus.OPEN, LoanRow.borrower_entity_id.in_(debtors))):
        loan.status = LoanStatus.FORGIVEN
        forgiven += 1
    for member_id in realm.members:
        society = await ctx.session.get(CommunitySocietyRow, member_id)
        if society is not None:
            nudge(society, SocialClass.FARMER, table.jubilee_relief)
            nudge(society, SocialClass.SERF_OR_SLAVE, table.jubilee_relief)
            if society.share(SocialClass.SERF_OR_SLAVE) > 0 and laws.param(member_id, LawKind.SLAVERY, "status") == "debt_only":
                freed = society.share_serf_or_slave
                society.share_serf_or_slave = 0.0
                society.share_farmer = round(society.share_farmer + freed, 2)
    await note(
        ctx,
        f"{realm.entity.name} proclaimed a jubilee: {forgiven} debts were struck from the ledgers.",
        key="polity.jubilee",
        ids=[realm.entity.id, row.law_entity_id],
    )
    return forgiven


async def standing_share(session: AsyncSession, rules: Rules, owner_id: int) -> int:
    share = await law_param(session, owner_id, LawKind.STANDING_ARMY, "share")
    if share is None:
        return 0
    polity = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == owner_id).limit(1))
    profile = await session.get(PolityProfileRow, polity) if polity is not None else None
    if profile is None or profile.tier < rules.realm_tiers.standing_army:
        return 0
    return int(share)


async def standing_floor(session: AsyncSession, rules: Rules, owner: EntityRow | None) -> int:
    if owner is None:
        return 0
    share = await standing_share(session, rules, owner.id)
    return round_half_up(headcount(owner) * share / PERCENT) if share else 0


async def levy_terms(ctx: TickContext, realm: Realm, laws: LawBook) -> int:
    table = ctx.rules.legislation
    returned = 0
    for member_id in realm.members:
        duration = laws.param(member_id, LawKind.LEVY_LAW, "duration")
        if duration is None:
            continue
        owner = await living_entity(ctx.session, member_id)
        floor = await standing_floor(ctx.session, ctx.rules, owner)
        armies = await ctx.session.scalars(
            select(ArmyRow)
            .join(WarRow, WarRow.id == ArmyRow.war_id)
            .where(ArmyRow.owner_entity_id == member_id, ArmyRow.disbanded_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
            .order_by(ArmyRow.entity_id)
        )
        for row in armies:
            if ctx.epoch - row.raised_epoch < int(duration):
                continue
            army = await living_entity(ctx.session, row.entity_id)
            size = (stat(army, "size") or 0) if army is not None else 0
            spare = max(0, size - floor)
            going = round_half_up(spare * table.levy_return_pct / PERCENT * laws.weight(member_id, LawKind.LEVY_LAW))
            if army is None or going <= 0:
                continue
            set_stats(army, size=size - going)
            demobilise(ctx.rules, owner, going)
            floor = max(0, floor - (size - going))
            returned += going
    return returned


async def standing_soldiers(ctx: TickContext, realm: Realm) -> int:
    soldiers = 0
    for member_id in realm.members:
        owner = await living_entity(ctx.session, member_id)
        soldiers += await standing_floor(ctx.session, ctx.rules, owner)
    return soldiers


async def luxury_factor(session: AsyncSession, rules: Rules, community_id: int, society: CommunitySocietyRow | None) -> float:
    if society is None:
        return 1.0
    noble = await law_param(session, community_id, LawKind.SUMPTUARY, "noble_luxury")
    merchant = await law_param(session, community_id, LawKind.SUMPTUARY, "merchant_luxury")
    if noble is None or merchant is None:
        return 1.0
    shift = (int(noble) - PERCENT // 2) * society.share(SocialClass.NOBLE) + (int(merchant) - PERCENT // 2) * society.share(SocialClass.MERCHANT)
    return max(0.0, 1 + shift / PERCENT / PERCENT * rules.legislation.sumptuary_pct / PERCENT * 2)


async def toll_rate(session: AsyncSession, master_id: int) -> int | None:
    rate = await law_param(session, master_id, LawKind.TOLLS, "rate")
    return int(rate) if rate is not None else None


async def bequest_order(session: AsyncSession, mortal: EntityRow, heirs: list[EntityRow]) -> list[EntityRow]:
    if len(heirs) < 2:
        return heirs
    split = await law_param(session, mortal.location_id, LawKind.INHERITANCE_SPLIT, "split") if mortal.location_id is not None else None
    if split is None:
        return heirs_by_custom(await inheritance_of(session, mortal), heirs)
    by_age = sorted(heirs, key=lambda heir: (-(stat(heir, "age") or 0), heir.id))
    if split == "youngest":
        return by_age[-1:]
    if split == "equal":
        return by_age
    return by_age[:1]


async def endogamous(session: AsyncSession, node_id: int | None) -> bool:
    if node_id is None:
        return False
    return bool(await law_param(session, node_id, LawKind.MARRIAGE_LAW, "endogamy"))


async def may_coin(session: AsyncSession, rules: Rules, issuer_id: int) -> bool:
    polity = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == issuer_id).limit(1))
    profile = await session.get(PolityProfileRow, polity) if polity is not None else None
    return profile is None or profile.tier >= rules.realm_tiers.coinage


async def realm_coinage(ctx: TickContext, realm: Realm) -> int:
    if realm.profile.tier < ctx.rules.realm_tiers.coinage or realm.profile.capital_entity_id is None:
        return 0
    capital = await ctx.session.get(CommunitySocietyRow, realm.profile.capital_entity_id)
    if capital is None or capital.currency_id is None:
        return 0
    adopted = 0
    for member_id in realm.members:
        society = await ctx.session.get(CommunitySocietyRow, member_id)
        if society is not None and society.currency_id is None:
            society.currency_id = capital.currency_id
            adopted += 1
    return adopted
