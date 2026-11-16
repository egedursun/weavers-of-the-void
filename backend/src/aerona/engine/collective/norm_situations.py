from collections.abc import Collection, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.intrigue import IdentityRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.collective import NormBehaviour, NormSituation
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.powers import PowerState
from aerona.domain.enums.relations import InteractionKind
from aerona.domain.enums.structure import StructureKind

WORKPLACES = frozenset(
    {
        StructureKind.FORGE,
        StructureKind.MILL,
        StructureKind.MINE,
        StructureKind.WORKSHOP,
        StructureKind.SAWMILL,
        StructureKind.TEXTILE_MILL,
        StructureKind.PAPER_MILL,
        StructureKind.FACTORY,
        StructureKind.OFFICE_TOWER,
    }
)


async def encounters(session: AsyncSession, ids: Collection[int]) -> dict[int, NormSituation]:
    found: dict[int, NormSituation] = {}
    for node_id in await session.scalars(select(IdentityRow.mortal_node_id).where(IdentityRow.mortal_node_id.in_(ids))):
        found[node_id] = NormSituation.ENCOUNTER_WITH_HIDDEN
    for node_id in await session.scalars(select(PowerRow.holder_node_id).where(PowerRow.holder_node_id.in_(ids), PowerRow.state == PowerState.ACTIVE)):
        found.setdefault(node_id, NormSituation.ENCOUNTER_WITH_GIFTED)
    for node_id in await session.scalars(select(MindProfileRow.node_id).where(MindProfileRow.node_id.in_(ids), MindProfileRow.origin != MindOrigin.BORN)):
        found[node_id] = NormSituation.ENCOUNTER_WITH_MADE_MIND
    return found


async def networks_of(session: AsyncSession, ids: Collection[int]) -> dict[int, set[int]]:
    found: dict[int, set[int]] = {}
    for network_id, member in await session.execute(
        select(NetworkNodeRow.network_entity_id, NetworkNodeRow.member_node_id).where(NetworkNodeRow.member_node_id.in_(ids))
    ):
        found.setdefault(member, set()).add(network_id)
    return found


async def place_situation(session: AsyncSession, place_id: int) -> NormSituation | None:
    if await session.scalar(select(MadeRealmRow.dimension_id).where(MadeRealmRow.host_node_id == place_id).limit(1)) is not None:
        return NormSituation.REALM
    works = await session.scalar(
        select(StructureProfileRow.host_entity_id)
        .where(StructureProfileRow.host_entity_id == place_id, StructureProfileRow.kind.in_(list(WORKPLACES)))
        .limit(1)
    )
    return NormSituation.WORKPLACE if works is not None else None


SHOWN_BY: Mapping[NormSituation, NormBehaviour] = {
    NormSituation.ENCOUNTER_WITH_GIFTED: NormBehaviour.POWER_DISPLAY,
    NormSituation.ENCOUNTER_WITH_MADE_MIND: NormBehaviour.AUGMENT_DISPLAY,
}


def deeper_behaviour(encounter: NormSituation | None, networked: bool, kind: InteractionKind) -> NormBehaviour | None:
    if kind is InteractionKind.BOAST and encounter is not None and encounter in SHOWN_BY:
        return SHOWN_BY[encounter]
    if kind is InteractionKind.CONFIDE_SECRET and encounter is NormSituation.ENCOUNTER_WITH_MADE_MIND:
        return NormBehaviour.COPY_DISCLOSURE
    if kind in (InteractionKind.TEACH, InteractionKind.GOSSIP) and networked:
        return NormBehaviour.DATA_SHARING
    return None
