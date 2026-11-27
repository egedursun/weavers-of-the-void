import tantivy

from aerona.services.divine_will.index import LoreIndex
from aerona.services.divine_will.store import ANALYZER, WORDS_FOLDER, lore_analyzer

Docs = dict[tuple[str, str, int], str]


def documents(index: LoreIndex) -> Docs:
    opened = tantivy.Index.open(str(index.folder / WORDS_FOLDER))
    opened.register_tokenizer(ANALYZER, lore_analyzer())
    searcher = opened.searcher()
    found: Docs = {}
    if searcher.num_docs == 0:
        return found
    for _score, address in searcher.search(tantivy.Query.all_query(), limit=searcher.num_docs, count=False).hits:
        document = searcher.doc(address)
        found[(str(document.get_first("source")), str(document.get_first("record")), int(str(document.get_first("ordinal"))))] = str(
            document.get_first("digest")
        )
    return found


def texts(index: LoreIndex, keys: list[tuple[str, str, int]]) -> dict[tuple[str, str, int], str]:
    opened = tantivy.Index.open(str(index.folder / WORDS_FOLDER))
    opened.register_tokenizer(ANALYZER, lore_analyzer())
    searcher = opened.searcher()
    found: dict[tuple[str, str, int], str] = {}
    for key in keys:
        query = tantivy.Query.term_query(opened.schema, "chunk", "|".join((key[0], key[1], str(key[2]))))
        for _score, address in searcher.search(query, limit=1, count=False).hits:
            found[key] = str(searcher.doc(address).get_first("text"))
    return found
