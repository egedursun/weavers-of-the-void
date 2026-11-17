from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.invariants import TYPED, GenericCheck, InvariantSpec, Remedy
from aerona.db.session import Database
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.council_order import DivineSeatRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.economy import CurrencyRow, WorldMaterialRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow
from aerona.db.tables.pantheon import PantheonTieRow, SyncretismRow
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import OrderKind
from aerona.domain.enums.creator import CovenantDuty, CreatorPromise
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin, MoneyForm
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.kinds import GoodCategory, KindConcept
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.services.integrity.invariants import CHECKS, findings, resolve, sweep
from tests.conftest import OpenDatabase
from tests.engine.core.factories import CoreWorld, bond, mortal, seed_core_world, settlement
from tests.engine.core.test_arcana_w15 import foreign_caster

Breaker = Callable[[AsyncSession, CoreWorld], Awaitable[None]]


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "integrity.db")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
async def world(session: AsyncSession) -> CoreWorld:
    return await seed_core_world(session)


async def captor_dies(session: AsyncSession, world: CoreWorld) -> None:
    captor = await mortal(session, "Holder", world, world.regions[0].id)
    held = await mortal(session, "Held", world, world.regions[0].id)
    session.add(CaptiveRow(captive_entity_id=held.id, captor_entity_id=captor.id, status=CaptiveStatus.HELD, taken_epoch=1))
    captor.status, captor.end_epoch = EntityStatus.DEAD, 1


async def order_loses_target(session: AsyncSession, world: CoreWorld) -> None:
    owner = await mortal(session, "Keeper", world, world.regions[0].id)
    orders = InstructionSetRow(owner_entity_id=owner.id, locked=[])
    session.add(orders)
    await session.flush()
    session.add(InstructionOrderRow(set_id=orders.id, kind=OrderKind.GUARD, target_node_id=None, locked=[]))


async def construct_makes_itself(session: AsyncSession, world: CoreWorld) -> None:
    body = await mortal(session, "Vessel", world, world.regions[0].id)
    session.add(ConstructRow(entity_id=body.id, maker_entity_id=body.id, locked=[]))


async def ruler_dies(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Seat", world, world.regions[0])
    ruler = await mortal(session, "Ruler", world, town.id)
    await bond(session, ruler.id, town.id, BondKind.RULES)
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, 1


async def covenant_without_people(session: AsyncSession, world: CoreWorld) -> None:
    keeper = await mortal(session, "Lone", world, world.regions[0].id)
    session.add(CovenantRow(people_entity_id=keeper.id, duty=CovenantDuty.WORSHIP, promise=CreatorPromise.PLENTY, locked=[]))


async def seat_without_god(session: AsyncSession, world: CoreWorld) -> None:
    session.add(DivineSeatRow(god_node_id=world.people.id, locked=[]))


async def tie_without_god(session: AsyncSession, world: CoreWorld) -> None:
    session.add(PantheonTieRow(god_node_id=world.son.id, other_node_id=world.people.id, locked=[]))


async def joining_without_people(session: AsyncSession, world: CoreWorld) -> None:
    god = await foreign_caster(session, world)
    session.add(SyncretismRow(foreign_god_id=god.id, son_id=world.son.id, people_entity_id=world.species.id, locked=[]))


async def holding_without_kind(session: AsyncSession, world: CoreWorld) -> None:
    session.add(KindHoldingRow(concept=KindConcept.GOOD, kind_id=987654, holder_node_id=world.people.id, locked=[]))


async def kind_derived_from_itself(session: AsyncSession, world: CoreWorld) -> None:
    kind = GoodKindRow(name="Loop Bread", category=GoodCategory.GRAIN, world_id=world.world.id, locked=[])
    session.add(kind)
    await session.flush()
    kind.derived_from_id = kind.id


async def kind_out_of_range(session: AsyncSession, world: CoreWorld) -> None:
    session.add(GoodKindRow(name="Dear Salt", category=GoodCategory.MINERAL_SEASONING, world_id=world.world.id, base_value=5000, locked=[]))


async def paper_made_of_metal(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Mint", world, world.regions[0])
    session.add(
        CurrencyRow(issuer_entity_id=town.id, name="Notes", metal=MaterialKind.SILVER, purity=100, supply=0, trust=50, minted_epoch=0, form=MoneyForm.PAPER)
    )


async def genome_with_unknown_allele(session: AsyncSession, world: CoreWorld) -> None:
    holder = await mortal(session, "Odd Blood", world, world.regions[0].id)
    session.add(GenomeRow(holder_node_id=holder.id, genes={"muscle": ["vast", "high"]}, potential={}, likeness={}, marks=[], locked=[]))


async def star_stuff_from_a_town(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Forge", world, world.regions[0])
    session.add(
        WorldMaterialRow(
            world_id=world.world.id,
            origin=MaterialOrigin.STAR,
            source_node_id=town.id,
            family=MaterialFamily.EXOTIC,
            hardness=50,
            toughness=50,
            weight=50,
            edge=50,
            conductivity=50,
            sanctity=0,
            corruption=0,
            rarity=50,
            base_value=10,
            decay=0,
            created_epoch=0,
        )
    )


BREAKERS: dict[str, Breaker] = {
    "genome_alleles": genome_with_unknown_allele,
    "money_metal": paper_made_of_metal,
    "material_source": star_stuff_from_a_town,
    "living_captor": captor_dies,
    "order_target": order_loses_target,
    "maker_not_self": construct_makes_itself,
    "living_ruler": ruler_dies,
    "covenant_people": covenant_without_people,
    "seat_god": seat_without_god,
    "tie_gods": tie_without_god,
    "syncretism_kinds": joining_without_people,
    "holding_kind": holding_without_kind,
    "kind_lineage": kind_derived_from_itself,
    "kind_ranges": kind_out_of_range,
}


@pytest.mark.parametrize("spec", TYPED, ids=lambda spec: spec.key)
async def test_each_invariant_finds_what_breaks_it_and_mends_it(session: AsyncSession, world: CoreWorld, spec: InvariantSpec) -> None:
    key = spec.key
    find, _ = CHECKS[key]
    assert await find(session) == []
    await BREAKERS[key](session, world)
    await session.flush()
    broken = await find(session)
    assert broken
    if spec.remedy is Remedy.REPAIR:
        await sweep(session)
    else:
        for finding in [item for item in await findings(session) if item.invariant == key]:
            await resolve(session, finding)
    assert await find(session) == []


async def test_every_typed_invariant_has_a_breaker() -> None:
    assert {spec.key for spec in TYPED} == set(BREAKERS) == set(CHECKS)


async def test_the_generic_checks_mend_ranges_epochs_and_report_stray_holds(session: AsyncSession, world: CoreWorld) -> None:
    session.add(TechnologyProfileRow(holder_node_id=world.people.id, family=TechFamily.ENERGY, level=3, updated_epoch=500, locked=["level", "nothing_here"]))
    await session.flush()
    swept = await sweep(session)
    assert swept.repaired[GenericCheck.PAST_EPOCHS.value] >= 1
    row = await session.get(TechnologyProfileRow, (world.people.id, TechFamily.ENERGY))
    assert row is not None
    await session.refresh(row)
    assert row.updated_epoch <= world.cosmos.epoch
    stray = [item for item in await findings(session) if item.check is GenericCheck.LOCKED_NAMES and item.table == "technology_profiles"]
    assert stray
    await resolve(session, stray[0])
    await session.refresh(row)
    assert row.locked == ["level"]
