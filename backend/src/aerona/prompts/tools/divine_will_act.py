from aerona.prompts.tools.divine_will_ids import DivineWillToolId

W = DivineWillToolId

PAGE_FIELD = "Which page of the result to read, from 1. Leave it out for the first page; read_more with the handle gives the next one."

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    W.SEARCH_ACTIONS: (
        "Searches every act the Creator can do, the same acts the player has on screen, by words in their id, title, group, "
        "input fields and cost. Leave the query empty and name a group to list that whole group."
    ),
    W.DESCRIBE_ACTION: "Gives one act in full: its group, whether it acts at once or runs as a job, its cost, and every input field with its type, limits and default, then its JSON schema.",
    W.PERFORM_ACTION: (
        "Performs one act of the Creator with the given input, exactly as the player's own controls do, with the same checks, cost, "
        "ledger and undo. Every act is first rehearsed without keeping anything. An act that would delete or end something, or spend "
        "much essence, is not done: it waits for the player's approval, and the turn ends. Otherwise it is done at once and the "
        "result names its ledger entry for undo. Anything written into the world is written in the world's lore language."
    ),
    W.JOB_STATUS: "Reads how a job started by an act stands: its kind, status, progress, stage, result and any error.",
    W.UNDO_ACTION: "Undoes one act from the ledger by its entry id, as the ledger's undo does, and says which changes were reversed and which could not be.",
    W.SET_RULE: (
        "Sets one rule of the world to a new value, as the player's rules screen does, within its range. The result gives the old "
        "and new value and how to go back. read_rule and search_rules give a rule's meaning, range and default first."
    ),
    W.RESET_RULE: "Returns one rule of the world to its default value, as the player's rules screen does, and gives the old value.",
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    W.SEARCH_ACTIONS: {
        "query": "Words to look for; leave it empty to list every act of the group.",
        "group": "Only acts of this group.",
        "page": PAGE_FIELD,
    },
    W.DESCRIBE_ACTION: {"action_id": "The id of the act, as search_actions lists it.", "page": PAGE_FIELD},
    W.PERFORM_ACTION: {
        "action_id": "The id of the act, as search_actions lists it.",
        "input": "The act's input fields as describe_action lists them, by name.",
    },
    W.JOB_STATUS: {"job_id": "The job id an act returned."},
    W.UNDO_ACTION: {"ledger_entry_id": "The ledger entry of the act to undo."},
    W.SET_RULE: {
        "namespace": "The rule's group, as read_rule names it.",
        "name": "The rule's name within its group.",
        "value": "The new value, within the rule's range.",
    },
    W.RESET_RULE: {"namespace": "The rule's group, as read_rule names it.", "name": "The rule's name within its group."},
}
