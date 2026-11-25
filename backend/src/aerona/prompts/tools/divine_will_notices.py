from aerona.prompts.tools.divine_will_ids import DivineWillToolId

DESCRIPTIONS: dict[DivineWillToolId, str] = {
    DivineWillToolId.SUGGEST_MODE: (
        "Shows the player a suggestion to switch to another mode, with the reason, when the request fits that mode better: a large or "
        "staged request is better as a plan, a question about the rules fits the mechanics guide. The player decides; do not act on "
        "the request in this turn."
    ),
}

FIELDS: dict[DivineWillToolId, dict[str, str]] = {
    DivineWillToolId.SUGGEST_MODE: {"mode": "The mode to suggest.", "reason": "Why that mode fits the request better, in the player's language."},
}
