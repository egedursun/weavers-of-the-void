from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.genetics import HouseholdForm
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass

FORM_CARE: Mapping[HouseholdForm, int] = total(
    HouseholdForm,
    {
        HouseholdForm.NUCLEAR: 20,
        HouseholdForm.EXTENDED: 60,
        HouseholdForm.STEM: 50,
        HouseholdForm.JOINT: 60,
        HouseholdForm.POLYGAMOUS: 50,
        HouseholdForm.COMMUNAL: 70,
        HouseholdForm.SINGLE: 0,
        HouseholdForm.INSTITUTIONAL: 80,
        HouseholdForm.MIXED: 40,
        HouseholdForm.CHOSEN: 40,
    },
)


YOUNG = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH, None})


CLASS_DISTRICTS: dict[SocialClass, tuple[DistrictKind, ...]] = {
    SocialClass.NOBLE: (DistrictKind.PALACE, DistrictKind.CITADEL, DistrictKind.MARKET),
    SocialClass.MERCHANT: (DistrictKind.MARKET, DistrictKind.HARBOUR, DistrictKind.FOREIGN_QUARTER),
    SocialClass.PRIEST: (DistrictKind.TEMPLE_QUARTER,),
    SocialClass.MONASTIC: (DistrictKind.TEMPLE_QUARTER,),
    SocialClass.SCRIBE: (DistrictKind.TEMPLE_QUARTER, DistrictKind.MARKET),
    SocialClass.ARTISAN: (DistrictKind.CRAFT_QUARTER, DistrictKind.MARKET),
    SocialClass.WARRIOR: (DistrictKind.CITADEL,),
    SocialClass.FARMER: (DistrictKind.FARMLAND,),
    SocialClass.SERF_OR_SLAVE: (DistrictKind.SLUMS, DistrictKind.FARMLAND),
    SocialClass.OUTCAST: (DistrictKind.SLUMS,),
    SocialClass.WORKER: (DistrictKind.INDUSTRIAL, DistrictKind.RESIDENTIAL, DistrictKind.SLUMS),
    SocialClass.PROFESSIONAL: (DistrictKind.BUSINESS, DistrictKind.RESEARCH, DistrictKind.SUBURB),
    SocialClass.OFFICIAL: (DistrictKind.CIVIC_QUARTER, DistrictKind.BUSINESS),
    SocialClass.CITIZEN: (DistrictKind.RESIDENTIAL, DistrictKind.SUBURB, DistrictKind.MARKET),
    SocialClass.UNEMPLOYED: (DistrictKind.SLUMS, DistrictKind.RESIDENTIAL),
}

RULES_REALM_OFFICE_KINDS = (OfficeKind.RULER, OfficeKind.REGENT)
RULER_DRAW_OFFICE_KINDS = (OfficeKind.RULER, OfficeKind.REGENT)
