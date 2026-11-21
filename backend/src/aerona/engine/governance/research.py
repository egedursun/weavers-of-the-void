from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.read_memo import memoized
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.governance import OrgResearchRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.lore.research import holder_levels, techniques_of
from aerona.engine.lore.research_depth import open_techniques
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

PROGRESS_LOCK = "progress"


async def home_of(ctx: TickContext, org: EntityRow) -> int | None:
    profile = await ctx.session.get(FactionProfileRow, org.id)
    return profile.home_entity_id if profile is not None and profile.home_entity_id is not None else org.location_id


@memoized(OrgResearchRow)
async def research_by_org(session: AsyncSession) -> dict[int, list[OrgResearchRow]]:
    found: dict[int, list[OrgResearchRow]] = {}
    for row in await session.scalars(select(OrgResearchRow).order_by(OrgResearchRow.org_node_id, OrgResearchRow.id)):
        found.setdefault(row.org_node_id, []).append(row)
    return found


async def open_research(ctx: TickContext, org_id: int) -> list[OrgResearchRow]:
    return [row for row in (await research_by_org(ctx.session)).get(org_id, []) if row.done_epoch is None]


async def reachable(ctx: TickContext, org: EntityRow) -> list[Technique]:
    home = await home_of(ctx, org)
    if home is None:
        return []
    levels = (await holder_levels(ctx.session)).get(home, {})
    known = await techniques_of(ctx.session, org.id)
    return [technique for technique in await open_techniques(ctx.session, home, levels) if technique not in known]


async def begin_research(ctx: TickContext, org: EntityRow, technique: Technique | None, design_id: int | None, budget: int) -> OrgResearchRow:
    row = OrgResearchRow(
        org_node_id=org.id,
        technique=technique,
        design_id=design_id,
        budget=budget,
        staff=ctx.rules.governance.research_first_staff,
        secrecy=ctx.rules.governance.research_secrecy,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def research_for_strategy(ctx: TickContext, org: EntityRow) -> OrgResearchRow | None:
    if await open_research(ctx, org.id):
        return None
    options = await reachable(ctx, org)
    if not options:
        return None
    technique = ctx.rng(f"governance.research_pick.{org.id}.{ctx.epoch}").pick(options)
    return await begin_research(ctx, org, technique, None, ctx.rules.governance.research_budget)


async def finish(ctx: TickContext, org: EntityRow, row: OrgResearchRow) -> None:
    row.done_epoch = ctx.epoch
    secret = row.secrecy > 0
    if row.technique is not None and await ctx.session.get(HolderTechniqueRow, (org.id, row.technique)) is None:
        ctx.session.add(HolderTechniqueRow(holder_entity_id=org.id, technique=row.technique, since_epoch=ctx.epoch, secret=secret))
    design = await ctx.session.get(DesignRow, row.design_id) if row.design_id is not None else None
    if design is not None and "owner_entity_id" not in (design.locked or []):
        design.owner_entity_id = org.id
    await record(
        ctx,
        "org.research_done",
        roles={IncidentRole.ACTOR: org.id},
        facts={
            "pursuit": spoken(row.technique) if row.technique is not None else design.name if design is not None else "a design",
            "kept": "in secret" if secret else "openly",
        },
    )


async def advance_research(ctx: TickContext, org: EntityRow, row: OrgResearchRow) -> bool:
    table = ctx.rules.governance
    if PROGRESS_LOCK in (row.locked or []) or row.budget <= 0 or row.staff <= 0:
        return False
    spent = min(row.budget, table.research_cost_per_staff * row.staff)
    if not await take_coin(ctx.session, ctx.rules, org, spent):
        return False
    row.budget -= spent
    row.progress = clamp_int(row.progress + row.staff * table.research_progress_per_staff, 0, PERCENT)
    if row.progress >= PERCENT:
        await finish(ctx, org, row)
        return True
    return False


async def spread_secrets(ctx: TickContext, org: EntityRow) -> int:
    rows = [row for row in (await research_by_org(ctx.session)).get(org.id, []) if row.done_epoch is not None]
    spread = 0
    for row in rows:
        if row.technique is None:
            continue
        known = await ctx.session.get(HolderTechniqueRow, (org.id, row.technique))
        if known is None or not known.secret:
            continue
        chance = ctx.rules.governance.secret_spread_per_epoch_pct * (PERCENT - row.secrecy) / PERCENT
        if ctx.rng(f"governance.secret.{row.id}.{ctx.epoch}").chance(chance):
            known.secret = False
            spread += 1
    return spread


async def tend_research(ctx: TickContext, org: EntityRow) -> tuple[int, int]:
    if held(org.id):
        return 0, 0
    done = 0
    for row in await open_research(ctx, org.id):
        done += 1 if await advance_research(ctx, org, row) else 0
    return done, await spread_secrets(ctx, org)
