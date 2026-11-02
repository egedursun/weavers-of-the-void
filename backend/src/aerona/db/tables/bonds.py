from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, event, text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.catalog.bonds import EVENT_BOND_KINDS, SINGULAR_NARRATIVE_KINDS
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.bond import ROLE_BOND_KINDS, SYMMETRIC_BOND_KINDS, BondKind, BondRole, BondState
from aerona.domain.enums.war import DebtStatus, WarCause


def _sql_list(values: frozenset[BondKind]) -> str:
    return ", ".join(f"'{value.value}'" for value in sorted(values))


def _directional_predicate() -> str:
    excluded = EVENT_BOND_KINDS | ROLE_BOND_KINDS | SYMMETRIC_BOND_KINDS
    return f"state = 'active' AND kind NOT IN ({_sql_list(excluded)})"


def _role_predicate() -> str:
    return f"state = 'active' AND kind IN ({_sql_list(ROLE_BOND_KINDS)})"


def _unordered_predicate() -> str:
    return f"state = 'active' AND kind IN ({_sql_list(SYMMETRIC_BOND_KINDS)})"


def _singular_predicate() -> str:
    return f"state = 'active' AND kind IN ({_sql_list(SINGULAR_NARRATIVE_KINDS)})"


def _inside_predicate() -> str:
    return f"state = 'active' AND kind = '{BondKind.INSIDE.value}' AND (role IS NULL OR role <> '{BondRole.SPIRIT_BINDING.value}')"


class BondRow(CreatedAtMixin, Base):
    __tablename__ = "bonds"
    __table_args__ = (
        CheckConstraint("source_node_id <> target_node_id", name="not_self"),
        at_least("epoch", 0),
        CheckConstraint("debt_amount IS NULL OR debt_amount >= 0", name="debt_amount_min"),
        CheckConstraint("kind = 'owes' OR (debt_amount IS NULL AND debt_due_epoch IS NULL AND debt_status IS NULL)", name="debt_only_on_owes"),
        CheckConstraint("kind = 'truce' OR truce_until_epoch IS NULL", name="truce_only_on_truce"),
        CheckConstraint("kind = 'enemy' OR (war_cause IS NULL AND incited_by_son_id IS NULL)", name="war_cause_only_on_enemy"),
        Index("ix_bonds_source", "source_node_id", "kind", "state"),
        Index("ix_bonds_target", "target_node_id", "kind", "state"),
        Index("ix_bonds_pair", "source_node_id", "target_node_id"),
        Index("ix_bonds_pair_reverse", "target_node_id", "source_node_id"),
        Index(
            "ux_bonds_active_state",
            "source_node_id",
            "target_node_id",
            "kind",
            unique=True,
            sqlite_where=text(_directional_predicate()),
        ),
        Index("ux_bonds_active_unordered", "pair_low", "pair_high", "kind", unique=True, sqlite_where=text(_unordered_predicate())),
        Index("ux_bonds_active_singular", "pair_low", "pair_high", "kind", unique=True, sqlite_where=text(_singular_predicate())),
        Index(
            "ux_bonds_active_role",
            "source_node_id",
            "target_node_id",
            "kind",
            "role_key",
            "description_key",
            unique=True,
            sqlite_where=text(_role_predicate()),
        ),
        Index("ux_bonds_active_inside", "source_node_id", unique=True, sqlite_where=text(_inside_predicate())),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[BondKind] = mapped_column(enum_type(BondKind, "kind"))
    description: Mapped[str | None] = mapped_column(Text)
    role: Mapped[BondRole | None] = mapped_column(enum_type(BondRole, "role"))
    epoch: Mapped[int]
    state: Mapped[BondState] = mapped_column(enum_type(BondState, "state"), default=BondState.ACTIVE)
    closed_epoch: Mapped[int | None]
    closed_reason: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"), index=True)
    debt_amount: Mapped[int | None]
    debt_what: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    debt_due_epoch: Mapped[int | None]
    debt_status: Mapped[DebtStatus | None] = mapped_column(enum_type(DebtStatus, "debt_status"))
    truce_until_epoch: Mapped[int | None]
    war_cause: Mapped[WarCause | None] = mapped_column(enum_type(WarCause, "war_cause"))
    incited_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    pair_low: Mapped[int] = mapped_column(default=0)
    pair_high: Mapped[int] = mapped_column(default=0)
    role_key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="")
    description_key: Mapped[str] = mapped_column(Text, default="")

    @property
    def active(self) -> bool:
        return self.state is BondState.ACTIVE

    def other_end(self, node_id: int) -> int:
        return self.target_node_id if self.source_node_id == node_id else self.source_node_id


def _refresh_keys(_mapper: object, _connection: object, bond: BondRow) -> None:
    bond.pair_low = min(bond.source_node_id, bond.target_node_id)
    bond.pair_high = max(bond.source_node_id, bond.target_node_id)
    bond.role_key = bond.role.value if bond.role is not None else ""
    bond.description_key = bond.description or ""


event.listen(BondRow, "before_insert", _refresh_keys)
event.listen(BondRow, "before_update", _refresh_keys)


class BondReviewRow(Base):
    __tablename__ = "bond_reviews"

    bond_id: Mapped[int] = mapped_column(ForeignKey("bonds.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int]
