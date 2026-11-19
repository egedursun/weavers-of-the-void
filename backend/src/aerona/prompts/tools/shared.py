LINK_FIELDS: dict[str, str] = {
    "links": "At least one meaningful bond to existing entities or siblings. The location bond (inside) is added automatically, do not repeat it.",
    "links.target_kind": "entity for a world entity, son for a sibling from the pantheon (or yourself)",
    "links.target_id": "The id of the bonded entity or son",
    "links.kind": (
        "Bond type. Direction is corrected by the engine: speaks, owns, celebrates, knows and rules always point from the community or mortal to the language, "
        "item, tradition, knowledge or place (when creating a language, give the speaks bond to the people who speak it). For example: lives_in, worships, "
        "protects, enemy, descends_from, source_of, tells_of. Use related only if no other type fits."
    ),
    "links.description": "Short description of the bond. Use related only if no concrete type fits, and then you MUST write the relation here.",
}

WORD_FIELDS: dict[str, str] = {
    "words": "Dictionary words: meaning, word class and origin",
    "words.word": "The word, in the language's own sounds",
    "words.meaning": "What it means",
    "words.kind": "Word class: noun, verb, adjective, affix, title, place_name, proper_name, number or interjection",
    "words.origin": "Etymology: from which event or which words it derived",
    "words.example": "Short usage example and its translation",
}

IMAGE_PROMPT_FIELD = 'An English image-generation prompt of the subject as its account gives it. {% include "shared/image_prompt_rules.md.j2" %}'
