from aerona.engine.couplings.carrion import carrion
from aerona.engine.couplings.deep import deep_seals
from aerona.engine.couplings.field import field_diplomacy
from aerona.engine.couplings.fisheries import closures
from aerona.engine.couplings.novelty import novelty
from aerona.engine.couplings.offices import office_creation
from aerona.engine.couplings.registers import sign_languages, sociolects
from aerona.engine.couplings.rite_body import restrain_casters
from aerona.engine.couplings.teachers import teachings
from aerona.engine.phase import Phase

PHASES = (
    Phase("restrain_casters", restrain_casters),
    Phase("sign_languages", sign_languages),
    Phase("sociolects", sociolects),
    Phase("carrion", carrion),
    Phase("teachings", teachings),
    Phase("office_creation", office_creation),
    Phase("field_diplomacy", field_diplomacy),
    Phase("deep_seals", deep_seals),
    Phase("closures", closures),
    Phase("novelty", novelty),
)
