from collections.abc import Mapping

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.society_depth import ClassStandingRow, CommunityNeedRow, CorveeRow, DriftImpositionRow, PolityLoyaltyRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause
from aerona.engine.context import TickContext
from aerona.engine.demography.control import move_cohort
from aerona.engine.demography.events import ennobled, enslaved, freed, ruined
from aerona.engine.demography.wealth import WEALTH_LOCK
from aerona.engine.notes import note
from aerona.engine.primitives.queries import living_entity

STANDING_NUMBERS = {"fed_pct": (0, PERCENT), "needs_met_pct": (0, PERCENT), "luxury_pct": (0, PERCENT * 10), WEALTH_LOCK: (0, 10**9)}
LOYALTY_NUMBERS = {"grievances": (0, 10**4), "benefits": (0, 10**4), "loyalty": (0, PERCENT)}
DRIFT_LIMIT = PERCENT
MOST_EPOCHS = 1000


async def community(ctx: TickContext, community_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, community_id)
    if entity is None or entity.entity_type not in SOCIETY_TYPES or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such people or settlement.")
    return entity


async def mortal(ctx: TickContext, mortal_id: int) -> EntityRow:
    entity = await living_entity(ctx.session, mortal_id)
    if entity is None or entity.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    return entity


def checked(name: str, value: int, limits: tuple[int, int]) -> int:
    low, high = limits
    if not low <= value <= high:
        raise ValidationFailedError(f"{name.replace('_', ' ').capitalize()} runs from {low} to {high}.")
    return value


async def hold_need(ctx: TickContext, community_id: int, social_class: SocialClass, commodity: CommodityKind, held_pct: int | None) -> CommunityNeedRow:
    entity = await community(ctx, community_id)
    row = await ctx.session.get(CommunityNeedRow, (entity.id, social_class, commodity))
    if row is None:
        row = CommunityNeedRow(community_entity_id=entity.id, social_class=social_class, commodity=commodity, wanted=0, got=0, epoch=ctx.epoch)
        ctx.session.add(row)
    row.held_pct = checked("met share", held_pct, (0, PERCENT)) if held_pct is not None else None
    await ctx.session.flush()
    return row


async def edit_standing(ctx: TickContext, community_id: int, social_class: SocialClass, values: Mapping[str, int], *, release: list[str]) -> ClassStandingRow:
    entity = await community(ctx, community_id)
    row = await ctx.session.get(ClassStandingRow, (entity.id, social_class))
    if row is None:
        row = ClassStandingRow(community_entity_id=entity.id, social_class=social_class, wealth=0, income=0, locked=[], epoch=ctx.epoch)
        ctx.session.add(row)
    for key, value in values.items():
        if key not in STANDING_NUMBERS:
            raise ValidationFailedError(f"Unknown field: {key}.")
        setattr(row, key, checked(key, value, STANDING_NUMBERS[key]))
        if key not in row.locked:
            row.locked = [*row.locked, key]
    row.locked = [key for key in row.locked if key not in release]
    await ctx.session.flush()
    return row


async def set_labour(ctx: TickContext, community_id: int, job: Job, workers: int | None) -> LabourRow:
    entity = await community(ctx, community_id)
    row = await ctx.session.get(LabourRow, (entity.id, job))
    if row is None:
        row = LabourRow(community_entity_id=entity.id, job=job, workers=0, output_pct=PERCENT, epoch=ctx.epoch, held=False)
        ctx.session.add(row)
    if workers is None:
        row.held = False
    else:
        row.workers = checked("workers", workers, (0, 10**9))
        row.held = True
    await ctx.session.flush()
    return row


async def set_corvee(ctx: TickContext, community_id: int, share_pct: int, polity_id: int | None, work_id: int | None = None) -> CorveeRow | None:
    entity = await community(ctx, community_id)
    row = await ctx.session.get(CorveeRow, entity.id)
    if share_pct <= 0:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
            await note(ctx, f"The corvee on {entity.name} was lifted; the farmhands went home.", key="labour.corvee_lifted", ids=[entity.id])
        return None
    if row is None:
        row = CorveeRow(community_entity_id=entity.id, since_epoch=ctx.epoch, by_hand=True)
        ctx.session.add(row)
    row.share_pct = checked("corvee share", share_pct, (0, PERCENT))
    row.polity_entity_id = polity_id
    if work_id is not None:
        work = await ctx.session.get(EntityRow, work_id)
        if work is None or work.entity_type is not EntityType.STRUCTURE:
            raise ValidationFailedError("Forced labour can only be set to a structure.")
    row.work_entity_id = work_id
    await ctx.session.flush()
    await note(
        ctx, f"A corvee was laid on {entity.name}: {row.share_pct}% of its farmhands must labour on the great works.", key="labour.corvee", ids=[entity.id]
    )
    return row


async def edit_loyalty(ctx: TickContext, polity_id: int, member_id: int, values: Mapping[str, int], *, release: list[str]) -> PolityLoyaltyRow:
    if await ctx.session.get(PolityMemberRow, (polity_id, member_id)) is None:
        raise NotFoundError("That community is not a member of that realm.")
    row = await ctx.session.get(PolityLoyaltyRow, (polity_id, member_id))
    if row is None:
        row = PolityLoyaltyRow(polity_entity_id=polity_id, member_entity_id=member_id, parts={}, locked=[], loyalty=PERCENT // 2, epoch=ctx.epoch)
        ctx.session.add(row)
    for key, value in values.items():
        if key not in LOYALTY_NUMBERS:
            raise ValidationFailedError(f"Unknown field: {key}.")
        setattr(row, key, checked(key, value, LOYALTY_NUMBERS[key]))
        if key not in row.locked:
            row.locked = [*row.locked, key]
    row.locked = [key for key in row.locked if key not in release]
    await ctx.session.flush()
    return row


async def impose_drift(ctx: TickContext, community_id: int, cause: DriftCause, axis: ValueAxis, *, amount: int, epochs: int) -> DriftImpositionRow:
    entity = await community(ctx, community_id)
    row = DriftImpositionRow(
        community_entity_id=entity.id,
        cause=cause,
        axis=axis,
        amount=checked("amount", amount, (-DRIFT_LIMIT, DRIFT_LIMIT)),
        epochs_left=checked("epochs", epochs, (1, MOST_EPOCHS)),
        created_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_drift(
    ctx: TickContext, imposition_id: int, *, amount: int | None, epochs: int | None, cause: DriftCause | None, axis: ValueAxis | None
) -> DriftImpositionRow:
    row = await ctx.session.get(DriftImpositionRow, imposition_id)
    if row is None:
        raise NotFoundError("No such pressure on that people.")
    if amount is not None:
        row.amount = checked("amount", amount, (-DRIFT_LIMIT, DRIFT_LIMIT))
    if epochs is not None:
        row.epochs_left = checked("epochs", epochs, (1, MOST_EPOCHS))
    if cause is not None:
        row.cause = cause
    if axis is not None:
        row.axis = axis
    await ctx.session.flush()
    return row


async def cancel_drift(ctx: TickContext, imposition_id: int) -> int:
    row = await ctx.session.get(DriftImpositionRow, imposition_id)
    if row is None:
        raise NotFoundError("No such pressure on that people.")
    community_id = row.community_entity_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    return community_id


async def ennoble(ctx: TickContext, mortal_id: int) -> EntityRow | None:
    hero = await mortal(ctx, mortal_id)
    if hero.social_class is SocialClass.NOBLE:
        raise ValidationFailedError(f"{hero.name} is already among the nobles.")
    hero.social_class = SocialClass.NOBLE
    benefactor = await ctx.session.get(EntityRow, hero.location_id) if hero.location_id is not None else None
    return await ennobled(ctx, hero, benefactor if benefactor is not None and benefactor.entity_type in SOCIETY_TYPES else None, by_hand=True)


async def ruin(ctx: TickContext, mortal_id: int, *, bondage: bool) -> EntityRow:
    member = await mortal(ctx, mortal_id)
    target = SocialClass.SERF_OR_SLAVE if bondage else SocialClass.OUTCAST
    if member.social_class is target:
        raise ValidationFailedError(f"{member.name} has already fallen that low.")
    member.social_class = target
    await ruined(ctx, member, None, by_hand=True)
    return member


async def enslave(ctx: TickContext, community_id: int, count: int, source: SocialClass) -> int:
    entity = await community(ctx, community_id)
    if source is SocialClass.SERF_OR_SLAVE:
        raise ValidationFailedError("Choose free people to put in chains.")
    moved = await move_cohort(ctx, entity.id, count=count, source=source, target=SocialClass.SERF_OR_SLAVE, band=None, condition=None)
    await enslaved(ctx, entity, moved, by_hand=True)
    return moved


async def manumit(ctx: TickContext, community_id: int, count: int, target: SocialClass) -> int:
    entity = await community(ctx, community_id)
    if target is SocialClass.SERF_OR_SLAVE:
        raise ValidationFailedError("Choose the class the freed join.")
    moved = await move_cohort(ctx, entity.id, count=count, source=SocialClass.SERF_OR_SLAVE, target=target, band=None, condition=None)
    await freed(ctx, entity, moved, by_hand=True)
    return moved
