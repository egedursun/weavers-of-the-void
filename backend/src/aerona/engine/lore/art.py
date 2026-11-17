from sqlalchemy import select

from aerona.catalog.art_modes import ART_MODES, IMAGE_MODES, PERFORMED_MODES, VERBAL_MODES
from aerona.catalog.kinds.motifs import MOTIF_SOURCES
from aerona.catalog.lore import ART_MESSAGES
from aerona.catalog.peoples import Style
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow, SpeakerCohortRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ArtMode, Technique
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, PreferenceKind, SkillKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import ArtworkStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.language import speakers
from aerona.engine.lore.motifs import people_motifs
from aerona.engine.lore.printing import banned_for, scribe_pace
from aerona.engine.lore.research import has_technique
from aerona.engine.lore.style import image_mode, style_fit, style_message, style_of
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.mind.preferences import art_fit, favourite, paint
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.transform.lore import remember_artwork

WEAK_CLAIM = 50
HALF = 2
PERFORMERS = (SkillKind.ORATORY, SkillKind.LORE)
IMAGES = IMAGE_MODES


async def favourite_form(ctx: TickContext, seat: EntityRow) -> ArtMode | None:
    people = await people_of(ctx.session, seat)
    loved = await favourite(ctx.session, people.id, PreferenceKind.ART_FORM) if people is not None else None
    if loved is None or loved.strength < ctx.rules.preferences.noted_above:
        return None
    return ArtMode(loved.target)


async def taste_of(ctx: TickContext, holder: EntityRow) -> Style | None:
    people = await people_of(ctx.session, holder)
    return style_of(await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None)


async def subject_of(ctx: TickContext, artwork_id: int) -> int | None:
    statement = select(BondRow.target_node_id).where(
        BondRow.source_node_id == artwork_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    celebrated = await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))
    return celebrated if celebrated is not None else await motif_subject(ctx, artwork_id)


async def motif_subject(ctx: TickContext, artwork_id: int) -> int | None:
    artwork = await ctx.session.get(EntityRow, artwork_id)
    home = await ctx.session.get(EntityRow, artwork.location_id) if artwork is not None and artwork.location_id is not None else None
    people = await people_of(ctx.session, home) if home is not None else None
    if artwork is None or people is None:
        return None
    for source in await people_motifs(ctx.session, people.id):
        spec = MOTIF_SOURCES[source]
        if not spec.entity_types:
            continue
        found = await ctx.session.scalars(
            select(EntityRow.id)
            .where(EntityRow.world_id == artwork.world_id, EntityRow.entity_type.in_(sorted(spec.entity_types)), EntityRow.status == spec.status)
            .where(EntityRow.id != artwork.id)
            .order_by(EntityRow.id)
        )
        candidates = list(found)
        if candidates:
            return candidates[artwork.id % len(candidates)]
    return None


async def author_of(ctx: TickContext, artwork_id: int) -> int | None:
    mortals = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL)
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == artwork_id, BondRow.kind == BondKind.OWNS, BondRow.source_node_id.in_(mortals))
    return await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))


async def spoken(ctx: TickContext, entity_id: int | None) -> int | None:
    if entity_id is None:
        return None
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))


async def profile_of(ctx: TickContext, artwork: EntityRow, medium: ArtMode | None = None) -> ArtworkProfileRow:
    row = await ctx.session.get(ArtworkProfileRow, artwork.id)
    if row is not None:
        return row
    chosen = medium or ArtMode.MUSICAL
    row = ArtworkProfileRow(
        artwork_entity_id=artwork.id,
        medium=chosen,
        performed=chosen in PERFORMED_MODES,
        author_entity_id=await author_of(ctx, artwork.id),
        subject_node_id=await subject_of(ctx, artwork.id),
        message={axis.value: value for axis, value in ART_MESSAGES[chosen].items()},
        quality=clamp_int(stat_or(artwork, "renown", PERCENT // HALF), 0, PERCENT),
        copies=1,
        language_entity_id=await spoken(ctx, artwork.location_id) if chosen in VERBAL_MODES else None,
        translations=[],
        propaganda=False,
        canon=False,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


def craft_weight(row: ArtworkProfileRow) -> float:
    return row.quality / (PERCENT / HALF)


def canon_weight(ctx: TickContext, row: ArtworkProfileRow) -> float:
    return 1 + ctx.rules.art.canon_pct / PERCENT if row.canon else 1.0


async def press_on(ctx: TickContext, community_id: int, row: ArtworkProfileRow, weight: float) -> bool:
    values = await stored_values(ctx.session, ValueHolder.CULTURE, community_id)
    if not values:
        return False
    holder = await ctx.session.get(EntityRow, community_id)
    taste = await taste_of(ctx, holder) if holder is not None else None
    tasted = weight * style_fit(ctx.rules, taste, row.medium)
    moved = False
    for key, value in style_message(ctx.rules, taste, row.medium, row.message).items():
        step = round_half_up(value * tasted)
        if step:
            axis = ValueAxis(key)
            values[axis] = values.get(axis, 0) + step
            moved = True
    if moved:
        await write_values(ctx.session, ValueHolder.CULTURE, community_id, values)
    return moved


async def readers_of(ctx: TickContext, row: ArtworkProfileRow) -> list[int]:
    found: set[int] = set()
    for language in row.translations:
        found.update(await speakers(ctx.session, language))
    return sorted(found)


async def pressure(ctx: TickContext, artwork: EntityRow, row: ArtworkProfileRow) -> bool:
    holder = await living_entity(ctx.session, artwork.location_id)
    if holder is None:
        return False
    weight = (
        (stat(artwork, "influence") or 0)
        * (stat(artwork, "renown") or 0)
        / (PERCENT * PERCENT)
        * ctx.rules.art.pressure_pct
        / PERCENT
        * craft_weight(row)
        * canon_weight(ctx, row)
    )
    subject = await ctx.session.get(EntityRow, row.subject_node_id) if row.subject_node_id is not None else None
    if subject is not None and await ruled_by(ctx, holder.id, subject.id):
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
    moved = await press_on(ctx, holder.id, row, weight * row.copies)
    abroad = weight * ctx.rules.art.translated_pct / PERCENT
    for reader in await readers_of(ctx, row):
        if reader != holder.id:
            moved = await press_on(ctx, reader, row, abroad) or moved
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
            son.fame += round_half_up(ctx.rules.art.god_fame * craft_weight(row))
            return "god"
        return None
    spirits = await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.origin_mortal_id == subject.id))
    kept = False
    for spirit in spirits:
        spirit.memory_strength = clamp_int(spirit.memory_strength + round_half_up(ctx.rules.art.commemoration_memory * craft_weight(row)), 0, PERCENT)
        kept = True
    return "remembered" if kept else None


async def skilled(ctx: TickContext, place_id: int, skills: tuple[SkillKind, ...], level: int) -> int | None:
    mortals = select(EntityRow.id).where(
        await present_among(ctx.session, [place_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    return await ctx.session.scalar(
        select(SkillRow.holder_node_id)
        .where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill.in_(list(skills)), SkillRow.level >= level)
        .order_by(SkillRow.level.desc(), SkillRow.holder_node_id)
        .limit(1)
    )


async def knows(ctx: TickContext, community_id: int, language_id: int) -> bool:
    if await spoken(ctx, community_id) == language_id:
        return True
    share = await ctx.session.scalar(
        select(SpeakerCohortRow.share).where(SpeakerCohortRow.community_entity_id == community_id, SpeakerCohortRow.language_entity_id == language_id).limit(1)
    )
    return (share or 0) >= ctx.rules.art.bilingual_share


async def translate(ctx: TickContext, artwork: EntityRow, row: ArtworkProfileRow) -> int | None:
    if row.medium not in VERBAL_MODES or row.language_entity_id is None or artwork.location_id is None:
        return None
    scribe = await skilled(ctx, artwork.location_id, (SkillKind.LANGUAGES, SkillKind.WRITING), ctx.rules.interpreters.interpreter_skill)
    if scribe is None or not ctx.rng(f"translate.{artwork.id}.{ctx.epoch}").chance(ctx.rules.art.translation_chance):
        return None
    neighbours = select(BondRow.target_node_id).where(
        BondRow.source_node_id == artwork.location_id, BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE
    )
    for partner in list(await ctx.session.scalars(neighbours.order_by(BondRow.id))):
        tongue = await spoken(ctx, partner)
        if tongue is None or tongue == row.language_entity_id or tongue in row.translations or not await knows(ctx, artwork.location_id, tongue):
            continue
        row.translations = [*row.translations, tongue]
        return scribe
    return None


async def performers_left(ctx: TickContext, artwork: EntityRow, row: ArtworkProfileRow) -> bool:
    home = await living_entity(ctx.session, artwork.location_id)
    voiced = home is not None and home.entity_type in COMMUNITY_TYPES
    if voiced and home is not None and (row.language_entity_id is None or await knows(ctx, home.id, row.language_entity_id)):
        return True
    author = await living_entity(ctx.session, row.author_entity_id)
    if author is not None:
        return True
    return artwork.location_id is not None and await skilled(ctx, artwork.location_id, PERFORMERS, ctx.rules.art.performer_skill) is not None


async def forgotten(ctx: TickContext, artwork: EntityRow, row: ArtworkProfileRow) -> bool:
    if not row.performed or row.canon or "performed" in row.locked or await performers_left(ctx, artwork, row):
        return False
    await retire(ctx.session, artwork, ctx.epoch, f"Epoch {ctx.epoch}: none were left who could perform it.", status=EntityStatus.DESTROYED)
    await remember_artwork(ctx, artwork, row)
    await note(ctx, f"{artwork.name} was forgotten, for none were left who could perform it.", key="art.forgotten", ids=[artwork.id])
    return True


async def art_year(ctx: TickContext, artwork: EntityRow) -> dict[str, int]:
    row = await profile_of(ctx, artwork)
    if await forgotten(ctx, artwork, row):
        return {"forgotten": 1}
    counts = {"pressed": int(await pressure(ctx, artwork, row)), "painted": int(await paint(ctx, artwork, row))}
    holder = await living_entity(ctx.session, artwork.location_id)
    if holder is not None:
        lean = await art_fit(ctx.session, holder, row)
        step = lean / PERCENT * ctx.rules.preferences.art_renown_step * ctx.rules.preferences.art_fit_pct / PERCENT
        if round_half_up(step):
            shift_stat(artwork, "renown", step, PERCENT // HALF)
            counts["tasted"] = 1
    remembered = await commemorate(ctx, row)
    if remembered:
        counts[f"commemorated_{remembered}"] = 1
    scribe = await translate(ctx, artwork, row)
    counts["translated"] = int(scribe is not None)
    if scribe is not None:
        await note(ctx, f"{artwork.name} was put into another tongue and its message carried further.", key="art.translated", ids=[artwork.id, scribe])
    if row.medium in VERBAL_MODES and (stat(artwork, "renown") or 0) >= PERCENT // HALF and "copies" not in row.locked:
        printed = await has_technique(ctx.session, artwork.location_id, Technique.PRINTING)
        gain = ctx.rules.art.copies_gain + (ctx.rules.technique_effects.printing_copies if printed else 0)
        pace = await scribe_pace(ctx.session, ctx.rules, artwork.location_id)
        if not await banned_for(ctx.session, artwork.location_id, artwork.id):
            row.copies += max(0, round_half_up(gain * pace * craft_weight(row) * canon_weight(ctx, row)))
    row.updated_epoch = ctx.epoch
    return counts


async def treasury_of(ctx: TickContext, patron: EntityRow) -> tuple[PolityProfileRow | None, SettlementProfileRow | None]:
    realm = await ctx.session.get(PolityProfileRow, patron.id) if patron.entity_type is EntityType.POLITY else None
    town = await ctx.session.get(SettlementProfileRow, patron.id) if patron.entity_type is EntityType.SETTLEMENT else None
    return realm, town


async def pay_for(ctx: TickContext, patron: EntityRow, cost: int) -> None:
    realm, town = await treasury_of(ctx, patron)
    if realm is not None:
        if realm.treasury < cost:
            raise ValidationFailedError(f"The treasury of {patron.name} cannot pay {cost} for the work.")
        realm.treasury -= cost
    elif town is not None:
        if town.treasury < cost:
            raise ValidationFailedError(f"The treasury of {patron.name} cannot pay {cost} for the work.")
        town.treasury -= cost


async def commission_work(
    ctx: TickContext,
    patron_id: int,
    *,
    name: str,
    medium: ArtMode,
    author_id: int | None,
    subject_id: int | None,
    message: dict[str, int] | None,
    paid: bool,
) -> EntityRow:
    patron = await living_entity(ctx.session, patron_id)
    if patron is None:
        raise NotFoundError("No such living patron.")
    author = await living_entity(ctx.session, author_id) if author_id is not None else None
    if author_id is not None and (author is None or author.entity_type is not EntityType.MORTAL):
        raise NotFoundError("No such living artist.")
    subject = await ctx.session.get(EntityRow, subject_id) if subject_id is not None else None
    home = patron if patron.entity_type in COMMUNITY_TYPES else await living_entity(ctx.session, patron.location_id)
    if home is None and patron.entity_type is EntityType.POLITY:
        realm = await ctx.session.get(PolityProfileRow, patron.id)
        home = await living_entity(ctx.session, (realm.capital_entity_id or realm.core_entity_id) if realm is not None else None)
    if home is None:
        raise ValidationFailedError(f"{patron.name} has nowhere to raise the work.")
    if paid:
        await pay_for(ctx, patron, ctx.rules.propaganda.cost)
    work = await create_record(
        ctx,
        RecordSpec(
            name=name.strip() or f"The {medium.value.replace('_', ' ').title()} of {patron.name}",
            entity_type=EntityType.ARTWORK,
            stats=ArtworkStats(renown=PERCENT // HALF, influence=PERCENT // HALF),
            body=f"Made at the bidding of {patron.name}{f' to honour {subject.name}' if subject is not None else ''}.",
            power=HALF,
            world_id=home.world_id,
            location_id=home.id,
        ),
    )
    skill = (
        await ctx.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == author.id).order_by(SkillRow.level.desc()).limit(1))
        if author
        else None
    )
    ctx.session.add(
        ArtworkProfileRow(
            artwork_entity_id=work.id,
            medium=medium,
            performed=medium in PERFORMED_MODES,
            author_entity_id=author.id if author is not None else None,
            patron_entity_id=patron.id,
            subject_node_id=subject.id if subject is not None else None,
            message=dict(message) if message else {axis.value: value for axis, value in ART_MESSAGES[medium].items()},
            quality=clamp_int(skill if skill is not None else PERCENT // HALF, 0, PERCENT),
            copies=1,
            language_entity_id=await spoken(ctx, home.id) if medium in VERBAL_MODES else None,
            translations=[],
            propaganda=False,
            canon=False,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    if author is not None:
        await connect(ctx.session, author.id, work.id, BondKind.OWNS, ctx.epoch, description="made it")
    if subject is not None:
        await connect(ctx.session, work.id, subject.id, BondKind.CELEBRATES, ctx.epoch, description="portrays")
    await note(ctx, f"{patron.name} commissioned {work.name}.", key="art.commissioned", ids=[work.id, patron.id, *([author.id] if author else [])])
    return work


async def canonise(ctx: TickContext, artwork_id: int, *, canon: bool) -> ArtworkProfileRow:
    artwork = await living_entity(ctx.session, artwork_id)
    if artwork is None or artwork.entity_type is not EntityType.ARTWORK:
        raise NotFoundError("No such living artwork.")
    row = await profile_of(ctx, artwork)
    row.canon = canon
    row.locked = sorted({*row.locked, "canon"})
    if canon:
        await note(ctx, f"{artwork.name} was set among the classics of its people.", key="art.canonised", ids=[artwork.id])
    await ctx.session.flush()
    return row


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
    medium = image_mode(taste)
    loved = await favourite_form(ctx, seat)
    medium = loved if loved is not None else medium
    message = {ValueAxis.HIERARCHY.value: 5, ValueAxis.HONOUR.value: 2}
    work = await create_record(
        ctx,
        RecordSpec(
            name=f"{ART_MODES[medium].label} of {ruler.name}",
            entity_type=EntityType.ARTWORK,
            stats=ArtworkStats(renown=PERCENT // HALF, influence=PERCENT // HALF),
            body=f"Raised in {seat.name} by order of the realm to praise {ruler.name}.",
            power=HALF,
            world_id=seat.world_id,
            location_id=seat.id,
        ),
    )
    ctx.session.add(
        ArtworkProfileRow(
            artwork_entity_id=work.id,
            medium=medium,
            performed=medium in PERFORMED_MODES,
            patron_entity_id=realm.polity_entity_id,
            subject_node_id=ruler.id,
            message=style_message(ctx.rules, taste, medium, message),
            quality=PERCENT // HALF,
            copies=1,
            translations=[],
            propaganda=True,
            canon=False,
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


async def images_in(ctx: TickContext, place_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(ArtworkProfileRow, ArtworkProfileRow.artwork_entity_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.ARTWORK,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == place_id,
            ArtworkProfileRow.medium.in_(list(IMAGES)),
        )
        .order_by(EntityRow.id)
    )
    return list(rows)


async def smash(ctx: TickContext, place_id: int, chance: int, reason: str) -> list[EntityRow]:
    broken = []
    for work in await images_in(ctx, place_id):
        if ctx.rng(f"smash.{work.id}.{ctx.epoch}").chance(chance):
            await retire(ctx.session, work, ctx.epoch, f"Epoch {ctx.epoch}: {reason}.", status=EntityStatus.DESTROYED)
            profile = await ctx.session.get(ArtworkProfileRow, work.id)
            if profile is not None:
                await remember_artwork(ctx, work, profile)
            broken.append(work)
    return broken
