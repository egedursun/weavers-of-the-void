import json
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import Field, ValidationError
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.divine_will import DivineWillConfirmationRow
from aerona.db.tables.ledger import LedgerChangeRow
from aerona.domain.enums.divine_will import ConfirmationReason
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.model import RuleDescriptor
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool
from aerona.tools.divine_will.lexical import ranked
from aerona.tools.divine_will.paging import failed, paged, paged_hits, plain
from aerona.tools.divine_will.ports import ActionCard, RuleDeskPort, action_desk
from aerona.tools.divine_will.rows import change_text, names_for
from aerona.tools.framework.inputs import ToolInput

W = DivineWillToolId
CATALOG = frozenset({Toolset.ACT, Toolset.CATALOG_READ})
ACTING = frozenset({Toolset.ACT})
NEAREST = 5
TITLE_WEIGHT = 4
ID_WEIGHT = 4
GROUP_WEIGHT = 2
FIELD_WEIGHT = 1
ID_SUFFIX = "_id"
GENERIC_EDITORS = frozenset({"entity:stat", "record_row:edit"})
GENERIC_NOTE = "Fields this act does not take may still be set: a thing's stats with entity:stat, any value of a record of a thing with record_row:edit."


class SearchActionsInput(PagedInput):
    query: str = Field(default="", max_length=300)
    group: str = Field(default="", max_length=60)


class DescribeActionInput(PagedInput):
    action_id: str = Field(min_length=1, max_length=120)


class PerformActionInput(ToolInput):
    action_id: str = Field(min_length=1, max_length=120)
    input: dict[str, Any] = Field(default_factory=dict)


class JobStatusInput(ToolInput):
    job_id: str = Field(min_length=1, max_length=64)


class SetRuleInput(ToolInput):
    namespace: str
    name: str
    value: float


class ResetRuleInput(ToolInput):
    namespace: str
    name: str


class UndoActionInput(ToolInput):
    ledger_entry_id: int = Field(ge=1)


def cards_of(call: WillCall) -> Sequence[ActionCard]:
    return action_desk(call).cards(call.rules)


def card_of(call: WillCall, action_id: str) -> ActionCard | None:
    return next((card for card in cards_of(call) if card.id == action_id), None)


def field_names(card: ActionCard) -> str:
    return " ".join([*card.input_model.model_fields, *(word for words in card.accepts.values() for word in words)])


def search_fields(card: ActionCard) -> list[tuple[str, int]]:
    return [(card.title, TITLE_WEIGHT), (card.id, ID_WEIGHT), (card.group, GROUP_WEIGHT), (field_names(card), FIELD_WEIGHT), (card.cost, FIELD_WEIGHT)]


def runs_as(card: ActionCard) -> str:
    return "runs as a job" if card.is_job else "acts at once"


def card_line(card: ActionCard) -> str:
    word = f" · confirmation word {card.confirmation}" if card.confirmation else ""
    return f"- {card.id} · {card.title} · group {card.group} · {runs_as(card)} · cost: {card.cost}{word}"


def unknown_action(call: WillCall, action_id: str) -> WillResult:
    near = ranked(action_id, cards_of(call), search_fields)[:NEAREST]
    hint = f" Nearest: {', '.join(card.id for card in near)}." if near else ""
    return failed(f"There is no action {action_id}.{hint} Find actions with search_actions.")


async def search_actions(call: WillCall, query: SearchActionsInput) -> WillResult:
    cards = list(cards_of(call))
    if query.group:
        groups = sorted({card.group for card in cards})
        if query.group not in groups:
            return failed(f"No group called {query.group}. Groups: {', '.join(groups)}.")
        cards = [card for card in cards if card.group == query.group]
    hits = [card_line(card) for card in ranked(query.query, cards, search_fields)]
    return await paged_hits(call, W.SEARCH_ACTIONS, query, hits, empty="No action matches. Try other words or leave the query empty to list a group.")


def type_text(node: Mapping[str, Any]) -> str:
    if "enum" in node:
        return "one of " + ", ".join(str(item) for item in node["enum"])
    if "$ref" in node:
        return str(node["$ref"]).rsplit("/", 1)[-1]
    if "anyOf" in node:
        return " or ".join(type_text(item) for item in node["anyOf"] if isinstance(item, Mapping))
    if node.get("type") == "array" and isinstance(node.get("items"), Mapping):
        return f"list of {type_text(node['items'])}"
    return str(node.get("type", "any"))


LIMITS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems", "maxItems", "pattern")


def field_line(name: str, node: Mapping[str, Any], required: bool) -> str:
    parts = [f"- {name}: {type_text(node)}", "required" if required else f"optional, default {json.dumps(node.get('default'), ensure_ascii=False)}"]
    parts += [f"{limit} {node[limit]}" for limit in LIMITS if limit in node]
    if node.get("description"):
        parts.append(str(node["description"]))
    return " · ".join(parts)


def schema_lines(card: ActionCard) -> list[str]:
    schema = card.schema()
    required = set(schema.get("required", []))
    properties: Mapping[str, Any] = schema.get("properties", {})
    lines = [
        f"# {card.id} · {card.title}",
        f"group {card.group} · {runs_as(card)} · cost: {card.cost}",
    ]
    if card.confirmation:
        lines.append(f"The player confirms this act with the word {card.confirmation}; it always asks first.")
    if card.id not in GENERIC_EDITORS and any(name.endswith(ID_SUFFIX) for name in properties):
        lines.append(GENERIC_NOTE)
    lines.append("## Input fields" if properties else "## Input\nThis action takes no input.")
    lines += [field_line(name, node, name in required) for name, node in properties.items() if isinstance(node, Mapping)]
    lines += [f"- {name} takes one of: {', '.join(words)}" for name, words in card.accepts.items()]
    for name, definition in schema.get("$defs", {}).items():
        if not isinstance(definition, Mapping):
            continue
        inner = set(definition.get("required", []))
        nested = definition.get("properties", {})
        lines.append(f"## {name}" + ("" if nested else f": {type_text(definition)}"))
        lines += [field_line(key, node, key in inner) for key, node in nested.items() if isinstance(node, Mapping)]
    lines.append("## JSON schema\n" + json.dumps(schema, ensure_ascii=False, indent=1))
    return lines


async def describe_action(call: WillCall, query: DescribeActionInput) -> WillResult:
    card = card_of(call, query.action_id)
    if card is None:
        return unknown_action(call, query.action_id)
    return await paged(call, W.DESCRIBE_ACTION, query, schema_lines(card), empty="")


def refused(raw: Mapping[str, Any]) -> WillResult:
    text = str(raw.get("error") or "The act was refused.")
    if raw.get("busy"):
        return failed(f"{text} Wait for the epoch to finish, or tell the player the act waits.")
    return failed(text)


def reason_of(call: WillCall, card: ActionCard, preview: Mapping[str, Any]) -> ConfirmationReason | None:
    destructive = bool(preview.get("deleted_nodes") or preview.get("deleted_records") or preview.get("ended")) or card.confirmation is not None
    essence = preview.get("essence") or 0
    costly = isinstance(essence, int | float) and essence >= call.rules.divine_will.costly_essence
    if destructive and costly:
        return ConfirmationReason.BOTH
    if destructive:
        return ConfirmationReason.DESTRUCTIVE
    return ConfirmationReason.COSTLY if costly else None


def preview_lines(preview: Mapping[str, Any]) -> list[str]:
    lines = [f"essence: {plain(preview.get('essence') or 0)}"]
    for label, key in (("deletes node", "deleted_nodes"), ("deletes record", "deleted_records"), ("ends", "ended")):
        for item in preview.get(key) or ():
            if isinstance(item, Mapping):
                named = item.get("name") or item.get("node_name") or ""
                where = item.get("key") or item.get("node_id") or ""
                lines.append(f"- {label} {named} {item.get('table') or ''} {where}".rstrip())
    for tally in preview.get("tallies") or ():
        if isinstance(tally, Mapping):
            lines.append(f"- {tally.get('operation')} {tally.get('table')}: {tally.get('count')}")
    return lines


async def ask_first(call: WillCall, card: ActionCard, payload: dict[str, Any], preview: Mapping[str, Any], reason: ConfirmationReason) -> WillResult:
    async with call.database.write() as session:
        row = DivineWillConfirmationRow(cycle_id=call.cycle_id, action_id=card.id, input=payload, reason=reason, preview=dict(preview))
        session.add(row)
        await session.flush()
        confirmation_id = row.id
    why = {
        ConfirmationReason.DESTRUCTIVE: "it deletes or ends something",
        ConfirmationReason.COSTLY: "it spends much essence",
        ConfirmationReason.BOTH: "it deletes or ends something and spends much essence",
    }[reason]
    lines = [f"{card.title} waits for the player's approval because {why}. The rehearsal changed nothing; this is what it would do:", *preview_lines(preview)]
    lines.append("Tell the player what waits and end the turn; the act runs if the player approves.")
    return WillResult(
        text="\n".join(lines),
        pause=True,
        payload={"confirmation_id": confirmation_id, "action_id": card.id, "reason": reason.value, "preview": dict(preview)},
    )


async def outcome_lines(call: WillCall, outcome: Mapping[str, Any]) -> list[str]:
    lines = [str(outcome.get("message") or "Done.")]
    spent, gained = outcome.get("essence") or 0, outcome.get("essence_gained") or 0
    if spent or gained:
        lines.append(f"essence spent {plain(spent)} · gained {plain(gained)}")
    entry = outcome.get("ledger_entry_id")
    created = [item for item in outcome.get("created_ids") or () if isinstance(item, int)]
    async with call.database.read() as session:
        names = await names_for(session, created)
        changes = list(await session.scalars(select(LedgerChangeRow).where(LedgerChangeRow.entry_id == entry).order_by(LedgerChangeRow.id))) if entry else []
    if created:
        lines.append("created: " + ", ".join(f"{names.get(item, 'unnamed')} (node {item})" for item in created))
    if outcome.get("job_id"):
        lines.append(f"running as job {outcome['job_id']}; follow it with job_status.")
    if entry:
        lines.append(f"ledger entry {entry}; undo it with undo_action. {several(len(changes), 'change', 'changes')}:")
        lines += [change_text(change) for change in changes]
    return lines


async def perform_action(call: WillCall, query: PerformActionInput) -> WillResult:
    card = card_of(call, query.action_id)
    if card is None:
        return unknown_action(call, query.action_id)
    try:
        card.input_model.model_validate(query.input)
    except ValidationError as error:
        return failed(f"The input does not fit {card.id}: {error.errors(include_url=False)}. Read its fields with describe_action.")
    payload = dict(query.input)
    preview = await call.player.preview(card.id, payload)
    if not preview.get("ok", True):
        return refused(preview)
    reason = reason_of(call, card, preview)
    if reason is not None:
        return await ask_first(call, card, payload, preview, reason)
    outcome = await call.player.perform(card.id, payload)
    if not outcome.get("ok", True):
        return refused(outcome)
    return WillResult(
        text="\n".join(await outcome_lines(call, outcome)),
        payload={
            "action_id": card.id,
            "ledger_entry_id": outcome.get("ledger_entry_id"),
            "job_id": outcome.get("job_id") or "",
            "essence": outcome.get("essence") or 0,
            "created_ids": list(outcome.get("created_ids") or ()),
        },
    )


async def job_status(call: WillCall, query: JobStatusInput) -> WillResult:
    found = await call.player.job(query.job_id)
    if not found.get("ok", True):
        return refused(found)
    lines = [f"job {query.job_id}"] + [
        f"{key}: {plain(value)}" for key, value in sorted(found.items()) if key not in ("ok", "busy", "job_id") and value not in ("", None)
    ]
    return WillResult(text="\n".join(lines), payload={"job_id": query.job_id, "status": str(found.get("status") or "")})


async def undo_action(call: WillCall, query: UndoActionInput) -> WillResult:
    result = await call.player.undo(query.ledger_entry_id)
    if not result.get("ok", True):
        return refused(result)
    applied = [str(item) for item in result.get("applied") or ()]
    conflicts = [str(item) for item in result.get("conflicts") or ()]
    lines = [f"Ledger entry {query.ledger_entry_id} is undone: {several(len(applied), 'change', 'changes')} reversed."]
    lines += [f"- reversed {item}" for item in applied]
    if conflicts:
        lines.append(f"{several(len(conflicts), 'change', 'changes')} could not be reversed:")
        lines += [f"- kept {item}" for item in conflicts]
    return WillResult(text="\n".join(lines), payload={"ledger_entry_id": query.ledger_entry_id, "applied": applied, "conflicts": conflicts})


def rule_line(descriptor: RuleDescriptor) -> str:
    bounds = f"default {plain(descriptor.default)}, from {plain(descriptor.minimum)} to {plain(descriptor.maximum)}"
    return f"{descriptor.namespace}.{descriptor.key} = {plain(descriptor.value)} ({bounds}): {descriptor.label}"


async def change_rule(call: WillCall, namespace: str, name: str, value: float | None) -> WillResult:
    desk: RuleDeskPort = call.services.rule_desk
    before = desk.find(namespace, name)
    if before is None:
        return failed(f"There is no rule {namespace}.{name}; search_rules finds rules by their words.")
    try:
        after = await desk.change(namespace, name, value)
    except (ValidationFailedError, NotFoundError) as error:
        return failed(str(error))
    undo = f"set_rule with value {plain(before.value)}" if before.value != before.default else f"reset_rule on {namespace}.{name}"
    lines = [f"The rule {namespace}.{name} changed from {plain(before.value)} to {plain(after.value)}.", rule_line(after), f"To go back, use {undo}."]
    return WillResult(
        text="\n".join(lines),
        payload={"rule": f"{namespace}.{name}", "before": plain(before.value), "after": plain(after.value), "default": plain(after.default)},
    )


async def set_rule(call: WillCall, query: SetRuleInput) -> WillResult:
    return await change_rule(call, query.namespace, query.name, query.value)


async def reset_rule(call: WillCall, query: ResetRuleInput) -> WillResult:
    return await change_rule(call, query.namespace, query.name, None)


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.SEARCH_ACTIONS, CATALOG, SearchActionsInput, search_actions),
        WillTool(W.DESCRIBE_ACTION, CATALOG, DescribeActionInput, describe_action),
        WillTool(W.PERFORM_ACTION, ACTING, PerformActionInput, perform_action),
        WillTool(W.JOB_STATUS, ACTING, JobStatusInput, job_status),
        WillTool(W.UNDO_ACTION, ACTING, UndoActionInput, undo_action),
        WillTool(W.SET_RULE, ACTING, SetRuleInput, set_rule),
        WillTool(W.RESET_RULE, ACTING, ResetRuleInput, reset_rule),
    ]
