from aerona.domain.enums.modifier import IncidentRole

ONLOOKER_ROLES = frozenset({IncidentRole.WITNESS, IncidentRole.TELLER})
NOT_PARTY_ROLES = ONLOOKER_ROLES | {IncidentRole.PLACE}
