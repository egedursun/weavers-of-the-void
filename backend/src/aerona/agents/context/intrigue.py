from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.communication import CONTENT_LABELS, STATE_LABELS, SUBJECT_LABELS
from aerona.catalog.intrigue import FAVOUR_LABELS, IDENTITY_LABELS, PHASE_LABELS, SCHEMES, SECRETS, belief_label
from aerona.catalog.titles import RANK_WORDS
from aerona.core.grammar import an, several, spoken
from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyShareRow, EstateProfileRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.intrigue import BeliefRow, FavourRow, HookRow, IdentityRow, SchemeRow, SecretRow, TrueNameRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import ClaimRow, OfficeRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.communication import DispatchState
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.intrigue.schemes import OPEN
from aerona.rules.registry import Rules

GUILD_RANK_WORDS = {FactionRank.NOVICE: "apprentice", FactionRank.MEMBER: "fellow", FactionRank.OFFICER: "master", FactionRank.LEADER: "grandmaster"}


@dataclass(frozen=True)
class IntrigueBits:
    secrets: list[str] = field(default_factory=list)
    leverage: list[str] = field(default_factory=list)
    mask: str = ""
    scheme: str = ""
    names: list[str] = field(default_factory=list)
    beliefs: list[str] = field(default_factory=list)


async def name_of(session: AsyncSession, node_id: int | None) -> str:
    node = await session.get(NodeRow, node_id) if node_id is not None else None
    return f"#{node.id} {node.name}" if node is not None else "someone unknown"


async def intrigue_lines(session: AsyncSession, rules: Rules, me: EntityRow) -> IntrigueBits:
    cap = rules.mortal_tools.ctx_event_lines
    own = [
        row
        for row in await session.scalars(
            select(SecretRow).where(SecretRow.holder_node_id == me.id, SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.severity.desc())
        )
    ]
    secrets = [f"{SECRETS[row.kind].label.lower()} (known to {several(len(row.known_by) - 1, 'other', 'others')})" for row in own[:cap]]
    leverage: list[str] = []
    for hook in await session.scalars(select(HookRow).where(HookRow.holder_node_id == me.id, HookRow.used_epoch.is_(None)).order_by(HookRow.id).limit(cap)):
        leverage.append(f"{an(spoken(hook.strength))} hook on {await name_of(session, hook.target_node_id)}")
    for hook in await session.scalars(select(HookRow).where(HookRow.target_node_id == me.id, HookRow.used_epoch.is_(None)).order_by(HookRow.id).limit(cap)):
        leverage.append(f"{await name_of(session, hook.holder_node_id)} holds {an(spoken(hook.strength))} hook on you")
    favours = await session.scalars(
        select(FavourRow)
        .where(or_(FavourRow.owed_by_node_id == me.id, FavourRow.owed_to_node_id == me.id), FavourRow.called_epoch.is_(None))
        .order_by(FavourRow.id)
        .limit(cap)
    )
    for favour in favours:
        if favour.owed_to_node_id == me.id:
            leverage.append(f"{await name_of(session, favour.owed_by_node_id)} owes you for {FAVOUR_LABELS[favour.origin].lower()}")
        else:
            leverage.append(f"you owe {await name_of(session, favour.owed_to_node_id)} for {FAVOUR_LABELS[favour.origin].lower()}")
    identity = await session.get(IdentityRow, me.id)
    mask = (
        f"you live as {identity.false_name}, {IDENTITY_LABELS[identity.reason].lower()}, {identity.exposure}% seen through"
        if identity is not None and identity.exposed_epoch is None
        else ""
    )
    scheme_row = await session.scalar(select(SchemeRow).where(SchemeRow.owner_node_id == me.id, SchemeRow.phase.in_(list(OPEN))).limit(1))
    scheme = (
        f"your {SCHEMES[scheme_row.kind].label.lower()} against {await name_of(session, scheme_row.target_node_id)} "
        f"is {PHASE_LABELS[scheme_row.phase].lower()}, power {scheme_row.power} of {SCHEMES[scheme_row.kind].difficulty}"
        if scheme_row is not None
        else ""
    )
    names = [
        f"the true name of {await name_of(session, row.bearer_node_id)}"
        for row in await session.scalars(select(TrueNameRow).order_by(TrueNameRow.bearer_node_id))
        if me.id in row.known_by and row.bearer_node_id != me.id
    ][:cap]
    beliefs = [
        f"{belief_label(row.attribute).lower()} of {await name_of(session, row.subject_node_id)} is about {spoken(row)} ({row.confidence}% sure)"
        for row in await session.scalars(select(BeliefRow).where(BeliefRow.holder_node_id == me.id).order_by(BeliefRow.confidence.desc()).limit(cap))
    ]
    return IntrigueBits(secrets, leverage[: cap * 2], mask, scheme, names, beliefs)


async def name_knowers(session: AsyncSession, bearer_id: int) -> int:
    row = await session.get(TrueNameRow, bearer_id)
    return len([known for known in row.known_by if known != bearer_id]) if row is not None else 0


async def names_known(session: AsyncSession, knower_id: int, cap: int) -> list[str]:
    rows = [
        row
        for row in await session.scalars(select(TrueNameRow).order_by(TrueNameRow.bearer_node_id))
        if knower_id in row.known_by and row.bearer_node_id != knower_id
    ]
    return [f"{await name_of(session, row.bearer_node_id)}: {row.name}" for row in rows[:cap]]


async def letter_lines(session: AsyncSession, rules: Rules, me: EntityRow) -> tuple[list[str], list[str]]:
    cap = rules.mortal_tools.ctx_event_lines
    letters: list[str] = []
    rows = await session.scalars(
        select(MessageRow)
        .where(MessageRow.intent == MessageIntent.DISPATCH, or_(MessageRow.sender_node_id == me.id, MessageRow.recipient_node_id == me.id))
        .order_by(MessageRow.id.desc())
        .limit(cap)
    )
    for row in rows:
        label = CONTENT_LABELS[row.content].lower() if row.content is not None else "a message"
        state = STATE_LABELS[row.state].lower() if row.state is not None else "sent"
        if row.sender_node_id == me.id:
            letters.append(f"{label} you sent to {await name_of(session, row.recipient_node_id)} is {state}")
        elif row.state is DispatchState.DELIVERED:
            letters.append(f"{label} came to you from {await name_of(session, row.sender_node_id)}{' (it may be misread)' if row.misread else ''}")
    opinions: list[str] = []
    home = me.location_id
    views: list[PublicOpinionRow] = []
    if home is not None:
        views = list(await session.scalars(select(PublicOpinionRow).where(PublicOpinionRow.community_node_id == home).order_by(PublicOpinionRow.approval)))
    for view in list(views)[:cap]:
        opinions.append(f"your people think {view.approval:+d} of {await name_of(session, view.subject_node_id)} ({SUBJECT_LABELS[view.subject].lower()})")
    return letters, opinions


async def title_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    found: list[str] = []
    for row in await session.scalars(select(TitleProfileRow).where(TitleProfileRow.holder_node_id == me.id).order_by(TitleProfileRow.title_entity_id)):
        found.append(f"you hold {await name_of(session, row.title_entity_id)}, {an(RANK_WORDS[row.rank].lower())}")
    claims = await session.scalars(select(ClaimRow).where(ClaimRow.claimant_entity_id == me.id, ClaimRow.title_entity_id.is_not(None)).order_by(ClaimRow.id))
    for claim in claims:
        found.append(f"you have a claim on {await name_of(session, claim.title_entity_id)}")
    return found


async def estate_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    found: list[str] = []
    realms = select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.RULER)
    for row in await session.scalars(
        select(EstateProfileRow).where(EstateProfileRow.polity_entity_id.in_(realms)).order_by(EstateProfileRow.faction_entity_id)
    ):
        found.append(f"the estate {await name_of(session, row.faction_entity_id)} is {row.loyalty} loyal with {row.influence} influence")
    member = await session.scalar(
        select(FactionMembershipRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == FactionMembershipRow.faction_entity_id)
        .where(FactionMembershipRow.mortal_entity_id == me.id, FactionProfileRow.kind.in_([FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD]))
        .limit(1)
    )
    if member is not None:
        found.append(f"guild rank: {GUILD_RANK_WORDS[member.rank]} of {await name_of(session, member.faction_entity_id)}")
    for share in await session.scalars(select(CompanyShareRow).where(CompanyShareRow.holder_node_id == me.id)):
        found.append(f"you hold {share.share}% of {await name_of(session, share.company_entity_id)}")
    return found
