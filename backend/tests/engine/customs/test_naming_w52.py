from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.naming import NAME_FORMS, NAMING_PATTERNS
from aerona.db.tables.customs import NameFormRow, NamingCustomRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import NameForm, NamingPattern
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.customs.naming import NamingTally, name_the_dead
from aerona.engine.primitives.naming import Namer
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement


def test_six_patterns_and_eight_forms() -> None:
    assert len(NAMING_PATTERNS) == len(NamingPattern) == 8 and len(NAME_FORMS) == len(NameForm) == 10


async def test_the_dead_take_their_new_name_and_keep_the_living_one_on_record(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    custom = NamingCustomRow(people_entity_id=world.people.id, posthumous_names=True, taboo_epochs=2, locked=[])
    session.add(custom)
    town = await settlement(session, "Old Hearth", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    dead = await mortal(session, "Orsolya", world, town.id)
    dead.status, dead.end_epoch = EntityStatus.DEAD, ctx.epoch
    await session.flush()
    tally = NamingTally()
    await name_the_dead(ctx, Namer(session, ctx.rules), world.people, custom, tally)
    await session.flush()
    posthumous = await session.get(NameFormRow, (dead.id, NameForm.POSTHUMOUS))
    assert posthumous is not None
    living = await session.get(NameFormRow, (dead.id, NameForm.BIRTH))
    assert dead.name == posthumous.name and living is not None and living.name == "Orsolya"
