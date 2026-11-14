from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.collective import HERALDIC_NAMES, LEGACY_TINCTURES
from aerona.catalog.heraldry import (
    ARRANGEMENT_NAMES,
    CHARGE_NAMES,
    COUNT_WEIGHTS,
    CREST_CHARGES,
    CREST_PCT,
    DIVISION_NAMES,
    EVERY_CHARGE,
    FUR_WEIGHT,
    FURS,
    LINE_NAMES,
    LINED_PCT,
    OPEN_ARRANGEMENTS,
    ORNAMENT_WEIGHTS,
    OUTSIDE_WEIGHTS,
    POSE_POOLS,
    POSE_WEIGHTS,
    PREFERRED_ARRANGEMENTS,
    REPEAT_PCT,
    RIM_LINED_PCT,
    RIM_NAMES,
    RIM_WEIGHTS,
    SHAPE_NAMES,
    SHAPE_WEIGHTS,
    SOLID_WEIGHT,
    STRAY_PCT,
    SUPPORTER_PCT,
    UNLINED,
    VALUE_POOLS,
)
from aerona.core.grammar import an
from aerona.core.random import SeededRandom
from aerona.db.tables.collective import ARMS_FIELDS, ArmsRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow, PolityProfileRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import (
    ArmsRim,
    ChargeArrangement,
    HeraldicCharge,
    HeraldicDivision,
    HeraldryHolderKind,
    PartitionLine,
    ShieldShape,
    SupporterPose,
    Tincture,
)
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.body.customs import people_of
from aerona.engine.collective.armory import Design, against, beneath, contrasting, partners, settled, slots
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note

H = HeraldryHolderKind
GUILDS = frozenset({FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD, FactionKind.THIEVES_GUILD, FactionKind.WARRIOR_ORDER, FactionKind.HOLY_ORDER})
DESIGN_FIELDS = tuple(name for name in ARMS_FIELDS if name != "motto")
STRONGEST = 3
TRIES = 24
NUMBERS = ("two", "three")
Signature = tuple[Any, ...]


@dataclass
class HeraldryTally:
    granted: int = 0
    differenced: int = 0
    quartered: int = 0


def design_of(arms: ArmsRow) -> Design:
    return Design(
        shape=arms.shape,
        field=arms.field,
        division=arms.division,
        line=arms.line,
        second=arms.second,
        charges=((arms.charge, arms.charge_tincture), (arms.charge_two, arms.charge_two_tincture), (arms.charge_three, arms.charge_three_tincture)),
        arrangement=arms.arrangement,
        rim=arms.rim,
        rim_line=arms.rim_line,
        rim_tincture=arms.rim_tincture,
        supporter=arms.supporter,
        pose=arms.supporter_pose,
        supporter_tincture=arms.supporter_tincture,
        crest=arms.crest,
        crest_tincture=arms.crest_tincture,
    )


def named(tincture: Tincture | None) -> str:
    return HERALDIC_NAMES[tincture] if tincture is not None else ""


def charges_text(design: Design) -> str:
    shown = [(charge, tincture) for charge, tincture in design.charges if charge is not HeraldicCharge.NONE]
    if not shown:
        return ""
    count = len(shown)
    arrangement = design.arrangement
    if count == 2 and arrangement is ChargeArrangement.TWO_AND_ONE:
        arrangement = ChargeArrangement.IN_FESS
    if count == 2 and arrangement is ChargeArrangement.ONE_AND_TWO:
        arrangement = ChargeArrangement.IN_PALE
    placing = ARRANGEMENT_NAMES[arrangement] if count > 1 or arrangement is ChargeArrangement.IN_CHIEF else ""
    if len({charge for charge, _ in shown}) == 1 and len({tincture for _, tincture in shown}) == 1:
        charge, tincture = shown[0]
        head = an(CHARGE_NAMES[charge][0]) if count == 1 else f"{NUMBERS[count - 2]} {CHARGE_NAMES[charge][1]}"
        text = f"{head} {named(tincture)}"
    else:
        items = [f"{an(CHARGE_NAMES[charge][0])} {named(tincture)}" for charge, tincture in shown]
        text = ", ".join(items[:-1]) + " and " + items[-1]
    return f"{text} {placing}".strip()


def supporters_text(design: Design) -> str:
    single, plural = CHARGE_NAMES[design.supporter]
    tincture = named(design.supporter_tincture)
    match design.pose:
        case SupporterPose.CROSSED:
            return f"behind it two {plural} in saltire {tincture}"
        case SupporterPose.BEHIND:
            return f"behind it {an(single)} palewise {tincture}"
        case SupporterPose.FLANKING:
            return f"supported by two {plural} {tincture}"
        case SupporterPose.CORNERS:
            return f"with four {plural} in the corners {tincture}"


def blazon_of(design: Design) -> str:
    design = settled(design)
    name, ordinary = DIVISION_NAMES[design.division]
    line = LINE_NAMES[design.line] if design.division not in UNLINED else ""
    field = named(design.field)
    if design.division is HeraldicDivision.PLAIN:
        head = field.capitalize()
    elif ordinary:
        head = f"{field.capitalize()}, {' '.join(part for part in (name, line, named(design.second)) if part)}"
    else:
        head = f"{' '.join(part for part in (name, line) if part).capitalize()} {field} and {named(design.second)}"
    parts = [head, charges_text(design)]
    if design.rim is not ArmsRim.LINE:
        parts.append(f"within {RIM_NAMES[design.rim]} {named(design.rim_tincture)}")
    extras = [", ".join(part for part in parts if part)]
    if design.rim_line is not PartitionLine.STRAIGHT:
        extras.append(f"the edge {LINE_NAMES[design.rim_line]}")
    if design.supporter is not HeraldicCharge.NONE:
        extras.append(supporters_text(design))
    if design.crest is not HeraldicCharge.NONE:
        extras.append(f"for a crest, {an(CHARGE_NAMES[design.crest][0])} {named(design.crest_tincture)}")
    extras.append(f"borne on {SHAPE_NAMES[design.shape]}")
    return "; ".join(extras)


def blazon(arms: ArmsRow) -> str:
    return blazon_of(design_of(arms))


def signature(values: dict[str, Any]) -> Signature:
    return tuple(values.get(name) for name in DESIGN_FIELDS)


def signature_of(arms: ArmsRow) -> Signature:
    return tuple(getattr(arms, name) for name in DESIGN_FIELDS)


def seconds(field: Tincture) -> list[Tincture]:
    furs = [fur for fur in FURS if field in partners(fur)]
    return partners(field) + furs


def ornament(rng: SeededRandom, weights: Mapping[Tincture, int] = ORNAMENT_WEIGHTS) -> Tincture:
    return rng.weighted(list(weights), list(weights.values()))


def styled_line(rng: SeededRandom, percent: float) -> PartitionLine:
    if not rng.chance(percent):
        return PartitionLine.STRAIGHT
    return rng.pick([line for line in PartitionLine if line is not PartitionLine.STRAIGHT])


def chosen_charges(rng: SeededRandom, axes: list[ValueAxis]) -> list[HeraldicCharge]:
    count = rng.weighted(list(COUNT_WEIGHTS), list(COUNT_WEIGHTS.values()))
    if count == 0:
        return []
    pools = [VALUE_POOLS[axis] for axis in axes] or [EVERY_CHARGE]
    first = rng.pick(pools[0])
    if rng.chance(REPEAT_PCT):
        return [first] * count
    found = [first]
    for k in range(1, count):
        found.append(rng.pick(EVERY_CHARGE if rng.chance(STRAY_PCT) else pools[min(k, len(pools) - 1)]))
    return found


def invent(rng: SeededRandom, hint: Tincture | None, axes: list[ValueAxis]) -> dict[str, Any]:
    shapes = list(ShieldShape)
    tinctures = list(Tincture)
    shape = rng.weighted(shapes, [SHAPE_WEIGHTS[shape] for shape in shapes])
    field = hint if hint is not None else rng.weighted(tinctures, [FUR_WEIGHT if tincture in FURS else SOLID_WEIGHT for tincture in tinctures])
    division = rng.pick(list(HeraldicDivision))
    line = PartitionLine.STRAIGHT if division in UNLINED else styled_line(rng, LINED_PCT)
    second = None if division is HeraldicDivision.PLAIN else rng.pick(seconds(field))
    charges = chosen_charges(rng, axes)
    arrangement = rng.pick(PREFERRED_ARRANGEMENTS.get(division, OPEN_ARRANGEMENTS))
    rims = list(ArmsRim)
    draft = Design(
        shape=shape,
        field=field,
        division=division,
        line=line,
        second=second,
        charges=tuple((charge, None) for charge in charges),
        arrangement=arrangement,
        rim=ArmsRim.LINE,
        rim_line=PartitionLine.STRAIGHT,
        rim_tincture=None,
        supporter=HeraldicCharge.NONE,
        pose=SupporterPose.CROSSED,
        supporter_tincture=None,
        crest=HeraldicCharge.NONE,
        crest_tincture=None,
    )
    unders = [beneath(draft, x, y, size) for x, y, size in slots(draft, len(charges))]
    everything = set().union(*unders) if unders else set()
    common = against(everything)
    shared = rng.pick(common) if common else None
    tints = [shared if shared is not None else rng.pick(against(under) or [contrasting(under)]) for under in unders]
    padded = [*zip(charges, tints, strict=True), *[(HeraldicCharge.NONE, None)] * (3 - len(charges))]
    supported = rng.chance(SUPPORTER_PCT)
    poses = list(SupporterPose)
    pose = rng.weighted(poses, [POSE_WEIGHTS[pose] for pose in poses]) if supported else SupporterPose.CROSSED
    crested = rng.chance(CREST_PCT)
    crest = (charges[0] if charges and rng.chance(30) else rng.pick(CREST_CHARGES)) if crested else HeraldicCharge.NONE
    return {
        "shape": shape,
        "field": field,
        "division": division,
        "line": line,
        "second": second,
        "charge": padded[0][0],
        "charge_tincture": padded[0][1],
        "charge_two": padded[1][0],
        "charge_two_tincture": padded[1][1],
        "charge_three": padded[2][0],
        "charge_three_tincture": padded[2][1],
        "arrangement": arrangement,
        "rim": rng.weighted(rims, [RIM_WEIGHTS[rim] for rim in rims]),
        "rim_line": styled_line(rng, RIM_LINED_PCT),
        "rim_tincture": ornament(rng),
        "supporter": rng.pick(POSE_POOLS[pose]) if supported else HeraldicCharge.NONE,
        "supporter_pose": pose,
        "supporter_tincture": ornament(rng, OUTSIDE_WEIGHTS) if supported else None,
        "crest": crest,
        "crest_tincture": ornament(rng, OUTSIDE_WEIGHTS) if crested else None,
    }


async def strongest(session: AsyncSession, holder: EntityRow) -> list[ValueAxis]:
    people = await people_of(session, holder)
    values = await stored_values(session, ValueHolder.CULTURE, people.id) if people is not None else {}
    return sorted(values, key=lambda axis: (-values[axis], axis.value))[:STRONGEST]


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
            title.emblem = text


async def grant(ctx: TickContext, holder: EntityRow, kind: HeraldryHolderKind, legacy: dict[str, str], taken: set[Signature]) -> ArmsRow:
    axes = await strongest(ctx.session, holder)
    hint = LEGACY_TINCTURES.get(legacy.get("field", ""))
    values: dict[str, Any] = {}
    for attempt in range(TRIES):
        values = invent(ctx.rng(f"arms.{holder.id}.{attempt}"), hint if attempt < TRIES // 2 else None, axes)
        if signature(values) not in taken:
            break
    taken.add(signature(values))
    row = ArmsRow(holder_entity_id=holder.id, holder_kind=kind, motto=legacy.get("motto") or None, since_epoch=ctx.epoch, locked=[], **values)
    ctx.session.add(row)
    await ctx.session.flush()
    await sync_emblem(ctx, row)
    return row


async def difference(
    ctx: TickContext, house: HouseProfileRow, entity: EntityRow, parent: ArmsRow, tally: HeraldryTally, *, taken: set[Signature]
) -> ArmsRow | None:
    if not ctx.rng(f"cadet_arms.{house.house_entity_id}").chance(ctx.rules.heraldry.cadet_bordure_pct):
        return None
    values = {name: getattr(parent, name) for name in DESIGN_FIELDS}
    for attempt in range(TRIES):
        rng = ctx.rng(f"bordure.{house.house_entity_id}.{attempt}")
        values |= {"division": HeraldicDivision.BORDURE, "line": styled_line(rng, LINED_PCT), "second": rng.pick(seconds(parent.field))}
        if signature(values) not in taken:
            break
    taken.add(signature(values))
    row = ArmsRow(
        holder_entity_id=house.house_entity_id,
        holder_kind=H.HOUSE,
        motto=parent.motto,
        parent_entity_id=parent.holder_entity_id,
        since_epoch=ctx.epoch,
        locked=[],
        **values,
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
    taken = {signature_of(row) for row in known.values()}
    for entity, kind, legacy in await holders(ctx):
        if entity.id in known:
            continue
        house = await ctx.session.get(HouseProfileRow, entity.id) if kind is H.HOUSE else None
        parent = known.get(house.parent_house_id) if house is not None and house.parent_house_id is not None else None
        row = await difference(ctx, house, entity, parent, tally, taken=taken) if house is not None and parent is not None else None
        known[entity.id] = row or await grant(ctx, entity, kind, legacy, taken)
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
