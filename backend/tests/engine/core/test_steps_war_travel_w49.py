from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.military import BattlePhase, DefenderAction, OutcomeClass, SiegeAction, SiegeWork, Tactic, UnitKind
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepState
from aerona.domain.enums.relations import ContestKind, ContestStake
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.military.battle import BattleResult, PhaseLog, Side, StackChange
from aerona.engine.military.battle_record import battle_steps
from aerona.engine.military.duels import Fighter, blow_of
from aerona.engine.military.logistics import March
from aerona.engine.military.siege import SeasonMarks, SiegeSeason, season_steps
from aerona.engine.records import sweep_bonds_of_the_dead
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, build_realm, context, link, mortal, settlement, tuned


@pytest.fixture
async def realm(session: AsyncSession) -> Realm:
    return await build_realm(session)


async def steps_of(session: AsyncSession, key: str) -> list[IncidentStepRow]:
    incident = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == key).order_by(IncidentRow.id.desc()).limit(1))
    assert incident is not None, key
    return list(await session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident).order_by(IncidentStepRow.position)))


async def test_a_bow_shoots_a_thrown_weapon_is_thrown_and_a_blade_still_cuts(realm: Realm) -> None:
    hero = await mortal(realm, "Ina")
    archer = Fighter(entity=hero, power=10.0, hp=100, armour=0, reach=2, honour=0, mercy=0, weapon_id=hero.id, weapon_class=ItemClass.BOW)
    assert blow_of(archer, InstrumentKind.ITEM, DamageType.PIERCE) is StepAction.SHOOT
    assert blow_of(replace(archer, weapon_class=ItemClass.THROWING), InstrumentKind.ITEM, DamageType.PIERCE) is StepAction.THROW
    assert blow_of(replace(archer, weapon_class=ItemClass.BLADE), InstrumentKind.ITEM, DamageType.CUT) is StepAction.CUT
    assert blow_of(archer, InstrumentKind.BODY, DamageType.BLUNT) is StepAction.STRIKE


async def test_a_battle_tells_the_hidden_the_sprung_the_countered_the_fleeing_and_the_arms(realm: Realm) -> None:
    first, second = await settlement(realm, "Aber"), await settlement(realm, "Bryn")
    host, foe = await settlement(realm, "Caer"), await settlement(realm, "Dol")
    attacker = Side(first, host, ArmyProfileRow(), [], 1.0, False, 0, set(), tactic=Tactic.HOLD_LINE)
    defender = Side(second, foe, ArmyProfileRow(), [], 1.0, True, 0, set(), tactic=Tactic.FRONTAL_ASSAULT)
    struck = StackChange(host.id, foe.id, 7, UnitKind.LEVY, 12, -5, False, False, None)
    phases = [
        PhaseLog(BattlePhase.SCOUTING, 0, 0, "", {"attacker_hidden": 40}),
        PhaseLog(BattlePhase.PLAN, 0, 0, ""),
        PhaseLog(BattlePhase.MELEE, 3, 12, "", {"attacker_revealed": 40}, [struck]),
        PhaseLog(BattlePhase.PURSUIT, 0, 9, ""),
    ]
    result = BattleResult(attacker, defender, attacker, defender, False, OutcomeClass.VICTORY, 40.0, phases, {}, {}, {})
    steps = battle_steps(result, {}, arms={7: second.id})
    assert steps[0].states == ((host.id, StepState.HIDDEN),)
    countered = next(step for step in steps if step.action is StepAction.COUNTER)
    assert (countered.actor, countered.target, countered.instrument_key) == (host.id, foe.id, Tactic.HOLD_LINE.value)
    melee = next(step for step in steps if step.action is StepAction.ADVANCE and step.actor is None)
    assert melee.states == ((host.id, StepState.REVEALED),)
    armed = next(step for step in steps if step.actor == host.id and step.action is StepAction.ADVANCE)
    assert (armed.instrument_kind, armed.instrument_node) == (InstrumentKind.EQUIPMENT_MODEL, second.id)
    pursuit = next(step for step in steps if step.action is StepAction.PURSUE)
    assert pursuit.states == ((foe.id, StepState.FLEEING),)


async def test_a_blockade_cuts_a_town_off_a_closed_ring_encircles_it_and_rationing_counts_the_days(realm: Realm) -> None:
    town, army, owner = await settlement(realm, "Esk"), await settlement(realm, "Fen"), await settlement(realm, "Gwy")
    siege = SiegeRow(
        id=1,
        war_id=1,
        besieged_entity_id=town.id,
        besieger_entity_id=owner.id,
        status=SiegeStatus.ONGOING,
        rounds=2,
        supplies=37,
        water=20,
        breaches=0,
        works={SiegeWork.CIRCUMVALLATION.value: 100, "famine": 2},
    )
    found = SiegeSeason(siege, SiegeAction.BLOCKADE, DefenderAction.RATION)
    march = March(army, owner, ArmyProfileRow(), None, True)
    steps = season_steps(found, town, march, SeasonMarks(60, 60, 0, {SiegeWork.CIRCUMVALLATION.value: 80, "famine": 1}))
    assert steps[0].states == ((town.id, StepState.CUT_OFF),)
    raised = [step for step in steps if step.action is StepAction.RAISE]
    assert [step.instrument_key for step in raised] == [SiegeWork.CIRCUMVALLATION.value]
    assert raised[0].states == ((town.id, StepState.ENCIRCLED),)
    rationed = next(step for step in steps if step.actor == town.id)
    assert (rationed.amount, rationed.unit) == (37, FactUnit.DAYS)


async def test_a_contest_scores_every_round_and_names_the_loser(realm: Realm) -> None:
    ctx = context(realm.session, tuned(Rules(), contests={"jitter": 0}))
    town = await settlement(realm, "Hafod")
    first, second, judge = await mortal(realm, "Iolo", location_id=town.id), await mortal(realm, "Jac", location_id=town.id), await mortal(realm, "Lowri")
    realm.session.add(SkillRow(holder_node_id=first.id, skill=SkillKind.LORE, level=90, peak=90, last_used_epoch=1, source=SkillSource.PLAYER))
    await realm.session.flush()
    bout = Bout(ContestKind.RIDDLE_GAME, ContestStake.UNION, first, second, judge_id=judge.id, stake_node_id=judge.id, place_id=town.id)
    row = await hold_contest(ctx, bout, ContestTally())
    assert row is not None and row.outcome.value != "drawn"
    key = "contest.famous" if row.famous else "contest.won"
    steps = await steps_of(realm.session, key)
    scored = [step for step in steps if step.action is StepAction.SCORE]
    assert len(scored) == 2 * len(row.rounds) and all(step.unit is FactUnit.COUNT for step in scored)
    lost = next(step for step in steps if step.action is StepAction.LOSE)
    won = next(step for step in steps if step.action is StepAction.WIN)
    assert lost.actor_node_id == won.target_node_id


async def test_an_heir_succeeds_the_dead_to_what_they_ruled(realm: Realm) -> None:
    ctx = context(realm.session)
    town, held_land = await settlement(realm, "Llan"), await settlement(realm, "Maen")
    ruler = await mortal(realm, "Nest", location_id=town.id)
    await link(realm.session, ruler.id, held_land.id, BondKind.RULES)
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, ctx.epoch
    await realm.session.flush()
    await sweep_bonds_of_the_dead(ctx)
    steps = await steps_of(realm.session, "records.inheritance")
    assert [(step.action, step.actor_node_id, step.target_node_id) for step in steps] == [(StepAction.SUCCEED, town.id, ruler.id)]
