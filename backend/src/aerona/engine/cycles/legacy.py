from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.collective import AccountStanceRow, FoundingMythRow
from aerona.db.tables.cycles import LegacyTraitRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import AccountStance
from aerona.domain.enums.cycles import LegacyKind
from aerona.domain.enums.demography import Aesthetic, FuneralCustom, MartialStyle
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.notes import note
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import active_bonds, connect

CULTURE_FIELDS = {LegacyKind.MARTIAL_STYLE: "martial_style", LegacyKind.AESTHETIC: "aesthetic", LegacyKind.FUNERAL_RITE: "funeral_rite"}
CULTURE_ENUMS = {LegacyKind.MARTIAL_STYLE: MartialStyle, LegacyKind.AESTHETIC: Aesthetic, LegacyKind.FUNERAL_RITE: FuneralCustom}


@dataclass
class LegacyTally:
    kept: int = 0
    myths: int = 0


async def predecessors(ctx: TickContext, people: EntityRow) -> list[EntityRow]:
    found = []
    for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[people.id]):
        other = await ctx.session.get(EntityRow, bond.target_node_id)
        if other is not None and other.entity_type is EntityType.PEOPLE and other.id != people.id:
            found.append(other)
    return found


async def kept(ctx: TickContext, people_id: int, predecessor_id: int) -> set[LegacyKind]:
    rows = await ctx.session.scalars(
        select(LegacyTraitRow.kind).where(LegacyTraitRow.people_entity_id == people_id, LegacyTraitRow.predecessor_entity_id == predecessor_id)
    )
    return set(rows)


def strongest(values: dict[ValueAxis, int]) -> ValueAxis | None:
    if not values:
        return None
    return max(sorted(values, key=lambda axis: axis.value), key=lambda axis: abs(values[axis]))


async def legacy_key(ctx: TickContext, kind: LegacyKind, people: EntityRow, predecessor: EntityRow) -> str | None:
    if kind in CULTURE_FIELDS:
        culture = await ctx.session.get(PeopleCultureRow, predecessor.id)
        return str(getattr(culture, CULTURE_FIELDS[kind]).value) if culture is not None else None
    if kind is LegacyKind.BELIEF:
        patron = await living_patron(ctx.session, predecessor)
        return str(patron.id) if patron is not None else None
    axis = strongest(await stored_values(ctx.session, ValueHolder.CULTURE, predecessor.id))
    return axis.value if axis is not None else None


async def apply_legacy(ctx: TickContext, kind: LegacyKind, people: EntityRow, predecessor: EntityRow, key: str) -> None:
    if kind in CULTURE_FIELDS:
        culture = await ctx.session.get(PeopleCultureRow, people.id)
        field = CULTURE_FIELDS[kind]
        if culture is not None and field not in culture.locked:
            setattr(culture, field, CULTURE_ENUMS[kind](key))
        return
    if kind is LegacyKind.BELIEF:
        await connect(ctx.session, people.id, int(key), BondKind.WORSHIPS, ctx.epoch, description=f"kept from {predecessor.name}")
        return
    axis = ValueAxis(key)
    theirs = await stored_values(ctx.session, ValueHolder.CULTURE, predecessor.id)
    mine = dict(await stored_values(ctx.session, ValueHolder.CULTURE, people.id))
    pull = ctx.rules.legacy_traits.value_pull
    mine[axis] = round(mine.get(axis, 0) + (theirs.get(axis, 0) - mine.get(axis, 0)) * pull / PERCENT)
    await write_values(ctx.session, ValueHolder.CULTURE, people.id, mine)


async def remember_in_myth(ctx: TickContext, people: EntityRow, predecessor: EntityRow, tally: LegacyTally) -> None:
    myth = await ctx.session.get(FoundingMythRow, people.id)
    if myth is None or myth.account_id is None:
        return
    if await ctx.session.get(AccountStanceRow, (myth.account_id, predecessor.id)) is not None:
        return
    ctx.session.add(AccountStanceRow(account_id=myth.account_id, node_id=predecessor.id, stance=AccountStance.GLORIFY))
    tally.myths += 1


async def inherit(ctx: TickContext, people: EntityRow, predecessor: EntityRow, tally: LegacyTally) -> None:
    table = ctx.rules.legacy_traits
    done = await kept(ctx, people.id, predecessor.id)
    carried: list[str] = []
    for kind in LegacyKind:
        if kind in done or not SeededRandom.for_epoch(people.id, predecessor.id, f"legacy.{kind.value}").chance(table.keep_pct):
            continue
        key = await legacy_key(ctx, kind, people, predecessor)
        if key is None or await ctx.session.get(LegacyTraitRow, (people.id, kind, key)) is not None:
            continue
        await apply_legacy(ctx, kind, people, predecessor, key)
        ctx.session.add(LegacyTraitRow(people_entity_id=people.id, kind=kind, key=key, predecessor_entity_id=predecessor.id, since_epoch=ctx.epoch, locked=[]))
        carried.append(kind.value.replace("_", " "))
        tally.kept += 1
    if carried:
        await remember_in_myth(ctx, people, predecessor, tally)
        await note(ctx, f"{people.name} kept from {predecessor.name} its {', '.join(carried)}.", key="legacy.kept", ids=[people.id, predecessor.id])


async def keep_legacies(ctx: TickContext, tally: LegacyTally) -> None:
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        for predecessor in await predecessors(ctx, people):
            await inherit(ctx, people, predecessor, tally)
    await ctx.session.flush()
