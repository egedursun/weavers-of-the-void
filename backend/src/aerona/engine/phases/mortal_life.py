from collections import defaultdict
from itertools import combinations

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.demography.promotion import dormant_ids
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mortal.acts import accumulate_stress, blasphemy, bribe, choose_path, convert, plot, repay, stress_break, update_loyalty
from aerona.engine.mortal.course import (
    backfill_deaths,
    betroth_children,
    educate,
    foster_orphan,
    live_one_epoch,
    match,
    patronise,
    seed_mortal,
    swear_kinship,
    upkeep_standing,
)
from aerona.engine.mortal.equipment import auto_equip
from aerona.engine.mortal.kinship import backfill_kin
from aerona.engine.mortal.learning import learn
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.phase import Phase
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.community_relations import change_relation, relation


async def living_mortals(ctx: TickContext) -> list[EntityRow]:
    sleeping = await dormant_ids(ctx)
    return [mortal for mortal in unheld(await canon(ctx.session, [EntityType.MORTAL])) if mortal.status is EntityStatus.CANON and mortal.id not in sleeping]


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.applied_fixups",
    "table.bodies",
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.injuries",
    "table.item_profiles",
    "table.memories",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.people_biology",
)
@writes(
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.applied_fixups",
    "table.bonds",
    "table.entities",
    "table.marriages",
    "table.mortal_equipment",
    "table.mortal_profiles",
)
async def mortal_survey(ctx: TickContext) -> None:
    ctx.count("kin_backfilled", sum((await backfill_kin(ctx.session, ctx.epoch)).values()))
    created = 0
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if mortal.status is not EntityStatus.CANON:
            continue
        created += 1 if await seed_mortal(ctx, mortal) else 0
        await auto_equip(ctx.session, mortal.id)
    ctx.count("profiles", created)
    ctx.count("deaths_recorded", await backfill_deaths(ctx))


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.age_set_members",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.book_contents",
    "table.charms",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.genomes",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.membership_categories",
    "table.memberships",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.prostheses",
    "table.purity",
    "table.purity_ranks",
    "table.region_environment",
    "table.skills",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
)
@writes(
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.personality_values",
    "table.skills",
    "table.thoughts",
)
async def mortal_life_course(ctx: TickContext) -> None:
    learned = 0
    for mortal in await living_mortals(ctx):
        await live_one_epoch(ctx, mortal)
        profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
        learned += await educate(ctx, mortal, profile)
        learned += await learn(ctx, mortal, profile)
    ctx.count("lessons", learned)


@reads(
    "table.bonds",
    "table.community_relations",
    "table.culture_values",
    "table.entities",
    "table.entity_flags",
    "table.held_identities",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.memories",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.traits",
    "table.wants",
    "table.war_sides",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.marriages",
    "table.memories",
    "table.oaths",
)
async def mortal_kin(ctx: TickContext) -> None:
    counts: dict[str, int] = defaultdict(int)
    for mortal in await living_mortals(ctx):
        profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
        outcome = await match(ctx, mortal, profile)
        if outcome is not None:
            counts[outcome] += 1
        counts["betrothed"] += 1 if await betroth_children(ctx, mortal) else 0
        counts["fostered"] += 1 if await foster_orphan(ctx, mortal, profile) else 0
        counts["sworn"] += 1 if await swear_kinship(ctx, mortal) else 0
    for key, value in counts.items():
        ctx.count(key, value)


@reads(
    "artwork.renown",
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.artwork_profiles",
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.item_profiles",
    "table.memories",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.offices",
    "table.traits",
)
@writes(
    "artwork.renown",
    "table.artwork_profiles",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mortal_equipment",
    "table.mortal_profiles",
)
async def mortal_standing(ctx: TickContext) -> None:
    funded = bribed = 0
    for mortal in await living_mortals(ctx):
        profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
        await upkeep_standing(ctx, mortal, profile)
        funded += 1 if await patronise(ctx, mortal, profile) else 0
        bribed += 1 if await bribe(ctx, mortal, profile) else 0
        await auto_equip(ctx.session, mortal.id)
    ctx.count("patronage", funded)
    ctx.count("bribes", bribed)


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.afflictions",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.charms",
    "table.community_relations",
    "table.conditions",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_values",
    "table.divine_wounds",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.examinations",
    "table.foreign_gods",
    "table.genomes",
    "table.held_identities",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.manumissions",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.needs",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.offices",
    "table.passions",
    "table.people_reproduction",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.prostheses",
    "table.regimes",
    "table.relationships",
    "table.reputations",
    "table.role_norms",
    "table.ruler_currencies",
    "table.skills",
    "table.sons",
    "table.tradition_profiles",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_materials",
)
@writes(
    "mortal.hp",
    "table.afflictions",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.mortal_profiles",
    "table.passions",
    "table.thoughts",
    "table.traits",
)
async def mortal_minds(ctx: TickContext) -> None:
    counts: dict[str, int] = defaultdict(int)
    for mortal in unheld(await living_mortals(ctx)):
        profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
        await update_loyalty(ctx, mortal, profile)
        await accumulate_stress(ctx, mortal, profile)
        broke = await stress_break(ctx, mortal, profile)
        if broke is not None:
            counts[f"break_{broke.value}"] += 1
        if mortal.status is not EntityStatus.CANON:
            continue
        counts["gratitude"] += 1 if await repay(ctx, mortal) else 0
        counts["plots"] += 1 if await plot(ctx, mortal, profile) else 0
        counts["conversions"] += 1 if await convert(ctx, mortal, profile) else 0
        counts["blasphemy_trials"] += 1 if mortal.status is EntityStatus.CANON and await blasphemy(ctx, mortal) else 0
        path = await choose_path(ctx, mortal, profile)
        if path is not None:
            counts[f"career_{path.value}"] += 1
    for key, value in counts.items():
        ctx.count(key, value)


@reads(
    "people.population",
    "table.bonds",
    "table.community_relations",
    "table.culture_values",
    "table.entities",
    "table.memories",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.settlement_profiles",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "people.population",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.polity_profiles",
    "table.settlement_profiles",
)
async def ethnic_relations(ctx: TickContext) -> None:
    table = ctx.rules.ethnic
    book = await RealmBook.load(ctx.session)
    clashes = 0
    for realm in book.realms.values():
        peoples: dict[int, EntityRow] = {}
        towns: dict[int, list[EntityRow]] = defaultdict(list)
        for member in book.members(realm):
            people = await people_of(ctx.session, member)
            if people is None:
                continue
            peoples[people.id] = people
            if member.entity_type is EntityType.SETTLEMENT:
                towns[people.id].append(member)
        for first, second in combinations(sorted(peoples), 2):
            if held(realm.entity.id, first, second):
                continue
            regard = await relation(ctx.session, ctx.rules, first, second)
            if regard >= table.harmony_above:
                await change_relation(ctx, first, second, table.harmony_relation, MemoryKind.GOODWILL, note="neighbours under one crown")
                continue
            if regard >= table.tension_below or not ctx.rng(seed_of("strife", realm.entity.id, first, second, ctx.epoch)).chance(table.strife_chance):
                continue
            await clash(ctx, realm.profile, peoples[first], peoples[second], [*towns[first], *towns[second]])
            clashes += 1
    ctx.count("ethnic_clashes", clashes)


async def clash(ctx: TickContext, profile: PolityProfileRow, first: EntityRow, second: EntityRow, towns: list[EntityRow]) -> None:
    table = ctx.rules.ethnic
    for town in towns:
        row = await ctx.session.get(SettlementProfileRow, town.id)
        if row is not None and "unrest" not in (row.locked or []):
            row.unrest = clamp_int(row.unrest + table.strife_unrest, 0, PERCENT)
    weaker = min((first, second), key=lambda people: (stat(people, "population") or 0, people.id))
    population = stat(weaker, "population") or 0
    set_stats(weaker, population=max(0, population - round_half_up(population * table.strife_population_pct / PERCENT)))
    if "stability" not in (profile.locked or []):
        profile.stability = clamp_int(profile.stability - table.strife_stability, 0, PERCENT)
    await change_relation(ctx, first.id, second.id, -table.strife_magnitude, MemoryKind.FOUGHT_US, note="strife within the realm", reverse=MemoryKind.FOUGHT_US)
    await record(
        ctx,
        "relations.ethnic_strife",
        roles={
            IncidentRole.ACTOR: first.id,
            IncidentRole.OPPONENT: second.id,
            IncidentRole.AUTHORITY: profile.polity_entity_id,
            IncidentRole.PLACE: [town.id for town in towns],
        },
        facts={"unrest": table.strife_unrest, "stability": table.strife_stability, "population_pct": table.strife_population_pct},
        steps=(StepDraft(StepAction.FEUD, actor=first.id, target=second.id),),
    )


SURVEY_PHASES = (Phase("mortal_survey", mortal_survey),)
LIFE_PHASES = (
    Phase("mortal_life_course", mortal_life_course),
    Phase("mortal_kin", mortal_kin),
    Phase("mortal_standing", mortal_standing),
    Phase("mortal_minds", mortal_minds),
    Phase("ethnic_relations", ethnic_relations),
)
PHASES = (*SURVEY_PHASES, *LIFE_PHASES)
