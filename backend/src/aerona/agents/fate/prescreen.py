from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import name_similarity_policy
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.prompts.contexts.fate import PrescreenKind, PrescreenWarning


async def unbound(scope: Scope, entity: EntityRow) -> bool:
    statement = select(BondRow.id).where(
        BondRow.state == BondState.ACTIVE,
        BondRow.kind != BondKind.INSIDE,
        (BondRow.source_node_id == entity.id) | (BondRow.target_node_id == entity.id),
    )
    return await scope.session.scalar(statement.limit(1)) is None


async def prescreen(scope: Scope, entity: EntityRow) -> list[PrescreenWarning]:
    fate = scope.rules.fate
    warnings: list[PrescreenWarning] = []
    if await unbound(scope, entity):
        warnings.append(PrescreenWarning(kind=PrescreenKind.UNBOUND))
    if len(entity.description) < fate.prescreen_min_description:
        warnings.append(PrescreenWarning(kind=PrescreenKind.SHORT_DESCRIPTION))
    similar = await NameRepository(scope.session).similar_name(entity.name, name_similarity_policy(scope.rules), ignore_node_id=entity.id)
    if similar:
        warnings.append(PrescreenWarning(kind=PrescreenKind.CONFUSABLE_NAME, other_name=similar))
    son = await scope.session.get(SonRow, entity.creator_son_id) if entity.creator_son_id is not None else None
    if son is not None and entity.domain is not None and entity.power_level >= fate.prescreen_max_off_domain_power and entity.domain not in son.domains:
        warnings.append(PrescreenWarning(kind=PrescreenKind.OFF_DOMAIN_POWER, power_level=entity.power_level, domain=DOMAIN_LABELS[entity.domain]))
    location = await scope.session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
    if location is not None and location.world_id != entity.world_id:
        warnings.append(PrescreenWarning(kind=PrescreenKind.LOCATION_IN_OTHER_WORLD))
    return warnings
