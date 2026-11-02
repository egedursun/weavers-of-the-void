from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import InsufficientResourcesError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, ThreadRow
from aerona.db.tables.motifs import MotifOverrideMode
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityOrigin, EntityType, MortalRole
from aerona.domain.enums.meta import MotifCategory
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import ExistenceBand, SonRelationLabel
from aerona.domain.models.entity_stats import NaturalLawStats, RegionStats
from aerona.engine.gods.progress import clamp_son, grant_progress, son_max_hp
from aerona.engine.primitives import canon_facts
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.motifs import record_motifs
from aerona.rules.registry import Rules
from aerona.services import empty_worlds, entities, importance, motifs, son_relations, sons, threads
from aerona.services import world as world_service
from aerona.services.bonds import BondService, flip_reversed, link_list, resolve_all_friend_and_foe
from aerona.services.chronicle import ChronicleWriter
from aerona.services.notifications import Notifier
from tests.services.app.factories import Cosmos, bond, make_entity, make_son, make_world


def writer() -> ChronicleWriter:
    return ChronicleWriter(Notifier())


async def test_single_throne_and_companions(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    service = BondService(writer())
    keep = await make_entity(session, "Saltkeep", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    old = await make_entity(session, "Old King", EntityType.MORTAL, world_id=world.world.id, location_id=keep.id, mortal_role=MortalRole.RULER)
    new = await make_entity(session, "New Queen", EntityType.MORTAL, world_id=world.world.id, location_id=keep.id, mortal_role=MortalRole.RULER)
    await service.connect(session, rules, BondDraft(old.id, keep.id, BondKind.RULES, 1))
    await service.connect(session, rules, BondDraft(new.id, keep.id, BondKind.RULES, 1))
    rulers = await BondRepository(session).incoming(keep.id, BondKind.RULES)
    assert [bond.source_node_id for bond in rulers] == [new.id]
    line = await session.scalar(select(ChronicleRow).order_by(ChronicleRow.id.desc()))
    assert line is not None
    assert line.text == "The shared throne over Saltkeep has ended: Old King withdrew from rule, New Queen reigns alone."
    companion = await service.connect(session, rules, BondDraft(world.region.id, new.id, BondKind.COMPANION, 1, description="walked"))
    assert companion.kind is BondKind.RELATED
    assert companion.description == "companion of: walked"


async def test_friend_and_foe_resolution(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    other = await make_entity(session, "Duskfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, world.people.id, other.id, BondKind.ENEMY)
    session.add(BondRow(source_node_id=world.people.id, target_node_id=other.id, kind=BondKind.ALLY, epoch=1))
    await session.flush()
    assert await resolve_all_friend_and_foe(session, rules) == 1
    repository = BondRepository(session)
    enemies = await repository.active_between(world.people.id, other.id, [BondKind.ENEMY])
    allies = await repository.active_between(world.people.id, other.id, [BondKind.ALLY])
    assert len(enemies) + len(allies) == 1


async def test_flip_and_link_list(session: AsyncSession, world: Cosmos) -> None:
    session.add(BondRow(source_node_id=world.region.id, target_node_id=world.people.id, kind=BondKind.LIVES_IN, epoch=1))
    await session.flush()
    assert await flip_reversed(session) == 1
    items = await link_list(session, world.people.id)
    lives = next(item for item in items if item.bond.kind is BondKind.LIVES_IN)
    assert lives.direction == "out"
    assert lives.other_name == "Amberreach"


async def test_entities_tags_origin_and_edit(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    assert entities.resolved_origin(EntityOrigin.SON, None) is EntityOrigin.CREATOR
    assert await entities.resolve_world(session, location_id=world.region.id, creator_son_id=None, maker_entity_id=None) == world.world.id
    assert await entities.add_tags(session, world.people.id, ["Salt", "tide"]) == ["salt", "tide"]
    assert await entities.remove_tags(session, world.people.id, ["salt"]) == ["salt"]
    mortal = await make_entity(session, "Ora", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    edit = entities.EntityEdit(name="Orayne, the Tide Witch", description="Orayne (#4) is a quiet son who sings.", subtype="sea_witch")
    edited = await entities.edit_entity(session, rules, mortal.id, edit)
    assert edited.name == "Orayne"
    assert edited.title == "the Tide Witch"
    assert edited.description == "Orayne is a quiet mortal who sings."
    assert edited.subtype == "sea witch"


async def test_canon_facts(session: AsyncSession, world: Cosmos) -> None:
    language = await make_entity(session, "Velari", EntityType.LANGUAGE, world_id=world.world.id)
    await bond(session, world.people.id, language.id, BondKind.SPEAKS)
    await bond(session, world.people.id, world.son.id, BondKind.WORSHIPS)
    assert await canon_facts.seed_if_empty(session) == 3
    facts = await canon_facts.facts_about(session, world.people.id, 10)
    assert {fact.predicate for fact in facts} == {"is located in", "speaks", "worships"}
    assert await canon_facts.certain_facts(session, [world.people.id]) == 0
    manual = await canon_facts.add_manual_fact(session, canon_facts.FactDraft(world.people.id, "fears", object_text="the deep"), 1)
    retracted = await canon_facts.retract_fact(session, manual.id)
    assert not retracted.active


async def test_threads(session: AsyncSession, world: Cosmos) -> None:
    older = ThreadRow(text="Who drowned the bell?", status=ThreadStatus.CLOSED, epoch=1, closed_epoch=2)
    open_one = ThreadRow(text="Who will ring it?", status=ThreadStatus.OPEN, epoch=2)
    session.add_all([older, open_one])
    await session.flush()
    assert [thread.id for thread in await threads.list_threads(session)] == [open_one.id, older.id]


async def test_son_relations_and_progress(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    rival = await make_son(session, "Vessa", world.world.id)
    relation = await son_relations.set_relation(session, rules, world.son.id, rival.id, value=-70, note="old feud")
    assert relation.label is SonRelationLabel.HATRED
    relation = await son_relations.change_relation(session, rules, rival.id, world.son.id, delta=50)
    assert relation.value == -20
    assert relation.note == "old feud"
    assert relation.label is SonRelationLabel.DISTANCE
    assert len(await son_relations.all_relations(session, rules)) == 1
    son = world.son
    progress = await grant_progress(await manual_context(session, "test", rules), son, xp=350, fame=4)
    assert [step.level for step in progress.level_ups] == [2, 3]
    assert son.level == 3
    assert son.xp == 50
    assert sons.action_points(rules, son, []) == 3
    son.existence = 20
    assert sons.band(rules, son) is ExistenceBand.FADED
    assert sons.action_points(rules, son, []) == 2
    son.existence = 5
    assert not sons.can_act(rules, son)
    assert sons.action_points(rules, son, []) == 0
    son.hp = 10_000
    clamp_son(rules, son)
    assert son.hp == son_max_hp(rules, son)
    stats = sons.summoned_stats(rules, Rarity.RARE, SeededRandom.for_epoch(1, 1, "summon"))
    assert all(1 <= value <= 100 for value in stats.as_dict().values())
    assert sons.existence_target(rules, faith=200, fame=200, anchor_alive=True, has_worshippers=True) == 100


async def test_world_essence_and_laws(session: AsyncSession, world: Cosmos) -> None:
    assert await world_service.spend_essence(session, 40, "costs.revelation") == 40
    with pytest.raises(InsufficientResourcesError, match=r"costs\.summon costs 500"):
        await world_service.spend_essence(session, 500, "costs.summon")
    assert await world_service.refund_essence(session, 40) == 150
    assert await world_service.gain_essence(session, -1000) == 0
    other = await make_world(session, "Dusk")
    law = await make_entity(session, "Law of Tides", EntityType.NATURAL_LAW, world_id=world.world.id, stats=NaturalLawStats())
    cosmic = await make_entity(session, "Law of Stars", EntityType.NATURAL_LAW, world_id=other.id, stats=NaturalLawStats(), origin=EntityOrigin.COSMOS)
    visible = await world_service.visible_laws(session, world.world.id)
    assert [entity.id for entity in visible] == [law.id, cosmic.id]
    removed = await world_service.reset_world(session)
    assert removed > 0
    assert await session.scalar(select(EntityRow.id)) is None


async def test_empty_worlds(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    other = await make_world(session, "Dusk")
    await make_entity(session, "Ashfield", EntityType.REGION, world_id=other.id, stats=RegionStats(fertility=90))
    await make_entity(session, "Barren", EntityType.REGION, world_id=other.id, stats=RegionStats(fertility=5))
    found = await empty_worlds.empty_worlds(session, rules, 4)
    assert [item.name for item in found] == ["Dusk"]
    assert [region.name for region in found[0].regions] == ["Ashfield"]
    assert found[0].empty_epochs == 3
    assert await empty_worlds.has_living(session, world.world.id)


async def test_importance_and_archive(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    event = await make_entity(session, "Old Flood", EntityType.EVENT, world_id=world.world.id, location_id=world.region.id, birth_epoch=1)
    infos = await importance.compute(session, rules, 10)
    assert infos[event.id].archived
    assert infos[event.id].reason == "9 epochs without mention"
    assert not infos[world.people.id].archived
    assert await importance.persist(session, rules, 10) > 0
    info = await importance.set_archive_mode(session, rules, 10, event.id, importance.ArchiveMode.ATLAS)
    assert not info.archived
    info = await importance.set_archive_mode(session, rules, 10, world.people.id, importance.ArchiveMode.HISTORY)
    assert info.archived
    missing = await importance.missing_images(session, 5)
    assert missing[0].importance is not None


async def test_motifs_from_tags(session: AsyncSession, world: Cosmos) -> None:
    rules = Rules()
    rules = replace(rules, language=replace(rules.language, motif_min_records=3, motif_min_repeats=2))
    for index in range(4):
        creation = await make_entity(session, f"Salt Shrine {index}", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
        tags: list[tuple[str, MotifCategory | None]] = [("bone", MotifCategory.MATERIAL), ("weeping stone", MotifCategory.PHRASE)]
        if index == 0:
            tags.append(("tide", MotifCategory.IMAGERY))
        await record_motifs(session, creation, tags, 1)
    cache = motifs.MotifCache()
    found = await cache.tired(session, rules, None)
    assert [motif.key for motif in found] == ["bone", "weeping stone"]
    world.cosmos.cosmology = "Bone is sacred here."
    cache.clear()
    assert [motif.key for motif in await cache.tired(session, rules, None)] == ["weeping stone"]
    await motifs.set_override(session, None, "weeping stone", MotifOverrideMode.ALLOWED)
    await motifs.set_override(session, None, "rust", MotifOverrideMode.PINNED)
    context = await cache.context(session, rules, None)
    assert [share.key for share in context.motifs] == ["rust"]
