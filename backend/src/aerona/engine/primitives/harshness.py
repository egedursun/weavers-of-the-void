from aerona.constants.units import PERCENT
from aerona.domain.enums.mortal import HarshnessProfile, HarshnessScale
from aerona.rules.registry import Rules


def harshness_profile(rules: Rules) -> HarshnessProfile:
    return HarshnessProfile(max(HarshnessProfile.HEROIC, min(HarshnessProfile.BRUTAL, int(rules.harshness.profile))))


def profile_values(rules: Rules, profile: HarshnessProfile) -> dict[HarshnessScale, int]:
    table = rules.harshness
    values = {
        HarshnessProfile.HEROIC: {
            HarshnessScale.WOUND_LETHALITY: table.heroic_wound_lethality_pct,
            HarshnessScale.INFECTION: table.heroic_infection_pct,
            HarshnessScale.PERMANENT_INJURY: table.heroic_permanent_injury_pct,
            HarshnessScale.DISEASE_DEATH: table.heroic_disease_death_pct,
            HarshnessScale.FAMINE_DEATH: table.heroic_famine_death_pct,
            HarshnessScale.CHILDBIRTH_DEATH: table.heroic_childbirth_death_pct,
            HarshnessScale.BATTLE_LOSS: table.heroic_battle_loss_pct,
            HarshnessScale.NOTABLE_SURVIVAL: table.heroic_notable_survival_pct,
        },
        HarshnessProfile.REALISTIC: {
            HarshnessScale.WOUND_LETHALITY: table.realistic_wound_lethality_pct,
            HarshnessScale.INFECTION: table.realistic_infection_pct,
            HarshnessScale.PERMANENT_INJURY: table.realistic_permanent_injury_pct,
            HarshnessScale.DISEASE_DEATH: table.realistic_disease_death_pct,
            HarshnessScale.FAMINE_DEATH: table.realistic_famine_death_pct,
            HarshnessScale.CHILDBIRTH_DEATH: table.realistic_childbirth_death_pct,
            HarshnessScale.BATTLE_LOSS: table.realistic_battle_loss_pct,
            HarshnessScale.NOTABLE_SURVIVAL: table.realistic_notable_survival_pct,
        },
        HarshnessProfile.BRUTAL: {
            HarshnessScale.WOUND_LETHALITY: table.brutal_wound_lethality_pct,
            HarshnessScale.INFECTION: table.brutal_infection_pct,
            HarshnessScale.PERMANENT_INJURY: table.brutal_permanent_injury_pct,
            HarshnessScale.DISEASE_DEATH: table.brutal_disease_death_pct,
            HarshnessScale.FAMINE_DEATH: table.brutal_famine_death_pct,
            HarshnessScale.CHILDBIRTH_DEATH: table.brutal_childbirth_death_pct,
            HarshnessScale.BATTLE_LOSS: table.brutal_battle_loss_pct,
            HarshnessScale.NOTABLE_SURVIVAL: table.brutal_notable_survival_pct,
        },
    }
    return values[profile]


def harshness(rules: Rules, scale: HarshnessScale) -> float:
    return max(0.0, profile_values(rules, harshness_profile(rules))[scale] / PERCENT)


def harsh_chance(rules: Rules, scale: HarshnessScale, chance: float) -> float:
    return max(0.0, min(float(PERCENT), chance * harshness(rules, scale)))
