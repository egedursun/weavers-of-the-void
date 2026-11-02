from enum import StrEnum

from pydantic import BaseModel


class MaintenanceTask(StrEnum):
    COMPLETION = "completion"
    NETWORK_RULES = "network_rules"
    LOOSE_ENDS = "loose_ends"
    DATA_REPAIRS = "data_repairs"
    HISTORY_REPAIRS = "history_repairs"
    EPOCH_YEARS = "epoch_years"
    MORTAL_AGES = "mortal_ages"
    IMPORTANCE = "importance"
    ENDINGS = "endings"
    NARRATIVE_SWEEP = "narrative_sweep"
    CERTAIN_FACTS = "certain_facts"
    INTUITIONS = "intuitions"
    MIRROR_PAIRS = "mirror_pairs"
    CAPTIONS = "captions"
    PLANNER_STATISTICS = "planner_statistics"
    PRUNE = "prune"


class TaskInfo(BaseModel):
    task: MaintenanceTask
    title: str
    description: str
    automatic: str
    rows: list[str]
    ledgered: bool
    needs_llm: bool
    running: bool


class TaskResult(BaseModel):
    task: MaintenanceTask
    counters: dict[str, int]
    ledger_entry_id: int | None = None
