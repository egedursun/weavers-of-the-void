from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mortal import MarriageEnd
from aerona.services.kinship.tree import CARE_KINDS, Kin, KinTie, KinUnion, TracedFamily

CARD_WIDTH = 232
CARD_HEIGHT = 84
SPOUSE_GAP = 60
SIBLING_GAP = 28
BRANCH_GAP = 84
ROW_GAP = 156
PAD = 72
LANE_STEP = 12
BUS_RISE = 40
JUNCTION_DROP = 16
ARC_LIFT = 26
CARE_BOW = 70
ORDER_SWEEPS = 10
PLACE_PASSES = 24
FREE_WEIGHT = 0.15
LANE_CLEARANCE = 12
UNPLACED = 3
PARTNER_KINDS = (BondKind.CONCUBINE_OF, BondKind.BETROTHED_TO)


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class PlacedCard:
    person_id: int
    x: float
    y: float


@dataclass(frozen=True)
class PartnerMark:
    key: str
    first: int
    second: int
    kind: BondKind
    ended: bool
    widowed: bool
    marriage_id: int | None
    bond_id: int | None
    path: str
    knot: Point


@dataclass
class FamilyLine:
    key: str
    parents: list[int]
    children: list[int]
    path: str


@dataclass(frozen=True)
class CareLine:
    tie: KinTie
    path: str


@dataclass(frozen=True)
class RowBand:
    generation: int
    y: float


@dataclass(frozen=True)
class FamilyLayout:
    width: float
    height: float
    cards: dict[int, PlacedCard]
    partners: list[PartnerMark]
    families: list[FamilyLine]
    care: list[CareLine]
    rows: list[RowBand]


@dataclass(frozen=True)
class Partnership:
    key: str
    first: int
    second: int
    kind: BondKind
    ended: bool
    widowed: bool
    union: KinUnion | None
    tie: KinTie | None


@dataclass
class Family:
    key: str
    parents: list[int]
    children: list[int] = field(default_factory=list)


@dataclass
class Cluster:
    generation: int
    members: list[int]
    width: float
    center: float = 0.0


@dataclass
class Bus:
    family: Family
    start: Point
    lead: str
    children: list[int]
    low: float
    high: float
    top: float
    lane: int = 0


def pair_key(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def num(value: float) -> str:
    return f"{round(value, 1):g}"


def partnerships_of(family: TracedFamily) -> dict[tuple[int, int], Partnership]:
    found: dict[tuple[int, int], Partnership] = {}
    for union in family.unions:
        key = pair_key(union.first_id, union.second_id)
        known = found.get(key)
        if known is not None and known.union is not None and known.union.start_epoch > union.start_epoch:
            continue
        found[key] = Partnership(
            key=f"marriage-{union.marriage_id}",
            first=union.first_id,
            second=union.second_id,
            kind=BondKind.SPOUSE_OF,
            ended=union.end_epoch is not None and union.cause_end is not MarriageEnd.DEATH,
            widowed=union.cause_end is MarriageEnd.DEATH,
            union=union,
            tie=None,
        )
    for tie in family.ties:
        if tie.kind not in PARTNER_KINDS:
            continue
        key = pair_key(tie.source_id, tie.target_id)
        if key in found:
            continue
        found[key] = Partnership(
            key=f"tie-{tie.bond_id}", first=tie.source_id, second=tie.target_id, kind=tie.kind, ended=tie.past, widowed=False, union=None, tie=tie
        )
    return found


def families_of(family: TracedFamily, partnerships: dict[tuple[int, int], Partnership], extras: list[KinTie]) -> list[Family]:
    parent_ties: dict[int, list[KinTie]] = defaultdict(list)
    for tie in family.ties:
        if tie.kind is BondKind.PARENT_OF:
            parent_ties[tie.target_id].append(tie)
    families: dict[str, Family] = {}
    for child in sorted(parent_ties):
        ties = parent_ties[child]
        parents = sorted(tie.source_id for tie in ties)
        pair = parents[:2]
        if len(parents) > 2:
            for i, first in enumerate(parents):
                for second in parents[i + 1 :]:
                    if pair_key(first, second) in partnerships:
                        pair = [first, second]
        extras.extend(tie for tie in ties if tie.source_id not in pair)
        key = "-".join(str(parent) for parent in pair)
        found = families.setdefault(key, Family(key=key, parents=pair))
        found.children.append(child)
    return list(families.values())


def order_members(members: list[int], links: dict[int, list[int]], rank: Callable[[int, int], int]) -> list[int]:
    if len(members) == 1:
        return members
    ordered_ids = sorted(members)
    hub = ordered_ids[0]
    for person in ordered_ids:
        if len(links.get(person, [])) > len(links.get(hub, [])):
            hub = person
    placed = {hub}

    def chain(start: int) -> list[int]:
        line: list[int] = []
        current: int | None = start
        while current is not None and current not in placed:
            placed.add(current)
            line.append(current)
            current = next((other for other in sorted(links.get(current, [])) if other not in placed), None)
        return line

    leaves = sorted(links.get(hub, []), key=lambda leaf: (rank(hub, leaf), leaf))
    arms = [arm for arm in (chain(leaf) for leaf in leaves) if arm]
    left: list[list[int]] = []
    right: list[list[int]] = []
    for arm in arms:
        side = left if sum(map(len, left)) < sum(map(len, right)) else right
        side.append(arm)
    ordered = [person for arm in reversed(left) for person in reversed(arm)] + [hub] + [person for arm in right for person in arm]
    return ordered + [person for person in ordered_ids if person not in ordered]


def clusters_of(people: list[Kin], partnerships: dict[tuple[int, int], Partnership]) -> list[Cluster]:
    generation = {person.id: person.generation for person in people}
    links: dict[int, list[int]] = defaultdict(list)
    for partnership in partnerships.values():
        if generation[partnership.first] == generation[partnership.second]:
            links[partnership.first].append(partnership.second)
            links[partnership.second].append(partnership.first)

    def rank(first: int, second: int) -> int:
        partnership = partnerships.get(pair_key(first, second))
        if partnership is None or partnership.ended:
            return UNPLACED
        if partnership.widowed:
            return 2
        return 0 if partnership.kind is BondKind.SPOUSE_OF else 1

    seen: set[int] = set()
    clusters: list[Cluster] = []
    for person in people:
        if person.id in seen:
            continue
        members: list[int] = []
        queue = [person.id]
        seen.add(person.id)
        while queue:
            current = queue.pop(0)
            members.append(current)
            for other in links.get(current, []):
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        ordered = order_members(members, links, rank)
        clusters.append(Cluster(generation=person.generation, members=ordered, width=len(ordered) * CARD_WIDTH + (len(ordered) - 1) * SPOUSE_GAP))
    return clusters


def isotonic(targets: list[float], weights: list[float]) -> list[float]:
    blocks: list[list[float]] = []
    for target, weight in zip(targets, weights, strict=True):
        blocks.append([target, weight, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            last = blocks.pop()
            before = blocks.pop()
            total = before[1] + last[1]
            blocks.append([(before[0] * before[1] + last[0] * last[1]) / total, total, before[2] + last[2]])
    return [block[0] for block in blocks for _ in range(int(block[2]))]


class Arrangement:
    def __init__(self, family: TracedFamily) -> None:
        self.people = family.people
        self.by_id = {person.id: person for person in family.people}
        self.partnerships = partnerships_of(family)
        self.extras: list[KinTie] = []
        self.families = families_of(family, self.partnerships, self.extras)
        self.child_of: dict[int, Family] = {}
        self.parent_in: dict[int, list[Family]] = defaultdict(list)
        for found in self.families:
            for child in found.children:
                self.child_of[child] = found
            for parent in found.parents:
                self.parent_in[parent].append(found)
        self.reaches: dict[int, list[int]] = defaultdict(list)
        for partnership in self.partnerships.values():
            if self.by_id[partnership.first].generation != self.by_id[partnership.second].generation:
                self.reaches[partnership.first].append(partnership.second)
                self.reaches[partnership.second].append(partnership.first)
        self.care_ties = [tie for tie in family.ties if tie.kind in CARE_KINDS]
        for tie in self.care_ties:
            self.reaches[tie.source_id].append(tie.target_id)
            self.reaches[tie.target_id].append(tie.source_id)
        self.clusters = clusters_of(family.people, self.partnerships)
        self.cluster_of = {member: cluster for cluster in self.clusters for member in cluster.members}
        self.generations = sorted({person.generation for person in family.people})
        self.rows = {
            generation: sorted(
                (cluster for cluster in self.clusters if cluster.generation == generation),
                key=lambda cluster: (min(self.by_id[member].birth_epoch for member in cluster.members), cluster.members[0]),
            )
            for generation in self.generations
        }
        self.slot: dict[int, float] = {}

    def offset(self, person: int) -> float:
        cluster = self.cluster_of[person]
        return cluster.members.index(person) * (CARD_WIDTH + SPOUSE_GAP) + CARD_WIDTH / 2 - cluster.width / 2

    def index_rows(self) -> None:
        for row in self.rows.values():
            for index, cluster in enumerate(row):
                for place, member in enumerate(cluster.members):
                    self.slot[member] = index + (place + 0.5) / len(cluster.members)

    def reorder(self, generation: int, score: Callable[[Cluster], float | None]) -> None:
        row = self.rows[generation]
        keyed = []
        for index, cluster in enumerate(row):
            value = score(cluster)
            keyed.append((index + 0.5 if value is None else value, index, cluster))
        keyed.sort(key=lambda entry: (entry[0], entry[1]))
        self.rows[generation] = [entry[2] for entry in keyed]
        self.index_rows()

    def from_parents(self, cluster: Cluster) -> float | None:
        values = [mean([self.slot[parent] for parent in self.child_of[member].parents]) for member in cluster.members if member in self.child_of]
        return mean(values) if values else None

    def from_children(self, cluster: Cluster) -> float | None:
        values = [self.slot[child] for member in cluster.members for own in self.parent_in.get(member, []) for child in own.children]
        return mean(values) if values else None

    def order(self) -> None:
        self.index_rows()
        for _ in range(ORDER_SWEEPS):
            for generation in self.generations[1:]:
                self.reorder(generation, self.from_parents)
            for generation in list(reversed(self.generations))[1:]:
                self.reorder(generation, self.from_children)
        for generation in self.generations[1:]:
            self.reorder(generation, self.from_parents)

    def siblings(self, first: Cluster, second: Cluster) -> bool:
        return any(a in self.child_of and self.child_of.get(a) is self.child_of.get(b) for a in first.members for b in second.members)

    def gaps(self, row: list[Cluster]) -> list[float]:
        return [
            row[index].width / 2 + (SIBLING_GAP if self.siblings(row[index], cluster) else BRANCH_GAP) + cluster.width / 2
            for index, cluster in enumerate(row[1:])
        ]

    def center(self, person: int) -> float:
        return self.cluster_of[person].center + self.offset(person)

    def anchor(self, found: Family) -> float:
        return mean([self.center(parent) for parent in found.parents])

    def settle_row(self, generation: int) -> None:
        row = self.rows[generation]
        targets: list[float] = []
        weights: list[float] = []
        for cluster in row:
            pulls: list[float] = []
            for member in cluster.members:
                if member in self.child_of:
                    pulls.append(self.anchor(self.child_of[member]) - self.offset(member))
                pulls.extend(self.center(other) - self.offset(member) for other in self.reaches.get(member, []))
                pulls.extend(cluster.center + mean([self.center(child) for child in own.children]) - self.anchor(own) for own in self.parent_in.get(member, []))
            targets.append(mean(pulls) if pulls else cluster.center)
            weights.append(len(pulls) if pulls else FREE_WEIGHT)
        offsets = [0.0]
        for gap in self.gaps(row):
            offsets.append(offsets[-1] + gap)
        settled = isotonic([target - offset for target, offset in zip(targets, offsets, strict=True)], weights)
        for cluster, value, offset in zip(row, settled, offsets, strict=True):
            cluster.center = value + offset

    def place(self) -> None:
        for row in self.rows.values():
            at = 0.0
            for cluster, gap in zip(row, [*self.gaps(row), 0.0], strict=True):
                cluster.center = at
                at += gap
        for turn in range(PLACE_PASSES):
            for generation in self.generations if turn % 2 == 0 else list(reversed(self.generations)):
                self.settle_row(generation)

    def adjacent(self, first: int, second: int) -> bool:
        cluster = self.cluster_of[first]
        return cluster is self.cluster_of[second] and abs(cluster.members.index(first) - cluster.members.index(second)) == 1


def partner_mark(arrangement: Arrangement, cards: dict[int, PlacedCard], partnership: Partnership) -> PartnerMark:
    a = cards[partnership.first]
    b = cards[partnership.second]
    lefty, righty = (a, b) if a.x <= b.x else (b, a)
    if a.y == b.y and arrangement.adjacent(partnership.first, partnership.second):
        y = a.y + CARD_HEIGHT / 2
        start = lefty.x + CARD_WIDTH
        path = f"M {num(start)} {num(y)} H {num(righty.x)}"
        knot = Point((start + righty.x) / 2, y)
    elif a.y == b.y:
        ax = lefty.x + CARD_WIDTH / 2
        bx = righty.x + CARD_WIDTH / 2
        top = a.y - ARC_LIFT
        path = f"M {num(ax)} {num(a.y)} C {num(ax)} {num(top)}, {num(bx)} {num(top)}, {num(bx)} {num(a.y)}"
        knot = Point((ax + bx) / 2, a.y - ARC_LIFT * 3 / 4)
    else:
        upper, lower = (a, b) if a.y < b.y else (b, a)
        start_point = Point(upper.x + CARD_WIDTH / 2, upper.y + CARD_HEIGHT)
        end = Point(lower.x + CARD_WIDTH / 2, lower.y)
        bend = (end.y - start_point.y) / 2
        path = (
            f"M {num(start_point.x)} {num(start_point.y)} C {num(start_point.x)} {num(start_point.y + bend)}, "
            f"{num(end.x)} {num(end.y - bend)}, {num(end.x)} {num(end.y)}"
        )
        knot = Point((start_point.x + end.x) / 2, (start_point.y + end.y) / 2)
    return PartnerMark(
        key=partnership.key,
        first=partnership.first,
        second=partnership.second,
        kind=partnership.kind,
        ended=partnership.ended,
        widowed=partnership.widowed,
        marriage_id=partnership.union.marriage_id if partnership.union is not None else None,
        bond_id=partnership.tie.bond_id if partnership.tie is not None else None,
        path=path,
        knot=Point(round(knot.x, 1), round(knot.y, 1)),
    )


def bus_start(arrangement: Arrangement, cards: dict[int, PlacedCard], marks: dict[tuple[int, int], PartnerMark], found: Family) -> tuple[Point, str]:
    def mid(person: int) -> float:
        return cards[person].x + CARD_WIDTH / 2

    first = found.parents[0]
    if len(found.parents) == 1:
        return Point(mid(first), cards[first].y + CARD_HEIGHT), ""
    second = found.parents[1]
    mark = marks.get(pair_key(first, second))
    if mark is not None and cards[first].y == cards[second].y and arrangement.adjacent(first, second):
        return mark.knot, ""
    junction = max(cards[first].y, cards[second].y) + CARD_HEIGHT + JUNCTION_DROP
    lead = " ".join(f"M {num(mid(parent))} {num(cards[parent].y + CARD_HEIGHT)} V {num(junction)}" for parent in found.parents)
    lead += f" M {num(min(mid(first), mid(second)))} {num(junction)} H {num(max(mid(first), mid(second)))}"
    return Point((mid(first) + mid(second)) / 2, junction), lead


def assign_lanes(buses: list[Bus]) -> None:
    by_top: dict[float, list[Bus]] = defaultdict(list)
    for bus in buses:
        by_top[bus.top].append(bus)
    for group in by_top.values():
        lanes: list[float] = []
        for bus in sorted(group, key=lambda item: item.low):
            free = next((index for index, end in enumerate(lanes) if end < bus.low - LANE_CLEARANCE), None)
            bus.lane = len(lanes) if free is None else free
            if free is None:
                lanes.append(bus.high)
            else:
                lanes[free] = bus.high


def family_lines(arrangement: Arrangement, cards: dict[int, PlacedCard], marks: dict[tuple[int, int], PartnerMark]) -> list[FamilyLine]:
    def mid(person: int) -> float:
        return cards[person].x + CARD_WIDTH / 2

    buses: list[Bus] = []
    for found in arrangement.families:
        start, lead = bus_start(arrangement, cards, marks, found)
        by_row: dict[float, list[int]] = defaultdict(list)
        for child in found.children:
            by_row[cards[child].y].append(child)
        for top, children in by_row.items():
            xs = [start.x, *(mid(child) for child in children)]
            buses.append(Bus(family=found, start=start, lead=lead, children=children, low=min(xs), high=max(xs), top=top))
            lead = ""
    assign_lanes(buses)
    lines: dict[str, FamilyLine] = {}
    for bus in buses:
        y = bus.top - BUS_RISE - bus.lane * LANE_STEP
        drops = " ".join(f"M {num(mid(child))} {num(y)} V {num(bus.top)}" for child in bus.children)
        path = f"{bus.lead} M {num(bus.start.x)} {num(bus.start.y)} V {num(y)} M {num(bus.low)} {num(y)} H {num(bus.high)} {drops}".strip()
        known = lines.get(bus.family.key)
        if known is None:
            lines[bus.family.key] = FamilyLine(key=bus.family.key, parents=bus.family.parents, children=list(bus.children), path=path)
        else:
            known.path += f" {path}"
            known.children.extend(bus.children)
    return list(lines.values())


def care_line(cards: dict[int, PlacedCard], tie: KinTie) -> CareLine:
    a = cards[tie.source_id]
    b = cards[tie.target_id]
    if a.y == b.y:
        ax = a.x + CARD_WIDTH / 2
        bx = b.x + CARD_WIDTH / 2
        y = a.y + CARD_HEIGHT
        return CareLine(tie=tie, path=f"M {num(ax)} {num(y)} C {num(ax)} {num(y + CARE_BOW)}, {num(bx)} {num(y + CARE_BOW)}, {num(bx)} {num(y)}")
    upper, lower = (a, b) if a.y < b.y else (b, a)
    start = Point(upper.x + CARD_WIDTH * 3 / 4, upper.y + CARD_HEIGHT)
    end = Point(lower.x + CARD_WIDTH / 4, lower.y)
    bend = (end.y - start.y) / 2
    return CareLine(
        tie=tie, path=f"M {num(start.x)} {num(start.y)} C {num(start.x)} {num(start.y + bend)}, {num(end.x)} {num(end.y - bend)}, {num(end.x)} {num(end.y)}"
    )


def lay_out(family: TracedFamily) -> FamilyLayout:
    arrangement = Arrangement(family)
    arrangement.order()
    arrangement.place()
    left = min(cluster.center - cluster.width / 2 for cluster in arrangement.clusters)
    right = max(cluster.center + cluster.width / 2 for cluster in arrangement.clusters)
    shift = PAD - left
    row_y = {generation: PAD + ARC_LIFT + index * (CARD_HEIGHT + ROW_GAP) for index, generation in enumerate(arrangement.generations)}
    cards = {
        person.id: PlacedCard(person_id=person.id, x=round(arrangement.center(person.id) + shift - CARD_WIDTH / 2, 1), y=row_y[person.generation])
        for person in family.people
    }
    partners = [partner_mark(arrangement, cards, partnership) for partnership in arrangement.partnerships.values()]
    marks = {pair_key(mark.first, mark.second): mark for mark in partners}
    count = len(arrangement.generations)
    return FamilyLayout(
        width=round(right - left + PAD * 2, 1),
        height=PAD * 2 + ARC_LIFT + count * CARD_HEIGHT + (count - 1) * ROW_GAP + CARE_BOW,
        cards=cards,
        partners=partners,
        families=family_lines(arrangement, cards, marks),
        care=[care_line(cards, tie) for tie in [*arrangement.extras, *arrangement.care_ties]],
        rows=[RowBand(generation=generation, y=row_y[generation]) for generation in arrangement.generations],
    )
