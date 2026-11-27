import re
from types import MappingProxyType

from aerona.domain.enums.mind import MemoryKind

GRUDGE_FRAGMENTS: MappingProxyType[MemoryKind, re.Pattern[str]] = MappingProxyType(
    {
        MemoryKind.HUMILIATED_ME: re.compile(r"^overcame it in the battle for (?P<place>.+)$"),
        MemoryKind.STOLE_FAITHFUL: re.compile(r"^took (?P<place>.+)$"),
        MemoryKind.AIDED_CHOSEN: re.compile(r"^blessed (?P<place>.+)$"),
    }
)
