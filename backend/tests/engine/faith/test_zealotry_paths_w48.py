from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.fanaticisms import FANATICISMS, fanaticism_order
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import DemographicTransitionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultHoldingRow, HeresyRow
from aerona.db.tables.means import WrittenWorkRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import FanaticismKind, HoldingKind, TenetKind
from aerona.domain.enums.means import WritingMedium
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import ArtworkStats, CultStats, SettlementStats
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.faith.zealotry import (
    FANATIC_PATHS,
    book_burning,
    fanaticism,
    followers,
    forced_conversion,
    martyrdom,
    millenarian_flight,
    mortification,
    persecution,
    purge,
)
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.faith.factories import Faithful, faithful, mortal, tick
from tests.engine.gods.factories import GodsWorld, bond, make_entity


async def devout(session: AsyncSession, world: GodsWorld, ours: Faithful, name: str) -> EntityRow:
    found = await mortal(session, world, ours.town, name)
    await bond(session, found.id, ours.god.id, BondKind.WORSHIPS)
    return found


async def unbeliever(session: AsyncSession, world: GodsWorld, ours: Faithful, name: str) -> EntityRow:
    theirs = await faithful(session, world, name="Moru")
    found = await mortal(session, world, ours.town, name)
    await bond(session, found.id, theirs.god.id, BondKind.WORSHIPS)
    return found


async def church_of(session: AsyncSession, ours: Faithful) -> Church:
    return (await FaithBook.load(session)).churches[ours.cult.id]


async def worshipped(session: AsyncSession, mortal_id: int) -> set[int]:
    rows = await session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id == mortal_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    return set(rows)


def test_every_fanaticism_has_a_path_and_a_way_to_be_chosen() -> None:
    assert set(FANATIC_PATHS) == set(FanaticismKind) == set(FANATICISMS)
    chosen = {kind for kind, spec in FANATICISMS.items() if spec.favoured_by or spec.orthodox or spec.fallback_rank is not None}
    assert chosen == set(FanaticismKind)
    for kind, spec in FANATICISMS.items():
        assert kind in fanaticism_order(spec.favoured_by, spec.orthodox)


def test_a_church_turns_first_to_what_its_tenets_favour_and_never_to_what_they_bar() -> None:
    order = fanaticism_order(frozenset({TenetKind.MARTYRDOM_GLORY, TenetKind.PACIFISM}), False)
    assert order[0] is FanaticismKind.MARTYRDOM
    assert FanaticismKind.CRUSADE not in order
    assert fanaticism_order(frozenset(), False) == [FanaticismKind.ICONOCLASM, FanaticismKind.INQUISITION, FanaticismKind.CRUSADE]


async def test_a_purge_drives_heretics_from_the_church_s_towns(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    sect = await make_entity(session, "Sect of the Ash", EntityType.CULT, world_id=world.world.id, location_id=ours.town.id, stats=CultStats(followers=10))
    session.add(HeresyRow(heresy_entity_id=sect.id, parent_entity_id=ours.cult.id, declared_epoch=1, suppressed=True, locked=[]))
    heretic = await mortal(session, world, ours.town, "Odran")
    await bond(session, heretic.id, sect.id, BondKind.MEMBER_OF)
    await make_entity(session, "Farstead", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats())
    await session.flush()
    line = await purge(ctx, await church_of(session, ours))
    assert line is not None and line.key == "faith.purge"
    assert heretic.location_id != ours.town.id


async def test_forced_conversion_moves_unbelievers_to_the_church_s_god(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    other = await unbeliever(session, world, ours, "Vessa")
    line = await forced_conversion(ctx, await church_of(session, ours))
    assert line is not None and await worshipped(session, other.id) == {ours.god.id}


async def test_a_martyr_dies_and_the_church_grows_in_zeal_and_devotion(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    martyr = await devout(session, world, ours, "Teo")
    zeal, devotion = stat(ours.cult, "zeal") or 0, stat(ours.cult, "devotion") or 0
    line = await martyrdom(ctx, await church_of(session, ours))
    assert line is not None and martyr.status is not EntityStatus.CANON
    assert (stat(ours.cult, "zeal") or 0) > zeal and (stat(ours.cult, "devotion") or 0) == devotion + rules.zeal.martyr_devotion


async def test_mortification_harms_the_devout_and_raises_devotion(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    penitent = await devout(session, world, ours, "Aru")
    hp = stat(penitent, "hp")
    line = await mortification(ctx, await church_of(session, ours))
    assert line is not None and (stat(ours.cult, "devotion") or 0) == rules.zeal.mortification_devotion
    assert penitent.status is EntityStatus.CANON and (hp is None or (stat(penitent, "hp") or 0) <= hp)


async def test_fanatics_burn_written_works_and_the_town_loses_literacy(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    work = await make_entity(session, "Annals", EntityType.ARTWORK, world_id=world.world.id, location_id=ours.town.id, stats=ArtworkStats())
    session.add(WrittenWorkRow(work_entity_id=work.id, medium=WritingMedium.CLAY_TABLET, locked=[]))
    session.add(DemographicTransitionRow(community_entity_id=ours.town.id, literacy=30, locked=[]))
    await session.flush()
    line = await book_burning(ctx, await church_of(session, ours))
    assert line is not None and work.status is EntityStatus.DESTROYED
    transition = await session.get(DemographicTransitionRow, ours.town.id)
    assert transition is not None and transition.literacy == 30 - rules.zeal.book_burning_literacy


async def test_persecution_harries_unbelievers_and_unsettles_their_town(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    await unbeliever(session, world, ours, "Vessa")
    session.add(SettlementProfileRow(settlement_entity_id=ours.town.id, size_tier=SizeTier.TOWN, crime=10, unrest=10, locked=[], foreigners={}))
    await session.flush()
    prosperity = stat(ours.town, "prosperity") or 0
    line = await persecution(ctx, await church_of(session, ours))
    profile = await session.get(SettlementProfileRow, ours.town.id)
    assert line is not None and (stat(ours.town, "prosperity") or 0) < prosperity
    assert profile is not None and profile.unrest == 10 + rules.zeal.persecution_unrest


async def test_millenarian_followers_leave_their_work_for_the_holy_place(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    seeker = await devout(session, world, ours, "Mira")
    shrine = await make_entity(session, "High Shrine", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats())
    session.add(CultHoldingRow(cult_entity_id=ours.cult.id, holding_entity_id=shrine.id, kind=HoldingKind.HOLY_PLACE, since_epoch=1))
    await session.flush()
    prosperity = stat(ours.town, "prosperity") or 0
    line = await millenarian_flight(ctx, await church_of(session, ours))
    assert line is not None and seeker.location_id == shrine.id
    assert (stat(ours.town, "prosperity") or 0) < prosperity


async def test_a_fanatic_church_turns_to_the_fanaticism_its_tenets_favour(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, replace(rules, zeal=replace(rules.zeal, fanaticism_chance=100)))
    ours = await faithful(session, world, tenets=(TenetKind.MARTYRDOM_GLORY,), name="Ilun")
    await devout(session, world, ours, "Teo")
    set_stats(ours.cult, zeal=95, devotion=1000)
    await session.flush()
    line = await fanaticism(ctx, await church_of(session, ours), await FaithBook.load(session), await RegionAtlas.load(session))
    assert line is not None and line.key == "faith.martyrdom"
    assert ours.doctrine.fanaticism is FanaticismKind.MARTYRDOM


async def test_a_held_follower_is_left_alone(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    ctx = tick(session, rules)
    ours = await faithful(session, world, name="Ilun")
    kept = await devout(session, world, ours, "Kept")
    token = HELD_SCOPE.set(HeldScope(None, frozenset({kept.id})))
    try:
        church = await church_of(session, ours)
        assert await followers(ctx, church) == []
        assert await mortification(ctx, church) is None
    finally:
        HELD_SCOPE.reset(token)
    assert kept.status is EntityStatus.CANON
