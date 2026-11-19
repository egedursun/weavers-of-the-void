from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.intrigue import IntrigueSecret

INTRIGUE_SECRET = total(
    IntrigueSecret,
    {
        IntrigueSecret.AFFAIR: Defined(
            "Affair",
            checked_by=(),
            used_by=(
                "catalog.intrigue.SCHEMES",
                "catalog.intrigue.SECRETS",
                "engine.intimacy.norms.judge_pair",
                "engine.intrigue.schemes.seduce",
                "engine.intrigue.talk.affair_secret",
                "engine.polity.trials.AREA_SECRETS",
            ),
        ),
        IntrigueSecret.ILLEGITIMATE_CHILD: Defined(
            "Illegitimate child", checked_by=(), used_by=("catalog.intrigue.SECRETS", "engine.intrigue.sources.hidden_birth")
        ),
        IntrigueSecret.MURDER: Defined(
            "Murder", checked_by=(), used_by=("catalog.intrigue.SCHEMES", "catalog.intrigue.SECRETS", "engine.polity.trials.NAMED_CRIME_SECRETS")
        ),
        IntrigueSecret.HERESY: Defined(
            "Heresy", checked_by=(), used_by=("catalog.intrigue.SECRETS", "engine.intrigue.sources.hidden_rites", "engine.polity.trials.NAMED_CRIME_SECRETS")
        ),
        IntrigueSecret.SECRET_CULT_MEMBERSHIP: Defined(
            "Secret cult membership",
            checked_by=(),
            used_by=(
                "catalog.intrigue.SCHEMES",
                "catalog.intrigue.SECRETS",
                "engine.intrigue.schemes.convert_secretly",
                "engine.intrigue.sources.hidden_memberships",
                "engine.polity.trials.AREA_SECRETS",
                "engine.polity.trials.NAMED_CRIME_SECRETS",
            ),
        ),
        IntrigueSecret.DEBT: Defined(
            "Debt", checked_by=(), used_by=("catalog.intrigue.SECRETS", "engine.intrigue.sources.noble_debts", "engine.polity.trials.AREA_SECRETS")
        ),
        IntrigueSecret.CRIME: Defined(
            "Crime",
            checked_by=(),
            used_by=(
                "catalog.intrigue.SCHEMES",
                "catalog.intrigue.SECRETS",
                "engine.intrigue.schemes.fabricate_hook",
                "engine.intrigue.schemes.frame",
                "engine.polity.trials.AREA_SECRETS",
                "engine.polity.trials.NAMED_CRIME_SECRETS",
            ),
        ),
        IntrigueSecret.COWARDICE_IN_BATTLE: Defined(
            "Cowardice in battle",
            checked_by=(),
            used_by=(
                "catalog.intrigue.SECRETS",
                "engine.intrigue.sources.cowardice",
                "engine.polity.trials.AREA_SECRETS",
                "engine.polity.trials.NAMED_CRIME_SECRETS",
            ),
        ),
        IntrigueSecret.HIDDEN_CONDITION: Defined(
            "Hidden condition",
            checked_by=(),
            used_by=("catalog.intrigue.SECRETS", "engine.intrigue.sources.hidden_conditions", "engine.polity.trials.AREA_SECRETS"),
        ),
        IntrigueSecret.FALSE_IDENTITY: Defined(
            "False identity",
            checked_by=("engine.intrigue.identities.tend_identity", "services.player.intrigue.unmask_identity"),
            used_by=("catalog.intrigue.SECRETS", "engine.intrigue.identities.assume"),
        ),
        IntrigueSecret.DEAL_WITH_OUTER_BEING: Defined(
            "Deal with outer being",
            checked_by=(),
            used_by=(
                "catalog.intrigue.SECRETS",
                "engine.intrigue.sources.hidden_rites",
                "engine.polity.trials.AREA_SECRETS",
                "engine.polity.trials.NAMED_CRIME_SECRETS",
            ),
        ),
        IntrigueSecret.TRUE_PARENTAGE: Defined(
            "True parentage",
            checked_by=("engine.intrigue.sources.likeness_noticed",),
            used_by=("catalog.intrigue.SECRETS", "engine.intrigue.sources.hidden_birth", "engine.polity.trials.AREA_SECRETS", "engine.regime.lineages.steer"),
        ),
        IntrigueSecret.BROKEN_OATH: Defined(
            "Broken oath",
            checked_by=("engine.powers.society.broken_vows",),
            used_by=(
                "catalog.intrigue.SECRETS",
                "engine.polity.oaths.broken_oath",
                "engine.polity.trials.AREA_SECRETS",
                "engine.polity.trials.NAMED_CRIME_SECRETS",
            ),
        ),
        IntrigueSecret.ECOSABOTAGE: Defined(
            "Ecosabotage", checked_by=(), used_by=("catalog.intrigue.SCHEMES", "catalog.intrigue.SECRETS", "engine.intrigue.schemes.ecosabotage")
        ),
        IntrigueSecret.BROKEN_CIPHER: Defined("Broken cipher", checked_by=(), used_by=("catalog.intrigue.SECRETS", "engine.communication.ciphers.attack")),
        IntrigueSecret.TRUE_HISTORY: Defined(
            "True history", checked_by=("engine.powers.backfill.buried_histories",), used_by=("catalog.intrigue.SECRETS", "engine.collective.accounts.expose")
        ),
    },
)
