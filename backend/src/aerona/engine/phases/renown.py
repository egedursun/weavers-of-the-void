from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.renown import ReputationRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.renown.book import aggregate
from aerona.engine.renown.claims import tend_claims
from aerona.engine.renown.currencies import CurrencyTally, tend_currencies
from aerona.engine.renown.deeds import DeedTally, hearsay
from aerona.engine.renown.lore import LoreTally, market


def count(ctx: TickContext, prefix: str, tally: object) -> None:
    for key, value in vars(tally).items():
        ctx.count(f"{prefix}_{key}", value)


async def fade_and_sum(ctx: TickContext) -> tuple[int, int]:
    table = ctx.rules.local_renown
    faded = raised = 0
    by_subject: dict[int, list[ReputationRow]] = defaultdict(list)
    for row in list(await ctx.session.scalars(select(ReputationRow).order_by(ReputationRow.id))):
        if held(row.subject_node_id):
            continue
        if row.heard_epoch < ctx.epoch and "value" not in row.locked and table.fade:
            row.value = max(0, row.value - table.fade)
            faded += 1
        if row.value == 0 and not row.locked:
            await ctx.session.delete(row)
            continue
        by_subject[row.subject_node_id].append(row)
    for subject_id, rows in sorted(by_subject.items()):
        profile = await ctx.session.get(MortalProfileRow, subject_id)
        if profile is None:
            continue
        glory, infamy = aggregate(rows)
        if "renown" not in profile.locked:
            lifted = clamp_int(glory * table.aggregate_pct / PERCENT, 0, PERCENT)
            raised += lifted > profile.renown
            profile.renown = max(profile.renown, lifted)
        if "infamy" not in profile.locked:
            profile.infamy = max(profile.infamy, clamp_int(infamy * table.aggregate_pct / PERCENT, 0, PERCENT))
    await ctx.session.flush()
    return faded, raised


@reads("table.culture_ethics", "table.deed_claims", "table.deeds", "table.mortal_profiles", "table.reputations", "table.rumours")
@writes("table.deed_claims", "table.mortal_profiles", "table.reputations")
async def renown_hearsay(ctx: TickContext) -> None:
    tally = DeedTally()
    await hearsay(ctx, tally)
    faded, raised = await fade_and_sum(ctx)
    ctx.count("reputation_faded", faded)
    ctx.count("renown_raised", raised)
    count(ctx, "deed", tally)


@reads("table.deed_claims", "table.deeds", "table.incident_participants")
async def renown_claims(ctx: TickContext) -> None:
    tally = DeedTally()
    await tend_claims(ctx, tally)
    count(ctx, "claim", tally)


@reads("table.faction_profiles", "table.offices", "table.polity_members", "table.reputations", "table.ruler_currencies")
@writes("table.ruler_currencies")
async def ruler_currencies(ctx: TickContext) -> None:
    tally = CurrencyTally()
    await tend_currencies(ctx, tally)
    count(ctx, "currency", tally)


@reads(
    "table.bonds",
    "table.faction_profiles",
    "table.holder_techniques",
    "table.polity_map_knowledge",
    "table.prophecy_conditions",
    "table.reputations",
    "table.world_maps",
)
@writes("table.faction_profiles", "table.holder_techniques", "table.lore_trades", "table.reputations")
async def lore_market(ctx: TickContext) -> None:
    tally = LoreTally()
    await market(ctx, tally)
    count(ctx, "lore", tally)


PHASES = (
    Phase("renown_hearsay", renown_hearsay),
    Phase("renown_claims", renown_claims),
    Phase("ruler_currencies", ruler_currencies),
    Phase("lore_market", lore_market),
)
