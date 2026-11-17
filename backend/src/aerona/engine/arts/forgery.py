from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.arts import ArtPriceRow, CollectorRow, ForgeryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import RelicRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import ForgeryKind, ForgeryStatus
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.models.entity_stats import ArtworkStats, ItemStats
from aerona.engine.context import TickContext
from aerona.engine.lore.items import profile_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat_or
from aerona.engine.sacred.places import realm_for, region_of

DOCUMENTS = frozenset({EntityType.TITLE, EntityType.LAW, EntityType.TREATY})
FORGEABLE = frozenset({EntityType.ARTWORK, *DOCUMENTS})
MIDDLING = 50


@dataclass
class ForgeryTally:
    forged: int = 0
    exposed: int = 0


def kind_for(original: EntityRow, relic: RelicRow | None) -> ForgeryKind:
    if original.entity_type is EntityType.ARTWORK:
        return ForgeryKind.ARTWORK
    if original.entity_type in DOCUMENTS:
        return ForgeryKind.DOCUMENT
    return ForgeryKind.RELIC if relic is not None else ForgeryKind.BRAND


async def copy_artwork(ctx: TickContext, original: EntityRow, forger: EntityRow, skill: int) -> EntityRow:
    copy = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ARTWORK,
            name=original.name,
            body=f"A work passed off as {original.name}.",
            stats=ArtworkStats(),
            power=max(1, original.power_level),
            location_id=forger.location_id,
            world_id=forger.world_id,
            subtype=original.subtype,
        ),
    )
    source = await ctx.session.get(ArtworkProfileRow, original.id)
    if source is not None:
        ctx.session.add(
            ArtworkProfileRow(
                artwork_entity_id=copy.id,
                medium=source.medium,
                performed=False,
                author_entity_id=source.author_entity_id,
                patron_entity_id=forger.id,
                subject_node_id=source.subject_node_id,
                message=source.message,
                quality=skill,
                copies=0,
                colour=source.colour,
                shape=source.shape,
                art_form_entity_id=source.art_form_entity_id,
                canon=False,
                updated_epoch=ctx.epoch,
                locked=[],
            )
        )
    return copy


async def forged_item(ctx: TickContext, name: str, body: str, forger: EntityRow, item_class: ItemClass) -> EntityRow:
    item = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=name,
            body=body,
            stats=ItemStats(),
            power=1,
            location_id=forger.location_id,
            world_id=forger.world_id,
            maker_entity_id=forger.id,
        ),
    )
    await profile_of(ctx, item, item_class)
    return item


async def claimed_realm(ctx: TickContext, original: EntityRow, forger: EntityRow) -> int | None:
    owner = await living_entity(ctx.session, original.affiliated_entity_id)
    if owner is not None and owner.entity_type is EntityType.POLITY:
        return owner.id
    return await realm_for(ctx.session, forger)


async def forge(ctx: TickContext, original: EntityRow, forger: EntityRow, *, brand: BrandRow | None = None) -> ForgeryRow:
    skill = clamp_int(stat_or(forger, "creativity", MIDDLING), 0, PERCENT)
    relic = await ctx.session.get(RelicRow, original.id)
    kind = ForgeryKind.BRAND if brand is not None else kind_for(original, relic)
    claim: ClaimRow | None = None
    if kind is ForgeryKind.ARTWORK:
        item = await copy_artwork(ctx, original, forger, skill)
    elif kind is ForgeryKind.RELIC:
        item = await forged_item(ctx, original.name, f"A relic passed off as {original.name}.", forger, ItemClass.HOLY_RELIC)
        if relic is not None:
            ctx.session.add(
                RelicRow(
                    item_entity_id=item.id,
                    saint_entity_id=relic.saint_entity_id,
                    cult_entity_id=relic.cult_entity_id,
                    sanctity=relic.sanctity,
                    canonised_epoch=ctx.epoch,
                    locked=[],
                )
            )
    elif kind is ForgeryKind.DOCUMENT:
        item = await forged_item(ctx, f"Charter of {original.name}", f"A charter that seems to grant {original.name}.", forger, ItemClass.SCROLL)
        realm = await claimed_realm(ctx, original, forger)
        if realm is not None:
            claim = ClaimRow(
                claimant_entity_id=forger.id,
                polity_entity_id=realm,
                title_entity_id=original.id if original.entity_type is EntityType.TITLE else None,
                strength=skill // 2,
                basis=ClaimBasis.FABRICATED,
                since_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(claim)
    else:
        label = brand.name if brand is not None else original.name
        item = await forged_item(ctx, f"Goods marked {label}", f"Goods that bear the mark of {label}.", forger, ItemClass.TOOL)
        if brand is not None and "counterfeits" not in brand.locked:
            brand.counterfeits += 1
    await ctx.session.flush()
    await connect(ctx.session, forger.id, item.id, BondKind.OWNS, ctx.epoch, description="forged")
    row = ForgeryRow(
        item_entity_id=item.id,
        kind=kind,
        forger_entity_id=forger.id,
        original_entity_id=original.id,
        brand_id=brand.id if brand is not None else None,
        claim_id=claim.id if claim is not None else None,
        skill=skill,
        made_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def work_of(ctx: TickContext, holder: EntityRow) -> EntityRow | None:
    authored = await ctx.session.scalar(
        select(EntityRow)
        .join(ArtworkProfileRow, ArtworkProfileRow.artwork_entity_id == EntityRow.id)
        .where(ArtworkProfileRow.author_entity_id == holder.id, EntityRow.status == EntityStatus.CANON)
        .order_by(ArtworkProfileRow.quality.desc(), EntityRow.id)
        .limit(1)
    )
    if authored is not None:
        return authored
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == holder.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(
        select(EntityRow)
        .outerjoin(RelicRow, RelicRow.item_entity_id == EntityRow.id)
        .where(
            EntityRow.id.in_(owned),
            EntityRow.status == EntityStatus.CANON,
            or_(EntityRow.entity_type == EntityType.ARTWORK, RelicRow.item_entity_id.is_not(None)),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )


async def worth_forging(ctx: TickContext, world_id: int | None) -> EntityRow | None:
    floor = ctx.rules.forgery.price_floor
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(ArtPriceRow, ArtPriceRow.artwork_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, ArtPriceRow.price >= floor)
        .order_by(ArtPriceRow.price.desc(), EntityRow.id)
        .limit(1)
    )
    if found is not None:
        return found
    return await ctx.session.scalar(
        select(EntityRow)
        .join(RelicRow, RelicRow.item_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(RelicRow.sanctity.desc(), EntityRow.id)
        .limit(1)
    )


async def renowned_brand(ctx: TickContext, world_id: int | None) -> BrandRow | None:
    return await ctx.session.scalar(
        select(BrandRow)
        .join(EntityRow, EntityRow.id == BrandRow.community_entity_id)
        .where(EntityRow.world_id == world_id, BrandRow.renowned > 0)
        .order_by(BrandRow.reputation.desc(), BrandRow.id)
        .limit(1)
    )


async def forge_works(ctx: TickContext, tally: ForgeryTally) -> None:
    table = ctx.rules.forgery
    makers = await ctx.session.scalars(
        select(EntityRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for maker in list(makers):
        if tally.forged >= table.forgeries_per_epoch:
            return
        if held(maker.id) or stat_or(maker, "creativity", 0) < table.skill_floor or not ctx.rng(f"forge.{maker.id}").chance(table.forge_chance):
            continue
        original = await worth_forging(ctx, maker.world_id)
        brand = None if original is not None else await renowned_brand(ctx, maker.world_id)
        if brand is not None:
            original = await living_entity(ctx.session, brand.community_entity_id)
        if original is None or held(original.id):
            continue
        row = await forge(ctx, original, maker, brand=brand)
        tally.forged += 1
        await note(ctx, f"{maker.name} made a forgery of {original.name} ({spoken(row.kind)}).", key="arts.forged", ids=[maker.id, original.id])


async def expose(ctx: TickContext, row: ForgeryRow, expert_id: int | None) -> None:
    table = ctx.rules.forgery
    row.status = ForgeryStatus.EXPOSED
    row.exposed_by_entity_id = expert_id
    row.exposed_epoch = ctx.epoch
    forger = await ctx.session.get(MortalProfileRow, row.forger_entity_id) if row.forger_entity_id is not None else None
    if forger is not None and not held(forger.entity_id) and "infamy" not in forger.locked:
        forger.infamy = clamp_int(forger.infamy + table.infamy, 0, PERCENT)
    price = await ctx.session.get(ArtPriceRow, row.item_entity_id)
    if price is not None and "price" not in price.locked:
        price.price = 0
    if price is not None and "provenance" not in price.locked:
        price.provenance = 0
    relic = await ctx.session.get(RelicRow, row.item_entity_id)
    if relic is not None and "sanctity" not in relic.locked:
        relic.sanctity = max(0, relic.sanctity - table.sanctity)
    claim = await ctx.session.get(ClaimRow, row.claim_id) if row.claim_id is not None else None
    if claim is not None and claim.ended_epoch is None:
        claim.ended_epoch = ctx.epoch
    brand = await ctx.session.get(BrandRow, row.brand_id) if row.brand_id is not None else None
    if brand is not None and "reputation" not in brand.locked:
        brand.reputation = max(0, brand.reputation - table.infamy)
    item = await ctx.session.get(EntityRow, row.item_entity_id)
    await note(ctx, f"{item.name if item else 'A work'} was shown to be a forgery.", key="arts.exposed", ids=[row.item_entity_id])


async def examine(ctx: TickContext, tally: ForgeryTally) -> None:
    table = ctx.rules.forgery
    for row in list(await ctx.session.scalars(select(ForgeryRow).where(ForgeryRow.status == ForgeryStatus.HIDDEN).order_by(ForgeryRow.id))):
        item = await living_entity(ctx.session, row.item_entity_id)
        if item is None or held(item.id) or "status" in row.locked:
            continue
        region = await region_of(ctx.session, item)
        experts = await ctx.session.execute(
            select(CollectorRow, EntityRow)
            .join(EntityRow, EntityRow.id == CollectorRow.holder_entity_id)
            .where(EntityRow.world_id == item.world_id)
            .order_by(CollectorRow.connoisseurship.desc(), CollectorRow.holder_entity_id)
            .limit(1)
        )
        best = next(iter(experts), None)
        if best is None:
            continue
        collector, expert = best
        edge = max(0, collector.connoisseurship - row.skill)
        local = region is not None and await region_of(ctx.session, expert) == region
        chance = table.expose_chance * (1 + edge / PERCENT) * (2 if local else 1)
        if ctx.rng(f"expose.{row.id}.{ctx.epoch}").chance(chance):
            await expose(ctx, row, expert.id)
            tally.exposed += 1


async def keep_forgeries(ctx: TickContext, tally: ForgeryTally) -> None:
    await forge_works(ctx, tally)
    await examine(ctx, tally)
    await ctx.session.flush()
