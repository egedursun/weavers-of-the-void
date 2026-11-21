from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

R = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class SeaWavesRules(Spanned):
    quake_wave_chance_pct: int = rule(
        20, 0, 100, R, "Chance that a quake, eruption or blow from the sky beside a sea raises a great wave, at full strength (%)"
    )
    storm_surge_chance_pct: int = rule(10, 0, 100, R, "Chance that a strong storm beside a sea drives a surge onto its coasts, at full strength (%)")
    harm_per_height: int = rule(5, 0, 50, R, "Harm a wave does for each point of its height; a hundred points at five is a full strike")
    warning_death_cut_pct: int = rule(60, 0, 100, R, "Share of the harm a warning spares those on a coast (%)")
    decay_per_hop: int = rule(15, 0, 100, R, "Height a wave loses for each region it crosses")
    floor: int = rule(10, 0, 100, R, "Height below which a wave does no harm")
    salt_height: int = rule(50, 0, 100, R, "Height at which a wave salts the land it floods")
    salt_fertility: int = rule(10, 0, 100, R, "Soil fertility a coast loses when salted")
    observation_floor: int = rule(40, 0, 100, R, "Accuracy at which a people's watching of the waters warns its coasts of a wave unbidden")
    warning_years: int = span(10, 0, 500, R, "Years a warning given on a coast holds")
    slide_pct: int = rule(30, 0, 100, R, "Chance that an eruption beside a sea sends its flank sliding into it, raising a greater wave (%)")
    storm_floor_pct: int = rule(50, 0, 100, R, "Strength of a storm at which it may drive a surge (%)")

    @property
    def warning_epochs(self) -> int:
        return self.epochs(self.warning_years)
