from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.economy import CommodityKind, LoanStatus
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.domain.enums.orders import SavingForm
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.urban import MarketPlay

C = CommodityKind

ILLEGAL_GOODS: MappingProxyType[LawKind, tuple[CommodityKind, ...]] = MappingProxyType(
    {LawKind.MAGIC_BAN: (C.MAGICAL_REAGENTS,), LawKind.WORSHIP_BAN: (C.SACRED_GOODS, C.INCENSE)}
)
STAPLES = frozenset({C.GRAIN, C.BREAD, C.FISH, C.LIVESTOCK, C.FODDER, C.FUEL, C.TIMBER})
LUXURIES = frozenset({C.LUXURIES, C.INCENSE, C.SACRED_GOODS, C.MAGICAL_REAGENTS, C.MOUNTS})
FOOD_HOARDS = (C.GRAIN, C.BREAD)
POLICY_LABELS: MappingProxyType[TradePolicyKind, str] = MappingProxyType(
    {
        TradePolicyKind.TARIFF: "Tariff",
        TradePolicyKind.SUBSIDY: "Subsidy",
        TradePolicyKind.EMBARGO: "Embargo",
        TradePolicyKind.QUOTA: "Quota",
        TradePolicyKind.LICENCE: "Licence",
        TradePolicyKind.PRICE_CONTROL: "Price control",
        TradePolicyKind.FREE_TRADE: "Free trade",
        TradePolicyKind.EXPORT_BAN: "Export ban",
        TradePolicyKind.SANCTION: "Sanction",
    }
)
CREDIT_LABELS: MappingProxyType[CreditState, str] = MappingProxyType(
    {
        CreditState.NORMAL: "Sound",
        CreditState.STRAINED: "Strained",
        CreditState.DEFAULT: "In default",
        CreditState.RESTRUCTURING: "Restructuring",
        CreditState.RESCUED: "Rescued",
        CreditState.REPUDIATED: "Repudiated its debts",
    }
)
SPECULATION_LABELS: MappingProxyType[SpeculationStatus, str] = MappingProxyType(
    {SpeculationStatus.HOARDING: "Hoarding", SpeculationStatus.SOLD: "Sold", SpeculationStatus.BUST: "Bust", SpeculationStatus.SEIZED: "Seized"}
)


@dataclass(frozen=True)
class LoanSpec:
    label: str
    owed: bool
    lender_loses: bool = False


LOAN_STATES = total(
    LoanStatus,
    {
        LoanStatus.OPEN: LoanSpec("Open", True),
        LoanStatus.REPAID: LoanSpec("Repaid", False),
        LoanStatus.DEFAULTED: LoanSpec("Defaulted", False, True),
        LoanStatus.FORGIVEN: LoanSpec("Forgiven", False, True),
        LoanStatus.RESCHEDULED: LoanSpec("Rescheduled", True),
        LoanStatus.COLLATERAL_SEIZED: LoanSpec("Collateral seized", False),
        LoanStatus.SOLD: LoanSpec("Sold to a new lender", True),
    },
)
OWED_LOANS = tuple(status for status, spec in LOAN_STATES.items() if spec.owed)


@dataclass(frozen=True)
class SavingSpec:
    label: str
    kept_in: str | None


SAVING_FORMS = total(
    SavingForm,
    {
        SavingForm.HOARD: SavingSpec("A buried hoard", None),
        SavingForm.DEPOSIT: SavingSpec("A deposit with a bank", None),
        SavingForm.INVESTMENT: SavingSpec("An investment in the town", None),
        SavingForm.LAND: SavingSpec("Land that earns rent", "land"),
        SavingForm.GOODS: SavingSpec("Stored goods and herds", "goods"),
    },
)


@dataclass(frozen=True)
class CoverSpec:
    label: str
    premium_rule: str


COVERS = total(
    InsuranceCover,
    {
        InsuranceCover.CARGO: CoverSpec("Cargo", "cargo_premium_pct"),
        InsuranceCover.HOUSE: CoverSpec("House", "house_premium_pct"),
        InsuranceCover.LIFE: CoverSpec("Life", "life_premium_pct"),
        InsuranceCover.CROP: CoverSpec("Crop", "crop_premium_pct"),
        InsuranceCover.VESSEL: CoverSpec("Vessel", "vessel_premium_pct"),
        InsuranceCover.LIVESTOCK: CoverSpec("Livestock", "livestock_premium_pct"),
    },
)
TOWN_COVERS = (InsuranceCover.CARGO, InsuranceCover.HOUSE, InsuranceCover.CROP, InsuranceCover.LIVESTOCK, InsuranceCover.VESSEL)


@dataclass(frozen=True)
class PlaySpec:
    label: str
    by_rumour: bool


PLAYS = total(
    MarketPlay,
    {
        MarketPlay.CORNER: PlaySpec("Cornering the market", False),
        MarketPlay.DUMP: PlaySpec("Dumping stock", False),
        MarketPlay.RUMOUR: PlaySpec("Spreading a false report", True),
    },
)
