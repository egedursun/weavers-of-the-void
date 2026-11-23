from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.catalog.market_kinds import FORGERIES, JUDGES
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import BrandRow
from aerona.db.tables.arts import ArtPriceRow, CollectorRow, ForgeryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import RelicRow
from aerona.db.tables.mind import SKILL_MAX, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import ArtMarketRole, ForgeryKind, ForgeryStatus
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.enums.records import StepAction
from aerona.domain.models.entity_stats import ArtworkStats, ItemStats
from aerona.engine.context import TickContext
from aerona.engine.economy.money import issued_by
from aerona.engine.economy.purse import receive_coin, take_coin
from aerona.engine.lore.items import profile_of
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.quota import WorldQuota
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import realm_for, region_of, town_of

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


async def forge_coin(ctx: TickContext, realm: EntityRow, forger: EntityRow) -> EntityRow:
    currency = await issued_by(ctx, realm.id)
    label = currency.name if currency is not None else realm.name
    item = await forged_item(ctx, f"False coin of {label}", f"Coin that passes for the coin of {label}.", forger, ItemClass.CURRENCY)
    if currency is not None and not currency.held and not held(realm.id):
        currency.trust = clamp_int(currency.trust - ctx.rules.forgery.coin_trust_cut, 0, PERCENT)
    return item


async def forge_lineage(ctx: TickContext, title: EntityRow, forger: EntityRow, skill: int) -> tuple[EntityRow, ClaimRow | None]:
    item = await forged_item(ctx, f"Lineage of {title.name}", f"A lineage that seems to descend to {title.name}.", forger, ItemClass.SCROLL)
    realm = await claimed_realm(ctx, title, forger)
    if realm is None:
        return item, None
    claim = ClaimRow(
        claimant_entity_id=forger.id,
        polity_entity_id=realm,
        title_entity_id=title.id,
        strength=skill // 2,
        basis=ClaimBasis.INHERITANCE,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(claim)
    return item, claim


async def forge_seal(ctx: TickContext, realm: EntityRow, forger: EntityRow) -> EntityRow:
    item = await forged_item(ctx, f"Seal of {realm.name}", f"A seal that passes false orders in the name of {realm.name}.", forger, ItemClass.SEAL)
    take = ctx.rules.forgery.seal_order_take
    if not held(realm.id) and await take_coin(ctx.session, ctx.rules, realm, take):
        await receive_coin(ctx.session, ctx.rules, forger, take)
    return item


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


async def forge(ctx: TickContext, original: EntityRow, forger: EntityRow, *, brand: BrandRow | None = None, kind: ForgeryKind | None = None) -> ForgeryRow:
    skill = clamp_int(stat_or(forger, "creativity", MIDDLING), 0, PERCENT)
    relic = await ctx.session.get(RelicRow, original.id)
    kind = kind if kind is not None else ForgeryKind.BRAND if brand is not None else kind_for(original, relic)
    claim: ClaimRow | None = None
    if kind is ForgeryKind.COIN:
        item = await forge_coin(ctx, original, forger)
    elif kind is ForgeryKind.LINEAGE:
        item, claim = await forge_lineage(ctx, original, forger, skill)
    elif kind is ForgeryKind.SEAL:
        item = await forge_seal(ctx, original, forger)
    elif kind is ForgeryKind.ARTWORK:
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
    await take_up_forging(ctx, forger)
    await ctx.session.flush()
    return row


async def take_up_forging(ctx: TickContext, forger: EntityRow) -> None:
    if held(forger.id) or await ctx.session.get(CollectorRow, forger.id) is not None:
        return
    ctx.session.add(CollectorRow(holder_entity_id=forger.id, role=ArtMarketRole.FORGER, connoisseurship=0, since_epoch=ctx.epoch, locked=[]))


async def other_target(ctx: TickContext, maker: EntityRow) -> tuple[EntityRow, ForgeryKind] | None:
    realm_id = await realm_for(ctx.session, maker)
    realm = await living_entity(ctx.session, realm_id) if realm_id is not None else None
    if realm is None:
        return None
    options: list[tuple[EntityRow, ForgeryKind]] = [(realm, ForgeryKind.SEAL)]
    if await issued_by(ctx, realm.id) is not None:
        options.append((realm, ForgeryKind.COIN))
    title = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.TITLE, EntityRow.status == EntityStatus.CANON, EntityRow.affiliated_entity_id == realm.id)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if title is not None:
        options.append((title, ForgeryKind.LINEAGE))
    return ctx.rng(f"forge.kind.{maker.id}.{ctx.epoch}").pick(options)


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
    quota = WorldQuota(table.forgeries_per_epoch)
    for maker in ctx.rng("forge.order").shuffled(makers):
        if quota.full(maker.world_id):
            continue
        if held(maker.id) or stat_or(maker, "creativity", 0) < table.skill_floor or not ctx.rng(f"forge.{maker.id}").chance(table.forge_chance):
            continue
        original = await worth_forging(ctx, maker.world_id)
        brand = None if original is not None else await renowned_brand(ctx, maker.world_id)
        if brand is not None:
            original = await living_entity(ctx.session, brand.community_entity_id)
        kind: ForgeryKind | None = None
        if original is None or ctx.rng(f"forge.other.{maker.id}.{ctx.epoch}").chance(MIDDLING):
            other = await other_target(ctx, maker)
            if other is not None:
                original, kind, brand = other[0], other[1], None
        if original is None or held(original.id):
            continue
        row = await forge(ctx, original, maker, brand=brand, kind=kind)
        quota.take(maker.world_id)
        tally.forged += 1
        await record(
            ctx,
            "arts.forged",
            roles={IncidentRole.MAKER: maker.id, IncidentRole.TARGET: original.id, IncidentRole.PRODUCT: row.item_entity_id},
            facts={"forgery": row.kind},
            steps=(StepDraft(StepAction.FORGE, actor=maker.id, target=original.id),),
        )


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
    await record(
        ctx,
        "arts.exposed",
        roles={IncidentRole.SUBJECT: row.item_entity_id},
        facts={"forgery": row.kind, "infamy": table.infamy},
        steps=(StepDraft(StepAction.REVEAL, target=row.item_entity_id),),
    )
    culprit = await living_entity(ctx.session, row.forger_entity_id) if row.forger_entity_id is not None else None
    town = await town_of(ctx.session, culprit) if culprit is not None else None
    if culprit is not None and town is not None:
        await report_crime(ctx, town.id, culprit.id, FORGERIES[row.kind].crime)


async def examine(ctx: TickContext, tally: ForgeryTally) -> None:
    table = ctx.rules.forgery
    for row in list(await ctx.session.scalars(select(ForgeryRow).where(ForgeryRow.status == ForgeryStatus.HIDDEN).order_by(ForgeryRow.id))):
        item = await living_entity(ctx.session, row.item_entity_id)
        if item is None or held(item.id) or "status" in row.locked:
            continue
        region = await region_of(ctx.session, item)
        found = await expert_for(ctx, row, item)
        if found is None:
            continue
        expert, discernment = found
        edge = max(0, discernment - row.skill)
        local = region is not None and await region_of(ctx.session, expert) == region
        chance = table.expose_chance * FORGERIES[row.kind].detect(ctx.rules) / PERCENT * (1 + edge / PERCENT) * (2 if local else 1)
        if ctx.rng(f"expose.{row.id}.{ctx.epoch}").chance(chance):
            await expose(ctx, row, expert.id)
            tally.exposed += 1


async def expert_for(ctx: TickContext, row: ForgeryRow, item: EntityRow) -> tuple[EntityRow, int] | None:
    skill = FORGERIES[row.kind].expert
    if skill is not None:
        found = await ctx.session.execute(
            select(EntityRow, SkillRow.level)
            .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
            .where(EntityRow.world_id == item.world_id, EntityRow.status == EntityStatus.CANON, SkillRow.skill == skill)
            .order_by(SkillRow.level.desc(), EntityRow.id)
            .limit(1)
        )
        best = next(iter(found), None)
        if best is not None:
            return best[0], round_half_up(best[1] * PERCENT / SKILL_MAX)
    judges = await ctx.session.execute(
        select(CollectorRow, EntityRow)
        .join(EntityRow, EntityRow.id == CollectorRow.holder_entity_id)
        .where(EntityRow.world_id == item.world_id, CollectorRow.role.in_(list(JUDGES)))
        .order_by(CollectorRow.connoisseurship.desc(), CollectorRow.holder_entity_id)
        .limit(1)
    )
    judge = next(iter(judges), None)
    return (judge[1], judge[0].connoisseurship) if judge is not None else None


async def unmask_forgers(ctx: TickContext, tally: ForgeryTally) -> None:
    table = ctx.rules.art_market
    forgers = await ctx.session.execute(
        select(CollectorRow, EntityRow)
        .join(EntityRow, EntityRow.id == CollectorRow.holder_entity_id)
        .where(CollectorRow.role == ArtMarketRole.FORGER, EntityRow.status == EntityStatus.CANON)
        .order_by(CollectorRow.holder_entity_id)
    )
    for _, forger in list(forgers):
        if held(forger.id) or not ctx.rng(f"forger.unmask.{forger.id}.{ctx.epoch}").chance(table.forger_detect_pct):
            continue
        judge = await ctx.session.scalar(
            select(CollectorRow.holder_entity_id)
            .join(EntityRow, EntityRow.id == CollectorRow.holder_entity_id)
            .where(CollectorRow.role.in_(list(JUDGES)), EntityRow.world_id == forger.world_id)
            .order_by(CollectorRow.connoisseurship.desc(), CollectorRow.holder_entity_id)
            .limit(1)
        )
        row = await ctx.session.scalar(
            select(ForgeryRow)
            .where(ForgeryRow.forger_entity_id == forger.id, ForgeryRow.status == ForgeryStatus.HIDDEN)
            .order_by(ForgeryRow.made_epoch, ForgeryRow.id)
            .limit(1)
        )
        if judge is None or row is None or "status" in row.locked:
            continue
        await expose(ctx, row, judge)
        tally.exposed += 1
        await record(
            ctx,
            "art.forgery_exposed",
            roles={IncidentRole.ACTOR: judge, IncidentRole.SUBJECT: forger.id},
            facts={"forgery": row.kind},
            steps=(StepDraft(StepAction.REVEAL, actor=judge, target=forger.id),),
        )


async def keep_forgeries(ctx: TickContext, tally: ForgeryTally) -> None:
    await forge_works(ctx, tally)
    await examine(ctx, tally)
    await unmask_forgers(ctx, tally)
    await ctx.session.flush()
