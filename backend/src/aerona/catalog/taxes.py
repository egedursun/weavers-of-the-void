from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import TaxKind

C = SocialClass
K = TaxKind
T = Technique


@dataclass(frozen=True)
class TaxSpec:
    classes: frozenset[SocialClass]
    rate: int
    collection: int
    evasion: int
    unrest: int
    take_pct: int
    gate: Technique | None


TAXES: Mapping[TaxKind, TaxSpec] = total(
    TaxKind,
    {
        K.LAND: TaxSpec(frozenset({C.FARMER, C.NOBLE}), 5, 20, 10, 100, 100, None),
        K.POLL: TaxSpec(frozenset({C.FARMER, C.ARTISAN, C.SERF_OR_SLAVE, C.WARRIOR}), 0, 30, 20, 140, 100, T.CENSUS),
        K.TRADE: TaxSpec(frozenset({C.MERCHANT, C.ARTISAN}), 5, 25, 30, 80, 100, T.COINAGE),
        K.CONSUMPTION: TaxSpec(frozenset({C.NOBLE, C.MERCHANT}), 0, 30, 25, 90, 100, T.DOUBLE_ENTRY),
        K.TITHE: TaxSpec(frozenset(SocialClass), 0, 15, 15, 90, 100, T.ORGANISED_CLERGY),
        K.INCOME: TaxSpec(frozenset({C.WORKER, C.PROFESSIONAL, C.ARTISAN, C.MERCHANT, C.OFFICIAL}), 0, 50, 35, 110, 120, T.BUREAUCRACY),
        K.PROPERTY: TaxSpec(frozenset({C.NOBLE, C.MERCHANT, C.CITIZEN}), 0, 40, 25, 100, 90, T.CENSUS),
        K.INHERITANCE: TaxSpec(frozenset({C.NOBLE, C.MERCHANT}), 0, 35, 40, 70, 60, T.WRITTEN_LAW),
        K.WEALTH: TaxSpec(frozenset({C.NOBLE}), 0, 55, 50, 120, 80, T.DOUBLE_ENTRY),
        K.COMPANY: TaxSpec(frozenset({C.MERCHANT, C.PROFESSIONAL}), 0, 45, 40, 60, 100, T.JOINT_STOCK),
        K.LABOUR_LEVY: TaxSpec(frozenset({C.FARMER, C.SERF_OR_SLAVE, C.WORKER}), 0, 20, 15, 150, 80, None),
        K.IN_KIND: TaxSpec(frozenset({C.FARMER, C.ARTISAN}), 0, 25, 10, 90, 90, None),
        K.LICENCE: TaxSpec(frozenset({C.MERCHANT, C.ARTISAN, C.PROFESSIONAL}), 0, 20, 20, 70, 80, T.WRITTEN_LAW),
        K.SEIGNIORAGE: TaxSpec(frozenset(SocialClass), 0, 10, 5, 50, 70, T.COINAGE),
        K.POLLUTION: TaxSpec(frozenset({C.WORKER, C.MERCHANT, C.ARTISAN}), 0, 45, 35, 60, 70, T.INDUSTRIAL_CHEMISTRY),
        K.EXCISE: TaxSpec(frozenset({C.CITIZEN, C.WORKER, C.FARMER, C.ARTISAN}), 0, 30, 30, 100, 90, T.DOUBLE_ENTRY),
    },
)
