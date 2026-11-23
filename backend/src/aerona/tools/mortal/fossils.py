from typing import Any

from sqlalchemy import select

from aerona.catalog.nature_kinds50 import PRESERVATIONS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.discovery import TheoryAdherentRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.ecology import RangeTrend
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.fossil import FossilReading
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.ecology.fossils import told
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity, top_region
from aerona.engine.recording.terms import explaining_alone, term
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class StudyFossilsInput(ToolInput):
    bed_id: int
    reading: FossilReading = FossilReading.DEEP_TIME


async def revive(call: MortalCall, bed: FossilBedRow) -> str | None:
    table = call.rules.fossils
    kind = await call.session.get(EntityRow, bed.source_entity_id) if bed.source_entity_id is not None else None
    if kind is None or kind.entity_type is not EntityType.SPECIES or kind.status is EntityStatus.CANON or held(kind.id):
        return None
    if (
        not PRESERVATIONS[bed.preservation].keeps_soft
        or bed.richness < table.revival_preservation_min
        or not await knows(call.session, call.me.id, KnowledgeBranch.BIOMANCY)
    ):
        return None
    kind.status = EntityStatus.CANON
    if await call.session.get(SpeciesRangeRow, (kind.id, bed.region_entity_id)) is None:
        call.session.add(
            SpeciesRangeRow(
                species_entity_id=kind.id, region_entity_id=bed.region_entity_id, abundance=table.revival_abundance, trend=RangeTrend.RISING, locked=[]
            )
        )
    await call.record(
        "life.revived",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: kind.id, IncidentRole.PLACE: bed.region_entity_id},
        facts={"richness": bed.richness},
        place=bed.region_entity_id,
    )
    return kind.name


async def study_fossils(call: MortalCall, args: StudyFossilsInput) -> str:
    bed = await call.session.get(FossilBedRow, args.bed_id)
    home = await top_region(call.session, call.me)
    if bed is None or bed.found_epoch is None:
        fail(MortalResult.FOSSILS_REFUSED, why="there is no such bed laid bare")
    if home is None or home.id != bed.region_entity_id:
        fail(MortalResult.FOSSILS_REFUSED, why="the bed lies in another land")
    if held(bed.region_entity_id) or "reading" in bed.locked:
        fail(MortalResult.FOSSILS_REFUSED, why="a god holds this bed as it is")
    if args.reading is FossilReading.UNREAD:
        fail(MortalResult.FOSSILS_REFUSED, why="studying a bed reads it one way or another")
    bed.reading = args.reading
    if args.reading is not FossilReading.DEEP_TIME:
        community = await living_entity(call.session, call.me.location_id)
        if community is not None and community.entity_type in COMMUNITY_TYPES:
            await told(call.tick, bed, community)
        call.target(bed.region_entity_id)
        await call.record(
            "land.fossil_read",
            roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: bed.region_entity_id},
            facts={"preservation": bed.preservation, "richness": bed.richness},
            place=bed.region_entity_id,
        )
        return result(MortalResult.FOSSILS_STUDIED, richness=bed.richness, preservation=spoken(bed.preservation))
    shift = call.rules.fossils.theory_shift
    for row in list(
        await call.session.scalars(
            select(TheoryAdherentRow).where(TheoryAdherentRow.adherent_entity_id == call.me.id).order_by(TheoryAdherentRow.theory_entity_id)
        )
    ):
        if "strength" not in row.locked:
            with explaining_alone():
                term("fossils.study", shift, source_node_id=call.me.id)
                row.strength = clamp_int(row.strength + shift, 0, PERCENT)
    call.target(bed.region_entity_id)
    await call.record(
        "land.fossil_read",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: bed.region_entity_id},
        facts={"preservation": bed.preservation, "richness": bed.richness},
        place=bed.region_entity_id,
    )
    raised = await revive(call, bed)
    revived = f" From its remains {raised} lives again." if raised else ""
    return result(MortalResult.FOSSILS_STUDIED, richness=bed.richness, preservation=spoken(bed.preservation)) + revived


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [ToolSpec(MortalToolId.STUDY_FOSSILS, AgentKind.MORTAL, StudyFossilsInput, meta, study_fossils)]
