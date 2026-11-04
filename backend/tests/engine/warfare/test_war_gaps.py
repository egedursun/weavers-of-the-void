from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.society import ReverenceRow
from aerona.db.tables.warfare import BattleRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.war import BattleOutcome, SiegeStatus, WarEnding
from aerona.domain.models.entity_stats import NaturalLawStats
from aerona.engine.phases.warfare import Theatre, campaigns, fight_battle, grant_victory, order_duel
from aerona.engine.services.war import OngoingWar, army_or_raise, declare_war, open_war
from aerona.rules.registry import Rules
from tests.db.factories import make_son
from tests.engine.warfare.factories import bond, make, make_ctx, society, tune

QUIET = {
    "battle_die": 1,
    "duel_chance": 0,
    "capture_chance": 0,
    "four_battle_exhaustion_chance": 0,
    "decisive_score": 50,
    "exhaustion_victory_margin": 50,
    "great_victory_diff": 1000,
}


async def chronicle_keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def siege_round(session: AsyncSession, world_id: int, rules: Rules, *, attacker_strong: bool) -> tuple[BattleOutcome, SiegeRow, WarRow]:
    ctx = make_ctx(session, rules)
    if attacker_strong:
        attacker = await make(session, "Horde", EntityType.PEOPLE, world_id, population=20000, martiality=95)
        city = await make(session, "Walltown", EntityType.SETTLEMENT, world_id, population=1000, defense=60, prosperity=50)
    else:
        attacker = await make(session, "Rabble", EntityType.PEOPLE, world_id, population=300, martiality=5)
        city = await make(session, "Walltown", EntityType.SETTLEMENT, world_id, population=20000, defense=95, prosperity=50)
    war = await open_war(ctx, attacker, city)
    theatre = await Theatre.load(ctx)
    armies = {side.id: await army_or_raise(ctx, theatre.strength, theatre.sides, side, war) for side in (attacker, city)}
    report = await fight_battle(ctx, theatre, OngoingWar(war, attacker.id, city.id), armies)
    assert report is not None
    siege = await session.scalar(select(SiegeRow))
    assert siege is not None
    return report.outcome, siege, war


async def test_siege_is_repulsed_when_the_defender_wins(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET})
    outcome, siege, war = await siege_round(session, world_id, rules, attacker_strong=False)
    assert outcome is BattleOutcome.SIEGE_REPULSED
    assert siege.status is SiegeStatus.REPULSED and siege.ended_epoch == 10
    assert war.score == -1
    battle = await session.scalar(select(BattleRow))
    assert battle is not None and battle.outcome is BattleOutcome.SIEGE_REPULSED and battle.siege_id == siege.id
    assert "war.battle.siege_repulsed" in await chronicle_keys(session)


async def test_siege_breaches_the_walls_when_the_breach_chance_is_certain(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "breach_min_pct": 100, "breach_max_pct": 100})
    outcome, siege, war = await siege_round(session, world_id, rules, attacker_strong=True)
    assert outcome is BattleOutcome.SIEGE_BREACHED
    assert siege.status is SiegeStatus.BREACHED
    assert war.score == rules.campaigns.breach_war_score
    assert "war.battle.siege_breached" in await chronicle_keys(session)


async def test_breach_costs_the_besieged_defense(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "breach_min_pct": 100, "breach_max_pct": 100})
    await siege_round(session, world_id, rules, attacker_strong=True)
    town = await session.scalar(select(SiegeRow.besieged_entity_id))
    assert town is not None
    entity = await EntityRepository(session).get(town)
    assert entity is not None and entity.stats.model_dump()["defense"] == 60 - rules.campaigns.breach_defense_loss


async def war_ban_law(session: AsyncSession, world_id: int) -> None:
    await EntityRepository(session).create(
        EntityDraft(
            name="Peace of Ash",
            entity_type=EntityType.NATURAL_LAW,
            description="No war.",
            stats=NaturalLawStats(),
            power_level=5,
            origin=EntityOrigin.SON,
            birth_epoch=1,
            world_id=world_id,
            natural_law=NaturalLaw.WAR_BAN,
            split_title=False,
        )
    )


async def hostile_pair(session: AsyncSession, world_id: int, rules: Rules) -> None:
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, martiality=10)
    await declare_war(make_ctx(session, rules), first.id, second.id, "grudge")


async def test_war_ban_law_lowers_the_chance_that_a_war_breaks_out(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "battle_chance": 100, "battle_chance_war_ban": 0})
    await hostile_pair(session, world_id, rules)
    await war_ban_law(session, world_id)
    await campaigns(make_ctx(session, rules))
    assert await session.scalar(select(func.count()).select_from(WarRow)) == 0
    assert "war.outbreak" not in await chronicle_keys(session)


async def test_without_a_war_ban_the_same_hostility_opens_a_war(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "battle_chance": 100, "battle_chance_war_ban": 0})
    await hostile_pair(session, world_id, rules)
    await campaigns(make_ctx(session, rules))
    assert await session.scalar(select(func.count()).select_from(WarRow)) == 1
    assert "war.outbreak" in await chronicle_keys(session)


async def test_duel_without_death_wounds_the_loser(session: AsyncSession, world_id: int) -> None:
    rules = tune(
        Rules(),
        campaigns={**QUIET, "duel_death_chance": 0, "duel_die": 1},
        duels={"yield_honour": -100, "mercy_spare": 100, "disarm_chance": 0, "exchanges_min": 20, "exchanges_max": 20},
    )
    ctx = make_ctx(session, rules)
    champion = await make(session, "Bren", EntityType.MORTAL, world_id, strength=95, agility=60, hp=100, age=30)
    victim = await make(session, "Tam", EntityType.MORTAL, world_id, strength=5, agility=5, hp=100, age=30)
    text = await order_duel(ctx, champion.id, victim.id)
    assert "Tam was crippled" in text
    assert victim.status is EntityStatus.CANON and champion.status is EntityStatus.CANON
    assert victim.stats.model_dump()["hp"] == 100 - rules.campaigns.duel_loser_hp_loss
    assert champion.stats.model_dump()["hp"] == 100
    assert await BondRepository(session).exists_between(champion.id, victim.id, BondKind.RIVAL)
    assert "war.duel_decree" in await chronicle_keys(session)


async def conquest_scene(session: AsyncSession, world_id: int, rules: Rules) -> tuple[int, int, int, int, WarRow]:
    ctx = make_ctx(session, rules)
    victor_god = await make_son(session, "Varos", world_id)
    loser_god = await make_son(session, "Ithren", world_id)
    victor = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    loser = await make(session, "Walltown", EntityType.SETTLEMENT, world_id, population=1000, defense=40)
    await bond(session, victor.id, victor_god.id, BondKind.WORSHIPS)
    await bond(session, loser.id, loser_god.id, BondKind.WORSHIPS)
    await society(session, victor.id)
    await society(session, loser.id)
    war = await open_war(ctx, victor, loser)
    return victor.id, loser.id, victor_god.id, loser_god.id, war


async def test_conquest_converts_the_loser_to_the_victors_god(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"conquest_conversion_chance": 100, "conquest_syncretism_pct": 0})
    victor, loser, victor_god, loser_god, war = await conquest_scene(session, world_id, rules)
    settlement = await grant_victory(make_ctx(session, rules), war.id, victor)
    assert settlement.ending is WarEnding.CONQUEST
    assert any("converted to the faith of Varos" in note for note in settlement.notes)
    bonds = BondRepository(session)
    assert await bonds.active_between(loser, victor_god, [BondKind.WORSHIPS])
    assert not await bonds.active_between(loser, loser_god, [BondKind.WORSHIPS])
    assert await bonds.exists_between(victor, loser, BondKind.RULES)


async def test_syncretic_conquest_adds_a_reverence_and_keeps_the_old_god(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"conquest_conversion_chance": 100, "conquest_syncretism_pct": 100})
    victor, loser, victor_god, loser_god, war = await conquest_scene(session, world_id, rules)
    settlement = await grant_victory(make_ctx(session, rules), war.id, victor)
    assert any("beside its own god" in note for note in settlement.notes)
    assert await session.get(ReverenceRow, (loser, victor_god)) is not None
    assert await BondRepository(session).active_between(loser, loser_god, [BondKind.WORSHIPS])


async def test_no_conversion_when_the_chance_is_zero(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={"conquest_conversion_chance": 0})
    victor, loser, victor_god, loser_god, war = await conquest_scene(session, world_id, rules)
    settlement = await grant_victory(make_ctx(session, rules), war.id, victor)
    assert not settlement.notes or all("faith" not in note for note in settlement.notes)
    assert await BondRepository(session).active_between(loser, loser_god, [BondKind.WORSHIPS])
    assert not await BondRepository(session).active_between(loser, victor_god, [BondKind.WORSHIPS])
