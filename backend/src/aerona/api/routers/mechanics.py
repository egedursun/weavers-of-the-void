from fastapi import APIRouter, Path
from sqlalchemy import select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.mechanics import EffectiveValue, GuardRecord, IncidentRecord, MechanicRecord, ModifierRecord, NodeMechanicsView
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.primitives.modifiers import ModifierIndex
from aerona.engine.primitives.stats import stat

router = APIRouter(tags=["mechanics"])

INCIDENTS_SHOWN = 20
SUPPRESSION_PREFIX = "mechanic:"


def mechanic_record(key: str) -> MechanicRecord:
    mechanic = REGISTERED[key]
    return MechanicRecord(
        key=mechanic.key,
        spec_item=mechanic.spec_item,
        title=mechanic.title,
        subsystem=mechanic.subsystem,
        phases=list(mechanic.phases),
        surfaces=list(mechanic.surface.keys),
        backfill=mechanic.backfill,
        fields=list(mechanic.fields),
        flows=list(mechanic.flows),
        exposure=mechanic.exposure,
        tools=list(mechanic.tools),
        couplings=sorted({coupling.target for coupling in mechanic.couplings}),
    )


def modifier_record(row: ModifierRow) -> ModifierRecord:
    return ModifierRecord(
        id=row.id,
        key=row.target_key,
        op=row.op,
        magnitude=row.magnitude,
        source_kind=row.source_kind,
        source_node_id=row.source_node_id,
        reason_key=row.reason_key,
        stacking_group=row.stacking_group,
        start_epoch=row.start_epoch,
        end_epoch=row.end_epoch,
        decay_pct=row.decay_pct,
    )


@router.get("/mechanics", response_model=list[MechanicRecord])
async def list_mechanics() -> list[MechanicRecord]:
    return [mechanic_record(key) for key in sorted(REGISTERED)]


@router.get("/nodes/{node_id}/mechanics", response_model=NodeMechanicsView)
async def node_mechanics(services: ServicesDep, node_id: int = Path(ge=1)) -> NodeMechanicsView:
    async with reader(services) as session:
        node = await session.get(NodeRow, node_id)
        if node is None:
            raise NotFoundError("No such record.")
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        rows = list(await session.scalars(select(ModifierRow).where(ModifierRow.target_node_id == node_id).order_by(ModifierRow.id)))
        guards: dict[ModifierSource, list[GuardRecord]] = {ModifierSource.PIN: [], ModifierSource.SUPPRESSION: []}
        for row in rows:
            if row.source_kind in guards:
                key = row.target_key.removeprefix(SUPPRESSION_PREFIX)
                guards[row.source_kind].append(GuardRecord(id=row.id, key=key, end_epoch=row.end_epoch))
        index = await ModifierIndex.load(session, epoch, [node_id])
        effective: list[EffectiveValue] = []
        for key in index.keys_of(node_id):
            base = stat(node, key) if isinstance(node, EntityRow) else None
            breakdown = index.breakdown(node_id, key, float(base or 0))
            effective.append(
                EffectiveValue(
                    key=key,
                    base=breakdown.base,
                    value=breakdown.value,
                    applied=[item.modifier_id for item in breakdown.applied],
                    ignored=[item.modifier_id for item in breakdown.ignored],
                )
            )
        statement = (
            select(IncidentRow, IncidentParticipantRow.role)
            .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
            .where(IncidentParticipantRow.node_id == node_id)
            .order_by(IncidentRow.id.desc())
            .limit(INCIDENTS_SHOWN)
        )
        incidents = [
            IncidentRecord(
                id=incident.id,
                kind=incident.kind,
                epoch=incident.epoch,
                year=incident.year,
                role=role,
                magnitude=incident.magnitude,
                cause_incident_id=incident.cause_incident_id,
                chronicle_id=incident.chronicle_id,
            )
            for incident, role in await session.execute(statement)
        ]
        return NodeMechanicsView(
            node_id=node_id,
            epoch=epoch,
            modifiers=[modifier_record(row) for row in rows if row.source_kind not in guards],
            effective=effective,
            pins=guards[ModifierSource.PIN],
            suppressions=guards[ModifierSource.SUPPRESSION],
            incidents=incidents,
        )
