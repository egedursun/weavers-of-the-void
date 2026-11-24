from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.customs import NameForm, NamingPattern

P = NamingPattern
F = NameForm


@dataclass(frozen=True)
class PatternSpec:
    label: str
    joiner: str


@dataclass(frozen=True)
class FormSpec:
    label: str
    public: bool = True


NAMING_PATTERNS: Mapping[NamingPattern, PatternSpec] = total(
    NamingPattern,
    {
        P.GIVEN: PatternSpec("A name of one's own", ""),
        P.PARENT: PatternSpec("Named for a parent", ", child of "),
        P.CLAN: PatternSpec("Named for the clan", " of "),
        P.TEKNONYM: PatternSpec("Parents named for their child", ""),
        P.PLACE: PatternSpec("Named for the birthplace", " of "),
        P.TRADE: PatternSpec("Named for the trade", ", "),
        P.ANCESTRAL: PatternSpec("Named for a forebear", ", again "),
        P.EVENT: PatternSpec("Named for the time of birth", ", born in "),
    },
)
NAME_FORMS: Mapping[NameForm, FormSpec] = total(
    NameForm,
    {
        F.BIRTH: FormSpec("Birth name"),
        F.SECRET: FormSpec("Secret name", public=False),
        F.DEED: FormSpec("Name of a deed"),
        F.INITIATION: FormSpec("Initiation name"),
        F.MARRIAGE: FormSpec("Marriage name"),
        F.VOW: FormSpec("Name of a vow"),
        F.ASCENSION: FormSpec("Name of rule"),
        F.POSTHUMOUS: FormSpec("Name after death"),
        F.EPITHET: FormSpec("Epithet"),
        F.ADOPTION: FormSpec("Adoption name"),
    },
)
