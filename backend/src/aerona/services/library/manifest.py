import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aerona.constants.library import MANIFEST_FORMAT, MANIFEST_VERSION, UNIVERSE_ID_PATTERN
from aerona.domain.enums.library import UniverseOrigin

PARTIAL_SUFFIX = ".partial"
TOKEN_BYTES = 4
UNIVERSE_ID = re.compile(UNIVERSE_ID_PATTERN)


@dataclass(frozen=True)
class UniverseManifest:
    id: str
    name: str
    summary: str
    notes: str
    tags: tuple[str, ...]
    origin: UniverseOrigin
    origin_note: str
    media_prefix: str
    created_at: datetime
    schema_revision: str
    app_version: str
    epoch: int
    year: int

    def as_json(self) -> dict[str, Any]:
        return {
            "format": MANIFEST_FORMAT,
            "version": MANIFEST_VERSION,
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "notes": self.notes,
            "tags": list(self.tags),
            "origin": self.origin.value,
            "origin_note": self.origin_note,
            "media_prefix": self.media_prefix,
            "created_at": self.created_at.isoformat(),
            "schema_revision": self.schema_revision,
            "app_version": self.app_version,
            "epoch": self.epoch,
            "year": self.year,
        }


def write_manifest(path: Path, manifest: UniverseManifest) -> None:
    partial = path.with_name(f"{path.name}.{secrets.token_hex(TOKEN_BYTES)}{PARTIAL_SUFFIX}")
    try:
        partial.write_text(json.dumps(manifest.as_json(), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def read_manifest(path: Path) -> UniverseManifest | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != MANIFEST_FORMAT or not isinstance(data.get("id"), str):
            return None
        if not UNIVERSE_ID.match(data["id"]):
            return None
        return UniverseManifest(
            id=data["id"],
            name=str(data["name"]),
            summary=str(data.get("summary", "")),
            notes=str(data.get("notes", "")),
            tags=tuple(str(tag) for tag in data.get("tags", [])),
            origin=UniverseOrigin(data.get("origin", UniverseOrigin.ADOPTED.value)),
            origin_note=str(data.get("origin_note", "")),
            media_prefix=str(data.get("media_prefix", "")),
            created_at=datetime.fromisoformat(data["created_at"]),
            schema_revision=str(data.get("schema_revision", "")),
            app_version=str(data.get("app_version", "")),
            epoch=int(data.get("epoch", 0)),
            year=int(data.get("year", 0)),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
