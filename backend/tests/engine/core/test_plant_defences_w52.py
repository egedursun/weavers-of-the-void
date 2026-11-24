from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.flora import PlantProfileRow
from aerona.db.tables.nature import SpeciesRelationRow
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.nature import PlantDefence, SymbiosisKind
from aerona.engine.nature.plants import guard_plants
from aerona.engine.nature.symbiosis import SymbiosisBook
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, range_of, told


def test_seven_defences_with_stinging_and_guardians() -> None:
    assert len(PlantDefence) == 9
    assert {PlantDefence.STINGING, PlantDefence.GUARDIANS} <= set(PlantDefence)


async def test_guardians_drive_off_grazers_only_while_their_allies_live(session: AsyncSession, world: CoreWorld) -> None:
    guarded_land, lonely_land = world.regions[0], world.regions[1]
    acacia = await kind(session, world, "Thorn Acacia", guarded_land, 60)
    ant = await kind(session, world, "Guard Ant", guarded_land, 60, diet=Diet.CARNIVORE)
    goat = await kind(session, world, "Browse Goat", guarded_land, 50, diet=Diet.HERBIVORE)
    lone_acacia = await kind(session, world, "Lone Acacia", lonely_land, 60)
    lone_goat = await kind(session, world, "Lone Goat", lonely_land, 50, diet=Diet.HERBIVORE)
    for plant in (acacia, lone_acacia):
        session.add(PlantProfileRow(species_entity_id=plant.id, defence=PlantDefence.GUARDIANS, locked=[]))
    session.add(SpeciesRelationRow(first_species_id=acacia.id, second_species_id=ant.id, kind=SymbiosisKind.MUTUALISM, strength=80, locked=[]))
    session.add(SpeciesRelationRow(first_species_id=lone_acacia.id, second_species_id=ant.id, kind=SymbiosisKind.MUTUALISM, strength=80, locked=[]))
    await session.flush()
    ctx = await manual_context(session, "plants", tuned_rules(plant_defences={"guardian_harm": 20}))
    book = await SymbiosisBook.load(session)
    await guard_plants(ctx, guarded_land.id, 1.0, book)
    await guard_plants(ctx, lonely_land.id, 1.0, book)
    assert (await range_of(session, goat, guarded_land)).abundance == 30
    assert (await range_of(session, ant, guarded_land)).abundance == 60
    assert (await range_of(session, lone_goat, lonely_land)).abundance == 50
    assert await told(session, "life.guardians_struck")
