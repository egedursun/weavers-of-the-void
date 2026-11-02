from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class BatchRules:
    concurrent: int = rule(1, 1, 4, RuleGroup.BATCH_JOBS, "Records processed simultaneously in batch deepening")
    wait_seconds: int = rule(0, 0, 600, RuleGroup.BATCH_JOBS, "Wait between two records in batch deepening (s)")
    retries: int = rule(2, 0, 5, RuleGroup.BATCH_JOBS, "Retry a failed record in batch deepening")
    pool_wait_seconds: int = rule(5, 1, 600, RuleGroup.BATCH_JOBS, "Batch deepening: re-check interval if the job pool is full (s)")
    retry_wait_seconds: int = rule(3, 0, 600, RuleGroup.BATCH_JOBS, "Wait before retrying a failed record in batch deepening (s)")
    log_lines: int = rule(200, 20, 5000, RuleGroup.BATCH_JOBS, "Lines kept in the batch-job log")
