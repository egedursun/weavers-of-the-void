from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.wilds import BeastCard, BeastWound, FoodWeb, HerdView, HostView, RangeView, SpeciesCard, WebLink, WebNode, WoundView, YieldView
from aerona.api.views.common import node_refs
from aerona.core.errors import NotFoundError
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesHostRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesUseRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.mind import MemoryKind
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
        ids = [
            *(item.region_entity_id for item in ranges),
            *(item.disease_entity_id for item in hosts),
            *(item.community_entity_id for item in herds),
            *hunts,
            *hunted_by,
            *descendants,
            *beasts,
            *row.migration_path,
            *(item for item in (row.domesticated_from_id, row.sacred_to_node_id) if item is not None),
        ]
        refs = await node_refs(session, ids)
        return SpeciesCard(
            species_id=entity_id,
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
            yields=[YieldView(product=item.product, commodity=item.commodity, material=item.material, rate=item.rate) for item in yields],
            hosts=[HostView(disease=ref(refs, item.disease_entity_id), immune=item.immune) for item in hosts],
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
                    locked=item.locked,
                )
                for item in herds
            ],
            hunts=listed(refs, hunts),
            hunted_by=listed(refs, hunted_by),
            descendants=listed(refs, descendants),
            beasts=listed(refs, beasts),
            locked=row.locked,
        )


@router.get("/entities/{entity_id}/beast", response_model=BeastCard)
async def beast_card(entity_id: Id, services: ServicesDep) -> BeastCard:
    async with reader(services) as session:
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
        ids = [
            *(item for item in (row.species_entity_id, row.lair_place_id, row.bound_to_node_id) if item is not None),
            *(item.subject_node_id for item in wounds),
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
        return FoodWeb(
            region_id=region_id,
            nodes=[
                WebNode(species=refs[item.species_entity_id], abundance=item.abundance, diet=profile.diet, size_class=profile.size_class)
                for item, profile in rows
                if item.species_entity_id in refs
            ],
            links=[WebLink(hunter_id=hunter, prey_id=prey) for hunter, prey in bonds],
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
                locked=item.locked,
            )
            for item in rows
        ]
