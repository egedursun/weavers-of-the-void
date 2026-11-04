from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import TRADITIONS
from aerona.catalog.peoples import FUNERAL_DEEDS, FUNERAL_NAMES, FUNERALS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.rules.registry import Rules

FUNERAL_SUBTYPE = "funeral rite"
RITE_SPREAD = 60
RITE_RIGIDITY = 70
RITE_POWER = 2
RITE_LINK = "funeral_rite_id"


def scaled(factor: float, pct: int) -> float:
    return max(0.0, 1 + (factor - 1) * pct / PERCENT)


def contagion(rules: Rules, rite: FuneralCustom) -> float:
    return scaled(FUNERALS[rite].contagion_pct / PERCENT, rules.customs.funeral_pct)


def spirit_factor(rules: Rules, rite: FuneralCustom | None) -> float:
    return scaled(FUNERALS[rite].spirit_pct / PERCENT, rules.customs.funeral_pct) if rite is not None else 1.0


def mourning_factor(rules: Rules, rite: FuneralCustom | None) -> float:
    return scaled(FUNERALS[rite].mourning_pct / PERCENT, rules.customs.funeral_pct) if rite is not None else 1.0


def restless_shift(rules: Rules, rite: FuneralCustom | None) -> int:
    return round(FUNERALS[rite].restless_shift * rules.customs.funeral_pct / PERCENT) if rite is not None else 0


def raises_dead(rite: FuneralCustom) -> bool:
    return FUNERALS[rite].raises_dead


def binds_spirits(rite: FuneralCustom | None) -> bool:
    return rite is not None and FUNERALS[rite].binds_spirits


def restless(rules: Rules, rite: FuneralCustom | None, unrest: int, threshold: int) -> bool:
    if binds_spirits(rite):
        return False
    return unrest + restless_shift(rules, rite) > threshold


async def rite_of(session: AsyncSession, entity: EntityRow) -> FuneralCustom | None:
    people = await people_of(session, entity)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.funeral_rite if culture is not None else None


def set_rite(culture: PeopleCultureRow, rite: FuneralCustom) -> None:
    if culture.funeral_rite is not rite:
        culture.funeral_rite = rite
        culture.funeral_rite_id = None


async def rite_tradition(session: AsyncSession, rules: Rules, people: EntityRow, culture: PeopleCultureRow, epoch: int) -> EntityRow | None:
    if RITE_LINK in culture.locked:
        return None
    current = await session.get(EntityRow, culture.funeral_rite_id) if culture.funeral_rite_id is not None else None
    if current is not None and current.status is EntityStatus.CANON:
        return None
    tradition = await open_record(
        session,
        epoch,
        RecordSpec(
            entity_type=EntityType.TRADITION,
            name=FUNERAL_NAMES[culture.funeral_rite].format(people=people.name),
            body=f"The {people.name} {FUNERAL_DEEDS[culture.funeral_rite]}.",
            stats=TraditionStats(spread=RITE_SPREAD, rigidity=RITE_RIGIDITY),
            power=RITE_POWER,
            world_id=people.world_id,
            subtype=FUNERAL_SUBTYPE,
        ),
    )
    await connect(session, people.id, tradition.id, BondKind.CELEBRATES, epoch, description="their funeral rite")
    spec = TRADITIONS[TraditionKind.FUNERAL_RITE]
    session.add(
        TraditionProfileRow(
            tradition_entity_id=tradition.id,
            kind=TraditionKind.FUNERAL_RITE,
            calendar_slot=None,
            cost={"goods": rules.traditions.offering_cost, **spec.cost},
            effects=dict(spec.effects),
            taboo_target=None,
            origin_entity_id=people.id,
            updated_epoch=epoch,
            locked=[],
        )
    )
    culture.funeral_rite_id = tradition.id
    return tradition
