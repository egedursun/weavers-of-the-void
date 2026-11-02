from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import max_essence
from aerona.constants.units import PERCENT
from aerona.db.tables.agency import CreationRewardRow
from aerona.db.tables.lore import ThreadRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class RewardDraft:
    entity_id: int
    son_id: int
    epoch: int
    xp: int
    renown: int
    essence: int
    cost: int
    land: bool = False
    thread_id: int | None = None
    fade_pct: int = PERCENT
    repeats: int = 0
    partner_son_id: int | None = None
    partner_xp: int = 0
    partner_renown: int = 0
    partner_cost: int = 0


@dataclass(frozen=True)
class RewardChange:
    xp: int
    renown: int
    essence: int
    thread: int
    taken_back_pct: int


def snapshot(row: CreationRewardRow) -> RewardDraft:
    return RewardDraft(
        entity_id=row.entity_id,
        son_id=row.son_id,
        epoch=row.epoch,
        xp=row.xp,
        renown=row.renown,
        essence=row.essence,
        cost=row.cost,
        land=row.land,
        thread_id=row.thread_id,
        fade_pct=row.fade_pct,
        repeats=row.repeats,
        partner_son_id=row.partner_son_id,
        partner_xp=row.partner_xp,
        partner_renown=row.partner_renown,
        partner_cost=row.partner_cost,
    )


def fade_pct(rules: Rules, same_type_this_epoch: int) -> int:
    tools = rules.son_tools
    return max(tools.same_type_fade_floor_pct, PERCENT - tools.same_type_fade_step_pct * same_type_this_epoch)


def creation_value(rules: Rules, base: int, power: int) -> int:
    return base + rules.core_rules.cost_per_power_level * power


def creation_gains(rules: Rules, value: int, power: int, fade: int) -> tuple[int, int]:
    tools = rules.son_tools
    xp = (tools.creation_xp_base + power * tools.creation_xp_per_power + value * tools.creation_xp_value_pct / PERCENT) * fade / PERCENT
    renown = value * tools.creation_renown_value_pct / PERCENT * fade / PERCENT
    return round(xp), round(renown)


def record_reward(session: AsyncSession, draft: RewardDraft) -> CreationRewardRow:
    row = CreationRewardRow(
        entity_id=draft.entity_id,
        son_id=draft.son_id,
        epoch=draft.epoch,
        xp=max(0, draft.xp),
        renown=max(0, draft.renown),
        essence=max(0, draft.essence),
        cost=max(0, draft.cost),
        land=draft.land,
        thread_id=draft.thread_id,
        fade_pct=draft.fade_pct,
        repeats=draft.repeats,
        partner_son_id=draft.partner_son_id,
        partner_xp=max(0, draft.partner_xp),
        partner_renown=max(0, draft.partner_renown),
        partner_cost=max(0, draft.partner_cost),
    )
    session.add(row)
    return row


def _settle(rules: Rules, son: SonRow | None, xp: int, renown: int, essence: int) -> None:
    if son is None:
        return
    son.xp = max(0, son.xp - xp)
    son.fame = max(0, son.fame - renown)
    son.essence = max(0, min(max_essence(rules, son.might), son.essence - essence))


async def _thread(session: AsyncSession, thread_id: int | None, take: bool) -> int:
    thread = await session.get(ThreadRow, thread_id) if thread_id is not None else None
    if thread is None:
        return 0
    if take:
        thread.progress = max(0, thread.progress - 1)
        return 1
    if thread.status is ThreadStatus.OPEN:
        thread.progress += 1
        return -1
    return 0


async def adjust_reward(
    session: AsyncSession, rules: Rules, entity_id: int, percent: int, *, thread: bool | None = None, raise_only: bool = False, reason: str | None = None
) -> RewardChange | None:
    row = await session.get(CreationRewardRow, entity_id)
    if row is None:
        return None
    before = max(0, min(PERCENT, row.taken_back_pct))
    target = max(0, min(PERCENT, percent))
    target = max(before, target) if raise_only else target
    thread_changes = row.thread_id is not None and thread is not None and thread != row.thread_reverted
    if target == before and not thread_changes:
        return None
    share = (target - before) / PERCENT
    xp, renown, essence = round(row.xp * share), round(row.renown * share), round(row.essence * share)
    _settle(rules, await session.get(SonRow, row.son_id), xp, renown, essence)
    if row.partner_son_id is not None:
        _settle(rules, await session.get(SonRow, row.partner_son_id), round(row.partner_xp * share), round(row.partner_renown * share), 0)
    moved = 0
    if thread_changes and thread is not None:
        moved = await _thread(session, row.thread_id, thread)
        row.thread_reverted = thread
    row.taken_back_pct = target
    row.reason = reason
    await session.flush()
    return RewardChange(xp, renown, essence, moved, target)


async def burn_after_undo(session: AsyncSession, rules: Rules, draft: RewardDraft, reason: str) -> RewardChange:
    tools = rules.son_tools
    keep = (PERCENT - tools.reject_take_back_pct) / PERCENT
    son = await session.get(SonRow, draft.son_id)
    if son is not None:
        son.xp += round(draft.xp * keep)
        son.fame += round(draft.renown * keep)
        son.essence = max(0, min(max_essence(rules, son.might), son.essence + round(draft.essence * keep) - draft.cost))
    partner = await session.get(SonRow, draft.partner_son_id) if draft.partner_son_id is not None else None
    if partner is not None:
        partner.xp += round(draft.partner_xp * keep)
        partner.fame += round(draft.partner_renown * keep)
        partner.essence = max(0, partner.essence - draft.partner_cost)
    moved = 0
    if not tools.reject_reverts_thread:
        moved = await _thread(session, draft.thread_id, take=False)
    row = await session.get(CreationRewardRow, draft.entity_id) or record_reward(session, draft)
    row.taken_back_pct = tools.reject_take_back_pct
    row.thread_reverted = bool(tools.reject_reverts_thread) and draft.thread_id is not None
    row.reason = reason
    await session.flush()
    return RewardChange(draft.xp, draft.renown, draft.essence, moved, row.taken_back_pct)
