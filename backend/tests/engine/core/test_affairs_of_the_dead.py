from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased

from aerona.catalog.affairs import OUTLIVES
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import GriefRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import ENDED_STATUSES
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.lifecycle.affairs import AFFAIRS, BOUND, SEATS
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
        for table, column in (*SEATS, *BOUND):
            count = len(list(await session.scalars(select(table).where(getattr(table, column).in_(gone)))))
            if count:
                left.append(f"{table.__tablename__} held by the ended through {column}: {count}")
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
        mourner, lost = aliased(EntityRow), aliased(EntityRow)
        outlived = list(
            await session.execute(
                select(GriefRow.id)
                .join(mourner, mourner.id == GriefRow.mourner_node_id)
                .join(lost, lost.id == GriefRow.deceased_node_id)
                .where(
                    mourner.status.in_(sorted(ENDED_STATUSES)),
                    func.json_extract(mourner.stats, "$.death_year") < func.json_extract(lost.stats, "$.death_year"),
                )
            )
        )
        died = (
            select(IncidentParticipantRow.node_id)
            .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
            .where(IncidentRow.kind.like("mortal.death%"), IncidentParticipantRow.role == IncidentRole.SUBJECT)
        )
        healthy_dead = list(await session.scalars(select(MortalProfileRow.entity_id).where(MortalProfileRow.entity_id.in_(died), MortalProfileRow.health > 0)))
    assert outlived == [], f"griefs of mourners who died before the one they mourn: {len(outlived)}"
    assert healthy_dead == [], f"the dead still in health: {healthy_dead[:10]}"
    assert left == [], f"open affairs of the dead: {left}"
    assert ties == [], f"open ties of the dead: {sorted(set(ties))}"
