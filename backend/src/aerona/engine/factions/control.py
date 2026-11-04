from collections.abc import Mapping, Sequence

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionGoalKind, FactionKind, FactionRank, FactionScale
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.factions.book import FactionBook, new_profile
from aerona.engine.factions.outlaws import contract, end_contract
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.queries import living_entity

NUMBERS = ("treasury", "cohesion", "secrecy", "reputation", "loyalty", "pay", "unpaid_epochs")
CAPPED = ("cohesion", "secrecy", "reputation", "loyalty")


def lock(locked: list[str], key: str) -> list[str]:
    return locked if key in locked else [*locked, key]


async def profile_of(ctx: TickContext, faction_id: int) -> FactionProfileRow:
    faction = await living_entity(ctx.session, faction_id)
    if faction is None or faction.entity_type is not EntityType.FACTION:
        raise NotFoundError("No such living faction.")
    profile = await ctx.session.get(FactionProfileRow, faction_id)
    return profile if profile is not None else new_profile(ctx, faction, FactionKind.SECRET_SOCIETY)


async def edit_faction(ctx: TickContext, faction_id: int, values: Mapping[str, object], *, release: Sequence[str]) -> FactionProfileRow:
    profile = await profile_of(ctx, faction_id)
    for key, value in values.items():
        if key in NUMBERS:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0 or (key in CAPPED and value > PERCENT):
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is out of range.")
            setattr(profile, key, value)
        elif key == "kind":
            profile.kind = FactionKind(str(value))
        elif key == "scale":
            profile.scale = FactionScale(str(value))
        elif key in {"armed", "outlawed"}:
            setattr(profile, key, bool(value))
        elif key in {"home", "leader", "chartered_by", "employer"}:
            setattr(profile, f"{key}_entity_id", int(value) if isinstance(value, int) else None)
        elif key == "monopoly":
            profile.monopoly = str(value) if value else None
        elif key == "influence_over" and isinstance(value, dict):
            profile.influence_over = {str(node): max(0, min(PERCENT, int(amount))) for node, amount in value.items()}
        elif key == "cohort_share" and isinstance(value, dict):
            profile.cohort_share = {str(social): max(0.0, min(float(PERCENT), float(share))) for social, share in value.items()}
        else:
            raise ValidationFailedError(f"Unknown faction field: {key}.")
        profile.locked = lock(profile.locked, key)
    profile.locked = [key for key in profile.locked if key not in set(release)]
    await ctx.session.flush()
    return profile


def checked_key(kind: FactionGoalKind, key: str | None) -> str | None:
    if key is None:
        return None
    if kind in {FactionGoalKind.ENACT_LAW, FactionGoalKind.ABOLISH_LAW}:
        LawKind(key)
    return key[:120]


async def set_goal(
    ctx: TickContext,
    faction_id: int,
    kind: FactionGoalKind,
    *,
    goal_id: int | None,
    target_id: int | None,
    target_key: str | None,
    priority: int,
    progress: int | None,
    remove: bool,
) -> FactionGoalRow | None:
    await profile_of(ctx, faction_id)
    goal = await ctx.session.get(FactionGoalRow, goal_id) if goal_id is not None else None
    if goal_id is not None and (goal is None or goal.faction_entity_id != faction_id):
        raise NotFoundError("No such goal.")
    if remove:
        if goal is None:
            raise NotFoundError("No such goal.")
        await ctx.session.delete(goal)
        await ctx.session.flush()
        return None
    try:
        key = checked_key(kind, target_key)
    except ValueError as error:
        raise ValidationFailedError("No such law kind.") from error
    if goal is None:
        goal = FactionGoalRow(faction_entity_id=faction_id, kind=kind, since_epoch=ctx.epoch, progress=0, set_by_player=True, locked=[])
        ctx.session.add(goal)
    goal.kind, goal.target_node_id, goal.target_key, goal.priority = kind, target_id, key, priority
    if progress is not None:
        goal.progress = progress
    goal.set_by_player = True
    goal.locked = sorted({*goal.locked, "priority"})
    await ctx.session.flush()
    return goal


async def set_member(ctx: TickContext, faction_id: int, mortal_id: int, *, rank: FactionRank | None, remove: bool) -> FactionMembershipRow | None:
    await profile_of(ctx, faction_id)
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such mortal.")
    row = await ctx.session.get(FactionMembershipRow, (faction_id, mortal_id))
    if remove:
        if row is None:
            raise NotFoundError("That mortal is not a member.")
        await ctx.session.delete(row)
        await ctx.session.flush()
        return None
    if row is None:
        row = FactionMembershipRow(faction_entity_id=faction_id, mortal_entity_id=mortal_id, rank=rank or FactionRank.MEMBER, joined_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if rank is not None:
        row.rank = rank
        row.locked = lock(row.locked, "rank")
        if rank is FactionRank.LEADER:
            profile = await profile_of(ctx, faction_id)
            profile.leader_entity_id = mortal_id
            profile.locked = lock(profile.locked, "leader")
    await ctx.session.flush()
    return row


async def fund(ctx: TickContext, faction_id: int, amount: int) -> FactionProfileRow:
    profile = await profile_of(ctx, faction_id)
    profile.treasury = max(0, profile.treasury + amount)
    await ctx.session.flush()
    return profile


async def outlaw(ctx: TickContext, faction_id: int, *, outlawed: bool) -> FactionProfileRow:
    profile = await profile_of(ctx, faction_id)
    profile.outlawed = outlawed
    profile.locked = lock(profile.locked, "outlawed")
    if outlawed:
        profile.chartered_by_entity_id = None
    await ctx.session.flush()
    return profile


async def charter(ctx: TickContext, faction_id: int, polity_id: int | None, *, monopoly: str | None) -> FactionProfileRow:
    profile = await profile_of(ctx, faction_id)
    if polity_id is not None and polity_id not in (await RealmBook.load(ctx.session)).realms:
        raise NotFoundError("No such realm to grant the charter.")
    profile.chartered_by_entity_id = polity_id
    profile.outlawed = False if polity_id is not None else profile.outlawed
    if monopoly is not None:
        profile.monopoly = monopoly or None
        profile.locked = lock(profile.locked, "monopoly")
    profile.locked = lock(profile.locked, "chartered_by")
    await ctx.session.flush()
    return profile


async def hire_company(ctx: TickContext, faction_id: int, polity_id: int | None, *, pay: int, epochs: int) -> FactionProfileRow:
    profile = await profile_of(ctx, faction_id)
    if profile.kind is not FactionKind.MERCENARY_COMPANY:
        raise ValidationFailedError("Only a free company takes a condotta.")
    if polity_id is None:
        await end_contract(ctx, profile)
        await ctx.session.flush()
        return profile
    realm = (await RealmBook.load(ctx.session)).realms.get(polity_id)
    if realm is None:
        raise NotFoundError("No such realm to hire the company.")
    if profile.employer_entity_id is not None:
        await end_contract(ctx, profile)
    await contract(ctx, await FactionBook.load(ctx.session), profile, realm, pay=pay, epochs=epochs)
    await ctx.session.flush()
    return profile


async def faction_members(ctx: TickContext, faction_id: int) -> list[FactionMembershipRow]:
    return list(await ctx.session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.faction_entity_id == faction_id)))
