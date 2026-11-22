from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.polity import ClaimBasis, ClauseKind, Jurisdiction, LegitimacyBasis, OathKind

CLAIM_BASIS = total(
    ClaimBasis,
    {
        ClaimBasis.INHERITANCE: Defined(
            "Inheritance",
            checked_by=(),
            used_by=(
                "engine.collective.accounts.rally_true_line",
                "engine.polity.houses.branch",
                "engine.polity.houses.inherit_claims",
                "engine.regime.rule.claimed_by_kin",
            ),
        ),
        ClaimBasis.MARRIAGE: Defined("Marriage", checked_by=(), used_by=("engine.polity.houses.marriage_claims",)),
        ClaimBasis.CONQUEST: Defined("Conquest", checked_by=("engine.polity.houses.inherit_claims",), used_by=("engine.polity.houses.conquest_claims",)),
        ClaimBasis.DIVINE: Defined("Divine", checked_by=("engine.polity.houses.inherit_claims",), used_by=("services.player.realms.GrantClaim",)),
        ClaimBasis.FABRICATED: Defined(
            "Fabricated",
            checked_by=(),
            used_by=(
                "engine.arts.forgery.forge",
                "engine.collective.storylets.apply_bond",
                "engine.intrigue.schemes.fabricate_claim",
                "engine.military.spycraft.plant_claimant",
                "engine.polity.houses.fabricate_claims",
            ),
        ),
        ClaimBasis.DE_JURE: Defined("De jure", checked_by=(), used_by=("engine.polity.titles.press_claims",)),
    },
)

CLAUSE_KIND = total(
    ClauseKind,
    {
        ClauseKind.CALL_TO_ARMS: Defined(
            "Call to arms",
            checked_by=("engine.military.alliance.betrayed_call", "engine.polity.coalitions.coalition_targets", "engine.polity.treaties.allies_called"),
            used_by=(
                "engine.factions.outlaws.contract",
                "engine.phases.civilization.sign_treaty",
                "engine.phases.diplomacy.form_alliance",
                "engine.phases.realms.house_cycles",
                "engine.phases.travel._contact",
                "engine.polity.accords.DEFAULT_CLAUSES",
                "engine.polity.coalitions.band",
                "engine.polity.control.create_vassalage",
                "engine.polity.treaties.PEACEFUL",
                "engine.polity.treaties.adopt_bonds",
                "engine.polity.treaties.vassal_duties",
                "services.player.diplomacy.decree",
                "services.player.diplomacy.found_federation",
                "tools.mortal.diplomacy._union",
                "tools.son.war.make_interworld_treaty",
            ),
        ),
        ClauseKind.TRIBUTE: Defined(
            "Tribute",
            checked_by=(
                "api.routers.wilds.beast_card",
                "engine.ecology.beasts.tribute_clauses",
                "engine.polity.accords.bond_ends",
                "engine.polity.treaties.adopt_bonds",
                "engine.polity.treaties.keep_clause",
            ),
            used_by=(
                "engine.ecology.beasts.swear_tribute",
                "engine.factions.outlaws.contract",
                "engine.military.aims.reparation_term",
                "engine.polity.accords.DEFAULT_CLAUSES",
                "engine.polity.control.create_vassalage",
                "engine.polity.treaties.vassal_duties",
                "engine.services.war.impose_tribute",
            ),
        ),
        ClauseKind.CESSION: Defined(
            "Cession", checked_by=("engine.polity.accords.execute_on_signing",), used_by=("engine.military.aims.cession_term", "engine.military.aims.press")
        ),
        ClauseKind.HOSTAGE: Defined("Hostage", checked_by=("engine.polity.treaties.keep_clause",), used_by=("engine.military.aims.hostage_term",)),
        ClauseKind.MARRIAGE: Defined(
            "Marriage",
            checked_by=("engine.polity.treaties.keep_clause",),
            used_by=(
                "engine.military.peace.clause_for",
                "engine.phases.diplomacy.form_alliance",
                "engine.phases.realms.house_cycles",
                "engine.polity.accords.DEFAULT_CLAUSES",
            ),
        ),
        ClauseKind.TRADE_RIGHTS: Defined(
            "Trade rights",
            checked_by=("engine.economy.convoys.escorted_by_treaty", "engine.polity.accords.execute_on_signing"),
            used_by=(
                "engine.military.peace.clause_for",
                "engine.phases.civilization.sign_treaty",
                "engine.phases.travel._contact",
                "engine.polity.accords.DEFAULT_CLAUSES",
                "tools.son.war.make_interworld_treaty",
            ),
        ),
        ClauseKind.TOLLS_WAIVED: Defined(
            "Tolls waived",
            checked_by=("engine.economy.book.EconomyBook.load", "engine.polity.treaties.keep_clause"),
            used_by=("engine.economy.routes.set_tolls", "engine.polity.accords.DEFAULT_CLAUSES"),
        ),
        ClauseKind.RELIGIOUS_FREEDOM: Defined(
            "Religious freedom",
            checked_by=(),
            used_by=(
                "engine.military.aims.cult_term",
                "engine.military.aims.faith_term",
                "engine.phases.religion_spread.religion_spread",
                "engine.polity.pacts.faith_pacts",
            ),
        ),
        ClauseKind.DEMILITARISED: Defined("Demilitarised", checked_by=("engine.polity.treaties.armed_breach",), used_by=("engine.military.peace.clause_for",)),
        ClauseKind.CHAMPION: Defined("Champion", checked_by=(), used_by=("engine.military.peace.clause_for", "engine.polity.treaties.champion_for")),
        ClauseKind.EXTRADITION: Defined("Extradition", checked_by=("engine.polity.treaties.keep_clause",), used_by=()),
        ClauseKind.WERGILD: Defined("Wergild", checked_by=("engine.polity.accords.execute_on_signing",), used_by=()),
        ClauseKind.NON_AGGRESSION: Defined(
            "Non aggression",
            checked_by=(),
            used_by=(
                "engine.military.aims.government_term",
                "engine.military.aims.liberty_term",
                "engine.military.aims.vassal_term",
                "engine.military.peace.clause_for",
                "engine.phases.civilization.sign_treaty",
                "engine.polity.accords.DEFAULT_CLAUSES",
                "engine.polity.pacts.beast_pacts",
                "engine.polity.pacts.faith_pacts",
                "engine.polity.pacts.god_pacts",
                "engine.polity.treaties.PEACEFUL",
                "tools.son.war.make_interworld_treaty",
            ),
        ),
        ClauseKind.ROUTE_CONTROL: Defined(
            "Route control", checked_by=("engine.economy.chokepoints.route_grants",), used_by=("engine.economy.chokepoints.route_term",)
        ),
        ClauseKind.RESOURCE_DEMAND: Defined(
            "Resource demand",
            checked_by=(
                "api.routers.polity_economy.resource_pacts",
                "engine.gods.pacts.pact_for",
                "engine.gods.pacts.pact_terms",
                "tools.framework.economy_lines.pact_lines",
            ),
            used_by=("engine.gods.pacts.strike_pact",),
        ),
        ClauseKind.RESEARCH_AGREEMENT: Defined(
            "Research agreement",
            checked_by=("engine.lore.research_depth.seal_agreements", "engine.lore.research_depth.share_agreements"),
            used_by=("engine.lore.research_depth.seal_agreements",),
        ),
        ClauseKind.FLEET_LIMIT: Defined(
            "Fleet limit",
            checked_by=("engine.operations.admiralty.limited_pair", "engine.operations.admiralty.limits_on", "engine.polity.treaties.armed_breach"),
            used_by=("engine.operations.admiralty.naval_treaties", "engine.polity.accords.DEFAULT_CLAUSES", "tools.son.operations.limit_fleets"),
        ),
        ClauseKind.AUTONOMOUS_WEAPONS_BAN: Defined(
            "Autonomous weapons ban", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.MIND_SEIZURE_BAN: Defined(
            "Mind seizure ban", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.SOLDIER_COPY_BAN: Defined(
            "Soldier copy ban", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.REPLICATOR_WEAPON_BAN: Defined(
            "Replicator weapon ban", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.CIVIL_NETWORK_SHIELD: Defined(
            "Civil network shield", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.CIVIL_HOST_SHIELD: Defined(
            "Civil host shield", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.NO_MIND_COMPULSION: Defined(
            "No mind compulsion", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.NO_PLAGUE_POWERS: Defined(
            "No plague powers", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.NO_DESIGNED_DISEASE: Defined(
            "No designed disease", checked_by=("engine.minds.war_methods.method_breached",), used_by=("engine.minds.war_methods.METHOD_CLAUSES",)
        ),
        ClauseKind.MASS_WEAPON_LIMIT: Defined(
            "Mass weapon limit",
            checked_by=("engine.mass_weapons.limits.bound_pair", "engine.minds.war_methods.method_breached"),
            used_by=("engine.mass_weapons.limits.bind_arsenals", "engine.minds.war_methods.METHOD_CLAUSES", "engine.polity.accords.DEFAULT_CLAUSES"),
        ),
    },
)

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

OATH_KIND = total(
    OathKind,
    {
        OathKind.FEALTY: Defined(
            "Fealty",
            checked_by=("engine.polity.oaths.lapse",),
            used_by=(
                "engine.leader_cults.cults.swear",
                "engine.phases.society.raise_rebels",
                "engine.polity.accords.accept",
                "engine.polity.accords.sign",
                "engine.polity.offices.appoint",
                "engine.polity.offices.seize_throne",
                "engine.polity.standing.secede",
                "engine.relations.passions.LOYAL_OATHS",
            ),
        ),
        OathKind.VENGEANCE: Defined(
            "Vengeance", checked_by=("engine.polity.oaths.lapse",), used_by=("engine.phases.mind.vengeance", "engine.polity.oaths.TIMED")
        ),
        OathKind.CELIBACY: Defined(
            "Celibacy",
            checked_by=("engine.polity.oaths.lapse",),
            used_by=(
                "agents.context.intimacy_lines.mortal_intimacy_lines",
                "engine.intimacy.restraint.break_vows",
                "engine.intimacy.restraint.vow_customs",
                "engine.polity.houses.break_celibacy",
                "engine.polity.oaths.vows",
                "tools.mortal.intimacy.VOW_OATHS",
            ),
        ),
        OathKind.PILGRIMAGE: Defined(
            "Pilgrimage",
            checked_by=("engine.mind.aspirations.prayed_since", "engine.polity.oaths.lapse"),
            used_by=("engine.polity.oaths.TIMED", "engine.polity.oaths.vows"),
        ),
        OathKind.PROTECTION: Defined(
            "Protection",
            checked_by=("engine.polity.oaths.lapse",),
            used_by=("engine.polity.accords.accept", "engine.polity.accords.sign", "engine.polity.oaths.pledges", "engine.relations.passions.LOYAL_OATHS"),
        ),
        OathKind.SILENCE: Defined(
            "Silence",
            checked_by=("engine.polity.oaths.lapse",),
            used_by=(
                "engine.factions.crime.punish_informers",
                "engine.factions.crime.swear_silence",
                "engine.phases.prisoners.torture",
                "engine.polity.offices.appoint",
            ),
        ),
        OathKind.SWORN_KINSHIP: Defined(
            "Sworn kinship",
            checked_by=("engine.polity.oaths.lapse",),
            used_by=("engine.mortal.course.swear_kinship", "engine.polity.oaths.pledges", "engine.relations.passions.LOYAL_OATHS"),
        ),
        OathKind.SERVICE: Defined("Service", checked_by=("engine.polity.vows.BREACHES", "engine.polity.vows.VOWS"), used_by=()),
        OathKind.POVERTY: Defined("Poverty", checked_by=("engine.polity.vows.BREACHES", "engine.polity.vows.VOWS"), used_by=()),
        OathKind.NONVIOLENCE: Defined("Nonviolence", checked_by=("engine.polity.vows.BREACHES", "engine.polity.vows.VOWS"), used_by=()),
        OathKind.FIDELITY: Defined(
            "Fidelity",
            checked_by=("engine.polity.vows.BREACHES", "engine.polity.vows.VOWS"),
            used_by=("agents.context.intimacy_lines.mortal_intimacy_lines", "engine.relations.affairs.consequences", "tools.mortal.intimacy.VOW_OATHS"),
        ),
        OathKind.SECRECY: Defined("Secrecy", checked_by=("engine.polity.vows.BREACHES", "engine.polity.vows.VOWS"), used_by=()),
    },
)
