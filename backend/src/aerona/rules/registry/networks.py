from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.INTERCONNECTION


@dataclass(frozen=True)
class NetworkRules:
    days_per_epoch: int = rule(360, 1, 10000, C, "Days in an epoch, against which a network's delay is counted")
    relay_days: int = rule(20, 0, 1000, C, "Days a message takes across a relay network")
    wired_days: int = rule(1, 0, 1000, C, "Days a message takes across a wired network")
    broadcast_days: int = rule(0, 0, 1000, C, "Days a message takes across a broadcast network")
    mesh_days: int = rule(3, 0, 1000, C, "Days a message takes across a mesh network")
    mind_link_days: int = rule(0, 0, 1000, C, "Days a message takes across minds joined directly")
    rite_link_days: int = rule(1, 0, 1000, C, "Days a message takes across a network bound by a working")
    grown_link_days: int = rule(5, 0, 1000, C, "Days a message takes across a living connection")
    interworld_days: int = rule(360, 0, 100000, C, "Days a message takes through a gateway to another world")
    outage_base: int = rule(5, 0, 100, C, "Chance of an outage each epoch for a network of no reliability")
    outage_epochs: int = rule(1, 1, 100, C, "Epochs an outage lasts")
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
