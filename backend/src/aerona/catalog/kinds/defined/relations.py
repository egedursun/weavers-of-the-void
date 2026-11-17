from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.relations import ContestEnd

CONTEST_END = total(
    ContestEnd,
    {
        ContestEnd.CHALLENGER: Defined(
            "Challenger",
            checked_by=("engine.mind.describe.bond_lines", "engine.relations.contests.hold_contest", "tools.mortal.social.challenge"),
            used_by=("engine.relations.contests.hold_contest",),
        ),
        ContestEnd.DEFENDER: Defined("Defender", checked_by=("engine.renown.claims.test_claim",), used_by=("engine.relations.contests.hold_contest",)),
        ContestEnd.DRAWN: Defined(
            "Drawn",
            checked_by=("engine.mind.describe.bond_lines", "engine.relations.contests.hold_contest", "tools.mortal.social.challenge"),
            used_by=("engine.relations.contests.hold_contest",),
        ),
    },
)
