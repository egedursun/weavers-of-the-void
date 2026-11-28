from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.happenings import EventProfileRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import WarSide
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.demography.vital import war_share
from aerona.engine.primitives.queries import count_societies
from aerona.engine.services.war import world_war_limit
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, settlement
from tests.engine.cycles.factories import context, war

EPOCH = 4


INNER_GROUPS = 40


async def count_of(session: AsyncSession, kind: EntityType) -> int:
    return len(list(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == kind, EntityRow.status == EntityStatus.CANON))))


async def at_war_from(session: AsyncSession, world: CoreWorld, year: int, *, fought: bool) -> int:
    town = await settlement(session, "Fordwick", world, world.regions[0])
    row = await war(session, world, world.people, town)
    row.last_clash_epoch = EPOCH if fought else EPOCH - 1
    session.add_all(
        [
            WarSideRow(war_id=row.id, entity_id=side.id, side=kind, joined_epoch=EPOCH)
            for side, kind in ((world.people, WarSide.ATTACKER), (town, WarSide.DEFENDER))
        ]
    )
    session.add(EventProfileRow(entity_id=row.event_entity_id, world_id=world.world.id, start_epoch=EPOCH, start_year=year, phase_epoch=EPOCH, locked=[]))
    await session.flush()
    return town.id


async def test_a_war_begun_late_in_the_epoch_weighs_only_its_years(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    years = rules.time.years_per_epoch
    start = epoch_start_year(EPOCH, years)
    town = await at_war_from(session, world, start + years * 4 // 5, fought=True)
    share = await war_share(context(session, world, rules, EPOCH), town)
    assert abs(share - 0.2) < 0.01


async def test_a_war_carried_from_an_earlier_epoch_weighs_the_whole_epoch(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    town = await at_war_from(session, world, epoch_start_year(EPOCH, rules.time.years_per_epoch) - 10, fought=True)
    assert await war_share(context(session, world, rules, EPOCH), town) == 1.0


async def test_a_war_declared_but_not_fought_this_epoch_weighs_lightly(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    town = await at_war_from(session, world, epoch_start_year(EPOCH, rules.time.years_per_epoch) - 10, fought=False)
    assert await war_share(context(session, world, rules, EPOCH), town) == rules.demography.quiet_war_stress_pct / 100


async def test_groups_within_towns_never_widen_the_caps_on_wars(session: AsyncSession, world: CoreWorld, rules: Rules) -> None:
    before = await world_war_limit(session, rules)
    for index in range(INNER_GROUPS):
        await entity(session, f"Circle {index}", EntityType.FACTION, FactionStats(), world_id=world.world.id)
    assert await world_war_limit(session, rules) == before
    await settlement(session, "Second Town", world, world.regions[0])
    assert await count_societies(session) == len([world.people]) + await count_of(session, EntityType.SETTLEMENT)
