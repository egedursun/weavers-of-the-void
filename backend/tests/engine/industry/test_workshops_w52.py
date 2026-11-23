from aerona.catalog.goods_traits import WORKSHOP_TRAITS
from aerona.catalog.methods import PROCESS_WORKSHOP, WORKSHOP_PROCESSES, workshop_capacity
from aerona.catalog.production import CHAIN_STEPS, WORKSHOP_LABELS
from aerona.db.tables.economy import WorkshopRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.industry import ProcessKind
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.refining import capacity
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, settlement, tuned

NEW = (WorkshopKind.POTTERY, WorkshopKind.GLASSWORKS, WorkshopKind.DYEWORKS, WorkshopKind.SCRIPTORIUM, WorkshopKind.EVAPORATION_WORKS)


def test_twenty_four_workshops_each_labelled_and_running_its_processes() -> None:
    assert len(WorkshopKind) == 24 and all(kind in WORKSHOP_LABELS and kind in WORKSHOP_TRAITS for kind in NEW)
    assert ProcessKind.FIRING in WORKSHOP_PROCESSES[WorkshopKind.POTTERY] and ProcessKind.FIRING in WORKSHOP_PROCESSES[WorkshopKind.GLASSWORKS]
    assert PROCESS_WORKSHOP[ProcessKind.COPYING] is WorkshopKind.SCRIPTORIUM and PROCESS_WORKSHOP[ProcessKind.EVAPORATING] is WorkshopKind.EVAPORATION_WORKS
    for kind in NEW:
        assert any(step.workshop is kind for step in CHAIN_STEPS)


async def test_a_workshops_capacity_comes_from_its_rule(realm: Realm) -> None:
    town = await settlement(realm, "Kilnsby")
    row = WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.POTTERY, level=2, built_epoch=1)
    step = next(step for step in CHAIN_STEPS if step.key == "fire_pottery")
    plain = context(realm.session)
    doubled = context(realm.session, rules=tuned(Rules(), workshops={"pottery_capacity": 200}))
    assert workshop_capacity(doubled.rules, WorkshopKind.POTTERY) == 200
    assert capacity(doubled, step, row) == 2 * capacity(plain, step, row)
    assert await EconomyBook.load(plain) is not None
