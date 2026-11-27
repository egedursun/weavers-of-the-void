import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def settle(ctx, row, subject):
    await record(ctx, "mood.spread", roles={IncidentRole.SUBJECT: subject})


async def homes(ctx):
    kept = {household for household in await ctx.session.scalars(select(FeelingSpreadRow.household_id)) if household is not None}
    for household in sorted(kept):
        await settle(ctx, None, household)


async def play(ctx, game: GameRow, power: PowerRow):
    await practise_subject(ctx.session, ctx.rules, 1, game.skill, subject_id=game.id, xp=1, epoch=1)
    await afflict(ctx, None, None, None, source_node_id=power.source_id)


async def fine(ctx, town: EntityRow, house: HouseholdRow):
    await record(ctx, "mood.spread", roles={IncidentRole.SUBJECT: town.id})
    await record(ctx, "mood.spread_household", roles={IncidentRole.SUBJECT: house.head_node_id})
    for security in await ctx.session.scalars(query.order_by(IssuedSecurityRow.id)):
        await record(ctx, "x", roles={IncidentRole.SUBJECT: security.issuer_node_id})
    place = await ctx.session.get(EntityRow, 3) if house is None else None
    await record(ctx, "x", roles={IncidentRole.SUBJECT: place.id})
"""


def checker() -> ModuleType:
    scripts = REPOSITORY_ROOT / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("check_role_ids", scripts / "check_role_ids.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_role_ids"] = module
    spec.loader.exec_module(module)
    return module


def test_an_id_of_a_table_that_is_no_node_passed_as_a_node_is_flagged() -> None:
    found = checker().strays({Path("module.py"): RAW})
    assert [(item.line, item.table) for item in found] == [(9, "households"), (13, "games"), (14, "power_sources")]


def test_the_backend_passes_only_nodes_where_a_node_is_meant() -> None:
    module = checker()
    assert module.strays({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
