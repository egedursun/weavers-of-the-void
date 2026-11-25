import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class Element(StrEnum):
    SCENE = "scene"
    ACTION = "action"
    CHARACTER = "character"
    PARENTHETICAL = "parenthetical"
    DIALOGUE = "dialogue"
    TRANSITION = "transition"
    CENTERED = "centered"
    SECTION = "section"
    SYNOPSIS = "synopsis"
    LYRIC = "lyric"
    PAGE_BREAK = "page_break"


BLOCK_CLASSES: dict[Element, str] = {
    Element.SCENE: "fn-scene",
    Element.ACTION: "fn-action",
    Element.CHARACTER: "fn-character",
    Element.PARENTHETICAL: "fn-parenthetical",
    Element.DIALOGUE: "fn-dialogue",
    Element.TRANSITION: "fn-transition",
    Element.CENTERED: "fn-centered",
    Element.SECTION: "fn-section",
    Element.SYNOPSIS: "fn-synopsis",
    Element.LYRIC: "fn-lyric",
    Element.PAGE_BREAK: "fn-page-break",
}


@dataclass(frozen=True)
class Block:
    element: Element
    text: str
    level: int = 0


@dataclass(frozen=True)
class Script:
    title_page: list[tuple[str, str]] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)


@dataclass(frozen=True)
class Span:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


BONEYARD = re.compile(r"/\*.*?\*/", re.DOTALL)
NOTE = re.compile(r"\[\[.*?\]\]", re.DOTALL)
TITLE_KEY = re.compile(r"^([A-Za-z][A-Za-z ]*):\s*(.*)$")
SCENE_START = re.compile(r"^(INT\.?/EXT|INT/EXT|I/E|INT|EXT|EST)[\.\s]", re.IGNORECASE)
PAGE_BREAK = re.compile(r"^={3,}\s*$")
EMPHASIS = re.compile(r"(\*\*\*|\*\*|\*|_)(?=\S)(.+?)(?<=\S)\1")
TRANSITION_END = "TO:"
TITLE_INDENT = ("   ", "\t")


def cased_upper(text: str) -> bool:
    return any(character.isupper() for character in text) and not any(character.islower() for character in text)


def character_name(line: str) -> bool:
    name = line.split("(", 1)[0].rstrip("^ ").strip()
    return bool(name) and cased_upper(name)


def split_title_page(lines: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or not TITLE_KEY.match(lines[start]):
        return [], lines
    pairs: list[tuple[str, str]] = []
    index = start
    while index < len(lines) and lines[index].strip():
        line = lines[index]
        matched = TITLE_KEY.match(line)
        if matched and not line.startswith(TITLE_INDENT):
            pairs.append((matched.group(1).strip(), matched.group(2).strip()))
        elif pairs:
            key, value = pairs[-1]
            pairs[-1] = (key, f"{value}\n{line.strip()}".strip())
        index += 1
    return pairs, lines[index:]


@dataclass(frozen=True)
class Line:
    text: str
    before_blank: bool
    after_blank: bool


def section(line: Line) -> Block:
    level = len(line.text) - len(line.text.lstrip("#"))
    return Block(Element.SECTION, line.text[level:].strip(), level)


LINE_RULES: tuple[tuple[Callable[[Line], bool], Callable[[Line], Block]], ...] = (
    (lambda line: PAGE_BREAK.match(line.text) is not None, lambda line: Block(Element.PAGE_BREAK, "")),
    (lambda line: line.text.startswith("#"), section),
    (lambda line: line.text.startswith("="), lambda line: Block(Element.SYNOPSIS, line.text[1:].strip())),
    (lambda line: line.text.startswith("~"), lambda line: Block(Element.LYRIC, line.text[1:].strip())),
    (
        lambda line: line.text.startswith(">") and line.text.endswith("<") and len(line.text) > 1,
        lambda line: Block(Element.CENTERED, line.text[1:-1].strip()),
    ),
    (lambda line: line.text.startswith(">"), lambda line: Block(Element.TRANSITION, line.text[1:].strip())),
    (
        lambda line: line.text.startswith(".") and len(line.text) > 1 and line.text[1] != ".",
        lambda line: Block(Element.SCENE, line.text[1:].strip()),
    ),
    (lambda line: line.before_blank and SCENE_START.match(line.text) is not None, lambda line: Block(Element.SCENE, line.text)),
    (
        lambda line: line.before_blank and line.after_blank and cased_upper(line.text) and line.text.endswith(TRANSITION_END),
        lambda line: Block(Element.TRANSITION, line.text),
    ),
)


def single_block(line: Line) -> Block | None:
    for matches, made in LINE_RULES:
        if matches(line):
            return made(line)
    return None


def parse_fountain(text: str) -> Script:
    cleaned = NOTE.sub("", BONEYARD.sub("", text.replace("\r\n", "\n")))
    title_page, lines = split_title_page(cleaned.split("\n"))
    blocks: list[Block] = []
    action: list[str] = []
    index = 0

    def flush() -> None:
        if action:
            blocks.append(Block(Element.ACTION, "\n".join(action).strip("\n")))
            action.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        before_blank = index == 0 or not lines[index - 1].strip()
        after_blank = index + 1 >= len(lines) or not lines[index + 1].strip()
        if not stripped:
            flush()
            index += 1
            continue
        found = single_block(Line(stripped, before_blank, after_blank))
        if found is not None:
            flush()
            blocks.append(found)
            index += 1
            continue
        forced = stripped.startswith("@")
        if before_blank and not after_blank and (forced or character_name(stripped)) and not stripped.startswith("!"):
            flush()
            blocks.append(Block(Element.CHARACTER, (stripped[1:] if forced else stripped).rstrip("^ ").strip()))
            index += 1
            while index < len(lines) and lines[index].strip():
                spoken = lines[index].strip()
                element = Element.PARENTHETICAL if spoken.startswith("(") and spoken.endswith(")") else Element.DIALOGUE
                if element is Element.DIALOGUE and blocks[-1].element is Element.DIALOGUE:
                    blocks[-1] = Block(Element.DIALOGUE, f"{blocks[-1].text}\n{spoken}")
                else:
                    blocks.append(Block(element, spoken))
                index += 1
            continue
        action.append(line[1:] if stripped.startswith("!") else line)
        index += 1
    flush()
    return Script(title_page, blocks)


def spans(text: str) -> list[Span]:
    found: list[Span] = []
    position = 0
    for match in EMPHASIS.finditer(text):
        if match.start() > position:
            found.append(Span(text[position : match.start()]))
        marker, inner = match.group(1), match.group(2)
        found.append(Span(inner, bold=marker in ("**", "***"), italic=marker in ("*", "***"), underline=marker == "_"))
        position = match.end()
    if position < len(text):
        found.append(Span(text[position:]))
    return found


def inline_html(text: str) -> str:
    rendered: list[str] = []
    for span in spans(text):
        piece = html.escape(span.text).replace("\n", "<br/>")
        if span.underline:
            piece = f"<u>{piece}</u>"
        if span.italic:
            piece = f"<em>{piece}</em>"
        if span.bold:
            piece = f"<strong>{piece}</strong>"
        rendered.append(piece)
    return "".join(rendered)


def fountain_html(script: Script) -> str:
    parts: list[str] = []
    if script.title_page:
        rows = "".join(
            f'<div class="fn-title-row"><span class="fn-key">{html.escape(key)}</span><span class="fn-value">{inline_html(value)}</span></div>'
            for key, value in script.title_page
        )
        parts.append(f'<section class="fn-title-page">{rows}</section>')
    for block in script.blocks:
        if block.element is Element.PAGE_BREAK:
            parts.append('<hr class="fn-page-break"/>')
        elif block.element is Element.SECTION:
            parts.append(f'<h{min(6, block.level + 1)} class="fn-section">{inline_html(block.text)}</h{min(6, block.level + 1)}>')
        elif block.element is Element.SCENE:
            parts.append(f'<h3 class="fn-scene">{inline_html(block.text)}</h3>')
        else:
            parts.append(f'<p class="{BLOCK_CLASSES[block.element]}">{inline_html(block.text)}</p>')
    return f'<div class="screenplay">{"".join(parts)}</div>'


def fountain_markdown(script: Script) -> str:
    parts: list[str] = []
    for key, value in script.title_page:
        parts.append(f"**{key}:** {value}")
    for block in script.blocks:
        if block.element is Element.PAGE_BREAK:
            parts.append("---")
        elif block.element is Element.SECTION:
            parts.append(f"{'#' * min(6, block.level)} {block.text}")
        elif block.element is Element.SCENE:
            parts.append(f"### {block.text}")
        elif block.element is Element.CHARACTER:
            parts.append(f"**{block.text}**")
        elif block.element is Element.PARENTHETICAL:
            parts.append(f"*{block.text}*")
        elif block.element in (Element.TRANSITION, Element.SYNOPSIS):
            parts.append(f"> {block.text}")
        elif block.element is Element.DIALOGUE:
            parts.append("  \n".join(block.text.split("\n")))
        else:
            parts.append(block.text)
    return "\n\n".join(parts) + "\n"
