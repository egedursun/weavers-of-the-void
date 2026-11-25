from typing import Any

from pydantic import Field

from aerona.core.errors import AeronaError
from aerona.core.grammar import several, spoken
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, ArtifactStatus, DivineWillMode
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool
from aerona.tools.divine_will.library_ports import (
    ArtifactDraft,
    ArtifactEdit,
    ArtifactPatch,
    ArtifactSummary,
    ArtifactView,
    LibraryQuery,
    LibrarySort,
    library_of,
)
from aerona.tools.divine_will.paging import failed, paged
from aerona.tools.framework.inputs import ToolInput

W = DivineWillToolId
WRITING = frozenset({Toolset.ARTIFACTS})
READING = frozenset({Toolset.ARTIFACTS, Toolset.ARTIFACTS_READ})


class ArtifactCreateInput(ToolInput):
    title: str = Field(min_length=1, max_length=300)
    kind: ArtifactKind
    format: ArtifactFormat = ArtifactFormat.MARKDOWN
    body: str = Field(min_length=1)
    language: str = Field(min_length=1, max_length=60)
    tags: list[str] = Field(default_factory=list)
    node_ids: list[int] = Field(default_factory=list)
    status: ArtifactStatus = ArtifactStatus.DRAFT


class ArtifactReadInput(PagedInput):
    artifact_id: int = Field(ge=1)
    version: int | None = Field(default=None, ge=1)


class ArtifactEditInput(ToolInput):
    artifact_id: int = Field(ge=1)
    edits: list[ArtifactEdit] = Field(min_length=1)
    summary: str = Field(default="", max_length=300)


class ArtifactUpdateInput(ToolInput):
    artifact_id: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: ArtifactStatus | None = None
    kind: ArtifactKind | None = None
    tags: list[str] | None = None
    node_ids: list[int] | None = None


class ArtifactListInput(PagedInput):
    q: str = Field(default="", max_length=300)
    kind: ArtifactKind | None = None
    status: ArtifactStatus | None = None
    format: ArtifactFormat | None = None
    language: str = Field(default="", max_length=60)
    mode: DivineWillMode | None = None
    tag: str = Field(default="", max_length=60)
    node_id: int | None = Field(default=None, ge=1)
    sort: LibrarySort | None = None


def subjects_text(summary: ArtifactSummary) -> str:
    return ", ".join(f"{subject.name} (node {subject.node_id})" for subject in summary.subjects) or "none"


def summary_line(summary: ArtifactSummary) -> str:
    facts = [
        f"kind {spoken(summary.kind)}",
        f"format {spoken(summary.format)}",
        f"status {spoken(summary.status)}",
        f"language {summary.language or 'not given'}",
        f"version {summary.current_version}",
        several(summary.characters, "character", "characters"),
        f"updated {summary.updated_at.date().isoformat()}",
    ]
    if summary.tags:
        facts.append(f"tags {', '.join(summary.tags)}")
    if summary.subjects:
        facts.append(f"about {subjects_text(summary)}")
    if summary.plan_id is not None:
        facts.append(f"holds plan {summary.plan_id}")
    return f"artifact {summary.id}: {summary.title} — {'; '.join(facts)}"


def artifact_head(view: ArtifactView) -> str:
    summary = view.artifact
    shown = "the current version" if view.version == summary.current_version else f"an older version; the current one is {summary.current_version}"
    versions = ", ".join(f"{item.version} ({item.summary or 'no note'})" for item in view.versions)
    return "\n".join(
        [
            summary_line(summary),
            f"Showing version {view.version}, {shown}.",
            f"Versions: {versions}",
            "Text:",
        ]
    )


async def create_artifact(call: WillCall, query: ArtifactCreateInput) -> WillResult:
    if query.kind is ArtifactKind.PLAN:
        return failed("A plan is written with plan_create; its artifact follows the plan.")
    draft = ArtifactDraft(
        title=query.title,
        kind=query.kind,
        format=query.format,
        body=query.body,
        language=query.language,
        mode=call.mode,
        tags=query.tags,
        node_ids=query.node_ids,
        cycle_id=call.cycle_id,
        status=query.status,
    )
    try:
        view = await library_of(call).artifacts.create(draft)
    except AeronaError as error:
        return failed(error.message)
    return WillResult(
        text=f"Created {summary_line(view.artifact)}. Read it with artifact_read and change it with artifact_edit; every change keeps a new version.",
        payload={"artifact_id": view.artifact.id, "version": view.version},
    )


async def read_artifact(call: WillCall, query: ArtifactReadInput) -> WillResult:
    try:
        view = await library_of(call).artifacts.read(query.artifact_id, query.version)
    except AeronaError as error:
        return failed(error.message)
    blocks = [f"{block}\n" for block in view.body.split("\n\n")]
    return await paged(call, W.ARTIFACT_READ, query, blocks, head=artifact_head(view), empty="The text is empty.")


async def edit_artifact(call: WillCall, query: ArtifactEditInput) -> WillResult:
    try:
        before = await library_of(call).artifacts.read(query.artifact_id)
        view = await library_of(call).artifacts.edit(query.artifact_id, query.edits, cycle_id=call.cycle_id, summary=query.summary)
    except AeronaError as error:
        return failed(error.message)
    made = view.version - before.artifact.current_version
    return WillResult(
        text=(
            f"Saved {several(made, 'new version', 'new versions')} of artifact {view.artifact.id}: it is now at version {view.version}, "
            f"{several(view.artifact.characters, 'character', 'characters')} long. Earlier versions are kept."
        ),
        payload={"artifact_id": view.artifact.id, "version": view.version},
    )


async def update_artifact(call: WillCall, query: ArtifactUpdateInput) -> WillResult:
    patch = ArtifactPatch(title=query.title, status=query.status, tags=query.tags, kind=query.kind, node_ids=query.node_ids)
    if patch == ArtifactPatch():
        return failed("Name at least one of title, status, kind, tags or node_ids to change.")
    try:
        view = await library_of(call).artifacts.patch(query.artifact_id, patch)
    except AeronaError as error:
        return failed(error.message)
    found = view.artifact
    tags = ", ".join(found.tags) or "none"
    text = f'Artifact {found.id} is now "{found.title}", {spoken(found.kind)}, {spoken(found.status)}, tags: {tags}. Its text and versions are unchanged.'
    return WillResult(text=text, payload={"artifact_id": found.id, "version": view.version})


def library_query(query: ArtifactListInput) -> LibraryQuery:
    return LibraryQuery(
        q=query.q,
        kind=query.kind,
        status=query.status,
        format=query.format,
        language=query.language or None,
        mode=query.mode,
        tag=query.tag or None,
        node_id=query.node_id,
        sort=query.sort,
    )


async def list_artifacts(call: WillCall, query: ArtifactListInput) -> WillResult:
    found = await library_of(call).artifacts.library(library_query(query))
    head = f"The library holds {several(found.total, 'matching artifact', 'matching artifacts')}." if found.total else ""
    return await paged(call, W.ARTIFACT_LIST, query, [summary_line(item) for item in found.items], head=head, empty="No artifact matches.")


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.ARTIFACT_CREATE, WRITING, ArtifactCreateInput, create_artifact),
        WillTool(W.ARTIFACT_READ, READING, ArtifactReadInput, read_artifact),
        WillTool(W.ARTIFACT_EDIT, WRITING, ArtifactEditInput, edit_artifact),
        WillTool(W.ARTIFACT_UPDATE, WRITING, ArtifactUpdateInput, update_artifact),
        WillTool(W.ARTIFACT_LIST, READING, ArtifactListInput, list_artifacts),
    ]
