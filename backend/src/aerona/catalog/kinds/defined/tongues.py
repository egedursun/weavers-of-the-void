from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.tongues import SoundChangeCause, SoundEnvironment

SOUND_CHANGE_CAUSE = total(
    SoundChangeCause,
    {
        SoundChangeCause.CONTACT: Defined("Contact with other tongues", checked_by=(), used_by=("engine.tongues.sounds.acquire",)),
        SoundChangeCause.PRESTIGE: Defined("A prestigious neighbour", checked_by=(), used_by=("engine.tongues.sounds.acquire",)),
        SoundChangeCause.MIGRATION: Defined("A move to new lands", checked_by=(), used_by=("engine.tongues.sounds.acquire",)),
        SoundChangeCause.DRIFT: Defined("Drift of time", checked_by=(), used_by=("db.tables.tongues.SoundChangeRow", "engine.tongues.sounds.acquire")),
        SoundChangeCause.INHERITED: Defined("Inherited from its parent", checked_by=(), used_by=("engine.tongues.sounds.inherit",)),
        SoundChangeCause.DECREE: Defined("A divine decree", checked_by=(), used_by=("services.player.tongues.add_change", "tools.son.tongues.decree_sound")),
    },
)

SOUND_ENVIRONMENT = total(
    SoundEnvironment,
    {
        SoundEnvironment.ANYWHERE: Defined(
            "Anywhere in a word",
            checked_by=(),
            used_by=(
                "db.tables.tongues.SoundChangeRow",
                "engine.tongues.sounds.assimilate",
                "engine.tongues.sounds.insert_vowel",
                "engine.tongues.sounds.merge",
                "engine.tongues.sounds.metathesise",
                "engine.tongues.sounds.palatalise",
                "services.player.tongues.ChangeDraft",
                "tools.son.tongues.DecreeSoundInput",
            ),
        ),
        SoundEnvironment.INITIAL: Defined("At the start of a word", checked_by=("engine.tongues.sounds.fits",), used_by=()),
        SoundEnvironment.FINAL: Defined(
            "At the end of a word", checked_by=("engine.tongues.sounds.fits",), used_by=("engine.tongues.sounds.lose", "engine.tongues.sounds.tone")
        ),
        SoundEnvironment.BETWEEN_VOWELS: Defined("Between vowels", checked_by=("engine.tongues.sounds.fits",), used_by=("engine.tongues.sounds.lenite",)),
    },
)
