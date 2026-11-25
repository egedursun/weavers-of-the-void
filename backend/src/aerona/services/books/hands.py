from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from aerona.core.grammar import several
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.team import CanonProposalRow, QueuedActRow
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.team import ProposalStatus, QueuedActStatus
from aerona.services.ledger import action_label
from aerona.services.team.legacy import account_remains, legacy_name

BEFORE_NAMES = "Before the team kept names"
QUEUE_LABELS: dict[QueuedActStatus, str] = {
    QueuedActStatus.QUEUED: "Waiting for the age to end",
    QueuedActStatus.APPLIED: "Applied after the age",
    QueuedActStatus.PROPOSED: "Sent for approval",
    QueuedActStatus.FAILED: "Could not be applied",
    QueuedActStatus.CANCELLED: "Cancelled",
}
PROPOSAL_LABELS: dict[ProposalStatus, str] = {
    ProposalStatus.PENDING: "Waiting for an administrator",
    ProposalStatus.APPROVED: "Approved",
    ProposalStatus.REJECTED: "Rejected",
    ProposalStatus.WITHDRAWN: "Withdrawn by its author",
}


@dataclass(frozen=True)
class HandAct:
    epoch: int
    label: str
    summary: str
    reason: str
    undone: bool
    undone_by: str


@dataclass
class Hand:
    name: str
    account_id: int | None = None
    former: bool = False
    acts: list[HandAct] = field(default_factory=list)
    kinds: Counter[str] = field(default_factory=Counter)
    queued: int = 0
    proposed: int = 0
    approved: int = 0
    decided: int = 0

    @property
    def epochs(self) -> str:
        found = sorted({act.epoch for act in self.acts})
        if not found:
            return ""
        return f"epoch {found[0]}" if found[0] == found[-1] else f"epochs {found[0]} to {found[-1]}"

    @property
    def tally(self) -> str:
        parts = [several(len(self.acts), "act", "acts")]
        undone = sum(1 for act in self.acts if act.undone)
        if undone:
            parts.append(f"{undone} undone")
        if self.queued:
            parts.append(f"{several(self.queued, 'act', 'acts')} queued during an age")
        if self.proposed:
            parts.append(f"{several(self.proposed, 'proposal', 'proposals')} to locked canon")
        if self.decided:
            parts.append(f"{several(self.decided, 'proposal', 'proposals')} decided")
        return ", ".join(parts)

    @property
    def most(self) -> list[tuple[str, int]]:
        return sorted(self.kinds.items(), key=lambda pair: (-pair[1], pair[0]))


@dataclass(frozen=True)
class QueueLine:
    title: str
    author: str
    status: str
    epoch: int
    reason: str
    result: str


@dataclass(frozen=True)
class ProposalLine:
    title: str
    author: str
    status: str
    epoch: int
    reason: str
    decided_by: str
    note: str


@dataclass
class TeamRecord:
    hands: list[Hand] = field(default_factory=list)
    queue: list[QueueLine] = field(default_factory=list)
    proposals: list[ProposalLine] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return bool(self.hands or self.queue or self.proposals)


async def team_record(session: AsyncSession) -> TeamRecord:
    bound = session.bind
    legacy = (legacy_name(str(bound.url)) if isinstance(bound, AsyncEngine) else "") or BEFORE_NAMES
    hands: dict[str, Hand] = {}
    entries = await session.scalars(
        select(LedgerEntryRow).where(LedgerEntryRow.actor_kind == ActorKind.CREATOR).order_by(LedgerEntryRow.epoch, LedgerEntryRow.id)
    )
    for entry in entries:
        name = entry.author_name or legacy
        hand = hands.setdefault(name, Hand(name, entry.author_account_id))
        label = action_label(entry.tool, entry.action_kind)
        hand.kinds[label] += 1
        hand.acts.append(HandAct(entry.epoch, label, entry.input_summary or "", entry.reason or "", entry.undone, entry.undone_by_name or ""))
    queue: list[QueueLine] = []
    for waited in await session.scalars(select(QueuedActRow).order_by(QueuedActRow.id)):
        name = waited.author_name or legacy
        hands.setdefault(name, Hand(name, waited.author_account_id)).queued += 1
        queue.append(QueueLine(waited.title, name, QUEUE_LABELS[waited.status], waited.queued_epoch, waited.reason or "", waited.result))
    proposals: list[ProposalLine] = []
    for row in await session.scalars(select(CanonProposalRow).order_by(CanonProposalRow.id)):
        name = row.author_name or legacy
        author = hands.setdefault(name, Hand(name, row.author_account_id))
        author.proposed += 1
        if row.status is ProposalStatus.APPROVED:
            author.approved += 1
        if row.decided_by_name:
            hands.setdefault(row.decided_by_name, Hand(row.decided_by_name, row.decided_by_account_id)).decided += 1
        proposals.append(ProposalLine(row.title, name, PROPOSAL_LABELS[row.status], row.proposed_epoch, row.reason or "", row.decided_by_name or "", row.note))
    url = str(bound.url) if isinstance(bound, AsyncEngine) else ""
    for hand in hands.values():
        if hand.account_id is not None:
            hand.former = not await account_remains(url, hand.account_id)
    ordered = sorted(hands.values(), key=lambda hand: (-len(hand.acts), hand.name.casefold()))
    return TeamRecord(ordered, queue, proposals)
