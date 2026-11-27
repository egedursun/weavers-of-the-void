from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.db.write_guard import held
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.reckoning import CaseOutcome, MeasureStage, ReckoningMeasure
from aerona.engine.context import TickContext
from aerona.engine.leader_cults.cults import CultTally, cult_of, tear_down
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.reckoning.book import ReckoningTally, servants
from aerona.engine.recording.record import record

LEGACY_FIXUP = "reckoning.legacy_purges"
MERCIFUL = 30
HARSH = -30
WEAK_STABILITY = 30
PRESSING = 60
FULL = 80
HALF = 50


async def choose(ctx: TickContext, ruler: int | None, realm: PolityProfileRow, pressure: int) -> list[tuple[ReckoningMeasure, int]]:
    values = await values_for(ctx.session, ruler) if ruler is not None else {}
    mercy = values.get(ValueAxis.MERCY, 0)
    chosen: list[tuple[ReckoningMeasure, int]] = []
    if realm.stability < WEAK_STABILITY:
        chosen.append((ReckoningMeasure.AMNESTY, FULL))
    elif mercy >= MERCIFUL:
        chosen += [(ReckoningMeasure.AMNESTY_FOR_CONFESSION, FULL), (ReckoningMeasure.TRUTH_INQUIRY, FULL)]
    elif mercy <= HARSH:
        chosen += [(ReckoningMeasure.TRIBUNAL, FULL), (ReckoningMeasure.OFFICE_BAR, FULL)]
    else:
        chosen += [(ReckoningMeasure.TRIBUNAL, HALF), (ReckoningMeasure.TRUTH_INQUIRY, HALF), (ReckoningMeasure.RECORD_OPENING, HALF)]
    if pressure >= PRESSING:
        chosen += [(ReckoningMeasure.REPARATION_TO_VICTIMS, HALF), (ReckoningMeasure.MEMORIAL, HALF), (ReckoningMeasure.RESTITUTION, HALF)]
    return chosen


async def tear_down_cults(ctx: TickContext, fallen: int | None) -> None:
    if fallen is None:
        return
    cult = await cult_of(ctx.session, fallen)
    if cult is not None:
        await tear_down(ctx, cult, CultTally())


async def open_reckoning(
    ctx: TickContext,
    realm: EntityRow,
    fallen: int | None,
    measures: list[tuple[ReckoningMeasure, int]],
    *,
    by: int | None,
    fallen_epoch: int,
    tally: ReckoningTally,
) -> ReckoningRow:
    row = ReckoningRow(polity_entity_id=realm.id, fallen_node_id=fallen, fallen_epoch=fallen_epoch, opened_by_node_id=by, opened_epoch=ctx.epoch, locked=[])
    profile = await ctx.session.get(PolityProfileRow, realm.id)
    row.fallen_government = profile.government if profile is not None else None
    ctx.session.add(row)
    await ctx.session.flush()
    row.resistance = clamp_int(len(await servants(ctx.session, row)) * ctx.rules.reckoning.servant_resistance, 0, PERCENT)
    await tear_down_cults(ctx, fallen)
    for measure, strength in dict(measures).items():
        ctx.session.add(
            ReckoningMeasureRow(reckoning_id=row.id, polity_entity_id=realm.id, measure=measure, strength=clamp_int(strength, 0, PERCENT), locked=[])
        )
    await ctx.session.flush()
    tally.opened += 1
    await record(
        ctx,
        "reckoning.opened",
        roles={IncidentRole.ACTOR: by, IncidentRole.SUBJECT: realm.id, IncidentRole.PREDECESSOR: fallen},
        facts={"measures": ", ".join(spoken(measure) for measure in dict(measures))},
    )
    return row


async def victims_pressure(ctx: TickContext, realm_id: int) -> int:
    purges = (
        select(CollectionRow.id)
        .join(CollectionMemberRow, CollectionMemberRow.collection_id == CollectionRow.id)
        .where(CollectionRow.kind == CollectionKind.PURGE, CollectionMemberRow.node_id == realm_id)
    )
    victims = select(CollectionMemberRow.node_id).where(CollectionMemberRow.collection_id.in_(purges), CollectionMemberRow.role == CollectionRole.VICTIM)
    return clamp_int(len(set(await ctx.session.scalars(victims))) * 10, 0, PERCENT)


async def after_coups(ctx: TickContext, tally: ReckoningTally) -> None:
    coups = select(IncidentRow.id).where(IncidentRow.kind == "polity.coup", IncidentRow.epoch == ctx.epoch).order_by(IncidentRow.id)
    for incident in list(await ctx.session.scalars(coups)):
        roles = {
            row.role: row.node_id for row in await ctx.session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident))
        }
        realm = await ctx.session.get(EntityRow, roles.get(IncidentRole.TARGET))
        profile = await ctx.session.get(PolityProfileRow, realm.id) if realm is not None else None
        if realm is None or profile is None or held(realm.id):
            continue
        if not ctx.rng(f"reckoning.open.{incident}").chance(ctx.rules.reckoning.open_chance_pct):
            continue
        pressure = await victims_pressure(ctx, realm.id)
        measures = await choose(ctx, roles.get(IncidentRole.ACTOR), profile, pressure)
        row = await open_reckoning(
            ctx, realm, roles.get(IncidentRole.PREDECESSOR), measures, by=roles.get(IncidentRole.ACTOR), fallen_epoch=ctx.epoch, tally=tally
        )
        row.victims_pressure = pressure


async def apply_legacy(ctx: TickContext, tally: ReckoningTally) -> None:
    if not await fixup_due(ctx.session, LEGACY_FIXUP):
        return
    made = 0
    for collection in list(await ctx.session.scalars(select(CollectionRow).where(CollectionRow.kind == CollectionKind.PURGE).order_by(CollectionRow.id))):
        members = list(await ctx.session.scalars(select(CollectionMemberRow).where(CollectionMemberRow.collection_id == collection.id)))
        leader = next((member.node_id for member in members if member.role is CollectionRole.LEADER), None)
        realm = await ctx.session.get(PolityProfileRow, leader) if leader is not None else None
        if realm is None:
            continue
        epoch = collection.end_epoch or collection.start_epoch
        row = ReckoningRow(
            polity_entity_id=realm.polity_entity_id, fallen_epoch=collection.start_epoch, opened_epoch=collection.start_epoch, closed_epoch=epoch, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
        ctx.session.add(
            ReckoningMeasureRow(
                reckoning_id=row.id,
                polity_entity_id=realm.polity_entity_id,
                measure=ReckoningMeasure.TRIBUNAL,
                stage=MeasureStage.DONE,
                started_epoch=collection.start_epoch,
                locked=[],
            )
        )
        for member in members:
            if member.role is CollectionRole.VICTIM:
                ctx.session.add(
                    ReckoningCaseRow(
                        reckoning_id=row.id,
                        accused_node_id=member.node_id,
                        incident_ids=[],
                        measure=ReckoningMeasure.TRIBUNAL,
                        outcome=CaseOutcome.CONVICTED,
                        epoch=epoch,
                        locked=[],
                    )
                )
        made += 1
    tally.opened += made
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"reckonings": made}))
    await ctx.session.flush()
