import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesProfileRow, SpeciesUseRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.mind import GriefRow, SkillRow, ThoughtRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import BeastTemper, Diet, DomesticationStage, HerdTraining, SizeClass, SpeciesUse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.mind import SkillKind, SkillSource, ThoughtKind
from aerona.domain.models.entity_stats import MortalStats, SettlementStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.domestication import feed, grazing_heads, guarded, produce, train, trained_effect, trained_heads
from aerona.engine.ecology.pet_control import give_pet, set_pet
from aerona.engine.ecology.pets import adopt_pets, tend_pets
from aerona.engine.ecology.profiles import SpeciesSpec, profile_of
from aerona.engine.economy.stocks import GoodsLedger, holding
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, tick, tuned


async def town(session: AsyncSession, cosmos: Cosmos, region_id: int, name: str = "Fold Hold") -> int:
    hold = await make_entity(session, name, EntityType.SETTLEMENT, SettlementStats(population=800), world_id=cosmos.home.id, location_id=region_id)
    return hold.id


async def kind(ctx: TickContext, cosmos: Cosmos, region_id: int, name: str, spec: SpeciesSpec, *uses: SpeciesUse) -> int:
    species = await make_entity(ctx.session, name, EntityType.SPECIES, SpeciesStats(hp=20), world_id=cosmos.home.id, location_id=region_id)
    await profile_of(ctx, species, spec)
    for use in uses:
        if await ctx.session.get(SpeciesUseRow, (species.id, use)) is None:
            ctx.session.add(SpeciesUseRow(species_entity_id=species.id, use=use))
    await ctx.session.flush()
    return species.id


def herd(community_id: int, species_id: int, head: int = 100, **values: object) -> HerdRow:
    row = HerdRow(
        community_entity_id=community_id, species_entity_id=species_id, head=head, stage=DomesticationStage.HERDED, since_epoch=1, fed_epochs=0, locked=[]
    )
    for key, value in values.items():
        setattr(row, key, value)
    return row


async def test_fertile_kinds_grow_their_herds_faster_and_graze_the_land(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Pasture Downs", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    slow = await kind(ctx, cosmos, region.id, "Slow Grazer", SpeciesSpec(size_class=SizeClass.LARGE, diet=Diet.HERBIVORE))
    quick = await kind(ctx, cosmos, region.id, "Quick Grazer", SpeciesSpec(size_class=SizeClass.SMALL, diet=Diet.HERBIVORE))
    for species_id in (slow, quick):
        profile = await ctx.session.get(SpeciesProfileRow, species_id)
        assert profile is not None
        profile.breeding_seasons, profile.litter_size = (1, 1) if species_id == slow else (2, 4)
    rows = [herd(hold, slow), herd(hold, quick)]
    ctx.session.add_all(rows)
    await ctx.session.flush()
    await GoodsLedger(ctx.session, ctx.epoch).add(hold, CommodityKind.FODDER, 1000, GoodsFlow.PRODUCTION)
    for row in rows:
        assert await feed(ctx, row)
    assert rows[1].head > rows[0].head > 100
    grazing = await grazing_heads(ctx.session)
    assert grazing[region.id] == rows[0].head + rows[1].head


async def test_milk_wool_and_eggs_follow_the_keepers_method(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Dairy Vale", cosmos.home.id)
    hand = await town(ctx.session, cosmos, region.id, "Hand Hold")
    penned = await town(ctx.session, cosmos, region.id, "Pen Hold")
    goat = await kind(ctx, cosmos, region.id, "Vale Goat", SpeciesSpec(size_class=SizeClass.MEDIUM, diet=Diet.HERBIVORE))
    products = set(await ctx.session.scalars(select(SpeciesYieldRow.product).where(SpeciesYieldRow.species_entity_id == goat)))
    assert {"milk", "wool"} <= products
    milk = await ctx.session.get(SpeciesYieldRow, (goat, "milk"))
    assert milk is not None and milk.commodity is CommodityKind.MILK
    ctx.session.add_all([herd(hand, goat), herd(penned, goat)])
    ctx.session.add(CommunityMethodRow(community_node_id=penned, process=ProcessKind.MILKING, method=MethodKind.PENNED_MILKING, adopted_epoch=1))
    await ctx.session.flush()
    for community in (hand, penned):
        row = await ctx.session.get(HerdRow, (community, goat))
        assert row is not None
        await produce(ctx, row)
    assert await holding(ctx.session, penned, CommodityKind.MILK) > await holding(ctx.session, hand, CommodityKind.MILK)
    assert await holding(ctx.session, hand, CommodityKind.WOOL) > 0


async def test_master_handlers_train_herds_for_war_hunting_and_guarding(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Kennel Moor", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    hound = await kind(ctx, cosmos, region.id, "Moor Hound", SpeciesSpec(size_class=SizeClass.MEDIUM, diet=Diet.CARNIVORE), SpeciesUse.GUARD)
    row = herd(hold, hound, training=HerdTraining.GUARD)
    ctx.session.add(row)
    handler = await make_entity(ctx.session, "Bran", EntityType.MORTAL, MortalStats(hp=30, age=30, lifespan=70), world_id=cosmos.home.id, location_id=hold)
    ctx.session.add(SkillRow(holder_node_id=handler.id, skill=SkillKind.BEAST_HANDLING, level=80, peak=80, last_used_epoch=1, source=SkillSource.PRACTICE))
    await ctx.session.flush()
    before = await guarded(ctx, hold)
    assert await train(ctx, row) > 0
    assert 0 < row.trained <= row.head
    assert await trained_heads(ctx.session, hold, HerdTraining.GUARD) == row.trained
    assert trained_effect(rules, row.trained) > 0
    assert await guarded(ctx, hold) < before
    row.training = None
    assert await train(ctx, row) == 0


async def test_mortals_take_pets_are_comforted_and_mourn_them(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Hearth Vale", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    hound = await kind(ctx, cosmos, region.id, "Hearth Hound", SpeciesSpec(size_class=SizeClass.SMALL, diet=Diet.CARNIVORE), SpeciesUse.GUARD)
    ctx.session.add(herd(hold, hound, head=20))
    owner = await make_entity(ctx.session, "Mira", EntityType.MORTAL, MortalStats(hp=30, age=30, lifespan=70), world_id=cosmos.home.id, location_id=hold)
    await ctx.session.flush()
    eager = tick(ctx.session, tuned(rules, "husbandry", pet_chance=100))
    assert await adopt_pets(eager) == 1
    bond = await ctx.session.scalar(select(BondRow).where(BondRow.kind == BondKind.PET_OF, BondRow.target_node_id == owner.id))
    assert bond is not None
    pet = await ctx.session.get(BeastProfileRow, bond.source_node_id)
    assert pet is not None and pet.temper is BeastTemper.COMPANION and pet.bound_to_node_id == owner.id
    tally = await tend_pets(ctx)
    assert tally.comforted == 1 and tally.hunted == 1
    kinds = set(await ctx.session.scalars(select(ThoughtRow.kind).where(ThoughtRow.holder_node_id == owner.id)))
    assert ThoughtKind.COMFORTED_BY_PET in kinds
    hunting = await ctx.session.scalar(select(SkillRow).where(SkillRow.holder_node_id == owner.id, SkillRow.skill == SkillKind.HUNTING))
    assert hunting is not None
    beast = await ctx.session.get(EntityRow, bond.source_node_id)
    assert beast is not None
    beast.status, beast.end_epoch = EntityStatus.DEAD, ctx.epoch
    await ctx.session.flush()
    assert (await tend_pets(ctx)).mourned == 1
    assert bond.state is not BondState.ACTIVE
    assert ThoughtKind.LOST_PET in set(await ctx.session.scalars(select(ThoughtRow.kind).where(ThoughtRow.holder_node_id == owner.id)))
    assert await ctx.session.scalar(select(GriefRow).where(GriefRow.mourner_node_id == owner.id, GriefRow.deceased_node_id == beast.id)) is not None


async def test_the_god_gives_and_frees_pets(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Gift Vale", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    cat = await kind(ctx, cosmos, region.id, "Barn Cat", SpeciesSpec(size_class=SizeClass.TINY, diet=Diet.CARNIVORE))
    owner = await make_entity(ctx.session, "Oren", EntityType.MORTAL, MortalStats(hp=30, age=30, lifespan=70), world_id=cosmos.home.id, location_id=hold)
    pet = await give_pet(ctx, owner.id, cat)
    with pytest.raises(ValidationFailedError):
        await give_pet(ctx, owner.id, cat)
    freed = await set_pet(ctx, pet.id, None)
    assert freed.temper is BeastTemper.TAMED and freed.bound_to_node_id is None
    kept = await set_pet(ctx, pet.id, owner.id)
    assert kept.temper is BeastTemper.COMPANION
    bonds = list(
        await ctx.session.scalars(select(BondRow).where(BondRow.source_node_id == pet.id, BondRow.kind == BondKind.PET_OF, BondRow.state == BondState.ACTIVE))
    )
    assert len(bonds) == 1
