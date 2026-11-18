import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend/src/aerona"
PROMPTS = BACKEND / "prompts"
ENUMS = BACKEND / "domain/enums"
FRONTEND = ROOT / "frontend/src"
SCREEN_SUFFIXES = frozenset({".ts", ".tsx"})
SHOWN_WORD = re.compile(r"[A-Z][a-z]+")
QUOTED = re.compile(r"(['\"`])((?:(?!\1).)*)\1")
TEMPLATE_HOLE = re.compile(r"\$\{[^}]*\}")
CODE_MARKS = re.compile(r"[=(){};<>\[\]]|^(?:import|export|const|let|return|if|case|type|interface)\b|^//|^\*|^[\w$]+\??:|\w\.\w|,$")
KEYED_SPECS = frozenset({"IncidentKindSpec"})
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
    BACKEND / "catalog/body_words.py",
    FRONTEND / "api/generated",
)
MORTAL_KINSHIP = re.compile(
    r"\b(men father|mother's or father's|father of|father_of|brother of)\b",
    re.IGNORECASE,
)


MEDIUM_RULE = "hardcoded image medium"
GENERIC_MEN = "men for people"
SEX_CONTEXT = re.compile(r"women|male|\(\?:")


@dataclass(frozen=True)
class Pattern:
    rule: str
    regex: re.Pattern[str]
    prompts_only: bool = False
    prose_only: bool = False
    creation_only: bool = False
    image_only: bool = False
    enum_only: bool = False


PATTERNS = (
    Pattern(
        "borrowed role name",
        re.compile(r"\b(angels?|angelic|choirs?|fury|furies|psychopomps?|valkyries?|eye in the sky|warrior halls?|ancestor halls?)\b", re.IGNORECASE),
        enum_only=True,
    ),
    Pattern(
        "borrowed imagery in a value",
        re.compile(r"\b(threads?|webs?|woven|stitch(?:es|ed)?)\b", re.IGNORECASE),
        enum_only=True,
    ),
    Pattern(
        "gendered value",
        re.compile(
            r"\b(brides?|grooms?|kings?|kingship|kingdoms?|queens?|lords?|lordships?|lad(?:y|ies)|dukes?|duch(?:y|ies|ess)|count(?:y|ies|ess)|"
            r"princes?|princess(?:es)?|emperors?|empress(?:es)?|monks?|nuns?|knights?|abbots?|abbess(?:es)?|"
            r"patri(?:lineal|local|archs?)|matri(?:lineal|local|archs?)|avunculocal|polygyny|polyandry|dowry|widow(?:er)?s?|maidens?|"
            r"mothers?|mothership|sisters?|daughters?|wi(?:fe|ves)|husbands?|levirate|sororate|priestess(?:es)?)\b",
            re.IGNORECASE,
        ),
        enum_only=True,
    ),
    Pattern(
        "borrowed custom name",
        re.compile(
            r"\b(siesta|flyting|war dance|scar rite|drinking hall|hunting lodge|silver tongue|iron nerve|swift blade|cold eye|shadow step|"
            r"granary keeper|ledger mind|battle eye|warlord|archsee|gavelkind|inquisitors?|twilight of (?:the )?gods|return of the king|lost paradise)\b",
            re.IGNORECASE,
        ),
        enum_only=True,
    ),
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
        GENERIC_MEN,
        re.compile(r"(?<![\w-])(?:big-)?men(?![\w-])", re.IGNORECASE),
        prose_only=True,
    ),
    Pattern(
        GENERIC_MEN,
        re.compile(r"['\"`][^'\"`]*(?<![\w-])(?:big-)?men(?![\w-])[^'\"`]*['\"`]", re.IGNORECASE),
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
        "a place given a will or a mood",
        re.compile(
            r"\b(?:merciless|pitiless|cruel|angry|brooding|hungry|jealous) (?:sun|sky|sea|land|ground|desert|wind|winter)s?\b|"
            r"\bcrowned by\b|\bhugging its (?:sun|star)\b|\bloud with life\b|\bsmothered by\b|\blakes? of light\b|"
            r"\beye of (?:the )?storms?\b|\b(?:life|it|they) clings? to\b",
            re.IGNORECASE,
        ),
        prose_only=True,
    ),
    Pattern(
        "assumed day and night",
        re.compile(r"\b(?:night after night|day after day|every night|each night|every morning|at dawn and dusk)\b", re.IGNORECASE),
        prose_only=True,
    ),
    Pattern(
        "borrowed end of the world",
        re.compile(r"\b(?:twilight of the gods|ragnar(?:o|\u00f6)k|g(?:o|\u00f6)tterd(?:a|\u00e4)mmerung|armageddon)\b", re.IGNORECASE),
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
        "assumed species in a deed",
        re.compile(r"\bhuman (?:sacrifices?|blood|flesh|lives?|souls?)\b|\bmankind\b|\bhumanity\b", re.IGNORECASE),
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
            r"(?-i:placeholder=\{?['\"][a-z][^'\"]*['\"])"
            r"|(?-i:placeholder=\{?['\"](?:The |A |An )?(?!(?:The|A|An) )[A-Z][\w'-]+ (?:(?:of|the|and) )*[A-Z][\w'-]+(?: (?:(?:of|the|and) )*[A-Z][\w'-]+)*['\"])"
            r"|placeholder=\{?['\"][^'\"]*\b(?:for example|e\.g\.|such as)\b[^'\"]*['\"]"
            r"|placeholder=\{['\"][^'\"]*\\n[^'\"]*['\"]\}",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        "open example list",
        re.compile(r"\((?:[^()]*?, ){2,}[^()]*?(?:…|\.\.\.|\bor another\b|\betc\.?)\s*\)"),
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
        "scene in an enum value",
        re.compile(
            r"\b(salted earth|salt soil|river of dead|cosmic mount|swallowed|god remains|god corpse|leak crystal|abductor|eternal storm|"
            r"living fog|crystal bloom|dead zone|mirror lake|singing stones|ghost road|star eater|nebula mind|leviathan|void shepherd|"
            r"cosmic titan|veil warden|plane sovereign|living constellation|ley nexus|time slip)\b",
            re.IGNORECASE,
        ),
        enum_only=True,
    ),
    Pattern(
        "borrowed creature name",
        re.compile(r"\b(?:golems?|chimeras?|dragonbone|homunculi|homunculus|revenants?|liches|lich|ghouls?|wraiths?)\b", re.IGNORECASE),
    ),
    Pattern(
        "paired motif in an enum value",
        re.compile(
            r"\b(?:sand|ash|salt|bone|blood|crowns?|knives?|thorns?|skulls?|embers?|iron|silver|gold) and (?:sand|ash|salt|bone|blood|crowns?|knives?|thorns?|skulls?|embers?|iron|silver|gold)\b",
            re.IGNORECASE,
        ),
        enum_only=True,
    ),
    Pattern(
        "scene in a travel or phenomenon name",
        re.compile(r"\b(river of the dead|being swallowed|god-corpse|cosmic mount|ghost road|living constellation|star eater)\b", re.IGNORECASE),
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


def screen_text(line: str) -> str:
    quoted = [TEMPLATE_HOLE.sub(" ", match.group(2)) for match in QUOTED.finditer(line)]
    bare = line.strip()
    spoken_line = [bare] if bare and not CODE_MARKS.search(bare) else []
    return " | ".join([*quoted, *spoken_line])


def prose(path: Path, value: str) -> str:
    if path.suffix == ".j2":
        return JINJA.sub(" ", value)
    if path.suffix in SCREEN_SUFFIXES:
        return " | ".join(part for part in screen_text(value).split(" | ") if any(character.isspace() for character in part.strip()) or SHOWN_WORD.fullmatch(part))
    return value if path.suffix == ".py" and any(character.isspace() for character in value.strip()) else ""


def matches(path: Path, line: int, value: str, in_prompts: bool, creation: bool | None = None, *, enum_value: bool = False) -> list[Finding]:
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
        and (enum_value or not pattern.enum_only)
        and not (pattern.rule == MEDIUM_RULE and path in STYLE_HOMES)
        and not (pattern.rule == GENERIC_MEN and SEX_CONTEXT.search(value))
        for match in [pattern.regex.search(prose(path, value) if pattern.prose_only else value)]
        if match
    ]


def enum_values(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        (item.lineno, item.value.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.Assign) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str)
    ]


def spaced(value: str) -> str:
    return value.replace("_", " ").replace(".", " ")


def kind_keys(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        (node.lineno, node.args[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") in KEYED_SPECS
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]


def enum_findings() -> list[Finding]:
    found: list[Finding] = []
    for path in sorted(ENUMS.glob("*.py")):
        for line, value in enum_values(path):
            found.extend(matches(path, line, spaced(value), True, False, enum_value=True))
    for path in backend_targets():
        if path.suffix != ".py" or path.is_relative_to(ENUMS):
            continue
        for line, value in kind_keys(path):
            found.extend(matches(path, line, spaced(value), True, False, enum_value=True))
    return found


KIND_FIELDS = frozenset({"name", "description", "label", "plural", "hint", "category_labels"})
KIND_SPEC_CALLS = frozenset({"ConceptSpec", "KindProperty"})


def kind_rows(tables: Path = BACKEND / "db/tables") -> set[str]:
    found = {"KindRow"}
    trees = [ast.parse(path.read_text(encoding="utf-8")) for path in sorted(tables.glob("*.py"))]
    grew = True
    while grew:
        grew = False
        for tree in trees:
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name not in found and any(getattr(base, "id", "") in found for base in node.bases):
                    found.add(node.name)
                    grew = True
    return found - {"KindRow"}


def constant_strings(tree: ast.Module, names: set[str]) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id in names for target in targets) and getattr(node, "value", None) is not None:
            found += [(item.lineno, item.value) for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)]
    return found


def imported(tree: ast.Module) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("aerona."):
            path = BACKEND.parent / Path(*node.module.split("."))
            for alias in node.names:
                found[alias.asname or alias.name] = path.with_suffix(".py")
    return found


def kind_text(path: Path, rows: set[str]) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    sources = imported(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and (node.func.id in rows or node.func.id in KIND_SPEC_CALLS)):
            continue
        values = node.args if node.func.id in KIND_SPEC_CALLS else []
        values = [*values, *(item.value for item in node.keywords if item.arg in KIND_FIELDS)]
        for value in values:
            found += [(item.lineno, item.value) for item in ast.walk(value) if isinstance(item, ast.Constant) and isinstance(item.value, str)]
            for name in {item.id for item in ast.walk(value) if isinstance(item, ast.Name) and item.id.isupper()}:
                home = sources.get(name)
                if home is not None and home.exists():
                    found += constant_strings(ast.parse(home.read_text(encoding="utf-8")), {name})
                else:
                    found += constant_strings(tree, {name})
    return found


def kind_findings() -> list[Finding]:
    rows = kind_rows()
    found: list[Finding] = []
    for path in backend_targets():
        if path.suffix != ".py" or path.is_relative_to(BACKEND / "db/tables"):
            continue
        for line, value in kind_text(path, rows):
            found.extend(matches(path, line, spaced(value), True, False, enum_value=True))
    return found


def scan() -> list[Finding]:
    findings: list[Finding] = [*enum_findings(), *kind_findings()]
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
