from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.records import IncidentFactRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import BattleOutcome
from aerona.engine.phases.warfare import BattleReport, Theatre, fight_battle
from aerona.engine.services.war import OngoingWar, army_or_raise, open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, tune

QUIET = {"battle_die": 1, "duel_chance": 0, "capture_chance": 0, "four_battle_exhaustion_chance": 0, "decisive_score": 50, "exhaustion_victory_margin": 50}


async def meetings(session: AsyncSession, world_id: int, *, weak_attacker: bool, times: int) -> tuple[list[BattleReport], list[str], int, list[int]]:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET, tactics={"scouting_margin": 0}))
    sizes = (600, 9000) if weak_attacker else (9000, 600)
    attacker = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=sizes[0], martiality=50)
    defender = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=sizes[1], martiality=50)
    weak = attacker if weak_attacker else defender
    session.add(
        SpyNetworkRow(owner_entity_id=weak.id, target_entity_id=(defender if weak_attacker else attacker).id, intel=1000, since_epoch=ctx.epoch, locked=[])
    )
    war = await open_war(ctx, attacker, defender)
    theatre = await Theatre.load(ctx)
    armies = {side.id: await army_or_raise(ctx, theatre.strength, theatre.sides, side, war) for side in (attacker, defender)}
    reports = []
    for _ in range(times):
        report = await fight_battle(ctx, theatre, OngoingWar(war, attacker.id, defender.id), armies, forced=True)
        assert report is not None
        reports.append(report)
    kinds = list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.like("war.battle.%")).order_by(IncidentRow.id)))
    sequences = list(await session.scalars(select(BattleRow.sequence).where(BattleRow.war_id == war.id).order_by(BattleRow.id)))
    return reports, kinds, war.battles, sequences


async def test_a_battle_refused_is_no_battle_fought_and_each_meeting_keeps_its_own_number(session: AsyncSession, world_id: int) -> None:
    reports, kinds, fought, sequences = await meetings(session, world_id, weak_attacker=False, times=2)
    assert reports[0].outcome is BattleOutcome.REFUSED
    assert kinds[0] == "war.battle.refused"
    assert fought == sum(1 for report in reports if report.outcome is not BattleOutcome.REFUSED)
    assert sequences == [1, 2]


async def test_an_attacker_that_draws_back_is_not_told_as_the_one_who_was_marched_on(session: AsyncSession, world_id: int) -> None:
    reports, kinds, fought, _ = await meetings(session, world_id, weak_attacker=True, times=1)
    assert reports[0].outcome is BattleOutcome.REFUSED
    assert fought == 0
    assert kinds == ["war.battle.withheld"]


async def test_only_the_wounded_come_home_maimed(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), campaigns=QUIET))
    attacker = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=600, martiality=50)
    defender = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=9000, martiality=50)
    war = await open_war(ctx, attacker, defender)
    theatre = await Theatre.load(ctx)
    armies = {side.id: await army_or_raise(ctx, theatre.strength, theatre.sides, side, war) for side in (attacker, defender)}
    report = await fight_battle(ctx, theatre, OngoingWar(war, attacker.id, defender.id), armies, forced=True)
    assert report is not None and report.outcome is not BattleOutcome.REFUSED
    told = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "battle.casualties"))
    wounded = await session.scalar(select(IncidentFactRow.number).where(IncidentFactRow.incident_id == told, IncidentFactRow.key == "wounded"))
    maimed = sum(row.count for row in await session.scalars(select(MaimedCohortRow)))
    battle = await session.scalar(select(BattleRow))
    assert battle is not None and wounded is not None
    assert battle.winner_losses + battle.loser_losses > wounded
    sides = 2
    assert maimed <= wounded * ctx.rules.maimed.return_pct / PERCENT + sides / 2
