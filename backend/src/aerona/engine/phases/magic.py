from aerona.constants.units import PERCENT
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.context import TickContext
from aerona.engine.environment.ley import LeyWeb
from aerona.engine.faith.book import FaithBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.rites import beyond_reach, cast, casting_limit, casting_steps, choose, spellcraft
from aerona.engine.mind.skills import practise_any
from aerona.engine.mortal.equipment import focus_pct
from aerona.engine.phase import Phase
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record

MAGIC_STORM_SUBTYPE = "magic storm"
WARDED_HOME_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PLACE})


@reads(
    "item.curse",
    "item.might",
    "region.magic",
    "resource.might",
    "table.bonds",
    "table.entities",
    "table.ley_lines",
    "table.name_registry",
    "table.nodes",
    "table.world_maps",
)
@writes(
    "item.curse",
    "item.might",
    "resource.might",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
)
async def magic_storms(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    engine = rules.world_engine
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    web = await LeyWeb.load(ctx.session)
    charged = await canon(ctx.session, [EntityType.RESOURCE, EntityType.ITEM])
    regions = {region.id: region for region in await canon(ctx.session, [EntityType.REGION])}
    for region in regions.values():
        chance = engine.magic_storm_chance * (rules.environment.ley_storm_pct / PERCENT if web.on_line(region.id) else 1)
        if held(region.id, region.world_id) or (stat(region, "magic") or 0) < effects.magic_storm_min_magic or not rng.chance(chance):
            continue
        reached = [region.id] + [other for other in web.partners(region.id) if rng.chance(rules.environment.ley_storm_spread_pct)]
        touched = [entity for entity in charged if atlas.top_region(entity.id) in reached]
        for entity in touched:
            set_stats(entity, might=clamp_int((stat(entity, "might") or 0) + effects.magic_storm_might_gain, 0, PERCENT))
            if rng.chance(engine.magic_storm_curse_chance):
                set_stats(entity, curse=clamp_int((stat(entity, "curse") or 0) + effects.magic_storm_curse_gain, 0, PERCENT))
        event = await open_record(
            ctx.session,
            ctx.epoch,
            RecordSpec(
                entity_type=EntityType.EVENT,
                name=f"{region.name} Magic Storm",
                body=f"The dense magic of {region.name} overflowed; resources and items grew stronger, some were cursed.",
                stats=EventStats(severity=clamp_int(effects.magic_storm_severity_base + rng.die(effects.magic_storm_severity_die), 0, PERCENT)),
                power=effects.magic_storm_power,
                location_id=region.id,
                world_id=region.world_id,
                subtype=MAGIC_STORM_SUBTYPE,
                engine_kind=EngineKind.MAGIC_STORM,
            ),
        )
        along = [regions[other].name for other in reached[1:] if other in regions]
        spread = f" It ran down the ley lines into {', '.join(along)}." if along else ""
        await record(
            ctx,
            "magic.storm",
            roles={IncidentRole.SUBJECT: [*[region.id, event.id, *reached[1:]]]},
            facts={"region": str(region.name), "count": len(touched), "spread": str(spread)},
        )


async def enemies_of(ctx: TickContext, entity_id: int) -> list[EntityRow]:
    bonds = await active_bonds(ctx.session, [BondKind.ENEMY], sources=[entity_id]) + await active_bonds(ctx.session, [BondKind.ENEMY], targets=[entity_id])
    found = [await living_entity(ctx.session, bond.other_end(entity_id)) for bond in sorted(bonds, key=lambda item: item.id)]
    return [enemy for enemy in found if enemy is not None]


async def aim(ctx: TickContext, mortal: EntityRow, enemies: list[EntityRow], *, protective: bool) -> tuple[EntityRow, RiteProfileRow, EntityRow | None] | None:
    chosen = await choose(ctx, mortal, hostile=bool(enemies), protective=protective)
    if chosen is None:
        return None
    rite, row = chosen
    if not enemies:
        return rite, row, None
    enemy = await enemy_in_reach(ctx, mortal, row, enemies)
    return (rite, row, enemy) if enemy is not None else None


async def enemy_in_reach(ctx: TickContext, mortal: EntityRow, row: RiteProfileRow, enemies: list[EntityRow]) -> EntityRow | None:
    for enemy in enemies:
        if await beyond_reach(ctx, mortal, row, enemy) is None:
            return enemy
    return None


@reads(
    "mortal.intellect",
    "settlement.prosperity",
    "table.augment_effects",
    "table.augments",
    "table.bonds",
    "table.charms",
    "table.creator",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incubating_ideas",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.ley_lines",
    "table.mind_attributes",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.region_environment",
    "table.region_pollution",
    "table.resurrection_orders",
    "table.reverences",
    "table.rite_profiles",
    "table.skills",
    "table.sky_events",
    "table.sons",
    "table.stars",
    "table.traits",
    "table.vassalages",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.region_pollution",
    "table.skills",
)
async def wizards(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    knowledge = await KnowledgeMap.load(ctx.session)
    web = await LeyWeb.load(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    churches = await FaithBook.load(ctx.session)
    realms = await RealmBook.load(ctx.session)
    worked = 0
    limit = await casting_limit(ctx)
    for mortal in ctx.rng("wizards.order").shuffled(await canon(ctx.session, [EntityType.MORTAL])):
        if mortal.status is not EntityStatus.CANON or not knowledge.knows(mortal.id, KnowledgeBranch.MAGIC):
            continue
        if (stat(mortal, "intellect") or 0) >= rules.world_effects.sorcerer_min_intellect:
            await practise_any(ctx.session, rules, mortal.id, (SkillKind.SPELLCRAFT,), rules.rites.spellcraft_xp, epoch=ctx.epoch)
        if await spellcraft(ctx.session, mortal.id) < rules.rites.wizard_skill:
            continue
        banned = laws.param(mortal.location_id or 0, LawKind.MAGIC_BAN, "severity")
        if banned is not None and rng.chance(int(banned)):
            continue
        if churches.holds(mortal.location_id or 0, TenetKind.ANTI_MAGIC):
            continue
        holy = 2 if churches.holds(mortal.location_id or 0, TenetKind.SANCTIFIED_MAGIC) else 1
        if not await has_flag(ctx.session, mortal.id, EntityFlag.WIZARD):
            await add_flag(ctx.session, mortal.id, EntityFlag.WIZARD, ctx.epoch)
            await record(ctx, "magic.wizard", roles={IncidentRole.SUBJECT: mortal.id})
        ley = rules.environment.ley_wizard_pct / PERCENT if web.on_line(atlas.top_region(mortal.id)) else 1
        if not rng.chance(rules.world_engine.sorcerer_act_chance * ley * holy * await focus_pct(ctx.session, rules, mortal.id)):
            continue
        home = await living_entity(ctx.session, mortal.location_id)
        if home is None or worked >= limit:
            continue
        enemies = await enemies_of(ctx, home.id)
        hostile = bool(enemies) and rng.chance(rules.world_engine.sorcerer_curse_chance)
        if not hostile and home.entity_type not in WARDED_HOME_TYPES:
            continue
        working = await aim(ctx, mortal, enemies if hostile else [], protective=rng.chance(rules.world_effects.sorcerer_protect_chance))
        if working is None:
            continue
        rite, row, enemy = working
        casting = await cast(ctx, mortal, rite, row, target=enemy if hostile else None, realms=realms)
        if casting is None:
            continue
        worked += 1
        targets = [enemy.id] if hostile and enemy is not None else [home.id]
        await record(
            ctx,
            "magic.rite",
            roles={IncidentRole.SUBJECT: [mortal.id, *[mortal.id, rite.id, *targets]]},
            facts={"rite": str(rite.name), "effect": casting.effect},
            steps=await casting_steps(ctx, casting),
        )


@reads(
    "people.magic",
    "people.population",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.natural_law_profiles",
    "table.nodes",
    "table.stars",
    "table.worlds",
)
@writes("people.population")
async def price_of_magic(ctx: TickContext) -> None:
    laws = await ctx.laws()
    if not laws.anywhere(NaturalLaw.MAGIC_PRICE):
        return
    effects = ctx.rules.world_effects
    limits = ctx.rules.limits
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        if (stat(people, "magic") or 0) <= effects.magic_price_min_magic or not laws.has(NaturalLaw.MAGIC_PRICE, people.world_id):
            continue
        population = stat(people, "population") or 0
        set_stats(
            people,
            population=clamp_int(population * effects.magic_price_population_kept_pct / PERCENT, limits.people_population_floor, limits.people_population_cap),
        )
        ctx.count("magic_price_paid")


STORM_PHASES = (Phase("magic_storms", magic_storms),)
SOCIETY_PHASES = (Phase("wizards", wizards),)
LAW_PHASES = (Phase("price_of_magic", price_of_magic),)
PHASES = STORM_PHASES + SOCIETY_PHASES + LAW_PHASES
