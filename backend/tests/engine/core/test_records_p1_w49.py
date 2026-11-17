from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.g01_single_combat import DUEL_ACTIONS
from aerona.catalog.incident_kinds.g01_single_combat import KINDS as COMBAT
from aerona.catalog.incident_kinds.g04_body import KINDS as BODY
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import DuelContext
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import InstrumentKind, StepAction, StepLocus
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.military.duels import bout, fighter, settle_bout
from aerona.engine.phases.births import deliver
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, tuned_rules

WRESTLING = frozenset({StepAction.GRAPPLE, StepAction.THROW_DOWN, StepAction.CHOKE, StepAction.LOCK, StepAction.BITE})


async def mace_for(session: AsyncSession, world: CoreWorld, owner_id: int) -> int:
    item = await entity(session, "Iron Mace", EntityType.ITEM, ItemStats(damage=60), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(ItemProfileRow(item_entity_id=item.id, item_class=ItemClass.MACE, quality=80, condition=100, reach=1, locked=[], secondary_materials=[]))
    await bond(session, owner_id, item.id, BondKind.OWNS)
    await session.flush()
    return item.id


async def test_a_duel_records_every_exchange_and_each_hit_names_its_mace_its_part_and_its_step(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "duel", rules=tuned_rules(duels={"exchanges_min": 7, "exchanges_max": 7, "grapple_chance": 0, "feint_chance": 0}))
    first = await mortal(session, "Arn", world, world.regions[0].id, strength=90, hp=200)
    second = await mortal(session, "Bel", world, world.regions[0].id, strength=30, hp=200)
    mace = await mace_for(session, world, first.id)
    fighters = (await fighter(ctx, first, second), await fighter(ctx, second, first))
    result = bout(ctx.rules, ctx.rng("duel.test"), *fighters, DuelContext.HONOUR)
    incident_id = await settle_bout(ctx, result)
    await session.flush()
    incident = await session.get(IncidentRow, incident_id)
    assert incident is not None and incident.kind == "duel.bout"
    steps = list(await session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident_id).order_by(IncidentStepRow.position)))
    assert steps and {step.action for step in steps} <= DUEL_ACTIONS
    blows = [step for step in steps if step.instrument_node_id == mace]
    assert blows and all(step.instrument_kind is InstrumentKind.ITEM and step.instrument_key == ItemClass.MACE.value for step in blows)
    struck = [step for step in steps if step.amount and step.target_node_id is not None]
    assert struck and all(step.locus_kind is StepLocus.BODY_PART and step.locus_key for step in struck)
    injuries = list(await session.scalars(select(InjuryRow).where(InjuryRow.step_id.in_([step.id for step in struck]))))
    assert injuries and all(row.incident_id == incident_id and row.instrument_kind is not None for row in injuries)
    linked = {step.id for step in steps if step.record_table == InjuryRow.__tablename__}
    assert {row.step_id for row in injuries} <= linked
    facts = {row.key for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id))}
    assert {"context", "exchanges", "end"} <= facts and bool({"winner_weapon", "loser_weapon"} & facts)


async def test_a_disarmed_fighter_wrestles_and_the_holds_are_told_as_steps(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(duels={"exchanges_min": 7, "exchanges_max": 7, "grapple_chance": 100, "feint_chance": 0, "yield_honour": -100})
    ctx = await manual_context(session, "duel", rules=rules)
    first = await mortal(session, "Cai", world, world.regions[0].id, hp=300, agility=80)
    second = await mortal(session, "Dov", world, world.regions[0].id, hp=300, agility=10)
    one, two = await fighter(ctx, first, second), await fighter(ctx, second, first)
    one.unarmed_skill, two.unarmed_skill = 90, 0
    one.disarmed = True
    result = bout(ctx.rules, ctx.rng("wrestle.test"), one, two, DuelContext.WAR)
    assert any(step.action in WRESTLING for step in result.steps)
    incident_id = await settle_bout(ctx, result)
    actions = set(await session.scalars(select(IncidentStepRow.action).where(IncidentStepRow.incident_id == incident_id)))
    assert actions & WRESTLING


async def test_a_birth_names_its_child_parents_and_labour_and_twins_are_one_happening(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(fertility={"stillbirth_pct": 0, "twins_pct": 100, "mortality_base_pct": 0})
    ctx = await manual_context(session, "births", rules=rules)
    town = world.regions[0].id
    first = await mortal(session, "Eda", world, town, age=25)
    second = await mortal(session, "Fen", world, town, age=27)
    born = await deliver(ctx, first, second, Namer(session, ctx.rules))
    assert len(born) == ctx.rules.fertility.twin_cap
    rows = list(await session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(["births.child", "births.twins"])).order_by(IncidentRow.id)))
    assert [row.kind for row in rows].count("births.child") == len(born) and rows[-1].kind == "births.twins"
    child = rows[0]
    roles = {(row.node_id, row.role) for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == child.id))}
    assert (first.id, IncidentRole.PARENT) in roles and (second.id, IncidentRole.PARENT) in roles and (born[0].id, IncidentRole.CHILD) in roles
    actions = list(await session.scalars(select(IncidentStepRow.action).where(IncidentStepRow.incident_id == child.id).order_by(IncidentStepRow.position)))
    assert actions == [StepAction.GO_INTO_LABOUR, StepAction.GIVE_BIRTH, StepAction.NAME_CHILD]
    assert child.place_entity_id == town


def test_every_kind_of_single_combat_and_the_body_is_typed_and_none_is_a_draft() -> None:
    assert not [spec.key for spec in (*COMBAT, *BODY) if spec.draft]
    assert all(spec.roles or spec.facts for spec in (*COMBAT, *BODY))
