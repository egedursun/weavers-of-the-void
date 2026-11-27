from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.land_memory import LAND_MEMORIES
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.region import RegionMemoryRow
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import RegionMemoryKind
from aerona.engine.environment.memory import darkness_of, fade_memories, fades, happenings, holiness_of
from aerona.engine.environment.memory_effects import answer_memories
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal, seed_core_world

RULES = Rules()
K = RegionMemoryKind
NEW = (K.FOUNDING, K.TREATY, K.EXPULSION, K.DISCOVERY)


async def happened(session: AsyncSession, world: CoreWorld, kind: str, parties: list[int]) -> IncidentRow:
    row = IncidentRow(kind=kind, epoch=1, place_entity_id=world.regions[0].id, world_id=world.world.id)
    session.add(row)
    await session.flush()
    for position, node in enumerate(parties):
        session.add(
            IncidentParticipantRow(incident_id=row.id, node_id=node, role=IncidentRole.ACTOR if position == 0 else IncidentRole.TARGET, position=position)
        )
    await session.flush()
    return row


def test_each_new_memory_reads_its_catalogue_row() -> None:
    assert all(kind in LAND_MEMORIES for kind in NEW)
    assert darkness_of(RULES, K.EXPULSION) > darkness_of(RULES, K.FOUNDING) == 0
    assert holiness_of(RULES, K.FOUNDING) > 0 and holiness_of(RULES, K.DISCOVERY) > 0
    assert all(fades(RULES, kind) for kind in NEW)


async def test_a_founding_a_treaty_an_expulsion_and_a_discovery_write_memories(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    for kind in ("polity.founded", "diplomacy.peace", "disease.expelled", "knowledge.discovered"):
        await happened(session, world, kind, [world.people.id])
    found = {item.kind: item for item in await happenings(session, RULES, await RegionAtlas.load(session), 0)}
    assert set(NEW) <= set(found)
    assert found[K.FOUNDING].magnitude == RULES.land_memory.founding_weight and found[K.FOUNDING].region_id == world.regions[0].id


async def test_a_treaty_binds_its_signers_and_an_expulsion_leaves_a_grievance(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    first, second = await mortal(session, "Signer", world, world.regions[0].id), await mortal(session, "Other", world, world.regions[0].id)
    treaty = await happened(session, world, "diplomacy.peace", [first.id, second.id])
    expulsion = await happened(session, world, "disease.expelled", [first.id, second.id])
    rows = [
        RegionMemoryRow(
            world_id=world.world.id, region_entity_id=world.regions[0].id, kind=K.TREATY, magnitude=30, epoch=1, source_key="a", incident_id=treaty.id
        ),
        RegionMemoryRow(
            world_id=world.world.id, region_entity_id=world.regions[0].id, kind=K.EXPULSION, magnitude=40, epoch=1, source_key="b", incident_id=expulsion.id
        ),
    ]
    session.add_all(rows)
    await session.flush()
    assert await answer_memories(ctx, rows) == 2
    kinds = {(row.holder_node_id, row.kind) for row in await session.scalars(select(MemoryRow))}
    assert (first.id, MemoryKind.MADE_PEACE) in kinds and (second.id, MemoryKind.MADE_PEACE) in kinds
    assert (second.id, MemoryKind.HARMED_ME) in kinds and (first.id, MemoryKind.HARMED_ME) not in kinds
    before = rows[0].magnitude
    await fade_memories(session, RULES, 5)
    assert rows[0].magnitude < before


async def test_a_witness_is_no_party_to_what_the_land_remembers_and_the_line_names_what_was_remembered(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    first, second = await mortal(session, "Signer", world, world.regions[0].id), await mortal(session, "Other", world, world.regions[0].id)
    onlooker = await mortal(session, "Onlooker", world, world.regions[0].id)
    treaty = await happened(session, world, "diplomacy.peace", [first.id, second.id])
    session.add(IncidentParticipantRow(incident_id=treaty.id, node_id=onlooker.id, role=IncidentRole.WITNESS, position=0))
    row = RegionMemoryRow(
        world_id=world.world.id, region_entity_id=world.regions[0].id, kind=K.TREATY, magnitude=30, epoch=1, source_key="c", incident_id=treaty.id
    )
    session.add(row)
    await session.flush()
    await answer_memories(ctx, [row])
    holders = {memory.holder_node_id for memory in await session.scalars(select(MemoryRow).where(MemoryRow.kind == MemoryKind.MADE_PEACE))}
    assert holders == {first.id, second.id}
    told = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.template_key == "memory.written"))
    assert told is not None and "of Signer" in told
