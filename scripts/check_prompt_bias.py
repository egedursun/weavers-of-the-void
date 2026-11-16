import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend/src/aerona"
PROMPTS = BACKEND / "prompts"
FRONTEND = ROOT / "frontend/src"
MODEL_FEEDING = (
    BACKEND / "catalog/genesis.py",
    FRONTEND / "features/onboarding",
)
CREATION_TEXT = (
    PROMPTS / "schemas/genesis.py",
    PROMPTS / "schemas/cosmos.py",
    PROMPTS / "templates/genesis",
    PROMPTS / "templates/world_birth",
)
IMAGE_TEXT = (PROMPTS / "data/images.py",)
STYLE_HOMES = (
    BACKEND / "catalog/image_styles.py",
    BACKEND / "domain/enums/world.py",
    FRONTEND / "features/images/imageStyles.ts",
)
SKIPPED = (
    BACKEND / "db/alembic",
    BACKEND / "migration/legacy",
    BACKEND / "rules/renames.py",
    BACKEND / "constants/agents.py",
    FRONTEND / "api/generated",
)
MORTAL_KINSHIP = re.compile(
    r"\b(men father|mother's or father's|father of|father_of|brother of)\b",
    re.IGNORECASE,
)


MEDIUM_RULE = "hardcoded image medium"


@dataclass(frozen=True)
class Pattern:
    rule: str
    regex: re.Pattern[str]
    prompts_only: bool = False
    prose_only: bool = False
    creation_only: bool = False
    image_only: bool = False


PATTERNS = (
    Pattern(
        "gendered default",
        re.compile(
            r"\b(he|him|his|himself|father|fathers|fatherly|brother|brothers|brotherly)\b|"
            r"(?<![A-Za-z])(brotherhoods?|brethren|fraternal|fraternity|sisterhoods?)(?![A-Za-z])|"
            r"\b(?![a-z]*(?:human|woman|women|omen|specimen|roman|amen|stamen|abdomen|semen|acumen|regimen|ramen|shaman|caiman|cayman|dolmen|"
            r"talisman|ottoman|german|hymen|cyclamen|dusman)s?\b)(?-i:[A-Za-z][a-z]*m[ae]n)\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "forced conflict quota",
        re.compile(
            r"\b(at least one (action|act|move|step) (on|of|toward) conflict|at least one (conflict|rivalry|betrayal|rebellion|war)|"
            r"seeds? of (tension|conflict|rivalry)|must (rebel|betray|quarrel|feud|clash)|always (rebel|betray|quarrel|feud|clash))\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "forced strangeness",
        re.compile(r"\b(strange|stranger|strangest|strangeness|uncanny|eerie|otherworldly)\b", re.IGNORECASE),
        prompts_only=True,
    ),
    Pattern(
        "steering example",
        re.compile(
            r"\b(e\.g\.|for example|for instance|such as)[^.;:]{0,40}\b(salt|ash|bone|blood|death)\b|"
            r"\b(salt|ash|bone|blood|death)[\w-]*[^.;:{}]{0,40}…",
            re.IGNORECASE,
        ),
        prompts_only=True,
    ),
    Pattern(
        "mandatory price",
        re.compile(
            r"\b(?:carr(?:y|ies)|bears?|must (?:have|carry|bear)|always (?:has|have|carries)) (?:a|an|its|their) (?:price|cost|toll)\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "forced difference",
        re.compile(r"\b(?:entirely|completely|wholly|utterly|totally) different\b|\b(?:the new ones|each new one) must differ\b", re.IGNORECASE),
    ),
    Pattern(
        "geography quota",
        re.compile(
            r"\bat least one (?:of them )?(?:a |an )?(?:seas?|oceans?|lakes?|rivers?|islands?|continents?|mountains?|deserts?|forests?|lands?|water)\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "canned cosmogony",
        re.compile(r"\b(?:named the void|the lands and waters of)\b", re.IGNORECASE),
        prose_only=True,
    ),
    Pattern(
        "creation example list",
        re.compile(
            r"(?:[\w'-]+(?: [\w'-]+){0,3}, ){2,}(?:or |and )?[\w'-]+(?: [\w'-]+){0,3},?\s?(?:…|\.\.\.)|"
            r"\((?:[^()]*?, ){2,}[^()]*?(?:…|\.\.\.|\bor another\b)[^()]*\)"
        ),
        creation_only=True,
    ),
    Pattern(
        "imposed reaction",
        re.compile(
            r"\b(?:all|everyone|every one) who (?:heard|saw|learned) (?:of )?(?:it|this|that)\b|"
            r"\b(?:shudder(?:s|ed|ing)?|trembl(?:e|es|ed|ing)|gasp(?:s|ed)?|aghast)\b",
            re.IGNORECASE,
        ),
        prose_only=True,
    ),
    Pattern(
        "stock image",
        re.compile(
            r"\b(?:into|inside|buried in|sank into|sinks into) (?:the )?(?:mist|fog)\b|\bwhisper(?:s|ed|ing)? (?:that|the same|it)\b|"
            r"\b(?:their|his|her) bones\b|\btook a breath\b|\bby (?:fire and )?lamp(?:light)?\b|\b(?:burnt|burned) out\b|\buntil [^.]{0,40}\bburns out\b|"
            r"\bswords? (?:was |were )?drawn\b",
            re.IGNORECASE,
        ),
        prose_only=True,
    ),
    Pattern(
        "borrowed imagery",
        re.compile(
            r"\b(wove|woven|weave|weaves|weaved|weaving (?:a|an|the|together|into|itself)|unthread\w*|stitch(?:es|ed|ing)?|re-?stitch\w*|"
            r"spindles?|spun|threads?|tapestry of|web of|world's web|strung like|shuttle|weft)\b",
            re.IGNORECASE,
        ),
        prose_only=True,
    ),
    Pattern(
        "canned afterlife name",
        re.compile(r"\b(?:blessed fields|the grey plain|the gray plain|the pits|the forgetting|hall of the fallen|house of the ancestors)\b", re.IGNORECASE),
        prose_only=True,
    ),
    Pattern(
        "model image ban",
        re.compile(
            r"\b(tired (?:images?|motifs?|names?|words?|openings?)|clich(?:e|é)s?|stock (?:names?|phrases?|images?)|overused (?:images?|words?|names?)|"
            r"(?:do not|don't|never) (?:use|repeat|reuse) (?:these|this|the following|any of these) (?:images?|words?|openings?|patterns?|roots?|names?|motifs?)|"
            r"forbidden (?:images?|openings?|patterns?|roots?|motifs?)|banned (?:images?|openings?|patterns?|roots?|motifs?))\b",
            re.IGNORECASE,
        ),
        prompts_only=True,
    ),
    Pattern(
        "assumed species",
        re.compile(r"\b(?:tiny |small )?(?:human|humans|mankind|men) (?:figures?|for scale|beings? for scale)\b", re.IGNORECASE),
    ),
    Pattern(
        "assumed carrier",
        re.compile(r"\b(caravans|no caravan|the caravan)\b(?! way)", re.IGNORECASE),
    ),
    Pattern(
        "example placeholder",
        re.compile(
            r"placeholder=['\"](?:[^'\":]*:\s*)?(?:(?!(?:a|an|the|its|their|your|one)\b)[a-z][\w'-]*(?: [\w'-]+)?, )+"
            r"(?!(?:a|an|the|its|their|your|one)\b)[a-z][\w'-]*(?: [\w'-]+)?…['\"]|"
            r"(?-i:placeholder=['\"][A-Z][\w'-]* (?:the|of) [A-Z][\w'-]*…['\"])|"
            r"(?-i:placeholder=\{?['\"][a-z][^'\"]*['\"])",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "image example list",
        re.compile(r":\s*(?:[\w'-]+(?: [\w'-]+){0,3}, ){2,}(?:or |and )?[\w'-]+|\((?:[^()]*?, ){2,}[^()]*\)"),
        prose_only=True,
        image_only=True,
    ),
    Pattern(
        "assumed body",
        re.compile(r"\b(faces?|garments?|garb|clothing|robed|dress)\b", re.IGNORECASE),
        prose_only=True,
        image_only=True,
    ),
    Pattern(
        "made mind persona",
        re.compile(
            r"\b(?:made minds?|artificial minds?|thinking machines?|machines?|constructs?|automatons?|robots?|androids?|golems?)\s+(?:are|is|seem|seems|remain|remains|stay|stays|feel|feels|act|acts|being)\s+(?:\w+\s+)?"
            r"(?:cold|emotionless|unfeeling|purely logical|coldly logical|servile|hostile|soulless)\b|"
            r"\b(?:made minds?|artificial minds?|thinking machines?|machines?|constructs?|automatons?|robots?|androids?|golems?)\b[^.;:]{0,40}\b(?:longs? to be|yearns? to be|dreams? of being) (?:alive|human|real)\b|"
            r"\b(?:cold|emotionless|unfeeling|coldly logical|servile|soulless)\s+(?:made minds?|artificial minds?|thinking machines?|machines?|constructs?|automatons?|robots?|androids?|golems?)\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "made mind uprising",
        re.compile(
            r"\b(?:made minds?|artificial minds?|thinking machines?|machines?|constructs?|automatons?|robots?|androids?|golems?)\b[^.;:]{0,40}\b(?:will|must|always|inevitably|eventually|one day)\s+(?:rise up|rise against|rebel|revolt|turn on|overthrow|take over|seize power)\b|"
            r"\b(?:machine|robot|android|construct|made minds?) (?:uprising|rebellion|revolt|takeover)\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "tech imagery",
        re.compile(
            r"\b(?:neon|cyberpunk|chrome-plated|holograms?|holographic|circuitry|glowing screens?|blinking lights|data streams?|"
            r"server farms?|rain-slicked|megacit(?:y|ies)|silicon dreams?)\b",
            re.IGNORECASE,
        ),
        prose_only=True,
    ),
    Pattern(
        "abundance tone",
        re.compile(
            r"\b(?:post-scarcity (?:paradise|utopia|dystopia)|utopian? of plenty|paradise of plenty|gilded cage|idle masses|decadent plenty|"
            r"(?:plenty|abundance) (?:breeds|brings) (?:decay|sloth|ruin|idleness|decadence)|end of all want)\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "designed being gender",
        re.compile(
            r"\b(?:made minds?|artificial minds?|thinking machines?|machines?|constructs?|automatons?|robots?|androids?|golems?|clones?|designed beings?)\b[^.;:]{0,30}\b(?:she|her|hers|herself)\b|\b(?:gynoids?|fembots?|(?:android|robot) (?:woman|women|girl|girls))\b",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        MEDIUM_RULE,
        re.compile(
            r"\b(photo-?realistic|photoreal|camera and lens|never a cartoon|wildlife photography|documentary style|astrophotography|"
            r"museum-grade|raking light|atmospheric perspective|establishing shot|still life)\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    text: str

    def render(self) -> str:
        return f"{self.path.relative_to(ROOT)}:{self.line}: {self.rule}: {self.text}"


def strings_of(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        return [(node.lineno, node.value) for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    return list(enumerate(text.splitlines(), start=1))


def under(path: Path, bases: tuple[Path, ...]) -> bool:
    return any(path == base or path.is_relative_to(base) for base in bases)


def skipped(path: Path) -> bool:
    return any(path == base or path.is_relative_to(base) for base in SKIPPED)


def backend_targets() -> list[Path]:
    return sorted(
        path for path in BACKEND.rglob("*") if path.suffix in {".py", ".j2"} and path.is_file() and "__pycache__" not in path.parts and not skipped(path)
    )


def frontend_targets() -> list[Path]:
    return sorted(
        path
        for path in FRONTEND.rglob("*")
        if path.suffix in {".ts", ".tsx"} and path.is_file() and "__screenshots__" not in path.parts and ".test." not in path.name and not skipped(path)
    )


def frontend_strings(path: Path) -> list[tuple[int, str]]:
    return list(enumerate(path.read_text(encoding="utf-8").splitlines(), start=1))


JINJA = re.compile(r"\{[{%#].*?[}%#]\}")


def prose(path: Path, value: str) -> str:
    if path.suffix == ".j2":
        return JINJA.sub(" ", value)
    return value if path.suffix == ".py" and any(character.isspace() for character in value.strip()) else ""


def matches(path: Path, line: int, value: str, in_prompts: bool, creation: bool | None = None) -> list[Finding]:
    if MORTAL_KINSHIP.search(value):
        return []
    creating = under(path, CREATION_TEXT) if creation is None else creation
    imaging = under(path, IMAGE_TEXT)
    return [
        Finding(path, line, pattern.rule, match.group(0))
        for pattern in PATTERNS
        if (in_prompts or not pattern.prompts_only)
        and (creating or not pattern.creation_only)
        and (imaging or not pattern.image_only)
        and not (pattern.rule == MEDIUM_RULE and path in STYLE_HOMES)
        for match in [pattern.regex.search(prose(path, value) if pattern.prose_only else value)]
        if match
    ]


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in backend_targets():
        feeding = path.is_relative_to(PROMPTS) or under(path, MODEL_FEEDING)
        creating = under(path, CREATION_TEXT)
        for line, value in strings_of(path):
            findings.extend(matches(path, line, value, feeding, creating))
    for path in frontend_targets():
        feeding = under(path, MODEL_FEEDING)
        for line, value in frontend_strings(path):
            findings.extend(matches(path, line, value, feeding, False))
    return findings


def main() -> int:
    findings = scan()
    for finding in findings:
        print(finding.render())
    print(f"prompt bias: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
