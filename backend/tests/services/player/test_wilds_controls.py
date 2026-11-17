import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import (
    BeastProfileRow,
    HerdRow,
    SpeciesCustomUseRow,
    SpeciesHostRow,
    SpeciesProductRow,
    SpeciesProfileRow,
    SpeciesRangeRow,
    SpeciesUseKindRow,
    SpeciesUseRow,
)
from aerona.db.tables.economy import PROPERTY_COLUMNS, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import AnimalRole, BeastTemper, Diet, DomesticationStage, FoodLink, SizeClass, Sociality, YieldProduct
from aerona.domain.enums.economy import CommodityKind, MaterialFamily, MaterialOrigin
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import DiseaseStats, EntityStats, ItemStats, MortalStats, PeopleStats, SettlementStats
from aerona.services.player import wilds
from aerona.services.player.catalog import WILDS_ACTIONS
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, ledger_entries

WILD_ACTIONS = (
    "species:create",
    "species:prey",
    "species:custom_use",
    "use_kind:create",
    "use_kind:edit",
    "use_kind:drop",
    "herd:drop",
    "people:totem",
    "beast:create",
    "beast:slay",
    "beast:treasure",
)


async def thing(session: AsyncSession, world: PlayerWorld, name: str, entity_type: EntityType, stats: EntityStats) -> EntityRow:
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=f"The {name}.",
            stats=stats,
            power_level=2,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world.world.id,
            location_id=world.region.id,
        )
    )


async def species(scope: PlayerScope, world: PlayerWorld, name: str, diet: Diet = Diet.HERBIVORE, size: SizeClass = SizeClass.MEDIUM) -> EntityRow:
    command = wilds.CreateSpecies(
        name=name,
        region_id=world.region.id,
        body_plan=BodyPlan.QUADRUPED,
        size_class=size,
        diet=diet,
        sociality=Sociality.HERD,
        nocturnal=True,
        migratory=False,
        products=[YieldProduct.SILK],
        traits=[CreatureTrait.CAMOUFLAGE],
        strength=40,
        danger=20,
        abundance=55,
    )
    effect = await wilds.create_species(scope, command)
    created = await scope.session.get(EntityRow, effect.created_ids[0])
    assert created is not None
    return created


def test_every_wilds_lever_is_in_the_catalogue() -> None:
    names = {action.id for action in WILDS_ACTIONS}
    assert set(WILD_ACTIONS) <= names


async def test_the_creator_makes_a_kind_with_a_chosen_nature(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    made = await species(scope, world, "Mistlope")
    profile = await session.get(SpeciesProfileRow, made.id)
    assert profile is not None and profile.nocturnal and profile.diet is Diet.HERBIVORE and profile.sociality is Sociality.HERD
    assert CreatureTrait.CAMOUFLAGE in await EntityRepository(session).traits(made.id)
    home = await session.get(SpeciesRangeRow, (made.id, world.region.id))
    assert home is not None and home.abundance == 55
    assert await ledger_entries(session)


async def test_prey_links_are_pinned_forbidden_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    wolf = await species(scope, world, "Greywolf", Diet.CARNIVORE)
    deer = await species(scope, world, "Reddeer")
    await wilds.set_prey(scope, wilds.Prey(hunter_id=wolf.id, prey_id=deer.id, link=FoodLink.PINNED))
    profile = await session.get(SpeciesProfileRow, wolf.id)
    assert profile is not None and profile.pinned_prey == [deer.id]
    active = select(BondRow).where(BondRow.source_node_id == wolf.id, BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE)
    assert await session.scalar(active) is not None
    await wilds.set_prey(scope, wilds.Prey(hunter_id=wolf.id, prey_id=deer.id, link=FoodLink.BARRED))
    assert profile.barred_prey == [deer.id] and profile.pinned_prey == []
    assert await session.scalar(active) is None
    await wilds.set_prey(scope, wilds.Prey(hunter_id=wolf.id, prey_id=deer.id, link=FoodLink.DERIVED))
    assert profile.barred_prey == [] and profile.pinned_prey == []
    with pytest.raises(ValidationFailedError):
        await wilds.set_prey(scope, wilds.Prey(hunter_id=wolf.id, prey_id=wolf.id, link=FoodLink.PINNED))


async def test_a_host_immunity_is_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    rat = await species(scope, world, "Sewer Rat", Diet.OMNIVORE, SizeClass.SMALL)
    pox = await thing(session, world, "Grey Pox", EntityType.DISEASE, DiseaseStats())
    await wilds.set_host(scope, wilds.Host(species_id=rat.id, disease_id=pox.id, carried=True, immune=True))
    host = await session.get(SpeciesHostRow, (rat.id, pox.id))
    assert host is not None and host.immune and host.locked == ["immune"]
    await wilds.set_host(scope, wilds.Host(species_id=rat.id, disease_id=pox.id, carried=True, immune=False, release=True))
    assert not host.immune and host.locked == []
    await wilds.set_host(scope, wilds.Host(species_id=rat.id, disease_id=pox.id, carried=False))
    assert await session.get(SpeciesHostRow, (rat.id, pox.id)) is None


async def test_ways_of_keeping_are_devised_kept_reshaped_and_forgotten(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hound = await species(scope, world, "Ashhound", Diet.CARNIVORE)
    effect = await wilds.create_use_kind(scope, wilds.NewUseKind(name="Grave-guarding", base_use=AnimalRole.GUARD, output_pct=150))
    kind_id = int(effect.values["kind_id"] or 0)
    await wilds.set_custom_use(scope, wilds.CustomUse(species_id=hound.id, kind_id=kind_id))
    assert await session.get(SpeciesCustomUseRow, (hound.id, kind_id)) is not None
    assert await session.get(SpeciesUseRow, (hound.id, AnimalRole.GUARD)) is not None
    await wilds.edit_use_kind(scope, wilds.EditUseKind(kind_id=kind_id, values={"output_pct": 200}))
    kind = await session.get(SpeciesUseKindRow, kind_id)
    assert kind is not None and kind.output_pct == 200 and kind.locked == ["output_pct"]
    await wilds.edit_use_kind(scope, wilds.EditUseKind(kind_id=kind_id, release=["output_pct"]))
    assert kind.locked == []
    await wilds.drop_use_kind(scope, wilds.UseKindTarget(kind_id=kind_id))
    assert await session.get(SpeciesUseKindRow, kind_id) is None


async def test_a_herd_is_scattered(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    goat = await species(scope, world, "Hill Goat")
    town = await thing(session, world, "Brae", EntityType.SETTLEMENT, SettlementStats(population=100))
    session.add(HerdRow(community_entity_id=town.id, species_entity_id=goat.id, head=20, stage=DomesticationStage.TAMED, locked=[]))
    await session.flush()
    await wilds.drop_herd(scope, wilds.HerdTarget(community_id=town.id, species_id=goat.id))
    assert await session.get(HerdRow, (town.id, goat.id)) is None
    with pytest.raises(NotFoundError):
        await wilds.drop_herd(scope, wilds.HerdTarget(community_id=town.id, species_id=goat.id))


async def test_a_people_takes_and_sets_aside_a_totem(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    bear = await species(scope, world, "Cave Bear", Diet.OMNIVORE, SizeClass.LARGE)
    people = await thing(session, world, "Bearfolk", EntityType.PEOPLE, PeopleStats(population=300))
    effect = await wilds.set_totem(scope, wilds.Totem(people_id=people.id, species_id=bear.id))
    assert effect.created_ids
    kept = select(BondRow).where(BondRow.source_node_id == people.id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    assert await session.scalar(kept) is not None
    await wilds.set_totem(scope, wilds.Totem(people_id=people.id, species_id=None))
    assert await session.scalar(kept) is None


async def test_a_beast_is_called_forth_given_treasure_and_slain(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    wyrm = await species(scope, world, "Ember Wyrm", Diet.CARNIVORE, SizeClass.HUGE)
    effect = await wilds.create_beast(
        scope,
        wilds.CreateBeast(
            name="Vharrun",
            species_id=wyrm.id,
            lair_id=world.region.id,
            size_class=SizeClass.COLOSSAL,
            temper=BeastTemper.HUNGRY,
            strength=90,
            terror=40,
            endurance=80,
            perception=70,
            willpower=60,
            intelligence=66,
        ),
    )
    beast = await session.get(EntityRow, effect.created_ids[0])
    row = await session.get(BeastProfileRow, effect.created_ids[0])
    assert beast is not None and row is not None
    assert (row.size_class, row.temper, row.endurance, row.perception, row.willpower, row.intelligence) == (
        SizeClass.COLOSSAL,
        BeastTemper.HUNGRY,
        80,
        70,
        60,
        66,
    )
    assert row.locked == [] and row.lair_place_id == world.region.id
    assert (beast.stats.hp or 0) > 0
    cup = await thing(session, world, "Gold Cup", EntityType.ITEM, ItemStats())
    await wilds.move_treasure(scope, wilds.Treasure(beast_id=beast.id, item_id=cup.id, into_hoard=True))
    owner = select(BondRow.source_node_id).where(BondRow.target_node_id == cup.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    assert await session.scalar(owner) == beast.id
    hero = await thing(session, world, "Edda", EntityType.MORTAL, MortalStats(age=30, lifespan=70))
    with pytest.raises(NotFoundError):
        await wilds.move_treasure(scope, wilds.Treasure(beast_id=beast.id, item_id=cup.id, into_hoard=False))
    row.hoard = {CommodityKind.LIVESTOCK.value: 10}
    await wilds.slay(scope, wilds.Slay(beast_id=beast.id, slayer_id=hero.id))
    assert beast.status is not EntityStatus.CANON
    assert await session.scalar(owner) == hero.id
    assert hero.title == "Slayer of Vharrun"
    assert await BondRepository(session).exists_between(hero.id, beast.id, BondKind.KILLED)


async def test_a_yield_can_name_a_world_material(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    moth = await species(scope, world, "Star Moth", Diet.HERBIVORE, SizeClass.TINY)
    with pytest.raises(NotFoundError):
        await wilds.set_yield(
            scope, wilds.SpeciesYield(species_id=moth.id, product="starsilk", commodity=CommodityKind.CLOTH, world_material_id=999999, rate=2)
        )
    stuff = WorldMaterialRow(
        world_id=world.world.id,
        origin=MaterialOrigin.BEAST,
        base_kind=MaterialKind.CLOTH,
        name="Starsilk",
        family=MaterialFamily.ORGANIC,
        **dict.fromkeys(PROPERTY_COLUMNS, 50),
        created_epoch=1,
    )
    session.add(stuff)
    await session.flush()
    await wilds.set_yield(scope, wilds.SpeciesYield(species_id=moth.id, product="starsilk", commodity=CommodityKind.CLOTH, world_material_id=stuff.id, rate=2))
    row = await session.get(SpeciesProductRow, (moth.id, "starsilk"))
    assert row is not None and row.world_material_id == stuff.id and row.material is MaterialKind.CLOTH
