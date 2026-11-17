from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import anatomy_of
from aerona.catalog.creature_anatomy import MONSTER_PLANS, MONSTER_SIZES
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.anatomy import CreatureAnatomyRow, CreatureAttackRow
from aerona.db.tables.body import BodyRow, ConditionRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import ArmyRow, CaptiveRow, SiegeRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.body import MADNESS_CONDITIONS, BodyPlan, ConditionKind, DamageType, TissueKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import MagicSchool, MagicSource
from aerona.domain.enums.ecology import (
    AttackDelivery,
    AttackEffect,
    AttackRange,
    Aversion,
    AwakeningTrigger,
    BeastTemper,
    Biochemistry,
    Diet,
    Habitat,
    SizeClass,
    SpeciesClass,
    Temperament,
    TissueMaterial,
)
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import BeastStats, MortalStats, ResourceStats, RiteStats, SettlementStats, SpeciesStats
from aerona.engine.body.book import ensure_body, wild_plan
from aerona.engine.body.tissues import PLAIN, Hardness, hardness_of, skin_kept, tissue_hit
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import has_beast_mount
from aerona.engine.ecology.anatomy import (
    BEAST_BODIES_FIXUP,
    armour_of,
    attack_specs,
    body_might,
    ensure_anatomy,
    fit_beast_bodies,
    generate,
    harm_factor,
    known_plan,
    repelled,
)
from aerona.engine.ecology.anatomy_control import edit_anatomy, reroll_anatomy
from aerona.engine.ecology.beast_acts import carry_off, free_captives, sight_scale, strike, triggered, void_trophy
from aerona.engine.ecology.beasts import profile_beast, raid
from aerona.engine.ecology.monsters import emerge_from_deep, roam_void
from aerona.engine.ecology.necromancy import necromancy
from aerona.engine.ecology.profiles import SpeciesSpec, profile_of
from aerona.engine.economy.stocks import GoodsLedger, holding
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_world, tick, tuned


async def town(session: AsyncSession, cosmos: Cosmos, region_id: int, name: str = "Watch Hold") -> EntityRow:
    return await make_entity(session, name, EntityType.SETTLEMENT, SettlementStats(population=900), world_id=cosmos.home.id, location_id=region_id)


async def mortal(session: AsyncSession, cosmos: Cosmos, home_id: int, name: str = "Tam") -> EntityRow:
    return await make_entity(session, name, EntityType.MORTAL, MortalStats(hp=30, age=30, lifespan=70), world_id=cosmos.home.id, location_id=home_id)


async def beast(ctx: TickContext, cosmos: Cosmos, region_id: int, name: str = "Old Horror") -> tuple[EntityRow, BeastProfileRow]:
    creature = await make_entity(
        ctx.session, name, EntityType.BEAST, BeastStats(hp=300, danger=60, strength=60), world_id=cosmos.home.id, location_id=region_id
    )
    row = await profile_beast(ctx, creature, None, size=SizeClass.HUGE)
    return creature, row


def attack(node_id: int, delivery: AttackDelivery, effect: AttackEffect, reach: AttackRange = AttackRange.NEAR) -> CreatureAttackRow:
    row = CreatureAttackRow(node_id=node_id, delivery=delivery, effect=effect, range=reach, recharge=0, permanent=False)
    row.locked = []
    return row


def stored(ctx: TickContext, row: CreatureAttackRow) -> CreatureAttackRow:
    ctx.session.add(row)
    return row


def anatomy(node_id: int, **values: object) -> CreatureAnatomyRow:
    row = CreatureAnatomyRow(node_id=node_id, generated_epoch=1, locked=[])
    for key, value in values.items():
        setattr(row, key, value)
    return row


def test_bodies_follow_traits_and_chemistry_and_monsters_grow_strange(rules: Rules) -> None:
    traits = {CreatureTrait.FIRE_BREATHING, CreatureTrait.STONESKIN}
    plain = generate(rules, 11, BodyPlan.QUADRUPED, traits, Biochemistry.CARBON_WATER, aggression=10, fear=80, monster=False)
    given = attack_specs(rules, 11, traits, monster=False)
    assert given[0].delivery is AttackDelivery.BREATH and given[0].effect is AttackEffect.HEAT
    assert plain.skin is TissueMaterial.MINERAL and plain.limbs >= 4
    assert plain.temperament is Temperament.SKITTISH
    again = generate(rules, 11, BodyPlan.QUADRUPED, traits, Biochemistry.CARBON_WATER, aggression=10, fear=80, monster=False)
    assert (again.limbs, again.heads, again.skin) == (plain.limbs, plain.heads, plain.skin)
    void = generate(rules, 12, BodyPlan.AMORPHOUS, set(), Biochemistry.VOID, aggression=50, fear=50, monster=False)
    assert void.habitat is Habitat.VOID and void.skin is TissueMaterial.INSUBSTANTIAL
    sure = tuned(
        rules, "creature_anatomy", exotic_tissue_pct=100, monster_attack_pct=100, sight_attack_pct=100, hoard_pct=100, abductor_pct=100, awakening_pct=100
    )
    monster = generate(sure, 13, BodyPlan.COLOSSAL, set(), Biochemistry.CARBON_WATER, aggression=50, fear=0, monster=True, deep=True)
    assert monster.skin in {TissueMaterial.CRYSTALLINE, TissueMaterial.ENERGY, TissueMaterial.VAPOUR, TissueMaterial.METALLIC, TissueMaterial.GEL}
    deliveries = {spec.delivery for spec in attack_specs(sure, 13, set(), monster=True)}
    assert AttackDelivery.GAZE in deliveries and len(deliveries) >= 2
    assert monster.hoards is not None and monster.awakening is not None
    assert monster.temperament is Temperament.SEIZES_PREY and monster.habitat is Habitat.DEEP
    assert harm_factor(rules, monster, 4, 2) > harm_factor(rules, plain, 4) >= 1.0
    assert armour_of(monster) > 0 and armour_of(None) == 0


async def test_every_kind_and_beast_gets_a_body_but_plants_do_not(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Body Vale", cosmos.home.id)
    hound = await make_entity(ctx.session, "Vale Hound", EntityType.SPECIES, SpeciesStats(hp=20), world_id=cosmos.home.id, location_id=region.id)
    await profile_of(ctx, hound, SpeciesSpec(diet=Diet.CARNIVORE))
    reed = await make_entity(ctx.session, "Vale Reed", EntityType.SPECIES, SpeciesStats(hp=5), world_id=cosmos.home.id, location_id=region.id)
    await profile_of(ctx, reed, SpeciesSpec(species_class=SpeciesClass.PLANT))
    horror, _ = await beast(ctx, cosmos, region.id)
    assert await ensure_anatomy(ctx) == 2
    assert await ctx.session.get(CreatureAnatomyRow, hound.id) is not None
    assert await ctx.session.get(CreatureAnatomyRow, horror.id) is not None
    assert await ctx.session.get(CreatureAnatomyRow, reed.id) is None
    assert await ensure_anatomy(ctx) == 0


async def test_a_monster_hoards_bites_and_shuns_what_it_hates(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Raid Vale", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    victim = await mortal(ctx.session, cosmos, hold.id)
    horror, row = await beast(ctx, cosmos, region.id)
    ctx.session.add(anatomy(horror.id, hoards=MaterialKind.GOLD, bite=PackageKind.SNAKE_VENOM, hates=Aversion.FIRE))
    ctx.session.add(attack(horror.id, AttackDelivery.BREATH, AttackEffect.HEAT))
    await GoodsLedger(ctx.session, ctx.epoch).add(hold.id, CommodityKind.LUXURIES, 20, GoodsFlow.PRODUCTION)
    await ctx.session.flush()
    await raid(ctx, horror, row, hold)
    assert row.hoard.get("gold", 0) > 0
    assert await ctx.session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == victim.id)) is not None
    atlas = await RegionAtlas.load(ctx.session)
    assert not await repelled(ctx, atlas, hold, Aversion.FIRE)
    await GoodsLedger(ctx.session, ctx.epoch).add(hold.id, CommodityKind.FUEL, 5, GoodsFlow.PRODUCTION)
    assert await repelled(ctx, atlas, hold, Aversion.FIRE)


async def test_sleepers_wake_to_deep_mining_or_desecration_and_the_deep_lets_monsters_out(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Mine Vale", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    seam = await make_entity(ctx.session, "Deep Seam", EntityType.RESOURCE, ResourceStats(abundance=40), world_id=cosmos.home.id, location_id=region.id)
    ctx.session.add(
        ResourceProfileRow(
            resource_entity_id=seam.id, commodity=CommodityKind.ORE, reserve=50, initial_reserve=100, richness=50, extraction_difficulty=20, quality=50
        )
    )
    await ctx.session.flush()
    atlas = await RegionAtlas.load(ctx.session)
    sleeper = anatomy(0, awakening=AwakeningTrigger.DEEP_MINING)
    assert await triggered(ctx, atlas, sleeper, region.id)
    holy = anatomy(0, awakening=AwakeningTrigger.DESECRATION)
    assert not await triggered(ctx, atlas, holy, region.id)
    ctx.session.add(MemoryRow(holder_node_id=hold.id, subject_node_id=hold.id, kind=MemoryKind.DESECRATED_HOLY, magnitude=-20, epoch=ctx.epoch, decay_pct=10))
    await ctx.session.flush()
    assert await triggered(ctx, atlas, holy, region.id)
    deep = tick(ctx.session, tuned(rules, "monsters", emerge_depth_pct=50, emerge_pct=100))
    assert await emerge_from_deep(deep, atlas) == 1
    emerged = await ctx.session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.BEAST, EntityRow.subtype == "monster of the deep"))
    assert emerged is not None
    body = await ctx.session.get(CreatureAnatomyRow, emerged.id)
    assert body is not None and body.habitat is Habitat.DEEP and body.awakening is AwakeningTrigger.DEEP_MINING
    profile = await ctx.session.get(BeastProfileRow, emerged.id)
    assert profile is not None and profile.size_class in MONSTER_SIZES
    assert await known_plan(ctx.session, emerged.id) in MONSTER_PLANS


async def test_an_abductor_carries_people_off_and_its_death_frees_them(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Night Vale", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    victim = await mortal(ctx.session, cosmos, hold.id, "Lio")
    horror, row = await beast(ctx, cosmos, region.id, "Night Taker")
    ctx.session.add(anatomy(horror.id, temperament=Temperament.SEIZES_PREY))
    await ctx.session.flush()
    eager = tick(ctx.session, tuned(rules, "monsters", abduct_pct=100))
    assert await carry_off(eager, horror, row, [hold]) is not None
    captive = await ctx.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == victim.id))
    assert captive is not None and captive.status is CaptiveStatus.HELD and captive.captor_entity_id == horror.id
    assert await free_captives(ctx, horror) == 1
    freed = await ctx.session.scalar(select(CaptiveRow.status).where(CaptiveRow.id == captive.id))
    assert freed is CaptiveStatus.RESCUED and victim.location_id == hold.id


async def test_void_creatures_roam_between_worlds_carry_riders_and_yield_void_glass(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Rim Vale", cosmos.home.id)
    far = await make_world(ctx.session, "Far Rim")
    landing = await make_region(ctx.session, "Far Shore", far.id)
    road = RouteRow(world_a_id=cosmos.home.id, world_b_id=far.id, method=TravelMethod.ANCIENT_GATE, duration_epochs=1, danger=10, created_epoch=1)
    ctx.session.add(road)
    drifter, row = await beast(ctx, cosmos, region.id, "Rim Drifter")
    ctx.session.add(anatomy(drifter.id, habitat=Habitat.VOID))
    await ctx.session.flush()
    roaming = tick(ctx.session, tuned(rules, "monsters", void_roam_pct=100))
    assert await roam_void(roaming, await RegionAtlas.load(ctx.session)) == 1
    assert drifter.world_id == far.id and drifter.location_id == landing.id and road.danger > 10
    rider = await mortal(ctx.session, cosmos, region.id, "Sel")
    row.temper, row.bound_to_node_id = BeastTemper.TAMED, rider.id
    row.size_class = SizeClass.SMALL
    await ctx.session.flush()
    assert await has_beast_mount(ctx.session, rider.id)
    hold = await town(ctx.session, cosmos, region.id, "Slayer Hold")
    hunter = await mortal(ctx.session, cosmos, hold.id, "Kor")
    assert await void_trophy(ctx, drifter, hunter) > 0
    assert await holding(ctx.session, hold.id, CommodityKind.LUXURIES, MaterialKind.VOID_GLASS) > 0


async def test_necromancers_raise_towers_and_hosts_and_besiege_towns(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Grave Vale", cosmos.home.id)
    home = await town(ctx.session, cosmos, region.id, "Grave Hold")
    await town(ctx.session, cosmos, region.id, "Near Hold")
    necro = await mortal(ctx.session, cosmos, home.id, "Vesk")
    rite = await make_entity(ctx.session, "Rite of Rising", EntityType.RITE, RiteStats(power=3), world_id=cosmos.home.id)
    ctx.session.add(RiteProfileRow(rite_entity_id=rite.id, school=MagicSchool.DEATH, source=MagicSource.SOUL, power=3))
    ctx.session.add(BondRow(source_node_id=necro.id, target_node_id=rite.id, kind=BondKind.OWNS, epoch=1))
    await ctx.session.flush()
    eager = tick(ctx.session, tuned(rules, "monsters", necro_tower_pct=100, necro_raise_pct=100, necro_siege_pct=100))
    assert (await necromancy(eager)).towers == 1
    tower = await ctx.session.scalar(select(StructureProfileRow).where(StructureProfileRow.builder_entity_id == necro.id))
    assert tower is not None and tower.kind is StructureKind.TOWER
    assert (await necromancy(eager)).hosts == 1
    host = await ctx.session.scalar(select(ArmyRow).where(ArmyRow.owner_entity_id == necro.id))
    assert host is not None
    assert (await necromancy(eager)).sieges == 1
    assert await ctx.session.scalar(select(SiegeRow).where(SiegeRow.besieger_entity_id == host.entity_id)) is not None


async def test_the_god_shapes_and_reshapes_a_body(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Shape Vale", cosmos.home.id)
    horror, _ = await beast(ctx, cosmos, region.id)
    row = await edit_anatomy(ctx, horror.id, {"heads": 3, "skin": "vapour", "habitat": "void"}, release=[])
    assert (row.heads, row.skin, row.habitat) == (3, TissueMaterial.VAPOUR, Habitat.VOID)
    assert set(row.locked) == {"heads", "skin", "habitat"}
    fresh = await reroll_anatomy(ctx, horror.id)
    assert fresh.locked == [] and fresh.node_id == horror.id
    assert horror.status is EntityStatus.CANON


def test_stone_skin_and_metal_bones_are_the_layers_a_blade_must_pass(rules: Rules) -> None:
    head = anatomy_of(BodyPlan.QUADRUPED).parts[0]
    flesh = tissue_hit(rules, BodyPlan.QUADRUPED, head, DamageType.CUT, 3)
    stone = tissue_hit(rules, BodyPlan.QUADRUPED, head, DamageType.CUT, 3, hardness=Hardness(TissueMaterial.MINERAL))
    metal = tissue_hit(rules, BodyPlan.QUADRUPED, head, DamageType.CUT, 3, hardness=Hardness(None, TissueMaterial.METALLIC))
    assert flesh.bone and flesh.organ
    assert stone.deepest is TissueKind.MUSCLE and not stone.bone
    assert metal.deepest is TissueKind.MUSCLE and not metal.bone
    hard = anatomy(1, skin=TissueMaterial.MINERAL, bone=TissueMaterial.MINERAL)
    assert hardness_of(hard) == Hardness(TissueMaterial.MINERAL, TissueMaterial.MINERAL) and hardness_of(None) == PLAIN
    assert skin_kept(rules, hard) < skin_kept(rules, anatomy(2, skin=TissueMaterial.SOFT_TISSUE)) == 1.0 == skin_kept(rules, None)


async def test_a_beast_is_wounded_through_the_body_of_its_kind_and_a_lone_monster_through_its_own(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Plan Vale", cosmos.home.id)
    eel = await make_entity(ctx.session, "Vale Eel", EntityType.SPECIES, SpeciesStats(hp=20), world_id=cosmos.home.id, location_id=region.id)
    await profile_of(ctx, eel, SpeciesSpec(body_plan=BodyPlan.SERPENTINE))
    kin = await make_entity(ctx.session, "Old Eel", EntityType.BEAST, BeastStats(hp=60), world_id=cosmos.home.id, location_id=region.id)
    await profile_beast(ctx, kin, eel)
    body = await ensure_body(ctx.session, ctx.rules, kin, ctx.epoch)
    assert body.plan is BodyPlan.SERPENTINE
    lone, _ = await beast(ctx, cosmos, region.id, "Lone Horror")
    assert (await ensure_body(ctx.session, ctx.rules, lone, ctx.epoch)).plan is wild_plan(lone.id) in MONSTER_PLANS
    assert await known_plan(ctx.session, lone.id) is wild_plan(lone.id)


async def test_old_beasts_given_a_human_body_are_given_the_body_of_their_kind_once(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Mend Vale", cosmos.home.id)
    crab = await make_entity(ctx.session, "Vale Crab", EntityType.SPECIES, SpeciesStats(hp=20), world_id=cosmos.home.id, location_id=region.id)
    await profile_of(ctx, crab, SpeciesSpec(body_plan=BodyPlan.INSECTOID))
    old = await make_entity(ctx.session, "Old Crab", EntityType.BEAST, BeastStats(hp=60), world_id=cosmos.home.id, location_id=region.id)
    await profile_beast(ctx, old, crab)
    ctx.session.add(BodyRow(node_id=old.id, plan=BodyPlan.HUMANOID, traits=[], fingers=10, hp_max=60, updated_epoch=1, locked=[]))
    await ctx.session.flush()
    assert await fit_beast_bodies(ctx.session) == 1
    fixed = await ctx.session.get(BodyRow, old.id)
    assert fixed is not None and fixed.plan is BodyPlan.INSECTOID
    assert await ctx.session.get(AppliedFixupRow, BEAST_BODIES_FIXUP) is not None
    fixed.plan = BodyPlan.HUMANOID
    assert await fit_beast_bodies(ctx.session) == 0


async def test_each_gaze_strikes_a_raided_town_its_own_way(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Gaze Vale", cosmos.home.id)
    hold = await town(ctx.session, cosmos, region.id)
    folk = [await mortal(ctx.session, cosmos, hold.id, name) for name in ("Ari", "Bel")]
    horror, _ = await beast(ctx, cosmos, region.id, "Gazer")
    lair = BeastProfileRow(beast_entity_id=horror.id)
    assert await sight_scale(ctx, horror, hold, []) == 1.0
    sleep = attack(horror.id, AttackDelivery.GAZE, AttackEffect.SLEEP, AttackRange.SIGHT)
    assert await sight_scale(ctx, horror, hold, [sleep]) == 1 + rules.creature_anatomy.sleep_raid_pct / 100
    await strike(ctx, horror, lair, hold, stored(ctx, attack(horror.id, AttackDelivery.GAZE, AttackEffect.FEAR, AttackRange.SIGHT)))
    for person in folk:
        profile = await ctx.session.get(MortalProfileRow, person.id)
        assert profile is not None and profile.stress > 0
    await strike(ctx, horror, lair, hold, stored(ctx, attack(horror.id, AttackDelivery.GAZE, AttackEffect.STILLNESS, AttackRange.SIGHT)))
    await strike(ctx, horror, lair, hold, stored(ctx, attack(horror.id, AttackDelivery.VOICE, AttackEffect.CONFUSION, AttackRange.FAR)))
    kinds = set(await ctx.session.scalars(select(ConditionRow.kind).where(ConditionRow.bearer_node_id.in_([person.id for person in folk]))))
    assert ConditionKind.WITHERED_LIMB in kinds and kinds & set(MADNESS_CONDITIONS)


async def test_a_monsters_body_counts_against_heroes(ctx: TickContext, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(ctx.session, "Might Vale", cosmos.home.id)
    horror, _ = await beast(ctx, cosmos, region.id, "Iron Wyrm")
    assert await body_might(ctx.session, rules, horror.id) == 1.0
    ctx.session.add(anatomy(horror.id, skin=TissueMaterial.METALLIC, bone=TissueMaterial.METALLIC, limbs=4, heads=1))
    ctx.session.add(attack(horror.id, AttackDelivery.BREATH, AttackEffect.HEAT))
    await ctx.session.flush()
    assert await body_might(ctx.session, rules, horror.id) > 1.0
