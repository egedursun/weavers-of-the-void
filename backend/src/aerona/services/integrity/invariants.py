from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import JSON, Column, ColumnElement, CompoundSelect, Enum, Integer, RowMapping, Select, Table, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.invariants import DERIVED_REASONS, GENERIC, TYPED, GenericCheck, Remedy
from aerona.db import tables
from aerona.db.base import Base
from aerona.db.columns import column_bounds
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow
from aerona.db.tables.council_order import DivineSeatRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.pantheon import PantheonTieRow, SyncretismRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import OrderKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import CaptiveStatus
from aerona.services.integrity.genome_alleles import mend_alleles, stray_alleles
from aerona.services.integrity.kind_links import bring_into_range, cut_lineage, drop_holding, kinds_out_of_range, stray_holdings, tangled_lineage
from aerona.services.integrity.money_links import clear_metal, clear_source, metal_paper, stray_sources
from aerona.services.integrity.record_links import (
    absent_witnesses,
    broken_checkpoints,
    clear_nesting,
    crossed_nesting,
    drop_fact,
    drop_step,
    drop_witness,
    early_moments,
    follow_cause,
    follow_step,
    give_witness_mode,
    misfit_facts,
    modeless_witnesses,
    retake_checkpoint,
    retire_kind,
    scope_change,
    steps_out_of_order,
    undeclared_steps,
    unknown_kinds,
    unscoped_changes,
)

LOCKED = "locked"
NODE_ID_LIST = "_node_ids"
PAST_EPOCHS = frozenset(
    {
        "created_epoch",
        "since_epoch",
        "updated_epoch",
        "registered_epoch",
        "granted_epoch",
        "founded_epoch",
        "made_epoch",
        "taken_epoch",
        "built_epoch",
        "chartered_epoch",
        "defeated_epoch",
        "last_used_epoch",
        "started_epoch",
    }
)
TARGETED_ORDERS = frozenset({OrderKind.GUARD, OrderKind.PROTECT, OrderKind.DESTROY, OrderKind.FOLLOW})
_ = tables


@dataclass(frozen=True)
class Finding:
    check: GenericCheck | None
    invariant: str | None
    table: str
    column: str | None
    key: str
    problem: str
    resolution: str
    remedy: Remedy


@dataclass
class Sweep:
    repaired: dict[str, int]
    findings: list[Finding]


def every_table() -> dict[str, Table]:
    return dict(sorted(Base.metadata.tables.items()))


def free_json(table: Table) -> list[Column[object]]:
    return [column for column in table.columns if type(column.type) is JSON and column.name != LOCKED and not column.name.endswith(NODE_ID_LIST)]


def keyed_by_thing(table: Table) -> bool:
    keys = list(table.primary_key.columns)
    return len(keys) == 1 and any(foreign.column.table.name in {"nodes", "entities"} for foreign in keys[0].foreign_keys)


def coverage() -> dict[str, str]:
    typed: dict[str, list[str]] = {}
    for spec in TYPED:
        typed.setdefault(spec.table, []).append(spec.text)
    found: dict[str, str] = {}
    for name, table in every_table().items():
        if name in typed:
            found[name] = "; ".join(typed[name])
        elif free_json(table):
            found[name] = DERIVED_REASONS["free_json"]
        elif keyed_by_thing(table):
            found[name] = DERIVED_REASONS["profile"]
        else:
            found[name] = DERIVED_REASONS["columns"]
    return found


def row_key(table: Table, row: RowMapping) -> str:
    return ",".join(f"{column.name}={row[column.name]}" for column in table.primary_key.columns)


def key_filter(table: Table, key: str) -> list[ColumnElement[bool]]:
    pairs = dict(part.split("=", 1) for part in key.split(","))
    return [column == type_of(column)(pairs[column.name]) for column in table.primary_key.columns]


def type_of(column: Column[object]) -> Callable[[str], object]:
    return int if isinstance(column.type, Integer) else str


def changed(result: object) -> int:
    return max(0, int(getattr(result, "rowcount", 0) or 0))


async def clamp_bounds(session: AsyncSession, table: Table) -> int:
    mended = 0
    for name, (low, high) in column_bounds(table).items():
        column = table.columns.get(name)
        if column is None:
            continue
        if low is not None:
            mended += changed(await session.execute(update(table).where(column < low).values({name: low})))
        if high is not None:
            mended += changed(await session.execute(update(table).where(column > high).values({name: high})))
    return mended


async def settle_epochs(session: AsyncSession, table: Table, epoch: int) -> int:
    mended = 0
    for column in table.columns:
        if column.name in PAST_EPOCHS and isinstance(column.type, Integer):
            mended += changed(await session.execute(update(table).where(column > epoch).values({column.name: epoch})))
    return mended


async def prune_node_lists(session: AsyncSession, table: Table, nodes: set[int]) -> int:
    mended = 0
    for column in table.columns:
        if not column.name.endswith(NODE_ID_LIST) or type(column.type) is not JSON:
            continue
        for row in (await session.execute(select(table))).mappings().all():
            ids = row[column.name] or []
            kept = [item for item in ids if item in nodes]
            if len(kept) != len(ids):
                await session.execute(update(table).where(*key_filter(table, row_key(table, row))).values({column.name: kept}))
                mended += 1
    return mended


async def odd_enums(session: AsyncSession, table: Table) -> list[Finding]:
    spec = GENERIC[GenericCheck.ENUM_VALUES]
    found: list[Finding] = []
    for column in table.columns:
        if not isinstance(column.type, Enum) or not column.type.enums:
            continue
        rows = (await session.execute(select(table).where(column.is_not(None), column.not_in(list(column.type.enums))))).mappings().all()
        found.extend(
            Finding(GenericCheck.ENUM_VALUES, None, table.name, column.name, row_key(table, row), f"holds {row[column.name]!r}", spec.resolution, spec.remedy)
            for row in rows
        )
    return found


async def stray_locks(session: AsyncSession, table: Table) -> list[Finding]:
    column = table.columns.get(LOCKED)
    if column is None or type(column.type) is not JSON:
        return []
    spec = GENERIC[GenericCheck.LOCKED_NAMES]
    names = set(table.columns.keys())
    found: list[Finding] = []
    for row in (await session.execute(select(table).where(column.is_not(None)))).mappings().all():
        locked = row[LOCKED]
        stray = sorted(str(item) for item in locked if str(item) not in names) if isinstance(locked, list) else []
        if stray:
            found.append(
                Finding(GenericCheck.LOCKED_NAMES, None, table.name, LOCKED, row_key(table, row), f"holds {', '.join(stray)}", spec.resolution, spec.remedy)
            )
    return found


async def generic_sweep(session: AsyncSession, epoch: int) -> Sweep:
    nodes = set(await session.scalars(select(NodeRow.id)))
    repaired = {GenericCheck.BOUNDED.value: 0, GenericCheck.PAST_EPOCHS.value: 0, GenericCheck.NODE_ID_LISTS.value: 0}
    findings: list[Finding] = []
    for table in every_table().values():
        repaired[GenericCheck.BOUNDED.value] += await clamp_bounds(session, table)
        repaired[GenericCheck.PAST_EPOCHS.value] += await settle_epochs(session, table, epoch)
        repaired[GenericCheck.NODE_ID_LISTS.value] += await prune_node_lists(session, table, nodes)
        findings.extend(await odd_enums(session, table))
        findings.extend(await stray_locks(session, table))
    return Sweep(repaired, findings)


async def resolve_generic(session: AsyncSession, finding: Finding) -> None:
    table = every_table()[finding.table]
    where = key_filter(table, finding.key)
    if finding.check is GenericCheck.LOCKED_NAMES:
        row = (await session.execute(select(table).where(*where))).mappings().first()
        if row is not None:
            kept = [item for item in row[LOCKED] or [] if str(item) in table.columns]
            await session.execute(update(table).where(*where).values({LOCKED: kept}))
        return
    column = table.columns[finding.column or ""]
    given = getattr(column.default, "arg", None)
    default = None if callable(given) else given
    if default is not None:
        await session.execute(update(table).where(*where).values({column.name: default}))
    else:
        await session.execute(delete(table).where(*where))


Find = Callable[[AsyncSession], Awaitable[list[int]]]
Fix = Callable[[AsyncSession, int], Awaitable[None]]


async def dead_captors(session: AsyncSession) -> list[int]:
    living = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    query = select(CaptiveRow.id).where(CaptiveRow.status == CaptiveStatus.HELD, CaptiveRow.captor_entity_id.not_in(living))
    return list(await session.scalars(query.order_by(CaptiveRow.id)))


async def release_captive(session: AsyncSession, captive_id: int) -> None:
    await session.execute(update(CaptiveRow).where(CaptiveRow.id == captive_id).values(status=CaptiveStatus.RELEASED))


async def targetless_orders(session: AsyncSession) -> list[int]:
    query = select(InstructionOrderRow.id).where(
        InstructionOrderRow.kind.in_(TARGETED_ORDERS), InstructionOrderRow.target_node_id.is_(None), InstructionOrderRow.lapsed.is_(False)
    )
    return list(await session.scalars(query.order_by(InstructionOrderRow.id)))


async def lapse_order(session: AsyncSession, order_id: int) -> None:
    await session.execute(update(InstructionOrderRow).where(InstructionOrderRow.id == order_id).values(lapsed=True))


async def self_made(session: AsyncSession) -> list[int]:
    query = select(ConstructRow.entity_id).where(
        (ConstructRow.maker_entity_id == ConstructRow.entity_id) | (ConstructRow.soul_entity_id == ConstructRow.entity_id)
    )
    return list(await session.scalars(query.order_by(ConstructRow.entity_id)))


async def clear_self(session: AsyncSession, construct_id: int) -> None:
    row = await session.get(ConstructRow, construct_id)
    if row is None:
        return
    if row.maker_entity_id == construct_id:
        row.maker_entity_id = None
    if row.soul_entity_id == construct_id:
        row.soul_entity_id = None


async def dead_rulers(session: AsyncSession) -> list[int]:
    living = select(NodeRow.id).where(NodeRow.id.not_in(select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)))
    query = select(BondRow.id).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.not_in(living))
    return list(await session.scalars(query.order_by(BondRow.id)))


async def close_rule(session: AsyncSession, bond_id: int) -> None:
    await session.execute(update(BondRow).where(BondRow.id == bond_id).values(state=BondState.PAST, closed_reason="the ruler is gone"))


def peoples() -> Select[int]:
    return select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE)


def gods() -> CompoundSelect[int]:
    return select(SonRow.id).union(select(ForeignGodRow.id))


async def stray_covenants(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(CovenantRow.id).where(CovenantRow.people_entity_id.not_in(peoples())).order_by(CovenantRow.id)))


async def strike_covenant(session: AsyncSession, covenant_id: int) -> None:
    await session.execute(delete(CovenantRow).where(CovenantRow.id == covenant_id))


async def stray_seats(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(DivineSeatRow.god_node_id).where(DivineSeatRow.god_node_id.not_in(gods())).order_by(DivineSeatRow.god_node_id)))


async def unseat(session: AsyncSession, god_id: int) -> None:
    await session.execute(delete(DivineSeatRow).where(DivineSeatRow.god_node_id == god_id))


async def stray_ties(session: AsyncSession) -> list[int]:
    query = select(PantheonTieRow.god_node_id).where(PantheonTieRow.god_node_id.not_in(gods()) | PantheonTieRow.other_node_id.not_in(gods()))
    return sorted(set(await session.scalars(query)))


async def untie(session: AsyncSession, god_id: int) -> None:
    await session.execute(delete(PantheonTieRow).where((PantheonTieRow.god_node_id == god_id) | (PantheonTieRow.other_node_id == god_id)))


async def stray_syncretisms(session: AsyncSession) -> list[int]:
    query = select(SyncretismRow.id).where(
        SyncretismRow.people_entity_id.not_in(peoples())
        | SyncretismRow.son_id.not_in(select(SonRow.id))
        | SyncretismRow.foreign_god_id.not_in(select(ForeignGodRow.id))
    )
    return list(await session.scalars(query.order_by(SyncretismRow.id)))


async def part_gods(session: AsyncSession, syncretism_id: int) -> None:
    await session.execute(delete(SyncretismRow).where(SyncretismRow.id == syncretism_id))


CHECKS: dict[str, tuple[Find, Fix]] = {
    "living_captor": (dead_captors, release_captive),
    "order_target": (targetless_orders, lapse_order),
    "maker_not_self": (self_made, clear_self),
    "living_ruler": (dead_rulers, close_rule),
    "covenant_people": (stray_covenants, strike_covenant),
    "seat_god": (stray_seats, unseat),
    "tie_gods": (stray_ties, untie),
    "syncretism_kinds": (stray_syncretisms, part_gods),
    "money_metal": (metal_paper, clear_metal),
    "material_source": (stray_sources, clear_source),
    "holding_kind": (stray_holdings, drop_holding),
    "kind_lineage": (tangled_lineage, cut_lineage),
    "kind_ranges": (kinds_out_of_range, bring_into_range),
    "genome_alleles": (stray_alleles, mend_alleles),
    "fact_schema": (misfit_facts, drop_fact),
    "step_nesting": (crossed_nesting, clear_nesting),
    "step_action": (undeclared_steps, drop_step),
    "moment_after_cause": (early_moments, follow_cause),
    "step_moment_order": (steps_out_of_order, follow_step),
    "witness_present": (absent_witnesses, drop_witness),
    "witness_mode": (modeless_witnesses, give_witness_mode),
    "change_in_scope": (unscoped_changes, scope_change),
    "checkpoint_holds": (broken_checkpoints, retake_checkpoint),
    "kind_known": (unknown_kinds, retire_kind),
}


async def typed_sweep(session: AsyncSession) -> Sweep:
    repaired: dict[str, int] = {}
    findings: list[Finding] = []
    for spec in TYPED:
        find, fix = CHECKS[spec.key]
        broken = await find(session)
        if spec.remedy is Remedy.REPAIR:
            for key in broken:
                await fix(session, key)
            repaired[spec.key] = len(broken)
        else:
            findings.extend(Finding(None, spec.key, spec.table, None, str(key), spec.text, spec.resolution, spec.remedy) for key in broken)
    return Sweep(repaired, findings)


async def sweep(session: AsyncSession) -> Sweep:
    cosmos = await CosmosRepository(session).get()
    epoch = cosmos.epoch if cosmos is not None else 0
    generic = await generic_sweep(session, epoch)
    typed = await typed_sweep(session)
    await session.flush()
    return Sweep({**generic.repaired, **typed.repaired}, [*generic.findings, *typed.findings])


async def findings(session: AsyncSession) -> list[Finding]:
    found: list[Finding] = []
    for table in every_table().values():
        found.extend(await odd_enums(session, table))
        found.extend(await stray_locks(session, table))
    for spec in TYPED:
        if spec.remedy is Remedy.REPORT:
            broken = await CHECKS[spec.key][0](session)
            found.extend(Finding(None, spec.key, spec.table, None, str(key), spec.text, spec.resolution, spec.remedy) for key in broken)
    return found


async def resolve(session: AsyncSession, finding: Finding) -> None:
    if finding.invariant is not None:
        await CHECKS[finding.invariant][1](session, int(finding.key))
    else:
        await resolve_generic(session, finding)
    await session.flush()


async def schema_repairs(session: AsyncSession) -> int:
    return sum((await sweep(session)).repaired.values())
