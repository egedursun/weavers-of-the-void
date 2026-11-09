import json
from pathlib import Path
from types import MappingProxyType

from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ActKind, TraitKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.structure import StructureKind

WORDS_FILE = Path(__file__).resolve().parent.parent / "migration" / "legacy" / "backfill_words.json"
RAW: dict[str, dict[str, list[str]]] = json.loads(WORDS_FILE.read_text(encoding="utf-8"))

WORKSHOP_WORDS: MappingProxyType[WorkshopKind, tuple[str, ...]] = MappingProxyType({WorkshopKind(key): tuple(words) for key, words in RAW["workshops"].items()})
RESOURCE_WORDS: MappingProxyType[CommodityKind, tuple[str, ...]] = MappingProxyType(
    {CommodityKind(key): tuple(words) for key, words in RAW["resources"].items()}
)
MATERIAL_WORDS: MappingProxyType[MaterialKind, tuple[str, ...]] = MappingProxyType({MaterialKind(key): tuple(words) for key, words in RAW["materials"].items()})
LOCAL_TRAIT_WORDS: MappingProxyType[TraitKind, tuple[str, ...]] = MappingProxyType(
    {TraitKind(key): tuple(words) for key, words in RAW.get("traits", {}).items()}
)
LAW_WORDS: MappingProxyType[LawKind, tuple[str, ...]] = MappingProxyType({LawKind(key): tuple(words) for key, words in RAW.get("laws", {}).items()})
STRUCTURE_WORDS: MappingProxyType[StructureKind, tuple[str, ...]] = MappingProxyType(
    {StructureKind(key): tuple(words) for key, words in RAW.get("structures", {}).items()}
)
ACT_WORDS: MappingProxyType[ActKind, tuple[str, ...]] = MappingProxyType(
    {act: (*RAW.get("acts", {}).get(act.value, []), act.value.replace("_", " ")) for act in ActKind}
)
