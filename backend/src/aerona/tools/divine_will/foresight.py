import asyncio
import time
from typing import Any

from pydantic import Field

from aerona.core.errors import AeronaError
from aerona.core.grammar import several, spoken
from aerona.domain.enums.divine_will import ForecastStatus
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.tools.divine_will.framework import PagedInput, Toolset, WillCall, WillResult, WillTool
from aerona.tools.divine_will.library_ports import FlowDeaths, ForecastReport, ForecastView, Intervention, ScenarioOutcome, TouchedNode, library_of
from aerona.tools.divine_will.paging import failed, paged
from aerona.tools.framework.inputs import ToolInput

W = DivineWillToolId
FORESEEING = frozenset({Toolset.FORESIGHT})
WITHOUT = "without the interventions"
WITH = "with the interventions"


class ForecastEstimateInput(ToolInput):
    epochs: int = Field(ge=1)


class ForecastRunInput(ToolInput):
    epochs: int = Field(ge=1)
    interventions: list[Intervention] = Field(default_factory=list)


WAITING = frozenset({ForecastStatus.QUEUED, ForecastStatus.RUNNING})
POLL_SECONDS = 2.0
WAIT_FACTOR = 3
SHORTEST_WAIT = 60
LONGEST_WAIT = 600


class ForecastReadInput(PagedInput):
    forecast_id: int = Field(ge=1)


def timed(seconds: float) -> str:
    return several(round(seconds), "second", "seconds")


def deaths_text(deaths: list[FlowDeaths]) -> str:
    return ", ".join(f"{spoken(item.category)} {item.deaths}" for item in deaths) or "none"


def node_text(node_id: int, before: TouchedNode | None, after: TouchedNode | None) -> str:
    found = after or before
    name = found.name if found is not None and found.name else f"node {node_id}"
    parts: list[str] = []
    for label, node in ((WITHOUT, before), (WITH, after)):
        if node is None or not node.exists:
            parts.append(f"{label}: gone")
            continue
        stats = ", ".join(f"{key} {value}" for key, value in sorted(node.stats.items()))
        status = f"status {spoken(node.status)}" if node.status is not None else "no status"
        parts.append(f"{label}: {status}{'; ' + stats if stats else ''}")
    return f"{name} (node {node_id}) — " + " | ".join(parts)


def compare(label: str, start: float, baseline: float, intervened: float) -> str:
    difference = round(intervened - baseline, 2)
    sign = "+" if difference > 0 else ""
    return f"{label}: {start} at the start; {baseline} {WITHOUT}; {intervened} {WITH} ({sign}{difference})"


def outcome_lines(report: ForecastReport) -> list[str]:
    base, changed = report.baseline, report.intervened
    lines = [
        f"Lived epochs {report.start_epoch} to {report.end_epoch} on two copies in {several(round(report.seconds), 'second', 'seconds')}.",
        *(
            f"Intervention {number}: {item.action_title} ({item.action_id}) — {item.message} Essence spent: {item.essence_spent}."
            for number, item in enumerate(report.interventions, start=1)
        ),
        compare("Population", report.start_population, base.population, changed.population),
        compare("Prosperity", report.start_prosperity, base.prosperity, changed.prosperity),
        compare("Communities", report.start_communities, base.communities, changed.communities),
        compare("Wars under way", report.start_wars, base.wars.ongoing, changed.wars.ongoing),
        f"Wars begun: {base.wars.begun} {WITHOUT}; {changed.wars.begun} {WITH}. Wars ended: {base.wars.ended} {WITHOUT}; {changed.wars.ended} {WITH}.",
        f"Deaths by flow {WITHOUT}: {deaths_text(base.deaths)}.",
        f"Deaths by flow {WITH}: {deaths_text(changed.deaths)}.",
    ]
    before = {node.node_id: node for node in base.nodes}
    after = {node.node_id: node for node in changed.nodes}
    lines.extend(node_text(node_id, before.get(node_id), after.get(node_id)) for node_id in sorted(before.keys() | after.keys()))
    lines.extend(chronicle_lines(WITHOUT, base))
    lines.extend(chronicle_lines(WITH, changed))
    return lines


def chronicle_lines(label: str, outcome: ScenarioOutcome) -> list[str]:
    head = f"Chronicle {label}: {several(len(outcome.chronicle), 'line', 'lines')}."
    return [head, *(f"[{label}] epoch {line.epoch}{f', year {line.year}' if line.year is not None else ''}: {line.text}" for line in outcome.chronicle)]


def forecast_head(view: ForecastView) -> str:
    lines = [
        f"forecast {view.id}: {spoken(view.status)}, {several(view.epochs, 'epoch', 'epochs')}, "
        f"{several(len(view.interventions), 'intervention', 'interventions')}, estimated {several(view.eta_seconds, 'second', 'seconds')}"
    ]
    if view.report is None:
        lines.append(f"Epochs lived on both copies so far: {view.epochs_done} of {view.epochs}.")
    if view.error:
        lines.append(f"It stopped: {view.error}")
    if view.status is ForecastStatus.CANCELLED:
        lines.append("The player cancelled it. Do not run it again unless the player asks; say it was cancelled and offer to run it.")
    return "\n".join(lines)


async def estimate_forecast(call: WillCall, query: ForecastEstimateInput) -> WillResult:
    try:
        found = await library_of(call).foresight.estimate(query.epochs, call.rules)
    except AeronaError as error:
        return failed(error.message)
    if found.measured_epoch is not None:
        basis = f"the engine took {timed(found.seconds_per_epoch)} for epoch {found.measured_epoch}"
    elif found.from_forecast_id is not None:
        basis = f"forecast {found.from_forecast_id} took {timed(found.seconds_per_epoch)} an epoch"
    else:
        basis = f"no epoch has been timed yet, so it reckons {timed(found.seconds_per_epoch)} an epoch"
    return WillResult(
        text=(
            f"A forecast of {several(found.epochs, 'epoch', 'epochs')} should take about "
            f"{several(found.eta_seconds, 'second', 'seconds')}: {basis}, with a margin."
        ),
        payload={"eta_seconds": found.eta_seconds},
    )


async def run_forecast(call: WillCall, query: ForecastRunInput) -> WillResult:
    try:
        view = await library_of(call).foresight.run(query.interventions, query.epochs, cycle_id=call.cycle_id, rules=call.rules)
    except AeronaError as error:
        return failed(error.message)
    return WillResult(
        text=(
            f"Started {forecast_head(view)} It lives two copies of the world, one with the interventions and one without, "
            "and changes nothing in the world itself. Read it with forecast_read once it is done."
        ),
        payload={"forecast_id": view.id, "eta_seconds": view.eta_seconds},
    )


async def finished_forecast(call: WillCall, forecast_id: int) -> ForecastView:
    foresight = library_of(call).foresight
    view = await foresight.read(forecast_id)
    deadline = time.monotonic() + min(LONGEST_WAIT, max(SHORTEST_WAIT, view.eta_seconds * WAIT_FACTOR))
    while view.status in WAITING and time.monotonic() < deadline:
        await asyncio.sleep(POLL_SECONDS)
        view = await foresight.read(forecast_id)
    return view


async def read_forecast(call: WillCall, query: ForecastReadInput) -> WillResult:
    try:
        view = await finished_forecast(call, query.forecast_id)
    except AeronaError as error:
        return failed(error.message)
    lines = outcome_lines(view.report) if view.report is not None else []
    return await paged(call, W.FORECAST_READ, query, lines, head=forecast_head(view), empty="It has no report yet.")


def tools() -> list[WillTool[Any]]:
    return [
        WillTool(W.FORECAST_ESTIMATE, FORESEEING, ForecastEstimateInput, estimate_forecast),
        WillTool(W.FORECAST_RUN, FORESEEING, ForecastRunInput, run_forecast),
        WillTool(W.FORECAST_READ, FORESEEING, ForecastReadInput, read_forecast),
    ]
