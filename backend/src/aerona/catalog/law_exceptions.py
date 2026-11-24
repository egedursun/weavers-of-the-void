from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.divine import LawException


@dataclass(frozen=True)
class ExceptionSpec:
    label: str
    spares: str
    names_kind: bool = False
    names_office: bool = False
    bargain_bound: bool = False


LAW_EXCEPTIONS: Mapping[LawException, ExceptionSpec] = total(
    LawException,
    {
        LawException.NONE: ExceptionSpec("Spares no one", ""),
        LawException.CREATOR_CHOSEN: ExceptionSpec("The Creator's chosen", "those the Creator has chosen"),
        LawException.AUTHOR_WORSHIPPERS: ExceptionSpec("Its author's faithful", "the faithful of its author"),
        LawException.HEROES: ExceptionSpec("Heroes", "heroes"),
        LawException.AVATARS: ExceptionSpec("Avatars", "avatars of the gods"),
        LawException.NAMED_KIND: ExceptionSpec("A named kind", "one kind of being", names_kind=True),
        LawException.OFFICE_HOLDERS: ExceptionSpec("Holders of a divine office", "the holders of a named divine office", names_office=True),
        LawException.BARGAINERS: ExceptionSpec("Those bound by an outer bargain", "those bound by an outer bargain", bargain_bound=True),
    },
)
