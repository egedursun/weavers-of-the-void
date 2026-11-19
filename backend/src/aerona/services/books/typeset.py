import asyncio
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from anyio import to_thread
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, Fit, FloatObject, NameObject, NumberObject

from aerona.constants.books import (
    PDF_LIBRARY_DIRECTORIES,
    PDF_LIBRARY_VARIABLE,
    PDF_LINK_PREFIX,
    PDF_POINTS_PER_PIXEL,
    PDF_SETTLE_PASSES,
    PDF_WORKER_MODULE,
)
from aerona.core.errors import ConflictError
from aerona.services.books.chunks import SplitBook

LAYOUT_FAILED = "The pages could not be set: {reason}"
ERROR_TAIL = 600
INTERNAL_LINK = re.compile(r'href="#([^"]+)"')
PAGE_NUMBERS = '.pageref::after{content:attr(data-page)}.toc li a::after{content:leader(". ") attr(data-page)}'
Report = Callable[[float], None]


@dataclass(frozen=True)
class Laid:
    pages: int
    heights: list[float]
    anchors: dict[str, list[float]]
    bookmarks: list[list[Any]]


@dataclass(frozen=True)
class Numbering:
    offsets: list[int]
    places: dict[str, int]


def worker_environment() -> dict[str, str]:
    environment = dict(os.environ)
    if sys.platform == "darwin":
        present = [directory for directory in PDF_LIBRARY_DIRECTORIES if Path(directory).is_dir()]
        existing = environment.get(PDF_LIBRARY_VARIABLE)
        environment[PDF_LIBRARY_VARIABLE] = os.pathsep.join([*present, *([existing] if existing else [])])
    return environment


async def run_worker(arguments: list[str], produced: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        PDF_WORKER_MODULE,
        *arguments,
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
    if process.returncode != 0 or not await to_thread.run_sync(produced.is_file):
        reason = error.decode(errors="replace").strip().splitlines()[-1:] if error else []
        raise ConflictError(LAYOUT_FAILED.format(reason=(reason[0] if reason else f"exit {process.returncode}")[-ERROR_TAIL:]))


def numbering(laid: list[Laid]) -> Numbering:
    offsets: list[int] = []
    places: dict[str, int] = {}
    total = 0
    for item in laid:
        offsets.append(total)
        for name, (page, _x, _y) in item.anchors.items():
            places.setdefault(name, total + int(page) + 1)
        total += item.pages
    return Numbering(offsets, places)


def printable(body: str, places: dict[str, int]) -> str:
    def linked(match: re.Match[str]) -> str:
        page = places.get(match.group(1))
        return f'href="{PDF_LINK_PREFIX}{match.group(1)}"' + (f' data-page="{page}"' if page is not None else "")

    return INTERNAL_LINK.sub(linked, body)


def print_style(offset: int) -> str:
    return f"@page:first{{counter-reset:page {offset + 1}}}{PAGE_NUMBERS}"


class Typesetter:
    def __init__(self, book: SplitBook, folder: Path, workers: int, report: Report) -> None:
        self.book = book
        self.folder = folder
        self.gate = asyncio.Semaphore(max(1, workers))
        self.report = report
        self.done = 0
        self.planned = 0

    async def lay(self, number: int, document: str, printing: bool) -> Laid:
        source = self.folder / f"chunk-{number}.html"
        info = self.folder / f"chunk-{number}.json"
        async with self.gate:
            await to_thread.run_sync(lambda: source.write_text(document, encoding="utf-8"))
            info.unlink(missing_ok=True)
            arguments = ["print", str(source), str(self.pdf(number)), str(info)] if printing else ["measure", str(source), str(info)]
            await run_worker(arguments, info)
            laid = Laid(**json.loads(await to_thread.run_sync(info.read_text)))
        self.done += 1
        self.report(self.done / max(1, self.planned))
        return laid

    def pdf(self, number: int) -> Path:
        return self.folder / f"chunk-{number}.pdf"

    async def measure(self) -> list[Laid]:
        self.done, self.planned = 0, len(self.book.bodies)
        return list(await asyncio.gather(*(self.lay(number, self.book.document(number), False) for number in range(self.planned))))

    def chunk(self, number: int, plan: Numbering) -> str:
        return self.book.document(number, print_style(plan.offsets[number]), printable(self.book.bodies[number], plan.places))

    async def print(self, measured: list[Laid]) -> list[Laid]:
        count = len(self.book.bodies)
        printed = list(measured)
        written: dict[int, str] = {}
        plan = numbering(measured)
        for _attempt in range(PDF_SETTLE_PASSES):
            documents = {number: self.chunk(number, plan) for number in range(count)}
            changed = [number for number in range(count) if written.get(number) != documents[number]]
            self.done, self.planned = 0, len(changed)
            for number, laid in zip(changed, await asyncio.gather(*(self.lay(number, documents[number], True) for number in changed)), strict=True):
                printed[number] = laid
                written[number] = documents[number]
            settled = numbering(printed)
            if settled == plan:
                return printed
            plan = settled
        return printed


def nearest(parents: dict[int, Any], level: int) -> Any:
    above = [key for key in parents if key < level]
    return parents[max(above)] if above else None


def bind(paths: list[Path], laid: list[Laid], target: Path, title: str) -> None:
    writer = PdfWriter()
    for path in paths:
        writer.append(str(path), import_outline=False)
    plan = numbering(laid)
    heights = [height for item in laid for height in item.heights]
    places = {name: (plan.offsets[number] + int(page), x, y) for number, item in enumerate(laid) for name, (page, x, y) in item.anchors.items()}
    for page in writer.pages:
        for reference in page.get("/Annots", []) or []:
            annotation = reference.get_object()
            action = annotation.get("/A")
            uri = str(action.get("/URI", "")) if isinstance(action, DictionaryObject) else ""
            if not uri.startswith(PDF_LINK_PREFIX):
                continue
            del annotation["/A"]
            found = places.get(unquote(uri[len(PDF_LINK_PREFIX) :]))
            if found is not None:
                number, x, y = found
                top = (heights[number] - y) * PDF_POINTS_PER_PIXEL
                annotation[NameObject("/Dest")] = ArrayObject(
                    [writer.pages[number].indirect_reference, NameObject("/XYZ"), FloatObject(x * PDF_POINTS_PER_PIXEL), FloatObject(top), NumberObject(0)]
                )
    parents: dict[int, Any] = {}
    for number, item in enumerate(laid):
        for level, label, page, x, y in item.bookmarks:
            at = plan.offsets[number] + int(page)
            fit = Fit.xyz(left=x * PDF_POINTS_PER_PIXEL, top=(heights[at] - y) * PDF_POINTS_PER_PIXEL)
            parents[int(level)] = writer.add_outline_item(title=str(label), page_number=at, parent=nearest(parents, int(level)), fit=fit)
            for deeper in [key for key in parents if key > int(level)]:
                del parents[deeper]
    writer.add_metadata({"/Title": title})
    with target.open("wb") as out:
        writer.write(out)
