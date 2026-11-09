import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend/src/aerona"
PROMPTS = BACKEND / "prompts"
FRONTEND = ROOT / "frontend/src"
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


PATTERNS = (
    Pattern(
        "gendered default",
        re.compile(
            r"\b(he|him|his|himself|father|fathers|fatherly|brother|brothers|brotherly)\b|"
            r"(?<![A-Za-z])(brotherhoods?|brethren|fraternal|fraternity|sisterhoods?)(?![A-Za-z])",
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
        re.compile(r"\b(strange|stranger|strangest|strangeness)\b", re.IGNORECASE),
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
        "borrowed imagery",
        re.compile(
            r"\b(wove|woven|weave|weaves|weaved|weaving (?:a|an|the|together|into|itself)|unthread\w*|stitch(?:es|ed|ing)?|re-?stitch\w*|"
            r"spindles?|spun|threads?|tapestry of|web of|world's web|strung like|shuttle|weft)\b",
            re.IGNORECASE,
        ),
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
        "assumed carrier",
        re.compile(r"\b(caravans|no caravan|the caravan)\b(?! way)", re.IGNORECASE),
    ),
    Pattern(
        "example placeholder",
        re.compile(
            r"placeholder=['\"](?:[^'\":]*:\s*)?(?:(?!(?:a|an|the|its|their|your|one)\b)[a-z][\w'-]*(?: [\w'-]+)?, )+"
            r"(?!(?:a|an|the|its|their|your|one)\b)[a-z][\w'-]*(?: [\w'-]+)?…['\"]|"
            r"(?-i:placeholder=['\"][A-Z][\w'-]* (?:the|of) [A-Z][\w'-]*…['\"])",
            re.IGNORECASE,
        ),
    ),
    Pattern(
        MEDIUM_RULE,
        re.compile(
            r"\b(photo-?realistic|photoreal|camera and lens|never a cartoon|wildlife photography|documentary style|astrophotography)\b",
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


def matches(path: Path, line: int, value: str, in_prompts: bool) -> list[Finding]:
    if MORTAL_KINSHIP.search(value):
        return []
    return [
        Finding(path, line, pattern.rule, match.group(0))
        for pattern in PATTERNS
        if (in_prompts or not pattern.prompts_only) and not (pattern.rule == MEDIUM_RULE and path in STYLE_HOMES)
        for match in [pattern.regex.search(prose(path, value) if pattern.prose_only else value)]
        if match
    ]


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in backend_targets():
        for line, value in strings_of(path):
            findings.extend(matches(path, line, value, path.is_relative_to(PROMPTS)))
    for path in frontend_targets():
        for line, value in frontend_strings(path):
            findings.extend(matches(path, line, value, in_prompts=False))
    return findings


def main() -> int:
    findings = scan()
    for finding in findings:
        print(finding.render())
    print(f"prompt bias: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
