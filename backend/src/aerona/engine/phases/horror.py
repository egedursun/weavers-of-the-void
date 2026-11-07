from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import RouteClosure, TravelMethod
from aerona.domain.enums.world import DARK_STAR_TYPES, Discovery, HorrorEventKind
from aerona.domain.models.entity_stats import CultStats, KnowledgeStats, OuterBeingStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.leak import apply_leak, leak_cap, leak_delta, record_breakdown
from aerona.engine.cosmos.routes import open_alignment
from aerona.engine.cosmos.sanity import sanity_of, shift_sanity
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.cosmos.world_types import mechanics_of
from aerona.engine.environment.book import scar_region
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.doom import doom_share
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import BondIndex, canon, connect, flags_by_entity, subtree
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import POPULATION_KEY, scale_stat, stat, stat_or
from aerona.rules.registry import Rules

SANITY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.CULT, EntityType.FACTION})
LAND_COMMUNITIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
OUTER_PREY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.SPECIES})
EYE_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL})
VOID_GUARDS = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
MADNESS_DOMAINS = frozenset({Domain.MADNESS, Domain.DREAM, Domain.SLEEP, Domain.SHADOW, Domain.LIES})
INTEREST_KEY = "interest"
WHISPERS_SUBTYPE = "whispers from beyond"


class SanityBand(StrEnum):
    CLEAR = "clear"
    CLOUDED = "clouded"
    MAD = "mad"


async def reopen_severed(ctx: TickContext) -> int:
    forgotten = set(await ctx.session.scalars(select(WorldRow.id).where(WorldRow.discovery == Discovery.FORGOTTEN)))
    statement = select(RouteRow).where(RouteRow.temp_closed_until_epoch.is_not(None), RouteRow.temp_closed_until_epoch <= ctx.epoch).order_by(RouteRow.id)
    reopened = 0
    for route in list(await ctx.session.scalars(statement)):
        if route.world_a_id in forgotten or route.world_b_id in forgotten:
            continue
        scorched = route.closure is RouteClosure.SCORCHED
        route.active = True
        route.temp_closed_until_epoch = None
        route.closure = None
        reopened += 1
        if scorched:
            await note(
                ctx,
                f"The light-sail route scorched by the flare cooled and opened again (route#{route.id}).",
                key="horror.route_cooled",
                feed=FeedCategory.GATE,
            )
        else:
            await note(ctx, f"The route severed by the void opened again (route#{route.id}).", key="horror.route_stitched", feed=FeedCategory.GATE)
    return reopened


async def reseal_temporary(ctx: TickContext) -> int:
    statement = select(RouteRow).where(RouteRow.temp_open_until_epoch.is_not(None), RouteRow.temp_open_until_epoch <= ctx.epoch).order_by(RouteRow.id)
    resealed = 0
    for route in list(await ctx.session.scalars(statement)):
        route.active = False
        route.temp_open_until_epoch = None
        route.temp_closed_until_epoch = None
        route.closure = RouteClosure.SEALED
        resealed += 1
        await note(ctx, f"The gate opened by the alignment closed again (route#{route.id}).", key="horror.route_resealed", feed=FeedCategory.GATE)
    return resealed


WARNINGS = (
    (
        "warning_1",
        "Something is leaking into {world}: nights are a moment too long, shadows a step behind. The peoples began to dream the same dream.",
        "horror.warning_first",
    ),
    ("warning_2", "{world}'s geometry is breaking: some valleys are bigger inside, some roads turn back onto themselves.", "horror.warning_geometry"),
    ("outer_being_threshold", "A tear opened in {world}'s sky. Something outside is looking in.", "horror.warning_tear"),
)


async def tear_land(ctx: TickContext, world_id: int, before: int, after: int) -> None:
    settings = ctx.rules.scars
    gained = after - max(before, settings.leak_wound_threshold)
    if gained <= 0:
        return
    grounds = list(await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world_id)))
    if not grounds:
        return
    torn = max(grounds, key=lambda ground: (ground.magic_density, -ground.entity_id))
    await scar_region(ctx.session, ctx.rules, torn, ScarKind.LEAK_WOUND, round(gained * settings.leak_wound_pct / PERCENT))


async def update_leaks(ctx: TickContext, knowledge: KnowledgeMap) -> None:
    share = await doom_share(ctx.session, ctx.rules)
    horror = ctx.rules.cosmic_horror
    for world in await WorldRepository(ctx.session).all_worlds():
        if held(world.id):
            continue
        change = await leak_delta(ctx.session, ctx.rules, world, ctx.epoch, share, knowledge=knowledge)
        record_breakdown(ctx.session, ctx.epoch, world.id, change)
        before = world.leakage
        after = apply_leak(world, change.delta, leak_cap(ctx.rules, world, ctx.epoch))
        await tear_land(ctx, world.id, before, after)
        for field_name, text, key in WARNINGS:
            threshold = getattr(horror, field_name)
            if before < threshold <= after:
                await note(ctx, text.format(world=world.name), key=key, feed=FeedCategory.LEAK)
    await ctx.session.flush()


@dataclass(frozen=True)
class SanityContext:
    leaks: dict[int, int]
    outer_worlds: set[int]
    void_erosion: dict[int, int]
    worshipping: set[int]
    knowledge: KnowledgeMap


async def _sanity_context(ctx: TickContext, knowledge: KnowledgeMap) -> SanityContext:
    worlds = await WorldRepository(ctx.session).all_worlds()
    stars = {star.id: star.star_type for star in await ctx.session.scalars(select(StarRow))}
    outer = {entity.world_id for entity in await canon(ctx.session, [EntityType.OUTER_BEING])}
    index = await BondIndex.load(ctx.session, [BondKind.WORSHIPS])
    return SanityContext(
        leaks={world.id: world.leakage for world in worlds},
        outer_worlds=outer,
        void_erosion={
            world.id: mechanics_of(world.world_type).sanity_erosion(ctx.rules)
            + (star_mechanics(stars[world.star_id]).sanity_erosion(ctx.rules) if world.star_id in stars else 0)
            for world in worlds
        },
        worshipping={bond.source_node_id for bond in index.bonds},
        knowledge=knowledge,
    )


async def sanity_drift(ctx: TickContext, entity: EntityRow, scene: SanityContext) -> int:
    horror = ctx.rules.cosmic_horror
    erosion = scene.leaks.get(entity.world_id, 0) / horror.leak_erosion_divisor + scene.void_erosion.get(entity.world_id, 0)
    erosion += horror.forbidden_erosion if scene.knowledge.knows(entity.id, KnowledgeBranch.FORBIDDEN) else 0
    erosion += horror.outer_being_erosion if entity.world_id in scene.outer_worlds else 0
    repair: float = horror.medicine_repair if scene.knowledge.knows(entity.id, KnowledgeBranch.MEDICINE) else 0
    if entity.entity_type in LAND_COMMUNITIES:
        repair += (await class_shares(ctx.session, ctx.rules, entity.id))[SocialClass.PRIEST] / horror.priest_repair_divisor
    repair += horror.worship_repair if entity.id in scene.worshipping else 0
    repair += horror.sanity_self_repair
    return round_half_up(sanity_of(ctx.rules, entity) - erosion + repair)


async def _whisperers_born(ctx: TickContext, entity: EntityRow) -> bool:
    if await EntityRepository(ctx.session).has_flag(entity.id, EntityFlag.WHISPER_SOURCE):
        return True
    cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    bonds = BondRepository(ctx.session)
    related = [*await bonds.incoming(entity.id, BondKind.RELATED), *await bonds.incoming(entity.id, BondKind.DESCENDS_FROM)]
    for bond in related:
        cult = await ctx.session.get(EntityRow, bond.source_node_id)
        if cult is not None and cult.id in cults and cult.status is EntityStatus.CANON:
            return True
    return False


async def birth_whisperers(ctx: TickContext, entity: EntityRow) -> EntityRow:
    horror = ctx.rules.cosmic_horror
    await EntityRepository(ctx.session).add_flag(entity.id, EntityFlag.WHISPER_SOURCE, ctx.epoch)
    population = stat_or(entity, POPULATION_KEY, horror.whisperers_default_population)
    cult = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{entity.name} Whisperers",
            entity_type=EntityType.CULT,
            body=f"Among {entity.name} a cult arose worshipping something whose name is not spoken; they pray not to the gods but to the outside.",
            stats=CultStats(
                followers=max(horror.whisperers_min_followers, round(population * horror.whisperers_share_pct / PERCENT)),
                zeal=horror.whisperers_zealotry,
                influence=horror.whisperers_influence,
            ),
            power=horror.whisperers_power,
            world_id=entity.world_id,
            location_id=entity.id if entity.entity_type is EntityType.SETTLEMENT else entity.location_id,
            subtype="cult of the unspoken",
            flags=(EntityFlag.OUTER_CULT,),
            sanity=horror.whisperers_sanity,
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(cult.id, entity.id, BondKind.DESCENDS_FROM, ctx.epoch, "born from within"))
    await note(
        ctx,
        f"Madness spread among {entity.name}: a cult that whispers to the outside was born, {cult.name}.",
        key="horror.whisperers",
        ids=[entity.id, cult.id],
        feed=FeedCategory.LEAK,
    )
    return cult


async def _madness(ctx: TickContext, entity: EntityRow, outer_cults: set[int]) -> None:
    horror = ctx.rules.cosmic_horror
    rng = ctx.rng("madness")
    if not rng.chance(horror.madness_chance):
        return
    eligible = entity.entity_type in LAND_COMMUNITIES and entity.id not in outer_cults and not await _whisperers_born(ctx, entity)
    if eligible and rng.chance(horror.whisperers_chance):
        await birth_whisperers(ctx, entity)
        return
    if stat(entity, POPULATION_KEY) is not None:
        scale_stat(ctx.rules, entity, POPULATION_KEY, (PERCENT - horror.madness_population_loss_pct) / PERCENT)
        await note(
            ctx, f"Madness epidemic in {entity.name}: people burned their homes and walked into the desert.", key="horror.madness_epidemic", ids=[entity.id]
        )


async def update_sanity(ctx: TickContext, knowledge: KnowledgeMap) -> None:
    horror = ctx.rules.cosmic_horror
    scene = await _sanity_context(ctx, knowledge)
    outer_cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    for entity in await canon(ctx.session, SANITY_TYPES):
        before = sanity_of(ctx.rules, entity)
        after = clamp_percent(await sanity_drift(ctx, entity, scene))
        if entity.sanity != after:
            entity.sanity = after
        if before >= horror.clouding_threshold > after:
            await note(ctx, f"{entity.name}'s mind is clouding: at night they speak in a language no one understands.", key="horror.clouding", ids=[entity.id])
        if after < horror.madness_threshold:
            await _madness(ctx, entity, outer_cults)
    await ctx.session.flush()


async def feed_madness_sons(ctx: TickContext) -> int:
    horror = ctx.rules.cosmic_horror
    worlds = await WorldRepository(ctx.session).all_worlds()
    average = sum(world.leakage for world in worlds) / len(worlds) if worlds else 0
    gain = round(average / horror.madness_son_essence_divisor)
    if not gain:
        return 0
    fed = 0
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)):
        if not set(son.domains) & MADNESS_DOMAINS:
            continue
        son.essence += gain
        son.existence = min(PERCENT_MAX, son.existence + horror.madness_son_existence_gain)
        fed += 1
    return fed


def son_sanity(rules: Rules, son: SonRow) -> int:
    return son.sanity if son.sanity is not None else rules.cosmic_horror.son_default_sanity


def son_sanity_band(rules: Rules, son: SonRow) -> SanityBand:
    value = son_sanity(rules, son)
    if value < rules.cosmic_horror.son_madness_threshold:
        return SanityBand.MAD
    if value < rules.cosmic_horror.son_clouding_threshold:
        return SanityBand.CLOUDED
    return SanityBand.CLEAR


async def _son_erosion(ctx: TickContext, son: SonRow, scene: SanityContext) -> float:
    horror = ctx.rules.cosmic_horror
    world_id = son.current_world_id
    erosion = scene.leaks.get(world_id, 0) / horror.son_leak_erosion_divisor if world_id is not None else 0.0
    erosion += horror.son_outer_erosion if world_id in scene.outer_worlds else 0
    bargains = list(await ctx.session.scalars(select(OuterBargainRow.son_id).where(OuterBargainRow.son_id == son.id)))
    erosion += len(bargains) * horror.son_bargain_erosion
    believers = [bond.source_node_id for bond in await BondRepository(ctx.session).incoming(son.id, BondKind.WORSHIPS)]
    erosion += sum(1 for believer in believers if scene.knowledge.knows(believer, KnowledgeBranch.FORBIDDEN)) * horror.son_forbidden_erosion
    if set(son.domains) & MADNESS_DOMAINS:
        erosion *= horror.son_madness_resistance_pct / PERCENT
    return erosion


async def update_son_sanity(ctx: TickContext, knowledge: KnowledgeMap) -> int:
    horror = ctx.rules.cosmic_horror
    scene = await _sanity_context(ctx, knowledge)
    changed = 0
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)):
        before = son_sanity(ctx.rules, son)
        after = clamp_percent(before - await _son_erosion(ctx, son, scene) + horror.son_sanity_repair)
        if after == son.sanity:
            continue
        son.sanity = after
        changed += 1
        if before >= horror.son_madness_threshold > after:
            await ctx.chronicle(
                ChronicleKind.HORROR, f"{son.name}'s mind broke: the things outside speak through them now.", template_key="horror.son_mad", son_id=son.id
            )
        elif before >= horror.son_clouding_threshold > after:
            await ctx.chronicle(
                ChronicleKind.HORROR, f"{son.name}'s mind is clouding; their words have begun to wander.", template_key="horror.son_clouded", son_id=son.id
            )
    return changed


async def summon_outer_being(ctx: TickContext, world: WorldRow) -> EntityRow | None:
    horror = ctx.rules.cosmic_horror
    regions = await canon(ctx.session, [EntityType.REGION], world.id)
    if not regions:
        return None
    region = max(regions, key=lambda item: (stat_or(item, "danger", 0), -item.id))
    rng = ctx.rng("outer")
    being = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"The Unspoken ({world.name})",
            entity_type=EntityType.OUTER_BEING,
            body=(f"Something came in through the tear in {world.name}'s sky. It cannot be fully seen; those who look remember only what they could not see."),
            stats=OuterBeingStats(
                size=clamp_percent(horror.outer_being_size_base + rng.die(horror.outer_being_size_die)),
                interest=clamp_percent(horror.outer_being_interest_base + rng.die(horror.outer_being_interest_die)),
                influence=clamp_percent(horror.outer_being_influence_base + rng.die(horror.outer_being_influence_die)),
            ),
            power=horror.outer_being_power,
            world_id=world.id,
            location_id=region.id,
            subtype="the unnamed",
            flags=(EntityFlag.NAMELESS,),
        ),
    )
    world.leakage = max(0, world.leakage - horror.outer_being_entry_leak_drop)
    await ctx.chronicle(
        ChronicleKind.OUTER_BEING,
        f"Something entered {world.name} from outside. No one speaks its name.",
        template_key="horror.outer_entered",
        entity_ids=[being.id],
        world_id=world.id,
        feed_category=FeedCategory.LEAK,
    )
    return being


async def outer_arrivals(ctx: TickContext) -> int:
    horror = ctx.rules.cosmic_horror
    present = {entity.world_id for entity in await canon(ctx.session, [EntityType.OUTER_BEING])}
    rng = ctx.rng("outer_roll")
    arrived = 0
    for world in await WorldRepository(ctx.session).all_worlds():
        if world.leakage < horror.outer_being_threshold or world.id in present or not rng.chance(horror.outer_being_chance):
            continue
        if await summon_outer_being(ctx, world) is not None:
            arrived += 1
    return arrived


async def outer_influence(ctx: TickContext) -> None:
    horror = ctx.rules.cosmic_horror
    rng = ctx.rng("outer_influence")
    cults = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    repository = EntityRepository(ctx.session)
    for being in await canon(ctx.session, [EntityType.OUTER_BEING]):
        interest = clamp_percent(stat_or(being, INTEREST_KEY, horror.default_interest) + rng.die(horror.interest_die) - horror.interest_decay)
        being.stats = being.stats.model_copy(update={INTEREST_KEY: interest})
        neighbours = (
            [item for item in await repository.contents(being.location_id) if item.entity_type in OUTER_PREY_TYPES] if being.location_id is not None else []
        )
        reach = horror.outer_being_victims + (stat_or(being, "size", 0) // horror.outer_being_size_per_victim if horror.outer_being_size_per_victim else 0)
        for victim in neighbours[:reach]:
            shift_sanity(ctx.rules, victim, -round(interest / horror.outer_being_sanity_divisor))
            if victim.entity_type is EntityType.SPECIES and rng.probability(interest / horror.outer_being_mutation_divisor):
                await repository.add_flag(victim.id, EntityFlag.MUTATION, ctx.epoch)
        for cult in await canon(ctx.session, [EntityType.CULT], being.world_id):
            if cult.id in cults:
                await connect(ctx.session, cult.id, being.id, BondKind.WORSHIPS, ctx.epoch, description="without speaking its name")
    await ctx.session.flush()


async def stars_align(ctx: TickContext, world: WorldRow) -> str:
    horror = ctx.rules.cosmic_horror
    await open_alignment(ctx, [TravelMethod.ANCIENT_GATE, TravelMethod.SLINGSHOT_ORBIT], danger_add=horror.alignment_route_danger)
    for item in await WorldRepository(ctx.session).all_worlds():
        item.leakage = min(PERCENT_MAX, item.leakage + horror.alignment_leak)
    return "The stars aligned: all gates opened at once and all worlds looked into the same darkness for a moment."


async def eye_in_the_sky(ctx: TickContext, world: WorldRow) -> str:
    loss = ctx.rules.cosmic_horror.sky_eye_sanity_loss
    for entity in await canon(ctx.session, None, world.id):
        if entity.sanity is not None or entity.entity_type in EYE_TYPES:
            shift_sanity(ctx.rules, entity, -loss)
    return f"An eye stayed open in {world.name}'s sky for a whole epoch. Nobody looked at it; but everyone knew they were being watched."


async def wave_of_silence(ctx: TickContext, world: WorldRow) -> str:
    rng = ctx.rng("silence")
    forgotten = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE], world.id):
        words = list(await ctx.session.scalars(select(LexemeRow.id).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id)))
        lost = rng.sample(words, len(words) * ctx.rules.cosmic_horror.silence_word_loss_pct // PERCENT)
        if lost:
            await ctx.session.execute(delete(LexemeRow).where(LexemeRow.id.in_(lost)))
            forgotten += len(lost)
    return f"A wave of silence passed through {world.name}: {forgotten} words were forgotten; people looked at things and could not remember their names."


async def reverse_rain(ctx: TickContext, world: WorldRow) -> str:
    souls = (await canon(ctx.session, [EntityType.SPIRIT], world.id))[: ctx.rules.cosmic_horror.reverse_rain_souls]
    for soul in souls:
        await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: rose to the sky with the reverse rain.")
    names = ", ".join(soul.name for soul in souls)
    gone = f"; {names} are no longer here" if names else ""
    return f"Reverse rain fell on {world.name}: the dead rose to the sky{gone}."


async def _void_candidate(ctx: TickContext, world: WorldRow) -> EntityRow | None:
    regions = await canon(ctx.session, [EntityType.REGION], world.id)
    places = await canon(ctx.session, [EntityType.PLACE], world.id)
    pool = places + (regions if len(regions) >= ctx.rules.cosmic_horror.void_min_regions else [])
    for candidate in pool:
        if not any(item.entity_type in VOID_GUARDS for item in await _subtree(ctx, candidate.id)):
            return candidate
    return None


async def _subtree(ctx: TickContext, root_id: int) -> list[EntityRow]:
    return await subtree(ctx.session, root_id)


async def visit_of_the_void(ctx: TickContext, world: WorldRow) -> str | None:
    target = await _void_candidate(ctx, world)
    if target is None:
        return None
    for item in [target, *await _subtree(ctx, target.id)]:
        await retire(ctx.session, item, ctx.epoch, f"Epoch {ctx.epoch}: erased by the Void.", status=EntityStatus.DESTROYED)
    await EntityRepository(ctx.session).add_flag(target.id, EntityFlag.VOID, ctx.epoch)
    return f"The Void visited {world.name}: {target.name} was erased from the map. In its place is a nothingness that tires the eye to look at."


async def the_dimming(ctx: TickContext, world: WorldRow) -> str | None:
    star = await ctx.session.get(StarRow, world.star_id) if world.star_id is not None else None
    if star is None or star.star_type in DARK_STAR_TYPES or star.brightness <= 0:
        return None
    before = star.brightness
    star.brightness = max(0, star.brightness - ctx.rules.cosmic_horror.dimming_brightness_loss)
    await ctx.session.flush()
    return (
        f"Something drank from {star.name}: its light fell from {before} to {star.brightness}. "
        f"{world.name} grew colder, and nobody could say what had stood between it and its sun."
    )


async def _whispered_knowledge(ctx: TickContext, world: WorldRow) -> EntityRow:
    horror = ctx.rules.cosmic_horror
    known = [item for item in await canon(ctx.session, [EntityType.KNOWLEDGE], world.id) if item.subtype == WHISPERS_SUBTYPE]
    if known:
        return known[0]
    return await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"Whispers from Beyond ({world.name})",
            entity_type=EntityType.KNOWLEDGE,
            body="Words that came from outside the world, heard in sleep and never spoken aloud by choice.",
            stats=KnowledgeStats(level=horror.whispers_knowledge_level, spread=0),
            power=horror.whispers_knowledge_power,
            world_id=world.id,
            subtype=WHISPERS_SUBTYPE,
            knowledge_branch=KnowledgeBranch.FORBIDDEN,
        ),
    )


async def whispers_from_beyond(ctx: TickContext, world: WorldRow) -> str | None:
    horror = ctx.rules.cosmic_horror
    knowledge = await _whispered_knowledge(ctx, world)
    heard = set(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == knowledge.id, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
        )
    )
    mortals = [item for item in await canon(ctx.session, [EntityType.MORTAL], world.id) if item.id not in heard]
    communities = [item for item in await canon(ctx.session, COMMUNITY_TYPES, world.id) if item.id not in heard]
    if mortals:
        listener = max(mortals, key=lambda item: (stat_or(item, "intellect", 0), -item.id))
    elif communities:
        listener = max(communities, key=lambda item: (item.importance or 0, -item.id))
    else:
        return None
    if not await teach(ctx, listener.id, knowledge, "heard it whispered from beyond the world"):
        return None
    shift_sanity(ctx.rules, listener, -horror.whispers_sanity_loss)
    return f"Whispers from beyond reached {listener.name} in {world.name}: they now know what should not be known, and they cannot stop listening."


async def horror_event(ctx: TickContext, kind: HorrorEventKind, world: WorldRow) -> str | None:
    handlers = {
        HorrorEventKind.STARS_ALIGN: stars_align,
        HorrorEventKind.EYE_IN_THE_SKY: eye_in_the_sky,
        HorrorEventKind.WAVE_OF_SILENCE: wave_of_silence,
        HorrorEventKind.REVERSE_RAIN: reverse_rain,
        HorrorEventKind.VISIT_OF_THE_VOID: visit_of_the_void,
        HorrorEventKind.THE_DIMMING: the_dimming,
        HorrorEventKind.WHISPERS_FROM_BEYOND: whispers_from_beyond,
    }
    text = await handlers[kind](ctx, world)
    if text is not None:
        await ctx.chronicle(ChronicleKind.HORROR, text, template_key=f"horror.{kind.value}", world_id=world.id, feed_category=FeedCategory.LEAK)
    return text


async def spontaneous_horror(ctx: TickContext) -> str | None:
    worlds = await WorldRepository(ctx.session).all_worlds()
    if not worlds:
        return None
    world = max(worlds, key=lambda item: (item.leakage, -item.id))
    horror = ctx.rules.cosmic_horror
    chance = world.leakage / horror.horror_event_divisor + await doom_share(ctx.session, ctx.rules) / horror.apocalypse_event_divisor
    rng = ctx.rng("horror_event")
    if not rng.probability(chance):
        return None
    return await horror_event(ctx, rng.pick(list(HorrorEventKind)), world)


@reads(
    "people.population",
    "settlement.population",
    "table.addictions",
    "table.bonds",
    "table.community_societies",
    "table.cosmos",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.nodes",
    "table.outer_bargains",
    "table.routes",
)
@writes(
    "people.population",
    "settlement.population",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.sons",
    "table.world_leak_items",
    "table.worlds",
)
async def horror_phase(ctx: TickContext) -> None:
    await reopen_severed(ctx)
    await reseal_temporary(ctx)
    knowledge = await KnowledgeMap.load(ctx.session)
    await update_leaks(ctx, knowledge)
    await update_sanity(ctx, knowledge)
    await feed_madness_sons(ctx)
    await update_son_sanity(ctx, knowledge)
    await outer_arrivals(ctx)
    await outer_influence(ctx)
    await spontaneous_horror(ctx)
    await ctx.session.flush()


async def _world(session: AsyncSession, world_id: int) -> WorldRow:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if world.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{world.name} was forgotten; nothing can be ordered inside the mist.")
    return world


async def order_horror_event(session: AsyncSession, rules: Rules, world_id: int, kind: HorrorEventKind) -> str:
    ctx = await manual_context(session, "horror_event", rules, key=f"{world_id}:{kind.value}")
    text = await horror_event(ctx, kind, await _world(session, world_id))
    if text is None:
        raise ValidationFailedError("Nothing in that world can be swallowed by the Void.")
    return text


async def order_outer_being(session: AsyncSession, rules: Rules, world_id: int) -> EntityRow:
    ctx = await manual_context(session, "summon_outer", rules, key=str(world_id))
    being = await summon_outer_being(ctx, await _world(session, world_id))
    if being is None:
        raise ValidationFailedError("A world without regions has nowhere for it to enter.")
    return being


async def spawn_outer_cult(session: AsyncSession, rules: Rules, entity_id: int) -> EntityRow:
    ctx = await manual_context(session, "outer_cult", rules, key=str(entity_id))
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.status is not EntityStatus.CANON or entity.entity_type not in LAND_COMMUNITIES:
        raise NotFoundError("Only a living people or settlement can give birth to such a cult.")
    return await birth_whisperers(ctx, entity)


async def suppress_outer_cult(session: AsyncSession, rules: Rules, cult_id: int) -> EntityRow:
    ctx = await manual_context(session, "suppress_cult", rules, key=str(cult_id))
    cult = await session.get(EntityRow, cult_id)
    if cult is None or cult.status is not EntityStatus.CANON or not await EntityRepository(session).has_flag(cult_id, EntityFlag.OUTER_CULT):
        raise NotFoundError("No such outer cult.")
    return await retire(session, cult, ctx.epoch, f"Epoch {ctx.epoch}: scattered by the creator's hand.", status=EntityStatus.DESTROYED, close_bonds=True)


async def set_son_sanity(session: AsyncSession, son_id: int, value: int) -> SonRow:
    son = await session.get(SonRow, son_id)
    if son is None:
        raise NotFoundError("No such son.")
    son.sanity = clamp_percent(value)
    await session.flush()
    return son


async def run_horror_phase(session: AsyncSession, rules: Rules) -> None:
    await horror_phase(await manual_context(session, "horror", rules))


PHASES = (Phase("horror", horror_phase),)
