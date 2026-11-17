from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.peoples import STYLE_AXES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.collective import AccountStanceRow, FoundingMythRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.cycles import LegacyTraitRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.discovery import ArtFormProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import AccountStance
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.cycles import LegacyKind
from aerona.domain.enums.demography import FuneralCustom, MartialStyle
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import divine_of
from aerona.engine.lore.art_forms import practise
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.recording.record import StepDraft, record

CULTURE_FIELDS = {LegacyKind.MARTIAL_STYLE: "martial_style", LegacyKind.FUNERAL_RITE: "funeral_rite"}
CULTURE_ENUMS = {LegacyKind.MARTIAL_STYLE: MartialStyle, LegacyKind.FUNERAL_RITE: FuneralCustom}
STYLE_SEPARATOR = ","


def style_key(culture: PeopleCultureRow) -> str:
    return STYLE_SEPARATOR.join(str(getattr(culture, axis)) for axis in STYLE_AXES)


def style_values(key: str) -> list[int]:
    values = [int(value) for value in key.split(STYLE_SEPARATOR)]
    if len(values) != len(STYLE_AXES) or any(not 0 <= value <= PERCENT for value in values):
        raise ValueError(key)
    return values


def keep_style(culture: PeopleCultureRow, key: str) -> None:
    for axis, value in zip(STYLE_AXES, style_values(key), strict=True):
        if axis not in culture.locked:
            setattr(culture, axis, value)


@dataclass
class LegacyTally:
    kept: int = 0
    myths: int = 0


async def predecessors(ctx: TickContext, people: EntityRow) -> list[tuple[EntityRow, int]]:
    table = ctx.rules.legacy_traits
    found: list[tuple[EntityRow, int]] = []
    for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[people.id]):
        other = await ctx.session.get(EntityRow, bond.target_node_id)
        if other is not None and other.entity_type is EntityType.PEOPLE and other.id != people.id:
            found.append((other, table.keep_pct))
    for bond in await active_bonds(ctx.session, [BondKind.PART_OF], targets=[people.id]):
        other = await ctx.session.get(EntityRow, bond.source_node_id)
        if other is not None and other.entity_type is EntityType.PEOPLE and other.id != people.id:
            found.append((other, table.absorbed_keep_pct))
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
    if kind is LegacyKind.AESTHETIC:
        culture = await ctx.session.get(PeopleCultureRow, predecessor.id)
        return style_key(culture) if culture is not None else None
    if kind is LegacyKind.BELIEF:
        patron = await living_patron(ctx.session, predecessor)
        return str(patron.id) if patron is not None else None
    if kind is LegacyKind.INNOVATION:
        mine = set(await ctx.session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == people.id)))
        theirs = await ctx.session.scalars(
            select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == predecessor.id).order_by(HolderTechniqueRow.technique)
        )
        return next((technique.value for technique in theirs if technique not in mine), None)
    if kind is LegacyKind.ART_FORM:
        form = await ctx.session.scalar(
            select(ArtFormProfileRow.art_form_entity_id)
            .where(ArtFormProfileRow.origin_culture_id == predecessor.id)
            .order_by(ArtFormProfileRow.art_form_entity_id)
            .limit(1)
        )
        return str(form) if form is not None else None
    axis = strongest(await stored_values(ctx.session, ValueHolder.CULTURE, predecessor.id))
    return axis.value if axis is not None else None


async def apply_legacy(ctx: TickContext, kind: LegacyKind, people: EntityRow, predecessor: EntityRow, key: str) -> None:
    if kind in CULTURE_FIELDS:
        custom = CULTURE_ENUMS[kind](key)
        culture = await ctx.session.get(PeopleCultureRow, people.id)
        field = CULTURE_FIELDS[kind]
        if culture is not None and field not in culture.locked:
            setattr(culture, field, custom)
        return
    if kind is LegacyKind.AESTHETIC:
        style_values(key)
        culture = await ctx.session.get(PeopleCultureRow, people.id)
        if culture is not None:
            keep_style(culture, key)
        return
    if kind is LegacyKind.BELIEF:
        god = await divine_of(ctx.session, int(key))
        if god is None:
            raise KeyError(key)
        await connect(ctx.session, people.id, god.id, BondKind.WORSHIPS, ctx.epoch, description=f"kept from {predecessor.name}")
        return
    if kind is LegacyKind.INNOVATION:
        technique = Technique(key)
        if await ctx.session.get(HolderTechniqueRow, (people.id, technique)) is None:
            ctx.session.add(HolderTechniqueRow(holder_entity_id=people.id, technique=technique, since_epoch=ctx.epoch, secret=False))
        return
    if kind is LegacyKind.ART_FORM:
        form = await ctx.session.get(ArtFormProfileRow, int(key))
        if form is None:
            raise KeyError(key)
        await practise(ctx, form.art_form_entity_id, people.id, ctx.rules.legacy_traits.art_mastery)
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


async def inherit(ctx: TickContext, people: EntityRow, predecessor: EntityRow, keep_pct: int, tally: LegacyTally) -> None:
    done = await kept(ctx, people.id, predecessor.id)
    carried: list[LegacyKind] = []
    for kind in LegacyKind:
        if kind in done or not SeededRandom.for_epoch(people.id, predecessor.id, f"legacy.{kind.value}").chance(keep_pct):
            continue
        key = await legacy_key(ctx, kind, people, predecessor)
        if key is None or await ctx.session.get(LegacyTraitRow, (people.id, kind, key)) is not None:
            continue
        await apply_legacy(ctx, kind, people, predecessor, key)
        ctx.session.add(LegacyTraitRow(people_entity_id=people.id, kind=kind, key=key, predecessor_entity_id=predecessor.id, since_epoch=ctx.epoch, locked=[]))
        carried.append(kind)
        tally.kept += 1
    if carried:
        await remember_in_myth(ctx, people, predecessor, tally)
        await record(
            ctx,
            "legacy.kept",
            roles={IncidentRole.HEIR: people.id, IncidentRole.PREDECESSOR: predecessor.id},
            facts={"legacies": carried},
            steps=(StepDraft(StepAction.INHERIT, actor=people.id, target=predecessor.id),),
        )


async def keep_legacies(ctx: TickContext, tally: LegacyTally) -> None:
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        for predecessor, keep_pct in await predecessors(ctx, people):
            await inherit(ctx, people, predecessor, keep_pct, tally)
    await ctx.session.flush()
