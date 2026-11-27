import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import FOR_THE_DEAD
from aerona.catalog.incident_kinds.newborns import NEWBORN_KINDS
from aerona.catalog.life.services import PRESENT_MODES
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionIncidentRow, GatheringRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import WitnessMode
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.calendar import epoch_end_year
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.physics import PhysicsTable
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.accounts import account_of
from aerona.rules.registry import Rules
from aerona.services.integrity.record_links import WITNESS_KEY, witness_key

JUDGMENT_FAMILY = "fate."
DEATH_KINDS = ("mortal.death.natural", "mortal.death.cause", "mortal.death.slain", "mortals.ghost")
AGE_FACT = "age"
AGE_PHRASE = r"(\bat age |\(age ){}\b"


@dataclass(frozen=True)
class AgeBound:
    mortal: EntityRow
    allowed: int


async def rules_of(session: AsyncSession) -> tuple[Rules, int]:
    cosmos = await CosmosRepository(session).require_cosmos()
    return rules_from_snapshot(cosmos.rules_snapshot), cosmos.epoch


async def move_incident(session: AsyncSession, incident: IncidentRow, year: int) -> None:
    incident.year, incident.season, incident.day, incident.hour = year, None, None, None
    line = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
    if line is not None:
        line.year = year
    for step in await session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident.id).order_by(IncidentStepRow.position)):
        if step.year is not None and step.year < year:
            step.year, step.season, step.day, step.hour = year, None, None, None


def close_year(rules: Rules, epoch: int) -> int:
    return epoch_end_year(epoch, rules.time.years_per_epoch) - 1


async def early_judgments(session: AsyncSession) -> list[int]:
    rules, _ = await rules_of(session)
    statement = select(IncidentRow).where(IncidentRow.kind.startswith(JUDGMENT_FAMILY), IncidentRow.year.is_not(None)).order_by(IncidentRow.id)
    return [row.id for row in await session.scalars(statement) if row.year is not None and row.year < close_year(rules, row.epoch)]


async def close_judgment(session: AsyncSession, incident_id: int) -> None:
    incident = await session.get(IncidentRow, incident_id)
    if incident is None or "year" in (incident.locked or []):
        return
    rules, _ = await rules_of(session)
    await move_incident(session, incident, close_year(rules, incident.epoch))


async def born_children(session: AsyncSession) -> dict[int, int]:
    born = (
        select(IncidentParticipantRow.node_id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(IncidentParticipantRow.role == IncidentRole.CHILD, IncidentRow.kind.in_(sorted(NEWBORN_KINDS)))
    )
    rows = await session.execute(select(NodeBirthRow.node_id, NodeBirthRow.year).where(NodeBirthRow.node_id.in_(born)).order_by(NodeBirthRow.node_id))
    return {int(node): int(year) for node, year in rows}


async def age_bounds(session: AsyncSession, only: int | None = None) -> list[AgeBound]:
    rules, epoch = await rules_of(session)
    births = await born_children(session)
    if only is not None:
        births = {node: year for node, year in births.items() if node == only}
    if not births:
        return []
    laws = await LawBook.load(session)
    physics = await PhysicsTable.load(session, rules)
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.id.in_(sorted(births))).order_by(EntityRow.id)
    found: list[AgeBound] = []
    for mortal in await session.scalars(statement):
        age = stat(mortal, "age")
        if age is None:
            continue
        ended = stat(mortal, "death_year")
        until = int(ended) if ended is not None else epoch_end_year(epoch, rules.time.years_per_epoch)
        scale = (rules.world_effects.short_life_aging_mult if laws.has(NaturalLaw.SHORT_LIFE, mortal.world_id) else 1) * physics.of(mortal.world_id).time
        allowed = round_half_up(max(0, until - births[mortal.id]) * max(1.0, scale))
        if age > allowed + max(1, epoch - mortal.birth_epoch + 1):
            found.append(AgeBound(mortal, allowed))
    return found


async def overaged(session: AsyncSession) -> list[int]:
    return [bound.mortal.id for bound in await age_bounds(session)]


def restated(text: str | None, before: int, after: int) -> str | None:
    if text is None:
        return None
    return re.sub(AGE_PHRASE.format(before), lambda found: f"{found.group(1)}{after}", text)


async def set_age(session: AsyncSession, mortal_id: int) -> None:
    bounds = await age_bounds(session, mortal_id)
    if not bounds:
        return
    mortal, allowed = bounds[0].mortal, bounds[0].allowed
    before = stat(mortal, "age")
    if before is None or not set_stats(mortal, age=allowed):
        return
    mortal.fate_note = restated(mortal.fate_note, int(before), allowed)
    mortal.description = restated(mortal.description, int(before), allowed) or mortal.description
    if mortal.status is not EntityStatus.DEAD:
        return
    deaths = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == mortal.id)
    for incident in await session.scalars(select(IncidentRow).where(IncidentRow.id.in_(deaths), IncidentRow.kind.in_(DEATH_KINDS)).order_by(IncidentRow.id)):
        for fact in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id, IncidentFactRow.key == AGE_FACT)):
            fact.number = allowed
        await session.flush()
        line = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
        told = (await account_of(session, incident.id)).retold
        if line is not None and told:
            line.text = told


async def gathering_floor(session: AsyncSession, row: GatheringRow) -> int | None:
    nodes = [node for node in (row.host_node_id, row.honoured_node_id, row.place_entity_id) if node is not None]
    years = list(await session.scalars(select(NodeBirthRow.year).where(NodeBirthRow.node_id.in_(nodes)).order_by(NodeBirthRow.year)))
    honoured = await session.get(EntityRow, row.honoured_node_id) if row.honoured_node_id is not None and row.kind in FOR_THE_DEAD else None
    death = stat(honoured, "death_year") if honoured is not None and honoured.status is EntityStatus.DEAD else None
    if death is not None:
        years.append(int(death))
    return max(years) if years else None


async def gathering_incidents(session: AsyncSession, row: GatheringRow) -> list[IncidentRow]:
    hosted = select(IncidentParticipantRow.incident_id).where(
        IncidentParticipantRow.node_id == row.host_node_id, IncidentParticipantRow.role == IncidentRole.HOST
    )
    statement = select(IncidentRow).where(IncidentRow.kind == f"gathering.{row.kind.value}", IncidentRow.epoch == row.epoch, IncidentRow.id.in_(hosted))
    if row.honoured_node_id is not None:
        honoured = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == row.honoured_node_id)
        statement = statement.where(IncidentRow.id.in_(honoured))
    if row.collection_id is not None:
        linked = select(CollectionIncidentRow.incident_id).where(CollectionIncidentRow.collection_id == row.collection_id)
        statement = select(IncidentRow).where(
            IncidentRow.kind == f"gathering.{row.kind.value}", or_(IncidentRow.id.in_(linked), IncidentRow.id.in_(statement.with_only_columns(IncidentRow.id)))
        )
    return list(await session.scalars(statement.order_by(IncidentRow.id)))


async def last_year_of(session: AsyncSession, epoch: int) -> int:
    rules, _ = await rules_of(session)
    return epoch_end_year(epoch, rules.time.years_per_epoch) - 1


async def early_rites(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(GatheringRow).order_by(GatheringRow.id)):
        floor = await gathering_floor(session, row)
        if floor is None:
            continue
        told = [incident.year for incident in await gathering_incidents(session, row) if incident.year is not None]
        last = await last_year_of(session, row.epoch)
        if (row.year is not None and not floor <= row.year <= max(floor, last)) or any(not floor <= year <= max(floor, last) for year in told):
            found.append(row.id)
    return found


async def follow_rite(session: AsyncSession, gathering_id: int) -> None:
    row = await session.get(GatheringRow, gathering_id)
    floor = await gathering_floor(session, row) if row is not None else None
    if row is None or floor is None:
        return
    last = max(floor, await last_year_of(session, row.epoch))
    if row.year is not None and not floor <= row.year <= last and "year" not in (row.locked or []):
        row.year = min(last, max(floor, row.year))
    for incident in await gathering_incidents(session, row):
        if incident.year is not None and not floor <= incident.year <= last and "year" not in (incident.locked or []):
            await move_incident(session, incident, min(last, max(floor, incident.year)))


async def unborn_witnesses(session: AsyncSession) -> list[int]:
    statement = (
        select(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .join(NodeBirthRow, NodeBirthRow.node_id == IncidentParticipantRow.node_id)
        .where(
            IncidentParticipantRow.role == IncidentRole.WITNESS,
            IncidentParticipantRow.witness_mode.in_(PRESENT_MODES),
            IncidentRow.year.is_not(None),
            IncidentRow.year < NodeBirthRow.year,
        )
        .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
    )
    return [witness_key(incident_id, node_id) for incident_id, node_id in await session.execute(statement)]


async def heard_later(session: AsyncSession, key: int) -> None:
    incident_id, node_id = divmod(key, WITNESS_KEY)
    row = await session.get(IncidentParticipantRow, (incident_id, node_id, IncidentRole.WITNESS))
    if row is None:
        return
    rules, _ = await rules_of(session)
    row.witness_mode = WitnessMode.HEARD
    row.fidelity = min(row.fidelity if row.fidelity is not None else rules.records.fidelity_heard, rules.records.fidelity_heard)
