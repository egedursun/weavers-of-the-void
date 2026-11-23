from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.minds import MIND_PURPOSES
from aerona.catalog.laws import LAW_PARAMS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.made import AugmentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.cosmography import BeingAgenda, BeingKind, BeingPhase, BeingScale, DimensionKind, RiftCause
from aerona.domain.enums.living import LivingCraftStance
from aerona.domain.enums.made import AugmentKind, AugmentMake, AugmentSlot, RealmEntry, SurveillanceFocus
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.minds import MindPurpose, MindUpkeep
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import GiftedAttitude, SourceLawLevel
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.context import TickContext
from aerona.engine.cosmos.beings import create_being, live
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension, ensure_ladder
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import tear_toward
from aerona.engine.living.society import living_stance
from aerona.engine.made.backfill import stance
from aerona.engine.made.kinds import WATCHES
from aerona.engine.primitives.augment_bonus import kind_strength
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int = 3, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "second_pass", rules=tuned_rules(**rules))


async def test_a_slumbering_being_sleeps_until_a_sign_in_the_sky_wakes_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, cosmic_beings={"wake_pct": 100})
    being = await create_being(ctx, BeingKind.ANCIENT_MADE_MIND, world.world, region=world.regions[0])
    profile = await session.get(CosmicBeingProfileRow, being.id)
    assert profile is not None and profile.agenda is BeingAgenda.SLUMBER and profile.scale is BeingScale.REGION
    cosmography = await Cosmography.load(session)
    await live(ctx, cosmography, being, profile)
    assert profile.phase is BeingPhase.DORMANT
    await live(ctx, cosmography, being, profile)
    assert profile.phase is BeingPhase.DORMANT
    session.add(SkyEventRow(kind=next(iter(SkyEventKind)), epoch=ctx.epoch, until_epoch=ctx.epoch, world_id=world.world.id))
    await session.flush()
    await live(ctx, cosmography, being, profile)
    assert profile.phase is BeingPhase.MANIFEST
    woke = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "being.woke"))
    assert woke is not None


async def test_a_being_the_size_of_a_region_troubles_only_the_towns_of_its_region(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, cosmic_beings={"ancient_lore_pct": 0, "ancient_dread": 10})
    near = await settlement(session, "Near", world, world.regions[0])
    far = await settlement(session, "Far", world, world.regions[1])
    for town in (near, far):
        session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, public_order=50, locked=[]))
    being = await create_being(ctx, BeingKind.ANCIENT_MADE_MIND, world.world, region=world.regions[0], phase=BeingPhase.MANIFEST)
    profile = await session.get(CosmicBeingProfileRow, being.id)
    assert profile is not None
    await live(ctx, await Cosmography.load(session), being, profile)
    near_order = await session.get(SettlementProfileRow, near.id)
    far_order = await session.get(SettlementProfileRow, far.id)
    assert near_order is not None and far_order is not None
    assert near_order.public_order == 40 and far_order.public_order == 50


async def test_a_rift_torn_by_a_weapon_of_mass_harm_opens_wider_and_names_its_maker(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    await ensure_ladder(session, ctx.rules)
    await create_dimension(session, ctx.rules, DimensionDraft("The Torn Side", DimensionKind.MIRROR, 0))
    holder = await mortal(session, "Wielder", world, world.regions[0].id)
    rift = await tear_toward(ctx, world.world, world.regions[0], RiftCause.MASS_WEAPON, by_node_id=holder.id)
    assert rift is not None
    assert rift.size == ctx.rules.rifts.open_size + ctx.rules.rifts.mass_weapon_size
    assert rift.opened_by_node_id == holder.id
    bargain = await tear_toward(ctx, world.world, world.regions[1], RiftCause.OUTER_BARGAIN, by_node_id=holder.id)
    assert bargain is not None and bargain.stability == ctx.rules.rifts.open_stability - ctx.rules.rifts.bargain_instability


def test_minds_made_to_fight_or_teach_have_purposes_of_their_own() -> None:
    assert MIND_PURPOSES[MindPurpose.SOLDIER].column == "militia"
    assert MIND_PURPOSES[MindPurpose.SOLDIER].will_pct > MIND_PURPOSES[MindPurpose.SERVANT].will_pct
    assert MIND_PURPOSES[MindPurpose.TEACHER].tends is None
    assert MindUpkeep.ATTENTION.value == "attention"
    assert RealmEntry.DREAM in RealmEntry


async def test_armour_and_life_support_augments_guard_the_body(session: AsyncSession, world: CoreWorld) -> None:
    bearer = await mortal(session, "Plated", world, world.regions[0].id)
    for kind in (AugmentKind.ARMOUR, AugmentKind.LIFE_SUPPORT):
        session.add(
            AugmentRow(
                bearer_node_id=bearer.id,
                slot=AugmentSlot.WHOLE_BODY,
                part=None,
                kind=kind,
                make=AugmentMake.MADE,
                quality=80,
                upkeep=MindUpkeep.MAINTENANCE,
                integration=50,
                strain=0,
                installed_epoch=1,
                locked=[],
            )
        )
    await session.flush()
    assert await kind_strength(session, bearer.id, AugmentKind.ARMOUR) == 40
    assert await kind_strength(session, bearer.id, AugmentKind.LIFE_SUPPORT) == 40


async def test_watching_by_kind_and_tongue_raises_the_grievance_of_a_mixed_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    town = await settlement(session, "Crossroads", world, world.regions[0])
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=10, crime=20, locked=[])
    session.add(profile)
    for name, people in (("One", world.people.id), ("Two", world.language.id)):
        visitor = await mortal(session, name, world, town.id)
        visitor.affiliated_entity_id = people
    await session.flush()
    await WATCHES[SurveillanceFocus.KIND](ctx, town, profile, 100)
    assert profile.unrest > 10 and profile.crime < 20


def test_peoples_lean_toward_the_new_stances_and_laws() -> None:
    lawful = {ValueAxis.KNOWLEDGE: 30, ValueAxis.CRAFTSMANSHIP: 30, ValueAxis.LAW: 30}
    assert living_stance(lawful) is LivingCraftStance.REGULATED
    assert stance({ValueAxis.LAW: 60}).value == "regulated"
    assert set(LAW_PARAMS[LawKind.SOURCE_LAW]["level"].choices) == {level.value for level in SourceLawLevel}
    assert GiftedAttitude.EXPLOITED in GiftedAttitude
