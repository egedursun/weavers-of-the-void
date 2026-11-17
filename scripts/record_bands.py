import argparse
import asyncio
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from aerona.db import tables
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.engine.pipeline import simulate
from aerona.engine.recording.bands import (
    place_share,
    record_counts,
    rows_per_thousand,
    terms_share,
)
from aerona.engine.startup import prepare_engine
from sqlalchemy import func, select

assert tables

ROOT = Path(__file__).resolve().parent.parent
BANDS = ROOT / "docs" / "spec" / "13-balance-bands.json"


@dataclass(frozen=True)
class RecordBand:
    metric: str
    low: float
    high: float
    meaning: str


def load_record_bands() -> tuple[list[RecordBand], dict[str, float]]:
    data = json.loads(BANDS.read_text(encoding="utf-8"))
    section = data["record_bands"]
    return [
        RecordBand(item["metric"], item["low"], item["high"], item["meaning"])
        for item in section["bands"]
    ], section["baseline"]


async def last_ids(database: Database) -> tuple[int, int]:
    async with database.read() as session:
        incident = int(
            await session.scalar(select(func.coalesce(func.max(IncidentRow.id), 0)))
            or 0
        )
        change = int(
            await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0)))
            or 0
        )
    return incident, change


async def measure(path: Path, epochs: int) -> dict[str, float]:
    _, baseline = load_record_bands()
    database = Database(f"sqlite+aiosqlite:///{path}")
    try:
        await prepare_engine(database)
        async with database.read() as session:
            before = await record_counts(session)
        since_incident, since_change = await last_ids(database)
        started = time.perf_counter()
        await simulate(database, epochs)
        seconds = (time.perf_counter() - started) / max(1, epochs)
        async with database.read() as session:
            after = await record_counts(session)
            terms = await terms_share(session, since_change)
            places = await place_share(session, since_incident)
    finally:
        await database.dispose()
    return {
        "record_rows_per_epoch_per_thousand_mortals": rows_per_thousand(
            before, after, epochs
        ),
        "numeric_changes_with_terms_pct": terms,
        "required_places_given_pct": places,
        "epoch_time_added_by_recording_pct": 100
        * (seconds - baseline["epoch_seconds"])
        / baseline["epoch_seconds"],
    }


def outside(values: dict[str, float]) -> list[str]:
    bands, _ = load_record_bands()
    return [
        f"{band.metric} = {values[band.metric]:.2f} outside [{band.low}, {band.high}]"
        for band in bands
        if not band.low <= values[band.metric] <= band.high
    ]


def copy_of(source: Path, folder: str) -> Path:
    target = Path(folder) / "record_bands.db"
    with sqlite3.connect(source) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--epochs", type=int, default=1)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        values = asyncio.run(
            measure(copy_of(arguments.world, folder), arguments.epochs)
        )
        shutil.rmtree(folder, ignore_errors=True)
    for key, value in values.items():
        print(f"{key}: {value:.2f}")
    problems = outside(values)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
