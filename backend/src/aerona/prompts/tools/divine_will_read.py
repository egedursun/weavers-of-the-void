from aerona.prompts.tools.divine_will_ids import DivineWillToolId

W = DivineWillToolId

PAGE_FIELD = "Which page of the result to read, from 1. Leave it out for the first page; read_more with the handle gives the next one."
NODE_FIELD = "The id of the node: an entity, son, foreign god, world, star, galaxy, cluster, dimension or the Creator."

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    W.READ_NODE: (
        "Reads one node's entry in full: its identity and every value it holds, its lore texts, every typed section of its records, "
        "every bond it has or had and every change made to its records. Ask for one part to read less. Long entries come in pages."
    ),
    W.READ_RECORDS: (
        "Lists every record row a node owns, table by table, with each row's key columns, every value and which values are held. "
        "These keys are what the record_row actions take. Name a table to read only that one."
    ),
    W.ENUMERATE: (
        "Lists every record of one kind, all of them, in a fixed order, page by page. Use it whenever the player asks about all "
        "or every record of something, or how many there are; never answer such questions from a search. The kind is an entity type, "
        "a kind of node, any table name, or tables to list every table with its columns. Filters match columns exactly; contains "
        "matches text in any text column; sort names columns, a leading minus sorts that column from high to low."
    ),
    W.GRAPH_NEIGHBOURS: (
        "Follows a node's links outward: its bonds, where it lies, what it made, who made it, the routes between worlds. "
        "Depth says how many steps to follow; bond_kinds keeps only links of those kinds. Every link reached is listed."
    ),
    W.GRAPH_PATH: "Finds the shortest chain of links between two nodes, step by step, within the given depth.",
    W.CHRONICLE: (
        "Reads the world's chronicle line by line in the order it happened, or newest first. Narrow it by epochs, world, a node "
        "the lines concern, the kind of line or words the line contains. Every matching line is listed, page by page."
    ),
    W.EXPLAIN: (
        "Explains why things are as they are. With an incident_id: the incident's moment, place, participants, facts, steps, the terms "
        "behind each number and every change it made, its causes and its effects. With a node_id: every incident the node took part in, "
        "with what caused each and what each led to."
    ),
    W.STATE_AT: (
        "Shows how a node stood at a past moment: every record of it then and now, field by field, with what changed since. "
        "Give the epoch, and a year with season, day and hour for a finer moment."
    ),
    W.LEDGER: (
        "Reads the ledger of acts upon the world: who acted, with which tool, in which epoch, what each act changed and whether it was "
        "undone. Narrow it by epoch, actor, tool or undone state."
    ),
    W.WORLD_OVERVIEW: (
        "Gives the world at a glance: its name, epoch, lore language, seed, tone and cosmology, the Creator, the count of records by type "
        "and status, every son, world, star and foreign god, and the wars under way."
    ),
    W.READ_MORE: "Reads the next page of an earlier result from its handle. Every paged result names its handle and says whether more follows.",
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    W.READ_NODE: {
        "node_id": NODE_FIELD,
        "part": "Which part to read: all, identity (every value of the node), lore (its long texts), sections (its typed records), bonds, "
        "or changes (every change made to its records, oldest first, with who made it, why and during which incident).",
        "page": PAGE_FIELD,
    },
    W.READ_RECORDS: {
        "node_id": NODE_FIELD,
        "table": "One table to read; leave it empty for every table the node owns rows in.",
        "page": PAGE_FIELD,
    },
    W.ENUMERATE: {
        "kind": "An entity type, a kind of node, a table name, or tables.",
        "filters": "Column names mapped to the exact value each must hold; null matches an empty column.",
        "contains": "Words that any text column of the record must contain.",
        "sort": "Column names to order by, first to last; prefix a name with a minus to sort it from high to low. Ties fall back to the record's key.",
        "page": PAGE_FIELD,
    },
    W.GRAPH_NEIGHBOURS: {
        "node_id": NODE_FIELD,
        "bond_kinds": "Link kinds to keep; leave it empty to follow every link.",
        "depth": "How many steps to follow outward, from 1 to 4.",
        "page": PAGE_FIELD,
    },
    W.GRAPH_PATH: {
        "first_id": "The node the path starts from.",
        "second_id": "The node the path ends at.",
        "depth": "The longest path to look for, in steps, from 1 to 12.",
        "page": PAGE_FIELD,
    },
    W.CHRONICLE: {
        "epoch_from": "The first epoch to read.",
        "epoch_to": "The last epoch to read.",
        "world_id": "Only lines of this world.",
        "node_id": "Only lines that concern this node.",
        "kind": "Only lines of this kind.",
        "contains": "Only lines that contain these words.",
        "newest_first": "True to read from the latest line backwards.",
        "page": PAGE_FIELD,
    },
    W.EXPLAIN: {
        "incident_id": "The incident to explain in full.",
        "node_id": "The node whose causes and effects to trace.",
        "depth": "How many causes back to follow from each incident, from 1 to 50.",
        "page": PAGE_FIELD,
    },
    W.STATE_AT: {
        "epoch": "The epoch of the moment.",
        "node_id": NODE_FIELD,
        "year": "The year within the world's count of years, for a moment inside an epoch.",
        "season": "The season, counted from 0, with a year.",
        "day": "The day, counted from 0, with a year.",
        "hour": "The hour, counted from 0, with a year.",
        "page": PAGE_FIELD,
    },
    W.LEDGER: {
        "epoch": "Only acts of this epoch.",
        "actor_kind": "Only acts of this kind of actor.",
        "actor_node_id": "Only acts of this actor.",
        "tool": "Only acts done with this tool or action id.",
        "undone": "True for only undone acts, false for only standing ones.",
        "newest_first": "False to read from the first act forwards.",
        "page": PAGE_FIELD,
    },
    W.WORLD_OVERVIEW: {"page": PAGE_FIELD},
    W.READ_MORE: {"handle": "The handle an earlier result gave."},
}
