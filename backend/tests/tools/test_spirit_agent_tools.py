from dataclasses import replace

import pytest

from aerona.db.session import Database
from aerona.tools.mortal.registry import SPIRIT_TOOLS
from tests.tools.every_mortal_tool import MORTAL_CASES
from tests.tools.every_setup import spirit
from tests.tools.every_tool import Case, Ids, combined, complete, nothing
from tests.tools.factories import Realm, mortal_toolkit
from tests.tools.test_every_tool import MORTAL_SPECS, PORTS, staged


def by_spirit(_realm: Realm, ids: Ids) -> int:
    return ids["spirit"]


def as_spirit(case: Case) -> Case:
    setup = combined(case.setup, spirit) if case.setup is not nothing else spirit
    return replace(case, setup=setup, actor=by_spirit)


async def test_a_spirit_is_offered_only_the_tools_of_the_speaking_dead(database: Database) -> None:
    _realm, ids = await staged(database, as_spirit(Case()))
    toolkit = await mortal_toolkit(database, ids["spirit"], action_points=6, ports=PORTS)
    assert set(toolkit.catalogue.names) == {tool.value for tool in SPIRIT_TOOLS}


@pytest.mark.parametrize("name", sorted(tool.value for tool in SPIRIT_TOOLS))
async def test_a_spirit_uses_each_of_its_tools(database: Database, name: str) -> None:
    case = as_spirit(MORTAL_CASES[name])
    realm, ids = await staged(database, case)
    toolkit = await mortal_toolkit(database, ids["spirit"], action_points=case.action_points, ports=PORTS)
    outcome = await toolkit.runtime.call(name, complete(MORTAL_SPECS[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
