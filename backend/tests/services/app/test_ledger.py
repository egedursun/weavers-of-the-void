import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import BusyError, ConflictError
from aerona.db.ledger_rows import delta_undo, merge_json
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.rules.registry import Rules
from aerona.services.chronicle import ChronicleWriter
from aerona.services.ledger import Ledger, action_label, summarize_inputs
from aerona.services.notifications import Notifier
from tests.services.app.factories import Cosmos, bond, make_entity, make_son


def make_ledger() -> Ledger:
    return Ledger(ChronicleWriter(Notifier()))


def test_summary_and_labels() -> None:
    assert summarize_inputs({"name": "Ora", "type": "mortal", "reason": "", "text": "x" * 100}) == f"Ora · mortal · {'x' * 80}"
    assert action_label("entity:archive") == "entity archive"


def test_delta_and_merge() -> None:
    assert delta_undo(20, 500, 0) == 500
    assert delta_undo(0, 20, 500) == 0
    assert delta_undo(480, 0, 500) == 0
    merged, ok = merge_json({"population": 120, "magic": 9}, {"population": 100, "magic": 5}, {"population": 150, "magic": 9})
    assert ok
    assert merged == {"population": 100, "magic": 5}


async def test_creator_action_captures_and_undoes_insert(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ledger = make_ledger()
    async with ledger.creator_action(session, "entity:create", ActionKind.CREATE_ENTITY, {"name": "Saltmarsh"}) as handle:
        marsh = await make_entity(session, "Saltmarsh", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
        world.son.essence = 40
    assert handle.entry_id is not None
    view = await ledger.read(session, limit=10)
    assert view.entries[0].entry.input_summary == "Saltmarsh"
    assert any(line.startswith("New entity: Saltmarsh (") for line in view.entries[0].rows)
    result = await ledger.undo(session, rules, handle.entry_id, epoch_running=False)
    assert not result.conflicts
    refreshed = await session.get(EntityRow, marsh.id, populate_existing=True)
    assert refreshed is not None
    assert refreshed.status is EntityStatus.REJECTED
    son = await session.get(SonRow, world.son.id, populate_existing=True)
    assert son is not None
    assert son.essence == 50
    entry = await session.get(LedgerEntryRow, handle.entry_id, populate_existing=True)
    assert entry is not None
    assert entry.undone
    lines = list(await session.scalars(select(ChronicleRow).where(ChronicleRow.kind == ChronicleKind.CREATOR_HAND)))
    assert lines[-1].text.startswith("Aeron's hand: a page was torn from Fate's ledger. Aeron's action (entity create)")
    with pytest.raises(ConflictError):
        await ledger.undo(session, rules, handle.entry_id, epoch_running=False)


async def test_quantity_delta_and_later_text_change(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ledger = make_ledger()
    async with ledger.creator_action(session, "bless", ActionKind.BLESS_ESSENCE) as handle:
        world.son.essence = 500
        world.people.description = "Blessed folk."
    world.son.essence = 480
    world.people.description = "Changed later."
    await session.flush()
    assert handle.entry_id is not None
    result = await ledger.undo(session, rules, handle.entry_id, epoch_running=False)
    son = await session.get(SonRow, world.son.id, populate_existing=True)
    assert son is not None
    assert son.essence == 50
    assert any("description changed later" in conflict for conflict in result.conflicts)


async def test_born_son_is_permanent(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ledger = make_ledger()
    async with ledger.creator_action(session, "summon", ActionKind.SUMMON_SON) as handle:
        child = await make_son(session, "Velarion", world.world.id)
        world.creator.essence -= 30
    assert handle.entry_id is not None
    result = await ledger.undo(session, rules, handle.entry_id, epoch_running=False)
    assert await session.get(SonRow, child.id) is not None
    assert any("born being cannot be undone" in conflict for conflict in result.conflicts)
    assert any("not refunded" in conflict for conflict in result.conflicts)


async def test_bond_insert_closed_and_dependents(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ledger = make_ledger()
    async with ledger.creator_action(session, "entity:create", ActionKind.CREATE_ENTITY) as first:
        well = await make_entity(session, "Deepwell", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
    async with ledger.creator_action(session, "bond", ActionKind.CREATE_ENTITY) as second:
        await bond(session, world.people.id, well.id, BondKind.PROTECTS)
    assert first.entry_id is not None
    assert second.entry_id is not None
    view = await ledger.read(session, limit=10)
    first_view = next(item for item in view.entries if item.entry.id == first.entry_id)
    assert [dependent.id for dependent in first_view.dependents] == [second.entry_id]
    await ledger.undo(session, rules, second.entry_id, epoch_running=False)
    bonds = await BondRepository(session).active_between(world.people.id, well.id, [BondKind.PROTECTS])
    assert bonds == []
    closed = await session.scalar(select(BondRow).where(BondRow.target_node_id == well.id, BondRow.kind == BondKind.PROTECTS))
    assert closed is not None
    assert closed.state is BondState.PAST


async def test_refusal_rolls_back_and_epoch_guard(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ledger = make_ledger()
    son_id = world.son.id
    with pytest.raises(RuntimeError):
        async with ledger.creator_action(session, "fail", ActionKind.CREATE_ENTITY):
            world.son.essence = 1
            await session.flush()
            raise RuntimeError("refused")
    son = await session.get(SonRow, son_id, populate_existing=True)
    assert son is not None
    assert son.essence == 50
    assert await session.scalar(select(LedgerEntryRow)) is None
    with pytest.raises(BusyError):
        await ledger.undo(session, rules, 1, epoch_running=True)


async def test_fate_rejection_undo_and_prune(session: AsyncSession, rules: Rules, world: Cosmos) -> None:
    ledger = make_ledger()
    async with ledger.record(
        session, epoch=1, actor_kind=ActorKind.SON, actor_node_id=world.son.id, actor_name="Ithren", tool="create_place", action_kind=ActionKind.CREATE_ENTITY
    ):
        isle = await make_entity(session, "Brine Isle", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
    result = await ledger.undo_creation(session, rules, isle.id)
    assert result is not None
    refreshed = await session.get(EntityRow, isle.id, populate_existing=True)
    assert refreshed is not None
    assert refreshed.status is EntityStatus.REJECTED
    assert await session.scalar(select(ChronicleRow).where(ChronicleRow.kind == ChronicleKind.CREATOR_HAND)) is None
    assert await ledger.prune(session, rules, 1 + rules.ledger.keep_epochs + 1) == 1
