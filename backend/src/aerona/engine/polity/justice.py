from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import CastingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import ClaimRow, PolityMemberRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import ROBBER_KINDS, FactionKind
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.customs.relief import relieved_theft
from aerona.engine.faith.book import patron_node
from aerona.engine.law.offences import wide_offences
from aerona.engine.mind.book import values_for
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of

RECENT_EPOCHS = 2
TREASON_KINDS = frozenset({FactionKind.REBELS, FactionKind.SECRET_SOCIETY})


async def _members_of(ctx: TickContext, mortals: list[EntityRow]) -> dict[int, set[FactionKind]]:
    ids = [mortal.id for mortal in mortals]
    found: dict[int, set[FactionKind]] = {}
    if not ids:
        return found
    statement = (
        select(FactionMembershipRow.mortal_entity_id, FactionProfileRow.kind)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == FactionMembershipRow.faction_entity_id)
        .where(FactionMembershipRow.mortal_entity_id.in_(ids))
    )
    for mortal_id, kind in await ctx.session.execute(statement):
        found.setdefault(mortal_id, set()).add(kind)
    bonded = (
        select(BondRow.source_node_id, FactionProfileRow.kind)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(ids))
    )
    for mortal_id, kind in await ctx.session.execute(bonded):
        found.setdefault(mortal_id, set()).add(kind)
    return found


async def _at_war(ctx: TickContext, town_id: int) -> bool:
    polity = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    sides = [town_id, *([polity] if polity is not None else [])]
    found = await ctx.session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(sides), WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        .limit(1)
    )
    return found is not None


async def offenders(ctx: TickContext, town_id: int, laws: LawBook) -> dict[CrimeKind, list[EntityRow]]:
    mortals = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town_id]))
            .order_by(EntityRow.id)
        )
    )
    found: dict[CrimeKind, list[EntityRow]] = {kind: [] for kind in CrimeKind}
    if not mortals:
        return found
    ids = {mortal.id for mortal in mortals}
    bands = await _members_of(ctx, mortals)
    killers = set(
        await ctx.session.scalars(
            select(MemoryRow.subject_node_id).where(
                MemoryRow.kind == MemoryKind.KILLED_KIN, MemoryRow.epoch >= ctx.epoch - RECENT_EPOCHS, MemoryRow.subject_node_id.in_(list(ids))
            )
        )
    )
    pressing = set(await ctx.session.scalars(select(ClaimRow.claimant_entity_id).where(ClaimRow.pressed.is_(True), ClaimRow.ended_epoch.is_(None))))
    banned = laws.param(town_id, LawKind.WORSHIP_BAN, "son_id")
    tolerance = laws.param(town_id, LawKind.RELIGIOUS_TOLERANCE, "level")
    home_god = await patron_node(ctx.session, town_id)
    worship = {
        source: target
        for source, target in await ctx.session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id).where(
                BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(list(ids))
            )
        )
    }
    commanders = set(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.COMMANDS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(list(ids)))
        )
    )
    war = await _at_war(ctx, town_id)
    relief = await relieved_theft(ctx.session, ctx.rules, town_id)
    casters = set(
        await ctx.session.scalars(
            select(CastingRow.caster_entity_id).where(CastingRow.caster_entity_id.in_(list(ids)), CastingRow.epoch >= ctx.epoch - RECENT_EPOCHS)
        )
    )
    believers = (await values_for(ctx.session, town_id)).get(ValueAxis.SUPERSTITION, 0) >= ctx.rules.witchcraft.belief_from
    for mortal in mortals:
        if believers and mortal.id in casters:
            found[CrimeKind.WITCHCRAFT].append(mortal)
        kinds = bands.get(mortal.id, set())
        if kinds & TREASON_KINDS or mortal.id in pressing:
            found[CrimeKind.TREASON].append(mortal)
        if mortal.id in killers:
            found[CrimeKind.MURDER].append(mortal)
        god = worship.get(mortal.id)
        if god is not None and ((banned and god == int(banned)) or (tolerance == "persecution" and home_god is not None and god != home_god)):
            found[CrimeKind.BLASPHEMY].append(mortal)
        if war and mortal.social_class is SocialClass.WARRIOR and mortal.id not in commanders:
            found[CrimeKind.DESERTION].append(mortal)
        if (mortal.social_class is SocialClass.OUTCAST or kinds & ROBBER_KINDS) and not ctx.rng(seed_of("relieved", mortal.id, ctx.epoch)).chance(
            relief * PERCENT
        ):
            found[CrimeKind.THEFT].append(mortal)
    await wide_offences(ctx, town_id, laws, mortals, found)
    return found
