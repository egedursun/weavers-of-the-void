from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.g05_making import KINDS as MAKING
from aerona.catalog.incident_kinds.g06_exchange import KINDS as EXCHANGE
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.culture import ItemHistoryRow
from aerona.db.tables.cycles import IndentureRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import ProcessGroup
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import release_indenture
from aerona.engine.lore.items import broke
from aerona.engine.phases.market import write_off_debt
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, settlement


async def account(session: AsyncSession, kind: str) -> tuple[IncidentRow, dict[IncidentRole, set[int]], dict[str, IncidentFactRow], str]:
    incident = await session.scalar(select(IncidentRow).where(IncidentRow.kind == kind).order_by(IncidentRow.id.desc()).limit(1))
    assert incident is not None
    roles: dict[IncidentRole, set[int]] = {}
    for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id)):
        roles.setdefault(row.role, set()).add(row.node_id)
    facts = {row.key: row for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id))}
    line = await session.get(ChronicleRow, incident.chronicle_id) if incident.chronicle_id is not None else None
    return incident, roles, facts, line.text if line is not None else ""


def test_every_kind_of_making_and_exchange_is_complete_and_in_its_group() -> None:
    assert all(not spec.draft and spec.template and spec.roles for spec in (*MAKING, *EXCHANGE))
    assert {spec.group for spec in MAKING} == {ProcessGroup.MAKING}
    assert {spec.group for spec in EXCHANGE} == {ProcessGroup.EXCHANGE}


async def test_a_broken_item_is_told_with_its_owner_and_its_story_links_the_happening(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Harrow", world, world.regions[0])
    blade = await entity(session, "Grey Edge", EntityType.ITEM, ItemStats(damage=40), world_id=world.world.id, location_id=town.id)
    await broke(ctx, blade, town.id)
    await session.flush()
    incident, roles, _, text = await account(session, "item.broken")
    assert roles[IncidentRole.SUBJECT] == {blade.id} and roles[IncidentRole.OWNER] == {town.id}
    assert text == "Grey Edge broke and is of no use until mended."
    deed = await session.scalar(select(ItemHistoryRow).where(ItemHistoryRow.item_entity_id == blade.id, ItemHistoryRow.deed == ItemDeed.BROKEN))
    assert deed is not None and deed.incident_id == incident.id


async def test_a_debt_written_off_keeps_who_owed_whom_and_how_much(session: AsyncSession, world: CoreWorld) -> None:
    debtor = await settlement(session, "Low Ford", world, world.regions[0])
    creditor = await settlement(session, "High Ford", world, world.regions[1])
    bond = await BondRepository(session).connect(
        BondDraft(debtor.id, creditor.id, BondKind.OWES, 1, "bought grain on credit", debt_amount=12, debt_what="grain", debt_due_epoch=2)
    )
    told = await write_off_debt(session, Rules(), bond.id)
    _, roles, facts, text = await account(session, "market.written_off")
    assert roles[IncidentRole.BORROWER] == {debtor.id} and roles[IncidentRole.LENDER] == {creditor.id}
    assert facts["owed"].number == 12 and facts["what"].name == "grain"
    assert told == text == "The Creator wrote off the debt of 12 grain that Low Ford owed to High Ford."


async def test_released_labourers_are_counted_in_the_happening(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brack", world, world.regions[0])
    bond = IndentureRow(community_entity_id=town.id, count=7, term_epochs=2, debt=70, exploitation=10, since_epoch=1, locked=[])
    session.add(bond)
    await session.flush()
    await release_indenture(ctx, bond.id)
    incident, roles, facts, text = await account(session, "indenture.released")
    assert roles[IncidentRole.SUBJECT] == {town.id} and incident.place_entity_id == town.id
    assert facts["count"].number == 7 and facts["by_hand"].number == 1
    assert text == "7 bound labourers of Brack went free of their bond."
