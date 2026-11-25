import difflib
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from aerona.core.grammar import several, spoken
from aerona.db.authorship import account_id, may_see, owns, visible
from aerona.db.session import Database
from aerona.db.tables.divine_will import (
    DivineWillArtifactNodeRow,
    DivineWillArtifactRow,
    DivineWillArtifactVersionRow,
    DivineWillPlanRow,
)
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.divine_will import ArtifactKind, ExportFormat, PlanStatus
from aerona.events.audience import private_audience
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.services.divine_will.exports import export_file
from aerona.services.divine_will.ownership import ownership_of
from aerona.tools.divine_will.library_ports import (
    ArtifactDiff,
    ArtifactDraft,
    ArtifactEdit,
    ArtifactPatch,
    ArtifactSummary,
    ArtifactView,
    ExportedFile,
    LibraryPage,
    LibraryQuery,
    LibrarySort,
    Subject,
    VersionSummary,
    VersionView,
)

Ranker = Callable[[str], Awaitable[list[int]]]
FUSION_K = 60
TITLE_WEIGHT = 5
SETTLED_PLANS = frozenset({PlanStatus.DONE, PlanStatus.ABANDONED, PlanStatus.FAILED})
NOT_YOURS = "Only its author can change this writing."


@dataclass(frozen=True)
class Candidate:
    row: DivineWillArtifactRow
    characters: int
    body: str


def clean_tags(tags: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for tag in tags:
        value = tag.strip()
        if value and value.casefold() not in {kept.casefold() for kept in seen}:
            seen.append(value)
    return seen


def clean_title(title: str) -> str:
    value = title.strip()
    if not value:
        raise ValidationFailedError("An artifact needs a title.")
    return value


def located(body: str, needle: str, what: str, version: int) -> int:
    found = body.count(needle)
    if found == 0:
        raise ValidationFailedError(
            f"The {what} was not found in version {version}. Read the artifact again and copy the passage exactly, with its spacing and punctuation."
        )
    if found > 1:
        raise ValidationFailedError(
            f"The {what} occurs {several(found, 'time', 'times')} in version {version}; include more of the text around it so it occurs once."
        )
    return body.index(needle)


def applied(body: str, edit: ArtifactEdit, version: int) -> tuple[str, str]:
    if edit.replace is not None:
        start = located(body, edit.replace.old, "text to replace", version)
        changed = body[:start] + edit.replace.new + body[start + len(edit.replace.old) :]
        summary = "Replaced one passage."
    elif edit.insert_after is not None:
        start = located(body, edit.insert_after.anchor, "anchor to insert after", version) + len(edit.insert_after.anchor)
        changed = body[:start] + edit.insert_after.text + body[start:]
        summary = "Inserted text after one passage."
    elif edit.append is not None:
        changed = f"{body.rstrip()}\n\n{edit.append.lstrip()}" if body.strip() else edit.append
        summary = "Added text at the end."
    else:
        changed = edit.rewrite or ""
        summary = "Rewrote the whole text."
    if changed == body:
        raise ValidationFailedError(f"This edit leaves version {version} as it was.")
    if not changed.strip():
        raise ValidationFailedError("An artifact cannot be left empty; write its text or delete it.")
    return changed, summary


def fused(ranked: Sequence[Sequence[int]]) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for ranking in ranked:
        for place, artifact_id in enumerate(ranking, start=1):
            scores[artifact_id] += 1.0 / (FUSION_K + place)
    return scores


def term_hits(candidate: Candidate, terms: Sequence[str]) -> int:
    title = candidate.row.title.casefold()
    body = candidate.body.casefold()
    if not all(term in title or term in body for term in terms):
        return 0
    return sum(title.count(term) * TITLE_WEIGHT + body.count(term) for term in terms)


def unified(before: str, after: str, a: int, b: int) -> tuple[str, int, int]:
    lines = list(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"version {a}", tofile=f"version {b}"))
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    text = "".join(line if line.endswith("\n") else f"{line}\n" for line in lines)
    return text, added, removed


async def require_artifact(session: AsyncSession, artifact_id: int) -> DivineWillArtifactRow:
    row = await session.get(DivineWillArtifactRow, artifact_id)
    if row is None or not may_see(row.author_account_id, row.shared):
        raise NotFoundError(f"No artifact {artifact_id}.")
    return row


async def owned_artifact(session: AsyncSession, artifact_id: int) -> DivineWillArtifactRow:
    row = await require_artifact(session, artifact_id)
    if not owns(row.author_account_id):
        raise ForbiddenError(NOT_YOURS)
    return row


async def require_version(session: AsyncSession, artifact_id: int, version: int) -> DivineWillArtifactVersionRow:
    row = await session.get(DivineWillArtifactVersionRow, (artifact_id, version))
    if row is None:
        raise NotFoundError(f"Artifact {artifact_id} has no version {version}.")
    return row


async def checked_nodes(session: AsyncSession, node_ids: Sequence[int]) -> list[int]:
    wanted = sorted(set(node_ids))
    if not wanted:
        return []
    found = set(await session.scalars(select(NodeRow.id).where(NodeRow.id.in_(wanted))))
    missing = [node_id for node_id in wanted if node_id not in found]
    if missing:
        raise ValidationFailedError(f"No such subject: {', '.join(str(node_id) for node_id in missing)}.")
    return wanted


async def set_subjects(session: AsyncSession, artifact_id: int, node_ids: Sequence[int]) -> None:
    wanted = await checked_nodes(session, node_ids)
    await session.execute(delete(DivineWillArtifactNodeRow).where(DivineWillArtifactNodeRow.artifact_id == artifact_id))
    session.add_all(DivineWillArtifactNodeRow(artifact_id=artifact_id, node_id=node_id) for node_id in wanted)
    await session.flush()


async def store_artifact(session: AsyncSession, draft: ArtifactDraft) -> DivineWillArtifactRow:
    if not draft.body.strip():
        raise ValidationFailedError("An artifact needs a text.")
    now = datetime.now(UTC)
    row = DivineWillArtifactRow(
        title=clean_title(draft.title),
        kind=draft.kind,
        format=draft.format,
        status=draft.status,
        language=draft.language.strip(),
        mode=draft.mode,
        tags=clean_tags(draft.tags),
        created_cycle_id=draft.cycle_id,
        current_version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    session.add(DivineWillArtifactVersionRow(artifact_id=row.id, version=1, body=draft.body, summary=draft.summary, cycle_id=draft.cycle_id, created_at=now))
    await set_subjects(session, row.id, draft.node_ids)
    return row


async def add_version(session: AsyncSession, row: DivineWillArtifactRow, body: str, summary: str, cycle_id: int | None) -> int:
    now = datetime.now(UTC)
    row.current_version += 1
    row.updated_at = now
    session.add(DivineWillArtifactVersionRow(artifact_id=row.id, version=row.current_version, body=body, summary=summary, cycle_id=cycle_id, created_at=now))
    await session.flush()
    return row.current_version


async def subjects_of(session: AsyncSession, artifact_ids: Sequence[int]) -> dict[int, list[Subject]]:
    found: dict[int, list[Subject]] = defaultdict(list)
    if not artifact_ids:
        return found
    rows = await session.execute(
        select(DivineWillArtifactNodeRow.artifact_id, NodeRow.id, NodeRow.name, NodeRow.kind)
        .join(NodeRow, NodeRow.id == DivineWillArtifactNodeRow.node_id)
        .where(DivineWillArtifactNodeRow.artifact_id.in_(artifact_ids))
        .order_by(DivineWillArtifactNodeRow.artifact_id, NodeRow.name, NodeRow.id)
    )
    for artifact_id, node_id, name, kind in rows:
        found[int(artifact_id)].append(Subject(int(node_id), str(name), kind))
    return found


async def plans_of(session: AsyncSession, artifact_ids: Sequence[int]) -> dict[int, int]:
    if not artifact_ids:
        return {}
    rows = await session.execute(
        select(DivineWillPlanRow.artifact_id, DivineWillPlanRow.id).where(DivineWillPlanRow.artifact_id.in_(artifact_ids)).order_by(DivineWillPlanRow.id)
    )
    return {int(artifact_id): int(plan_id) for artifact_id, plan_id in rows if artifact_id is not None}


def summarised(row: DivineWillArtifactRow, characters: int, subjects: list[Subject], plan_id: int | None) -> ArtifactSummary:
    return ArtifactSummary(
        id=row.id,
        title=row.title,
        kind=row.kind,
        format=row.format,
        status=row.status,
        language=row.language,
        mode=row.mode,
        tags=list(row.tags),
        subjects=subjects,
        current_version=row.current_version,
        characters=characters,
        created_cycle_id=row.created_cycle_id,
        plan_id=plan_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        owner=ownership_of(row.author_account_id, row.author_name, row.shared),
    )


async def view_of(session: AsyncSession, row: DivineWillArtifactRow, version: int | None = None) -> ArtifactView:
    shown = await require_version(session, row.id, version or row.current_version)
    current = shown if shown.version == row.current_version else await require_version(session, row.id, row.current_version)
    versions = [
        VersionSummary(int(number), str(summary), cycle_id, int(characters), created_at)
        for number, summary, cycle_id, characters, created_at in await session.execute(
            select(
                DivineWillArtifactVersionRow.version,
                DivineWillArtifactVersionRow.summary,
                DivineWillArtifactVersionRow.cycle_id,
                func.length(DivineWillArtifactVersionRow.body),
                DivineWillArtifactVersionRow.created_at,
            )
            .where(DivineWillArtifactVersionRow.artifact_id == row.id)
            .order_by(DivineWillArtifactVersionRow.version)
        )
    ]
    subjects = (await subjects_of(session, [row.id])).get(row.id, [])
    plan_id = (await plans_of(session, [row.id])).get(row.id)
    return ArtifactView(summarised(row, len(current.body), subjects, plan_id), shown.body, shown.version, versions)


def ordered(candidates: list[Candidate], sort: LibrarySort, scores: dict[int, float]) -> list[Candidate]:
    if sort is LibrarySort.RELEVANCE:
        return sorted(candidates, key=lambda item: (-scores.get(item.row.id, 0.0), -item.row.updated_at.timestamp(), -item.row.id))
    if sort is LibrarySort.CREATED:
        return sorted(candidates, key=lambda item: (-item.row.created_at.timestamp(), -item.row.id))
    if sort is LibrarySort.TITLE:
        return sorted(candidates, key=lambda item: (item.row.title.casefold(), item.row.id))
    if sort is LibrarySort.LENGTH:
        return sorted(candidates, key=lambda item: (-item.characters, item.row.id))
    return sorted(candidates, key=lambda item: (-item.row.updated_at.timestamp(), -item.row.id))


class ArtifactLibrary:
    def __init__(self, database: Database, bus: EventBus, ranker: Ranker | None = None) -> None:
        self.database = database
        self.bus = bus
        self.ranker = ranker

    def changed(self, view: ArtifactView | None, artifact_id: int, *, cycle_id: int | None = None) -> None:
        payload = {"artifact_id": artifact_id, "version": view.artifact.current_version if view else 0, "cycle_id": cycle_id, "deleted": view is None}
        owner = view.artifact.owner if view is not None else None
        audience = private_audience(owner.author_account_id, owner.shared) if owner is not None else account_id()
        self.bus.publish(EventKind.DIVINE_WILL_ARTIFACT_CHANGED, payload, audience=audience)

    async def create(self, draft: ArtifactDraft) -> ArtifactView:
        async with self.database.write() as session:
            row = await store_artifact(session, draft)
            view = await view_of(session, row)
        self.changed(view, view.artifact.id, cycle_id=draft.cycle_id)
        return view

    async def read(self, artifact_id: int, version: int | None = None) -> ArtifactView:
        async with self.database.read() as session:
            return await view_of(session, await require_artifact(session, artifact_id), version)

    async def version(self, artifact_id: int, version: int) -> VersionView:
        async with self.database.read() as session:
            await require_artifact(session, artifact_id)
            row = await require_version(session, artifact_id, version)
            return VersionView(artifact_id, row.version, row.body, row.summary, row.cycle_id, row.created_at)

    async def edit(self, artifact_id: int, edits: Sequence[ArtifactEdit], *, cycle_id: int | None, summary: str = "") -> ArtifactView:
        if not edits:
            raise ValidationFailedError("Name at least one edit.")
        async with self.database.write() as session:
            row = await owned_artifact(session, artifact_id)
            if row.kind is ArtifactKind.PLAN:
                raise ConflictError("A plan's artifact follows its plan; revise the plan's steps instead.")
            body = (await require_version(session, row.id, row.current_version)).body
            version = row.current_version
            changes: list[tuple[str, str]] = []
            for number, edit in enumerate(edits, start=1):
                try:
                    body, said = applied(body, edit, version + number - 1)
                except ValidationFailedError as error:
                    raise ValidationFailedError(f"Edit {number} of {len(edits)} was refused and nothing was changed: {error.message}") from error
                changes.append((body, summary.strip() or said))
            for text, said in changes:
                await add_version(session, row, text, said, cycle_id)
            view = await view_of(session, row)
        self.changed(view, artifact_id, cycle_id=cycle_id)
        return view

    async def patch(self, artifact_id: int, patch: ArtifactPatch) -> ArtifactView:
        async with self.database.write() as session:
            row = await owned_artifact(session, artifact_id)
            mirrored = (await plans_of(session, [row.id])).get(row.id) is not None
            if patch.kind is not None and patch.kind is not row.kind and (mirrored or patch.kind is ArtifactKind.PLAN):
                raise ConflictError("Only a plan keeps an artifact of the plan kind, and a plan's artifact keeps that kind.")
            if patch.title is not None:
                row.title = clean_title(patch.title)
            if patch.status is not None:
                row.status = patch.status
            if patch.tags is not None:
                row.tags = clean_tags(patch.tags)
            if patch.kind is not None:
                row.kind = patch.kind
            if patch.node_ids is not None:
                await set_subjects(session, row.id, patch.node_ids)
            if patch.shared is not None:
                row.shared = patch.shared
            row.updated_at = datetime.now(UTC)
            await session.flush()
            view = await view_of(session, row)
        self.changed(view, artifact_id)
        return view

    async def delete(self, artifact_id: int) -> None:
        async with self.database.write() as session:
            row = await owned_artifact(session, artifact_id)
            plan = await session.scalar(select(DivineWillPlanRow).where(DivineWillPlanRow.artifact_id == row.id).order_by(DivineWillPlanRow.id).limit(1))
            if plan is not None and plan.status not in SETTLED_PLANS:
                raise ConflictError(f"This artifact holds plan {plan.id}, which is still {spoken(plan.status)}; finish or abandon the plan first.")
            await session.delete(row)
        self.changed(None, artifact_id)

    async def versions_diff(self, artifact_id: int, a: int, b: int) -> ArtifactDiff:
        async with self.database.read() as session:
            await require_artifact(session, artifact_id)
            before = await require_version(session, artifact_id, a)
            after = await require_version(session, artifact_id, b)
        text, added, removed = unified(before.body, after.body, a, b)
        return ArtifactDiff(artifact_id, a, b, text, added, removed)

    async def export(self, artifact_id: int, export: ExportFormat, version: int | None = None) -> ExportedFile:
        view = await self.read(artifact_id, version)
        return await export_file(view, export)

    async def candidates(self, session: AsyncSession, query: LibraryQuery, *, with_bodies: bool) -> list[Candidate]:
        current = (DivineWillArtifactVersionRow.artifact_id == DivineWillArtifactRow.id) & (
            DivineWillArtifactVersionRow.version == DivineWillArtifactRow.current_version
        )
        columns: list[Any] = [DivineWillArtifactRow, func.length(DivineWillArtifactVersionRow.body)]
        if with_bodies:
            columns.append(DivineWillArtifactVersionRow.body)
        statement = (
            select(*columns)
            .join(DivineWillArtifactVersionRow, current)
            .where(visible(DivineWillArtifactRow.author_account_id, DivineWillArtifactRow.shared))
            .order_by(DivineWillArtifactRow.id)
        )
        for column, value in (
            (DivineWillArtifactRow.kind, query.kind),
            (DivineWillArtifactRow.status, query.status),
            (DivineWillArtifactRow.format, query.format),
            (DivineWillArtifactRow.mode, query.mode),
        ):
            if value is not None:
                statement = statement.where(column == value)
        if query.node_id is not None:
            statement = statement.where(
                DivineWillArtifactRow.id.in_(select(DivineWillArtifactNodeRow.artifact_id).where(DivineWillArtifactNodeRow.node_id == query.node_id))
            )
        found = [Candidate(row[0], int(row[1] or 0), str(row[2]) if with_bodies else "") for row in await session.execute(statement)]
        if query.language:
            wanted = query.language.strip().casefold()
            found = [item for item in found if item.row.language.casefold() == wanted]
        if query.tag:
            tag = query.tag.strip().casefold()
            found = [item for item in found if tag in {value.casefold() for value in item.row.tags}]
        return found

    async def library(self, query: LibraryQuery) -> LibraryPage:
        terms = [term.casefold() for term in query.q.split() if term.strip()]
        async with self.database.read() as session:
            facet_rows = list(await session.execute(select(DivineWillArtifactRow.language, DivineWillArtifactRow.tags).order_by(DivineWillArtifactRow.id)))
            found = await self.candidates(session, query, with_bodies=bool(terms))
            scores: dict[int, float] = {}
            if terms:
                hits = {item.row.id: term_hits(item, terms) for item in found}
                text_ranking = [artifact_id for artifact_id, count in sorted(hits.items(), key=lambda pair: (-pair[1], pair[0])) if count > 0]
                matched = set(text_ranking)
                meaning = [artifact_id for artifact_id in await self.ranker(query.q) if artifact_id in matched] if self.ranker is not None else []
                scores = fused([text_ranking, meaning])
                found = [item for item in found if item.row.id in scores]
            chosen = ordered(found, query.sort or (LibrarySort.RELEVANCE if terms else LibrarySort.UPDATED), scores)
            total = len(chosen)
            offset = max(0, query.offset)
            window = chosen[offset:] if query.limit is None else chosen[offset : offset + max(1, query.limit)]
            ids = [item.row.id for item in window]
            subjects = await subjects_of(session, ids)
            plans = await plans_of(session, ids)
            items = [summarised(item.row, item.characters, subjects.get(item.row.id, []), plans.get(item.row.id)) for item in window]
        languages = sorted({str(language) for language, _ in facet_rows if language}, key=str.casefold)
        tags = sorted({tag for _, values in facet_rows for tag in clean_tags(values or [])}, key=str.casefold)
        return LibraryPage(items, total, offset, len(items) if query.limit is None else max(1, query.limit), languages, tags)
