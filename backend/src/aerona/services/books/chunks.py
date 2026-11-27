import html
import re
from dataclasses import dataclass, field

TAG = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*)>")
CLASS = re.compile(r"""class=["']([^"']*)["']""")
MARKUP = re.compile(r"<[^>]+>")
ID_ATTRIBUTE = re.compile(r"""\sid=(?:"[^"]*"|'[^']*')""")
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
CONTAINERS = frozenset({"section", "li", "table", "tbody"})
OPEN_LISTS = frozenset({"timeline", "log", "index-list", "changes"})
HEADINGS = frozenset({"h2", "h3", "h4", "h5", "h6", "header"})
HEADING_GROUP = "group-head"
CHAPTER_HEAD = "chapter-head"
MAIN_OPEN = "<main>"
MAIN_CLOSE = "</main>"
HEAD_CLOSE = "</head>"


@dataclass
class Opened:
    name: str
    tag: str
    classes: frozenset[str]
    carried: str = ""


@dataclass
class Splitter:
    target: int
    chunks: list[str] = field(default_factory=list)
    stack: list[Opened] = field(default_factory=list)
    start: int = 0
    prefix: str = ""
    chapter: str = ""
    previous: Opened | None = None
    keep_ids: bool = True

    def splittable(self) -> bool:
        if self.previous is not None and (self.previous.name in HEADINGS or HEADING_GROUP in self.previous.classes):
            return False
        return all(item.name in CONTAINERS or (item.name == "ul" and bool(item.classes & OPEN_LISTS)) for item in self.stack)

    def cut(self, source: str, at: int) -> None:
        self.chunks.append(self.prefix + source[self.start : at] + "".join(f"</{item.name}>" for item in reversed(self.stack)))
        carried = f'<span style="string-set:chapter &quot;{html.escape(self.chapter, quote=True)}&quot;"></span>' if self.chapter else ""
        reopened = "".join(item.tag + item.carried for item in self.stack)
        self.prefix = (reopened if self.keep_ids else ID_ATTRIBUTE.sub("", reopened)) + carried
        self.start = at

    def close(self, name: str, source: str, end: int) -> None:
        while self.stack:
            item = self.stack.pop()
            if item.name == name:
                self.previous = item
                break
        if name == "header" and self.previous is not None and CHAPTER_HEAD in self.previous.classes:
            heading = re.search(r"<h2[^>]*>(.*?)</h2>", source[source.rfind("<header", 0, end) : end], re.S)
            self.chapter = html.unescape(MARKUP.sub("", heading.group(1))).strip() if heading else self.chapter

    def feed(self, source: str) -> list[str]:
        for match in TAG.finditer(source):
            closing, name, rest = match.group(1), match.group(2).lower(), match.group(3)
            if closing:
                self.close(name, source, match.start())
                continue
            if match.start() - self.start + len(self.prefix) >= self.target and self.splittable():
                self.cut(source, match.start())
            if name in VOID or rest.rstrip().endswith("/"):
                continue
            found = CLASS.search(rest)
            if name == "thead" and self.stack and self.stack[-1].name == "table":
                self.stack[-1].carried = source[match.start() : source.find("</thead>", match.end()) + len("</thead>")]
            self.stack.append(Opened(name, match.group(0), frozenset(found.group(1).split()) if found else frozenset()))
            self.previous = None
        self.chunks.append(self.prefix + source[self.start :])
        return self.chunks


@dataclass(frozen=True)
class SplitBook:
    head: str
    bodies: list[str]
    tail: str

    def document(self, number: int, style: str = "", body: str | None = None) -> str:
        head = self.head.replace(HEAD_CLOSE, f"<style>{style}</style>{HEAD_CLOSE}", 1) if style else self.head
        return head + (self.bodies[number] if body is None else body) + self.tail


def split_book(document: str, target: int, *, keep_ids: bool = True) -> SplitBook:
    opening = document.index(MAIN_OPEN) + len(MAIN_OPEN)
    closing = document.rindex(MAIN_CLOSE)
    return SplitBook(document[:opening], Splitter(target, keep_ids=keep_ids).feed(document[opening:closing]), document[closing:])
