from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kinds import KindStance
from aerona.engine.body.customs import people_of
from aerona.engine.kinds.acts import STANCE_TOLD
from aerona.engine.primitives.queries import active_bonds


async def told(scope: Scope, row: KindHoldingRow, holder: str) -> str | None:
    spec = CONCEPTS.get(row.concept)
    kind = await scope.session.get(spec.table, row.kind_id) if spec is not None else None
    if spec is None or kind is None or kind.retired:
        return None
    sort = spec.category_labels[kind.category_key()].lower()
    return f"{holder} {STANCE_TOLD[row.stance]} {kind.name} ({spec.label.lower()}, {sort}; kind {kind.id}, strength {row.strength})"


async def held_lines(scope: Scope, holders: list[int], label: str, limit: int) -> list[str]:
    if not holders or limit <= 0:
        return []
    rows = await scope.session.scalars(
        select(KindHoldingRow).where(KindHoldingRow.holder_node_id.in_(holders)).order_by(KindHoldingRow.strength.desc(), KindHoldingRow.id).limit(limit)
    )
    found = [await told(scope, row, label) for row in rows]
    return [line for line in found if line is not None]


async def mortal_kinds_lines(scope: Scope, me: EntityRow) -> list[str]:
    budget = scope.rules.kinds.context_lines
    people = await people_of(scope.session, me)
    if people is None:
        return []
    own = await held_lines(scope, [people.id], f"the {people.name}", budget)
    partners = [bond.target_node_id for bond in await active_bonds(scope.session, [BondKind.TRADES_WITH], sources=[people.id])]
    mine = set(await scope.session.scalars(select(KindHoldingRow.kind_id).where(KindHoldingRow.holder_node_id == people.id)))
    met = [line for line in await held_lines(scope, partners, "your trading partners", budget) if not any(f"kind {kind_id}," in line for kind_id in mine)]
    return own + met[: max(0, budget - len(own))]


async def son_kinds_lines(scope: Scope, son: SonRow) -> list[str]:
    budget = scope.rules.kinds.context_lines
    own = await held_lines(scope, [son.id], "you", budget)
    if son.current_world_id is None:
        return own
    peoples = list(
        await scope.session.scalars(
            select(EntityRow.id).where(
                EntityRow.world_id == son.current_world_id, EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON
            )
        )
    )
    rows = await scope.session.scalars(
        select(KindHoldingRow)
        .where(KindHoldingRow.holder_node_id.in_(peoples), KindHoldingRow.stance != KindStance.FORBIDS)
        .order_by(KindHoldingRow.strength.desc(), KindHoldingRow.id)
        .limit(max(0, budget - len(own)))
    )
    found = list(own)
    for row in rows:
        people = await scope.session.get(EntityRow, row.holder_node_id)
        line = await told(scope, row, f"the {people.name}" if people is not None else "a people")
        if line is not None:
            found.append(line)
    return found
