from dataclasses import dataclass, field, replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.terrain import default_terrain
from aerona.catalog.worlds import STAR_TYPE_LABELS, WORLD_TYPES
from aerona.constants.cosmos import (
    MOON_ORBIT_BASE,
    MOON_ORBIT_STEP,
    PLANET_ORBIT_BASE,
    PLANET_ORBIT_JITTER,
    PLANET_ORBIT_STEP,
    WORLD_SEED_ALPHABET,
    WORLD_SEED_LENGTH,
)
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository, normalize_name
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow, lexeme_key
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.world import StarType, WorldType
from aerona.domain.models.entity_stats import CelestialStats, EntityStats, LanguageStats, PeopleStats, RegionStats, ResourceStats, SpeciesStats
from aerona.domain.models.phonology import Phonology
from aerona.domain.models.profiles import TravelResource
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god, parse_domains
from aerona.engine.cosmos.maps import store_world_map
from aerona.engine.cosmos.resources import DepositSpec, cosmic_deposits, create_cosmic_deposit, set_mechanics
from aerona.engine.cosmos.routes import connect_world
from aerona.engine.cosmos.stars import StarSpec, create_star
from aerona.engine.cosmos.world_types import mechanics_of
from aerona.engine.cosmos.worlds import assign_mirror_twin
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.numbers import clamp_float, clamp_percent
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.language.alphabet import first_word
from aerona.language.generator import NameKind
from aerona.language.syllables import syllabify
from aerona.prompts.schemas.cosmos import NativeKind, NewWorldOutput, PlacementChoice
from aerona.prompts.schemas.shared import NamingRuleOutput
from aerona.rules.registry import Rules

PHONOLOGY_FALLBACK_PATTERN = "CV"


@dataclass(frozen=True)
class BirthRequest:
    forced_type: WorldType | None = None
    creator_son_id: int | None = None
    star_id: int | None = None
    parent_world_id: int | None = None
    new_star: bool = False
    new_star_type: StarType | None = None


@dataclass
class BirthState:
    world: WorldRow
    origin: EntityOrigin
    son: SonRow | None
    phonemes: frozenset[str] | None
    regions: list[EntityRow] = field(default_factory=list)
    created: list[EntityRow] = field(default_factory=list)
    misfits: list[EntityRow] = field(default_factory=list)


def roll(rng: SeededRandom, base: int, die: int) -> int:
    return clamp_percent(base + rng.die(die))


def phoneme_set(output: NewWorldOutput, rules: Rules) -> frozenset[str] | None:
    letters = frozenset(letter for word in output.language.words for letter in word.word.lower() if letter.isalpha())
    return letters if len(letters) >= rules.world_birth.phoneme_set_min else None


def fits(name: str, phonemes: frozenset[str] | None) -> bool:
    return phonemes is None or all(letter in phonemes for letter in first_word(name).lower() if letter.isalpha())


def narrative_star_type(output: NewWorldOutput) -> StarType | None:
    text = f"{output.description} {output.day} {output.cosmology}".lower()
    matches = [(len(label), star_type) for star_type, label in STAR_TYPE_LABELS.items() if label.lower() in text]
    return max(matches, key=lambda item: item[0])[1] if matches else None


def phonology_from(dialect: NamingRuleOutput, rules: Rules) -> Phonology | None:
    vowels = tuple(dict.fromkeys(letter for letter in dialect.vowels.lower() if letter.isalpha()))
    consonants = tuple(dict.fromkeys(letter for letter in dialect.consonants.lower() if letter.isalpha()))
    if not vowels or not consonants:
        return None
    lengths = [len(syllabify(name.lower())) for name in dialect.sample_names if name.strip()]
    low = max(1, min(lengths)) if lengths else rules.language.name_min_syllables
    high = max(low, *lengths) if lengths else max(low, rules.language.name_max_syllables)
    return Phonology(
        vowels=vowels,
        consonants=consonants,
        forbidden_sounds=tuple(dialect.forbidden_sounds),
        syllable_patterns=tuple(dialect.syllable_patterns) or (PHONOLOGY_FALLBACK_PATTERN,),
        preferred_endings=tuple(dialect.endings),
        min_syllables=low,
        max_syllables=high,
        sample_names=tuple(name.strip() for name in dialect.sample_names if name.strip()),
    )


def world_seed(name: str, rng: SeededRandom) -> str:
    suffix = "".join(rng.pick(WORLD_SEED_ALPHABET) for _ in range(WORLD_SEED_LENGTH))
    return f"{name}:{suffix}"


async def _orbit(session: AsyncSession, rng: SeededRandom, star_id: int | None, parent_id: int | None) -> float:
    if parent_id is not None:
        moons = int(await session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.parent_world_id == parent_id)) or 0)
        return MOON_ORBIT_BASE + moons * MOON_ORBIT_STEP
    planets = int(await session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.star_id == star_id, WorldRow.parent_world_id.is_(None))) or 0)
    return PLANET_ORBIT_BASE + planets * PLANET_ORBIT_STEP + rng.random() * PLANET_ORBIT_JITTER


def _needs_new_star(output: NewWorldOutput, stars: list[StarRow]) -> bool:
    if output.placement is not PlacementChoice.NEW_STAR:
        return False
    if output.star is not None and output.star.name.strip():
        return True
    wanted = narrative_star_type(output)
    return wanted is not None and all(star.star_type is not wanted for star in stars)


async def _requested_placement(session: AsyncSession, output: NewWorldOutput, request: BirthRequest) -> tuple[int | None, int | None] | None:
    if request.parent_world_id is not None and await session.get(WorldRow, request.parent_world_id) is not None:
        return None, request.parent_world_id
    if request.star_id is not None and await session.get(StarRow, request.star_id) is not None:
        return request.star_id, None
    if request.new_star:
        return None, None
    if output.placement is PlacementChoice.MOON and output.parent_world_id is not None and await session.get(WorldRow, output.parent_world_id) is not None:
        return None, output.parent_world_id
    return None


async def _placement(session: AsyncSession, rng: SeededRandom, output: NewWorldOutput, request: BirthRequest) -> tuple[int | None, int | None]:
    requested = await _requested_placement(session, output, request)
    if requested is not None:
        return requested
    stars = list(await session.scalars(select(StarRow).order_by(StarRow.id)))
    if not stars or _needs_new_star(output, stars):
        return None, None
    if output.star_id is not None and any(star.id == output.star_id for star in stars):
        return output.star_id, None
    wanted = narrative_star_type(output)
    matching = [star for star in stars if star.star_type is wanted]
    return (matching[0] if matching else rng.pick(stars)).id, None


async def _new_star(ctx: TickContext, output: NewWorldOutput, world_name: str, requested: StarType | None) -> StarRow:
    birth = ctx.rules.world_birth
    fallback_type = requested or narrative_star_type(output) or StarType.YELLOW_DWARF
    name = output.star.name.strip() if output.star is not None and output.star.name.strip() else f"{world_name} Sun"
    if normalize_name(name) == normalize_name(world_name):
        name = f"{world_name} Sun"
    star_type = requested or (output.star.type if output.star is not None and output.star.name.strip() else fallback_type)
    description = output.star.description if output.star is not None else None
    return await create_star(
        ctx.session, ctx.rng("birth_star"), ctx.epoch, StarSpec(name, star_type, birth.star_brightness_base, birth.star_brightness_die, description)
    )


async def _insert_world(ctx: TickContext, output: NewWorldOutput, request: BirthRequest, world_type: WorldType) -> WorldRow:
    session, rules = ctx.session, ctx.rules
    rng = ctx.rng("birth_world")
    name = await NameRepository(session).unique_name(output.name)
    star_id, parent_id = await _placement(session, rng, output, request)
    if star_id is None and parent_id is None:
        star_id = (await _new_star(ctx, output, name, request.new_star_type)).id
    mechanics = mechanics_of(world_type)
    terrain = default_terrain(world_type, rules)
    physics = rules.world_physics
    return await WorldRepository(session).create_world(
        WorldDraft(
            name=name,
            world_type=world_type,
            orbit=await _orbit(session, rng, star_id, parent_id),
            terrain_seed=world_seed(name, rng),
            terrain_sea=(terrain.sea_pct or 0) / PERCENT,
            terrain_mountains=(terrain.mountains_pct or 0) / PERCENT,
            terrain_humidity=clamp_float((terrain.moisture_pct or 0) / PERCENT, -1.0, 1.0),
            danger=roll(rng, rules.world_birth.danger_base, rules.world_birth.danger_die),
            created_epoch=ctx.epoch,
            star_id=star_id,
            parent_world_id=parent_id,
            gravity=mechanics.forced_gravity or output.gravity,
            atmosphere=mechanics.forced_atmosphere or output.atmosphere,
            time_factor=clamp_float(output.time_factor or 1.0, physics.time_factor_min / PERCENT, physics.time_factor_max / PERCENT),
            phonology=phonology_from(output.dialect, rules),
            cosmology=output.cosmology,
            description=f"{output.description} {output.day}".strip(),
            creator_son_id=request.creator_son_id,
        )
    )


async def _add(ctx: TickContext, state: BirthState, spec: RecordSpec) -> EntityRow:
    entity = await open_record(ctx.session, ctx.epoch, spec)
    state.created.append(entity)
    if not fits(entity.name, state.phonemes):
        state.misfits.append(entity)
    return entity


def _region_at(state: BirthState, index: int) -> EntityRow:
    return state.regions[max(0, min(index, len(state.regions) - 1))]


async def _regions(ctx: TickContext, state: BirthState, output: NewWorldOutput) -> None:
    birth = ctx.rules.world_birth
    rng = ctx.rng("birth_regions")
    for item in [region for region in output.regions if region.name.strip()][: birth.regions_max]:
        stats = RegionStats(
            breadth=roll(rng, birth.region_breadth_base, birth.region_breadth_die),
            danger=clamp_percent(item.danger),
            fertility=clamp_percent(item.fertility),
            magic=clamp_percent(item.magic),
        )
        state.regions.append(
            await _add(
                ctx,
                state,
                replace(
                    _spec(
                        state,
                        item.name,
                        EntityType.REGION,
                        item.description,
                        stats,
                        power=birth.region_power,
                        subtype=item.subtype,
                        image_prompt=item.image_prompt,
                    ),
                    is_water=item.water,
                ),
            )
        )
    if not state.regions:
        raise ValidationFailedError("A world cannot be born without regions.")


def _spec(
    state: BirthState, name: str, entity_type: EntityType, description: str, stats: EntityStats, *, power: int, subtype: str, image_prompt: str | None = None
) -> RecordSpec:
    return RecordSpec(
        name=name,
        entity_type=entity_type,
        body=description,
        stats=stats,
        power=power,
        world_id=state.world.id,
        subtype=subtype,
        origin=state.origin,
        creator_son_id=state.son.id if state.son is not None else None,
        pending=False,
        image_prompt=image_prompt,
    )


async def _sky_and_resource(ctx: TickContext, state: BirthState, output: NewWorldOutput) -> EntityRow | None:
    birth = ctx.rules.world_birth
    rng = ctx.rng("birth_bodies")
    if output.sky.name.strip():
        sky_stats = CelestialStats(
            brightness=roll(rng, birth.sky_brightness_base, birth.sky_brightness_die), influence=roll(rng, birth.sky_influence_base, birth.sky_influence_die)
        )
        await _add(
            ctx,
            state,
            _spec(
                state,
                output.sky.name,
                EntityType.CELESTIAL,
                output.sky.description,
                sky_stats,
                power=birth.sky_power,
                subtype=output.sky.subtype,
                image_prompt=output.sky.image_prompt,
            ),
        )
    unique = output.unique_resource
    if not unique.name.strip():
        return None
    region = _region_at(state, unique.region_index)
    stats = ResourceStats(
        abundance=roll(rng, birth.resource_abundance_base, birth.resource_abundance_die),
        value=roll(rng, birth.resource_value_base, birth.resource_value_die),
        might=roll(rng, birth.resource_might_base, birth.resource_might_die),
    )
    base = _spec(
        state,
        unique.name,
        EntityType.RESOURCE,
        f"{unique.description} Rule: {unique.rule}",
        stats,
        power=birth.resource_power,
        subtype=unique.subtype,
        image_prompt=unique.image_prompt,
    )
    resource = await _add(ctx, state, replace(base, location_id=region.id, flags=(EntityFlag.ORIGINAL_RESOURCE,)))
    mechanics = list(dict.fromkeys(unique.mechanics))[: birth.resource_mechanics_max]
    sacred_son = state.son.id if state.son is not None and ResourceMechanic.SACRED in mechanics else None
    if mechanics:
        await set_mechanics(ctx.session, resource, [item for item in mechanics if item is not ResourceMechanic.SACRED or sacred_son is not None], sacred_son)
    return resource


async def _cosmic_resource(ctx: TickContext, state: BirthState, output: NewWorldOutput, unique: EntityRow | None) -> None:
    offered = output.cosmic_resource
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    if offered is None or not offered.name.strip() or cosmos.travel_resource is not None or await cosmic_deposits(ctx.session):
        return
    if unique is not None and normalize_name(unique.name) == normalize_name(offered.name):
        return
    resource = TravelResource(name=offered.name, description=offered.description, rule=offered.rule, side_effect=offered.side_effect)
    cosmos.travel_resource = resource
    birth = ctx.rules.world_birth
    rng = ctx.rng("birth_cosmic")
    deposit = await create_cosmic_deposit(
        ctx.session,
        ctx.epoch,
        resource,
        DepositSpec(
            region=_region_at(state, offered.region_index),
            abundance=birth.cosmic_deposit_abundance_base + rng.die(birth.cosmic_deposit_abundance_die),
            value=birth.cosmic_deposit_value,
            might=birth.cosmic_deposit_might_base + rng.die(birth.cosmic_deposit_might_die),
            power_level=birth.cosmic_deposit_power,
            name=f"{offered.name} Deposit",
            origin=state.origin,
            creator_son_id=state.son.id if state.son is not None else None,
        ),
    )
    await EntityRepository(ctx.session).add_flag(deposit.id, EntityFlag.FIXED_NAME)
    deposit.image_prompt = offered.image_prompt
    state.created.append(deposit)


async def _language(ctx: TickContext, state: BirthState, output: NewWorldOutput) -> EntityRow | None:
    birth = ctx.rules.world_birth
    item = output.language
    if not item.name.strip():
        return None
    rng = ctx.rng("birth_language")
    stats = LanguageStats(
        spread=birth.language_spread,
        complexity=roll(rng, birth.language_complexity_base, birth.language_complexity_die),
        sacredness=roll(rng, birth.language_sacredness_base, birth.language_sacredness_die),
    )
    language = await open_record(
        ctx.session,
        ctx.epoch,
        _spec(state, item.name, EntityType.LANGUAGE, item.description, stats, power=birth.language_power, subtype=item.subtype or "native language"),
    )
    state.created.append(language)
    if state.world.phonology is not None:
        ctx.session.add(LanguageProfileRow(entity_id=language.id, phonology=state.world.phonology, seed=state.world.terrain_seed))
    seen: set[str] = set()
    actor = ActorKind.SON if state.son is not None else ActorKind.CREATOR
    actor_id = state.son.id if state.son is not None else await _creator_id(ctx.session)
    for word in item.words[: birth.words_max]:
        key = lexeme_key(word.word)
        if not key or key in seen:
            continue
        seen.add(key)
        ctx.session.add(
            LexemeRow(
                language_entity_id=language.id,
                word=word.word,
                meaning=word.meaning,
                part_of_speech=word.kind,
                etymology=word.origin or None,
                added_by_kind=actor,
                added_by_node_id=actor_id,
                epoch=ctx.epoch,
            )
        )
    await ctx.session.flush()
    return language


async def _creator_id(session: AsyncSession) -> int | None:
    creator = await CosmosRepository(session).creator()
    return creator.id if creator is not None else None


async def _rename_misfits(ctx: TickContext, state: BirthState, language: EntityRow | None) -> None:
    if language is None:
        return
    repository = EntityRepository(ctx.session)
    namer = Namer(ctx.session, ctx.rules)
    for entity in state.misfits:
        kind = NameKind.PLACE if entity.entity_type is EntityType.REGION else NameKind.GENERAL
        derived = await namer.from_language(language, f"birth:{state.world.id}:{entity.id}", kind)
        if derived is not None:
            await repository.rename(entity, derived)
            await repository.add_flag(entity.id, EntityFlag.NAME_FROM_LANGUAGE, ctx.epoch)


async def _natives(ctx: TickContext, state: BirthState, output: NewWorldOutput, language: EntityRow | None, unique: EntityRow | None) -> None:
    birth = ctx.rules.world_birth
    rng = ctx.rng("birth_natives")
    bonds = BondRepository(ctx.session)
    for item in [native for native in output.natives if native.name.strip()][: birth.natives_max]:
        region = _region_at(state, item.region_index)
        stats: EntityStats
        if item.kind is NativeKind.PEOPLE:
            stats = PeopleStats(
                population=birth.people_population_base + rng.die(birth.people_population_die),
                martiality=roll(rng, birth.people_martiality_base, birth.people_martiality_die),
                magic=clamp_percent(rng.die(birth.people_magic_die)),
                craft=roll(rng, birth.people_craft_base, birth.people_craft_die),
                piety=roll(rng, birth.people_piety_base, birth.people_piety_die),
            )
            entity_type = EntityType.PEOPLE
        else:
            stats = SpeciesStats(
                hp=birth.species_hp_base + rng.die(birth.species_hp_die),
                strength=roll(rng, birth.species_strength_base, birth.species_strength_die),
                agility=roll(rng, birth.species_agility_base, birth.species_agility_die),
                intelligence=clamp_percent(rng.die(birth.species_intelligence_die)),
                danger=roll(rng, birth.species_danger_base, birth.species_danger_die),
            )
            entity_type = EntityType.SPECIES
        base = _spec(state, item.name, entity_type, item.description, stats, power=birth.native_power, subtype=item.subtype, image_prompt=item.image_prompt)
        native = await _add(ctx, state, replace(base, location_id=region.id, flags=(EntityFlag.NATIVE,)))
        if entity_type is EntityType.PEOPLE and language is not None:
            await bonds.connect(BondDraft(native.id, language.id, BondKind.SPEAKS, ctx.epoch, "native tongue"))
        if entity_type is EntityType.PEOPLE and unique is not None and unique.location_id == region.id:
            await bonds.connect(BondDraft(native.id, unique.id, BondKind.OWNS, ctx.epoch, "native resource"))


async def _old_god(ctx: TickContext, state: BirthState, output: NewWorldOutput) -> None:
    item = output.old_god
    if item is None or not item.name.strip():
        return
    fallback = WORLD_TYPES[state.world.world_type].domains
    god = await add_foreign_god(
        ctx.session,
        ctx.rules,
        ctx.rng("birth_old_god"),
        ctx.epoch,
        NewForeignGod(
            name=item.name,
            world_id=state.world.id,
            domains=parse_domains(item.domains, fallback),
            title=item.title,
            description=item.description,
            stance=item.attitude,
            image_prompt=item.image_prompt,
        ),
    )
    ctx.count("old_gods")
    await ctx.chronicle(
        ChronicleKind.FOREIGN_GOD, f"{god.name}, an old god, already dwelt on {state.world.name}.", template_key="cosmos.old_god", world_id=state.world.id
    )


async def _son_claims(ctx: TickContext, state: BirthState) -> int | None:
    son = state.son
    if son is None:
        return None
    previous = son.current_world_id
    son.current_world_id = state.world.id
    await BondRepository(ctx.session).connect(BondDraft(son.id, state.regions[0].id, BondKind.PROTECTS, ctx.epoch, "the world he birthed"))
    return previous


async def process_world_birth(ctx: TickContext, output: NewWorldOutput, request: BirthRequest) -> WorldRow:
    if not output.name.strip():
        raise ValidationFailedError("World birth output has no name.")
    world_type = request.forced_type or output.type or WorldType.ORDINARY
    son = await ctx.session.get(SonRow, request.creator_son_id) if request.creator_son_id is not None else None
    world = await _insert_world(ctx, output, request, world_type)
    world.image_prompt = output.image_prompt
    state = BirthState(world, EntityOrigin.COSMOS if son is not None else EntityOrigin.CREATOR, son, phoneme_set(output, ctx.rules))
    if WORLD_TYPES[world_type].mirror:
        await assign_mirror_twin(ctx.session, world)
    await _regions(ctx, state, output)
    unique = await _sky_and_resource(ctx, state, output)
    await _cosmic_resource(ctx, state, output, unique)
    language = await _language(ctx, state, output)
    await _rename_misfits(ctx, state, language)
    await _natives(ctx, state, output, language, unique)
    await _old_god(ctx, state, output)
    previous = await _son_claims(ctx, state)
    await connect_world(ctx, world, previous)
    maker = son.name if son is not None else "The Creator"
    text = f"{maker} birthed a new world: {world.name} ({WORLD_TYPES[world_type].label}). {output.description}"
    ids = [entity.id for entity in state.created if entity.entity_type in (EntityType.REGION, EntityType.CELESTIAL, EntityType.RESOURCE)]
    await ctx.chronicle(
        ChronicleKind.WORLD_BIRTH,
        text,
        template_key="cosmos.world_born",
        entity_ids=ids,
        son_id=son.id if son else None,
        world_id=world.id,
        feed_category=FeedCategory.WORLD,
    )
    ctx.count("worlds_born")
    await ctx.session.flush()
    await store_world_map(ctx.session, ctx.rules, world, ctx.epoch)
    return world
