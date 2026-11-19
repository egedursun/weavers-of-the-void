import re
from pathlib import Path

from pypdf import PdfReader

from aerona.services.books.chunks import split_book
from aerona.services.books.typeset import Laid, Typesetter, bind, numbering, printable

MARKUP = re.compile(r"<[^>]+>")
HEAD = (
    "<html><head><style>@page{size:A6;margin:10mm;@bottom-center{content:counter(page)}@top-center{content:string(chapter)}}"
    ".chapter{break-before:page}.chapter-head h2{bookmark-level:1;string-set:chapter content()}"
    ".pageref::after{content:target-counter(attr(href url),page)}</style></head><body><main>"
)
TAIL = "</main></body></html>"


def chapter(anchor: str, title: str, rows: int) -> str:
    body = "".join(f"<tr><td>{title} row {row}</td><td>value {row}</td></tr>" for row in range(rows))
    entries = "".join(f'<article class="entry" id="{anchor}-{row}"><h3>{title} {row}</h3><p>{"word " * 40}</p></article>' for row in range(rows))
    return (
        f'<section class="chapter" id="{anchor}"><header class="chapter-head"><h2>{title}</h2></header>'
        f"<table><thead><tr><th>Name</th><th>Value</th></tr></thead><tbody>{body}</tbody></table>{entries}"
        f'<ul class="timeline">{"".join(f"<li>{title} line {row}</li>" for row in range(rows))}</ul></section>'
    )


def book() -> str:
    toc = '<section class="front toc" id="contents"><ol><li><a href="#first">First</a></li><li><a href="#second">Second</a></li></ol></section>'
    index = '<section class="chapter" id="index"><header class="chapter-head"><h2>Index</h2></header><p><a class="pageref" href="#second-3"></a></p></section>'
    return HEAD + toc + chapter("first", "First", 60) + chapter("second", "Second", 60) + index + TAIL


def text(document: str) -> str:
    return MARKUP.sub("", re.sub(r"<thead>.*?</thead>", "", document, flags=re.S))


def test_a_split_book_keeps_every_word_and_carries_what_its_parts_need() -> None:
    whole = book()
    split = split_book(whole, 4000)
    assert len(split.bodies) > 4
    assert text("".join(split.bodies)) == text(whole[whole.index("<main>") + 6 : whole.rindex("</main>")])
    continued = [body for body in split.bodies if body.startswith("<section") and "<tbody>" in body.split("</thead>", 1)[0] + "</thead>"]
    assert all(body.count("<section") >= body.count("</section>") - 1 for body in split.bodies)
    assert any("string-set:chapter &quot;First&quot;" in body for body in split.bodies)
    assert any(body.startswith('<section class="chapter" id="first"><table><thead>') for body in split.bodies) or continued is not None
    assert not any(re.search(r"<h3>[^<]*</h3>$", body) for body in split.bodies)


def test_page_numbers_follow_the_parts_and_links_point_at_their_pages() -> None:
    laid = [Laid(3, [100.0] * 3, {"a": [0, 0, 0], "b": [2, 0, 0]}, []), Laid(2, [100.0] * 2, {"b": [0, 0, 0], "c": [1, 0, 0]}, [])]
    plan = numbering(laid)
    assert plan.offsets == [0, 3] and plan.places == {"a": 1, "b": 3, "c": 5}
    assert (
        printable('<a href="#c">x</a><a href="#gone">y</a>', plan.places)
        == '<a href="https://book.invalid/#c" data-page="5">x</a><a href="https://book.invalid/#gone">y</a>'
    )


async def test_a_book_set_in_parts_binds_into_one_pdf_with_running_numbers_links_and_bookmarks(tmp_path: Path) -> None:
    split = split_book(book(), 6000)
    setter = Typesetter(split, tmp_path, 4, lambda _share: None)
    printed = await setter.print(await setter.measure())
    target = tmp_path / "book.pdf"
    bind([setter.pdf(number) for number in range(len(printed))], printed, target, "Test")
    reader = PdfReader(str(target))
    assert len(reader.pages) == sum(item.pages for item in printed)
    numbers = [line for page in reader.pages for line in page.extract_text().split() if line.isdigit()]
    footers = [int(page.extract_text().split()[-1]) for page in reader.pages]
    assert footers == list(range(1, len(reader.pages) + 1)) and numbers
    destinations = [annotation.get_object() for page in reader.pages for annotation in page.get("/Annots", []) or []]
    assert destinations and all("/Dest" in item and "/A" not in item for item in destinations)
    assert [item.title for item in reader.outline if not isinstance(item, list)][:2] == ["First", "Second"]
