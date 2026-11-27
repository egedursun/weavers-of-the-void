import json
import re
import shutil
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tantivy

from aerona.domain.enums.divine_will import ChunkSource
from aerona.services.divine_will.chunking import Chunk

STORE_FORMAT = 1
ANALYZER = "lore"
LONGEST_TOKEN = 40
WRITER_HEAP = 128_000_000
WRITER_THREADS = 2
NO_ID = -1
META_FILE = "index.json"
WORDS_FOLDER = "words"
KEY_SEPARATOR = "|"
WORD = re.compile(r"[^\W_]+")
LOOKUP_BATCH = 1024
TEXT_FIELD = "text"

PassageKey = tuple[ChunkSource, str]
ChunkKey = tuple[str, str, int]


def passage_term(key: PassageKey) -> str:
    return f"{key[0].value}{KEY_SEPARATOR}{key[1]}"


def chunk_term(source: ChunkSource, source_id: str, ordinal: int) -> str:
    return f"{source.value}{KEY_SEPARATOR}{source_id}{KEY_SEPARATOR}{ordinal}"


def chunk_key(chunk: Chunk) -> ChunkKey:
    return chunk.source.value, chunk.source_id, chunk.ordinal


def query_words(query: str) -> str:
    return " ".join(word.lower() for word in WORD.findall(query))


@dataclass(frozen=True)
class Rendered:
    key: PassageKey
    refs: frozenset[str]
    chunks: tuple[Chunk, ...]


@dataclass(frozen=True)
class Found:
    chunk: Chunk
    parts: int
    score: float


@dataclass(frozen=True)
class Exclusions:
    sources: frozenset[ChunkSource] | None = None
    attachments: frozenset[str] | None = None
    artifacts: frozenset[str] = frozenset()
    cycles: frozenset[int] = frozenset()


@dataclass
class StoreMeta:
    format: int = STORE_FORMAT
    schema: str = ""
    built: bool = False
    cursors: dict[str, int] = field(default_factory=dict)
    built_at: str = ""

    def text(self) -> str:
        return json.dumps(
            {"format": self.format, "schema": self.schema, "built": self.built, "cursors": self.cursors, "built_at": self.built_at}, sort_keys=True
        )

    @classmethod
    def parsed(cls, text: str) -> "StoreMeta":
        data = json.loads(text)
        return cls(
            format=int(data.get("format", 0)),
            schema=str(data.get("schema", "")),
            built=bool(data.get("built", False)),
            cursors={str(name): int(value) for name, value in dict(data.get("cursors", {})).items()},
            built_at=str(data.get("built_at", "")),
        )


def word_schema() -> tantivy.Schema:
    builder = tantivy.SchemaBuilder()
    builder.add_text_field("passage", stored=False, tokenizer_name="raw", index_option="basic")
    builder.add_text_field("chunk", stored=False, tokenizer_name="raw", index_option="basic")
    builder.add_text_field("source", stored=True, tokenizer_name="raw", index_option="basic")
    builder.add_text_field("record", stored=True, tokenizer_name="raw", index_option="basic")
    builder.add_unsigned_field("ordinal", stored=True)
    builder.add_integer_field("node", stored=True)
    builder.add_integer_field("cycle", stored=True, indexed=True)
    builder.add_unsigned_field("parts", stored=True)
    builder.add_unsigned_field("tokens", stored=True)
    builder.add_text_field("digest", stored=True, tokenizer_name="raw", index_option="basic")
    builder.add_text_field(TEXT_FIELD, stored=True, tokenizer_name=ANALYZER, index_option="freq")
    builder.add_text_field("refs", stored=False, tokenizer_name="raw", index_option="basic")
    return builder.build()


def lore_analyzer() -> tantivy.TextAnalyzer:
    return (
        tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.simple())
        .filter(tantivy.Filter.remove_long(LONGEST_TOKEN))
        .filter(tantivy.Filter.lowercase())
        .filter(tantivy.Filter.ascii_fold())
        .build()
    )


def matches(result: tantivy.SearchResult) -> int:
    return int(getattr(result, "count", 0) or 0)


def first(document: tantivy.Document, name: str) -> Any:
    return document.get_first(name)


def chunk_of(document: tantivy.Document) -> tuple[Chunk, int]:
    node = int(first(document, "node"))
    cycle = int(first(document, "cycle"))
    chunk = Chunk(
        source=ChunkSource(str(first(document, "source"))),
        source_id=str(first(document, "record")),
        ordinal=int(first(document, "ordinal")),
        node_id=None if node == NO_ID else node,
        cycle_id=None if cycle == NO_ID else cycle,
        text=str(first(document, TEXT_FIELD)),
        tokens=int(first(document, "tokens")),
        digest=str(first(document, "digest")),
    )
    return chunk, int(first(document, "parts"))


class WordStore:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self._lock = threading.Lock()
        self._schema = word_schema()
        self._index: tantivy.Index | None = None
        self._writer: tantivy.IndexWriter | None = None
        self.meta = StoreMeta()

    @property
    def words(self) -> Path:
        return self.folder / WORDS_FOLDER

    def open(self, schema: str) -> bool:
        with self._lock:
            meta_path = self.folder / META_FILE
            meta = StoreMeta.parsed(meta_path.read_text()) if meta_path.is_file() else None
            usable = meta is not None and meta.format == STORE_FORMAT and meta.schema == schema and self.words.is_dir()
            if not usable:
                self._wipe()
                self.meta = StoreMeta(schema=schema)
                self._save_meta()
            else:
                assert meta is not None
                self.meta = meta
            self._index = self._opened()
            return usable and self.meta.built

    def reset(self, schema: str) -> None:
        with self._lock:
            self._wipe()
            self.meta = StoreMeta(schema=schema)
            self._save_meta()
            self._index = self._opened()

    def close(self) -> None:
        with self._lock:
            writer, self._writer = self._writer, None
            if writer is not None:
                writer.wait_merging_threads()
            self._index = None

    def _wipe(self) -> None:
        writer, self._writer = self._writer, None
        if writer is not None:
            writer.rollback()
        self._index = None
        if self.words.exists():
            shutil.rmtree(self.words)
        self.words.mkdir(parents=True, exist_ok=True)

    def _opened(self) -> tantivy.Index:
        self.words.mkdir(parents=True, exist_ok=True)
        index = tantivy.Index(self._schema, path=str(self.words), reuse=True)
        index.register_tokenizer(ANALYZER, lore_analyzer())
        return index

    def _save_meta(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        target = self.folder / META_FILE
        staged = target.with_suffix(".tmp")
        staged.write_text(self.meta.text())
        staged.replace(target)

    def save_meta(self) -> None:
        with self._lock:
            self._save_meta()

    def _index_now(self) -> tantivy.Index:
        if self._index is None:
            self._index = self._opened()
        return self._index

    def _writer_now(self) -> tantivy.IndexWriter:
        if self._writer is None:
            self._writer = self._index_now().writer(heap_size=WRITER_HEAP, num_threads=WRITER_THREADS)
        return self._writer

    def apply(self, rendered: Sequence[Rendered], removed: Iterable[PassageKey]) -> None:
        with self._lock:
            writer = self._writer_now()
            for key in removed:
                writer.delete_documents_by_term("passage", passage_term(key))
            for item in rendered:
                writer.delete_documents_by_term("passage", passage_term(item.key))
                for chunk in item.chunks:
                    writer.add_document(self._document(item, chunk))
            writer.commit()
            self._index_now().reload()

    def _document(self, item: Rendered, chunk: Chunk) -> tantivy.Document:
        document = tantivy.Document()
        document.add_text("passage", passage_term(item.key))
        document.add_text("chunk", chunk_term(chunk.source, chunk.source_id, chunk.ordinal))
        document.add_text("source", chunk.source.value)
        document.add_text("record", chunk.source_id)
        document.add_unsigned("ordinal", chunk.ordinal)
        document.add_integer("node", NO_ID if chunk.node_id is None else chunk.node_id)
        document.add_integer("cycle", NO_ID if chunk.cycle_id is None else chunk.cycle_id)
        document.add_unsigned("parts", len(item.chunks))
        document.add_unsigned("tokens", chunk.tokens)
        document.add_text("digest", chunk.digest)
        document.add_text(TEXT_FIELD, chunk.text)
        for ref in sorted(item.refs):
            document.add_text("refs", ref)
        return document

    def _searcher(self) -> tantivy.Searcher:
        return self._index_now().searcher()

    def count(self) -> int:
        with self._lock:
            return int(self._searcher().num_docs)

    def counts(self) -> dict[ChunkSource, int]:
        with self._lock:
            searcher = self._searcher()
            return {
                source: matches(searcher.search(tantivy.Query.term_query(self._schema, "source", source.value), limit=1, count=True)) for source in ChunkSource
            }

    def _all(self, searcher: tantivy.Searcher, query: tantivy.Query) -> list[tantivy.DocAddress]:
        total = matches(searcher.search(query, limit=1, count=True))
        if total == 0:
            return []
        return [address for _score, address in searcher.search(query, limit=total, count=False).hits]

    def dependents(self, refs: Iterable[str]) -> set[PassageKey]:
        wanted = sorted(set(refs))
        if not wanted:
            return set()
        found: set[PassageKey] = set()
        with self._lock:
            searcher = self._searcher()
            for start in range(0, len(wanted), LOOKUP_BATCH):
                query = tantivy.Query.term_set_query(self._schema, "refs", wanted[start : start + LOOKUP_BATCH])
                for address in self._all(searcher, query):
                    document = searcher.doc(address)
                    found.add((ChunkSource(str(first(document, "source"))), str(first(document, "record"))))
        return found

    def chunks_of(self, sources: Iterable[ChunkSource]) -> list[Chunk]:
        values = sorted(source.value for source in sources)
        if not values:
            return []
        with self._lock:
            searcher = self._searcher()
            query = tantivy.Query.term_set_query(self._schema, "source", values)
            return [chunk_of(searcher.doc(address))[0] for address in self._all(searcher, query)]

    def chunks(self, keys: Sequence[ChunkKey]) -> dict[ChunkKey, tuple[Chunk, int]]:
        found: dict[ChunkKey, tuple[Chunk, int]] = {}
        terms = [chunk_term(ChunkSource(source), source_id, ordinal) for source, source_id, ordinal in keys]
        with self._lock:
            searcher = self._searcher()
            for start in range(0, len(terms), LOOKUP_BATCH):
                query = tantivy.Query.term_set_query(self._schema, "chunk", terms[start : start + LOOKUP_BATCH])
                for address in self._all(searcher, query):
                    chunk, parts = chunk_of(searcher.doc(address))
                    found[(chunk.source.value, chunk.source_id, chunk.ordinal)] = (chunk, parts)
        return found

    def search(self, text: str, exclusions: Exclusions, limit: int) -> tuple[list[Found], int]:
        words = query_words(text)
        if not words:
            return [], 0
        with self._lock:
            index = self._index_now()
            searcher = index.searcher()
            clauses: list[tuple[tantivy.Occur, tantivy.Query]] = [(tantivy.Occur.Must, index.parse_query(words, [TEXT_FIELD]))]
            clauses.extend(self._filters(exclusions))
            query = tantivy.Query.boolean_query(clauses)
            result = searcher.search(query, limit=max(1, limit), count=True)
            found = []
            for score, address in result.hits:
                chunk, parts = chunk_of(searcher.doc(address))
                found.append(Found(chunk, parts, float(score)))
            return found, matches(result)

    def _filters(self, exclusions: Exclusions) -> list[tuple[tantivy.Occur, tantivy.Query]]:
        schema = self._schema
        clauses: list[tuple[tantivy.Occur, tantivy.Query]] = []
        if exclusions.sources is not None:
            clauses.append((tantivy.Occur.Must, tantivy.Query.term_set_query(schema, "source", sorted(source.value for source in exclusions.sources))))
        if exclusions.attachments is not None:
            attachment = tantivy.Query.term_query(schema, "source", ChunkSource.ATTACHMENT.value)
            if exclusions.attachments:
                kept = tantivy.Query.term_set_query(schema, "record", sorted(exclusions.attachments))
                foreign = tantivy.Query.boolean_query([(tantivy.Occur.Must, attachment), (tantivy.Occur.MustNot, kept)])
                clauses.append((tantivy.Occur.MustNot, foreign))
            else:
                clauses.append((tantivy.Occur.MustNot, attachment))
        if exclusions.artifacts:
            artifact = tantivy.Query.term_query(schema, "source", ChunkSource.ARTIFACT.value)
            hidden = tantivy.Query.term_set_query(schema, "record", sorted(exclusions.artifacts))
            clauses.append((tantivy.Occur.MustNot, tantivy.Query.boolean_query([(tantivy.Occur.Must, artifact), (tantivy.Occur.Must, hidden)])))
        if exclusions.cycles:
            clauses.append((tantivy.Occur.MustNot, tantivy.Query.term_set_query(schema, "cycle", sorted(exclusions.cycles))))
        return clauses
