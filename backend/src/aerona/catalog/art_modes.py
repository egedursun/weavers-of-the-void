from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.crafts import RightKind
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.mind import SkillKind, ValueAxis

M = ArtMode
V = ValueAxis
S = SkillKind


@dataclass(frozen=True)
class ArtModeSpec:
    label: str
    structure: tuple[str, ...]
    skills: tuple[SkillKind, ...]
    message: dict[ValueAxis, int]
    words: tuple[str, ...]
    right: RightKind
    performed: bool = False
    verbal: bool = False
    image: bool = False
    written: bool = False
    heard: bool = False


ART_MODES = total(
    ArtMode,
    {
        M.VERBAL: ArtModeSpec(
            "Verbal art",
            ("metre", "rhyme", "stanza", "line_length", "subjects"),
            (S.WRITING, S.ORATORY),
            {V.HONOUR: 3, V.KNOWLEDGE: 3},
            ("epic", "saga", "poem", "ballad", "lay", "verse", "book", "chronicle", "codex", "treatise", "history", "annals"),
            RightKind.STORY,
            performed=True,
            verbal=True,
            written=True,
            heard=True,
        ),
        M.MUSICAL: ArtModeSpec(
            "Music",
            ("scale", "rhythm", "voices", "instruments"),
            (S.ORATORY,),
            {V.KINSHIP: 3},
            ("song", "hymn", "chant", "anthem", "lament", "music", "symphony", "melody"),
            RightKind.SONG,
            performed=True,
            verbal=True,
            heard=True,
        ),
        M.MOVEMENT: ArtModeSpec(
            "Movement",
            ("tempo", "group_size", "movement"),
            (S.ORATORY,),
            {V.KINSHIP: 2, V.MARTIAL: 2},
            ("dance",),
            RightKind.DANCE,
            performed=True,
            heard=True,
        ),
        M.RITUAL_PERFORMANCE: ArtModeSpec(
            "Performance",
            ("form", "cast", "subjects"),
            (S.ORATORY, S.WRITING),
            {V.MERCY: 3},
            ("play", "drama", "tragedy", "comedy"),
            RightKind.STORY,
            performed=True,
            verbal=True,
            written=True,
            heard=True,
        ),
        M.FLAT_IMAGE: ArtModeSpec(
            "Flat image",
            ("palette", "motifs", "materials"),
            (S.POTTERY, S.WRITING),
            {V.PIETY: 4},
            ("fresco", "mural", "painting", "mosaic", "calligraphy"),
            RightKind.DESIGN,
            image=True,
        ),
        M.SOLID_IMAGE: ArtModeSpec(
            "Solid image",
            ("motifs", "materials", "scale"),
            (S.MASONRY, S.CARPENTRY),
            {V.HIERARCHY: 4, V.MARTIAL: 2},
            ("statue", "bust", "sculpture", "carving", "relief", "stele"),
            RightKind.DESIGN,
            image=True,
        ),
        M.BUILT: ArtModeSpec(
            "Built form",
            ("motifs", "materials", "proportions"),
            (S.MASONRY, S.ENGINEERING),
            {V.HIERARCHY: 3},
            ("frieze", "ornament", "facade"),
            RightKind.DESIGN,
            image=True,
        ),
        M.TEXTILE_IMAGE: ArtModeSpec(
            "Textile image",
            ("palette", "motifs", "pattern"),
            (S.WEAVING,),
            {V.TRADITION: 4},
            ("tapestry", "weaving", "embroidery"),
            RightKind.DESIGN,
            image=True,
        ),
        M.WORN: ArtModeSpec(
            "Worn art",
            ("cut", "ornament", "colours"),
            (S.WEAVING, S.JEWELLING),
            {V.HIERARCHY: 2, V.TRADITION: 2},
            ("costume", "adornment", "jewellery"),
            RightKind.DESIGN,
            image=True,
        ),
        M.CULINARY: ArtModeSpec(
            "Culinary art", ("flavours", "courses", "presentation"), (S.ETIQUETTE,), {V.KINSHIP: 2, V.LEISURE: 2}, ("cuisine", "recipe"), RightKind.DESIGN
        ),
        M.SCENT: ArtModeSpec("Scent art", ("notes", "strength", "occasion"), (S.ALCHEMY,), {V.PIETY: 2}, ("perfume", "incense"), RightKind.DESIGN),
        M.LIGHT: ArtModeSpec(
            "Light art", ("colour", "motion", "timing"), (S.ENGINEERING,), {V.PIETY: 2}, ("illumination",), RightKind.DESIGN, performed=True, image=True
        ),
        M.RECORDED: ArtModeSpec(
            "Recorded art",
            ("medium", "length", "subjects"),
            (S.WRITING, S.ELECTRONICS),
            {V.KNOWLEDGE: 4},
            ("recording", "archive"),
            RightKind.STORY,
            written=True,
            heard=True,
        ),
        M.INTERACTIVE: ArtModeSpec("Interactive art", ("rules", "players", "choices"), (S.STRATEGY,), {V.COMPETITION: 3}, ("puzzle",), RightKind.DESIGN),
        M.LANDSCAPE: ArtModeSpec(
            "Landscape art", ("plants", "paths", "views"), (S.FORAGING, S.ENGINEERING), {V.NATURE: 3}, ("garden", "park"), RightKind.DESIGN, image=True
        ),
        M.BODY: ArtModeSpec(
            "Body art", ("placement", "pattern", "meaning"), (S.MEDICINE,), {V.TRADITION: 3}, ("tattoo", "body marking"), RightKind.DESIGN, image=True
        ),
        M.MADE_MIND_ART: ArtModeSpec(
            "Made-mind art", ("source", "method", "curation"), (S.ELECTRONICS,), {V.KNOWLEDGE: 2, V.ARTWORK: 2}, ("generated",), RightKind.DESIGN
        ),
    },
)

PERFORMED_MODES = frozenset(mode for mode, spec in ART_MODES.items() if spec.performed)
VERBAL_MODES = frozenset(mode for mode, spec in ART_MODES.items() if spec.verbal)
IMAGE_MODES = frozenset(mode for mode, spec in ART_MODES.items() if spec.image)
WRITTEN_MODES = frozenset(mode for mode, spec in ART_MODES.items() if spec.written)
HEARD_MODES = frozenset(mode for mode, spec in ART_MODES.items() if spec.heard)
