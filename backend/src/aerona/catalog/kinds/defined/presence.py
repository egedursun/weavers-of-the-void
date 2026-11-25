from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.presence import SpeakerGroup

SPEAKER_GROUP = total(
    SpeakerGroup,
    {
        SpeakerGroup.SONS: Defined(
            "Sons",
            checked_by=("services.presence.speakers.speaker_lines",),
            used_by=("services.presence.speakers.god_lines", "services.presence.speakers.speaker_of", "services.presence.tools.ACTING_GROUPS"),
        ),
        SpeakerGroup.FOREIGN_GODS: Defined(
            "Foreign gods",
            checked_by=("services.presence.speakers.speaker_lines",),
            used_by=("services.presence.speakers.god_lines", "services.presence.speakers.speaker_of"),
        ),
        SpeakerGroup.MORTALS: Defined("Mortals", checked_by=(), used_by=("services.presence.speakers.ENTITY_GROUPS", "services.presence.tools.ACTING_GROUPS")),
        SpeakerGroup.SPIRITS: Defined("Spirits", checked_by=(), used_by=("services.presence.speakers.ENTITY_GROUPS", "services.presence.tools.ACTING_GROUPS")),
        SpeakerGroup.BEINGS: Defined("Beings", checked_by=(), used_by=("services.presence.speakers.ENTITY_GROUPS", "services.presence.tools.READING_GROUPS")),
        SpeakerGroup.BEASTS: Defined(
            "Beasts",
            checked_by=("services.presence.speakers.entity_lines", "services.presence.speakers.speaker_of"),
            used_by=("services.presence.speakers.ENTITY_GROUPS", "services.presence.tools.ACTING_GROUPS"),
        ),
    },
)
