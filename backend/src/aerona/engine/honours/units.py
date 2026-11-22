from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life_traits import UNIT_HONOUR_KIND_TRAITS, having
from aerona.catalog.units import UNITS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.honours import UnitHonourKind
from aerona.domain.enums.life_traits import UnitHonourKindTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.lore.history import record
from aerona.engine.lore.items import standard_item
from aerona.engine.military.battle import BattleResult, Side
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record as record_incident
from aerona.language.generator import NameKind


@dataclass
class HonourTally:
    named: int = 0
    honoured: int = 0
    reconstituted: int = 0
    disbanded: int = 0
    borne: int = 0
    nicknamed: int = 0


async def owner_of(ctx: TickContext, row: ArmyUnitRow) -> int | None:
    army = await ctx.session.get(ArmyRow, row.army_entity_id)
    return army.owner_entity_id if army is not None else None


async def reconstitute(ctx: TickContext, row: ArmyUnitRow, owner: int | None) -> NamedUnitRow | None:
    old = await ctx.session.scalar(
        select(NamedUnitRow)
        .where(NamedUnitRow.unit_id.is_(None), NamedUnitRow.raised_from_entity_id == row.origin_entity_id, NamedUnitRow.owner_entity_id == owner)
        .order_by(NamedUnitRow.esprit.desc(), NamedUnitRow.id)
        .limit(1)
    )
    if old is None:
        return None
    old.unit_id, old.disbanded_epoch = row.id, None
    if "esprit" not in old.locked:
        old.esprit = round_half_up(old.esprit * ctx.rules.unit_honours.reconstitute_pct / PERCENT)
    await record_incident(ctx, "honours.reconstituted", roles={IncidentRole.SUBJECT: row.army_entity_id}, facts={"unit": old.name, "esprit": old.esprit})
    return old


async def name_unit(ctx: TickContext, row: ArmyUnitRow, tally: HonourTally) -> NamedUnitRow | None:
    found = await ctx.session.scalar(select(NamedUnitRow).where(NamedUnitRow.unit_id == row.id).limit(1))
    if found is not None or row.origin_entity_id is None:
        return found
    owner = await owner_of(ctx, row)
    revived = await reconstitute(ctx, row, owner)
    if revived is not None:
        tally.reconstituted += 1
        return revived
    origin = await ctx.session.get(EntityRow, row.origin_entity_id)
    if origin is None:
        return None
    word = await Namer(ctx.session, ctx.rules).from_speaker(origin.id, seed_of("unit.name", row.id), NameKind.GENERAL)
    name = f"{word} of {origin.name}" if word else f"The {UNITS[row.kind].label} of {origin.name}"
    named = NamedUnitRow(
        unit_id=row.id,
        owner_entity_id=owner,
        name=name,
        raised_from_entity_id=origin.id,
        esprit=ctx.rules.unit_honours.seed_esprit,
        formed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(named)
    await ctx.session.flush()
    tally.named += 1
    return named


def honour_for(ctx: TickContext, side: Side, won: bool, lost_share: int, alive: bool) -> UnitHonourKind | None:
    if lost_share >= ctx.rules.unit_honours.massacre_share:
        return UnitHonourKind.MASSACRE
    if won:
        return UnitHonourKind.STAND if side.defending else UnitHonourKind.VICTORY
    return UnitHonourKind.SURVIVAL if alive else None


def esprit_shift(ctx: TickContext, kind: UnitHonourKind) -> int:
    table = ctx.rules.unit_honours
    return {
        UnitHonourKind.VICTORY: table.honour_esprit,
        UnitHonourKind.STAND: table.honour_esprit,
        UnitHonourKind.SIEGE: table.honour_esprit,
        UnitHonourKind.SURVIVAL: table.survival_esprit,
        UnitHonourKind.MASSACRE: -table.massacre_esprit,
    }[kind]


GLORIOUS = having(UNIT_HONOUR_KIND_TRAITS, UnitHonourKindTrait.GLORIOUS)


async def bestow(ctx: TickContext, named: NamedUnitRow, kind: UnitHonourKind, place: str, tally: HonourTally, *, army_id: int | None = None) -> None:
    ctx.session.add(UnitHonourRow(named_unit_id=named.id, kind=kind, note=place, epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    if "esprit" not in named.locked:
        named.esprit = clamp_int(named.esprit + esprit_shift(ctx, kind), 0, PERCENT)
    tally.honoured += 1
    await bear_on_standard(ctx, named, kind, place, army_id=army_id, tally=tally)
    await earn_nickname(ctx, named, tally)


async def bear_on_standard(ctx: TickContext, named: NamedUnitRow, kind: UnitHonourKind, place: str, *, army_id: int | None, tally: HonourTally) -> None:
    if kind not in GLORIOUS:
        return
    owners = [node for node in (army_id, named.owner_entity_id) if node is not None]
    item_id = await standard_item(ctx, owners)
    if item_id is None or held(item_id):
        return
    profile = await ctx.session.get(ItemProfileRow, item_id)
    if profile is not None and "renown" not in profile.locked:
        profile.renown = clamp_int(profile.renown + ctx.rules.unit_honours.standard_renown, 0, PERCENT)
    record(ctx, item_id, ItemDeed.BATTLE, named.owner_entity_id, f"{named.name}: {spoken(kind)} at {place}")
    tally.borne += 1


async def earn_nickname(ctx: TickContext, named: NamedUnitRow, tally: HonourTally) -> None:
    if named.nickname is not None or "nickname" in named.locked or named.raised_from_entity_id is None:
        return
    earned = await ctx.session.scalar(
        select(func.count()).select_from(UnitHonourRow).where(UnitHonourRow.named_unit_id == named.id, UnitHonourRow.kind.in_(GLORIOUS))
    )
    if (earned or 0) < ctx.rules.unit_honours.nickname_honours:
        return
    word = await Namer(ctx.session, ctx.rules).from_speaker(named.raised_from_entity_id, seed_of("unit.nickname", named.id), NameKind.GENERAL)
    if not word:
        return
    named.nickname = word
    tally.nicknamed += 1
    owner = {IncidentRole.OWNER: named.owner_entity_id} if named.owner_entity_id is not None else {}
    await record_incident(ctx, "honours.nicknamed", roles=owner, facts={"unit": named.name, "nickname": word, "honours": earned or 0})


async def honour_battle(ctx: TickContext, result: BattleResult, place: str, tally: HonourTally) -> None:
    for side in (result.attacker, result.defender):
        won = result.winner is side
        for stack in side.stacks:
            row = stack.row
            if held(row.army_entity_id) or stack.start <= 0:
                continue
            named = (
                await name_unit(ctx, row, tally)
                if row.count > 0
                else await ctx.session.scalar(select(NamedUnitRow).where(NamedUnitRow.unit_id == row.id).limit(1))
            )
            if named is None:
                continue
            if "battles" not in named.locked:
                named.battles += 1
            kind = honour_for(ctx, side, won, stack.lost * PERCENT // stack.start, row.count > 0)
            if kind is not None:
                await bestow(ctx, named, kind, place, tally, army_id=row.army_entity_id)


async def honour_siege(ctx: TickContext, army_id: int, town: EntityRow, tally: HonourTally) -> None:
    for row in list(await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id, ArmyUnitRow.count > 0))):
        named = await name_unit(ctx, row, tally)
        if named is not None and not held(army_id):
            await bestow(ctx, named, UnitHonourKind.SIEGE, town.name, tally, army_id=army_id)


async def disband_units(ctx: TickContext, army_id: int, tally: HonourTally) -> None:
    table = ctx.rules.unit_honours
    for row in list(await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id))):
        named = await ctx.session.scalar(select(NamedUnitRow).where(NamedUnitRow.unit_id == row.id).limit(1))
        if named is None or held(army_id):
            continue
        honours = list(await ctx.session.scalars(select(UnitHonourRow.id).where(UnitHonourRow.named_unit_id == named.id)))
        named.unit_id, named.disbanded_epoch = None, ctx.epoch
        tally.disbanded += 1
        owner = await ctx.session.get(EntityRow, named.owner_entity_id) if named.owner_entity_id is not None else None
        if honours and owner is not None and not held(owner.id):
            await shift_standing(ctx.session, owner, "renown", -table.disband_renown, ctx.epoch, default=0)
            await record_incident(
                ctx,
                "honours.disbanded",
                roles={IncidentRole.ACTOR: owner.id},
                facts={"unit": named.name, "honours": len(honours), "renown_lost": table.disband_renown},
            )


async def esprit_morale(ctx: TickContext, rows: list[ArmyUnitRow]) -> int:
    weighted = total = 0
    for row in rows:
        named = await ctx.session.scalar(select(NamedUnitRow.esprit).where(NamedUnitRow.unit_id == row.id).limit(1))
        if named is not None and row.count > 0:
            weighted += int(named) * row.count
            total += row.count
    return round_half_up(weighted / total * ctx.rules.unit_honours.morale_pct / PERCENT) if total else 0
