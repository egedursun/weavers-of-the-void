from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.concealment import SeekerAim

SEEKER_AIM = total(
    SeekerAim,
    {
        SeekerAim.EXPOSE: Defined("To expose it", checked_by=(), used_by=("engine.powers.backfill.buried_histories",)),
        SeekerAim.EXPLOIT: Defined("To use it", checked_by=("engine.concealment.kinds.after_seeking",), used_by=()),
        SeekerAim.DESTROY_THE_HIDDEN: Defined("To destroy the hidden", checked_by=("engine.concealment.kinds.after_seeking",), used_by=()),
        SeekerAim.JOIN_THE_HIDDEN: Defined("To join the hidden", checked_by=("engine.concealment.truths.seek",), used_by=()),
        SeekerAim.UNDERSTAND: Defined(
            "To understand it",
            checked_by=("engine.concealment.kinds.after_seeking",),
            used_by=("db.tables.concealment.TruthSeekerRow", "tools.mortal.powers.InvestigateInput"),
        ),
    },
)
