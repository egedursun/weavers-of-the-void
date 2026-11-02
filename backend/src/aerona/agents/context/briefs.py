from aerona.catalog.domains import DOMAIN_LABELS
from aerona.db.tables.sons import SonRow
from aerona.prompts.contexts.common import SonBrief


def son_brief(son: SonRow) -> SonBrief:
    return SonBrief(id=son.id, name=son.name, title=son.title, domain_1=DOMAIN_LABELS[son.domain_primary], domain_2=DOMAIN_LABELS[son.domain_secondary])
