from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.context import TickContext
from aerona.engine.environment.ley import LeyWeb
from aerona.engine.faith.book import FaithBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore.rites import cast, choose
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import set_stats, stat

MAGIC_STORM_SUBTYPE = "magic storm"
WARDED_HOME_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PLACE})


@reads(
    "item.curse",
    "item.might",
    "region.magic",
    "resource.might",
    "table.bonds",
    "table.epoch_year_cursors",
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
    "table.epoch_year_cursors",
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
        if (stat(region, "magic") or 0) < effects.magic_storm_min_magic or not rng.chance(chance):
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
        await note(
            ctx,
            f"A magic storm broke out in {region.name}; {len(touched)} resources and items grew stronger.{spread}",
            key="magic.storm",
            ids=[region.id, event.id, *reached[1:]],
        )


async def first_enemy(ctx: TickContext, entity_id: int) -> EntityRow | None:
    bonds = await active_bonds(ctx.session, [BondKind.ENEMY], sources=[entity_id]) + await active_bonds(ctx.session, [BondKind.ENEMY], targets=[entity_id])
    for bond in sorted(bonds, key=lambda item: item.id):
        enemy = await living_entity(ctx.session, bond.other_end(entity_id))
        if enemy is not None:
            return enemy
    return None


@reads(
    "mortal.intellect",
    "settlement.prosperity",
    "table.bonds",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.ley_lines",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.resurrection_orders",
    "table.reverences",
    "table.rite_profiles",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
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
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if mortal.status is not EntityStatus.CANON or (stat(mortal, "intellect") or 0) < rules.world_effects.sorcerer_min_intellect:
            continue
        if not knowledge.knows(mortal.id, KnowledgeBranch.MAGIC):
            continue
        banned = laws.param(mortal.location_id or 0, LawKind.MAGIC_BAN, "severity")
        if banned is not None and rng.chance(int(banned)):
            continue
        if churches.holds(mortal.location_id or 0, TenetKind.ANTI_MAGIC):
            continue
        holy = 2 if churches.holds(mortal.location_id or 0, TenetKind.SANCTIFIED_MAGIC) else 1
        if not await has_flag(ctx.session, mortal.id, EntityFlag.WIZARD):
            await add_flag(ctx.session, mortal.id, EntityFlag.WIZARD, ctx.epoch)
            await note(ctx, f"{mortal.name} deciphered the language of magic; now a wizard.", key="magic.wizard", ids=[mortal.id])
        ley = rules.environment.ley_wizard_pct / PERCENT if web.on_line(atlas.top_region(mortal.id)) else 1
        if not rng.chance(rules.world_engine.sorcerer_act_chance * ley * holy):
            continue
        home = await living_entity(ctx.session, mortal.location_id)
        if home is None or worked >= rules.rites.cap:
            continue
        enemy = await first_enemy(ctx, home.id)
        hostile = enemy is not None and rng.chance(rules.world_engine.sorcerer_curse_chance)
        if not hostile and home.entity_type not in WARDED_HOME_TYPES:
            continue
        chosen = await choose(ctx, mortal, hostile=hostile, protective=rng.chance(rules.world_effects.sorcerer_protect_chance))
        if chosen is None:
            continue
        rite, row = chosen
        casting = await cast(ctx, mortal, rite, row, target=enemy if hostile else None, realms=realms)
        if casting is None:
            continue
        worked += 1
        targets = [enemy.id] if hostile and enemy is not None else [home.id]
        await note(ctx, f"Wizard {mortal.name} worked {rite.name}: {casting.effect}.", key="magic.rite", ids=[mortal.id, rite.id, *targets])


@reads("people.magic", "people.population")
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
