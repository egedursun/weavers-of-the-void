from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.regime import CredentialKind, LegitimacyType, Routinisation

CREDENTIAL_KIND = total(
    CredentialKind,
    {
        CredentialKind.EXAMINATION: Defined(
            "Passed the examinations", checked_by=(), used_by=("engine.regime.learning.hold_sitting", "tools.mortal.regime.sit_examination")
        ),
        CredentialKind.MASTER: Defined("Master", checked_by=(), used_by=("engine.regime.learning.confer", "services.player.regime.CredentialDraft")),
        CredentialKind.DOCTOR: Defined("Doctor", checked_by=(), used_by=("engine.regime.learning.confer",)),
        CredentialKind.ORDINATION: Defined("Ordained", checked_by=(), used_by=("engine.regime.learning.ordain",)),
        CredentialKind.DEGREE: Defined("Degree", checked_by=(), used_by=("engine.regime.learning.confer",)),
        CredentialKind.LICENCE: Defined("Licensed", checked_by=(), used_by=("engine.regime.learning.license_holders",)),
        CredentialKind.COMMISSION: Defined(
            "Commissioned", checked_by=("engine.regime.learning.license_holders",), used_by=("engine.regime.learning.license_holders",)
        ),
    },
)

LEGITIMACY_TYPE = total(
    LegitimacyType,
    {
        LegitimacyType.TRADITIONAL: Defined(
            "Custom and descent",
            checked_by=("engine.regime.book.TYPE_LABELS", "engine.regime.book.kinds_of", "engine.regime.rule.legitimacy_targets"),
            used_by=(),
        ),
        LegitimacyType.CHARISMATIC: Defined(
            "Charisma",
            checked_by=(
                "engine.regime.book.TYPE_LABELS",
                "engine.regime.book.kinds_of",
                "engine.regime.rule.legitimacy_targets",
                "engine.regime.rule.routinise",
            ),
            used_by=(),
        ),
        LegitimacyType.RATIONAL: Defined(
            "Law and office", checked_by=("engine.regime.book.TYPE_LABELS", "engine.regime.book.kinds_of", "engine.regime.rule.legitimacy_targets"), used_by=()
        ),
        LegitimacyType.DIVINE_MANDATE: Defined("Divine mandate", checked_by=(), used_by=()),
        LegitimacyType.POPULAR: Defined("Popular", checked_by=(), used_by=()),
        LegitimacyType.PERFORMANCE: Defined("Performance", checked_by=(), used_by=()),
    },
)

ROUTINISATION = total(
    Routinisation,
    {
        Routinisation.NONE: Defined("No founder to mourn", checked_by=("engine.regime.rule.routinise",), used_by=("db.tables.regime.RegimeRow",)),
        Routinisation.PENDING: Defined(
            "In crisis over the founder's legacy",
            checked_by=("engine.regime.rule.routinise",),
            used_by=("agents.context.regime_lines.son_regime_lines", "engine.regime.rule.routinise"),
        ),
        Routinisation.DYNASTY: Defined("Turned into a dynasty", checked_by=(), used_by=("engine.regime.rule.turn_charisma",)),
        Routinisation.INSTITUTION: Defined("Turned into rules and offices", checked_by=(), used_by=("engine.regime.rule.turn_charisma",)),
        Routinisation.SCHISM: Defined(
            "Split by schism", checked_by=(), used_by=("agents.context.regime_lines.son_regime_lines", "engine.regime.rule.turn_charisma")
        ),
    },
)
