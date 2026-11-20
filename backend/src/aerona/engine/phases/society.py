from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held as frozen
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathBreach, OathKind, RevoltKind
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import may_wed
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.drives import unrest
from aerona.engine.phase import Phase
from aerona.engine.phases.society_support.community import CommunityBook
from aerona.engine.polity.oaths import break_on
from aerona.engine.polity.revolt_causes import revolt_kind
from aerona.engine.polity.revolts import REVOLTS, seed_aims
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.war import declare_war, uprising_target

BOOTSTRAP_EXCLUDED_FLAGS = (EntityFlag.GODLESS, EntityFlag.WORSHIPS_PLANET)
REBELS_SUBTYPE = "rebels"


@reads(
    "table.bonds",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.nodes",
    "table.sons",
    "table.stars",
    "table.world_maps",
    "table.worlds",
)
@writes("table.bonds")
async def language_and_faith(ctx: TickContext) -> None:
    session = ctx.session
    excluded: set[int] = set()
    for flag in BOOTSTRAP_EXCLUDED_FLAGS:
        excluded |= await flags_by_entity(session, flag)
    seeking = await flags_by_entity(session, EntityFlag.SEEKING_GOD)
    bonds = BondRepository(session)
    bound = 0
    atlas = await RegionAtlas.load(session)
    for community in await canon(session, COMMUNITY_TYPES):
        if community.id in excluded:
            continue
        speaks = bool(await bonds.outgoing(community.id, BondKind.SPEAKS))
        worships = bool(await bonds.outgoing(community.id, BondKind.WORSHIPS))
        if speaks and (worships or community.id in seeking):
            continue
        await bind_language_and_faith(ctx, community, atlas)
        bound += 1
    ctx.count("bound", bound)


def _just_law_present(book: CommunityBook, settlement: EntityRow, threshold: int) -> bool:
    return any(value >= threshold for value in book.justice_values(settlement.id))


async def raise_rebels(ctx: TickContext, settlement: EntityRow, book: CommunityBook, entities: dict[int, EntityRow]) -> EntityRow:
    settings = ctx.rules.society
    rng = ctx.rng(f"rebels.{settlement.id}")
    kind = await revolt_kind(ctx, settlement)
    risen = round_half_up((stat(settlement, "population") or 0) * ctx.rules.revolts.rebel_share_pct / PERCENT)
    rebels = await create_record(
        ctx,
        RecordSpec(
            name=f"{settlement.name} Rebels" if kind is RevoltKind.PEASANT else f"the {spoken(kind)} revolt of {settlement.name}",
            entity_type=EntityType.FACTION,
            stats=FactionStats(
                strength=clamp_int(settings.rebel_strength_base + rng.die(settings.rebel_strength_die) + risen // 100, 0, PERCENT),
                wealth=clamp_int(settings.rebel_wealth_base + rng.die(settings.rebel_wealth_die), 0, PERCENT),
                sway=clamp_int(settings.rebel_sway_base + rng.die(settings.rebel_sway_die), 0, PERCENT),
            ),
            body=f"{REVOLTS[kind].text.capitalize()} in {settlement.name} turned into an uprising.",
            power=settings.rebel_power,
            world_id=settlement.world_id,
            location_id=settlement.id,
            subtype=REBELS_SUBTYPE if kind is RevoltKind.PEASANT else f"{kind.value} revolt",
            engine_kind=EngineKind.REBELS,
            social_class=REVOLTS[kind].rising,
            affiliated_entity_id=settlement.id,
        ),
    )
    target = await uprising_target(ctx.session, settlement)
    sworn = list(
        await ctx.session.scalars(
            select(EntityRow.id).where(
                EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_of(ctx.session, settlement)
            )
        )
    )
    await break_on(ctx, sworn, OathKind.FEALTY, OathBreach.TOWN_REVOLTED, occasion=settlement.id)
    cause = REVOLTS[kind].cause
    if await declare_war(ctx, rebels.id, target.id, f"{kind.value} revolt", cause=cause, world_cap=False):
        await seed_aims(ctx, rebels.id, target.id, REVOLTS[kind].aims)
    language = await spoken_language(ctx.session, settlement.id)
    if language is not None:
        await BondRepository(ctx.session).connect(BondDraft(rebels.id, language.id, BondKind.SPEAKS, ctx.epoch, "the tongue of the city"))
    unknown = ctx.rules.world_effects.unknown_stat
    shift_stat(settlement, "defense", -settings.poverty_revolt_defense_loss, unknown)
    shift_stat(settlement, "prosperity", -settings.poverty_revolt_prosperity_loss, unknown)
    rulers = [entities[bond.source_node_id] for bond in book.bonds.incoming(settlement.id, BondKind.RULES) if bond.source_node_id in entities]
    await record_incident(
        ctx,
        "society.poverty_uprising",
        roles={IncidentRole.PLACE: settlement.id, IncidentRole.ACTOR: rebels.id, IncidentRole.TARGET: rulers[0].id if rulers else None},
        facts={"defense_lost": settings.poverty_revolt_defense_loss, "prosperity_lost": settings.poverty_revolt_prosperity_loss},
        place=settlement.id,
    )
    return rebels


@reads(
    "law.justice",
    "polity.subjects",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.ciphers",
    "table.claims",
    "table.community_societies",
    "table.cosmos",
    "table.creator",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.power_registry",
    "table.pressures",
    "table.professions_of_value",
    "table.reputations",
    "table.secrets",
    "table.settlement_profiles",
    "table.signal_links",
    "table.sons",
    "table.stars",
    "table.tax_policies",
    "table.tradition_profiles",
    "table.traits",
    "table.tributes",
    "table.vassalages",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "settlement.defense",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incident_terms",
    "table.incidents",
    "table.memories",
    "table.messages",
    "table.mortal_profiles",
    "table.name_registry",
    "table.oaths",
    "table.professions_of_value",
    "table.reputations",
    "table.secrets",
    "table.traits",
    "table.war_aims",
)
async def uprisings(ctx: TickContext) -> None:
    settings = ctx.rules.society
    session = ctx.session
    settlements = await canon(session, [EntityType.SETTLEMENT])
    threshold = relative_threshold(
        settlements, "population", fraction(settings.poverty_revolt_top_pct), settings.poverty_revolt_min_population, settings.poverty_revolt_always_population
    )
    entities = {entity.id: entity for entity in await canon(session)}
    book = await CommunityBook.load(session)
    rng = ctx.rng("uprising")
    raised = 0
    for settlement in settlements:
        pressed = await pressures_of(session, settlement.id)
        town = await session.get(SettlementProfileRow, settlement.id)
        if town is not None:
            restless = town.unrest >= ctx.rules.crime.revolt_unrest
        elif pressed:
            restless = await unrest(session, ctx.rules, settlement.id) >= ctx.rules.needs.uprising_pressure
        else:
            restless = stat_or(settlement, "prosperity", ctx.rules.world_effects.unknown_prosperity) < settings.poverty_revolt_prosperity
        if not restless or stat_or(settlement, "population", 0) < threshold(settlement) or frozen(settlement.id):
            continue
        just = _just_law_present(book, settlement, settings.just_law_threshold)
        heat = 1 + max(0, town.unrest - ctx.rules.crime.revolt_unrest) / PERCENT if town is not None else 1.0
        if not rng.chance((settings.poverty_revolt_just_law_chance if just else settings.poverty_revolt_chance) * heat):
            continue
        await raise_rebels(ctx, settlement, book, entities)
        raised += 1
    ctx.count("uprisings", raised)


@reads(
    "mortal.age",
    "table.age_set_members",
    "table.bonds",
    "table.child_standing",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.kin_group_members",
    "table.kin_groups",
    "table.kinship_systems",
    "table.memberships",
    "table.node_births",
    "table.nodes",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.purity",
    "table.sons",
    "table.stars",
    "table.union_customs",
    "table.worlds",
)
@writes("table.bonds", "table.chronicle", "table.chronicle_entities", "table.entities", "table.incident_participants", "table.incidents")
async def love_and_rivalry(ctx: TickContext) -> None:
    settings = ctx.rules.society
    session = ctx.session
    by_place: dict[int, list[EntityRow]] = defaultdict(list)
    for mortal in unheld(await canon(session, [EntityType.MORTAL])):
        age = stat(mortal, "age")
        if mortal.location_id is not None and age is not None and age >= settings.love_min_age:
            by_place[mortal.location_id].append(mortal)
    bonds = BondRepository(session)
    rng = ctx.rng("love")
    formed = 0
    for place in sorted(by_place):
        group = by_place[place]
        for index, first in enumerate(group):
            for second in group[index + 1 :]:
                if await bonds.exists_between(first.id, second.id, BondKind.LOVES) or await bonds.exists_between(first.id, second.id, BondKind.ENEMY):
                    continue
                if not rng.chance(settings.over_epoch(settings.love_rivalry_chance)):
                    continue
                love = rng.chance(settings.love_share_pct)
                if love and not await may_wed(session, ctx.rules, first, second):
                    continue
                await bonds.connect(
                    BondDraft(
                        first.id,
                        second.id,
                        BondKind.LOVES if love else BondKind.ENEMY,
                        ctx.epoch,
                        "love" if love else "rivalry",
                        war_cause=None if love else WarCause.RIVALRY,
                    )
                )
                await record_incident(
                    ctx,
                    "society.love" if love else "society.rivalry",
                    roles={
                        IncidentRole.ACTOR: first.id,
                        IncidentRole.CO_ACTOR: second.id,
                    },
                )
                formed += 1
    ctx.count("pairs", formed)


PHASES = (
    Phase("language_and_faith", language_and_faith),
    Phase("uprisings", uprisings),
    Phase("love_and_rivalry", love_and_rivalry),
)
