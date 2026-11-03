from fastapi import APIRouter, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.mechanics import ActingMechanic, EffectiveValue, GuardRecord, IncidentRecord, MechanicRecord, ModifierRecord, NodeMechanicsView
from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import GENERIC_CARRIERS, all_edges, mechanic_reads, mechanic_writes
from aerona.engine.interconnect.incidents import chain_to, last_incident
from aerona.engine.interconnect.sources import SOURCE_SUBSYSTEMS, reason_text
from aerona.engine.primitives.modifiers import ModifierIndex
from aerona.engine.primitives.stats import base_stat

router = APIRouter(tags=["mechanics"])

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


def modifier_record(row: ModifierRow, names: dict[int, str]) -> ModifierRecord:
    source_name = names.get(row.source_node_id) if row.source_node_id is not None else None
    return ModifierRecord(
        id=row.id,
        key=row.target_key,
        op=row.op,
        magnitude=row.magnitude,
        source_kind=row.source_kind,
        source_subsystem=SOURCE_SUBSYSTEMS[row.source_kind],
        source_node_id=row.source_node_id,
        source_name=source_name,
        reason_key=row.reason_key,
        reason=reason_text(row.reason_key, source_name),
        stacking_group=row.stacking_group,
        start_epoch=row.start_epoch,
        end_epoch=row.end_epoch,
        decay_pct=row.decay_pct,
    )


def stat_keys(entity: EntityRow) -> list[str]:
    return [key for key, value in entity.stats.model_dump().items() if key != "kind" and isinstance(value, int)]


async def source_names(session: AsyncSession, rows: list[ModifierRow]) -> dict[int, str]:
    ids = sorted({row.source_node_id for row in rows if row.source_node_id is not None})
    names: dict[int, str] = {}
    for node_id in ids:
        found = await session.get(EntityRow, node_id)
        if found is not None:
            names[node_id] = found.name
    return names


async def acting_mechanics(session: AsyncSession, entity: EntityRow | None, suppressed: set[str]) -> list[ActingMechanic]:
    if entity is None:
        return []
    kind = entity.entity_type.value
    prefix = f"{kind}."
    edges = all_edges()
    found: list[ActingMechanic] = []
    for mechanic in sorted(REGISTERED.values(), key=lambda item: item.key):
        writes = sorted(key.removeprefix(prefix) for key in mechanic_writes(mechanic) if key.startswith(prefix))
        reads = sorted(key.removeprefix(prefix) for key in mechanic_reads(mechanic) if key.startswith(prefix))
        if kind not in mechanic.targets and not writes and not reads:
            continue
        last = await last_incident(session, entity.id, mechanic.templates)
        chronicle = await session.get(ChronicleRow, last.chronicle_id) if last is not None and last.chronicle_id is not None else None
        found.append(
            ActingMechanic(
                key=mechanic.key,
                title=mechanic.title,
                subsystem=mechanic.subsystem,
                spec_item=mechanic.spec_item,
                fields=sorted({*mechanic.fields, *writes}),
                reads=reads,
                writes=writes,
                affects=sorted(
                    {
                        edge.target
                        for edge in edges
                        if edge.writer == mechanic.key and edge.target != mechanic.subsystem and edge.carrier not in GENERIC_CARRIERS
                    }
                ),
                suppressed=mechanic.key in suppressed,
                last_incident_id=last.id if last is not None else None,
                last_text=chronicle.text if chronicle is not None else None,
                last_epoch=last.epoch if last is not None else None,
            )
        )
    return found


@router.get("/mechanics", response_model=list[MechanicRecord])
async def list_mechanics() -> list[MechanicRecord]:
    return [mechanic_record(key) for key in sorted(REGISTERED)]


@router.get("/nodes/{node_id}/mechanics", response_model=NodeMechanicsView)
async def node_mechanics(services: ServicesDep, node_id: int = Path(ge=1)) -> NodeMechanicsView:
    async with reader(services) as session:
        entity = await session.get(EntityRow, node_id)
        node = entity if entity is not None else await session.get(NodeRow, node_id)
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
        keys = sorted({*index.keys_of(node_id), *(stat_keys(entity) if entity is not None else [])})
        for key in keys:
            base = base_stat(entity, key) if entity is not None else None
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
        )
        found = list(await session.execute(statement))
        followed: dict[int | None, list[int]] = {}
        for child in await session.scalars(select(IncidentRow).where(IncidentRow.cause_incident_id.in_([row.id for row, _ in found]))):
            followed.setdefault(child.cause_incident_id, []).append(child.id)
        depth = services.rules.current.incidents.chain_depth
        incidents = []
        for incident, role in found:
            chain = await chain_to(session, incident.id, depth)
            chronicle = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
            incidents.append(
                IncidentRecord(
                    id=incident.id,
                    kind=incident.kind,
                    epoch=incident.epoch,
                    year=incident.year,
                    role=role,
                    magnitude=incident.magnitude,
                    cause_incident_id=incident.cause_incident_id,
                    chronicle_id=incident.chronicle_id,
                    text=chronicle.text if chronicle is not None else None,
                    note=incident.note,
                    thread_id=incident.thread_id,
                    causes=list(chain.texts[:-1]),
                    consequences=followed.get(incident.id, []),
                )
            )
        return NodeMechanicsView(
            node_id=node_id,
            epoch=epoch,
            acting=await acting_mechanics(session, entity, {guard.key for guard in guards[ModifierSource.SUPPRESSION]}),
            modifiers=[modifier_record(row, await source_names(session, rows)) for row in rows if row.source_kind not in guards],
            effective=effective,
            pins=guards[ModifierSource.PIN],
            suppressions=guards[ModifierSource.SUPPRESSION],
            incidents=incidents,
        )
