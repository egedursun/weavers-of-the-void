from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.collective import HERALDIC_NAMES, LEGACY_TINCTURES, METALS, VALUE_CHARGES
from aerona.core.grammar import an
from aerona.db.tables.collective import ArmsRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, PolityProfileRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import HeraldicCharge, HeraldicDivision, HeraldryHolderKind, Tincture
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueHolder
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note

H = HeraldryHolderKind
GUILDS = frozenset({FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD, FactionKind.THIEVES_GUILD, FactionKind.WARRIOR_ORDER, FactionKind.HOLY_ORDER})
PLAIN_DIVISIONS = (HeraldicDivision.PLAIN, HeraldicDivision.PER_PALE, HeraldicDivision.PER_FESS, HeraldicDivision.PER_BEND, HeraldicDivision.CHEVRON)


@dataclass
class HeraldryTally:
    granted: int = 0
    differenced: int = 0
    quartered: int = 0


def blazon(arms: ArmsRow) -> str:
    field = HERALDIC_NAMES[arms.field]
    parts = [field.capitalize()]
    if arms.division is not HeraldicDivision.PLAIN and arms.second is not None:
        parts = [f"{arms.division.value.replace('_', ' ').capitalize()} {field} and {HERALDIC_NAMES[arms.second]}"]
    if arms.charge is not HeraldicCharge.NONE and arms.charge_tincture is not None:
        parts.append(f"{an(arms.charge.value)} {HERALDIC_NAMES[arms.charge_tincture]}")
    return ", ".join(parts)


def contrast(field: Tincture, rng_pick: Tincture) -> Tincture:
    if (field in METALS) == (rng_pick in METALS):
        return Tincture.SILVER if field not in METALS else Tincture.BLACK
    return rng_pick


async def charge_for(ctx: TickContext, holder: EntityRow) -> HeraldicCharge:
    people = await people_of(ctx.session, holder)
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id) if people is not None else {}
    if not values:
        return ctx.rng(f"arms_charge.{holder.id}").pick([charge for charge in HeraldicCharge if charge is not HeraldicCharge.NONE])
    axis = max(values, key=lambda axis: (values[axis], axis.value))
    return VALUE_CHARGES[axis]


async def sync_emblem(ctx: TickContext, arms: ArmsRow) -> None:
    text = blazon(arms)
    if arms.holder_kind is H.HOUSE:
        house = await ctx.session.get(HouseProfileRow, arms.holder_entity_id)
        if house is not None:
            house.emblem = {**house.emblem, "field": HERALDIC_NAMES[arms.field], "charge": arms.charge.value, "blazon": text}
    elif arms.holder_kind is H.POLITY:
        realm = await ctx.session.get(PolityProfileRow, arms.holder_entity_id)
        if realm is not None:
            realm.emblem = {**realm.emblem, "field": HERALDIC_NAMES[arms.field], "charge": arms.charge.value, "blazon": text}
    elif arms.holder_kind is H.TITLE:
        title = await ctx.session.get(TitleProfileRow, arms.holder_entity_id)
        if title is not None and "emblem" not in title.locked:
            title.emblem = text[:80]


async def grant(ctx: TickContext, holder: EntityRow, kind: HeraldryHolderKind, legacy: dict[str, str] | None = None) -> ArmsRow:
    rng = ctx.rng(f"arms.{holder.id}")
    field = LEGACY_TINCTURES.get((legacy or {}).get("field", ""), rng.pick(list(Tincture)))
    division = rng.pick(PLAIN_DIVISIONS)
    row = ArmsRow(
        holder_entity_id=holder.id,
        holder_kind=kind,
        field=field,
        division=division,
        second=contrast(field, rng.pick(list(Tincture))) if division is not HeraldicDivision.PLAIN else None,
        charge=await charge_for(ctx, holder),
        charge_tincture=contrast(field, rng.pick(list(Tincture))),
        motto=(legacy or {}).get("motto") or None,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await sync_emblem(ctx, row)
    return row


async def difference(ctx: TickContext, house: HouseProfileRow, entity: EntityRow, parent: ArmsRow, tally: HeraldryTally) -> ArmsRow | None:
    if not ctx.rng(f"cadet_arms.{house.house_entity_id}").chance(ctx.rules.heraldry.cadet_bordure_pct):
        return None
    row = ArmsRow(
        holder_entity_id=house.house_entity_id,
        holder_kind=H.HOUSE,
        field=parent.field,
        division=HeraldicDivision.BORDURE,
        second=contrast(parent.field, ctx.rng(f"bordure.{house.house_entity_id}").pick(list(Tincture))),
        charge=parent.charge,
        charge_tincture=parent.charge_tincture,
        motto=parent.motto,
        parent_entity_id=parent.holder_entity_id,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await sync_emblem(ctx, row)
    tally.differenced += 1
    await note(ctx, f"{entity.name}, a cadet branch, bore its parent's arms within a border.", key="heraldry.cadet", ids=[entity.id])
    return row


async def holders(ctx: TickContext) -> list[tuple[EntityRow, HeraldryHolderKind, dict[str, str]]]:
    found: list[tuple[int, HeraldryHolderKind, dict[str, str]]] = []
    for profile in await ctx.session.scalars(select(HouseProfileRow).order_by(HouseProfileRow.house_entity_id)):
        found.append((profile.house_entity_id, H.HOUSE, dict(profile.emblem or {})))
    for realm in await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id)):
        found.append((realm.polity_entity_id, H.POLITY, dict(realm.emblem or {})))
    for title in await ctx.session.scalars(select(TitleProfileRow).where(TitleProfileRow.destroyed_epoch.is_(None)).order_by(TitleProfileRow.title_entity_id)):
        found.append((title.title_entity_id, H.TITLE, {}))
    for army in await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)):
        found.append((army.entity_id, H.ARMY, {}))
    for guild in await ctx.session.scalars(
        select(FactionProfileRow).where(FactionProfileRow.kind.in_(sorted(GUILDS))).order_by(FactionProfileRow.faction_entity_id)
    ):
        found.append((guild.faction_entity_id, H.GUILD, {}))
    rows: list[tuple[EntityRow, HeraldryHolderKind, dict[str, str]]] = []
    for holder_id, kind, legacy in found:
        entity = await ctx.session.get(EntityRow, holder_id)
        if entity is not None and entity.status is EntityStatus.CANON and not held(entity.id):
            rows.append((entity, kind, legacy))
    return rows


async def grant_arms(ctx: TickContext, tally: HeraldryTally) -> None:
    known = {row.holder_entity_id: row for row in await ctx.session.scalars(select(ArmsRow))}
    for entity, kind, legacy in await holders(ctx):
        if entity.id in known:
            continue
        house = await ctx.session.get(HouseProfileRow, entity.id) if kind is H.HOUSE else None
        parent = known.get(house.parent_house_id) if house is not None and house.parent_house_id is not None else None
        row = await difference(ctx, house, entity, parent, tally) if house is not None and parent is not None else None
        known[entity.id] = row or await grant(ctx, entity, kind, legacy)
        tally.granted += row is None


async def house_of_mortal(ctx: TickContext, mortal_id: int) -> int | None:
    return await ctx.session.scalar(
        select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id, HouseMemberRow.by_marriage.is_(False)).limit(1)
    )


async def quarter_on_marriage(ctx: TickContext, tally: HeraldryTally) -> None:
    for marriage in list(await ctx.session.scalars(select(MarriageRow).where(MarriageRow.start_epoch == ctx.epoch).order_by(MarriageRow.id))):
        first, second = await house_of_mortal(ctx, marriage.first_id), await house_of_mortal(ctx, marriage.second_id)
        if first is None or second is None or first == second:
            continue
        mine, theirs = await ctx.session.get(ArmsRow, first), await ctx.session.get(ArmsRow, second)
        if mine is None or theirs is None or held(first) or {"division", "second"} & set(mine.locked):
            continue
        if mine.quartered_entity_id is not None or not ctx.rng(f"quarter.{marriage.id}").chance(ctx.rules.heraldry.quarter_pct):
            continue
        mine.division, mine.second, mine.quartered_entity_id = HeraldicDivision.QUARTERLY, theirs.field, second
        await sync_emblem(ctx, mine)
        tally.quartered += 1
        house, other = await ctx.session.get(EntityRow, first), await ctx.session.get(EntityRow, second)
        if house is not None and other is not None:
            await note(ctx, f"{house.name} quartered its arms with those of {other.name} after a marriage.", key="heraldry.quartered", ids=[house.id, other.id])


async def keep_heraldry(ctx: TickContext, tally: HeraldryTally) -> None:
    await grant_arms(ctx, tally)
    await quarter_on_marriage(ctx, tally)
    await ctx.session.flush()
