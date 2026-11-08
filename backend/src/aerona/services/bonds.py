from dataclasses import dataclass, replace

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import bond_spec
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import VISIBLE_BOND_STATES, BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMPANION_TYPES, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.war import DebtStatus
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.community_relations import relation
from aerona.engine.services.war_resolution import make_peace
from aerona.rules.registry import Rules
from aerona.services.chronicle import ChronicleLine, ChronicleWriter

FRIENDLY_KINDS = (BondKind.ALLY, BondKind.TRADES_WITH)
COMPANION_NODE_KINDS = frozenset({NodeKind.SON, NodeKind.FOREIGN_GOD})
SHARED_THRONE_TEMPLATE = "bonds.shared_throne_ended"
SHARED_THRONE_TEXT = "The shared throne over {place} has ended: {withdrawn} withdrew from rule, {keeper} reigns alone."
GRUDGE_ENDED = "the grudge died out"
FRIEND_AND_FOE = "friend and foe at once"
OUT = "out"
IN = "in"


@dataclass(frozen=True)
class DebtTerms:
    amount: int | None
    what: str | None
    due_epoch: int | None
    status: DebtStatus | None


@dataclass(frozen=True)
class LinkItem:
    bond: BondRow
    direction: str
    other_node_id: int
    other_kind: NodeKind | None
    other_name: str | None
    debt: DebtTerms | None

    @property
    def active(self) -> bool:
        return self.bond.state is BondState.ACTIVE


def is_visible(bond: BondRow) -> bool:
    return bond.state in VISIBLE_BOND_STATES


async def _entity_types(session: AsyncSession, ids: list[int]) -> dict[int, EntityType]:
    rows = await session.execute(select(EntityRow.id, EntityRow.entity_type).where(EntityRow.id.in_(ids)))
    return {entity_id: entity_type for entity_id, entity_type in rows}


async def companion_endpoints_valid(session: AsyncSession, first: int, second: int) -> bool:
    kinds = await NodeRepository(session).kinds_of([first, second])
    types = await _entity_types(session, [first, second])
    for node_id in (first, second):
        kind = kinds.get(node_id)
        if kind in COMPANION_NODE_KINDS:
            continue
        if kind is not NodeKind.ENTITY or types.get(node_id) not in COMPANION_TYPES:
            return False
    return True


async def _mortal_rulers(session: AsyncSession, target_id: int, except_id: int) -> list[BondRow]:
    rulers = await BondRepository(session).incoming(target_id, BondKind.RULES)
    types = await _entity_types(session, [bond.source_node_id for bond in rulers])
    return [bond for bond in rulers if bond.source_node_id != except_id and types.get(bond.source_node_id) is EntityType.MORTAL]


class BondService:
    def __init__(self, writer: ChronicleWriter) -> None:
        self._writer = writer

    async def connect(self, session: AsyncSession, rules: Rules, draft: BondDraft, *, shared_theme_only: bool = False) -> BondRow:
        if draft.kind is BondKind.COMPANION:
            if shared_theme_only:
                raise ValidationFailedError("A shared theme alone is not companionship.")
            if not await companion_endpoints_valid(session, draft.source_node_id, draft.target_node_id):
                label = bond_spec(BondKind.COMPANION).label
                description = f"{label}: {draft.description}" if draft.description else label
                draft = replace(draft, kind=BondKind.RELATED, description=description)
        repository = BondRepository(session)
        normalized = await repository.normalize(draft)
        displaced = await self._displaced_rulers(session, normalized)
        bond = await repository.connect(normalized)
        if displaced:
            await self._shared_throne_line(session, rules, normalized.target_node_id, normalized.source_node_id, displaced)
        if normalized.kind in FRIENDLY_KINDS:
            await resolve_friend_and_foe(session, rules, normalized.source_node_id, normalized.target_node_id)
        return bond

    async def _displaced_rulers(self, session: AsyncSession, draft: BondDraft) -> list[int]:
        if draft.kind is not BondKind.RULES:
            return []
        types = await _entity_types(session, [draft.source_node_id, draft.target_node_id])
        if types.get(draft.source_node_id) is not EntityType.MORTAL or draft.target_node_id not in types:
            return []
        return [bond.source_node_id for bond in await _mortal_rulers(session, draft.target_node_id, draft.source_node_id)]

    async def _shared_throne_line(self, session: AsyncSession, rules: Rules, place_id: int, keeper_id: int, withdrawn: list[int]) -> None:
        names = await NodeRepository(session).names_of([place_id, keeper_id, *withdrawn])
        text = SHARED_THRONE_TEXT.format(
            place=names.get(place_id, ""),
            withdrawn=", ".join(names.get(node_id, "") for node_id in withdrawn),
            keeper=names.get(keeper_id, ""),
        )
        line = ChronicleLine(kind=ChronicleKind.WORLD, text=text, entity_ids=[place_id, keeper_id, *withdrawn], template_key=SHARED_THRONE_TEMPLATE)
        await self._writer.write(session, rules, line)

    async def enforce_single_throne(self, session: AsyncSession, rules: Rules, epoch: int) -> int:
        statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
        by_target: dict[int, list[BondRow]] = {}
        for bond in await session.scalars(statement):
            by_target.setdefault(bond.target_node_id, []).append(bond)
        closed = 0
        repository = BondRepository(session)
        for target_id, bonds in by_target.items():
            types = await _entity_types(session, [bond.source_node_id for bond in bonds])
            mortal_bonds = [bond for bond in bonds if types.get(bond.source_node_id) is EntityType.MORTAL]
            if len(mortal_bonds) < 2:
                continue
            keeper, withdrawn = mortal_bonds[-1], mortal_bonds[:-1]
            for bond in withdrawn:
                await repository.deactivate(bond, epoch)
            closed += len(withdrawn)
            await self._shared_throne_line(session, rules, target_id, keeper.source_node_id, [bond.source_node_id for bond in withdrawn])
        return closed


async def resolve_friend_and_foe(session: AsyncSession, rules: Rules, first: int, second: int) -> bool:
    repository = BondRepository(session)
    if not await repository.active_between(first, second, [BondKind.ENEMY]):
        return False
    kinds = await NodeRepository(session).kinds_of([first, second])
    if any(kind is not NodeKind.ENTITY for kind in kinds.values()):
        return False
    ctx = await manual_context(session, "bonds.friend_and_foe", rules)
    if await relation(session, rules, first, second) >= 0:
        await make_peace(ctx, first, second, GRUDGE_ENDED)
    else:
        await repository.close_between(first, second, FRIENDLY_KINDS, ctx.epoch, FRIEND_AND_FOE)
    return True


async def resolve_all_friend_and_foe(session: AsyncSession, rules: Rules) -> int:
    enemies = await session.scalars(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    pairs = {tuple(sorted((bond.source_node_id, bond.target_node_id))) for bond in enemies}
    resolved = 0
    for first, second in sorted(pairs):
        if await BondRepository(session).active_between(first, second, FRIENDLY_KINDS):
            resolved += await resolve_friend_and_foe(session, rules, first, second)
    return resolved


async def move_entity(session: AsyncSession, entity_id: int, location_id: int | None, epoch: int) -> EntityRow:
    repository = EntityRepository(session)
    entity = await repository.require_entity(entity_id)
    if location_id is not None:
        await repository.require_entity(location_id)
    return await repository.move(entity, location_id, epoch)


async def flip_reversed(session: AsyncSession) -> int:
    repository = BondRepository(session)
    statement = select(BondRow).where(BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    changed = 0
    for bond in list(await session.scalars(statement)):
        draft = BondDraft(bond.source_node_id, bond.target_node_id, bond.kind, bond.epoch, description=bond.description, role=bond.role)
        normalized = await repository.normalize(draft)
        if (normalized.source_node_id, normalized.target_node_id, normalized.kind) == (bond.source_node_id, bond.target_node_id, bond.kind):
            continue
        bond.source_node_id, bond.target_node_id = normalized.source_node_id, normalized.target_node_id
        bond.kind, bond.description = normalized.kind, normalized.description
        changed += 1
    await session.flush()
    return changed


async def link_list(session: AsyncSession, node_id: int, include_hidden: bool = False) -> list[LinkItem]:
    statement = select(BondRow).where(or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id))
    bonds = [bond for bond in await session.scalars(statement) if include_hidden or is_visible(bond)]
    others = [bond.other_end(node_id) for bond in bonds]
    nodes = NodeRepository(session)
    names = await nodes.names_of(others)
    kinds = await nodes.kinds_of(others)
    items = [
        LinkItem(
            bond=bond,
            direction=OUT if bond.source_node_id == node_id else IN,
            other_node_id=bond.other_end(node_id),
            other_kind=kinds.get(bond.other_end(node_id)),
            other_name=names.get(bond.other_end(node_id)),
            debt=DebtTerms(bond.debt_amount, bond.debt_what, bond.debt_due_epoch, bond.debt_status) if bond.kind is BondKind.OWES else None,
        )
        for bond in bonds
    ]
    return sorted(items, key=lambda item: (item.direction != OUT, not item.active, item.bond.id))
