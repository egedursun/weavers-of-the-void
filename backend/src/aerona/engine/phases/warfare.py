from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.phases import DUEL_ENDINGS, DUEL_FATES, END_WAR_BY_DECREE_WAR_ENDINGS, SACKED_SACK_CHOICES
from aerona.catalog.life.services import ENDING_LABELS
from aerona.catalog.life_traits import STARVATION_STAGE_TRAITS, having
from aerona.catalog.mind import COMMAND_SKILLS
from aerona.constants.units import PERCENT
from aerona.constants.warfare import BATTLE_NAME_TEMPLATE, SIEGE_NAME_TEMPLATE
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.core.grammar import several, spoken
from aerona.db.faction_kinds import kind_of
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.chronicle import ChronicleRepository, caused_by
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, OccupationRow
from aerona.db.tables.mind import VALUE_MAX
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, SiegeRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import Capacity, Consciousness, HarmCause
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.life_traits import StarvationStageTrait
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.military import BattlePhase, CasualtyFate, CommandArea, DuelContext, DuelEnd, OutcomeClass, SackChoice, Stance
from aerona.domain.enums.mind import ActKind, MemoryKind, ThoughtKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.society import Commodity, NaturalLaw
from aerona.domain.enums.war import BattleOutcome, SiegeStatus, WarCause, WarEnding, WarStatus
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import EventStats
from aerona.domain.models.moment import Moment
from aerona.engine.body.book import effective, strike_style
from aerona.engine.body.cohorts import return_maimed
from aerona.engine.body.customs import people_of
from aerona.engine.body.variants import fear_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import WorldView, world_views
from aerona.engine.couplings.field import parley
from aerona.engine.demography.biology import acclimatised, profiles_of
from aerona.engine.economy.equipment import march_burden, siege_engines, suffer_heat
from aerona.engine.economy.loot import loot_temples
from aerona.engine.environment.battleground import (
    BattleGround,
    attack_factor,
    battle_site,
    defend_factor,
    night_chance,
    omen_morale,
    scar_battlefield,
    season_losses,
)
from aerona.engine.environment.book import EnvironmentBook, add_scar, region_environment, scar_region
from aerona.engine.environment.years import grant_sub_steps
from aerona.engine.equipment.field import main_arms
from aerona.engine.eras.effects import tech_factor
from aerona.engine.forecasting.reading import sky_omens
from aerona.engine.honours.units import HonourTally, disband_units, honour_battle
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.causes import war_cause_incident
from aerona.engine.kinds.nature import sturdiness
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.arms import wear_in_duel
from aerona.engine.lore.rites import warded
from aerona.engine.lore.taboos import dead_season, forbidden, winter_rest
from aerona.engine.military.aftermath import (
    cohesion_after,
    exotic_toll,
    magic_sheet,
    marsh_fever,
    morale_sheet,
    note_casualty,
    raise_the_dead,
    record_stacks,
    recover_wounded,
    send_home_wounded,
    street_toll,
    take_baggage,
)
from aerona.engine.military.aims import REGION_AIMS, advance, set_aims
from aerona.engine.military.alliance import allied_armies, allies_on_side, march_with
from aerona.engine.military.battle import BattleResult, Field
from aerona.engine.military.battle_record import battle_steps
from aerona.engine.military.campaign import bridged, home_news
from aerona.engine.military.causes import raiders
from aerona.engine.military.clash import captives_taken, cautious, clash, earn_traits, learn_tactic, log_phases
from aerona.engine.military.command import command_areas
from aerona.engine.military.duels import bout, crippling, fighter, set_footing, settle_bout
from aerona.engine.military.engineering import earthworks_of
from aerona.engine.military.feuds import house_feud
from aerona.engine.military.finance import pay_contracts
from aerona.engine.military.logistics import March, campaign_season, in_contact, mark_front
from aerona.engine.military.marshal import keep_templates
from aerona.engine.military.naval import SeaFight, sea_battle, weather_the_storm
from aerona.engine.military.occupation import end_occupations, occupy, partisans, seeks_peace, weary
from aerona.engine.military.siege import SiegeSeason, breach_bonus, open_siege, sack, siege_season, wall_defence
from aerona.engine.military.siege_depth import sack_choice
from aerona.engine.military.standards import capture_standard
from aerona.engine.military.support import rally_support
from aerona.engine.military.terms import fights_on, separate_peace, terror
from aerona.engine.military.trials import settle_trial, trial_claims
from aerona.engine.military.units import muster, profile_of, reconcile_sizes, resize, retire_stacks
from aerona.engine.military.upkeep import drill_armies, hire_mercenaries, lost_trade, occupation_levies, occupation_revolts, war_taxes
from aerona.engine.military.vessels import muster_fleet
from aerona.engine.military.war_lines import keep_war_lines
from aerona.engine.mind.book import best_effective, values_for
from aerona.engine.mind.hooks import duelled, fought, judged
from aerona.engine.mind.thoughts import think
from aerona.engine.operations.command import CommandTally, issue_orders
from aerona.engine.operations.supply import Network, SupplyTally, culminate, network, operation_of, supply_season
from aerona.engine.phase import Phase
from aerona.engine.polity.law_effects import standing_floor
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap, LawBook
from aerona.engine.primitives.levies import demobilise, stand_down
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_float, clamp_int, round_half_up
from aerona.engine.primitives.physics import air_attrition_pct
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import set_stats, shift_stat, stat, stat_or
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.recording.moments import incident_moment
from aerona.engine.recording.record import FactInput, record
from aerona.engine.recording.terms import explaining
from aerona.engine.records import death_path
from aerona.engine.renown.currencies import on_victory
from aerona.engine.renown.deeds import acclaim_deed
from aerona.engine.services.casus_belli import gather_casus_belli
from aerona.engine.services.community_relations import change_relation, start_blood_feud
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import (
    OngoingWar,
    army_or_raise,
    can_open_war,
    commander_of,
    declare_war,
    hostile_pairs,
    is_community,
    log_size,
    ongoing_wars,
    open_war,
    raise_army,
    require_ongoing_war,
    take_captive,
    unordered,
    uprising_target,
    violence_after,
    war_event,
    world_war_limit,
)
from aerona.engine.services.war_geography import Neighbourhood
from aerona.engine.services.war_resolution import WarSettlement, close_stale_wars, end_war, settle_peace
from aerona.engine.urban.morphology import siege_of
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

ARMY_SIZE_FIXUP = "military.army_size_matches_stacks"
PAIR = 2
POPULATION_CAPS = {EntityType.SETTLEMENT: "settlement_population_cap", EntityType.PEOPLE: "people_population_cap"}


@dataclass
class Theatre:
    strength: MilitaryStrength
    sides: SideIndex
    neighbourhood: Neighbourhood
    laws: LawBook
    ground: EnvironmentBook
    supply: Network | None = None
    views: Mapping[int, WorldView] = field(default_factory=dict)

    @classmethod
    async def load(cls, ctx: TickContext) -> "Theatre":
        neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
        return cls(
            await MilitaryStrength.load(ctx.session, ctx.rules),
            await SideIndex.load(ctx.session, neighbourhood),
            neighbourhood,
            await ctx.laws(),
            await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch),
            views=await world_views(ctx.session, ctx.rules),
        )

    def battleground(
        self,
        ctx: TickContext,
        war: WarRow,
        defender: EntityRow,
        *,
        slot: str,
        season_index: int,
        year: int | None,
        region_id: int | None = None,
        urban: bool = False,
    ) -> BattleGround:
        home = self.ground.region_of(defender.id)
        region = (self.ground.regions.get(region_id) if region_id is not None else None) or home
        at_home = home is None or region is home
        place = (self.ground.place_of(defender.location_id) or self.ground.place_of(defender.id)) if at_home else None
        anchor = region.entity_id if region is not None else self.ground.atlas.top_region(defender.id)
        site = None if place is not None else battle_site(ctx.rules, self.ground, anchor, ctx.environment.rng(f"site.{war.id}.{slot}"))
        season = self.ground.season_at(defender.world_id, season_index)
        weather = self.ground.weather(ctx.environment.world_seed, ctx.epoch, region, season, slot) if region is not None else None
        world = self.ground.worlds.get(defender.world_id)
        view = self.views.get(world.id) if world is not None else None
        chance = night_chance(ctx.rules, view.nights if view is not None else True, world.day_length_hours) if world is not None else 0.0
        night = ctx.environment.rng(f"night.{war.id}.{slot}").chance(chance)
        site_id = site.entity_id if site is not None else None
        return BattleGround(region=region, place=place or site, season=season, weather=weather, year=year, night=night, urban=urban, site_id=site_id)


@dataclass
class BattleReport:
    war: WarRow
    winner: EntityRow
    loser: EntityRow
    gap: float
    outcome: BattleOutcome
    summary: str
    record: EntityRow | None = None
    ids: list[int] = field(default_factory=list)
    settlement: WarSettlement | None = None
    refused: bool = False
    ground: BattleGround | None = None


async def is_uprising(session: AsyncSession, entity: EntityRow) -> bool:
    return entity.entity_type is EntityType.FACTION and (entity.social_class is not None or await kind_of(session, entity.id) is FactionKind.REBELS)


def battle_severity(rules: Rules, gap: float) -> int:
    campaigns = rules.campaigns
    base = campaigns.battle_event_severity_base
    lead = max(0.0, gap)
    return clamp_int(base + (campaigns.battle_severity_ceiling - base) * lead / (lead + campaigns.battle_severity_half_gap), 0, PERCENT_MAX)


async def redirect_uprisings(ctx: TickContext) -> int:
    bonds = BondRepository(ctx.session)
    redirected = 0
    enemies = list(await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)))
    for bond in enemies:
        ends = [await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)]
        first, second = ends
        if first is None or second is None:
            continue
        if is_community(first) and is_community(second):
            continue
        rebels, overlord = (first, second) if await is_uprising(ctx.session, first) and not is_community(second) else (second, first)
        if not await is_uprising(ctx.session, rebels) or is_community(overlord):
            continue
        await bonds.deactivate(bond, ctx.epoch, "uprising redirected")
        if rebels.status is not EntityStatus.CANON or overlord.status is not EntityStatus.CANON:
            continue
        ruled = [
            target
            for target in [await living_entity(ctx.session, ruled.target_node_id) for ruled in await bonds.outgoing(overlord.id, BondKind.RULES)]
            if target is not None and is_community(target) and target.id != rebels.id
        ]
        ruled.sort(key=lambda target: (target.id != rebels.location_id, target.location_id != rebels.location_id))
        target = ruled[0] if ruled else None
        if target is None or await can_open_war(ctx.session, ctx.rules, rebels.id, target.id, ctx.epoch, world_cap=False, cause=WarCause.UPRISING) is not None:
            continue
        await declare_war(ctx, rebels.id, target.id, bond.description or "uprising", cause=WarCause.UPRISING, world_cap=False, since_epoch=bond.epoch)
        redirected += 1
        await record(
            ctx,
            "war.uprising_redirected",
            roles={IncidentRole.ACTOR: rebels.id, IncidentRole.AUTHORITY: overlord.id, IncidentRole.TARGET: target.id},
            place=rebels.location_id,
        )
    return redirected


async def end_wars_with_subjects(ctx: TickContext) -> int:
    bonds = BondRepository(ctx.session)
    ended = 0
    for first_id, second_id, _ in await hostile_pairs(ctx.session):
        if await bonds.active_between(first_id, second_id, [BondKind.RULES, BondKind.PAYS_TRIBUTE]):
            await settle_peace(ctx, first_id, second_id, WarEnding.PEACE, "no war with subjects", apply_relation=False)
            ended += 1
    return ended


async def idle_armies(ctx: TickContext) -> int:
    campaigns = ctx.rules.campaigns
    repository = EntityRepository(ctx.session)
    disbanded = 0
    for row in list(await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))):
        war = await ctx.session.get(WarRow, row.war_id) if row.war_id is not None else None
        if war is not None and war.status is not WarStatus.ENDED:
            continue
        army = await living_entity(ctx.session, row.entity_id)
        if army is None:
            continue
        row.war_id = None
        await repository.add_flag(army.id, EntityFlag.ON_WATCH, ctx.epoch)
        if await repository.has_flag(army.id, EntityFlag.IMMORTAL) or campaigns.idle_army_return_pct <= 0:
            continue
        size = stat(army, "size") or 0
        returning = min(size, max(1, round_half_up(size * campaigns.idle_army_return_pct / PERCENT)))
        owner = await living_entity(ctx.session, row.owner_entity_id)
        floor = await standing_floor(ctx.session, ctx.rules, owner)
        if floor >= size:
            continue
        returning = min(returning, size - floor)
        remaining = size - returning
        if remaining < campaigns.idle_army_disband_below and floor == 0:
            returning, remaining = size, 0
        await resize(ctx.session, ctx.rules, army, remaining)
        demobilise(ctx.rules, owner, returning)
        if remaining > 0:
            continue
        row.disbanded_epoch = ctx.epoch
        await disband_units(ctx, army.id, HonourTally())
        await retire_stacks(ctx.session, army.id)
        home = owner.name if owner is not None else "their homes"
        await retire_in(ctx, army, f"the army without a war stood down; its soldiers went back to {home}", close_bonds=True)
        roles = {IncidentRole.SUBJECT: army.id, **({IncidentRole.OWNER: owner.id} if owner is not None else {})}
        await record(ctx, "warfare.army_stood_down", roles=roles, facts={"returned": returning}, place=army.location_id)
        disbanded += 1
    return disbanded


async def backfill_army_sizes(ctx: TickContext) -> int:
    found = await reconcile_sizes(ctx)
    if await ctx.session.get(AppliedFixupRow, ARMY_SIZE_FIXUP) is None:
        ctx.session.add(AppliedFixupRow(key=ARMY_SIZE_FIXUP, result=found))
    return sum(found.values())


async def campaign_upkeep(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    ctx.count("armies_drilled", await drill_armies(ctx))
    for key, value in (await keep_templates(ctx)).items():
        ctx.count(f"templates_{key}", value)
    for key, value in (await keep_war_lines(ctx)).items():
        ctx.count(f"war_lines_{key}", value)
    casus_belli = await gather_casus_belli(ctx)
    ctx.count("casus_belli_found", sum(casus_belli.found.values()))
    ctx.count("casus_belli_lapsed", casus_belli.lapsed)
    ctx.count("home_news", await home_news(ctx, atlas))
    ctx.count("wounded_recovered", await recover_wounded(ctx))
    for key, value in (await pay_contracts(ctx)).items():
        ctx.count(f"contracts_{key}", value)
    ctx.count("mercenaries_hired", await hire_mercenaries(ctx))
    ctx.count("occupation_levies", await occupation_levies(ctx, atlas))
    ctx.count("occupation_revolts", await occupation_revolts(ctx, atlas))
    ctx.count("raids_declared", await raiders(ctx))


async def heat_toll(ctx: TickContext) -> int:
    ground = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    lost = 0
    statement = select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None), ArmyRow.war_id.is_not(None)).order_by(ArmyRow.entity_id)
    for row in await ctx.session.scalars(statement):
        army = await living_entity(ctx.session, row.entity_id)
        region = ground.region_of(row.entity_id) if army is not None else None
        if army is not None and region is not None:
            lost += await suffer_heat(ctx, army, region.temperature)
    return lost


@reads(
    "army.size",
    "settlement.population",
    "table.armies",
    "table.battles",
    "table.bonds",
    "table.entity_flags",
    "table.node_materials",
    "table.region_environment",
    "table.war_sides",
    "table.wars",
    "table.world_materials",
)
@writes("army.size", "settlement.population", "table.armies", "table.entities")
@reads("army.size", "settlement.population")
@writes("army.size", "settlement.population")
async def _side_losses(ctx: TickContext, war: WarRow, side_id: int) -> int:
    rows = await ctx.session.scalars(select(BattleRow).where(BattleRow.war_id == war.id, BattleRow.epoch == ctx.epoch - 1))
    bouts = [row for row in rows if side_id in {row.winner_entity_id, row.loser_entity_id}]
    return sum(row.winner_losses if row.winner_entity_id == side_id else row.loser_losses for row in bouts)


async def _occupied(ctx: TickContext, atlas: RegionAtlas, side_id: int) -> int:
    home = atlas.top_region(side_id)
    rows = await ctx.session.scalars(select(OccupationRow).where(OccupationRow.occupier_entity_id != side_id))
    return sum(1 for row in rows if row.region_entity_id == home or side_id in atlas.communities_in(row.region_entity_id))


async def weariness(ctx: TickContext) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    ended = 0
    for item in await ongoing_wars(ctx.session):
        war = item.war
        rows = {row.entity_id: row for row in await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None)))}
        for ally in [row for side_id, row in sorted(rows.items()) if side_id not in (item.attacker_id, item.defender_id)]:
            await tire_side(ctx, atlas, war, ally)
            await separate_peace(ctx, item, ally)
        for side_id in (item.attacker_id, item.defender_id):
            row = rows.get(side_id)
            if row is None:
                continue
            await tire_side(ctx, atlas, war, row)
            if "weariness" not in war_locks(war):
                row.weariness = clamp_int(row.weariness + await war_taxes(ctx, row) + await lost_trade(ctx, row), 0, PERCENT_MAX)
            behind = (war.score < 0) if side_id == item.attacker_id else (war.score > 0)
            if war.status is WarStatus.ONGOING and await seeks_peace(ctx, war, row, humiliated=behind):
                await _weary_peace(ctx, item, side_id, behind=behind)
                ended += 1
                break
    return ended


async def tire_side(ctx: TickContext, atlas: RegionAtlas, war: WarRow, row: WarSideRow) -> None:
    dead = await _side_losses(ctx, war, row.entity_id)
    maimed = dead * ctx.rules.maimed.return_pct // PERCENT
    occupied = await _occupied(ctx, atlas, row.entity_id)
    await weary(ctx, war, row, dead=dead, maimed=maimed, occupied=occupied)
    await rally_support(ctx, war, row, dead=dead, maimed=maimed, occupied=occupied)


async def _weary_peace(ctx: TickContext, item: OngoingWar, side_id: int, *, behind: bool) -> None:
    war = item.war
    other = item.foe_of(side_id)
    event = await war_event(ctx.session, war)
    if behind:
        await end_war(ctx, war, WarEnding.VICTORY, victor_id=other, loser_id=side_id, reason="war weariness")
    else:
        await end_war(ctx, war, WarEnding.WHITE_PEACE, reason="war weariness")
    weary_side = await living_entity(ctx.session, side_id)
    roles = {IncidentRole.OPPONENT: other, **({IncidentRole.ACTOR: weary_side.id} if weary_side is not None else {})}
    await record(ctx, "war.weary_peace", roles=roles, facts={"war": event.id})


@reads(
    "army.equipment",
    "army.experience",
    "army.morale",
    "army.size",
    "cult.zeal",
    "faction.wealth",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.armies",
    "table.army_officers",
    "table.army_profiles",
    "table.army_templates",
    "table.army_units",
    "table.artwork_profiles",
    "table.asabiyya",
    "table.battles",
    "table.beast_profiles",
    "table.beliefs",
    "table.bias_weights",
    "table.bodies",
    "table.bonds",
    "table.calendars",
    "table.casus_belli",
    "table.ciphers",
    "table.claims",
    "table.collaborations",
    "table.community_cohorts",
    "table.community_societies",
    "table.community_stocks",
    "table.cult_tenets",
    "table.culture_values",
    "table.currencies",
    "table.custom_kinds",
    "table.districts",
    "table.entities",
    "table.entity_flags",
    "table.feeling_spread",
    "table.feuds",
    "table.forced_weather",
    "table.goods",
    "table.herds",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_members",
    "table.house_profiles",
    "table.injuries",
    "table.law_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.magic_sites",
    "table.memories",
    "table.mercenary_contracts",
    "table.network_nodes",
    "table.node_materials",
    "table.nodes",
    "table.occupation_measures",
    "table.occupation_regimes",
    "table.occupations",
    "table.offices",
    "table.peace_terms",
    "table.people_biology",
    "table.people_culture",
    "table.personality_values",
    "table.place_environment",
    "table.plant_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.public_opinion",
    "table.region_environment",
    "table.relationships",
    "table.routes",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sieges",
    "table.signal_links",
    "table.skills",
    "table.sky_events",
    "table.slave_markets",
    "table.species_ranges",
    "table.spy_agents",
    "table.spy_networks",
    "table.stars",
    "table.trade_policies",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.unit_designs",
    "table.vassalages",
    "table.vessel_profiles",
    "table.war_production",
    "table.war_sides",
    "table.wars",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "army.size",
    "people.population",
    "people.wealth",
    "settlement.population",
    "settlement.wealth",
    "table.applied_fixups",
    "table.armies",
    "table.army_officers",
    "table.army_profiles",
    "table.army_templates",
    "table.army_units",
    "table.battle_casualties",
    "table.battle_stacks",
    "table.bias_weights",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.casus_belli",
    "table.claims",
    "table.community_cohorts",
    "table.community_stocks",
    "table.currencies",
    "table.districts",
    "table.entities",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.learned_tactics",
    "table.loans",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.messages",
    "table.occupations",
    "table.offices",
    "table.peace_terms",
    "table.polity_profiles",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sons",
    "table.spy_agents",
    "table.spy_networks",
    "table.treaty_breaches",
    "table.vessel_profiles",
    "table.war_production",
    "table.war_sides",
)
async def war_upkeep(ctx: TickContext) -> None:
    ctx.count("army_sizes_backfilled", await backfill_army_sizes(ctx))
    ctx.count("armies_stood_down", await idle_armies(ctx))
    ctx.count("heat_losses", await heat_toll(ctx))
    ctx.count("stale_wars_closed", await close_stale_wars(ctx))
    ctx.count("uprisings_redirected", await redirect_uprisings(ctx))
    ctx.count("subject_wars_ended", await end_wars_with_subjects(ctx))
    ctx.count("blockades_lifted", await clear_blockades(ctx))
    lost = await partisans(ctx)
    ctx.count("partisan_dead", lost)
    ctx.count("occupations_ended", await end_occupations(ctx))
    await campaign_upkeep(ctx)
    ctx.count("weary_peace", await weariness(ctx))


async def battle_power(ctx: TickContext, theatre: Theatre, community: EntityRow, army: EntityRow, army_row: ArmyRow) -> float:
    campaigns = ctx.rules.campaigns
    commander = await commander_of(ctx.session, army_row)
    command = 0.0
    if commander is not None:
        summed = (
            await effective(ctx.session, commander, "strength", rules=ctx.rules)
            + await effective(ctx.session, commander, "intellect", capacity=Capacity.COMMAND, rules=ctx.rules)
            + await effective(ctx.session, commander, "charisma", capacity=Capacity.COMMAND, rules=ctx.rules)
        )
        tactics = await best_effective(ctx.session, commander.id, COMMAND_SKILLS)
        command = summed / campaigns.strength_commander_divisor * (PERCENT + tactics * ctx.rules.skills.commander_tactics_pct / PERCENT) / PERCENT
    burden = max(0.0, 1 - await march_burden(ctx, army) * ctx.rules.materials.march_campaign_pct / PERCENT)
    return burden * (
        await theatre.strength.power(community) * campaigns.strength_community_share_pct / PERCENT
        + log_size(stat(army, "size") or 0) * campaigns.strength_size_log_mult
        + (stat(army, "morale") or 0) / campaigns.strength_morale_divisor
        + (stat(army, "equipment") or 0) / campaigns.strength_equipment_divisor
        + (stat(army, "experience") or 0) / campaigns.strength_experience_divisor
        + command
    )


def war_locks(war: WarRow) -> list[str]:
    return list(war.locked or [])


def battle_field(rules: Rules, ground: BattleGround) -> Field:
    region = ground.region
    river = region is not None and region.river_class in {RiverClass.RIVER, RiverClass.GREAT_RIVER}
    bridge = river and bridged(rules, region)
    ford = river and region is not None and region.river_class is RiverClass.RIVER
    weather = ground.weather.kind if ground.weather is not None else None
    return Field(ground.terrain, weather, ground.night, river, bridge=bridge, ford=ford, cover=ground.cover, earthworks=earthworks_of(region))


def _besieged(rules: Rules, defender: EntityRow) -> EntityRow | None:
    defense = stat(defender, "defense")
    if defender.entity_type is EntityType.SETTLEMENT and defense is not None and defense >= rules.campaigns.siege_min_defense:
        return defender
    return None


async def _siege(
    ctx: TickContext, war: WarRow, besieged: EntityRow, winner: EntityRow, *, armies: dict[int, EntityRow], gap: float, attacker_id: int
) -> tuple[BattleOutcome, str, SiegeRow]:
    campaigns = ctx.rules.campaigns
    besieger = next(entity_id for entity_id in armies if entity_id != besieged.id)
    besieger_entity = await living_entity(ctx.session, besieger)
    siege = await open_siege(ctx, war, besieged, besieger_entity or besieged)
    siege.rounds += 1
    attacker_army = armies[besieger]
    society = await _society(ctx, besieged.id)
    food = society.stock_food if society is not None else campaigns.siege_default_supplies
    starving = campaigns.breach_starving_bonus_pct / PERCENT if food < campaigns.breach_starving_supplies else 0
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    if town is not None:
        urban = ctx.rules.urban
        starving = campaigns.breach_starving_bonus_pct / PERCENT if town.siege_supplies < urban.ration_supplies_days else 0
        if town.siege_water < urban.ration_supplies_days // 2:
            starving += campaigns.breach_starving_bonus_pct / PERCENT / 2
        if (
            town.unrest >= ctx.rules.crime.treason_unrest
            and winner.id != besieged.id
            and ctx.rng(f"treason.{besieged.id}").chance(ctx.rules.crime.treason_chance)
        ):
            shift_stat(besieged, "defense", -campaigns.breach_defense_loss)
            siege.status, siege.ended_epoch = SiegeStatus.BREACHED, ctx.epoch
            return BattleOutcome.SIEGE_BREACHED, f"a disgruntled faction opened the gates of {besieged.name}", siege
    owner = await ctx.session.get(ArmyRow, attacker_army.id)
    engines = await siege_engines(ctx, await living_entity(ctx.session, owner.owner_entity_id) if owner is not None else None, attacker_army)
    starving += engines * ctx.rules.materials.engine_breach_pct / PERCENT
    areas = await command_areas(ctx.session, owner.commander_entity_id if owner is not None else None)
    starving += ctx.rules.army_depth.command_area_pct / PERCENT * areas[CommandArea.SIEGE] / PERCENT
    starving += campaigns.breach_starving_bonus_pct / PERCENT * (siege.breaches + (siege.starvation in HUNGRY))
    starving += breach_bonus(ctx, siege)
    breach_chance = clamp_float(gap / campaigns.breach_diff_divisor + starving, campaigns.breach_min_pct / PERCENT, campaigns.breach_max_pct / PERCENT)
    sign = 1 if winner.id == attacker_id else -1
    besieger_name = besieger_entity.name if besieger_entity is not None else "the besiegers"
    if winner.id == besieged.id:
        war.score += sign
        shift_stat(attacker_army, "morale", -campaigns.siege_repelled_morale_loss * await fear_of(ctx.session, attacker_army))
        siege.status, siege.ended_epoch = SiegeStatus.REPULSED, ctx.epoch
        return BattleOutcome.SIEGE_REPULSED, f"{besieged.name} repulsed the siege from behind its walls", siege
    if ctx.rng("breach").probability(breach_chance):
        shift_stat(besieged, "defense", -campaigns.breach_defense_loss)
        war.score += sign * campaigns.breach_war_score
        siege.status, siege.ended_epoch = SiegeStatus.BREACHED, ctx.epoch
        return BattleOutcome.SIEGE_BREACHED, f"{besieger_name} breached the walls of {besieged.name}", siege
    population = stat_or(besieged, "population", campaigns.siege_default_population)
    remaining = clamp_int(
        population * campaigns.siege_population_kept_pct / PERCENT, ctx.rules.limits.population_floor, ctx.rules.limits.settlement_population_cap
    )
    set_stats(besieged, population=remaining)
    prosperity = stat(besieged, "prosperity")
    set_stats(
        besieged,
        prosperity=clamp_int((prosperity if prosperity is not None else ctx.rules.society.default_stat) - campaigns.siege_prosperity_loss, 0, PERCENT_MAX),
    )
    if society is not None:
        await shift_stock(ctx.session, ctx.rules, besieged.id, Commodity.FOOD, -campaigns.siege_supply_loss, epoch=ctx.epoch, flow=GoodsFlow.SIEGE)
    shift_stat(attacker_army, "morale", -campaigns.siege_attacker_morale_loss * await fear_of(ctx.session, attacker_army))
    return BattleOutcome.SIEGE_STARVATION, f"{besieger_name} laid siege to {besieged.name}; the walls hold but food is running low in the city", siege


async def _society(ctx: TickContext, entity_id: int) -> CommunitySocietyRow | None:
    return await ctx.session.get(CommunitySocietyRow, entity_id)


def _community_losses(ctx: TickContext, winner: EntityRow, loser: EntityRow, loss: float) -> None:
    campaigns = ctx.rules.campaigns
    limits = ctx.rules.limits
    share = 1 - loss / campaigns.community_loss_divisor
    population = stat(loser, "population")
    if population is not None:
        cap = getattr(limits, POPULATION_CAPS.get(loser.entity_type, "people_population_cap"))
        set_stats(loser, population=clamp_int(population * share, limits.population_floor, cap))
    followers = stat(loser, "followers")
    if followers is not None:
        set_stats(loser, followers=clamp_int(followers * share, 1, limits.cult_follower_cap))
    for key in ("prosperity", "wealth"):
        shift_stat(loser, key, -campaigns.loser_prosperity_loss)
    shift_stat(winner, "wealth", campaigns.winner_wealth_gain)


async def _place(ctx: TickContext, theatre: Theatre, loser: EntityRow, besieged: EntityRow | None, site_id: int | None = None) -> EntityRow | None:
    if besieged is not None:
        return besieged
    site = await living_entity(ctx.session, site_id)
    if site is not None:
        return site
    if loser.entity_type is EntityType.SETTLEMENT:
        return loser
    location = await living_entity(ctx.session, loser.location_id)
    if location is not None:
        return location
    return await living_entity(ctx.session, theatre.neighbourhood.top_region(loser.id))


async def _record(ctx: TickContext, report: BattleReport, place: EntityRow | None, armies: dict[int, EntityRow], sequence: int) -> None:
    campaigns = ctx.rules.campaigns
    event = await war_event(ctx.session, report.war)
    besieged = report.outcome in (BattleOutcome.SIEGE_BREACHED, BattleOutcome.SIEGE_REPULSED, BattleOutcome.SIEGE_STARVATION)
    bonds = BondRepository(ctx.session)
    if not besieged and report.gap < campaigns.battle_record_min_diff:
        where = place.name if place is not None else report.loser.name
        event.description = f"{event.description} Epoch {ctx.epoch}, clash #{sequence} ({where}): {report.summary}."
        await bonds.connect(BondDraft(event.id, report.loser.id, BondKind.PARTY_TO, ctx.epoch, "loser", role=BondRole.LOSER, war_id=report.war.id))
        return
    named_after = place if place is not None and place.entity_type is EntityType.SETTLEMENT else report.loser
    derived = await Namer(ctx.session, ctx.rules).from_speaker(named_after.id, seed_of(report.war.id, sequence, "battle"), NameKind.PLACE)
    root = derived or (place.name if place is not None else report.loser.name)
    winner_army, loser_army = armies[report.winner.id], armies[report.loser.id]
    winner_soldiers = several(stat(winner_army, "size") or 0, "soldier", "soldiers")
    loser_soldiers = several(stat(loser_army, "size") or 0, "soldier", "soldiers")
    body = (
        f"Clash #{sequence} of {event.name}. {winner_army.name} ({winner_soldiers}, morale {stat(winner_army, 'morale') or 0}) "
        f"against {loser_army.name} ({loser_soldiers}, morale {stat(loser_army, 'morale') or 0}). {report.summary}."
    )
    made = await create_record(
        ctx,
        RecordSpec(
            name=(SIEGE_NAME_TEMPLATE if besieged else BATTLE_NAME_TEMPLATE).format(root=root),
            entity_type=EntityType.EVENT,
            stats=EventStats(severity=battle_severity(ctx.rules, report.gap)),
            body=body,
            power=clamp_int(
                campaigns.battle_event_power_min + round_half_up(report.gap / campaigns.battle_event_power_divisor),
                campaigns.battle_event_power_min,
                campaigns.battle_event_power_max,
            ),
            world_id=event.world_id,
            location_id=place.id if place is not None else None,
            engine_kind=EngineKind.SIEGE if besieged else EngineKind.BATTLE,
            flags=(EntityFlag.NAME_FROM_LANGUAGE,) if derived else (),
        ),
    )
    report.record = made
    await bonds.connect(BondDraft(made.id, event.id, BondKind.PART_OF, ctx.epoch, "battle", war_id=report.war.id))
    await bonds.connect(BondDraft(made.id, report.winner.id, BondKind.PARTY_TO, ctx.epoch, "victor", role=BondRole.VICTOR, war_id=report.war.id))
    await bonds.connect(BondDraft(made.id, report.loser.id, BondKind.PARTY_TO, ctx.epoch, "loser", role=BondRole.LOSER, war_id=report.war.id))


async def duel(
    ctx: TickContext,
    theatre: Theatre,
    first: EntityRow,
    second: EntityRow,
    *,
    war: WarRow | None,
    anchor_id: int | None,
    context: DuelContext = DuelContext.WAR,
    ground: BattleGround | None = None,
    battle_id: int | None = None,
    cause: int | None = None,
) -> "Duelled":
    campaigns = ctx.rules.campaigns
    bonds = BondRepository(ctx.session)
    event = await war_event(ctx.session, war) if war is not None else None
    label = event.name if event is not None else "single combat"
    if not await bonds.exists_between(first.id, second.id, BondKind.RIVAL):
        await bonds.connect(BondDraft(first.id, second.id, BondKind.RIVAL, ctx.epoch, label))
    if event is not None and war is not None:
        for hero in (first, second):
            await bonds.connect(BondDraft(event.id, hero.id, BondKind.PARTY_TO, ctx.epoch, "dueled", role=BondRole.DUELED, war_id=war.id))
    fighters = (await fighter(ctx, first, second), await fighter(ctx, second, first))
    terrain = ground.terrain if ground is not None else None
    weather = ground.weather.kind if ground is not None and ground.weather is not None else None
    for one in fighters:
        set_footing(ctx.rules, one, terrain, weather, await injuries_of(ctx, one.entity.id))
    result = bout(ctx.rules, ctx.rng(f"duel.{first.id}.{second.id}.{ctx.epoch}"), *fighters, context)
    await duelled(ctx, first)
    await duelled(ctx, second)
    await wear_in_duel(ctx, first.id, result.exchanges)
    await wear_in_duel(ctx, second.id, result.exchanges)
    winner, loser = result.winner.entity, result.loser.entity
    await judged(ctx, winner.id, loser.id, ActKind.DUELLING, note=label)
    await think(ctx.session, ctx.rules, winner.id, ThoughtKind.WON_DUEL, ctx.epoch, subject_id=loser.id)
    await think(ctx.session, ctx.rules, loser.id, ThoughtKind.LOST_DUEL, ctx.epoch, subject_id=winner.id)
    style = await strike_style(ctx.session, ctx.rules, winner, loser)
    ctx.count(f"duel_{result.end.value}")
    if stat(loser, "hp") is None:
        set_stats(loser, hp=campaigns.hero_default_hp)
    bout_id = await settle_bout(ctx, result, style=style, terrain=terrain, weather=weather, cause=cause, place_id=first.location_id)
    fate = CasualtyFate.KILLED if result.killed else DUEL_FATES[result.end]
    harmed = sum(hit for target_id, hit in result.hits if target_id == loser.id)
    side = theatre.sides.side_of(loser)
    note_casualty(ctx, battle_id, loser, side_id=side, fate=fate, harm=harmed, note=f"fell to {winner.name} in single combat")
    if result.killed:
        death_cause = f"fell in a duel with {winner.name} in {label}"
        await death_path(ctx, loser, death_cause, winner.id, f"{label} duel", forced=True, event_id=anchor_id, harm=HarmCause.DUEL, style=style)
        if anchor_id is not None:
            await bonds.connect(BondDraft(anchor_id, loser.id, BondKind.CAUSED, ctx.epoch, "fell in a duel"))
        shift_stat(winner, "charisma", campaigns.duel_winner_charisma)
        winner_side, loser_side = theatre.sides.side_of(winner), theatre.sides.side_of(loser)
        if winner_side is not None and loser_side is not None and winner_side != loser_side:
            await start_blood_feud(ctx, winner_side, loser_side, f"the blood of {loser.name}")
        await house_feud(ctx, winner.id, loser.id, f"the blood of {loser.name}")
        exchanges_counted = several(result.exchanges, "exchange", "exchanges")
        return Duelled(
            bout_id,
            winner.id,
            loser.id,
            f"In a duel of {exchanges_counted} {winner.name} killed {loser.name}; now there is a blood feud between the two sides.",
        )
    if result.end is DuelEnd.CRIPPLED and loser.status is EntityStatus.CANON:
        await apply_hits(ctx, loser, crippling(ctx.rules, result, style), lethal=False)
    ending = DUEL_ENDINGS[result.end].format(winner=winner.name, loser=loser.name)
    mercy = f" {winner.name} spared the fallen." if result.spared else ""
    return Duelled(
        bout_id, winner.id, loser.id, f"{winner.name} and {loser.name} dueled for {several(result.exchanges, 'exchange', 'exchanges')}; {ending}.{mercy}"
    )


@dataclass(frozen=True)
class Duelled:
    incident_id: int
    winner_id: int
    loser_id: int
    text: str


async def injuries_of(ctx: TickContext, mortal_id: int) -> int:
    found = await ctx.session.scalar(select(func.count()).select_from(InjuryRow).where(InjuryRow.bearer_node_id == mortal_id, InjuryRow.healed_epoch.is_(None)))
    return int(found or 0)


async def ordeals(ctx: TickContext, theatre: Theatre) -> int:
    bouts = 0
    for claimant, ruler, realm_id in await trial_claims(ctx):
        if not ctx.rng(f"trial.{realm_id}.{ctx.epoch}").chance(ctx.rules.duels.trial_chance):
            continue
        fought_out = await duel(ctx, theatre, claimant, ruler, war=None, anchor_id=realm_id, context=DuelContext.TRIAL)
        await settle_trial(ctx, claimant, ruler, realm_id)
        await record(
            ctx,
            "war.trial_by_combat",
            roles={IncidentRole.ACTOR: claimant.id, IncidentRole.OPPONENT: ruler.id},
            facts={"realm": realm_id, "victor": fought_out.winner_id},
            cause=fought_out.incident_id,
        )
        bouts += 1
    for item in await ongoing_wars(ctx.session):
        if item.war.cause is not WarCause.HOLY_WAR or not ctx.rng(f"god_duel.{item.war.id}.{ctx.epoch}").chance(ctx.rules.duels.god_duel_chance):
            continue
        first, second = theatre.sides.heroes_of(item.attacker_id), theatre.sides.heroes_of(item.defender_id)
        if not first or not second:
            continue
        champion, rival = first[0], second[0]
        fought_out = await duel(ctx, theatre, champion, rival, war=item.war, anchor_id=item.war.event_entity_id, context=DuelContext.GOD)
        with explaining():
            moved = ctx.rules.duels.god_duel_score if fought_out.winner_id == champion.id else -ctx.rules.duels.god_duel_score
            item.war.score += moved
            await record(
                ctx,
                "war.god_duel",
                roles={IncidentRole.ACTOR: champion.id, IncidentRole.OPPONENT: rival.id},
                facts={"war": item.war.event_entity_id, "victor": fought_out.winner_id, "score": moved},
                cause=fought_out.incident_id,
            )
        bouts += 1
    return bouts


async def _seasoned(ctx: TickContext, theatre: Theatre, sides: tuple[EntityRow, ...], armies: dict[int, tuple[EntityRow, ArmyRow]]) -> None:
    for place, side in enumerate(sides):
        won = place == 0
        for hero in theatre.sides.heroes_of(side.id):
            await fought(ctx, hero, survived=hero.status is EntityStatus.CANON, won=won)
        found = armies.get(side.id)
        commander = await commander_of(ctx.session, found[1]) if found is not None else None
        if commander is not None:
            await fought(ctx, commander, commander=True, survived=commander.status is EntityStatus.CANON, won=won)


async def out_cold(session: AsyncSession, mortal_id: int) -> bool:
    body = await session.get(BodyRow, mortal_id)
    return body is not None and body.consciousness is Consciousness.UNCONSCIOUS


async def _heroics(ctx: TickContext, theatre: Theatre, report: BattleReport, battle_id: int | None = None) -> None:
    anchor = report.record.id if report.record is not None else report.war.event_entity_id
    winners, losers = theatre.sides.heroes_of(report.winner.id), theatre.sides.heroes_of(report.loser.id)
    if winners and losers and ctx.rng("duel_roll").chance(ctx.rules.campaigns.duel_chance):
        first, second = ctx.rng("duelists").pick(winners), ctx.rng("duelists").pick(losers)
        if not await forbidden(ctx, first.id, ActKind.DUELLING):
            await duel(ctx, theatre, first, second, war=report.war, anchor_id=anchor, ground=report.ground, battle_id=battle_id)
            report.ids.extend((first.id, second.id))
    candidates = [hero for hero in theatre.sides.heroes_of(report.loser.id) if hero.status is EntityStatus.CANON]
    fallen = [hero for hero in candidates if await out_cold(ctx.session, hero.id)]
    prisoner: EntityRow | None = None
    if fallen and ctx.rng("capture_fallen").chance(ctx.rules.tissues.unconscious_capture_pct):
        prisoner = ctx.rng("captive_fallen").pick(fallen)
    elif candidates and ctx.rng("capture").chance(ctx.rules.campaigns.capture_chance):
        prisoner = ctx.rng("captive").pick(candidates)
    if prisoner is not None:
        event = await war_event(ctx.session, report.war)
        await take_captive(ctx, report.winner, prisoner, report.war, description=event.name, home_id=report.loser.id)
        theatre.sides.mark_captive(prisoner.id)
        await BondRepository(ctx.session).connect(BondDraft(anchor, prisoner.id, BondKind.CAUSED, ctx.epoch, "was captured"))
        report.ids.append(prisoner.id)
        note_casualty(ctx, battle_id, prisoner, side_id=report.loser.id, fate=CasualtyFate.CAPTURED, harm=0, note=f"taken prisoner by {report.winner.name}")


async def _patron_effects(ctx: TickContext, theatre: Theatre, winner: EntityRow, loser: EntityRow) -> int | None:
    campaigns = ctx.rules.campaigns
    winner_patron = await theatre.strength.patron_bonus(winner)
    loser_patron = await theatre.strength.patron_bonus(loser)
    if winner_patron.son is None:
        return None
    winner_patron.son.fame += campaigns.patron_renown_per_battle
    winner_patron.son.xp += campaigns.patron_xp_per_battle
    if loser_patron.son is not None and loser_patron.son.id != winner_patron.son.id:
        await SonRepository(ctx.session).change_relation(winner_patron.son.id, loser_patron.son.id, -campaigns.patron_relation_loss)
    return winner_patron.son.id


async def _omens(ctx: TickContext, theatre: Theatre, ground: BattleGround, sides: tuple[EntityRow, ...], armies: dict[int, tuple[EntityRow, ArmyRow]]) -> None:
    for side in sides:
        patron = (await theatre.strength.patron_bonus(side)).son
        domains = frozenset({patron.domain_primary, patron.domain_secondary}) if patron is not None else frozenset()
        culture = await values_for(ctx.session, side.id)
        reading = (culture[ValueAxis.SUPERSTITION] + VALUE_MAX) // 2 if ValueAxis.SUPERSTITION in culture else ctx.rules.campaigns.omen_default_piety
        shift = omen_morale(ctx.rules, ground.weather, domains, reading)
        if shift:
            shift_stat(armies[side.id][0], "morale", shift)


async def _mark_ground(ctx: TickContext, ground: BattleGround, gap: float, outcome: BattleOutcome) -> None:
    region = ground.region
    if region is None:
        return
    settings = ctx.rules.scars
    depth = scar_battlefield(ctx.rules, region, gap)
    if outcome is BattleOutcome.SIEGE_BREACHED:
        add_scar(region, ScarKind.BURNED, settings.siege_burn_depth)
    if depth >= settings.haunted_battlefield_depth and ctx.rng(f"haunted.{region.entity_id}").chance(settings.haunted_chance):
        await scar_region(ctx.session, ctx.rules, region, ScarKind.HAUNTED, settings.haunted_depth)


HUNGRY = having(STARVATION_STAGE_TRAITS, StarvationStageTrait.HUNGRY)
GREAT_CLASSES = frozenset({OutcomeClass.DECISIVE, OutcomeClass.MASSACRE, OutcomeClass.ROUT})


def _battle_score(war: WarRow, rules: Rules, result: BattleResult, *, attacker_id: int, gap: float) -> BattleOutcome:
    assert result.winner is not None
    sign = 1 if result.winner.entity.id == attacker_id else -1
    great = result.outcome in GREAT_CLASSES or gap >= rules.campaigns.great_victory_diff
    if result.outcome is not OutcomeClass.STALEMATE:
        war.score += sign * (rules.campaigns.great_victory_score if great else 1)
    return BattleOutcome.GREAT_VICTORY if great else BattleOutcome.FIELD_VICTORY


def _battle_row(
    ctx: TickContext, report: BattleReport, result: BattleResult, *, place: EntityRow | None, siege: SiegeRow | None, ground: BattleGround
) -> BattleRow:
    war = report.war
    winner, loser = result.winner, result.loser
    row = BattleRow(
        war_id=war.id,
        epoch=ctx.epoch,
        sequence=war.battles,
        record_entity_id=report.record.id if report.record is not None else None,
        place_entity_id=place.id if place is not None else None,
        winner_entity_id=report.winner.id,
        loser_entity_id=report.loser.id,
        outcome=report.outcome,
        gap=report.gap,
        siege_id=siege.id if siege is not None else None,
        weather=ground.weather.kind if ground.weather is not None else None,
        season_name=ground.season.name if ground.season is not None else None,
        terrain=ground.terrain,
        year=ground.year,
        night=ground.night,
        tactics_attacker=None if result.refused else result.attacker.tactic,
        tactics_defender=None if result.refused else result.defender.tactic,
        outcome_class=result.outcome,
        casualties_by_kind=dict(result.by_kind),
        winner_losses=winner.lost if winner is not None else 0,
        loser_losses=loser.lost if loser is not None else 0,
        tactic_factors=dict(result.factors),
        morale=morale_sheet(result),
        magic=magic_sheet(result),
        width=result.attacker.width,
        reserves_committed=result.attacker.reserves_committed + result.defender.reserves_committed,
        command_collapsed_entity_id=result.collapsed,
        planned_entity_id=result.planned_by,
        trap_entity_id=result.trapped_by,
        feint=result.feint,
        salvaged=winner.salvaged if winner is not None else 0,
        standard_entity_id=result.standard_taken,
    )
    ctx.session.add(row)
    return row


async def _refused(
    ctx: TickContext, report: BattleReport, result: BattleResult, ground: BattleGround, *, event: EntityRow, commander_id: int | None
) -> BattleReport:
    report.refused = True
    place = await living_entity(ctx.session, ground.region.entity_id) if ground.region is not None else None
    row = _battle_row(ctx, report, result, place=place, siege=None, ground=ground)
    await ctx.session.flush()
    log_phases(ctx, row.id, result)
    await cautious(ctx, commander_id)
    margin = next((log.details.get("margin", 0) for log in result.phases if log.phase is BattlePhase.SCOUTING), 0)
    await record(
        ctx,
        "war.battle.refused",
        roles={
            IncidentRole.ACTOR: report.winner.id,
            IncidentRole.OPPONENT: report.loser.id,
            IncidentRole.MEMBER: [result.attacker.army.id, result.defender.army.id],
        },
        facts={"war": event.id, "margin": int(margin) if isinstance(margin, int) else 0},
        place=place.id if place is not None else None,
    )
    ctx.count("battles_refused")
    return report


async def _announce(
    ctx: TickContext,
    report: BattleReport,
    result: BattleResult,
    event: EntityRow,
    *,
    armies: dict[int, tuple[EntityRow, ArmyRow]],
    place: EntityRow | None,
    son_id: int | None,
    taken: int,
) -> int | None:
    war = report.war
    winner_side, loser_side = (result.winner, result.loser) if result.winner is not None and result.loser is not None else (result.attacker, result.defender)
    commanders = {side: army.commander_entity_id for side, (_, army) in armies.items()}
    outbreak = await ChronicleRepository(ctx.session).prior_incident([war.event_entity_id], ("war.outbreak", "war.battle."))
    ground = report.ground
    roles: dict[IncidentRole, int | list[int]] = {
        IncidentRole.ACTOR: report.winner.id,
        IncidentRole.OPPONENT: report.loser.id,
        IncidentRole.MEMBER: sorted({winner_side.army.id, loser_side.army.id}),
    }
    leaders = sorted({commander for commander in commanders.values() if commander is not None})
    if leaders:
        roles[IncidentRole.LEADER] = leaders
    witnesses = sorted({node for node in report.ids if node not in leaders})
    if witnesses:
        roles[IncidentRole.WITNESS] = witnesses
    facts: dict[str, FactInput] = {
        "war": event.id,
        "winner_start": winner_side.start,
        "loser_start": loser_side.start,
        "winner_lost": winner_side.lost,
        "loser_lost": loser_side.lost,
        "wounded": sum(result.wounded.values()),
        "captured": taken,
        "missing": sum(stack.missing for stack in (*result.attacker.stacks, *result.defender.stacks)),
        "deserted": sum(stack.deserted for stack in (*result.attacker.stacks, *result.defender.stacks)),
        "gap": round(result.gap),
        "outcome_class": result.outcome,
        "winner_tactic": winner_side.tactic,
        "loser_tactic": loser_side.tactic,
    }
    if report.record is not None:
        facts["battle"] = report.record.id
    if ground is not None and ground.terrain is not None:
        facts["terrain"] = ground.terrain
    if ground is not None and ground.weather is not None:
        facts["weather"] = ground.weather.kind
    write = await record(
        ctx,
        f"war.battle.{report.outcome.value}",
        roles=roles,
        facts=facts,
        steps=battle_steps(
            result, commanders, await main_arms(ctx.session, [stack.row.id for side in (result.attacker, result.defender) for stack in side.stacks])
        ),
        place=place.id if place is not None else None,
        cause=outbreak,
        son_id=son_id,
        at_moment=await battle_moment(ctx, ground, outbreak),
    )
    return write.incident_id


async def battle_moment(ctx: TickContext, ground: BattleGround | None, cause: int | None) -> Moment | None:
    if ground is None or ground.year is None or ground.season is None:
        return None
    return Moment(ground.year, ground.season.position).at_least(await incident_moment(ctx.session, cause))


async def _powers(
    ctx: TickContext,
    theatre: Theatre,
    war: WarRow,
    sides: tuple[EntityRow, EntityRow],
    armies: dict[int, tuple[EntityRow, ArmyRow]],
    *,
    ground: BattleGround,
    besieged: EntityRow | None,
) -> tuple[float, float]:
    attacker, defender = sides
    attacker_power = await battle_power(ctx, theatre, attacker, *armies[attacker.id]) * attack_factor(ctx.rules, ground)
    defender_power = await battle_power(ctx, theatre, defender, *armies[defender.id]) * defend_factor(ctx.rules, ground)
    if besieged is not None:
        walls = await ctx.session.get(SettlementInfrastructureRow, besieged.id)
        town = await ctx.session.get(SettlementProfileRow, besieged.id)
        rings = siege_of(ctx.rules, town.morphology) if town is not None else 0
        siege = await open_siege(ctx, war, besieged, attacker)
        defender_power *= wall_defence(ctx, siege, walls, rings, people=stat_or(besieged, "population", 0)) * await warded(ctx, besieged.id)
        if walls is not None:
            defender_power *= await sturdiness(ctx.session, ctx.rules, walls.walls_material, walls.walls_world_material_id)
        defender_power *= await tech_factor(ctx.session, ctx.rules, besieged.id, EraChannel.FORTIFICATION)
    return attacker_power, defender_power


async def _sacked(
    ctx: TickContext, besieged: EntityRow, armies: dict[int, tuple[EntityRow, ArmyRow]], attacker: EntityRow, siege: SiegeRow | None = None
) -> None:
    profile = await profile_of(ctx, armies[attacker.id][0], attacker)
    homeward = [March(army, besieged, await profile_of(ctx, army, besieged), None, False) for owner, (army, _) in armies.items() if owner == besieged.id]
    choice = await sack_choice(ctx, siege, attacker, armies[attacker.id][1].commander_entity_id) if siege is not None else SackChoice.SACK
    ctx.count("sack_dead", await sack(ctx, besieged, profile, homeward=homeward, victor=attacker, siege=siege, choice=choice))
    if siege is not None and choice in SACKED_SACK_CHOICES:
        await terror(ctx, siege.war_id, attacker, besieged, choice.value)
    ctx.count("temple_loot", await loot_temples(ctx, besieged, attacker))


async def _spoils(
    ctx: TickContext,
    theatre: Theatre,
    report: BattleReport,
    result: BattleResult,
    *,
    column: Field,
    armies: dict[int, tuple[EntityRow, ArmyRow]],
    besieged: EntityRow | None,
) -> int:
    war, winner = report.war, report.winner
    taken = captives_taken(ctx, result, war.id)
    await advance(ctx, war.id, winner.id, ctx.rules.war_aims.battle_score)
    if report.outcome is BattleOutcome.SIEGE_BREACHED and besieged is not None:
        await _siege_won(ctx, theatre, war, winner, besieged)
    ctx.count("traits_earned", await earn_traits(ctx, result, column, {side: found[1].commander_entity_id for side, found in armies.items()}))
    return taken


async def _clashed(ctx: TickContext, war: WarRow) -> EntityRow:
    war.status = WarStatus.ONGOING
    war.battles += 1
    war.last_clash_epoch = ctx.epoch
    return await war_event(ctx.session, war)


def _escalate(ctx: TickContext, war: WarRow, event: EntityRow, gap: float) -> None:
    campaigns = ctx.rules.campaigns
    war.violence = violence_after(ctx.rules, war, gap)
    if (war.battles - 1) % campaigns.war_power_battle_interval == 0:
        event.power_level = clamp_int(event.power_level + campaigns.war_power_step, campaigns.war_power_min, campaigns.war_power_max)
    set_stats(event, severity=war.violence)


async def _honours(
    ctx: TickContext, war: WarRow, result: BattleResult, column: Field, armies: dict[int, tuple[EntityRow, ArmyRow]], *, attacker_id: int
) -> None:
    assert result.winner is not None
    winner = result.winner.entity
    await _toll(ctx, result, column, armies[winner.id][1].commander_entity_id)
    await hail_victor(ctx, winner, armies[winner.id][1].commander_entity_id)
    await capture_standard(ctx, war, result, attacker_id=attacker_id)
    event = await ctx.session.get(EntityRow, war.event_entity_id)
    honours = HonourTally()
    await honour_battle(ctx, result, event.name if event is not None else "the field", honours)
    for key, value in vars(honours).items():
        ctx.count(f"unit_honours_{key}", value)
    if result.outcome is OutcomeClass.MASSACRE and result.loser is not None:
        await terror(ctx, war.id, winner, result.loser.entity, "massacre")


async def _toll(ctx: TickContext, result: BattleResult, column: Field, commander_id: int | None) -> None:
    assert result.winner is not None and result.loser is not None
    for side in (result.winner, result.loser):
        await return_maimed(ctx, side.entity, side.lost)
        ctx.count("wounded_home", await send_home_wounded(ctx, side, result.wounded.get(side.entity.id, 0)))
        ctx.count("dead_raised", await raise_the_dead(ctx, side))
    ctx.count("baggage_taken", await take_baggage(ctx, result.winner, result.loser))
    ctx.count("tactics_learned", await learn_tactic(ctx, result, commander_id))
    await marsh_fever(ctx, column.terrain, (result.attacker, result.defender))
    await cohesion_after(ctx, result)


async def _ground_toll(
    ctx: TickContext, theatre: Theatre, ground: BattleGround, *, column: Field, place: EntityRow | None, sides: tuple[EntityRow, EntityRow]
) -> None:
    ctx.count("street_dead", await street_toll(ctx, column.terrain, place))
    leaders = [hero for side in sides for hero in theatre.sides.heroes_of(side.id)]
    ctx.count("exotic_shaken", await exotic_toll(ctx, column.terrain, ground.region, leaders))


async def hail_victor(ctx: TickContext, winner: EntityRow, commander_id: int | None) -> None:
    await on_victory(ctx, winner.id)
    if commander_id is not None:
        await acclaim_deed(ctx, commander_id, ReputationAxis.HEROISM, ctx.rules.local_renown.act_magnitude, place_id=winner.id)


async def fight_battle(
    ctx: TickContext,
    theatre: Theatre,
    item: OngoingWar,
    armies: dict[int, tuple[EntityRow, ArmyRow]],
    ground: BattleGround | None = None,
    *,
    forced: bool = False,
) -> BattleReport | None:
    campaigns = ctx.rules.campaigns
    war = item.war
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        return None
    if not forced and await parley(ctx, war, (attacker, defender), (armies[attacker.id][0].id, armies[defender.id][0].id)):
        return None
    ground = ground or BattleGround()
    besieged = _besieged(ctx.rules, defender)
    await _omens(ctx, theatre, ground, (attacker, defender), armies)
    attacker_power, defender_power = await _powers(ctx, theatre, war, (attacker, defender), armies, ground=ground, besieged=besieged)
    column = battle_field(ctx.rules, ground)
    forces = {side.id: [armies[side.id], *await allied_armies(ctx, war, side.id)] for side in (attacker, defender)}
    result = await clash(ctx, war.id, war.battles + 1, forces, (attacker, defender), powers=(attacker_power, defender_power), ground=column)
    assert result.winner is not None and result.loser is not None
    winner, loser = result.winner.entity, result.loser.entity
    gap = result.gap / PERCENT * max(attacker_power, defender_power)
    event = await _clashed(ctx, war)
    if result.refused:
        report = BattleReport(war, winner, loser, 0.0, BattleOutcome.REFUSED, "battle refused")
        return await _refused(ctx, report, result, ground, event=event, commander_id=armies[loser.id][1].commander_entity_id)
    _escalate(ctx, war, event, gap)
    army_entities = {side: army for side, (army, _) in armies.items()}
    siege: SiegeRow | None = None
    if besieged is not None:
        outcome, summary, siege = await _siege(ctx, war, besieged, winner, armies=army_entities, gap=gap, attacker_id=attacker.id)
        if outcome is BattleOutcome.SIEGE_BREACHED:
            await _sacked(ctx, besieged, armies, attacker, siege)
    else:
        outcome = _battle_score(war, ctx.rules, result, attacker_id=attacker.id, gap=gap)
        summary = f"{winner.name} prevailed over {loser.name} ({spoken(result.outcome)}; {spoken(result.winner.tactic)})"
    await _honours(ctx, war, result, column, armies, attacker_id=attacker.id)
    _community_losses(ctx, winner, loser, result.loser.lost / max(1, result.loser.start))
    await change_relation(ctx, attacker.id, defender.id, -campaigns.battle_relation, MemoryKind.FOUGHT_US, note="battle")
    son_id = await _patron_effects(ctx, theatre, winner, loser)
    place = await _place(ctx, theatre, loser, besieged, ground.site_id)
    report = BattleReport(war, winner, loser, gap, outcome, summary, ground=ground)
    await _record(ctx, report, place, army_entities, war.battles)
    await ctx.session.flush()
    row = _battle_row(ctx, report, result, place=place, siege=siege, ground=ground)
    await ctx.session.flush()
    log_phases(ctx, row.id, result)
    record_stacks(ctx, row, result)
    taken = await _spoils(ctx, theatre, report, result, column=column, armies=armies, besieged=besieged)
    await _mark_ground(ctx, ground, gap, outcome)
    await _ground_toll(ctx, theatre, ground, column=column, place=place, sides=(attacker, defender))
    await _heroics(ctx, theatre, report, row.id)
    await _seasoned(ctx, theatre, (winner, loser), armies)
    battle_incident = await _announce(ctx, report, result, event, armies=armies, place=place, son_id=son_id, taken=taken)
    ctx.count("battles")
    ctx.count("battle_captives", taken)
    with caused_by(battle_incident):
        report.settlement = await check_war_end(ctx, item, attacker, defender, armies)
    return report


async def _salt_earth(ctx: TickContext, war: WarRow, settlement: WarSettlement, victor: EntityRow, loser: EntityRow) -> None:
    settings = ctx.rules.scars
    if settlement.ending is not WarEnding.CONQUEST or (war.violence or 0) < settings.salted_violence:
        return
    if not ctx.rng(f"salt.{war.id}").chance(settings.salted_chance):
        return
    ground = await region_environment(ctx.session, loser.id)
    if ground is None:
        return
    add_scar(ground, ScarKind.MADE_BARREN, settings.salted_depth)
    await record(
        ctx,
        "war.made_barren",
        roles={IncidentRole.ACTOR: victor.id, IncidentRole.VICTIM: loser.id},
        facts={"depth": settings.salted_depth},
        place=ground.entity_id,
    )


async def check_war_end(
    ctx: TickContext, item: OngoingWar, attacker: EntityRow, defender: EntityRow, armies: dict[int, tuple[EntityRow, ArmyRow]]
) -> WarSettlement | None:
    campaigns = ctx.rules.campaigns
    war = item.war
    routed = next(
        (
            side
            for side in (attacker.id, defender.id)
            if (stat(armies[side][0], "morale") or 0) <= campaigns.disband_morale or (stat(armies[side][0], "size") or 0) < campaigns.disband_soldiers
        ),
        None,
    )
    tired = war.battles >= campaigns.exhaustion_min_battles and ctx.rng("war_end").chance(campaigns.four_battle_exhaustion_chance)
    score = war.score
    if abs(score) < campaigns.decisive_score and routed is None and not tired:
        return None
    decisive = abs(score) >= campaigns.decisive_score or abs(score) >= campaigns.exhaustion_victory_margin
    victor: EntityRow | None = None
    if routed is not None:
        victor = defender if routed == attacker.id else attacker
    elif decisive and score:
        victor = attacker if score > 0 else defender
    loser = (defender if victor.id == attacker.id else attacker) if victor is not None else None
    event = await war_event(ctx.session, war)
    if victor is None or loser is None:
        settlement = await end_war(ctx, war, WarEnding.WHITE_PEACE, reason="white peace")
        await record(
            ctx,
            "war.ended_white_peace",
            roles={IncidentRole.ACTOR: attacker.id, IncidentRole.OPPONENT: defender.id},
            facts={"war": event.id, "ending": WarEnding.WHITE_PEACE},
        )
        return settlement
    if routed is None and await fights_on(ctx, war, loser):
        return None
    settlement = await end_war(ctx, war, WarEnding.VICTORY, victor_id=victor.id, loser_id=loser.id)
    await _salt_earth(ctx, war, settlement, victor, loser)
    roles: dict[IncidentRole, int] = {IncidentRole.ACTOR: victor.id, IncidentRole.OPPONENT: loser.id}
    if routed is not None:
        roles[IncidentRole.SUBJECT] = armies[routed][0].id
    await record(ctx, f"war.ended_{settlement.ending.value}", roles=roles, facts={"war": event.id, "ending": settlement.ending})
    return settlement


async def _outbreak(ctx: TickContext, war: WarRow, attacker: EntityRow, defender: EntityRow, armies: dict[int, tuple[EntityRow, ArmyRow]]) -> None:
    first, second = armies[attacker.id][0], armies[defender.id][0]
    cause = await war_cause_incident(ctx.session, war.cause, attacker.id, defender.id, ctx.epoch)
    await record(
        ctx,
        "war.outbreak",
        roles={IncidentRole.ACTOR: attacker.id, IncidentRole.TARGET: defender.id},
        facts={
            "war": war.event_entity_id,
            "attacker_army": first.id,
            "defender_army": second.id,
            "attacker_soldiers": stat_or(first, "size", 0),
            "defender_soldiers": stat_or(second, "size", 0),
            "cause": war.cause,
        },
        cause=cause,
    )


async def _armies(ctx: TickContext, theatre: Theatre, war: WarRow, attacker: EntityRow, defender: EntityRow) -> dict[int, tuple[EntityRow, ArmyRow]]:
    armies = {side.id: await army_or_raise(ctx, theatre.strength, theatre.sides, side, war) for side in (attacker, defender)}
    for side in (attacker, defender):
        for ally_id in await allies_on_side(ctx, war, side.id):
            ally = await living_entity(ctx.session, ally_id)
            if ally is not None and is_community(ally):
                await army_or_raise(ctx, theatre.strength, theatre.sides, ally, war)
    return armies


async def omen_shift(ctx: TickContext, attacker: EntityRow) -> int:
    table = ctx.rules.campaigns
    folk = await people_of(ctx.session, attacker)
    if folk is None:
        return 0
    shift = await sky_omens(ctx.session, folk.id) * table.omen_battle_pct
    return max(-table.omen_battle_cap, min(table.omen_battle_cap, shift))


def _battle_chance(ctx: TickContext, theatre: Theatre, attacker: EntityRow, defender: EntityRow) -> int:
    banned = theatre.laws.has(NaturalLaw.WAR_BAN, attacker.world_id) or theatre.laws.has(NaturalLaw.WAR_BAN, defender.world_id)
    return ctx.rules.campaigns.battle_chance_war_ban if banned else ctx.rules.campaigns.battle_chance


async def _acclimatised(ctx: TickContext, theatre: Theatre, side: EntityRow, ground: BattleGround) -> bool:
    if ground.region is None:
        return True
    biology, _ = await profiles_of(ctx.session, side)
    if biology is not None:
        return acclimatised(ctx.rules, biology, ground.region.temperature_band)
    home = theatre.ground.region_of(side.id)
    if home is None:
        return True
    return abs(home.temperature - ground.region.temperature) <= ctx.rules.weather.acclimatised_within


async def _weather_losses(
    ctx: TickContext, theatre: Theatre, ground: BattleGround, sides: tuple[EntityRow, ...], armies: dict[int, tuple[EntityRow, ArmyRow]]
) -> int:
    lost = 0
    cap = ctx.rules.limits.army_soldier_cap
    for side in sides:
        army = armies[side.id][0]
        size = stat(army, "size") or 0
        share = season_losses(
            ctx.rules,
            ground.weather,
            ground.region,
            armour_pct=stat(army, "equipment") or 0,
            acclimatised=await _acclimatised(ctx, theatre, side, ground),
            air_pct=air_attrition_pct(ctx.rules, await ctx.session.get(WorldRow, army.world_id)),
        )
        dead = round_half_up(size * share)
        if dead:
            await resize(ctx.session, ctx.rules, army, clamp_int(size - dead, 0, cap))
            lost += dead
    return lost


async def _marches(ctx: TickContext, theatre: Theatre, sides: tuple[EntityRow, EntityRow], armies: dict[int, tuple[EntityRow, ArmyRow]]) -> list[March]:
    attacker, defender = sides
    knowledge = await KnowledgeMap.load(ctx.session)
    found: list[March] = []
    for side, goal, attacking in ((attacker, defender, True), (defender, defender, False)):
        army = armies[side.id][0]
        await muster(ctx, army, side, knowledge)
        ctx.count("vessels_mustered", await muster_fleet(ctx, army, side))
        profile = await profile_of(ctx, army, side)
        found.append(March(army, side, profile, profile.target_entity_id or theatre.neighbourhood.top_region(goal.id), attacking))
    return found


async def _manoeuvre(ctx: TickContext, theatre: Theatre, marches: list[March], index: int, *, ground: BattleGround, war_id: int) -> bool:
    atlas = theatre.neighbourhood.atlas
    weather = ground.weather.kind if ground.weather is not None else None
    knowledge = await KnowledgeMap.load(ctx.session)
    theatre.supply = theatre.supply or await network(ctx)
    command, supply = CommandTally(), SupplyTally()
    for position, march in enumerate(marches):
        enemy = marches[1 - position] if len(marches) == PAIR else None
        operation = await operation_of(ctx, march.army.id)
        short = operation.need > 0 and operation.delivered * PERCENT < operation.need * ctx.rules.culmination.supply_pct
        report = await issue_orders(ctx, march.army.id, march.profile, attacking=march.attacking, short=short, tally=command)
        log = await campaign_season(ctx, atlas, theatre.ground, march, index, weather=weather, season_row=ground.season, enemy=enemy)
        flow = await supply_season(ctx, march, index, raided=log.raided, order=report.order, web=theatre.supply, tally=supply)
        await culminate(ctx, march, flow, supply)
        ctx.count("march_regions", log.moved)
        ctx.count("attrition_dead", log.dead)
        ctx.count("deserters", log.deserted)
        ctx.count("storm_losses", await weather_the_storm(ctx, march, weather, knowledge))
    if ctx.rng(f"sea.{marches[0].army.id}.{index}").chance(ctx.rules.campaigns.season_engagement_pct):
        fight = await sea_battle(ctx, marches, weather, f"{ctx.epoch}.{index}.{marches[0].army.id}")
        if fight is not None:
            await _sea_report(ctx, fight)
    for key, value in (*vars(command).items(), *vars(supply).items()):
        ctx.count(f"operations_{key}", value)
    war = await ctx.session.get(WarRow, war_id)
    if war is not None:
        for march in marches:
            ctx.count("allies_marched", await march_with(ctx, war, march.owner.id, march.profile))
    contact = in_contact(atlas, marches[0].profile, marches[1].profile)
    if contact:
        await mark_front(ctx, war_id, marches[0].profile, marches[1].profile)
    return contact


async def _sea_report(ctx: TickContext, fight: SeaFight) -> None:
    lost = fight.sunk.get(fight.loser.army.id, 0)
    await record(
        ctx,
        "war.sea_battle",
        roles={
            IncidentRole.ACTOR: fight.winner.owner.id,
            IncidentRole.OPPONENT: fight.loser.owner.id,
            IncidentRole.MEMBER: [fight.winner.army.id, fight.loser.army.id],
        },
        facts={"sunk": lost, "winner_fleet": fight.winner.army.id, "loser_fleet": fight.loser.army.id},
        steps=fight.steps,
        place=fight.loser.profile.region_entity_id,
    )
    ctx.count("sea_battles")
    ctx.count("ships_sunk", sum(fight.sunk.values()))


async def clear_blockades(ctx: TickContext) -> int:
    rows = list(await ctx.session.scalars(select(ArmyProfileRow).where(ArmyProfileRow.blockade_entity_id.is_not(None))))
    if not rows:
        return 0
    pairs = {item.pair() for item in await ongoing_wars(ctx.session)}
    cleared = 0
    for profile in rows:
        army = await ctx.session.get(ArmyRow, profile.army_entity_id)
        target = profile.blockade_entity_id
        if army is None or target is None or unordered(army.owner_entity_id, target) not in pairs:
            profile.blockade_entity_id = None
            cleared += 1
    return cleared


async def _siege_won(ctx: TickContext, theatre: Theatre | None, war: WarRow, winner: EntityRow, besieged: EntityRow) -> None:
    score = ctx.rules.war_aims.siege_score
    await advance(ctx, war.id, winner.id, score, target=besieged.id)
    region = (theatre.neighbourhood.atlas if theatre is not None else await RegionAtlas.load(ctx.session)).top_region(besieged.id)
    if region is not None:
        await advance(ctx, war.id, winner.id, score, target=region, kinds=REGION_AIMS)


async def _besiege(
    ctx: TickContext, item: OngoingWar, sides: tuple[EntityRow, EntityRow], marches: list[March], armies: dict[int, tuple[EntityRow, ArmyRow]]
) -> SiegeSeason | None:
    defender = sides[1]
    besieged = _besieged(ctx.rules, defender)
    if besieged is None or marches[0].profile.stance is not Stance.BESIEGE or item.war.status is not WarStatus.ONGOING:
        return None
    step = await siege_season(ctx, item.war, besieged, marches[0], stat(armies[defender.id][0], "size") or 0)
    ctx.count("siege_seasons")
    ctx.count("sally_dead", step.sally_dead)
    return step


async def _surrender(
    ctx: TickContext,
    item: OngoingWar,
    sides: tuple[EntityRow, EntityRow],
    step: SiegeSeason,
    *,
    marches: list[March],
    armies: dict[int, tuple[EntityRow, ArmyRow]],
) -> WarSettlement | None:
    attacker, defender = sides
    campaigns = ctx.rules.campaigns
    siege, war = step.siege, item.war
    siege.status, siege.ended_epoch = SiegeStatus.BREACHED, ctx.epoch
    shift_stat(defender, "defense", -campaigns.breach_defense_loss)
    war.score += campaigns.breach_war_score
    choice = await sack_choice(ctx, siege, attacker, armies[attacker.id][1].commander_entity_id)
    homeward = [march for march in marches if march.owner.id == defender.id]
    dead = await sack(ctx, defender, marches[0].profile, homeward=homeward, victor=attacker, siege=siege, choice=choice)
    event = await war_event(ctx.session, war)
    await record(
        ctx,
        "war.siege.surrender",
        roles={IncidentRole.ACTOR: attacker.id, IncidentRole.TARGET: defender.id},
        facts={"war": event.id, "seasons": siege.rounds, "hunger": siege.starvation, "dead": dead},
        place=defender.id,
        cause=step.incident_id,
    )
    ctx.count("sieges_surrendered")
    await _siege_won(ctx, None, war, attacker, defender)
    return await check_war_end(ctx, item, attacker, defender, armies)


async def campaign(ctx: TickContext, theatre: Theatre, item: OngoingWar, armies: dict[int, tuple[EntityRow, ArmyRow]], cap: int) -> int:
    settings = ctx.rules.campaigns
    war = item.war
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        return 0
    seasons = grant_sub_steps(ctx.environment, settings.war_seasons())
    if not seasons:
        report = await fight_battle(ctx, theatre, item, armies)
        return int(report is not None)
    count = max(1, len(theatre.ground.seasons_of(defender.world_id)))
    ctx.count("war_aims_set", await set_aims(ctx, war, attacker, defender))
    marches = await _marches(ctx, theatre, (attacker, defender), armies)
    rng = ctx.rng(f"campaign.{war.id}")
    start = rng.below(count)
    years = ctx.rules.time.years_per_epoch
    per_year = max(1, settings.seasons_per_war_epoch)
    first_year = rng.below(max(1, years - seasons // per_year))
    base = epoch_start_year(ctx.epoch, years)
    bouts = 0
    lost = 0
    winter_shamed = False
    for index in range(seasons):
        year = base + min(years - 1, first_year + index // per_year)
        meeting = marches[0].profile.region_entity_id if in_contact(theatre.neighbourhood.atlas, marches[0].profile, marches[1].profile) else None
        ground = theatre.battleground(ctx, war, defender, slot=f"war.{war.id}.{index}", season_index=start + index % per_year, year=year, region_id=meeting)
        lost += await _weather_losses(ctx, theatre, ground, (attacker, defender), armies)
        contact = await _manoeuvre(ctx, theatre, marches, index, ground=ground, war_id=war.id)
        if await occupy(ctx, war, marches[0], defender, theatre.neighbourhood.atlas) is not None:
            ctx.count("occupation_seasons")
        step = await _besiege(ctx, item, (attacker, defender), marches, armies)
        if step is not None and step.surrendered:
            if await _surrender(ctx, item, (attacker, defender), step, marches=marches, armies=armies) is not None:
                break
            continue
        storm = step is not None and step.assault
        if ground.season is not None and dead_season(ctx, ground.season.growth):
            resting, winter_shamed = await winter_rest(ctx, attacker.id, defender.id, shamed=winter_shamed)
            if resting and not storm:
                ctx.count("winter_taboo_rest")
                continue
        suitability = ground.season.campaign if ground.season is not None else PERCENT
        if not contact or bouts >= cap or held(attacker.id, defender.id) or not (storm or rng.chance(settings.season_engagement_pct * suitability / PERCENT)):
            continue
        if storm:
            ground = replace(ground, urban=True)
        report = await fight_battle(ctx, theatre, item, armies, ground)
        bouts += 1
        if report is None or report.settlement is not None:
            break
    if bouts == 0 and war.status is WarStatus.ONGOING:
        await check_war_end(ctx, item, attacker, defender, armies)
    ctx.count("campaign_seasons", seasons)
    ctx.count("weather_dead", lost)
    return bouts


@reads(
    "army.equipment",
    "army.experience",
    "army.morale",
    "army.size",
    "cult.followers",
    "cult.zeal",
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "item.damage",
    "item.might",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "people.martiality",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.age_sets",
    "table.applied_fixups",
    "table.armies",
    "table.army_officers",
    "table.army_operations",
    "table.army_profiles",
    "table.army_templates",
    "table.army_unit_equipment",
    "table.army_units",
    "table.asabiyya",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.beast_profiles",
    "table.beliefs",
    "table.bias_weights",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.calendars",
    "table.campaign_fronts",
    "table.captive_cohorts",
    "table.captives",
    "table.casus_belli",
    "table.celestial_readings",
    "table.charms",
    "table.claims",
    "table.commander_traits",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.cosmos",
    "table.creator",
    "table.creator_taboos",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_values",
    "table.currencies",
    "table.custom_kinds",
    "table.deed_claims",
    "table.deeds",
    "table.demographic_transitions",
    "table.depots",
    "table.design_components",
    "table.design_mounts",
    "table.design_sections",
    "table.designated_heirs",
    "table.designs",
    "table.dimensional_events",
    "table.dimensions",
    "table.disease_profiles",
    "table.districts",
    "table.divine_standing",
    "table.divine_wounds",
    "table.echelons",
    "table.entities",
    "table.entity_flags",
    "table.entity_traits",
    "table.equipment_models",
    "table.equipment_stores",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.feuds",
    "table.forced_weather",
    "table.foreign_gods",
    "table.fortune_laws",
    "table.fortune_profiles",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.genomes",
    "table.goods",
    "table.goods_flows",
    "table.held_identities",
    "table.herds",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incident_step_states",
    "table.incident_steps",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.inspirations",
    "table.item_profiles",
    "table.language_profiles",
    "table.language_registers",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.learned_tactics",
    "table.lexemes",
    "table.loans",
    "table.lost_lands",
    "table.luck_beliefs",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.mind_attributes",
    "table.mind_facets",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.named_units",
    "table.natural_law_profiles",
    "table.network_nodes",
    "table.network_profiles",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.nutrition_scores",
    "table.occupations",
    "table.offices",
    "table.outbreaks",
    "table.passions",
    "table.peace_terms",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.perennials",
    "table.personality_values",
    "table.place_environment",
    "table.polity_map_knowledge",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.polity_treasury",
    "table.professions_of_value",
    "table.prostheses",
    "table.public_clocks",
    "table.regimes",
    "table.region_dangers",
    "table.region_environment",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.role_norms",
    "table.routes",
    "table.ruler_currencies",
    "table.sense_profiles",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sieges",
    "table.skills",
    "table.sky_events",
    "table.son_powers",
    "table.son_relations",
    "table.sons",
    "table.speaker_cohorts",
    "table.spirit_profiles",
    "table.spy_agents",
    "table.spy_networks",
    "table.stars",
    "table.structure_profiles",
    "table.theatres",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.transport_assets",
    "table.treaty_clauses",
    "table.treaty_profiles",
    "table.tributes",
    "table.unit_design_equipment",
    "table.unit_design_techniques",
    "table.unit_designs",
    "table.unit_honours",
    "table.vassalages",
    "table.vehicle_groups",
    "table.vessel_profiles",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
    "table.workshops",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "army.equipment",
    "army.experience",
    "army.morale",
    "army.size",
    "cult.followers",
    "event.severity",
    "faction.wealth",
    "mortal.charisma",
    "mortal.death_year",
    "mortal.hp",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.armies",
    "table.army_movements",
    "table.army_officers",
    "table.army_operations",
    "table.army_profiles",
    "table.army_unit_equipment",
    "table.army_units",
    "table.battle_casualties",
    "table.battle_phases",
    "table.battle_stacks",
    "table.battles",
    "table.bias_weights",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.campaign_fronts",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.commander_traits",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.deed_claims",
    "table.deeds",
    "table.depots",
    "table.design_components",
    "table.design_mounts",
    "table.design_sections",
    "table.design_techniques",
    "table.designs",
    "table.districts",
    "table.divine_standing",
    "table.echelons",
    "table.entities",
    "table.entity_flags",
    "table.equipment_models",
    "table.equipment_stores",
    "table.event_casualties",
    "table.event_footprints",
    "table.event_profiles",
    "table.feuds",
    "table.foreign_gods",
    "table.goods",
    "table.goods_flows",
    "table.house_members",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_step_states",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.learned_tactics",
    "table.loans",
    "table.lost_lands",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.named_units",
    "table.node_materials",
    "table.occupations",
    "table.offices",
    "table.peace_terms",
    "table.personality_values",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.region_environment",
    "table.relationships",
    "table.reputations",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sieges",
    "table.skills",
    "table.son_relations",
    "table.sons",
    "table.spy_agents",
    "table.spy_networks",
    "table.supply_flows",
    "table.thoughts",
    "table.traits",
    "table.transport_assets",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.tributes",
    "table.unit_honours",
    "table.vessel_profiles",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
)
async def campaigns(ctx: TickContext) -> None:
    rules = ctx.rules
    theatre = await Theatre.load(ctx)
    ongoing = await ongoing_wars(ctx.session)
    by_pair = {item.pair(): item for item in ongoing}
    pairs = ctx.rng("pairs").shuffled([(first, second) for first, second, _ in await hostile_pairs(ctx.session)])
    pairs.sort(key=lambda pair: unordered(*pair) not in by_pair)
    world_limit = await world_war_limit(ctx.session, ctx.rules)
    rng = ctx.rng("clash")
    for first_id, second_id in pairs:
        first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
        if first is None or second is None or held(first_id, second_id):
            continue
        item = by_pair.get(unordered(first_id, second_id))
        if item is None:
            open_count = len(ongoing)
            if open_count >= world_limit or any(
                sum(1 for war in ongoing if war.involves(side)) >= rules.diplomacy.community_war_cap for side in (first_id, second_id)
            ):
                continue
        if not rng.chance(clamp_int(_battle_chance(ctx, theatre, first, second) + await omen_shift(ctx, first), 0, PERCENT)):
            continue
        if item is None:
            war = await open_war(ctx, first, second)
            item = OngoingWar(war, first.id, second.id)
            ongoing.append(item)
            by_pair[item.pair()] = item
            armies = await _armies(ctx, theatre, war, first, second)
            await _outbreak(ctx, war, first, second, armies)
            if rules.campaigns.mobilization:
                continue
        else:
            attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
            if attacker is None or defender is None:
                continue
            armies = await _armies(ctx, theatre, item.war, attacker, defender)
        await campaign(ctx, theatre, item, armies, max(1, rules.campaigns.battle_cap))
    ctx.count("ordeals", await ordeals(ctx, theatre))


async def force_battle(ctx: TickContext, war_id: int, region_id: int | None = None) -> BattleReport:
    item = await require_ongoing_war(ctx.session, war_id)
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        raise ConflictError("Both sides must still stand to fight.")
    theatre = await Theatre.load(ctx)
    if region_id is not None and region_id not in theatre.ground.regions:
        raise ValidationFailedError("A battle can only be fought in a known region.")
    slot = f"forced.{item.war.id}.{item.war.battles}"
    ground = theatre.battleground(ctx, item.war, defender, slot=slot, season_index=item.war.battles, year=None, region_id=region_id)
    report = await fight_battle(ctx, theatre, item, await _armies(ctx, theatre, item.war, attacker, defender), ground, forced=True)
    if report is None:
        raise ConflictError("The battle could not be fought.")
    return report


async def open_war_now(ctx: TickContext, attacker_id: int, defender_id: int, reason: str = "by decree") -> WarRow:
    attacker, defender = await living_entity(ctx.session, attacker_id), await living_entity(ctx.session, defender_id)
    if not is_community(attacker) or not is_community(defender) or attacker is None or defender is None:
        raise ValidationFailedError("Only two living communities can wage a war.")
    if await require_existing_war(ctx, attacker.id, defender.id) is not None:
        raise ConflictError(f"{attacker.name} and {defender.name} are already at war.")
    bonds = BondRepository(ctx.session)
    if not await bonds.exists_between(attacker.id, defender.id, BondKind.ENEMY) and not await declare_war(
        ctx, attacker.id, defender.id, reason, community_cap=True
    ):
        raise ConflictError(f"{attacker.name} and {defender.name} cannot go to war now.")
    theatre = await Theatre.load(ctx)
    war = await open_war(ctx, attacker, defender, cause=WarCause.DECLARED, cause_text=reason)
    armies = await _armies(ctx, theatre, war, attacker, defender)
    await _outbreak(ctx, war, attacker, defender, armies)
    return war


async def require_existing_war(ctx: TickContext, first_id: int, second_id: int) -> OngoingWar | None:
    pair = unordered(first_id, second_id)
    return next((item for item in await ongoing_wars(ctx.session, first_id) if item.pair() == pair), None)


async def raise_war_army(ctx: TickContext, war_id: int, community_id: int) -> EntityRow:
    item = await require_ongoing_war(ctx.session, war_id)
    community = await living_entity(ctx.session, community_id)
    if community is None or not item.involves(community.id):
        raise ValidationFailedError("Only a living side of the war can raise an army for it.")
    theatre = await Theatre.load(ctx)
    army, _ = await raise_army(ctx, theatre.strength, theatre.sides, community, item.war)
    return army


async def disband_army(ctx: TickContext, army_id: int) -> None:
    row = await ctx.session.get(ArmyRow, army_id)
    army = await living_entity(ctx.session, army_id)
    if row is None or army is None or row.disbanded_epoch is not None:
        raise NotFoundError("No such standing army.")
    row.disbanded_epoch = ctx.epoch
    stand_down(ctx.rules, army, await living_entity(ctx.session, row.owner_entity_id))
    await disband_units(ctx, army.id, HonourTally())
    await retire_stacks(ctx.session, army.id)
    await retire_in(ctx, army, "disbanded by decree", close_bonds=True)


async def bless_army(ctx: TickContext, army_id: int, morale: int = 0, equipment: int = 0, experience: int = 0) -> EntityRow:
    army = await living_entity(ctx.session, army_id)
    if army is None or army.entity_type is not EntityType.ARMY:
        raise NotFoundError("No such army.")
    for key, delta in (("morale", morale), ("equipment", equipment), ("experience", experience)):
        shift_stat(army, key, delta)
    await ctx.session.flush()
    return army


async def order_duel(ctx: TickContext, first_id: int, second_id: int, war_id: int | None = None) -> str:
    first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
    if first is None or second is None or first.id == second.id:
        raise ValidationFailedError("A duel needs two different living mortals.")
    if first.entity_type is not EntityType.MORTAL or second.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only mortals fight duels.")
    war = (await require_ongoing_war(ctx.session, war_id)).war if war_id is not None else None
    theatre = await Theatre.load(ctx)
    fought_out = await duel(ctx, theatre, first, second, war=war, anchor_id=war.event_entity_id if war is not None else None)
    await record(
        ctx,
        "war.duel_decree",
        roles={IncidentRole.ACTOR: first.id, IncidentRole.OPPONENT: second.id},
        facts={"victor": fought_out.winner_id, "war": war.event_entity_id if war is not None else None},
        cause=fought_out.incident_id,
    )
    return fought_out.text


async def grant_victory(ctx: TickContext, war_id: int, victor_id: int) -> WarSettlement:
    item = await require_ongoing_war(ctx.session, war_id)
    if not item.involves(victor_id):
        raise ValidationFailedError("The victor must be a side of the war.")
    loser_id = item.foe_of(victor_id)
    return await end_war(ctx, item.war, WarEnding.VICTORY, victor_id=victor_id, loser_id=loser_id)


async def end_war_by_decree(ctx: TickContext, war_id: int, ending: WarEnding = WarEnding.PEACE) -> WarSettlement:
    if ending in END_WAR_BY_DECREE_WAR_ENDINGS:
        raise ValidationFailedError("Grant a victory to a side instead.")
    item = await require_ongoing_war(ctx.session, war_id)
    return await end_war(ctx, item.war, ending, reason=f"{ENDING_LABELS[ending]} by decree", close_hostility=True)


async def incite_uprising(ctx: TickContext, community_id: int) -> bool:
    community = await living_entity(ctx.session, community_id)
    if community is None or not is_community(community):
        raise ValidationFailedError("Only a living community can rise up.")
    target = await uprising_target(ctx.session, community)
    if target.id == community.id:
        raise ConflictError(f"No one rules {community.name}; there is no one to rise against.")
    return await declare_war(ctx, community.id, target.id, "uprising", cause=WarCause.UPRISING, world_cap=False)


PHASES = (Phase("war_upkeep", war_upkeep), Phase("campaigns", campaigns))
