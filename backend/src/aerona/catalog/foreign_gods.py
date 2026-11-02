from dataclasses import dataclass

from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus

F = ForeignGodPowerEffect


@dataclass(frozen=True)
class ForeignGodPowerSpec:
    effect: ForeignGodPowerEffect
    label: str
    effect_text: str


FOREIGN_GOD_POWERS: dict[ForeignGodPowerEffect, ForeignGodPowerSpec] = {
    spec.effect: spec
    for spec in (
        ForeignGodPowerSpec(F.SHIELD, "Shield", "Stronger in battle."),
        ForeignGodPowerSpec(F.CALLER, "Caller", "Draws unclaimed communities to its worship."),
        ForeignGodPowerSpec(F.THIEF, "Worshipper-thief", "Steals the sons' worshippers more often."),
        ForeignGodPowerSpec(F.DESTROYER, "Destroyer", "Attacks more often."),
        ForeignGodPowerSpec(F.FERTILE, "Bountiful", "Its friends prosper more."),
        ForeignGodPowerSpec(F.REVIVING, "Reviving", "Wakes sooner after a defeat."),
        ForeignGodPowerSpec(F.DEATHLESS, "Deathless", "Never dies even in a crushing defeat; it is only defeated."),
        ForeignGodPowerSpec(F.SHARP_TONGUED, "Sharp-tongued", "Sons who parley with it are at a disadvantage."),
    )
}

FOREIGN_GOD_STATUS_LABELS: dict[ForeignGodStatus, str] = {
    ForeignGodStatus.AWAKE: "Awake",
    ForeignGodStatus.ASLEEP: "Asleep",
    ForeignGodStatus.DEFEATED: "Defeated",
    ForeignGodStatus.DEAD: "Dead",
}
