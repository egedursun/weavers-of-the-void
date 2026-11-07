from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.demography.promotion import dormant_ids
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import living_minds
from aerona.engine.phase import Phase
from aerona.engine.primitives.queries import living_entity
from aerona.engine.relations.affairs import AffairTally, flag_lovers, tend_affairs
from aerona.engine.relations.book import refresh_kinds
from aerona.engine.relations.circles import CircleTally, tend_circles
from aerona.engine.relations.contests import ContestTally, tend_contests
from aerona.engine.relations.interactions import SocialTally, fade, feel_changes, living_mortals_by_place, socialise
from aerona.engine.relations.passions import PassionTally, tend_passions
from aerona.engine.relations.pecking import PeckingTally, tend_pecking


async def social_mortals(ctx: TickContext) -> list[EntityRow]:
    sleeping = await dormant_ids(ctx)
    return unheld(entity for entity in await living_minds(ctx.session) if entity.entity_type is EntityType.MORTAL and entity.id not in sleeping)


def count(ctx: TickContext, prefix: str, tally: object) -> None:
    for key, value in vars(tally).items():
        if isinstance(value, dict):
            for name, amount in value.items():
                ctx.count(f"{prefix}_{name}", amount)
        else:
            ctx.count(f"{prefix}_{key}", value)


@reads(
    "mortal.age",
    "mortal.agility",
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
    "table.army_officers",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.entity_flags",
    "table.faction_memberships",
    "table.genomes",
    "table.griefs",
    "table.holder_levels",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.needs",
    "table.nodes",
    "table.passions",
    "table.personality_values",
    "table.prostheses",
    "table.relationships",
    "table.reputations",
    "table.skills",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.wants",
)
@writes(
    "mortal.hp",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.injuries",
    "table.memories",
    "table.mortal_profiles",
    "table.persuasions",
    "table.relationships",
    "table.reputations",
    "table.skills",
    "table.thoughts",
)
async def relations_social(ctx: TickContext) -> None:
    mortals = await social_mortals(ctx)
    places = await living_mortals_by_place(ctx, mortals)
    tally, affairs = SocialTally(), AffairTally()
    met: set[tuple[int, int]] = set()
    for place_id, group in sorted(places.items()):
        scene = await socialise(ctx, place_id, group, tally)
        if scene is not None:
            met |= scene.met
    ids = [mortal.id for mortal in mortals]
    ctx.count("relations_faded", await fade(ctx, ids, met))
    for mortal in mortals:
        for row, before, after in await refresh_kinds(ctx.session, ctx.rules, mortal.id, ctx.epoch):
            await feel_changes(ctx, row, before, after)
            affairs.begun += await flag_lovers(ctx, row)
    await tend_affairs(ctx, affairs)
    count(ctx, "social", tally)
    count(ctx, "affair", affairs)


@reads(
    "faction.wealth",
    "table.bonds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.personality_values",
    "table.preferences",
    "table.relationships",
    "table.routes",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.relationships",
    "table.social_circles",
)
async def relations_circles(ctx: TickContext) -> None:
    tally = CircleTally()
    for place_id, group in sorted((await living_mortals_by_place(ctx, await social_mortals(ctx))).items()):
        place = await living_entity(ctx.session, place_id)
        if place is not None:
            await tend_circles(ctx, place, group, tally)
    count(ctx, "circle", tally)


@reads(
    "table.bonds",
    "table.entity_flags",
    "table.house_members",
    "table.memories",
    "table.minds",
    "table.mortal_profiles",
    "table.nodes",
    "table.oaths",
    "table.passions",
    "table.personality_values",
    "table.relationships",
)
@writes("table.passions")
async def relations_passions(ctx: TickContext) -> None:
    tally = PassionTally()
    for mortal in await social_mortals(ctx):
        await tend_passions(ctx, mortal, tally)
    count(ctx, "passion", tally)


@reads(
    "mortal.strength",
    "table.bodies",
    "table.bonds",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.griefs",
    "table.group_ranks",
    "table.house_members",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.needs",
    "table.offices",
    "table.personality_values",
    "table.relationships",
    "table.skills",
    "table.thoughts",
    "table.traits",
    "table.wants",
)
@writes("table.faction_profiles", "table.group_ranks", "table.relationships", "table.thoughts")
async def relations_pecking(ctx: TickContext) -> None:
    tally = PeckingTally()
    await tend_pecking(ctx, tally)
    count(ctx, "pecking", tally)


@reads(
    "table.bonds",
    "table.captives",
    "table.deed_claims",
    "table.deeds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.group_ranks",
    "table.incubating_ideas",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.passions",
    "table.relationships",
    "table.reputations",
    "table.skills",
    "table.thoughts",
)
@writes(
    "table.artwork_profiles",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.contests",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.epoch_year_cursors",
    "table.group_ranks",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.name_registry",
    "table.relationships",
    "table.reputations",
    "table.thoughts",
)
async def relations_contests(ctx: TickContext) -> None:
    tally = ContestTally()
    await tend_contests(ctx, await living_mortals_by_place(ctx, await social_mortals(ctx)), tally)
    count(ctx, "contest", tally)


PHASES = (
    Phase("relations_social", relations_social),
    Phase("relations_circles", relations_circles),
    Phase("relations_passions", relations_passions),
    Phase("relations_pecking", relations_pecking),
    Phase("relations_contests", relations_contests),
)
