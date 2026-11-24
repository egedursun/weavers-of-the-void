from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.DISEASE


@dataclass(frozen=True)
class DiseaseAgentRules:
    resistance_per_overuse: int = rule(5, 0, 50, G, "Resistance a disease gains when one cure is overused against it")
    overuse_per_use: int = rule(10, 0, 100, G, "Overuse one community's use of a cure adds against a disease each epoch")
    overuse_fade: int = rule(5, 0, 100, G, "Overuse that fades each epoch a disease meets no cure")
    resistance_fade: int = rule(1, 0, 50, G, "Resistance a disease loses each epoch no cure is used against it")
    mutation_virus_pct: int = rule(10, 0, 100, G, "Mutation rate a virus is given (%)")
    mutation_bacterium_pct: int = rule(5, 0, 100, G, "Mutation rate a bacterium is given (%)")
    mutation_fungus_pct: int = rule(3, 0, 100, G, "Mutation rate a fungus is given (%)")
    mutation_parasite_pct: int = rule(2, 0, 100, G, "Mutation rate a parasite is given (%)")
    mutation_prion_pct: int = rule(0, 0, 100, G, "Mutation rate a prion is given (%)")
    survival_water_pct: int = rule(30, 0, 100, G, "Survival in water at which a disease spreads by water (%)")
    survival_soil_pct: int = rule(20, 0, 100, G, "Survival in soil at which a disease lingers in its land after an outbreak (%)")
    survival_object_pct: int = rule(10, 0, 100, G, "Survival on objects at which a disease travels with goods (%)")
    wrong_cure_trust_loss: int = rule(5, 0, 100, G, "Piety a community loses when its healers' cure fails against a disease")
    right_cure_cut: int = rule(10, 0, 100, G, "Severity an outbreak loses when a community uses a cure that works on it")
    identify_level: int = rule(4, 0, 10, G, "Medicine level at which a community tells what a disease is")
    rite_piety: int = rule(60, 0, 100, G, "Piety above which a community answers a sickness first with rites")
    linger_load: int = rule(20, 0, 100, G, "Load a disease that survives in soil or in a reservoir keeps in its land after an outbreak")
    affinity_fit_pct: int = rule(150, 0, 500, G, "Spread of a sickness where its warmth and moisture both suit the land (%)")
    affinity_misfit_pct: int = rule(50, 0, 100, G, "Spread of a sickness where neither its warmth nor its moisture suits the land (%)")


@dataclass(frozen=True)
class CureRules:
    surgery_death_pct: int = rule(15, 0, 100, G, "Chance a cutting cure kills or fails where healers know nothing of cleanliness (%)")
    surgery_infection_pct: int = rule(20, 0, 100, G, "Severity a failed cutting cure adds to an outbreak through infection (%)")
    antiviral_resistance: int = rule(8, 0, 50, G, "Resistance a virus gains when an antiviral is overused against it")
    antiviral_level: int = rule(7, 0, 10, G, "Medicine level a community needs before it can make an antiviral")
    surgery_level: int = rule(3, 0, 10, G, "Medicine level a community needs before its healers cut out a sickness")
    herb_level: int = rule(2, 0, 10, G, "Medicine level a community needs before its healers use herbs")
    immunisation_level: int = rule(4, 0, 20, G, "Medicine level a people needs before it can immunise its folk against a sickness")
