from sqlalchemy import select

from aerona.catalog.life.leagues import APPLY_LEGACY_TREATY_KINDS, BINDING_TREATIES, TREATY_AIMS
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.polity import TreatyPartyRow, TreatyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leagues import LeagueVoteBasis
from aerona.domain.enums.polity import TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.leagues.book import LeagueTally, living_polity
from aerona.engine.leagues.founding import found_league
from aerona.engine.polity.signatories import realm_of_party

LEGACY_FIXUP = "leagues.legacy_coalitions"
BLOC_SIZE = 3


async def parties_of(ctx: TickContext, treaty_id: int) -> list[EntityRow]:
    found: dict[int, EntityRow] = {}
    for party in await ctx.session.scalars(
        select(TreatyPartyRow.party_node_id).where(TreatyPartyRow.treaty_entity_id == treaty_id).order_by(TreatyPartyRow.party_node_id)
    ):
        polity = await living_polity(ctx.session, await realm_of_party(ctx.session, party))
        if polity is not None and not held(polity.id):
            found.setdefault(polity.id, polity)
    return [found[key] for key in sorted(found)]


async def leagued(ctx: TickContext, polity_ids: list[int]) -> bool:
    query = select(LeagueMemberRow.league_entity_id).where(LeagueMemberRow.polity_entity_id.in_(polity_ids)).limit(1)
    return await ctx.session.scalar(query) is not None


async def from_treaty(ctx: TickContext, treaty: TreatyProfileRow, tally: LeagueTally) -> EntityRow | None:
    parties = await parties_of(ctx, treaty.treaty_entity_id)
    if len(parties) < ctx.rules.leagues.found_min_members or await leagued(ctx, [party.id for party in parties]):
        return None
    league = await found_league(ctx, parties, TREATY_AIMS[treaty.kind], LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, tally)
    profile = await ctx.session.get(PolityLeagueRow, league.id)
    if profile is not None:
        profile.charter_treaty_id = treaty.treaty_entity_id
    return league


async def apply_legacy(ctx: TickContext, tally: LeagueTally) -> None:
    if not await fixup_due(ctx.session, LEGACY_FIXUP):
        return
    query = select(TreatyProfileRow).where(TreatyProfileRow.kind.in_(APPLY_LEGACY_TREATY_KINDS), TreatyProfileRow.status == TreatyStatus.IN_FORCE)
    made = 0
    for treaty in list(await ctx.session.scalars(query.order_by(TreatyProfileRow.treaty_entity_id))):
        if await from_treaty(ctx, treaty, tally) is not None:
            made += 1
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"leagues": made}))
    await ctx.session.flush()


Bound = dict[frozenset[int], TreatyProfileRow]


async def binding_ties(ctx: TickContext, treaties: list[TreatyProfileRow]) -> Bound:
    ties: Bound = {}
    for treaty in treaties:
        parties = [party.id for party in await parties_of(ctx, treaty.treaty_entity_id)]
        for index, first in enumerate(parties):
            for second in parties[index + 1 :]:
                ties.setdefault(frozenset((first, second)), treaty)
    return ties


async def from_bloc(ctx: TickContext, ring: tuple[int, int, int], ties: Bound, tally: LeagueTally) -> EntityRow | None:
    polities = [polity for polity in [await living_polity(ctx.session, member) for member in ring] if polity is not None]
    if len(polities) < len(ring) or await leagued(ctx, list(ring)):
        return None
    charters = [ties[frozenset(pair)] for pair in ((ring[0], ring[1]), (ring[1], ring[2]), (ring[0], ring[2]))]
    aims = sorted({aim for charter in charters for aim in TREATY_AIMS[charter.kind]})
    league = await found_league(ctx, polities, aims, LeagueVoteBasis.ONE_MEMBER_ONE_VOTE, tally)
    profile = await ctx.session.get(PolityLeagueRow, league.id)
    if profile is not None:
        profile.charter_treaty_id = charters[0].treaty_entity_id
    return league


async def found_from_blocs(ctx: TickContext, ties: Bound, tally: LeagueTally) -> None:
    if ctx.rules.leagues.found_min_members > BLOC_SIZE:
        return
    partners: dict[int, set[int]] = {}
    for pair in ties:
        first, second = sorted(pair)
        partners.setdefault(first, set()).add(second)
        partners.setdefault(second, set()).add(first)
    for first in sorted(partners):
        for second, third in sorted((b, c) for b in partners[first] for c in partners[first] if first < b < c and c in partners.get(b, set())):
            if ctx.rng(f"leagues.bloc.{first}.{second}.{third}.{ctx.epoch}").chance(ctx.rules.leagues.found_chance_pct):
                await from_bloc(ctx, (first, second, third), ties, tally)


async def maybe_found(ctx: TickContext, tally: LeagueTally) -> None:
    query = select(TreatyProfileRow).where(TreatyProfileRow.kind.in_(list(BINDING_TREATIES)), TreatyProfileRow.status == TreatyStatus.IN_FORCE)
    standing: list[TreatyProfileRow] = []
    for treaty in list(await ctx.session.scalars(query.order_by(TreatyProfileRow.treaty_entity_id))):
        treaty_entity = await ctx.session.get(EntityRow, treaty.treaty_entity_id)
        if treaty_entity is None or treaty_entity.status is not EntityStatus.CANON or treaty_entity.entity_type is not EntityType.TREATY:
            continue
        standing.append(treaty)
        if ctx.rng(f"leagues.found.{treaty.treaty_entity_id}.{ctx.epoch}").chance(ctx.rules.leagues.found_chance_pct):
            await from_treaty(ctx, treaty, tally)
    await found_from_blocs(ctx, await binding_ties(ctx, standing), tally)
