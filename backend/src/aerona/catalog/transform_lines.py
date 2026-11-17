from types import MappingProxyType

from aerona.catalog.god_lines import Line
from aerona.domain.enums.transform import TransformKind

K = TransformKind

LINES = MappingProxyType(
    {
        K.DEIFICATION: Line("transform.deification", "{subject} was raised from mortal life to godhood as {result}."),
        K.MANTLING: Line("transform.mantling", "{subject} took up a god's mantle and became {result}."),
        K.SPIRIT_RISING: Line("transform.spirit_rising", "{subject} died and rose again as the spirit {result}."),
        K.REINCARNATION: Line("transform.reincarnation", "The spirit {subject} was born again as {result}."),
        K.POSSESSION: Line("transform.possession", "The spirit {subject} took {result} as its host."),
        K.LOCAL_GOD: Line("transform.local_god", "The spirit {subject} was worshipped until it stood as the local god {result}."),
        K.BEAST_CURSE: Line("transform.beast_curse", "A curse turned {subject} into a beast."),
        K.CURSE_LIFTED: Line("transform.curse_lifted", "The curse on {subject} was lifted and {result} walked again in their own shape."),
        K.UPLIFT: Line("transform.uplift", "The kind {subject} woke to speech and reckoning and became the people {result}."),
        K.CITY_STATE: Line("transform.city_state", "{subject} ruled itself and became the realm {result}."),
        K.SECESSION: Line("transform.secession", "{subject} broke away and became the realm {result}."),
        K.THEOCRACY: Line("transform.theocracy", "The faith {subject} took up rule and became the realm {result}."),
        K.TITLE_RAISED: Line("transform.title_raised", "The realm {subject} was raised to the title {result}."),
        K.REALM_FROM_TITLE: Line("transform.realm_from_title", "The title {subject} was made a realm of its own: {result}."),
        K.MANIFESTATION: Line("transform.manifestation", "The legend {subject} was believed until it stood in the world as {result}."),
        K.LEGEND_FIXED: Line("transform.legend_fixed", "The legend {subject} was fixed into the work {result}."),
        K.ARTWORK_REMEMBERED: Line("transform.artwork_remembered", "The lost work {subject} lives on as the legend {result}."),
        K.EVENT_PHENOMENON: Line("transform.event_phenomenon", "The happening {subject} outlasted its moment and stayed in the world as {result}."),
        K.DEAD_GOD: Line("transform.dead_god", "The body of {subject} became the place {result}."),
        K.CONSTRUCT: Line("transform.construct", "The made thing {subject} woke and moved as {result}."),
        K.BEAST_PROMOTION: Line("transform.beast_promotion", "One of the kind {subject} grew past its kin into the beast {result}."),
        K.LANGUAGE_DEATH: Line("transform.language_death", "The last speakers of {subject} were gone; the language is dead."),
        K.LANGUAGE_REVIVAL: Line("transform.language_revival", "The dead language {subject} was spoken again."),
        K.THEORY_SETTLED: Line("transform.theory_settled", "The account {subject} was held so widely and so long that it became the knowledge {result}."),
        K.TRADITION_CODIFIED: Line("transform.tradition_codified", "The custom {subject} was written down as the law {result}."),
        K.FALL: Line("transform.fall", "{subject} fell from godhood and lives on as the mortal {result}."),
        K.RESTORATION: Line("transform.restoration", "{subject} climbed back from mortal life and is a god again."),
        K.LOSS_OF_SAPIENCE: Line(
            "transform.loss_of_sapience", "The people {subject} lost speech and reckoning; what is left of them lives on as the kind {result}."
        ),
        K.ETHNORELIGIOUS: Line("transform.ethnoreligious", "The faithful of {subject} kept to one another for generations and became the people {result}."),
        K.NATION_BUILDING: Line("transform.nation_building", "The subjects of {subject} came to share one tongue and one name and became the people {result}."),
        K.HOUSE_PEOPLE: Line("transform.house_people", "The house {subject} grew over generations into the people {result}."),
        K.POCKET_WORLD: Line("transform.pocket_world", "The phenomenon {subject} grew past its bounds into the world {result}."),
        K.WORLD_SOUL: Line("transform.world_soul", "The world {subject} woke as the god {result}, its body the world itself."),
        K.STAR_GOD: Line("transform.star_god", "The star {subject} was worshipped until it stood as the god {result}."),
        K.SACRALISATION: Line("transform.sacralisation", "The teaching {subject} was worshipped and became the faith {result}."),
        K.SECULARISATION: Line("transform.secularisation", "The faith {subject} kept its teachings and let go of its worship, becoming the teaching {result}."),
        K.PROGENITOR: Line("transform.progenitor", "The beast {subject} bred a line of its own: the kind {result}."),
        K.OUTER_ENTRY: Line("transform.outer_entry", "The outer being {subject} was worshipped into the cosmos as the god {result}."),
        K.CORRUPTION: Line("transform.corruption", "{subject} passed out of the cosmos and became the outer being {result}."),
        K.COLOSSAL_CORPSE: Line("transform.colossal_corpse", "The body of {subject} became the place {result}."),
    }
)
