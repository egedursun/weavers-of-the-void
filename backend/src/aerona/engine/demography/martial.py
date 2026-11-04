from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.demography import MartialStyle
from aerona.engine.body.customs import people_of
from aerona.engine.demography.peoples import tally_battle

RECORD_LOCK = "martial_record"
DEPTH_FIXUP = "peoples.depth_backfill"


@dataclass
class BattleTally:
    fought: dict[int, list[tuple[int, bool, int | None]]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    async def load(cls, session: AsyncSession, since: int, epoch: int) -> "BattleTally":
        tally = cls()
        found: dict[int, int | None] = {}

        async def folk(entity_id: int) -> int | None:
            if entity_id not in found:
                entity = await session.get(EntityRow, entity_id)
                people = await people_of(session, entity) if entity is not None else None
                found[entity_id] = people.id if people is not None else None
            return found[entity_id]

        rows = await session.scalars(select(BattleRow).where(BattleRow.epoch > since, BattleRow.epoch <= epoch).order_by(BattleRow.epoch, BattleRow.id))
        for battle in rows:
            winner, loser = await folk(battle.winner_entity_id), await folk(battle.loser_entity_id)
            if winner is not None:
                tally.fought[winner].append((battle.epoch, True, loser))
            if loser is not None:
                tally.fought[loser].append((battle.epoch, False, winner))
        return tally


async def backfill_records(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, DEPTH_FIXUP) is not None:
        return 0
    rows = list(await session.scalars(select(PeopleCultureRow)))
    for row in rows:
        if RECORD_LOCK not in row.locked:
            row.martial_record = {}
        row.martial_epoch = 0
    session.add(AppliedFixupRow(key=DEPTH_FIXUP, result={"peoples": len(rows)}))
    await session.flush()
    return len(rows)


async def earliest_tally(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.min(PeopleCultureRow.martial_epoch))) or 0)


async def record_battles(session: AsyncSession, tally: BattleTally, culture: PeopleCultureRow, epoch: int) -> MartialStyle | None:
    victors: Counter[MartialStyle] = Counter()
    for when, won, enemy in tally.fought.get(culture.people_entity_id, []):
        if when <= culture.martial_epoch:
            continue
        if RECORD_LOCK not in culture.locked:
            tally_battle(culture, won=won)
        if not won and enemy is not None:
            foe = await session.get(PeopleCultureRow, enemy)
            if foe is not None:
                victors[foe.martial_style] += 1
    culture.martial_epoch = epoch
    return max(victors, key=lambda style: (victors[style], style.value)) if victors else None
