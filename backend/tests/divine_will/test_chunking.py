from itertools import pairwise

from aerona.domain.enums.divine_will import ChunkSource
from aerona.llm.token_count import count_tokens
from aerona.services.divine_will.chunking import CHUNK_TOKENS, OVERLAP_TOKENS, Chunk, Passage, chunk_passage, digest_of
from aerona.services.divine_will.embedding import EMBEDDER_KEY

HEADING = "Brinewatch — settlement"
SENTENCE = "The people of the town count each harvest and write the number into the ledger kept by the gate."


def chunks_of(body: str, heading: str = HEADING) -> list[Chunk]:
    return chunk_passage(Passage(ChunkSource.ENTITY, "9", heading, body, node_id=9), count_tokens, EMBEDDER_KEY)


def body_of(chunk: Chunk, heading: str = HEADING) -> str:
    return chunk.text.removeprefix(f"{heading}\n")


def shared(first: str, second: str) -> str:
    words, following = first.split(), second.split()
    for size in range(min(len(words), len(following)), 0, -1):
        if words[-size:] == following[:size]:
            return " ".join(words[-size:])
    return ""


def test_a_short_record_is_one_chunk_with_its_heading() -> None:
    found = chunks_of(SENTENCE)
    assert [chunk.text for chunk in found] == [f"{HEADING}\n{SENTENCE}"]
    assert found[0].tokens == count_tokens(found[0].text)
    assert (found[0].source, found[0].source_id, found[0].ordinal, found[0].node_id) == (ChunkSource.ENTITY, "9", 0, 9)


def test_long_records_split_within_the_budget_with_an_overlap() -> None:
    body = "\n\n".join(" ".join(f"{SENTENCE[:-1]} in year {year}." for year in range(paragraph * 6, paragraph * 6 + 6)) for paragraph in range(8))
    found = chunks_of(body)
    assert len(found) > 3
    assert all(chunk.tokens <= CHUNK_TOKENS and chunk.text.startswith(f"{HEADING}\n") for chunk in found)
    assert [chunk.ordinal for chunk in found] == list(range(len(found)))
    for first, second in pairwise(found):
        overlap = shared(body_of(first), body_of(second))
        assert overlap
        assert count_tokens(overlap) <= OVERLAP_TOKENS
    told = " ".join(body_of(chunk) for chunk in found).split()
    assert set(body.split()) <= set(told)


def test_paragraphs_that_fit_are_kept_whole() -> None:
    paragraphs = [" ".join(f"Paragraph {number} sentence {index} tells of the market." for index in range(9)) for number in range(5)]
    found = chunks_of("\n\n".join(paragraphs))
    for paragraph in paragraphs:
        assert any(paragraph in chunk.text for chunk in found), paragraph


def test_a_word_longer_than_the_budget_is_cut_by_characters() -> None:
    word = "x" * 5000
    found = chunks_of(word)
    assert len(found) > 1
    assert all(chunk.tokens <= CHUNK_TOKENS for chunk in found)
    assert "".join(body_of(chunk) for chunk in found).count("x") >= len(word)


def test_sentences_without_spaces_split_at_their_full_stops() -> None:
    sentence = "町の人々は毎年の収穫を数えて門の帳簿に記す。"
    found = chunks_of(sentence * 60)
    assert len(found) > 1
    assert all(chunk.tokens <= CHUNK_TOKENS for chunk in found)
    assert all(body_of(chunk).endswith("。") for chunk in found[:-1])


def test_digests_follow_the_text_alone() -> None:
    first, again = chunks_of(SENTENCE), chunks_of(SENTENCE)
    changed = chunks_of(f"{SENTENCE} A new line.")
    assert first[0].digest == again[0].digest == digest_of(first[0].text, EMBEDDER_KEY)
    assert changed[0].digest != first[0].digest
    assert digest_of(first[0].text, "another model") != first[0].digest


def test_a_heading_alone_still_makes_a_chunk() -> None:
    assert [chunk.text for chunk in chunks_of("")] == [HEADING]
    assert chunks_of("", heading="") == []
