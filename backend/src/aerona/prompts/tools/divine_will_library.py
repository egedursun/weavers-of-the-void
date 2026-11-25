from aerona.prompts.tools.divine_will_ids import DivineWillToolId

W = DivineWillToolId

PAGE_FIELD = "Which page of the result to read, from 1. Leave it out for the first page; read_more with the handle gives the next one."
STEP_FIELDS: dict[str, str] = {
    "steps": "Every step of the plan in the order it should run; a step is numbered by its place in this list, from 1.",
    "steps.title": "What the step does, in a few words, in the player's language.",
    "steps.action_id": (
        "The id of the act the step performs, as search_actions lists it; or rule:set to change a rule of the world, "
        "or rule:reset to return a rule to its default, as set_rule and reset_rule do."
    ),
    "steps.input": (
        "The act's input fields as describe_action lists them, by name; free text the act writes into the world is in the world's lore language. "
        "A rule step takes namespace and name, and rule:set also takes value."
    ),
    "steps.depends_on": "The numbers of the steps that must be done before this one runs; leave it empty when it waits for none.",
    "steps.declared_impact": (
        "What the step does to the world: safe, costly (spends much essence) or destructive (deletes or ends something). "
        "Approving the plan approves what each step declares; a step whose rehearsal shows more than it declared stops the plan and asks the player."
    ),
    "steps.estimated_essence": "The essence the step should spend, as describe_action gives its cost; 0 when it is free.",
}

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    W.ARTIFACT_CREATE: (
        "Writes a new artifact into the library: a piece of written work kept with every version, which the player reads, exports and "
        "finds again by search. The text is written in the language given here. Markdown suits prose and notes, fountain suits screenplays "
        "and html suits a page with its own layout."
    ),
    W.ARTIFACT_READ: "Reads an artifact in full, its current version or an earlier one, with its kind, format, status, language, tags, subjects and list of versions.",
    W.ARTIFACT_EDIT: (
        "Changes an artifact. Each edit is one of: replace a passage that occurs exactly once with new text; insert text right after a "
        "passage that occurs exactly once; append text at the end; or rewrite the whole text. Every edit keeps a new version and the "
        "earlier ones stay readable. If a passage is missing or occurs more than once, nothing is changed and the reason is given."
    ),
    W.ARTIFACT_UPDATE: (
        "Changes what an artifact is rather than its text: its title, whether it is a draft or final, its kind, its tags and the "
        "records it is about. Only the fields given change; the text and its versions stay as they are."
    ),
    W.ARTIFACT_LIST: (
        "Lists the library: every artifact matching the words of the query in its title or text, and the filters given, with its "
        "kind, format, status, language, version, length, tags and subjects."
    ),
    W.PLAN_CREATE: (
        "Writes a plan: an ordered list of the Creator's acts, each checked against the act's input fields, kept with its own artifact. "
        "Nothing in the world changes while planning; the plan runs only when the player approves it and executes it. A step may also "
        "change a rule of the world with the reserved acts rule:set (namespace, name, value) and rule:reset (namespace, name); "
        "search_rules and read_rule give a rule's name and range."
    ),
    W.PLAN_READ: "Reads a plan with every step: its act, input, what it declares, what it waits for, its state, ledger entry and outcome.",
    W.PLAN_REVISE: (
        "Replaces the steps of a plan with a new list. Steps already done, skipped or undone keep their place, act and input. A revised "
        "plan waits for the player's approval again; a running plan stops after its current step."
    ),
    W.FORECAST_ESTIMATE: "Says how long a forecast of a number of epochs should take, from how long the engine took for the last epoch.",
    W.FORECAST_RUN: (
        "Foresees the world: copies it twice, performs the interventions on one copy only, then lives both copies the same number of "
        "epochs through the engine alone and compares them. The world itself does not change. Acts that run as jobs need the language "
        "model and cannot be interventions. A rule of the world can be changed on the copy with the reserved acts rule:set "
        "(namespace, name, value) and rule:reset (namespace, name)."
    ),
    W.FORECAST_READ: (
        "Reads a forecast. While it still runs, the read waits for its end, up to three times its estimate and at most ten minutes, "
        "so one read is enough; once done it gives the comparison of both copies, population, prosperity, communities, wars, deaths "
        "by flow, every node the interventions touched, and the chronicle each copy wrote."
    ),
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    W.ARTIFACT_CREATE: {
        "title": "The artifact's title, in the artifact's language.",
        "kind": "What the work is.",
        "format": "markdown for prose, fountain for a screenplay, html for a page with its own layout.",
        "body": "The whole text of the artifact.",
        "language": "The language the artifact is written in, the one the player chose for it; the player's own language when they chose none.",
        "tags": "Short labels the player can filter the library by.",
        "node_ids": "The ids of the nodes the artifact is about.",
        "status": "draft while the work goes on, final when the player calls it finished.",
    },
    W.ARTIFACT_READ: {
        "artifact_id": "The artifact's id, as artifact_list gives it.",
        "version": "An earlier version to read; leave it out for the current one.",
        "page": PAGE_FIELD,
    },
    W.ARTIFACT_UPDATE: {
        "artifact_id": "The artifact's id, as artifact_list gives it.",
        "title": "A new title; leave it out to keep the title.",
        "status": "draft or final; leave it out to keep the status.",
        "kind": "A new kind; leave it out to keep the kind.",
        "tags": "The whole new list of tags; leave it out to keep the tags.",
        "node_ids": "The whole new list of records the artifact is about; leave it out to keep them.",
    },
    W.ARTIFACT_EDIT: {
        "artifact_id": "The artifact's id, as artifact_list gives it.",
        "edits": "The changes in order; each holds exactly one of replace, insert_after, append or rewrite, and each keeps a new version.",
        "edits.replace": "Replaces one passage.",
        "edits.replace.old": "The passage to replace, copied exactly from the current text; it must occur once.",
        "edits.replace.new": "The text that takes its place.",
        "edits.insert_after": "Inserts text after one passage.",
        "edits.insert_after.anchor": "The passage to insert after, copied exactly from the current text; it must occur once.",
        "edits.insert_after.text": "The text to insert, with the line breaks it needs.",
        "edits.append": "Text to add after the end, as a new paragraph.",
        "edits.rewrite": "The whole new text, replacing all of it.",
        "summary": "A short note of what the change does, kept with each new version.",
    },
    W.ARTIFACT_LIST: {
        "q": "Words to find in the title or text; leave it empty to list everything.",
        "kind": "Only artifacts of this kind.",
        "status": "Only drafts, or only final works.",
        "format": "Only artifacts of this format.",
        "language": "Only artifacts written in this language.",
        "mode": "Only artifacts written in this mode.",
        "tag": "Only artifacts carrying this tag.",
        "node_id": "Only artifacts about this node.",
        "sort": "relevance (with a query), updated, created, title or length; newest first when left out.",
        "page": PAGE_FIELD,
    },
    W.PLAN_CREATE: {"title": "The plan's title, in the player's language.", **STEP_FIELDS},
    W.PLAN_READ: {"plan_id": "The plan's id.", "page": PAGE_FIELD},
    W.PLAN_REVISE: {"plan_id": "The plan's id.", "title": "A new title; leave it empty to keep the title.", **STEP_FIELDS},
    W.FORECAST_ESTIMATE: {"epochs": "How many epochs the forecast would live, at most the rule divine_will.forecast_max_epochs."},
    W.FORECAST_RUN: {
        "epochs": "How many epochs both copies live, at most the rule divine_will.forecast_max_epochs.",
        "interventions": "The acts to perform on the changed copy, in order; leave it empty to foresee the world as it goes.",
        "interventions.action_id": "The id of the act, as search_actions lists it.",
        "interventions.input": "The act's input fields as describe_action lists them, by name.",
    },
    W.FORECAST_READ: {"forecast_id": "The forecast's id, as forecast_run gives it.", "page": PAGE_FIELD},
}
