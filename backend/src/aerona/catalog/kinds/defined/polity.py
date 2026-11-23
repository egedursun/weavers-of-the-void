from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.polity import Jurisdiction, LegitimacyBasis

JURISDICTION = total(
    Jurisdiction,
    {
        Jurisdiction.POLITY: Defined("Polity", checked_by=(), used_by=("engine.polity.laws.jurisdiction_of",)),
        Jurisdiction.SETTLEMENT: Defined(
            "Settlement",
            checked_by=(),
            used_by=("engine.city_rules.conurbations.spread_laws", "engine.occupation_regime.rule.impose_laws", "engine.polity.laws.jurisdiction_of"),
        ),
        Jurisdiction.CULT: Defined("Cult", checked_by=("engine.polity.laws.faithful_cults",), used_by=("engine.polity.laws.jurisdiction_of",)),
    },
)

LEGITIMACY_BASIS = total(
    LegitimacyBasis,
    {
        LegitimacyBasis.CUSTOM: Defined(
            "Custom",
            checked_by=("engine.polity.governance.repeal_discord",),
            used_by=(
                "db.tables.polity.LawProfileRow",
                "engine.couplings.fisheries.closures",
                "engine.polity.laws.attach_profile",
                "engine.transform.realms.codify",
            ),
        ),
        LegitimacyBasis.DECREE: Defined(
            "Decree",
            checked_by=("engine.polity.laws.enact",),
            used_by=(
                "engine.polity.control.enact_law",
                "engine.polity.governance.agenda",
                "engine.polity.governance.consider",
                "engine.polity.laws.attach_profile",
                "engine.polity.laws.enact",
                "tools.mortal.couplings.declare_closure",
                "tools.mortal.justice.BASES",
                "tools.mortal.ruler.enact_law",
            ),
        ),
        LegitimacyBasis.DIVINE: Defined(
            "Divine",
            checked_by=(),
            used_by=(
                "engine.polity.governance.agenda",
                "engine.polity.governance.consider",
                "engine.polity.governance.cult_laws",
                "tools.mortal.justice.BASES",
                "tools.son.creation_effects.polity_extras",
            ),
        ),
        LegitimacyBasis.COUNCIL: Defined(
            "Council",
            checked_by=(),
            used_by=(
                "db.tables.justice.LawProposalRow",
                "engine.factions.estates.lobby",
                "engine.polity.assembly.ban_void",
                "engine.polity.governance.agenda",
                "engine.polity.governance.consider",
                "engine.polity.policy.codify",
                "engine.polity.policy.revolution",
                "services.player.justice.CreateProposal",
                "tools.mortal.justice.BASES",
            ),
        ),
    },
)
