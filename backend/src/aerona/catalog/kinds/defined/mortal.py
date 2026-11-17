from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.mortal import DeathCause, MarriageEnd

DEATH_CAUSE = total(
    DeathCause,
    {
        DeathCause.OLD_AGE: Defined(
            "Old age",
            checked_by=(),
            used_by=(
                "engine.folkways.mishaps.VIOLENT",
                "engine.lifecycle.mortal_death.die",
                "engine.mortal.course.backfill_deaths",
                "engine.mortal.death.HARM_DEATHS",
                "engine.phases.mortals.age_one",
            ),
        ),
        DeathCause.WOUNDS: Defined(
            "Wounds",
            checked_by=(),
            used_by=("engine.body.healing._fester", "engine.body.healing.bled_out", "engine.mortal.course.backfill_deaths", "engine.phases.mortals.succumb"),
        ),
        DeathCause.BATTLE: Defined(
            "Battle",
            checked_by=("engine.mind.ethics.killing_act",),
            used_by=(
                "engine.folkways.mishaps.VIOLENT",
                "engine.mortal.course.DEATH_FLAGS",
                "engine.mortal.death.GLORIOUS_DEATHS",
                "engine.mortal.death.HARM_DEATHS",
                "engine.phases.casualties.fall",
            ),
        ),
        DeathCause.DUEL: Defined(
            "Duel",
            checked_by=("engine.mind.ethics.killing_act",),
            used_by=("engine.folkways.mishaps.VIOLENT", "engine.mortal.death.GLORIOUS_DEATHS", "engine.mortal.death.HARM_DEATHS"),
        ),
        DeathCause.EXECUTION: Defined(
            "Execution",
            checked_by=("engine.mind.ethics.killing_act",),
            used_by=(
                "engine.folkways.mishaps.VIOLENT",
                "engine.law.outlawry.caught",
                "engine.mortal.course.DEATH_FLAGS",
                "engine.mortal.death.HARM_DEATHS",
                "engine.mortal.death.SHAMEFUL_DEATHS",
                "engine.mortal.justice.sentence",
            ),
        ),
        DeathCause.MURDER: Defined(
            "Murder",
            checked_by=(),
            used_by=(
                "catalog.law_depth.METHOD_SEEMING",
                "engine.folkways.mishaps.VIOLENT",
                "engine.intrigue.schemes.murder",
                "engine.military.spy_depth.reprisals",
                "engine.mortal.death.HARM_DEATHS",
                "engine.phases.espionage.assassinate",
                "engine.phases.vendettas.assassinate",
            ),
        ),
        DeathCause.MONSTER: Defined(
            "Monster", checked_by=(), used_by=("engine.mortal.death.GLORIOUS_DEATHS", "engine.mortal.death.HARM_DEATHS", "engine.phases.heroism._hero_loses")
        ),
        DeathCause.DISEASE: Defined(
            "Disease", checked_by=("engine.folkways.mishaps.deaths_in",), used_by=("catalog.law_depth.METHOD_SEEMING", "engine.mortal.course.DEATH_FLAGS")
        ),
        DeathCause.CHILDBIRTH: Defined("Childbirth", checked_by=(), used_by=("engine.phases.births.deliver",)),
        DeathCause.FAMINE: Defined("Famine", checked_by=(), used_by=("engine.demography.promotion.starve_named",)),
        DeathCause.ACCIDENT: Defined(
            "Accident", checked_by=("engine.folkways.mishaps.deaths_in",), used_by=("catalog.law_depth.METHOD_SEEMING", "engine.mortal.death.HARM_DEATHS")
        ),
        DeathCause.DISASTER: Defined(
            "Disaster", checked_by=(), used_by=("engine.mortal.course.DEATH_FLAGS", "engine.mortal.death.HARM_DEATHS", "engine.phases.disasters._strike_mortal")
        ),
        DeathCause.EXPOSURE: Defined("Exposure", checked_by=(), used_by=("engine.households.life.give_up_infant", "engine.mortal.death.HARM_DEATHS")),
        DeathCause.CURSE: Defined("Curse", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.MAGIC: Defined("Magic", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.DIVINE: Defined(
            "Divine",
            checked_by=(),
            used_by=(
                "engine.gods.deification.deify",
                "engine.lifecycle.mortal_death.force_death",
                "engine.mortal.death.HARM_DEATHS",
                "engine.records.retire_record",
            ),
        ),
        DeathCause.POISON: Defined("Poison", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.SACRIFICE: Defined(
            "Sacrifice",
            checked_by=("engine.mind.ethics.killing_act",),
            used_by=("engine.folkways.mishaps.VIOLENT", "engine.mortal.death.GLORIOUS_DEATHS", "engine.mortal.death.HARM_DEATHS"),
        ),
        DeathCause.HARDSHIP: Defined("Hardship", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS", "engine.phases.heroes._quest_failed")),
        DeathCause.DESPAIR: Defined(
            "Despair", checked_by=("engine.mind.ethics.killing_act",), used_by=("engine.mortal.acts.despair", "engine.mortal.death.SHAMEFUL_DEATHS")
        ),
        DeathCause.UNKNOWN: Defined(
            "Unknown",
            checked_by=(),
            used_by=(
                "catalog.law_depth.METHOD_SEEMING",
                "engine.lifecycle.mortal_death.die",
                "engine.mortal.course.backfill_deaths",
                "engine.mortal.death.manner_of",
            ),
        ),
        DeathCause.INDUSTRIAL: Defined("Industrial", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.CRASH: Defined("Crash", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.RADIATION: Defined("Radiation", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.DECOMPRESSION: Defined("Decompression", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.EXPERIMENT: Defined("Experiment", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
        DeathCause.BOMBARDMENT: Defined("Bombardment", checked_by=(), used_by=("engine.mortal.death.HARM_DEATHS",)),
    },
)

MARRIAGE_END = total(
    MarriageEnd,
    {
        MarriageEnd.DEATH: Defined(
            "Death", checked_by=("engine.cycles.kinship.keep_kinship",), used_by=("engine.mortal.kinship.backfill_kin", "engine.mortal.kinship.widow")
        ),
        MarriageEnd.DIVORCE: Defined(
            "Divorce",
            checked_by=(),
            used_by=("engine.mortal.course.end_marriages", "engine.relations.affairs.consequences", "services.player.mortals.EndMarriage"),
        ),
        MarriageEnd.ANNULMENT: Defined("Annulment", checked_by=(), used_by=("engine.mortal.course.end_marriages",)),
        MarriageEnd.WAR: Defined("War", checked_by=(), used_by=("engine.mortal.course.end_marriages",)),
        MarriageEnd.TERM: Defined("Its term ended by custom", checked_by=(), used_by=("engine.unions.keep.end_terms",)),
    },
)
