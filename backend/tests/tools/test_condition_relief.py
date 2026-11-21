from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.body import ConditionRow
from tests.tools.every_setup import hospital
from tests.tools.every_setup_orders import a_condition
from tests.tools.every_son_tool import plain
from tests.tools.every_tool import Case, complete
from tests.tools.factories import Realm, mortal_toolkit
from tests.tools.test_every_tool import MORTAL_SPECS, PORTS, staged


async def hospital_and_condition(session: AsyncSession, realm: Realm) -> dict[str, int]:
    return {**await hospital(session, realm), **await a_condition(session, realm)}


async def test_seek_cure_seeks_relief_for_a_condition_of_any_cause(database: Database) -> None:
    case = Case(plain(condition_id=lambda _realm, ids: ids["condition"]), hospital_and_condition)
    realm, ids = await staged(database, case)
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=case.action_points, ports=PORTS)
    outcome = await toolkit.runtime.call("seek_cure", complete(MORTAL_SPECS["seek_cure"].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
    async with database.write() as session:
        row = await session.get(ConditionRow, ids["condition"])
        assert row is not None and (row.severity < 2 or "nothing eased" in outcome.text)
