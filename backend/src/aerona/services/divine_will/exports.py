import asyncio
import base64
import html
import io
import re
import sys
import tempfile
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import docx
from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph
from ebooklib import epub
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdownify import markdownify

from aerona.constants.app import APP_NAME
from aerona.core.errors import ConflictError
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, ArtifactStatus, ExportFormat
from aerona.services.books.typeset import worker_environment
from aerona.services.divine_will.fountain import Block, Element, Script, fountain_html, fountain_markdown, parse_fountain, spans
from aerona.tools.divine_will.library_ports import EXPORT_MEDIA, ArtifactView, ExportedFile

FONT_DIRECTORY = Path(__file__).resolve().parent.parent / "books" / "fonts"
PAGE_STYLE_FILE = Path(__file__).resolve().parent / "artifact.css"
FONT_FILES: tuple[tuple[str, int, str, str], ...] = (
    ("Book Serif", 400, "normal", "alegreya-regular.ttf"),
    ("Book Serif", 400, "italic", "alegreya-italic.ttf"),
    ("Book Serif", 700, "normal", "alegreya-bold.ttf"),
    ("Book Display", 600, "normal", "cormorant-semibold.ttf"),
)
KIND_LABELS: dict[ArtifactKind, str] = {
    ArtifactKind.STORY: "Story",
    ArtifactKind.CHAPTER: "Chapter",
    ArtifactKind.NOVEL: "Novel",
    ArtifactKind.SCREENPLAY: "Screenplay",
    ArtifactKind.POEM: "Poem",
    ArtifactKind.CHRONICLE: "Chronicle",
    ArtifactKind.ENCYCLOPEDIA: "Encyclopedia",
    ArtifactKind.OUTLINE: "Outline",
    ArtifactKind.NOTES: "Notes",
    ArtifactKind.REPORT: "Report",
    ArtifactKind.PLAN: "Plan",
    ArtifactKind.FORECAST: "Forecast",
    ArtifactKind.HTML_PAGE: "Web page",
}
STATUS_LABELS: dict[ArtifactStatus, str] = {ArtifactStatus.DRAFT: "Draft", ArtifactStatus.FINAL: "Final"}
EXTENSIONS: dict[ExportFormat, str] = {
    ExportFormat.MD: "md",
    ExportFormat.HTML: "html",
    ExportFormat.PDF: "pdf",
    ExportFormat.EPUB: "epub",
    ExportFormat.DOCX: "docx",
    ExportFormat.FOUNTAIN: "fountain",
}
LANGUAGE_CODE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
DOCUMENT_START = re.compile(r"<!doctype|<html[\s>]", re.IGNORECASE)
CHAPTER_HEADING = re.compile(r"(?=<h([12])[ >])")
TAGS = re.compile(r"<[^>]+>")
SLUG_BREAK = re.compile(r"[^\w]+", re.UNICODE)
UNKNOWN_LANGUAGE = "und"
PRINT_WORKER = "aerona.services.divine_will.print_worker"
ERROR_TAIL = 600
SOURCE_NAME = "artifact.html"
PRINTED_NAME = "artifact.pdf"
ORNAMENT = "⁂"
ACCENT = RGBColor(0x5B, 0x23, 0x91)
SOFT = RGBColor(0x7A, 0x6A, 0x52)
CODE_FONT = "Courier New"
PROSE_FONT = "Georgia"
SCREENPLAY_POINTS = 12
CHARACTER_INDENT = Pt(158)
DIALOGUE_INDENT = Pt(72)
PARENTHETICAL_INDENT = Pt(115)


@cache
def markdown() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False, "xhtmlOut": True}).enable("table").enable("strikethrough")


@cache
def page_style() -> str:
    return PAGE_STYLE_FILE.read_text(encoding="utf-8")


@cache
def font_faces() -> str:
    rules = []
    for family, weight, style, name in FONT_FILES:
        encoded = base64.b64encode((FONT_DIRECTORY / name).read_bytes()).decode("ascii")
        rules.append(
            f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:{style};src:url("data:font/ttf;base64,{encoded}") format("truetype")}}'
        )
    return "\n".join(rules)


@dataclass(frozen=True)
class Chapter:
    title: str
    body: str


@dataclass
class Walk:
    lists: list[str] = field(default_factory=list)
    quotes: int = 0
    heading: int | None = None
    table: list[list[list[Token]]] | None = None
    in_cell: bool = False

    def follow(self, token: Token) -> bool:
        kind = token.type
        if kind == "heading_open":
            self.heading = int(token.tag[1])
        elif kind == "heading_close":
            self.heading = None
        elif kind in ("bullet_list_open", "ordered_list_open"):
            self.lists.append("bullet" if kind == "bullet_list_open" else "ordered")
        elif kind in ("bullet_list_close", "ordered_list_close"):
            self.lists.pop()
        elif kind in ("blockquote_open", "blockquote_close"):
            self.quotes += 1 if kind == "blockquote_open" else -1
        elif kind == "table_open":
            self.table = []
        elif kind == "tr_open" and self.table is not None:
            self.table.append([])
        elif kind in ("th_open", "td_open", "th_close", "td_close"):
            self.in_cell = kind.endswith("_open")
        else:
            return False
        return True


def kind_label(view: ArtifactView) -> str:
    return KIND_LABELS[view.artifact.kind]


def language_code(language: str) -> str:
    value = language.strip()
    return value if LANGUAGE_CODE.match(value) else UNKNOWN_LANGUAGE


def meta_line(view: ArtifactView) -> str:
    summary = view.artifact
    parts = [STATUS_LABELS[summary.status], f"Version {view.version}", summary.updated_at.date().isoformat()]
    if summary.language:
        parts.insert(0, summary.language)
    return " · ".join(parts)


def slug(title: str) -> str:
    folded = unicodedata.normalize("NFKC", title).strip().lower()
    return SLUG_BREAK.sub("-", folded).strip("-_") or "artifact"


def file_name(view: ArtifactView, export: ExportFormat) -> str:
    return f"{slug(view.artifact.title)}-v{view.version}.{EXTENSIONS[export]}"


def is_document(body: str) -> bool:
    return DOCUMENT_START.search(body) is not None


def as_markdown(view: ArtifactView) -> str:
    if view.artifact.format is ArtifactFormat.MARKDOWN:
        return view.body
    if view.artifact.format is ArtifactFormat.FOUNTAIN:
        return fountain_markdown(parse_fountain(view.body))
    return str(markdownify(view.body, heading_style="ATX"))


def body_html(view: ArtifactView) -> str:
    if view.artifact.format is ArtifactFormat.FOUNTAIN:
        return fountain_html(parse_fountain(view.body))
    return str(markdown().render(as_markdown(view)))


def page_html(view: ArtifactView, *, printed: bool = False) -> str:
    if view.artifact.format is ArtifactFormat.HTML and is_document(view.body):
        return view.body
    summary = view.artifact
    language = language_code(summary.language)
    content = view.body if summary.format is ArtifactFormat.HTML else body_html(view)
    classes = " ".join(name for name, wanted in (("printed", printed), ("screenplay-print", summary.format is ArtifactFormat.FOUNTAIN)) if wanted)
    return (
        "<!doctype html>"
        f'<html lang="{html.escape(language)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(summary.title)}</title>"
        f"<style>{font_faces()}{page_style()}</style></head>"
        f'<body class="{classes}"><main>'
        f'<header class="title"><p class="overline">{html.escape(kind_label(view))}</p>'
        f"<h1>{html.escape(summary.title)}</h1>"
        f'<p class="meta">{html.escape(meta_line(view))}</p></header>'
        f"<article>{content}</article>"
        f'<footer class="imprint">{html.escape(APP_NAME)}</footer>'
        "</main></body></html>"
    )


async def export_pdf(view: ArtifactView) -> bytes:
    with tempfile.TemporaryDirectory(prefix="divine-will-print-") as folder:
        source, printed = Path(folder) / SOURCE_NAME, Path(folder) / PRINTED_NAME
        await asyncio.to_thread(source.write_text, page_html(view, printed=True), encoding="utf-8")
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            PRINT_WORKER,
            str(source),
            str(printed),
            env=worker_environment(),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _out, error = await process.communicate()
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        if process.returncode != 0 or not printed.is_file():
            reason = error.decode(errors="replace").strip().splitlines()[-1:] if error else []
            raise ConflictError(f"The artifact could not be printed: {(reason[0] if reason else f'exit {process.returncode}')[-ERROR_TAIL:]}")
        return await asyncio.to_thread(printed.read_bytes)


def chapters(view: ArtifactView) -> list[Chapter]:
    if view.artifact.format is ArtifactFormat.FOUNTAIN:
        return [Chapter(view.artifact.title, body_html(view))]
    rendered = body_html(view)
    levels = {match.group(1) for match in CHAPTER_HEADING.finditer(rendered)}
    if not levels:
        return [Chapter(view.artifact.title, rendered)]
    level = min(levels)
    pieces = re.split(rf"(?=<h{level}[ >])", rendered)
    found: list[Chapter] = []
    for piece in pieces:
        if not piece.strip():
            continue
        heading = re.match(rf"<h{level}[^>]*>(.*?)</h{level}>", piece, re.DOTALL)
        title = html.unescape(TAGS.sub("", heading.group(1))).strip() if heading else view.artifact.title
        found.append(Chapter(title or view.artifact.title, piece))
    return found


def export_epub(view: ArtifactView) -> bytes:
    summary = view.artifact
    book = epub.EpubBook()
    book.set_identifier(f"divine-will-artifact-{summary.id}-v{view.version}")
    book.set_title(summary.title)
    book.set_language(language_code(summary.language))
    book.add_metadata("DC", "publisher", APP_NAME)
    book.add_metadata("DC", "date", summary.updated_at.date().isoformat())
    style = epub.EpubItem(uid="style", file_name="style/book.css", media_type="text/css", content=page_style().encode("utf-8"))
    book.add_item(style)
    title_page = epub.EpubHtml(title=summary.title, file_name="title.xhtml", lang=language_code(summary.language))
    title_page.content = (
        f'<header class="title"><p class="overline">{html.escape(kind_label(view))}</p><h1>{html.escape(summary.title)}</h1>'
        f'<p class="meta">{html.escape(meta_line(view))}</p></header>'
    )
    title_page.add_item(style)
    book.add_item(title_page)
    items = [title_page]
    for number, chapter in enumerate(chapters(view), start=1):
        item = epub.EpubHtml(title=chapter.title, file_name=f"chapter-{number}.xhtml", lang=language_code(summary.language))
        item.content = chapter.body
        item.add_item(style)
        book.add_item(item)
        items.append(item)
    book.toc = [epub.Link(item.file_name, item.title, f"part-{number}") for number, item in enumerate(items)]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *items]
    buffer = io.BytesIO()
    epub.write_epub(buffer, book, {"raise_exceptions": True})
    return buffer.getvalue()


def styled(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = PROSE_FONT
    normal.font.size = Pt(11)
    for level in range(1, 7):
        heading = document.styles[f"Heading {level}"]
        heading.font.name = PROSE_FONT
        heading.font.color.rgb = ACCENT


MARKS: dict[str, tuple[str, bool]] = {
    "strong_open": ("bold", True),
    "strong_close": ("bold", False),
    "em_open": ("italic", True),
    "em_close": ("italic", False),
    "s_open": ("strike", True),
    "s_close": ("strike", False),
}
LEAF_TOKENS = frozenset({"text", "code_inline", "image"})
FOUNTAIN_MARKS = {"strong_open": "**", "strong_close": "**", "em_open": "*", "em_close": "*", "softbreak": "\n", "hardbreak": "\n"}


def add_leaf(paragraph: Paragraph, child: Token, marks: dict[str, bool]) -> None:
    if child.type == "softbreak":
        paragraph.add_run(" ")
    elif child.type == "hardbreak":
        paragraph.add_run().add_break()
    elif child.type in LEAF_TOKENS:
        run = paragraph.add_run(child.content)
        run.bold, run.italic, run.font.strike = marks["bold"], marks["italic"], marks["strike"]
        if child.type == "code_inline":
            run.font.name = CODE_FONT


def add_spans(paragraph: Paragraph, children: Sequence[Token]) -> None:
    marks = {"bold": False, "italic": False, "strike": False}
    link = ""
    for child in children:
        if child.type in MARKS:
            name, on = MARKS[child.type]
            marks[name] = on
        elif child.type == "link_open":
            link = str(child.attrs.get("href", ""))
        elif child.type == "link_close":
            if link:
                paragraph.add_run(f" ({link})").font.color.rgb = SOFT
            link = ""
        else:
            add_leaf(paragraph, child, marks)


def paragraph_style(walk: Walk) -> str:
    if walk.heading is not None:
        return f"Heading {walk.heading}"
    if walk.lists:
        depth = "" if len(walk.lists) == 1 else f" {min(3, len(walk.lists))}"
        return f"List Bullet{depth}" if walk.lists[-1] == "bullet" else f"List Number{depth}"
    if walk.quotes:
        return "Quote"
    return "Normal"


def add_table(document: Document, rows: list[list[list[Token]]]) -> None:
    width = max((len(row) for row in rows), default=0)
    if not width:
        return
    table = document.add_table(rows=len(rows), cols=width)
    table.style = document.styles["Table Grid"]
    for row_index, row in enumerate(rows):
        for column, children in enumerate(row):
            cell = table.cell(row_index, column)
            add_spans(cell.paragraphs[0], children)
            if row_index == 0:
                for run in cell.paragraphs[0].runs:
                    run.bold = True


def docx_markdown(document: Document, text: str) -> None:
    walk = Walk()
    for token in markdown().parse(text):
        kind = token.type
        if walk.follow(token):
            continue
        if kind == "table_close" and walk.table is not None:
            add_table(document, walk.table)
            walk.table = None
        elif kind == "inline" and walk.in_cell and walk.table:
            walk.table[-1].append(list(token.children or []))
        elif kind == "inline":
            add_spans(document.add_paragraph(style=paragraph_style(walk)), token.children or [])
        elif kind in ("fence", "code_block"):
            run = document.add_paragraph().add_run(token.content.rstrip("\n"))
            run.font.name = CODE_FONT
        elif kind == "hr":
            document.add_paragraph(ORNAMENT).alignment = WD_ALIGN_PARAGRAPH.CENTER


def docx_block(document: Document, block: Block) -> None:
    if block.element is Element.PAGE_BREAK:
        document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        return
    if block.element is Element.SECTION:
        document.add_heading(block.text, level=min(6, max(1, block.level)))
        return
    paragraph = document.add_paragraph()
    layout = paragraph.paragraph_format
    if block.element is Element.CHARACTER:
        layout.left_indent = CHARACTER_INDENT
        layout.space_after = Pt(0)
    elif block.element is Element.PARENTHETICAL:
        layout.left_indent = PARENTHETICAL_INDENT
        layout.space_after = Pt(0)
    elif block.element in (Element.DIALOGUE, Element.LYRIC):
        layout.left_indent = DIALOGUE_INDENT
        layout.right_indent = DIALOGUE_INDENT
    elif block.element is Element.TRANSITION:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif block.element is Element.CENTERED:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    text = block.text.upper() if block.element in (Element.SCENE, Element.CHARACTER, Element.TRANSITION) else block.text
    for span in spans(text):
        run = paragraph.add_run(span.text)
        run.font.name = CODE_FONT
        run.font.size = Pt(SCREENPLAY_POINTS)
        run.bold = span.bold or block.element is Element.SCENE
        run.italic = span.italic or block.element in (Element.SYNOPSIS, Element.LYRIC)
        run.underline = span.underline


def docx_script(document: Document, script: Script) -> None:
    for key, value in script.title_page:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        label = paragraph.add_run(f"{key}: ")
        label.font.color.rgb = SOFT
        paragraph.add_run(value)
    for block in script.blocks:
        docx_block(document, block)


def export_docx(view: ArtifactView) -> bytes:
    document = docx.Document()
    styled(document)
    summary = view.artifact
    document.core_properties.title = summary.title
    document.core_properties.language = summary.language
    document.core_properties.category = kind_label(view)
    overline = document.add_paragraph(kind_label(view).upper())
    overline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_heading(summary.title, level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta = document.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta.add_run(meta_line(view))
    meta_run.italic = True
    meta_run.font.color.rgb = SOFT
    if summary.format is ArtifactFormat.FOUNTAIN:
        docx_script(document, parse_fountain(view.body))
    else:
        docx_markdown(document, as_markdown(view))
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def plain_lines(text: str) -> list[str]:
    lines: list[str] = []
    walk = Walk()
    for token in markdown().parse(text):
        kind = token.type
        if walk.follow(token):
            continue
        if kind == "inline":
            words = "".join(FOUNTAIN_MARKS.get(child.type, child.content) for child in token.children or [])
            if walk.heading is not None:
                lines.append(f">{words.strip()}<")
            elif walk.lists:
                lines.append(f"!{'  ' * (len(walk.lists) - 1)}- {words}")
            else:
                lines.append(f"!{words}")
        elif kind in ("fence", "code_block"):
            lines.append("!" + token.content.rstrip("\n"))
        elif kind == "hr":
            lines.append("===")
    return lines


def export_fountain(view: ArtifactView) -> str:
    if view.artifact.format is ArtifactFormat.FOUNTAIN:
        return view.body
    head = f"Title: {view.artifact.title}\nDraft date: {view.artifact.updated_at.date().isoformat()}\n"
    return head + "\n" + "\n\n".join(plain_lines(as_markdown(view))) + "\n"


def export_markdown(view: ArtifactView) -> str:
    return f"# {view.artifact.title}\n\n*{kind_label(view)} · {meta_line(view)}*\n\n{as_markdown(view).strip()}\n"


def written(view: ArtifactView, export: ExportFormat) -> bytes:
    if export is ExportFormat.MD:
        return export_markdown(view).encode("utf-8")
    if export is ExportFormat.HTML:
        return page_html(view).encode("utf-8")
    if export is ExportFormat.EPUB:
        return export_epub(view)
    if export is ExportFormat.DOCX:
        return export_docx(view)
    return export_fountain(view).encode("utf-8")


async def export_file(view: ArtifactView, export: ExportFormat) -> ExportedFile:
    content = await export_pdf(view) if export is ExportFormat.PDF else await asyncio.to_thread(written, view, export)
    return ExportedFile(file_name(view, export), EXPORT_MEDIA[export], content)
