from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.unions import KinMatch, PluralSide, UnionDescent, UnionForm

KIN_MATCH = total(
    KinMatch,
    {
        KinMatch.NONE: Defined(
            "No kin sought",
            checked_by=(),
            used_by=(
                "db.tables.unions.UnionCustomRow",
                "engine.cycles.seeding.match_for",
                "services.player.cycles.UnionDraft",
                "tools.son.cycles.ShapeUnionsInput",
            ),
        ),
        KinMatch.CROSS_COUSIN: Defined(
            "A child of a parent's other-side sibling", checked_by=("engine.cycles.lineage.COUSIN_SOUGHT",), used_by=("engine.cycles.seeding.match_for",)
        ),
        KinMatch.PARALLEL_COUSIN: Defined("A child of a parent's same-side sibling", checked_by=("engine.cycles.lineage.COUSIN_SOUGHT",), used_by=()),
    },
)

PLURAL_SIDE = total(
    PluralSide,
    {
        PluralSide.FIRST: Defined(
            "The first side",
            checked_by=("engine.demography.kinship.spouse_limit", "engine.polity.houses.plural_sex"),
            used_by=("engine.collective.demography.scarce_side_plural", "engine.demography.peoples.spousing_for"),
        ),
        PluralSide.SECOND: Defined(
            "The second side",
            checked_by=("engine.demography.kinship.spouse_limit",),
            used_by=(
                "engine.collective.demography.scarce_side_plural",
                "engine.demography.peoples.customs_of",
                "engine.demography.peoples.spousing_for",
                "engine.polity.governance.wanted_laws",
            ),
        ),
        PluralSide.EITHER: Defined(
            "Either side",
            checked_by=("engine.polity.houses.plural_sex",),
            used_by=(
                "catalog.laws.LAW_PARAMS",
                "db.tables.unions.UnionCustomRow",
                "engine.collective.demography.scarce_side_plural",
                "engine.demography.peoples.spousing_for",
                "engine.unions.axes.Spousing",
                "services.player.cycles.UnionDraft",
                "tools.son.cycles.ShapeUnionsInput",
            ),
        ),
    },
)

UNION_DESCENT = total(
    UnionDescent,
    {
        UnionDescent.THROUGH_FIRST: Defined(
            "Through the first side", checked_by=("engine.unions.customs.line_house",), used_by=("engine.unions.axes.DESCENT_OF",)
        ),
        UnionDescent.THROUGH_SECOND: Defined(
            "Through the second side", checked_by=("engine.unions.customs.line_house",), used_by=("engine.unions.axes.DESCENT_OF",)
        ),
        UnionDescent.THROUGH_BOTH: Defined(
            "Through both sides",
            checked_by=(),
            used_by=(
                "db.tables.unions.UnionCustomRow",
                "engine.unions.axes.DESCENT_OF",
                "engine.unions.axes.fresh_custom",
                "services.player.cycles.UnionDraft",
            ),
        ),
        UnionDescent.CHOSEN: Defined("As each child chooses", checked_by=("engine.unions.customs.line_house",), used_by=("engine.unions.axes.DESCENT_OF",)),
        UnionDescent.BY_HOUSE_RULE: Defined("By the rule of the greater house", checked_by=("engine.unions.customs.line_house",), used_by=()),
    },
)

UNION_FORM = total(
    UnionForm,
    {
        UnionForm.PAIR: Defined(
            "Two partners",
            checked_by=(),
            used_by=(
                "catalog.laws.LAW_PARAMS",
                "db.tables.mortal.MarriageRow",
                "db.tables.unions.UnionCustomRow",
                "engine.demography.peoples.spousing_for",
                "engine.mortal.course.match",
                "engine.mortal.kinship.marry",
                "engine.unions.axes.Spousing",
                "services.player.cycles.UnionDraft",
                "services.player.mortals.ForceMarriage",
            ),
        ),
        UnionForm.PLURAL: Defined(
            "One partner with several",
            checked_by=(
                "engine.demography.kinship.spouse_limit",
                "engine.polity.houses.plural_sex",
                "engine.polity.houses.wed",
                "engine.unions.axes.Spousing.plural_on",
            ),
            used_by=(
                "engine.collective.demography.scarce_side_plural",
                "engine.demography.peoples.spousing_for",
                "engine.mortal.course.match",
                "engine.unions.axes.PLURAL_FORMS",
            ),
        ),
        UnionForm.GROUP: Defined(
            "A group joined together",
            checked_by=("engine.demography.kinship.spouse_limit", "engine.polity.houses.suitable", "engine.polity.houses.wed"),
            used_by=("engine.collective.demography.scarce_side_plural", "engine.demography.peoples.spousing_for", "engine.unions.axes.PLURAL_FORMS"),
        ),
        UnionForm.SERIAL: Defined("One at a time, ended by custom", checked_by=(), used_by=("engine.unions.customs.TERM_FORMS",)),
        UnionForm.CONTRACT: Defined("For a set term", checked_by=(), used_by=("engine.unions.customs.TERM_FORMS",)),
        UnionForm.POSTHUMOUS: Defined("Joined even with the dead", checked_by=("engine.unions.customs.kept_past_death",), used_by=()),
        UnionForm.NONE: Defined("No unions at all", checked_by=("engine.unions.customs.partners_allowed",), used_by=()),
    },
)
