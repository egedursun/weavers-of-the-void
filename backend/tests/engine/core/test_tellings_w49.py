from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.made import InformationTrustRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.db.tables.tellings import RumourDistortionRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import RumourChannel
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import IncidentTier, InstrumentKind, RumourDistortion, StepAction, StepLocus, StepOutcome, WitnessMode
from aerona.engine.context import TickContext
from aerona.engine.lore.rumours import plant
from aerona.engine.lore.tellings import Telling, heard_again, told_version
from aerona.engine.lore.witnesses import choose_witnesses
from aerona.engine.notes import fold_tick_lines
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal, settlement

MACE = "flanged_mace"
CLUB = "war_club"


def duel(actor: int, target: int) -> Telling:
    incident = IncidentRow(id=1, kind="player.history", epoch=1, year=40, tier=IncidentTier.STEPS, locked=[])
    strike = IncidentStepRow(
        id=11,
        incident_id=1,
        position=0,
        round=1,
        action=StepAction.STRIKE,
        actor_node_id=actor,
        target_node_id=target,
        instrument_kind=InstrumentKind.EQUIPMENT_MODEL,
        instrument_key=MACE,
        locus_kind=StepLocus.BODY_PART,
        locus_key="arm",
        outcome=StepOutcome.BROKEN,
    )
    fall = IncidentStepRow(id=12, incident_id=1, position=1, round=1, action=StepAction.FALL, actor_node_id=target)
    return Telling(
        incident,
        roles=[
            IncidentParticipantRow(incident_id=1, node_id=actor, role=IncidentRole.ACTOR, position=0),
            IncidentParticipantRow(incident_id=1, node_id=target, role=IncidentRole.TARGET, position=1),
        ],
        facts=[IncidentFactRow(incident_id=1, key="exchanges", position=0, number=3)],
        steps=[strike, fall],
    )


def test_a_retold_duel_names_another_weapon_and_drops_the_fall_while_the_record_keeps_both() -> None:
    telling = duel(5, 6)
    swapped = RumourDistortionRow(distortion=RumourDistortion.ROLE_CHANGED, role=IncidentRole.INSTRUMENT, step_id=11, told_enum_value=CLUB)
    dropped = RumourDistortionRow(distortion=RumourDistortion.STEP_DROPPED, step_id=12)
    later = RumourDistortionRow(distortion=RumourDistortion.MOMENT_CHANGED, told_year=43)
    told = told_version(telling, [swapped, dropped, later])
    assert [step.instrument_key for step in told.steps] == [CLUB]
    assert told.year == 43
    assert [step.instrument_key for step in telling.steps] == [MACE, None] and telling.incident.year == 40


def test_a_swapped_doer_and_a_changed_amount_change_only_the_told_version() -> None:
    telling = duel(5, 6)
    told = told_version(
        telling,
        [
            RumourDistortionRow(distortion=RumourDistortion.DOER_SWAPPED, role=IncidentRole.ACTOR, told_node_id=9),
            RumourDistortionRow(distortion=RumourDistortion.AMOUNT_CHANGED, fact_key="exchanges", told_number=7),
        ],
    )
    assert [(part.role, part.node_id) for part in told.parts] == [(IncidentRole.ACTOR, 9), (IncidentRole.TARGET, 6)]
    assert [fact.number for fact in told.facts] == [7]
    assert telling.roles[0].node_id == 5 and telling.facts[0].number == 3


async def test_those_present_at_a_happening_witness_it_by_what_they_saw(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    near = await settlement(session, "Velm", world, world.regions[1])
    doer = await mortal(session, "Ama", world, town.id)
    onlooker = await mortal(session, "Dun", world, town.id)
    neighbour = await mortal(session, "Kel", world, near.id)
    incident = IncidentRow(kind="player.history", epoch=ctx.epoch, world_id=world.world.id, place_entity_id=town.id, magnitude=10, locked=[])
    session.add(incident)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=incident.id, node_id=doer.id, role=IncidentRole.ACTOR, position=0))
    await session.flush()
    assert await choose_witnesses(ctx, await RegionAtlas.load(session)) > 0
    seen = {
        row.node_id: row
        for row in await session.scalars(
            select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id, IncidentParticipantRow.role == IncidentRole.WITNESS)
        )
    }
    assert seen[onlooker.id].witness_mode is WitnessMode.SAW and seen[onlooker.id].fidelity == ctx.rules.records.fidelity_saw
    assert seen[town.id].witness_mode is WitnessMode.SAW
    assert doer.id not in seen
    assert neighbour.id not in seen
    assert near.id not in seen
    again = await choose_witnesses(ctx, await RegionAtlas.load(session))
    assert again == 0
    loud = IncidentRow(
        kind="player.history", epoch=ctx.epoch, world_id=world.world.id, place_entity_id=town.id, magnitude=ctx.rules.rumours.min_magnitude, locked=[]
    )
    session.add(loud)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=loud.id, node_id=doer.id, role=IncidentRole.ACTOR, position=0))
    await session.flush()
    await choose_witnesses(ctx, await RegionAtlas.load(session))
    heard = {
        row.node_id: row.witness_mode
        for row in await session.scalars(
            select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == loud.id, IncidentParticipantRow.role == IncidentRole.WITNESS)
        )
    }
    assert heard[town.id] is WitnessMode.SAW and neighbour.id not in heard
    assert all(mode is WitnessMode.HEARD for node, mode in heard.items() if node not in {town.id, onlooker.id})


async def rumour(session: AsyncSession, incident_id: int, carrier: int, fidelity: int) -> RumourRow:
    row = RumourRow(
        incident_id=incident_id,
        carrier_entity_id=carrier,
        channel=RumourChannel.ROUTE,
        fidelity=fidelity,
        hops=1,
        epoch=1,
        lingered=0,
        acted=False,
        planted=False,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return row


async def test_a_truer_telling_corrects_a_garbled_one_and_a_contrary_one_costs_trust(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    other = await settlement(session, "Velm", world, world.regions[1])
    incident = IncidentRow(kind="player.history", epoch=ctx.epoch, world_id=world.world.id, place_entity_id=town.id, year=40, locked=[])
    session.add(incident)
    await session.flush()
    held = await rumour(session, incident.id, town.id, 40)
    garbled = RumourDistortionRow(rumour_id=held.id, position=0, distortion=RumourDistortion.MOMENT_CHANGED, told_year=44, epoch=1, locked=[])
    session.add(garbled)
    truer = await rumour(session, incident.id, other.id, 80)
    await session.flush()
    assert await heard_again(ctx, truer, held, [], [garbled]) == "rumour.corrected"
    await session.flush()
    assert held.fidelity == 80
    assert not list(await session.scalars(select(RumourDistortionRow).where(RumourDistortionRow.rumour_id == held.id)))
    contrary = RumourDistortionRow(rumour_id=truer.id, position=0, distortion=RumourDistortion.PLACE_CHANGED, told_node_id=other.id, epoch=1, locked=[])
    session.add(contrary)
    await session.flush()
    assert await heard_again(ctx, truer, held, [contrary], []) == "information.contradicted"
    trust = await session.get(InformationTrustRow, town.id)
    assert trust is not None and trust.information_trust == 60 - round(ctx.rules.rumours.contradiction_trust_loss * 1 * truer.fidelity / 100)
    wider = RumourDistortionRow(rumour_id=truer.id, position=1, distortion=RumourDistortion.MOMENT_CHANGED, told_year=99, epoch=1, locked=[])
    session.add(wider)
    await session.flush()
    before = trust.information_trust
    assert await heard_again(ctx, truer, held, [contrary, wider], []) == "information.contradicted"
    assert before - trust.information_trust == round(ctx.rules.rumours.contradiction_trust_loss * 2 * truer.fidelity / 100)


async def test_folding_groups_lines_as_a_view_and_hides_none_of_them(session: AsyncSession, world: CoreWorld, rules: Rules) -> None:
    rows = [ChronicleRow(epoch=1, kind=ChronicleKind.WORLD, text=f"The bell rang {index} times.", template_key="player.history") for index in range(4)]
    session.add_all(rows)
    await session.flush()
    folded = await fold_tick_lines(session, rules, 1, 0)
    assert folded.folded_groups == 1
    kept = list(await session.scalars(select(ChronicleRow).where(ChronicleRow.template_key == "player.history")))
    assert len(kept) == 4 and all(row.visible and row.kind is ChronicleKind.WORLD for row in kept)
    assert not list(await session.scalars(select(ChronicleRow).where(ChronicleRow.template_key.like("%.folded"))))


async def test_a_planted_rumour_is_an_untold_account_with_its_subject_and_its_false_content(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    accused = await mortal(session, "Ama", world, town.id)
    row = await plant(ctx, town.id, incident_id=None, subject_id=accused.id, text="Ama opened the gates at night.", fidelity=70)
    incident = await session.get(IncidentRow, row.incident_id)
    assert incident is not None and not INCIDENT_KINDS[incident.kind].told
    roles = {
        (part.node_id, part.role) for part in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id))
    }
    assert roles == {(accused.id, IncidentRole.SUBJECT)}
    facts = list(await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id)))
    assert [(fact.key, fact.name) for fact in facts] == [("account", "Ama opened the gates at night.")]
    assert incident.chronicle_id is None


async def test_a_ruined_town_hears_nothing_and_a_named_witness_says_how_it_knows(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await settlement(session, "Ardun", world, world.regions[0])
    near = await settlement(session, "Velm", world, world.regions[1])
    ruin = await settlement(session, "Osk", world, world.regions[1])
    ruin.status, ruin.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    doer = await mortal(session, "Ama", world, town.id)
    named = await mortal(session, "Dun", world, town.id)
    await session.flush()
    atlas = await RegionAtlas.load(session)
    assert ruin.id not in atlas.communities_in(world.regions[1].id) and near.id in atlas.communities_in(world.regions[1].id)
    loud = IncidentRow(
        kind="player.history", epoch=ctx.epoch, world_id=world.world.id, place_entity_id=town.id, magnitude=ctx.rules.rumours.min_magnitude, locked=[]
    )
    session.add(loud)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=loud.id, node_id=doer.id, role=IncidentRole.ACTOR, position=0))
    session.add(IncidentParticipantRow(incident_id=loud.id, node_id=named.id, role=IncidentRole.WITNESS, position=1))
    await session.flush()
    await choose_witnesses(ctx, atlas)
    witnesses = {
        row.node_id: row
        for row in await session.scalars(
            select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == loud.id, IncidentParticipantRow.role == IncidentRole.WITNESS)
        )
    }
    assert ruin.id not in witnesses
    assert witnesses[near.id].witness_mode is WitnessMode.HEARD
    assert witnesses[named.id].witness_mode is WitnessMode.SAW and witnesses[named.id].fidelity == ctx.rules.records.fidelity_saw
