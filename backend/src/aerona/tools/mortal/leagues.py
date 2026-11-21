from typing import Any

from pydantic import Field

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import PolityLeagueRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leagues import LeagueAim, LeagueDecisionKind, LeagueOrgan, LeagueStanding, LeagueVoteBasis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.leagues.book import LeagueTally, core_of, living_polity, membership, voters_of
from aerona.engine.leagues.decisions import propose, vote
from aerona.engine.leagues.founding import found_league
from aerona.engine.leagues.life import enemies_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

POLITIES_MAX = 20
AIMS_MAX = 9


class FoundLeagueInput(ToolInput):
    polity_ids: list[int] = Field(min_length=2, max_length=POLITIES_MAX)
    aims: list[LeagueAim] = Field(min_length=1, max_length=AIMS_MAX)
    vote_basis: LeagueVoteBasis


class JoinLeagueInput(ToolInput):
    league_id: int
    polity_id: int


class TableLeagueMotionInput(ToolInput):
    league_id: int
    organ: LeagueOrgan
    kind: LeagueDecisionKind
    subject_id: int | None = None


async def ruled_polity(call: MortalCall, polity_id: int) -> EntityRow:
    polity = await living_polity(call.session, polity_id)
    if polity is None or not await controls(call, polity.id):
        fail(MortalResult.LEAGUE_REFUSED, why="only the ruler of a realm speaks for it")
    if held(polity.id):
        fail(MortalResult.LEAGUE_REFUSED, why="a god holds that realm as it is")
    return polity


async def league_of(call: MortalCall, league_id: int) -> tuple[EntityRow, PolityLeagueRow]:
    league = await call.session.get(EntityRow, league_id)
    profile = await call.session.get(PolityLeagueRow, league_id)
    if league is None or profile is None or league.entity_type is not EntityType.LEAGUE or league.status is not EntityStatus.CANON:
        fail(MortalResult.LEAGUE_REFUSED, why="there is no such league")
    if held(league.id):
        fail(MortalResult.LEAGUE_REFUSED, why="a god holds that league as it is")
    return league, profile


async def found_league_tool(call: MortalCall, args: FoundLeagueInput) -> str:
    ids = list(dict.fromkeys(args.polity_ids))
    mine = [polity_id for polity_id in ids if await controls(call, polity_id)]
    if not mine:
        fail(MortalResult.LEAGUE_REFUSED, why="a league is founded by the ruler of one of its realms")
    polities = [polity for polity in [await living_polity(call.session, polity_id) for polity_id in ids] if polity is not None and not held(polity.id)]
    if len(polities) < len(ids):
        fail(MortalResult.LEAGUE_REFUSED, why="every founder must be a living realm no god holds")
    cores = [await core_of(call.session, polity.id) for polity in polities]
    for core in cores:
        if core is not None and set(await enemies_of(call.tick, core)) & {other for other in cores if other is not None}:
            fail(MortalResult.LEAGUE_REFUSED, why="realms at war with each other do not found a league together")
    first = next(polity for polity in polities if polity.id == mine[0])
    ordered = [first, *[polity for polity in polities if polity.id != first.id]]
    league = await found_league(call.tick, ordered, list(dict.fromkeys(args.aims)), args.vote_basis, LeagueTally())
    call.target(league.id)
    return result(MortalResult.LEAGUE_FOUNDED, league=league.name, count=len(ordered), basis=spoken(args.vote_basis))


async def join_league_tool(call: MortalCall, args: JoinLeagueInput) -> str:
    league, profile = await league_of(call, args.league_id)
    polity = await ruled_polity(call, args.polity_id)
    found = await membership(call.session, league.id, polity.id)
    if found is not None and found.standing is not LeagueStanding.EXPELLED:
        fail(MortalResult.LEAGUE_REFUSED, why=f"{polity.name} already stands in it as {spoken(found.standing)}")
    decision = await propose(call.tick, profile, LeagueDecisionKind.ADMIT, LeagueOrgan.ASSEMBLY, subject=polity.id, proposer=polity.id)
    if decision is None:
        fail(MortalResult.LEAGUE_REFUSED, why="the league has no assembly to hear it")
    outcome = await vote(call.tick, profile, decision, LeagueTally())
    call.target(league.id)
    return result(MortalResult.LEAGUE_MOTION_DECIDED, kind=spoken(decision.kind), league=league.name, outcome=spoken(outcome))


async def speaker(call: MortalCall, league_id: int) -> int:
    for member in await voters_of(call.session, league_id):
        if await controls(call, member.polity_entity_id):
            return member.polity_entity_id
    fail(MortalResult.LEAGUE_REFUSED, why="only the ruler of a voting member lays a motion before the league")


async def table_league_motion_tool(call: MortalCall, args: TableLeagueMotionInput) -> str:
    league, profile = await league_of(call, args.league_id)
    proposer = await speaker(call, league.id)
    if args.organ.value not in (profile.organs or []):
        fail(MortalResult.LEAGUE_REFUSED, why=f"the league has no {spoken(args.organ)}")
    subject = await call.session.get(EntityRow, args.subject_id) if args.subject_id is not None else None
    if args.subject_id is not None and (subject is None or held(subject.id)):
        fail(MortalResult.LEAGUE_REFUSED, why="the subject must exist and no god may hold it")
    decision = await propose(call.tick, profile, args.kind, args.organ, subject=args.subject_id, proposer=proposer)
    if decision is None:
        fail(MortalResult.LEAGUE_REFUSED, why="the league has no organ to hear it")
    await call.record(
        "league.motion_tabled",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: league.id},
        facts={"kind": decision.kind, "organ": decision.organ},
    )
    outcome = await vote(call.tick, profile, decision, LeagueTally())
    call.target(league.id)
    return result(MortalResult.LEAGUE_MOTION_DECIDED, kind=spoken(decision.kind), league=league.name, outcome=spoken(outcome))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    rule = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FOUND_LEAGUE, AgentKind.MORTAL, FoundLeagueInput, rule, found_league_tool),
        ToolSpec(MortalToolId.JOIN_LEAGUE, AgentKind.MORTAL, JoinLeagueInput, rule, join_league_tool),
        ToolSpec(MortalToolId.TABLE_LEAGUE_MOTION, AgentKind.MORTAL, TableLeagueMotionInput, rule, table_league_motion_tool),
    ]
