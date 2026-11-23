from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.context import TickContext
from aerona.engine.military.parole import ParoleTally, join_captors, keep_paroles, offer_parole
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.war import open_war, take_captive
from aerona.services.integrity.w52_agent_f import oathless_paroles, release_oathless, release_unwed, unwed_joiners
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules


async def war_captive(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> tuple[CaptiveRow, EntityRow, EntityRow, EntityRow]:
    captor = await settlement(session, "Brack", world, world.regions[0])
    home = await settlement(session, "Hollin", world, world.regions[1])
    captain = await mortal(session, "Captain Ilse", world, home.id)
    war = await open_war(ctx, captor, home)
    row = await take_captive(ctx, captor, captain, war, description="taken at the ford", home_id=home.id)
    return row, captor, home, captain


async def test_a_paroled_captain_goes_home_under_oath_and_breaks_it_when_war_comes_again(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "parole", rules=tuned_rules(captives={"parole_pct": 100, "parole_kept_pct": 0}))
    row, captor, home, captain = await war_captive(session, world, ctx)
    assert await offer_parole(ctx, row, captain, captor, home)
    oath = await session.get(OathRow, row.oath_id)
    assert row.status is CaptiveStatus.PAROLED and oath is not None and oath.kind is OathKind.NONVIOLENCE and oath.recipient_node_id == captor.id
    assert await session.scalar(select(IncidentRow).where(IncidentRow.kind == "captive.paroled")) is not None
    tally = ParoleTally()
    await keep_paroles(ctx, tally)
    assert tally.broken == 1 and oath.status is OathStatus.BROKEN
    grudge = await session.scalar(
        select(MemoryRow).where(MemoryRow.holder_node_id == captor.id, MemoryRow.subject_node_id == captain.id, MemoryRow.kind == MemoryKind.BETRAYED_ME)
    )
    assert grudge is not None and grudge.magnitude < 0


async def test_a_captive_married_in_joins_the_captors_for_good(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "married_in", rules=tuned_rules(captives={"married_in_pct": 100}))
    row, captor, home, captain = await war_captive(session, world, ctx)
    spouse = await mortal(session, "Tove", world, captor.id)
    row.married_entity_id = spouse.id
    await session.flush()
    assert await join_captors(ctx, row, captain, captor, home)
    assert row.status is CaptiveStatus.MARRIED_IN and captain.location_id == captor.id
    assert await session.scalar(select(IncidentRow).where(IncidentRow.kind == "captive.married_in")) is not None


async def test_a_parole_with_no_oath_and_a_joining_with_no_spouse_are_mended(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "mend")
    row, _captor, _home, _captain = await war_captive(session, world, ctx)
    row.status = CaptiveStatus.PAROLED
    await session.flush()
    assert await oathless_paroles(session) == [row.id]
    await release_oathless(session, row.id)
    assert row.status is CaptiveStatus.RELEASED
    row.status = CaptiveStatus.MARRIED_IN
    await session.flush()
    assert await unwed_joiners(session) == [row.id]
    await release_unwed(session, row.id)
    assert row.status is CaptiveStatus.RELEASED
