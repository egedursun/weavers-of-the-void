from typing import Any

from sqlalchemy import select

from aerona.catalog.methods import METHODS, PROCESS_LABELS
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.industry import MethodKind
from aerona.engine.economy.book import EconomyBook
from aerona.engine.industry.methods import MethodTally, adopt, allowed
from aerona.engine.industry.owners import buy
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines


class MethodInput(ToolInput):
    method: MethodKind


class BuyInput(ToolInput):
    kind: WorkshopKind


async def works_of(call: MortalCall) -> EntityRow | None:
    if call.me.entity_type in SOCIETY_TYPES:
        return call.me
    for home_id in (call.me.affiliated_entity_id, call.me.location_id):
        home = await call.session.get(EntityRow, home_id) if home_id is not None else None
        if home is not None and home.entity_type in SOCIETY_TYPES:
            return home
    return None


async def choose_method(call: MortalCall, args: MethodInput) -> str:
    spec = METHODS[args.method]
    community = await works_of(call)
    if community is None:
        fail(MortalResult.METHOD_REFUSED, name=call.me.name, method=spec.label.lower(), why="you belong to no community with works")
    book = await EconomyBook.load(call.tick)
    row = book.methods.get(community.id, {}).get(spec.process)
    if row is not None and "method" in row.locked:
        fail(MortalResult.METHOD_REFUSED, name=community.name, method=spec.label.lower(), why="a god holds the way it is done")
    why = allowed(book, community, spec)
    if why is not None:
        fail(MortalResult.METHOD_REFUSED, name=community.name, method=spec.label.lower(), why=why)
    await adopt(call.tick, book, community, spec, MethodTally())
    call.target(community.id)
    await call.chronicle(
        ChronicleKind.PRODUCTION,
        lines.METHOD_CHOSEN,
        entity_ids=[call.me.id, community.id],
        me=call.me.name,
        method=spec.label.lower(),
        process=PROCESS_LABELS[spec.process].lower(),
    )
    return result(MortalResult.METHOD_CHOSEN, name=community.name, method=spec.label.lower(), process=PROCESS_LABELS[spec.process].lower())


async def buy_workshop(call: MortalCall, args: BuyInput) -> str:
    label = WORKSHOP_LABELS[args.kind].lower()
    community = await works_of(call)
    if community is None:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why="you belong to no community with works")
    workshop = await call.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == community.id, WorkshopRow.kind == args.kind))
    if workshop is None:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why=f"{community.name} has none")
    if workshop.held:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why="a god holds who owns it")
    price = await buy(call.tick, workshop, call.me.id)
    if price is None:
        fail(MortalResult.WORKSHOP_REFUSED, workshop=label, why="you own it already or cannot pay its price")
    call.target(community.id)
    await call.chronicle(
        ChronicleKind.TRADE, lines.WORKSHOP_BOUGHT, entity_ids=[call.me.id, community.id], me=call.me.name, workshop=label, place=community.name, price=price
    )
    return result(MortalResult.WORKSHOP_BOUGHT, workshop=label, place=community.name, price=price)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.BUY_WORKSHOP, AgentKind.MORTAL, BuyInput, ToolMeta(ActionKind.BARTER, mortal_standard_action), buy_workshop),
        ToolSpec(MortalToolId.CHOOSE_METHOD, AgentKind.MORTAL, MethodInput, ToolMeta(ActionKind.PRODUCE, mortal_standard_action), choose_method),
    ]
