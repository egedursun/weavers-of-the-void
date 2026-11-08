from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.wilds import (
    AnatomyView,
    BeastCard,
    BeastTributeView,
    BeastWound,
    CropView,
    CustomUseView,
    FoodWeb,
    HerdView,
    HostView,
    LifeKind,
    MortalPets,
    PetView,
    PlantView,
    RangeCell,
    RangeView,
    RegionCrops,
    SownView,
    SpeciesCard,
    SpeciesRangeMap,
    TotemView,
    UseKindView,
    WebLink,
    WebNode,
    WorldLife,
    WoundView,
    YieldView,
)
from aerona.api.views.common import node_refs
from aerona.catalog.flora import BIOCHEMISTRY_LABELS, PRODUCT_BY_NAME
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.ecology import (
    BeastProfileRow,
    HerdRow,
    SpeciesCustomUseRow,
    SpeciesHostRow,
    SpeciesProfileRow,
    SpeciesRangeRow,
    SpeciesUseKindRow,
    SpeciesUseRow,
    SpeciesYieldRow,
)
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.flora import CropPestRow, PlantProfileRow, RegionCropRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import UNBOUND_BIOCHEMISTRY, Biochemistry, FoodLink, PlantYield
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind, TreatyStatus
from aerona.engine.ecology.anatomy import armour_of, harm_factor, plan_limbs
from aerona.engine.ecology.beasts import RIDEABLE, reach_of, rest_chance, tame_chance, wake_chance, wound_harm
from aerona.engine.ecology.biochemistry import bearable, tolerated
from aerona.engine.ecology.flora import CropBook
from aerona.engine.ecology.pets import animal_kind_ids, hunting_kinds
from aerona.engine.ecology.pets import pet_kind_ids as pet_kinds_of
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["wilds"])
Id = Annotated[int, Path(ge=1)]
Refs = dict[int, NodeRef]


def ref(refs: Refs, node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def listed(refs: Refs, ids: list[int]) -> list[NodeRef]:
    return [refs[item] for item in ids if item in refs]


@router.get("/entities/{entity_id}/ecology", response_model=SpeciesCard)
async def species_card(entity_id: Id, services: ServicesDep) -> SpeciesCard:
    async with reader(services) as session:
        row = await session.get(SpeciesProfileRow, entity_id)
        if row is None:
            raise NotFoundError("The world has not yet described this kind; it will after the next epoch.")
        ranges = list(
            await session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == entity_id).order_by(SpeciesRangeRow.abundance.desc()))
        )
        yields = list(await session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == entity_id).order_by(SpeciesYieldRow.product)))
        uses = list(await session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == entity_id).order_by(SpeciesUseRow.use)))
        hosts = list(await session.scalars(select(SpeciesHostRow).where(SpeciesHostRow.species_entity_id == entity_id)))
        herds = list(await session.scalars(select(HerdRow).where(HerdRow.species_entity_id == entity_id).order_by(HerdRow.head.desc())))
        traits = list(await session.scalars(select(EntityTraitRow.trait).where(EntityTraitRow.entity_id == entity_id).order_by(EntityTraitRow.trait)))
        active = (BondRow.state == BondState.ACTIVE, BondRow.kind == BondKind.HUNTS)
        hunts = list(await session.scalars(select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, *active)))
        hunted_by = list(await session.scalars(select(BondRow.source_node_id).where(BondRow.target_node_id == entity_id, *active)))
        descendants = list(
            await session.scalars(select(BondRow.source_node_id).where(BondRow.target_node_id == entity_id, BondRow.kind == BondKind.DESCENDS_FROM))
        )
        beasts = list(await session.scalars(select(BeastProfileRow.beast_entity_id).where(BeastProfileRow.species_entity_id == entity_id)))
        customs = list(
            await session.scalars(
                select(SpeciesUseKindRow)
                .join(SpeciesCustomUseRow, SpeciesCustomUseRow.kind_id == SpeciesUseKindRow.id)
                .where(SpeciesCustomUseRow.species_entity_id == entity_id)
                .order_by(SpeciesUseKindRow.name)
            )
        )
        stuffs = {
            row.id: row.name
            for row in await session.scalars(
                select(WorldMaterialRow).where(WorldMaterialRow.id.in_([item.world_material_id for item in yields if item.world_material_id is not None]))
            )
        }
        totems = list(
            await session.scalars(
                select(BondRow.source_node_id)
                .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == BondRow.target_node_id)
                .where(BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE, TraditionProfileRow.origin_entity_id == entity_id)
            )
        )
        species = await session.get(EntityRow, entity_id)
        plant = await session.get(PlantProfileRow, entity_id)
        sown = list(await session.scalars(select(RegionCropRow).where(RegionCropRow.plant_entity_id == entity_id).order_by(RegionCropRow.share.desc())))
        pests = list(await session.scalars(select(CropPestRow.pest_entity_id).where(CropPestRow.plant_entity_id == entity_id)))
        pest_of = list(await session.scalars(select(CropPestRow.plant_entity_id).where(CropPestRow.pest_entity_id == entity_id)))
        crops = await CropBook.load(session, await world_rules(services, session)) if sown else None
        allowed = await tolerated(session, species.world_id if species is not None else None)
        ids = [
            *(item.region_entity_id for item in sown),
            *pests,
            *pest_of,
            *([plant.cultivar_of_id] if plant is not None and plant.cultivar_of_id is not None else []),
            *(item.region_entity_id for item in ranges),
            *(item.disease_entity_id for item in hosts),
            *(item.community_entity_id for item in herds),
            *hunts,
            *hunted_by,
            *descendants,
            *beasts,
            *row.migration_path,
            *row.pinned_prey,
            *row.barred_prey,
            *totems,
            *(item for item in (row.domesticated_from_id, row.sacred_to_node_id) if item is not None),
        ]
        refs = await node_refs(session, ids)
        return SpeciesCard(
            species_id=entity_id,
            world_id=species.world_id if species is not None else None,
            species_class=row.species_class,
            biochemistry=row.biochemistry,
            bearable=bearable(row.biochemistry, allowed) or species is None or species.world_id is None,
            plant=PlantView(
                growth_cycle=plant.growth_cycle,
                growing_seasons=plant.growing_seasons,
                soil_need=plant.soil_need,
                cultivation=plant.cultivation,
                cultivar_of=ref(refs, plant.cultivar_of_id),
                since_epoch=plant.since_epoch,
                locked=plant.locked,
            )
            if plant is not None
            else None,
            sown_in=[
                SownView(
                    region=ref(refs, item.region_entity_id),
                    share=item.share,
                    fit=round(crops.fit(entity_id, item.region_entity_id) * PERCENT) if crops is not None else 0,
                    since_epoch=item.since_epoch,
                    locked=item.locked,
                )
                for item in sown
            ],
            pests=listed(refs, pests),
            pest_of=listed(refs, pest_of),
            body_plan=row.body_plan,
            size_class=row.size_class,
            lifespan_years=row.lifespan_years,
            maturity_years=row.maturity_years,
            litter_size=row.litter_size,
            breeding_seasons=row.breeding_seasons,
            diet=row.diet,
            metabolism=row.metabolism,
            habitat=row.habitat,
            temperature_min=row.temperature_min,
            temperature_max=row.temperature_max,
            water_need=row.water_need,
            altitude_min=row.altitude_min,
            altitude_max=row.altitude_max,
            nocturnal=row.nocturnal,
            migratory=row.migratory,
            migration_path=listed(refs, row.migration_path),
            aggression=row.aggression,
            territoriality=row.territoriality,
            sociality=row.sociality,
            cunning=row.cunning,
            fear_of_people=row.fear_of_people,
            tameability=row.tameability,
            stage=row.stage,
            domesticated_from=ref(refs, row.domesticated_from_id),
            sacred_to=ref(refs, row.sacred_to_node_id),
            traits=traits,
            uses=uses,
            yields=[
                YieldView(
                    product=item.product,
                    commodity=item.commodity,
                    material=item.material,
                    world_material_id=item.world_material_id,
                    world_material=stuffs.get(item.world_material_id) if item.world_material_id is not None else None,
                    rate=item.rate,
                )
                for item in yields
            ],
            hosts=[HostView(disease=ref(refs, item.disease_entity_id), immune=item.immune, locked=item.locked) for item in hosts],
            ranges=[
                RangeView(
                    region=ref(refs, item.region_entity_id),
                    abundance=item.abundance,
                    trend=item.trend,
                    fit=item.fit,
                    hunted=item.hunted,
                    since_epoch=item.since_epoch,
                    locked=item.locked,
                )
                for item in ranges
            ],
            herds=[
                HerdView(
                    community=ref(refs, item.community_entity_id),
                    species=refs.get(entity_id),
                    head=item.head,
                    stage=item.stage,
                    since_epoch=item.since_epoch,
                    fed_epochs=item.fed_epochs,
                    training=item.training,
                    trained=item.trained,
                    locked=item.locked,
                )
                for item in herds
            ],
            hunts=listed(refs, hunts),
            hunted_by=listed(refs, hunted_by),
            descendants=listed(refs, descendants),
            beasts=listed(refs, beasts),
            pinned_prey=listed(refs, row.pinned_prey),
            barred_prey=listed(refs, row.barred_prey),
            custom_uses=[CustomUseView(kind_id=item.id, name=item.name, base_use=item.base_use, output_pct=item.output_pct) for item in customs],
            totem_of=listed(refs, totems),
            abundance=stat(species, "abundance") or 0 if species is not None else 0,
            stage_epoch=row.stage_epoch,
            locked=row.locked,
        )


@router.get("/entities/{entity_id}/beast", response_model=BeastCard)
async def beast_card(entity_id: Id, services: ServicesDep) -> BeastCard:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        beast = await session.get(EntityRow, entity_id)
        row = await session.get(BeastProfileRow, entity_id)
        if beast is None or row is None:
            raise NotFoundError("No such beast.")
        wounds = list(
            await session.scalars(
                select(MemoryRow)
                .where(MemoryRow.holder_node_id == entity_id, MemoryRow.kind == MemoryKind.HARMED_ME)
                .order_by(MemoryRow.epoch.desc(), MemoryRow.id.desc())
            )
        )
        treasures = list(
            await session.scalars(
                select(BondRow.target_node_id)
                .join(EntityRow, EntityRow.id == BondRow.target_node_id)
                .where(
                    BondRow.source_node_id == entity_id,
                    BondRow.kind == BondKind.OWNS,
                    BondRow.state == BondState.ACTIVE,
                    EntityRow.entity_type == EntityType.ITEM,
                )
                .order_by(BondRow.target_node_id)
            )
        )
        tributes = list(
            await session.execute(
                select(TreatyClauseRow)
                .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
                .where(
                    TreatyProfileRow.status == TreatyStatus.IN_FORCE,
                    TreatyClauseRow.kind == ClauseKind.TRIBUTE,
                    TreatyClauseRow.beneficiary_node_id == entity_id,
                )
                .order_by(TreatyClauseRow.id)
            )
        )
        clauses = [item for (item,) in tributes]
        owners = list(
            await session.scalars(
                select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, BondRow.kind == BondKind.PET_OF, BondRow.state == BondState.ACTIVE)
            )
        )
        ids = [
            *(item for item in (row.species_entity_id, row.lair_place_id, row.bound_to_node_id) if item is not None),
            *owners,
            *(item.subject_node_id for item in wounds),
            *treasures,
            *(item.treaty_entity_id for item in clauses),
            *(item.obligor_node_id for item in clauses if item.obligor_node_id is not None),
        ]
        injuries = list(await session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == entity_id).order_by(InjuryRow.id)))
        body = await session.get(BodyRow, entity_id)
        refs = await node_refs(session, ids)
        return BeastCard(
            beast_id=entity_id,
            species=ref(refs, row.species_entity_id),
            endurance=row.endurance,
            perception=row.perception,
            willpower=row.willpower,
            intelligence=row.intelligence,
            age=row.age,
            lifespan=row.lifespan,
            size_class=row.size_class,
            lair=ref(refs, row.lair_place_id),
            temper=row.temper,
            bound_to=ref(refs, row.bound_to_node_id),
            pet_of=ref(refs, owners[0]) if owners else None,
            hoard=row.hoard,
            raids=row.raids,
            woke_epoch=row.woke_epoch,
            terror=stat(beast, "terror") or 0,
            renown=stat(beast, "renown") or 0,
            wounds=[WoundView(by=ref(refs, item.subject_node_id), epoch=item.epoch) for item in wounds],
            injuries=[
                BeastWound(part=item.part, kind=item.kind.value, severity=item.severity, state=item.state.value, function_loss=item.function_loss)
                for item in injuries
            ],
            body_plan=body.plan.value if body is not None else None,
            hp=stat(beast, "hp") or 0,
            treasures=listed(refs, treasures),
            tributes=[
                BeastTributeView(
                    town=ref(refs, item.obligor_node_id),
                    treaty=ref(refs, item.treaty_entity_id),
                    commodity=CommodityKind(str(item.params.get("commodity", CommodityKind.LUXURIES.value))),
                    units=int(item.params.get("units", rules.beasts.tribute_hoard)),
                    last_kept_epoch=item.last_kept_epoch,
                )
                for item in clauses
            ],
            reach=reach_of(rules, row),
            harm_taken_pct=round(wound_harm(rules, row) * PERCENT / max(1, rules.beasts.wound_damage)),
            wake_pct=wake_chance(rules, row),
            tame_pct=tame_chance(rules, row),
            rest_pct=rest_chance(rules, row),
            rideable=row.size_class in RIDEABLE,
            locked=row.locked,
        )


@router.get("/regions/{region_id}/food-web", response_model=FoodWeb)
async def food_web(region_id: Id, services: ServicesDep) -> FoodWeb:
    async with reader(services) as session:
        rows = list(
            await session.execute(
                select(SpeciesRangeRow, SpeciesProfileRow)
                .join(SpeciesProfileRow, SpeciesProfileRow.species_entity_id == SpeciesRangeRow.species_entity_id)
                .where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0)
                .order_by(SpeciesRangeRow.abundance.desc())
            )
        )
        ids = [item.species_entity_id for item, _ in rows]
        refs = await node_refs(session, ids)
        bonds = await session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id).where(
                BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(ids), BondRow.target_node_id.in_(ids)
            )
        )
        pinned = {(profile.species_entity_id, prey) for _, profile in rows for prey in profile.pinned_prey}
        return FoodWeb(
            region_id=region_id,
            nodes=[
                WebNode(species=refs[item.species_entity_id], abundance=item.abundance, diet=profile.diet, size_class=profile.size_class)
                for item, profile in rows
                if item.species_entity_id in refs
            ],
            links=[WebLink(hunter_id=hunter, prey_id=prey, kind=FoodLink.PINNED if (hunter, prey) in pinned else FoodLink.DERIVED) for hunter, prey in bonds],
        )


@router.get("/entities/{entity_id}/herds", response_model=list[HerdView])
async def herds(entity_id: Id, services: ServicesDep) -> list[HerdView]:
    async with reader(services) as session:
        rows = list(await session.scalars(select(HerdRow).where(HerdRow.community_entity_id == entity_id).order_by(HerdRow.head.desc())))
        refs = await node_refs(session, [entity_id, *(item.species_entity_id for item in rows)])
        return [
            HerdView(
                community=refs.get(entity_id),
                species=ref(refs, item.species_entity_id),
                head=item.head,
                stage=item.stage,
                since_epoch=item.since_epoch,
                fed_epochs=item.fed_epochs,
                training=item.training,
                trained=item.trained,
                locked=item.locked,
            )
            for item in rows
        ]


@router.get("/species/{species_id}/range-map", response_model=SpeciesRangeMap)
async def range_map(species_id: Id, services: ServicesDep) -> SpeciesRangeMap:
    async with reader(services) as session:
        species = await session.get(EntityRow, species_id)
        if species is None or species.entity_type is not EntityType.SPECIES:
            raise NotFoundError("No such species.")
        rows = list(
            await session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == species_id).order_by(SpeciesRangeRow.abundance.desc()))
        )
        refs = await node_refs(session, [item.region_entity_id for item in rows])
        cells = [
            RangeCell(region=refs[item.region_entity_id], abundance=item.abundance, trend=item.trend, fit=item.fit)
            for item in rows
            if item.region_entity_id in refs
        ]
        return SpeciesRangeMap(species_id=species_id, world_id=species.world_id, peak=max((cell.abundance for cell in cells), default=0), cells=cells)


@router.get("/use-kinds", response_model=list[UseKindView])
async def use_kinds(services: ServicesDep) -> list[UseKindView]:
    async with reader(services) as session:
        kinds = list(await session.scalars(select(SpeciesUseKindRow).order_by(SpeciesUseKindRow.name)))
        held = list(await session.scalars(select(SpeciesCustomUseRow)))
        refs = await node_refs(session, [item.species_entity_id for item in held])
        return [
            UseKindView(
                id=kind.id,
                name=kind.name,
                base_use=kind.base_use,
                output_pct=kind.output_pct,
                description=kind.description,
                locked=kind.locked,
                species=listed(refs, [item.species_entity_id for item in held if item.kind_id == kind.id]),
            )
            for kind in kinds
        ]


@router.get("/entities/{entity_id}/totem", response_model=TotemView)
async def totem(entity_id: Id, services: ServicesDep) -> TotemView:
    async with reader(services) as session:
        found = (
            await session.execute(
                select(TraditionProfileRow.tradition_entity_id, TraditionProfileRow.origin_entity_id)
                .join(BondRow, BondRow.target_node_id == TraditionProfileRow.tradition_entity_id)
                .join(EntityRow, EntityRow.id == TraditionProfileRow.origin_entity_id)
                .where(
                    BondRow.source_node_id == entity_id,
                    BondRow.kind == BondKind.CELEBRATES,
                    BondRow.state == BondState.ACTIVE,
                    EntityRow.entity_type == EntityType.SPECIES,
                )
                .limit(1)
            )
        ).first()
        if found is None:
            return TotemView(people_id=entity_id, species=None, tradition=None)
        tradition_id, species_id = found
        refs = await node_refs(session, [item for item in (tradition_id, species_id) if item is not None])
        return TotemView(people_id=entity_id, species=ref(refs, species_id), tradition=ref(refs, tradition_id))


@router.get("/regions/{region_id}/crops", response_model=RegionCrops)
async def region_crops(region_id: Id, services: ServicesDep) -> RegionCrops:
    async with reader(services) as session:
        region = await session.get(EntityRow, region_id)
        if region is None or region.entity_type is not EntityType.REGION:
            raise NotFoundError("No such region.")
        rules = await world_rules(services, session)
        book = await CropBook.load(session, rules)
        rows = book.crops.get(region_id, [])
        hosts: dict[int, list[int]] = {}
        for plant_id, pest_id in await session.execute(
            select(CropPestRow.plant_entity_id, CropPestRow.pest_entity_id).where(CropPestRow.plant_entity_id.in_([row.plant_entity_id for row in rows]))
        ):
            hosts.setdefault(plant_id, []).append(pest_id)
        refs = await node_refs(session, [*(row.plant_entity_id for row in rows), *(pest for pests in hosts.values() for pest in pests)])
        crops = [
            CropView(
                plant=ref(refs, row.plant_entity_id),
                share=row.share,
                fit=round(book.fit(row.plant_entity_id, region_id) * PERCENT),
                cultivation=book.plants[row.plant_entity_id].cultivation if row.plant_entity_id in book.plants else None,
                products=[PlantYield(item.product) for item in book.yields.get(row.plant_entity_id, []) if item.product in PRODUCT_BY_NAME],
                pests=listed(refs, hosts.get(row.plant_entity_id, [])),
                since_epoch=row.since_epoch,
                locked=row.locked,
            )
            for row in sorted(rows, key=lambda item: (-item.share, item.plant_entity_id))
        ]
        return RegionCrops(
            region_id=region_id, world_id=region.world_id, harvest_pct=round(book.factor(region_id) * PERCENT), crop_cap=rules.flora.crop_cap, crops=crops
        )


@router.get("/worlds/{world_id}/life", response_model=WorldLife)
async def world_life(world_id: Id, services: ServicesDep) -> WorldLife:
    async with reader(services) as session:
        if await session.get(WorldRow, world_id) is None:
            raise NotFoundError("No such world.")
        borne = await tolerated(session, world_id)
        counts: dict[Biochemistry, int] = {}
        for kind in await session.scalars(
            select(SpeciesProfileRow.biochemistry)
            .join(EntityRow, EntityRow.id == SpeciesProfileRow.species_entity_id)
            .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        ):
            counts[kind] = counts.get(kind, 0) + 1
        return WorldLife(
            world_id=world_id,
            kinds=[
                LifeKind(
                    biochemistry=kind,
                    label=BIOCHEMISTRY_LABELS[kind],
                    borne=kind in borne,
                    anywhere=kind in UNBOUND_BIOCHEMISTRY,
                    kinds=counts.get(kind, 0),
                )
                for kind in Biochemistry
            ],
        )


@router.get("/entities/{entity_id}/pets", response_model=MortalPets)
async def mortal_pets(entity_id: Id, services: ServicesDep) -> MortalPets:
    async with reader(services) as session:
        mortal = await session.get(EntityRow, entity_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL:
            raise NotFoundError("Only a mortal keeps pets.")
        rows = list(
            await session.execute(
                select(BondRow, BeastProfileRow)
                .join(BeastProfileRow, BeastProfileRow.beast_entity_id == BondRow.source_node_id)
                .where(BondRow.target_node_id == entity_id, BondRow.kind == BondKind.PET_OF, BondRow.state == BondState.ACTIVE)
                .order_by(BondRow.id)
            )
        )
        kinds = await pet_kinds_of(session, mortal.location_id)
        animals = [kind for kind in await animal_kind_ids(session) if kind not in kinds]
        kept = [row.species_entity_id for _, row in rows if row.species_entity_id is not None]
        refs = await node_refs(session, [*(bond.source_node_id for bond, _ in rows), *kept, *kinds, *animals])
        hunting = await hunting_kinds(session, kept)
        return MortalPets(
            mortal_id=entity_id,
            pets=[
                PetView(
                    pet=ref(refs, bond.source_node_id),
                    species=ref(refs, row.species_entity_id),
                    size_class=row.size_class,
                    age=row.age,
                    lifespan=row.lifespan,
                    hunts=row.species_entity_id in hunting,
                    since_epoch=bond.epoch,
                )
                for bond, row in rows
            ],
            kinds=listed(refs, kinds),
            other_kinds=listed(refs, animals),
        )


@router.get("/nodes/{node_id}/anatomy", response_model=AnatomyView | None)
async def creature_anatomy(node_id: Id, services: ServicesDep) -> AnatomyView | None:
    async with reader(services) as session:
        row = await session.get(CreatureAnatomyRow, node_id)
        if row is None:
            return None
        rules = await world_rules(services, session)
        limbs = await plan_limbs(session, node_id)
        return AnatomyView(
            node_id=node_id,
            limbs=row.limbs,
            heads=row.heads,
            wings=row.wings,
            tails=row.tails,
            skin=row.skin,
            bone=row.bone,
            breath=row.breath,
            bite=row.bite,
            gaze=row.gaze,
            temperament=row.temperament,
            hoards=row.hoards,
            hates=row.hates,
            awakening=row.awakening,
            habitat=row.habitat,
            armour_pct=armour_of(row),
            harm_pct=round((harm_factor(rules, row, limbs) - 1) * PERCENT),
            generated_epoch=row.generated_epoch,
            locked=row.locked,
        )
