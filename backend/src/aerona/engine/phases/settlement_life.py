from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.community import CommunityBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import canon
from aerona.engine.services.war import ongoing_wars
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import (
    bandits_near,
    build,
    capacities,
    collect_taxes,
    endure_siege,
    festivals_and_alms,
    fires,
    foreigners,
    invest,
    keep_order,
    keep_walls,
    literacy_of,
    pay_soldiers,
    prestige,
    punish,
    remember,
    retier,
    sanitation,
    stir_unrest,
    urban_drift,
    wear,
)

JUSTICE_FULL = 100


@reads(
    "faction.strength",
    "law.justice",
    "people.wealth",
    "settlement.defense",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "structure.splendor",
    "table.armies",
    "table.bonds",
    "table.claims",
    "table.community_cohorts",
    "table.community_labour",
    "table.community_societies",
    "table.culture_values",
    "table.districts",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.memories",
    "table.mortal_repute",
    "table.occupations",
    "table.offices",
    "table.people_culture",
    "table.polity_members",
    "table.pressures",
    "table.quarantines",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sieges",
    "table.trade_flows",
    "table.traits",
    "table.tributes",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "faction.strength",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.army_profiles",
    "table.chronicle",
    "table.chronicle_entities",
    "table.culture_values",
    "table.districts",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.mortal_repute",
    "table.sentences",
    "table.settlement_history",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.settlement_treasury",
)
async def settlement_life(ctx: TickContext) -> None:
    knowledge = await KnowledgeMap.load(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    community = await CommunityBook.load(ctx.session)
    statutes = await LawBook.load(ctx.session)
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        town = await town_of(ctx, settlement, knowledge)
        region = atlas.top_region(settlement.id)
        ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
        people = await people_of(ctx.session, settlement)
        values = await culture_of(ctx.session, people.id) if people is not None else {}
        society = await ctx.session.get(CommunitySocietyRow, settlement.id)
        at_war = bool(await ongoing_wars(ctx.session, settlement.id))
        await capacities(ctx, town, knowledge)
        ctx.count("invested", await invest(ctx, town))
        ctx.count("taxed", await collect_taxes(ctx, town, await literacy_of(ctx, town)))
        if not await pay_soldiers(ctx, town):
            town.profile.public_order = max(0, town.profile.public_order - 5)
        await keep_walls(ctx, town)
        await wear(ctx, town)
        foreign = await foreigners(ctx, town)
        ctx.count("built", await build(ctx, town, knowledge, at_war=at_war, foreign=foreign))
        justice = max(community.justice_values(settlement.id), default=0) / JUSTICE_FULL
        await keep_order(ctx, town, justice=justice, bands=await bandits_near(ctx, atlas, town), hierarchy=values.get(ValueAxis.HIERARCHY, 0))
        ctx.count("punished", 1 if await punish(ctx, town, statutes) else 0)
        festival = festivals_and_alms(ctx, town, society)
        tension = await urban_drift(ctx, town)
        await stir_unrest(ctx, town, tension=tension, festival=festival, region=region)
        ctx.count("fires", await fires(ctx, town, ground, knowledge))
        sanitation(ctx, town, knowledge)
        await endure_siege(ctx, town, values)
        await prestige(ctx, town)
        tier = retier(ctx, town)
        if tier is not None:
            await note(
                ctx,
                f"{settlement.name} is now a {tier.value}.",
                key="settlement.tier",
                ids=[settlement.id],
                kind=ChronicleKind.CIVILIZATION,
            )
        town.profile.updated_epoch = ctx.epoch
        remember(ctx, town)
    await ctx.session.flush()


PHASES = (Phase("settlement_life", settlement_life),)
