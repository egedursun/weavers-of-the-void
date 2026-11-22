from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import GATHERING_COLLECTIONS, GATHERING_THOUGHTS
from aerona.catalog.intrigue import BELIEF_SOURCE_LABELS
from aerona.catalog.life.folkways import LEANINGS, RESPONSES
from aerona.catalog.life.households import FORM_CARE
from aerona.catalog.needs_sources import ACTIVITY_COLUMNS, NEED_SOURCES
from aerona.catalog.norms import BEHAVIOUR_READINGS, SITUATION_SHIFTS
from aerona.catalog.preferences import STATIC_TARGETS
from aerona.constants.units import PERCENT
from aerona.db.tables.belief_depth import SourceTrustRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.customs import TIME_FIELDS
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.pantheon import SyncretismRow
from aerona.db.tables.rift_control import RiftControlRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.domain.enums.activities import ActivityKind
from aerona.domain.enums.collective import NormBehaviour, NormSituation
from aerona.domain.enums.cosmography import RiftCause, RiftState, RiftWork
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.folkways import MishapAttribution
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.genetics import HouseholdForm
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.mind import MemoryKind, NeedKind, PreferenceKind, ValueAxis
from aerona.domain.enums.relations import InteractionKind
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.engine.collective.norm_situations import deeper_behaviour
from aerona.engine.cosmos.rift_control import chosen_work, work_on
from aerona.engine.customs.time_budgets import shares_for
from aerona.engine.divine.pantheon import blend
from aerona.engine.households.forms import heir_by_custom
from aerona.engine.interconnect.registry import MECHANICS
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.mind.preference_depth import shared_taste
from aerona.engine.mind.preferences import write_pref
from aerona.engine.mind.wider_needs import wider_needs
from aerona.engine.minds.continuity import merge_minds
from aerona.engine.storyteller.regions import along_curve, deeper_aim
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal
from tests.engine.core.test_arcana_w15 import foreign_caster
from tests.engine.core.test_minds_w44 import at

NEW_NEEDS = (NeedKind.AUTONOMY, NeedKind.KNOWLEDGE, NeedKind.STIMULATION, NeedKind.CONTINUITY, NeedKind.UPKEEP)


def rift(world: CoreWorld, size: int, route: int | None = None) -> RiftRow:
    row = RiftRow(
        world_id=world.world.id,
        region_entity_id=world.regions[0].id,
        dimension_id=1,
        size=size,
        stability=50,
        state=RiftState.OPEN,
        cause=RiftCause.MADE_REALM_GATE,
        opened_epoch=1,
        route_id=route,
    )
    row.locked = []
    return row


async def test_rifts_are_sealed_steadied_or_gated_by_their_holders(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    assert chosen_work(rift(world, 80)) is RiftWork.SEALING
    assert chosen_work(rift(world, 10)) is RiftWork.STABILISING
    torn = rift(world, 40)
    control = RiftControlRow(rift_id=1, work=RiftWork.SEALING, locked=[])
    await work_on(ctx, torn, control)
    assert torn.size == 40 - ctx.rules.rift_control.seal_step


def test_the_cosmic_scales_meet_through_registry_edges() -> None:
    edges = MECHANICS["cosmic_scale_edges"].couplings
    assert {edge.rule_key for edge in edges} >= {"rift_control.claim_epochs", "council.ruling_epochs"}
    assert MECHANICS["rift_control"].tables == ("rift_controls",)


async def test_every_need_has_sources_and_the_new_needs_are_reckoned(session: AsyncSession, world: CoreWorld) -> None:
    assert all(NEED_SOURCES[need] for need in NeedKind)
    assert {ACTIVITY_COLUMNS[kind] for kind in ActivityKind} <= set(TIME_FIELDS)
    someone = await mortal(session, "Ilse", world, world.regions[0].id)
    needs = await wider_needs(session, Rules(), someone, values={}, pressures={}, epoch=3)
    assert set(needs) == set(NEW_NEEDS)
    assert all(0 <= value <= PERCENT for value in needs.values())


async def test_new_tastes_have_targets_and_shared_tastes_draw_people(session: AsyncSession, world: CoreWorld) -> None:
    for kind in (PreferenceKind.TECHNOLOGY, PreferenceKind.GAME, PreferenceKind.PROFESSION, PreferenceKind.SOUND):
        assert STATIC_TARGETS[kind]
    first = await mortal(session, "Arn", world, world.regions[0].id)
    second = await mortal(session, "Bel", world, world.regions[0].id)
    for holder in (first, second):
        await write_pref(session, holder.id, PreferenceKind.GAME, "dice", 50)
    assert await shared_taste(session, Rules(), first.id, second.id) == Rules().preference_depth.partner_pull


async def test_a_source_trusted_too_little_is_not_heeded(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    assert set(BELIEF_SOURCE_LABELS) == set(BeliefSource)
    watcher = await mortal(session, "Cass", world, world.regions[0].id)
    session.add(SourceTrustRow(holder_node_id=watcher.id, source=BeliefSource.RUMOUR, trust=0, locked=[]))
    await session.flush()
    assert await believe(ctx, watcher.id, world.people.id, "wealth", 50, source=BeliefSource.RUMOUR, confidence=80) is None
    assert await believe(ctx, watcher.id, world.people.id, "wealth", 50, source=BeliefSource.SURVEILLANCE, confidence=80) is not None
    assert await session.scalar(select(func.count(BeliefRow.id)).where(BeliefRow.holder_node_id == watcher.id)) == 1


def test_new_gatherings_and_the_day_of_eight_activities() -> None:
    for kind in (GatheringKind.EXHIBITION, GatheringKind.SUMMIT_OF_GODS, GatheringKind.MOURNING, GatheringKind.SPORT_MATCH):
        assert GATHERING_COLLECTIONS[kind] and GATHERING_THOUGHTS[kind]
    shares = shares_for({ValueAxis.KNOWLEDGE: 60, ValueAxis.FAMILY: 40, ValueAxis.ARTWORK: 20}, Rules())
    assert shares["learning"] and shares["care"] and shares["art"]


def test_storyteller_follows_set_points_and_new_profiles() -> None:
    assert along_curve([[0, 10], [10, 60]], 5) == 35
    assert along_curve([], 5) is None
    row = StorytellerRow(world_id=1, profile=StorytellerProfile.SLOW_BURN, cycle_offset=0, target_points=[])
    rules = Rules()
    assert deeper_aim(rules, row, 10) == rules.storyteller_depth.slow_burn_step * 10
    row.profile = StorytellerProfile.EPISODIC
    peak = rules.storyteller_depth.episode_epochs - 1
    assert deeper_aim(rules, row, peak) == rules.storyteller_depth.episode_peak


async def test_joined_worship_and_merged_minds_conserve_their_stocks(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    god = await foreign_caster(session, world)
    god.faith, world.son.faith = 12, 4
    joined = SyncretismRow(foreign_god_id=god.id, son_id=world.son.id, people_entity_id=world.people.id, dominant_node_id=world.son.id, since_epoch=1)
    joined.locked = []
    session.add(joined)
    await session.flush()
    await blend(ctx)
    found = await session.get(ForeignGodRow, god.id)
    assert found is not None and found.faith + world.son.faith == 16
    first = await mortal(session, "Dov", world, world.regions[0].id)
    second = await mortal(session, "Eir", world, world.regions[0].id)
    session.add(MemoryRow(holder_node_id=second.id, subject_node_id=first.id, kind=MemoryKind.SAVED_ME, magnitude=10, decay_pct=10, epoch=1))
    await session.flush()
    before = await session.scalar(select(func.count(MemoryRow.id)).where(MemoryRow.holder_node_id.in_([first.id, second.id])))
    await merge_minds(ctx, first.id, second.id, forced=True)
    after = await session.scalar(select(func.count(MemoryRow.id)).where(MemoryRow.holder_node_id.in_([first.id, second.id])))
    assert before == after
    assert second.status is not EntityStatus.CANON


def test_household_forms_share_care_and_heirs_follow_custom() -> None:
    assert FORM_CARE[HouseholdForm.COMMUNAL] > FORM_CARE[HouseholdForm.NUCLEAR] > FORM_CARE[HouseholdForm.SINGLE]
    assert heir_by_custom(None, [], {}, {}) is None


def test_norms_reach_new_places_and_behaviours() -> None:
    assert NormSituation.WORKPLACE in SITUATION_SHIFTS and NormBehaviour.POWER_DISPLAY in BEHAVIOUR_READINGS
    assert deeper_behaviour(NormSituation.ENCOUNTER_WITH_GIFTED, False, InteractionKind.BOAST) is NormBehaviour.POWER_DISPLAY
    assert deeper_behaviour(None, True, InteractionKind.GOSSIP) is NormBehaviour.DATA_SHARING


def test_every_attribution_of_misfortune_has_a_leaning_and_a_response() -> None:
    assert set(LEANINGS) == set(MishapAttribution) == set(RESPONSES)
