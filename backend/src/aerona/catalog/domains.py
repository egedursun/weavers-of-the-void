from aerona.domain.enums.domain import DEATH_DOMAINS, Domain

DOMAIN_LABELS: dict[Domain, str] = {domain: domain.value.replace("_", " ").title() for domain in Domain}


def match_domain(value: str) -> Domain | None:
    folded = " ".join(value.casefold().split())
    if not folded:
        return None
    for domain in Domain:
        if folded in (domain.value, DOMAIN_LABELS[domain].casefold()):
            return domain
    return next((domain for domain in Domain if folded in domain.value or domain.value in folded), None)


def is_death_domain(domain: Domain) -> bool:
    return domain in DEATH_DOMAINS
