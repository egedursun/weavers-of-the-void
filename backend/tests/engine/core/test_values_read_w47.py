from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import HEAD_FIRST
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.db.tables.urban import OrderLawRow
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.tongues import WordOrder
from aerona.domain.enums.urban import OrderLaw
from aerona.domain.models.genesis import GenesisSettings
from aerona.engine.factions.order_laws import LAW_EFFECTS, keep_law
from aerona.engine.technology.profiles import seed_worlds
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_minds_w44 import at


def test_word_order_sets_where_the_head_of_a_compound_stands() -> None:
    assert HEAD_FIRST[WordOrder.SVO] and HEAD_FIRST[WordOrder.VSO]
    assert not HEAD_FIRST[WordOrder.SOV] and not HEAD_FIRST[WordOrder.OSV]
    assert set(LAW_EFFECTS) == set(OrderLaw)


async def test_an_order_that_keeps_secrecy_grows_secret(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    profile = FactionProfileRow(faction_entity_id=world.people.id, kind=FactionKind.MAGE_ORDER, secrecy=0, influence_over={}, cohort_share={}, locked=[])
    law = OrderLawRow(faction_entity_id=world.people.id, law=OrderLaw.KEEP_SECRECY, strength=60, locked=[])
    await keep_law(ctx, profile, law, [])
    assert 0 < profile.secrecy <= law.strength


async def test_worlds_start_each_family_where_genesis_set_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 1)
    settings = world.cosmos.genesis_settings or GenesisSettings(magic=50, danger=50, peoples=1)
    world.cosmos.genesis_settings = settings.model_copy(update={"technology_levels": {TechFamily.SPACE: 9}})
    await session.flush()
    await seed_worlds(ctx)
    space = await session.get(TechnologyProfileRow, (world.world.id, TechFamily.SPACE))
    farming = await session.get(TechnologyProfileRow, (world.world.id, TechFamily.AGRICULTURE))
    assert space is not None and space.level == 9
    assert farming is not None and farming.level != 9
