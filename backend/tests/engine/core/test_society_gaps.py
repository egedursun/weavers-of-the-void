from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.phases.births import villages
from aerona.engine.phases.doom import doom_clock
from aerona.engine.phases.factions import FactionKind, eligible_kinds, factions
from aerona.engine.phases.magic import wizards
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, add_flag, bond, knowledge, mortal, settlement, tuned_rules
from tests.engine.warfare.factories import society as seed_society


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def count_settlements(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT)) or 0)


async def test_crowded_people_resettle_a_ruin_instead_of_founding_a_village(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "villages", tuned_rules(deep_life={"first_village_chance": 100}))
    ruin = await settlement(session, "Ashen Hold", world, world.regions[0], population=50)
    await EntityRepository(session).set_status(ruin, EntityStatus.DEAD, 2, "burned")
    await add_flag(session, ruin.id, EntityFlag.RUIN)
    before = await count_settlements(session)
    await villages(ctx, await RegionAtlas.load(session), Namer(session, ctx.rules))
    assert ruin.status is EntityStatus.CANON
    assert await has_flag(session, ruin.id, EntityFlag.REBUILT)
    assert not await has_flag(session, ruin.id, EntityFlag.RUIN)
    assert await count_settlements(session) == before
    assert await BondRepository(session).exists_between(ruin.id, world.people.id, BondKind.DESCENDS_FROM)
    recorded = await keys(session)
    assert "births.village_ruin" in recorded and "births.village" not in recorded


async def test_crowded_people_found_a_village_when_no_ruin_stands(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "villages", tuned_rules(deep_life={"first_village_chance": 100}))
    before = await count_settlements(session)
    await villages(ctx, await RegionAtlas.load(session), Namer(session, ctx.rules))
    assert await count_settlements(session) == before + 1
    assert "births.village" in await keys(session)


async def faction_town(session: AsyncSession, world: CoreWorld, **shares: float) -> EntityRow:
    town = await settlement(session, "Marketholm", world, world.regions[1], population=3000, prosperity=70)
    await seed_society(session, town.id, warrior=shares.get("warrior", 1.0), merchant=shares.get("merchant", 1.0), priest=shares.get("priest", 1.0))
    return town


async def test_merchant_guild_needs_trade_prosperity_and_merchants(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(factions={"faction_chance": 100, "faction_min_population": 100})
    ctx = await manual_context(session, "guild", rules)
    town = await faction_town(session, world, merchant=25.0)
    assert await eligible_kinds(ctx, town) == []
    partner = await settlement(session, "Saltgate", world, world.regions[3])
    await bond(session, town.id, partner.id, BondKind.TRADES_WITH)
    assert await eligible_kinds(ctx, town) == [FactionKind.GUILD]
    await factions(ctx)
    guild = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.FACTION))
    assert guild is not None and guild.engine_kind is EngineKind.MERCHANT_GUILD and guild.affiliated_entity_id == town.id
    assert "faction.founded_guild" in await keys(session)
    assert await eligible_kinds(ctx, town) == []


async def test_merchant_guild_is_refused_to_a_poor_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "guild", tuned_rules())
    town = await faction_town(session, world, merchant=25.0)
    partner = await settlement(session, "Saltgate", world, world.regions[3])
    await bond(session, town.id, partner.id, BondKind.TRADES_WITH)
    town.stats = town.stats.model_copy(update={"prosperity": ctx.rules.factions.guild_min_prosperity - 1})
    assert await eligible_kinds(ctx, town) == []


async def test_priests_council_needs_priests_and_a_god(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(factions={"faction_chance": 100, "faction_min_population": 100})
    ctx = await manual_context(session, "council", rules)
    town = await faction_town(session, world, priest=25.0)
    assert await eligible_kinds(ctx, town) == []
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    assert await eligible_kinds(ctx, town) == [FactionKind.COUNCIL]
    await factions(ctx)
    council = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.FACTION))
    assert council is not None and council.engine_kind is EngineKind.PRIESTS_COUNCIL
    assert await BondRepository(session).exists_between(council.id, world.son.id, BondKind.WORSHIPS)
    assert "faction.founded_council" in await keys(session)


async def test_wizard_wards_a_home_with_protection_or_plenty(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0], defense=30)
    mage = await mortal(session, "Vesna", world, town.id, intellect=90)
    lore = await knowledge(session, world, "Ember Lore", KnowledgeBranch.MAGIC)
    await bond(session, mage.id, lore.id, BondKind.KNOWS)
    protect = await manual_context(
        session,
        "ward",
        tuned_rules(world_engine={"sorcerer_act_chance": 100, "sorcerer_curse_chance": 0}, world_effects={"sorcerer_protect_chance": 100}),
    )
    await wizards(protect)
    assert await has_flag(session, town.id, EntityFlag.PROTECTED)
    assert stat(town, "defense") == 30 + protect.rules.intervention_effects.protection_defense_gain
    assert "magic.ward" in await keys(session)
    plenty = await manual_context(
        session,
        "plenty",
        tuned_rules(world_engine={"sorcerer_act_chance": 100, "sorcerer_curse_chance": 0}, world_effects={"sorcerer_protect_chance": 0}),
    )
    await wizards(plenty)
    assert "magic.plenty" in await keys(session)


async def test_doom_clock_chronicles_the_first_and_final_omens(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(apocalypse={"cursed": 50, "peace": 0, "faith_cap": 0, "warning_1_pct": 10, "warning_2_pct": 20})
    ctx = await manual_context(session, "doom", rules)
    await add_flag(session, world.people.id, EntityFlag.CURSED)
    world.cosmos.doom_clock = 0
    await doom_clock(ctx)
    recorded = await keys(session)
    assert world.cosmos.doom_clock > 0
    assert "doom.omen_10" in recorded and "doom.omen_20" in recorded


async def test_doom_clock_omen_is_silent_below_the_warning_point(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(apocalypse={"cursed": 0, "peace": 0, "faith_cap": 0, "godless": 0, "warning_1_pct": 50, "warning_2_pct": 80})
    ctx = await manual_context(session, "doom", rules)
    world.cosmos.doom_clock = 0
    await doom_clock(ctx)
    assert not any(key and key.startswith("doom.omen") for key in await keys(session))
