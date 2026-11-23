from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.faith import ReincarnationRow, SpiritProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import JudgementDoctrine, RebirthPath, ReincarnationGate
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.models.entity_stats import PeopleStats, SpiritStats
from aerona.engine.faith.doctrine import rebirth_path_of
from aerona.engine.faith.souls import kind_to_bear, reborn_as_kind
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, seed_core_world, settlement
from tests.engine.core.test_sacred_w25 import at


async def test_a_people_that_holds_nature_dear_teaches_rebirth_into_other_kinds_and_reveres_the_kind_its_dead_became(session: AsyncSession) -> None:
    world: CoreWorld = await seed_core_world(session)
    rules = Rules()
    assert rebirth_path_of(rules, {ValueAxis.NATURE: rules.doctrine.value_tenet}, JudgementDoctrine.NONE) is RebirthPath.KIND
    folk = await entity(session, "Kin of the Wild", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    home = await settlement(session, "Deerholt", world, world.regions[0])
    await bond(session, home.id, folk.id, BondKind.DESCENDS_FROM)
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=world.regions[0].id, abundance=40))
    elder = await mortal(session, "Old Bram", world, home.id)
    soul = await entity(session, "Soul of Old Bram", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=home.id)
    profile = SpiritProfileRow(spirit_entity_id=soul.id, origin_mortal_id=elder.id, locked=[])
    session.add(profile)
    await session.flush()
    ctx = await at(session, 3, rebirth={"kind_path_pct": 100})
    species = await kind_to_bear(ctx, soul, home)
    assert species is not None and species.id == world.species.id
    await reborn_as_kind(ctx, profile, soul, home, gate=ReincarnationGate.TENET, species=species)
    row = await session.scalar(select(ReincarnationRow).where(ReincarnationRow.spirit_entity_id == soul.id))
    assert row is not None and row.path is RebirthPath.KIND and row.species_entity_id == species.id
    regard = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == folk.id, MemoryRow.subject_node_id == species.id))
    assert regard is not None and regard.magnitude > 0
    assert await session.scalar(select(IncidentRow).where(IncidentRow.kind == "soul.reborn")) is not None
