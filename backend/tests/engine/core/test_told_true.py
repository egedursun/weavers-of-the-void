from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.chronicle import CHRONICLE_KINDS
from aerona.catalog.titles import title_name
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cycles import GiftRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.sons import SonPowerRow
from aerona.db.tables.titles import TitleHolderRow, TitleProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.chronicle import ChronicleKind, NotificationCategory
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.son import PowerEffect, ReputationLabel
from aerona.domain.enums.titles import TitleTenure, TitleTier
from aerona.domain.models.entity_stats import EventStats, TitleStats
from aerona.engine.cycles.gifts import GiftTally, settle_due
from aerona.engine.divine.grammar import carry_presets
from aerona.engine.gatherings.occasions import coronations
from aerona.engine.phases.sons import keep_divine_mind, wake_or_heal
from aerona.engine.primitives.manual import manual_context
from aerona.prompts.tools.results import SonResult, result
from aerona.services.books.history import son_fate
from tests.engine.core.factories import CoreWorld, entity, mortal, tuned_rules


async def test_a_renamed_member_renames_the_histories_titled_after_it(session: AsyncSession, world: CoreWorld) -> None:
    plague = await entity(session, "Ofjur Plague (Epoch 8)", EntityType.EVENT, EventStats(), world_id=world.world.id)
    row = CollectionRow(kind=CollectionKind.PLAGUE, name="Plague of Ofjur Plague (Epoch 8)", world_id=world.world.id, start_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    session.add(CollectionMemberRow(collection_id=row.id, node_id=plague.id, role=CollectionRole.LEADER, since_epoch=1))
    await session.flush()
    await NameRepository(session).rename(plague.id, "Upcegin")
    assert row.name == "Plague of Upcegin"


def test_a_title_is_named_by_its_plain_rank() -> None:
    assert title_name(TitleTier.GUILD, "Ormedal") == "the headship of Ormedal"
    assert title_name(TitleTier.DISTRICT, "the realm of Kaldren") == "the district title of the realm of Kaldren"


def test_a_tool_result_starts_each_sentence_with_a_capital() -> None:
    assert result(SonResult.MIRACLE_DONE, notes="the land and stores filled", level="") == "The miracle happened. The land and stores filled."


def test_a_change_of_existence_is_filed_as_ascension_not_death() -> None:
    assert CHRONICLE_KINDS[ChronicleKind.EXISTENCE].notification is NotificationCategory.ASCENSION


async def test_a_ruler_who_gains_two_titles_at_once_is_crowned_once(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "crown", tuned_rules())
    ruler = await mortal(session, "Avek", world, None)
    for name in ("the title of Hisolin", "the district title of Hisolin"):
        title = await entity(session, name, EntityType.TITLE, TitleStats(), world_id=world.world.id)
        session.add(TitleProfileRow(title_entity_id=title.id, rank=TitleTier.REALM, locked=[]))
        session.add(TitleHolderRow(title_entity_id=title.id, holder_node_id=ruler.id, tenure=TitleTenure.FOUNDED, since_epoch=ctx.epoch))
    await session.flush()
    assert [occasion.honoured_id for occasion in await coronations(ctx)] == [ruler.id]


async def test_a_gift_owed_by_one_who_died_closes_without_a_line(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "gifts", tuned_rules())
    giver = await mortal(session, "Giver", world, None)
    gone = await mortal(session, "Gone", world, None)
    gone.status, gone.end_epoch = EntityStatus.DEAD, ctx.epoch
    gift = GiftRow(giver_node_id=giver.id, receiver_node_id=gone.id, value=10, occasion=GiftOccasion.COURTESY, due_epoch=ctx.epoch, epoch=ctx.epoch, locked=[])
    session.add(gift)
    await session.flush()
    await settle_due(ctx, GiftTally())
    told = await session.scalar(select(func.count()).select_from(IncidentRow).where(IncidentRow.kind == "gifts.lapsed"))
    assert gift.state is GiftState.LAPSED and told == 0


async def test_a_sealed_power_does_not_wake_before_its_level(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "presets", tuned_rules())
    world.son.level = 1
    session.add(SonPowerRow(son_id=world.son.id, slot=2, name="Late Gift", description="A gift for later.", effect=next(iter(PowerEffect))))
    await session.flush()
    await carry_presets(ctx)
    awake = await session.scalar(select(func.count()).select_from(DivinePowerRow).where(DivinePowerRow.holder_node_id == world.son.id))
    assert awake == 0


async def test_a_son_keeps_its_body_and_mind_in_step_with_itself(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "renewal", tuned_rules())
    session.add(BodyRow(node_id=world.son.id, plan=BodyPlan.HUMANOID, fingers=10, hp_max=1, locked=[]))
    session.add(MindProfileRow(node_id=world.son.id, stability=100, run_epochs=0, updated_epoch=0, locked=[]))
    world.son.sanity = 40
    world.son.birth_epoch = ctx.epoch - 7
    await session.flush()
    await wake_or_heal(ctx, world.son)
    await keep_divine_mind(ctx, world.son)
    body = await session.get(BodyRow, world.son.id)
    mind = await session.get(MindProfileRow, world.son.id)
    assert body is not None and body.hp_max > 1 and world.son.hp <= body.hp_max
    assert mind is not None and mind.stability == 40 and mind.run_epochs == 8 and mind.updated_epoch == ctx.epoch
    await keep_divine_mind(ctx, world.son)
    assert mind.run_epochs == 8


async def test_fate_tells_how_the_son_sees_the_creator(session: AsyncSession, world: CoreWorld) -> None:
    world.son.reputation_label = ReputationLabel.FORGOTTEN
    lines = await son_fate(session, world.son, {})
    assert "Sees the Creator as: a forgotten god" in lines


async def test_fate_tells_when_the_anchor_perished(session: AsyncSession, world: CoreWorld) -> None:
    anchor = await entity(session, "Quayside", EntityType.EVENT, EventStats(), world_id=world.world.id)
    anchor.status, anchor.end_epoch = EntityStatus.DESTROYED, 4
    world.son.anchor_entity_id = anchor.id
    await session.flush()
    lines = await son_fate(session, world.son, {anchor.id: anchor.name})
    assert "Anchor: Quayside (perished in Epoch 4)" in lines
