from sqlalchemy import select

from aerona.catalog.lore import ART_MESSAGES, ART_WORDS
from aerona.catalog.peoples import AESTHETIC_AXES, AESTHETIC_IMAGES, AESTHETIC_MEDIA, AESTHETIC_SHUNS, IMAGE_NAMES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import PERFORMED_MEDIA, VERBAL_MEDIA, ArtMedium, Technique
from aerona.domain.enums.demography import Aesthetic
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import ArtworkStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

WEAK_CLAIM = 50


async def taste_of(ctx: TickContext, holder: EntityRow) -> Aesthetic | None:
    people = await people_of(ctx.session, holder)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.aesthetic if culture is not None else None


def aesthetic_fit(rules: Rules, taste: Aesthetic | None, medium: ArtMedium) -> float:
    if taste is None:
        return 1.0
    if medium in AESTHETIC_MEDIA[taste]:
        return rules.customs.aesthetic_fit_pct / PERCENT
    if medium in AESTHETIC_SHUNS[taste]:
        return rules.customs.aesthetic_clash_pct / PERCENT
    return 1.0


def taste_message(rules: Rules, taste: Aesthetic | None, medium: ArtMedium, message: dict[str, int]) -> dict[str, int]:
    if taste is None or medium not in AESTHETIC_MEDIA[taste]:
        return dict(message)
    axis = AESTHETIC_AXES[taste].value
    return {**message, axis: message.get(axis, 0) + rules.customs.aesthetic_message}


def medium_of(artwork: EntityRow) -> ArtMedium:
    text = f"{artwork.name} {artwork.subtype or ''}".lower()
    for medium, words in ART_WORDS.items():
        if any(word in text for word in words):
            return medium
    return ArtMedium.SONG


async def subject_of(ctx: TickContext, artwork_id: int) -> int | None:
    statement = select(BondRow.target_node_id).where(
        BondRow.source_node_id == artwork_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    return await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))


async def author_of(ctx: TickContext, artwork_id: int) -> int | None:
    mortals = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL)
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == artwork_id, BondRow.kind == BondKind.OWNS, BondRow.source_node_id.in_(mortals))
    return await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))


async def spoken(ctx: TickContext, entity_id: int | None) -> int | None:
    if entity_id is None:
        return None
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))


async def profile_of(ctx: TickContext, artwork: EntityRow) -> ArtworkProfileRow:
    row = await ctx.session.get(ArtworkProfileRow, artwork.id)
    if row is not None:
        return row
    medium = medium_of(artwork)
    author = await author_of(ctx, artwork.id)
    row = ArtworkProfileRow(
        artwork_entity_id=artwork.id,
        medium=medium,
        performed=medium in PERFORMED_MEDIA,
        author_entity_id=author,
        subject_node_id=await subject_of(ctx, artwork.id),
        message={axis.value: value for axis, value in ART_MESSAGES[medium].items()},
        quality=clamp_int(stat(artwork, "renown") or PERCENT // 2, 0, PERCENT),
        copies=1,
        language_entity_id=await spoken(ctx, artwork.location_id) if medium in VERBAL_MEDIA else None,
        translations=[],
        propaganda=False,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def pressure(ctx: TickContext, artwork: EntityRow, row: ArtworkProfileRow) -> bool:
    holder = await living_entity(ctx.session, artwork.location_id)
    if holder is None:
        return False
    weight = (stat(artwork, "influence") or 0) * (stat(artwork, "renown") or 0) / (PERCENT * PERCENT) * ctx.rules.art.pressure_pct / PERCENT
    subject = await ctx.session.get(EntityRow, row.subject_node_id) if row.subject_node_id is not None else None
    conqueror = subject is not None and await ruled_by(ctx, holder.id, subject.id)
    if conqueror and subject is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=holder.id,
            subject_id=subject.id,
            kind=MemoryKind.HUMILIATED_ME,
            magnitude=-ctx.rules.art.humiliation,
            epoch=ctx.epoch,
            note=artwork.name,
        )
        return True
    values = await stored_values(ctx.session, ValueHolder.CULTURE, holder.id)
    if not values:
        return False
    taste = await taste_of(ctx, holder)
    weight *= aesthetic_fit(ctx.rules, taste, row.medium)
    moved = False
    for key, value in taste_message(ctx.rules, taste, row.medium, row.message).items():
        step = round_half_up(value * weight * row.copies)
        if step:
            axis = ValueAxis(key)
            values[axis] = values.get(axis, 0) + step
            moved = True
    if moved:
        await write_values(ctx.session, ValueHolder.CULTURE, holder.id, values)
    return moved


async def ruled_by(ctx: TickContext, community_id: int, ruler_id: int) -> bool:
    statement = select(BondRow.id).where(
        BondRow.source_node_id == ruler_id, BondRow.target_node_id == community_id, BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def commemorate(ctx: TickContext, row: ArtworkProfileRow) -> str | None:
    if row.subject_node_id is None:
        return None
    subject = await ctx.session.get(EntityRow, row.subject_node_id)
    if subject is None:
        son = await ctx.session.get(SonRow, row.subject_node_id)
        if son is not None:
            son.fame += ctx.rules.art.god_fame
            return "god"
        return None
    spirits = await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id == subject.id))
    kept = False
    for spirit in spirits:
        spirit.memory_strength = clamp_int(spirit.memory_strength + ctx.rules.art.commemoration_memory, 0, PERCENT)
        kept = True
    return "remembered" if kept else None


async def translate(ctx: TickContext, artwork: EntityRow, row: ArtworkProfileRow) -> bool:
    if row.medium not in VERBAL_MEDIA or row.language_entity_id is None or artwork.location_id is None:
        return False
    if not ctx.rng(f"translate.{artwork.id}.{ctx.epoch}").chance(ctx.rules.art.translation_chance):
        return False
    neighbours = select(BondRow.target_node_id).where(
        BondRow.source_node_id == artwork.location_id, BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE
    )
    for partner in list(await ctx.session.scalars(neighbours)):
        tongue = await spoken(ctx, partner)
        if tongue is not None and tongue != row.language_entity_id and tongue not in row.translations:
            row.translations = [*row.translations, tongue]
            return True
    return False


async def art_year(ctx: TickContext, artwork: EntityRow) -> dict[str, int]:
    row = await profile_of(ctx, artwork)
    counts = {"pressed": int(await pressure(ctx, artwork, row))}
    remembered = await commemorate(ctx, row)
    if remembered:
        counts[f"commemorated_{remembered}"] = 1
    counts["translated"] = int(await translate(ctx, artwork, row))
    if row.medium in VERBAL_MEDIA and (stat(artwork, "renown") or 0) >= PERCENT // 2 and "copies" not in row.locked:
        printed = await has_technique(ctx.session, artwork.location_id, Technique.PRINTING)
        row.copies += ctx.rules.art.copies_gain + (ctx.rules.technique_effects.printing_copies if printed else 0)
    row.updated_epoch = ctx.epoch
    return counts


async def commission(ctx: TickContext, realm: PolityProfileRow) -> EntityRow | None:
    table = ctx.rules.propaganda
    if realm.treasury < table.cost or realm.legitimacy >= WEAK_CLAIM:
        return None
    if not ctx.rng(f"propaganda.{realm.polity_entity_id}.{ctx.epoch}").chance(table.commission_chance):
        return None
    ruler_id = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm.polity_entity_id, OfficeRow.kind == OfficeKind.RULER)
    )
    ruler = await living_entity(ctx.session, ruler_id)
    seat = await living_entity(ctx.session, realm.capital_entity_id or realm.core_entity_id)
    if ruler is None or seat is None:
        return None
    realm.treasury -= table.cost
    taste = await taste_of(ctx, seat)
    medium = AESTHETIC_IMAGES[taste] if taste is not None else ArtMedium.STATUE
    message = {ValueAxis.HIERARCHY.value: 5, ValueAxis.HONOUR.value: 2}
    work = await create_record(
        ctx,
        RecordSpec(
            name=IMAGE_NAMES.get(medium, IMAGE_NAMES[ArtMedium.STATUE]).format(ruler=ruler.name),
            entity_type=EntityType.ARTWORK,
            stats=ArtworkStats(renown=PERCENT // 2, influence=PERCENT // 2),
            body=f"Raised in {seat.name} by order of the realm to praise {ruler.name}.",
            power=2,
            world_id=seat.world_id,
            location_id=seat.id,
        ),
    )
    ctx.session.add(
        ArtworkProfileRow(
            artwork_entity_id=work.id,
            medium=medium,
            performed=medium in PERFORMED_MEDIA,
            patron_entity_id=realm.polity_entity_id,
            subject_node_id=ruler.id,
            message=taste_message(ctx.rules, taste, medium, message),
            quality=PERCENT // 2,
            copies=1,
            translations=[],
            propaganda=True,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    realm.legitimacy = clamp_int(realm.legitimacy + table.legitimacy, 0, PERCENT)
    return work


async def living_artworks(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.ARTWORK, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )


IMAGES = frozenset({ArtMedium.STATUE, ArtMedium.FRESCO, ArtMedium.MOSAIC, ArtMedium.CARVING, ArtMedium.TAPESTRY, ArtMedium.ARCHITECTURE_ORNAMENT})


async def images_in(ctx: TickContext, place_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.ARTWORK, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == place_id)
        .order_by(EntityRow.id)
    )
    return [work for work in rows if medium_of(work) in IMAGES]


async def smash(ctx: TickContext, place_id: int, chance: int, reason: str) -> list[EntityRow]:
    broken = []
    for work in await images_in(ctx, place_id):
        if ctx.rng(f"smash.{work.id}.{ctx.epoch}").chance(chance):
            await retire(ctx.session, work, ctx.epoch, f"Epoch {ctx.epoch}: {reason}.", status=EntityStatus.DESTROYED)
            broken.append(work)
    return broken
