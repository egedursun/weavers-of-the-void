from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.storylets import STORYLETS
from aerona.catalog.vehicles import FRAMES
from aerona.constants.units import PERCENT
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.collective import StoryletRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance, CollectiveTrigger, DesignComponentKind, StoryletStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.collective.accounts import HistoryTally, record, strike
from aerona.engine.collective.book import shift
from aerona.engine.collective.crowds import stir
from aerona.engine.collective.designs import FULL_SIZE, draw_design, frame_sizes
from aerona.engine.collective.storylets import StoryletTally, cast_of, names, resolve
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.vehicles.fleet import opened
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

MAX_CHOICE = 3
MAX_NAMED = 8
EMPHASIS = 2
SLANT_COST = 4


class StoryletChoiceInput(ToolInput):
    run_id: int
    choice: int = Field(ge=0, le=MAX_CHOICE)


class RouseInput(ToolInput):
    grievance: CollectiveTrigger


class AccountInput(ToolInput):
    collection_id: int
    praise_ids: list[int] = Field(default_factory=list, max_length=MAX_NAMED)
    blame_ids: list[int] = Field(default_factory=list, max_length=MAX_NAMED)


class StrikeInput(ToolInput):
    figure_id: int


class DesignInput(ToolInput):
    frame: VehicleFrame
    emphasis: DesignComponentKind


async def ruled_realm(call: MortalCall) -> int | None:
    return await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )


async def choose_storylet(call: MortalCall, args: StoryletChoiceInput) -> str:
    run = await call.session.get(StoryletRunRow, args.run_id)
    if run is None or run.chooser_node_id != call.me.id or run.status is not StoryletStatus.OPEN or run.opened_epoch > call.tick.epoch:
        fail(MortalResult.STORYLET_CHOICE_REFUSED, why="no such storylet waits for your choice")
    choices = STORYLETS[run.storylet].steps[run.step].choices
    if args.choice >= len(choices):
        fail(MortalResult.STORYLET_CHOICE_REFUSED, why=f"that storylet has only {several(len(choices), 'choice', 'choices')}")
    known = await names(call.session, cast_of(run))
    text = choices[args.choice].text.format(**known)
    await resolve(call.tick, run, args.choice, StoryletTally(), by="agent")
    await call.record("tools.mortal.choose_storylet", roles={IncidentRole.ACTOR: call.me.id}, facts={"storylet": run.storylet, "choice": text})
    return result(MortalResult.STORYLET_CHOSEN, choice=text)


async def rouse_crowd(call: MortalCall, args: RouseInput) -> str:
    town = await living_entity(call.session, call.me.location_id) if call.me.location_id is not None else None
    mood = await stir(call.tick, town.id if town is not None else None, args.grievance)
    if town is None or mood is None:
        fail(MortalResult.ROUSE_REFUSED, why="there is no town about you to rouse")
    shift(mood, "agitation", stat_or(call.me, "charisma", PERCENT // 2) / 2)
    call.target(town.id)
    await call.record(
        "tools.mortal.rouse_crowd",
        roles={IncidentRole.LEADER: call.me.id, IncidentRole.PLACE: town.id},
        facts={"grievance": args.grievance, "agitation": mood.agitation},
        place=town.id,
    )
    return result(MortalResult.CROWD_ROUSED, name=town.name, anger=mood.anger, anxiety=mood.anxiety, fervour=mood.fervour, agitation=mood.agitation)


async def commission_account(call: MortalCall, args: AccountInput) -> str:
    realm_id = await ruled_realm(call)
    realm = await call.session.get(EntityRow, realm_id) if realm_id is not None else None
    if realm is None or held(realm.id):
        fail(MortalResult.ACCOUNT_REFUSED, why="you rule no realm")
    event = await call.session.get(CollectionRow, args.collection_id)
    if event is None:
        fail(MortalResult.ACCOUNT_REFUSED, why="there is no such event")
    stances = {node: AccountStance.GLORIFY for node in args.praise_ids} | {node: AccountStance.VILIFY for node in args.blame_ids}
    known = {node for node in stances if await call.session.get(EntityRow, node) is not None}
    stances = {node: stance for node, stance in stances.items() if node in known}
    fidelity = call.tick.rules.historiography.official_fidelity - SLANT_COST * len(stances)
    written = await record(
        call.tick,
        realm,
        AccountKind.OFFICIAL_CHRONICLE,
        fidelity=fidelity,
        stances=stances,
        collection_id=event.id,
        medium=AccountMedium.BOOK,
        author_id=call.me.id,
    )
    if written is None:
        fail(MortalResult.ACCOUNT_REFUSED, why="the realm's records are held by a god")
    await call.record(
        "tools.mortal.commission_account",
        roles={IncidentRole.PATRON: call.me.id, IncidentRole.AUTHORITY: realm.id, IncidentRole.SUBJECT: sorted(stances)},
        facts={"event": event.name, "fidelity": written.fidelity},
    )
    return result(MortalResult.ACCOUNT_WRITTEN, name=event.name, fidelity=written.fidelity)


async def strike_memory(call: MortalCall, args: StrikeInput) -> str:
    realm_id = await ruled_realm(call)
    realm = await call.session.get(EntityRow, realm_id) if realm_id is not None else None
    figure = await call.session.get(EntityRow, args.figure_id)
    if realm is None:
        fail(MortalResult.STRIKE_REFUSED, why="you rule no realm")
    if figure is None or figure.id in {call.me.id, realm.id}:
        fail(MortalResult.STRIKE_REFUSED, why="there is no such figure to strike")
    if await strike(call.tick, realm.id, figure.id, HistoryTally()) is None:
        fail(MortalResult.STRIKE_REFUSED, why="a god holds that memory fast")
    call.target(figure.id)
    await call.record("tools.mortal.strike_memory", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: figure.id, IncidentRole.AUTHORITY: realm.id})
    return result(MortalResult.MEMORY_STRUCK, name=figure.name)


async def design_owner(call: MortalCall) -> EntityRow | None:
    realm_id = await ruled_realm(call)
    if realm_id is None and call.me.location_id is not None:
        realm_id = await call.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == call.me.location_id).limit(1))
    owner_id = realm_id or call.me.location_id
    return await living_entity(call.session, owner_id) if owner_id is not None else None


async def draw_a_design(call: MortalCall, args: DesignInput) -> str:
    sizes = frame_sizes(args.frame)
    if args.emphasis not in sizes:
        fail(MortalResult.DESIGN_REFUSED, why=f"{an(FRAMES[args.frame].label.lower())} has no {spoken(args.emphasis)}")
    owner = await design_owner(call)
    if owner is None or held(owner.id):
        fail(MortalResult.DESIGN_REFUSED, why="you build for no town or realm")
    knowledge = await KnowledgeMap.load(call.session)
    if not opened(FRAMES[args.frame], knowledge, owner, call.rules):
        fail(
            MortalResult.DESIGN_REFUSED,
            why=f"{owner.name} cannot yet build {an(FRAMES[args.frame].label.lower())}: it lacks the knowledge or is too small a power for a hull that size",
        )
    sizes[args.emphasis] = min(FULL_SIZE, sizes[args.emphasis] + EMPHASIS)
    skill = stat_or(call.me, "intellect", PERCENT // 2)
    design = await draw_design(call.tick, owner, args.frame, sizes=sizes, quality=skill, designer_id=call.me.id, knowledge=knowledge)
    await call.record(
        "tools.mortal.draw_design",
        roles={IncidentRole.MAKER: call.me.id, IncidentRole.OWNER: owner.id, IncidentRole.PRODUCT: design.entity_id},
        facts={"frame": args.frame, "emphasis": args.emphasis, "quality": skill},
    )
    return result(
        MortalResult.DESIGN_DRAWN, name=design.name, speed=design.speed, reach=design.range, cargo=design.cargo, arms=design.armament, crew=design.crew
    )


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.CHOOSE_STORYLET, mortal, StoryletChoiceInput, meta, choose_storylet),
        ToolSpec(MortalToolId.ROUSE_CROWD, mortal, RouseInput, meta, rouse_crowd),
        ToolSpec(MortalToolId.COMMISSION_ACCOUNT, mortal, AccountInput, meta, commission_account),
        ToolSpec(MortalToolId.STRIKE_MEMORY, mortal, StrikeInput, meta, strike_memory),
        ToolSpec(MortalToolId.DRAW_DESIGN, mortal, DesignInput, meta, draw_a_design),
    ]
