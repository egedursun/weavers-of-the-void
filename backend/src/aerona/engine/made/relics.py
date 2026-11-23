from sqlalchemy import select

from aerona.catalog.life.made import DECLINE, RESTORABLE, STANCE_USE
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRelicRow, SalvageSiteRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.made import RelicStance, RelicState, RelicUse
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.augments import seek_enhancements
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.research import raise_holder
from aerona.engine.made.backfill import keep_made_kinds, legacy_backfill
from aerona.engine.made.doctrine import doctrine_here
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.technology.profiles import family_level


async def holder_of(ctx: TickContext, thing: EntityRow) -> EntityRow | None:
    network = await ctx.session.get(NetworkProfileRow, thing.id)
    owner = network.owner_node_id if network is not None else thing.affiliated_entity_id
    found = await ctx.session.get(EntityRow, owner) if owner is not None else None
    if found is None and thing.location_id is not None:
        found = await ctx.session.get(EntityRow, thing.location_id)
    return found


async def mark_collapse(ctx: TickContext) -> int:
    marked = 0
    things: list[int] = []
    for network in list(
        await ctx.session.scalars(select(NetworkProfileRow).where(NetworkProfileRow.tech_level > 0).order_by(NetworkProfileRow.network_entity_id))
    ):
        if network.owner_node_id is None or held(network.network_entity_id) or await ctx.session.get(MadeRelicRow, network.network_entity_id) is not None:
            continue
        if await family_level(ctx.session, network.owner_node_id, TechFamily.COMMUNICATION) >= network.tech_level:
            continue
        ctx.session.add(
            MadeRelicRow(
                thing_node_id=network.network_entity_id,
                make_knowledge=network.tech_level,
                repair_knowledge=max(0, network.tech_level - 1),
                function_state=RelicState.FAILING,
                understood_pct=0,
                use=RelicUse.AS_MADE,
                is_relic=True,
                updated_epoch=ctx.epoch,
                locked=[],
            )
        )
        marked += 1
        things.append(network.network_entity_id)
    if marked:
        await record(ctx, "relic.collapse", roles={IncidentRole.SUBJECT: things}, facts={"marked": marked})
    return marked


async def keep_relic(ctx: TickContext, relic: MadeRelicRow, thing: EntityRow) -> None:
    table = ctx.rules.made_relics
    holder = await holder_of(ctx, thing)
    level = await family_level(ctx.session, holder.id, TechFamily.COMMUNICATION) if holder is not None else 0
    if "is_relic" not in relic.locked:
        relic.is_relic = level < relic.make_knowledge
    repairable = level >= relic.repair_knowledge
    if (
        not repairable
        and "function_state" not in relic.locked
        and relic.function_state in DECLINE
        and ctx.rng(f"relic.wear.{relic.thing_node_id}.{ctx.epoch}").chance(table.wear)
    ):
        relic.function_state = DECLINE[relic.function_state]
    if relic.use is RelicUse.REPURPOSED and "understood_pct" not in relic.locked:
        relic.understood_pct = clamp_percent(relic.understood_pct + table.study_gain)
    if await restore_or_dismantle(ctx, relic, thing, holder, repairable=repairable):
        return
    await recover_making(ctx, relic, thing, holder, repairable=repairable, level=level)
    misused = relic.use is RelicUse.AS_MADE or (
        relic.use is RelicUse.REPURPOSED and ctx.rng(f"relic.misuse.{relic.thing_node_id}.{ctx.epoch}").chance(table.wear)
    )
    if relic.function_state is RelicState.FAILING and misused and holder is not None and not held(holder.id):
        shift_stat(holder, "prosperity", -table.misuse_harm, 0)
    if relic.understood_pct < table.revere_below and holder is not None and "use" not in relic.locked:
        doctrine = await doctrine_here(ctx.session, holder)
        if doctrine is not None and doctrine.relic_stance in STANCE_USE:
            before = relic.use
            relic.use = STANCE_USE[doctrine.relic_stance]
            if doctrine.relic_stance is RelicStance.STUDIED and before is not relic.use:
                await record(
                    ctx,
                    "relic.studied",
                    roles={IncidentRole.SUBJECT: thing.id, IncidentRole.OWNER: holder.id},
                    facts={"understood": relic.understood_pct},
                    place=thing.location_id,
                )
        elif doctrine is None and level == 0:
            relic.use = RelicUse.IGNORED
    if "function_state" not in relic.locked:
        if relic.use is RelicUse.IGNORED and relic.function_state is RelicState.WORKING:
            relic.function_state = RelicState.DORMANT
        elif relic.use is not RelicUse.IGNORED and relic.function_state is RelicState.DORMANT:
            relic.function_state = RelicState.WORKING
    relic.updated_epoch = ctx.epoch


async def recover_making(ctx: TickContext, relic: MadeRelicRow, thing: EntityRow, holder: EntityRow | None, *, repairable: bool, level: int) -> None:
    table = ctx.rules.made_relics
    if relic.understood_pct >= table.recovery_at and not repairable and "repair_knowledge" not in relic.locked:
        relic.repair_knowledge = level
        await record(
            ctx,
            "relic.recovered",
            roles={IncidentRole.SUBJECT: thing.id, IncidentRole.OWNER: holder.id if holder is not None else None},
            facts={"understood": relic.understood_pct, "repair_knowledge": level},
            place=thing.location_id,
        )


async def restore_or_dismantle(ctx: TickContext, relic: MadeRelicRow, thing: EntityRow, holder: EntityRow | None, *, repairable: bool) -> bool:
    restorable = relic.function_state in RESTORABLE and "function_state" not in relic.locked
    if relic.understood_pct >= ctx.rules.made_relics.recovery_at and repairable and restorable:
        relic.function_state = RelicState.RESTORED
        owner = holder.id if holder is not None else None
        await record(ctx, "relic.restored", roles={IncidentRole.SUBJECT: thing.id, IncidentRole.OWNER: owner}, place=thing.location_id)
    if relic.use is RelicUse.DISMANTLED and relic.is_relic:
        await dismantle(ctx, relic, thing, holder)
        return True
    return False


async def dismantle(ctx: TickContext, relic: MadeRelicRow, thing: EntityRow, holder: EntityRow | None) -> None:
    table = ctx.rules.made_relics
    if holder is not None and not held(holder.id):
        await give_coin(ctx.session, ctx.rules, holder, table.dismantle_yield)
        await raise_holder(ctx, holder.id, KnowledgeBranch.METALLURGY, table.dismantle_cap)
    relic.is_relic = False
    relic.function_state = RelicState.BROKEN
    relic.updated_epoch = ctx.epoch
    await record(
        ctx,
        "relic.dismantled",
        roles={IncidentRole.SUBJECT: thing.id, IncidentRole.OWNER: holder.id if holder is not None else None},
        facts={"salvage": table.dismantle_yield},
    )


async def salvage(ctx: TickContext) -> int:
    table = ctx.rules.made_relics
    taken = 0
    for site in list(await ctx.session.scalars(select(SalvageSiteRow).where(SalvageSiteRow.yield_left > 0).order_by(SalvageSiteRow.site_entity_id))):
        if site.rights_holder_node_id is None or held(site.site_entity_id) or held(site.rights_holder_node_id):
            continue
        holder = await ctx.session.get(EntityRow, site.rights_holder_node_id)
        if holder is None or holder.status is not EntityStatus.CANON:
            continue
        amount = min(site.yield_left, table.salvage_yield)
        await give_coin(ctx.session, ctx.rules, holder, amount)
        site.yield_left -= amount
        site.last_salvaged_epoch = ctx.epoch
        taken += 1
        if site.yield_left <= 0:
            await record(
                ctx, "salvage.exhausted", roles={IncidentRole.SUBJECT: site.site_entity_id, IncidentRole.OWNER: holder.id}, facts={"last_yield": amount}
            )
    return taken


@reads(
    "table.applied_fixups",
    "table.augments",
    "table.cult_doctrines",
    "table.culture_values",
    "table.entities",
    "table.holder_levels",
    "table.made_relics",
    "table.network_profiles",
    "table.nodes",
    "table.people_substrates",
    "table.place_profiles",
    "table.prostheses",
    "table.replicator_lines",
    "table.salvage_sites",
    "table.structure_profiles",
)
@writes(
    "table.applied_fixups",
    "table.cult_doctrines",
    "table.entities",
    "table.made_relics",
    "table.mortal_profiles",
    "table.people_substrates",
    "table.salvage_sites",
    "table.settlement_profiles",
)
async def keep_relics(ctx: TickContext) -> None:
    ctx.count("made_world_backfilled", await legacy_backfill(ctx))
    ctx.count("made_kinds_kept", await keep_made_kinds(ctx))
    ctx.count("augments_sought", await seek_enhancements(ctx))
    ctx.count("relics_marked", await mark_collapse(ctx))
    for relic in list(await ctx.session.scalars(select(MadeRelicRow).order_by(MadeRelicRow.thing_node_id))):
        thing = await ctx.session.get(EntityRow, relic.thing_node_id)
        if thing is None or held(relic.thing_node_id):
            continue
        await keep_relic(ctx, relic, thing)
    ctx.count("salvages", await salvage(ctx))
    await ctx.session.flush()
