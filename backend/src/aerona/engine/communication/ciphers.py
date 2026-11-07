from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.communication import CipherRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import best_skill
from aerona.engine.notes import note
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int

STRENGTH = "strength"
BROKEN = "broken_by"


@dataclass
class CipherTally:
    devised: int = 0
    broken: int = 0
    noticed: int = 0


async def best_cryptographer(ctx: TickContext, holder_id: int) -> tuple[int | None, int]:
    best: tuple[int | None, int] = (None, 0)
    mortals = await ctx.session.scalars(
        select(EntityRow.id)
        .where(EntityRow.location_id == holder_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal in mortals:
        skill = await best_skill(ctx.session, mortal, [SkillKind.CRYPTOGRAPHY])
        if skill > best[1]:
            best = (mortal, skill)
    return best


async def devise(ctx: TickContext, owner: EntityRow, tally: CipherTally) -> None:
    table = ctx.rules.communication
    row = await ctx.session.get(CipherRow, owner.id)
    _, skill = await best_cryptographer(ctx, owner.id)
    strength = clamp_int(table.cipher_base + skill * table.cipher_skill_pct / PERCENT, 0, PERCENT)
    if row is None:
        ctx.session.add(CipherRow(owner_node_id=owner.id, strength=strength, broken_by=[], attempts={}, since_epoch=ctx.epoch, locked=[]))
        tally.devised += 1
    elif STRENGTH not in (row.locked or []):
        row.strength = max(row.strength, strength)


async def intercepted_count(ctx: TickContext, breaker_id: int, owner_id: int) -> int:
    found = await ctx.session.scalar(
        select(func.count(MessageRow.id)).where(
            MessageRow.intent == MessageIntent.DISPATCH,
            MessageRow.sender_node_id == owner_id,
            MessageRow.intercepted_by_node_id == breaker_id,
            MessageRow.enciphered.is_(True),
        )
    )
    return int(found or 0)


async def attack(ctx: TickContext, cipher: CipherRow, tally: CipherTally) -> None:
    table = ctx.rules.communication
    breakers = await ctx.session.scalars(
        select(MessageRow.intercepted_by_node_id)
        .where(MessageRow.sender_node_id == cipher.owner_node_id, MessageRow.intercepted_by_node_id.is_not(None), MessageRow.enciphered.is_(True))
        .distinct()
    )
    for breaker_id in list(breakers):
        if breaker_id is None or breaker_id in cipher.broken_by or held(breaker_id) or BROKEN in (cipher.locked or []):
            continue
        _, skill = await best_cryptographer(ctx, breaker_id)
        volume = await intercepted_count(ctx, breaker_id, cipher.owner_node_id)
        chance = table.codebreak_pct * volume * (skill + 1) / (cipher.strength + 1)
        attempts = {**cipher.attempts, str(breaker_id): cipher.attempts.get(str(breaker_id), 0) + 1}
        cipher.attempts = attempts
        if not ctx.rng(seed_of("cipher.break", cipher.owner_node_id, breaker_id, ctx.epoch)).chance(chance):
            continue
        cipher.broken_by = sorted({*cipher.broken_by, breaker_id})
        await keep_secret(ctx, breaker_id, IntrigueSecret.BROKEN_CIPHER, about_id=cipher.owner_node_id, source="cipher")
        tally.broken += 1


async def notice_break(ctx: TickContext, cipher: CipherRow, tally: CipherTally) -> None:
    if not cipher.broken_by or cipher.break_known or held(cipher.owner_node_id):
        return
    if not ctx.rng(seed_of("cipher.noticed", cipher.owner_node_id, ctx.epoch)).chance(ctx.rules.communication.break_noticed_pct):
        return
    cipher.break_known = True
    owner = await ctx.session.get(EntityRow, cipher.owner_node_id)
    tally.noticed += 1
    if owner is not None:
        await note(
            ctx,
            f"{owner.name} learned that its cipher had been broken and set about a new one.",
            key="communication.cipher_broken",
            ids=[owner.id],
            kind=ChronicleKind.WORLD,
        )
    if STRENGTH not in (cipher.locked or []):
        cipher.broken_by, cipher.break_known, cipher.since_epoch = [], False, ctx.epoch


async def tend_ciphers(ctx: TickContext, owners: list[EntityRow], tally: CipherTally) -> None:
    for owner in owners:
        if not held(owner.id) and await has_technique(ctx.session, owner.id, Technique.CRYPTOGRAPHY):
            await devise(ctx, owner, tally)
    for cipher in list(await ctx.session.scalars(select(CipherRow).order_by(CipherRow.owner_node_id))):
        await attack(ctx, cipher, tally)
        await notice_break(ctx, cipher, tally)
