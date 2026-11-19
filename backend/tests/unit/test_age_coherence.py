from collections import Counter

from aerona.catalog.crimes import PUNISHMENTS
from aerona.catalog.methods import METHODS
from aerona.catalog.structures import BRANCH_LEVELS
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.mortal import PunishmentKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.world import TechnologyEra
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.industry.methods import founded_past
from aerona.engine.polity.governance import humane_code
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.structures.needs import SiteFacts, founding_order, wanted
from aerona.prompts.schemas.order import order_for, unordered
from aerona.rules.registry import Rules

SITE = 7


def facts(level: int, techniques: frozenset[Technique]) -> SiteFacts:
    site = EntityRow(id=SITE, entity_type=EntityType.PEOPLE, stats=PeopleStats(population=1000, prosperity=50))
    levels = {SITE: dict.fromkeys(KnowledgeBranch, level)}
    return SiteFacts(
        site=site,
        town=None,
        shares={},
        knowledge=KnowledgeMap({SITE: set(KnowledgeBranch)}, levels),
        at_war=False,
        patron=False,
        coastal=False,
        river=False,
        literacy=100,
        capital=False,
        outbreak=False,
        present=Counter(),
        workshops=set(),
        barred=set(),
        techniques=techniques,
    )


def test_a_people_that_knows_electricity_wants_power_and_founds_its_age_first() -> None:
    modern = wanted(Rules(), facts(9, frozenset({Technique.ELECTRICITY})))
    assert StructureKind.POWER_PLANT in modern
    assert StructureKind.POWER_PLANT not in wanted(Rules(), facts(9, frozenset()))
    assert StructureKind.POWER_PLANT not in wanted(Rules(), facts(2, frozenset({Technique.ELECTRICITY})))
    ordered = founding_order(modern)
    ranks = [BRANCH_LEVELS.get(kind, 0) for kind in ordered]
    assert ranks == sorted(ranks, reverse=True) and ordered[0] in BRANCH_LEVELS


def test_a_humane_code_keeps_no_penalty_harsher_than_prison() -> None:
    gaol = PUNISHMENTS[PunishmentKind.IMPRISONMENT].harm
    harms = {spec.word: spec.harm for spec in PUNISHMENTS.values()}
    code = humane_code()
    assert code and all(harms[str(word)] <= gaol for word in code.values())
    assert "death" not in code.values()


def test_choice_lists_follow_no_fixed_order_but_keep_every_choice() -> None:
    schema = {"properties": {"domain": {"type": "string", "enum": [domain.value for domain in Domain]}}}
    orders = {tuple(unordered(schema, order_for(f"prompt {index}"))["properties"]["domain"]["enum"]) for index in range(8)}
    assert len(orders) > 1
    assert all(sorted(order) == sorted(domain.value for domain in Domain) for order in orders)
    assert unordered(schema, order_for("same")) == unordered(schema, order_for("same"))
    firsts = {order[0] for order in orders}
    assert firsts != {Domain.SEA.value}


def test_a_world_that_began_in_an_age_leaves_older_methods_freely_but_pays_for_newer_ones() -> None:
    churning, creamery = METHODS[MethodKind.HAND_CHURNING], METHODS[MethodKind.CREAMERY]
    bloomery, furnace = METHODS[MethodKind.BLOOMERY], METHODS[MethodKind.BLAST_FURNACE]
    assert founded_past(churning, creamery, TechnologyEra.INFORMATION)
    assert not founded_past(churning, creamery, TechnologyEra.IRON)
    assert not founded_past(bloomery, furnace, TechnologyEra.IRON)
