import hashlib
import re
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import numpy as np
import onnxruntime
from huggingface_hub import hf_hub_download
from numpy.typing import NDArray
from sentencepiece import SentencePieceProcessor

from aerona.llm.token_count import count_tokens
from aerona.settings import Settings

MODEL_NAME = "multilingual-e5-small"
DIMENSIONS = 384
MAX_POSITIONS = 512
BODY_TOKENS = MAX_POSITIONS - 2
START_ID = 0
PAD_ID = 1
END_ID = 2
UNKNOWN_ID = 3
FAIRSEQ_OFFSET = 1
SPACE_PIECE = "▁"
MASK_TOKEN = "<mask>"
SPECIAL_HINT = "<"
SPECIAL_TOKENS = {"<s>": START_ID, "<pad>": PAD_ID, "</s>": END_ID, "<unk>": UNKNOWN_ID}
CPU_PROVIDER = "CPUExecutionProvider"
HIDDEN_OUTPUT = "last_hidden_state"
HASH_BLOCK = 1 << 20
SMALLEST_NORM = 1e-12
MISSING_FILE = "The embedding model file {name} is missing from {directory} and fetching is off."
FETCH_FAILED = "The embedding model file {name} could not be fetched: {reason}"
WRONG_HASH = "The embedding model file {name} does not match its pinned SHA-256 and was removed."

Vector = NDArray[np.float32]


class TextRole(StrEnum):
    QUERY = "query: "
    PASSAGE = "passage: "


@dataclass(frozen=True)
class ModelFile:
    repo: str
    revision: str
    path: str
    sha256: str


MODEL_FILE = ModelFile(
    "Xenova/multilingual-e5-small",
    "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
    "onnx/model_quantized.onnx",
    "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193",
)
VOCABULARY_FILE = ModelFile(
    "intfloat/multilingual-e5-small",
    "614241f622f53c4eeff9890bdc4f31cfecc418b3",
    "sentencepiece.bpe.model",
    "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
)
MODEL_FILES = (MODEL_FILE, VOCABULARY_FILE)
EMBEDDER_KEY = f"{MODEL_NAME}:{MODEL_FILE.sha256}:{VOCABULARY_FILE.sha256}"

Fetcher = Callable[[ModelFile, Path], None]
Counter = Callable[[str], int]


class TextEmbedder(Protocol):
    def embed(self, texts: Sequence[str], role: TextRole) -> Vector: ...

    def count(self, text: str) -> int: ...


class EmbedderUnavailableError(Exception):
    pass


def model_directory(settings: Settings) -> Path:
    return settings.embed_model_dir or settings.process.models / MODEL_NAME


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(HASH_BLOCK):
            digest.update(block)
    return digest.hexdigest()


def holds(directory: Path, file: ModelFile) -> bool:
    target = directory / file.path
    return target.is_file() and sha256_of(target) == file.sha256


def download(file: ModelFile, directory: Path) -> None:
    hf_hub_download(repo_id=file.repo, filename=file.path, revision=file.revision, local_dir=directory)


FETCHING = threading.Lock()


def ensure_files(directory: Path, fetch: Fetcher | None) -> None:
    with FETCHING:
        fetch_missing(directory, fetch)


def fetch_missing(directory: Path, fetch: Fetcher | None) -> None:
    for file in MODEL_FILES:
        if holds(directory, file):
            continue
        if fetch is None:
            raise EmbedderUnavailableError(MISSING_FILE.format(name=file.path, directory=directory))
        try:
            fetch(file, directory)
        except Exception as error:
            raise EmbedderUnavailableError(FETCH_FAILED.format(name=file.path, reason=error)) from error
        if not holds(directory, file):
            (directory / file.path).unlink(missing_ok=True)
            raise EmbedderUnavailableError(WRONG_HASH.format(name=file.path))


class Vocabulary:
    def __init__(self, path: Path) -> None:
        self._processor = SentencePieceProcessor(model_file=str(path))
        self._space = self._processor.piece_to_id(SPACE_PIECE) + FAIRSEQ_OFFSET
        self._specials = {**SPECIAL_TOKENS, MASK_TOKEN: self._processor.get_piece_size() + FAIRSEQ_OFFSET}
        self._split = re.compile("(" + "|".join(re.escape(token) for token in sorted(self._specials, key=len, reverse=True)) + ")")

    def pieces(self, text: str) -> list[int]:
        found: list[int] = []
        for part in self._split.split(text):
            if not part:
                continue
            special = self._specials.get(part)
            if special is not None:
                found.append(special)
                continue
            found.extend(piece + FAIRSEQ_OFFSET if piece else UNKNOWN_ID for piece in self._processor.encode(part))
            if part[-1].isspace():
                found.append(self._space)
        return found

    def ids(self, text: str) -> list[int]:
        return [START_ID, *self.pieces(text)[:BODY_TOKENS], END_ID]

    def count(self, text: str) -> int:
        if SPECIAL_HINT in text:
            return len(self.pieces(text))
        found = len(self._processor.encode(text))
        return found + 1 if text and text[-1].isspace() else found


class Embedder:
    def __init__(self, directory: Path, threads: int) -> None:
        self.vocabulary = Vocabulary(directory / VOCABULARY_FILE.path)
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = onnxruntime.InferenceSession(str(directory / MODEL_FILE.path), options, providers=[CPU_PROVIDER])
        self._pool = ThreadPoolExecutor(max_workers=max(1, threads), thread_name_prefix="embed")

    def embed(self, texts: Sequence[str], role: TextRole) -> Vector:
        found = np.zeros((len(texts), DIMENSIONS), dtype=np.float32)
        for index, vector in enumerate(self._pool.map(self.one, [role.value + text for text in texts])):
            found[index] = vector
        return found

    def one(self, text: str) -> Vector:
        ids = np.asarray([self.vocabulary.ids(text)], dtype=np.int64)
        mask = np.ones_like(ids)
        feeds = {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)}
        hidden = np.asarray(self._session.run([HIDDEN_OUTPUT], feeds)[0], dtype=np.float32)
        pooled = hidden[0].mean(axis=0)
        return np.asarray(pooled / max(float(np.linalg.norm(pooled)), SMALLEST_NORM), dtype=np.float32)

    def count(self, text: str) -> int:
        return self.vocabulary.count(text)


LOADED: dict[tuple[Path, int], Embedder] = {}
LOADING = threading.Lock()


def load_embedder(directory: Path, threads: int) -> Embedder:
    key = (directory.resolve(), max(1, threads))
    with LOADING:
        found = LOADED.get(key)
        if found is None:
            found = LOADED[key] = Embedder(directory, threads)
        return found


def token_counter(directory: Path) -> Counter:
    if holds(directory, VOCABULARY_FILE):
        return Vocabulary(directory / VOCABULARY_FILE.path).count
    return count_tokens
