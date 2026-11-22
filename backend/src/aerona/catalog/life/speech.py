from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.speech import HumourForm

FORM_AXES: dict[ValueAxis, HumourForm] = {
    ValueAxis.TRUTH: HumourForm.IRONY,
    ValueAxis.FRIENDSHIP: HumourForm.TEASING,
    ValueAxis.ARTWORK: HumourForm.STORYTELLING,
    ValueAxis.LEISURE: HumourForm.ABSURD,
    ValueAxis.COMPETITION: HumourForm.WORDPLAY,
    ValueAxis.SUPERSTITION: HumourForm.RITUAL_CLOWNING,
    ValueAxis.LAW: HumourForm.SATIRE,
}
