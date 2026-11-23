from pydantic import Field

from aerona.prompts.contexts.base import ContextItem


class CommodityLine(ContextItem):
    label: str
    quantity: int
    quality: int
    lots: list[str] = Field(default_factory=list)
    price: int | None = None
    supply: int | None = None
    demand: int | None = None
    imported: int = 0
    exported: int = 0


class CurrencyLine(ContextItem):
    id: int
    name: str
    metal: str
    purity: int
    trust: int
    supply: int
    issuer: str
    debased: bool = False


class LoanLine(ContextItem):
    id: int
    role: str
    other: str
    principal: int
    owed: int
    interest_pct: int
    due_epoch: int
    status: str
    currency: str = ""
    purpose: str = ""


class DebtLine(ContextItem):
    id: int
    role: str
    other: str
    amount: int
    what: str
    due_epoch: int | None
    status: str
    currency: str = ""


class TollLine(ContextItem):
    region: str
    controller: str
    rate_pct: int
    treasury: str = ""
    held: bool = False


class RouteLine(ContextItem):
    id: int
    name: str
    mode: str
    status: str
    partner: str
    capacity: int
    danger: int
    bandits: int
    beasts: int
    weather: int
    sea: int
    officials: int = 0
    spoilage: int = 0
    pilferage: int = 0
    season_pct: int
    closed_season: str = ""
    carrier: str = ""
    aids: list[str] = Field(default_factory=list)
    convoys: list[str] = Field(default_factory=list)
    length: int
    renown: int
    controller: str = ""
    blockaded_by: str = ""
    chokepoint: bool = False
    closed_by_player: bool = False
    held: list[str] = Field(default_factory=list)
    tolls: list[TollLine] = Field(default_factory=list)
    losses: list[str] = Field(default_factory=list)


class SettlementPlanLine(ContextItem):
    tier: str
    settled: str = ""
    treasury: int
    tax_rate: int
    order: int
    crime: int
    unrest: int
    sanitation: int
    fire_risk: int
    prestige: int
    militia: int
    free_city: bool
    rationing: bool
    districts: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)


class CohortLine(ContextItem):
    age_band: str
    sex_kind: str
    social_class: str
    condition: str
    count: int


class OutbreakLine(ContextItem):
    disease: str
    region: str
    status: str
    severity: int
    infected: int
    dead: int
    quarantined: bool
    path: str


class EndemicLine(ContextItem):
    disease: str
    region: str
    load: int


class LabourLine(ContextItem):
    job: str
    workers: int
    output_pct: int


class EconomyBlock(ContextItem):
    commodities: list[CommodityLine] = Field(default_factory=list)
    currency: CurrencyLine | None = None
    loans: list[LoanLine] = Field(default_factory=list)
    debts: list[DebtLine] = Field(default_factory=list)
    routes: list[RouteLine] = Field(default_factory=list)
    settlement: SettlementPlanLine | None = None
    cohorts: list[CohortLine] = Field(default_factory=list)
    labour: list[LabourLine] = Field(default_factory=list)
    outbreaks: list[OutbreakLine] = Field(default_factory=list)
    endemic: list[EndemicLine] = Field(default_factory=list)
    pacts: list[str] = Field(default_factory=list)

    def empty(self) -> bool:
        return not any(
            (
                self.commodities,
                self.currency,
                self.loans,
                self.debts,
                self.routes,
                self.settlement,
                self.cohorts,
                self.labour,
                self.outbreaks,
                self.endemic,
                self.pacts,
            )
        )
