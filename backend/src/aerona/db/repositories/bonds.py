from collections.abc import Iterable
from dataclasses import dataclass, replace

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm.attributes import instance_state
from sqlalchemy.orm.util import identity_key

from aerona.catalog.bonds import EVENT_BOND_KINDS, UNORDERED_PAIR_KINDS, bond_spec, endpoints_valid, should_swap
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.bond_index import bond_lookup
from aerona.db.repositories.base import Repository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import BOND_DOWNGRADES, write_blocked
from aerona.domain.enums.bond import ROLE_BOND_KINDS, BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.war import WarCause

PATRON_KINDS = frozenset({NodeKind.SON, NodeKind.CREATOR})
GOD_KINDS = frozenset({NodeKind.SON, NodeKind.CREATOR, NodeKind.FOREIGN_GOD})


@dataclass(frozen=True)
class BondDraft:
    source_node_id: int
    target_node_id: int
    kind: BondKind
    epoch: int
    description: str | None = None
    role: BondRole | None = None
    war_id: int | None = None
    debt_amount: int | None = None
    debt_what: str | None = None
    debt_due_epoch: int | None = None
    debt_currency_id: int | None = None
    truce_until_epoch: int | None = None
    war_cause: WarCause | None = None
    incited_by_son_id: int | None = None

    def swapped(self) -> "BondDraft":
        return replace(self, source_node_id=self.target_node_id, target_node_id=self.source_node_id)


def _pair_filter(first: int, second: int, both_directions: bool) -> ColumnElement[bool]:
    forward = and_(BondRow.source_node_id == first, BondRow.target_node_id == second)
    if not both_directions:
        return forward
    return or_(forward, and_(BondRow.source_node_id == second, BondRow.target_node_id == first))


BOND_KEY = "bonds"
ANCHORED_BOND_KINDS = frozenset({BondKind.OWES, BondKind.PURSUES, BondKind.HOLDS_CAPTIVE, BondKind.PAYS_TRIBUTE})


class BondRepository(Repository):
    async def connect(self, draft: BondDraft) -> BondRow:
        if draft.source_node_id == draft.target_node_id:
            raise ValidationFailedError("A record cannot be bound to itself; choose two different ones.")
        normalized = await self.normalize(draft)
        if normalized.kind not in EVENT_BOND_KINDS:
            existing = await self._find_duplicate(normalized)
            if existing is not None:
                if normalized.kind not in ROLE_BOND_KINDS and normalized.description and normalized.description != existing.description:
                    existing.description = normalized.description
                    await self.flush()
                return existing
        if normalized.kind is BondKind.INSIDE and normalized.role is not BondRole.SPIRIT_BINDING:
            for held in await self.outgoing(normalized.source_node_id, BondKind.INSIDE):
                if held.target_node_id != normalized.target_node_id and held.role is not BondRole.SPIRIT_BINDING:
                    await self.deactivate(held, normalized.epoch)
        guarded = normalized.kind not in ANCHORED_BOND_KINDS and (
            write_blocked(normalized.source_node_id, BOND_KEY) or write_blocked(normalized.target_node_id, BOND_KEY)
        )
        if not guarded:
            await self._apply_side_effects(normalized)
        if normalized.kind is BondKind.OWES and normalized.debt_currency_id is None:
            normalized = replace(normalized, debt_currency_id=await self.debt_coin(normalized.target_node_id, normalized.source_node_id))
        bond = BondRow(
            source_node_id=normalized.source_node_id,
            target_node_id=normalized.target_node_id,
            kind=normalized.kind,
            epoch=normalized.epoch,
            description=normalized.description,
            role=normalized.role,
            war_id=normalized.war_id,
            debt_amount=normalized.debt_amount,
            debt_what=normalized.debt_what,
            debt_due_epoch=normalized.debt_due_epoch,
            debt_currency_id=normalized.debt_currency_id,
            truce_until_epoch=normalized.truce_until_epoch,
            war_cause=normalized.war_cause,
            incited_by_son_id=normalized.incited_by_son_id,
            state=BondState.ACTIVE,
        )
        return bond if guarded else await self.insert(bond)

    async def debt_coin(self, creditor_id: int, debtor_id: int) -> int | None:
        for party_id in (creditor_id, debtor_id):
            party = await self.session.get(EntityRow, party_id)
            homes = [party_id] if party is None else [party_id, party.affiliated_entity_id, party.location_id]
            for home in homes:
                society = await self.session.get(CommunitySocietyRow, home) if home is not None else None
                if society is not None and society.currency_id is not None:
                    return society.currency_id
        return None

    async def normalize(self, draft: BondDraft) -> BondDraft:
        kinds = await NodeRepository(self.session).kinds_of([draft.source_node_id, draft.target_node_id])
        source_kind = kinds.get(draft.source_node_id)
        target_kind = kinds.get(draft.target_node_id)
        if source_kind is None or target_kind is None:
            raise NotFoundError("A bond needs two existing records.")
        result = draft
        if draft.kind is BondKind.WORSHIPS and source_kind is not NodeKind.ENTITY and target_kind is NodeKind.ENTITY:
            result = draft.swapped()
        if source_kind is NodeKind.ENTITY and target_kind is NodeKind.ENTITY:
            types = await self._entity_types([draft.source_node_id, draft.target_node_id])
            subject_type, object_type = types[result.source_node_id], types[result.target_node_id]
            if should_swap(result.kind, subject_type, object_type):
                result = result.swapped()
                subject_type, object_type = object_type, subject_type
            if not endpoints_valid(result.kind, subject_type, object_type):
                downgrades = BOND_DOWNGRADES.get()
                if downgrades is not None:
                    downgrades.append(f"{spoken(result.kind)} from {spoken(subject_type)} to {spoken(object_type)}")
                label = bond_spec(result.kind).label
                description = f"{label}: {result.description}" if result.description else label
                result = replace(result, kind=BondKind.RELATED, description=description)
        return result

    async def deactivate(self, bond: BondRow, epoch: int, reason: str | None = None, state: BondState = BondState.PAST) -> BondRow:
        bond.state = state
        bond.closed_epoch = epoch
        bond.closed_reason = reason
        await self.flush()
        return bond

    async def close_between(self, first: int, second: int, kinds: Iterable[BondKind], epoch: int, reason: str | None = None) -> int:
        bonds = await self.active_between(first, second, kinds)
        for bond in bonds:
            await self.deactivate(bond, epoch, reason)
        return len(bonds)

    async def active_between(self, first: int, second: int, kinds: Iterable[BondKind]) -> list[BondRow]:
        lookup = await bond_lookup(self.session)
        if lookup is not None:
            pairs = {(first, second), (second, first)}
            return [bond for bond in lookup.select(kinds, (BondState.ACTIVE,), [first, second]) if (bond.source_node_id, bond.target_node_id) in pairs]
        statement = select(BondRow).where(_pair_filter(first, second, True), BondRow.kind.in_(list(kinds)), BondRow.state == BondState.ACTIVE)
        return list(await self.session.scalars(statement.order_by(BondRow.id)))

    async def exists_between(self, first: int, second: int, kind: BondKind) -> bool:
        return bool(await self.active_between(first, second, [kind]))

    async def outgoing(self, node_id: int, kind: BondKind | None = None, active_only: bool = True) -> list[BondRow]:
        lookup = await bond_lookup(self.session)
        if lookup is not None:
            return lookup.select([kind] if kind is not None else None, (BondState.ACTIVE,) if active_only else tuple(BondState), [node_id])
        statement = select(BondRow).where(BondRow.source_node_id == node_id)
        if kind is not None:
            statement = statement.where(BondRow.kind == kind)
        if active_only:
            statement = statement.where(BondRow.state == BondState.ACTIVE)
        return list(await self.session.scalars(statement.order_by(BondRow.id)))

    async def incoming(self, node_id: int, kind: BondKind | None = None, active_only: bool = True) -> list[BondRow]:
        lookup = await bond_lookup(self.session)
        if lookup is not None:
            return lookup.select([kind] if kind is not None else None, (BondState.ACTIVE,) if active_only else tuple(BondState), targets=[node_id])
        statement = select(BondRow).where(BondRow.target_node_id == node_id)
        if kind is not None:
            statement = statement.where(BondRow.kind == kind)
        if active_only:
            statement = statement.where(BondRow.state == BondState.ACTIVE)
        return list(await self.session.scalars(statement.order_by(BondRow.id)))

    async def touching(self, node_id: int, states: Iterable[BondState]) -> list[BondRow]:
        statement = select(BondRow).where(or_(BondRow.source_node_id == node_id, BondRow.target_node_id == node_id), BondRow.state.in_(list(states)))
        return list(await self.session.scalars(statement.order_by(BondRow.id)))

    async def patron(self, entity_id: int) -> int | None:
        for bond in await self.outgoing(entity_id, BondKind.WORSHIPS):
            kind = await NodeRepository(self.session).kind_of(bond.target_node_id)
            if kind in PATRON_KINDS:
                return bond.target_node_id
        known = self.session.sync_session.identity_map.get(identity_key(EntityRow, entity_id))
        if isinstance(known, EntityRow) and not instance_state(known).expired:
            return known.creator_son_id
        creator_son_id: int | None = await self.session.scalar(select(EntityRow.creator_son_id).where(EntityRow.id == entity_id))
        return creator_son_id

    async def hide_for_rejection(self, node_id: int, epoch: int) -> int:
        bonds = await self.touching(node_id, [BondState.ACTIVE])
        for bond in bonds:
            await self.deactivate(bond, epoch, None, BondState.HIDDEN_REJECTED)
        return len(bonds)

    async def reopen_after_restore(self, node_id: int) -> int:
        reopened = 0
        for bond in await self.touching(node_id, [BondState.HIDDEN_REJECTED]):
            other = bond.other_end(node_id)
            other_status: EntityStatus | None = await self.session.scalar(select(EntityRow.status).where(EntityRow.id == other))
            if other_status is EntityStatus.REJECTED or not await self._still_located(bond):
                continue
            bond.state = BondState.ACTIVE
            bond.closed_epoch = None
            bond.closed_reason = None
            reopened += 1
        await self.flush()
        return reopened

    async def _still_located(self, bond: BondRow) -> bool:
        if bond.kind is not BondKind.INSIDE or bond.role is BondRole.SPIRIT_BINDING:
            return True
        location: int | None = await self.session.scalar(select(EntityRow.location_id).where(EntityRow.id == bond.source_node_id))
        return location == bond.target_node_id

    async def refresh_location(self, entity_id: int, location_id: int | None, epoch: int) -> BondRow | None:
        for bond in await self.outgoing(entity_id, BondKind.INSIDE):
            if bond.target_node_id != location_id and bond.role is not BondRole.SPIRIT_BINDING:
                await self.deactivate(bond, epoch, None)
        if location_id is None or location_id == entity_id:
            return None
        return await self.connect(BondDraft(entity_id, location_id, BondKind.INSIDE, epoch))

    async def _find_duplicate(self, draft: BondDraft) -> BondRow | None:
        both_directions = draft.kind in UNORDERED_PAIR_KINDS
        statement = select(BondRow).where(
            _pair_filter(draft.source_node_id, draft.target_node_id, both_directions),
            BondRow.kind == draft.kind,
            BondRow.state == BondState.ACTIVE,
        )
        if draft.kind in ROLE_BOND_KINDS:
            statement = statement.where(BondRow.role.is_(None) if draft.role is None else BondRow.role == draft.role)
            statement = statement.where(BondRow.description.is_(None) if draft.description is None else BondRow.description == draft.description)
        found: BondRow | None = await self.session.scalar(statement.order_by(BondRow.id).limit(1))
        return found

    async def _apply_side_effects(self, draft: BondDraft) -> None:
        kinds = await NodeRepository(self.session).kinds_of([draft.source_node_id, draft.target_node_id])
        if kinds.get(draft.source_node_id) is not NodeKind.ENTITY:
            return
        if draft.kind is BondKind.WORSHIPS and kinds.get(draft.target_node_id) in GOD_KINDS:
            await self._replace_patron(draft)
        if kinds.get(draft.target_node_id) is not NodeKind.ENTITY:
            return
        if draft.kind is BondKind.ENEMY:
            await self.close_between(draft.source_node_id, draft.target_node_id, [BondKind.ALLY, BondKind.TRADES_WITH], draft.epoch)
        if draft.kind is BondKind.RULES:
            types = await self._entity_types([draft.source_node_id])
            if types.get(draft.source_node_id) is EntityType.MORTAL:
                await self._dethrone_other_mortals(draft)

    async def _replace_patron(self, draft: BondDraft) -> None:
        current = await self.outgoing(draft.source_node_id, BondKind.WORSHIPS)
        kinds = await NodeRepository(self.session).kinds_of([bond.target_node_id for bond in current])
        for bond in current:
            if bond.target_node_id != draft.target_node_id and kinds.get(bond.target_node_id) in GOD_KINDS:
                await self.deactivate(bond, draft.epoch, None)

    async def _dethrone_other_mortals(self, draft: BondDraft) -> None:
        for bond in await self.incoming(draft.target_node_id, BondKind.RULES):
            if bond.source_node_id == draft.source_node_id:
                continue
            types = await self._entity_types([bond.source_node_id])
            if types.get(bond.source_node_id) is EntityType.MORTAL:
                await self.deactivate(bond, draft.epoch, None)

    async def _entity_types(self, entity_ids: list[int]) -> dict[int, EntityType]:
        rows = await self.session.execute(select(EntityRow.id, EntityRow.entity_type).where(EntityRow.id.in_(entity_ids)))
        return {entity_id: entity_type for entity_id, entity_type in rows}
