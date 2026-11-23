from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.crafts import AID_NEEDS
from aerona.catalog.means import LIFTS, LOCKS
from aerona.catalog.rebuilding import REBUILD_PLANS
from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.belonging import SanctuaryRow
from aerona.db.tables.crafts import AssistiveAidRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.divine import CouncilRulingRow, DivineWoundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.means import SecurityRow, WaterLiftRow
from aerona.db.tables.museums import MuseumPieceRow
from aerona.db.tables.mythic import ServitorRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.agrarian import RebuildPlan
from aerona.domain.enums.belonging import SanctuaryKind, SanctuaryState
from aerona.domain.enums.divine import PenanceDeed, SonPunishment, WoundCause
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.museum import PieceKind
from aerona.domain.enums.mythic import ServitorOrigin
from aerona.engine.body.customs import people_of
from aerona.engine.eras.effects import era_techniques
from aerona.rules.registry import Rules


async def known(session: AsyncSession, holder_id: int | None) -> frozenset[object]:
    if holder_id is None:
        return frozenset()
    town = await session.get(EntityRow, holder_id)
    people = await people_of(session, town) if town is not None else None
    held = set(await era_techniques(session, holder_id))
    for owner in (holder_id, people.id if people is not None else None):
        if owner is not None:
            held |= set(await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == owner)))
    return frozenset(held)


async def siteless_moves(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ReconstructionRow).where(ReconstructionRow.finished_epoch.is_(None)).order_by(ReconstructionRow.id))
    return [row.id for row in rows if REBUILD_PLANS[row.plan].moves and row.site_entity_id is None]


async def stay_in_place(session: AsyncSession, key: int) -> None:
    row = await session.get(ReconstructionRow, key)
    if row is not None:
        row.plan = RebuildPlan.PLANNED


async def nameless_regalia(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(MuseumPieceRow.id).where(MuseumPieceRow.kind == PieceKind.REGALIA, MuseumPieceRow.polity_entity_id.is_(None)))
    return sorted(rows)


async def plain_piece(session: AsyncSession, key: int) -> None:
    row = await session.get(MuseumPieceRow, key)
    if row is not None:
        row.kind = PieceKind.ARTIFACT


async def unchartered_freedom(session: AsyncSession) -> list[int]:
    found: list[int] = []
    rows = await session.scalars(
        select(SanctuaryRow).where(SanctuaryRow.kind == SanctuaryKind.FREE_CITY, SanctuaryRow.state == SanctuaryState.SHELTERED).order_by(SanctuaryRow.id)
    )
    for row in rows:
        town = await session.get(SettlementProfileRow, row.host_entity_id)
        if town is None or not town.free_city or town.charter_entity_id is None:
            found.append(row.id)
    return found


async def plain_hospitality(session: AsyncSession, key: int) -> None:
    row = await session.get(SanctuaryRow, key)
    if row is not None:
        row.kind = SanctuaryKind.HOSPITALITY


async def host_of(session: AsyncSession, structure_id: int) -> int | None:
    profile = await session.get(StructureProfileRow, structure_id)
    return profile.host_entity_id if profile is not None else None


async def unknown_locks(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(SecurityRow).where(SecurityRow.lock.is_not(None)).order_by(SecurityRow.holder_entity_id)):
        needs = LOCKS[row.lock].needs if row.lock is not None else ()
        have = await known(session, await host_of(session, row.holder_entity_id))
        if needs and not all(need in have for need in needs):
            found.append(row.holder_entity_id)
    return found


async def unlock(session: AsyncSession, key: int) -> None:
    row = await session.get(SecurityRow, key)
    if row is not None:
        row.lock = None
        row.lock_quality = 0


async def bare_lifts(session: AsyncSession, town_id: int) -> list[WaterLiftRow]:
    rows = await session.scalars(select(WaterLiftRow).where(WaterLiftRow.settlement_entity_id == town_id).order_by(WaterLiftRow.device))
    have = await known(session, town_id)
    return [row for row in rows if LIFTS[row.device].needs not in have]


async def unpowered_lifts(session: AsyncSession) -> list[int]:
    towns = sorted(set(await session.scalars(select(WaterLiftRow.settlement_entity_id))))
    return [town for town in towns if await bare_lifts(session, town)]


async def drop_lift(session: AsyncSession, key: int) -> None:
    for row in await bare_lifts(session, key):
        await session.delete(row)


async def bare_aids(session: AsyncSession, holder_id: int) -> list[AssistiveAidRow]:
    holder = await session.get(EntityRow, holder_id)
    town = holder.location_id if holder is not None and holder.entity_type is EntityType.MORTAL else None
    have = await known(session, town)
    rows = await session.scalars(select(AssistiveAidRow).where(AssistiveAidRow.holder_node_id == holder_id).order_by(AssistiveAidRow.kind))
    return [row for row in rows if not all(need in have for need in AID_NEEDS[row.kind])]


async def unknown_aids(session: AsyncSession) -> list[int]:
    holders = sorted(set(await session.scalars(select(AssistiveAidRow.holder_node_id))))
    return [holder for holder in holders if await bare_aids(session, holder)]


async def drop_aid(session: AsyncSession, key: int) -> None:
    for row in await bare_aids(session, key):
        await session.delete(row)


async def unnamed_slayers(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(DivineWoundRow).where(DivineWoundRow.cause == WoundCause.MORTAL_SLAYER).order_by(DivineWoundRow.id))
    found: list[int] = []
    for row in rows:
        slayer = await session.get(EntityRow, row.cause_node_id) if row.cause_node_id is not None else None
        if slayer is None or slayer.entity_type is not EntityType.MORTAL:
            found.append(row.id)
    return found


async def unknown_dealer(session: AsyncSession, key: int) -> None:
    row = await session.get(DivineWoundRow, key)
    if row is not None:
        row.cause, row.cause_node_id = WoundCause.CREATOR, None


async def open_penances(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(CouncilRulingRow.id).where(
            CouncilRulingRow.punishment == SonPunishment.PENANCE,
            or_(CouncilRulingRow.penance_deed.is_(None), CouncilRulingRow.until_epoch.is_(None)),
        )
    )
    return sorted(rows)


async def set_penance(session: AsyncSession, key: int) -> None:
    row = await session.get(CouncilRulingRow, key)
    if row is not None:
        row.penance_deed = row.penance_deed or PenanceDeed.RESTORE_WORLD
        row.until_epoch = row.until_epoch if row.until_epoch is not None else row.epoch + Rules().council.penance_epochs


async def masterless_defectors(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(ServitorRow.spirit_entity_id).where(ServitorRow.origin == ServitorOrigin.DEFECTED, ServitorRow.former_god_node_id.is_(None))
    )
    return sorted(rows)


async def made_servitor(session: AsyncSession, key: int) -> None:
    row = await session.get(ServitorRow, key)
    if row is not None:
        row.origin = ServitorOrigin.MADE
