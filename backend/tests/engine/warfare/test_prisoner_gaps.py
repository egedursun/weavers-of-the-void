from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.phases.prisoners import prisoners
from aerona.engine.services.war import take_captive
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make, make_ctx, tune

SETTLED = {"ransom_chance": 0, "execution_chance": 0, "captive_defection_chance": 0}


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def hold(
    session: AsyncSession, world_id: int, rules: Rules, agility: int = 40, intellect: int = 40
) -> tuple[CaptiveRow, EntityRow, EntityRow, EntityRow]:
    home = await make(session, "Home", EntityType.PEOPLE, world_id, population=900, wealth=10, prosperity=10)
    captor = await make(session, "Captor", EntityType.PEOPLE, world_id, population=900, wealth=10, prosperity=40)
    hero = await make(session, "Tam", EntityType.MORTAL, world_id, age=30, agility=agility, intellect=intellect)
    await bond(session, hero.id, home.id, BondKind.PROTECTS)
    row = await take_captive(make_ctx(session, rules, epoch=5), captor, hero, None, description="raid", home_id=home.id)
    return row, home, captor, hero


async def test_prisoner_escapes_when_agility_and_intellect_make_escape_certain(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**SETTLED, "escape_agility_divisor": 1, "escape_intellect_divisor": 1})
    row, _, captor, hero = await hold(session, world_id, rules, agility=90, intellect=90)
    await prisoners(make_ctx(session, rules, epoch=6))
    assert row.status is CaptiveStatus.ESCAPED
    assert not await BondRepository(session).exists_between(captor.id, hero.id, BondKind.HOLDS_CAPTIVE)
    assert hero.status is EntityStatus.CANON
    assert "prisoner.escaped" in await keys(session)


async def test_prisoner_stays_held_when_escape_is_impossible(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**SETTLED, "escape_agility_divisor": 100000, "escape_intellect_divisor": 100000})
    row, _, captor, hero = await hold(session, world_id, rules, agility=90, intellect=90)
    await prisoners(make_ctx(session, rules, epoch=6))
    assert row.status is CaptiveStatus.HELD
    assert await BondRepository(session).exists_between(captor.id, hero.id, BondKind.HOLDS_CAPTIVE)
    assert "prisoner.escaped" not in await keys(session)


async def test_new_prisoner_is_not_tested_in_the_epoch_of_capture(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns={**SETTLED, "escape_agility_divisor": 1, "escape_intellect_divisor": 1})
    row, *_ = await hold(session, world_id, rules, agility=90, intellect=90)
    await prisoners(make_ctx(session, rules, epoch=5))
    assert row.status is CaptiveStatus.HELD


async def test_prisoner_is_released_quietly_when_the_captive_is_dead(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns=SETTLED)
    row, _, _, hero = await hold(session, world_id, rules, agility=40, intellect=40)
    await EntityRepository(session).set_status(hero, EntityStatus.DEAD, 5, "died in the cells")
    await prisoners(make_ctx(session, rules, epoch=6))
    assert row.status is CaptiveStatus.RELEASED
    assert "prisoner.freed" not in await keys(session)


async def test_prisoner_is_freed_when_the_captors_scatter(session: AsyncSession, world_id: int) -> None:
    rules = tune(Rules(), campaigns=SETTLED)
    row, _, captor, hero = await hold(session, world_id, rules, agility=40, intellect=40)
    await EntityRepository(session).set_status(captor, EntityStatus.DEAD, 5, "scattered")
    await prisoners(make_ctx(session, rules, epoch=6))
    assert row.status is CaptiveStatus.RELEASED
    assert hero.status is EntityStatus.CANON
    assert "prisoner.freed" in await keys(session)
