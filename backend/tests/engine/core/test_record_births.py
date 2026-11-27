from dataclasses import replace
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.node import NodeBirthRow
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.record_keepers import RecordKeeperKind
from aerona.domain.models.calendar import YearWindow
from aerona.domain.models.moment import Moment
from aerona.engine.context import TickContext, phase_window
from aerona.engine.recording.record import record
from aerona.tools.framework.actors import MortalToolRuntime, SonToolRuntime
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.runtime import RuntimeSettings
from tests.engine.core.factories import CoreWorld, mortal


async def test_nothing_happens_to_a_thing_before_it_first_appears(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    maker = await mortal(session, "Orun", world, world.regions[0].id)
    maker.birth_epoch = ctx.epoch - 1
    being = await mortal(session, "Ilse", world, world.regions[0].id)
    being.birth_epoch = ctx.epoch
    first = await record(ctx, "tools.mortal.build_network", roles={IncidentRole.ACTOR: maker.id, IncidentRole.PRODUCT: being.id}, at_moment=Moment(31))
    born = await session.get(NodeBirthRow, being.id)
    assert born is not None and born.year == 31 and first.row.year == 31
    assert await session.get(NodeBirthRow, maker.id) is None
    early = replace(ctx, environment=replace(ctx.environment, window=YearWindow(start=0, end=5)))
    later = await record(early, "record_keeper.recovered", roles={IncidentRole.SUBJECT: being.id}, facts={"kind": RecordKeeperKind.HISTORIAN})
    assert later.row.year is not None and later.row.year >= 31


async def test_a_god_acts_in_the_gods_turn_and_a_mortal_in_the_mortals_turn_in_the_order_of_their_calls(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    settings = RuntimeSettings(rules=ctx.rules, epoch=ctx.epoch, world_seed=1, lore_language=ctx.environment.lore_language, actor_node_id=world.son.id)
    son = SonToolRuntime(Database("sqlite+aiosqlite://"), settings, [], ToolPorts())
    mortal_runtime = MortalToolRuntime(Database("sqlite+aiosqlite://"), settings, [], ToolPorts())
    spec = MagicMock()
    spec.name = "probe"
    first = son._tick(session, spec).environment
    son._calls = 3
    third = son._tick(session, spec).environment
    assert first.window == phase_window(ctx.rules, EpochPhase.GODS)
    assert mortal_runtime._tick(session, spec).environment.window == phase_window(ctx.rules, EpochPhase.MORTALS)
    assert first.progress is not None and third.progress is not None and 0 < first.progress < third.progress < 1
