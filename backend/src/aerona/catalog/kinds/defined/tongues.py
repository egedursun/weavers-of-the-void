from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.tongues import ScriptChangeCause, SenseShift, SoundChangeCause, SoundEnvironment, WordRegister

SCRIPT_CHANGE_CAUSE = total(
    ScriptChangeCause,
    {
        ScriptChangeCause.INVENTION: Defined(
            "Invented",
            checked_by=(),
            used_by=(
                "db.tables.tongues.ScriptRow",
                "engine.phases.writing.adopt_script",
                "engine.tongues.scripts.script_of",
                "services.player.tongues.ScriptDraft",
            ),
        ),
        ScriptChangeCause.REFORM: Defined("Reformed", checked_by=(), used_by=("engine.tongues.scripts.evolve", "tools.mortal.tongues.reform_script")),
        ScriptChangeCause.SIMPLIFICATION: Defined("Worn simpler", checked_by=(), used_by=("engine.tongues.scripts.evolve",)),
        ScriptChangeCause.BORROWING: Defined("Borrowed", checked_by=(), used_by=("engine.tongues.scripts.borrow",)),
    },
)

SENSE_SHIFT = total(
    SenseShift,
    {
        SenseShift.BROADENED: Defined("Broadened", checked_by=("engine.tongues.meaning.shift_word",), used_by=("engine.tongues.meaning.DRIFTS",)),
        SenseShift.NARROWED: Defined("Narrowed", checked_by=("engine.tongues.meaning.shift_word",), used_by=("engine.tongues.meaning.DRIFTS",)),
        SenseShift.PEJORATIVE: Defined("Grew darker", checked_by=(), used_by=("engine.tongues.meaning.DRIFTS",)),
        SenseShift.AMELIORATIVE: Defined("Grew kinder", checked_by=(), used_by=("engine.tongues.meaning.DRIFTS",)),
        SenseShift.EUPHEMISM: Defined("Said instead of a name", checked_by=("engine.tongues.meaning.veiled",), used_by=("engine.tongues.meaning.veil",)),
        SenseShift.RESTORED: Defined("Restored", checked_by=("engine.tongues.meaning.shift_word",), used_by=("engine.tongues.meaning.DRIFTS",)),
    },
)

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

WORD_REGISTER = total(
    WordRegister,
    {
        WordRegister.COMMON: Defined(
            "Common speech",
            checked_by=("engine.tongues.meaning.common_words",),
            used_by=("db.tables.lore.LexemeRow", "engine.tongues.meaning.shift_word", "engine.tongues.meaning.veil"),
        ),
        WordRegister.SACRED: Defined(
            "Sacred speech",
            checked_by=(),
            used_by=("engine.tongues.divine.give_tongue", "engine.tongues.meaning.veil", "engine.tongues.sounds.FIXED_REGISTERS"),
        ),
        WordRegister.POETIC: Defined("Poetry", checked_by=(), used_by=("engine.tongues.sounds.FIXED_REGISTERS",)),
        WordRegister.ARCHAIC: Defined(
            "Archaic",
            checked_by=("engine.tongues.meaning.shift_word",),
            used_by=("engine.tongues.meaning.shift_word", "engine.tongues.sounds.FIXED_REGISTERS", "engine.tongues.sounds.reconstruct"),
        ),
    },
)
