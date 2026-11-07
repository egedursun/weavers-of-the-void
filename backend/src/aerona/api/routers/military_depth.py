from typing import Annotated

from fastapi import APIRouter, Path, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.military_depth import (
    BattleDepthView,
    BattleStackView,
    CasualtyView,
    FeudView,
    HullSpecView,
    PeaceTermView,
    RecordColumnView,
    RecordKindView,
    RecordRowView,
    RecordTableView,
    VesselView,
)
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.vessels import HULLS, HullSpec
from aerona.core.errors import NotFoundError
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import BattleCasualtyRow, BattleStackRow, FeudRow, PeaceTermRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.military import VesselArmament
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.military import records
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["military"])
Id = Annotated[int, Path(ge=1)]
GRIEF = (MemoryKind.KILLED_KIN, MemoryKind.MAIMED_ME, MemoryKind.HUMILIATED_ME)


def hull_view(spec: HullSpec) -> HullSpecView:
    return HullSpecView(
        hull=spec.hull,
        label=spec.label,
        speed=spec.speed,
        range=spec.range,
        cargo=spec.cargo,
        crew=spec.crew,
        seaworthiness=spec.seaworthiness,
        slots=spec.slots,
        armament=list(spec.armament),
        sky=spec.sky,
        living=spec.living,
        strangeness=spec.strangeness,
    )


@router.get("/military/kinds", response_model=list[RecordKindView])
async def record_kinds() -> list[RecordKindView]:
    return [
        RecordKindView(kind=kind.key, label=kind.label, creatable=kind.creatable, deletable=kind.deletable, scope=kind.scope, required=list(kind.required))
        for kind in records.KINDS.values()
    ]


@router.get("/military/records/{kind}", response_model=RecordTableView)
async def record_table(services: ServicesDep, kind: str, scope_id: Annotated[int | None, Query(ge=1)] = None) -> RecordTableView:
    found = records.kind_of(kind)
    async with reader(services) as session:
        rows = await records.rows_of(session, found, scope_id)
        values = [records.as_dict(found, row) for row in rows]
        wanted = {value for item in values for key, value in item.items() if linked(key) and isinstance(value, int)}
        refs = await node_refs(session, wanted)
        return RecordTableView(
            kind=found.key,
            label=found.label,
            creatable=found.creatable,
            deletable=found.deletable,
            scope=found.scope,
            columns=[
                RecordColumnView(name=c.name, kind=c.kind, options=list(c.options), nullable=c.nullable, required=c.required) for c in records.columns(found)
            ],
            rows=[
                RecordRowView(
                    id=int(item["id"]),
                    values=item,
                    locked=list(getattr(row, "locked", None) or []),
                    refs={key: refs[value] for key, value in item.items() if linked(key) and isinstance(value, int) and value in refs},
                )
                for row, item in zip(rows, values, strict=True)
            ],
        )


def linked(key: str) -> bool:
    return key.endswith("_entity_id") or key in {"relief_army_id", "battle_region_id"}


@router.get("/battles/{battle_id}/depth", response_model=BattleDepthView)
async def battle_depth(services: ServicesDep, battle_id: Id) -> BattleDepthView:
    async with reader(services) as session:
        battle = await session.get(BattleRow, battle_id)
        if battle is None:
            raise NotFoundError("No such battle.")
        stacks = list(await session.scalars(select(BattleStackRow).where(BattleStackRow.battle_id == battle_id).order_by(BattleStackRow.id)))
        fallen = list(await session.scalars(select(BattleCasualtyRow).where(BattleCasualtyRow.battle_id == battle_id).order_by(BattleCasualtyRow.id)))
        wanted = {item for row in stacks for item in (row.side_entity_id, row.army_entity_id) if item}
        wanted |= {item for row in fallen for item in (row.mortal_entity_id, row.side_entity_id) if item}
        refs = await node_refs(session, wanted)
        return BattleDepthView(
            battle_id=battle_id,
            stacks=[
                BattleStackView(
                    side=refs.get(row.side_entity_id),
                    army=refs.get(row.army_entity_id) if row.army_entity_id else None,
                    kind=row.kind,
                    label=row.label,
                    start=row.start,
                    lost=row.lost,
                    wounded=row.wounded,
                    routed=row.routed,
                    killed=row.killed,
                    walking=row.walking,
                    stretcher=row.stretcher,
                    captured=row.captured,
                    missing=row.missing,
                    deserted=row.deserted,
                    reserve=row.reserve,
                    organisation=row.organisation,
                    ammunition_spent=row.ammunition_spent,
                    formation=row.formation,
                    morale_state=row.morale_state,
                    target_class=row.target_class,
                )
                for row in stacks
            ],
            casualties=[
                CasualtyView(
                    mortal=refs.get(row.mortal_entity_id),
                    side=refs.get(row.side_entity_id) if row.side_entity_id else None,
                    fate=row.fate,
                    harm=row.harm,
                    note=row.note,
                )
                for row in fallen
            ],
            tactic_factors=dict(battle.tactic_factors or {}),
            morale=dict(battle.morale or {}),
            magic=dict(battle.magic or {}),
        )


@router.get("/vessels/hulls", response_model=list[HullSpecView])
async def hulls() -> list[HullSpecView]:
    return [hull_view(spec) for spec in HULLS.values()]


@router.get("/entities/{entity_id}/vessel", response_model=VesselView)
async def vessel_card(services: ServicesDep, entity_id: Id) -> VesselView:
    async with reader(services) as session:
        row = await session.get(VesselProfileRow, entity_id)
        if row is None:
            raise NotFoundError("This is not a vessel.")
        owners = await active_bonds(session, [BondKind.OWNS], targets=[entity_id])
        owner_id = owners[0].source_node_id if owners else None
        linked_ids = {entity_id, owner_id, row.captain_entity_id, row.home_port_entity_id, row.region_entity_id, row.fleet_army_entity_id, row.legend_entity_id}
        refs = await node_refs(session, {item for item in linked_ids if item})
        vessel = refs.get(entity_id)
        body = await session.get(EntityRow, entity_id)
        strangeness = (stat(body, "strangeness") or 0) if body is not None else 0
        return VesselView(
            vessel=vessel,
            owner=refs.get(owner_id) if owner_id else None,
            captain=refs.get(row.captain_entity_id) if row.captain_entity_id else None,
            home_port=refs.get(row.home_port_entity_id) if row.home_port_entity_id else None,
            region=refs.get(row.region_entity_id) if row.region_entity_id else None,
            fleet=refs.get(row.fleet_army_entity_id) if row.fleet_army_entity_id else None,
            legend=refs.get(row.legend_entity_id) if row.legend_entity_id else None,
            hull=hull_view(HULLS[row.hull_class]),
            hull_material=row.hull_material,
            fabric_material=row.fabric_material,
            condition=row.condition,
            armament=[VesselArmament(item) for item in row.armament if item in VesselArmament._value2member_map_],
            seaworthiness=row.seaworthiness,
            cargo_capacity=row.cargo_capacity,
            crew=row.crew,
            seamanship=row.seamanship,
            renown=row.renown,
            strangeness=strangeness,
            status=row.status,
            voyages=row.voyages,
            locked=list(row.locked or []),
        )


async def grief_between(session: AsyncSession, first: int, second: int) -> int:
    found = await session.scalar(
        select(func.coalesce(func.sum(MemoryRow.magnitude), 0)).where(
            or_(
                (MemoryRow.holder_node_id == first) & (MemoryRow.subject_node_id == second),
                (MemoryRow.holder_node_id == second) & (MemoryRow.subject_node_id == first),
            ),
            MemoryRow.kind.in_(GRIEF),
            MemoryRow.magnitude < 0,
        )
    )
    return -int(found or 0)


@router.get("/feuds", response_model=list[FeudView])
async def feuds(services: ServicesDep, entity_id: Annotated[int | None, Query(ge=1)] = None) -> list[FeudView]:
    async with reader(services) as session:
        statement = select(FeudRow)
        if entity_id is not None:
            statement = statement.where(or_(FeudRow.first_entity_id == entity_id, FeudRow.second_entity_id == entity_id))
        rows = list(await session.scalars(statement.order_by(FeudRow.status, FeudRow.intensity.desc(), FeudRow.id)))
        refs = await node_refs(session, {item for row in rows for item in (row.first_entity_id, row.second_entity_id)})
        return [
            FeudView(
                id=row.id,
                first=refs.get(row.first_entity_id),
                second=refs.get(row.second_entity_id),
                party=row.party,
                intensity=row.intensity,
                grievance=row.grievance,
                generations=row.generations,
                status=row.status,
                cause=row.cause,
                since_epoch=row.since_epoch,
                last_epoch=row.last_epoch,
                last_action=row.last_action,
                ended_epoch=row.ended_epoch,
                grief=await grief_between(session, row.first_entity_id, row.second_entity_id),
                locked=list(row.locked or []),
            )
            for row in rows
        ]


@router.get("/wars/{war_id}/terms", response_model=list[PeaceTermView])
async def peace_terms(services: ServicesDep, war_id: Id) -> list[PeaceTermView]:
    async with reader(services) as session:
        rows = list(await session.scalars(select(PeaceTermRow).where(PeaceTermRow.war_id == war_id).order_by(PeaceTermRow.id)))
        refs: dict[int, NodeRef] = await node_refs(
            session, {item for row in rows for item in (row.beneficiary_entity_id, row.obligor_entity_id, row.treaty_entity_id) if item}
        )
        return [
            PeaceTermView(
                id=row.id,
                war_id=row.war_id,
                kind=row.kind,
                beneficiary=refs.get(row.beneficiary_entity_id) if row.beneficiary_entity_id else None,
                obligor=refs.get(row.obligor_entity_id) if row.obligor_entity_id else None,
                treaty=refs.get(row.treaty_entity_id) if row.treaty_entity_id else None,
                params=dict(row.params or {}),
                epoch=row.epoch,
                note=row.note,
            )
            for row in rows
        ]
