import re
from dataclasses import dataclass, field

from aerona.catalog.bonds import EVENT_BOND_KINDS, SINGULAR_NARRATIVE_KINDS
from aerona.constants.migration import DUPLICATE_ON_MIGRATION
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import ROLE_BOND_KINDS, SYMMETRIC_BOND_KINDS, BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.war import DebtStatus
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.source import LegacyRow

DIRECTIONAL_EXCLUDED = EVENT_BOND_KINDS | ROLE_BOND_KINDS | SYMMETRIC_BOND_KINDS
BondKey = tuple[object, ...]


@dataclass
class ActiveKeys:
    seen: set[BondKey] = field(default_factory=set)

    def keys(self, bond: BondRow) -> list[BondKey]:
        low, high = min(bond.source_node_id, bond.target_node_id), max(bond.source_node_id, bond.target_node_id)
        found: list[BondKey] = []
        if bond.kind not in DIRECTIONAL_EXCLUDED:
            found.append(("directional", bond.source_node_id, bond.target_node_id, bond.kind))
        if bond.kind in SYMMETRIC_BOND_KINDS:
            found.append(("unordered", low, high, bond.kind))
        if bond.kind in SINGULAR_NARRATIVE_KINDS:
            found.append(("singular", low, high, bond.kind))
        if bond.kind in ROLE_BOND_KINDS:
            found.append(("role", bond.source_node_id, bond.target_node_id, bond.kind, bond.role.value if bond.role else "", bond.description or ""))
        if bond.kind is BondKind.INSIDE and bond.role is not BondRole.SPIRIT_BINDING:
            found.append(("inside", bond.source_node_id))
        return found

    def admit(self, bond: BondRow) -> bool:
        keys = self.keys(bond)
        if any(key in self.seen for key in keys):
            return False
        self.seen.update(keys)
        return True


class BondImporter:
    def __init__(self, context: MigrationContext) -> None:
        self.context = context
        self.vocabulary = context.vocabulary
        texts = context.vocabulary.texts
        self.closed_prefix = texts.closed_prefix
        self.overdue = texts.overdue_marker
        self.debt = re.compile(texts.debt_pattern, re.IGNORECASE)
        self.truce = re.compile(texts.truce_pattern, re.IGNORECASE)
        self.active = ActiveKeys()
        self.dropped_kinds = context.vocabulary.enums["dropped_bond_kind"]

    def _endpoints(self, row: LegacyRow, kind: BondKind) -> tuple[int, int] | None:
        source = self.context.node(row.text("source_kind"), row.integer("source_id"))
        target = self.context.node(row.text("target_kind"), row.integer("target_id"))
        if source is None or target is None:
            return None
        son_code, entity_code = self.vocabulary.code("son"), self.vocabulary.code("entity")
        if kind is BondKind.WORSHIPS and row.text("source_kind") == son_code and row.text("target_kind") == entity_code:
            self.context.report.convert("worship_bonds_flipped")
            return target, source
        return source, target

    def _role(self, kind: BondKind, description: str | None) -> BondRole | None:
        if description is None:
            return None
        table = self.vocabulary.bond_roles.get(kind.value, {})
        english = table.get(description.strip())
        return BondRole(english) if english is not None else None

    def _state(self, row: LegacyRow, description: str | None) -> tuple[BondState, str | None]:
        if row.flag("active"):
            return BondState.ACTIVE, None
        if row.flag("closed_by_rejection"):
            return BondState.HIDDEN_REJECTED, None
        if description is not None and description.startswith(self.closed_prefix):
            reason = description[len(self.closed_prefix) :].strip()
            return BondState.HIDDEN_CLOSED, reason[:KEY_MAX_LENGTH] or None
        return BondState.PAST, None

    def _terms(self, legacy_id: int, bond: BondRow, description: str | None) -> None:
        if description is None:
            return
        if bond.kind is BondKind.OWES:
            match = self.debt.search(description)
            if match is None:
                self.context.report.place_failed("debt terms", f"bond:{legacy_id}", f"could not read {description!r}")
                return
            bond.debt_amount = int(match.group("amount"))
            bond.debt_what = match.group("what").strip()[:KEY_MAX_LENGTH]
            bond.debt_due_epoch = int(match.group("due"))
            if bond.state is BondState.ACTIVE:
                bond.debt_status = DebtStatus.OVERDUE if self.overdue in description else DebtStatus.OPEN
            self.context.report.convert("debts")
        elif bond.kind is BondKind.TRUCE:
            match = self.truce.search(description)
            if match is None:
                self.context.report.place_failed("truce terms", f"bond:{legacy_id}", f"could not read {description!r}")
                return
            bond.truce_until_epoch = int(match.group("until"))
            self.context.report.convert("truces")

    def _rejected_end(self, source: int, target: int) -> bool:
        for node in (source, target):
            facts = self.context.facts(node)
            if facts is not None and facts.status is EntityStatus.REJECTED:
                return True
        return False

    async def run(self) -> None:
        created: list[tuple[int, BondRow, str | None]] = []
        report = self.context.report
        for row in self.context.source.iterate("bonds", ("id",)):
            legacy_id = row.integer("id") or 0
            raw_kind = row.text("kind")
            if raw_kind in self.dropped_kinds:
                report.not_migrated["legacy_past_bonds"] = report.not_migrated.get("legacy_past_bonds", 0) + 1
                continue
            kind = self.vocabulary.decode_as("bond_kind", raw_kind, BondKind)
            if kind is None:
                report.place_failed("bond", f"bond:{legacy_id}", f"unknown kind {raw_kind!r}")
                continue
            endpoints = self._endpoints(row, kind)
            if endpoints is None:
                report.place_failed("bond", f"bond:{legacy_id}", "an endpoint is missing")
                continue
            source, target = endpoints
            if source == target:
                report.place_failed("bond", f"bond:{legacy_id}", "both ends are the same record")
                continue
            description = row.text("description")
            state, reason = self._state(row, description)
            if state in (BondState.ACTIVE, BondState.PAST) and self._rejected_end(source, target):
                state = BondState.HIDDEN_REJECTED
            bond = BondRow(
                source_node_id=source,
                target_node_id=target,
                kind=kind,
                description=description,
                role=self._role(kind, description),
                epoch=max(0, row.integer("epoch") or 0),
                state=state,
                closed_reason=reason,
            )
            if bond.state is BondState.ACTIVE and not self.active.admit(bond):
                bond.state = BondState.PAST
                bond.closed_reason = DUPLICATE_ON_MIGRATION
                report.convert("duplicate_active_bonds_closed")
            created.append((legacy_id, bond, description))
        for legacy_id, bond, description in created:
            self._terms(legacy_id, bond, description)
        self.context.session.add_all([bond for _, bond, _ in created])
        await self.context.session.flush()
        for legacy_id, bond, _ in created:
            self.context.ids.put(LegacyKind.BOND, legacy_id, bond.id)


async def import_bonds(context: MigrationContext) -> None:
    await BondImporter(context).run()
