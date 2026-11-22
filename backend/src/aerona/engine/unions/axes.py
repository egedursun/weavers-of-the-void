from collections.abc import Mapping
from dataclasses import dataclass

from aerona.catalog.life.unions import DESCENT_OF
from aerona.core.total import total
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.cycles import ResidenceRule
from aerona.domain.enums.unions import PartnerScope, PluralSide, UnionDescent, UnionForm, UnionResidence

RESIDENCE_OF: Mapping[ResidenceRule, UnionResidence] = total(
    ResidenceRule,
    {
        ResidenceRule.WITH_FIRST_FAMILY: UnionResidence.WITH_FIRST_FAMILY,
        ResidenceRule.WITH_SECOND_FAMILY: UnionResidence.WITH_SECOND_FAMILY,
        ResidenceRule.NEW_HOUSEHOLD: UnionResidence.NEW_HOUSEHOLD,
        ResidenceRule.WITH_KIN_OF_THE_FIRST_LINE: UnionResidence.WITH_SECOND_FAMILY,
    },
)
PLURAL_FORMS = frozenset({UnionForm.PLURAL, UnionForm.GROUP})


@dataclass(frozen=True)
class Spousing:
    form: UnionForm = UnionForm.PAIR
    side: PluralSide = PluralSide.EITHER
    endogamy: PartnerScope = PartnerScope.NONE

    @property
    def several(self) -> bool:
        return self.form in PLURAL_FORMS

    def plural_on(self, side: PluralSide) -> bool:
        return self.form is UnionForm.PLURAL and self.side is side


def spousing_of(custom: UnionCustomRow | None) -> Spousing:
    return Spousing(custom.form, custom.plural_side, custom.endogamy) if custom is not None else Spousing()


def fresh_custom(people_id: int, spousing: Spousing, kinship: KinshipSystemRow | None, exchange_value: int) -> UnionCustomRow:
    return UnionCustomRow(
        people_entity_id=people_id,
        form=spousing.form,
        plural_side=spousing.side,
        endogamy=spousing.endogamy,
        residence=RESIDENCE_OF[kinship.residence] if kinship is not None else UnionResidence.NEW_HOUSEHOLD,
        descent=DESCENT_OF[kinship.descent] if kinship is not None else UnionDescent.THROUGH_BOTH,
        exchange_value=exchange_value,
        locked=[],
    )


def drift_custom(row: UnionCustomRow, spousing: Spousing) -> None:
    if "form" not in row.locked:
        row.form = spousing.form
    if "plural_side" not in row.locked:
        row.plural_side = spousing.side
    if "endogamy" not in row.locked:
        row.endogamy = spousing.endogamy
