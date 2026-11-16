from aerona.engine.augments import keep_augments
from aerona.engine.made.abundance import keep_abundance
from aerona.engine.made.company_power import keep_company_power
from aerona.engine.made.intrusion import foes_intrude
from aerona.engine.made.peoples import form_made_peoples
from aerona.engine.made.realms import keep_realms
from aerona.engine.made.relics import keep_relics
from aerona.engine.made.replicators import run_replicators
from aerona.engine.made.surveillance import keep_watch
from aerona.engine.made.trust import keep_trust
from aerona.engine.minds.law import keep_mind_law
from aerona.engine.minds.phase import minds
from aerona.engine.networks.phase import networks
from aerona.engine.phase import Phase

PHASES = (
    Phase("networks", networks),
    Phase("intrusions", foes_intrude),
    Phase("surveillance", keep_watch),
    Phase("information_trust", keep_trust),
    Phase("company_power", keep_company_power),
    Phase("replicators", run_replicators),
    Phase("abundance", keep_abundance),
    Phase("minds", minds),
    Phase("made_realms", keep_realms),
    Phase("augments", keep_augments),
    Phase("mind_law", keep_mind_law),
    Phase("made_peoples", form_made_peoples),
    Phase("made_relics", keep_relics),
)
