import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from aerona.catalog.society import SOCIAL_CLASSES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityFlag, EntityType, MortalRole
from aerona.domain.enums.mind import TraitEffect
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import MortalStats, PeopleStats, SettlementStats
from aerona.engine.body.book import factor
from aerona.engine.body.cohorts import healer_demand
from aerona.engine.body.customs import culture_of
from aerona.engine.body.hits import weighted
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.ruler_roles import ruler_role
from aerona.engine.mind.book import effect_of, scaled_by
from aerona.engine.mind.space import value_distance
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.settlements import resettle_ruin
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import (
    BondIndex,
    active_bonds,
    add_flag,
    canon,
    close,
    connect,
    descendants,
    has_flag,
    living_entity,
    living_son,
    spoken_language,
)
from aerona.engine.primitives.records import RecordSpec, indefinite, open_record, sentence_case
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import headcount, headcount_bounds, set_stats, stat
from aerona.language.generator import NameKind
from aerona.language.titles import from_among
from aerona.rules.registry import Rules

Bias = Callable[[Rules], int]
STAT_KEYS = ("strength", "agility", "intellect", "charisma")
COUPLE_KINDS = (BondKind.LOVES, BondKind.ALLY)
CHILD_SUBTYPE = "child"
VILLAGE_SUBTYPE = "village"
HOMELAND_SUBTYPE = "homeland"
NEW_PEOPLE_SUBTYPE = "new tribe"
SAPIENT_SUBTYPE = "sapient species"
DIVERGENCE = "divergence"


@dataclass(frozen=True)
class NotableRole:
    key: str
    suffix: str
    subtype: str
    role: MortalRole
    biases: Mapping[str, Bias] = field(default_factory=dict)


NOTABLE_ROLES: dict[SocialClass, tuple[NotableRole, ...]] = {
    SocialClass.FARMER: (
        NotableRole(
            "leader",
            "Leader",
            "folk leader",
            MortalRole.FARMER,
            {"strength": lambda r: r.deep_life.role_farmer_leader_strength, "charisma": lambda r: r.deep_life.role_farmer_leader_charisma},
        ),
        NotableRole(
            "shepherd",
            "Shepherd",
            "shepherd",
            MortalRole.FARMER,
            {"agility": lambda r: r.deep_life.role_farmer_shepherd_agility, "strength": lambda r: r.deep_life.role_farmer_shepherd_strength},
        ),
        NotableRole(
            "midwife",
            "Midwife",
            "midwife",
            MortalRole.HEALER,
            {"intellect": lambda r: r.deep_life.role_farmer_midwife_intellect, "charisma": lambda r: r.deep_life.role_farmer_midwife_charisma},
        ),
    ),
    SocialClass.ARTISAN: (
        NotableRole(
            "master",
            "Master",
            "master artisan",
            MortalRole.ARTISAN,
            {"intellect": lambda r: r.deep_life.role_artisan_master_intellect, "agility": lambda r: r.deep_life.role_artisan_master_agility},
        ),
        NotableRole("smith", "Smith", "smith", MortalRole.ARTISAN, {"strength": lambda r: r.deep_life.role_artisan_smith_strength}),
        NotableRole("architect", "Architect", "architect", MortalRole.ARTISAN, {"intellect": lambda r: r.deep_life.role_artisan_architect_intellect}),
    ),
    SocialClass.MERCHANT: (
        NotableRole(
            "trader",
            "Merchant",
            "merchant",
            MortalRole.MERCHANT,
            {"intellect": lambda r: r.deep_life.role_merchant_trader_intellect, "charisma": lambda r: r.deep_life.role_merchant_trader_charisma},
        ),
        NotableRole(
            "caravaneer",
            "Caravaneer",
            "caravaneer",
            MortalRole.MERCHANT,
            {"agility": lambda r: r.deep_life.role_merchant_caravaneer_agility, "strength": lambda r: r.deep_life.role_merchant_caravaneer_strength},
        ),
        NotableRole(
            "moneychanger", "Money-changer", "money-changer", MortalRole.MERCHANT, {"intellect": lambda r: r.deep_life.role_merchant_moneychanger_intellect}
        ),
    ),
    SocialClass.PRIEST: (
        NotableRole(
            "seer",
            "Seer",
            "seer",
            MortalRole.SEER,
            {"intellect": lambda r: r.deep_life.role_priest_seer_intellect, "charisma": lambda r: r.deep_life.role_priest_seer_charisma},
        ),
        NotableRole(
            "healer",
            "Healer",
            "healer",
            MortalRole.HEALER,
            {"intellect": lambda r: r.deep_life.role_priest_healer_intellect, "charisma": lambda r: r.deep_life.role_priest_healer_charisma},
        ),
        NotableRole("bard", "Bard", "bard", MortalRole.SCRIBE, {"charisma": lambda r: r.deep_life.role_priest_bard_charisma}),
    ),
    SocialClass.WARRIOR: (
        NotableRole(
            "warrior",
            "Warrior",
            "hero",
            MortalRole.HERO,
            {"strength": lambda r: r.deep_life.role_warrior_warrior_strength, "agility": lambda r: r.deep_life.role_warrior_warrior_agility},
        ),
        NotableRole(
            "hunter",
            "Hunter",
            "hunter",
            MortalRole.HUNTER,
            {"agility": lambda r: r.deep_life.role_warrior_hunter_agility, "strength": lambda r: r.deep_life.role_warrior_hunter_strength},
        ),
        NotableRole(
            "guard",
            "Guard",
            "guard warrior",
            MortalRole.WARRIOR,
            {"strength": lambda r: r.deep_life.role_warrior_guard_strength, "charisma": lambda r: r.deep_life.role_warrior_guard_charisma},
        ),
    ),
    SocialClass.SCRIBE: (
        NotableRole("sage", "Sage", "sage", MortalRole.SAGE, {"intellect": lambda r: r.deep_life.role_scribe_sage_intellect}),
        NotableRole(
            "historian",
            "Historian",
            "historian",
            MortalRole.SCRIBE,
            {"intellect": lambda r: r.deep_life.role_scribe_historian_intellect, "charisma": lambda r: r.deep_life.role_scribe_historian_charisma},
        ),
        NotableRole(
            "cartographer",
            "Cartographer",
            "cartographer",
            MortalRole.EXPLORER,
            {"intellect": lambda r: r.deep_life.role_scribe_cartographer_intellect, "agility": lambda r: r.deep_life.role_scribe_cartographer_agility},
        ),
    ),
    SocialClass.NOBLE: (
        NotableRole("lord", "Lord", "landholder", MortalRole.RULER, {"charisma": lambda r: r.deep_life.role_noble_lord_charisma}),
        NotableRole("knight", "Knight", "knight", MortalRole.KNIGHT, {"strength": lambda r: r.deep_life.role_noble_knight_strength}),
    ),
    SocialClass.SERF_OR_SLAVE: (NotableRole("bondsman", "Bondsman", "bondsman", MortalRole.COMMONER, {"strength": lambda r: r.deep_life.role_serf_strength}),),
    SocialClass.OUTCAST: (
        NotableRole("beggar", "Beggar", "beggar", MortalRole.COMMONER, {"charisma": lambda r: r.deep_life.role_outcast_charisma}),
        NotableRole("outlaw", "Outlaw", "outlaw", MortalRole.BANDIT, {"agility": lambda r: r.deep_life.role_outcast_outlaw_agility}),
    ),
    SocialClass.MONASTIC: (NotableRole("monk", "Brother", "monk", MortalRole.SAGE, {"intellect": lambda r: r.deep_life.role_monastic_intellect}),),
}

RULER_TITLES: dict[EntityType, tuple[str, str]] = {
    EntityType.CULT: ("High Priest", "high priest"),
    EntityType.FACTION: ("Leader", "leader"),
    EntityType.PEOPLE: ("Chieftain", "chieftain"),
    EntityType.SETTLEMENT: ("Sovereign", "sovereign"),
}


@dataclass(frozen=True)
class BirthPlan:
    name: str
    subtype: str
    role: MortalRole
    body: str
    biases: Mapping[str, int] = field(default_factory=dict)
    extra_lifespan: int = 0
    flags: tuple[EntityFlag, ...] = ()


async def born_mortal(ctx: TickContext, community: EntityRow, plan: BirthPlan, namer: Namer | None = None) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(seed_of("born", community.id, plan.subtype, plan.name))
    stats = {key: clamp_int(life.birth_stat_base + plan.biases.get(key, 0) + rng.die(life.birth_stat_die), 0, PERCENT) for key in STAT_KEYS}
    language_name = await (namer or Namer(ctx.session, ctx.rules)).person(
        [community], seed_of(community.id, ctx.epoch, plan.subtype, rng.below(PERCENT * PERCENT))
    )
    lifespan = life.birth_lifespan_base + rng.die(life.birth_lifespan_die) + plan.extra_lifespan
    age = round_half_up(lifespan * (life.birth_age_min_pct / PERCENT + rng.random() * life.birth_age_range_pct / PERCENT))
    flags = plan.flags + ((EntityFlag.NAME_FROM_LANGUAGE,) if language_name else ())
    mortal = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.MORTAL,
            name=language_name or plan.name,
            body=plan.body,
            stats=MortalStats(hp=life.birth_hp, age=age, lifespan=min(lifespan, life.lifespan_cap), **stats),
            power=clamp_int(round_half_up(community.power_level * life.birth_power_share_pct / PERCENT) + 1, 1, life.birth_power_max),
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            world_id=community.world_id,
            subtype=plan.subtype,
            mortal_role=plan.role,
            title=plan.name if language_name else None,
            flags=flags,
        ),
    )
    await connect(ctx.session, mortal.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch)
    await connect(ctx.session, mortal.id, community.id, BondKind.PROTECTS, ctx.epoch)
    patron = await living_patron(ctx.session, community)
    if patron is not None:
        await connect(ctx.session, mortal.id, patron.id, BondKind.WORSHIPS, ctx.epoch)
    language = await spoken_language(ctx.session, community.id)
    if language is not None:
        await connect(ctx.session, mortal.id, language.id, BondKind.SPEAKS, ctx.epoch)
    ctx.count("mortals_born")
    return mortal


async def has_ruler(ctx: TickContext, target_id: int, except_id: int | None = None) -> bool:
    for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[target_id]):
        if bond.source_node_id != except_id and await living_entity(ctx.session, bond.source_node_id) is not None:
            return True
    return False


async def single_rule(ctx: TickContext) -> int:
    closed = 0
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        bonds = []
        for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[community.id]):
            if await living_entity(ctx.session, bond.source_node_id) is not None:
                bonds.append(bond)
        if len({bond.source_node_id for bond in bonds}) <= 1:
            continue
        newest_first = sorted(bonds, key=lambda bond: bond.id, reverse=True)
        keep = next((bond for bond in newest_first if bond.role is not BondRole.HOMELAND), newest_first[0])
        for bond in newest_first:
            if bond.id == keep.id or bond.source_node_id == keep.source_node_id:
                continue
            await close(ctx.session, bond, ctx.epoch, "single ruler")
            closed += 1
            if bond.role is BondRole.HOMELAND and not await active_bonds(
                ctx.session, [BondKind.LIVES_IN], sources=[bond.source_node_id], targets=[community.id]
            ):
                await BondRepository(ctx.session).connect(
                    BondDraft(bond.source_node_id, community.id, BondKind.LIVES_IN, ctx.epoch, "homeland", role=BondRole.HOMELAND)
                )
    return closed


async def birthed_people(ctx: TickContext, settlement_id: int) -> bool:
    for bond in await active_bonds(ctx.session, [BondKind.RULES, BondKind.LIVES_IN], targets=[settlement_id]):
        source = await living_entity(ctx.session, bond.source_node_id)
        if bond.role is BondRole.HOMELAND and source is not None and source.entity_type is EntityType.PEOPLE:
            return True
    for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[settlement_id]):
        ancestor = await living_entity(ctx.session, bond.target_node_id)
        if ancestor is not None and ancestor.entity_type is EntityType.PEOPLE:
            for divergence in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[ancestor.id]):
                if divergence.description == DIVERGENCE:
                    return True
    return False


def pick_class(rng_value: float, shares: Mapping[SocialClass, float]) -> SocialClass:
    total = sum(max(0.0, value) for value in shares.values())
    if total <= 0:
        return SocialClass.FARMER
    threshold = rng_value * total
    running = 0.0
    for social_class in SocialClass:
        running += max(0.0, shares.get(social_class, 0.0))
        if threshold < running:
            return social_class
    return SocialClass.FARMER


def notable_plan(rules: Rules, community: EntityRow, social_class: SocialClass, role: NotableRole) -> BirthPlan:
    circle = from_among(community.name, SOCIAL_CLASSES[social_class].plural.lower())
    return BirthPlan(
        name=f"{community.name} {role.suffix}",
        subtype=role.subtype,
        role=role.role,
        body=f"{sentence_case(indefinite(role.subtype))} whose name is spoken arose {circle}.",
        biases={key: bias(rules) for key, bias in role.biases.items()},
        extra_lifespan=rules.deep_life.notable_warrior_lifespan_bonus if social_class is SocialClass.WARRIOR else 0,
    )


async def raise_notable(ctx: TickContext, community: EntityRow, social_class: SocialClass, role: NotableRole, namer: Namer | None = None) -> EntityRow:
    plan = notable_plan(ctx.rules, community, social_class, role)
    mortal = await born_mortal(ctx, community, plan, namer)
    circle = from_among(community.name, SOCIAL_CLASSES[social_class].plural.lower())
    await note(
        ctx,
        f"{sentence_case(indefinite(role.subtype))} whose name is spoken arose {circle}: {mortal.name}.",
        key="births.notable",
        ids=[community.id, mortal.id],
    )
    return mortal


async def notables(ctx: TickContext, namer: Namer) -> None:
    rules = ctx.rules
    life = rules.deep_life
    rng = ctx.rng("notables")
    communities = await canon(ctx.session, SOCIETY_TYPES)
    cap = clamp_int(math.ceil(len(communities) * life.notable_cap_share_pct / PERCENT), life.notable_cap_min, rules.deep_world.notable_cap)
    born = 0
    for community in rng.shuffled(communities):
        if born >= cap:
            return
        population = stat(community, "population") or 0
        if population < rules.deep_world.notable_min_population:
            continue
        crowd = math.log10(max(1, population))
        living = await descendants(ctx.session, community.id, [EntityType.MORTAL])
        if len(living) >= life.notable_alive_base + math.floor(crowd):
            continue
        chance = rules.deep_world.notable_chance + PERCENT * min(life.notable_crowd_max_pct / PERCENT, crowd / life.notable_crowd_divisor)
        if not rng.chance(chance):
            continue
        social_class = pick_class(rng.random(), await class_shares(ctx.session, rules, community.id))
        demand = await healer_demand(ctx, community)
        roles = NOTABLE_ROLES[social_class]
        pick = weighted(rng, {index: demand if role.role is MortalRole.HEALER else 1.0 for index, role in enumerate(roles)})
        await raise_notable(ctx, community, social_class, roles[pick] if pick is not None else rng.pick(roles), namer)
        born += 1


async def crown(ctx: TickContext, community: EntityRow, namer: Namer | None = None) -> EntityRow:
    life = ctx.rules.deep_life
    suffix, _ = RULER_TITLES[community.entity_type]
    subtype = ruler_role(ctx.rules, community, await class_shares(ctx.session, ctx.rules, community.id), ctx.rng(seed_of("ruler_role", community.id)))
    plan = BirthPlan(
        name=f"{community.name} {suffix}",
        subtype=subtype,
        role=MortalRole.RULER,
        body=f"Took the throne of {community.name} as {subtype}.",
        biases={"charisma": life.ruler_charisma_bias, "intellect": life.ruler_intellect_bias},
        extra_lifespan=life.ruler_lifespan_bonus,
    )
    ruler = await born_mortal(ctx, community, plan, namer)
    await connect(ctx.session, ruler.id, community.id, BondKind.RULES, ctx.epoch, description="took the throne")
    await note(ctx, f"{ruler.name} took the throne of {community.name} as {subtype}.", key="births.ruler", ids=[community.id, ruler.id])
    return ruler


async def rulers(ctx: TickContext, namer: Namer) -> None:
    world_rules = ctx.rules.deep_world
    rng = ctx.rng("rulers")
    crowned = 0
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        if crowned >= world_rules.ruler_cap:
            return
        if community.entity_type is not EntityType.FACTION and headcount(community) < world_rules.ruler_min_population:
            continue
        if await has_ruler(ctx, community.id) or not rng.chance(world_rules.ruler_chance):
            continue
        await crown(ctx, community, namer)
        crowned += 1


async def kin_settlements(ctx: TickContext, atlas: RegionAtlas, people: EntityRow) -> list[EntityRow]:
    language = await spoken_language(ctx.session, people.id)
    region = atlas.top_region(people.id)
    found = []
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT], people.world_id):
        if atlas.top_region(settlement.id) != region:
            continue
        descends = bool(await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[settlement.id], targets=[people.id]))
        speaks = language is not None and bool(await active_bonds(ctx.session, [BondKind.SPEAKS], sources=[settlement.id], targets=[language.id]))
        if descends or speaks:
            found.append(settlement)
    return found


async def homeland_rule(ctx: TickContext, people: EntityRow, settlement: EntityRow) -> None:
    await BondRepository(ctx.session).connect(BondDraft(people.id, settlement.id, BondKind.RULES, ctx.epoch, "own people's homeland", role=BondRole.HOMELAND))


async def found_settlement(
    ctx: TickContext, atlas: RegionAtlas, people: EntityRow, region: EntityRow, *, migrants: int, existing: int, namer: Namer
) -> EntityRow:
    life = ctx.rules.deep_life
    floor, _ = headcount_bounds(ctx.rules, people)
    set_stats(people, population=max(floor, (stat(people, "population") or 0) - migrants))
    reason = f"when {people.name} grew crowded"
    ruin = await resettle_ruin(ctx, region, people, migrants, reason, atlas=atlas)
    if ruin is not None:
        if not await has_ruler(ctx, ruin.id):
            await homeland_rule(ctx, people, ruin)
        await note(
            ctx, f"{people.name} grew crowded; they settled the ruin of {ruin.name} and rebuilt it.", key="births.village_ruin", ids=[people.id, ruin.id]
        )
        return ruin
    name = await namer.from_speaker(people.id, seed_of(people.id, ctx.epoch, "village", existing), NameKind.PLACE)
    subtype = VILLAGE_SUBTYPE if existing else HOMELAND_SUBTYPE
    piety = stat(people, "piety")
    settlement = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.SETTLEMENT,
            name=name or f"{people.name} {'Village' if existing else 'Homeland'}",
            body=f"{people.name} grew crowded; {migrants} people founded a new settlement in {region.name}.",
            stats=SettlementStats(
                population=migrants,
                prosperity=life.village_prosperity,
                defense=life.village_defense,
                piety=piety if piety is not None else ctx.rules.society.default_stat,
            ),
            power=max(life.derived_min_power, people.power_level - 1),
            location_id=people.location_id if people.location_id is not None else region.id,
            world_id=people.world_id,
            subtype=subtype,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if name else (),
        ),
    )
    atlas.remember(settlement)
    await connect(ctx.session, settlement.id, people.id, BondKind.DESCENDS_FROM, ctx.epoch)
    await homeland_rule(ctx, people, settlement)
    language = await spoken_language(ctx.session, people.id)
    if language is not None:
        await connect(ctx.session, settlement.id, language.id, BondKind.SPEAKS, ctx.epoch)
    patron = await living_patron(ctx.session, people)
    if patron is not None:
        await connect(ctx.session, settlement.id, patron.id, BondKind.WORSHIPS, ctx.epoch)
    await bind_language_and_faith(ctx, settlement, atlas, people)
    await note(
        ctx, f"{people.name} grew crowded; they founded a new settlement in {region.name}.", key="births.village", ids=[people.id, settlement.id, region.id]
    )
    ctx.count("villages")
    return settlement


def village_migrants(rules: Rules, population: int) -> int:
    world_rules = rules.deep_world
    wanted = max(world_rules.village_min_population, round_half_up(population * rules.deep_life.village_migration_pct / PERCENT))
    return min(wanted, max(0, population - world_rules.village_people_remainder))


async def villages(ctx: TickContext, atlas: RegionAtlas, namer: Namer) -> None:
    rules = ctx.rules
    world_rules = rules.deep_world
    life = rules.deep_life
    rng = ctx.rng("villages")
    founded = 0
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        if founded >= life.village_cap:
            return
        population = stat(people, "population") or 0
        region = await living_entity(ctx.session, atlas.top_region(people.id))
        if population < world_rules.first_village_population or region is None:
            continue
        existing = len(await kin_settlements(ctx, atlas, people))
        if existing and population < world_rules.extra_village_population:
            continue
        if existing >= math.ceil(population / world_rules.people_per_village):
            continue
        if not rng.chance(life.extra_village_chance if existing else life.first_village_chance):
            continue
        migrants = village_migrants(rules, population)
        if migrants < world_rules.village_min_population:
            continue
        await found_settlement(ctx, atlas, people, region, migrants=migrants, existing=existing, namer=namer)
        founded += 1


async def ethnogenesis(ctx: TickContext, atlas: RegionAtlas, settlement: EntityRow, ancestor: EntityRow, namer: Namer) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(seed_of("ethnogenesis", settlement.id))
    population = stat(settlement, "population") or 0
    split = round_half_up(population * min(PERCENT, life.ethnogenesis_population_pct) / PERCENT)
    region = await living_entity(ctx.session, atlas.top_region(settlement.id))
    name = await namer.from_speaker(settlement.id, seed_of(settlement.id, ctx.epoch, "people"), NameKind.PEOPLE)
    piety = stat(settlement, "piety")
    people = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=name or f"People of {settlement.name}",
            body=(
                f"Rooted in {region.name if region else settlement.name} and descended from {ancestor.name}, the people of {settlement.name} "
                "became a distinct folk over generations, with its own customs, its own tongue and its own name."
            ),
            stats=PeopleStats(
                population=max(ctx.rules.limits.people_population_floor, split),
                martiality=clamp_int(life.ethno_stat_base + rng.die(life.ethno_stat_die), 0, PERCENT),
                magic=clamp_int(rng.die(life.ethno_magic_die), 0, PERCENT),
                craft=clamp_int(life.ethno_stat_base + rng.die(life.ethno_stat_die), 0, PERCENT),
                piety=piety if piety is not None else ctx.rules.society.default_stat,
            ),
            power=max(life.derived_min_power, settlement.power_level),
            location_id=region.id if region is not None else settlement.location_id,
            world_id=settlement.world_id,
            subtype=NEW_PEOPLE_SUBTYPE,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if name else (),
        ),
    )
    floor, cap = headcount_bounds(ctx.rules, settlement)
    set_stats(settlement, population=clamp_int(population - split, floor, cap))
    await connect(ctx.session, people.id, ancestor.id, BondKind.DESCENDS_FROM, ctx.epoch, description=DIVERGENCE)
    await connect(ctx.session, settlement.id, people.id, BondKind.DESCENDS_FROM, ctx.epoch)
    await BondRepository(ctx.session).connect(BondDraft(people.id, settlement.id, BondKind.LIVES_IN, ctx.epoch, "homeland", role=BondRole.HOMELAND))
    language = await spoken_language(ctx.session, settlement.id)
    if language is not None:
        await connect(ctx.session, people.id, language.id, BondKind.SPEAKS, ctx.epoch)
    patron = await living_patron(ctx.session, settlement)
    if patron is not None:
        await connect(ctx.session, people.id, patron.id, BondKind.WORSHIPS, ctx.epoch)
    atlas.remember(people)
    await bind_language_and_faith(ctx, people, atlas, settlement)
    await note(
        ctx,
        f"Descended from {ancestor.name}, {settlement.name} became a distinct people over generations.",
        key="births.ethnogenesis",
        ids=[settlement.id, people.id, ancestor.id],
    )
    ctx.count("new_peoples")
    return people


async def first_ancestor(ctx: TickContext, settlement: EntityRow) -> EntityRow | None:
    bonds = await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[settlement.id])
    return await living_entity(ctx.session, bonds[0].target_node_id) if bonds else None


async def ethnogeneses(ctx: TickContext, atlas: RegionAtlas, namer: Namer) -> int:
    world_rules = ctx.rules.deep_world
    rng = ctx.rng("ethnogenesis")
    born = 0
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if born >= ctx.rules.deep_life.new_people_cap:
            break
        if (
            ctx.epoch - settlement.birth_epoch < world_rules.ethnogenesis_min_age
            or (stat(settlement, "population") or 0) < world_rules.ethnogenesis_min_population
        ):
            continue
        ancestor = await first_ancestor(ctx, settlement)
        if ancestor is None or ancestor.entity_type not in SOCIETY_TYPES:
            continue
        region, ancestor_region = atlas.top_region(settlement.id), atlas.top_region(ancestor.id)
        if region is None or ancestor_region is None or region == ancestor_region:
            continue
        own, parent = await culture_of(ctx.session, settlement.id), await culture_of(ctx.session, ancestor.id)
        if own and parent and value_distance(own, parent) < ctx.rules.peoples.ethnogenesis_distance:
            continue
        if await birthed_people(ctx, settlement.id) or not rng.chance(world_rules.ethnogenesis_chance):
            continue
        await ethnogenesis(ctx, atlas, settlement, ancestor, namer)
        born += 1
    return born


async def uplift(ctx: TickContext, atlas: RegionAtlas, species: EntityRow) -> EntityRow:
    life = ctx.rules.deep_life
    rng = ctx.rng(seed_of("sapience", species.id))
    region_id = atlas.top_region(species.id)
    if region_id is None:
        homes = await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[species.id])
        region_id = homes[0].target_node_id if homes else species.location_id
    strength = stat(species, "strength")
    people = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=f"Lineage of {species.name}",
            body=f"Among the {species.name} a branch arose that learned to speak, to make tools and to bury its dead; it is now a people.",
            stats=PeopleStats(
                population=life.sapient_population_base + rng.die(life.sapient_population_die),
                martiality=clamp_int((strength if strength is not None else life.sapient_default_strength) + rng.die(life.sapient_martiality_die), 0, PERCENT),
                magic=clamp_int(rng.die(life.sapient_magic_die), 0, PERCENT),
                craft=clamp_int(rng.die(life.sapient_craft_die), 0, PERCENT),
                piety=clamp_int(life.sapient_piety_base + rng.die(life.sapient_piety_die), 0, PERCENT),
            ),
            power=max(life.derived_min_power, species.power_level),
            location_id=region_id,
            world_id=species.world_id,
            subtype=SAPIENT_SUBTYPE,
        ),
    )
    await connect(ctx.session, people.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, description="sapience")
    await add_flag(ctx.session, species.id, EntityFlag.SPECIES_BECAME_PEOPLE, ctx.epoch)
    creator = await living_son(ctx.session, species.creator_son_id)
    if creator is not None:
        await connect(ctx.session, people.id, creator.id, BondKind.WORSHIPS, ctx.epoch, description="its creator")
    atlas.remember(people)
    await bind_language_and_faith(ctx, people, atlas)
    await note(
        ctx,
        f"A branch that learned to speak arose among the {species.name}; it is now a people called {people.name}.",
        key="births.sapience",
        ids=[species.id, people.id],
    )
    ctx.count("new_peoples")
    return people


async def sapience(ctx: TickContext, atlas: RegionAtlas, already: int) -> None:
    life = ctx.rules.deep_life
    rng = ctx.rng("sapience")
    born = already
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        if born >= life.new_people_cap:
            return
        if (stat(species, "intelligence") or 0) < life.sapience_min_intelligence or await has_flag(ctx.session, species.id, EntityFlag.SPECIES_BECAME_PEOPLE):
            continue
        if not rng.chance(ctx.rules.deep_world.sapience_chance):
            continue
        await uplift(ctx, atlas, species)
        born += 1


@reads(
    "cult.followers",
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "species.intelligence",
    "table.bonds",
    "table.community_societies",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.language_profiles",
    "table.lexemes",
    "table.maimed_cohorts",
    "table.name_registry",
    "table.nodes",
    "table.world_maps",
)
@writes(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.name_registry",
)
@reads("cult.followers", "people.piety", "people.population", "settlement.piety", "settlement.population", "species.intelligence")
@writes("people.population", "settlement.population")
async def spontaneous_births(ctx: TickContext) -> None:
    await single_rule(ctx)
    namer = Namer(ctx.session, ctx.rules)
    atlas = await RegionAtlas.load(ctx.session)
    await notables(ctx, namer)
    await rulers(ctx, namer)
    await villages(ctx, atlas, namer)
    born = await ethnogeneses(ctx, atlas, namer)
    await sapience(ctx, atlas, born)


def inherited(rules: Rules, first: EntityRow, second: EntityRow, key: str) -> int:
    default = rules.world_effects.inheritance_default_stat
    return (stat(first, key) or default) + (stat(second, key) or default)


async def bear_child(ctx: TickContext, first: EntityRow, second: EntityRow, namer: Namer | None = None) -> EntityRow:
    effects = ctx.rules.world_effects
    rng = ctx.rng(seed_of("child", first.id, second.id))
    deviation = effects.inheritance_deviation

    def averaged(key: str) -> int:
        total = inherited(ctx.rules, first, second, key)
        return clamp_int(total / 2 + rng.integer(-deviation, deviation), 0, PERCENT)

    lifespans = (stat(first, "lifespan") or effects.default_lifespan) + (stat(second, "lifespan") or effects.default_lifespan)
    child_namer = namer or Namer(ctx.session, ctx.rules)
    name = await child_namer.person([first], seed_of(first.id, second.id, ctx.epoch, CHILD_SUBTYPE)) or await child_namer.person(
        [second], seed_of(second.id, first.id, ctx.epoch, CHILD_SUBTYPE)
    )
    child = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.MORTAL,
            name=name or f"Child of {first.name} and {second.name}",
            body=f"A child was born from the union of {first.name} and {second.name}.",
            stats=MortalStats(
                hp=effects.child_hp,
                strength=averaged("strength"),
                agility=averaged("agility"),
                intellect=averaged("intellect"),
                charisma=averaged("charisma"),
                age=0,
                lifespan=clamp_int(lifespans / 2 + rng.integer(-deviation, deviation), effects.child_min_lifespan, ctx.rules.deep_life.lifespan_cap),
            ),
            power=max(1, round_half_up((first.power_level + second.power_level) / 2) - 1),
            location_id=first.location_id,
            world_id=first.world_id,
            subtype=CHILD_SUBTYPE,
            mortal_role=MortalRole.COMMONER,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if name else (),
        ),
    )
    for parent in (first, second):
        await connect(ctx.session, child.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch)
    language = await spoken_language(ctx.session, first.id) or await spoken_language(ctx.session, second.id)
    if language is not None:
        await connect(ctx.session, child.id, language.id, BondKind.SPEAKS, ctx.epoch)
    patron = await living_patron(ctx.session, first) or await living_patron(ctx.session, second)
    if patron is not None:
        await connect(ctx.session, child.id, patron.id, BondKind.WORSHIPS, ctx.epoch)
    await note(ctx, f"A child of {first.name} and {second.name} was born.", key="births.child", ids=[first.id, second.id, child.id])
    ctx.count("children")
    return child


@reads("table.bodies", "table.bonds", "table.traits")
async def couples_bear_children(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    namer = Namer(ctx.session, rules)
    bonds = await BondIndex.load(ctx.session, COUPLE_KINDS)
    born = 0
    seen: set[frozenset[int]] = set()
    for bond in bonds.bonds:
        if born >= rules.world_effects.birth_cap:
            return
        pair = frozenset((bond.source_node_id, bond.target_node_id))
        if pair in seen:
            continue
        seen.add(pair)
        first = await living_entity(ctx.session, bond.source_node_id)
        second = await living_entity(ctx.session, bond.target_node_id)
        if first is None or second is None or first.entity_type is not EntityType.MORTAL or second.entity_type is not EntityType.MORTAL:
            continue
        fertile = await factor(ctx.session, first.id, Capacity.FERTILITY) * await factor(ctx.session, second.id, Capacity.FERTILITY)
        for parent in (first, second):
            fertile *= scaled_by(await effect_of(ctx.session, parent.id, TraitEffect.FERTILITY, rules.traits.effect_scale_pct))
        if not rng.chance(rules.world_engine.birth_chance * fertile):
            continue
        await bear_child(ctx, first, second, namer)
        born += 1


async def require_living(ctx: TickContext, entity_id: int, types: frozenset[EntityType], label: str) -> EntityRow:
    found = await living_entity(ctx.session, entity_id)
    if found is None or found.entity_type not in types:
        raise ValidationFailedError(f"{label} must be a living record of the right kind.")
    return found


async def bless_with_child(ctx: TickContext, first_id: int, second_id: int) -> EntityRow:
    mortals = frozenset({EntityType.MORTAL})
    first = await require_living(ctx, first_id, mortals, "The first parent")
    second = await require_living(ctx, second_id, mortals, "The second parent")
    if first.id == second.id:
        raise ValidationFailedError("A child needs two parents.")
    return await bear_child(ctx, first, second)


async def raise_notable_by_hand(ctx: TickContext, community_id: int, social_class: SocialClass | None = None, role_key: str | None = None) -> EntityRow:
    community = await require_living(ctx, community_id, frozenset(SOCIETY_TYPES), "The community")
    rng = ctx.rng(seed_of("notable_by_hand", community.id))
    chosen_class = social_class or pick_class(rng.random(), await class_shares(ctx.session, ctx.rules, community.id))
    roles = NOTABLE_ROLES[chosen_class]
    role = next((item for item in roles if item.key == role_key), None) if role_key else rng.pick(roles)
    if role is None:
        raise ValidationFailedError(f"No {role_key} role exists among the {SOCIAL_CLASSES[chosen_class].plural.lower()}.")
    return await raise_notable(ctx, community, chosen_class, role)


async def crown_ruler(ctx: TickContext, community_id: int) -> EntityRow:
    community = await require_living(ctx, community_id, frozenset(COMMUNITY_TYPES), "The community")
    if await has_ruler(ctx, community.id):
        raise ValidationFailedError(f"{community.name} already has a ruler.")
    return await crown(ctx, community)


async def order_village(ctx: TickContext, people_id: int) -> EntityRow:
    people = await require_living(ctx, people_id, frozenset({EntityType.PEOPLE}), "The people")
    atlas = await RegionAtlas.load(ctx.session)
    region = await living_entity(ctx.session, atlas.top_region(people.id))
    if region is None:
        raise ValidationFailedError(f"{people.name} lives in no region.")
    migrants = village_migrants(ctx.rules, stat(people, "population") or 0)
    if migrants < ctx.rules.deep_world.village_min_population:
        raise ValidationFailedError(f"{people.name} is too small to send out settlers.")
    existing = len(await kin_settlements(ctx, atlas, people))
    return await found_settlement(ctx, atlas, people, region, migrants=migrants, existing=existing, namer=Namer(ctx.session, ctx.rules))


async def trigger_ethnogenesis(ctx: TickContext, settlement_id: int) -> EntityRow:
    settlement = await require_living(ctx, settlement_id, frozenset({EntityType.SETTLEMENT}), "The settlement")
    ancestor = await first_ancestor(ctx, settlement)
    if ancestor is None:
        raise ValidationFailedError(f"{settlement.name} descends from no living community.")
    if await birthed_people(ctx, settlement.id):
        raise ValidationFailedError(f"A people already sprang from {settlement.name}.")
    return await ethnogenesis(ctx, await RegionAtlas.load(ctx.session), settlement, ancestor, Namer(ctx.session, ctx.rules))


async def awaken_species(ctx: TickContext, species_id: int) -> EntityRow:
    species = await require_living(ctx, species_id, frozenset({EntityType.SPECIES}), "The species")
    if await has_flag(ctx.session, species.id, EntityFlag.SPECIES_BECAME_PEOPLE):
        raise ValidationFailedError(f"{species.name} already became a people.")
    return await uplift(ctx, await RegionAtlas.load(ctx.session), species)


COUPLE_PHASES = (Phase("couple_births", couples_bear_children),)
SPONTANEOUS_PHASES = (Phase("spontaneous_births", spontaneous_births),)
PHASES = COUPLE_PHASES + SPONTANEOUS_PHASES
