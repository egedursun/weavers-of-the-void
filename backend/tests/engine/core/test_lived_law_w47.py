import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import HolderTechniqueRow, IdeologyAdherentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fortune import FortuneProfileRow
from aerona.db.tables.law_depth import RegistryRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.thin_sections import ConstitutionRow
from aerona.domain.enums.culture import IdeologyTenet, Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.fortune.profiles import keep_fortune
from aerona.engine.law.records import record_events
from aerona.engine.lore import ideology
from aerona.engine.lore.control import create_lore
from aerona.engine.lore.creed_change import keep_constitutions
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at

SOURCE = Path(__file__).resolve().parents[3] / "src" / "aerona"
LONE_HOLDER = re.compile(r"written_code\([^,()]+,\s*\[[\w.]+\]\)")


async def people_realm(session: AsyncSession, world: CoreWorld, town: EntityRow) -> EntityRow:
    polity = await entity(session, "Crown of the Folk", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=town.id,
            core_entity_id=world.people.id,
            legitimacy=50,
            stability=50,
            treasury=4000,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity


async def test_a_realm_takes_the_creed_its_towns_hold_and_writes_a_constitution(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    town = await settlement(session, "Ordel", world, world.regions[0])
    polity = await people_realm(session, world, town)
    creed = await create_lore(
        ctx,
        EntityType.IDEOLOGY,
        name="The Even Path",
        description="",
        world_id=world.world.id,
        location_id=None,
        power=3,
        values={"tenets": [IdeologyTenet.EGALITARIANISM.value]},
    )
    session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=town.id, strength=90))
    await session.flush()
    assert await ideology.adopt(ctx, creed) == 1
    profile = await session.get(PolityProfileRow, polity.id)
    assert profile is not None and profile.ideology_entity_id == creed.id
    assert await keep_constitutions(ctx) == 1
    assert await session.get(ConstitutionRow, polity.id) is not None
    told = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.template_key == "lore.constitution_written"))
    assert told is not None and polity.name in told and creed.name in told


async def test_a_realm_whose_seat_writes_its_law_keeps_a_register_of_births(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    town = await settlement(session, "Ordel", world, world.regions[0])
    polity = await people_realm(session, world, town)
    session.add(HolderTechniqueRow(holder_entity_id=world.people.id, technique=Technique.WRITTEN_LAW, since_epoch=0))
    child = await mortal(session, "Wren", world, town.id, age=0)
    child.birth_epoch = ctx.epoch
    await session.flush()
    assert await record_events(ctx) >= 1
    births = list(await session.scalars(select(RegistryRow).where(RegistryRow.kind == RegistryKind.BIRTH, RegistryRow.holder_entity_id == polity.id)))
    assert [row.subject_entity_id for row in births] == [child.id]


async def test_every_living_mortal_keeps_a_fortune_profile(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    town = await settlement(session, "Ordel", world, world.regions[0])
    one = await mortal(session, "Tamsin", world, town.id)
    await keep_fortune(ctx)
    assert await session.get(FortuneProfileRow, one.id) is not None


def test_no_code_check_asks_a_lone_holder() -> None:
    lone = [f"{path.relative_to(SOURCE)}:{match.group(0)}" for path in SOURCE.rglob("*.py") for match in LONE_HOLDER.finditer(path.read_text(encoding="utf-8"))]
    assert lone == []
