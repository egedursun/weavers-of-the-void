from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.kin import KinAgenda, KinDuty

KIN_AGENDA = total(
    KinAgenda,
    {
        KinAgenda.CHOOSE_HEAD: Defined("Choose head", checked_by=("tools.mortal.kin.convene_kin_group",), used_by=()),
        KinAgenda.SHARE_LAND: Defined("Share land", checked_by=("tools.mortal.kin.convene_kin_group",), used_by=()),
        KinAgenda.FEUD: Defined("Feud", checked_by=("tools.mortal.kin.convene_kin_group",), used_by=()),
        KinAgenda.MARRIAGE: Defined("Marriage", checked_by=("tools.mortal.kin.convene_kin_group",), used_by=()),
        KinAgenda.MIGRATE: Defined("Migrate", checked_by=("tools.mortal.kin.convene_kin_group",), used_by=()),
    },
)

KIN_DUTY = total(
    KinDuty,
    {
        KinDuty.SUPPORT: Defined(
            "Support",
            checked_by=("engine.kin.seed.duties_for",),
            used_by=("engine.kin.duties.help_in_need", "engine.kin.seed.BASE", "tools.mortal.kin.NEED_DUTIES"),
        ),
        KinDuty.RAISE: Defined("Raise", checked_by=(), used_by=("engine.kin.duties.foster_orphans", "engine.kin.seed.BASE", "engine.kin.seed.duties_for")),
        KinDuty.TEACH: Defined("Teach", checked_by=(), used_by=("engine.kin.seed.BASE",)),
        KinDuty.PROTECT: Defined("Protect", checked_by=(), used_by=("engine.kin.seed.BASE", "tools.mortal.kin.NEED_DUTIES")),
        KinDuty.AVENGE: Defined(
            "Avenge", checked_by=(), used_by=("engine.kin.duties.avenge", "engine.kin.duties.mourn_and_avenge", "engine.kin.seed.duties_for")
        ),
        KinDuty.MARRY_TO: Defined("Marry to", checked_by=(), used_by=("engine.kin.seed.duties_for",)),
        KinDuty.INHERIT_FROM: Defined("Inherit from", checked_by=(), used_by=("engine.kin.seed.BASE", "engine.kin.seed.duties_for")),
        KinDuty.MOURN: Defined("Mourn", checked_by=(), used_by=("engine.kin.duties.mourn_and_avenge", "engine.kin.seed.BASE")),
        KinDuty.HOST: Defined("Host", checked_by=(), used_by=("engine.kin.seed.BASE", "tools.mortal.kin.NEED_DUTIES")),
        KinDuty.OBEY: Defined("Obey", checked_by=(), used_by=("engine.kin.seed.BASE", "engine.kin.seed.duties_for")),
        KinDuty.JOKE_WITH: Defined("Joke with", checked_by=(), used_by=("engine.kin.duties.keep_closeness",)),
        KinDuty.AVOID: Defined("Avoid", checked_by=(), used_by=("engine.kin.duties.keep_closeness", "engine.kin.seed.duties_for")),
    },
)
