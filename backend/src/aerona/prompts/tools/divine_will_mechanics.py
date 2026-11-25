from aerona.prompts.tools.divine_will_ids import DivineWillToolId

W = DivineWillToolId

PAGE_FIELD = "Which page of the result to read, from 1. Leave it out for the first page; read_more with the handle gives the next one."

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    W.SEARCH_RULES: (
        "Searches the world's rules by words in their name, label and group. Each hit gives the value this world uses, its default, "
        "its range and what it means. Leave the query empty and name a group to list that whole group."
    ),
    W.READ_RULE: "Reads one rule in full: its meaning, value, default, range, group, whether this world changed it, and the mechanics it steers.",
    W.SEARCH_MECHANICS: "Searches the registry of the engine's mechanics by words in their key, title, subsystem, phases, tables, tools and levers.",
    W.READ_MECHANIC: (
        "Reads one mechanic in full: its subsystem, the epoch phases that run it, the tables and fields it touches, the agent tools and "
        "god levers that reach it, the rules that steer it and every mechanic it feeds or is fed by."
    ),
    W.READ_GAME_RULES: (
        "Reads the rules booklet of the game. Without a section it lists every section by its path; with a section it reads that section in full, page by page."
    ),
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    W.SEARCH_RULES: {"query": "Words to look for.", "group": "Only rules of this group.", "page": PAGE_FIELD},
    W.READ_RULE: {"namespace": "The part of the rule's path before the dot.", "name": "The part of the rule's path after the dot.", "page": PAGE_FIELD},
    W.SEARCH_MECHANICS: {"query": "Words to look for; leave it empty to list every mechanic.", "page": PAGE_FIELD},
    W.READ_MECHANIC: {"key": "The mechanic's key, as search_mechanics lists it.", "page": PAGE_FIELD},
    W.READ_GAME_RULES: {"section": "The section's path or title; leave it empty to list the sections.", "page": PAGE_FIELD},
}
