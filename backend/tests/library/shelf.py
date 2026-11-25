import hashlib
import io
import json
import sqlite3
import tarfile
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from PIL import Image

from tests.polling import until

LOCAL_ORIGIN = {"origin": "http://localhost"}
POLL_SECONDS = 0.05
SETTLED = frozenset({"waiting", "done", "failed", "cancelled"})
TABLES_QUERY = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"


def png(width: int = 64, height: int = 32) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 90, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


async def settled(http: AsyncClient, path: str) -> dict[str, Any]:
    bodies: list[dict[str, Any]] = []

    async def done() -> bool:
        bodies.append((await http.get(path)).json())
        return bodies[-1]["status"] in SETTLED

    assert await until(done, step=POLL_SECONDS), f"{path} never settled"
    return bodies[-1]


async def exported(http: AsyncClient, universe_id: str) -> bytes:
    job = (await http.post(f"/api/library/universes/{universe_id}/export")).json()
    finished = await settled(http, f"/api/library/exports/{job['id']}")
    assert finished["status"] == "done", finished
    response = await http.get(f"/api/library/exports/{job['id']}/file")
    assert response.status_code == 200
    return response.content


async def uploaded(http: AsyncClient, data: bytes, file_name: str = "shared.aerona") -> dict[str, Any]:
    response = await http.post("/api/library/imports", files={"file": (file_name, data, "application/octet-stream")}, headers=LOCAL_ORIGIN)
    assert response.status_code == 202, response.text
    return await settled(http, f"/api/library/imports/{response.json()['id']}")


async def imported(http: AsyncClient, data: bytes, name: str | None = None) -> dict[str, Any]:
    checked = await uploaded(http, data)
    assert checked["status"] == "waiting", checked
    confirmed = await http.post(f"/api/library/imports/{checked['id']}/confirm", json={"name": name} if name else {})
    assert confirmed.status_code == 202, confirmed.text
    finished = await settled(http, f"/api/library/imports/{checked['id']}")
    assert finished["status"] == "done", finished
    return finished


def members_of(data: bytes) -> list[tuple[str, bytes]]:
    found: list[tuple[str, bytes]] = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            handle = archive.extractfile(member)
            found.append((member.name, handle.read() if handle is not None else b""))
    return found


def packed(members: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, body in members:
            info = tarfile.TarInfo(name)
            info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


def relisted(members: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    library = json.loads(dict(members)["library.json"])
    bodies = dict(members)
    library["files"] = [
        {"path": item["path"], "size": len(bodies[item["path"]]), "sha256": hashlib.sha256(bodies[item["path"]]).hexdigest()} for item in library["files"]
    ]
    encoded = json.dumps(library).encode()
    return [(name, encoded if name == "library.json" else body) for name, body in members]


def replaced(members: list[tuple[str, bytes]], name: str, body: bytes) -> list[tuple[str, bytes]]:
    return [(found, body if found == name else data) for found, data in members]


def database_with(data: bytes, tmp: Path, statement: str) -> bytes:
    path = tmp / "edited.db"
    path.write_bytes(data)
    connection = sqlite3.connect(path)
    try:
        connection.execute(statement)
        connection.commit()
    finally:
        connection.close()
    return path.read_bytes()


def table_digests(path: Path) -> dict[str, tuple[int, str]]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        found: dict[str, tuple[int, str]] = {}
        for (table,) in connection.execute(TABLES_QUERY).fetchall():
            columns = len(connection.execute(f'SELECT * FROM "{table}" LIMIT 0').description)
            order = ", ".join(str(position) for position in range(1, columns + 1))
            rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY {order}').fetchall()
            found[table] = (len(rows), hashlib.sha256(repr(rows).encode()).hexdigest())
        return found
    finally:
        connection.close()


def tree_of(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
