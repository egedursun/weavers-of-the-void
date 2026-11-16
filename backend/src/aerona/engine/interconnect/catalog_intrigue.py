from aerona.db.tables.intrigue import BeliefRow, FavourRow, HookRow, IdentityRow, SchemeRow, SecretRow, TrueNameRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

INTRIGUE = "section-intrigue"
S = Subsystem
E = EdgeKind

INTRIGUE_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="secrets_and_hooks",
        spec_item="F20",
        title=(
            "Things keep typed secrets born of affairs, hidden births, hidden conditions, debts, hidden faiths, heretical and void rites, "
            "broken oaths, flight in battle and schemes; whoever learns one holds a hook, and a secret brought to light shames its keeper"
        ),
        subsystem=S.INTRIGUE,
        phases=("intrigue_survey", "intrigue", "love_and_rivalry", "couple_births"),
        surface=Surface(drawer=INTRIGUE),
        backfill="intrigue_survey: hidden conditions, noble debts and hidden memberships become secrets",
        templates=("intrigue.exposed",),
        fields=("severity", "known_by", "exposed_epoch", "strength", "source", "used_epoch", "last_demand"),
        tables=(SecretRow.__tablename__, HookRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("press_leverage",),
        targets=("mortal", "faction", "polity", "son"),
        couplings=(
            Coupling(S.SOCIAL, "gossip passes secrets on and confidants learn their friends' secrets", E.FLOW, "intrigue.gossip_pct"),
            Coupling(S.SOCIAL, "an exposed secret brings infamy and the judgement of the people's ethics", E.MODIFIER, "intrigue.expose_infamy_pct"),
            Coupling(S.WAR, "spy networks learn the secrets of those they watch", E.FLOW, "intrigue.spy_learn_pct"),
            Coupling(S.POLITY, "a hook forces a marriage, a step down from office or support", E.TRIGGER, "intrigue.hook_comply_pct"),
            Coupling(S.BODY, "a child who looks like a hidden parent may give the parentage away", E.TRIGGER, "intrigue.likeness_notice_pct"),
        ),
    ),
    Mechanic(
        key="favours",
        spec_item="F20",
        title="Gifts, rescues, support in war or succession and aid in schemes leave favours owed; honouring one wins trust, refusing costs trust and honour",
        subsystem=S.INTRIGUE,
        phases=("love_and_rivalry", "intrigue", "treaty_cycles", "polity_cycles", "house_cycles"),
        surface=Surface(drawer=INTRIGUE),
        backfill="none: favours are owed from the next epoch",
        fields=("magnitude", "origin", "called_epoch", "honoured"),
        tables=(FavourRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("press_leverage",),
        targets=("mortal", "polity"),
        couplings=(
            Coupling(S.SOCIAL, "an honoured favour warms the creditor", E.MODIFIER, "intrigue.favour_trust"),
            Coupling(S.SOCIAL, "a refused favour costs friendship and honour", E.MODIFIER, "intrigue.favour_refusal"),
            Coupling(S.WAR, "a guarantor who goes to war leaves its ward in its debt", E.FLOW, "intrigue.war_favour"),
        ),
    ),
    Mechanic(
        key="false_identities",
        spec_item="F20",
        title="Spies, the blood-cursed, exiles and impostors live under false names that wear thin with carelessness and memorable looks",
        subsystem=S.INTRIGUE,
        phases=("intrigue_survey", "intrigue"),
        surface=Surface(drawer=INTRIGUE),
        backfill="intrigue_survey: active spies, the blood-cursed and some exiles take false names",
        fields=("false_name", "cover_role", "community_node_id", "exposure"),
        tables=(IdentityRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("mortal",),
        couplings=(
            Coupling(S.MIND, "a mortal of little caution slips", E.MODIFIER, "intrigue.identity_slip"),
            Coupling(S.BODY, "rare looks make a face easy to remember", E.MODIFIER, "intrigue.identity_look"),
        ),
    ),
    Mechanic(
        key="schemes",
        spec_item="F20",
        title=(
            "Ambitious, cruel and deceitful mortals plot schemes against rivals: they recruit friends as agents, gather power from skill in intrigue "
            "and deception and strike against the target's spymaster and intuition; each epoch a scheme may be discovered"
        ),
        subsystem=S.INTRIGUE,
        phases=("intrigue",),
        surface=Surface(drawer=INTRIGUE),
        backfill="none: schemes begin from the next epoch",
        templates=("intrigue.scheme_done", "intrigue.scheme_exposed"),
        fields=("phase", "power", "secrecy", "progress", "agents", "discovered_by", "outcome"),
        tables=(SchemeRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("plot_scheme",),
        targets=("mortal", "faction", "cult"),
        couplings=(
            Coupling(S.POLITY, "a coup seizes the throne, a forged claim adds a claimant who poses as a lost heir", E.TRIGGER, "intrigue.scheme_cap"),
            Coupling(S.KNOWLEDGE, "skill in intrigue and deception gathers power", E.MODIFIER, "intrigue.agent_power"),
            Coupling(S.POLITY, "the target's spymaster and intuition defend", E.MODIFIER, "intrigue.defence_spymaster"),
            Coupling(S.LAW, "a discovered scheme brings infamy and betrayal", E.TRIGGER, "intrigue.discovery_pct"),
        ),
    ),
    Mechanic(
        key="intrigue_conditions",
        spec_item="F20/RP8",
        title="Fog, blizzards and storms, festivals, plague and siege change a scheme's odds and witnesses; schemes may blight a land in the night",
        subsystem=S.INTRIGUE,
        phases=("intrigue",),
        surface=Surface(drawer=INTRIGUE),
        backfill="none: conditions are read at each strike",
        fields=("phase", "outcome"),
        tables=(SchemeRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("plot_scheme",),
        targets=("mortal", "settlement", "region"),
        couplings=(
            Coupling(S.ENVIRONMENT, "fog and blizzards cover a scheme and hide its witnesses", E.MODIFIER, "intrigue.night_fog_pct"),
            Coupling(S.ENVIRONMENT, "storms cut pursuit", E.MODIFIER, "intrigue.storm_pct"),
            Coupling(S.CULTURE, "festival crowds give cover and witnesses", E.MODIFIER, "intrigue.crowd_pct"),
            Coupling(S.BODY, "plague panic and siege distract the watch", E.MODIFIER, "intrigue.panic_pct"),
            Coupling(S.ECOLOGY, "a sabotage of the land blights it", E.TRIGGER),
        ),
    ),
    Mechanic(
        key="true_names",
        spec_item="F20/RP3",
        title=(
            "Gods, spirits, outer beings and some other beings bear a true name; knowing it gives a strong hook, "
            "strengthens rites against its bearer and wards against its own, and a widely known name is cast off"
        ),
        subsystem=S.MAGIC,
        phases=("intrigue_survey", "intrigue", "rite_cycles"),
        surface=Surface(drawer=INTRIGUE),
        backfill="intrigue_survey: true names for every son, foreign god, spirit and outer being and some other beings",
        templates=("intrigue.true_name_changed",),
        fields=("name", "known_by", "language_node_id"),
        tables=(TrueNameRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("reveal_true_name",),
        targets=("son", "foreign_god", "spirit", "mortal"),
        couplings=(
            Coupling(S.MAGIC, "a known true name strengthens a binding rite", E.MODIFIER, "intrigue.true_name_power_pct"),
            Coupling(S.MAGIC, "knowing a caster's true name wards against their rites", E.MODIFIER, "intrigue.true_name_ward_pct"),
            Coupling(S.KNOWLEDGE, "scholars of old tongues learn true names", E.FLOW, "intrigue.research_name_pct"),
            Coupling(S.GODS, "a son reborn under a new true name spends essence", E.FLOW, "intrigue.rename_essence"),
        ),
    ),
    Mechanic(
        key="belief_state",
        spec_item="F22",
        title=(
            "Every actor decides on what it believes, not on the truth: beliefs come from sight of neighbours, spies, rumour and planted lies, "
            "stray from the truth by their confidence and fade each epoch"
        ),
        subsystem=S.MIND,
        phases=("intrigue", "love_and_rivalry", "war_upkeep", "treaty_cycles", "speculation", "industry_methods", "trade_flow"),
        surface=Surface(drawer=INTRIGUE),
        backfill="none: beliefs form from the next epoch",
        fields=("value", "confidence", "source", "false", "as_of_epoch"),
        tables=(BeliefRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("settlement", "people", "polity", "mortal"),
        couplings=(
            Coupling(S.WAR, "raiders weigh the wealth they believe a neighbour holds", E.MODIFIER, "belief_state.prior_pct"),
            Coupling(S.POLITY, "guarantors weigh the defences they believe an attacker has", E.MODIFIER, "belief_state.observe_confidence"),
            Coupling(S.INTRIGUE, "deep spy networks plant false reports", E.TRIGGER, "intrigue.deceive_pct"),
            Coupling(S.MIND, "confidence fades each epoch", E.MODIFIER, "belief_state.decay"),
            Coupling(
                S.ECONOMY,
                "speculators buy what they believe is rising, owners pick methods by the prices they believe",
                E.MODIFIER,
                "belief_state.observe_confidence",
            ),
            Coupling(S.ECONOMY, "a community that knows its neighbours well trades more along its routes", E.MODIFIER, "arbitrage.belief_pct"),
            Coupling(S.SOCIAL, "an appeal to evidence moves those who trust what they know", E.MODIFIER, "belief_state.spy_confidence"),
        ),
    ),
)
