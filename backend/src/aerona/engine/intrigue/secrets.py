from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.intrigue import SECRETS
from aerona.constants.units import PERCENT
from aerona.db.tables.intrigue import HookRow, SecretRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import HookSource, HookStrength, IntrigueSecret
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

KNOWN = "known_by"


async def secrets_of(session: AsyncSession, holder_id: int) -> list[SecretRow]:
    return list(await session.scalars(select(SecretRow).where(SecretRow.holder_node_id == holder_id).order_by(SecretRow.id)))


async def keep_secret(
    ctx: TickContext,
    holder_id: int,
    kind: IntrigueSecret,
    *,
    about_id: int | None = None,
    severity: int | None = None,
    known_by: tuple[int, ...] = (),
    source: str | None = None,
) -> SecretRow | None:
    if held(holder_id):
        return None
    for row in await secrets_of(ctx.session, holder_id):
        if row.kind is kind and row.about_node_id == about_id and row.exposed_epoch is None:
            if KNOWN not in (row.locked or []):
                row.known_by = sorted({*row.known_by, *known_by})
            return row
    row = SecretRow(
        holder_node_id=holder_id,
        kind=kind,
        about_node_id=about_id,
        severity=severity if severity is not None else SECRETS[kind].severity,
        known_by=sorted({holder_id, *known_by}),
        source=source,
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def grant_hook(ctx: TickContext, holder_id: int, target_id: int, source: HookSource, *, strong: bool, secret_id: int | None = None) -> HookRow | None:
    if holder_id == target_id or held(holder_id):
        return None
    found = await ctx.session.scalar(
        select(HookRow).where(HookRow.holder_node_id == holder_id, HookRow.target_node_id == target_id, HookRow.used_epoch.is_(None)).limit(1)
    )
    strength = HookStrength.STRONG if strong else HookStrength.WEAK
    if found is not None:
        if strong and not found.locked:
            found.strength = strength
        return found
    row = HookRow(holder_node_id=holder_id, target_node_id=target_id, strength=strength, source=source, secret_id=secret_id, created_epoch=ctx.epoch)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def learn(ctx: TickContext, secret: SecretRow, learner_id: int) -> bool:
    if learner_id in secret.known_by or KNOWN in (secret.locked or []) or held(learner_id):
        return False
    secret.known_by = sorted({*secret.known_by, learner_id})
    if learner_id != secret.holder_node_id:
        await grant_hook(ctx, learner_id, secret.holder_node_id, HookSource.SECRET, strong=secret.severity >= ctx.rules.intrigue.strong_at, secret_id=secret.id)
    return True


async def expose(ctx: TickContext, secret: SecretRow, *, by_id: int | None = None) -> bool:
    if secret.exposed_epoch is not None or "exposed_epoch" in (secret.locked or []) or held(secret.holder_node_id):
        return False
    secret.exposed_epoch = ctx.epoch
    spec = SECRETS[secret.kind]
    await add_infamy(
        ctx.session, secret.holder_node_id, round_half_up(secret.severity * ctx.rules.intrigue.expose_infamy_pct / PERCENT), ctx.epoch, rules=ctx.rules
    )
    if spec.act is not None:
        await judged(ctx, secret.holder_node_id, secret.about_node_id or secret.holder_node_id, spec.act, note=spec.label.lower())
    if by_id is not None and by_id != secret.holder_node_id:
        await remember(
            ctx.session, ctx.rules, holder_id=secret.holder_node_id, subject_id=by_id, kind=MemoryKind.BETRAYED_ME, magnitude=-secret.severity, epoch=ctx.epoch
        )
    for hook in await ctx.session.scalars(select(HookRow).where(HookRow.secret_id == secret.id)):
        if not hook.locked:
            await ctx.session.delete(hook)
    holder = await living_entity(ctx.session, secret.holder_node_id)
    if holder is not None:
        await record(
            ctx,
            f"intrigue.exposed_{secret.kind.value}",
            roles={IncidentRole.SUBJECT: holder.id, IncidentRole.ACTOR: by_id, IncidentRole.TARGET: secret.about_node_id},
            facts={"severity": secret.severity},
            place=holder.location_id,
        )
    return True
