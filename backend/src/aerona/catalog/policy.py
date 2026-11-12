from collections.abc import Callable, Mapping
from types import MappingProxyType

from aerona.catalog.laws import penal_cruelty
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import MandateKind

C = SocialClass
Terms = Mapping[str, int | str | bool]
Shift = dict[SocialClass, int]
CRUEL = 50


def slavery(terms: Terms) -> Shift:
    if terms.get("status") == "allowed":
        return {C.NOBLE: 5, C.MERCHANT: 2, C.SERF_OR_SLAVE: -12}
    return {C.SERF_OR_SLAVE: 8, C.NOBLE: -3} if terms.get("status") == "banned" else {C.SERF_OR_SLAVE: -4}


def serfdom(terms: Terms) -> Shift:
    return {C.NOBLE: 6, C.SERF_OR_SLAVE: -10, C.FARMER: -4} if terms.get("allowed") else {C.SERF_OR_SLAVE: 4, C.FARMER: 2, C.NOBLE: -2}


def tax_rate(terms: Terms) -> Shift:
    burden = -int(terms.get("rate", 10)) // 10
    return {C.FARMER: burden, C.ARTISAN: burden, C.MERCHANT: burden}


def tolerance(terms: Terms) -> Shift:
    level = terms.get("level")
    if level == "persecution":
        return {C.PRIEST: 4, C.OUTCAST: -4, C.MERCHANT: -2}
    return {C.MERCHANT: 2, C.PRIEST: -2} if level == "free" else {}


def penal(terms: Terms) -> Shift:
    return {C.OUTCAST: -5, C.NOBLE: 2} if penal_cruelty(dict(terms)) >= CRUEL else {C.OUTCAST: 2}


def franchise(terms: Terms) -> Shift:
    voters = terms.get("voters")
    if voters == "all":
        return {C.FARMER: 6, C.ARTISAN: 6, C.SERF_OR_SLAVE: 4, C.NOBLE: -6}
    if voters == "free":
        return {C.FARMER: 4, C.ARTISAN: 4, C.NOBLE: -3}
    if voters == "landholders":
        return {C.FARMER: 3, C.MERCHANT: 3, C.NOBLE: -1}
    return {C.NOBLE: 3, C.FARMER: -2, C.ARTISAN: -2}


def constitution(terms: Terms) -> Shift:
    rights = {C.NOBLE: 3, C.PRIEST: 2} if terms.get("estates_rights") else {C.NOBLE: -3}
    voters = franchise(terms)
    return {social_class: rights.get(social_class, 0) + voters.get(social_class, 0) for social_class in {*rights, *voters}}


def fixed(shift: Shift) -> Callable[[Terms], Shift]:
    def effect(_terms: Terms) -> Shift:
        return dict(shift)

    return effect


LAW_POLICY: MappingProxyType[LawKind, Callable[[Terms], Shift]] = MappingProxyType(
    {
        LawKind.SLAVERY: slavery,
        LawKind.SERFDOM: serfdom,
        LawKind.TAX_RATE: tax_rate,
        LawKind.TITHE: fixed({C.PRIEST: 5, C.MONASTIC: 3, C.FARMER: -3}),
        LawKind.TOLLS: fixed({C.MERCHANT: -4, C.NOBLE: 2}),
        LawKind.CONSCRIPTION: fixed({C.FARMER: -4, C.WARRIOR: 3}),
        LawKind.STANDING_ARMY: fixed({C.WARRIOR: 5, C.FARMER: -1}),
        LawKind.VETERAN_PENSION: fixed({C.WARRIOR: 6}),
        LawKind.SUMPTUARY: fixed({C.NOBLE: 4, C.MERCHANT: -5}),
        LawKind.GUILD_CHARTER: fixed({C.ARTISAN: 5, C.MERCHANT: 2}),
        LawKind.FOREIGNER_RIGHTS: fixed({C.MERCHANT: 3}),
        LawKind.RELIGIOUS_TOLERANCE: tolerance,
        LawKind.WORSHIP_BAN: fixed({C.PRIEST: 2, C.OUTCAST: -3}),
        LawKind.CENSORSHIP: fixed({C.SCRIBE: -6, C.NOBLE: 2}),
        LawKind.PENAL_CODE: penal,
        LawKind.QUARANTINE: fixed({C.MERCHANT: -3}),
        LawKind.SANITATION: fixed({C.FARMER: 2, C.ARTISAN: 2}),
        LawKind.MAGIC_BAN: fixed({C.SCRIBE: -3, C.PRIEST: 3}),
        LawKind.LICENSED_MAGIC: fixed({C.SCRIBE: 2}),
        LawKind.FRANCHISE: franchise,
        LawKind.CONSTITUTION: constitution,
    }
)
MANDATE_POLICY: MappingProxyType[MandateKind, Shift] = MappingProxyType(
    {
        MandateKind.CURFEW: {social_class: -3 for social_class in SocialClass},
        MandateKind.EXPORT_BAN: {C.MERCHANT: -5, C.FARMER: 2},
        MandateKind.FAMINE_RELIEF: {C.FARMER: 5, C.SERF_OR_SLAVE: 3},
        MandateKind.PRODUCE: {C.ARTISAN: -2, C.WARRIOR: 2},
        MandateKind.BUILD: {C.ARTISAN: 2},
        MandateKind.SLUM_CLEARANCE: {C.OUTCAST: -5, C.MERCHANT: 2, C.NOBLE: 2},
        MandateKind.PREPARE: {C.ARTISAN: 1, C.FARMER: 1},
        MandateKind.ENCLOSURE: {C.FARMER: -6, C.SERF_OR_SLAVE: -4, C.NOBLE: 4, C.MERCHANT: 2},
    }
)
