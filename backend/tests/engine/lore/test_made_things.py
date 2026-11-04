from sqlalchemy import select

from aerona.db.tables.culture import (
    ArtworkProfileRow,
    BookContentRow,
    HolderLevelRow,
    HolderTechniqueRow,
    IdeologyAdherentRow,
    ItemEnchantmentRow,
    ItemHistoryRow,
    ItemProfileRow,
    ProphecyConditionRow,
    RiteEffectRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import BattleRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import (
    ArtMedium,
    IdeologyTenet,
    ItemClass,
    ItemDeed,
    MagicSchool,
    ProphecyConsequence,
    ProphecyPredicate,
    ProphecyState,
    RiteEffectKind,
    Technique,
)
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import BattleOutcome, WarCause, WarStatus
from aerona.domain.models.entity_stats import ArtworkStats, EventStats, ItemStats, KnowledgeStats, ProphecyStats
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.lore import art, ideology, items, made_control, prophecy, research, rites
from aerona.engine.lore.arms import best_weapon, held_profiles, wear_in_duel
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, settlement, tuned

RULES = Rules()


async def blade(realm: Realm, owner_id: int, name: str = "Edge") -> int:
    item = await make(realm.session, name, EntityType.ITEM, ItemStats(damage=40), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, owner_id, item.id, BondKind.OWNS)
    return item.id


async def test_items_take_a_class_from_typed_stats_never_from_their_names(realm: Realm) -> None:
    ctx = context(realm.session, RULES)
    named_crown = await make(realm.session, "Crown of Sorrow", EntityType.ITEM, ItemStats(damage=30), world_id=realm.world.id)
    row = await items.profile_of(ctx, named_crown)
    assert row.item_class is ItemClass.BLADE


async def test_a_duel_wears_arms_until_they_break_and_lose_their_use(realm: Realm) -> None:
    hero = await mortal(realm, "Ardo")
    item_id = await blade(realm, hero.id)
    ctx = context(realm.session, tuned(RULES, item_powers={"duel_wear": 50}))
    await items.profile_of(ctx, await realm.session.get_one(EntityRow, item_id))
    await realm.session.flush()
    await wear_in_duel(ctx, hero.id, 2)
    held = await held_profiles(realm.session, hero.id)
    assert held[0].condition == 0
    assert best_weapon(held, RULES.item_wear.broken) is None
    deed = await realm.session.scalar(select(ItemHistoryRow.deed).where(ItemHistoryRow.item_entity_id == item_id, ItemHistoryRow.deed == ItemDeed.BROKEN))
    assert deed is ItemDeed.BROKEN


async def test_enchantments_are_bounded_by_the_material_and_raise_worth(realm: Realm) -> None:
    owner = await mortal(realm, "Ardo")
    item_id = await blade(realm, owner.id)
    ctx = context(realm.session, RULES)
    item = await realm.session.get_one(EntityRow, item_id)
    row = await items.profile_of(ctx, item)
    row.material = "wood"
    realm.session.add(ItemEnchantmentRow(item_entity_id=item_id, effect=RiteEffectKind.WARD, strength=100, since_epoch=1))
    await realm.session.flush()
    book = await MaterialBook.load(realm.session)
    spells = await items.bounded_enchantments(ctx, book, item, row)
    assert spells[0].strength < 100
    assert items.worth(ctx, row, items.props_of(book, item.world_id, row.material), 50) > items.worth(ctx, row, None, 0)


async def test_an_item_given_by_hand_changes_owner_and_records_the_gift(realm: Realm) -> None:
    first, second = await mortal(realm, "Ardo"), await mortal(realm, "Bela")
    item_id = await blade(realm, first.id)
    ctx = context(realm.session, RULES)
    await made_control.transfer(ctx, item_id, second.id, "a gift")
    assert await items.owner_of(ctx, item_id) == second.id
    assert await realm.session.scalar(select(ItemHistoryRow.deed).where(ItemHistoryRow.deed == ItemDeed.GIVEN)) is ItemDeed.GIVEN


async def test_images_are_found_by_their_stored_medium_and_performed_works_fade_without_performers(realm: Realm) -> None:
    town = await settlement(realm, "Ashford")
    ctx = context(realm.session, RULES)
    song = await make(
        realm.session, "The Great Statue", EntityType.ARTWORK, ArtworkStats(renown=50, influence=50), world_id=realm.world.id, location_id=town.id
    )
    await art.profile_of(ctx, song, ArtMedium.SONG)
    statue = await make(realm.session, "A Little Song", EntityType.ARTWORK, ArtworkStats(renown=50, influence=50), world_id=realm.world.id, location_id=town.id)
    await art.profile_of(ctx, statue, ArtMedium.STATUE)
    await realm.session.flush()
    assert [work.id for work in await art.images_in(ctx, town.id)] == [statue.id]
    lost = await make(realm.session, "Lost Lay", EntityType.ARTWORK, ArtworkStats(renown=50), world_id=realm.world.id, location_id=realm.far_region.id)
    row = await art.profile_of(ctx, lost, ArtMedium.SONG)
    assert await art.forgotten(ctx, lost, row)
    assert lost.status is EntityStatus.DESTROYED
    kept = await make(realm.session, "Kept Lay", EntityType.ARTWORK, ArtworkStats(renown=50), world_id=realm.world.id, location_id=realm.far_region.id)
    classic = await art.profile_of(ctx, kept, ArtMedium.SONG)
    classic.canon = True
    assert not await art.forgotten(ctx, kept, classic)


async def test_a_rite_refuses_unmet_requirements_and_a_dispel_undoes_its_ward(realm: Realm) -> None:
    town = await settlement(realm, "Ashford")
    mage = await mortal(realm, "Ilse", location_id=town.id)
    ctx = context(realm.session, RULES)
    rite, row = await rites.design(
        ctx, rites.Design(name="Wall of Wind", school=MagicSchool.WARDING, source=None, power=3, workings=((RiteEffectKind.WARD, 5, None, None),)), mage
    )
    row.requirements = {"ley": True}
    assert await rites.unmet(ctx, mage, row) == "it needs a ley line"
    row.requirements = {}
    casting = await rites.cast(ctx, mage, rite, row, target=None, realms=await RealmBook.load(realm.session), forced=True)
    assert casting is not None
    effects = list(await realm.session.scalars(select(RiteEffectRow.effect).where(RiteEffectRow.rite_entity_id == rite.id)))
    assert effects == [RiteEffectKind.WARD]
    undone = await rites.dispel(ctx, rite.id)
    assert undone is not None and not undone.succeeded


async def test_typed_prophecies_come_true_by_event_and_failure_mocks_the_seer(realm: Realm) -> None:
    seer = await mortal(realm, "Orla")
    ctx = context(realm.session, RULES, epoch=5)
    told = await make(
        realm.session, "The Flood Saying", EntityType.PROPHECY, ProphecyStats(certainty=60), world_id=realm.world.id, birth_epoch=4, maker_entity_id=seer.id
    )
    row = await prophecy.typed_condition(
        ctx,
        told,
        prophecy.Foretelling(predicate=ProphecyPredicate.WITHIN_EPOCHS, event_kind=EngineKind.FLOOD, within_epochs=3, consequence=ProphecyConsequence.OMEN),
    )
    assert row.deadline_epoch == 7
    assert not await prophecy.met(ctx, row.predicate, row.args, told.birth_epoch)
    await make(realm.session, "The Deluge", EntityType.EVENT, EventStats(severity=70), world_id=realm.world.id, birth_epoch=5, engine_kind=EngineKind.FLOOD)
    assert await prophecy.met(ctx, row.predicate, row.args, told.birth_epoch)
    before = stat(seer, "charisma") or 0
    row.seer_entity_id = seer.id
    await prophecy.fail(ctx, row)
    assert row.state is ProphecyState.FAILED
    assert (stat(seer, "charisma") or 0) < before
    assert await realm.session.get(ProphecyConditionRow, told.id) is row


async def test_research_progress_builds_levels_and_books_teach_their_readers(realm: Realm) -> None:
    town = await settlement(realm, "Ashford")
    ctx = context(realm.session, tuned(RULES, research={"book_progress": 40}))
    record = await make(
        realm.session, "Leechcraft", EntityType.KNOWLEDGE, KnowledgeStats(level=4), world_id=realm.world.id, knowledge_branch=KnowledgeBranch.MEDICINE
    )
    level = HolderLevelRow(
        holder_entity_id=town.id, branch=KnowledgeBranch.MEDICINE, level=1, practitioners=0, progress=0, secret=False, updated_epoch=1, locked=[]
    )
    realm.session.add(level)
    book = await make(realm.session, "Herbal", EntityType.ITEM, ItemStats(might=5), world_id=realm.world.id, location_id=town.id)
    await link(realm.session, town.id, book.id, BondKind.OWNS)
    realm.session.add(BookContentRow(book_entity_id=book.id, knowledge_entity_id=record.id, fidelity=50))
    await realm.session.flush()
    assert await research.read_books(ctx) == 1
    assert level.progress == 20
    assert await research.spread_of(ctx) >= 1
    assert (stat(record, "spread") or 0) > 0


async def test_a_secret_branch_does_not_leak_its_techniques_along_the_roads(realm: Realm) -> None:
    first, second = await settlement(realm, "Ashford"), await settlement(realm, "Brindle")
    await link(realm.session, first.id, second.id, BondKind.TRADES_WITH)
    for holder, secret in ((first.id, True), (second.id, False)):
        realm.session.add(
            HolderLevelRow(
                holder_entity_id=holder, branch=KnowledgeBranch.METALLURGY, level=5, practitioners=0, progress=0, secret=secret, updated_epoch=1, locked=[]
            )
        )
    realm.session.add(HolderTechniqueRow(holder_entity_id=first.id, technique=Technique.BRONZE, since_epoch=1, secret=False))
    await realm.session.flush()
    assert await research.diffuse_techniques(context(realm.session, RULES)) == 0


async def test_a_school_is_founded_from_chosen_tenets_and_can_be_suppressed(realm: Realm) -> None:
    town = await settlement(realm, "Ashford")
    sage = await mortal(realm, "Tem", location_id=town.id)
    ctx = context(realm.session, RULES)
    creed = await ideology.found_school(ctx, sage, [IdeologyTenet.RATIONALISM], "The Lamp")
    await realm.session.flush()
    row = await realm.session.get_one(IdeologyAdherentRow, (creed.id, town.id))
    before = row.strength
    assert await ideology.suppress(ctx, creed, None) == 2
    assert row.strength < before
    assert creed.name == "The Lamp"
    assert await realm.session.scalar(select(ArtworkProfileRow)) is None
    assert await realm.session.scalar(select(ItemProfileRow)) is None


async def test_a_rite_of_raising_only_calls_back_the_dead_the_battlefield_left_unraised(realm: Realm) -> None:
    ctx = context(realm.session, tuned(RULES, rites={"raise_dead_pct": 50}), epoch=4)
    first = await settlement(realm, "Ashford")
    second = await settlement(realm, "Coldwater")
    record = await make(realm.session, "War of the Fords", EntityType.EVENT, EventStats(severity=40), world_id=realm.world.id, engine_kind=EngineKind.WAR)
    war = WarRow(event_entity_id=record.id, world_id=realm.world.id, status=WarStatus.ONGOING, cause=WarCause.HOSTILITY, started_epoch=1)
    realm.session.add(war)
    await realm.session.flush()
    battle = BattleRow(
        war_id=war.id,
        epoch=4,
        sequence=1,
        winner_entity_id=first.id,
        loser_entity_id=second.id,
        outcome=BattleOutcome.FIELD_VICTORY,
        gap=5.0,
        winner_losses=100,
        loser_losses=300,
        magic={"raised": 150},
    )
    realm.session.add(battle)
    await realm.session.flush()
    assert await rites.claim_battle_dead(ctx, 500) == 50
    assert battle.magic["raised"] == 200
    assert await rites.claim_battle_dead(ctx, 500) == 0
