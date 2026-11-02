from dataclasses import dataclass

from aerona.domain.enums.meta import AchievementKey, ScenarioKey

S = ScenarioKey
A = AchievementKey


@dataclass(frozen=True)
class GoalSpec[K]:
    key: K
    name: str
    description: str


SCENARIOS: dict[ScenarioKey, GoalSpec[ScenarioKey]] = {
    spec.key: spec
    for spec in (
        GoalSpec(S.DOOM_FAR, "Keep doomsday away", "The doomsday clock must stay below its warning mark for the whole trial."),
        GoalSpec(S.ONE_FAITH, "Unite all peoples in one faith", "Every people of the world worships the same god, a son or you."),
        GoalSpec(S.LOST_STAR, "Rekindle the lost star", "A dead star or black sun burns again."),
        GoalSpec(S.MANY_WORLDS, "A cosmos of many worlds", "Enough worlds in the cosmos, each with a living people."),
        GoalSpec(S.LONG_PEACE, "A long peace", "No war stays open for many consecutive epochs."),
        GoalSpec(S.COSMIC_POWER, "A civilization reaching for the stars", "A people reaches the civilization tier of an interstellar power."),
        GoalSpec(S.LOYAL_PANTHEON, "A loyal pantheon", "No son rebels for many epochs and every son stays loyal."),
        GoalSpec(S.NEW_HORIZONS, "New horizons", "New lands and regions enter the map, by mortals, sons or your hand."),
    )
}

ACHIEVEMENTS: dict[AchievementKey, GoalSpec[AchievementKey]] = {
    spec.key: spec
    for spec in (
        GoalSpec(A.SECOND_SKY, "Another sky", "The cosmos holds more than one world."),
        GoalSpec(A.CONSTELLATION, "Constellation", "A cosmos of many stars."),
        GoalSpec(A.PROPHECY_FULFILLED, "The word came true", "A prophecy was fulfilled."),
        GoalSpec(A.RETURN_FROM_DEATH, "Return from death", "A dead son was resurrected."),
        GoalSpec(A.FATHERS_HAND, "The father's hand", "A rebellion was suppressed."),
        GoalSpec(A.BABEL, "Babel", "Many languages are spoken."),
        GoalSpec(A.CROWDED_WORLD, "Crowded world", "The peoples have grown beyond counting."),
        GoalSpec(A.FIRST_PRAYER, "Someone called you", "A mortal prayed directly to you."),
        GoalSpec(A.CREATORS_CULT, "The creator's cult", "Several communities worship you directly."),
        GoalSpec(A.INTERSTELLAR_TRAVELLER, "Interstellar traveller", "A journey reached another world."),
        GoalSpec(A.SAGA_COMPLETED, "Saga completed", "A legendary quest ended in success."),
        GoalSpec(A.GOD_OF_EPOCHS, "God of epochs", "The world left many epochs behind."),
        GoalSpec(A.ANCIENT, "Ancient", "The world left a great many epochs behind."),
        GoalSpec(A.CROWDED_PANTHEON, "Crowded pantheon", "Many sons live at once."),
        GoalSpec(A.FIRST_EXPLORERS, "First explorers", "Mortals found a land that was not on the map."),
        GoalSpec(A.SENSED_WORLD, "Sensed world", "A world sensed by sky-watching mortals came to light."),
        GoalSpec(A.WEAPONS_SILENT, "The weapons fell silent", "An epoch ended without any war among many peoples."),
    )
}
