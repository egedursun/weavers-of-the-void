import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

INIT = """
class Rules:
    taxation: TaxationRules = field(default_factory=TaxationRules)
    campaigns: CampaignsRules = field(default_factory=CampaignsRules)
"""

REGISTRY = """
class TaxationRules(Spanned):
    per_capita_output: int = rule(2, 0, 100, G, "Taxable output of a hundred people in a year")
    rate_cap: int = rule(50, 0, 100, G, "Highest tax rate (%)")


class CampaignsRules(Spanned):
    seasons_per_war_epoch: int = rule(1, 0, 12, G, "Campaign seasons an active war fights each year")
    usual_leave: int = rule(10, 0, 100, G, "Share of a year that is the usual leave")
"""

SOURCE = """
async def collect_taxes(ctx, town):
    table = ctx.rules.taxation
    return town.people * table.per_capita_output * table.rate_cap


async def scaled_taxes(ctx, town):
    table = ctx.rules.taxation
    return town.people * table.per_epoch(table.per_capita_output)


def infected(ctx, campaign):
    return max(1, ctx.rules.campaigns.seasons_per_war_epoch) if campaign else 1


def on_leave(ctx):
    return ctx.rules.campaigns.usual_leave


def in_years(ctx, world):
    return [ctx.rules.campaigns.seasons_per_war_epoch for _ in world_years(ctx.environment, world, "war")]
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_yearly_rules", REPOSITORY_ROOT / "scripts" / "check_yearly_rules.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_yearly_rules"] = module
    spec.loader.exec_module(module)
    return module


def test_a_yearly_rule_read_once_an_epoch_is_flagged_and_a_scaled_or_partial_one_is_not() -> None:
    module = checker()
    yearly = module.yearly_rules({Path("registry.py"): REGISTRY}, module.table_names(INIT))
    assert set(yearly) == {("taxation", "per_capita_output"), ("campaigns", "seasons_per_war_epoch")}
    found = module.unscaled_reads({Path("module.py"): SOURCE}, yearly)
    assert [(item.line, item.name) for item in found] == [(4, "per_capita_output"), (13, "seasons_per_war_epoch")]


def test_the_engine_reads_no_yearly_rule_unscaled() -> None:
    module = checker()
    yearly = module.yearly_rules(
        {path: path.read_text(encoding="utf-8") for path in sorted(module.REGISTRY.glob("*.py"))},
        module.table_names((module.REGISTRY / "__init__.py").read_text(encoding="utf-8")),
    )
    assert len(yearly) > 20
    assert module.unscaled_reads(module.engine_files(), yearly) == []
