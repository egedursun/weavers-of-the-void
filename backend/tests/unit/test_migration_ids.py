import re
from collections import Counter
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[2] / "src" / "aerona" / "db" / "alembic" / "versions"
REVISION = re.compile(r'^revision = "([0-9a-z_]+)"', re.M)
DOWN = re.compile(r"^down_revision = (.+)$", re.M)


def test_every_migration_has_its_own_id_and_the_chain_has_one_head() -> None:
    revisions: list[str] = []
    downs: set[str] = set()
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        found = REVISION.search(text)
        assert found is not None, path.name
        revisions.append(found.group(1))
        down = DOWN.search(text)
        if down is not None:
            downs.update(re.findall(r'"([0-9a-z_]+)"', down.group(1)))
    assert [revision for revision, count in Counter(revisions).items() if count > 1] == []
    assert len(set(revisions) - downs) == 1
