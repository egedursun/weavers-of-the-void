from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, CultHoldingRow, RelicRow, SpiritProfileRow
from aerona.db.tables.society import SoulRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import FuneralRite, HoldingKind, SpiritAlignment
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.doctrine import liturgy_for, rebirth_path_of
from aerona.engine.faith.judgement import default_criteria, judge, profile_for, recount
from aerona.engine.faith.works import bones_of, canonise, hold, saints
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.words import names_word

PROFILES_FIXUP = "faith.spirit_profiles"
CRITERIA_FIXUP = "faith.strata_criteria"
POPULATION_FIXUP = "faith.strata_population"
SAINTS_FIXUP = "faith.dead_saints"
BONES_FIXUP = "faith.relic_bones"
FUNERAL_FIXUP = "faith.funeral_rites"
DOCTRINE_FIXUP = "faith.doctrine_liturgy_rebirth"
FUNERAL_WORDS = ((("burn", "pyre", "fire", "ash"), FuneralRite.BURNING), (("sky", "tower", "vulture", "expos", "wind"), FuneralRite.EXPOSURE))


async def applied(ctx: TickContext, key: str) -> bool:
    return await ctx.session.get(AppliedFixupRow, key) is not None


async def mark(ctx: TickContext, key: str, done: int) -> int:
    ctx.session.add(AppliedFixupRow(key=key, result={"rows": done}))
    await ctx.session.flush()
    return done


async def origin_of(ctx: TickContext, spirit: EntityRow) -> tuple[EntityRow | None, EntityRow | None]:
    soul = await ctx.session.scalar(select(SoulRow).where(SoulRow.spirit_entity_id == spirit.id))
    if soul is not None:
        realm = await ctx.session.get(EntityRow, soul.realm_entity_id) if soul.realm_entity_id is not None else None
        return await ctx.session.get(EntityRow, soul.mortal_entity_id), realm
    mortal_id = await ctx.session.scalar(
        select(BondRow.target_node_id).where(BondRow.source_node_id == spirit.id, BondRow.kind == BondKind.DESCENDS_FROM).order_by(BondRow.id).limit(1)
    )
    mortal = await ctx.session.get(EntityRow, mortal_id) if mortal_id is not None else None
    return (mortal if mortal is not None and mortal.entity_type is EntityType.MORTAL else None), None


def temper(ctx: TickContext, spirit: EntityRow) -> SpiritAlignment:
    unrest = stat(spirit, "unrest") or 0
    if unrest >= ctx.rules.spirits.vengeful_unrest:
        return SpiritAlignment.VENGEFUL
    if unrest <= ctx.rules.world_effects.spirit_restless_threshold:
        return SpiritAlignment.GUARDIAN
    return SpiritAlignment.NEUTRAL


async def spirit_profiles(ctx: TickContext) -> int:
    known = select(SpiritProfileRow.spirit_entity_id)
    spirits = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(known))
            .order_by(EntityRow.id)
        )
    )
    for spirit in spirits:
        mortal, realm = await origin_of(ctx, spirit)
        if mortal is None:
            ctx.session.add(
                SpiritProfileRow(
                    spirit_entity_id=spirit.id,
                    imprint={},
                    traits=[],
                    deeds={},
                    memory_strength=100,
                    veneration=0,
                    alignment=temper(ctx, spirit),
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
            )
            continue
        if realm is not None:
            await judge(ctx, spirit, mortal, realm)
        else:
            profile = await profile_for(ctx, spirit, mortal)
            profile.alignment = temper(ctx, spirit)
    await ctx.session.flush()
    return len(spirits)


async def strata_criteria(ctx: TickContext) -> int:
    rows = list(await ctx.session.scalars(select(AfterlifeStratumRow).order_by(AfterlifeStratumRow.id)))
    for row in rows:
        row.criteria = default_criteria(ctx.rules.afterlife, row.kind).stored()
    return len(rows)


async def dead_saints(ctx: TickContext, book: FaithBook) -> int:
    named = 0
    for church in book.churches.values():
        if church.doctrine is None:
            continue
        for saint in await saints(ctx, church, since=0):
            await canonise(ctx, church, saint)
            named += 1
    return named


async def relic_bones(ctx: TickContext, book: FaithBook) -> int:
    mortals = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL)
    moved = 0
    for row in list(await ctx.session.scalars(select(RelicRow).where(RelicRow.item_entity_id.in_(mortals)))):
        church = book.churches.get(row.cult_entity_id or -1)
        saint = await ctx.session.get(EntityRow, row.item_entity_id)
        if church is None or saint is None:
            continue
        bones = await bones_of(ctx, church, saint)
        ctx.session.add(
            RelicRow(
                item_entity_id=bones.id,
                saint_entity_id=saint.id,
                cult_entity_id=row.cult_entity_id,
                shrine_entity_id=row.shrine_entity_id,
                sanctity=row.sanctity,
                pilgrims=row.pilgrims,
                canonised_epoch=row.canonised_epoch,
                locked=list(row.locked or []),
            )
        )
        holding = await ctx.session.get(CultHoldingRow, (church.cult.id, saint.id))
        if holding is not None:
            await ctx.session.delete(holding)
        await ctx.session.delete(row)
        await hold(ctx, church, bones.id, HoldingKind.RELIC)
        moved += 1
    await ctx.session.flush()
    return moved


async def funeral_rites(ctx: TickContext) -> int:
    rows = list(
        await ctx.session.scalars(
            select(TraditionProfileRow).where(TraditionProfileRow.kind == TraditionKind.FUNERAL_RITE, TraditionProfileRow.funeral_rite.is_(None))
        )
    )
    for row in rows:
        tradition = await ctx.session.get(EntityRow, row.tradition_entity_id)
        text = f"{tradition.name} {tradition.subtype or ''}".lower() if tradition is not None else ""
        row.funeral_rite = next((rite for words, rite in FUNERAL_WORDS if names_word(text, words)), FuneralRite.BURIAL)
    return len(rows)


async def doctrine_fields(ctx: TickContext, book: FaithBook) -> int:
    touched = 0
    for church in book.churches.values():
        doctrine: CultDoctrineRow | None = church.doctrine
        if doctrine is None:
            continue
        if doctrine.liturgical_language_id is None and "liturgical_language_id" not in doctrine.locked:
            doctrine.liturgical_language_id = await liturgy_for(ctx.session, church)
        if "rebirth_path" not in doctrine.locked:
            doctrine.rebirth_path = rebirth_path_of(ctx.rules, await values_for(ctx.session, church.cult.id), doctrine.judgement)
        touched += 1
    return touched


async def backfill_faith(ctx: TickContext, book: FaithBook) -> int:
    done = 0
    if not await applied(ctx, CRITERIA_FIXUP):
        done += await mark(ctx, CRITERIA_FIXUP, await strata_criteria(ctx))
    if not await applied(ctx, FUNERAL_FIXUP):
        done += await mark(ctx, FUNERAL_FIXUP, await funeral_rites(ctx))
    if not await applied(ctx, DOCTRINE_FIXUP):
        done += await mark(ctx, DOCTRINE_FIXUP, await doctrine_fields(ctx, book))
    if not await applied(ctx, PROFILES_FIXUP):
        done += await mark(ctx, PROFILES_FIXUP, await spirit_profiles(ctx))
    if not await applied(ctx, BONES_FIXUP):
        done += await mark(ctx, BONES_FIXUP, await relic_bones(ctx, book))
    if not await applied(ctx, SAINTS_FIXUP):
        done += await mark(ctx, SAINTS_FIXUP, await dead_saints(ctx, book))
    if not await applied(ctx, POPULATION_FIXUP):
        await recount(ctx)
        done += await mark(ctx, POPULATION_FIXUP, len(list(await ctx.session.scalars(select(AfterlifeStratumRow.id)))))
    return done
