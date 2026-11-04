from aerona.constants.units import PERCENT
from aerona.domain.enums.mortal import HarshnessProfile, HarshnessScale
from aerona.rules.registry import Rules


def harshness_profile(rules: Rules) -> HarshnessProfile:
    return HarshnessProfile(max(HarshnessProfile.HEROIC, min(HarshnessProfile.BRUTAL, int(rules.harshness.profile))))


def harshness(rules: Rules, scale: HarshnessScale) -> float:
    profile = harshness_profile(rules)
    value: int = getattr(rules.harshness, f"{profile.name.lower()}_{scale.value}_pct")
    return max(0.0, value / PERCENT)


def harsh_chance(rules: Rules, scale: HarshnessScale, chance: float) -> float:
    return max(0.0, min(float(PERCENT), chance * harshness(rules, scale)))
