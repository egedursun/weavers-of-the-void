from typing import Annotated

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.routers.wars import require_war, summaries
from aerona.api.schemas.military import (
    AimView,
    ArmyCard,
    ArmyWorksView,
    BattlePhaseView,
    BattleReportView,
    CaptiveCohortView,
    CasusBelliView,
    FrontView,
    MilitaryOverview,
    MovementView,
    OccupationView,
    SideWeariness,
    SiegeTracker,
    SpyNetworkView,
    StackView,
    UnitKindSpec,
    WarRoomView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.units import UNITS, weapon_of
from aerona.catalog.war_terms import CASUS_BELLI_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import (
    ArmyMovementRow,
    ArmyProfileRow,
    ArmyUnitRow,
    BattlePhaseRow,
    CampaignFrontRow,
    CaptiveCohortRow,
    CommanderTraitRow,
    OccupationRow,
    SpyNetworkRow,
    WarAimRow,
)
from aerona.db.tables.warfare import ArmyRow, BattleRow, CasusBelliRow, SiegeRow, WarSideRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.military import CommanderTrait, Stance
from aerona.domain.enums.war import WarSide
from aerona.engine.economy.route_dangers import PATROLS, patrolled_regions_of
from aerona.engine.military.battle import class_of
from aerona.engine.military.campaign import on_road
from aerona.engine.military.command import best_area, command_areas
from aerona.engine.military.engineering import RIVERS, earthworks_of, engineers, sappers, supply_limit
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import sides_of
from aerona.rules.registry import Rules

router = APIRouter(tags=["military"])
Id = Annotated[int, Path(ge=1)]
Refs = dict[int, NodeRef]


def ref(refs: Refs, node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def traits_of(session: AsyncSession, mortal_id: int | None) -> list[CommanderTrait]:
    if mortal_id is None:
        return []
    return sorted(await session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == mortal_id)))


async def army_cards(session: AsyncSession, rows: list[ArmyRow], rules: Rules) -> list[ArmyCard]:
    ids = [row.entity_id for row in rows]
    if not ids:
        return []
    armies = {entity.id: entity for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(ids)))}
    profiles = {profile.army_entity_id: profile for profile in await session.scalars(select(ArmyProfileRow).where(ArmyProfileRow.army_entity_id.in_(ids)))}
    stacks = list(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id.in_(ids)).order_by(ArmyUnitRow.id)))
    moving = select(ArmyMovementRow).where(ArmyMovementRow.army_entity_id.in_(ids))
    moves = list(await session.scalars(moving.order_by(ArmyMovementRow.epoch, ArmyMovementRow.season)))
    wanted: set[int] = {*ids, *(row.owner_entity_id for row in rows), *(row.commander_entity_id for row in rows if row.commander_entity_id)}
    for profile in profiles.values():
        wanted.update(item for item in (profile.region_entity_id, profile.target_entity_id, profile.blockade_entity_id, *profile.supply_line) if item)
    wanted.update(item for move in moves for item in (move.from_region_id, move.to_region_id) if item)
    refs = await node_refs(session, wanted)
    regions = {region.entity_id: region for region in await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id.in_(wanted)))}
    worlds = {region.world_id for region in regions.values()}
    seasons = list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id.in_(worlds))))
    patrolled = await patrolled_regions_of(session)
    cards: list[ArmyCard] = []
    for row in rows:
        blank = ArmyProfileRow(army_entity_id=row.entity_id, stance=Stance.MARCH, doctrine="shieldwall", supply_line=[], locked=[])
        profile = profiles.get(row.entity_id) or blank
        army = armies.get(row.entity_id)
        areas = await command_areas(session, row.commander_entity_id)
        cards.append(
            ArmyCard(
                army=ref(refs, row.entity_id),
                owner=ref(refs, row.owner_entity_id),
                commander=ref(refs, row.commander_entity_id),
                war_id=row.war_id,
                size=(stat(army, "size") or 0) if army is not None else 0,
                region=ref(refs, profile.region_entity_id),
                target=ref(refs, profile.target_entity_id),
                blockade=ref(refs, profile.blockade_entity_id),
                stance=profile.stance,
                doctrine=profile.doctrine,
                supply_days=profile.supply_days or 0,
                supply_line=[refs[item] for item in profile.supply_line if item in refs],
                cohesion=profile.cohesion or 0,
                war_chest=profile.war_chest or 0,
                disease=profile.disease or 0,
                loot=profile.loot or 0,
                entrenchment=profile.entrenchment or 0,
                forced_march=bool(profile.forced_march),
                baggage=profile.baggage or 0,
                contact_seasons=profile.contact_seasons or 0,
                locked=list(profile.locked or []),
                stacks=[stack_view(stack, rules) for stack in stacks if stack.army_entity_id == row.entity_id],
                movements=[movement_view(move, refs) for move in moves if move.army_entity_id == row.entity_id],
                commander_traits=await traits_of(session, row.commander_entity_id),
                command_areas=areas,
                best_area=best_area(areas),
                works=works_view(
                    rules,
                    regions.get(profile.region_entity_id or 0),
                    [season for season in seasons if army is not None and season.world_id == army.world_id],
                    [stack for stack in stacks if stack.army_entity_id == row.entity_id],
                    size=(stat(army, "size") or 0) if army is not None else 0,
                    patrolling=profile.region_entity_id in patrolled and profile.stance in PATROLS,
                ),
            )
        )
    return cards


def works_view(
    rules: Rules,
    region: RegionEnvironmentRow | None,
    seasons: list[WorldSeasonRow],
    stacks: list[ArmyUnitRow],
    *,
    size: int,
    patrolling: bool,
) -> ArmyWorksView:
    limits = [supply_limit(rules, region, season) for season in seasons] or [supply_limit(rules, region, None)]
    scars = region.scars if region is not None else {}
    return ArmyWorksView(
        supply_low=min(limits),
        supply_high=max(limits),
        eaten_out=size > min(limits),
        sappers=sappers(stacks),
        engineers=engineers(rules, stacks),
        earthworks=earthworks_of(region),
        military_road=scars.get(ScarKind.MILITARY_ROAD.value, 0),
        bridge_down=scars.get(ScarKind.BRIDGE_DOWN.value, 0),
        river=region is not None and region.river_class in RIVERS,
        road=on_road(region, rules),
        patrolling=patrolling,
    )


def stack_view(row: ArmyUnitRow, rules: Rules) -> StackView:
    spec = UNITS[row.kind]
    weapon = weapon_of(spec)
    return StackView(
        id=row.id,
        kind=row.kind,
        family=spec.family,
        label=spec.label,
        count=row.count,
        quality=row.quality,
        armour=row.armour,
        shield=row.shield,
        helmet=row.helmet,
        weapons=list(row.weapons),
        experience=row.experience,
        morale=row.morale,
        fatigue=row.fatigue,
        wounded=row.wounded,
        condition=row.condition,
        organisation=row.organisation,
        discipline=row.discipline,
        ammunition=row.ammunition,
        missing=row.missing,
        morale_state=row.morale_state,
        formation=row.formation,
        target_class=class_of(rules, spec, row),
        reach=weapon.reach,
        volleys=weapon.volleys,
        accuracy=weapon.accuracy,
        piercing=weapon.piercing,
        locked=list(row.locked or []),
    )


def movement_view(row: ArmyMovementRow, refs: Refs) -> MovementView:
    return MovementView(
        epoch=row.epoch,
        season=row.season,
        from_region=ref(refs, row.from_region_id),
        to_region=ref(refs, row.to_region_id),
        stance=row.stance,
        supply_days=row.supply_days,
        attrition=row.attrition,
        note=row.note,
    )


async def battle_reports(session: AsyncSession, rows: list[BattleRow]) -> list[BattleReportView]:
    phases = list(await session.scalars(select(BattlePhaseRow).where(BattlePhaseRow.battle_id.in_([row.id for row in rows])).order_by(BattlePhaseRow.position)))
    linked = [
        item
        for row in rows
        for item in (
            row.record_entity_id,
            row.place_entity_id,
            row.winner_entity_id,
            row.loser_entity_id,
            row.command_collapsed_entity_id,
            row.planned_entity_id,
            row.trap_entity_id,
            row.standard_entity_id,
        )
        if item
    ]
    refs = await node_refs(session, linked)
    return [
        BattleReportView(
            id=row.id,
            war_id=row.war_id,
            epoch=row.epoch,
            sequence=row.sequence,
            record=ref(refs, row.record_entity_id),
            place=ref(refs, row.place_entity_id),
            winner=ref(refs, row.winner_entity_id),
            loser=ref(refs, row.loser_entity_id),
            outcome=row.outcome,
            outcome_class=row.outcome_class,
            gap=row.gap,
            siege_id=row.siege_id,
            weather=row.weather,
            terrain=row.terrain,
            ground=row.ground,
            season_name=row.season_name,
            year=row.year,
            night=row.night,
            tactics_attacker=row.tactics_attacker,
            tactics_defender=row.tactics_defender,
            casualties_by_kind=dict(row.casualties_by_kind or {}),
            winner_losses=row.winner_losses,
            loser_losses=row.loser_losses,
            width=row.width,
            reserves_committed=row.reserves_committed,
            command_collapsed=ref(refs, row.command_collapsed_entity_id),
            planned_by=ref(refs, row.planned_entity_id),
            trap_by=ref(refs, row.trap_entity_id),
            feint=row.feint,
            salvaged=row.salvaged,
            standard_taken=ref(refs, row.standard_entity_id),
            phases=[
                BattlePhaseView(
                    position=phase.position,
                    phase=phase.phase,
                    attacker_losses=phase.attacker_losses,
                    defender_losses=phase.defender_losses,
                    summary=phase.summary,
                    details=dict(phase.details or {}),
                )
                for phase in phases
                if phase.battle_id == row.id
            ],
        )
        for row in rows
    ]


def siege_view(row: SiegeRow, refs: Refs) -> SiegeTracker:
    return SiegeTracker(
        id=row.id,
        besieged=ref(refs, row.besieged_entity_id),
        besieger=ref(refs, row.besieger_entity_id),
        status=row.status,
        started_epoch=row.started_epoch,
        ended_epoch=row.ended_epoch,
        rounds=row.rounds,
        walls_level=row.walls_level,
        breaches=row.breaches,
        supplies=row.supplies,
        water=row.water,
        disease_inside=row.disease_inside,
        disease_outside=row.disease_outside,
        works={key: int(value) for key, value in (row.works or {}).items()},
        sallies=row.sallies,
        starvation=row.starvation,
        last_action=row.last_action,
        last_defence=row.last_defence,
    )


def occupation_view(row: OccupationRow, refs: Refs) -> OccupationView:
    return OccupationView(
        region=ref(refs, row.region_entity_id),
        occupier=ref(refs, row.occupier_entity_id),
        war_id=row.war_id,
        since_epoch=row.since_epoch,
        control=row.control,
        resistance=row.resistance,
    )


def cohort_view(row: CaptiveCohortRow, refs: Refs) -> CaptiveCohortView:
    return CaptiveCohortView(
        id=row.id,
        captor=ref(refs, row.captor_entity_id),
        origin=ref(refs, row.origin_entity_id),
        war_id=row.war_id,
        count=row.count,
        social_class=row.social_class,
        fate=row.fate,
        since_epoch=row.since_epoch,
        settled_epoch=row.settled_epoch,
    )


def aim_view(row: WarAimRow, refs: Refs) -> AimView:
    return AimView(
        id=row.id,
        side=ref(refs, row.side_entity_id),
        kind=row.kind,
        target=ref(refs, row.target_entity_id),
        achieved=row.achieved,
        params=dict(row.params or {}),
        locked=list(row.locked or []),
    )


def front_view(row: CampaignFrontRow, refs: Refs) -> FrontView:
    return FrontView(
        first_region=ref(refs, row.first_region_id), second_region=ref(refs, row.second_region_id), since_epoch=row.since_epoch, last_epoch=row.last_epoch
    )


def network_view(row: SpyNetworkRow, refs: Refs) -> SpyNetworkView:
    return SpyNetworkView(
        id=row.id,
        owner=ref(refs, row.owner_entity_id),
        target=ref(refs, row.target_entity_id),
        agents=row.agents,
        depth=row.depth,
        exposure=row.exposure,
        cover=row.cover,
        spymaster=ref(refs, row.spymaster_entity_id),
        intel=row.intel,
        last_operation=row.last_operation,
        last_epoch=row.last_epoch,
        since_epoch=row.since_epoch,
    )


@router.get("/units/kinds", response_model=list[UnitKindSpec])
async def unit_kinds() -> list[UnitKindSpec]:
    return [
        UnitKindSpec(
            kind=spec.kind,
            family=spec.family,
            label=spec.label,
            melee=spec.melee,
            missile=spec.missile,
            defence=spec.defence,
            speed=spec.speed,
            mass=spec.mass,
            cost=spec.cost,
            upkeep=spec.upkeep,
            armour=spec.armour,
            shield=spec.shield,
            terror=spec.terror,
        )
        for spec in UNITS.values()
    ]


def casus_belli_view(row: CasusBelliRow, refs: dict[int, NodeRef]) -> CasusBelliView:
    return CasusBelliView(
        id=row.id,
        holder=ref(refs, row.holder_entity_id),
        target=ref(refs, row.target_entity_id),
        kind=row.kind,
        label=CASUS_BELLI_LABELS[row.kind],
        justification=row.justification,
        since_epoch=row.since_epoch,
        expires_epoch=row.expires_epoch,
        used_war_id=row.used_war_id,
        locked=list(row.locked or []),
    )


@router.get("/wars/{war_id}/room", response_model=WarRoomView)
async def war_room(services: ServicesDep, war_id: Id) -> WarRoomView:
    async with reader(services) as session:
        war = await require_war(session, war_id)
        sides = list(await session.scalars(select(WarSideRow).where(WarSideRow.war_id == war_id).order_by(WarSideRow.joined_epoch, WarSideRow.entity_id)))
        aims = list(await session.scalars(select(WarAimRow).where(WarAimRow.war_id == war_id).order_by(WarAimRow.id)))
        armies = list(await session.scalars(select(ArmyRow).where(ArmyRow.war_id == war_id).order_by(ArmyRow.entity_id)))
        sieges = list(await session.scalars(select(SiegeRow).where(SiegeRow.war_id == war_id).order_by(SiegeRow.id)))
        fronts = list(await session.scalars(select(CampaignFrontRow).where(CampaignFrontRow.war_id == war_id).order_by(CampaignFrontRow.id)))
        occupations = list(await session.scalars(select(OccupationRow).where(OccupationRow.war_id == war_id).order_by(OccupationRow.region_entity_id)))
        captives = list(await session.scalars(select(CaptiveCohortRow).where(CaptiveCohortRow.war_id == war_id).order_by(CaptiveCohortRow.id)))
        battles = list(await session.scalars(select(BattleRow).where(BattleRow.war_id == war_id).order_by(BattleRow.epoch, BattleRow.sequence)))
        refs = await node_refs(
            session,
            [
                *(row.entity_id for row in sides),
                *(item for row in aims for item in (row.side_entity_id, row.target_entity_id) if item),
                *(item for row in sieges for item in (row.besieged_entity_id, row.besieger_entity_id)),
                *(item for row in fronts for item in (row.first_region_id, row.second_region_id)),
                *(item for row in occupations for item in (row.region_entity_id, row.occupier_entity_id)),
                *(item for row in captives for item in (row.captor_entity_id, row.origin_entity_id) if item),
            ],
        )
        cause = await session.get(CasusBelliRow, war.casus_belli_id) if war.casus_belli_id is not None else None
        cause_refs = await node_refs(session, [cause.holder_entity_id, cause.target_entity_id] if cause is not None else [])
        primary = await sides_of(session, war)
        return WarRoomView(
            war=(await summaries(session, [war]))[0],
            weariness=[
                SideWeariness(
                    entity=ref(refs, row.entity_id),
                    side=row.side,
                    weariness=row.weariness,
                    support=row.support,
                    left_epoch=row.left_epoch,
                    primary=primary is not None and row.entity_id in primary,
                    locked=list(row.locked or []),
                    budget=services.rules.current.war_conduct.base_budget
                    + max(0, war.score if row.side is WarSide.ATTACKER else -war.score) * services.rules.current.war_conduct.score_unit,
                )
                for row in sides
            ],
            justified=war.justified,
            casus_belli=casus_belli_view(cause, cause_refs) if cause is not None else None,
            aims=[aim_view(row, refs) for row in aims],
            armies=await army_cards(session, armies, services.rules.current),
            sieges=[siege_view(row, refs) for row in sieges],
            fronts=[front_view(row, refs) for row in fronts],
            occupations=[occupation_view(row, refs) for row in occupations],
            captives=[cohort_view(row, refs) for row in captives],
            battles=await battle_reports(session, battles),
        )


@router.get("/entities/{entity_id}/army", response_model=ArmyCard)
async def army_card(services: ServicesDep, entity_id: Id) -> ArmyCard:
    async with reader(services) as session:
        row = await session.get(ArmyRow, entity_id)
        if row is None:
            raise NotFoundError("No such army.")
        return (await army_cards(session, [row], services.rules.current))[0]


@router.get("/entities/{entity_id}/military", response_model=MilitaryOverview)
async def military_overview(services: ServicesDep, entity_id: Id) -> MilitaryOverview:
    async with reader(services) as session:
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        standing = select(ArmyRow).where(ArmyRow.owner_entity_id == entity_id, ArmyRow.disbanded_epoch.is_(None))
        armies = list(await session.scalars(standing.order_by(ArmyRow.entity_id)))
        involved = or_(CaptiveCohortRow.captor_entity_id == entity_id, CaptiveCohortRow.origin_entity_id == entity_id)
        cohorts = list(await session.scalars(select(CaptiveCohortRow).where(involved).order_by(CaptiveCohortRow.id)))
        spying = or_(SpyNetworkRow.owner_entity_id == entity_id, SpyNetworkRow.target_entity_id == entity_id)
        networks = list(await session.scalars(select(SpyNetworkRow).where(spying).order_by(SpyNetworkRow.id)))
        occupations = list(await session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id)))
        home = entity.location_id if entity.entity_type is not EntityType.REGION else entity.id
        mine = [row for row in occupations if row.occupier_entity_id == entity_id]
        suffered = [row for row in occupations if row.region_entity_id in {entity_id, home} and row.occupier_entity_id != entity_id]
        refs = await node_refs(
            session,
            [
                *(item for row in cohorts for item in (row.captor_entity_id, row.origin_entity_id) if item),
                *(item for row in networks for item in (row.owner_entity_id, row.target_entity_id, row.spymaster_entity_id) if item),
                *(item for row in [*mine, *suffered] for item in (row.region_entity_id, row.occupier_entity_id)),
            ],
        )
        return MilitaryOverview(
            armies=await army_cards(session, armies, services.rules.current),
            captives_held=[cohort_view(row, refs) for row in cohorts if row.captor_entity_id == entity_id],
            captives_lost=[cohort_view(row, refs) for row in cohorts if row.origin_entity_id == entity_id],
            networks=[network_view(row, refs) for row in networks if row.owner_entity_id == entity_id],
            watched_by=[network_view(row, refs) for row in networks if row.target_entity_id == entity_id],
            occupying=[occupation_view(row, refs) for row in mine],
            occupied=[occupation_view(row, refs) for row in suffered],
            commander_traits=await traits_of(session, entity_id if entity.entity_type is EntityType.MORTAL else None),
        )
