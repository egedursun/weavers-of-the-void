from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.REPUTATION


@dataclass(frozen=True)
class SpeechRules:
    persuasion_pct: int = rule(20, 0, 100, S, "Effect a speech at full skill and full reach has on its audience")
    satire_legitimacy_loss: int = rule(5, 0, 100, S, "Legitimacy a realm loses each epoch where satire of rulers is tolerated and spread by an outlet")
    offence_threshold: int = rule(50, 0, 100, S, "Offence threshold a people holds where its humour style sets none")
    humour_ease_pct: int = rule(10, 0, 100, S, "Honour a speaker gains from mockery its people allows, in tenths of the effect")
    ruler_speech_pct: int = rule(20, 0, 100, S, "Chance each epoch that the ruler of a restless realm speaks to rally it")
    restless_at: int = rule(50, 0, 100, S, "Unrest of a seat at which its ruler is moved to speak")
    punishment_honour: int = rule(15, 0, 100, S, "Honour a speaker loses when mockery of rulers is punished")
