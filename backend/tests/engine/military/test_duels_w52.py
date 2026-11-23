from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.ethics import DUEL_END_LABELS, HONOUR_MODELS
from aerona.catalog.life.phases import DUEL_ENDINGS, DUEL_FATES
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import CultureHonourRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.mind import HonourModel
from aerona.domain.models.entity_stats import PeopleStats, TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.military.duels import Fighter, bout
from aerona.engine.mind.ethics import duel_end_of
from aerona.engine.phases.vendettas import ritual_duels
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


def fighter(ident: int, *, hp: int = 100, footing: int = 100, mercy: int = 0) -> Fighter:
    body = EntityRow(id=ident, name=f"Fighter {ident}", entity_type=EntityType.MORTAL)
    return Fighter(entity=body, power=10.0, hp=hp, armour=0, reach=1, honour=50, mercy=mercy, footing=footing)


def stream(key: str) -> SeededRandom:
    return SeededRandom(RandomKey(5, 3, key))


def test_every_ending_has_a_fate_a_line_and_a_label() -> None:
    assert set(DUEL_FATES) == set(DUEL_ENDINGS) == set(DUEL_END_LABELS) == set(DuelEnd)
    assert {spec.duel_end for spec in HONOUR_MODELS.values()} >= {DuelEnd.FIRST_WOUND, DuelEnd.RING_OUT}


def test_a_duel_to_the_first_wound_ends_at_the_first_harm_and_no_one_dies() -> None:
    rules = tuned_rules(duels={"exchanges_min": 30, "exchanges_max": 30})
    for seed in range(12):
        result = bout(rules, stream(f"first.{seed}"), fighter(1), fighter(2), DuelContext.HONOUR, ending=DuelEnd.FIRST_WOUND)
        if result.end is DuelEnd.FIRST_WOUND:
            assert result.loser.harm > 0 and not result.killed and result.loser.harm < result.loser.hp
            return
    raise AssertionError("no duel to the first wound ended at a wound")


def test_a_fighter_who_loses_footing_is_driven_out_of_the_bounds() -> None:
    rules = tuned_rules(duels={"ring_footing": 100})
    result = bout(rules, stream("ring"), fighter(1), fighter(2, footing=90), DuelContext.RITUAL, ending=DuelEnd.RING_OUT)
    assert result.end is DuelEnd.RING_OUT and not result.killed


def test_a_ritual_duel_is_rarely_to_the_death() -> None:
    lethal = tuned_rules(campaigns={"duel_death_chance": 100}, duels={"ritual_death_pct": 0, "exchanges_min": 30, "exchanges_max": 30, "mercy_spare": 100})
    for seed in range(8):
        result = bout(lethal, stream(f"ritual.{seed}"), fighter(1, hp=20), fighter(2, hp=20), DuelContext.RITUAL)
        assert not result.killed
    assert any(bout(lethal, stream(f"war.{seed}"), fighter(1, hp=20), fighter(2, hp=20), DuelContext.WAR).killed for seed in range(8))


async def test_a_culture_sets_its_ending_by_its_honour_model_unless_the_god_sets_another(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "Shore Folk", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    session.add(CultureHonourRow(entity_id=folk.id, model=HonourModel.FACE, locked=[]))
    await session.flush()
    assert await duel_end_of(session, folk.id) is HONOUR_MODELS[HonourModel.FACE].duel_end
    row = await session.get(CultureHonourRow, folk.id)
    assert row is not None
    row.duel_end = DuelEnd.DEATH
    assert await duel_end_of(session, folk.id) is DuelEnd.DEATH
    assert await duel_end_of(session, None) is HONOUR_MODELS[HonourModel.DIGNITY].duel_end


async def test_a_town_that_keeps_a_duel_custom_marks_a_passage_with_a_ritual_duel(session: AsyncSession, world: CoreWorld) -> None:
    ctx: TickContext = await manual_context(session, "ritual", rules=tuned_rules(duels={"ritual_pct": 100}))
    town = await settlement(session, "Ringhold", world, world.regions[0])
    custom = await entity(session, "The Circle Bout", EntityType.TRADITION, TraditionStats(), world_id=world.world.id)
    session.add(TraditionProfileRow(tradition_entity_id=custom.id, kind=TraditionFunction.DUEL_CUSTOM, cost={}, effects={}, locked=[]))
    await bond(session, town.id, custom.id, BondKind.CELEBRATES)
    first = await mortal(session, "Ama", world, town.id, age=18)
    second = await mortal(session, "Tove", world, town.id, age=19)
    await mortal(session, "Old Ren", world, town.id, age=60)
    await session.flush()
    assert await ritual_duels(ctx) == 1
    fought = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "duel.fought"))
    assert fought is not None
    renowned = [await session.get(MortalProfileRow, one.id) for one in (first, second)]
    assert all(profile is not None and profile.renown > 0 for profile in renowned)
    assert Rules().duels.ritual_death_pct == 2
