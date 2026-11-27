from collections import Counter
from collections.abc import Awaitable, Callable
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.factions import CLASS_OF_KIND
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.governance import OrgCliqueRow, OrgGovernanceRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.governance import CliqueAim, GoverningBody, HeadSelection, OrgStrategy
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of
from aerona.engine.governance.seats import members_of, seats_of, shares_of, sync_seats
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.maturity import of_age, of_age_among, of_age_query
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

HEAD_LOCK = "head_node_id"
STRATEGY_LOCK = "strategy"
TRUST_LOCK = "trust"


async def living(ctx: TickContext, node_id: int | None) -> EntityRow | None:
    found = await ctx.session.get(EntityRow, node_id) if node_id is not None else None
    return found if found is not None and found.status is EntityStatus.CANON else None


async def candidates(ctx: TickContext, row: OrgGovernanceRow) -> list[EntityRow]:
    ids = [member.mortal_entity_id for member in await members_of(ctx, row.org_node_id)]
    if row.decision_body is GoverningBody.SHAREHOLDERS_MEETING:
        ids += [holder for holder in await shares_of(ctx, row.org_node_id) if holder not in ids]
    found = [entity for entity in [await living(ctx, node) for node in ids] if entity is not None]
    pool = [entity for entity in found if not held(entity.id)]
    if row.head_selection is not HeadSelection.INHERITED:
        pool = await of_age_among(ctx.session, pool)
    return pool or await home_folk(ctx, row.org_node_id)


async def home_folk(ctx: TickContext, org_id: int) -> list[EntityRow]:
    org = await ctx.session.get(EntityRow, org_id)
    profile = await ctx.session.get(FactionProfileRow, org_id)
    home = (profile.home_entity_id if profile is not None else None) or (org.location_id if org is not None else None)
    if home is None:
        return []
    folk = [
        mortal
        for mortal in await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [home]), of_age_query())
            .order_by(EntityRow.id)
        )
        if not held(mortal.id)
    ]
    wanted = CLASS_OF_KIND.get(profile.kind) if profile is not None else None
    kin = [mortal for mortal in folk if wanted is not None and mortal.social_class is wanted]
    return kin or folk


def standing(entity: EntityRow) -> int:
    return stat_or(entity, "charisma", 0) + stat_or(entity, "intellect", 0) + stat_or(entity, "wisdom", 0)


async def clique_choice(ctx: TickContext, row: OrgGovernanceRow, member_id: int) -> int | None:
    for clique in await cliques_of(ctx, row.org_node_id):
        if clique.aim is CliqueAim.HEAD and member_id in (clique.members or []) and clique.aim_node_id is not None:
            return clique.aim_node_id
    return None


@memoized(OrgCliqueRow)
async def cliques_by_org(session: AsyncSession) -> dict[int, list[OrgCliqueRow]]:
    found: dict[int, list[OrgCliqueRow]] = {}
    for row in await session.scalars(select(OrgCliqueRow).order_by(OrgCliqueRow.org_node_id, OrgCliqueRow.id)):
        found.setdefault(row.org_node_id, []).append(row)
    return found


async def cliques_of(ctx: TickContext, org_id: int) -> list[OrgCliqueRow]:
    return list((await cliques_by_org(ctx.session)).get(org_id, []))


async def election(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow], by_body: bool) -> EntityRow | None:
    allowed = {entity.id: entity for entity in pool}
    favourite = max(pool, key=lambda entity: (standing(entity), -entity.id))
    tally: Counter[int] = Counter()
    voters = [(seat.member_node_id, seat.vote_weight) for seat in await seats_of(ctx, row.org_node_id)] if by_body else [(entity.id, 1) for entity in pool]
    for voter, weight in voters:
        choice = await clique_choice(ctx, row, voter)
        tally[choice if choice in allowed else favourite.id] += weight
    if not tally:
        return favourite
    winner = max(tally, key=lambda node: (tally[node], -node))
    return allowed.get(winner, favourite)


async def heir(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    if row.head_node_id is not None:
        children = {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.PARENT_OF], sources=[row.head_node_id])}
        heirs = [entity for entity in pool if entity.id in children]
        if heirs:
            return max(heirs, key=lambda entity: (stat_or(entity, "age", 0), -entity.id))
    return await eldest_member(ctx, row, pool)


async def eldest_member(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    joined = {member.mortal_entity_id: member.joined_epoch for member in await members_of(ctx, row.org_node_id)}
    return min(pool, key=lambda entity: (joined.get(entity.id, ctx.epoch), entity.id))


async def owner_choice(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    del ctx, row
    return max(pool, key=lambda entity: (stat_or(entity, "intellect", 0) + stat_or(entity, "charisma", 0), -entity.id))


async def richest(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    del row
    purses = {entity.id: await coin_of(ctx.session, ctx.rules, entity) for entity in pool}
    return max(pool, key=lambda entity: (purses[entity.id], -entity.id))


async def by_body(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    return await election(ctx, row, pool, by_body=True)


async def by_members(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    return await election(ctx, row, pool, by_body=False)


async def by_lot(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    return ctx.rng(f"governance.lot.{row.org_node_id}.{ctx.epoch}").pick(pool)


async def by_divination(ctx: TickContext, row: OrgGovernanceRow, pool: list[EntityRow]) -> EntityRow | None:
    return ctx.rng(f"governance.divination.{row.org_node_id}.{ctx.epoch}").weighted_by(pool, lambda entity: max(1, stat_or(entity, "wisdom", 0)))


type Chooser = Callable[[TickContext, OrgGovernanceRow, list[EntityRow]], Awaitable[EntityRow | None]]
CHOOSERS: MappingProxyType[HeadSelection, Chooser] = total(
    HeadSelection,
    {
        HeadSelection.APPOINTED_BY_OWNER: owner_choice,
        HeadSelection.ELECTED_BY_BODY: by_body,
        HeadSelection.ELECTED_BY_MEMBERS: by_members,
        HeadSelection.INHERITED: heir,
        HeadSelection.SENIORITY: eldest_member,
        HeadSelection.LOT: by_lot,
        HeadSelection.DIVINATION: by_divination,
        HeadSelection.PURCHASE: richest,
    },
)


async def chosen_head(ctx: TickContext, row: OrgGovernanceRow) -> EntityRow | None:
    pool = await candidates(ctx, row)
    return await CHOOSERS[row.head_selection](ctx, row, pool) if pool else None


async def install_head(ctx: TickContext, row: OrgGovernanceRow, head: EntityRow, why: str) -> None:
    row.head_node_id = head.id
    row.term_ends_epoch = ctx.epoch + max(1, row.term_epochs)
    if TRUST_LOCK not in (row.locked or []):
        row.trust = ctx.rules.governance.new_head_trust
    profile = await ctx.session.get(FactionProfileRow, row.org_node_id)
    if profile is not None and "leader_entity_id" not in (profile.locked or []):
        profile.leader_entity_id = head.id
    member = await ctx.session.get(FactionMembershipRow, (row.org_node_id, head.id))
    if member is None and profile is not None and head.entity_type is EntityType.MORTAL:
        ctx.session.add(
            FactionMembershipRow(faction_entity_id=row.org_node_id, mortal_entity_id=head.id, rank=FactionRank.LEADER, joined_epoch=ctx.epoch, locked=[])
        )
    elif member is not None and "rank" not in (member.locked or []):
        member.rank = FactionRank.LEADER
    await record(
        ctx,
        "org.head_chosen",
        roles={IncidentRole.SUBJECT: row.org_node_id, IncidentRole.ACTOR: head.id},
        facts={"selection": row.head_selection, "why": why},
    )


async def renew_head(ctx: TickContext, row: OrgGovernanceRow) -> bool:
    if HEAD_LOCK in (row.locked or []):
        return False
    current = await living(ctx, row.head_node_id)
    member_ids = {member.mortal_entity_id for member in await members_of(ctx, row.org_node_id)}
    lost = current is None or (row.decision_body is not GoverningBody.SHAREHOLDERS_MEETING and member_ids and current.id not in member_ids)
    young = current is not None and row.head_selection is not HeadSelection.INHERITED and not await of_age(ctx.session, current.id)
    ended = row.term_ends_epoch is not None and ctx.epoch >= row.term_ends_epoch
    if not lost and not young and not ended:
        return False
    head = await chosen_head(ctx, row)
    if head is None:
        return False
    why = "the head was gone" if lost else "the head was too young to lead" if young else "the term ended"
    if head.id == row.head_node_id:
        row.term_ends_epoch = ctx.epoch + max(1, row.term_epochs)
        return False
    await install_head(ctx, row, head, why)
    return True


async def strategy_vote(ctx: TickContext, row: OrgGovernanceRow) -> OrgStrategy | None:
    seats = await seats_of(ctx, row.org_node_id)
    if not seats or STRATEGY_LOCK in (row.locked or []):
        return None
    cliques = [clique for clique in await cliques_of(ctx, row.org_node_id) if clique.aim is CliqueAim.STRATEGY and clique.aim_strategy is not None]
    if not any(clique.aim_strategy is not row.strategy for clique in cliques):
        return None
    tally: Counter[OrgStrategy] = Counter()
    for seat in seats:
        backed = next((clique.aim_strategy for clique in cliques if seat.member_node_id in (clique.members or [])), None)
        tally[backed or row.strategy] += seat.vote_weight
    winner = max(tally, key=lambda item: (tally[item], item is row.strategy, item.value))
    cast = sum(tally.values())
    await record(
        ctx,
        "org.vote_held",
        roles={IncidentRole.SUBJECT: row.org_node_id},
        facts={"motion": winner, "for_votes": tally[winner], "cast": cast, "quorum": row.quorum_pct},
    )
    if winner is row.strategy or tally[winner] * PERCENT < row.quorum_pct * max(1, cast):
        return None
    return winner


async def set_strategy(ctx: TickContext, row: OrgGovernanceRow, strategy: OrgStrategy, actor: int | None, reason: str | None = None) -> None:
    before = row.strategy
    row.strategy = strategy
    roles = {IncidentRole.SUBJECT: row.org_node_id} | ({IncidentRole.ACTOR: actor} if actor is not None else {})
    facts = {"before": before, "after": strategy} | ({"reason": reason} if reason is not None else {})
    await record(ctx, "org.strategy_changed", roles=roles, facts=facts)


async def head_defies(ctx: TickContext, row: OrgGovernanceRow, decided: OrgStrategy) -> bool:
    head = row.head_node_id
    if head is None or TRUST_LOCK in (row.locked or []):
        return False
    wish = next(
        (clique.aim_strategy for clique in await cliques_of(ctx, row.org_node_id) if clique.aim is CliqueAim.STRATEGY and head in (clique.members or [])),
        None,
    )
    if wish is None or wish is decided:
        return False
    row.trust = clamp_int(row.trust - ctx.rules.governance.head_defiance_trust_loss, 0, PERCENT)
    return True


async def remove_head(ctx: TickContext, row: OrgGovernanceRow) -> bool:
    if row.head_node_id is None or HEAD_LOCK in (row.locked or []) or row.trust >= ctx.rules.governance.removal_trust:
        return False
    if row.decision_body in {GoverningBody.HEAD, GoverningBody.FOUNDER, GoverningBody.MADE_MIND, GoverningBody.NONE}:
        return False
    removed = row.head_node_id
    await record(ctx, "org.head_removed", roles={IncidentRole.SUBJECT: row.org_node_id, IncidentRole.VICTIM: removed}, facts={"trust": row.trust})
    row.head_node_id = None
    head = await chosen_head(ctx, row)
    if head is not None and head.id != removed:
        await install_head(ctx, row, head, "the body removed the head")
    return True


async def govern(ctx: TickContext, row: OrgGovernanceRow) -> tuple[bool, bool, bool]:
    chosen = await renew_head(ctx, row)
    await sync_seats(ctx, row)
    decided = await strategy_vote(ctx, row)
    defied = False
    if decided is not None:
        defied = await head_defies(ctx, row, decided)
        if not defied:
            await set_strategy(ctx, row, decided, None)
    removed = await remove_head(ctx, row)
    if removed:
        await sync_seats(ctx, row)
    return chosen, defied, removed
