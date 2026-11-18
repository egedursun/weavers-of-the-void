from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.domain.enums.record_keepers import RecordKeeperKind


async def mortal_keeper_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    for row in await scope.session.scalars(select(RecordKeeperRow).where(RecordKeeperRow.keeper_entity_id == me.id).order_by(RecordKeeperRow.id)):
        if row.kind is RecordKeeperKind.CHRONICLER:
            found.append(f"you write the chronicle of every age, since age {row.since_epoch}")
            continue
        people = await scope.session.get(EntityRow, row.scope_node_id)
        found.append(f"you write the history of {people.name if people is not None else 'your people'}, since age {row.since_epoch}")
    return found
