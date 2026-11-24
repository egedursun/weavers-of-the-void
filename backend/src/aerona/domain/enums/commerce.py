from enum import StrEnum


class ShopForm(StrEnum):
    STALL = "stall"
    SHOP = "shop"
    HOUSE_TRADE = "house_trade"
    PEDDLER = "peddler"
    MARKET_HALL = "market_hall"
    WAREHOUSE_OUTLET = "warehouse_outlet"
    ORDER_HOUSE = "order_house"
    NETWORK_STORE = "network_store"


class SupplyTier(StrEnum):
    PRODUCER = "producer"
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    BROKER = "broker"
    PEDDLER = "peddler"


class PromotionMedium(StrEnum):
    CRIER = "crier"
    SIGN = "sign"
    DISPLAY = "display"
    PATRONAGE = "patronage"
    GIFT = "gift"
    MEDIA = "media"


class LeaseThing(StrEnum):
    LAND = "land"
    DWELLING = "dwelling"
    STRUCTURE = "structure"
    VESSEL = "vessel"
    VEHICLE = "vehicle"
    ITEM = "item"
    MADE_MIND = "made_mind"
    ANIMAL = "animal"


class LeaseUpkeep(StrEnum):
    OWNER = "owner"
    LESSEE = "lessee"
    SHARED = "shared"


class LeaseDefault(StrEnum):
    EVICTION = "eviction"
    COURT = "court"
    DEBT = "debt"
