from pathlib import Path

import numpy as np
import pytest
from tokenizers import Tokenizer

from aerona.services.divine_will.embedding import (
    MAX_POSITIONS,
    MODEL_FILE,
    MODEL_FILES,
    MODEL_NAME,
    VOCABULARY_FILE,
    EmbedderUnavailableError,
    ModelFile,
    TextRole,
    Vocabulary,
    ensure_files,
    load_embedder,
    model_directory,
)
from aerona.settings import Settings
from tests.divine_will.embedder_fixtures import REFERENCE_TOKENIZER, model_folder

SAMPLES = (
    "The Kessar Folk settled the vale in the second epoch.",
    "query: how many people live in Brinewatch",
    "passage: \uff26\uff55\uff4c\uff4c width letters, \u00bd and the \ufb01 ligature",
    "  leading   spaces\tand\nnew lines  ",
    "ends with a space ",
    "T\u00fcrk\u00e7e metin: \u0130stanbul'da \u0131\u015f\u0131k ve \u011f",
    "日本語のテキストです。句読点も含む\uff01",
    "Привет, мир! Как дела?",
    "مرحبا بالعالم، هذا نص عربي.",
    "हिन्दी में एक वाक्य।",
    "emoji 🙂 and the literal <unk> token",
    "<s> </s> <pad> <mask>",
    "x<mask>y  <unk>  z ",
    "   ",
    "",
    "a" * 3000,
    "word " * 700,
)


def test_token_ids_match_the_reference_tokenizer() -> None:
    model_dir = model_folder()
    vocabulary = Vocabulary(model_dir / VOCABULARY_FILE.path)
    reference = Tokenizer.from_file(str(model_dir / REFERENCE_TOKENIZER))
    reference.enable_truncation(MAX_POSITIONS)
    for text in SAMPLES:
        assert vocabulary.ids(text) == reference.encode(text).ids, text
        assert vocabulary.count(text) == len(vocabulary.pieces(text)), text
        assert len(vocabulary.ids(text)) <= MAX_POSITIONS


def test_embeddings_are_normalised_and_deterministic() -> None:
    model_dir = model_folder()
    embedder = load_embedder(model_dir, 2)
    texts = ["The council meets at the turn of each epoch.", "A road joins the two towns.", "Brinewatch"]
    first = embedder.embed(texts, TextRole.PASSAGE)
    again = embedder.embed(texts, TextRole.PASSAGE)
    alone = np.concatenate([embedder.embed([text], TextRole.PASSAGE) for text in texts])
    assert first.shape == (3, 384)
    assert np.allclose(np.linalg.norm(first, axis=1), 1.0, atol=1e-5)
    assert np.array_equal(first, again)
    assert np.array_equal(first, alone)
    assert load_embedder(model_dir, 2) is embedder


def test_a_query_is_closest_to_the_passage_it_asks_about() -> None:
    model_dir = model_folder()
    embedder = load_embedder(model_dir, 2)
    passages = embedder.embed(["The river floods the lowlands every spring.", "The council votes on a new tax on salt traders."], TextRole.PASSAGE)
    query = embedder.embed(["when does the river flood"], TextRole.QUERY)[0]
    scores = passages @ query
    assert scores[0] > scores[1]


def test_missing_files_without_fetching_leave_the_model_unavailable(tmp_path: Path) -> None:
    with pytest.raises(EmbedderUnavailableError, match="missing"):
        ensure_files(tmp_path, None)


def test_a_failed_fetch_leaves_the_model_unavailable(tmp_path: Path) -> None:
    def offline(_file: ModelFile, _directory: Path) -> None:
        raise OSError("no network")

    with pytest.raises(EmbedderUnavailableError, match="no network"):
        ensure_files(tmp_path, offline)


def test_a_fetched_file_with_the_wrong_hash_is_removed(tmp_path: Path) -> None:
    def tampered(file: ModelFile, directory: Path) -> None:
        target = directory / file.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"not the model")

    with pytest.raises(EmbedderUnavailableError, match="SHA-256"):
        ensure_files(tmp_path, tampered)
    assert not (tmp_path / MODEL_FILE.path).exists()


def test_fetched_files_are_verified_before_use(tmp_path: Path) -> None:
    model_dir = model_folder()
    fetched: list[str] = []

    def linked(file: ModelFile, directory: Path) -> None:
        fetched.append(file.path)
        target = directory / file.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(model_dir / file.path)

    ensure_files(tmp_path, linked)
    ensure_files(tmp_path, linked)
    assert fetched == [file.path for file in MODEL_FILES]


def test_the_model_folder_defaults_under_the_data_folder(tmp_path: Path) -> None:
    assert model_directory(Settings(data_dir=tmp_path)) == tmp_path / "models" / MODEL_NAME
    assert model_directory(Settings(data_dir=tmp_path, embed_model_dir=tmp_path / "elsewhere")) == tmp_path / "elsewhere"
