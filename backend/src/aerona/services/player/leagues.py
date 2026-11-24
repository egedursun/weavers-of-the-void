from pydantic import Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leagues import LeagueAim, LeagueVoteBasis
from aerona.engine.leagues.book import LeagueTally, living_polity
from aerona.engine.leagues.founding import found_league
from aerona.engine.leagues.life import dissolve
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.services.player.shaping import Shaped, shape_after

PARTNERS_MAX = 20


class FoundLeague(Shaped):
    founder_id: int
    partner_ids: list[int] = Field(min_length=1, max_length=PARTNERS_MAX)
    aims: list[LeagueAim] = Field(min_length=1)
    vote_basis: LeagueVoteBasis = LeagueVoteBasis.ONE_MEMBER_ONE_VOTE
    seat_id: int | None = None


class LeagueTarget(Command):
    league_id: int


@player_action("league:found", ActionKind.EDIT_RECORD)
async def league_found(scope: PlayerScope, command: FoundLeague) -> Effect:
    ids = list(dict.fromkeys([command.founder_id, *command.partner_ids]))
    polities = [await living_polity(scope.session, polity_id) for polity_id in ids]
    realms = [polity for polity in polities if polity is not None]
    if len(realms) < len(ids):
        raise ValidationFailedError("Every founder of a league must be a living realm.")
    ctx = await scope.context("league_found")
    if len(realms) < ctx.rules.leagues.found_min_members:
        raise ValidationFailedError(f"A league needs at least {ctx.rules.leagues.found_min_members} realms.")
    league = await found_league(ctx, realms, list(dict.fromkeys(command.aims)), command.vote_basis, LeagueTally(), seat=command.seat_id)
    await shape_after(scope, league.id, command)
    return Effect(f"{league.name.capitalize()} stands.", league.id, created_ids=(league.id,))


@player_action("league:dissolve", ActionKind.EDIT_RECORD)
async def league_dissolve(scope: PlayerScope, command: LeagueTarget) -> Effect:
    league = await scope.session.get(EntityRow, command.league_id)
    if league is None or league.entity_type is not EntityType.LEAGUE:
        raise NotFoundError("There is no such league.")
    if league.status is not EntityStatus.CANON:
        raise ValidationFailedError("That league has already ended.")
    await dissolve(await scope.context("league_dissolve"), league, "the god dissolved it", LeagueTally())
    return Effect(f"{league.name.capitalize()} is dissolved.", league.id)
