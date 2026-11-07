from aerona.db.tables.communication import CipherRow, PublicOpinionRow, SignalLinkRow
from aerona.db.tables.lore import MessageRow
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

CORRESPONDENCE = "section-correspondence"
S = Subsystem
E = EdgeKind

COMMUNICATION_MECHANICS: tuple[Mechanic, ...] = (
    Mechanic(
        key="dispatches",
        spec_item="F21",
        title=(
            "Messages between the living travel by envoy, letter, herald, bird, signal fire, dream or magic, taking time by distance, "
            "medium, season and signal links; spies read or seize them, outlaws waylay them, forgers replace them and tongues misread them"
        ),
        subsystem=S.COMMUNICATION,
        phases=("correspondence", "intrigue", "treaty_cycles", "war_upkeep"),
        surface=Surface(drawer=CORRESPONDENCE),
        backfill="none: messages between the living are sent from the next epoch",
        fields=("medium", "content", "state", "arrival_epoch", "intercepted_by_node_id", "forged", "misread", "enciphered", "envoy_fate"),
        tables=(MessageRow.__tablename__,),
        exposure=Exposure.TOOL,
        tools=("send_dispatch",),
        targets=("polity", "mortal", "settlement"),
        couplings=(
            Coupling(S.INTRIGUE, "spies intercept messages to and from their targets and learn what they carry", E.FLOW, "communication.spy_intercept_pct"),
            Coupling(S.WAR, "a forged declaration starts a war between the innocent, and a slain envoy brings one", E.TRIGGER),
            Coupling(S.MIND, "reports and intelligence become beliefs when they arrive", E.FLOW, "communication.report_confidence"),
            Coupling(
                S.SOCIAL,
                "gifts to the recipient's taste win favour; insults sting honour cultures twice",
                E.MODIFIER,
                "communication.gift_friendship",
            ),
            Coupling(S.LANGUAGE, "a message between tongues may be misread, a misread clause becomes a treaty dispute", E.TRIGGER, "communication.misread_pct"),
            Coupling(S.ENVIRONMENT, "the cold season closes passes and slows messages over land", E.MODIFIER, "communication.winter_delay_pct"),
        ),
    ),
    Mechanic(
        key="public_opinion",
        spec_item="F21",
        title=(
            "Every community holds an opinion of its ruler, its wars, its laws, its gods and its creeds, fed by fortune, renown, rumour, heralds, "
            "art and broadsheets and muted by censorship"
        ),
        subsystem=S.COMMUNICATION,
        phases=("public_opinion", "polity_cycles"),
        surface=Surface(drawer=CORRESPONDENCE),
        backfill="none: opinions form from the next epoch",
        fields=("approval", "censored", "subject"),
        tables=(PublicOpinionRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=("settlement", "people", "polity"),
        couplings=(
            Coupling(S.POLITY, "approval of the ruler feeds legitimacy and discontent costs stability", E.MODIFIER, "communication.legitimacy_pct"),
            Coupling(S.WAR, "approval of a war eases its weariness", E.MODIFIER, "communication.war_support_pct"),
            Coupling(
                S.LAW,
                "approval of a law raises its enforcement; a hierarchical realm out of favour censors",
                E.MODIFIER,
                "communication.enforcement_pct",
            ),
            Coupling(S.KNOWLEDGE, "printing amplifies rumour", E.MODIFIER, "communication.broadsheet_pct"),
            Coupling(S.CULTURE, "art glorifying a subject raises approval of it", E.MODIFIER, "communication.propaganda_approval"),
        ),
    ),
    Mechanic(
        key="ciphers_and_signals",
        spec_item="F21/RP3",
        title=(
            "Realms that know cryptography write in ciphers that codebreakers break over seasons by the traffic they intercept; "
            "signal links shorten journeys and fall to those who take their lands"
        ),
        subsystem=S.COMMUNICATION,
        phases=("correspondence",),
        surface=Surface(drawer=CORRESPONDENCE),
        backfill="none: ciphers and signal links arise from the next epoch",
        templates=("communication.cipher_broken",),
        fields=("strength", "broken_by", "break_known", "kind", "state"),
        tables=(CipherRow.__tablename__, SignalLinkRow.__tablename__),
        exposure=Exposure.CONTEXT,
        targets=("polity", "region"),
        couplings=(
            Coupling(S.KNOWLEDGE, "the best cryptographer strengthens a cipher", E.MODIFIER, "communication.cipher_skill_pct"),
            Coupling(S.INTRIGUE, "a broken cipher is a secret until its owner notices", E.TRIGGER, "communication.break_noticed_pct"),
            Coupling(S.WAR, "an enemy taking either end captures or burns a signal link", E.TRIGGER),
            Coupling(S.COMMUNICATION, "a signal link cuts the journey of its owner's messages", E.MODIFIER, "communication.signal_cut"),
        ),
    ),
)
