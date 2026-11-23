from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.living import Fertility

FERTILITY = total(
    Fertility,
    {
        Fertility.STERILE: Defined(
            "Sterile",
            checked_by=("engine.living.blessing.bless_line",),
            used_by=(
                "catalog.life.living.BREED_FERTILITYS",
                "catalog.life.living.SEED_DUES_FERTILITYS",
                "engine.living.backfill.alive",
                "engine.living.lines.cross_or_release",
                "engine.living.lines.make_line",
            ),
        ),
        Fertility.BREEDS_TRUE: Defined(
            "Breeds true",
            checked_by=(),
            used_by=(
                "db.tables.living.LivingLineRow",
                "db.tables.living.LivingProfileRow",
                "engine.living.backfill.bred_lines",
                "engine.living.backfill.bred_species_lines",
                "engine.living.blessing.bless_line",
                "engine.living.control.give_life",
                "engine.living.lines.LineDraft",
                "services.player.living.LineCreate",
                "tools.mortal.living.DesignLineInput",
            ),
        ),
        Fertility.BREEDS_WILD: Defined("Breeds wild", checked_by=("engine.living.profiles.breed",), used_by=("engine.living.lines.drift",)),
        Fertility.NEEDS_MAKER: Defined(
            "Needs its maker", checked_by=(), used_by=("catalog.life.living.BREED_FERTILITYS", "catalog.life.living.SEED_DUES_FERTILITYS")
        ),
        Fertility.CROSSES_WILD: Defined("Crosses with wild kin", checked_by=("engine.living.lines.cross_wild",), used_by=()),
    },
)
