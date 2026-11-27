from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.under_age import ACTING_ROLES, UNDER_AGE_KINDS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.pipeline import simulate
from aerona.engine.primitives.maturity import UNDER_AGE
from aerona.engine.primitives.stats import set_stats
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

YOUNG_EVERY = 2
CHILD_AGE = 4


async def make_young(session: AsyncSession, epoch: int) -> set[int]:
    mortals = list(
        await session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    young: set[int] = set()
    for mortal in mortals[::YOUNG_EVERY]:
        profile, _ = await ensure_profile(session, mortal.id, epoch)
        profile.life_stage = LifeStage.CHILD
        profile.locked = sorted({*(profile.locked or []), "life_stage"})
        set_stats(mortal, age=CHILD_AGE)
        young.add(mortal.id)
    await session.flush()
    return young


async def acting_young(session: AsyncSession, after: int) -> list[tuple[str, str]]:
    under = select(MortalProfileRow.entity_id).where(MortalProfileRow.life_stage.in_(sorted(UNDER_AGE)))
    rows = await session.execute(
        select(IncidentRow.kind, IncidentParticipantRow.role)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.id > after, IncidentParticipantRow.node_id.in_(under), IncidentParticipantRow.role.in_(sorted(ACTING_ROLES)))
    )
    return sorted({(kind, role.value) for kind, role in rows if kind not in UNDER_AGE_KINDS})


def test_every_kind_a_child_may_act_in_is_a_declared_kind() -> None:
    assert sorted(UNDER_AGE_KINDS - set(INCIDENT_KINDS)) == []


async def test_no_infant_or_child_takes_an_acting_part_in_a_lived_epoch(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
        cosmos = await CosmosRepository(session).get()
        assert cosmos is not None
        young = await make_young(session, cosmos.epoch)
        before = await session.scalar(select(func.max(IncidentRow.id))) or 0
    assert young
    await simulate(database, 1, rules=eager(Rules()))
    async with database.read() as session:
        assert await acting_young(session, before) == []
