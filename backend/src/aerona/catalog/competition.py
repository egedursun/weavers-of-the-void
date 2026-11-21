from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.competition import CartelAim, MarketForm

CARTEL_PRICE_WEIGHT: MappingProxyType[CartelAim, int] = total(
    CartelAim,
    {CartelAim.PRICE: 100, CartelAim.QUOTA: 80, CartelAim.TERRITORY: 60, CartelAim.BID_RIGGING: 40},
)
BUYER_POWER_WEIGHT: MappingProxyType[MarketForm, int] = total(
    MarketForm,
    {MarketForm.MANY_SELLERS: 0, MarketForm.FEW_SELLERS: 0, MarketForm.ONE_SELLER: 0, MarketForm.ONE_BUYER: 100, MarketForm.FEW_BUYERS: 50},
)
