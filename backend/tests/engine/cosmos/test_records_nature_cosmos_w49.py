import pytest
from sqlalchemy import or_, select

from aerona.catalog.incident_kinds.g13_nature import KINDS as NATURE
from aerona.catalog.incident_kinds.g14_cosmos import KINDS as COSMOS
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentStepRow
from aerona.domain.enums.cosmography import BeingKind, BeingPhase, DimensionKind, RiftCause
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.records import FactValue, StepAction
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.beings import create_being
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.rifts import open_rift
from aerona.engine.phases.disasters import send_disaster
from aerona.engine.recording.render import render_incident
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region

SAMPLE_NUMBER = 2
SAMPLE_NAME = "Ithren"


def sample(fact: FactSpec) -> object:
    if fact.value is FactValue.NUMBER:
        return SAMPLE_NUMBER
    if fact.value is FactValue.ENUM and fact.enum is not None:
        first = next(iter(fact.enum))
        return [first] if fact.many else first
    return SAMPLE_NAME


@pytest.mark.parametrize("spec", [*NATURE, *COSMOS], ids=lambda spec: spec.key)
def test_every_nature_and_cosmos_kind_is_typed_and_tells_its_sample(spec: IncidentKindSpec) -> None:
    assert not spec.draft and spec.roles
    text = render_incident(spec, {role.role: [SAMPLE_NAME] for role in spec.roles}, {fact.key: sample(fact) for fact in spec.facts})
    assert text and "{" not in text and "}" not in text


def test_the_two_groups_share_no_key() -> None:
    keys = [spec.key for spec in (*NATURE, *COSMOS)]
    assert len(keys) == len(set(keys))


async def test_a_sent_disaster_records_its_place_and_every_step_from_begin_to_end(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Low Plain", cosmos.home.id)
    await make_entity(ctx.session, "Harrow", EntityType.SETTLEMENT, SettlementStats(population=400), world_id=cosmos.home.id, location_id=region.id)
    await send_disaster(ctx, region.id, Disaster.STORM, 60, by_id=cosmos.creator.id)
    await ctx.session.flush()
    incident = await ctx.session.scalar(select(IncidentRow).where(IncidentRow.kind == "disasters.manual_storm"))
    assert incident is not None and incident.place_entity_id == region.id
    actions = list(
        await ctx.session.scalars(select(IncidentStepRow.action).where(IncidentStepRow.incident_id == incident.id).order_by(IncidentStepRow.position))
    )
    assert actions[0] is StepAction.BEGIN and actions[-1] is StepAction.END


async def test_heavenly_happenings_name_only_entities_as_their_place_origin_and_destination(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    region = await make_region(ctx.session, "High Fell", cosmos.home.id)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Underside", DimensionKind.SHADOW, ctx.epoch))
    await create_being(ctx, BeingKind.STAR_FEEDER, cosmos.home, region=region, home_dimension_id=plane.id, phase=BeingPhase.MANIFEST)
    await create_being(ctx, BeingKind.RIFT_BORN, cosmos.home, home_dimension_id=plane.id)
    await open_rift(ctx, cosmos.home, None, plane, RiftCause.GOD)
    await ctx.session.flush()
    arrived = await ctx.session.scalar(select(IncidentRow).where(IncidentRow.kind == "being.arrived.star_feeder"))
    assert arrived is not None and arrived.place_entity_id == region.id and arrived.destination_entity_id is None
    pointed = [IncidentRow.place_entity_id, IncidentRow.origin_entity_id, IncidentRow.destination_entity_id]
    rows = list(await ctx.session.scalars(select(IncidentRow).where(or_(*(column.is_not(None) for column in pointed)))))
    ids = {value for row in rows for value in (row.place_entity_id, row.origin_entity_id, row.destination_entity_id) if value is not None}
    found = set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.id.in_(ids))))
    assert ids == found
