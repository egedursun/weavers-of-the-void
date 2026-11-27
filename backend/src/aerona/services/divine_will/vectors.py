import sqlite3
import threading
from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from aerona.services.divine_will.embedding import DIMENSIONS

VECTORS_FILE = "vectors.db"
WRITE_BATCH = 500

Vector16 = NDArray[np.float16]


class VectorStore:
    def __init__(self, folder: Path) -> None:
        self.path = folder / VECTORS_FILE
        self._lock = threading.Lock()
        self._connection: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, check_same_thread=False)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS vectors (digest TEXT PRIMARY KEY, vector BLOB NOT NULL)")
            self._connection = connection
        return self._connection

    def load(self) -> dict[str, Vector16]:
        with self._lock:
            found: dict[str, Vector16] = {}
            for digest, blob in self._connect().execute("SELECT digest, vector FROM vectors ORDER BY digest"):
                vector = np.frombuffer(blob, dtype=np.float16)
                if vector.size == DIMENSIONS:
                    found[str(digest)] = vector
            return found

    def add(self, vectors: Mapping[str, Vector16]) -> None:
        if not vectors:
            return
        with self._lock:
            connection = self._connect()
            items = sorted(vectors.items())
            for start in range(0, len(items), WRITE_BATCH):
                connection.executemany(
                    "INSERT OR REPLACE INTO vectors (digest, vector) VALUES (?, ?)",
                    ((digest, vector.astype(np.float16).tobytes()) for digest, vector in items[start : start + WRITE_BATCH]),
                )
            connection.commit()

    def keep(self, digests: Iterable[str]) -> int:
        wanted = set(digests)
        with self._lock:
            connection = self._connect()
            stale = [digest for (digest,) in connection.execute("SELECT digest FROM vectors ORDER BY digest") if digest not in wanted]
            for start in range(0, len(stale), WRITE_BATCH):
                part = stale[start : start + WRITE_BATCH]
                connection.execute(f"DELETE FROM vectors WHERE digest IN ({','.join('?' * len(part))})", part)
            connection.commit()
            return len(stale)

    def reset(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
            for suffix in ("", "-wal", "-shm"):
                Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
