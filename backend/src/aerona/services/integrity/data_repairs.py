import hashlib
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.fate.naming import requeue_engine_drafts
from aerona.catalog.bonds import EVENT_BOND_KINDS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import ROLE_BOND_KINDS, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.cosmos.ladder import ensure_ladder
from aerona.engine.primitives.canon_facts import seed_if_empty
from aerona.rules.registry import Rules
from aerona.services.bonds import BondService, flip_reversed, resolve_all_friend_and_foe
from aerona.services.images.records import clear_file_name_captions
from aerona.services.importance import persist_if_missing
from aerona.services.integrity.age_consistency import raise_lifespans
from aerona.services.integrity.containment import close_market_trade, close_mismatched_inside
from aerona.services.integrity.epoch_years import align_epoch_years
from aerona.services.integrity.folk_names import repair_belief_names
from aerona.services.integrity.graph_ends import repair_graph_ends
from aerona.services.integrity.location_bonds import add_missing_inside_bonds, close_stale_inside_bonds
from aerona.services.integrity.network import RepairLog
from aerona.services.integrity.single_ruler import homeland_to_lives_in, single_rule
from aerona.services.integrity.war_truces import close_unfought_truces
from aerona.services.name_report import refit_pending_names
from aerona.services.narrative import backfill_endings, sweep_narratives

logger = logging.getLogger(__name__)

DUPLICATE_BOND = "duplicate bond"
HISTORY_REPAIRS_KEY = "history_repairs"
SIGNATURE_FIELD = "signature"
SIGNED_SERVICES = ("narrative.py", "name_report.py")
STATS_TABLE_QUERY = "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_stat1'"

Repair = Callable[[AsyncSession, Rules, int], Awaitable[int]]
StepReport = Callable[[str, int, int], None]


async def close_duplicate_bonds(session: AsyncSession, epoch: int) -> int:
    seen: set[tuple[object, ...]] = set()
    repository = BondRepository(session)
    closed = 0
    for bond in list(await session.scalars(select(BondRow).where(BondRow.state == BondState.ACTIVE).order_by(BondRow.id))):
        if bond.kind in EVENT_BOND_KINDS:
            continue
        key: tuple[object, ...] = (bond.source_node_id, bond.target_node_id, bond.kind)
        if bond.kind in ROLE_BOND_KINDS:
            key += (bond.role, bond.description or "")
        if key in seen:
            await repository.deactivate(bond, epoch, DUPLICATE_BOND, BondState.HIDDEN_CLOSED)
            closed += 1
        else:
            seen.add(key)
    return closed


async def mark_rejected_bonds(session: AsyncSession, epoch: int) -> int:
    rejected = select(EntityRow.id).where(EntityRow.status == EntityStatus.REJECTED)
    statement = select(BondRow).where(
        or_(BondRow.source_node_id.in_(rejected), BondRow.target_node_id.in_(rejected)), BondRow.state.in_([BondState.ACTIVE, BondState.PAST])
    )
    marked = 0
    for bond in await session.scalars(statement):
        bond.state = BondState.HIDDEN_REJECTED
        bond.closed_epoch = bond.closed_epoch or epoch
        marked += 1
    await session.flush()
    return marked


GRAPH_ENDS_STEP = "graph_ends"


class DataRepairs:
    def __init__(self, bonds: BondService, log: RepairLog) -> None:
        self._bonds = bonds
        self._log = log

    def steps(self) -> list[tuple[str, Repair]]:
        return [
            ("friend_and_foe", lambda session, rules, epoch: resolve_all_friend_and_foe(session, rules)),
            ("shared_thrones", self._bonds.enforce_single_throne),
            ("bond_endpoints", lambda session, rules, epoch: flip_reversed(session)),
            ("duplicate_bonds", lambda session, rules, epoch: close_duplicate_bonds(session, epoch)),
            ("rejection_marks", lambda session, rules, epoch: mark_rejected_bonds(session, epoch)),
            ("stale_location_bonds", lambda session, rules, epoch: close_stale_inside_bonds(session, epoch)),
            ("homeland_rule", lambda session, rules, epoch: homeland_to_lives_in(session, epoch)),
            ("single_rule", lambda session, rules, epoch: single_rule(session, epoch)),
            ("inside_bonds", lambda session, rules, epoch: close_mismatched_inside(session, epoch)),
            ("market_trade", lambda session, rules, epoch: close_market_trade(session, epoch)),
            ("unfought_truces", close_unfought_truces),
            ("missing_inside", lambda session, rules, epoch: add_missing_inside_bonds(session, epoch)),
            ("epoch_years", lambda session, rules, epoch: align_epoch_years(session, rules)),
            ("belief_names", lambda session, rules, epoch: repair_belief_names(session, rules)),
            ("pending_dialect_names", refit_pending_names),
            ("engine_drafts", lambda session, rules, epoch: requeue_engine_drafts(session)),
        ]

    async def run(self, session: AsyncSession, rules: Rules, on_step: StepReport | None = None) -> dict[str, int]:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            return {}
        counters: dict[str, int] = {}
        steps = self.steps()
        for index, (name, step) in enumerate(steps, start=1):
            if on_step is not None:
                on_step(name, index, len(steps))
            async with session.begin_nested():
                counters[name] = await step(session, rules, cosmos.epoch)
        changed = {name: value for name, value in counters.items() if value}
        if changed:
            logger.info("data repairs: %s", changed)
        return counters

    def startup_steps(self) -> list[tuple[str, Repair]]:
        return [
            ("importance", persist_if_missing),
            ("planner_statistics", planner_statistics),
            ("data_repairs", self.run_all),
            (GRAPH_ENDS_STEP, self.graph_ends),
            ("certain_facts", lambda session, rules, epoch: seed_if_empty(session)),
            ("scale_ladder", lambda session, rules, epoch: ensure_ladder(session, rules)),
        ]

    def history_steps(self) -> list[tuple[str, Repair]]:
        return [
            ("mortal_ages", lambda session, rules, epoch: raise_lifespans(session, rules)),
            ("narrative_leaks", lambda session, rules, epoch: sweep_narratives(session)),
            ("endings", lambda session, rules, epoch: backfill_endings(session)),
            ("captions", lambda session, rules, epoch: clear_file_name_captions(session)),
        ]

    async def run_all(self, session: AsyncSession, rules: Rules, epoch: int) -> int:
        return sum((await self.run(session, rules)).values())

    async def graph_ends(self, session: AsyncSession, rules: Rules, epoch: int) -> int:
        return (await repair_graph_ends(session, rules, epoch, self._log)).total

    async def startup(self, session: AsyncSession, rules: Rules, *, history: bool = True) -> dict[str, int]:
        cosmos = await CosmosRepository(session).get()
        if cosmos is None:
            return {}
        counters: dict[str, int] = {}
        steps = self.startup_steps() + (self.history_steps() if history else [])
        for name, step in steps:
            counters[name] = await step(session, rules, cosmos.epoch)
        if history:
            await sign_history(session)
        return counters


async def planner_statistics(session: AsyncSession, rules: Rules, epoch: int) -> int:
    await refresh_planner_statistics(session)
    return 0


def history_signature() -> str:
    services = Path(__file__).resolve().parent.parent
    sources = sorted(services.joinpath("integrity").glob("*.py")) + [services / name for name in SIGNED_SERVICES]
    digest = hashlib.sha1(usedforsecurity=False)
    for source in sources:
        if source.exists():
            digest.update(source.name.encode())
            digest.update(source.read_bytes())
    return digest.hexdigest()


async def history_signed(session: AsyncSession) -> bool:
    row = await session.get(AppliedFixupRow, HISTORY_REPAIRS_KEY)
    return row is not None and (row.result or {}).get(SIGNATURE_FIELD) == history_signature()


async def sign_history(session: AsyncSession) -> None:
    row = await session.get(AppliedFixupRow, HISTORY_REPAIRS_KEY)
    if row is None:
        session.add(AppliedFixupRow(key=HISTORY_REPAIRS_KEY, result={SIGNATURE_FIELD: history_signature()}))
    else:
        row.result = {SIGNATURE_FIELD: history_signature()}
    await session.flush()


async def refresh_planner_statistics(session: AsyncSession) -> None:
    if await session.scalar(text(STATS_TABLE_QUERY)) is None:
        await session.execute(text("ANALYZE"))
    else:
        await session.execute(text("PRAGMA optimize"))


def checkpoint(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()
