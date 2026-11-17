from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.aspirations import FEARS, GOALS
from aerona.catalog.peoples import VALUE_STYLE, Style
from aerona.db.kind_concepts.culture import BUILT_INS
from aerona.db.session import Database
from aerona.db.tables.culture_kinds import AimKindRow, FearKindRow, ReadingKindRow, TenetKindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.mind import DreamRow, FacetRow, FearRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ArtMode, IdeologyTenet
from aerona.domain.enums.culture_kinds import TenetScope
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.kinds import KindConcept, KindStance
from aerona.domain.enums.mind import DreamKind, DreamReading, Facet, FearKind, IdeaKind, LifeGoal, ValueAxis, ValueHolder
from aerona.domain.models.entity_stats import MortalStats, PeopleStats, SettlementStats
from aerona.engine.demography.peoples import style_columns
from aerona.engine.kinds.culture_life import ensure_culture_built_ins, keep_culture_kinds
from aerona.engine.lore.style import favoured_modes, image_mode, style_fit
from aerona.engine.mind.aspirations import choose_goal, seed_fears
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.dreams import read_into
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.cosmos.factories import Cosmos, make_entity, seed_cosmos, tick
from tests.tools.factories import connect


@pytest.fixture
async def session(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[AsyncSession]:
    database: Database = open_database(tmp_path / "culture_kinds.db")
    async with database.write() as found:
        yield found
    await database.dispose()


@pytest.fixture
async def cosmos(session: AsyncSession) -> Cosmos:
    return await seed_cosmos(session)


async def folk_and_mortal(session: AsyncSession, cosmos: Cosmos) -> tuple[EntityRow, EntityRow]:
    people = await make_entity(session, "Orrin", EntityType.PEOPLE, PeopleStats(population=4000), world_id=cosmos.home.id)
    town = await make_entity(session, "Vessa", EntityType.SETTLEMENT, SettlementStats(population=900, prosperity=40), world_id=cosmos.home.id)
    await connect(session, town.id, people.id, BondKind.DESCENDS_FROM)
    mortal = await make_entity(session, "Iska", EntityType.MORTAL, MortalStats(), world_id=cosmos.home.id, location_id=town.id)
    await session.flush()
    return people, mortal


async def hold(session: AsyncSession, concept: KindConcept, kind_id: int, holder_id: int, strength: int = 100) -> None:
    session.add(KindHoldingRow(concept=concept, kind_id=kind_id, holder_node_id=holder_id, stance=KindStance.USES, strength=strength, locked=[]))
    await session.flush()


async def test_every_legacy_value_is_a_built_in_kind(session: AsyncSession, cosmos: Cosmos) -> None:
    await ensure_culture_built_ins(session)
    tenets = len(IdeaKind) + len(IdeologyTenet) + len(TenetKind)
    expected = {TenetKindRow: tenets, FearKindRow: len(FearKind), ReadingKindRow: len(DreamReading), AimKindRow: len(LifeGoal)}
    for table, count in expected.items():
        assert await session.scalar(select(func.count()).select_from(table).where(table.built_in.is_(True))) == count
    assert await ensure_culture_built_ins(session) == 0
    assert {table: len(rows) for table, rows in BUILT_INS} == expected


async def test_a_held_tenet_moves_its_people_s_values(session: AsyncSession, cosmos: Cosmos) -> None:
    people, _ = await folk_and_mortal(session, cosmos)
    await write_values(session, ValueHolder.CULTURE, people.id, {ValueAxis.MERCY: 0})
    tenet = TenetKindRow(name="Mercy above all", category=TenetScope.IDEA, value_axis=ValueAxis.MERCY, value_delta=40, locked=[])
    session.add(tenet)
    await session.flush()
    await hold(session, KindConcept.TENET, tenet.id, people.id)
    tally = await keep_culture_kinds(tick(session, Rules()))
    assert tally.tenets == 1
    assert (await stored_values(session, ValueHolder.CULTURE, people.id))[ValueAxis.MERCY] > 0


async def test_a_held_tenet_spares_a_held_people(session: AsyncSession, cosmos: Cosmos) -> None:
    people, _ = await folk_and_mortal(session, cosmos)
    await write_values(session, ValueHolder.CULTURE, people.id, {ValueAxis.MERCY: 0})
    tenet = TenetKindRow(name="Mercy above all", category=TenetScope.IDEA, value_axis=ValueAxis.MERCY, value_delta=40, locked=[])
    session.add(tenet)
    await session.flush()
    await hold(session, KindConcept.TENET, tenet.id, people.id)
    token = HELD_SCOPE.set(HeldScope(None, frozenset({people.id})))
    try:
        await keep_culture_kinds(tick(session, Rules()))
    finally:
        HELD_SCOPE.reset(token)
    assert (await stored_values(session, ValueHolder.CULTURE, people.id))[ValueAxis.MERCY] == 0


async def test_a_held_fear_kind_is_taken_by_its_mortals(session: AsyncSession, cosmos: Cosmos) -> None:
    people, mortal = await folk_and_mortal(session, cosmos)
    session.add(FacetRow(node_id=mortal.id, facet=Facet.IMAGINATION, value=50))
    fear = FearKindRow(name="The quiet", category=FearKind.DARK, grip=90, facet=Facet.IMAGINATION, facet_weight=100, locked=[])
    session.add(fear)
    await session.flush()
    await hold(session, KindConcept.FEAR, fear.id, people.id)
    await seed_fears(tick(session, Rules()), mortal)
    taken = {row.kind: row.fear_kind_id for row in await session.scalars(select(FearRow).where(FearRow.holder_node_id == mortal.id))}
    assert taken[FearKind.DARK] == fear.id
    assert FEARS[FearKind.DARK].label


async def test_a_held_aim_draws_a_mortal_to_its_goal(session: AsyncSession, cosmos: Cosmos) -> None:
    people, mortal = await folk_and_mortal(session, cosmos)
    aim = AimKindRow(name="The long road", category=LifeGoal.SEE_THE_WORLD, pull=100, locked=[])
    session.add(aim)
    await session.flush()
    await hold(session, KindConcept.AIM, aim.id, people.id)
    rules = Rules()
    goal, _ = await choose_goal(tick(session, rules), mortal)
    assert goal is LifeGoal.SEE_THE_WORLD
    assert GOALS[goal].label


async def test_a_culture_s_own_reading_moves_the_dreamer_by_its_lean(session: AsyncSession, cosmos: Cosmos) -> None:
    people, mortal = await folk_and_mortal(session, cosmos)
    await write_values(session, ValueHolder.PERSONAL, mortal.id, {ValueAxis.FAMILY: 0})
    reading = ReadingKindRow(name="The calling home", category=DreamReading.CALL_TO_LOVE, valence=60, value_axis=ValueAxis.FAMILY, lean=20, locked=[])
    session.add(reading)
    await session.flush()
    await hold(session, KindConcept.DREAM_READING, reading.id, people.id)
    dream = DreamRow(dreamer_node_id=mortal.id, kind=DreamKind.LONGING, epoch=1, intensity=60, content=[], reading=DreamReading.CALL_TO_LOVE)
    session.add(dream)
    await session.flush()
    await read_into(tick(session, Rules()), mortal, dream)
    assert dream.reading_kind_id == reading.id
    assert (await stored_values(session, ValueHolder.PERSONAL, mortal.id)).get(ValueAxis.FAMILY, 0) > 0


def test_style_axes_choose_and_weigh_art_forms() -> None:
    rules = Rules()
    ornate = Style(ornament=95, geometry=50, colour=90, scale=50, symmetry=50)
    plain = Style(ornament=5, geometry=50, colour=5, scale=50, symmetry=50)
    assert ArtMode.TEXTILE_IMAGE in favoured_modes(ornate, rules.customs.style_modes)
    assert style_fit(rules, ornate, ArtMode.TEXTILE_IMAGE) > style_fit(rules, plain, ArtMode.TEXTILE_IMAGE)
    assert image_mode(ornate) in {ArtMode.FLAT_IMAGE, ArtMode.TEXTILE_IMAGE}
    assert style_fit(rules, None, ArtMode.VERBAL) == 1.0


def test_a_people_s_style_axes_follow_its_values() -> None:
    base = VALUE_STYLE[ValueAxis.WEALTH]
    richer = style_columns({ValueAxis.WEALTH: 80})
    assert richer["ornament"] > base.ornament
    assert set(richer) == {"ornament", "geometry", "colour", "scale", "symmetry"}
