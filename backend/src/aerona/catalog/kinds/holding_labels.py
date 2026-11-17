from aerona.core.total import total
from aerona.domain.enums.kinds import KindSpread, KindStance

STANCE_LABELS = total(
    KindStance,
    {
        KindStance.MAKES: "Makes",
        KindStance.USES: "Uses",
        KindStance.FAVOURS: "Favours",
        KindStance.FORBIDS: "Forbids",
        KindStance.BLESSES: "Blesses",
    },
)

SPREAD_LABELS = total(
    KindSpread,
    {
        KindSpread.INVENTED: "Invented",
        KindSpread.TRADE: "By trade",
        KindSpread.CONTACT: "By contact",
        KindSpread.CONQUEST: "By conquest",
        KindSpread.MIGRATION: "By migration",
        KindSpread.DECREE: "By decree",
        KindSpread.DIVINE: "By a god",
        KindSpread.GENESIS: "From the beginning",
    },
)
