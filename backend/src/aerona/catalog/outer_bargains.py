from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.divine import BargainGain, BargainPrice
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class GainSpec:
    label: str
    size: Callable[[Rules], int]


@dataclass(frozen=True)
class PriceSpec:
    label: str
    weight: Callable[[Rules], int]
    lasting: bool = False


BARGAIN_GAINS: Mapping[BargainGain, GainSpec] = total(
    BargainGain,
    {
        BargainGain.ESSENCE: GainSpec("Essence", lambda rules: rules.outer_bargains.essence_size),
        BargainGain.POWER: GainSpec("A power", lambda rules: rules.outer_bargains.power_size),
        BargainGain.MIGHT: GainSpec("Might", lambda rules: rules.outer_bargains.might_size),
        BargainGain.KNOWLEDGE: GainSpec("Knowledge out of reach", lambda rules: rules.outer_bargains.knowledge_size),
        BargainGain.LONGEVITY: GainSpec("A longer span", lambda rules: rules.outer_bargains.longevity_size),
    },
)

BARGAIN_PRICES: Mapping[BargainPrice, PriceSpec] = total(
    BargainPrice,
    {
        BargainPrice.WORLD_SANITY: PriceSpec("A world's sanity", lambda rules: rules.outer_bargains.world_sanity_weight),
        BargainPrice.DOMAIN: PriceSpec("A domain", lambda rules: rules.outer_bargains.domain_weight),
        BargainPrice.TRUE_NAME: PriceSpec("A true name", lambda rules: rules.outer_bargains.true_name_weight),
        BargainPrice.WORSHIPPERS: PriceSpec("The souls of the faithful", lambda rules: rules.outer_bargains.worshippers_weight),
        BargainPrice.DESCENDANTS: PriceSpec("The bargainer's line", lambda rules: rules.outer_bargains.descendants_weight, lasting=True),
    },
)
