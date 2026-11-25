from aerona.domain.enums.divine_will import ChunkSource
from aerona.prompts.tools.divine_will_ids import DivineWillToolId

W = DivineWillToolId

SOURCE_NAMES = ", ".join(source.value for source in ChunkSource)
PAGE_FIELD = "Which page of the result to read, from 1. Leave it out for the first page; read_more with the handle gives the next one."
QUERY_FIELD = "What to look for, in any language. Several short searches with different words find more than one long one."
HANDLE_FIELD = "The handle of an earlier search to read again at the page asked for, instead of a new query."

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    W.SEARCH_LORE: (
        "Searches every written record of the world for passages close to the query, both by the words they contain and by what they mean, "
        "and gives the passages best first. Each passage comes in full with its source, its record and the node it belongs to, "
        "so it can be read further with read_node, explain or chronicle. The sources are: "
        f"{SOURCE_NAMES}. Documents the player attached are searched only while their exchange is within memory. "
        "Search more than once with other words, including words of the lore language, before answering; "
        "for every record of a kind, or how many there are, use enumerate instead."
    ),
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    W.SEARCH_LORE: {
        "query": QUERY_FIELD,
        "sources": f"Search only passages from these sources: {SOURCE_NAMES}. Leave it empty to search them all.",
        "handle": HANDLE_FIELD,
        "page": PAGE_FIELD,
    },
}
