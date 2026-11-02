from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_undo import UndoRun
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import assignments, creator, diplomacy, god_power
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def _undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    names = label_names(changes, await node_names(session, changes))
    report = await UndoRun(session, epoch, changes, names).run()
    return report.conflicts


async def test_edit_creator_is_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await creator.edit_creator(scope, creator.EditCreator(title="the Weaver"))
    conflicts = await _undo(session, outcome.ledger_entry_id, world.cosmos.epoch)
    assert conflicts == []
    await session.refresh(world.creator)
    assert world.creator.title is None


async def test_deify_undo_keeps_the_born_son(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal = await make_entity(
        session,
        "Asha",
        EntityType.MORTAL,
        world_id=world.world.id,
        stats=MortalStats(hp=40, strength=90, agility=20, intellect=80, charisma=10, age=30, lifespan=70),
    )
    outcome = await god_power.deify_mortal(scope, god_power.EntityTarget(entity_id=mortal.id))
    conflicts = await _undo(session, outcome.ledger_entry_id, world.cosmos.epoch)
    assert any("born being" in item for item in conflicts)
    assert await session.scalar(select(SonRow.id).where(SonRow.id == outcome.values["son_id"])) is not None


async def test_stat_and_alliance_are_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    first_id, second_id, epoch = first.id, second.id, world.cosmos.epoch
    stat = await assignments.set_stat(scope, assignments.SetStat(entity_id=first_id, stat="defense", value=99))
    alliance = await diplomacy.decree(scope, diplomacy.Decree(entity_id=first_id, target_id=second_id, kind=diplomacy.DecreeKind.ALLIANCE))
    assert await _undo(session, alliance.ledger_entry_id, epoch) == []
    assert not await BondRepository(session).exists_between(first_id, second_id, BondKind.ALLY)
    assert await _undo(session, stat.ledger_entry_id, epoch) == []
    restored = await session.scalar(select(EntityRow).where(EntityRow.id == first_id))
    assert restored is not None and restored.stats.model_dump()["defense"] == 40
