import io
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from docx import Document
from PIL import Image

from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus, ChunkSource
from aerona.services.divine_will.attachments import read_document
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, open_api

ORIGIN = {"origin": "http://localhost:5173"}
UPLOAD = "/api/divine-will/attachments"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def tiny_pdf(text: str) -> bytes:
    content = f"BT /F1 18 Tf 20 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = b"%PDF-1.4\n"
    offsets: list[int] = []
    for number, item in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{number} 0 obj\n".encode() + item + b"\nendobj\n"
    table = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    body += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    body += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{table}\n%%EOF\n".encode()
    return body


def tiny_docx(text: str) -> bytes:
    document = Document()
    document.add_heading("Survey of the coast", level=1)
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def tiny_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
async def uploads(tmp_path: Path, settings: Settings) -> AsyncIterator[ApiWorld]:
    limited = settings.model_copy(update={"divine_will_upload_max_files": 2, "divine_will_upload_max_mb": 1, "data_dir": settings.data_dir})
    async for api in open_api(limited, seeded=False):
        yield api


def test_markitdown_turns_a_docx_and_a_pdf_into_text() -> None:
    docx = read_document(tiny_docx("The harbour of Brinewatch holds forty boats."), "survey.docx", DOCX)
    assert docx.status is AttachmentStatus.CONVERTED
    assert "Survey of the coast" in docx.markdown and "forty boats" in docx.markdown
    pdf = read_document(tiny_pdf("Tide tables of the northern bay"), "tides.pdf", "application/pdf")
    assert pdf.status is AttachmentStatus.CONVERTED and "Tide tables of the northern bay" in pdf.markdown
    table = read_document(b"name,boats\nBrinewatch,40\n", "harbours.csv", "text/csv")
    assert table.status is AttachmentStatus.CONVERTED and "Brinewatch" in table.markdown


def test_a_broken_document_is_kept_as_unreadable() -> None:
    for data, name, mime in (
        (b"%PDF-1.4\n" + bytes(range(256)) * 8, "broken.pdf", "application/pdf"),
        (b"PK\x03\x04" + bytes(range(256)), "broken.docx", DOCX),
        (b"", "empty.txt", "text/plain"),
    ):
        broken = read_document(data, name, mime)
        assert broken.status is AttachmentStatus.UNREADABLE and broken.note and not broken.markdown, name


async def test_uploads_are_stored_converted_and_indexed(uploads: ApiWorld) -> None:
    files = [
        ("files", ("survey.docx", tiny_docx("The harbour of Brinewatch holds forty boats."), DOCX)),
        ("files", ("tides.pdf", tiny_pdf("Tide tables of the northern bay"), "application/pdf")),
    ]
    response = await uploads.http.post(UPLOAD, files=files, headers=ORIGIN)
    assert response.status_code == 201, response.text
    stored = response.json()["attachments"]
    assert [item["status"] for item in stored] == [AttachmentStatus.CONVERTED.value] * 2
    assert all(item["cycle_id"] is None and item["kind"] == AttachmentKind.DOCUMENT.value for item in stored)
    detail = await uploads.http.get(f"{UPLOAD}/{stored[0]['id']}")
    assert "forty boats" in detail.json()["markdown"]
    original = await uploads.http.get(f"{UPLOAD}/{stored[1]['id']}/file")
    assert original.content.startswith(b"%PDF") and original.headers["content-disposition"].startswith("attachment")
    index = uploads.services.application.lore_index
    await index.refresh_attachments(embed=False)
    counts = {item.source: item.passages for item in index.state().sources}
    assert counts[ChunkSource.ATTACHMENT] >= 2
    state = await uploads.http.get("/api/divine-will/index")
    assert state.status_code == 200 and state.json()["passages"] >= 2


async def test_an_image_is_stored_for_the_model_to_see(uploads: ApiWorld) -> None:
    response = await uploads.http.post(UPLOAD, files=[("files", ("pixel.png", tiny_png(), "image/png"))], headers=ORIGIN)
    assert response.status_code == 201, response.text
    (image,) = response.json()["attachments"]
    assert image["kind"] == AttachmentKind.IMAGE.value and image["status"] == AttachmentStatus.STORED.value
    shown = await uploads.http.get(f"{UPLOAD}/{image['id']}/file")
    assert shown.headers["content-type"] == "image/png" and shown.headers["content-disposition"].startswith("inline")


async def test_too_many_files_are_refused(uploads: ApiWorld) -> None:
    files = [("files", (f"note-{number}.txt", b"a line of text", "text/plain")) for number in range(3)]
    response = await uploads.http.post(UPLOAD, files=files, headers=ORIGIN)
    assert response.status_code == 422
    assert "At most 2 files" in response.json()["error"]


async def test_a_file_over_the_size_limit_is_refused(uploads: ApiWorld) -> None:
    response = await uploads.http.post(UPLOAD, files=[("files", ("big.txt", b"x" * (1024 * 1024 + 10), "text/plain"))], headers=ORIGIN)
    assert response.status_code == 413
    assert "at most 1 MB" in response.json()["error"]


async def test_a_form_from_nowhere_is_refused(uploads: ApiWorld) -> None:
    response = await uploads.http.post(UPLOAD, files=[("files", ("note.txt", b"a line", "text/plain"))])
    assert response.status_code == 403
