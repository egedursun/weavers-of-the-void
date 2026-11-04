from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, ResourceMechanic
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import PeopleStats, ResourceStats, SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import (
    BESTOWED,
    DANGER_KEY,
    SPECIES_STAT_KEYS,
    STRENGTH_KEY,
    assign_traits,
    common_child,
    species_danger,
    traits_of,
    weave_chimera,
)
from aerona.engine.cosmos.resources import set_mechanics, travel_resource
from aerona.engine.cosmos.sanity import sanity_of, shift_sanity
from aerona.engine.ecology.foodweb import broken_links, diet_allows, form_link, regions_of
from aerona.engine.ecology.ranges import adapt_subspecies
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import active_bonds, canon, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.stats import FOLLOWERS_KEY, POPULATION_KEY, put_stat, scale_stat, shift_bounded, stat, stat_or
from aerona.rules.registry import Rules

VICTIM_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL})
WEAVER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
FERTILITY_KEY = "fertility"
MARTIALITY_KEY = "martiality"
MAGIC_KEY = "magic"


async def _species(ctx: TickContext) -> list[EntityRow]:
    return await canon(ctx.session, [EntityType.SPECIES])


async def _location(ctx: TickContext, species: EntityRow) -> EntityRow | None:
    return await ctx.session.get(EntityRow, species.location_id) if species.location_id is not None else None


async def edible_souls(ctx: TickContext, location: EntityRow) -> list[EntityRow]:
    spared = await flags_by_entity(ctx.session, EntityFlag.SPARED_SOUL)
    contents = await EntityRepository(ctx.session).contents(location.id)
    return [item for item in contents if item.entity_type is EntityType.SPIRIT and item.status is EntityStatus.CANON and item.id not in spared]


async def swallow_soul(ctx: TickContext, species: EntityRow, soul: EntityRow) -> EntityRow:
    await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: {species.name} swallowed it.")
    await note(ctx, f"{species.name} swallowed {soul.name}; in those lands no dead return anymore.", key="creatures.soul_eaten", ids=[species.id, soul.id])
    return soul


async def _soul_eating(ctx: TickContext, species: EntityRow, location: EntityRow) -> None:
    souls = await edible_souls(ctx, location)
    if souls and ctx.rng("soul_eater").chance(ctx.rules.creatures.soul_eater_chance):
        await swallow_soul(ctx, species, souls[0])


async def _gnaw_minds(ctx: TickContext, location: EntityRow) -> None:
    creatures = ctx.rules.creatures
    victims = [item for item in await EntityRepository(ctx.session).contents(location.id) if item.entity_type in VICTIM_TYPES]
    if location.entity_type in VICTIM_TYPES:
        victims.insert(0, location)
    for victim in victims[: creatures.mind_reader_victims]:
        shift_sanity(ctx.rules, victim, -creatures.mind_reader_sanity_loss)


async def trait_effects(ctx: TickContext, species: EntityRow) -> None:
    creatures = ctx.rules.creatures
    traits = await traits_of(ctx.session, species.id)
    location = await _location(ctx, species)
    if location is not None and CreatureTrait.RADIANT in traits:
        shift_bounded(ctx.rules, location, DANGER_KEY, -creatures.radiant_danger_drop)
        shift_bounded(ctx.rules, location, FERTILITY_KEY, creatures.radiant_fertility_gain)
    if location is not None and CreatureTrait.SOUL_EATER in traits:
        await _soul_eating(ctx, species, location)
    if location is not None and traits & {CreatureTrait.MIND_READER, CreatureTrait.SOUL_EATER}:
        await _gnaw_minds(ctx, location)
    if CreatureTrait.FISSIPAROUS in traits and ctx.rng("fission").chance(creatures.fission_chance):
        shift_bounded(ctx.rules, species, DANGER_KEY, creatures.fission_danger_gain)


async def _mutation_chance(ctx: TickContext, species: EntityRow, leaks: dict[int, int], flags: set[EntityFlag]) -> float:
    creatures = ctx.rules.creatures
    chance = leaks.get(species.world_id, 0) / creatures.mutation_leak_divisor
    if EntityFlag.MUTATION in flags:
        chance += creatures.mutation_tagged_bonus_pct / PERCENT
    if EntityFlag.CURSED in flags:
        chance += creatures.mutation_cursed_bonus_pct / PERCENT
    if stat_or(species, "might", 0):
        chance += creatures.mutation_might_bonus_pct / PERCENT
    return chance


async def mutate_species(ctx: TickContext, species: EntityRow, leak: int) -> EntityRow:
    creatures = ctx.rules.creatures
    rng = ctx.rng("mutation")
    owned = await traits_of(ctx.session, species.id)
    fresh = [trait for trait in CreatureTrait if trait not in owned and trait not in BESTOWED]
    new_trait = rng.pick_or_none(fresh)
    stats = species.stats
    if isinstance(stats, SpeciesStats):
        changes = {
            key: clamp_percent(stat_or(species, key, creatures.chimera_default_stat) + rng.die(creatures.mutation_die) - creatures.mutation_shift)
            for key in SPECIES_STAT_KEYS
        }
        stats = stats.model_copy(update=changes)
    cause = "under the influence of what leaked in from outside" if leak >= creatures.mutation_leak_text_threshold else "under the influence of curse and magic"
    born = f": {new_trait.value.replace('_', ' ')}" if new_trait is not None else ""
    mutant = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{species.name} Corruption",
            entity_type=EntityType.SPECIES,
            body=f"{species.name} changed {cause}; a new form was born{born}.",
            stats=stats,
            power=species.power_level,
            world_id=species.world_id,
            location_id=species.location_id,
            subtype="mutant",
            flags=(EntityFlag.MUTANT,),
            traits=[*sorted(owned), *([new_trait] if new_trait is not None else [])],
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(mutant.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, "mutation"))
    await EntityRepository(ctx.session).add_flag(species.id, EntityFlag.MUTATED, ctx.epoch)
    await note(ctx, f"{species.name} mutated; a new form was born.", key="creatures.mutation", ids=[species.id, mutant.id])
    return mutant


async def species_mutations(ctx: TickContext) -> int:
    cap = ctx.rules.creatures.mutation_cap
    leaks = {world.id: world.leakage for world in await ctx.session.scalars(select(WorldRow))}
    repository = EntityRepository(ctx.session)
    mutated = 0
    rng = ctx.rng("mutation_roll")
    for species in await _species(ctx):
        if mutated >= cap:
            break
        flags = await repository.flags(species.id)
        if EntityFlag.MUTATED in flags:
            continue
        if rng.probability(await _mutation_chance(ctx, species, leaks, flags)):
            await mutate_species(ctx, species, leaks.get(species.world_id, 0))
            mutated += 1
    return mutated


async def split_changed_people(ctx: TickContext, people: EntityRow) -> EntityRow:
    creatures = ctx.rules.creatures
    population = stat_or(people, POPULATION_KEY, creatures.people_default_population)
    changed = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{people.name} Changed Ones",
            entity_type=EntityType.PEOPLE,
            body=f"A branch whose bodies and language changed split from {people.name}; they now consider themselves another people.",
            stats=PeopleStats(
                population=max(1, round(population * creatures.people_mutation_share_pct / PERCENT)),
                martiality=clamp_percent(stat_or(people, MARTIALITY_KEY, creatures.people_default_martiality) + creatures.changed_martiality_gain),
                magic=clamp_percent(stat_or(people, MAGIC_KEY, creatures.people_default_magic) + creatures.changed_magic_gain),
                craft=creatures.changed_craft,
                piety=creatures.changed_piety,
            ),
            power=people.power_level,
            world_id=people.world_id,
            location_id=people.location_id,
            subtype="changed people",
            flags=(EntityFlag.MUTANT,),
            sanity=creatures.changed_sanity,
        ),
    )
    scale_stat(ctx.rules, people, POPULATION_KEY, (PERCENT - creatures.people_mutation_share_pct) / PERCENT)
    await EntityRepository(ctx.session).add_flag(people.id, EntityFlag.MUTATED, ctx.epoch)
    await BondRepository(ctx.session).connect(BondDraft(changed.id, people.id, BondKind.DESCENDS_FROM, ctx.epoch, "mutation"))
    await note(ctx, f"A changed branch split from {people.name}: {changed.name}.", key="creatures.people_mutation", ids=[people.id, changed.id])
    return changed


async def people_mutation(ctx: TickContext) -> EntityRow | None:
    creatures = ctx.rules.creatures
    mutated = await flags_by_entity(ctx.session, EntityFlag.MUTATED)
    rng = ctx.rng("people_mutation")
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        if people.id in mutated or sanity_of(ctx.rules, people) >= creatures.people_mutation_sanity:
            continue
        if rng.chance(creatures.people_mutation_chance):
            return await split_changed_people(ctx, people)
    return None


async def hybridize(ctx: TickContext) -> EntityRow | None:
    rng = ctx.rng("hybrid")
    placed = [species for species in await _species(ctx) if species.location_id is not None]
    for index, first in enumerate(placed):
        for second in placed[index + 1 :]:
            if first.location_id != second.location_id or not rng.chance(ctx.rules.creatures.hybrid_chance):
                continue
            if await common_child(ctx.session, first.id, second.id):
                continue
            hybrid = await weave_chimera(
                ctx,
                first,
                second,
                name=f"{first.name.split()[0]} {second.name.split()[0]} Hybrid",
                description=f"{first.name} and {second.name} mixed over generations in the same lands and bore a hybrid.",
            )
            hybrid.subtype = "hybrid"
            await note(ctx, f"{first.name} and {second.name} hybridized.", key="creatures.hybrid", ids=[first.id, second.id, hybrid.id])
            return hybrid
    return None


async def _weaving_candidate(ctx: TickContext, atlas: RegionAtlas) -> tuple[EntityRow, EntityRow, EntityRow] | None:
    knowledge = await KnowledgeMap.load(ctx.session)
    megafauna = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    species = [item for item in await _species(ctx) if item.id not in megafauna]
    reach = ctx.rules.creatures.chimera_weave_distance
    for weaver in await canon(ctx.session, WEAVER_TYPES):
        if not knowledge.knows(weaver.id, KnowledgeBranch.BIOMANCY):
            continue
        near = sorted(
            (item for item in species if item.world_id == weaver.world_id and atlas.distance(weaver.id, item.id) <= reach),
            key=lambda item: (atlas.distance(weaver.id, item.id), item.id),
        )
        for index, first in enumerate(near):
            for second in near[index + 1 :]:
                if not await common_child(ctx.session, first.id, second.id):
                    return weaver, first, second
    return None


async def weave_spontaneously(ctx: TickContext) -> EntityRow | None:
    candidate = await _weaving_candidate(ctx, await RegionAtlas.load(ctx.session))
    if candidate is None or not ctx.rng("weave").chance(ctx.rules.creatures.chimera_weave_chance):
        return None
    weaver, first, second = candidate
    chimera = await weave_chimera(
        ctx, first, second, weaver=weaver, description=f"{weaver.name} joined {first.name} and {second.name} with biomancy and wove a chimera."
    )
    await BondRepository(ctx.session).connect(BondDraft(weaver.id, chimera.id, BondKind.TAMED, ctx.epoch, "its own weaving"))
    text = f"{weaver.name} wove a chimera from {first.name} and {second.name}: {chimera.name}."
    await ctx.chronicle(
        ChronicleKind.CHIMERA, text, template_key="creatures.chimera_woven", entity_ids=[weaver.id, chimera.id], feed_category=FeedCategory.LIFE
    )
    return chimera


async def chimera_escapes(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    repository = EntityRepository(ctx.session)
    escaped = await flags_by_entity(ctx.session, EntityFlag.ESCAPED)
    rng = ctx.rng("escape")
    count = 0
    for chimera in await repository.with_flag(EntityFlag.CHIMERA):
        if chimera.id in escaped:
            continue
        makers = await active_bonds(ctx.session, [BondKind.PRODUCED], targets=[chimera.id])
        if not makers or not rng.probability(stat_or(chimera, DANGER_KEY, creatures.chimera_default_danger) / creatures.chimera_escape_divisor):
            continue
        await repository.add_flag(chimera.id, EntityFlag.ESCAPED, ctx.epoch)
        weaver = await ctx.session.get(EntityRow, makers[0].source_node_id)
        if weaver is not None and weaver.status is EntityStatus.CANON:
            await BondRepository(ctx.session).connect(BondDraft(chimera.id, weaver.id, BondKind.HUNTS, ctx.epoch, "escaped and returned"))
            for key in (POPULATION_KEY, FOLLOWERS_KEY):
                scale_stat(ctx.rules, weaver, key, (PERCENT - creatures.chimera_escape_population_loss_pct) / PERCENT)
        await note(ctx, f"{chimera.name} got out of control and turned on those who wove it.", key="creatures.chimera_escaped", ids=[chimera.id])
        count += 1
    return count


async def megafauna_trail(ctx: TickContext, beast: EntityRow) -> EntityRow | None:
    creatures = ctx.rules.creatures
    if beast.location_id is None:
        return None
    rng = ctx.rng("trail")
    cosmic = await travel_resource(ctx.session) is not None
    trail = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{beast.name} Trail",
            entity_type=EntityType.RESOURCE,
            body=f"The ground changed where {beast.name} passed; a valuable and strange trail remained.",
            stats=ResourceStats(
                abundance=creatures.trace_abundance,
                value=clamp_percent(creatures.trace_value_base + rng.die(creatures.trace_value_die)),
                might=clamp_percent(creatures.trace_might_base + rng.die(creatures.trace_might_die)),
            ),
            power=creatures.trace_power,
            world_id=beast.world_id,
            location_id=beast.location_id,
            subtype="trail resource",
            engine_kind=EngineKind.COSMIC_TRAVEL_RESOURCE if cosmic else None,
        ),
    )
    await set_mechanics(ctx.session, trail, [ResourceMechanic.ADDICTIVE] if cosmic else [ResourceMechanic.DECAYING])
    await note(ctx, f"Where {beast.name} passed, a strange trail remained: {trail.name}.", key="creatures.megafauna_trail", ids=[beast.id, trail.id])
    return trail


async def megafauna(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    repository = EntityRepository(ctx.session)
    rng = ctx.rng("megafauna")
    tagged = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    trails = 0
    for beast in await _species(ctx):
        if beast.power_level < creatures.megafauna_min_power and beast.id not in tagged:
            continue
        if beast.id not in tagged:
            await repository.add_flag(beast.id, EntityFlag.MEGAFAUNA, ctx.epoch)
            await note(ctx, f"{beast.name} grew so large it is now as old and big as a world itself: a megafauna.", key="creatures.megafauna", ids=[beast.id])
        if beast.location_id is not None and rng.chance(creatures.megafauna_trace_chance):
            await megafauna_trail(ctx, beast)
            trails += 1
    return trails


async def _prey_for(
    ctx: TickContext, hunter: EntityRow, species: list[EntityRow], atlas: RegionAtlas, *, megafauna_ids: set[int], ranges: dict[int, dict[int, int]]
) -> EntityRow | None:
    margin = ctx.rules.creatures.predation_danger_margin
    hunter_danger = species_danger(ctx.rules, hunter)
    candidates = [
        prey
        for prey in species
        if prey.id != hunter.id
        and prey.world_id == hunter.world_id
        and prey.id not in megafauna_ids
        and (atlas.same_region(hunter.id, prey.id) or (hunter.location_id is not None and hunter.location_id == prey.location_id))
        and hunter_danger >= species_danger(ctx.rules, prey) + margin
        and stat_or(hunter, STRENGTH_KEY, 0) >= stat_or(prey, STRENGTH_KEY, 0)
    ]
    for prey in sorted(candidates, key=lambda prey: (species_danger(ctx.rules, prey), prey.id)):
        if await diet_allows(ctx, hunter, prey, ranges):
            return prey
    return None


async def predator_bonds(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    species = await _species(ctx)
    ids = {item.id for item in species}
    hunting = {bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.HUNTS]) if bond.target_node_id in ids}
    atlas = await RegionAtlas.load(ctx.session)
    megafauna_ids = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    rng = ctx.rng("predation")
    ranges = await regions_of(ctx)
    ctx.count("hunting_links_broken", await broken_links(ctx, species, ranges))
    formed = 0
    for hunter in species:
        if formed >= creatures.predation_link_cap:
            break
        if hunter.id in hunting:
            continue
        prey = await _prey_for(ctx, hunter, species, atlas, megafauna_ids=megafauna_ids, ranges=ranges)
        if prey is None or not rng.chance(creatures.predation_link_chance):
            continue
        await form_link(ctx, hunter, prey)
        await note(ctx, f"{hunter.name} began hunting the herds of {prey.name}.", key="creatures.predation", ids=[hunter.id, prey.id])
        formed += 1
    return formed


async def _hunt_pairs(ctx: TickContext) -> list[tuple[BondRow, EntityRow, EntityRow]]:
    pairs: list[tuple[BondRow, EntityRow, EntityRow]] = []
    for bond in await active_bonds(ctx.session, [BondKind.HUNTS]):
        hunter = await ctx.session.get(EntityRow, bond.source_node_id)
        prey = await ctx.session.get(EntityRow, bond.target_node_id)
        if hunter is not None and prey is not None and hunter.entity_type is EntityType.SPECIES and prey.entity_type is EntityType.SPECIES:
            pairs.append((bond, hunter, prey))
    return pairs


async def predation_pressure(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    rng = ctx.rng("depletion")
    extinct = 0
    for _bond, hunter, prey in await _hunt_pairs(ctx):
        if hunter.status is not EntityStatus.CANON or prey.status is not EntityStatus.CANON:
            continue
        gap = species_danger(ctx.rules, hunter) - species_danger(ctx.rules, prey)
        if gap < creatures.depletion_danger_margin or prey.power_level > creatures.depletion_max_prey_power or not rng.chance(creatures.prey_depletion_chance):
            continue
        await retire(ctx.session, prey, ctx.epoch, f"Epoch {ctx.epoch}: {hunter.name} consumed it.")
        await note(ctx, f"{prey.name} became extinct as {hunter.name}'s prey.", key="creatures.prey_extinct", ids=[hunter.id, prey.id])
        extinct += 1
    return extinct


async def danger_reversion(ctx: TickContext) -> None:
    creatures = ctx.rules.creatures
    megafauna_ids = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    for species in await _species(ctx):
        danger = stat(species, DANGER_KEY)
        if species.id in megafauna_ids or danger is None or danger <= creatures.danger_reversion_threshold:
            continue
        put_stat(ctx.rules, species, DANGER_KEY, danger - max(1, round((danger - creatures.danger_reversion_mean) / creatures.danger_reversion_divisor)))


async def starving_predators(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    starved = 0
    for bond, hunter, prey in await _hunt_pairs(ctx):
        if hunter.status is not EntityStatus.CANON or prey.status is EntityStatus.CANON:
            continue
        await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "prey extinct")
        put_stat(ctx.rules, hunter, DANGER_KEY, species_danger(ctx.rules, hunter) + creatures.starving_predator_danger)
        await note(
            ctx,
            f"{prey.name} went extinct; {hunter.name}, which hunted it, starved and turned on the settlements.",
            key="creatures.starving",
            ids=[hunter.id, prey.id],
        )
        starved += 1
    return starved


async def invasive_pressure(ctx: TickContext) -> None:
    loss = ctx.rules.creatures.invasive_fertility_loss
    for species in await EntityRepository(ctx.session).with_flag(EntityFlag.INVASIVE):
        location = await _location(ctx, species)
        if location is not None:
            shift_bounded(ctx.rules, location, FERTILITY_KEY, -loss)


@reads(
    "place.danger",
    "place.fertility",
    "region.danger",
    "region.fertility",
    "species.agility",
    "species.danger",
    "species.hp",
    "species.intelligence",
    "species.might",
    "species.strength",
    "table.bonds",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.name_registry",
    "table.nodes",
    "table.world_maps",
)
@writes(
    "place.danger",
    "place.fertility",
    "region.danger",
    "region.fertility",
    "species.danger",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
)
@reads(
    "place.danger",
    "place.fertility",
    "region.danger",
    "region.fertility",
    "species.agility",
    "species.danger",
    "species.hp",
    "species.intelligence",
    "species.might",
    "species.strength",
)
@writes("place.danger", "place.fertility", "region.danger", "region.fertility", "species.danger")
async def creature_phase(ctx: TickContext) -> None:
    for species in await _species(ctx):
        await assign_traits(ctx, species)
    for species in await _species(ctx):
        await trait_effects(ctx, species)
    await species_mutations(ctx)
    await people_mutation(ctx)
    await hybridize(ctx)
    await weave_spontaneously(ctx)
    await chimera_escapes(ctx)
    await megafauna(ctx)
    await predator_bonds(ctx)
    await predation_pressure(ctx)
    await danger_reversion(ctx)
    await starving_predators(ctx)
    await invasive_pressure(ctx)
    await ctx.session.flush()


async def creature_migration(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    atlas = await RegionAtlas.load(ctx.session)
    rng = ctx.rng("creature_migration")
    moved = 0
    for species in await _species(ctx):
        if moved >= creatures.creature_migration_cap or species_danger(ctx.rules, species) < creatures.creature_migration_min_danger:
            continue
        chance = creatures.creature_migration_chance * (2 if CreatureTrait.FISSIPAROUS in await traits_of(ctx.session, species.id) else 1)
        if not rng.chance(chance):
            continue
        home = atlas.top_region(species.id)
        living = {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[species.id])}
        targets = [region for region in (atlas.neighbour_regions(home) if home is not None else []) if region not in living and not atlas.is_water(region)]
        if not targets:
            continue
        target = await ctx.session.get(EntityRow, targets[0])
        if target is None or target.status is not EntityStatus.CANON:
            continue
        await BondRepository(ctx.session).connect(BondDraft(species.id, target.id, BondKind.LIVES_IN, ctx.epoch, f"Epoch {ctx.epoch} migration"))
        source = await ctx.session.get(EntityRow, home) if home is not None else None
        origin = source.name if source is not None else "its lands"
        await note(
            ctx,
            f"Herds of {species.name} spilled out of {origin} and spread into the lands of {target.name}.",
            key="creatures.migration",
            ids=[species.id, target.id],
        )
        moved += 1
    return moved


async def _worshipper_of(ctx: TickContext, son_id: int, world_id: int) -> EntityRow | None:
    bonds = BondRepository(ctx.session)
    for community in await canon(ctx.session, [EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT], world_id):
        if await bonds.patron(community.id) == son_id:
            return community
    return None


async def creature_rebellion(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    rng = ctx.rng("creature_revolt")
    risen = 0
    for species in await _species(ctx):
        if species.creator_son_id is None:
            continue
        if (
            stat_or(species, "intelligence", 0) < creatures.creature_revolt_min_intelligence
            or species_danger(ctx.rules, species) < creatures.creature_revolt_min_danger
        ):
            continue
        if not rng.chance(ctx.rules.creatures.creature_revolt_chance):
            continue
        son = await SonRepository(ctx.session).get(species.creator_son_id)
        if son is None:
            continue
        await BondRepository(ctx.session).connect(
            BondDraft(species.id, son.id, BondKind.ENEMY, ctx.epoch, "rebellion against its creator", war_cause=WarCause.INDEPENDENCE)
        )
        victim = await _worshipper_of(ctx, son.id, species.world_id)
        if victim is not None:
            for key in (POPULATION_KEY, FOLLOWERS_KEY):
                scale_stat(ctx.rules, victim, key, creatures.creature_revolt_population_kept_pct / PERCENT)
        son.existence = max(0, son.existence - creatures.creature_revolt_son_existence_loss)
        attacked = f"; it attacked {victim.name} who worship them" if victim is not None else ""
        await note(ctx, f"{species.name} rose up against its creator {son.name}{attacked}.", key="creatures.rebellion", ids=[species.id], son_id=son.id)
        risen += 1
    return risen


async def speciation(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    rng = ctx.rng("speciation")
    born = 0
    for species in await _species(ctx):
        if born >= creatures.speciation_cap:
            break
        homes = [
            bond
            for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[species.id])
            if bond.epoch <= ctx.epoch - creatures.speciation_min_epochs
        ]
        if not homes or not rng.chance(ctx.rules.creatures.speciation_chance):
            continue
        bond = min(homes, key=lambda item: (item.epoch, item.id))
        home = await ctx.session.get(EntityRow, bond.target_node_id)
        if home is None or home.status is not EntityStatus.CANON:
            continue
        await _branch_subspecies(ctx, species, home, bond)
        born += 1
    return born


async def _branch_subspecies(ctx: TickContext, species: EntityRow, home: EntityRow, bond: BondRow) -> EntityRow:
    deviation = ctx.rules.creatures.speciation_stat_deviation
    rng = ctx.rng("subspecies")
    stats = species.stats
    if isinstance(stats, SpeciesStats):
        changes = {
            key: clamp_percent(stat_or(species, key, 0) + rng.die(2 * deviation + 1) - deviation - 1)
            for key in SPECIES_STAT_KEYS
            if stat(species, key) is not None
        }
        stats = stats.model_copy(update=changes)
    child = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{home.name} {species.name}",
            entity_type=EntityType.SPECIES,
            body=f"Over generations in the lands of {home.name}, {species.name} changed into a distinct subspecies.",
            stats=stats,
            power=species.power_level,
            world_id=home.world_id,
            location_id=home.id,
            subtype="subspecies",
            traits=sorted(await traits_of(ctx.session, species.id)),
        ),
    )
    bonds = BondRepository(ctx.session)
    await adapt_subspecies(ctx, species, child, home.id)
    await bonds.connect(BondDraft(child.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, "evolution"))
    await bonds.deactivate(bond, ctx.epoch, "speciation")
    await note(
        ctx, f"{species.name} diverged into a new subspecies in the lands of {home.name}.", key="creatures.speciation", ids=[species.id, child.id, home.id]
    )
    return child


async def _require_species(session: AsyncSession, entity_id: int) -> EntityRow:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or entity.entity_type is not EntityType.SPECIES or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such living species.")
    return entity


async def order_feeding(session: AsyncSession, rules: Rules, species_id: int, soul_id: int | None = None) -> EntityRow:
    ctx = await manual_context(session, "feed", rules, key=str(species_id))
    species = await _require_species(session, species_id)
    if CreatureTrait.SOUL_EATER not in await traits_of(session, species.id):
        raise ValidationFailedError(f"{species.name} does not feed on souls.")
    location = await _location(ctx, species)
    souls = await edible_souls(ctx, location) if location is not None else []
    chosen = next((soul for soul in souls if soul_id is None or soul.id == soul_id), None)
    if chosen is None:
        raise ValidationFailedError(f"No unspared soul lingers where {species.name} lives.")
    return await swallow_soul(ctx, species, chosen)


async def spare_soul(session: AsyncSession, rules: Rules, soul_id: int, spared: bool = True) -> bool:
    ctx = await manual_context(session, "spare_soul", rules, key=str(soul_id))
    soul = await session.get(EntityRow, soul_id)
    if soul is None or soul.entity_type is not EntityType.SPIRIT or soul.status is not EntityStatus.CANON:
        raise NotFoundError("No such lingering soul.")
    repository = EntityRepository(session)
    if not spared:
        return await repository.remove_flag(soul.id, EntityFlag.SPARED_SOUL)
    changed = await repository.add_flag(soul.id, EntityFlag.SPARED_SOUL, ctx.epoch)
    if changed:
        await note(ctx, f"The Creator spared {soul.name}; no hunger may swallow it.", key="creatures.soul_spared", ids=[soul.id])
    return changed


async def force_mutation(session: AsyncSession, rules: Rules, species_id: int) -> EntityRow:
    ctx = await manual_context(session, "mutation", rules, key=str(species_id))
    species = await _require_species(session, species_id)
    world = await session.get(WorldRow, species.world_id)
    return await mutate_species(ctx, species, world.leakage if world is not None else 0)


async def force_people_split(session: AsyncSession, rules: Rules, people_id: int) -> EntityRow:
    ctx = await manual_context(session, "people_split", rules, key=str(people_id))
    people = await session.get(EntityRow, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE or people.status is not EntityStatus.CANON:
        raise NotFoundError("No such living people.")
    return await split_changed_people(ctx, people)


async def cross_species(session: AsyncSession, rules: Rules, first_id: int, second_id: int, weaver_id: int | None = None) -> EntityRow:
    if first_id == second_id:
        raise ValidationFailedError("A chimera needs two different species.")
    ctx = await manual_context(session, "chimera", rules, key=f"{first_id}:{second_id}")
    first, second = await _require_species(session, first_id), await _require_species(session, second_id)
    weaver = await session.get(EntityRow, weaver_id) if weaver_id is not None else None
    chimera = await weave_chimera(ctx, first, second, weaver=weaver)
    if weaver is not None:
        await BondRepository(session).connect(BondDraft(weaver.id, chimera.id, BondKind.TAMED, ctx.epoch, "its own weaving"))
    return chimera


async def place_megafauna_trail(session: AsyncSession, rules: Rules, species_id: int) -> EntityRow | None:
    ctx = await manual_context(session, "trail", rules, key=str(species_id))
    return await megafauna_trail(ctx, await _require_species(session, species_id))


async def cull_species(session: AsyncSession, rules: Rules, species_id: int, reason: str) -> EntityRow:
    ctx = await manual_context(session, "cull", rules, key=str(species_id))
    species = await _require_species(session, species_id)
    return await retire(session, species, ctx.epoch, f"Epoch {ctx.epoch}: {reason}.", close_bonds=True)


async def spare_prey(session: AsyncSession, species_id: int, epoch: int) -> int:
    closed = 0
    bonds = BondRepository(session)
    for bond in await bonds.incoming(species_id, BondKind.HUNTS):
        await bonds.deactivate(bond, epoch, "spared by the creator")
        closed += 1
    return closed


async def introduce_species(session: AsyncSession, rules: Rules, species_id: int, region_id: int) -> EntityRow:
    ctx = await manual_context(session, "introduce", rules, key=f"{species_id}:{region_id}")
    species = await _require_species(session, species_id)
    region = await session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION or region.status is not EntityStatus.CANON:
        raise NotFoundError("No such region.")
    carried = await open_record(
        session,
        ctx.epoch,
        RecordSpec(
            name=f"{species.name} (stowaway)",
            entity_type=EntityType.SPECIES,
            body=f"{species.name} was carried to {region.name} and became a non-native invader there.",
            stats=species.stats,
            power=species.power_level,
            world_id=region.world_id,
            location_id=region.id,
            subtype="invasive species",
            flags=(EntityFlag.INVASIVE,),
            traits=sorted(await traits_of(session, species.id)),
        ),
    )
    await BondRepository(session).connect(BondDraft(carried.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, "introduced"))
    return carried


async def run_creature_phase(session: AsyncSession, rules: Rules) -> None:
    await creature_phase(await manual_context(session, "creatures", rules))


@reads("species.danger", "table.bonds", "table.entity_traits", "table.epoch_year_cursors", "table.nodes", "table.world_maps")
@writes("table.bonds", "table.chronicle", "table.chronicle_entities", "table.epoch_year_cursors", "table.incident_participants", "table.incidents")
@reads("species.danger")
async def creature_migration_phase(ctx: TickContext) -> None:
    await creature_migration(ctx)


@reads("species.danger", "species.intelligence")
@reads("species.danger", "species.intelligence")
async def creature_rebellion_phase(ctx: TickContext) -> None:
    await creature_rebellion(ctx)


@reads(
    "species.agility",
    "species.danger",
    "species.intelligence",
    "species.strength",
    "table.bonds",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.name_registry",
    "table.nodes",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
)
@reads("species.agility", "species.danger", "species.intelligence", "species.strength")
async def speciation_phase(ctx: TickContext) -> None:
    await speciation(ctx)


PHASES = (
    Phase("creatures", creature_phase),
    Phase("creature_migration", creature_migration_phase),
    Phase("creature_rebellion", creature_rebellion_phase),
    Phase("speciation", speciation_phase),
)
