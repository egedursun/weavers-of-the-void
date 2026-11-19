from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class GeomorphologyRules(Spanned):
    desert_rainfall_below: int = rule(30, 0, 100, G, "A land can turn to desert while its rainfall is below this")
    overgrazed_above: int = rule(40, 0, 100, G, "A land is overgrazed when more of it than this is grazed")
    desertify_rate: int = rule(12, 0, 100, G, "Desertification a dry, overgrazed land gains per epoch")
    drought_desertify: int = rule(10, 0, 100, G, "Desertification added when a drought strikes a dry, overgrazed land")
    desert_recover_rate: int = rule(6, 0, 100, G, "Desertification a rested, watered land loses per epoch")
    desertified_at: int = rule(70, 1, 100, G, "Desertification at which a land becomes desert")
    desert_recovered_below: int = rule(30, 0, 100, G, "Desertification below which a desert land recovers")
    desert_rainfall_drop: int = rule(10, 0, 100, G, "Rainfall a desert land loses as its bare ground stops holding water")
    desert_soil_base_drop: int = rule(15, 0, 100, G, "Natural soil fertility lost when a land turns to desert")
    salt_flat_rainfall_below: int = rule(15, 0, 100, G, "A desert land without a river turns to salt flat below this rainfall")
    salted_earth_salt_depth: int = rule(40, 0, 100, G, "Depth of salted earth at which the soil itself turns to salt")
    river_shift_severity: int = rule(60, 0, 100, G, "Flood severity at which a river can leave its bed")
    river_shift_chance: int = rule(25, 0, 100, G, "Chance a great flood moves the river into a neighbouring land (%)")
    volcanic_pressure_gain: int = rule(6, 0, 100, G, "Pressure a volcanic land builds per epoch")
    eruption_base_chance: int = rule(2, 0, 100, G, "Base chance of an eruption in a volcanic land (%)")
    eruption_pressure_pct: int = rule(12, 0, 100, G, "Eruption chance added per point of volcanic pressure (%)")
    volcanic_quake_relief: int = rule(20, 0, 100, G, "Pressure a volcanic earthquake releases")
    volcanic_quake_eruption_chance: int = rule(25, 0, 100, G, "Chance a volcanic earthquake wakes an eruption (%)")
    volcanic_quake_pct: int = rule(150, 100, 1000, G, "Strength of a volcanic earthquake against an ordinary one (%)")
    eruption_population_loss: int = rule(10, 0, 100, G, "Population an eruption kills at full strength (%)")
    eruption_prosperity_loss: int = rule(15, 0, 100, G, "Prosperity an eruption buries")
    eruption_durability_loss: int = rule(30, 0, 100, G, "Durability an eruption takes from structures")
    eruption_mortal_death_chance: int = rule(15, 0, 100, G, "Chance a named mortal dies in an eruption (%)")
    eruption_burn_depth_pct: int = rule(30, 0, 200, G, "Burned ground left per point of eruption severity (%)")
    ash_weathering_years: int = span(100, 1, 2500, G, "Years before fresh ash weathers into rich volcanic soil")

    @property
    def ash_weathering_epochs(self) -> int:
        return self.epochs(self.ash_weathering_years)
