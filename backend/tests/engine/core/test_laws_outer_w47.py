from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.law_grammar import LEGACY_GRAMMAR, Grammar, preset_of
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.law_grammar import LawExceptionRow, LawTheoryRow
from aerona.db.tables.outer_agency import OuterPlanRow
from aerona.db.tables.powers import PowerRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.law_grammar import LawCondition, LawExceptionKind, LawOperator, LawTarget
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.outer import OuterFate, OuterPlanState, OuterPrice, OuterSealKind
from aerona.domain.enums.powers import PowerOrigin
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.entity_stats import NaturalLawStats, OuterBeingStats
from aerona.engine.divine.law_grammar import refusal, set_grammar, spared, tend_grammar
from aerona.engine.divine.outer import outer_profile
from aerona.engine.divine.outer_agency import outer_agency, seal_being, strike_bargain
from tests.engine.core.factories import CoreWorld, entity, mortal
from tests.engine.core.test_minds_w44 import at


def test_every_old_law_is_a_row_of_the_grammar_and_maps_back() -> None:
    for law, grammar in LEGACY_GRAMMAR.items():
        if law is NaturalLaw.NONE:
            assert grammar is None
            continue
        assert grammar is not None
        assert preset_of(grammar.target, grammar.operator, grammar.key, grammar.value) is law


def test_a_law_takes_only_workings_its_target_allows() -> None:
    assert refusal(LawTarget.HARVEST, LawOperator.MULTIPLY, "harvest", 140) is None
    assert refusal(LawTarget.HARVEST, LawOperator.FORBID, "harvest", 0) is not None
    assert refusal(LawTarget.POWERS, LawOperator.SET, "strength", 2) is None
    assert refusal(LawTarget.POWERS, LawOperator.SET, "colour", 2) is not None


async def new_law(session: AsyncSession, world: CoreWorld, name: str) -> int:
    law = await entity(session, name, EntityType.NATURAL_LAW, NaturalLawStats(), world_id=world.world.id)
    return law.id


async def test_a_law_over_a_measure_presses_through_the_modifier_bus(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    world.people.stats = world.people.stats.model_copy(update={"prosperity": 40})
    law = await session.get(type(world.people), await new_law(session, world, "The Even Hand"))
    assert law is not None
    row = await set_grammar(ctx, law, Grammar(LawTarget.STAT, LawOperator.SET, "prosperity", 80), LawCondition.ALWAYS, None, hold=True)
    await tend_grammar(ctx, [row])
    found = await session.scalar(
        select(ModifierRow).where(
            ModifierRow.target_node_id == world.people.id, ModifierRow.source_kind == ModifierSource.LAW_GRAMMAR, ModifierRow.target_key == "prosperity"
        )
    )
    assert found is not None and found.magnitude > 0
    assert law.natural_law is NaturalLaw.NONE


async def test_the_weaker_of_two_contrary_laws_is_suspended_and_peoples_form_theories(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    rows = []
    for name, value, strength in (("The Firm Rule", 80, 90), ("The Soft Rule", 20, 20)):
        law = await session.get(type(world.people), await new_law(session, world, name))
        assert law is not None
        row = await set_grammar(ctx, law, Grammar(LawTarget.STAT, LawOperator.SET, "prosperity", value), LawCondition.ALWAYS, None, hold=True)
        row.strength = strength
        rows.append(row)
    await tend_grammar(ctx, rows)
    assert rows[1].suspended and not rows[0].suspended
    theory = await session.scalar(
        select(LawTheoryRow).where(LawTheoryRow.holder_node_id == world.people.id, LawTheoryRow.law_entity_id == rows[0].law_entity_id)
    )
    assert theory is not None


async def test_an_exception_spares_its_kind(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    law_id = await new_law(session, world, "The Narrow Rule")
    session.add(LawExceptionRow(law_entity_id=law_id, kind=LawExceptionKind.KIND, entity_type=EntityType.PEOPLE, locked=[]))
    await session.flush()
    assert await spared(ctx, law_id, world.people)
    assert await session.get(NaturalLawProfileRow, law_id) is None


async def test_an_outer_being_takes_up_an_aim_and_a_seal_thwarts_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    being = await entity(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    await outer_agency(ctx)
    plan = await session.scalar(select(OuterPlanRow).where(OuterPlanRow.outer_entity_id == being.id))
    assert plan is not None and plan.state is OuterPlanState.ACTIVE and plan.progress > 0
    await seal_being(ctx, being, world.son.id, OuterSealKind.SEAL, 100)
    await outer_agency(ctx)
    assert plan.state is OuterPlanState.THWARTED
    assert (await outer_profile(ctx, being)).fate is OuterFate.SEALED


async def test_a_bargain_gives_a_bonded_power_and_an_unfed_being_starves(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    being = await entity(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    holder = await mortal(session, "Wren", world, world.regions[0].id)
    pact = await strike_bargain(ctx, being, holder, OuterPrice.OFFERING)
    power = await session.get(PowerRow, pact.power_id)
    assert power is not None and power.origin is PowerOrigin.BONDED and power.granted_by_node_id == being.id
    profile = await outer_profile(ctx, being)
    profile.unfed_epochs = ctx.rules.outer_beings.starve_epochs
    await outer_agency(ctx)
    assert profile.fate is OuterFate.STARVED and being.status is EntityStatus.DESTROYED
