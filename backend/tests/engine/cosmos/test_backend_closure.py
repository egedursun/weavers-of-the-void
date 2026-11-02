from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow, GodConflictRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.society import ArchiveHoldingRow, ResurrectionOrderRow, SoulRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect
from aerona.domain.enums.intervention import Disaster, Miracle
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.son import Stat
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import (
    CultStats,
    KnowledgeStats,
    MortalStats,
    NaturalLawStats,
    PeopleStats,
    SettlementStats,
    SpiritStats,
)
from aerona.domain.models.stats import StatBlock
from aerona.engine.context import TickContext
from aerona.engine.cosmos.duels import son_duel
from aerona.engine.cosmos.foreign_gods import clean_existence, clean_powers, clean_stats
from aerona.engine.cosmos.routes import RouteBook
from aerona.engine.gods.interventions import apply_miracle
from aerona.engine.phases.afterlife import cosmic_archive, planetary_consciousness, realm_regions, soul_buildup, soul_descent, soul_harvest
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.phases.pantheon import attitude_drift, friendly_help, grow_power, rival_clashes, spontaneous_god_war
from aerona.engine.primitives.knowledge import LawBook
from aerona.language.titles import community_phrase
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick, tuned


async def keys(session: AsyncSession) -> list[str]:
    return [key for key in await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)) if key]


async def souls(session: AsyncSession, world_id: int, count: int) -> None:
    region = await make_region(session, f"Ash Shore {world_id}", world_id)
    for index in range(count):
        await make_entity(
            session,
            f"Shade {world_id}.{index}",
            EntityType.SPIRIT,
            SpiritStats(),
            world_id=world_id,
            location_id=region.id,
            engine_kind=EngineKind.DESCENDED_SOUL,
        )


async def test_only_a_crowded_realm_of_the_dead_gains_leak(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    threshold = rules.beyond.soul_buildup_threshold
    dead = await make_world(session, "Nethis", WorldType.DEAD)
    quiet = await make_world(session, "Lethe", WorldType.DEAD)
    ordinary = await make_world(session, "Velmor")
    await souls(session, dead.id, threshold)
    await souls(session, quiet.id, threshold - 1)
    await souls(session, ordinary.id, threshold)
    before = (dead.leakage, quiet.leakage, ordinary.leakage)
    await soul_buildup(tick(session, rules))
    assert dead.leakage == before[0] + rules.beyond.soul_buildup_leak
    assert (quiet.leakage, ordinary.leakage) == before[1:]


async def test_souls_never_descend_to_a_linked_realm_of_another_world(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beyond", soul_descent_chance=100))
    realm = await make_world(session, "Nethis", WorldType.DEAD)
    await make_region(session, "Ash Shore", realm.id)
    await make_route(session, cosmos.home.id, realm.id)
    dead = await make_entity(session, "Orrin", EntityType.MORTAL, MortalStats(age=60, lifespan=70), world_id=cosmos.home.id)
    await EntityRepository(session).set_status(dead, EntityStatus.DEAD, ctx.epoch)
    assert await realm_regions(session, cosmos.home) == []
    assert await soul_descent(ctx) == 0
    assert await session.scalar(select(SoulRow)) is None
    realm_native = await make_entity(session, "Velis", EntityType.MORTAL, MortalStats(age=60, lifespan=70), world_id=realm.id)
    await EntityRepository(session).set_status(realm_native, EntityStatus.DEAD, ctx.epoch)
    assert await soul_descent(ctx) == 1


async def test_a_zealous_cult_harvests_a_soul(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "beyond", soul_harvest_chance=100))
    region = await make_region(session, "Vale", cosmos.home.id)
    cult = await make_entity(
        session, "Bone Choir", EntityType.CULT, CultStats(followers=100, zeal=90, influence=40), world_id=cosmos.home.id, location_id=region.id
    )
    calm = await make_entity(
        session, "Quiet Choir", EntityType.CULT, CultStats(followers=100, zeal=10, influence=40), world_id=cosmos.home.id, location_id=region.id
    )
    soul = await make_entity(session, "Shade", EntityType.SPIRIT, SpiritStats(), world_id=cosmos.home.id, location_id=region.id)
    assert await soul_harvest(ctx) == 1
    beyond = rules.beyond
    assert soul.status is EntityStatus.DEAD
    assert cult.stats.model_dump()["followers"] == round(100 * beyond.soul_harvest_follower_mult_pct / 100)
    assert cult.stats.model_dump()["influence"] == 40 + beyond.soul_harvest_influence_gain
    assert await EntityRepository(session).has_flag(cult.id, EntityFlag.SOUL_HARVESTER)
    assert calm.stats.model_dump()["followers"] == 100
    assert "beyond.soul_harvest" in await keys(session)


async def test_planet_worship_happens_only_inside_the_planet_act_roll(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    living = await make_world(session, "Gaia", WorldType.LIVING)
    region = await make_region(session, "Moss", living.id)
    folk = await make_entity(session, "Mossfolk", EntityType.PEOPLE, PeopleStats(population=500), world_id=living.id, location_id=region.id)
    still = tuned(tuned(rules, "beyond", planet_acts_chance=0), "beyond", planet_worship_chance=100)
    await planetary_consciousness(tick(session, still))
    assert not await EntityRepository(session).has_flag(folk.id, EntityFlag.WORSHIPS_PLANET)
    acting = tuned(tuned(rules, "beyond", planet_acts_chance=100), "beyond", planet_worship_chance=100)
    await planetary_consciousness(tick(session, acting))
    assert await EntityRepository(session).has_flag(folk.id, EntityFlag.WORSHIPS_PLANET)
    assert "beyond.planet_worship" in await keys(session)


async def test_the_archive_appears_in_the_most_magical_region_and_is_read(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    second = await make_world(session, "Velmor")
    await make_route(session, cosmos.home.id, second.id)
    await make_region(session, "Dull Plain", cosmos.home.id, magic=10)
    arcane = await make_region(session, "Starfall", second.id, magic=90)
    scribes = await make_entity(session, "Scribefolk", EntityType.PEOPLE, PeopleStats(population=900), world_id=second.id, location_id=arcane.id)
    await teach(session, scribes, KnowledgeBranch.WRITING)
    unknown = await make_entity(
        session, "Star Charts", EntityType.KNOWLEDGE, KnowledgeStats(level=1), world_id=cosmos.home.id, knowledge_branch=KnowledgeBranch.ASTRONOMY
    )
    tuned_rules = tuned(tuned(tuned(rules, "beyond", archive_min_worlds=2), "beyond", archive_appear_chance=100), "beyond", archive_knowledge_chance=100)
    await cosmic_archive(tick(session, tuned_rules))
    archive = await session.scalar(select(EntityRow).where(EntityRow.engine_kind == EngineKind.COSMIC_ARCHIVE))
    assert archive is not None and archive.location_id == arcane.id
    assert await BondRepository(session).exists_between(scribes.id, unknown.id, BondKind.KNOWS) or await session.scalar(select(ArchiveHoldingRow)) is not None
    recorded = await keys(session)
    assert "beyond.archive_appeared" in recorded and "beyond.archive_read" in recorded


async def test_archive_reading_is_capped_per_epoch(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    second = await make_world(session, "Velmor")
    await make_route(session, cosmos.home.id, second.id)
    region = await make_region(session, "Starfall", cosmos.home.id, magic=90)
    readers = []
    for index in range(3):
        reader = await make_entity(session, f"Scribes {index}", EntityType.PEOPLE, PeopleStats(population=900), world_id=cosmos.home.id, location_id=region.id)
        await teach(session, reader, KnowledgeBranch.WRITING)
        readers.append(reader)
    for index in range(3):
        await make_entity(session, f"Lore {index}", EntityType.KNOWLEDGE, KnowledgeStats(level=1), world_id=second.id, knowledge_branch=KnowledgeBranch.MAGIC)
    capped = tuned(tuned(tuned(rules, "beyond", archive_appear_chance=100), "beyond", archive_knowledge_chance=100), "beyond", archive_seekers_cap=1)
    await cosmic_archive(tick(session, capped))
    assert int((await keys(session)).count("beyond.archive_read")) == 1


async def test_rival_clash_picks_a_pair_and_a_weighted_arena(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    first = await make_son(session, "Velan", cosmos.home.id)
    second = await make_son(session, "Morak", cosmos.home.id)
    calm = await make_son(session, "Sefa", cosmos.home.id)
    repository = SonRepository(session)
    await repository.change_relation(first.id, second.id, -(rules.pantheon.rival_relation + 10))
    first.wrath, first.ambition = 100, 100
    second.wrath, second.ambition = 0, 0
    ctx = tick(session, tuned(rules, "pantheon", rival_chance=100))
    assert await rival_clashes(ctx) == 1
    duel = await session.scalar(select(GodConflictRow).where(GodConflictRow.duel.is_(True)))
    assert duel is not None and {duel.attacker_node_id, duel.defender_node_id} == {first.id, second.id}
    assert calm.id not in {duel.attacker_node_id, duel.defender_node_id}
    assert "pantheon.rival_clash" in await keys(session)


async def test_a_son_beaten_again_and_again_withdraws(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    strong = await make_son(session, "Velan", cosmos.home.id, stats=95)
    weak = await make_son(session, "Morak", cosmos.home.id, stats=5)
    streak = rules.pantheon.rival_defeat_streak
    for epoch in range(1, streak):
        await son_duel(tick(session, rules, epoch=epoch), strong, weak, Stat.STRENGTH, "old feud")
    repository = SonRepository(session)
    await repository.change_relation(strong.id, weak.id, -100)
    ctx = tick(session, tuned(tuned(rules, "pantheon", rival_chance=100), "pantheon", rival_cooldown_epochs=0), epoch=streak + 5)
    before = await repository.relation(strong.id, weak.id)
    assert await rival_clashes(ctx) == 1
    after = await repository.relation(strong.id, weak.id)
    assert "pantheon.rival_withdrew" in await keys(session)
    assert after > before - rules.son_tools.challenge_relation


async def foreign_god(session: AsyncSession, world_id: int, stance: int = 0, power: int = 40) -> int:
    god = await ForeignGodRepository(session).create(ForeignGodDraft("Ombrun", world_id, Domain.STORM, power, StatBlock.uniform(50), 1, title="the Old"))
    god.stance, god.contacted = stance, True
    return god.id


async def test_faith_beyond_the_threshold_grows_a_foreign_god(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    god_id = await foreign_god(session, cosmos.home.id, power=40)
    region = await make_region(session, "Vale", cosmos.home.id)
    for index in range(4):
        folk = await make_entity(
            session, f"Folk {index}", EntityType.PEOPLE, PeopleStats(population=50000, piety=90), world_id=cosmos.home.id, location_id=region.id
        )
        await BondRepository(session).connect(BondDraft(folk.id, god_id, BondKind.WORSHIPS, 1))
    god = await session.get(ForeignGodRow, god_id)
    assert god is not None
    await grow_power(tick(session, tuned(rules, "pantheon", foreign_growth_faith=0)), god)
    assert god.faith > 0 and god.power == 40 + rules.pantheon.foreign_growth
    await grow_power(tick(session, tuned(rules, "pantheon", foreign_growth_faith=10**9)), god)
    assert god.power == 40 + rules.pantheon.foreign_growth


async def test_a_friendly_god_gives_its_worshippers_prosperity(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    god_id = await foreign_god(session, cosmos.home.id, stance=80)
    region = await make_region(session, "Vale", cosmos.home.id)
    town = await make_entity(
        session, "Harbor", EntityType.SETTLEMENT, SettlementStats(population=900, prosperity=40), world_id=cosmos.home.id, location_id=region.id
    )
    await BondRepository(session).connect(BondDraft(town.id, god_id, BondKind.WORSHIPS, 1))
    god = await session.get(ForeignGodRow, god_id)
    assert god is not None
    god.faith, god.power = rules.foreign_gods.action_full_faith, rules.foreign_gods.action_full_power
    helped = await friendly_help(tick(session, tuned(rules, "pantheon", foreign_friend_help_chance=100)), god, set())
    assert helped == 1 and town.stats.model_dump()["prosperity"] > 40


async def test_rebels_and_cursed_natives_sour_a_foreign_god(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    god_id = await foreign_god(session, cosmos.home.id, stance=20)
    rebel = await make_son(session, "Velan", cosmos.home.id)
    rebel.rebel = True
    region = await make_region(session, "Vale", cosmos.home.id)
    cursed = await make_entity(session, "Ashfolk", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id, location_id=region.id)
    await EntityRepository(session).add_flag(cursed.id, EntityFlag.CURSED, 1)
    god = await session.get(ForeignGodRow, god_id)
    assert god is not None
    await attitude_drift(tick(session, rules), god, [cursed])
    pantheon = rules.pantheon
    assert god.stance == 20 - pantheon.foreign_rebel_attitude_drift - pantheon.foreign_curse_attitude_drift


async def test_the_strongest_reachable_son_wars_on_a_hostile_god(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    god_id = await foreign_god(session, cosmos.home.id, stance=-100)
    weak = await make_son(session, "Velan", cosmos.home.id, stats=20, rarity=Rarity.MYTHIC)
    strong = await make_son(session, "Morak", cosmos.home.id, stats=90, rarity=Rarity.MYTHIC)
    ctx = tick(session, tuned(rules, "pantheon", son_war_chance=100))
    text = await spontaneous_god_war(ctx, await RouteBook.load(session, rules, ctx.epoch))
    conflict = await session.scalar(select(GodConflictRow).where(GodConflictRow.defender_node_id == god_id))
    assert text is not None and "Morak" in text
    assert conflict is not None and conflict.attacker_node_id == strong.id != weak.id
    assert "pantheon.spontaneous_god_war" in await keys(session)


def test_foreign_god_stats_powers_and_existence_are_sanitized(rules: Rules) -> None:
    previous = StatBlock.uniform(40)
    stats = clean_stats({"strength": 250, "will": -5, "wisdom": "high", "cunning": True}, previous, rules)
    assert stats.get(Stat.STRENGTH) == 100 and stats.get(Stat.WILL) == 1
    assert stats.get(Stat.WISDOM) == 40 and stats.get(Stat.CUNNING) == 40
    neutral = clean_stats({}, None, rules)
    assert neutral.get(Stat.CHARISMA) == rules.foreign_gods.stat_neutral
    powers = clean_powers([{"effect": "deathless", "name": ["Never", "Dying"]}, {"effect": "unknown"}, "noise", {"effect": "shield", "description": ""}])
    assert [power.effect for power in powers] == [ForeignGodPowerEffect.DEATHLESS, ForeignGodPowerEffect.SHIELD]
    assert powers[0].name == "Never\n\nDying" and powers[1].description
    existence = clean_existence({"mode": "nonsense", "nature": '["A storm", "that thinks"]'})
    assert existence.mode is None and existence.nature == "A storm\n\nthat thinks"


def test_community_phrases_follow_the_kind_of_community() -> None:
    assert community_phrase(EntityType.MORTAL, "Orrin") == "around Orrin"
    assert community_phrase(EntityType.PEOPLE, "Kessar") == "among the Kessar people"
    assert community_phrase(EntityType.PEOPLE, "Kessar Folk") == "among the Kessar Folk"
    assert community_phrase(EntityType.FACTION, "Red Oars") == "within Red Oars"
    assert community_phrase(EntityType.CULT, "Bone Choir") == "within Bone Choir"
    assert community_phrase(EntityType.ARMY, "Salt Spears") == "within Salt Spears"
    assert community_phrase(EntityType.SETTLEMENT, "Brinewatch") == "in Brinewatch"


async def test_the_law_book_is_loaded_once_per_step_and_answers_per_world(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    other = await make_world(session, "Velmor")
    await make_entity(session, "Law of Ash", EntityType.NATURAL_LAW, NaturalLawStats(), world_id=other.id, natural_law=NaturalLaw.WAR_BAN)
    ctx = tick(session, rules)
    first = await ctx.laws()
    assert await ctx.laws() is first
    assert first.has(NaturalLaw.WAR_BAN, other.id) and not first.has(NaturalLaw.WAR_BAN, cosmos.home.id)
    assert first.anywhere(NaturalLaw.WAR_BAN) and first.of(other.id) == {NaturalLaw.WAR_BAN}
    assert (await LawBook.load(session)).of(cosmos.home.id) == set()


async def test_astronomers_suffer_disasters_at_reduced_severity(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(session, "Floodplain", cosmos.home.id)
    plain = await make_entity(
        session, "Lowtown", EntityType.SETTLEMENT, SettlementStats(population=1000, prosperity=50), world_id=cosmos.home.id, location_id=region.id
    )
    wise = await make_entity(
        session, "Startown", EntityType.SETTLEMENT, SettlementStats(population=1000, prosperity=50), world_id=cosmos.home.id, location_id=region.id
    )
    await teach(session, wise, KnowledgeBranch.ASTRONOMY)
    await apply_disaster(tick(session, rules), region, Disaster.FLOOD, 0.5)
    assert plain.stats.model_dump()["population"] < wise.stats.model_dump()["population"] <= 1000


async def test_miracles_raise_resurrection_cult_devotion_heal_and_bring_plenty(ctx: TickContext, cosmos: Cosmos) -> None:
    rules = ctx.rules
    session = ctx.session
    son = await make_son(session, "Velan", cosmos.home.id)
    region = await make_region(session, "Vale", cosmos.home.id, fertility=40)
    cult = await make_entity(
        session, "Ashen Vigil", EntityType.CULT, CultStats(followers=100, zeal=60, influence=40, devotion=10), world_id=cosmos.home.id, location_id=region.id
    )
    session.add(ResurrectionOrderRow(cult_entity_id=cult.id, son_id=son.id))
    await session.flush()
    await apply_miracle(ctx, cult, Miracle.PROTECTION, "peace")
    assert cult.stats.model_dump()["devotion"] == 10 + rules.intervention_effects.resurrection_cult_devotion_gain
    mortal = await make_entity(session, "Orrin", EntityType.MORTAL, MortalStats(hp=5, age=30, lifespan=70), world_id=cosmos.home.id, location_id=region.id)
    await EntityRepository(session).add_flag(mortal.id, EntityFlag.CURSED, 1)
    healed = await apply_miracle(ctx, mortal, Miracle.HEALING, "peace")
    assert mortal.stats.model_dump()["hp"] == rules.intervention_effects.healing_hp
    assert not await EntityRepository(session).has_flag(mortal.id, EntityFlag.CURSED)
    assert {effect.value for effect in healed.effects} >= {"health", "curse_lifted"}
    folk = await make_entity(
        session, "Valefolk", EntityType.PEOPLE, PeopleStats(population=1000, prosperity=40), world_id=cosmos.home.id, location_id=region.id
    )
    grown = await apply_miracle(ctx, folk, Miracle.HEALING, "peace")
    assert folk.stats.model_dump()["population"] == round(1000 * (1 + rules.intervention_effects.healing_growth_pct / 100)) and grown.grown
    await apply_miracle(ctx, region, Miracle.BOUNTY, "peace")
    assert region.stats.model_dump()["fertility"] == 40 + rules.intervention_effects.bounty_fertility_gain
    await apply_miracle(ctx, folk, Miracle.BOUNTY, "peace")
    assert folk.stats.model_dump()["prosperity"] > 40
