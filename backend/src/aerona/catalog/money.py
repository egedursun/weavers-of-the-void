from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CurrencyIssuer, MoneyForm
from aerona.domain.enums.entity import EngineKind, EntityType

F = MoneyForm


@dataclass(frozen=True)
class MoneyFormSpec:
    label: str
    hint: str
    uses_metal: bool
    technique: Technique | None
    counterfeit_pct: int
    intrusion: bool


MONEY_FORMS: Mapping[MoneyForm, MoneyFormSpec] = total(
    MoneyForm,
    {
        F.COIN: MoneyFormSpec("Coin", "Struck pieces of metal whose worth rests on their purity", True, Technique.COINAGE, 60, False),
        F.COMMODITY: MoneyFormSpec("Commodity money", "A good that keeps and passes from hand to hand", True, None, 20, False),
        F.TOKEN: MoneyFormSpec("Tokens", "Pieces that stand for worth by the word of their issuer", False, None, 80, False),
        F.PAPER: MoneyFormSpec("Paper money", "Notes printed by an issuer", False, Technique.PRINTING, 100, False),
        F.LEDGER: MoneyFormSpec("Ledger money", "Balances written in the books of an issuer", False, Technique.DOUBLE_ENTRY, 30, False),
        F.NETWORK: MoneyFormSpec("Network money", "Balances kept in a network of made minds or machines", False, Technique.COMPUTATION, 40, True),
        F.REPUTATION: MoneyFormSpec("Reputation", "Standing that others will accept in place of goods", False, None, 10, False),
        F.ENERGY: MoneyFormSpec("Stored energy", "Worth counted in stored energy", False, Technique.ELECTRICITY, 20, True),
        F.ESSENCE_BACKED: MoneyFormSpec("Essence-backed money", "Worth that rests on a source of power", False, None, 30, False),
        F.LABOUR_HOURS: MoneyFormSpec("Labour hours", "Worth counted in hours of work given", False, None, 50, False),
        F.GIFT_TALLY: MoneyFormSpec("Gift tally", "A count of gifts given and owed", False, None, 10, False),
    },
)
REFORMS: tuple[MoneyForm, ...] = (F.PAPER, F.LEDGER, F.NETWORK)


def metal_allowed(form: MoneyForm) -> bool:
    return MONEY_FORMS[form].uses_metal


def issuer_kind_of(entity_type: EntityType, engine_kind: EngineKind | None) -> CurrencyIssuer:
    if entity_type is EntityType.POLITY:
        return CurrencyIssuer.POLITY
    if entity_type is EntityType.CULT:
        return CurrencyIssuer.TEMPLE
    if entity_type is EntityType.FACTION:
        return CurrencyIssuer.BANK if engine_kind is EngineKind.MERCHANT_GUILD else CurrencyIssuer.COMPANY
    return CurrencyIssuer.COMMUNITY
