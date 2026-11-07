from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.key_index import index_spec, keyed_rows
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.military import ArmyOfficerRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import RelationshipRow, SocialCircleRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import MoodState
from aerona.domain.enums.relations import CircleKind, RelationType
from aerona.engine.mind.book import is_locked, mind_of
from aerona.engine.mortal.kin import partners_of
from aerona.engine.mortal.kinship import close_between
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.rules.registry import Rules

R = RelationType
RELATIONS_KEY = "relations"
FRIENDLY = frozenset({R.FRIEND, R.CLOSE_FRIEND, R.BEST_FRIEND, R.CONFIDANT})
WARLIKE = frozenset({FactionKind.WARRIOR_ORDER, FactionKind.MERCENARY_COMPANY, FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.VOID_PIRATES})
MOODS = {
    MoodState.ELATED: 2,
    MoodState.CONTENT: 1,
    MoodState.FINE: 0,
    MoodState.UNEASY: -1,
    MoodState.UNHAPPY: -2,
    MoodState.MISERABLE: -3,
    MoodState.BROKEN: -4,
}
BOND_OF = {
    R.LOVER: BondKind.LOVES,
    R.RIVAL: BondKind.RIVAL,
    R.NEMESIS: BondKind.RIVAL,
    R.ENEMY: BondKind.ENEMY,
    R.BEST_FRIEND: BondKind.COMPANION,
    R.CLOSE_FRIEND: BondKind.COMPANION,
}
FIELDS = ("friendship", "romance", "familiarity", "rivalry")


@dataclass
class Facts:
    spouses: set[int] = field(default_factory=set)
    masters: set[int] = field(default_factory=set)
    apprentices: set[int] = field(default_factory=set)
    drinking: set[int] = field(default_factory=set)
    comrades: set[int] = field(default_factory=set)
    wealth: dict[int, int] = field(default_factory=dict)
    skill: dict[int, int] = field(default_factory=dict)


def mood_of(profile: MortalProfileRow | None) -> int:
    return MOODS.get(profile.mood, 0) if profile is not None and profile.mood is not None else 0


RELATION_PAIRS = index_spec(RelationshipRow, "holder_node_id", "subject_node_id")


async def relation(session: AsyncSession, holder_id: int, subject_id: int) -> RelationshipRow | None:
    pairs = await keyed_rows(session, RELATION_PAIRS)
    if pairs is not None:
        found = pairs.rows.get((holder_id, subject_id))
        return found[0] if found else None
    return await session.scalar(select(RelationshipRow).where(RelationshipRow.holder_node_id == holder_id, RelationshipRow.subject_node_id == subject_id))


async def ensure_relation(session: AsyncSession, holder_id: int, subject_id: int, epoch: int) -> RelationshipRow | None:
    if holder_id == subject_id or write_blocked(holder_id, RELATIONS_KEY) or is_locked(await mind_of(session, holder_id), RELATIONS_KEY):
        return None
    row = await relation(session, holder_id, subject_id)
    if row is None:
        row = RelationshipRow(holder_node_id=holder_id, subject_node_id=subject_id, kinds=[], since_epoch=epoch, last_epoch=epoch, locked=[])
        session.add(row)
        await session.flush()
    return row


RELATION_HOLDERS = index_spec(RelationshipRow, "holder_node_id")
RELATION_SUBJECTS = index_spec(RelationshipRow, "subject_node_id")


async def relations_of(session: AsyncSession, holder_id: int) -> list[RelationshipRow]:
    held_rows = await keyed_rows(session, RELATION_HOLDERS)
    if held_rows is not None:
        return sorted(held_rows.rows.get((holder_id,), []), key=lambda row: row.id)
    return list(await session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id == holder_id).order_by(RelationshipRow.id)))


async def relations_about(session: AsyncSession, subject_id: int) -> list[RelationshipRow]:
    about = await keyed_rows(session, RELATION_SUBJECTS)
    if about is not None:
        return sorted(about.rows.get((subject_id,), []), key=lambda row: row.id)
    return list(await session.scalars(select(RelationshipRow).where(RelationshipRow.subject_node_id == subject_id).order_by(RelationshipRow.id)))


def shift(rules: Rules, row: RelationshipRow, epoch: int, **deltas: float) -> None:
    scale = rules.social.delta_pct / PERCENT
    for name, delta in deltas.items():
        if not delta or name in row.locked:
            continue
        low = RELATION_MIN if name == "friendship" else 0
        high = RELATION_MAX if name == "friendship" else PERCENT
        setattr(row, name, clamp_int(getattr(row, name) + delta * scale, low, high))
    row.last_epoch = epoch


async def facts_for(session: AsyncSession, holder_id: int, others: Iterable[int]) -> Facts:
    facts = Facts(spouses=set(await partners_of(session, holder_id)))
    facts.masters = {bond.target_node_id for bond in await active_bonds(session, [BondKind.APPRENTICE_OF], sources=[holder_id])}
    facts.apprentices = {bond.source_node_id for bond in await active_bonds(session, [BondKind.APPRENTICE_OF], targets=[holder_id])}
    halls = select(SocialCircleRow.faction_entity_id).where(SocialCircleRow.kind == CircleKind.DRINKING_HALL)
    mine = select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id == holder_id)
    facts.drinking = set(
        await session.scalars(
            select(FactionMembershipRow.mortal_entity_id).where(
                FactionMembershipRow.faction_entity_id.in_(halls), FactionMembershipRow.faction_entity_id.in_(mine)
            )
        )
    )
    bands = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind.in_(list(WARLIKE)))
    armies = select(ArmyOfficerRow.army_entity_id).where(ArmyOfficerRow.mortal_entity_id == holder_id, ArmyOfficerRow.until_epoch.is_(None))
    facts.comrades = set(
        await session.scalars(
            select(FactionMembershipRow.mortal_entity_id).where(
                FactionMembershipRow.faction_entity_id.in_(bands), FactionMembershipRow.faction_entity_id.in_(mine)
            )
        )
    )
    serving = select(ArmyOfficerRow.mortal_entity_id).where(ArmyOfficerRow.army_entity_id.in_(armies), ArmyOfficerRow.until_epoch.is_(None))
    facts.comrades |= set(await session.scalars(serving))
    people = {holder_id, *others}
    for profile in await session.scalars(select(MortalProfileRow).where(MortalProfileRow.entity_id.in_(people))):
        facts.wealth[profile.entity_id] = profile.wealth
    for row in await session.scalars(select(SkillRow).where(SkillRow.holder_node_id.in_(people))):
        facts.skill[row.holder_node_id] = max(facts.skill.get(row.holder_node_id, 0), row.level)
    return facts


def held_above(value: int, threshold: int, had: bool, give: int) -> bool:
    return value >= (threshold - give if had else threshold)


def held_below(value: int, threshold: int, had: bool, give: int) -> bool:
    return value <= (threshold + give if had else threshold)


@dataclass(frozen=True)
class Reading:
    rules: Rules
    row: RelationshipRow
    back: RelationshipRow | None
    facts: Facts
    had: frozenset[RelationType]

    def above(self, value: int, threshold: int, *kinds: RelationType) -> bool:
        return held_above(value, threshold, bool(self.had & set(kinds)), self.rules.social.hysteresis)

    def below(self, value: int, threshold: int, *kinds: RelationType) -> bool:
        return held_below(value, threshold, bool(self.had & set(kinds)), self.rules.social.hysteresis)


def romantic_kinds(reading: Reading) -> set[RelationType]:
    table, row = reading.rules.social, reading.row
    kinds: set[RelationType] = {R.SPOUSE} if row.subject_node_id in reading.facts.spouses else set()
    theirs = reading.back.romance if reading.back is not None else 0
    if reading.above(row.romance, table.lover_at, R.LOVER) and reading.above(theirs, table.lover_at, R.LOVER):
        kinds.add(R.LOVER)
    elif reading.above(row.romance, table.crush_at, R.CRUSH):
        kinds.add(R.CRUSH)
    if R.LOVER not in kinds and reading.had & {R.LOVER, R.EX_LOVER}:
        kinds.add(R.EX_LOVER)
    return kinds


def friendly_kinds(reading: Reading, best: bool) -> set[RelationType]:
    table, row = reading.rules.social, reading.row
    if not reading.above(row.friendship, table.friend_at, *FRIENDLY):
        return set()
    kinds = {R.FRIEND}
    if reading.above(row.friendship, table.close_at, R.CLOSE_FRIEND, R.BEST_FRIEND, R.CONFIDANT):
        kinds.add(R.CLOSE_FRIEND)
        if best and reading.above(row.friendship, table.best_at, R.BEST_FRIEND):
            kinds.add(R.BEST_FRIEND)
        if reading.above(row.familiarity, table.confidant_at, R.CONFIDANT):
            kinds.add(R.CONFIDANT)
    return kinds


def hostile_kinds(reading: Reading) -> set[RelationType]:
    table, row = reading.rules.social, reading.row
    kinds: set[RelationType] = {R.ENEMY} if reading.below(row.friendship, table.enemy_at, R.ENEMY) else set()
    if reading.above(row.rivalry, table.rival_at, R.RIVAL, R.NEMESIS):
        kinds.add(R.RIVAL)
        if R.ENEMY in kinds and reading.above(row.rivalry, table.nemesis_at, R.NEMESIS):
            kinds.add(R.NEMESIS)
    return kinds


def standing_kinds(reading: Reading) -> set[RelationType]:
    table, row, facts = reading.rules.social, reading.row, reading.facts
    other, me = row.subject_node_id, row.holder_node_id
    warm = row.friendship >= table.friend_at - table.hysteresis
    gap = facts.skill.get(other, 0) - facts.skill.get(me, 0)
    riches = facts.wealth.get(other, 0) - facts.wealth.get(me, 0)
    checks = {
        R.MENTOR: other in facts.masters or (warm and gap >= table.mentor_gap),
        R.PROTEGE: other in facts.apprentices or (warm and -gap >= table.mentor_gap),
        R.COMRADE_IN_ARMS: other in facts.comrades,
        R.DRINKING_COMPANION: other in facts.drinking and row.friendship >= 0,
        R.PATRON: warm and riches >= table.patron_gap,
        R.CLIENT: warm and -riches >= table.patron_gap,
    }
    return {kind for kind, met in checks.items() if met}


def derive(rules: Rules, row: RelationshipRow, back: RelationshipRow | None, facts: Facts, best: bool) -> set[RelationType]:
    reading = Reading(rules, row, back, facts, frozenset(RelationType(kind) for kind in row.kinds))
    kinds = romantic_kinds(reading) | friendly_kinds(reading, best) | hostile_kinds(reading) | standing_kinds(reading)
    if not kinds and reading.above(row.familiarity, rules.social.acquaintance_at, R.ACQUAINTANCE):
        kinds.add(R.ACQUAINTANCE)
    return kinds


async def sync_bonds(session: AsyncSession, row: RelationshipRow, before: set[RelationType], after: set[RelationType], epoch: int) -> None:
    gained = {BOND_OF[kind] for kind in after - before if kind in BOND_OF}
    kept = {BOND_OF[kind] for kind in after if kind in BOND_OF}
    lost = {BOND_OF[kind] for kind in before - after if kind in BOND_OF} - kept
    for kind in sorted(gained, key=lambda item: item.value):
        await connect(session, row.holder_node_id, row.subject_node_id, kind, epoch, description="a bond that grew between them")
    for kind in sorted(lost, key=lambda item: item.value):
        await close_between(session, row.holder_node_id, row.subject_node_id, (kind,), epoch=epoch, reason="the bond faded")


def ranked(kinds: Iterable[str]) -> list[str]:
    order = [kind.value for kind in RelationType]
    return sorted(set(kinds), key=order.index)


async def refresh_kinds(session: AsyncSession, rules: Rules, holder_id: int, epoch: int) -> list[tuple[RelationshipRow, set[RelationType], set[RelationType]]]:
    rows = [row for row in await relations_of(session, holder_id) if "kinds" not in row.locked]
    if not rows or write_blocked(holder_id, RELATIONS_KEY) or is_locked(await mind_of(session, holder_id), RELATIONS_KEY):
        return []
    facts = await facts_for(session, holder_id, [row.subject_node_id for row in rows])
    backs = {
        row.holder_node_id: row
        for row in await session.scalars(
            select(RelationshipRow).where(
                RelationshipRow.subject_node_id == holder_id, RelationshipRow.holder_node_id.in_([row.subject_node_id for row in rows])
            )
        )
    }
    best = max(rows, key=lambda row: (row.friendship, -row.id))
    changes = []
    for row in rows:
        before = set(RelationType(kind) for kind in row.kinds)
        after = derive(rules, row, backs.get(row.subject_node_id), facts, row is best)
        if after != before:
            row.kinds = ranked(kind.value for kind in after)
            await sync_bonds(session, row, before, after, epoch)
            changes.append((row, before, after))
    return changes


async def pairs_known(session: AsyncSession, ids: Iterable[int]) -> list[RelationshipRow]:
    group = list(ids)
    return list(
        await session.scalars(
            select(RelationshipRow).where(
                or_(RelationshipRow.holder_node_id.in_(group), RelationshipRow.subject_node_id.in_(group)),
            )
        )
    )
