from aerona.core.grammar import spoken
from aerona.domain.enums.domain import Domain

DOMAIN_LABELS: dict[Domain, str] = {domain: spoken(domain).title() for domain in Domain}


def match_domain(value: str) -> Domain | None:
    folded = " ".join(value.casefold().split())
    if not folded:
        return None
    for domain in Domain:
        if folded in (domain.value, DOMAIN_LABELS[domain].casefold()):
            return domain
    return next((domain for domain in Domain if folded in domain.value or domain.value in folded), None)
