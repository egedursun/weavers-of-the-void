from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.eras import ERA_FLOORS
from aerona.catalog.units import SUCCESSORS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.eras import EraChannel, ProgrammeStage, TechFamily
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, SocialClass
from aerona.domain.enums.world import TechnologyEra
from aerona.domain.models.entity_stats import KnowledgeStats, NaturalLawStats, PolityStats
from aerona.domain.models.genesis import GenesisSettings
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import era_of, era_techniques, tech_bonus, tech_factor, tech_relief
from aerona.engine.eras.progress import EraTally, era_doom, keep_floors, keep_programmes
from aerona.engine.lore.research import ensure_holders
from aerona.engine.military.units import era_here, fieldable, settled_successor
from aerona.engine.phases.factions import eligible_kinds
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.technology.profiles import family_level
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "tech_eras", rules=tuned_rules(**rules))


async def knows(session: AsyncSession, holder: EntityRow, *techniques: Technique) -> None:
    for technique in techniques:
        session.add(HolderTechniqueRow(holder_entity_id=holder.id, technique=technique, since_epoch=0, secret=False))
    await session.flush()


async def realm(session: AsyncSession, world: CoreWorld, capital: EntityRow, treasury: int = 4000) -> EntityRow:
    polity = await entity(session, f"Crown of {capital.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=capital.id,
            core_entity_id=polity.id,
            legitimacy=50,
            stability=50,
            treasury=treasury,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=capital.id))
    await session.flush()
    return polity


async def programme(session: AsyncSession, polity: EntityRow, technique: Technique, progress: int) -> TechProgrammeRow:
    row = TechProgrammeRow(polity_entity_id=polity.id, technique=technique, progress=progress, stage=ProgrammeStage.TESTING, started_epoch=0, locked=[])
    session.add(row)
    await session.flush()
    return row


async def test_known_techniques_set_the_era_and_change_industry_sickness_and_messages(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await settlement(session, "Harrowgate", world, world.regions[0])
    assert era_of(await era_techniques(session, town.id)) is TechnologyEra.STONE
    await knows(session, town, Technique.STEAM_POWER, Technique.FACTORY_PRODUCTION, Technique.VACCINES, Technique.TELEGRAPH)
    assert era_of(await era_techniques(session, town.id)) is TechnologyEra.STEAM
    assert await tech_factor(session, rules, town.id, EraChannel.INDUSTRY) == 1 + (rules.eras.steam_pct + rules.eras.factory_pct) / 100
    assert await tech_relief(session, rules, town.id, EraChannel.DISEASE) == 1 - rules.eras.vaccines_pct / 100
    assert await tech_bonus(session, rules, town.id, EraChannel.MESSAGES) == rules.eras.telegraph_hops
    assert await tech_bonus(session, rules, town.id, EraChannel.POLLUTION) == rules.eras.steam_pollution_pct + rules.eras.factory_pollution_pct


async def test_a_member_town_reads_the_techniques_of_its_realms_capital(session: AsyncSession, world: CoreWorld) -> None:
    capital = await settlement(session, "Orrin", world, world.regions[0])
    town = await settlement(session, "Low Orrin", world, world.regions[0])
    polity = await realm(session, world, capital)
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await knows(session, capital, Technique.ELECTRICITY)
    assert Technique.ELECTRICITY in await era_techniques(session, town.id)
    assert era_of(await era_techniques(session, polity.id)) is TechnologyEra.ELECTRICAL


async def test_a_law_of_no_gunpowder_silences_powder_and_dangerous_techniques_feed_doom(session: AsyncSession, world: CoreWorld) -> None:
    capital = await settlement(session, "Kesk", world, world.regions[0])
    await realm(session, world, capital)
    await knows(session, capital, Technique.GUNPOWDER, Technique.FIREARMS, Technique.NUCLEAR_WEAPONS, Technique.ARTIFICIAL_MINDS)
    ctx = await at(session, 2)
    assert await era_doom(ctx) == ctx.rules.eras.nuclear_doom + ctx.rules.eras.minds_doom
    assert await tech_bonus(session, ctx.rules, capital.id, EraChannel.FIREPOWER) > 0
    law = await entity(session, "The Damp Air", EntityType.NATURAL_LAW, NaturalLawStats(), world_id=world.world.id)
    law.natural_law = NaturalLaw.NO_GUNPOWDER
    await session.flush()
    known = await era_techniques(session, capital.id)
    assert Technique.GUNPOWDER not in known and Technique.FIREARMS not in known and Technique.NUCLEAR_WEAPONS in known
    assert await tech_bonus(session, ctx.rules, capital.id, EraChannel.FIREPOWER) == ctx.rules.eras.nuclear_pct


async def test_a_programme_paid_by_the_treasury_completes_and_teaches_its_capital(session: AsyncSession, world: CoreWorld) -> None:
    capital = await settlement(session, "Vael", world, world.regions[0])
    polity = await realm(session, world, capital)
    row = await programme(session, polity, Technique.NUCLEAR_POWER, 95)
    ctx = await at(session, 4, programmes={"start_chance": 0, "sabotage_chance": 0})
    tally = EraTally()
    await keep_programmes(ctx, tally)
    profile = await session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.treasury == 4000 - ctx.rules.programmes.treasury_cost
    assert row.stage is ProgrammeStage.COMPLETE and row.finished_epoch == 4 and tally.completed == 1
    assert await session.get(HolderTechniqueRow, (capital.id, Technique.NUCLEAR_POWER)) is not None


async def test_a_realm_without_coin_abandons_and_a_spying_rival_sets_a_programme_back(session: AsyncSession, world: CoreWorld) -> None:
    poor_town = await settlement(session, "Brin", world, world.regions[0])
    poor = await realm(session, world, poor_town, treasury=10)
    starved = await programme(session, poor, Technique.ROCKETRY, 50)
    rich_town = await settlement(session, "Selm", world, world.regions[0])
    rich = await realm(session, world, rich_town)
    watched = await programme(session, rich, Technique.ROCKETRY, 50)
    rival_town = await settlement(session, "Ost", world, world.regions[0])
    rival = await realm(session, world, rival_town)
    session.add(SpyNetworkRow(owner_entity_id=rival.id, target_entity_id=rich.id, agent_ids=[], since_epoch=0, revealed_aims=[], locked=[]))
    await session.flush()
    ctx = await at(session, 3, programmes={"start_chance": 0, "sabotage_chance": 100, "abandon_below": 100, "base_years": 400})
    tally = EraTally()
    await keep_programmes(ctx, tally)
    assert starved.stage is ProgrammeStage.ABANDONED and tally.abandoned == 1
    table = ctx.rules.programmes
    assert watched.sabotaged == 1 and watched.progress == 50 + table.base_progress - table.sabotage_loss


async def test_the_starting_era_gives_fresh_towns_their_floor_of_knowledge(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.genesis_settings = GenesisSettings(magic=50, danger=50, peoples=1, technology=TechnologyEra.STEAM)
    town = await settlement(session, "Coalbrook", world, world.regions[0])
    tally = EraTally()
    await keep_floors(await at(session, 1), tally)
    levels = {row.branch: row.level for row in await session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == town.id))}
    assert levels[KnowledgeBranch.METALLURGY] == 6 and tally.floored >= 1
    known = await era_techniques(session, town.id)
    assert {Technique.BRONZE, Technique.IRON, Technique.STEEL, Technique.PRINTING_PRESS, Technique.STEAM_POWER} <= known
    assert era_of(known) is TechnologyEra.STEAM


async def test_a_wandering_mortal_reads_the_era_of_its_people_never_below_the_starting_era(session: AsyncSession, world: CoreWorld) -> None:
    wanderer = await mortal(session, "Tamsin", world, world.regions[0].id)
    await bond(session, wanderer.id, world.people.id, BondKind.DESCENDS_FROM)
    assert era_of(await era_techniques(session, wanderer.id), TechnologyEra.IRON) is TechnologyEra.IRON
    await knows(session, world.people, Technique.ELECTRICITY)
    assert era_of(await era_techniques(session, wanderer.id), TechnologyEra.IRON) is TechnologyEra.ELECTRICAL


async def test_industry_raises_unions_of_workers_societies_of_engineers_and_exchanges_of_financiers(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Forgeham", world, world.regions[0])
    shares = {f"share_{item.value}": 0.0 for item in SocialClass}
    shares.update({"share_artisan": 40.0, "share_professional": 20.0, "share_merchant": 40.0})
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            **shares,
            **{f"satisfaction_{item.value}": 50 for item in SocialClass},
            stock_food=0,
            stock_ore=0,
            stock_goods=0,
            price_food=100,
            price_ore=100,
            price_goods=100,
        )
    )
    await session.flush()
    ctx = await at(session, 3)
    assert not {FactionKind.WORKERS_UNION, FactionKind.ENGINEERS_SOCIETY, FactionKind.FINANCIERS} & set(await eligible_kinds(ctx, town))
    await knows(session, town, Technique.FACTORY_PRODUCTION, Technique.STEAM_POWER, Technique.BANKING)
    found = set(await eligible_kinds(await at(session, 3), town))
    assert {FactionKind.WORKERS_UNION, FactionKind.ENGINEERS_SOCIETY, FactionKind.FINANCIERS} <= found


async def test_a_people_of_an_information_age_world_keeps_its_era_whatever_old_lore_it_knows(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.genesis_settings = GenesisSettings(magic=50, danger=50, peoples=1, technology=TechnologyEra.INFORMATION)
    smithing = await entity(session, "First smithing", EntityType.KNOWLEDGE, KnowledgeStats(level=1), world_id=world.world.id)
    smithing.knowledge_branch = KnowledgeBranch.METALLURGY
    await bond(session, world.people.id, smithing.id, BondKind.KNOWS)
    ctx = await at(session, 1)
    await keep_floors(ctx, EraTally())
    await ensure_holders(ctx)
    await keep_floors(ctx, EraTally())
    levels = {row.branch: row.level for row in await session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == world.people.id))}
    floors = ERA_FLOORS[TechnologyEra.INFORMATION]
    assert all(levels.get(branch, 0) >= level for branch, level in floors.items()), levels
    known = await era_techniques(session, world.people.id)
    assert {Technique.FIREARMS, Technique.RAILWAYS, Technique.ELECTRICITY, Technique.TELEPHONE, Technique.COMPUTATION, Technique.RADIO} <= known
    assert Technique.NUCLEAR_POWER not in known
    assert era_of(known) is TechnologyEra.INFORMATION
    assert await family_level(session, world.people.id, TechFamily.TRANSPORT) >= floors[KnowledgeBranch.SHIPBUILDING]
    knowledge = await KnowledgeMap.load(session)
    fielded = await fieldable(ctx, world.people)
    reach = await era_here(ctx, fielded)
    newest = {kind: settled_successor(ctx.rules, kind, community_id=world.people.id, knowledge=knowledge, techniques=fielded, era=reach) for kind in SUCCESSORS}
    assert newest[UnitKind.ARCHERS] is UnitKind.GUNNERS and newest[UnitKind.LEVY] is UnitKind.GUNNERS
    assert newest[UnitKind.SHIELD_INFANTRY] is UnitKind.MECHANISED_INFANTRY and newest[UnitKind.CHARIOTS] is UnitKind.VEHICLE_CREW
