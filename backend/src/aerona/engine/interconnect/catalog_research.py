from aerona.db.tables.affairs import TaxPolicyRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import (
    HolderLevelRow,
    HolderTechniqueRow,
    IdeologyTenetRow,
    InstitutionRow,
    ResearchBoostRow,
    ResearchFocusRow,
    ResearchProgressRow,
)
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import LoanRow, ProductionRunRow, TradeRouteProfileRow
from aerona.db.tables.estates import EstateProfileRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.mind import CultureValueRow, SkillRow
from aerona.db.tables.polity import LawProfileRow, OfficeRow, PolityProfileRow, TreatyClauseRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import SiegeRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

CYCLES = ("research_cycles",)
S = Subsystem
E = EdgeKind
LEARNING = "section-learning"
HOLDERS = ("people", "settlement", "cult", "faction")

RESEARCH_MECHANICS = (
    Mechanic(
        key="research_focus",
        spec_item="S8.4/RP2",
        title="Each epoch scholars draw a few techniques within reach, weighted by need and boosts; the focus advances at full pace, the rest slowly",
        subsystem=S.KNOWLEDGE,
        phases=CYCLES,
        surface=Surface(drawer="ResearchFocus"),
        backfill="research_cycles: every holder draws its first choices in the next epoch",
        fields=("technique", "chooser", "options", "epoch"),
        tables=(ResearchFocusRow.__tablename__, ResearchProgressRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("choose_research",),
        targets=HOLDERS,
        couplings=(
            Coupling(S.KNOWLEDGE, "the chosen technique advances at full pace", E.MODIFIER, "research_depth.focus_pct"),
            Coupling(S.KNOWLEDGE, "the rest within reach move slowly", E.MODIFIER, "research_depth.unfocused_pct"),
            Coupling(S.WAR, "need weighs the draw toward what war, hunger and sickness call for", E.MODIFIER, "research_depth.need_weight"),
            Coupling(S.MIND, "the most skilled scholars in the field choose", E.MODIFIER),
        ),
    ),
    Mechanic(
        key="research_boosts",
        spec_item="S8.4/RP2",
        title="Deeds lived through push the techniques they teach: great catches, sieges repulsed, plagues outlived, eclipses watched, trials, debts",
        subsystem=S.KNOWLEDGE,
        phases=CYCLES,
        surface=Surface(drawer="ResearchBoost"),
        backfill="none: boosts are earned from the next epoch",
        templates=("research.boosted",),
        fields=("trigger", "technique", "progress"),
        tables=(
            ResearchBoostRow.__tablename__,
            ProductionRunRow.__tablename__,
            SiegeRow.__tablename__,
            OutbreakRow.__tablename__,
            SkyEventRow.__tablename__,
            CrimeCaseRow.__tablename__,
            LoanRow.__tablename__,
        ),
        exposure=Exposure.CONTEXT,
        targets=HOLDERS,
        couplings=(
            Coupling(S.ECONOMY, "a great catch from the sea pushes sailing and map-making", E.TRIGGER, "research_depth.fishing_scale"),
            Coupling(
                S.WAR, "a siege repulsed pushes fortification; riders of the plains at war push horse archery", E.TRIGGER, "research_depth.boost_progress"
            ),
            Coupling(S.BODY, "an outbreak outlived pushes quarantine, herbal lore and hospitals", E.TRIGGER, "research_depth.boost_progress"),
            Coupling(S.COSMOS, "an eclipse watched from an observatory pushes the calendar", E.TRIGGER, "research_depth.boost_progress"),
            Coupling(S.LAW, "a great trial pushes written and codified law", E.TRIGGER, "research_depth.great_trial_evidence"),
            Coupling(S.ECONOMY, "a great debt pushes banking and double entry", E.TRIGGER, "research_depth.great_debt"),
        ),
    ),
    Mechanic(
        key="research_catch_up",
        spec_item="S8.4/RP2",
        title="Techniques known by neighbours and trade partners come faster; captives leak what their homeland knew",
        subsystem=S.KNOWLEDGE,
        phases=CYCLES,
        surface=Surface(drawer=LEARNING),
        backfill="computed",
        fields=("progress",),
        tables=(ResearchProgressRow.__tablename__, CaptiveCohortRow.__tablename__, HolderTechniqueRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=HOLDERS,
        couplings=(
            Coupling(S.ECONOMY, "each neighbour or trade partner that knows it speeds it", E.MODIFIER, "research_depth.catch_up_pct"),
            Coupling(S.WAR, "captives leak their homeland's techniques to their captors", E.FLOW, "research_depth.captive_leak"),
        ),
    ),
    Mechanic(
        key="institutions",
        spec_item="S8.4/RP2",
        title="Institutions are born where a technique meets wealth, trade and scholars, spread to neighbours and kin, and are embraced or refused",
        subsystem=S.KNOWLEDGE,
        phases=CYCLES,
        surface=Surface(drawer="InstitutionCard"),
        backfill="none: the first institutions are born from the next epoch",
        templates=("research.institution_born", "research.institution_embraced"),
        fields=("origin", "embraced", "since_epoch", "refused_epochs"),
        tables=(InstitutionRow.__tablename__, PolityProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=HOLDERS,
        couplings=(
            Coupling(S.ECONOMY, "it is born only where prosperity and trade gather", E.TRIGGER, "research_depth.origin_wealth"),
            Coupling(S.SOCIAL, "it spreads to neighbours, faster among kin and fellow worshippers", E.FLOW, "research_depth.kin_spread_pct"),
            Coupling(S.POLITY, "embracing it costs the treasury", E.FLOW, "research_depth.embrace_cost"),
            Coupling(S.KNOWLEDGE, "embraced it quickens research; refused it holds research back", E.MODIFIER, "research_depth.refusal_pct"),
        ),
    ),
    Mechanic(
        key="specialised_scholars",
        spec_item="S8.4/RP2",
        title="Scholars skilled in a branch's own craft push that branch more than learned generalists",
        subsystem=S.KNOWLEDGE,
        phases=("knowledge_levels",),
        surface=Surface(drawer=LEARNING),
        backfill="computed",
        fields=("level", "skill"),
        tables=(SkillRow.__tablename__, HolderLevelRow.__tablename__),
        targets=(*HOLDERS, "mortal"),
        couplings=(Coupling(S.MIND, "a scholar's skill in the branch's craft weighs more", E.MODIFIER, "research_depth.expertise_pct"),),
    ),
    Mechanic(
        key="court_scholar",
        spec_item="S8.4/RP2",
        title="A realm that keeps a court scholar pays a stipend, gains prestige and quickens the research of every member",
        subsystem=S.POLITY,
        phases=CYCLES,
        surface=Surface(drawer="OfficesChart"),
        backfill="none: realms that know logic seat a court scholar from the next epoch",
        fields=("kind", "holder_entity_id", "treasury", "prestige"),
        tables=(OfficeRow.__tablename__, PolityProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("polity", "mortal"),
        couplings=(
            Coupling(S.KNOWLEDGE, "the scholar's learning quickens research", E.MODIFIER, "research_depth.patron_research_pct"),
            Coupling(S.ECONOMY, "the stipend comes out of the treasury", E.FLOW, "research_depth.patron_stipend"),
            Coupling(S.POLITY, "the ruler gains prestige as a patron", E.FLOW, "research_depth.patron_prestige"),
        ),
    ),
    Mechanic(
        key="research_agreements",
        spec_item="S8.4/RP2",
        title="Trade pacts between realms that keep court scholars grow a research agreement; the one behind learns from the one ahead",
        subsystem=S.LAW,
        phases=CYCLES,
        surface=Surface(drawer="TreatyView"),
        backfill="none",
        fields=("kind", "params", "last_kept_epoch"),
        tables=(TreatyClauseRow.__tablename__, ResearchProgressRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("treaty", "polity"),
        couplings=(Coupling(S.KNOWLEDGE, "a party behind in a branch gains progress in it", E.FLOW, "research_depth.agreement_share_pct"),),
    ),
    Mechanic(
        key="technique_social_change",
        spec_item="S8.4/RP2",
        title="Adopting a technique shifts what a people values and the shares of its classes",
        subsystem=S.SOCIAL,
        phases=CYCLES,
        surface=Surface(drawer=LEARNING),
        backfill="none: techniques adopted from now on change their society",
        fields=("value", "share_scribe", "share_merchant", "share_artisan", "share_priest", "share_monastic", "share_warrior", "share_farmer"),
        tables=(CultureValueRow.__tablename__, CommunitySocietyRow.__tablename__),
        targets=HOLDERS,
        couplings=(
            Coupling(S.MIND, "values move toward what the technique teaches", E.MODIFIER, "research_depth.social_shift_pct"),
            Coupling(S.SOCIAL, "the classes it calls for grow", E.MODIFIER, "research_depth.social_shift_pct"),
        ),
    ),
    Mechanic(
        key="capabilities",
        spec_item="S8.4/RP2",
        title="Combinations of branches and techniques unlock capabilities: blue-water navigation lengthens sea reach, universities may rise",
        subsystem=S.KNOWLEDGE,
        phases=("trade_flow", "research_cycles"),
        surface=Surface(drawer="Capabilities"),
        backfill="computed",
        fields=("capability",),
        tables=(HolderLevelRow.__tablename__, HolderTechniqueRow.__tablename__, TradeRouteProfileRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=HOLDERS,
        couplings=(
            Coupling(S.ECONOMY, "coastal markets with blue-water navigation reach partners farther away", E.MODIFIER, "research_depth.capability_reach"),
            Coupling(S.KNOWLEDGE, "a university can rise only where the university capability is met", E.TRIGGER),
        ),
    ),
    Mechanic(
        key="civic_gates",
        spec_item="S8.4/RP2",
        title="Civics gate governments, offices, laws, taxes, privileges and creeds: what a realm has not learned it cannot found",
        subsystem=S.POLITY,
        phases=("polity_cycles", "estates", "ideology_cycles"),
        surface=Surface(drawer=LEARNING),
        backfill="none: existing institutions of state stand; new ones need their civic",
        fields=("government", "kind", "rate", "privileges", "tenets"),
        tables=(
            PolityProfileRow.__tablename__,
            OfficeRow.__tablename__,
            LawProfileRow.__tablename__,
            TaxPolicyRow.__tablename__,
            EstateProfileRow.__tablename__,
            IdeologyTenetRow.__tablename__,
        ),
        exposure=Exposure.TOOL,
        tools=("enact_law", "appoint_officer", "bargain_with_estate", "found_school"),
        targets=("polity", "faction", "ideology"),
        couplings=(
            Coupling(S.LAW, "written law opens republics, penal codes and governors", E.TRIGGER),
            Coupling(S.ECONOMY, "a census opens the poll tax; double entry the consumption tax", E.TRIGGER),
            Coupling(S.FAITH, "an organised clergy opens theocracy and tithes", E.TRIGGER),
            Coupling(S.SOCIAL, "guilds open monopolies; codified law judicial immunity", E.TRIGGER),
        ),
    ),
)
