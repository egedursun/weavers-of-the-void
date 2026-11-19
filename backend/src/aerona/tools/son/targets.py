from collections.abc import Sequence

from sqlalchemy import select

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.queries import active_bonds
from aerona.prompts.tools.results import SonResult
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.shared_inputs import LinkInput, LinkTarget
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.son.support import ensure_in_reach

BLOCKING_STATES = frozenset({EntityStatus.REJECTED, EntityStatus.DESTROYED})
PLACEABLE_STATES = frozenset({EntityStatus.CANON, EntityStatus.DEAD})
LABEL_SEPARATOR = ", "
CREATION_FORBIDDEN_BONDS = frozenset(
    {
        BondKind.HOLDS_CAPTIVE,
        BondKind.COMMANDS,
        BondKind.PAYS_TRIBUTE,
        BondKind.OWES,
        BondKind.SPY_NETWORK,
        BondKind.TRUCE,
        BondKind.PARTY_TO,
        BondKind.MEMBER_OF,
        BondKind.PASSENGER_OF,
        BondKind.CAPTAIN_OF,
        BondKind.KILLED,
        BondKind.CURSED,
        BondKind.BLESSED,
        BondKind.DESTROYED,
        BondKind.TAMED,
    }
)
SEIZING_BONDS = frozenset({BondKind.OWNS, BondKind.RULES})


async def check_links(call: SonCall, links: Sequence[LinkInput], *, creating: bool = False) -> list[EntityRow]:
    entities: list[EntityRow] = []
    for link in links:
        if creating and link.kind in CREATION_FORBIDDEN_BONDS:
            fail(SonResult.LINK_MECHANICAL, kind=link.kind)
        if (
            creating
            and link.kind in SEIZING_BONDS
            and link.target_kind is LinkTarget.ENTITY
            and await active_bonds(call.session, [link.kind], targets=[link.target_id])
        ):
            fail(SonResult.LINK_SEIZES, id=link.target_id, kind=link.kind)
        if link.target_kind is LinkTarget.SON:
            if await call.session.get(SonRow, link.target_id) is None:
                fail(SonResult.LINK_NO_SIBLING, id=link.target_id)
            continue
        entity = await call.session.get(EntityRow, link.target_id)
        if entity is None:
            fail(SonResult.LINK_NO_RECORD, id=link.target_id)
        if entity.status in BLOCKING_STATES:
            fail(SonResult.LINK_STATE, reason=state_reason(entity, entity.id))
        await ensure_in_reach(call, entity)
        entities.append(entity)
    return entities


def infer_location(linked: Sequence[EntityRow], allowed: frozenset[EntityType]) -> int | None:
    for entity in linked:
        if entity.entity_type in allowed and entity.status in PLACEABLE_STATES:
            return entity.id
    for entity in linked:
        if entity.location_id is not None:
            return entity.location_id
    return None


def type_labels(types: frozenset[EntityType]) -> str:
    return LABEL_SEPARATOR.join(sorted(ENTITY_TYPES[kind].label for kind in types))


async def resolve_location(call: SonCall, entity_type: EntityType, given: int | None, linked: Sequence[EntityRow]) -> EntityRow | None:
    spec = ENTITY_TYPES[entity_type]
    if not spec.containers:
        return None
    location_id = given
    if location_id is None and spec.location_required:
        location_id = infer_location(linked, spec.containers)
    if location_id is not None:
        location = await call.session.get(EntityRow, location_id)
        if location is None or location.status not in PLACEABLE_STATES:
            fail(SonResult.LOCATION_STATE, reason=state_reason(location, location_id))
        if location.entity_type not in spec.containers:
            fail(
                SonResult.LOCATION_TYPE,
                type=spec.label,
                location_type=ENTITY_TYPES[location.entity_type].label,
                allowed=type_labels(spec.containers),
            )
        await ensure_in_reach(call, location)
        return location
    if spec.location_required:
        statement = (
            select(EntityRow)
            .where(EntityRow.entity_type.in_(list(spec.containers)), EntityRow.status == EntityStatus.CANON, EntityRow.world_id == call.world_id)
            .order_by(EntityRow.id.desc())
            .limit(call.rules.son_tools.location_suggestions)
        )
        examples = LABEL_SEPARATOR.join(f"#{entity.id} {entity.name}" for entity in await call.session.scalars(statement))
        fail(SonResult.LOCATION_REQUIRED, type=spec.label, allowed=type_labels(spec.containers), examples=examples)
    return None
