from sqlalchemy import select

from aerona.catalog.life.domain import GONE_STATES, STANDING_STATES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.structure import ConstructionState, RuinCause
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import decay_loss
from aerona.engine.economy.stocks import goods_of
from aerona.engine.means.building import can_repair, weathering
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.structures.integrity import ensure_sections, mend_sections, overall, state_for
from aerona.engine.structures.profiles import host_for, material_props, refresh, standing_state
from aerona.engine.structures.spec import Resolved
from aerona.engine.structures.workshops import unlink


async def pay_coin(ctx: TickContext, profile: StructureProfileRow, work: EntityRow) -> bool:
    if profile.upkeep_coin <= 0:
        return True
    town = await ctx.session.get(SettlementProfileRow, profile.host_entity_id) if profile.host_entity_id is not None else None
    if town is None:
        return profile.host_entity_id is not None
    if town.treasury < profile.upkeep_coin:
        return False
    town.treasury -= profile.upkeep_coin
    ctx.session.add(
        SettlementTreasuryRow(
            settlement_entity_id=town.settlement_entity_id,
            epoch=ctx.epoch,
            entry=TreasuryEntry.UPKEEP,
            amount=-profile.upkeep_coin,
            balance=town.treasury,
            note=f"upkeep of {work.name}",
        )
    )
    return True


async def pay_goods(ctx: TickContext, profile: StructureProfileRow, resolved: Resolved) -> bool:
    if profile.upkeep_goods <= 0:
        return True
    if profile.host_entity_id is None:
        return False
    taken = await goods_of(ctx.session, ctx.epoch).take_units(profile.host_entity_id, resolved.upkeep_commodity, profile.upkeep_goods, GoodsFlow.CONSTRUCTION)
    return taken >= profile.upkeep_goods


async def wear(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, *, paid: bool) -> None:
    if "condition" in profile.locked:
        return
    table = ctx.rules.upkeep
    props = await material_props(ctx.session, work)
    weather = await weathering(ctx, work, profile)
    decay = round_half_up(decay_loss(ctx.rules, props, 0) * table.wear_decay_pct / PERCENT * weather) if props is not None else 0
    ceiling = stat_or(work, "durability", PERCENT)
    rows = await ensure_sections(ctx.session, work, profile)
    if paid and await can_repair(ctx, work, profile):
        await mend_sections(ctx.session, ctx.rules, work.id, table.repair_step - decay, rebuild=False)
        await mend_sections(ctx.session, ctx.rules, work.id, ctx.rules.integrity.rebuild_step, rebuild=True)
    else:
        for row in rows:
            if not set(row.locked or []) & {"condition", "state"}:
                row.condition = clamp_int(row.condition - table.unpaid_condition_loss - decay, 0, PERCENT)
                row.state = state_for(ctx.rules, row.condition)
    profile.condition = clamp_int(min(ceiling, overall(rows)), 0, PERCENT)


async def fall_to_ruin(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, cause: RuinCause) -> None:
    profile.construction_state = ConstructionState.RUINED
    profile.effect_pct = 0
    await add_flag(ctx.session, work.id, EntityFlag.RUIN, ctx.epoch)
    await unlink(ctx.session, work.id)
    await record(
        ctx,
        "structures.ruined",
        roles={IncidentRole.SUBJECT: work.id, IncidentRole.OWNER: profile.host_entity_id},
        facts={"cause": cause, "condition": profile.condition, "unpaid_epochs": profile.unpaid_epochs},
        place=work.location_id,
    )
    ctx.count("structures_ruined")


async def keep(ctx: TickContext, work: EntityRow, profile: StructureProfileRow) -> None:
    if "host_entity_id" not in profile.locked:
        host = await host_for(ctx.session, work)
        profile.host_entity_id = host.id if host is not None else None
    if profile.construction_state not in STANDING_STATES:
        await refresh(ctx.session, ctx.rules, work, profile)
        return
    resolved = await refresh(ctx.session, ctx.rules, work, profile)
    paid = await pay_coin(ctx, profile, work) and await pay_goods(ctx, profile, resolved)
    profile.unpaid_epochs = 0 if paid else profile.unpaid_epochs + 1
    await wear(ctx, work, profile, paid=paid)
    before = profile.construction_state
    if "construction_state" not in profile.locked:
        profile.construction_state = standing_state(ctx.rules, profile)
        if profile.host_entity_id is None and profile.unpaid_epochs >= ctx.rules.upkeep.ruin_neglect_epochs:
            profile.construction_state = ConstructionState.RUINED
    if profile.construction_state is ConstructionState.RUINED:
        await fall_to_ruin(ctx, work, profile, RuinCause.UNKEPT if profile.condition > 0 else RuinCause.CRUMBLED)
        return
    if before is ConstructionState.COMPLETE and profile.construction_state is ConstructionState.DAMAGED:
        await record(
            ctx,
            "structures.neglected",
            roles={IncidentRole.SUBJECT: work.id, IncidentRole.OWNER: profile.host_entity_id},
            facts={"condition": profile.condition, "unpaid_epochs": profile.unpaid_epochs},
            place=work.location_id,
        )
    await refresh(ctx.session, ctx.rules, work, profile)
    profile.updated_epoch = ctx.epoch


async def upkeep_all(ctx: TickContext) -> int:
    rows = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, StructureProfileRow.construction_state.not_in(list(GONE_STATES)))
        .order_by(EntityRow.id)
    )
    kept = 0
    for work, profile in rows.all():
        if held(work.id):
            continue
        await keep(ctx, work, profile)
        kept += 1
    return kept
