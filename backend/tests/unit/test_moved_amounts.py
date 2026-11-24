from types import SimpleNamespace
from typing import cast

import pytest

from aerona.catalog.incident_kinds.amounts import NEVER_ZERO, ZERO_TOLD, amount_problems
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import fill
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, FactValue, ProcessGroup
from aerona.engine.context import TickContext
from aerona.engine.economy.credit import sell_on_credit
from aerona.engine.recording.record import typed_facts
from aerona.rules.registry import Rules


def test_a_percent_field_reads_as_a_whole_percent() -> None:
    assert fill("moved to {stock:%}", stock=26) == "moved to 26%"
    assert fill("{share:%} of the year", share=0) == "0% of the year"


def test_every_amount_a_template_tells_as_moved_is_listed_once() -> None:
    assert amount_problems(dict(INCIDENT_KINDS)) == []
    assert not NEVER_ZERO & ZERO_TOLD


def test_an_unlisted_moved_amount_is_found() -> None:
    spec = IncidentKindSpec(
        "probe.bought",
        ProcessGroup.EXCHANGE,
        "{buyer} bought {units} at market.",
        roles=(RoleSpec(IncidentRole.BUYER),),
        facts=(FactSpec("units", FactValue.NUMBER, unit=FactUnit.COUNT),),
    )
    assert amount_problems({**INCIDENT_KINDS, spec.key: spec}) == [
        "probe.bought: tells the amount units it moved; list it once in NEVER_ZERO or ZERO_TOLD of catalog/incident_kinds/amounts.py"
    ]


@pytest.mark.parametrize(("key", "fact"), sorted(NEVER_ZERO))
def test_a_happening_that_moved_nothing_is_refused(key: str, fact: str) -> None:
    spec = INCIDENT_KINDS[key]
    declared = spec.fact(fact)
    assert declared is not None
    with pytest.raises(ValidationFailedError, match="cannot be told with no"):
        typed_facts(spec, {fact: 0})


async def test_nothing_delivered_is_never_sold_on_credit() -> None:
    ctx = cast(TickContext, SimpleNamespace(rules=Rules()))
    nobody = EntityRow(id=1, name="Buyer")
    assert not await sell_on_credit(ctx, nobody, nobody, CommodityKind.GRAIN, 0)
