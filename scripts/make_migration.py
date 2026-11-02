import subprocess
import sys
import tempfile
from pathlib import Path

from aerona.db.migrations import SCRIPT_LOCATION, autogenerate, upgrade_to_head_sync

MIGRATIONS_DIR = SCRIPT_LOCATION / "versions"


def main() -> int:
    message = " ".join(sys.argv[1:]) or "schema"
    with tempfile.TemporaryDirectory() as directory:
        url = f"sqlite+aiosqlite:///{Path(directory) / 'migration.db'}"
        upgrade_to_head_sync(url)
        autogenerate(url, message)
    for migration in MIGRATIONS_DIR.glob("*.py"):
        lines = migration.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if not line.strip().startswith("#")]
        migration.write_text("\n".join(kept) + "\n", encoding="utf-8")
    targets = [str(path) for path in MIGRATIONS_DIR.glob("*.py")]
    subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", "--quiet", *targets], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "format", "--quiet", *targets], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
