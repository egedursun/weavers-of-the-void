from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.arts import ArtMovementRow, ArtPriceRow, CollectorRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.museums import MuseumCollectionRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import ArtMarketRole
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import town_of

CURATORS_FIXUP = "art_market.w52"
SWING_LIMIT = 100
MIDDLING = 50
NOISE = 20


async def backfill_curators(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, CURATORS_FIXUP):
        return 0
    keepers = set(await ctx.session.scalars(select(MuseumCollectionRow.keeper_entity_id)))
    turned = 0
    for row in await ctx.session.scalars(
        select(CollectorRow).where(CollectorRow.holder_entity_id.in_(sorted(keepers))).order_by(CollectorRow.holder_entity_id)
    ):
        if held(row.holder_entity_id) or "role" in row.locked or row.role is ArtMarketRole.CURATOR:
            continue
        row.role = ArtMarketRole.CURATOR
        turned += 1
    ctx.session.add(AppliedFixupRow(key=CURATORS_FIXUP, result={"curators": turned}))
    await ctx.session.flush()
    return turned


async def appoint_curators(ctx: TickContext) -> int:
    known = set(await ctx.session.scalars(select(CollectorRow.holder_entity_id)))
    appointed = 0
    for keeper in sorted(set(await ctx.session.scalars(select(MuseumCollectionRow.keeper_entity_id))) - known):
        if held(keeper) or await living_entity(ctx.session, keeper) is None:
            continue
        ctx.session.add(CollectorRow(holder_entity_id=keeper, role=ArtMarketRole.CURATOR, connoisseurship=MIDDLING, since_epoch=ctx.epoch, locked=[]))
        appointed += 1
    return appointed


async def show_collections(ctx: TickContext) -> int:
    table = ctx.rules.art_market
    curators = set(await ctx.session.scalars(select(CollectorRow.holder_entity_id).where(CollectorRow.role == ArtMarketRole.CURATOR)))
    raised = 0
    for hoard in await ctx.session.scalars(
        select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id.in_(sorted(curators))).order_by(MuseumCollectionRow.id)
    ):
        site = await living_entity(ctx.session, hoard.structure_entity_id or hoard.keeper_entity_id)
        town = await town_of(ctx.session, site) if site is not None else None
        works = await ctx.session.get(SettlementProfileRow, town.id) if town is not None else None
        if works is None or held(works.settlement_entity_id) or "prestige" in works.locked:
            continue
        works.prestige = clamp_int(works.prestige + table.curator_prestige, 0, PERCENT)
        raised += 1
    return raised


async def appoint_critics(ctx: TickContext) -> int:
    table = ctx.rules.art_market
    known = select(CollectorRow.holder_entity_id)
    worlds = set(await ctx.session.scalars(select(EntityRow.world_id).join(CollectorRow, CollectorRow.holder_entity_id == EntityRow.id)))
    found = await ctx.session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id.not_in(known),
            MortalProfileRow.renown >= table.critic_renown,
        )
        .order_by(EntityRow.id)
    )
    appointed = 0
    for mortal, profile in list(found):
        if mortal.world_id not in worlds or held(mortal.id) or not ctx.rng(f"critic.{mortal.id}.{ctx.epoch}").chance(table.critic_chance):
            continue
        taste = await ctx.session.scalar(
            select(ArtworkProfileRow.art_form_entity_id)
            .where(ArtworkProfileRow.art_form_entity_id.is_not(None))
            .order_by(ArtworkProfileRow.quality.desc(), ArtworkProfileRow.artwork_entity_id)
            .limit(1)
        )
        ctx.session.add(
            CollectorRow(
                holder_entity_id=mortal.id,
                role=ArtMarketRole.CRITIC,
                taste_form_entity_id=taste,
                connoisseurship=clamp_int(profile.renown, 0, PERCENT),
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        appointed += 1
    return appointed


async def review(ctx: TickContext, critic: CollectorRow, profile: ArtworkProfileRow, price: ArtPriceRow) -> int:
    table = ctx.rules.art_market
    rng = ctx.rng(f"review.{critic.holder_entity_id}.{profile.artwork_entity_id}.{ctx.epoch}")
    praised = profile.quality + rng.integer(-NOISE, NOISE) >= MIDDLING
    swing = round_half_up(table.critic_price_swing_pct * critic.connoisseurship / PERCENT) * (1 if praised else -1)
    if "acclaim" not in price.locked:
        price.acclaim = clamp_int((price.acclaim or 0) + swing, -SWING_LIMIT, SWING_LIMIT)
    movement = await ctx.session.scalar(
        select(ArtMovementRow).where(ArtMovementRow.art_form_entity_id == profile.art_form_entity_id).order_by(ArtMovementRow.faction_entity_id).limit(1)
    )
    if movement is not None and not held(movement.faction_entity_id):
        if praised and "patrons" not in movement.locked:
            movement.patrons += table.movement_swing
        elif not praised and "scandals" not in movement.locked:
            movement.scandals += table.movement_swing
    await record(
        ctx,
        "art.reviewed",
        roles={IncidentRole.ACTOR: critic.holder_entity_id, IncidentRole.SUBJECT: profile.artwork_entity_id},
        facts={"acclaim": swing, "praised": int(praised)},
        steps=(StepDraft(StepAction.JUDGE, actor=critic.holder_entity_id, target=profile.artwork_entity_id, amount=swing, unit=FactUnit.PERCENT),),
    )
    return swing


async def critic_of(ctx: TickContext, mortal: EntityRow) -> CollectorRow | None:
    row = await ctx.session.get(CollectorRow, mortal.id)
    if row is not None:
        return row if row.role is ArtMarketRole.CRITIC else None
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None or profile.renown < ctx.rules.art_market.critic_renown:
        return None
    row = CollectorRow(
        holder_entity_id=mortal.id, role=ArtMarketRole.CRITIC, connoisseurship=clamp_int(profile.renown, 0, PERCENT), since_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def keep_reviews(ctx: TickContext) -> int:
    reviewed = 0
    critics = list(await ctx.session.scalars(select(CollectorRow).where(CollectorRow.role == ArtMarketRole.CRITIC).order_by(CollectorRow.holder_entity_id)))
    for critic in critics:
        if held(critic.holder_entity_id) or await living_entity(ctx.session, critic.holder_entity_id) is None:
            continue
        works = list(
            await ctx.session.execute(
                select(ArtworkProfileRow, ArtPriceRow)
                .join(ArtPriceRow, ArtPriceRow.artwork_entity_id == ArtworkProfileRow.artwork_entity_id)
                .where(ArtworkProfileRow.art_form_entity_id == critic.taste_form_entity_id)
                .order_by(ArtworkProfileRow.artwork_entity_id)
            )
        )
        for profile, price in ctx.rng(f"reviews.{critic.holder_entity_id}.{ctx.epoch}").shuffled(works)[: ctx.rules.art_market.reviews_per_critic]:
            if held(profile.artwork_entity_id):
                continue
            await review(ctx, critic, profile, price)
            reviewed += 1
    return reviewed
