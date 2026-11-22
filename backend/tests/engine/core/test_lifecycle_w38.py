import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.cosmos import CAUSE_END
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.arcana import LabTextRow, WarpingRow
from aerona.db.tables.celestial import SkyEventRow, StarRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.culture import CastingRow, IdeologyAdherentRow, IdeologyProfileRow, RiteProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.divine import BreachPointRow
from aerona.db.tables.intrigue import FavourRow, HookRow, SecretRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import DimensionKind, RiftCause, RiftState
from aerona.domain.enums.culture import MagicSchool, MagicSource
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import FavourOrigin, HookSource, HookStrength, IntrigueSecret
from aerona.domain.enums.lifecycle_end import LifecycleCause, LifecycleKind, LifecycleState
from aerona.domain.enums.world import SkyEventKind, StarType, WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.domain.models.entity_stats import DiseaseStats, IdeologyStats, ItemStats, OuterBeingStats, RiteStats
from aerona.engine.arcana.warping import WarpTally, warp_world
from aerona.engine.context import TickContext
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.world_end_control import declare_end
from aerona.engine.cosmos.world_ends import EndingTally, keep_world_ends
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.divine.control import open_breach
from aerona.engine.intrigue.decay import DecayTally, keep_decays
from aerona.engine.lifecycle.end_control import destroy
from aerona.engine.lifecycle.ends import EndTally, keep_ends
from aerona.engine.lore.rites import unmet
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "lifecycle_ends", rules=tuned_rules(**rules))


async def state_of(session: AsyncSession, holder_id: int) -> LifecycleStateRow:
    row = await session.get(LifecycleStateRow, holder_id)
    assert row is not None
    return row


async def test_an_ideology_with_no_one_left_falls_dormant_is_taken_up_from_its_texts_and_dies_out_without_them(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Quillford", world, world.regions[0])
    book = await entity(session, "The Plain Creed", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    await bond(session, town.id, book.id, BondKind.OWNS)
    creed = await entity(session, "The Plain Way", EntityType.IDEOLOGY, IdeologyStats(), world_id=world.world.id)
    session.add(IdeologyProfileRow(ideology_entity_id=creed.id, texts=[book.id], locked=[]))
    await session.flush()
    await keep_ends(await at(session, 2, lifecycle_ends={"revival_pct": 0}), EndTally())
    row = await state_of(session, creed.id)
    assert row.state is LifecycleState.DORMANT and row.cause is LifecycleCause.NO_ADHERENTS
    await keep_ends(await at(session, 3, lifecycle_ends={"revival_pct": 100}), EndTally())
    assert row.state is LifecycleState.ACTIVE and row.cause is LifecycleCause.REVIVED
    assert await session.get(IdeologyAdherentRow, (creed.id, town.id)) is not None
    await session.delete(await session.get(IdeologyAdherentRow, (creed.id, town.id)))
    book.status = EntityStatus.DEAD
    book.end_epoch = 1
    await session.flush()
    await keep_ends(await at(session, 4, lifecycle_ends={"revival_pct": 0}), EndTally())
    assert row.state is LifecycleState.EXTINCT and row.cause is LifecycleCause.NO_TEXTS


async def test_a_disease_without_hosts_is_eradicated_and_a_new_outbreak_rereleases_it(session: AsyncSession, world: CoreWorld) -> None:
    sickness = await entity(session, "Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    epochs = tuned_rules().lifecycle_ends.eradication_epochs
    for epoch in range(2, 2 + epochs):
        await keep_ends(await at(session, epoch), EndTally())
    row = await state_of(session, sickness.id)
    assert row.state is LifecycleState.ERADICATED
    ctx = await at(session, 2 + epochs)
    assert sickness.id not in (await DiseaseBook.load(session, ctx.rules, ctx.epoch)).diseases
    session.add(
        OutbreakRow(
            disease_entity_id=sickness.id,
            region_entity_id=world.regions[0].id,
            path=SpreadPath.ORIGIN,
            status=OutbreakStatus.ACTIVE,
            severity=40,
            started_epoch=ctx.epoch,
            locked=[],
        )
    )
    await session.flush()
    await keep_ends(ctx, EndTally())
    assert row.state is LifecycleState.ACTIVE and row.cause is LifecycleCause.RERELEASED


async def test_an_outer_being_with_no_breach_cult_or_interest_is_banished_and_returns_through_the_leak(session: AsyncSession, world: CoreWorld) -> None:
    being = await entity(session, "The Hollow Reach", EntityType.OUTER_BEING, OuterBeingStats(interest=0), world_id=world.world.id)
    await keep_ends(await at(session, 2), EndTally())
    row = await state_of(session, being.id)
    assert row.state is LifecycleState.BANISHED
    world.world.leakage = 100
    await session.flush()
    await keep_ends(await at(session, 3, lifecycle_ends={"return_pct": 100}), EndTally())
    assert row.state is LifecycleState.ACTIVE and row.cause is LifecycleCause.RETURNED
    assert await session.scalar(select(BreachPointRow.id).where(BreachPointRow.outer_entity_id == being.id)) is not None


async def test_a_rite_no_one_casts_falls_dormant_and_a_faded_text_reconstructs_it_corrupted(session: AsyncSession, world: CoreWorld) -> None:
    caster = await mortal(session, "Ilse", world, world.regions[0].id)
    rite = await entity(session, "Ember Call", EntityType.RITE, RiteStats(), world_id=world.world.id)
    kin = await entity(session, "Ash Call", EntityType.RITE, RiteStats(), world_id=world.world.id)
    book = await entity(session, "Notes on Embers", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=world.regions[0].id)
    for item in (rite, kin):
        session.add(
            RiteProfileRow(
                rite_entity_id=item.id, school=MagicSchool.ELEMENTAL_FIRE, source=MagicSource.LEY, requirements={}, cost={}, backlash_chance=10, locked=[]
            )
        )
    session.add(LabTextRow(book_entity_id=book.id, rite_entity_id=rite.id, fidelity=0, locked=[]))
    await session.flush()
    window = tuned_rules().lifecycle_ends.practice_epochs
    for epoch in range(2, 2 + window):
        await keep_ends(await at(session, epoch, lifecycle_ends={"revival_pct": 0}), EndTally())
    row = await state_of(session, rite.id)
    assert row.state is LifecycleState.DORMANT and row.cause is LifecycleCause.NO_PRACTITIONERS
    session.add(CastingRow(rite_entity_id=kin.id, caster_entity_id=caster.id, epoch=2 + window))
    await session.flush()
    await keep_ends(await at(session, 2 + window, lifecycle_ends={"revival_pct": 100, "corruption_pct": 100}), EndTally())
    profile = await session.get(RiteProfileRow, rite.id)
    assert row.state is LifecycleState.CORRUPTED and row.cause is LifecycleCause.RECONSTRUCTED
    assert profile is not None and profile.backlash_chance == 10 + tuned_rules().lifecycle_ends.corrupted_backlash


async def test_favours_fade_and_die_with_their_debtor_and_a_stale_secret_loses_its_hold(session: AsyncSession, world: CoreWorld) -> None:
    debtor = await mortal(session, "Brann", world, world.regions[0].id)
    creditor = await mortal(session, "Cela", world, world.regions[0].id)
    subject = await mortal(session, "Dov", world, world.regions[0].id)
    favour = FavourRow(owed_by_node_id=debtor.id, owed_to_node_id=creditor.id, magnitude=50, origin=next(iter(FavourOrigin)), created_epoch=1)
    secret = SecretRow(holder_node_id=creditor.id, kind=next(iter(IntrigueSecret)), about_node_id=subject.id, severity=70, known_by=[], locked=[])
    session.add_all([favour, secret])
    await session.flush()
    hook = HookRow(holder_node_id=debtor.id, target_node_id=creditor.id, strength=HookStrength.STRONG, source=HookSource.SECRET, secret_id=secret.id)
    session.add(hook)
    subject.status = EntityStatus.DEAD
    subject.end_epoch = 1
    await session.flush()
    tally = DecayTally()
    await keep_decays(await at(session, 2), tally)
    assert favour.magnitude == 45 and secret.severity == 52 and tally.secrets_staled == 1
    assert hook.strength is HookStrength.WEAK
    debtor.status = EntityStatus.DEAD
    debtor.end_epoch = 1
    await session.flush()
    await keep_decays(await at(session, 3), DecayTally())
    assert await session.scalar(select(FavourRow.id).where(FavourRow.id == favour.id)) is None


async def test_warping_fades_away_from_magic_but_never_below_a_permanent_stage(session: AsyncSession, world: CoreWorld) -> None:
    light = await mortal(session, "Faro", world, world.regions[0].id)
    deep = await mortal(session, "Gwen", world, world.regions[0].id)
    rules = tuned_rules().warping
    session.add_all(
        [
            WarpingRow(node_id=light.id, value=30, stage=1, updated_epoch=1, locked=[]),
            WarpingRow(node_id=deep.id, value=rules.unmoored_at, stage=3, updated_epoch=1, locked=[]),
        ]
    )
    await session.flush()
    tally = WarpTally()
    await warp_world(await at(session, 2), tally)
    shallow = await session.get(WarpingRow, light.id)
    lasting = await session.get(WarpingRow, deep.id)
    assert shallow is not None and lasting is not None
    assert shallow.value == 30 - rules.fade and lasting.value == rules.unmoored_at and tally.faded == 1


async def test_a_world_under_a_dead_star_freezes_dead_and_the_god_can_transfigure_another(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lastlight", world, world.regions[0])
    villager = await mortal(session, "Hale", world, town.id)
    star = await session.get(StarRow, world.world.star_id) if world.world.star_id is not None else None
    assert star is not None
    star.star_type = StarType.BLACK_SUN
    session.add(SkyEventRow(kind=SkyEventKind.BLACK_SUN, epoch=2, world_id=world.world.id, star_id=star.id, text="The star went dark."))
    await session.flush()
    frozen = tuned_rules().world_ends.frozen_epochs
    tally = EndingTally()
    await keep_world_ends(await at(session, 2 + frozen - 1), tally)
    assert tally.frozen == 0
    await keep_world_ends(await at(session, 2 + frozen), tally)
    row = await session.get(WorldEndRow, world.world.id)
    assert row is not None and row.state is WorldEnd.FROZEN_DEAD and row.cause is WorldEndCause.STAR_DEATH and tally.frozen == 1
    assert villager.status is not EntityStatus.CANON and town.status is not EntityStatus.CANON and row.lives_ended >= 2
    changed = await declare_end(await at(session, 9), world.world.id, WorldEnd.TRANSFIGURED, WorldEndCause.BELIEF_DRIFT, WorldType.HOLLOW)
    assert changed.state is WorldEnd.TRANSFIGURED and changed.new_type is WorldType.HOLLOW and world.world.world_type is WorldType.HOLLOW


async def test_a_lost_rite_cannot_be_cast_and_a_destroyed_outer_being_opens_no_breach(session: AsyncSession, world: CoreWorld) -> None:
    caster = await mortal(session, "Ilse", world, world.regions[0].id)
    rite = await entity(session, "Ember Call", EntityType.RITE, RiteStats(), world_id=world.world.id)
    profile = RiteProfileRow(rite_entity_id=rite.id, school=MagicSchool.ELEMENTAL_FIRE, source=MagicSource.LEY, requirements={}, cost={}, locked=[])
    session.add(profile)
    session.add(LifecycleStateRow(holder_entity_id=rite.id, kind=LifecycleKind.RITE, state=LifecycleState.LOST, cause=LifecycleCause.NO_TEXTS, locked=[]))
    being = await entity(session, "The Hollow Reach", EntityType.OUTER_BEING, OuterBeingStats(interest=0), world_id=world.world.id)
    await session.flush()
    ctx = await at(session, 2)
    assert await unmet(ctx, caster, profile) == "no one living knows that rite and no text of it survives"
    await destroy(ctx, being.id)
    with pytest.raises(ValidationFailedError):
        await open_breach(ctx, being.id, world.regions[0].id, 30)


async def test_a_swollen_giant_swallows_its_nearest_world(session: AsyncSession, world: CoreWorld) -> None:
    star = await session.get(StarRow, world.world.star_id) if world.world.star_id is not None else None
    assert star is not None
    star.star_type, star.created_epoch = StarType.RED_GIANT, 0
    world.world.orbit = 0.5
    await session.flush()
    tally = EndingTally()
    await keep_world_ends(await at(session, tuned_rules().world_ends.giant_epochs), tally)
    row = await session.get(WorldEndRow, world.world.id)
    assert row is not None and row.state is WorldEnd.CONSUMED and row.cause is WorldEndCause.STAR_GIANT and tally.ended == 1


async def test_a_world_torn_by_many_rifts_sinks_into_the_void(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    await ensure_ladder(session, ctx.rules)
    dimension = await create_dimension(session, ctx.rules, DimensionDraft("The Other Side", DimensionKind.MIRROR, 0))
    for _ in range(tuned_rules().world_ends.void_rifts):
        session.add(RiftRow(world_id=world.world.id, dimension_id=dimension.id, state=RiftState.OPEN, cause=RiftCause.CONVERGENCE, opened_epoch=1, locked=[]))
    await session.flush()
    await keep_world_ends(ctx, EndingTally())
    row = await session.get(WorldEndRow, world.world.id)
    assert row is not None and row.state is WorldEnd.SUNK_INTO_VOID and row.cause is WorldEndCause.VOID


def test_every_cause_brings_an_end() -> None:
    assert set(CAUSE_END) == set(WorldEndCause)
