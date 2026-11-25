from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.prompts.tools.divine_will_retrieval import HANDLE_FIELD, PAGE_FIELD, QUERY_FIELD

W = DivineWillToolId

ATTACHMENT_FIELD = "The id of an attached file, as attachment_list gives it."

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    W.ATTACHMENT_LIST: (
        "Lists the files the player attached in the exchanges within memory: each file's id, name, kind, type and size, "
        "the exchange it came with, whether it was turned into text, and whether you were shown it as an image. "
        "Files of exchanges beyond memory are not listed."
    ),
    W.ATTACHMENT_READ: (
        "Reads one attached document in full, as the text it was turned into, page by page. "
        "An image has no text here: its entry says whether you were shown it, and when you were not, tell the player you cannot see it."
    ),
    W.ATTACHMENT_SEARCH: (
        "Searches only the documents attached within memory, by their words and by what they mean, "
        "and gives the passages best first, each in full with the file it comes from."
    ),
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    W.ATTACHMENT_LIST: {"page": PAGE_FIELD},
    W.ATTACHMENT_READ: {"attachment_id": ATTACHMENT_FIELD, "page": PAGE_FIELD},
    W.ATTACHMENT_SEARCH: {"query": QUERY_FIELD, "handle": HANDLE_FIELD, "page": PAGE_FIELD},
}
