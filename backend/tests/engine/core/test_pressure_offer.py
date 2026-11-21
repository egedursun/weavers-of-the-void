from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mind import PressureRow
from aerona.domain.enums.mind import PressureKind
from aerona.prompts import MortalToolId
from aerona.rules.registry import Rules
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.mortal.registry import mortal_may_use, mortal_specs, mortal_state
from tests.engine.core.factories import CoreWorld, mortal


async def test_a_mortal_is_offered_easing_a_pressure_only_while_one_weighs_on_them(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    spec = next(item for item in mortal_specs() if item.name == MortalToolId.EASE_PRESSURE.value)
    calm = await mortal(session, "Tamsin Ore", world, None)
    assert not mortal_may_use(spec, calm, rules, await mortal_state(session, rules, calm), ToolPorts())
    session.add(PressureRow(entity_id=calm.id, pressure=next(iter(PressureKind)), value=40))
    await session.flush()
    assert mortal_may_use(spec, calm, rules, await mortal_state(session, rules, calm), ToolPorts())
