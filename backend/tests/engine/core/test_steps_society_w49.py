import pytest
from sqlalchemy import select

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.records import IncidentStepRow
from aerona.domain.enums.cycles import GiftOccasion, ManumissionPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import HouseholdDecision
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.engine.cycles.gifts import give, refuse
from aerona.engine.cycles.indenture import bought_freedom
from aerona.engine.intrigue.schemes import plotted
from aerona.engine.phases.vendettas import mediate, wergild
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import checked_steps, record
from aerona.rules.registry import Rules
from tests.engine.integration.factories import seed_rich_cosmos

DECLARED = {
    "tools.mortal.adopted": {StepAction.ADOPT},
    "tools.son.answer_oracle": {StepAction.ANSWER},
    "tools.son.answer_offerings": {StepAction.ANSWER, StepAction.RETURN_GIFT},
    "gods.mood.prayer_answered": {StepAction.ANSWER},
    "vendetta.assassinate": {StepAction.AVENGE},
    "vendetta.ambush": {StepAction.AVENGE},
    "vendetta.abduct": {StepAction.AVENGE},
    "vendetta.raid": {StepAction.AVENGE},
    "vendetta.raid_halls": {StepAction.AVENGE},
    "vendetta.destroy_property": {StepAction.AVENGE},
    "vendetta.demand_wergild": {StepAction.APOLOGISE, StepAction.RECONCILE},
    "vendetta.mediated": {StepAction.RECONCILE},
    "vendetta.seek_mediation": {StepAction.RECONCILE},
    "gifts.refused": {StepAction.REFUSE, StepAction.INSULT},
    "oaths.broken": {StepAction.BREAK_OATH},
    "diplomacy.betrayal": {StepAction.BETRAY},
    "diplomacy.betrayal_war": {StepAction.BETRAY},
    "war.call_betrayed": {StepAction.REFUSE, StepAction.BETRAY},
    "prisoner.ransomed": {StepAction.PAY, StepAction.BUY_FREEDOM},
    "tools.mortal.ransomed": {StepAction.PAY, StepAction.BUY_FREEDOM},
    "society.freed": {StepAction.BUY_FREEDOM},
    "manumission.freed": {StepAction.BUY_FREEDOM},
    "tools.son.crown_ruler": {StepAction.CROWN},
    "polity.coup": {StepAction.DEPOSE, StepAction.CROWN},
    "polity.coup_empty_throne": {StepAction.CROWN},
    "war.mutiny.deposed": {StepAction.DEPOSE},
    f"households.{HouseholdDecision.HIRE_SERVANT.value}": {StepAction.HIRE},
    f"households.{HouseholdDecision.DISMISS_SERVANT.value}": {StepAction.DISMISS},
    "war.mercenaries_hired": {StepAction.HIRE},
    "civilization.debt_paid": {StepAction.REPAY},
    "tools.mortal.repaid": {StepAction.REPAY},
    "trust.forgery_found": {StepAction.FIND_EVIDENCE},
    "tools.mortal.investigate": {StepAction.INVESTIGATE, StepAction.FIND_EVIDENCE},
    "tools.son.expose_forgery": {StepAction.FIND_EVIDENCE},
    "tools.mortal.forge_record": {StepAction.FORGE_RECORD},
    f"intrigue.scheme_done_{PlotKind.FORGE_LETTER.value}": {StepAction.FORGE_RECORD},
    f"intrigue.scheme_done_{PlotKind.FRAME.value}": {StepAction.DECEIVE},
    f"intrigue.scheme_done_{PlotKind.SWAY.value}": {StepAction.PERSUADE},
    f"intrigue.scheme_exposed_{PlotKind.MURDER.value}": {StepAction.FIND_EVIDENCE},
    "tools.son.spread_word": {StepAction.SPREAD_WORD},
    "faction.strike": {StepAction.STRIKE_WORK},
    "art.translated": {StepAction.TRANSLATE},
    "tools.mortal.preached": {StepAction.PERSUADE},
    "tools.mortal.preach_failed": {StepAction.PERSUADE},
    "statecraft.terms_eased": {StepAction.BARGAIN},
    "statecraft.terms_refused": {StepAction.BARGAIN},
}


@pytest.mark.parametrize("key", sorted(DECLARED))
def test_every_kind_declares_the_stages_its_process_records(key: str) -> None:
    assert DECLARED[key] <= INCIDENT_KINDS[key].steps


def test_a_kind_without_servants_records_no_hiring() -> None:
    assert INCIDENT_KINDS[f"households.{HouseholdDecision.MARRY.value}"].steps == frozenset()


def test_only_bought_freedom_is_told_as_bought() -> None:
    bought = bought_freedom(7, 12, ManumissionPath.PURCHASE)
    assert [(step.action, step.target, step.amount, step.unit) for step in bought] == [(StepAction.BUY_FREEDOM, 7, 12, FactUnit.PEOPLE)]
    assert bought_freedom(7, 12, ManumissionPath.LAW) == ()
    assert bought_freedom(7, 0, ManumissionPath.PURCHASE) == ()
    assert bought_freedom(7, 12, None) == ()


def test_a_deceitful_plot_records_its_deceit_and_a_plain_one_records_none() -> None:
    owner, target = make_holder(1), make_holder(2)
    framed = plotted(SchemeRow(id=5, kind=PlotKind.FRAME), owner, target)
    assert [(step.action, step.actor, step.target, step.outcome) for step in framed] == [(StepAction.DECEIVE, 1, 2, StepOutcome.SUCCESS)]
    checked_steps(INCIDENT_KINDS[f"intrigue.scheme_done_{PlotKind.FRAME.value}"], framed)
    assert plotted(SchemeRow(id=6, kind=PlotKind.MURDER), owner, target) == ()


def make_holder(node_id: int) -> EntityRow:
    return EntityRow(id=node_id, name=f"Holder {node_id}", entity_type=EntityType.MORTAL)


async def test_wergild_is_an_apology_then_a_reconciliation(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w49_wergild_steps", Rules())
        avenger, enemy = cosmos.home.extra["town"], cosmos.home.extra["port"]
        deed = await wergild(ctx, avenger, enemy)
        assert deed is not None
        assert [step.action for step in deed.steps] == [StepAction.APOLOGISE, StepAction.RECONCILE]
        assert (deed.steps[0].actor, deed.steps[0].target, deed.steps[0].unit) == (enemy.id, avenger.id, FactUnit.WEALTH_POINTS)
        written = await record(
            ctx,
            "vendetta.demand_wergild",
            roles={IncidentRole.ACTOR: avenger.id, IncidentRole.TARGET: enemy.id, **deed.roles},
            facts={"intensity": 40, **deed.facts},
            steps=deed.steps,
        )
        actions = list(
            await session.scalars(select(IncidentStepRow.action).where(IncidentStepRow.incident_id == written.incident_id).order_by(IncidentStepRow.position))
        )
        assert actions == [StepAction.APOLOGISE, StepAction.RECONCILE]
        mediated = await mediate(ctx, avenger, enemy)
        assert mediated is not None
        assert [(step.action, step.outcome) for step in mediated.steps] == [(StepAction.RECONCILE, StepOutcome.ACCEPTED)]


async def test_a_refused_gift_is_refused_and_taken_as_an_insult(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w49_refused_gift", Rules())
        giver, receiver = cosmos.home.extra["town"], cosmos.home.extra["port"]
        gift = await give(ctx, giver.id, receiver.id, 10, GiftOccasion.COURTESY, pay=False)
        assert gift is not None
        await refuse(ctx, gift)
        rows = list(
            await session.scalars(
                select(IncidentStepRow).where(IncidentStepRow.action.in_([StepAction.REFUSE, StepAction.INSULT])).order_by(IncidentStepRow.id)
            )
        )
        assert [(row.action, row.actor_node_id, row.target_node_id) for row in rows] == [
            (StepAction.REFUSE, receiver.id, giver.id),
            (StepAction.INSULT, receiver.id, giver.id),
        ]
        assert rows[1].amount == ctx.rules.reciprocity.refusal_insult
