from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict

from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.depth_society import (
    AdminView,
    ArmyOption,
    BiologyView,
    ClassMood,
    CultureView,
    CureView,
    DefenceView,
    DemographyView,
    DiseaseView,
    DistrictDesignView,
    DistrictEffectsView,
    DistrictView,
    EndemicView,
    ForeignShare,
    HistoryPoint,
    ImmunityView,
    InfrastructureView,
    KinEffectsView,
    LabourFlowView,
    LabourView,
    LinkedRecord,
    MartialRecordView,
    NeighbourCulture,
    OutbreakView,
    PopulationCohortView,
    SettlementPlanView,
    SocietyPressureView,
    StorageView,
    StrainView,
    TreasuryLine,
    ValuePoint,
    WorkFactor,
)
from aerona.api.views.disease import afflictions, community_holds, disease_incidents, disease_sick, host_views, named_mortals, unseen_pct
from aerona.catalog.peoples import KIN
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.disease import DiseaseCureRow, DiseaseProfileRow, EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import (
    DESIGN_PARAMETERS,
    DistrictRow,
    SettlementHistoryRow,
    SettlementInfrastructureRow,
    SettlementProfileRow,
    SettlementTreasuryRow,
)
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.demography import Job, MartialStyle
from aerona.domain.enums.disease import DiseaseTarget, OutbreakStatus
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.cosmos.lifeforms import habitability
from aerona.engine.demography.biology import (
    battle_edge,
    edible,
    food_need,
    footprint,
    hunger_level,
    immunity_factor,
    job_factors,
    mount_fit,
    natures,
    record_of,
    scaled,
)
from aerona.engine.demography.labour import AGE_WORK, condition_work, jobs_for, mobilisation
from aerona.engine.demography.mobility import inequality
from aerona.engine.disease.harm import community_targets
from aerona.engine.mind.book import pressures_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.society import supply_index
from aerona.engine.primitives.stats import stat
from aerona.engine.settlement.book import Town
from aerona.engine.settlement.districts import base_parameters, designs_for
from aerona.engine.settlement.life import housing_of, slots_of
from aerona.engine.settlement.readout import plan_readout
from aerona.rules.registry import Rules

router = APIRouter(tags=["depth-society"])


async def rules_of(session: AsyncSession) -> Rules:
    cosmos = await CosmosRepository(session).require_cosmos()
    return rules_from_snapshot(cosmos.rules_snapshot)


async def names_of(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {entity_id: name for entity_id, name in await session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.id.in_(list(ids))))}


async def entity_of(session: AsyncSession, entity_id: int, types: frozenset[EntityType] | None = None) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or (types is not None and entity.entity_type not in types):
        raise NotFoundError("No such record.")
    return entity


def values_list(values: Mapping[ValueAxis, int]) -> list[ValuePoint]:
    return [ValuePoint(axis=axis, value=value) for axis, value in sorted(values.items(), key=lambda item: item[0].value)]


async def neighbours_of(session: AsyncSession, people: EntityRow) -> list[NeighbourCulture]:
    atlas = await RegionAtlas.load(session)
    home = atlas.top_region(people.id)
    if home is None:
        return []
    near = {home, *atlas.neighbour_regions(home)}
    found = await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON))
    views = []
    for other in found:
        if other.id == people.id or atlas.top_region(other.id) not in near:
            continue
        values = await culture_of(session, other.id)
        if values:
            views.append(NeighbourCulture(entity_id=other.id, name=other.name, values=values_list(values)))
    return views


def labour_flows(rules: Rules, rows: list[CohortRow], targets: frozenset[DiseaseTarget] = frozenset()) -> list[LabourFlowView]:
    found: dict[tuple[SocialClass, Job], float] = defaultdict(float)
    for row in rows:
        hands = row.count * AGE_WORK[row.age_band]
        for job, share in jobs_for(rules, row.social_class).items():
            found[(row.social_class, job)] += hands * condition_work(rules, row.condition, job, targets) * share
    return [LabourFlowView(social_class=key[0], job=key[1], workers=round(value)) for key, value in sorted(found.items()) if value >= 1]


@router.get("/entities/{entity_id}/demography", response_model=DemographyView)
async def demography(services: ServicesDep, entity_id: int = Path(ge=1)) -> DemographyView:
    async with reader(services) as session:
        rules = await rules_of(session)
        entity = await entity_of(session, entity_id)
        people = await people_of(session, entity)
        cohorts = [
            PopulationCohortView(age_band=row.age_band, sex=row.sex, social_class=row.social_class, condition=row.condition, count=row.count)
            for row in await session.scalars(select(CohortRow).where(CohortRow.community_entity_id == entity.id))
            if row.count > 0
        ]
        labour = [
            LabourView(job=row.job, workers=row.workers, output_pct=row.output_pct)
            for row in await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == entity.id).order_by(LabourRow.job))
        ]
        society = await session.get(CommunitySocietyRow, entity.id)
        flows = labour_flows(
            rules, list(await session.scalars(select(CohortRow).where(CohortRow.community_entity_id == entity.id))), await community_targets(session, entity.id)
        )
        pressures = [SocietyPressureView(kind=kind, value=value) for kind, value in sorted((await pressures_of(session, entity.id)).items())]
        classes = (
            [ClassMood(social_class=item, share=society.share(item), satisfaction=society.satisfaction(item)) for item in SocialClass]
            if society is not None
            else []
        )
        biology = await session.get(PeopleBiologyRow, people.id) if people is not None else None
        culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
        values = await culture_of(session, people.id) if people is not None else {}
        return DemographyView(
            entity_id=entity.id,
            people_id=people.id if people is not None else None,
            cohorts=cohorts,
            labour=labour,
            flows=flows,
            pressures=pressures,
            classes=classes,
            biology=await biology_view(session, rules, entity, biology, culture) if biology is not None else None,
            culture=await culture_view(session, culture) if culture is not None else None,
            values=values_list(values),
            neighbours=await neighbours_of(session, people) if people is not None else [],
            inequality=inequality(society) if society is not None else 0,
            mobilisation_pct=round(await mobilisation(session, rules, entity, harvest_share=0.0) * PERCENT),
            afflictions=await afflictions(session, entity.id),
            named=await named_mortals(session, entity.id),
            held=await community_holds(session, entity.id),
        )


async def linked_record(session: AsyncSession, entity_id: int | None) -> LinkedRecord | None:
    found = await session.get(EntityRow, entity_id) if entity_id is not None else None
    return LinkedRecord(id=found.id, name=found.name) if found is not None else None


async def biology_view(session: AsyncSession, rules: Rules, community: EntityRow, biology: PeopleBiologyRow, culture: PeopleCultureRow | None) -> BiologyView:
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(community.id)
    ground = await session.get(RegionEnvironmentRow, region) if region is not None else None
    magic = (await known_levels(session, [community.id])).get(community.id, {}).get(KnowledgeBranch.MAGIC, 0)
    hunger = hunger_level(rules, biology, ground, await supply_index(session, community.id, Commodity.FOOD), magic)
    neutral = battle_edge(rules, biology, None, terrain=None, weather=None, night=False, river=False, defending=False)
    fleet = scaled(KIN[biology.body_plan].naval_pct / PERCENT, rules.biology.naval_pct)
    immunities = [found for found in [await linked_record(session, item) for item in biology.immunities] if found is not None]
    return BiologyView(
        maturity_years=biology.maturity_years,
        adult_years=biology.adult_years,
        elder_years=biology.elder_years,
        fertility_pct=biology.fertility_pct,
        acclimatised=biology.acclimatised,
        staple=biology.staple,
        traits=sorted(natures(biology), key=lambda item: item.value),
        immunities=immunities,
        body_plan=biology.body_plan,
        size_class=biology.size_class,
        diet=biology.diet,
        edible=sorted(edible(biology.diet), key=lambda item: item.value),
        biochemistry=biology.biochemistry,
        air=biology.air,
        gravity_low=round(biology.gravity_low * PERCENT),
        gravity_high=round(biology.gravity_high * PERCENT),
        habitability=await habitability(session, rules, biology, community.world_id),
        effects=KinEffectsView(
            food_pct=round(food_need(rules, biology) * PERCENT),
            room_pct=round(footprint(rules, biology) * PERCENT),
            strength_pct=round(neutral * PERCENT),
            disease_pct=round(immunity_factor(rules, biology, culture, 0) * PERCENT),
            fleet_pct=round(fleet * PERCENT),
            mount=mount_fit(biology),
            hunger_pct=round(hunger * PERCENT),
            work=[WorkFactor(job=job, pct=round(value * PERCENT)) for job, value in sorted(job_factors(rules, biology).items())],
        ),
        locked=list(biology.locked),
    )


async def culture_view(session: AsyncSession, culture: PeopleCultureRow) -> CultureView:
    record = [
        MartialRecordView(style=MartialStyle(style), wins=int(entry[0]), losses=int(entry[1]) if len(entry) > 1 else 0)
        for style, entry in sorted((culture.martial_record or {}).items())
        if style in MartialStyle._value2member_map_ and entry
    ]
    wins, losses = record_of(culture, culture.martial_style.value)
    return CultureView(
        cohesion=culture.cohesion,
        literacy=culture.literacy,
        urbanisation=culture.urbanisation,
        aesthetic=culture.aesthetic,
        martial_style=culture.martial_style,
        marriage=culture.marriage,
        endogamous=culture.endogamous,
        inheritance=culture.inheritance,
        slavery_lawful=culture.slavery_lawful,
        staples=[CommodityKind(item) for item in culture.staples if item in CommodityKind._value2member_map_],
        liturgical_language=await linked_record(session, culture.liturgical_language_id),
        trade_language=await linked_record(session, culture.trade_language_id),
        funeral_rite=culture.funeral_rite,
        funeral_tradition=await linked_record(session, culture.funeral_rite_id),
        martial_record=record,
        martial_net=wins - losses,
        locked=list(culture.locked),
    )


def outbreak_views(rows: list[OutbreakRow], names: dict[int, str], sources: dict[int, int], unseen: Mapping[int, int] | None = None) -> list[OutbreakView]:
    return [
        OutbreakView(
            id=row.id,
            disease_id=row.disease_entity_id,
            disease=names.get(row.disease_entity_id, ""),
            region_id=row.region_entity_id,
            region=names.get(row.region_entity_id, ""),
            source_region_id=sources.get(row.source_outbreak_id) if row.source_outbreak_id is not None else None,
            path=row.path,
            status=row.status,
            severity=row.severity,
            infected=row.infected,
            dead=row.dead,
            started_epoch=row.started_epoch,
            ended_epoch=row.ended_epoch,
            quarantined=row.quarantined,
            season_factor=row.season_factor,
            event_id=row.event_entity_id,
            locked=list(row.locked or []),
            unseen_pct=(unseen or {}).get(row.id, 0),
        )
        for row in rows
    ]


async def unseen_of(session: AsyncSession, rules: Rules, rows: list[OutbreakRow]) -> dict[int, int]:
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    profiles = {
        row.disease_entity_id: row
        for row in await session.scalars(select(DiseaseProfileRow).where(DiseaseProfileRow.disease_entity_id.in_({item.disease_entity_id for item in rows})))
    }
    return {row.id: unseen_pct(rules, profiles.get(row.disease_entity_id), row, epoch) for row in rows if row.status is not OutbreakStatus.ENDED}


def endemic_views(rows: list[EndemicDiseaseRow], names: dict[int, str]) -> list[EndemicView]:
    return [
        EndemicView(
            region_id=row.region_entity_id,
            region=names.get(row.region_entity_id, ""),
            load=row.load,
            since_epoch=row.since_epoch,
            locked=bool(row.locked),
            disease_id=row.disease_entity_id,
            disease=names.get(row.disease_entity_id, ""),
        )
        for row in rows
    ]


async def source_regions(session: AsyncSession, rows: list[OutbreakRow]) -> dict[int, int]:
    wanted = {row.source_outbreak_id for row in rows if row.source_outbreak_id is not None}
    if not wanted:
        return {}
    return {row.id: row.region_entity_id for row in await session.scalars(select(OutbreakRow).where(OutbreakRow.id.in_(list(wanted))))}


@router.get("/entities/{entity_id}/disease", response_model=DiseaseView)
async def disease(services: ServicesDep, entity_id: int = Path(ge=1)) -> DiseaseView:
    async with reader(services) as session:
        entity = await entity_of(session, entity_id, frozenset({EntityType.DISEASE}))
        profile = await session.get(DiseaseProfileRow, entity.id)
        if profile is None:
            raise NotFoundError("This disease has not been studied yet; it gains its profile in the next epoch.")
        strains = list(await session.scalars(select(DiseaseProfileRow).where(DiseaseProfileRow.parent_disease_id == entity.id)))
        outbreaks = list(
            await session.scalars(select(OutbreakRow).where(OutbreakRow.disease_entity_id == entity.id).order_by(OutbreakRow.started_epoch, OutbreakRow.id))
        )
        endemic = list(await session.scalars(select(EndemicDiseaseRow).where(EndemicDiseaseRow.disease_entity_id == entity.id)))
        cures = list(await session.scalars(select(DiseaseCureRow).where(DiseaseCureRow.disease_entity_id == entity.id)))
        immunities = list(await session.scalars(select(ImmunityRow).where(ImmunityRow.disease_entity_id == entity.id)))
        ids = {
            entity.id,
            *(row.disease_entity_id for row in strains),
            *(row.region_entity_id for row in outbreaks),
            *(row.region_entity_id for row in endemic),
            *(row.disease_entity_id for row in endemic),
            *(row.community_entity_id for row in cures),
            *(row.community_entity_id for row in immunities),
        }
        names = await names_of(session, ids)
        children = {row.id: row for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_([row.disease_entity_id for row in strains])))}
        rules = await rules_of(session)
        incidents = await disease_incidents(session, entity.id, profile.origin_incident_id)
        return DiseaseView(
            entity_id=entity.id,
            name=entity.name,
            vector=profile.vector,
            virulence=profile.virulence,
            lethality=profile.lethality,
            chronic_rate=profile.chronic_rate,
            incubation=profile.incubation,
            target_functions=[DiseaseTarget(item) for item in profile.target_functions],
            climate_affinity=profile.climate_affinity,
            host_species_id=profile.host_species_id,
            immunity_epochs=profile.immunity_epochs,
            mutation_rate=profile.mutation_rate,
            stigma=profile.stigma,
            cure_level=profile.cure_level,
            generation=profile.generation,
            parent_id=profile.parent_disease_id,
            origin_region_id=profile.origin_region_id,
            emerged_epoch=profile.emerged_epoch,
            locked=list(profile.locked),
            origin_incident_id=profile.origin_incident_id,
            origin=next((item for item in incidents if item.id == profile.origin_incident_id), None),
            incidents=incidents,
            hosts=await host_views(session, profile),
            unseen_pct=unseen_pct(rules, profile, None, 0),
            sick=await disease_sick(session, entity.id),
            strains=[
                StrainView(
                    id=row.disease_entity_id,
                    name=names.get(row.disease_entity_id, ""),
                    generation=row.generation,
                    virulence=row.virulence,
                    lethality=row.lethality,
                )
                for row in strains
                if row.disease_entity_id in children
            ],
            outbreaks=outbreak_views(outbreaks, names, await source_regions(session, outbreaks), await unseen_of(session, rules, outbreaks)),
            endemic=endemic_views(endemic, names),
            cures=[
                CureView(community_id=row.community_entity_id, community=names.get(row.community_entity_id, ""), source=row.source, since_epoch=row.since_epoch)
                for row in cures
            ],
            immunities=[
                ImmunityView(
                    community_id=row.community_entity_id,
                    community=names.get(row.community_entity_id, ""),
                    age_band=row.age_band,
                    immune_pct=row.immune_pct,
                    locked=bool(row.locked),
                )
                for row in immunities
            ],
        )


@router.get("/entities/{entity_id}/settlement-plan", response_model=SettlementPlanView)
async def settlement_plan(services: ServicesDep, entity_id: int = Path(ge=1)) -> SettlementPlanView:
    async with reader(services) as session:
        rules = await rules_of(session)
        entity = await entity_of(session, entity_id, frozenset({EntityType.SETTLEMENT}))
        profile = await session.get(SettlementProfileRow, entity.id)
        infrastructure = await session.get(SettlementInfrastructureRow, entity.id)
        if profile is None or infrastructure is None:
            raise NotFoundError("This settlement is surveyed at the next epoch.")
        districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == entity.id).order_by(DistrictRow.id)))
        town = Town(entity, profile, infrastructure, districts, designs=await designs_for(session, districts))
        readout = await plan_readout(session, rules, town)
        armies = [
            ArmyOption(id=army.id, name=army.name, size=stat(army, "size") or 0)
            for army in await session.scalars(
                select(EntityRow)
                .join(ArmyRow, ArmyRow.entity_id == EntityRow.id)
                .where(ArmyRow.owner_entity_id == entity.id, ArmyRow.disbanded_epoch.is_(None))
                .order_by(EntityRow.id)
            )
        ]
        ledger = list(
            await session.scalars(
                select(SettlementTreasuryRow)
                .where(SettlementTreasuryRow.settlement_entity_id == entity.id)
                .order_by(SettlementTreasuryRow.epoch, SettlementTreasuryRow.id)
            )
        )
        history = list(
            await session.scalars(
                select(SettlementHistoryRow).where(SettlementHistoryRow.settlement_entity_id == entity.id).order_by(SettlementHistoryRow.epoch)
            )
        )
        names = await names_of(session, {int(key) for key in profile.foreigners})
        return SettlementPlanView(
            entity_id=entity.id,
            world_id=entity.world_id,
            size_tier=profile.size_tier,
            treasury=profile.treasury,
            tax_rate=profile.tax_rate,
            public_order=profile.public_order,
            crime=profile.crime,
            unrest=profile.unrest,
            sanitation=profile.sanitation,
            fire_risk=profile.fire_risk,
            wealth=stat(entity, "wealth") or 0,
            prestige=profile.prestige,
            militia=profile.militia,
            garrison_id=profile.garrison_entity_id,
            free_city=profile.free_city,
            charter_id=profile.charter_entity_id,
            siege_supplies=profile.siege_supplies,
            siege_water=profile.siege_water,
            siege_disease=profile.siege_disease,
            investment_pool=profile.investment_pool,
            construction_capacity=profile.construction_capacity,
            hauling_capacity=profile.hauling_capacity,
            rationing=profile.rationing,
            admin_capacity=profile.admin_capacity,
            admin=AdminView(**asdict(readout.admin), total=readout.admin.total),
            food_storage=StorageView(**asdict(readout.food), total=readout.food.total),
            goods_storage=StorageView(**asdict(readout.goods), total=readout.goods.total),
            defences=DefenceView(**asdict(readout.defences)),
            district_effects=DistrictEffectsView(**asdict(readout.effects)),
            prestige_pull_pct=readout.prestige_pull_pct,
            prestige_investment_pct=readout.prestige_investment_pct,
            armies=armies,
            kind_defaults={kind: base_parameters(rules, kind) for kind in DistrictKind},
            designs=[
                DistrictDesignView(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    base_kind=row.base_kind,
                    parameters={key: getattr(row, key) for key in DESIGN_PARAMETERS},
                    defaults=base_parameters(rules, row.base_kind),
                    created_epoch=row.created_epoch,
                )
                for row in readout.designs
            ],
            district_slots=slots_of(rules, town),
            housing=housing_of(rules, town),
            locked=list(profile.locked),
            foreigners=[ForeignShare(people_id=int(key), name=names.get(int(key), ""), share=value) for key, value in sorted(profile.foreigners.items())],
            infrastructure=InfrastructureView(
                walls_level=infrastructure.walls_level,
                walls_material=infrastructure.walls_material,
                walls_condition=infrastructure.walls_condition,
                gates=infrastructure.gates,
                roads=infrastructure.roads,
                water=infrastructure.water,
                sewers=infrastructure.sewers,
                granary_capacity=infrastructure.granary_capacity,
                warehouse_capacity=infrastructure.warehouse_capacity,
                harbour_capacity=infrastructure.harbour_capacity,
                towers=infrastructure.towers,
                bridges=infrastructure.bridges,
                irrigation=infrastructure.irrigation,
                locked=list(infrastructure.locked),
            ),
            districts=[
                DistrictView(
                    id=row.id,
                    kind=row.kind,
                    level=row.level,
                    condition=row.condition,
                    material=row.material,
                    built_epoch=row.built_epoch,
                    design_id=row.design_id,
                    locked=list(row.locked or []),
                    effects=readout.district_effects.get(row.id, {}),
                )
                for row in districts
            ],
            treasury_ledger=[TreasuryLine(epoch=row.epoch, entry=row.entry, amount=row.amount, balance=row.balance, note=row.note) for row in ledger],
            history=[
                HistoryPoint(
                    epoch=row.epoch,
                    size_tier=row.size_tier,
                    public_order=row.public_order,
                    crime=row.crime,
                    unrest=row.unrest,
                    sanitation=row.sanitation,
                    wealth=row.wealth,
                    treasury=row.treasury,
                    population=row.population,
                )
                for row in history
            ],
        )
