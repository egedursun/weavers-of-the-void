from aerona.domain.enums.modifier import IncidentRole

R = IncidentRole
ACTING_ROLES = frozenset(
    {
        R.ACTOR,
        R.CO_ACTOR,
        R.ALLY,
        R.LEADER,
        R.MAKER,
        R.BUYER,
        R.SELLER,
        R.LENDER,
        R.BORROWER,
        R.ACCUSER,
        R.JUDGE,
        R.ADVOCATE,
        R.TEACHER,
        R.HEALER,
        R.OFFICIANT,
        R.HOST,
        R.ENVOY,
        R.MEDIATOR,
        R.AUTHORITY,
        R.PATRON,
    }
)
UNDER_AGE_KINDS = frozenset({"afterlife.possession"})
