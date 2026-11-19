from sqlalchemy import or_, select

from aerona.catalog.affairs import OUTLIVES
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import ENDED_STATUSES
from aerona.engine.lifecycle.affairs import AFFAIRS
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 2


async def test_nothing_the_dead_held_stays_open_after_their_end(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await simulate(database, EPOCHS, rules=eager(Rules()))
    async with database.read() as session:
        gone = select(EntityRow.id).where(EntityRow.status.in_(sorted(ENDED_STATUSES)))
        left = []
        for affair in AFFAIRS:
            count = len(
                list(
                    await session.scalars(
                        select(affair.row).where(getattr(affair.row, affair.holder).in_(gone), getattr(affair.row, affair.state).in_(list(affair.active)))
                    )
                )
            )
            if count:
                left.append(f"{affair.row.__tablename__} by {affair.holder}: {count}")
        ending = [kind for kind, outlives in OUTLIVES.items() if not outlives]
        ties = list(
            await session.scalars(
                select(BondRow.kind).where(
                    BondRow.state == BondState.ACTIVE,
                    BondRow.kind.in_(ending),
                    or_(BondRow.source_node_id.in_(gone), BondRow.target_node_id.in_(gone)),
                )
            )
        )
    assert left == [], f"open affairs of the dead: {left}"
    assert ties == [], f"open ties of the dead: {sorted(set(ties))}"
