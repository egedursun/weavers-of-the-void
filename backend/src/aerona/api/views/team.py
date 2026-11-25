from aerona.api.schemas.team import AuthorView, CanonProposalView, ConflictChangeView, QueuedActView
from aerona.db.tables.team import CanonProposalRow, QueuedActRow
from aerona.domain.enums.team import CanonTouch


def author_view(account_id: int | None, name: str | None) -> AuthorView | None:
    if account_id is None and not name:
        return None
    return AuthorView(account_id=account_id, name=name or "")


def queued_view(row: QueuedActRow) -> QueuedActView:
    return QueuedActView(
        id=row.id,
        source=row.source,
        action_id=row.action_id,
        title=row.title,
        payload=dict(row.payload),
        reason=row.reason,
        author=author_view(row.author_account_id, row.author_name),
        queued_epoch=row.queued_epoch,
        queued_at=row.created_at,
        status=row.status,
        result=row.result,
        applied_at=row.applied_at,
        ledger_entry_id=row.ledger_entry_id,
        cancelled_by=author_view(row.cancelled_by_account_id, row.cancelled_by_name),
        plan_id=row.plan_id,
        plan_ordinal=row.plan_ordinal,
        presence_session_id=row.presence_session_id,
        conflict=[ConflictChangeView.model_validate(item) for item in row.conflict],
        proposal_id=row.proposal_id,
    )


def proposal_view(row: CanonProposalRow) -> CanonProposalView:
    return CanonProposalView(
        id=row.id,
        action_id=row.action_id,
        title=row.title,
        payload=dict(row.payload),
        reason=row.reason,
        preview=dict(row.preview),
        touches=[CanonTouch(value) for value in row.touches],
        held_node_ids=list(row.held_node_ids),
        author=author_view(row.author_account_id, row.author_name),
        proposed_epoch=row.proposed_epoch,
        proposed_at=row.created_at,
        status=row.status,
        decided_by=author_view(row.decided_by_account_id, row.decided_by_name),
        decided_at=row.decided_at,
        note=row.note,
        result=row.result,
        ledger_entry_id=row.ledger_entry_id,
    )
