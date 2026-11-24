from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, ResourceMechanic
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import PeopleStats, ResourceStats, SpeciesStats, revised
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import (
    BESTOWED,
    DANGER_KEY,
    SPECIES_STAT_KEYS,
    common_child,
    merge_species,
    species_danger,
    traits_of,
)
from aerona.engine.cosmos.resources import set_mechanics, travel_resource
from aerona.engine.cosmos.sanity import sanity_of, shift_sanity
from aerona.engine.cosmos.worldlife import radiation_mutation
from aerona.engine.ecology.biochemistry import can_live_on
from aerona.engine.ecology.evolution import apart, inherit_traits, settle_size
from aerona.engine.ecology.foodweb import derive_links
from aerona.engine.ecology.profiles import assign_traits
from aerona.engine.ecology.ranges import adapt_subspecies
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent, scaled_cap
from aerona.engine.primitives.queries import active_bonds, canon, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.stats import FOLLOWERS_KEY, POPULATION_KEY, put_stat, scale_stat, shift_bounded, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.space_weather.reading import dose_mutation
from aerona.rules.registry import Rules

VICTIM_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL})
MAKER_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
FERTILITY_KEY = "fertility"
MARTIALITY_KEY = "martiality"
MAGIC_KEY = "magic"


async def _species(ctx: TickContext) -> list[EntityRow]:
    return unheld(await canon(ctx.session, [EntityType.SPECIES]))


async def _location(ctx: TickContext, species: EntityRow) -> EntityRow | None:
    return await ctx.session.get(EntityRow, species.location_id) if species.location_id is not None else None


async def edible_souls(ctx: TickContext, location: EntityRow) -> list[EntityRow]:
    spared = await flags_by_entity(ctx.session, EntityFlag.SPARED_SOUL)
    contents = await EntityRepository(ctx.session).contents(location.id)
    return [item for item in contents if item.entity_type is EntityType.SPIRIT and item.status is EntityStatus.CANON and item.id not in spared]


async def swallow_soul(ctx: TickContext, species: EntityRow, soul: EntityRow) -> EntityRow:
    await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: {species.name} swallowed it.")
    await record(
        ctx,
        "creatures.soul_eaten",
        roles={IncidentRole.ACTOR: species.id, IncidentRole.VICTIM: soul.id, IncidentRole.PLACE: soul.location_id},
        place=soul.location_id,
    )
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
    field = await ctx.session.get(WorldFieldRow, species.world_id) if species.world_id is not None else None
    return chance + radiation_mutation(ctx.rules, await ctx.session.get(WorldRow, species.world_id)) + dose_mutation(ctx.rules, field)


async def mutate_species(ctx: TickContext, species: EntityRow, leak: int, chance: float) -> EntityRow:
    creatures = ctx.rules.creatures
    rng = ctx.rng("mutation")
    owned = await traits_of(ctx.session, species.id)
    fresh = [trait for trait in CreatureTrait if trait not in owned and trait not in BESTOWED]
    new_trait = rng.pick_or_none(fresh)
    stats = species.stats
    if isinstance(stats, SpeciesStats):
        changes = {
            key: clamp_percent(stat_or(species, key, creatures.merged_default_stat) + rng.die(creatures.mutation_die) - creatures.mutation_shift)
            for key in SPECIES_STAT_KEYS
        }
        stats = revised(stats, changes)
    cause = "what leaked in from outside" if leak >= creatures.mutation_leak_text_threshold else "curse and magic"
    born = f": {spoken(new_trait)}" if new_trait is not None else ""
    mutant = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{species.name} Corruption",
            entity_type=EntityType.SPECIES,
            body=f"{species.name} changed under {cause}; a new form was born{born}.",
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
    await record(
        ctx,
        "creatures.mutation",
        roles={IncidentRole.SUBJECT: species.id, IncidentRole.PRODUCT: mutant.id},
        facts={"cause": cause, "trait": new_trait, "leak": leak, "chance": chance},
    )
    return mutant


async def species_mutations(ctx: TickContext) -> int:
    every = await _species(ctx)
    cap = scaled_cap(ctx.rules.creatures.mutation_cap, ctx.rules.creatures.cap_species_divisor, len(every))
    leaks = {world.id: world.leakage for world in await ctx.session.scalars(select(WorldRow))}
    repository = EntityRepository(ctx.session)
    mutated = 0
    rng = ctx.rng("mutation_roll")
    for species in ctx.rng("mutation_order").shuffled(every):
        if mutated >= cap:
            break
        flags = await repository.flags(species.id)
        if EntityFlag.MUTATED in flags:
            continue
        chance = await _mutation_chance(ctx, species, leaks, flags)
        if rng.probability(chance):
            await mutate_species(ctx, species, leaks.get(species.world_id, 0), chance * PERCENT)
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
    await record(
        ctx,
        "creatures.people_mutation",
        roles={IncidentRole.SUBJECT: people.id, IncidentRole.PRODUCT: changed.id},
        facts={"count": max(1, round(population * creatures.people_mutation_share_pct / PERCENT)), "share": creatures.people_mutation_share_pct},
    )
    return changed


async def people_mutation(ctx: TickContext) -> EntityRow | None:
    creatures = ctx.rules.creatures
    mutated = await flags_by_entity(ctx.session, EntityFlag.MUTATED)
    rng = ctx.rng("people_mutation")
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        if people.id in mutated or held(people.id) or sanity_of(ctx.rules, people) >= creatures.people_mutation_sanity:
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
            hybrid = await merge_species(
                ctx,
                first,
                second,
                name=f"{first.name.split()[0]} {second.name.split()[0]} Hybrid",
                description=f"{first.name} and {second.name} mixed over generations in the same lands and bore a hybrid.",
            )
            hybrid.subtype = "hybrid"
            await record(
                ctx,
                "creatures.hybrid",
                roles={IncidentRole.ACTOR: first.id, IncidentRole.CO_ACTOR: second.id, IncidentRole.PRODUCT: hybrid.id, IncidentRole.PLACE: first.location_id},
                facts={"chance": ctx.rules.creatures.hybrid_chance},
                place=first.location_id,
            )
            return hybrid
    return None


async def _weaving_candidate(ctx: TickContext, atlas: RegionAtlas) -> tuple[EntityRow, EntityRow, EntityRow] | None:
    knowledge = await KnowledgeMap.load(ctx.session)
    megafauna = await flags_by_entity(ctx.session, EntityFlag.MEGAFAUNA)
    species = [item for item in await _species(ctx) if item.id not in megafauna]
    reach = ctx.rules.creatures.species_merge_distance
    for maker in await canon(ctx.session, MAKER_TYPES):
        if not knowledge.knows(maker.id, KnowledgeBranch.BIOMANCY):
            continue
        near = sorted(
            (item for item in species if item.world_id == maker.world_id and atlas.distance(maker.id, item.id) <= reach),
            key=lambda item: (atlas.distance(maker.id, item.id), item.id),
        )
        for index, first in enumerate(near):
            for second in near[index + 1 :]:
                if not await common_child(ctx.session, first.id, second.id):
                    return maker, first, second
    return None


async def merge_spontaneously(ctx: TickContext) -> EntityRow | None:
    candidate = await _weaving_candidate(ctx, await RegionAtlas.load(ctx.session))
    if candidate is None or not ctx.rng("weave").chance(ctx.rules.creatures.species_merge_chance):
        return None
    maker, first, second = candidate
    merged = await merge_species(
        ctx, first, second, maker=maker, description=f"{maker.name} joined {first.name} and {second.name} with biomancy into a new species."
    )
    await BondRepository(ctx.session).connect(BondDraft(maker.id, merged.id, BondKind.TAMED, ctx.epoch, "its own making"))
    await record(
        ctx,
        "creatures.species_merged",
        roles={IncidentRole.MAKER: maker.id, IncidentRole.ACTOR: first.id, IncidentRole.CO_ACTOR: second.id, IncidentRole.PRODUCT: merged.id},
        facts={"chance": ctx.rules.creatures.species_merge_chance},
    )
    return merged


async def merged_escapes(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    repository = EntityRepository(ctx.session)
    escaped = await flags_by_entity(ctx.session, EntityFlag.ESCAPED)
    rng = ctx.rng("escape")
    count = 0
    for merged in await repository.with_flag(EntityFlag.MERGED_SPECIES):
        if merged.id in escaped:
            continue
        makers = await active_bonds(ctx.session, [BondKind.PRODUCED], targets=[merged.id])
        if not makers or not rng.probability(stat_or(merged, DANGER_KEY, creatures.merged_default_danger) / creatures.merged_escape_divisor):
            continue
        await repository.add_flag(merged.id, EntityFlag.ESCAPED, ctx.epoch)
        maker = await ctx.session.get(EntityRow, makers[0].source_node_id)
        if maker is not None and maker.status is EntityStatus.CANON:
            await BondRepository(ctx.session).connect(BondDraft(merged.id, maker.id, BondKind.HUNTS, ctx.epoch, "escaped and returned"))
            for key in (POPULATION_KEY, FOLLOWERS_KEY):
                scale_stat(ctx.rules, maker, key, (PERCENT - creatures.merged_escape_population_loss_pct) / PERCENT)
        await record(
            ctx,
            "creatures.merged_escaped",
            roles={IncidentRole.ACTOR: merged.id, IncidentRole.VICTIM: maker.id if maker is not None and maker.status is EntityStatus.CANON else None},
            facts={"loss": creatures.merged_escape_population_loss_pct, "danger": stat_or(merged, DANGER_KEY, creatures.merged_default_danger)},
        )
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
            body=f"The ground changed where {beast.name} passed; a trail of value remained.",
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
    await set_resource_yield(ctx.session, ctx.rules, trail.id, CommodityKind.MAGICAL_REAGENTS)
    await record(
        ctx,
        "creatures.megafauna_trail",
        roles={IncidentRole.SUBJECT: beast.id, IncidentRole.PRODUCT: trail.id, IncidentRole.PLACE: beast.location_id},
        facts={"value": stat_or(trail, "value", 0), "might": stat_or(trail, "might", 0)},
        place=beast.location_id,
    )
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
            await record(ctx, "creatures.megafauna", roles={IncidentRole.SUBJECT: beast.id}, facts={"power": beast.power_level})
        if beast.location_id is not None and rng.chance(creatures.megafauna_trace_chance):
            await megafauna_trail(ctx, beast)
            trails += 1
    return trails


async def predator_bonds(ctx: TickContext) -> int:
    species = await _species(ctx)
    change = await derive_links(ctx, species)
    ctx.count("hunting_links_broken", change.broken)
    known = {item.id for item in species}
    for hunter_id, prey_ids in sorted(change.formed.items()):
        prey = sorted(item for item in prey_ids if item in known)
        if hunter_id in known and prey:
            await record(ctx, "creatures.predation", roles={IncidentRole.ACTOR: hunter_id, IncidentRole.TARGET: prey})
    return sum(len(items) for items in change.formed.values())


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
        if hunter.status is not EntityStatus.CANON or prey.status is not EntityStatus.CANON or held(hunter.id, prey.id):
            continue
        gap = species_danger(ctx.rules, hunter) - species_danger(ctx.rules, prey)
        if gap < creatures.depletion_danger_margin or prey.power_level > creatures.depletion_max_prey_power or not rng.chance(creatures.prey_depletion_chance):
            continue
        await retire(ctx.session, prey, ctx.epoch, f"Epoch {ctx.epoch}: {hunter.name} consumed it.")
        await record(
            ctx,
            "creatures.prey_extinct",
            roles={IncidentRole.ACTOR: hunter.id, IncidentRole.VICTIM: prey.id},
            facts={"gap": gap, "chance": creatures.prey_depletion_chance},
        )
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
        await record(
            ctx,
            "creatures.starving",
            roles={IncidentRole.ACTOR: hunter.id, IncidentRole.SUBJECT: prey.id},
            facts={"danger": species_danger(ctx.rules, hunter)},
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
    "table.applied_fixups",
    "table.bodies",
    "table.bonds",
    "table.creator",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.entity_traits",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.polity_profiles",
    "table.region_environment",
    "table.sons",
    "table.species_products",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_uses",
    "table.stars",
    "table.world_biochemistries",
    "table.world_fields",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "place.danger",
    "place.fertility",
    "region.danger",
    "region.fertility",
    "species.danger",
    "species.intelligence",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.entity_traits",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.plant_profiles",
    "table.species_products",
    "table.species_profiles",
    "table.species_uses",
)
async def creature_phase(ctx: TickContext) -> None:
    for species in await _species(ctx):
        await assign_traits(ctx, species)
    for species in await _species(ctx):
        await trait_effects(ctx, species)
    await species_mutations(ctx)
    await people_mutation(ctx)
    await hybridize(ctx)
    await merge_spontaneously(ctx)
    await merged_escapes(ctx)
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
    every = await _species(ctx)
    limit = scaled_cap(creatures.creature_migration_cap, creatures.cap_species_divisor, len(every))
    for species in ctx.rng("creature_migration_order").shuffled(unheld(every)):
        if moved >= limit or species_danger(ctx.rules, species) < creatures.creature_migration_min_danger:
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
        if target is None or target.status is not EntityStatus.CANON or held(target.id):
            continue
        await BondRepository(ctx.session).connect(BondDraft(species.id, target.id, BondKind.LIVES_IN, ctx.epoch, f"Epoch {ctx.epoch} migration"))
        await record(
            ctx,
            "creatures.migration",
            roles={IncidentRole.SUBJECT: species.id, IncidentRole.ORIGIN: home, IncidentRole.DESTINATION: target.id},
            facts={"chance": chance},
            origin=home,
            destination=target.id,
            steps=(
                StepDraft(StepAction.DEPART, actor=species.id, locus_kind=StepLocus.REGION, locus_node=home),
                StepDraft(StepAction.MIGRATE, actor=species.id, locus_kind=StepLocus.REGION, locus_node=target.id),
                StepDraft(StepAction.ARRIVE, actor=species.id, locus_kind=StepLocus.REGION, locus_node=target.id),
            ),
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
        await record(
            ctx,
            "creatures.rebellion",
            roles={IncidentRole.ACTOR: species.id, IncidentRole.TARGET: son.id, IncidentRole.VICTIM: victim.id if victim is not None else None},
            facts={"kept": creatures.creature_revolt_population_kept_pct, "existence_loss": creatures.creature_revolt_son_existence_loss},
            son_id=son.id,
        )
        risen += 1
    return risen


def isolated(atlas: RegionAtlas, region_id: int, lands: set[int]) -> bool:
    return not set(atlas.neighbour_regions(region_id)) & (lands - {region_id})


def unlike(rules: Rules, home: RegionEnvironmentRow | None, land: RegionEnvironmentRow | None) -> bool:
    if home is None or land is None:
        return False
    return land.dominant_terrain is not home.dominant_terrain or abs(land.temperature - home.temperature) >= rules.habitat.subspecies_gap


async def drifting_range(ctx: TickContext, atlas: RegionAtlas, species: EntityRow) -> SpeciesRangeRow | None:
    rows = list(
        await ctx.session.scalars(
            select(SpeciesRangeRow)
            .where(SpeciesRangeRow.species_entity_id == species.id, SpeciesRangeRow.abundance > 0)
            .order_by(SpeciesRangeRow.region_entity_id)
        )
    )
    if len(rows) < 2:
        return None
    home = max(rows, key=lambda row: (row.abundance, -row.region_entity_id))
    home_land = await ctx.session.get(RegionEnvironmentRow, home.region_entity_id)
    lands = {row.region_entity_id for row in rows}
    old = ctx.epoch - ctx.rules.creatures.speciation_min_epochs
    for row in sorted(rows, key=lambda item: (item.since_epoch, item.region_entity_id)):
        if row is home or row.since_epoch > old or not isolated(atlas, row.region_entity_id, lands):
            continue
        if unlike(ctx.rules, home_land, await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)) or await apart(
            ctx.session, ctx.rules, species.id, row.region_entity_id
        ):
            return row
    return None


async def speciation(ctx: TickContext) -> int:
    creatures = ctx.rules.creatures
    rng = ctx.rng("speciation")
    atlas = await RegionAtlas.load(ctx.session)
    born = 0
    every = await _species(ctx)
    limit = scaled_cap(creatures.speciation_cap, creatures.cap_species_divisor, len(every))
    for species in ctx.rng("speciation_order").shuffled(unheld(every)):
        if born >= limit:
            break
        row = await drifting_range(ctx, atlas, species)
        if row is None or not rng.chance(creatures.speciation_chance):
            continue
        region = await ctx.session.get(EntityRow, row.region_entity_id)
        if region is None or held(region.id) or region.status is not EntityStatus.CANON or region.entity_type is not EntityType.REGION:
            continue
        await _branch_subspecies(ctx, species, region)
        born += 1
    return born


async def _branch_subspecies(ctx: TickContext, species: EntityRow, home: EntityRow) -> EntityRow:
    deviation = ctx.rules.creatures.speciation_stat_deviation
    rng = ctx.rng("subspecies")
    stats = species.stats
    if isinstance(stats, SpeciesStats):
        changes = {
            key: clamp_percent(stat_or(species, key, 0) + rng.die(2 * deviation + 1) - deviation - 1)
            for key in SPECIES_STAT_KEYS
            if stat(species, key) is not None
        }
        stats = revised(stats, changes)
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
    await bonds.connect(BondDraft(child.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, "evolution"))
    await adapt_subspecies(ctx, species, child, home.id)
    await inherit_traits(ctx.session, species.id, child.id, home.id, ctx.epoch)
    await ctx.session.flush()
    await settle_size(ctx.session, child.id, home.id)
    for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[species.id], targets=[home.id]):
        await bonds.deactivate(bond, ctx.epoch, "speciation")
    await record(
        ctx,
        "creatures.speciation",
        roles={IncidentRole.SUBJECT: species.id, IncidentRole.PRODUCT: child.id, IncidentRole.PLACE: home.id},
        place=home.id,
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
        creator = await session.scalar(select(CreatorRow.id).limit(1))
        await record(ctx, "creatures.soul_spared", roles={IncidentRole.AUTHORITY: creator, IncidentRole.SUBJECT: soul.id})
    return changed


async def force_mutation(session: AsyncSession, rules: Rules, species_id: int) -> EntityRow:
    ctx = await manual_context(session, "mutation", rules, key=str(species_id))
    species = await _require_species(session, species_id)
    world = await session.get(WorldRow, species.world_id)
    return await mutate_species(ctx, species, world.leakage if world is not None else 0, PERCENT)


async def force_people_split(session: AsyncSession, rules: Rules, people_id: int) -> EntityRow:
    ctx = await manual_context(session, "people_split", rules, key=str(people_id))
    people = await session.get(EntityRow, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE or people.status is not EntityStatus.CANON:
        raise NotFoundError("No such living people.")
    return await split_changed_people(ctx, people)


async def cross_species(session: AsyncSession, rules: Rules, first_id: int, second_id: int, maker_id: int | None = None) -> EntityRow:
    if first_id == second_id:
        raise ValidationFailedError("Merging needs two different species.")
    ctx = await manual_context(session, "merged_species", rules, key=f"{first_id}:{second_id}")
    first, second = await _require_species(session, first_id), await _require_species(session, second_id)
    maker = await session.get(EntityRow, maker_id) if maker_id is not None else None
    merged = await merge_species(ctx, first, second, maker=maker)
    if maker is not None:
        await BondRepository(session).connect(BondDraft(maker.id, merged.id, BondKind.TAMED, ctx.epoch, "its own making"))
    return merged


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
        hunter = await session.get(SpeciesProfileRow, bond.source_node_id)
        if hunter is not None:
            hunter.barred_prey = sorted({*hunter.barred_prey, species_id})
            hunter.pinned_prey = [prey for prey in hunter.pinned_prey if prey != species_id]
        closed += 1
    return closed


async def introduce_species(session: AsyncSession, rules: Rules, species_id: int, region_id: int) -> EntityRow:
    ctx = await manual_context(session, "introduce", rules, key=f"{species_id}:{region_id}")
    species = await _require_species(session, species_id)
    region = await session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION or region.status is not EntityStatus.CANON:
        raise NotFoundError("No such region.")
    if not await can_live_on(session, species.id, region.world_id):
        raise ValidationFailedError(f"{species.name} cannot live there: that world does not bear its kind of life.")
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


@reads(
    "species.danger",
    "table.bonds",
    "table.creator",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.entity_traits",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.node_births",
    "table.nodes",
    "table.sons",
    "table.stars",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
)
async def creature_migration_phase(ctx: TickContext) -> None:
    await creature_migration(ctx)


@reads("species.danger", "species.intelligence")
@writes(
    "cult.followers",
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_participants",
    "table.incidents",
    "table.sons",
)
async def creature_rebellion_phase(ctx: TickContext) -> None:
    await creature_rebellion(ctx)


@reads(
    "species.agility",
    "species.danger",
    "species.intelligence",
    "species.strength",
    "table.bonds",
    "table.entity_traits",
    "table.name_registry",
    "table.nodes",
    "table.region_environment",
    "table.species_products",
    "table.species_profiles",
    "table.species_ranges",
    "table.world_maps",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_traits",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.species_products",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_uses",
)
async def speciation_phase(ctx: TickContext) -> None:
    await speciation(ctx)


PHASES = (
    Phase("creatures", creature_phase),
    Phase("creature_migration", creature_migration_phase),
    Phase("creature_rebellion", creature_rebellion_phase),
    Phase("speciation", speciation_phase),
)
