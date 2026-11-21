from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.protected_nature import ProtectedAreaRow
from aerona.domain.enums.creature_groups import GroupForm
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.protected_nature import ProtectionBasis
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import BeastStats, SpeciesStats
from aerona.engine.creature_groups.groups import GroupTally, contest, fight, form_groups, group_danger, hunt_factor, raid, roam
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def kind_of(session: AsyncSession, world: CoreWorld, name: str, *traits: CreatureTrait, abundance: int = 50, region: int = 1) -> EntityRow:
    species = await entity(session, name, EntityType.SPECIES, SpeciesStats(intelligence=10, danger=40), world_id=world.world.id)
    for trait in traits:
        await EntityRepository(session).add_trait(species.id, trait)
    session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=world.regions[region].id, abundance=abundance, fit=20, locked=[]))
    await session.flush()
    return species


async def beast_of(session: AsyncSession, world: CoreWorld, species: EntityRow, name: str, region: int = 1) -> EntityRow:
    beast = await entity(session, name, EntityType.BEAST, BeastStats(danger=50), world_id=world.world.id, location_id=world.regions[region].id)
    session.add(BeastProfileRow(beast_entity_id=beast.id, species_entity_id=species.id, locked=[]))
    await session.flush()
    return beast


async def test_a_plentiful_pack_hunting_kind_gathers_into_a_led_pack_and_a_grazing_one_into_a_herd(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "form", tuned_rules(creature_groups={"form_floor": 20, "size_per_abundance": 10}))
    wolves = await kind_of(session, world, "Grey Runners", CreatureTrait.PACK_HUNTER)
    deer = await kind_of(session, world, "Long Grazers")
    alpha = await beast_of(session, world, wolves, "Old Scar")
    await form_groups(ctx, await RegionAtlas.load(session), GroupTally())
    pack = await session.scalar(select(CreatureGroupRow).where(CreatureGroupRow.species_entity_id == wolves.id))
    herd = await session.scalar(select(CreatureGroupRow).where(CreatureGroupRow.species_entity_id == deer.id))
    assert pack is not None and pack.form is GroupForm.PACK and pack.size == 500 and pack.leader_node_id == alpha.id and pack.ranks == 2
    assert herd is not None and herd.form is GroupForm.HERD and herd.leader_node_id is None
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "beasts.group_formed")) is not None
    assert await hunt_factor(session, ctx.rules, deer.id, world.regions[1].id) > 1
    assert (await group_danger(session, ctx.rules))[world.regions[1].id] > 0


async def test_a_hungry_pack_raids_a_town_and_its_leader_falls_to_a_challenger(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "raid", tuned_rules(creature_groups={"raid_hunger_threshold": 50, "raid_loss": 10, "contest_chance_pct": 100}))
    wolves = await kind_of(session, world, "Night Runners", CreatureTrait.PACK_HUNTER)
    first, second = await beast_of(session, world, wolves, "First Fang"), await beast_of(session, world, wolves, "Second Fang")
    town = await settlement(session, "Fold", world, world.regions[1], prosperity=50)
    atlas = await RegionAtlas.load(session)
    await form_groups(ctx, atlas, GroupTally())
    pack = await session.scalar(select(CreatureGroupRow).where(CreatureGroupRow.species_entity_id == wolves.id))
    assert pack is not None
    pack.hunger = 80
    tally = GroupTally()
    await raid(ctx, atlas, pack, tally)
    assert tally.raids == 1 and stat_or(town, "prosperity", 0) == 40 and pack.hunger == 50
    await contest(ctx, atlas, pack, tally)
    assert pack.leader_node_id == second.id != first.id and tally.contests == 1


async def test_rival_packs_fight_for_ground_and_the_smaller_loses_numbers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "war", tuned_rules(creature_groups={"territory_war_pct": 100, "war_loss_pct": 50}))
    big = await kind_of(session, world, "Big Runners", CreatureTrait.PACK_HUNTER, abundance=80)
    small = await kind_of(session, world, "Small Runners", CreatureTrait.PACK_HUNTER, abundance=30)
    await form_groups(ctx, await RegionAtlas.load(session), GroupTally())
    groups = list(await session.scalars(select(CreatureGroupRow).order_by(CreatureGroupRow.id)))
    loser = next(group for group in groups if group.species_entity_id == small.id)
    before = loser.size
    tally = GroupTally()
    await fight(ctx, groups[0], groups, tally)
    assert tally.wars == 1 and loser.size == before // 2 and big.id != small.id


async def test_settlement_pushes_a_group_to_the_next_land_but_protected_land_keeps_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "push", tuned_rules(creature_groups={"push_population": 100, "move_pct": 100}))
    deer = await kind_of(session, world, "Shy Grazers")
    await settlement(session, "Crowdby", world, world.regions[1], population=5000)
    atlas = await RegionAtlas.load(session)
    await form_groups(ctx, atlas, GroupTally())
    herd = await session.scalar(select(CreatureGroupRow).where(CreatureGroupRow.species_entity_id == deer.id))
    assert herd is not None
    session.add(ProtectedAreaRow(region_entity_id=world.regions[1].id, basis=next(iter(ProtectionBasis)), strength=50, locked=[]))
    await session.flush()
    await roam(ctx, atlas, herd, GroupTally())
    assert herd.region_entity_id == world.regions[1].id
    shield = await session.scalar(select(ProtectedAreaRow))
    assert shield is not None
    await session.delete(shield)
    await session.flush()
    tally = GroupTally()
    await roam(ctx, atlas, herd, tally)
    assert tally.moved == 1 and herd.region_entity_id != world.regions[1].id
    moved = await session.get(SpeciesRangeRow, (deer.id, herd.region_entity_id))
    assert moved is not None and moved.abundance > 0
