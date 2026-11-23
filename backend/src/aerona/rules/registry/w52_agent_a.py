from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

M = RuleGroup.DEATH_AND_RESURRECTION
A = RuleGroup.HEROES_AND_MORTALS
MIND = RuleGroup.MIND


@dataclass(frozen=True)
class DeathReadingRules:
    martial_glory_pct: int = rule(50, 0, 100, M, "How far a people's love of war turns a death in a fight toward glory (%)")
    honour_shame_pct: int = rule(50, 0, 100, M, "How far a people's sense of honour turns a judged or self-sought death toward shame (%)")
    piety_offering_pct: int = rule(50, 0, 100, M, "How far a people's piety turns a death offered to a god toward glory (%)")
    death_rest_pct: int = rule(30, 0, 100, M, "How far a people's regard for death honours a quiet death (%)")
    dread_curse_pct: int = rule(50, 0, 100, M, "How far a people's dread of the uncanny turns a death by curse or power toward a curse (%)")
    glorious_at: int = rule(60, 0, 100, M, "Reading above which a people holds a death glorious")
    honourable_at: int = rule(25, 0, 100, M, "Reading above which a people holds a death honourable")
    shameful_at: int = rule(25, 0, 100, M, "Reading below the negative of which a people holds a death shameful")
    cursed_at: int = rule(60, 0, 100, M, "Reading below the negative of which a people holds a death cursed")
    glorious_renown: int = rule(5, 0, 100, M, "Renown a mortal's name keeps after a death their people hold glorious")
    lament_pct: int = rule(150, 0, 500, M, "How much more kin lament a death their people hold glorious or cursed (%)")


@dataclass(frozen=True)
class FuneralRules(Spanned):
    mummification_cost: int = rule(30, 0, 500, M, "Treasury a people spends on preserving each of its dead")
    secondary_rite_years: int = span(3, 0, 50, M, "Years between laying the dead to rest and gathering the bones in a second rite")
    second_rite_cohesion: int = rule(2, 0, 50, M, "Cohesion a people gains from each gathering of its dead in a second rite")
    preserved_draw_pct: int = rule(50, 0, 300, M, "How much more a preserved body draws grave robbers (%)")


@dataclass(frozen=True)
class PackageRules:
    fortune_roll_pct: int = rule(15, 0, 100, A, "How far a fortune shifts every chance rolled for its holder, at full strength (%)")
    fortune_line_pct: int = rule(50, 0, 100, A, "Chance a line's fortune passes to each child (%)")
    fortune_strength: int = rule(60, 0, 100, A, "Strength a fortune is laid with when no other strength is set")
    transform_recur_pct: int = rule(100, 0, 100, A, "Chance a changed body changes again when its sign comes (%)")
    charm_strength: int = rule(60, 0, 100, A, "Strength a charm is laid with")
    charm_fade: int = rule(5, 0, 50, A, "Strength a charm loses each epoch it is not renewed")
    charm_renew_cost: int = rule(10, 0, 500, A, "Treasury the charmer pays each epoch to keep a fading charm at full strength")
    charm_pull: int = rule(10, 0, 100, A, "Warmth toward its target a charm stirs in the charmed each epoch, at full strength")
    unkept_mind_pct: int = rule(20, 0, 100, A, "Intellect and charisma a changed body loses while it does not keep its own mind")


@dataclass(frozen=True)
class EmotionRules:
    joy_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of joy that fades each epoch (%)")
    contentment_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of contentment that fades each epoch (%)")
    pride_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of pride that fades each epoch (%)")
    love_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of love that fades each epoch (%)")
    gratitude_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of gratitude that fades each epoch (%)")
    relief_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of relief that fades each epoch (%)")
    hope_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of hope that fades each epoch (%)")
    awe_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of awe that fades each epoch (%)")
    amusement_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of amusement that fades each epoch (%)")
    fear_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of fear that fades each epoch (%)")
    anxiety_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of anxiety that fades each epoch (%)")
    anger_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of anger that fades each epoch (%)")
    rage_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of rage that fades each epoch (%)")
    grief_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of grief that fades each epoch (%)")
    sadness_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of sadness that fades each epoch (%)")
    shame_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of shame that fades each epoch (%)")
    guilt_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of guilt that fades each epoch (%)")
    envy_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of envy that fades each epoch (%)")
    jealousy_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of jealousy that fades each epoch (%)")
    disgust_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of disgust that fades each epoch (%)")
    loneliness_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of loneliness that fades each epoch (%)")
    boredom_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of boredom that fades each epoch (%)")
    despair_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of despair that fades each epoch (%)")
    longing_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of longing that fades each epoch (%)")
    surprise_decay: int = rule(50, 0, 50, MIND, "Share of a feeling of surprise that fades each epoch (%)")
    curiosity_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of curiosity that fades each epoch (%)")
    compassion_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of compassion that fades each epoch (%)")
    contempt_decay: int = rule(30, 0, 50, MIND, "Share of a feeling of contempt that fades each epoch (%)")
    surprise_act_weight: int = rule(30, 0, 100, MIND, "How much a surprise sharpens the next feeling of the same epoch (%)")
    curiosity_act_weight: int = rule(30, 0, 100, MIND, "Chance a strong curiosity sends its holder to study, explore or seek out strangers (%)")
    compassion_act_weight: int = rule(30, 0, 100, MIND, "Chance a strong compassion moves its holder to give to the one who suffers (%)")
    contempt_act_weight: int = rule(30, 0, 100, MIND, "Chance a strong contempt moves its holder to insult or shut out the one held low (%)")
    felt_intensity: int = rule(40, 0, 100, MIND, "Strength a feeling of one of these four must reach before it moves its holder to act")
    surprise_share_pct: int = rule(60, 0, 100, MIND, "Strength of a surprise against the unexpected happening that stirred it (%)")
    compassion_gift: int = rule(3, 0, 100, MIND, "Wealth a moved holder gives to the one who suffers")
    contempt_insult: int = rule(10, 0, 100, MIND, "Ill will an insult from contempt leaves in the one held low")
    curiosity_xp: int = rule(20, 0, 500, MIND, "Practice a strong curiosity gives in study")


@dataclass(frozen=True)
class BreakRules(Spanned):
    withdrawal_years: int = span(5, 0, 100, MIND, "Years one who withdraws stops acting, leaving office and duties")
    withdrawal_care_cut: int = rule(30, 0, 100, MIND, "How much care from a healer shortens a withdrawal (%)")
    withdrawal_ease: int = rule(10, 0, 100, MIND, "Stress a withdrawn mortal sheds each epoch of rest")
