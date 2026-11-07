import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.intrigue import BeliefRow, FavourRow, HookRow, IdentityRow, SchemeRow, SecretRow, TrueNameRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, HookDemand, HookStrength, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.services.player import intrigue
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def pair(session: AsyncSession, world: PlayerWorld) -> tuple[int, int]:
    town = await make_entity(session, "Corrow", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    first = await make_entity(session, "Wren", EntityType.MORTAL, world_id=world.world.id, location_id=town.id)
    second = await make_entity(session, "Yarrow", EntityType.MORTAL, world_id=world.world.id, location_id=town.id)
    return first.id, second.id


async def test_the_god_keeps_edits_exposes_and_strikes_secrets(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await pair(session, world)
    effect = await intrigue.keep(scope, intrigue.KeepSecret(holder_id=first, kind=IntrigueSecret.HERESY, known_by=[second]))
    row = await session.get(SecretRow, effect.values["secret_id"])
    assert row is not None and set(row.known_by) == {first, second}
    await intrigue.edit_secret(scope, intrigue.EditSecret(secret_id=row.id, severity=90))
    assert row.severity == 90 and "severity" in row.locked
    await intrigue.hold_secret(scope, intrigue.EditSecret(secret_id=row.id, hold=False))
    await intrigue.reveal(scope, intrigue.SecretTarget(secret_id=row.id))
    assert row.exposed_epoch is not None
    with pytest.raises(ValidationFailedError):
        await intrigue.reveal(scope, intrigue.SecretTarget(secret_id=row.id))
    await intrigue.delete_secret(scope, intrigue.SecretTarget(secret_id=row.id))
    with pytest.raises(NotFoundError):
        await intrigue.delete_secret(scope, intrigue.SecretTarget(secret_id=row.id))


async def test_the_god_grants_presses_and_breaks_hooks_and_favours(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await pair(session, world)
    effect = await intrigue.grant(scope, intrigue.GrantHook(holder_id=first, target_id=second, strength=HookStrength.STRONG))
    hook = await session.get(HookRow, effect.values["hook_id"])
    assert hook is not None and hook.strength is HookStrength.STRONG
    await intrigue.edit_hook(scope, intrigue.EditHook(hook_id=hook.id, strength=HookStrength.WEAK, hold=False))
    await intrigue.press(scope, intrigue.UseHook(hook_id=hook.id, demand=HookDemand.SUPPORT))
    assert hook.used_epoch is not None and hook.last_demand is HookDemand.SUPPORT
    await intrigue.edit_hook(scope, intrigue.EditHook(hook_id=hook.id, last_demand=HookDemand.VOTE, hold=False))
    assert hook.last_demand is HookDemand.VOTE
    await intrigue.edit_hook(scope, intrigue.EditHook(hook_id=hook.id, clear_demand=True, hold=False))
    assert hook.last_demand is None
    await intrigue.delete_hook(scope, intrigue.HookTarget(hook_id=hook.id))
    owed = await intrigue.indebt(scope, intrigue.OweFavour(owed_by_id=second, owed_to_id=first, magnitude=30, origin=FavourOrigin.RESCUE))
    favour = await session.get(FavourRow, owed.values["favour_id"])
    assert favour is not None and favour.magnitude == 30
    await intrigue.edit_favour(scope, intrigue.EditFavour(favour_id=favour.id, magnitude=60))
    await intrigue.call(scope, intrigue.CallFavour(favour_id=favour.id, honour=False))
    assert favour.honoured is False
    await intrigue.delete_favour(scope, intrigue.FavourTarget(favour_id=favour.id))
    assert await session.get(FavourRow, favour.id) is None


async def test_the_god_masks_unmasks_and_schemes(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await pair(session, world)
    await intrigue.mask(scope, intrigue.AssumeIdentity(mortal_id=first, false_name="Ashby", reason=IdentityReason.SPY))
    row = await session.get(IdentityRow, first)
    assert row is not None and row.false_name == "Ashby"
    await intrigue.edit_identity(scope, intrigue.EditIdentity(mortal_id=first, exposure=40))
    assert row.exposure == 40 and "exposure" in row.locked
    await intrigue.unmask_identity(scope, intrigue.IdentityTarget(mortal_id=first))
    assert row.exposed_epoch is not None
    await intrigue.delete_identity(scope, intrigue.IdentityTarget(mortal_id=first))
    with pytest.raises(ValidationFailedError):
        await intrigue.mask(scope, intrigue.AssumeIdentity(mortal_id=world.world.id, false_name="No"))
    begun = await intrigue.plot(scope, intrigue.BeginScheme(owner_id=first, kind=PlotKind.SWAY, target_id=second))
    scheme = await session.get(SchemeRow, begun.values["scheme_id"])
    assert scheme is not None and scheme.phase is SchemePhase.RECRUIT
    await intrigue.edit_scheme(scope, intrigue.EditScheme(scheme_id=scheme.id, phase=SchemePhase.PREPARE, power=30, agents=[second]))
    assert scheme.power == 30 and scheme.agents == [second]
    await intrigue.edit_scheme(scope, intrigue.EditScheme(scheme_id=scheme.id, discovered_by=[second]))
    assert scheme.discovered_by == [second] and "discovered_by" in scheme.locked
    await intrigue.hold_scheme(scope, intrigue.EditScheme(scheme_id=scheme.id))
    assert "phase" in scheme.locked
    await intrigue.delete_scheme(scope, intrigue.SchemeTarget(scheme_id=scheme.id))
    with pytest.raises(ValidationFailedError):
        await intrigue.plot(scope, intrigue.BeginScheme(owner_id=first, kind=PlotKind.MURDER))


async def test_the_god_names_reveals_and_shapes_beliefs(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await pair(session, world)
    await intrigue.name_truly(scope, intrigue.SetTrueName(bearer_id=first, name="Ulvren"))
    row = await session.get(TrueNameRow, first)
    assert row is not None and row.name == "Ulvren"
    await intrigue.teach(scope, intrigue.TeachTrueName(bearer_id=first, learner_id=second))
    assert second in row.known_by
    assert await session.scalar(select(HookRow).where(HookRow.holder_node_id == second, HookRow.target_node_id == first)) is not None
    await intrigue.teach(scope, intrigue.TeachTrueName(bearer_id=first, learner_id=second, forget=True))
    assert second not in row.known_by
    await intrigue.name_truly(scope, intrigue.SetTrueName(bearer_id=first, name="Ulvrenn"))
    assert row.name == "Ulvrenn"
    await intrigue.delete_true_name(scope, intrigue.TrueNameTarget(bearer_id=first))
    assert await session.get(TrueNameRow, first) is None
    await intrigue.set_belief(
        scope, intrigue.SetBelief(holder_id=first, subject_id=second, attribute="wealth", value=12, confidence=70, source=BeliefSource.SPY)
    )
    belief = await session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == first))
    assert belief is not None and belief.value == 12 and "value" in belief.locked
    await intrigue.delete_belief(scope, intrigue.BeliefTarget(belief_id=belief.id))
    assert await session.get(BeliefRow, belief.id) is None
