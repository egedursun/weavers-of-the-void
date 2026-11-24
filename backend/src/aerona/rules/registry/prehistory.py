from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.COSMOS


@dataclass(frozen=True)
class PrehistoryRules:
    epochs: int = rule(0, 0, 1000, C, "Epochs of prehistory a world the Creator makes runs before it joins the cosmos, unless the making names its own length")
    son_world_epochs: int = rule(0, 0, 1000, C, "Epochs of prehistory a world born of a son runs before it joins the cosmos")
    resolution: int = rule(1, 1, 20, C, "Rounds of a prehistory between runs of its coarse steps (war, diplomacy, spread of knowledge, accounts and legends)")
    digest_size: int = rule(12, 1, 200, C, "Happenings of a prehistory, by magnitude, kept in its digest for Fate, the chronicler and the book")
    son_seed_cost: int = rule(60, 0, 100000, C, "Essence a son spends to give a world it made, still empty of lore, a prehistory")
    seed_cost: int = rule(300, 0, 100000, C, "Essence the Creator spends to seed a prehistory for a world still empty of lore")
    deep_time_max_epochs: int = rule(100, 1, 1000, C, "Most epochs one fast-forward of deep time may run")
    deep_time_cost: int = rule(50, 0, 100000, C, "Essence the Creator spends for each epoch of a fast-forward of deep time")
    deep_time_digest_size: int = rule(12, 1, 200, C, "Happenings of a fast-forward, by magnitude, kept in its digest")
    ruin_prosperity: int = rule(30, 0, 100, C, "Prosperity each community of a made world loses when its prehistory ends with its makers gone")
