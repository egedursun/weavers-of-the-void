from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class ItemPowersRules:
    tool_quality: int = rule(10, 0, 100, H, "Quality a forge gains when its smiths hold good tools")
    knowledge_quality: int = rule(3, 0, 100, H, "Quality each level of metallurgy lends a crafted thing")
    instrument_cohesion: int = rule(2, 0, 100, H, "Cohesion a people gains each epoch from the music of its instruments")
    mirror_intel: int = rule(5, 0, 100, H, "Intelligence a seeing-mirror yields on its holder's nearest foe each epoch")
    vessel_faith: int = rule(2, 0, 100, H, "Faith a libation vessel pours to its keepers' god each epoch")
    key_defense: int = rule(3, 0, 100, H, "Defence a town keeps while the keys to its gates are held at home")
    jewel_prestige: int = rule(2, 0, 100, H, "House prestige each ten points of a treasure's worth lend its house each epoch")
    currency_prosperity: int = rule(2, 0, 100, H, "Prosperity a hoard of coin lends the community that keeps it")
    idol_zeal: int = rule(2, 0, 100, H, "Zeal an idol stirs in the cult that keeps it")
    map_journey: int = rule(1, 0, 10, H, "Epochs a map or astrolabe spares a journey")
    prosthesis_quality: int = rule(10, 0, 100, H, "Quality a crafted limb lends the prosthesis it is fitted as")
    spirit_guard: int = rule(5, 0, 100, H, "Cover a guardian spirit bound in a thing lends its bearer")
    spirit_curse: int = rule(5, 0, 100, H, "Harm a vengeful spirit bound in a thing deals its bearer each epoch")
    value_material_pct: int = rule(50, 0, 300, H, "Weight of the material's worth in a thing's value (%)")
    value_enchant: int = rule(2, 0, 100, H, "Worth each ten points of enchantment add to a thing")
    weight_fatigue_pct: int = rule(20, 0, 300, H, "Stamina each point of carried weight costs a fighter per exchange (%)")
    duel_wear: int = rule(1, 0, 100, H, "Condition a weapon or armour loses with each exchange of a duel")
    repair_units: int = rule(1, 0, 100, H, "Units of its own material a repair consumes")
    seize_chance: int = rule(30, 0, 100, H, "A ruler who lacks the realm's regalia seizes them from their keeper (%)")
    relic_faith: int = rule(2, 0, 100, H, "Faith a healing at a relic brings the god of its cult")
    betrayal_opinion: int = rule(10, 0, 100, H, "Ill will a betraying curse breeds in its bearer toward their liege, per epoch at full curse")
    wrathful_curse: int = rule(50, 0, 100, H, "Curse at which a bloodthirsty thing makes its bearer wrathful and quarrelsome")
    provocation: int = rule(30, 0, 100, H, "Insult a bloodthirsty bearer takes from the strongest rival nearby, seeking a duel")


@dataclass(frozen=True)
class EnchantmentsRules:
    damage_pct: int = rule(20, 0, 300, H, "Weight a war enchantment adds to its wielder's blows (% of its strength)")
    ward_pct: int = rule(30, 0, 300, H, "Cover a warding enchantment lends (% of its strength)")
    heal_pct: int = rule(10, 0, 100, H, "Function a healing enchantment restores to its bearer's wounds each epoch (% of its strength)")
    bless_pct: int = rule(5, 0, 100, H, "Prosperity a blessing enchantment brings its bearer's home each epoch (% of its strength)")
    curse_pct: int = rule(5, 0, 100, H, "Harm a cursing enchantment deals its bearer each epoch (% of its strength)")
    scry_pct: int = rule(5, 0, 100, H, "Intelligence a scrying enchantment yields each epoch (% of its strength)")
    harvest_pct: int = rule(5, 0, 100, H, "Harvest a fertile enchantment brings its bearer's land (% of its strength)")
