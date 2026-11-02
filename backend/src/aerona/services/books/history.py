from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.foreign_gods import ForeignGodRow, GodConflictRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import GodConflictOutcome
from aerona.services.narrative import clean_lore

CREATOR_HAND_KINDS = (ChronicleKind.CREATOR_HAND, ChronicleKind.DIVINE_SIGN, ChronicleKind.ORDER)
SON_FATE_KINDS = (
    ChronicleKind.DEATH,
    ChronicleKind.RESURRECTION,
    ChronicleKind.ASCENSION,
    ChronicleKind.REBELLION,
    ChronicleKind.ORDER,
    ChronicleKind.CREATOR_HAND,
    ChronicleKind.DIVINE_SIGN,
    ChronicleKind.EXISTENCE,
)


@dataclass
class HandDeed:
    text: str
    undone: bool = False
    unledgered: bool = False


@dataclass
class HandEpoch:
    epoch: int
    deeds: list[HandDeed] = field(default_factory=list)


async def creator_hand(session: AsyncSession) -> list[HandEpoch]:
    epochs: dict[int, HandEpoch] = {}
    for entry in await session.scalars(
        select(LedgerEntryRow).where(LedgerEntryRow.actor_kind == ActorKind.CREATOR).order_by(LedgerEntryRow.epoch, LedgerEntryRow.id)
    ):
        label = entry.tool.replace("_", " ").replace(":", " ")
        text = f"{label}: {entry.input_summary}" if entry.input_summary else label
        epochs.setdefault(entry.epoch, HandEpoch(entry.epoch)).deeds.append(HandDeed(text, undone=entry.undone))
    lines = await session.scalars(
        select(ChronicleRow)
        .where(ChronicleRow.kind.in_(CREATOR_HAND_KINDS), ChronicleRow.visible.is_(True), ChronicleRow.son_id.is_(None))
        .order_by(ChronicleRow.epoch, ChronicleRow.id)
    )
    for line in lines:
        epochs.setdefault(line.epoch, HandEpoch(line.epoch)).deeds.append(HandDeed(clean_lore(line.text), unledgered=True))
    return [epochs[epoch] for epoch in sorted(epochs)]


async def son_fate(session: AsyncSession, son: SonRow, names: dict[int, str]) -> list[str]:
    lines: list[str] = [f"Status: {son.status.value.replace('_', ' ')}"]
    if son.status is SonStatus.DEAD and son.death_epoch is not None:
        cause = f" ({son.death_cause.value.replace('_', ' ')})" if son.death_cause is not None else ""
        lines.append(f"Died in Epoch {son.death_epoch}{cause}")
    if son.rebel:
        lines.append("In rebellion against the father")
    if son.chained:
        lines.append("Chained")
    if son.standing_order:
        lines.append(f"Standing order{' (absolute)' if son.order_absolute else ''}: {son.standing_order}")
    if son.reputation_label is not None:
        lines.append(f"Reputation: {son.reputation_label.value.replace('_', ' ')}")
    if son.anchor_entity_id is not None:
        lines.append(f"Anchor: {names.get(son.anchor_entity_id, '?')}")
    if son.current_world_id is not None:
        lines.append(f"World: {names.get(son.current_world_id, '?')}")
    worshippers = await session.scalar(
        select(func.count()).select_from(BondRow).where(BondRow.kind == BondKind.WORSHIPS, BondRow.target_node_id == son.id, BondRow.state == BondState.ACTIVE)
    )
    if worshippers:
        lines.append(f"Worshipped by {worshippers}")
    rows = await session.scalars(
        select(ChronicleRow)
        .where(ChronicleRow.son_id == son.id, ChronicleRow.kind.in_(SON_FATE_KINDS), ChronicleRow.visible.is_(True))
        .order_by(ChronicleRow.id)
    )
    lines.extend(f"Epoch {row.epoch}: {clean_lore(row.text)}" for row in rows)
    return lines


async def god_fate(session: AsyncSession, god: ForeignGodRow, names: dict[int, str]) -> list[str]:
    lines = [f"Status: {god.status.value}", f"Arose in Epoch {god.created_epoch}"]
    if god.defeated_epoch is not None:
        lines.append(f"Defeated in Epoch {god.defeated_epoch}")
    conflicts = list(
        await session.scalars(
            select(GodConflictRow)
            .where(or_(GodConflictRow.attacker_node_id == god.id, GodConflictRow.defender_node_id == god.id))
            .order_by(GodConflictRow.epoch, GodConflictRow.id)
        )
    )
    killer: int | None = None
    for conflict in conflicts:
        attacker = conflict.attacker_node_id == god.id
        other = conflict.defender_node_id if attacker else conflict.attacker_node_id
        if conflict.outcome is GodConflictOutcome.DRAW:
            verdict = "drew with"
        else:
            won = (conflict.outcome is GodConflictOutcome.ATTACKER_WON) == attacker
            verdict = "defeated" if won else "fell to"
            killer = other if not won else killer
        kind = "duel" if conflict.duel else "conflict"
        lines.append(f"Epoch {conflict.epoch}: {kind}, {verdict} {names.get(other, '?')}")
    if god.death_epoch is not None:
        lines.append(f"Died in Epoch {god.death_epoch}" + (f", slain by {names[killer]}" if killer is not None and killer in names else ""))
    return lines


def ending_line(status: str, end_epoch: int | None, note: str | None) -> str | None:
    if end_epoch is None:
        return None
    return f"{status.capitalize()} in Epoch {end_epoch}" + (f": {note}" if note else "")
