from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.war import BattleOutcome, CaptiveStatus, SiegeStatus, WarEnding, WarStatus
from aerona.engine.phases.warfare import Theatre, campaigns, fight_battle, force_battle, redirect_uprisings, war_upkeep
from aerona.engine.services.community_relations import has_blood_feud, relation
from aerona.engine.services.war import OngoingWar, army_or_raise, declare_war, open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx, tune

QUIET = {
    "battle_die": 1,
    "duel_chance": 0,
    "capture_chance": 0,
    "four_battle_exhaustion_chance": 0,
    "decisive_score": 50,
    "exhaustion_victory_margin": 50,
    "great_victory_diff": 1000,
    "seasons_per_war_epoch": 0,
}


async def test_new_war_mobilises_then_clashes_next_epoch(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "battle_chance": 100})
    strong = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    weak = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000, martiality=60)
    first_ctx = make_ctx(session, rules, epoch=10)
    await declare_war(first_ctx, strong.id, weak.id, "old grudge")
    await campaigns(first_ctx)
    war = await session.scalar(select(WarRow))
    assert war is not None and war.status is WarStatus.MOBILIZING and war.battles == 0
    assert len(list(await session.scalars(select(ArmyRow)))) == 2
    second_ctx = make_ctx(session, rules, epoch=11)
    await campaigns(second_ctx)
    await session.refresh(war)
    assert war.status.value == WarStatus.ONGOING.value and war.battles == 1 and war.last_clash_epoch == 11
    battle = await session.scalar(select(BattleRow))
    assert battle is not None and battle.winner_entity_id == strong.id and battle.outcome is BattleOutcome.FIELD_VICTORY
    assert war.score >= 0 and battle.outcome_class is not None
    assert await relation(session, rules, strong.id, weak.id) < 0
    texts = [row.text for row in await session.scalars(select(ChronicleRow).order_by(ChronicleRow.id))]
    assert any(text.startswith("War broke out between Iron Folk and Reed Folk") for text in texts)


async def test_a_war_takes_the_field_after_its_first_epoch_even_when_its_armies_never_meet(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "battle_chance": 100})
    strong = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    weak = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000, martiality=60)
    first_ctx = make_ctx(session, rules, epoch=10)
    await declare_war(first_ctx, strong.id, weak.id, "old grudge")
    await campaigns(first_ctx)
    war = await session.scalar(select(WarRow))
    assert war is not None and war.status is WarStatus.MOBILIZING
    quiet = tune(Rules(), campaigns={**QUIET, "battle_chance": 0})
    await campaigns(make_ctx(session, quiet, epoch=11))
    await session.refresh(war)
    assert war.status.value == WarStatus.ONGOING.value and war.battles == 0


async def test_rout_ends_war_with_tribute(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "disband_morale": 100, "tribute_conversion_chance": 0})
    ctx = make_ctx(session, rules)
    strong = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    weak = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, martiality=10)
    await declare_war(ctx, strong.id, weak.id, "grudge")
    war = await open_war(ctx, strong, weak)
    report = await force_battle(ctx, war.id)
    assert report.settlement is not None and report.settlement.ending is WarEnding.TRIBUTE
    assert war.status is WarStatus.ENDED
    assert await BondRepository(session).exists_between(weak.id, strong.id, BondKind.PAYS_TRIBUTE)
    armies = list(await session.scalars(select(ArmyRow)))
    assert all(army.disbanded_epoch == ctx.epoch for army in armies)


async def test_siege_starvation_costs_the_attacker_morale(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "breach_min_pct": 0, "breach_max_pct": 0, "siege_attacker_morale_loss": 9, "winner_morale_gain": 0})
    ctx = make_ctx(session, rules)
    horde = await make(session, "Horde", EntityType.PEOPLE, world_id, population=9000, martiality=60)
    city = await make(session, "Walltown", EntityType.SETTLEMENT, world_id, population=6000, defense=60, prosperity=50)
    war = await open_war(ctx, horde, city)
    theatre = await Theatre.load(ctx)
    armies = {side.id: await army_or_raise(ctx, theatre.strength, theatre.sides, side, war) for side in (horde, city)}
    morale_before = armies[horde.id][0].stats.model_dump()["morale"]
    report = await fight_battle(ctx, theatre, OngoingWar(war, horde.id, city.id), armies)
    assert report is not None and report.outcome is BattleOutcome.SIEGE_STARVATION
    assert armies[horde.id][0].stats.model_dump()["morale"] <= morale_before - 9
    assert city.stats.model_dump()["population"] < 6000
    siege = await session.scalar(select(SiegeRow))
    assert siege is not None and siege.status is SiegeStatus.ONGOING and siege.rounds == 1
    assert report.record is not None and report.record.name.startswith("Siege of")


async def test_capture_takes_a_hero_prisoner_with_synced_bond(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**QUIET, "capture_chance": 100}, tactics={"scouting_margin": 1000})
    ctx = make_ctx(session, rules)
    strong = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    weak = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, martiality=10)
    hero = await make(session, "Tam", EntityType.MORTAL, world_id, strength=30, age=25)
    await bond(session, hero.id, weak.id, BondKind.PROTECTS)
    war = await open_war(ctx, strong, weak)
    await force_battle(ctx, war.id)
    captive = await session.scalar(select(CaptiveRow))
    assert captive is not None and captive.captive_entity_id == hero.id and captive.status is CaptiveStatus.HELD
    assert await BondRepository(session).exists_between(strong.id, hero.id, BondKind.HOLDS_CAPTIVE)


async def test_duel_to_the_death_starts_a_blood_feud(session: AsyncSession, world_id: int) -> None:
    rules = tune(
        Rules(),
        campaigns={**QUIET, "duel_chance": 100, "duel_death_chance": 100, "duel_die": 1},
        duels={"yield_honour": -100, "mercy_spare": 100, "disarm_chance": 0, "exchanges_min": 20, "exchanges_max": 20},
    )
    ctx = make_ctx(session, rules)
    strong = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000, martiality=90)
    weak = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, martiality=10)
    champion = await make(session, "Bren", EntityType.MORTAL, world_id, strength=90, age=30)
    victim = await make(session, "Tam", EntityType.MORTAL, world_id, strength=10, age=30)
    await bond(session, champion.id, strong.id, BondKind.PROTECTS)
    await bond(session, victim.id, weak.id, BondKind.PROTECTS)
    war = await open_war(ctx, strong, weak)
    await force_battle(ctx, war.id)
    assert victim.status is EntityStatus.DEAD
    assert await has_blood_feud(session, strong.id, weak.id)


async def test_upkeep_ends_wars_with_subjects_and_redirects_uprisings(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    overlord = await make(session, "Empire", EntityType.PEOPLE, world_id, population=9000)
    vassal = await make(session, "Vassal Town", EntityType.SETTLEMENT, world_id, population=400)
    await declare_war(ctx, overlord.id, vassal.id, "grudge")
    await bond(session, overlord.id, vassal.id, BondKind.RULES)
    king = await make(session, "King Oran", EntityType.MORTAL, world_id)
    realm = await make(session, "Realm", EntityType.SETTLEMENT, world_id, population=800)
    rebels = await make(session, "Red Rebels", EntityType.FACTION, world_id, strength=40)
    rebels.engine_kind = EngineKind.REBELS
    await bond(session, king.id, realm.id, BondKind.RULES)
    await bond(session, rebels.id, king.id, BondKind.ENEMY, epoch=4, description="tyranny")
    await war_upkeep(ctx)
    repository = BondRepository(session)
    assert not await repository.exists_between(overlord.id, vassal.id, BondKind.ENEMY)
    assert not await repository.exists_between(rebels.id, king.id, BondKind.ENEMY)
    redirected = await repository.active_between(rebels.id, realm.id, [BondKind.ENEMY])
    assert redirected and redirected[0].epoch == 4
    assert await redirect_uprisings(ctx) == 0
