from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.intrigue import IdentityRow, SecretRow
from aerona.domain.enums.belonging import FugitiveKind
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand, HookSource, HookStrength, IdentityReason, IntrigueSecret
from aerona.engine.intrigue.favours import owe, use_hook
from aerona.engine.intrigue.identities import assume
from aerona.engine.intrigue.secrets import expose, grant_hook
from aerona.engine.intrigue.sources import backfill_power_secrets, hidden_lives
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, mortal, settlement, tuned_rules


async def test_a_silence_demand_wears_a_strong_hook_and_a_favour_for_shelter_is_weighed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "intrigue", rules=tuned_rules(hooks={"silence_cost": 100}, favours={"hospitality_weight": 50}))
    town = await settlement(session, "Courthold", world, world.regions[0])
    holder = await mortal(session, "Merchant", world, town.id)
    witness = await mortal(session, "Witness", world, town.id)
    hook = await grant_hook(ctx, holder.id, witness.id, HookSource.SECRET, strong=True)
    assert hook is not None
    await use_hook(ctx, hook, HookDemand.SILENCE)
    assert hook.strength is HookStrength.WEAK and hook.last_demand is HookDemand.SILENCE
    favour = await owe(ctx, witness.id, town.id, FavourOrigin.HOSPITALITY, 40)
    assert favour is not None and favour.magnitude == 20


async def test_a_revealed_hidden_power_unmasks_its_holder(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "intrigue")
    town = await settlement(session, "Maskhold", world, world.regions[0])
    gifted = await mortal(session, "Gifted", world, town.id)
    mask = await assume(ctx, gifted, IdentityReason.HIDDEN_POWER, "Nobody", community_id=town.id)
    assert mask is not None
    secret = await session.scalar(select(SecretRow).where(SecretRow.holder_node_id == gifted.id, SecretRow.kind == IntrigueSecret.HIDDEN_POWER))
    assert secret is not None
    assert await expose(ctx, secret)
    assert mask.exposed_epoch == ctx.epoch


async def test_the_fixup_gives_every_hidden_power_its_secret_once(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "intrigue")
    gifted = await mortal(session, "Gifted", world, world.regions[0].id)
    session.add(IdentityRow(mortal_node_id=gifted.id, false_name="Nobody", reason=IdentityReason.HIDDEN_POWER, exposure=0, since_epoch=1, locked=[]))
    await session.flush()
    assert await backfill_power_secrets(ctx) == 1
    assert await backfill_power_secrets(ctx) == 0


async def test_a_fugitive_at_large_may_live_under_a_false_name_and_a_caught_one_does_not(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "intrigue", rules=tuned_rules(intrigue={"exile_mask_pct": 100}))
    runner = await mortal(session, "Runner", world, world.regions[0].id)
    taken = await mortal(session, "Taken", world, world.regions[0].id)
    session.add(FugitiveRow(mortal_entity_id=runner.id, kind=FugitiveKind.RUNAWAY, fled_epoch=1, locked=[]))
    session.add(FugitiveRow(mortal_entity_id=taken.id, kind=FugitiveKind.DESERTER, fled_epoch=1, caught_epoch=2, locked=[]))
    await session.flush()
    hiding = {mortal_id for mortal_id, reason, _cover, _home in await hidden_lives(ctx) if reason is IdentityReason.FUGITIVE}
    assert runner.id in hiding and taken.id not in hiding
