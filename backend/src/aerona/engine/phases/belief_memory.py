import math
from collections.abc import Callable

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several, spoken
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ProphecyState
from aerona.domain.enums.entity import COMMUNITY_TYPES, LOCATION_TYPES, EntityFlag, EntityOrigin, EntityStatus, EntityType, LegendCategory, MortalRole
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.entity_stats import EntityStats, ItemStats, LegendStats, ResourceStats, SpeciesStats, SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.legends import believed
from aerona.engine.lore.prophecy import condition_of
from aerona.engine.lore.prophecy import fail as fail_prophecy
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.living_stats import mock_prophecy
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, connect, flags_by_entity, living_entity, load_entities, remove_flag
from aerona.engine.primitives.records import RecordSpec, definite, open_record, retire, sentence_case
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.transform.record import blocked, record_transformation
from aerona.rules.registry import Rules

TELLER_KINDS = (BondKind.CELEBRATES, BondKind.TELLS_OF)
PLACE_BOND_KINDS = (BondKind.TELLS_OF, BondKind.RELATED, BondKind.INSIDE)
KEEPER_ROLES = frozenset({MortalRole.SAGE, MortalRole.SEER, MortalRole.SCRIBE, MortalRole.JOURNALIST})
BLURRED_SUBTYPE = "blurred memory"


MANIFESTATION_SUBTYPES: dict[LegendCategory, str] = {
    LegendCategory.CREATURE: "creature from the legend",
    LegendCategory.SPIRIT: "spirit born of belief",
    LegendCategory.RESOURCE: "hallowed resource",
    LegendCategory.RELIC: "relic from the legend",
}
MANIFESTATION_TYPES: dict[LegendCategory, EntityType] = {
    LegendCategory.CREATURE: EntityType.SPECIES,
    LegendCategory.SPIRIT: EntityType.SPIRIT,
    LegendCategory.RESOURCE: EntityType.RESOURCE,
    LegendCategory.RELIC: EntityType.ITEM,
}
SUBJECT_CATEGORIES: dict[EntityType, LegendCategory] = {
    EntityType.SPECIES: LegendCategory.CREATURE,
    EntityType.OUTER_BEING: LegendCategory.CREATURE,
    EntityType.COSMIC_BEING: LegendCategory.CREATURE,
    EntityType.SPIRIT: LegendCategory.SPIRIT,
    EntityType.MORTAL: LegendCategory.SPIRIT,
    EntityType.RESOURCE: LegendCategory.RESOURCE,
    EntityType.REGION: LegendCategory.RESOURCE,
    EntityType.PLACE: LegendCategory.RESOURCE,
}


def category_of_subject(subject: EntityRow | None) -> LegendCategory:
    if subject is None:
        return LegendCategory.RELIC
    return SUBJECT_CATEGORIES.get(subject.entity_type, LegendCategory.RELIC)


async def manifestation_of(ctx: TickContext, legend: EntityRow) -> LegendCategory:
    if legend.legend_category is not None:
        return legend.legend_category
    bonds = await active_bonds(ctx.session, [BondKind.TELLS_OF], sources=[legend.id])
    subject = await ctx.session.get(EntityRow, bonds[0].target_node_id) if bonds else None
    category = category_of_subject(subject)
    legend.legend_category = category
    return category


def manifestation_stats(rules: Rules, kind: LegendCategory, die: Callable[[int], int]) -> EntityStats:
    life = rules.deep_life
    if kind is LegendCategory.CREATURE:
        return SpeciesStats(
            hp=life.manifest_creature_hp + die(life.manifest_creature_hp_die),
            strength=clamp_int(life.manifest_creature_strength + die(life.manifest_creature_strength_die), 0, PERCENT),
            agility=clamp_int(life.manifest_creature_agility + die(life.manifest_creature_agility_die), 0, PERCENT),
            intelligence=clamp_int(life.manifest_creature_intelligence + die(life.manifest_creature_intelligence_die), 0, PERCENT),
            danger=clamp_int(life.manifest_creature_danger + die(life.manifest_creature_danger_die), 0, PERCENT),
        )
    if kind is LegendCategory.SPIRIT:
        return SpiritStats(
            strength=clamp_int(life.manifest_spirit_strength + die(life.manifest_spirit_strength_die), 0, PERCENT),
            unrest=clamp_int(life.manifest_spirit_unrest + die(life.manifest_spirit_unrest_die), 0, PERCENT),
        )
    if kind is LegendCategory.RESOURCE:
        return ResourceStats(
            abundance=clamp_int(life.manifest_resource_abundance + die(life.manifest_resource_abundance_die), 0, PERCENT),
            value=clamp_int(life.manifest_resource_value + die(life.manifest_resource_value_die), 0, PERCENT),
            might=clamp_int(life.manifest_resource_might + die(life.manifest_resource_might_die), 0, PERCENT),
        )
    return ItemStats(
        damage=clamp_int(die(life.manifest_relic_damage_die), 0, PERCENT),
        protection=clamp_int(die(life.manifest_relic_protection_die), 0, PERCENT),
        might=clamp_int(life.manifest_relic_might + die(life.manifest_relic_might_die), 0, PERCENT),
        curse=clamp_int(die(life.manifest_relic_curse_die), 0, PERCENT),
    )


async def living_tellers(ctx: TickContext, target_id: int) -> list[BondRow]:
    tellers = []
    for bond in await active_bonds(ctx.session, TELLER_KINDS, targets=[target_id]):
        if await living_entity(ctx.session, bond.source_node_id) is not None:
            tellers.append(bond)
    return tellers


async def legend_spread(ctx: TickContext) -> None:
    life = ctx.rules.deep_life
    legends = await canon(ctx.session, [EntityType.LEGEND])
    await load_entities(ctx.session, [bond.source_node_id for bond in await active_bonds(ctx.session, TELLER_KINDS, targets=[legend.id for legend in legends])])
    for legend in legends:
        tellers = len(await living_tellers(ctx, legend.id))
        current = stat(legend, "spread")
        base = current if current is not None else life.legend_default_spread
        set_stats(legend, spread=clamp_int(base + tellers * life.legend_spread_per_teller - life.legend_spread_decay, 0, PERCENT))


async def celebrants(ctx: TickContext, tradition: EntityRow) -> int:
    count = 0
    for bond in await active_bonds(ctx.session, list(BondKind), targets=[tradition.id]):
        source = await living_entity(ctx.session, bond.source_node_id)
        if source is not None and (bond.kind is BondKind.CELEBRATES or source.entity_type in COMMUNITY_TYPES):
            count += 1
    return count


def resisted_fade(ctx: TickContext, tradition: EntityRow, amount: int) -> int:
    rigidity = clamp_int(stat(tradition, "rigidity") or 0, 0, PERCENT)
    kept = max(0.0, 1 - rigidity * ctx.rules.life_cycles.tradition_rigidity_resistance_pct / (PERCENT * PERCENT))
    exact = amount * kept
    whole = math.floor(exact)
    return whole + (1 if ctx.rng(f"fade.{tradition.id}").random() < exact - whole else 0)


async def traditions(ctx: TickContext) -> None:
    life = ctx.rules.deep_life
    kept = await canon(ctx.session, [EntityType.TRADITION])
    await load_entities(ctx.session, [bond.source_node_id for bond in await active_bonds(ctx.session, list(BondKind), targets=[item.id for item in kept])])
    for tradition in kept:
        if ctx.epoch - tradition.birth_epoch <= life.tradition_grace_epochs:
            continue
        count = await celebrants(ctx, tradition)
        current = stat(tradition, "spread")
        base = current if current is not None else life.tradition_default_spread
        if count:
            delta = min(life.tradition_celebrants_per_point, count) - 1
        else:
            decay = life.engine_tradition_decay if tradition.origin is EntityOrigin.ENGINE else life.tradition_decay
            delta = -resisted_fade(ctx, tradition, decay)
        spread = clamp_int(base + delta, 0, PERCENT)
        set_stats(tradition, spread=spread)
        if spread <= life.tradition_forget_spread and not count:
            await retire(ctx.session, tradition, ctx.epoch, f"Epoch {ctx.epoch}: no one left to celebrate it; forgotten.", close_bonds=True)
            await note(
                ctx,
                f"{sentence_case(definite(tradition.name))} tradition was forgotten; no one celebrates it any more.",
                key="memory.tradition_forgotten",
                ids=[tradition.id],
            )


async def forgotten_tales(ctx: TickContext) -> None:
    life = ctx.rules.deep_life
    tales = await flags_by_entity(ctx.session, EntityFlag.FAIRY_TALE)
    for legend in await canon(ctx.session, [EntityType.LEGEND]):
        if legend.id not in tales or (stat(legend, "spread") or 0) > life.tale_forget_spread or ctx.epoch - legend.birth_epoch < life.tale_forget_min_age:
            continue
        await retire(ctx.session, legend, ctx.epoch, f"Epoch {ctx.epoch}: its last teller died too; the tale was forgotten.", close_bonds=True)


async def forgotten_prophecies(ctx: TickContext) -> None:
    for prophecy in await canon(ctx.session, [EntityType.PROPHECY]):
        row = await condition_of(ctx, prophecy)
        if row.deadline_epoch is None or ctx.epoch <= row.deadline_epoch or row.state is not ProphecyState.PENDING:
            continue
        age = ctx.epoch - prophecy.birth_epoch
        await fail_prophecy(ctx, row)
        await mock_prophecy(ctx, prophecy)
        await retire(
            ctx.session, prophecy, ctx.epoch, f"Epoch {ctx.epoch}: waited {several(age, 'epoch', 'epochs')} and was forgotten unfulfilled.", close_bonds=True
        )
        await note(
            ctx,
            f"{sentence_case(definite(prophecy.name))} prophecy went unfulfilled for {several(age, 'epoch', 'epochs')}; no one knows it by heart any more.",
            key="memory.prophecy_forgotten",
            ids=[prophecy.id],
        )


async def legend_place(ctx: TickContext, legend: EntityRow) -> EntityRow | None:
    place = await living_entity(ctx.session, legend.location_id)
    if place is not None:
        return place
    for bond in await active_bonds(ctx.session, PLACE_BOND_KINDS, sources=[legend.id]):
        target = await living_entity(ctx.session, bond.target_node_id)
        if target is not None and target.entity_type in LOCATION_TYPES:
            return target
    return None


async def manifest(ctx: TickContext, legend: EntityRow, place: EntityRow) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(f"manifest.{legend.id}")
    kind = await manifestation_of(ctx, legend)
    created = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=MANIFESTATION_TYPES[kind],
            name=f"Manifestation of {legend.name}",
            body=f"So many believed the legend of {legend.name} for so long that what it told truly appeared in {place.name}.",
            stats=manifestation_stats(ctx.rules, kind, rng.die),
            power=clamp_int(legend.power_level + life.manifestation_power_bonus, life.derived_min_power, life.manifestation_max_power),
            location_id=place.id,
            world_id=place.world_id,
            subtype=MANIFESTATION_SUBTYPES[kind],
            flags=(EntityFlag.BORN_OF_BELIEF,),
        ),
    )
    await connect(ctx.session, legend.id, created.id, BondKind.SOURCE_OF, ctx.epoch, description="born of belief")
    await add_flag(ctx.session, legend.id, EntityFlag.MANIFESTED, ctx.epoch)
    await note(
        ctx,
        f"So many believed {definite(legend.name)} legend that it became real in {place.name}: what was told is now there.",
        key="memory.manifestation",
        ids=[legend.id, created.id, place.id],
    )
    ctx.count("manifestations")
    await record_transformation(ctx, TransformKind.MANIFESTATION, legend.id, created.id)
    return created


async def manifestations(ctx: TickContext) -> None:
    life = ctx.rules.deep_life
    rng = ctx.rng("manifestation")
    manifested = await flags_by_entity(ctx.session, EntityFlag.MANIFESTED)
    made = 0
    for legend in await canon(ctx.session, [EntityType.LEGEND]):
        if made >= life.manifestation_cap:
            return
        if legend.id in manifested or not await believed(ctx, legend):
            continue
        if not rng.chance(ctx.rules.deep_world.manifestation_chance):
            continue
        place = await legend_place(ctx, legend)
        if place is None or await blocked(ctx, TransformKind.MANIFESTATION, legend.id):
            continue
        await manifest(ctx, legend, place)
        made += 1


async def told_events(ctx: TickContext) -> set[int]:
    statement = select(BondRow.target_node_id).where(BondRow.kind == BondKind.TELLS_OF, BondRow.state.in_([BondState.ACTIVE, BondState.PAST]))
    return set(await ctx.session.scalars(statement))


async def legendify(ctx: TickContext, event: EntityRow) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(f"legendify.{event.id}")
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=f"Tale of {event.name}",
            body=(
                f"{event.name} of Epoch {event.birth_epoch} became a legend through generations of retelling: "
                "details blurred, heroes grew, culprits changed, numbers were exaggerated."
            ),
            stats=LegendStats(spread=clamp_int(life.legend_spread_base + rng.die(life.legend_spread_die), 0, PERCENT)),
            power=max(life.derived_min_power, event.power_level - life.legend_power_gap),
            world_id=event.world_id,
            subtype=BLURRED_SUBTYPE,
            flags=(EntityFlag.CORRUPTED_MEMORY,),
        ),
    )
    await connect(ctx.session, legend.id, event.id, BondKind.TELLS_OF, ctx.epoch, description="distortingly")
    await note(
        ctx,
        f"{event.name} of Epoch {event.birth_epoch} is now a legend no one fully remembers; every teller adds something.",
        key="memory.legendification",
        ids=[event.id, legend.id],
    )
    return legend


async def legendification(ctx: TickContext) -> None:
    life = ctx.rules.deep_life
    rng = ctx.rng("legendification")
    told = await told_events(ctx)
    statement = (
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.EVENT,
            EntityRow.status.in_([EntityStatus.CANON, EntityStatus.DEAD]),
            EntityRow.birth_epoch <= ctx.epoch - life.legend_event_min_age,
        )
        .order_by(EntityRow.birth_epoch, EntityRow.id)
    )
    made = 0
    for event in await ctx.session.scalars(statement):
        if made >= life.legendization_cap:
            break
        if event.id in told or (stat(event, "severity") or 0) < life.legend_event_min_severity:
            continue
        if not rng.chance(ctx.rules.deep_world.legendization_chance):
            continue
        await legendify(ctx, event)
        made += 1
    await year_legends(ctx, life.legendization_cap - made)


async def legendify_year(ctx: TickContext, year: NotableYearRow) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(f"legendify.year.{year.id}")
    region = await ctx.session.get(EntityRow, year.region_entity_id) if year.region_entity_id is not None else None
    title = year.name[:1].upper() + year.name[1:]
    legend = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.LEGEND,
            name=f"Tale of {title}",
            body=f"{title}, the year {year.year}, lived on in the telling long after the last who saw it died; each teller made it greater.",
            stats=LegendStats(spread=clamp_int(life.legend_spread_base + rng.die(life.legend_spread_die), 0, PERCENT)),
            power=life.derived_min_power,
            world_id=year.world_id,
            location_id=region.id if region is not None else None,
            subtype=BLURRED_SUBTYPE,
            flags=(EntityFlag.CORRUPTED_MEMORY,),
        ),
    )
    if region is not None:
        await connect(ctx.session, legend.id, region.id, BondKind.TELLS_OF, ctx.epoch, description=f"the year {year.year}")
    year.legend_entity_id = legend.id
    await note(ctx, f"{title} of the year {year.year} became a tale; no one alive saw it, yet everyone knows it.", key="memory.year_legend", ids=[legend.id])
    return legend


async def year_legends(ctx: TickContext, room: int) -> int:
    life = ctx.rules.deep_life
    rng = ctx.rng("year_legends")
    statement = (
        select(NotableYearRow)
        .where(
            NotableYearRow.legend_entity_id.is_(None),
            NotableYearRow.epoch <= ctx.epoch - life.legend_event_min_age,
            NotableYearRow.magnitude >= life.legend_event_min_severity,
        )
        .order_by(NotableYearRow.epoch, NotableYearRow.id)
    )
    made = 0
    famine_above = PERCENT - ctx.rules.harvest.famine_event_below
    for year in await ctx.session.scalars(statement):
        if made >= room:
            break
        if year.kind is NotableYearKind.HUNGER and year.magnitude > famine_above:
            continue
        if rng.chance(ctx.rules.deep_world.legendization_chance):
            await legendify_year(ctx, year)
            made += 1
    return made


async def fairy_tales(ctx: TickContext) -> None:
    life = ctx.rules.deep_life
    rng = ctx.rng("fairy_tales")
    atlas = await RegionAtlas.load(ctx.session)
    keepers = [mortal for mortal in await canon(ctx.session, [EntityType.MORTAL]) if mortal.mortal_role in KEEPER_ROLES]
    tales = await flags_by_entity(ctx.session, EntityFlag.FAIRY_TALE)
    legends = await canon(ctx.session, [EntityType.LEGEND])
    places = [bond.target_node_id for bond in await active_bonds(ctx.session, PLACE_BOND_KINDS, sources=[legend.id for legend in legends])]
    await load_entities(ctx.session, [*(legend.location_id for legend in legends), *places])
    for legend in legends:
        if legend.id in tales or ctx.epoch - legend.birth_epoch < life.tale_min_age or (stat(legend, "spread") or 0) >= life.tale_spread_threshold:
            continue
        place = await legend_place(ctx, legend)
        anchor = place.id if place is not None else legend.id
        if any(atlas.distance(keeper.id, anchor) <= life.tale_keeper_distance for keeper in keepers):
            continue
        if not rng.chance(ctx.rules.deep_world.fairy_tale_chance):
            continue
        await add_flag(ctx.session, legend.id, EntityFlag.FAIRY_TALE, ctx.epoch)
        await note(ctx, f"{legend.name} is now only a tale told to the young; the grown no longer believe it.", key="memory.fairy_tale", ids=[legend.id])


@reads(
    "event.severity",
    "legend.spread",
    "table.bonds",
    "table.cult_tenets",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.name_registry",
    "table.nodes",
    "table.notable_years",
    "table.prophecy_conditions",
    "table.routes",
    "table.skills",
    "table.transform_prospects",
    "table.world_maps",
    "tradition.rigidity",
    "tradition.spread",
)
@writes(
    "legend.spread",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.name_registry",
    "table.transformations",
    "tradition.spread",
)
async def belief_and_memory(ctx: TickContext) -> None:
    await legend_spread(ctx)
    await traditions(ctx)
    await forgotten_tales(ctx)
    await forgotten_prophecies(ctx)
    await manifestations(ctx)
    await legendification(ctx)
    await fairy_tales(ctx)


async def require_record(ctx: TickContext, entity_id: int, entity_type: EntityType, statuses: frozenset[EntityStatus]) -> EntityRow:
    found = await ctx.session.get(EntityRow, entity_id)
    if found is None or found.entity_type is not entity_type or found.status not in statuses:
        raise ValidationFailedError(f"No such {spoken(entity_type)} to act on.")
    return found


async def retire_legend(ctx: TickContext, legend_id: int) -> EntityRow:
    legend = await require_record(ctx, legend_id, EntityType.LEGEND, frozenset({EntityStatus.CANON}))
    return await retire(ctx.session, legend, ctx.epoch, f"Epoch {ctx.epoch}: the gods let it be forgotten.", close_bonds=True)


async def revive_legend(ctx: TickContext, legend_id: int) -> EntityRow:
    legend = await require_record(ctx, legend_id, EntityType.LEGEND, frozenset({EntityStatus.CANON, EntityStatus.DEAD}))
    if legend.status is EntityStatus.DEAD:
        await EntityRepository(ctx.session).set_status(legend, EntityStatus.CANON, ctx.epoch)
        legend.end_epoch = None
    await remove_flag(ctx.session, legend.id, EntityFlag.FAIRY_TALE)
    set_stats(legend, spread=max(stat(legend, "spread") or 0, ctx.rules.deep_life.legend_default_spread))
    await note(ctx, f"{legend.name} is told again.", key="memory.legend_revived", ids=[legend.id])
    return legend


async def fulfil_prophecy(ctx: TickContext, prophecy_id: int) -> EntityRow:
    prophecy = await require_record(ctx, prophecy_id, EntityType.PROPHECY, frozenset({EntityStatus.CANON}))
    return await retire(ctx.session, prophecy, ctx.epoch, f"Epoch {ctx.epoch}: the prophecy was fulfilled.", status=EntityStatus.FULFILLED)


async def retire_prophecy(ctx: TickContext, prophecy_id: int) -> EntityRow:
    prophecy = await require_record(ctx, prophecy_id, EntityType.PROPHECY, frozenset({EntityStatus.CANON}))
    return await retire(ctx.session, prophecy, ctx.epoch, f"Epoch {ctx.epoch}: the gods let it be forgotten unfulfilled.", close_bonds=True)


async def event_to_legend(ctx: TickContext, event_id: int) -> EntityRow:
    event = await require_record(ctx, event_id, EntityType.EVENT, frozenset({EntityStatus.CANON, EntityStatus.DEAD}))
    return await legendify(ctx, event)


async def manifest_legend(ctx: TickContext, legend_id: int) -> EntityRow:
    legend = await require_record(ctx, legend_id, EntityType.LEGEND, frozenset({EntityStatus.CANON}))
    place = await legend_place(ctx, legend)
    if place is None:
        raise ValidationFailedError(f"{legend.name} is told of no place where it could appear.")
    return await manifest(ctx, legend, place)


PHASES = (Phase("belief_and_memory", belief_and_memory),)
