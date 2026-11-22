from collections.abc import Awaitable, Callable

from sqlalchemy import select

from aerona.catalog.life.polity import TO_SECRECY_FACTION_KINDS
from aerona.core.dispatch import Handlers
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MarriageRow, MortalProfileRow
from aerona.db.tables.polity import OathRow
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OathBreach, OathKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext

Swore = Callable[[TickContext, EntityRow, frozenset[TenetKind]], Awaitable[tuple[bool, int | None]]]
Broke = Callable[[TickContext, OathRow, EntityRow], Awaitable[OathBreach | None]]
SERVING = frozenset({SocialClass.SERF_OR_SLAVE, SocialClass.WORKER})


VOWS: Handlers[OathKind, Swore] = Handlers(OathKind)


@VOWS.on(OathKind.SERVICE)
async def to_serve(ctx: TickContext, mortal: EntityRow, _tenets: frozenset[TenetKind]) -> tuple[bool, int | None]:
    lord = mortal.affiliated_entity_id
    return mortal.social_class in SERVING and lord is not None, lord


@VOWS.on(OathKind.POVERTY)
async def to_poverty(_ctx: TickContext, mortal: EntityRow, tenets: frozenset[TenetKind]) -> tuple[bool, int | None]:
    return TenetKind.ASCETICISM in tenets and mortal.social_class in {SocialClass.PRIEST, SocialClass.MONASTIC}, None


@VOWS.on(OathKind.NONVIOLENCE)
async def to_peace(_ctx: TickContext, _mortal: EntityRow, tenets: frozenset[TenetKind]) -> tuple[bool, int | None]:
    return TenetKind.PACIFISM in tenets, None


@VOWS.on(OathKind.FIDELITY)
async def to_fidelity(ctx: TickContext, mortal: EntityRow, _tenets: frozenset[TenetKind]) -> tuple[bool, int | None]:
    marriage = await ctx.session.scalar(
        select(MarriageRow).where(MarriageRow.end_epoch.is_(None), (MarriageRow.first_id == mortal.id) | (MarriageRow.second_id == mortal.id)).limit(1)
    )
    if marriage is None or marriage.start_epoch != ctx.epoch:
        return False, None
    return True, marriage.second_id if marriage.first_id == mortal.id else marriage.first_id


@VOWS.on(OathKind.SECRECY)
async def to_secrecy(ctx: TickContext, mortal: EntityRow, _tenets: frozenset[TenetKind]) -> tuple[bool, int | None]:
    secret = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind.in_(TO_SECRECY_FACTION_KINDS))
    society = await ctx.session.scalar(
        select(FactionMembershipRow.faction_entity_id)
        .where(FactionMembershipRow.mortal_entity_id == mortal.id, FactionMembershipRow.faction_entity_id.in_(secret))
        .limit(1)
    )
    return society is not None, society


BREACHES: Handlers[OathKind, Broke] = Handlers(OathKind)


@BREACHES.on(OathKind.SERVICE)
async def service_broken(_ctx: TickContext, oath: OathRow, swearer: EntityRow) -> OathBreach | None:
    return OathBreach.SERVICE_LEFT if oath.recipient_node_id is not None and swearer.affiliated_entity_id != oath.recipient_node_id else None


@BREACHES.on(OathKind.POVERTY)
async def poverty_broken(ctx: TickContext, _oath: OathRow, swearer: EntityRow) -> OathBreach | None:
    profile = await ctx.session.get(MortalProfileRow, swearer.id)
    return OathBreach.WEALTH_GATHERED if profile is not None and profile.wealth > ctx.rules.oaths.poverty_wealth else None


@BREACHES.on(OathKind.NONVIOLENCE)
async def peace_broken(ctx: TickContext, oath: OathRow, swearer: EntityRow) -> OathBreach | None:
    killed = await ctx.session.scalar(
        select(MemoryRow.id)
        .where(MemoryRow.subject_node_id == swearer.id, MemoryRow.kind == MemoryKind.KILLED_KIN, MemoryRow.epoch >= oath.sworn_epoch)
        .limit(1)
    )
    return OathBreach.BLOOD_SHED if killed is not None else None


@BREACHES.on(OathKind.FIDELITY)
async def fidelity_broken(ctx: TickContext, oath: OathRow, swearer: EntityRow) -> OathBreach | None:
    marriage = await ctx.session.scalar(
        select(MarriageRow.id).where(MarriageRow.end_epoch.is_(None), (MarriageRow.first_id == swearer.id) | (MarriageRow.second_id == swearer.id)).limit(1)
    )
    return OathBreach.UNION_PUT_ASIDE if marriage is None else None


@BREACHES.on(OathKind.SECRECY)
async def secrecy_broken(ctx: TickContext, oath: OathRow, swearer: EntityRow) -> OathBreach | None:
    if oath.recipient_node_id is None:
        return None
    still = await ctx.session.get(FactionMembershipRow, (oath.recipient_node_id, swearer.id))
    return OathBreach.KEEPERS_LEFT if still is None else None
