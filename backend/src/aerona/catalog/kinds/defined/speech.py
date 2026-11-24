from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.speech import SpeechAim

SPEECH_AIM = total(
    SpeechAim,
    {
        SpeechAim.PERSUADE: Defined("Persuade", checked_by=(), used_by=("db.tables.speech.SpeechRow", "engine.speech.oratory.RAISING")),
        SpeechAim.TEACH: Defined("Teach", checked_by=(), used_by=("engine.speech.oratory.RAISING",)),
        SpeechAim.MOCK: Defined("Mock", checked_by=("engine.speech.oratory.hear",), used_by=("tools.mortal.speech.satirise",)),
        SpeechAim.MOURN: Defined("Mourn", checked_by=(), used_by=("engine.speech.oratory.RAISING",)),
        SpeechAim.RALLY: Defined(
            "Rally", checked_by=(), used_by=("engine.speech.oratory.RAISING", "engine.speech.oratory.STIRRING", "engine.speech.oratory.rulers_rally")
        ),
        SpeechAim.DEFEND: Defined("Defend", checked_by=(), used_by=("engine.speech.oratory.RAISING",)),
        SpeechAim.ACCUSE: Defined("Accuse", checked_by=("engine.speech.oratory.hear",), used_by=("engine.speech.oratory.STIRRING",)),
        SpeechAim.PRAISE: Defined("Praise", checked_by=(), used_by=("engine.speech.oratory.RAISING",)),
        SpeechAim.WARN: Defined("Warn", checked_by=("engine.speech.oratory.hear",), used_by=("engine.speech.oratory.STIRRING",)),
    },
)
