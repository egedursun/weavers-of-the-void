import re
import secrets
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup, escape

from aerona.catalog.life.divine import MOTION_LABELS
from aerona.catalog.tongues import PART_OF_SPEECH_LABELS
from aerona.constants.books import (
    ARTICLE_WIDTH,
    CODEX_IMAGE_WIDTH,
    COVER_WIDTH,
    PLATE_WIDTH,
    PORTRAIT_WIDTH,
    PRINT_ARTICLE_PIXELS,
    PRINT_ARTICLE_WIDTH,
    PRINT_COVER_PIXELS,
    PRINT_COVER_WIDTH,
    PRINT_PLATE_PIXELS,
    PRINT_PLATE_WIDTH,
    PRINT_PORTRAIT_PIXELS,
    PRINT_PORTRAIT_WIDTH,
)
from aerona.core.grammar import spoken
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.divine import CouncilMotion
from aerona.rules.registry import Rules
from aerona.services.books.mapsvg import MapPicture
from aerona.services.books.model import BookModel, EntityArticle, SonArticle
from aerona.services.codex import guide_markdown

TEMPLATE_DIRECTORY = Path(__file__).resolve().parent / "templates"
BOOK_TEMPLATE = "book.html.j2"
ENTRY_TEMPLATE = "entry.html.j2"
CODEX_TEMPLATE = "codex.md.j2"
EMPTY_TEMPLATE = "empty.html.j2"
MEDIA_PREFIX = "/api/media/"
BOOK_ASSET_PREFIX = "/api/book/"
FONT_DIRECTORY = Path(__file__).resolve().parent / "fonts"
BRAND_LOGO = Path(__file__).resolve().parent / "brand" / "logo.png"
SCREEN_WIDTHS = {"cover": COVER_WIDTH, "portrait": PORTRAIT_WIDTH, "article": ARTICLE_WIDTH, "plate": PLATE_WIDTH}
PRINT_WIDTHS = {
    "cover": (PRINT_COVER_WIDTH, PRINT_COVER_PIXELS),
    "portrait": (PRINT_PORTRAIT_WIDTH, PRINT_PORTRAIT_PIXELS),
    "article": (PRINT_ARTICLE_WIDTH, PRINT_ARTICLE_PIXELS),
    "plate": (PRINT_PLATE_WIDTH, PRINT_PLATE_PIXELS),
}
CODEX_IMAGE_DIRECTORY = "images"
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*$")
HEADING_LINE = re.compile(r"^[ \t]*#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
BULLET = re.compile(r"^[-*•]\s+(.+)$")
BOLD = re.compile(r"\*\*(.+?)\*\*")
EXTRA_BLANK_LINES = re.compile(r"\n[ \t]*(?:\n[ \t]*){2,}")
CODEX_CHUNK = 1_048_576
NONCE_BYTES = 16
PIPE = "|"
ESCAPED_PIPE = "\\|"


@dataclass(frozen=True)
class PdfState:
    ready: bool
    stale: bool
    url: str
    size_mb: float
    epoch: int | None
    world_epoch: int | None = None


@dataclass(frozen=True)
class RenderedBook:
    html: str
    nonce: str


class BookLinks(Protocol):
    printing: bool

    def media(self, file_name: str | None, size: str) -> str: ...

    def terrain(self, picture: MapPicture) -> str: ...

    def font(self, file_name: str) -> str: ...

    def logo(self) -> str: ...


class ScreenLinks:
    printing = False

    def media(self, file_name: str | None, size: str) -> str:
        return f"{MEDIA_PREFIX}{quote(file_name)}?w={SCREEN_WIDTHS[size]}" if file_name else ""

    def terrain(self, picture: MapPicture) -> str:
        return f"{BOOK_ASSET_PREFIX}maps/{picture.world_id}.jpg?v={quote(picture.signature)}"

    def font(self, file_name: str) -> str:
        return f"{BOOK_ASSET_PREFIX}fonts/{quote(file_name)}"

    def logo(self) -> str:
        return f"{BOOK_ASSET_PREFIX}brand/logo.png"


@dataclass
class PrintLinks:
    directory: Path
    printing: bool = True
    images: dict[tuple[str, int, int], Path] = field(default_factory=dict)
    maps: dict[int, Path] = field(default_factory=dict)

    def media(self, file_name: str | None, size: str) -> str:
        if not file_name:
            return ""
        width, pixels = PRINT_WIDTHS[size]
        path = self.images.setdefault((file_name, width, pixels), self.directory / f"image-{len(self.images)}.jpg")
        return path.as_uri()

    def terrain(self, picture: MapPicture) -> str:
        return self.maps.setdefault(picture.world_id, self.directory / f"map-{picture.world_id}.jpg").as_uri()

    def font(self, file_name: str) -> str:
        return (FONT_DIRECTORY / file_name).as_uri()

    def logo(self) -> str:
        return BRAND_LOGO.as_uri()


def _inline(text: str) -> Markup:
    escaped = str(escape(text))
    return Markup(BOLD.sub(r"<b>\1</b>", escaped))


def paragraphs(text: str | None) -> Markup:
    if not text:
        return Markup("")
    blocks: list[Markup] = []
    items: list[Markup] = []
    for raw in str(text).split("\n"):
        line = raw.strip()
        if not line:
            continue
        bullet = BULLET.match(line)
        if bullet:
            items.append(Markup("<li>{}</li>").format(_inline(bullet.group(1))))
            continue
        if items:
            blocks.append(Markup("<ul>{}</ul>").format(Markup("").join(items)))
            items = []
        title = HEADING.match(line)
        if title:
            blocks.append(Markup('<p class="sublabel">{}</p>').format(_inline(title.group(1))))
        else:
            blocks.append(Markup("<p>{}</p>").format(_inline(line)))
    if items:
        blocks.append(Markup("<ul>{}</ul>").format(Markup("").join(items)))
    return Markup("").join(blocks)


def prose(text: str | None) -> str:
    if not text:
        return ""
    return HEADING_LINE.sub(lambda found: f"**{found.group(1).strip().rstrip(':')}**", str(text).strip())


@dataclass
class CodexLinks:
    base: str | None = None
    images: dict[tuple[str, int, int], str] = field(default_factory=dict)
    maps: dict[int, str] = field(default_factory=dict)
    heavens: dict[str, str] = field(default_factory=dict)

    def heaven(self, anchor: str, figure: str) -> str:
        if self.base is not None:
            return f"data:image/svg+xml;utf8,{quote(str(figure))}"
        path = f"{CODEX_IMAGE_DIRECTORY}/{quote(anchor)}.svg"
        self.heavens[path] = str(figure)
        return path

    def media(self, file_name: str | None) -> str:
        if not file_name:
            return ""
        if self.base is not None:
            return f"{self.base}{MEDIA_PREFIX.lstrip('/')}{quote(file_name)}?w={CODEX_IMAGE_WIDTH}"
        return self.images.setdefault((file_name, CODEX_IMAGE_WIDTH, CODEX_IMAGE_WIDTH), f"{CODEX_IMAGE_DIRECTORY}/{quote(Path(file_name).stem)}.jpg")

    def terrain(self, picture: MapPicture) -> str:
        if self.base is not None:
            return f"{self.base}{BOOK_ASSET_PREFIX.lstrip('/')}maps/{picture.world_id}.jpg?v={quote(picture.signature)}"
        return self.maps.setdefault(picture.world_id, f"{CODEX_IMAGE_DIRECTORY}/map-{picture.world_id}.jpg")


def table_cell(value: object) -> str:
    return " ".join(str(value or "").split()).replace(PIPE, ESCAPED_PIPE)


def plain_text(text: str) -> str:
    cleaned = re.sub(r'[{}\[\]"]', "", text)
    cleaned = re.sub(r"\b[a-z0-9]+(?:[_.][a-z0-9]+)+\b", lambda match: re.sub(r"[_.]", " ", match.group(0)), cleaned)
    return re.sub(r"\s+([,.;:])", r"\1", cleaned).strip()


def motion_label(motion: CouncilMotion) -> str:
    return MOTION_LABELS[motion]


def speech_part(part: PartOfSpeech | None) -> str:
    return PART_OF_SPEECH_LABELS[part] if part is not None else ""


def key_words(text: str) -> str:
    return re.sub(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b", lambda match: match.group(0).replace("_", " "), text)


def heading(level: int) -> str:
    return "#" * max(1, min(6, level))


def with_descendants(articles: Iterable[EntityArticle]) -> Iterator[EntityArticle]:
    waiting = list(reversed(list(articles)))
    while waiting:
        article = waiting.pop()
        yield article
        waiting.extend(reversed(article.children))


def _html_environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIRECTORY),
        autoescape=select_autoescape(enabled_extensions=("html", "svg", "j2"), default=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["paragraphs"] = paragraphs
    environment.filters["plain"] = plain_text
    environment.filters["keys"] = key_words
    environment.filters["motion"] = motion_label
    environment.filters["speech_part"] = speech_part
    environment.filters["with_descendants"] = with_descendants
    environment.filters["spoken"] = spoken
    return environment


def _markdown_environment() -> Environment:
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIRECTORY), autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    environment.filters["cell"] = table_cell
    environment.filters["prose"] = prose
    environment.filters["heading"] = heading
    environment.filters["with_descendants"] = with_descendants
    environment.filters["plain"] = plain_text
    environment.filters["keys"] = key_words
    environment.filters["motion"] = motion_label
    environment.filters["speech_part"] = speech_part
    environment.filters["spoken"] = spoken
    environment.globals["guide_markdown"] = guide_markdown
    return environment


HTML = _html_environment()
MARKDOWN = _markdown_environment()


def new_nonce() -> str:
    return secrets.token_urlsafe(NONCE_BYTES)


def render_book(model: BookModel | None, rules: Rules, *, links: BookLinks | None = None, pdf: PdfState | None = None) -> RenderedBook:
    nonce = new_nonce()
    chosen = links or ScreenLinks()
    if model is None:
        return RenderedBook(HTML.get_template(EMPTY_TEMPLATE).render(nonce=nonce, links=chosen, pdf=None), nonce)
    html = HTML.get_template(BOOK_TEMPLATE).render(book=model, rules=rules, nonce=nonce, single=False, links=chosen, pdf=pdf)
    return RenderedBook(html, nonce)


def render_entry(model: BookModel, rules: Rules, *, son: SonArticle | None = None, entity: EntityArticle | None = None) -> RenderedBook:
    nonce = new_nonce()
    html = HTML.get_template(ENTRY_TEMPLATE).render(book=model, rules=rules, nonce=nonce, single=True, son=son, entity=entity, links=ScreenLinks(), pdf=None)
    return RenderedBook(html, nonce)


def codex_chunks(model: BookModel | None, rules: Rules, links: CodexLinks) -> Iterator[str]:
    buffer = ""
    started = False
    for piece in MARKDOWN.get_template(CODEX_TEMPLATE).generate(book=model, rules=rules, links=links):
        buffer += piece
        if len(buffer) < CODEX_CHUNK:
            continue
        cut = len(buffer.rstrip(" \t\n"))
        if cut == 0:
            continue
        ready = EXTRA_BLANK_LINES.sub("\n\n", buffer[:cut])
        buffer = buffer[cut:]
        if not started:
            ready = ready.lstrip()
            started = bool(ready)
        if ready:
            yield ready
    tail = EXTRA_BLANK_LINES.sub("\n\n", buffer)
    tail = tail.strip() if not started else tail.rstrip()
    yield tail + "\n"


def render_codex(model: BookModel | None, rules: Rules, links: CodexLinks) -> str:
    return "".join(codex_chunks(model, rules, links))


def find_son(model: BookModel, son_id: int) -> SonArticle | None:
    return next((article for article in model.sons if article.son.id == son_id), None)


def find_entity(model: BookModel, entity_id: int) -> EntityArticle | None:
    def walk(articles: list[EntityArticle]) -> EntityArticle | None:
        for article in articles:
            if article.entity.id == entity_id:
                return article
            found = walk(article.children)
            if found is not None:
                return found
        return None

    for group in model.encyclopedia:
        for _label, articles in group.groups:
            found = walk(articles)
            if found is not None:
                return found
    return next((language.article for language in model.languages if language.article.entity.id == entity_id), None)
