import io
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import docx
import pytest
from ebooklib import ITEM_DOCUMENT, epub
from pypdf import PdfReader

from aerona.domain.enums.divine_will import ArtifactFormat, ExportFormat
from aerona.services.divine_will.exports import export_file, page_html
from aerona.services.divine_will.fountain import Element, parse_fountain
from tests.divine_will.library_fixtures import view_of

MARKDOWN = "# Opening\n\nSome *slanted* and **heavy** words.\n\n- first\n- second\n\n## Later\n\n| key | value |\n|---|---|\n| a | 1 |\n\n---\n\n> aside\n"
FOUNTAIN = (
    "Title: Draft Script\nAuthor: Nobody\n\n"
    "INT. HALL - DAY\n\nA person waits.\n\nANNA\n(quietly)\nIt is time.\nWe go.\n\n"
    "CUT TO:\n\n.FORCED HEADING\n\n>CENTERED<\n\n= a synopsis\n\n# Act Two\n\n~a sung line\n\n===\n\n@lowercase name\nSpoken.\n"
)
PAGE = "<h1>Own Page</h1><p>Body <b>text</b></p><script>alert(1)</script><img src='http://example.invalid/x.png'>"
SOURCES = {ArtifactFormat.MARKDOWN: MARKDOWN, ArtifactFormat.FOUNTAIN: FOUNTAIN, ArtifactFormat.HTML: PAGE}
SPOKEN = {ArtifactFormat.MARKDOWN: "heavy", ArtifactFormat.FOUNTAIN: "It is time.", ArtifactFormat.HTML: "Own Page"}


class Collected(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def opened_text(export: ExportFormat, content: bytes, folder: Path) -> str:
    if export is ExportFormat.PDF:
        reader = PdfReader(io.BytesIO(content))
        assert len(reader.pages) >= 1
        return "\n".join(page.extract_text() for page in reader.pages)
    if export is ExportFormat.DOCX:
        document = docx.Document(io.BytesIO(content))
        cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
        return "\n".join([*(paragraph.text for paragraph in document.paragraphs), *cells])
    if export is ExportFormat.EPUB:
        path = folder / "book.epub"
        path.write_bytes(content)
        book = epub.read_epub(str(path))
        assert book.get_metadata("DC", "title")[0][0] == "Jardín Été"
        contents = [item.get_content() for item in book.get_items_of_type(ITEM_DOCUMENT)]
        return "\n".join(content.decode("utf-8") if isinstance(content, bytes) else content for content in contents)
    if export is ExportFormat.HTML:
        parsed = Collected()
        parsed.feed(content.decode("utf-8"))
        assert "html" in parsed.tags
        return "".join(parsed.text)
    return content.decode("utf-8")


@pytest.mark.parametrize("form", list(ArtifactFormat))
@pytest.mark.parametrize("export", list(ExportFormat))
async def test_every_export_is_a_valid_file_with_the_whole_text(form: ArtifactFormat, export: ExportFormat, tmp_path: Path) -> None:
    exported = await export_file(view_of(SOURCES[form], form), export)
    assert exported.filename == f"jardín-été-v3.{export.value}"
    assert exported.content
    text = opened_text(export, exported.content, tmp_path)
    assert SPOKEN[form] in text
    if export is ExportFormat.EPUB:
        assert zipfile.ZipFile(io.BytesIO(exported.content)).read("mimetype") == b"application/epub+zip"


async def test_a_designed_page_holds_its_title_kind_and_own_fonts() -> None:
    page = page_html(view_of(MARKDOWN, ArtifactFormat.MARKDOWN))
    assert '<html lang="es">' in page
    assert "<h1>Jardín Été</h1>" in page
    assert "Story" in page
    assert "data:font/ttf;base64," in page
    assert "prefers-color-scheme: dark" in page
    assert "http" not in page.split("<article>")[0].replace("http-equiv", "")


async def test_markdown_never_lets_raw_html_or_script_links_through() -> None:
    page = page_html(view_of("<script>alert(1)</script>\n\n[go](javascript:alert(1))", ArtifactFormat.MARKDOWN))
    article = page.split("<article>")[1]
    assert "<script>" not in article
    assert 'href="javascript' not in article


def test_a_full_html_page_is_exported_as_its_own_document() -> None:
    own = "<!doctype html><html><head><title>Mine</title></head><body>Mine</body></html>"
    assert page_html(view_of(own, ArtifactFormat.HTML)) == own


def test_fountain_reads_every_element_of_a_screenplay() -> None:
    script = parse_fountain(FOUNTAIN)
    assert script.title_page == [("Title", "Draft Script"), ("Author", "Nobody")]
    kinds = [(block.element, block.text) for block in script.blocks]
    assert (Element.SCENE, "INT. HALL - DAY") in kinds
    assert (Element.ACTION, "A person waits.") in kinds
    assert (Element.CHARACTER, "ANNA") in kinds
    assert (Element.PARENTHETICAL, "(quietly)") in kinds
    assert (Element.DIALOGUE, "It is time.\nWe go.") in kinds
    assert (Element.TRANSITION, "CUT TO:") in kinds
    assert (Element.SCENE, "FORCED HEADING") in kinds
    assert (Element.CENTERED, "CENTERED") in kinds
    assert (Element.SYNOPSIS, "a synopsis") in kinds
    assert (Element.LYRIC, "a sung line") in kinds
    assert (Element.CHARACTER, "lowercase name") in kinds
    assert any(block.element is Element.SECTION and block.level == 1 and block.text == "Act Two" for block in script.blocks)
    assert any(block.element is Element.PAGE_BREAK for block in script.blocks)


def test_uncased_scripts_are_never_read_as_character_names() -> None:
    script = parse_fountain("書いた\n言葉です\n")
    assert [block.element for block in script.blocks] == [Element.ACTION]


async def test_prose_turned_into_a_screenplay_stays_action() -> None:
    exported = await export_file(view_of("SHOUTING LINE\nnext line\n\n# Heading", ArtifactFormat.MARKDOWN), ExportFormat.FOUNTAIN)
    script = parse_fountain(exported.content.decode("utf-8"))
    assert [block.element for block in script.blocks] == [Element.ACTION, Element.CENTERED]
