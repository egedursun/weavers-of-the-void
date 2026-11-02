from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.creator import CREATOR_PASSIONS
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.creator import CreatorPassion
from aerona.engine.gods.queries import creator_row
from aerona.engine.gods.reputation import (
    CosmosReputation,
    Reputation,
    ReputationAxes,
    clean_passions,
    cosmos_reputation,
    creator_passions,
    drift_son,
    push_reputation,
    refresh_reputation,
)
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.gods.context import record_action, require, require_creator


@dataclass(frozen=True)
class PassionsView:
    passions: tuple[CreatorPassion, ...]
    automatic: bool


async def read_passions(session: AsyncSession, rules: Rules) -> PassionsView:
    ctx = await manual_context(session, "passions", rules)
    passions, automatic = await creator_passions(session, rules, ctx.epoch)
    return PassionsView(tuple(passions), automatic)


async def set_passions(session: AsyncSession, rules: Rules, passions: list[CreatorPassion], automatic: bool) -> PassionsView:
    ctx = await manual_context(session, "set_passions", rules)
    creator = await require_creator(session)
    if automatic:
        creator.passions = []
        creator.passions_automatic = True
        await session.flush()
        return await read_passions(session, rules)
    cleaned = clean_passions(rules, passions)
    creator.passions = cleaned
    creator.passions_automatic = False
    names = god_lines.PASSION_JOIN.join(CREATOR_PASSIONS[passion].label.lower() for passion in cleaned)
    line = god_lines.PASSIONS_REVEALED
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, line.render(creator=creator.name, passions=names), template_key=line.key)
    await record_action(ctx, ActionKind.SET_PASSIONS, creator.id)
    return PassionsView(tuple(cleaned), False)


async def son_reputation(session: AsyncSession, rules: Rules, son_id: int) -> Reputation:
    ctx = await manual_context(session, "son_reputation", rules)
    son = require(await session.get(SonRow, son_id), "son")
    return await refresh_reputation(session, rules, son, ctx.epoch)


async def nudge_reputation(session: AsyncSession, rules: Rules, son_id: int, delta: ReputationAxes) -> Reputation:
    ctx = await manual_context(session, "push_reputation", rules)
    son = require(await session.get(SonRow, son_id), "son")
    result = await push_reputation(session, rules, son, delta, ctx.epoch)
    await record_action(ctx, ActionKind.PUSH_REPUTATION, son_id)
    return result


async def apply_drift_now(session: AsyncSession, rules: Rules, son_id: int) -> Reputation:
    ctx = await manual_context(session, "reputation_drift", rules)
    son = require(await session.get(SonRow, son_id), "son")
    return await drift_son(ctx, son, await creator_row(session))


async def read_cosmos_reputation(session: AsyncSession, rules: Rules) -> CosmosReputation:
    ctx = await manual_context(session, "cosmos_reputation", rules)
    return await cosmos_reputation(session, rules, ctx.epoch)
