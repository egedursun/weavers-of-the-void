from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import first_faith_god, living_patron, patron_node, worship_creator, worships_anyone
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.queries import active_bonds, add_flag, connect, living_entity, living_son, spoken_language
from aerona.engine.primitives.records import MINIMUM_POWER_LEVEL, RecordSpec, open_record
from aerona.engine.recording.record import StepDraft, record
from aerona.language.lexicon import LexiconEntry, admissible_entries
from aerona.language.primitive import primitive_language_name, primitive_words
from aerona.language.succession import SpokenNearby, nearest_language

PRIMITIVE_SUBTYPE = "primitive language"


@dataclass(frozen=True)
class Binding:
    language_id: int | None
    new_language: bool
    god_id: int | None
    seeking: bool


@dataclass(frozen=True)
class FaithBinding:
    god_id: int | None
    seeking: bool


async def store_words(ctx: TickContext, language: EntityRow, entries: Sequence[LexiconEntry], added_by: int | None) -> int:
    existing = list(await ctx.session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language.id)))
    admitted = admissible_entries(entries, existing)
    for entry in admitted:
        await add_lexeme(
            ctx.session,
            LexemeRow(
                language_entity_id=language.id,
                word=entry.word,
                meaning=entry.meaning,
                part_of_speech=entry.part_of_speech,
                etymology=entry.origin or None,
                example=entry.example or None,
                added_by_kind=ActorKind.ENGINE,
                added_by_node_id=added_by,
                epoch=ctx.epoch,
            ),
        )
    await ctx.session.flush()
    return len(admitted)


async def closest_language(ctx: TickContext, entity: EntityRow, atlas: RegionAtlas) -> EntityRow | None:
    location = await living_entity(ctx.session, entity.location_id)
    location_language = await spoken_language(ctx.session, location.id) if location is not None and location.entity_type in COMMUNITY_TYPES else None
    ancestors = []
    for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[entity.id]):
        language = await spoken_language(ctx.session, bond.target_node_id)
        ancestors.append(language.id if language is not None else None)
    statement = (
        select(BondRow.source_node_id, BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.kind == BondKind.SPEAKS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.world_id == entity.world_id,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
            EntityRow.id != entity.id,
        )
        .order_by(BondRow.id)
    )
    speakers = []
    for speaker_id, language_id in await ctx.session.execute(statement):
        language = await living_entity(ctx.session, language_id)
        if language is not None and language.entity_type is EntityType.LANGUAGE:
            speakers.append(SpokenNearby(language_id=language_id, same_region=atlas.same_region(entity.id, speaker_id)))
    chosen = nearest_language(location_language.id if location_language is not None else None, ancestors, speakers, ctx.rules)
    found = await living_entity(ctx.session, chosen)
    return found if found is not None and found.entity_type is EntityType.LANGUAGE else None


async def primitive_language(ctx: TickContext, entity: EntityRow) -> EntityRow:
    life = ctx.rules.deep_life
    language = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LANGUAGE,
            name=primitive_language_name(entity.name),
            body=f"A language born among {entity.name} from signs and first sounds, learned from no one.",
            stats=LanguageStats(
                spread=life.primitive_language_spread, complexity=life.primitive_language_complexity, sacredness=life.primitive_language_sacredness
            ),
            power=MINIMUM_POWER_LEVEL,
            world_id=entity.world_id,
            subtype=PRIMITIVE_SUBTYPE,
            engine_kind=EngineKind.PRIMITIVE_LANGUAGE,
        ),
    )
    namer = Namer(ctx.session, ctx.rules)
    words = primitive_words(await namer.voice(language), entity.name, await namer.pool(), ctx.rules)
    await store_words(ctx, language, words, entity.id)
    return language


async def bind_first_language(ctx: TickContext, entity: EntityRow, atlas: RegionAtlas, source: EntityRow | None = None) -> tuple[EntityRow | None, bool]:
    current = await spoken_language(ctx.session, entity.id)
    if current is not None:
        return current, False
    language = await spoken_language(ctx.session, source.id) if source is not None else None
    if language is None or language.status is not EntityStatus.CANON:
        language = await closest_language(ctx, entity, atlas)
    if language is not None:
        await connect(ctx.session, entity.id, language.id, BondKind.SPEAKS, ctx.epoch, description="nearest language")
        return language, False
    language = await primitive_language(ctx, entity)
    await connect(ctx.session, entity.id, language.id, BondKind.SPEAKS, ctx.epoch, description="first sounds")
    await record(
        ctx,
        "settling.primitive_language",
        roles={IncidentRole.ACTOR: entity.id, IncidentRole.PRODUCT: language.id},
    )
    return language, True


async def bind_first_faith(ctx: TickContext, entity: EntityRow, atlas: RegionAtlas, source: EntityRow | None = None) -> FaithBinding:
    if await worships_anyone(ctx.session, entity.id):
        return FaithBinding(await patron_node(ctx.session, entity), seeking=False)
    rng = ctx.rng(seed_of("first_faith", entity.id))
    inherited = await living_patron(ctx.session, source) if source is not None else None
    if inherited is None and entity.creator_son_id is not None and rng.chance(ctx.rules.deep_life.first_faith_creator_chance):
        inherited = await living_son(ctx.session, entity.creator_son_id)
    if inherited is None and not rng.chance(ctx.rules.deep_life.first_faith_chance):
        return FaithBinding(None, seeking=False)
    god = inherited or await first_faith_god(ctx.session, ctx.rules, entity, atlas, rng.random())
    if god is not None:
        await connect(ctx.session, entity.id, god.id, BondKind.WORSHIPS, ctx.epoch, description="first faith")
        return FaithBinding(god.id, seeking=False)
    if rng.chance(ctx.rules.deep_world.new_people_worship_creator_chance) and await worship_creator(ctx.session, entity, ctx.epoch, "first faith"):
        await record(
            ctx,
            "settling.creator_faith",
            roles={IncidentRole.ACTOR: entity.id, IncidentRole.TARGET: await patron_node(ctx.session, entity)},
            steps=(StepDraft(StepAction.PRAY, actor=entity.id),),
        )
        return FaithBinding(await patron_node(ctx.session, entity), seeking=False)
    await add_flag(ctx.session, entity.id, EntityFlag.SEEKING_GOD, ctx.epoch)
    await record(
        ctx,
        "settling.seeking_god",
        roles={IncidentRole.ACTOR: entity.id},
        steps=(StepDraft(StepAction.PRAY, actor=entity.id, outcome=StepOutcome.NO_EFFECT),),
    )
    return FaithBinding(None, seeking=True)


async def bind_language_and_faith(ctx: TickContext, entity: EntityRow, atlas: RegionAtlas | None = None, source: EntityRow | None = None) -> Binding:
    if entity.status is not EntityStatus.CANON:
        return Binding(None, new_language=False, god_id=None, seeking=False)
    region_atlas = atlas or await RegionAtlas.load(ctx.session)
    region_atlas.remember(entity)
    language, created = await bind_first_language(ctx, entity, region_atlas, source)
    faith = await bind_first_faith(ctx, entity, region_atlas, source)
    return Binding(language.id if language is not None else None, new_language=created, god_id=faith.god_id, seeking=faith.seeking)
