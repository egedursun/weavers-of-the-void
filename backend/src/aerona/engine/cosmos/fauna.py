from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.creatures import trait_war_bonus
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.biochemistry import can_live_on
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import stat, stat_or
from aerona.rules.registry import Rules

SPECIES_STAT_KEYS = ("strength", "agility", "intelligence", "danger")
STRENGTH_KEY = "strength"
INTELLIGENCE_KEY = "intelligence"
DANGER_KEY = "danger"
HP_KEY = "hp"

BESTOWED = frozenset({CreatureTrait.SACRED_ANIMAL})


async def traits_of(session: AsyncSession, entity_id: int) -> set[CreatureTrait]:
    return await EntityRepository(session).traits(entity_id)


def trait_war(rules: Rules, traits: Iterable[CreatureTrait]) -> int:
    return sum(trait_war_bonus(rules, trait) for trait in traits)


async def common_child(session: AsyncSession, first: int, second: int) -> bool:
    children_of_first = select(BondRow.source_node_id).where(BondRow.target_node_id == first, BondRow.kind == BondKind.DESCENDS_FROM)
    statement = select(BondRow.id).where(
        BondRow.target_node_id == second, BondRow.kind == BondKind.DESCENDS_FROM, BondRow.source_node_id.in_(children_of_first)
    )
    return await session.scalar(statement.limit(1)) is not None


def _chimera_stat(rng: SeededRandom, rules: Rules, first: EntityRow, second: EntityRow, key: str) -> int:
    creatures = rules.creatures
    default = creatures.chimera_default_stat
    average = (stat_or(first, key, default) + stat_or(second, key, default)) / 2
    ceiling = creatures.chimera_hp_cap if key == HP_KEY else 100
    return clamp_int(average + rng.die(creatures.chimera_die) - creatures.chimera_shift, 0, ceiling)


async def merge_species(
    ctx: TickContext, first: EntityRow, second: EntityRow, *, name: str | None = None, maker: EntityRow | None = None, description: str | None = None
) -> EntityRow:
    creatures = ctx.rules.creatures
    rng = ctx.rng("chimera")
    traits = list(dict.fromkeys([*sorted(await traits_of(ctx.session, first.id)), *sorted(await traits_of(ctx.session, second.id))]))
    stats = SpeciesStats(
        hp=max(1, _chimera_stat(rng, ctx.rules, first, second, HP_KEY)),
        strength=_chimera_stat(rng, ctx.rules, first, second, STRENGTH_KEY),
        agility=_chimera_stat(rng, ctx.rules, first, second, "agility"),
        intelligence=_chimera_stat(rng, ctx.rules, first, second, INTELLIGENCE_KEY),
        danger=clamp_percent(_chimera_stat(rng, ctx.rules, first, second, DANGER_KEY) + creatures.chimera_danger_bonus),
    )
    chimera = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=name or f"{first.name.split()[0]}-{second.name.split()[0]}",
            entity_type=EntityType.SPECIES,
            body=description or f"A chimera made by combining {first.name} and {second.name}.",
            stats=stats,
            power=max(first.power_level, second.power_level),
            world_id=first.world_id,
            location_id=first.location_id or second.location_id,
            subtype="chimera",
            engine_kind=EngineKind.CHIMERA,
            flags=(EntityFlag.CHIMERA,),
            traits=traits[: creatures.chimera_trait_cap],
        ),
    )
    bonds = BondRepository(ctx.session)
    for parent in (first, second):
        await bonds.connect(BondDraft(chimera.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, "chimera"))
    if maker is not None:
        await bonds.connect(BondDraft(maker.id, chimera.id, BondKind.PRODUCED, ctx.epoch, "made a chimera"))
    return chimera


async def stowaway(ctx: TickContext, origin_world_id: int, region: EntityRow) -> EntityRow | None:
    creatures = ctx.rules.creatures
    statement = select(EntityRow).where(
        EntityRow.world_id == origin_world_id, EntityRow.entity_type == EntityType.SPECIES, EntityRow.status == EntityStatus.CANON
    )
    candidates = [
        species
        for species in await ctx.session.scalars(statement.order_by(EntityRow.id))
        if stat_or(species, DANGER_KEY, 0) < creatures.stowaway_danger_cap and await can_live_on(ctx.session, species.id, region.world_id)
    ]
    rng = ctx.rng("stowaway")
    if not candidates or not rng.chance(creatures.stowaway_chance):
        return None
    source = rng.pick(candidates)
    carried = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"{source.name} (stowaway)",
            entity_type=EntityType.SPECIES,
            body=f"{source.name} was carried to another world in ships' holds and became a non-native invader there.",
            stats=source.stats,
            power=source.power_level,
            world_id=region.world_id,
            location_id=region.id,
            subtype="invasive species",
            flags=(EntityFlag.INVASIVE,),
            traits=sorted(await traits_of(ctx.session, source.id)),
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(carried.id, source.id, BondKind.DESCENDS_FROM, ctx.epoch, "stowaway"))
    return carried


async def species_by_trait(session: AsyncSession, trait: CreatureTrait) -> set[int]:
    return set(await session.scalars(select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == trait)))


def species_danger(rules: Rules, species: EntityRow) -> int:
    value = stat(species, DANGER_KEY)
    return rules.creatures.species_default_danger if value is None else value
