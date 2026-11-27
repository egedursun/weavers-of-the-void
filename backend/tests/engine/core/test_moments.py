from itertools import pairwise

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.sequence import AFTER_KINDS
from aerona.catalog.incident_kinds.under_age import ACTING_ROLES
from aerona.db.record_context import PHASE_FAMILY
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.moment import Moment
from aerona.engine.context import phase_window
from aerona.engine.pipeline import simulate
from aerona.engine.recording.chains import PRINCIPALS
from aerona.rules.registry import Rules
from aerona.services.integrity.chronology import early_rites, overaged, unborn_witnesses
from aerona.services.integrity.record_links import ahead_of_births, births_after_sighting, births_unknown
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 2
PILE = 8
DEATH_FAMILY = "mortal.death"


def moment_of(year: int | None, season: int | None, day: int | None, hour: int | None) -> Moment | None:
    return Moment(year, season, day, hour) if year is not None else None


async def test_no_happening_is_earlier_than_its_cause_and_no_step_earlier_than_the_one_before(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, EPOCHS, rules=eager(Rules()))
    cause = aliased(IncidentRow)
    async with database.read() as session:
        pairs = (
            await session.execute(
                select(
                    IncidentRow.id,
                    IncidentRow.kind,
                    IncidentRow.year,
                    IncidentRow.season,
                    IncidentRow.day,
                    IncidentRow.hour,
                    cause.year,
                    cause.season,
                    cause.day,
                    cause.hour,
                ).join(cause, cause.id == IncidentRow.cause_incident_id)
            )
        ).all()
        steps = (
            await session.execute(
                select(
                    IncidentStepRow.incident_id,
                    IncidentStepRow.position,
                    IncidentStepRow.year,
                    IncidentStepRow.season,
                    IncidentStepRow.day,
                    IncidentStepRow.hour,
                )
            )
        ).all()
        years = (
            await session.execute(select(IncidentRow.kind, IncidentRow.year, ChronicleRow.year).join(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id))
        ).all()
    early = []
    for incident_id, kind, *rest in pairs:
        own, before = moment_of(*rest[:4]), moment_of(*rest[4:])
        if own is None or (before is not None and own.before(before)):
            early.append(f"{kind} #{incident_id} at {own} before its cause at {before}")
    ordered: dict[int, list[tuple[int, Moment | None]]] = {}
    for incident_id, position, *moment in steps:
        ordered.setdefault(incident_id, []).append((position, moment_of(*moment)))
    for incident_id, rows in ordered.items():
        moments = [moment for _, moment in sorted(rows, key=lambda row: row[0])]
        if any(moment is None for moment in moments) or any(later.before(earlier) for earlier, later in pairwise(moments) if earlier and later):
            early.append(f"the steps of #{incident_id} go back in time")
    told = [f"{kind}: incident year {year} but line year {line}" for kind, year, line in years if year != line]
    async with database.read() as session:
        unborn = await ahead_of_births(session)
        undated = await births_unknown(session)
        late_births = await births_after_sighting(session)
        overgrown = await overaged(session)
        dead_acts = (
            await session.execute(
                select(IncidentRow.id, IncidentRow.kind, IncidentParticipantRow.role)
                .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
                .join(EntityRow, EntityRow.id == IncidentParticipantRow.node_id)
                .where(
                    EntityRow.entity_type == EntityType.MORTAL,
                    EntityRow.status == EntityStatus.DEAD,
                    IncidentParticipantRow.role.in_(sorted(ACTING_ROLES)),
                    IncidentRow.year > func.json_extract(EntityRow.stats, "$.death_year"),
                )
            )
        ).all()
        death = aliased(IncidentRow)
        died = aliased(IncidentParticipantRow)
        after_death = (
            await session.execute(
                select(IncidentRow.id, IncidentRow.kind, IncidentRow.year, death.year)
                .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
                .join(died, (died.node_id == IncidentParticipantRow.node_id) & (died.role == IncidentRole.SUBJECT))
                .join(death, (death.id == died.incident_id) & death.kind.like(f"{DEATH_FAMILY}%"))
                .where(IncidentRow.id > death.id, IncidentRow.year < death.year)
            )
        ).all()
        phases = (
            await session.execute(select(IncidentRow.epoch, IncidentRow.year).where(IncidentRow.kind.like(f"{PHASE_FAMILY}.%")).order_by(IncidentRow.id))
        ).all()
        early_rite = await early_rites(session)
        unborn_seers = await unborn_witnesses(session)
        dated = (
            await session.execute(
                select(IncidentRow.id, IncidentRow.kind, IncidentRow.year, IncidentFactRow.number)
                .join(IncidentFactRow, IncidentFactRow.incident_id == IncidentRow.id)
                .where(IncidentFactRow.key == "year", IncidentFactRow.unit == FactUnit.YEARS)
            )
        ).all()
    misdated = [
        f"{kind} #{incident_id} told as of year {number} but standing in year {year}"
        for incident_id, kind, year, number in dated
        if number is not None and int(number) != year
    ]
    assert early == []
    assert told == []
    assert unborn == [], f"happenings earlier than the first record of someone in them: {unborn[:20]}"
    assert misdated == [], f"happenings that tell one year and stand in another: {misdated[:20]}"
    assert undated == [], f"things named in the age they were made with no moment of coming into being: {undated[:20]}"
    assert late_births == [], f"things dated as coming into being after the first record that names them: {late_births[:20]}"
    assert overgrown == [], f"mortals born in the world older than the years since their birth: {overgrown[:20]}"
    assert dead_acts == [], f"mortals acting after the year of their death: {dead_acts[:20]}"
    assert after_death == [], f"records written after a death but dated before it: {after_death[:20]}"
    by_epoch: dict[int, list[int]] = {}
    for epoch, year in phases:
        if year is not None:
            by_epoch.setdefault(epoch, []).append(year)
    assert all(earlier <= later for years_of in by_epoch.values() for earlier, later in pairwise(years_of)), "engine steps go back in time"
    assert all(len(set(years_of)) > 1 for years_of in by_epoch.values()), "every engine step of an epoch stands in one year"
    assert early_rite == [], f"gatherings earlier than their host, the one they honour, or the death they honour: {early_rite[:20]}"
    breaks = await chain_breaks(database)
    assert breaks == ([], []), f"happenings told before the happening they follow, or all of one kind in a single year: {breaks[0][:12]} {breaks[1][:12]}"
    assert unborn_seers == [], f"witnesses who saw what happened before they came into being: {unborn_seers[:20]}"


async def chain_breaks(database: Database) -> tuple[list[str], list[str]]:
    async with database.read() as session:
        told = (
            await session.execute(
                select(
                    IncidentRow.id,
                    IncidentRow.epoch,
                    IncidentRow.kind,
                    IncidentRow.year,
                    IncidentRow.season,
                    IncidentRow.day,
                    IncidentRow.hour,
                    IncidentParticipantRow.node_id,
                )
                .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
                .where(IncidentParticipantRow.role.in_(sorted(PRINCIPALS)), IncidentRow.year.is_not(None))
            )
        ).all()
        stamped = set(await session.scalars(select(IncidentFactRow.incident_id).where(IncidentFactRow.key == "year")))
    seen: dict[tuple[int, int], list[tuple[int, str, Moment]]] = {}
    years_of_kind: dict[tuple[int, str], dict[int, int]] = {}
    for incident_id, epoch, kind, year, season, day, hour, node in told:
        if year is None:
            continue
        seen.setdefault((epoch, node), []).append((incident_id, kind, Moment(year, season, day, hour)))
        if incident_id not in stamped:
            years_of_kind.setdefault((epoch, kind), {})[incident_id] = year
    reversed_chains = [
        f"{kind} #{incident_id} at {moment} before {prior_kind} #{prior_id} at {prior_moment}"
        for happenings in seen.values()
        for incident_id, kind, moment in happenings
        for prior_id, prior_kind, prior_moment in happenings
        if prior_id < incident_id and prior_kind in AFTER_KINDS.get(kind, frozenset()) and moment.before(prior_moment)
    ]
    piled = sorted(
        f"{kind} in epoch {epoch}: {len(years)} told, all in year {next(iter(years.values()))}"
        for (epoch, kind), years in years_of_kind.items()
        if INCIDENT_KINDS[kind].told and len(years) >= PILE and len(set(years.values())) == 1 and next(iter(years.values())) not in window_ends(epoch)
    )
    return reversed_chains, piled


def window_ends(epoch: int) -> set[int]:
    rules = Rules()
    start = epoch_start_year(epoch, rules.time.years_per_epoch)
    return {start + phase_window(rules, phase).end - 1 for phase in EpochPhase}
