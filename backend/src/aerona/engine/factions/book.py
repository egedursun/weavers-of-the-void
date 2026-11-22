from collections import defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionActionRow, FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import ARMED_KINDS, KIND_OF_ENGINE, ROBBER_KINDS, SECRET_KINDS, FactionActionKind, FactionKind, FactionRank, FactionScale
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat

PROFILE_FIXUP = "faction_profiles_from_kinds"
CLASS_OF_KIND = MappingProxyType(
    {
        FactionKind.MERCHANT_GUILD: SocialClass.MERCHANT,
        FactionKind.CRAFT_GUILD: SocialClass.ARTISAN,
        FactionKind.PRIESTHOOD: SocialClass.PRIEST,
        FactionKind.WARRIOR_ORDER: SocialClass.WARRIOR,
        FactionKind.NOBLE_COUNCIL: SocialClass.NOBLE,
        FactionKind.PEASANT_LEAGUE: SocialClass.FARMER,
        FactionKind.SCHOLARS_ACADEMY: SocialClass.SCRIBE,
        FactionKind.BANDITS: SocialClass.OUTCAST,
        FactionKind.PIRATES: SocialClass.OUTCAST,
        FactionKind.ASSASSINS: SocialClass.OUTCAST,
        FactionKind.MERCENARY_COMPANY: SocialClass.WARRIOR,
        FactionKind.REBELS: SocialClass.FARMER,
        FactionKind.CRIME_FAMILY: SocialClass.OUTCAST,
        FactionKind.THIEVES_GUILD: SocialClass.OUTCAST,
        FactionKind.SMUGGLING_RING: SocialClass.OUTCAST,
        FactionKind.PIRATE_CONFEDERACY: SocialClass.OUTCAST,
        FactionKind.WORKERS_UNION: SocialClass.ARTISAN,
        FactionKind.WORKER_BODY: SocialClass.WORKER,
        FactionKind.ENGINEERS_SOCIETY: SocialClass.PROFESSIONAL,
        FactionKind.FINANCIERS: SocialClass.MERCHANT,
        FactionKind.VETERANS: SocialClass.WARRIOR,
    }
)


@dataclass
class FactionBook:
    entities: dict[int, EntityRow]
    profiles: dict[int, FactionProfileRow]
    goals: dict[int, list[FactionGoalRow]] = field(default_factory=lambda: defaultdict(list))
    members: dict[int, list[FactionMembershipRow]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    async def load(cls, session: AsyncSession) -> "FactionBook":
        entities = {
            row.id: row
            for row in await session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        }
        profiles = {row.faction_entity_id: row for row in await session.scalars(select(FactionProfileRow)) if row.faction_entity_id in entities}
        book = cls(entities, profiles)
        for goal in await session.scalars(select(FactionGoalRow).where(FactionGoalRow.achieved_epoch.is_(None)).order_by(FactionGoalRow.id)):
            if goal.faction_entity_id in entities:
                book.goals[goal.faction_entity_id].append(goal)
        for member in await session.scalars(select(FactionMembershipRow)):
            if member.faction_entity_id in entities:
                book.members[member.faction_entity_id].append(member)
        return book


async def move_member(session: AsyncSession, row: FactionMembershipRow, faction_id: int, epoch: int) -> FactionMembershipRow:
    moved = FactionMembershipRow(
        faction_entity_id=faction_id, mortal_entity_id=row.mortal_entity_id, rank=row.rank, joined_epoch=epoch, locked=list(row.locked or [])
    )
    await session.delete(row)
    session.add(moved)
    return moved


def default_kind(faction: EntityRow) -> FactionKind:
    if faction.engine_kind is not None and faction.engine_kind in KIND_OF_ENGINE:
        return KIND_OF_ENGINE[faction.engine_kind]
    if faction.social_class is SocialClass.NOBLE:
        return FactionKind.NOBLE_COUNCIL
    if faction.social_class is SocialClass.MERCHANT:
        return FactionKind.MERCHANT_GUILD
    return (
        FactionKind.SECRET_SOCIETY
        if faction.social_class is None and (stat(faction, "sway") or 0) > (stat(faction, "strength") or 0)
        else FactionKind.WARRIOR_ORDER
    )


def new_profile(ctx: TickContext, faction: EntityRow, kind: FactionKind) -> FactionProfileRow:
    profile = FactionProfileRow(
        faction_entity_id=faction.id,
        kind=kind,
        scale=FactionScale.BAND,
        treasury=clamp_int((stat(faction, "wealth") or 0) * 2, 0, 10**9),
        cohesion=60,
        secrecy=ctx.rules.intrigue.secret_base if kind in SECRET_KINDS else 0,
        armed=kind in ARMED_KINDS,
        reputation=PERCENT // 2,
        influence_over={},
        cohort_share={},
        home_entity_id=faction.affiliated_entity_id or faction.location_id,
        outlawed=False,
        pay=ctx.rules.mercenaries.pay if kind is FactionKind.MERCENARY_COMPANY else 0,
        loyalty=PERCENT // 2,
        unpaid_epochs=0,
        founded_epoch=faction.birth_epoch or ctx.epoch,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(profile)
    return profile


async def backfill_profiles(ctx: TickContext, book: FactionBook) -> int:
    fixed = await ctx.session.get(AppliedFixupRow, PROFILE_FIXUP) is not None
    made = 0
    for faction in book.entities.values():
        if faction.id in book.profiles:
            continue
        book.profiles[faction.id] = new_profile(ctx, faction, default_kind(faction))
        made += 1
        members = await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == faction.id)
        )
        for mortal_id in members:
            mortal = await ctx.session.get(EntityRow, mortal_id)
            if mortal is not None and mortal.entity_type is EntityType.MORTAL and await ctx.session.get(FactionMembershipRow, (faction.id, mortal_id)) is None:
                row = FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=mortal_id, rank=FactionRank.MEMBER, joined_epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
                book.members[faction.id].append(row)
    if not fixed:
        ctx.session.add(AppliedFixupRow(key=PROFILE_FIXUP, result={"profiles": made}))
    await ctx.session.flush()
    return made


def log(
    ctx: TickContext,
    faction_id: int,
    kind: FactionActionKind,
    *,
    target: int | None = None,
    goal: FactionGoalRow | None = None,
    success: bool = True,
    amount: int = 0,
    note: str = "",
) -> None:
    ctx.session.add(
        FactionActionRow(
            faction_entity_id=faction_id,
            epoch=ctx.epoch,
            kind=kind,
            goal_id=goal.id if goal is not None else None,
            target_node_id=target,
            success=success,
            amount=amount,
            note=note or None,
        )
    )
    ctx.count(f"faction_act.{kind.value}")


async def robber_ids(session: AsyncSession) -> frozenset[int]:
    statement = (
        select(FactionProfileRow.faction_entity_id)
        .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.kind.in_(list(ROBBER_KINDS)), EntityRow.status == EntityStatus.CANON)
    )
    return frozenset(await session.scalars(statement))


@memoized(FactionProfileRow)
async def monopoly_homes(session: AsyncSession) -> frozenset[int | None]:
    return frozenset(await session.scalars(select(FactionProfileRow.home_entity_id).where(FactionProfileRow.monopoly.is_not(None)).distinct()))


@memoized(FactionProfileRow)
async def monopolies_at(session: AsyncSession, community_id: int) -> frozenset[str]:
    if community_id not in await monopoly_homes(session):
        return frozenset()
    rows = await session.scalars(
        select(FactionProfileRow.monopoly).where(FactionProfileRow.home_entity_id == community_id, FactionProfileRow.monopoly.is_not(None))
    )
    return frozenset(str(row) for row in rows)


async def monopoly_factor(session: AsyncSession, community_id: int, commodity: CommodityKind, rules_pct: int) -> float:
    return rules_pct / PERCENT if commodity.value in await monopolies_at(session, community_id) else 1.0
