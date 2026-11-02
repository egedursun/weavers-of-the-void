import hashlib
import secrets
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath

from aerona.constants.maintenance import IMPORTED_OBJECT_PREFIX, IMPORTED_OBJECT_TOKEN_BYTES
from aerona.media.keys import is_original_key, is_sha256, original_key
from aerona.media.store import MediaStore, read_all

KNOWN_QUERY = "SELECT sha256, object_key FROM images ORDER BY id"
ROWS_QUERY = "SELECT id, object_key, sha256 FROM images"
RELINK_STATEMENT = "UPDATE images SET object_key = ?, sha256 = ? WHERE id = ?"
DROP_STATEMENT = "DELETE FROM images WHERE id = ?"
PROMOTE_COVERS = (
    "UPDATE images SET is_cover = 1 WHERE id IN (SELECT MAX(id) FROM images GROUP BY target_node_id HAVING SUM(CASE WHEN is_cover THEN 1 ELSE 0 END) = 0)"
)


def digest_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def known_objects(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        known: dict[str, str] = {}
        for digest, key in connection.execute(KNOWN_QUERY):
            if is_sha256(digest) and is_original_key(str(key)):
                known.setdefault(str(digest), str(key))
        return known
    except sqlite3.Error:
        return {}
    finally:
        connection.close()


def relink_images(path: Path, mapping: Mapping[str, str], digests: Mapping[str, str]) -> int:
    connection = sqlite3.connect(path)
    try:
        dropped = 0
        rows = connection.execute(ROWS_QUERY).fetchall()
        for row_id, key, digest in rows:
            local = mapping.get(str(key))
            if local is None:
                connection.execute(DROP_STATEMENT, (row_id,))
                dropped += 1
            else:
                connection.execute(RELINK_STATEMENT, (local, digests.get(str(key), digest), row_id))
        connection.execute(PROMOTE_COVERS)
        connection.commit()
        return dropped
    finally:
        connection.close()


def fresh_key(key: str) -> str:
    name = PurePosixPath(key).name
    return original_key(f"{IMPORTED_OBJECT_PREFIX}{secrets.token_hex(IMPORTED_OBJECT_TOKEN_BYTES)}-{name}")


class MediaReceiver:
    def __init__(self, store: MediaStore, known: Mapping[str, str]) -> None:
        self._store = store
        self._known = dict(known)
        self.mapping: dict[str, str] = {}
        self.digests: dict[str, str] = {}
        self.written: list[str] = []

    async def receive(self, key: str, data: bytes, digest: str) -> None:
        if not is_original_key(key) or key in self.mapping:
            return
        local = self._known.get(digest)
        if local is None or not await self._store.exists(local):
            local = await self._place(key, data, digest)
            self._known[digest] = local
        self.mapping[key] = local
        self.digests[key] = digest

    async def _place(self, key: str, data: bytes, digest: str) -> str:
        existing = await read_all(self._store, key)
        if existing is not None and digest_of(existing) == digest:
            return key
        target = key if existing is None else fresh_key(key)
        await self._store.put(target, data)
        self.written.append(target)
        return target

    async def adopt_present(self, keys: Iterable[str]) -> None:
        for key in sorted(set(keys) - set(self.mapping)):
            if is_original_key(key) and await self._store.exists(key):
                self.mapping[key] = key

    async def discard(self) -> None:
        for key in self.written:
            await self._store.delete(key)
        self.written.clear()
