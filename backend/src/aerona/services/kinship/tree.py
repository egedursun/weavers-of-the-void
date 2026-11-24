from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.collective import LEGACY_TINCTURES
from aerona.catalog.heraldry import FUR_SOLIDS
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import ArmsInk, Tincture
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityStatus, MortalRole
from aerona.domain.enums.mortal import MarriageEnd
from aerona.domain.enums.unions import UnionForm, UnionPurpose
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.mortal.life import sex_of_stats
from aerona.services.images.records import covers_of

KIN_STATES = (BondState.ACTIVE, BondState.PAST)
PARTNER_KINDS = (BondKind.CONCUBINE_OF, BondKind.BETROTHED_TO)
CARE_STEPS = {BondKind.FOSTERED_BY: -1, BondKind.GODPARENT_OF: 1, BondKind.SWORN_KIN: 0}
CARE_KINDS = tuple(CARE_STEPS)


@dataclass(frozen=True)
class Kin:
    id: int
    name: str
    title: str | None
    living: bool
    sex: SexKind | None
    role: MortalRole | None
    generation: int
    birth_epoch: int
    end_epoch: int | None
    cover: str | None
    house_id: int | None
    blood: bool


@dataclass(frozen=True)
class KinHouse:
    id: int
    name: str
    ink: ArmsInk | None


@dataclass(frozen=True)
class KinUnion:
    marriage_id: int
    first_id: int
    second_id: int
    form: UnionForm
    purpose: UnionPurpose
    start_epoch: int
    end_epoch: int | None
    cause_end: MarriageEnd | None
    forced: bool


@dataclass(frozen=True)
class KinTie:
    bond_id: int
    kind: BondKind
    source_id: int
    target_id: int
    past: bool
    epoch: int


@dataclass(frozen=True)
class TracedFamily:
    root: int
    up: int
    down: int
    deeper_up: bool
    deeper_down: bool
    people: list[Kin]
    houses: list[KinHouse]
    unions: list[KinUnion]
    ties: list[KinTie]


@dataclass
class Placement:
    generations: dict[int, int] = field(default_factory=dict)

    def place(self, person: int, generation: int) -> bool:
        if person in self.generations:
            return False
        self.generations[person] = generation
        return True

    def at(self, generation: int) -> list[int]:
        return sorted(person for person, level in self.generations.items() if level == generation)


async def parent_bonds(session: AsyncSession, *, parents: Iterable[int] | None = None, children: Iterable[int] | None = None) -> list[BondRow]:
    query = select(BondRow).where(BondRow.kind == BondKind.PARENT_OF, BondRow.state.in_(KIN_STATES))
    if parents is not None:
        query = query.where(BondRow.source_node_id.in_(list(parents)))
    if children is not None:
        query = query.where(BondRow.target_node_id.in_(list(children)))
    return list(await session.scalars(query.order_by(BondRow.id)))


async def marriages_among(session: AsyncSession, people: Iterable[int]) -> list[MarriageRow]:
    ids = list(people)
    query = select(MarriageRow).where(or_(MarriageRow.first_id.in_(ids), MarriageRow.second_id.in_(ids)))
    return list(await session.scalars(query.order_by(MarriageRow.start_epoch, MarriageRow.id)))


async def bonds_touching(session: AsyncSession, kinds: Iterable[BondKind], people: Iterable[int]) -> list[BondRow]:
    ids = list(people)
    query = select(BondRow).where(
        BondRow.kind.in_(list(kinds)), BondRow.state.in_(KIN_STATES), or_(BondRow.source_node_id.in_(ids), BondRow.target_node_id.in_(ids))
    )
    return list(await session.scalars(query.order_by(BondRow.id)))


async def climb(session: AsyncSession, placed: Placement, root: int, up: int) -> bool:
    frontier = [root]
    for step in range(1, up + 1):
        grown = [bond.source_node_id for bond in await parent_bonds(session, children=frontier) if placed.place(bond.source_node_id, -step)]
        if not grown:
            return False
        frontier = grown
    return bool(await parent_bonds(session, children=frontier))


async def descend(session: AsyncSession, placed: Placement, up: int, down: int) -> bool:
    for level in range(-up, down):
        for bond in await parent_bonds(session, parents=placed.at(level)):
            placed.place(bond.target_node_id, level + 1)
    bottom = placed.at(down)
    return any(bond.target_node_id not in placed.generations for bond in await parent_bonds(session, parents=bottom))


async def settle(session: AsyncSession, placed: Placement, fixed: set[int]) -> None:
    parents: dict[int, list[int]] = {}
    for bond in await parent_bonds(session, children=[person for person in placed.generations if person not in fixed]):
        if bond.source_node_id in placed.generations:
            parents.setdefault(bond.target_node_id, []).append(bond.source_node_id)
    for _ in placed.generations:
        moved = False
        for child, sources in parents.items():
            lowest = max(placed.generations[source] for source in sources) + 1
            if placed.generations[child] < lowest:
                placed.generations[child] = lowest
                moved = True
        if not moved:
            return


async def join_partners(session: AsyncSession, placed: Placement, people: Iterable[int]) -> list[int]:
    anchors = set(people)
    joined: list[int] = []
    for row in await marriages_among(session, anchors):
        for person, partner in ((row.first_id, row.second_id), (row.second_id, row.first_id)):
            if person in anchors and placed.place(partner, placed.generations[person]):
                joined.append(partner)
    for bond in await bonds_touching(session, PARTNER_KINDS, anchors):
        for person, partner in ((bond.source_node_id, bond.target_node_id), (bond.target_node_id, bond.source_node_id)):
            if person in anchors and placed.place(partner, placed.generations[person]):
                joined.append(partner)
    return joined


async def join_stepchildren(session: AsyncSession, placed: Placement, partners: Iterable[int], down: int) -> None:
    for bond in await parent_bonds(session, parents=partners):
        level = placed.generations[bond.source_node_id] + 1
        if level <= down:
            placed.place(bond.target_node_id, level)


async def join_carers(session: AsyncSession, placed: Placement, care: frozenset[BondKind]) -> None:
    anchors = set(placed.generations)
    for bond in await bonds_touching(session, care, anchors):
        step = CARE_STEPS.get(bond.kind)
        if step is None:
            continue
        if bond.source_node_id in anchors:
            placed.place(bond.target_node_id, placed.generations[bond.source_node_id] + step)
        elif bond.target_node_id in anchors:
            placed.place(bond.source_node_id, placed.generations[bond.target_node_id] - step)


def ink_of(emblem: dict[str, str]) -> ArmsInk | None:
    name = emblem.get("field")
    if name is None:
        return None
    tincture = LEGACY_TINCTURES.get(name) or (Tincture(name) if name in Tincture.__members__.values() else None)
    if tincture is None:
        return None
    return ArmsInk(FUR_SOLIDS.get(tincture, tincture).value)


async def houses_of(session: AsyncSession, people: list[int]) -> tuple[dict[int, int], list[KinHouse]]:
    members = await session.scalars(
        select(HouseMemberRow)
        .where(HouseMemberRow.mortal_entity_id.in_(people))
        .order_by(HouseMemberRow.by_marriage, HouseMemberRow.joined_epoch, HouseMemberRow.house_entity_id)
    )
    chosen: dict[int, int] = {}
    for member in members:
        chosen.setdefault(member.mortal_entity_id, member.house_entity_id)
    house_ids = sorted(set(chosen.values()))
    rows = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_(house_ids)).order_by(EntityRow.id))}
    profiles = {row.house_entity_id: row for row in await session.scalars(select(HouseProfileRow).where(HouseProfileRow.house_entity_id.in_(house_ids)))}
    houses = [
        KinHouse(id=house_id, name=rows[house_id].name, ink=ink_of(profiles[house_id].emblem) if house_id in profiles else None)
        for house_id in house_ids
        if house_id in rows
    ]
    return {person: house for person, house in chosen.items() if house in rows}, houses


async def trace_family(session: AsyncSession, root: int, up: int, down: int, care: frozenset[BondKind] = frozenset(CARE_KINDS)) -> TracedFamily:
    placed = Placement()
    placed.place(root, 0)
    deeper_up = await climb(session, placed, root, up)
    climbed = set(placed.generations)
    deeper_down = await descend(session, placed, up, down)
    await settle(session, placed, climbed)
    blood = set(placed.generations)
    partners = await join_partners(session, placed, blood)
    partners += await join_partners(session, placed, partners)
    await join_stepchildren(session, placed, partners, down)
    await join_carers(session, placed, care)
    rows = list(await session.scalars(select(EntityRow).where(EntityRow.id.in_(sorted(placed.generations))).order_by(EntityRow.id)))
    present = {row.id for row in rows}
    covers = await covers_of(session, present)
    house_of, houses = await houses_of(session, sorted(present))
    people = [
        Kin(
            id=row.id,
            name=row.name,
            title=row.title,
            living=row.status is EntityStatus.CANON,
            sex=sex_of_stats(row) if isinstance(row.stats, MortalStats) else None,
            role=row.mortal_role,
            generation=placed.generations[row.id],
            birth_epoch=row.birth_epoch,
            end_epoch=row.end_epoch,
            cover=covers.get(row.id),
            house_id=house_of.get(row.id),
            blood=row.id in blood,
        )
        for row in sorted(rows, key=lambda row: (placed.generations[row.id], row.birth_epoch, row.id))
    ]
    unions = [
        KinUnion(
            marriage_id=row.id,
            first_id=row.first_id,
            second_id=row.second_id,
            form=row.form,
            purpose=row.purpose,
            start_epoch=row.start_epoch,
            end_epoch=row.end_epoch,
            cause_end=row.cause_end,
            forced=row.forced,
        )
        for row in await marriages_among(session, present)
        if row.first_id in present and row.second_id in present
    ]
    kinds = (BondKind.PARENT_OF, *PARTNER_KINDS, *sorted(care))
    ties = [
        KinTie(
            bond_id=bond.id,
            kind=bond.kind,
            source_id=bond.source_node_id,
            target_id=bond.target_node_id,
            past=bond.state is BondState.PAST,
            epoch=bond.epoch,
        )
        for bond in await bonds_touching(session, kinds, present)
        if bond.source_node_id in present and bond.target_node_id in present
    ]
    used = {house.id for house in houses if any(person.house_id == house.id for person in people)}
    return TracedFamily(
        root=root,
        up=up,
        down=down,
        deeper_up=deeper_up,
        deeper_down=deeper_down,
        people=people,
        houses=[house for house in houses if house.id in used],
        unions=unions,
        ties=ties,
    )
