from aerona.domain.enums.polity import ClauseKind, PartyRole
from aerona.tools.framework.inputs import ToolInput


class ClauseInput(ToolInput):
    kind: ClauseKind
    obligor_id: int | None = None
    beneficiary_id: int | None = None
    params: dict[str, int | str | bool] | None = None


class PartyInput(ToolInput):
    party_id: int
    role: PartyRole = PartyRole.SIGNATORY
