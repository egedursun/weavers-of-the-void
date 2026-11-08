from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.zealotry import crusade, iconoclasm, infidel_neighbour
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.faith.factories import faithful, tick
from tests.engine.gods.factories import GodsWorld, make_entity


async def test_a_zealous_church_wages_holy_war_on_unbelieving_neighbours(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    book = await FaithBook.load(session)
    atlas = await RegionAtlas.load(session)
    assert await infidel_neighbour(ctx, book.churches[ours.cult.id], book, atlas) is None
    theirs = await faithful(session, world, name="Moru")
    book = await FaithBook.load(session)
    atlas = await RegionAtlas.load(session)
    church = book.churches[ours.cult.id]
    pair = await infidel_neighbour(ctx, church, book, atlas)
    assert pair is not None and pair[1].id in {theirs.town.id, theirs.people.id}
    line = await crusade(ctx, church, book, atlas)
    assert line is not None and line.key == "faith.crusade"
    war = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.source_node_id == pair[0].id))
    assert war is not None and war.target_node_id == pair[1].id


async def test_iconoclasts_tear_down_a_rival_temple_in_their_lands(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, replace(rules, art=replace(rules.art, iconoclasm_chance=0)))
    ours = await faithful(session, world, name="Ilun")
    book = await FaithBook.load(session)
    church = book.churches[ours.cult.id]
    assert await iconoclasm(ctx, church) is None
    temple = await make_entity(session, "House of Moru", EntityType.STRUCTURE, world_id=world.world.id, location_id=ours.town.id, stats=StructureStats())
    temple.engine_kind = EngineKind.TEMPLE
    await session.flush()
    prosperity = stat(ours.town, "prosperity") or 0
    line = await iconoclasm(ctx, (await FaithBook.load(session)).churches[ours.cult.id])
    assert line is not None and temple.status is not EntityStatus.CANON
    assert (stat(ours.town, "prosperity") or 0) < prosperity
