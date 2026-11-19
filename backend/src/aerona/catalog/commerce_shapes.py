from aerona.domain.enums.commerce import LeaseThing, PromotionMedium, ShopForm, SupplyTier

SHOP_TURNOVER_PCT: dict[ShopForm, int] = {
    ShopForm.STALL: 60,
    ShopForm.SHOP: 100,
    ShopForm.HOUSE_TRADE: 50,
    ShopForm.PEDDLER: 70,
    ShopForm.MARKET_HALL: 150,
    ShopForm.WAREHOUSE_OUTLET: 200,
    ShopForm.ORDER_HOUSE: 120,
    ShopForm.NETWORK_STORE: 250,
}

PROMOTION_PULL_PCT: dict[PromotionMedium, int] = {
    PromotionMedium.CRIER: 80,
    PromotionMedium.SIGN: 60,
    PromotionMedium.DISPLAY: 100,
    PromotionMedium.PATRONAGE: 120,
    PromotionMedium.GIFT: 150,
    PromotionMedium.MEDIA: 200,
}

TIER_INCOME_PCT: dict[SupplyTier, int] = {
    SupplyTier.PRODUCER: 60,
    SupplyTier.WHOLESALE: 80,
    SupplyTier.RETAIL: 100,
}

LEASE_UPKEEP_PCT: dict[LeaseThing, int] = {
    LeaseThing.LAND: 50,
    LeaseThing.DWELLING: 100,
    LeaseThing.STRUCTURE: 120,
    LeaseThing.VESSEL: 150,
    LeaseThing.VEHICLE: 110,
    LeaseThing.ITEM: 30,
    LeaseThing.MADE_MIND: 200,
    LeaseThing.ANIMAL: 80,
}
