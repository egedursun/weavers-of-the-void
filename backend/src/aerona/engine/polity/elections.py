from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import agree, several
from aerona.db.tables.affairs import CouncilSeatRow, ElectionRow
from aerona.db.tables.estates import EstateProfileRow, MovementProfileRow, MovementSupportRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.intrigue import HookDemand
from aerona.domain.enums.polity import DecisionRule, LawKind, OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.communication.opinion import approval_of
from aerona.engine.context import TickContext
from aerona.engine.intrigue.favours import hook_on, use_hook
from aerona.engine.mortal.justice import community_ruler
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.engine.regime.book import patron_pull

ALL = frozenset(SocialClass)
VOTERS: dict[str, frozenset[SocialClass]] = {
    "nobles": frozenset({SocialClass.NOBLE}),
    "landholders": frozenset({SocialClass.NOBLE, SocialClass.FARMER, SocialClass.MERCHANT}),
    "citizens": frozenset({SocialClass.NOBLE, SocialClass.MERCHANT, SocialClass.PROFESSIONAL, SocialClass.OFFICIAL, SocialClass.CITIZEN}),
    "free": frozenset(ALL - {SocialClass.SERF_OR_SLAVE, SocialClass.OUTCAST}),
    "all": ALL,
}
HOLDER = "holder_entity_id"


@dataclass
class ElectionTally:
    held_elections: int = 0
    seats: int = 0
    chancellors: int = 0


def voters_of(laws: LawBook, realm: Realm) -> frozenset[SocialClass]:
    for kind in (LawKind.FRANCHISE, LawKind.CONSTITUTION):
        value = laws.param(realm.entity.id, kind, "voters")
        if value is not None:
            return VOTERS.get(str(value), VOTERS["nobles"])
    return VOTERS["nobles"]


def electing(laws: LawBook, realm: Realm) -> bool:
    return realm.profile.decision_rule is DecisionRule.ASSEMBLY or laws.param(realm.entity.id, LawKind.SUCCESSION_RULE, "rule") == "elective"


async def candidates(ctx: TickContext, realm: Realm) -> tuple[dict[int, SocialClass], dict[int, int]]:
    estates = {
        row.faction_entity_id: row.social_class
        for row in await ctx.session.scalars(select(EstateProfileRow).where(EstateProfileRow.polity_entity_id == realm.entity.id))
        if not held(row.faction_entity_id)
    }
    parties = {
        row.faction_entity_id: row.support
        for row in await ctx.session.scalars(select(MovementProfileRow).where(MovementProfileRow.polity_entity_id == realm.entity.id))
        if not held(row.faction_entity_id)
    }
    return estates, parties


async def count_votes(ctx: TickContext, book: RealmBook, realm: Realm, voters: frozenset[SocialClass]) -> tuple[dict[int, float], int]:
    table = ctx.rules.affairs
    estates, parties = await candidates(ctx, realm)
    votes: dict[int, float] = {}
    enfranchised = 0.0
    people = 0.0
    for member in book.members(realm):
        weight = float(max(1, stat(member, "population") or 0))
        shares = await class_shares(ctx.session, ctx.rules, member.id)
        allowed = sum(share for social_class, share in shares.items() if social_class in voters) / PERCENT
        people += weight
        enfranchised += weight * allowed
        for estate_id, social_class in estates.items():
            if social_class in voters:
                estate = await ctx.session.get(EstateProfileRow, estate_id)
                loyalty = estate.loyalty if estate is not None else PERCENT // 2
                votes[estate_id] = votes.get(estate_id, 0.0) + weight * shares.get(social_class, 0.0) / PERCENT * table.estate_appeal_pct / PERCENT * (
                    1 + loyalty / PERCENT
                )
        for party_id in parties:
            backing = await ctx.session.get(MovementSupportRow, (party_id, member.id))
            if backing is not None:
                votes[party_id] = votes.get(party_id, 0.0) + weight * allowed * backing.share / PERCENT * table.party_appeal_pct / PERCENT
    await sway(ctx, book, realm, votes, voters)
    for profile in await ctx.session.scalars(select(FactionProfileRow).order_by(FactionProfileRow.faction_entity_id)):
        purse = int((profile.influence_over or {}).get(str(realm.entity.id), 0))
        if purse > 0 and not held(profile.faction_entity_id):
            votes[profile.faction_entity_id] = votes.get(profile.faction_entity_id, 0.0) + enfranchised * purse / PERCENT * table.purse_appeal_pct / PERCENT
    turnout = round(enfranchised / people * PERCENT) if people else 0
    return {holder: value for holder, value in votes.items() if value > 0}, turnout


async def sway(ctx: TickContext, book: RealmBook, realm: Realm, votes: dict[int, float], voters: frozenset[SocialClass]) -> None:
    table = ctx.rules.affairs
    for candidate in list(votes):
        leader = await ctx.session.scalar(
            select(FactionMembershipRow.mortal_entity_id)
            .where(FactionMembershipRow.faction_entity_id == candidate, FactionMembershipRow.rank == FactionRank.LEADER)
            .limit(1)
        )
        for member in book.members(realm):
            weight = float(max(1, stat(member, "population") or 0))
            shares = await class_shares(ctx.session, ctx.rules, member.id)
            allowed = sum(share for social_class, share in shares.items() if social_class in voters) / PERCENT
            approval = await approval_of(ctx, member.id, candidate)
            votes[candidate] = max(0.0, votes[candidate] + weight * allowed * approval / PERCENT * table.opinion_votes_pct / PERCENT)
            lord = await community_ruler(ctx.session, member.id)
            hook = await hook_on(ctx, leader, lord.id) if leader is not None and lord is not None else None
            if hook is not None and await use_hook(ctx, hook, HookDemand.VOTE):
                votes[candidate] += weight * allowed * table.hook_votes_pct / PERCENT
            pull = await patron_pull(ctx.session, ctx.rules, realm.entity.id, leader, lord.id if lord is not None else None)
            votes[candidate] += weight * allowed * pull * ctx.rules.clientelism.client_votes_pct / PERCENT


def apportion(votes: dict[int, float], seats: int) -> dict[int, int]:
    total = sum(votes.values())
    if total <= 0 or seats <= 0:
        return {}
    quotas = {holder: value / total * seats for holder, value in votes.items()}
    given = {holder: int(quota) for holder, quota in quotas.items()}
    left = seats - sum(given.values())
    for holder in sorted(quotas, key=lambda item: (-(quotas[item] - given[item]), item))[:left]:
        given[holder] += 1
    return {holder: count for holder, count in given.items() if count > 0}


async def seat(ctx: TickContext, realm: Realm, given: dict[int, int], votes: dict[int, float]) -> int:
    total = sum(votes.values()) or 1.0
    kept = {row.holder_node_id: row for row in await ctx.session.scalars(select(CouncilSeatRow).where(CouncilSeatRow.polity_entity_id == realm.entity.id))}
    for holder, row in kept.items():
        if not row.locked and holder not in given:
            await ctx.session.delete(row)
    for holder, count in given.items():
        found = kept.get(holder)
        if found is None:
            found = CouncilSeatRow(polity_entity_id=realm.entity.id, holder_node_id=holder, since_epoch=ctx.epoch)
            ctx.session.add(found)
        elif found.locked:
            continue
        found.seats, found.votes = count, round(votes.get(holder, 0.0) / total * PERCENT)
    await ctx.session.flush()
    return sum(given.values())


async def install(ctx: TickContext, realm: Realm, winner: int, tally: ElectionTally) -> None:
    office = realm.office(OfficeKind.CHANCELLOR)
    leader = await ctx.session.scalar(
        select(FactionMembershipRow.mortal_entity_id)
        .where(FactionMembershipRow.faction_entity_id == winner, FactionMembershipRow.rank == FactionRank.LEADER)
        .limit(1)
    )
    if office is None or leader is None or HOLDER in (office.locked or []) or held(leader) or office.holder_entity_id == leader:
        return
    office.holder_entity_id, office.since_epoch = leader, ctx.epoch
    tally.chancellors += 1


async def elect(ctx: TickContext, book: RealmBook, laws: LawBook, realm: Realm, tally: ElectionTally, *, force: bool = False) -> None:
    last = await ctx.session.scalar(
        select(ElectionRow.epoch).where(ElectionRow.polity_entity_id == realm.entity.id).order_by(ElectionRow.epoch.desc()).limit(1)
    )
    if not force and last is not None and ctx.epoch - last < ctx.rules.affairs.election_epochs:
        return
    votes, turnout = await count_votes(ctx, book, realm, voters_of(laws, realm))
    given = apportion(votes, ctx.rules.affairs.seats)
    winner = max(votes, key=lambda holder: (votes[holder], -holder)) if votes else None
    seats = await seat(ctx, realm, given, votes)
    total = sum(votes.values()) or 1.0
    ctx.session.add(
        ElectionRow(
            polity_entity_id=realm.entity.id,
            epoch=ctx.epoch,
            seats=seats,
            turnout=turnout,
            winner_node_id=winner,
            results={str(holder): round(value / total * PERCENT) for holder, value in votes.items()},
        )
    )
    tally.held_elections += 1
    tally.seats += seats
    if winner is not None:
        await install(ctx, realm, winner, tally)
    winner_name = book.entities[winner].name if winner is not None and winner in book.entities else "no one"
    await note(
        ctx,
        f"{realm.entity.name} went to the polls; {winner_name} carried the most votes, "
        f"and {several(seats, 'seat', 'seats')} {agree(seats, 'was', 'were')} filled.",
        key="affairs.election",
        ids=[realm.entity.id, *([winner] if winner is not None else [])],
        kind=ChronicleKind.CIVILIZATION,
    )


async def tend_elections(ctx: TickContext, tally: ElectionTally) -> None:
    book = await RealmBook.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if not held(realm.entity.id) and electing(laws, realm):
            await elect(ctx, book, laws, realm, tally)
