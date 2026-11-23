from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

C = RuleGroup.INTERCONNECTION


@dataclass(frozen=True)
class NetworkRules(Spanned):
    days_per_epoch: int = rule(360, 1, 10000, C, "Days in a year; a network's delay is counted against the days of a whole epoch")
    relay_days: int = rule(20, 0, 1000, C, "Days a message takes across a relay network")
    wired_days: int = rule(1, 0, 1000, C, "Days a message takes across a wired network")
    broadcast_days: int = rule(0, 0, 1000, C, "Days a message takes across a broadcast network")
    mesh_days: int = rule(3, 0, 1000, C, "Days a message takes across a mesh network")
    mind_link_days: int = rule(0, 0, 1000, C, "Days a message takes across minds joined directly")
    rite_link_days: int = rule(1, 0, 1000, C, "Days a message takes across a network bound by a working")
    grown_link_days: int = rule(5, 0, 1000, C, "Days a message takes across a living connection")
    interworld_days: int = rule(360, 0, 100000, C, "Days a message takes through a gateway to another world")
    outage_base: int = rule(5, 0, 100, C, "Chance of an outage each epoch for a network of no reliability")
    outage_years: int = span(1, 1, 2500, C, "Years an outage lasts")
    war_outage: int = rule(25, 0, 100, C, "Chance a network with a member under siege goes down")
    decay_outage: int = rule(20, 0, 100, C, "Chance a network whose making no member can repair goes down")
    dependency_gain: int = rule(4, 0, 100, C, "Dependency a member gains each epoch the network runs")
    dependency_loss: int = rule(10, 0, 100, C, "Dependency a member loses each epoch the network is down")
    shock_order: int = rule(10, 0, 100, C, "Public order a fully dependent town loses in an outage")
    shock_prosperity: int = rule(8, 0, 100, C, "Prosperity a fully dependent town loses in an outage")
    growth_chance: int = rule(10, 0, 100, C, "Chance each epoch an owner extends its network to a town of its realm")
    growth_cost: int = rule(5, 0, 1000, C, "Treasury a realm spends to join a town to its network")
    rumour_pct: int = rule(50, 0, 400, C, "Added reach of rumours and opinion among members of a network carrying opinion, at full capacity (%)")
    censorship_distrust: int = rule(3, 0, 100, C, "Liberty-valuing members' regard for an owner lost each epoch at full censorship")
    price_pull_pct: int = rule(30, 0, 100, C, "Share of the gap between member markets closed each epoch at full capacity (%)")
    admin_discount_pct: int = rule(30, 0, 100, C, "Share of a dependent member's cost of governance its realm saves at full dependency (%)")
    diffusion_pct: int = rule(40, 0, 400, C, "Added spread of techniques between members of a network carrying records, at full capacity (%)")
    energy_draw: int = rule(10, 0, 100, C, "Energy a member town gives a running network at full capacity each epoch")
    ledger_shock: int = rule(10, 0, 100, C, "Trust the money a network carries loses each time the network goes down")
    shortage_pct: int = rule(50, 0, 100, C, "Share of a member town's energy left unmet at which a network or a mind it keeps goes short (%)")
    command_pct: int = rule(10, 0, 100, C, "Coordination a running network that carries control gives an army in battle (%)")
    confusion_pct: int = rule(15, 0, 100, C, "Coordination an army loses in battle while every network that carries its control is down (%)")

    @property
    def outage_epochs(self) -> int:
        return self.epochs(self.outage_years)

    dream_link_days: int = rule(0, 0, 1000, C, "Days a message takes across a network carried through dreams")
    quake_outage: int = rule(40, 0, 100, C, "Chance a network with a member in a land struck by a quake goes down")
    shutdown_pct: int = rule(20, 0, 100, C, "Chance each epoch an owner whose towns are restless cuts its own network to silence them (%)")
    shutdown_unrest: int = rule(40, 0, 100, C, "Unrest of a member town at which its owner may cut the network")
    shutdown_trust: int = rule(5, 0, 100, C, "Regard each member town loses for an owner that cuts its network")
    gateway_reach_pct: int = rule(50, 0, 200, C, "Added spread of prices and techniques a network gains through each town it shares with another network (%)")
