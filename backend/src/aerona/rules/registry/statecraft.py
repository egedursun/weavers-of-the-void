from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class StatecraftRules(Spanned):
    conquest_threat: int = rule(25, 0, 100, W, "Threat a conquest of land stirs in the realms that hear of it")
    associated_distance: int = rule(10, 0, 200, W, "Distance of values below which a subject realm is freely associated with its overlord")
    war_threat: int = rule(12, 0, 100, W, "Threat a war declared without a claim stirs in the realms that hear of it")
    breach_threat: int = rule(10, 0, 100, W, "Threat a broken treaty stirs in the realms that hear of it")
    far_threat_pct: int = rule(40, 0, 100, W, "Share of threat a realm feels when the aggressor does not border it (%)")
    protectorate_tiers: int = rule(
        2, 0, 10, W, "Tiers a bordering subject with no army of its own must stand below its overlord to become a protectorate the overlord defends"
    )
    distance_threat_pct: int = rule(50, 0, 200, W, "How much distance in values swells the threat a realm feels (%)")
    threat_decay: int = rule(5, 0, 100, W, "Threat that fades each epoch")
    marriage_threat: int = rule(10, 0, 100, W, "Threat a marriage pact between two realms soothes")
    breach_trust: int = rule(25, 0, 100, W, "Trust the wronged party loses when a treaty is broken")
    witness_trust: int = rule(8, 0, 100, W, "Trust other realms lose in a realm that breaks a treaty")
    kept_trust: int = rule(5, 0, 100, W, "Trust each party gains when a treaty is kept to its end")
    trust_drift: int = rule(2, 0, 100, W, "Trust that drifts back toward its middle each epoch")
    coalition_members: int = rule(2, 2, 20, W, "Realms that must share the threat before a coalition forms")
    coalition_war_pct: int = rule(25, 0, 100, W, "Chance each epoch a coalition stronger than its foe goes to war (%)")
    capacity_base: int = rule(6, 0, 500, W, "Relations every realm can keep")
    capacity_admin: int = rule(25, 1, 100, W, "Administration per extra relation a realm can keep")
    capacity_skill: int = rule(30, 1, 100, W, "Diplomatic skill of the chancellor and envoys per extra relation")
    capacity_embassy: int = rule(1, 0, 10, W, "Extra relations each embassy holds up")
    strain_decay: int = rule(3, 0, 100, W, "Regard lost each epoch with every partner per relation beyond capacity")
    crisis_pct: int = rule(40, 0, 100, W, "Chance a war over a claim opens as a crisis instead (%)")
    crisis_steps: int = rule(3, 1, 10, W, "Escalation steps before a crisis becomes a war")
    back_down_ratio_pct: int = rule(60, 0, 100, W, "Strength ratio below which a side backs down in a crisis (%)")
    backer_trust: int = rule(60, 0, 100, W, "Trust at which a realm backs a side in a crisis")
    swing_promise: int = rule(20, 0, 100, W, "Share of the spoils promised to win a swing party")
    back_down_legitimacy: int = rule(8, 0, 100, W, "Legitimacy a realm loses when it backs down in a crisis")
    pay_share_pct: int = rule(25, 0, 100, W, "Share of its treasury a realm pays to settle a demand for payment (%)")
    sphere_ratio_pct: int = rule(200, 100, 1000, W, "Power a great power needs over a lesser realm to draw it into its sphere (%)")
    sphere_growth: int = rule(5, 0, 100, W, "Strength a sphere gains each epoch")
    sphere_contest: int = rule(10, 0, 100, W, "Strength a weaker sphere loses each epoch to a contested client")
    sphere_regard: int = rule(3, 0, 100, W, "Regard a client and its power gain each epoch")
    summit_years: int = span(10, 1, 1250, W, "Years between summits of the great powers of a world")
    summit_trust: int = rule(10, 0, 100, W, "Trust the great powers gain at a summit")
    liberty_drift_pct: int = rule(30, 0, 100, W, "How fast a subject's wish for liberty moves toward what it feels (%)")
    liberty_strength_pct: int = rule(50, 0, 200, W, "How much a subject's strength against its overlord feeds its wish for liberty (%)")
    liberty_distance_pct: int = rule(30, 0, 200, W, "How much distance in values feeds a subject's wish for liberty (%)")
    liberty_revolt: int = rule(80, 0, 100, W, "Wish for liberty at which a subject rises")
    renegotiate_at: int = rule(60, 0, 100, W, "Wish for liberty at which a subject demands better terms")
    renegotiate_loyalty: int = rule(10, 0, 100, W, "Loyalty a subject loses when its overlord rewrites its terms or refuses its demand")

    @property
    def summit_epochs(self) -> int:
        return self.epochs(self.summit_years)
