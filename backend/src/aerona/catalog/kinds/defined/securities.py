from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.securities import SecurityKind

SECURITY_KIND = total(
    SecurityKind,
    {
        SecurityKind.SHARE: Defined(
            "Share",
            checked_by=("engine.securities.holdings.share_security", "engine.securities.shares.float_shares", "engine.securities.shares.sync_shares"),
            used_by=("db.tables.securities.IssuedSecurityRow", "engine.securities.shares.issue_shares"),
        ),
        SecurityKind.BOND: Defined(
            "Bond",
            checked_by=("engine.securities.bonds.bond_open",),
            used_by=(
                "engine.securities.bonds.issue_bonds",
                "engine.securities.debts.FACE_REPAID",
                "engine.securities.debts.PAID_EACH_EPOCH",
                "engine.securities.debts.mirror_loans",
            ),
        ),
        SecurityKind.ANNUITY: Defined("Annuity", checked_by=(), used_by=("engine.securities.debts.PAID_EACH_EPOCH",)),
        SecurityKind.NOTE: Defined("Note", checked_by=(), used_by=("engine.securities.debts.COUPON_AT_MATURITY", "engine.securities.debts.FACE_REPAID")),
        SecurityKind.FUTURE: Defined("Future", checked_by=("engine.securities.pricing.move_price",), used_by=()),
    },
)
