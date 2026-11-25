import hashlib
import os
from collections.abc import Sequence
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from aerona.constants.paths import MODELS_DIRNAME
from aerona.llm.token_count import count_tokens
from aerona.services.divine_will.embedding import DIMENSIONS, MODEL_FILES, MODEL_NAME, TextRole, Vector, holds, sha256_of

REPOSITORY = Path(__file__).resolve().parents[3]
MODEL_ENV = "AERONA_TEST_EMBED_MODEL_DIR"
REFERENCE_TOKENIZER = "tokenizer.json"
REFERENCE_SHA256 = "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"
MISSING = (
    "The embedding model files {names} are missing from {folder}. Put onnx/model_quantized.onnx, sentencepiece.bpe.model and the "
    "reference tokenizer.json of multilingual-e5-small there, or name their folder in {env}."
)


@cache
def model_folder() -> Path:
    folder = Path(os.environ.get(MODEL_ENV) or REPOSITORY / "data" / MODELS_DIRNAME / MODEL_NAME)
    missing = [file.path for file in MODEL_FILES if not holds(folder, file)]
    reference = folder / REFERENCE_TOKENIZER
    if not reference.is_file() or sha256_of(reference) != REFERENCE_SHA256:
        missing.append(REFERENCE_TOKENIZER)
    if missing:
        pytest.fail(MISSING.format(names=", ".join(missing), folder=folder, env=MODEL_ENV))
    return folder


class CountingEmbedder:
    def __init__(self) -> None:
        self.passages: list[str] = []
        self.queries: list[str] = []

    def embed(self, texts: Sequence[str], role: TextRole) -> Vector:
        (self.passages if role is TextRole.PASSAGE else self.queries).extend(texts)
        rows = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
            vector = np.random.default_rng(seed).standard_normal(DIMENSIONS).astype(np.float32)
            rows.append(vector / np.linalg.norm(vector))
        return np.asarray(rows, dtype=np.float32).reshape(len(texts), DIMENSIONS)

    def count(self, text: str) -> int:
        return count_tokens(text)
