from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class AgentsRules:
    concurrent_jobs: int = rule(8, 1, 32, RuleGroup.AGENTS_AND_MODEL, "Maximum simultaneous content jobs (deepening, epic, prompt); the rest are queued")
    auto_deepen: int = rule(3, 0, 20, RuleGroup.AGENTS_AND_MODEL, "Records to auto-deepen at epoch end (0 off)")
    manual_job_share: int = rule(
        2, 0, 12, RuleGroup.AGENTS_AND_MODEL, "Simultaneous job slots that background work (auto-deepening, stale epics) leaves free for manual jobs"
    )
    sons_parallel: int = rule(2, 1, 6, RuleGroup.AGENTS_AND_MODEL, "Sons thinking at the same time")
    local_god_epochs: int = rule(3, 1, 200, RuleGroup.COSMOS, "Epochs for a sleeping local god to be born on a godless world")
    local_god_rebirth_epochs: int = rule(5, 0, 1000, RuleGroup.COSMOS, "Epochs for a new sleeping god to be born on a world whose native god died (mourning)")
    local_god_strength: int = rule(30, 1, 100, RuleGroup.COSMOS, "Strength of a sleeping local god")
    local_god_worshipped_pct: int = rule(
        50, 0, 100, RuleGroup.COSMOS, "No local god is born on a world where at least this share of communities worships a son or the Creator"
    )
    local_god_with_sons: int = rule(0, 0, 1, RuleGroup.COSMOS, "Can a local god be born on a world a son lives on or guards (1: yes, 0: no)")
    prompt_batches: int = rule(10, 1, 1000, RuleGroup.AGENTS_AND_MODEL, 'Manual "write prompts": maximum number of batches')
    auto_deepen_power_weight: int = rule(2, 0, 100, RuleGroup.AGENTS_AND_MODEL, "Auto-deepening order: weight of one power level equivalent to one link")
    epic_refresh_epochs: int = rule(
        8,
        0,
        1000,
        RuleGroup.AGENTS_AND_MODEL,
        "Stale epic: when the Creator's and sons' epic/depth is this many epochs old it is rewritten in the background at epoch end (0 off)",
    )
    epic_refresh_per_epoch: int = rule(
        1, 0, 20, RuleGroup.AGENTS_AND_MODEL, "Stale epic: maximum refreshed per epoch (low priority: when the job pool is idle)"
    )
    mad_son_action_loss: int = rule(1, 0, 10, RuleGroup.AGENTS_AND_MODEL, "Action points a son loses while their sanity is below the madness threshold")
    localise_batch: int = rule(
        40, 1, 500, RuleGroup.AGENTS_AND_MODEL, "Engine chronicle lines translated into the lore language per model call (non-English worlds)"
    )
