import re

from sqlalchemy import select

from aerona.catalog.incident_kinds.g07_law import KINDS as LAW_KINDS
from aerona.catalog.incident_kinds.g08_diplomacy import KINDS as DIPLOMACY_KINDS
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.cycles import LongPlanKind, PlanOutcome
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathBreach, OathKind
from aerona.engine.cycles.control import advance_plan, new_plan
from aerona.engine.phases.tribute import decree_tribute, forgive_tribute
from aerona.engine.polity.oaths import break_oath, swear
from tests.engine.society.factories import Realm, context, mortal, settlement, son, tuned

PLACEHOLDER = re.compile(r"\{(\w+)")


async def incident_of(realm: Realm, key: str) -> IncidentRow:
    found = await realm.session.scalar(select(IncidentRow).where(IncidentRow.kind == key).order_by(IncidentRow.id.desc()).limit(1))
    assert found is not None, key
    return found


async def roles_of(realm: Realm, incident: IncidentRow) -> dict[IncidentRole, set[int]]:
    rows = await realm.session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id))
    found: dict[IncidentRole, set[int]] = {}
    for row in rows:
        found.setdefault(row.role, set()).add(row.node_id)
    return found


async def facts_of(realm: Realm, incident: IncidentRow) -> dict[str, IncidentFactRow]:
    return {row.key: row for row in await realm.session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id))}


def test_every_law_and_diplomacy_kind_is_typed_and_tells_only_its_declared_fields() -> None:
    kinds = [*LAW_KINDS, *DIPLOMACY_KINDS]
    assert not [kind.key for kind in kinds if kind.draft]
    for kind in kinds:
        declared = {spec.role.value for spec in kind.roles} | {spec.key for spec in kind.facts}
        assert set(PLACEHOLDER.findall(kind.template)) <= declared, kind.key


async def test_a_broken_oath_is_told_with_its_breach_its_witness_and_the_wrath_it_caused(realm: Realm) -> None:
    ctx = context(realm.session, tuned(oaths={"wrath_curse_chance": 100}))
    town = await settlement(realm, "Hollin")
    swearer = await mortal(realm, "Brann", location_id=town.id)
    lord = await mortal(realm, "Avel", location_id=town.id)
    witness = await son(realm.session, "Vael", realm.world.id)
    oath = await swear(ctx, swearer, OathKind.FEALTY, recipient_id=lord.id, witness=witness)
    await break_oath(ctx, oath, OathBreach.THRONE_SEIZED)
    broken = await incident_of(realm, "oaths.broken")
    roles = await roles_of(realm, broken)
    assert roles[IncidentRole.SUBJECT] == {swearer.id} and roles[IncidentRole.RECEIVER] == {lord.id} and roles[IncidentRole.PATRON] == {witness.id}
    facts = await facts_of(realm, broken)
    assert facts["breach"].enum_value == OathBreach.THRONE_SEIZED.value and facts["oath_kind"].enum_value == OathKind.FEALTY.value
    wrath = await incident_of(realm, "oaths.wrath_cursed")
    assert wrath.cause_incident_id == broken.id and broken.place_entity_id == town.id


async def test_tribute_is_told_between_its_giver_and_receiver_and_its_forgiving_counts_its_years(realm: Realm) -> None:
    ctx = context(realm.session)
    payer, receiver = await settlement(realm, "Hollin"), await settlement(realm, "Farwatch")
    row = await decree_tribute(ctx, payer.id, receiver.id)
    decreed = await incident_of(realm, "tribute.decree")
    assert await roles_of(realm, decreed) == {IncidentRole.GIVER: {payer.id}, IncidentRole.RECEIVER: {receiver.id}}
    await forgive_tribute(context(realm.session, epoch=ctx.epoch + 2), row.id)
    forgiven = await facts_of(realm, await incident_of(realm, "tribute.forgiven"))
    assert forgiven["epochs"].number == 2


async def test_a_fulfilled_plan_is_told_by_its_typed_outcome(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Hollin")
    plan = await new_plan(ctx, town.id, LongPlanKind.EXPLORATION, "The Long Road", target_id=None, carrier_id=None, steps=2, step_cost=0, secrecy=50)
    begun = await facts_of(realm, await incident_of(realm, "plans.begun"))
    assert begun["plan"].name == "The Long Road" and begun["plan_kind"].enum_value == LongPlanKind.EXPLORATION.value
    await advance_plan(ctx, plan.id, 2)
    keys = {f"plans.completed_{outcome.value}" for outcome in (PlanOutcome.WAYS_CHARTED, PlanOutcome.NOTHING_FOUND)}
    told = await realm.session.scalar(select(IncidentRow).where(IncidentRow.kind.in_(keys)))
    assert told is not None
    assert (await facts_of(realm, told))["plan"].name == "The Long Road"
