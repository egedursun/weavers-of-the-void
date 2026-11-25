import io
from datetime import UTC, datetime
from urllib.parse import quote

import docx
from pypdf import PdfReader

from aerona.db.tables.divine_will import DivineWillForecastRow
from aerona.domain.enums.divine_will import ArtifactKind, ExportFormat, ForecastStatus
from aerona.services.divine_will.artifacts import ArtifactLibrary
from aerona.services.divine_will.library import library_for
from aerona.tools.divine_will.library_ports import ArtifactEdit, ReplaceSpec, StepDraft
from tests.api.conftest import ApiWorld
from tests.divine_will.library_fixtures import draft

BASE = "/api/divine-will"


async def written(api: ApiWorld) -> int:
    library = ArtifactLibrary(api.services.database, api.services.bus)
    first = await library.create(draft("Notas de Año", "Uno dos tres.\n\nCuatro cinco.", kind=ArtifactKind.NOTES, language="es", tags=("liste",)))
    await library.edit(first.artifact.id, [ArtifactEdit(replace=ReplaceSpec(old="Cuatro", new="Seis"))], cycle_id=None)
    await library.create(draft("Other", "Unrelated words."))
    return first.artifact.id


async def test_the_library_lists_reads_diffs_patches_and_deletes(api: ApiWorld) -> None:
    artifact_id = await written(api)
    page = (await api.http.get(f"{BASE}/artifacts", params={"q": "AÑO SEIS", "language": "es", "kind": "notes", "sort": "relevance", "limit": 5})).json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == artifact_id
    assert page["languages"] == ["en", "es"]
    assert page["tags"] == ["liste"]
    everything = (await api.http.get(f"{BASE}/artifacts", params={"offset": 1, "limit": 1, "sort": "title"})).json()
    assert (everything["total"], everything["offset"], everything["limit"], len(everything["items"])) == (2, 1, 1, 1)
    full = (await api.http.get(f"{BASE}/artifacts/{artifact_id}")).json()
    assert full["body"] == "Uno dos tres.\n\nSeis cinco."
    assert [item["version"] for item in full["versions"]] == [1, 2]
    first = (await api.http.get(f"{BASE}/artifacts/{artifact_id}/versions/1")).json()
    assert first["body"] == "Uno dos tres.\n\nCuatro cinco."
    diff = (await api.http.get(f"{BASE}/artifacts/{artifact_id}/diff", params={"a": 1, "b": 2})).json()
    assert "+Seis cinco." in diff["text"] and diff["added"] == 1
    patched = await api.http.patch(f"{BASE}/artifacts/{artifact_id}", json={"title": "Liste", "status": "final", "tags": ["a", "b"]})
    assert patched.status_code == 200, patched.text
    assert (patched.json()["artifact"]["title"], patched.json()["artifact"]["status"]) == ("Liste", "final")
    refused = await api.http.patch(f"{BASE}/artifacts/{artifact_id}", json={"kind": "plan"})
    assert refused.status_code == 409
    missing = await api.http.get(f"{BASE}/artifacts/{artifact_id}/versions/9")
    assert missing.status_code == 404
    assert (await api.http.delete(f"{BASE}/artifacts/{artifact_id}")).json()["ok"] is True
    assert (await api.http.get(f"{BASE}/artifacts/{artifact_id}")).status_code == 404


async def test_every_export_downloads_as_its_own_file(api: ApiWorld) -> None:
    artifact_id = await written(api)
    for export in ExportFormat:
        response = await api.http.get(f"{BASE}/artifacts/{artifact_id}/export", params={"format": export.value})
        assert response.status_code == 200, response.text
        disposition = response.headers["content-disposition"]
        assert disposition.startswith("attachment;")
        assert quote(f"notas-de-año-v2.{export.value}") in disposition
        if export is ExportFormat.PDF:
            assert len(PdfReader(io.BytesIO(response.content)).pages) >= 1
        elif export is ExportFormat.DOCX:
            assert any("Seis cinco." in paragraph.text for paragraph in docx.Document(io.BytesIO(response.content)).paragraphs)
        else:
            assert response.content
    older = await api.http.get(f"{BASE}/artifacts/{artifact_id}/export", params={"format": "md", "version": 1})
    assert "Cuatro cinco." in older.text


async def test_a_plan_is_edited_approved_and_run_from_the_api(api: ApiWorld) -> None:
    desk = library_for(api.services).plans
    plan = await desk.create("Moods", [StepDraft(title="One", action_id="creator:mood", input={"contentment": 40})], cycle_id=None)
    shown = (await api.http.get(f"{BASE}/plans/{plan.id}")).json()
    assert shown["status"] == "draft" and shown["steps"][0]["action_title"]
    steps = [{"title": "One", "action_id": "creator:mood", "input": {"contentment": 41}}, {"title": "Two", "action_id": "creator:mood", "input": {"anger": 5}}]
    revised = await api.http.put(f"{BASE}/plans/{plan.id}/steps", json={"steps": steps, "title": "Two moods"})
    assert revised.status_code == 200, revised.text
    assert revised.json()["title"] == "Two moods"
    bad = await api.http.put(f"{BASE}/plans/{plan.id}/steps", json={"steps": [{"title": "x", "action_id": "nowhere"}]})
    assert bad.status_code == 400
    assert (await api.http.post(f"{BASE}/plans/{plan.id}/execute")).status_code == 409
    assert (await api.http.post(f"{BASE}/plans/{plan.id}/approve")).json()["status"] == "approved"
    assert (await api.http.post(f"{BASE}/plans/{plan.id}/steps/2/skip")).json()["steps"][1]["status"] == "skipped"
    started = await api.http.post(f"{BASE}/plans/{plan.id}/execute")
    assert started.status_code == 202, started.text
    await api.wait_job(started.json()["job_id"])
    done = (await api.http.get(f"{BASE}/plans/{plan.id}")).json()
    assert done["status"] == "done"
    assert done["steps"][0]["status"] == "done" and done["steps"][0]["ledger_entry_id"]
    undone = await api.http.post(f"{BASE}/plans/{plan.id}/steps/1/undo")
    assert undone.status_code == 200, undone.text
    assert undone.json()["steps"][0]["status"] == "undone"
    assert (await api.http.post(f"{BASE}/plans/{plan.id}/pause")).status_code == 409
    assert (await api.http.post(f"{BASE}/plans/{plan.id}/resume")).status_code == 409
    assert (await api.http.post(f"{BASE}/plans/{plan.id}/abandon")).status_code == 409


async def test_a_forecast_is_read_and_an_ended_one_cannot_be_cancelled(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        row = DivineWillForecastRow(epochs=1, status=ForecastStatus.CANCELLED, eta_seconds=40, interventions=[], report={"epochs_done": 0, "error": ""})
        row.created_at = datetime.now(UTC)
        session.add(row)
        await session.flush()
        forecast_id = row.id
    shown = (await api.http.get(f"{BASE}/forecasts/{forecast_id}")).json()
    assert (shown["status"], shown["report"], shown["eta_seconds"]) == ("cancelled", None, 40)
    assert (await api.http.post(f"{BASE}/forecasts/{forecast_id}/cancel")).status_code == 409
    assert (await api.http.get(f"{BASE}/forecasts/999")).status_code == 404
