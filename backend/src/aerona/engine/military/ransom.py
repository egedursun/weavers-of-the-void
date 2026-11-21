from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points, wealth_points
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.services.community_relations import change_relation, relation

HIGH_CLASSES = frozenset({SocialClass.NOBLE, SocialClass.PRIEST})


async def house_of(ctx: TickContext, mortal_id: int) -> HouseProfileRow | None:
    house_id = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).limit(1))
    return await ctx.session.get(HouseProfileRow, house_id) if house_id is not None else None


async def realm_of(ctx: TickContext, community_id: int) -> PolityProfileRow | None:
    polity_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return await ctx.session.get(PolityProfileRow, polity_id) if polity_id is not None else None


def cohort_ransom(ctx: TickContext, row: CaptiveCohortRow) -> int:
    table = ctx.rules.captive_depth
    base = row.count * table.ransom_per_100 / PERCENT
    if row.social_class in HIGH_CLASSES:
        base *= table.noble_ransom_pct / PERCENT
    return max(1, round_half_up(base))


async def named_ransom(ctx: TickContext, captive: EntityRow) -> int:
    table = ctx.rules.captive_depth
    house = await house_of(ctx, captive.id)
    prestige = house.prestige if house is not None else 0
    rank = table.noble_ransom_pct / PERCENT if house is not None else 1.0
    return max(1, round_half_up(table.named_ransom * rank * (1 + prestige * table.prestige_ransom_pct / PERCENT / PERCENT)))


async def pay_from_treasury(ctx: TickContext, payer: EntityRow, amount: int, *, captive: EntityRow | None = None) -> int:
    paid = await draw_ransom(ctx, payer, amount, captive=captive)
    if paid > 0 and stat(payer, "prosperity") is not None:
        shift_stat(payer, "prosperity", -ctx.rules.campaigns.ransom_cost)
    return paid


async def draw_ransom(ctx: TickContext, payer: EntityRow, amount: int, *, captive: EntityRow | None = None) -> int:
    if captive is not None:
        house = await house_of(ctx, captive.id)
        if house is not None and house.wealth >= amount:
            house.wealth -= amount
            return amount
    realm = await realm_of(ctx, payer.id)
    if realm is not None and realm.treasury >= amount:
        realm.treasury -= amount
        return amount
    if await points_of(ctx.session, payer) >= wealth_points(ctx.rules, amount):
        await shift_points(ctx.session, payer, -wealth_points(ctx.rules, amount))
        return amount
    return 0


async def release_by_opinion(ctx: TickContext, captor: EntityRow, home: EntityRow | None) -> bool:
    if home is None:
        return False
    return await relation(ctx.session, ctx.rules, captor.id, home.id) >= ctx.rules.captive_depth.release_opinion


async def grow_ward(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> int:
    if "loyalty" not in row.locked:
        row.loyalty = clamp_int(row.loyalty + ctx.rules.captive_depth.ward_loyalty, -PERCENT, PERCENT)
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=captive.id,
        subject_id=captor.id,
        kind=MemoryKind.TAUGHT_ME,
        magnitude=ctx.rules.captive_depth.ward_loyalty,
        epoch=ctx.epoch,
        note="raised at their court",
    )
    return row.loyalty


async def ward_returns(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> int:
    home = await living_entity(ctx.session, row.home_entity_id)
    if home is None or row.loyalty <= 0:
        return 0
    warmth = round_half_up(row.loyalty * ctx.rules.captive_depth.ward_relation_pct / PERCENT)
    await change_relation(ctx, home.id, captor.id, warmth, MemoryKind.GOODWILL, note=f"{captive.name} was raised by them")
    return warmth


async def marry_captive(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow) -> EntityRow | None:
    if row.married_entity_id is not None or await house_of(ctx, captive.id) is None:
        return None
    if not ctx.rng(f"captive_marriage.{row.id}.{ctx.epoch}").chance(ctx.rules.captive_depth.marriage_chance):
        return None
    realm = await realm_of(ctx, captor.id)
    if realm is None:
        return None
    house = await ctx.session.scalar(select(HouseProfileRow).where(HouseProfileRow.polity_entity_id == realm.polity_entity_id).limit(1))
    if house is None:
        return None
    spouse_id = await ctx.session.scalar(
        select(HouseMemberRow.mortal_entity_id)
        .where(HouseMemberRow.house_entity_id == house.house_entity_id, HouseMemberRow.mortal_entity_id != captive.id)
        .limit(1)
    )
    spouse = await living_entity(ctx.session, spouse_id)
    if spouse is None:
        return None
    await BondRepository(ctx.session).connect(BondDraft(captive.id, spouse.id, BondKind.LOVES, ctx.epoch, "married in captivity"))
    if await ctx.session.get(HouseMemberRow, (house.house_entity_id, captive.id)) is None:
        ctx.session.add(HouseMemberRow(house_entity_id=house.house_entity_id, mortal_entity_id=captive.id, joined_epoch=ctx.epoch))
    row.married_entity_id = spouse.id
    if "loyalty" not in row.locked:
        row.loyalty = clamp_int(row.loyalty + ctx.rules.captive_depth.ward_loyalty * 2, -PERCENT, PERCENT)
    return spouse


async def carry_language(ctx: TickContext, row: CaptiveCohortRow, settled_in: EntityRow | None) -> bool:
    if settled_in is None or row.language_entity_id is None:
        return False
    language = await living_entity(ctx.session, row.language_entity_id)
    if language is None:
        return False
    bonds = BondRepository(ctx.session)
    if await bonds.exists_between(settled_in.id, language.id, BondKind.SPEAKS):
        return False
    share = row.count * PERCENT / max(1, stat(settled_in, "population") or 0) * ctx.rules.captive_depth.language_pct / PERCENT
    if share < 1:
        return False
    await bonds.connect(BondDraft(settled_in.id, language.id, BondKind.SPEAKS, ctx.epoch, "brought by captives"))
    return True
