import hashlib
import re
from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from aerona.domain.enums.divine_will import ChunkSource
from aerona.services.divine_will.embedding import Counter

CHUNK_TOKENS = 256
OVERLAP_TOKENS = 32
HEADING_SHARE = 2
PARAGRAPH_BREAK = "\n\n"
SENTENCE_BREAK = " "
LINE_BREAK = "\n"
PARAGRAPHS = re.compile(r"\n[ \t\r\f\v]*\n+")
SENTENCES = re.compile(r"(?<=[.!?;\u2026])\s+|(?<=[\u3002\uff01\uff1f\uff1b])\s*|(?<=[\u061f\u0964\u06d4])\s+")
SPACES = re.compile(r"[ \t\r\f\v]+")
DIGEST_SEPARATOR = "\x00"


@dataclass(frozen=True)
class Passage:
    source: ChunkSource
    source_id: str
    heading: str
    body: str
    node_id: int | None = None
    cycle_id: int | None = None


@dataclass(frozen=True)
class Chunk:
    source: ChunkSource
    source_id: str
    ordinal: int
    node_id: int | None
    cycle_id: int | None
    text: str
    tokens: int
    digest: str

    @property
    def key(self) -> tuple[ChunkSource, str, int]:
        return self.source, self.source_id, self.ordinal


@dataclass(frozen=True)
class Unit:
    text: str
    joiner: str
    tokens: int


def digest_of(text: str, model_key: str) -> str:
    return hashlib.sha256(f"{model_key}{DIGEST_SEPARATOR}{text}".encode()).hexdigest()


def tidy(text: str) -> str:
    lines = [SPACES.sub(" ", line).strip() for line in text.replace("\r\n", "\n").split("\n")]
    return PARAGRAPHS.sub(PARAGRAPH_BREAK, "\n".join(lines)).strip()


def character_pieces(text: str, limit: int, count: Counter) -> Iterator[str]:
    rest = text
    while rest:
        if count(rest) <= limit:
            yield rest
            return
        low, high = 1, len(rest)
        while low < high:
            middle = (low + high + 1) // 2
            if count(rest[:middle]) <= limit:
                low = middle
            else:
                high = middle - 1
        yield rest[:low]
        rest = rest[low:]


def word_pieces(text: str, limit: int, count: Counter) -> Iterator[str]:
    words: list[str] = []
    for word in text.split():
        if count(word) > limit:
            if words:
                yield " ".join(words)
                words = []
            yield from character_pieces(word, limit, count)
            continue
        if words and count(" ".join([*words, word])) > limit:
            yield " ".join(words)
            words = []
        words.append(word)
    if words:
        yield " ".join(words)


def units_of(body: str, limit: int, count: Counter) -> Iterator[Unit]:
    for raw in PARAGRAPHS.split(body):
        paragraph = raw.strip()
        if not paragraph:
            continue
        joiner = PARAGRAPH_BREAK
        tokens = count(paragraph)
        if tokens <= limit:
            yield Unit(paragraph, joiner, tokens)
            continue
        for piece_of in SENTENCES.split(paragraph):
            sentence = piece_of.strip()
            if not sentence:
                continue
            tokens = count(sentence)
            pieces = [sentence] if tokens <= limit else list(word_pieces(sentence, limit, count))
            for piece in pieces:
                yield Unit(piece, joiner, tokens if len(pieces) == 1 else count(piece))
                joiner = SENTENCE_BREAK


def joined(units: Iterable[Unit]) -> str:
    text = ""
    for unit in units:
        text = f"{text}{unit.joiner}{unit.text}" if text else unit.text
    return text


def tail(text: str, limit: int, count: Counter) -> str:
    words = text.split()
    if not words:
        return ""
    if count(words[-1]) > limit:
        pieces = list(character_pieces(words[-1][::-1], limit, count))
        return pieces[0][::-1] if pieces else ""
    low, high = 1, len(words)
    while low < high:
        middle = (low + high + 1) // 2
        if count(" ".join(words[-middle:])) <= limit:
            low = middle
        else:
            high = middle - 1
    return " ".join(words[-low:])


def packed(units: list[Unit], budget: int, count: Counter) -> list[str]:
    bodies: list[str] = []
    queue = deque(units)
    carry: Unit | None = None
    while queue:
        current = [carry] if carry is not None else []
        used = carry.tokens if carry is not None else 0
        fresh = 0
        while queue and (fresh == 0 or used + queue[0].tokens <= budget):
            unit = queue.popleft()
            current.append(unit)
            used += unit.tokens
            fresh += 1
        while fresh > 1 and count(joined(current)) > budget:
            queue.appendleft(current.pop())
            fresh -= 1
        if carry is not None and count(joined(current)) > budget:
            current = current[1:]
        body = joined(current)
        bodies.append(body)
        overlap = tail(body, OVERLAP_TOKENS, count) if queue else ""
        carry = Unit(overlap, PARAGRAPH_BREAK, count(overlap)) if overlap else None
    return bodies


def chunk_passage(passage: Passage, count: Counter, model_key: str) -> list[Chunk]:
    heading = tidy(passage.heading).replace(PARAGRAPH_BREAK, LINE_BREAK)
    body = tidy(passage.body)
    head_tokens = count(heading) + 1 if heading else 0
    if head_tokens * HEADING_SHARE > CHUNK_TOKENS:
        body = tidy(f"{heading}{PARAGRAPH_BREAK}{body}")
        heading = ""
        head_tokens = 0
    budget = CHUNK_TOKENS - head_tokens
    bodies = packed(list(units_of(body, budget - OVERLAP_TOKENS, count)), budget, count) if body else [""] if heading else []
    chunks: list[Chunk] = []
    for ordinal, piece in enumerate(bodies):
        text = f"{heading}{LINE_BREAK}{piece}" if heading and piece else heading or piece
        chunks.append(
            Chunk(
                source=passage.source,
                source_id=passage.source_id,
                ordinal=ordinal,
                node_id=passage.node_id,
                cycle_id=passage.cycle_id,
                text=text,
                tokens=count(text),
                digest=digest_of(text, model_key),
            )
        )
    return chunks
