from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.mind import COMMAND_SKILLS
from aerona.constants.units import PERCENT
from aerona.constants.warfare import BATTLE_NAME_TEMPLATE, SIEGE_NAME_TEMPLATE
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, OccupationRow
from aerona.db.tables.mind import VALUE_MAX
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, SiegeRow, WarRow, WarSideRow
from aerona.domain.enums.body import Capacity, HarmCause
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.military import DuelContext, DuelEnd, OutcomeClass, Stance, StarvationStage
from aerona.domain.enums.mind import ActKind, MemoryKind, ValueAxis
from aerona.domain.enums.society import Commodity, NaturalLaw
from aerona.domain.enums.war import BattleOutcome, SiegeStatus, WarCause, WarEnding, WarStatus
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.body.book import effective, strike_style
from aerona.engine.body.cohorts import return_maimed
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.equipment import march_burden, siege_engines, suffer_heat
from aerona.engine.environment.battleground import BattleGround, attack_factor, defend_factor, night_chance, omen_morale, scar_battlefield, season_losses
from aerona.engine.environment.book import EnvironmentBook, add_scar, region_environment, scar_region
from aerona.engine.environment.years import grant_sub_steps
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.arms import wear_in_duel
from aerona.engine.lore.rites import warded
from aerona.engine.lore.taboos import dead_season, forbidden, winter_rest
from aerona.engine.military.aims import REGION_AIMS, advance, set_aims
from aerona.engine.military.battle import BattleResult, Field
from aerona.engine.military.clash import captives_taken, cautious, clash, earn_traits, log_phases
from aerona.engine.military.duels import bout, fighter
from aerona.engine.military.logistics import March, campaign_season, in_contact, mark_front
from aerona.engine.military.naval import SeaFight, sea_battle, weather_the_storm
from aerona.engine.military.occupation import announce_partisans, end_occupations, occupy, partisans, seeks_peace, weary
from aerona.engine.military.siege import SiegeSeason, open_siege, sack, siege_season, wall_defence
from aerona.engine.military.units import muster, profile_of
from aerona.engine.mind.book import best_effective, values_for
from aerona.engine.mind.hooks import duelled, fought, judged
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap, LawBook
from aerona.engine.primitives.levies import demobilise, stand_down
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_float, clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.records import death_path
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
)
from aerona.engine.services.war_geography import Neighbourhood
from aerona.engine.services.war_resolution import ENDING_LABELS, WarSettlement, close_stale_wars, end_war, settle_peace
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

POPULATION_CAPS = {EntityType.SETTLEMENT: "settlement_population_cap", EntityType.PEOPLE: "people_population_cap"}


@dataclass
class Theatre:
    strength: MilitaryStrength
    sides: SideIndex
    neighbourhood: Neighbourhood
    laws: LawBook
    ground: EnvironmentBook

    @classmethod
    async def load(cls, ctx: TickContext) -> "Theatre":
        neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
        return cls(
            await MilitaryStrength.load(ctx.session, ctx.rules),
            await SideIndex.load(ctx.session, neighbourhood),
            neighbourhood,
            await ctx.laws(),
            await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch),
        )

    def battleground(self, ctx: TickContext, war: WarRow, defender: EntityRow, *, slot: str, season_index: int, year: int | None) -> BattleGround:
        region = self.ground.region_of(defender.id)
        place = self.ground.place_of(defender.location_id) or self.ground.place_of(defender.id)
        season = self.ground.season_at(defender.world_id, season_index)
        weather = self.ground.weather(ctx.environment.world_seed, ctx.epoch, region, season, slot) if region is not None else None
        world = self.ground.worlds.get(defender.world_id)
        chance = night_chance(ctx.rules, world.world_type, world.day_length_hours) if world is not None else 0.0
        night = ctx.environment.rng(f"night.{war.id}.{slot}").chance(chance)
        return BattleGround(region=region, place=place, season=season, weather=weather, year=year, night=night)


@dataclass
class BattleReport:
    war: WarRow
    winner: EntityRow
    loser: EntityRow
    gap: float
    outcome: BattleOutcome
    summary: str
    record: EntityRow | None = None
    hero_texts: list[str] = field(default_factory=list)
    ids: list[int] = field(default_factory=list)
    settlement: WarSettlement | None = None
    refused: bool = False


def is_uprising(entity: EntityRow) -> bool:
    return entity.entity_type is EntityType.FACTION and (entity.engine_kind is EngineKind.REBELS or entity.social_class is not None)


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
        rebels, overlord = (first, second) if is_uprising(first) and not is_community(second) else (second, first)
        if not is_uprising(rebels) or is_community(overlord):
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
        if target is None or await can_open_war(ctx.session, ctx.rules, rebels.id, target.id, ctx.epoch, world_cap=False) is not None:
            continue
        await declare_war(ctx, rebels.id, target.id, bond.description or "uprising", cause=WarCause.UPRISING, world_cap=False, since_epoch=bond.epoch)
        redirected += 1
        text = f"{rebels.name} defies the rule of {overlord.name}; the revolt is now an open war with {target.name}."
        await ctx.chronicle(
            ChronicleKind.WAR, text, template_key="war.uprising_redirected", entity_ids=(rebels.id, overlord.id, target.id), feed_category=FeedCategory.WAR
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
        remaining = size - returning
        if remaining < campaigns.idle_army_disband_below:
            returning, remaining = size, 0
        set_stats(army, size=remaining)
        demobilise(ctx.rules, owner, returning)
        if remaining > 0:
            continue
        row.disbanded_epoch = ctx.epoch
        home = owner.name if owner is not None else "their homes"
        await retire_in(ctx, army, f"the army without a war stood down; its soldiers went back to {home}", close_bonds=True)
        await note(ctx, f"{army.name} stood down: soldiers without a war went back to {home}.", key="warfare.army_stood_down", ids=[army.id])
        disbanded += 1
    return disbanded


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
    fought = [row for row in rows if side_id in {row.winner_entity_id, row.loser_entity_id}]
    return sum(row.winner_losses if row.winner_entity_id == side_id else row.loser_losses for row in fought)


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
        for side_id in (item.attacker_id, item.defender_id):
            row = rows.get(side_id)
            if row is None:
                continue
            dead = await _side_losses(ctx, war, side_id)
            await weary(ctx, war, row, dead=dead, maimed=dead * ctx.rules.maimed.return_pct // PERCENT, occupied=await _occupied(ctx, atlas, side_id))
            behind = (war.score < 0) if side_id == item.attacker_id else (war.score > 0)
            if war.status is WarStatus.ONGOING and await seeks_peace(ctx, war, row, humiliated=behind):
                await _weary_peace(ctx, item, side_id, behind=behind)
                ended += 1
                break
    return ended


async def _weary_peace(ctx: TickContext, item: OngoingWar, side_id: int, *, behind: bool) -> None:
    war = item.war
    other = item.defender_id if side_id == item.attacker_id else item.attacker_id
    event = await war_event(ctx.session, war)
    if behind:
        await end_war(ctx, war, WarEnding.VICTORY, victor_id=other, loser_id=side_id, reason="war weariness")
    else:
        await end_war(ctx, war, WarEnding.WHITE_PEACE, reason="war weariness")
    weary_side = await living_entity(ctx.session, side_id)
    name = weary_side.name if weary_side is not None else "one side"
    await ctx.chronicle(
        ChronicleKind.WAR,
        f"{event.name} ended because {name} was worn out by war and sued for peace.",
        template_key="war.weary_peace",
        entity_ids=(war.event_entity_id, item.attacker_id, item.defender_id),
        feed_category=FeedCategory.WAR,
    )


@reads(
    "army.size",
    "table.armies",
    "table.army_profiles",
    "table.battles",
    "table.bonds",
    "table.calendars",
    "table.culture_values",
    "table.forced_weather",
    "table.node_materials",
    "table.occupations",
    "table.place_environment",
    "table.region_environment",
    "table.sky_events",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.world_seasons",
)
@writes("table.occupations", "table.war_sides")
async def war_upkeep(ctx: TickContext) -> None:
    ctx.count("armies_stood_down", await idle_armies(ctx))
    ctx.count("heat_losses", await heat_toll(ctx))
    ctx.count("stale_wars_closed", await close_stale_wars(ctx))
    ctx.count("uprisings_redirected", await redirect_uprisings(ctx))
    ctx.count("subject_wars_ended", await end_wars_with_subjects(ctx))
    ctx.count("blockades_lifted", await clear_blockades(ctx))
    lost = await partisans(ctx)
    ctx.count("partisan_dead", lost)
    await announce_partisans(ctx, lost)
    ctx.count("occupations_ended", await end_occupations(ctx))
    ctx.count("weary_peace", await weariness(ctx))


async def battle_power(ctx: TickContext, theatre: Theatre, community: EntityRow, army: EntityRow, army_row: ArmyRow) -> float:
    campaigns = ctx.rules.campaigns
    commander = await commander_of(ctx.session, army_row)
    command = 0.0
    if commander is not None:
        total = (
            await effective(ctx.session, commander, "strength", rules=ctx.rules)
            + await effective(ctx.session, commander, "intellect", capacity=Capacity.COMMAND, rules=ctx.rules)
            + await effective(ctx.session, commander, "charisma", capacity=Capacity.COMMAND, rules=ctx.rules)
        )
        tactics = await best_effective(ctx.session, commander.id, COMMAND_SKILLS)
        command = total / campaigns.strength_commander_divisor * (PERCENT + tactics * ctx.rules.skills.commander_tactics_pct / PERCENT) / PERCENT
    patron = await theatre.strength.patron_bonus(community)
    burden = max(0.0, 1 - await march_burden(ctx, army) * ctx.rules.materials.march_campaign_pct / PERCENT)
    return burden * (
        await theatre.strength.power(community) * campaigns.strength_community_share_pct / PERCENT
        + await theatre.strength.ally_power(community)
        + log_size(stat(army, "size") or 0) * campaigns.strength_size_log_mult
        + (stat(army, "morale") or 0) / campaigns.strength_morale_divisor
        + (stat(army, "equipment") or 0) / campaigns.strength_equipment_divisor
        + (stat(army, "experience") or 0) / campaigns.strength_experience_divisor
        + command
        + patron.bonus
        + ctx.rng("battle").die(campaigns.battle_die) * campaigns.battle_die_mult
    )


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
    starving += campaigns.breach_starving_bonus_pct / PERCENT * (siege.breaches + (siege.starvation in HUNGRY))
    breach_chance = clamp_float(gap / campaigns.breach_diff_divisor + starving, campaigns.breach_min_pct / PERCENT, campaigns.breach_max_pct / PERCENT)
    sign = 1 if winner.id == attacker_id else -1
    besieger_name = besieger_entity.name if besieger_entity is not None else "the besiegers"
    if winner.id == besieged.id:
        war.score += sign
        shift_stat(attacker_army, "morale", -campaigns.siege_repelled_morale_loss)
        siege.status, siege.ended_epoch = SiegeStatus.REPULSED, ctx.epoch
        return BattleOutcome.SIEGE_REPULSED, f"{besieged.name} repulsed the siege from behind its walls", siege
    if ctx.rng("breach").probability(breach_chance):
        shift_stat(besieged, "defense", -campaigns.breach_defense_loss)
        war.score += sign * campaigns.breach_war_score
        siege.status, siege.ended_epoch = SiegeStatus.BREACHED, ctx.epoch
        return BattleOutcome.SIEGE_BREACHED, f"{besieger_name} breached the walls of {besieged.name}", siege
    population = stat(besieged, "population") or campaigns.siege_default_population
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
    shift_stat(attacker_army, "morale", -campaigns.siege_attacker_morale_loss)
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


async def _place(ctx: TickContext, theatre: Theatre, loser: EntityRow, besieged: EntityRow | None) -> EntityRow | None:
    if besieged is not None:
        return besieged
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
    body = (
        f"Clash #{sequence} of {event.name}. {winner_army.name} ({stat(winner_army, 'size') or 0} soldiers, morale {stat(winner_army, 'morale') or 0}) "
        f"against {loser_army.name} ({stat(loser_army, 'size') or 0} soldiers, morale {stat(loser_army, 'morale') or 0}). {report.summary}."
    )
    record = await create_record(
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
    report.record = record
    await bonds.connect(BondDraft(record.id, event.id, BondKind.PART_OF, ctx.epoch, "battle", war_id=report.war.id))
    await bonds.connect(BondDraft(record.id, report.winner.id, BondKind.PARTY_TO, ctx.epoch, "victor", role=BondRole.VICTOR, war_id=report.war.id))
    await bonds.connect(BondDraft(record.id, report.loser.id, BondKind.PARTY_TO, ctx.epoch, "loser", role=BondRole.LOSER, war_id=report.war.id))


async def duel(
    ctx: TickContext,
    theatre: Theatre,
    first: EntityRow,
    second: EntityRow,
    *,
    war: WarRow | None,
    anchor_id: int | None,
    context: DuelContext = DuelContext.WAR,
) -> str:
    campaigns = ctx.rules.campaigns
    bonds = BondRepository(ctx.session)
    event = await war_event(ctx.session, war) if war is not None else None
    label = event.name if event is not None else "single combat"
    if not await bonds.exists_between(first.id, second.id, BondKind.RIVAL):
        await bonds.connect(BondDraft(first.id, second.id, BondKind.RIVAL, ctx.epoch, label))
    if event is not None and war is not None:
        for hero in (first, second):
            await bonds.connect(BondDraft(event.id, hero.id, BondKind.PARTY_TO, ctx.epoch, "dueled", role=BondRole.DUELED, war_id=war.id))
    result = bout(ctx.rules, ctx.rng(f"duel.{first.id}.{second.id}.{ctx.epoch}"), await fighter(ctx, first), await fighter(ctx, second), context)
    await duelled(ctx, first)
    await duelled(ctx, second)
    await wear_in_duel(ctx, first.id, result.exchanges)
    await wear_in_duel(ctx, second.id, result.exchanges)
    winner, loser = result.winner.entity, result.loser.entity
    await judged(ctx, winner.id, loser.id, ActKind.DUELLING, note=label)
    style = await strike_style(ctx.session, ctx.rules, winner, loser)
    ctx.count(f"duel_{result.end.value}")
    if result.killed:
        cause = f"fell in a duel with {winner.name} in {label}"
        await death_path(ctx, loser, cause, winner.id, f"{label} duel", forced=True, event_id=anchor_id, harm=HarmCause.DUEL, style=style)
        if anchor_id is not None:
            await bonds.connect(BondDraft(anchor_id, loser.id, BondKind.CAUSED, ctx.epoch, "fell in a duel"))
        shift_stat(winner, "charisma", campaigns.duel_winner_charisma)
        winner_side, loser_side = theatre.sides.side_of(winner), theatre.sides.side_of(loser)
        if winner_side is not None and loser_side is not None and winner_side != loser_side:
            await start_blood_feud(ctx, winner_side, loser_side, f"the blood of {loser.name}")
        return f" In a duel of {result.exchanges} exchanges {winner.name} killed {loser.name}; now there is a blood feud between the two sides."
    if stat(loser, "hp") is None:
        set_stats(loser, hp=campaigns.hero_default_hp)
    harm = campaigns.duel_loser_hp_loss if result.end is DuelEnd.CRIPPLED else result.loser.harm
    if harm > 0:
        await apply_hits(ctx, loser, Harm(harm, HarmCause.DUEL, "fell in a duel", source_node_id=winner.id, killer_id=winner.id, style=style), lethal=False)
    ending = DUEL_ENDINGS[result.end].format(winner=winner.name, loser=loser.name)
    mercy = f" {winner.name} spared the fallen." if result.spared else ""
    return f" {winner.name} and {loser.name} dueled for {result.exchanges} exchanges; {ending}.{mercy}"


async def _seasoned(ctx: TickContext, theatre: Theatre, sides: tuple[EntityRow, ...], armies: dict[int, tuple[EntityRow, ArmyRow]]) -> None:
    for side in sides:
        for hero in theatre.sides.heroes_of(side.id):
            await fought(ctx, hero, survived=hero.status is EntityStatus.CANON)
        found = armies.get(side.id)
        commander = await commander_of(ctx.session, found[1]) if found is not None else None
        if commander is not None:
            await fought(ctx, commander, commander=True, survived=commander.status is EntityStatus.CANON)


async def _heroics(ctx: TickContext, theatre: Theatre, report: BattleReport) -> None:
    anchor = report.record.id if report.record is not None else report.war.event_entity_id
    winners, losers = theatre.sides.heroes_of(report.winner.id), theatre.sides.heroes_of(report.loser.id)
    if winners and losers and ctx.rng("duel_roll").chance(ctx.rules.campaigns.duel_chance):
        first, second = ctx.rng("duelists").pick(winners), ctx.rng("duelists").pick(losers)
        if not await forbidden(ctx, first.id, ActKind.DUELLING):
            report.hero_texts.append(await duel(ctx, theatre, first, second, war=report.war, anchor_id=anchor))
            report.ids.extend((first.id, second.id))
    candidates = [hero for hero in theatre.sides.heroes_of(report.loser.id) if hero.status is EntityStatus.CANON]
    if candidates and ctx.rng("capture").chance(ctx.rules.campaigns.capture_chance):
        prisoner = ctx.rng("captive").pick(candidates)
        event = await war_event(ctx.session, report.war)
        await take_captive(ctx, report.winner, prisoner, report.war, description=event.name, home_id=report.loser.id)
        theatre.sides.mark_captive(prisoner.id)
        await BondRepository(ctx.session).connect(BondDraft(anchor, prisoner.id, BondKind.CAUSED, ctx.epoch, "was captured"))
        report.hero_texts.append(f" {prisoner.name} was taken prisoner.")
        report.ids.append(prisoner.id)


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


DUEL_ENDINGS = {
    DuelEnd.YIELD: "{loser} yielded",
    DuelEnd.DISARM: "{loser} lost the weapon and yielded",
    DuelEnd.CRIPPLED: "{loser} was crippled",
    DuelEnd.DEATH: "{loser} died",
    DuelEnd.EXHAUSTION: "both were spent and {winner} stood the steadier",
}
HUNGRY = frozenset({StarvationStage.FAMINE, StarvationStage.TABOO_BROKEN})
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
    text = f"{event.name}: {report.loser.name} saw {report.winner.name} coming and would not give battle."
    await ctx.chronicle(
        ChronicleKind.WAR,
        text,
        template_key="war.battle.refused",
        entity_ids=(report.war.event_entity_id, report.winner.id, report.loser.id),
        feed_category=FeedCategory.WAR,
        year=ground.year,
    )
    ctx.count("battles_refused")
    return report


async def _announce(
    ctx: TickContext, report: BattleReport, event: EntityRow, *, ground: BattleGround, place: EntityRow | None, son_id: int | None, taken: int
) -> None:
    war = report.war
    ids = [*([report.record.id] if report.record is not None else []), war.event_entity_id, report.winner.id, report.loser.id, *report.ids]
    setting = ground.describe()
    lead = f"{event.name}, {setting}" if setting else event.name
    captives = f" {taken} soldiers were led away captive." if taken else ""
    text = f"{lead}: {report.summary}.{captives}{''.join(report.hero_texts)}"
    await ctx.chronicle(
        ChronicleKind.WAR,
        text,
        template_key=f"war.battle.{report.outcome.value}",
        entity_ids=ids,
        son_id=son_id,
        feed_category=FeedCategory.WAR,
        place_entity_id=place.id if place is not None else None,
        year=ground.year,
    )


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
        defender_power *= wall_defence(ctx, await open_siege(ctx, war, besieged, attacker)) * await warded(ctx, besieged.id)
    return attacker_power, defender_power


async def _sacked(ctx: TickContext, besieged: EntityRow, armies: dict[int, tuple[EntityRow, ArmyRow]], attacker: EntityRow) -> None:
    profile = await profile_of(ctx, armies[attacker.id][0], attacker)
    homeward = [March(army, besieged, await profile_of(ctx, army, besieged), None, False) for owner, (army, _) in armies.items() if owner == besieged.id]
    ctx.count("sack_dead", await sack(ctx, besieged, profile, homeward=homeward))


async def _spoils(
    ctx: TickContext,
    theatre: Theatre,
    report: BattleReport,
    result: BattleResult,
    *,
    field: Field,
    armies: dict[int, tuple[EntityRow, ArmyRow]],
    besieged: EntityRow | None,
) -> int:
    war, winner = report.war, report.winner
    taken = captives_taken(ctx, result, war.id)
    await advance(ctx, war.id, winner.id, ctx.rules.war_aims.battle_score)
    if report.outcome is BattleOutcome.SIEGE_BREACHED and besieged is not None:
        await _siege_won(ctx, theatre, war, winner, besieged)
    ctx.count("traits_earned", await earn_traits(ctx, result, field, {side: found[1].commander_entity_id for side, found in armies.items()}))
    return taken


def _escalate(ctx: TickContext, war: WarRow, event: EntityRow, gap: float) -> None:
    campaigns = ctx.rules.campaigns
    war.violence = violence_after(ctx.rules, war, gap)
    if (war.battles - 1) % campaigns.war_power_battle_interval == 0:
        event.power_level = clamp_int(event.power_level + campaigns.war_power_step, campaigns.war_power_min, campaigns.war_power_max)
    set_stats(event, severity=war.violence)


async def fight_battle(
    ctx: TickContext, theatre: Theatre, item: OngoingWar, armies: dict[int, tuple[EntityRow, ArmyRow]], ground: BattleGround | None = None
) -> BattleReport | None:
    campaigns = ctx.rules.campaigns
    war = item.war
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        return None
    ground = ground or BattleGround()
    besieged = _besieged(ctx.rules, defender)
    await _omens(ctx, theatre, ground, (attacker, defender), armies)
    attacker_power, defender_power = await _powers(ctx, theatre, war, (attacker, defender), armies, ground=ground, besieged=besieged)
    river = ground.region is not None and ground.region.river_class in {RiverClass.RIVER, RiverClass.GREAT_RIVER}
    field = Field(ground.terrain, ground.weather.kind if ground.weather is not None else None, ground.night, river)
    result = await clash(ctx, war.id, war.battles + 1, armies, (attacker, defender), powers=(attacker_power, defender_power), ground=field)
    assert result.winner is not None and result.loser is not None
    winner, loser = result.winner.entity, result.loser.entity
    gap = result.gap / PERCENT * max(attacker_power, defender_power)
    war.status = WarStatus.ONGOING
    war.battles += 1
    war.last_clash_epoch = ctx.epoch
    event = await war_event(ctx.session, war)
    if result.refused:
        report = BattleReport(war, winner, loser, 0.0, BattleOutcome.REFUSED, "battle refused")
        return await _refused(ctx, report, result, ground, event=event, commander_id=armies[loser.id][1].commander_entity_id)
    _escalate(ctx, war, event, gap)
    army_entities = {side: army for side, (army, _) in armies.items()}
    siege: SiegeRow | None = None
    if besieged is not None:
        outcome, summary, siege = await _siege(ctx, war, besieged, winner, armies=army_entities, gap=gap, attacker_id=attacker.id)
        if outcome is BattleOutcome.SIEGE_BREACHED:
            await _sacked(ctx, besieged, armies, attacker)
    else:
        outcome = _battle_score(war, ctx.rules, result, attacker_id=attacker.id, gap=gap)
        summary = f"{winner.name} prevailed over {loser.name} ({result.outcome.value}; {result.winner.tactic.value.replace('_', ' ')})"
    for side in (result.winner, result.loser):
        await return_maimed(ctx, side.entity, side.lost)
    _community_losses(ctx, winner, loser, result.loser.lost / max(1, result.loser.start))
    await change_relation(ctx, attacker.id, defender.id, -campaigns.battle_relation, MemoryKind.FOUGHT_US, note="battle")
    son_id = await _patron_effects(ctx, theatre, winner, loser)
    place = await _place(ctx, theatre, loser, besieged)
    report = BattleReport(war, winner, loser, gap, outcome, summary)
    await _record(ctx, report, place, army_entities, war.battles)
    await ctx.session.flush()
    row = _battle_row(ctx, report, result, place=place, siege=siege, ground=ground)
    await ctx.session.flush()
    log_phases(ctx, row.id, result)
    taken = await _spoils(ctx, theatre, report, result, field=field, armies=armies, besieged=besieged)
    await _mark_ground(ctx, ground, gap, outcome)
    await _heroics(ctx, theatre, report)
    await _seasoned(ctx, theatre, (winner, loser), armies)
    await _announce(ctx, report, event, ground=ground, place=place, son_id=son_id, taken=taken)
    ctx.count("battles")
    ctx.count("battle_captives", taken)
    report.settlement = await check_war_end(ctx, item, attacker, defender, armies)
    return report


async def _salt_earth(ctx: TickContext, war: WarRow, settlement: WarSettlement, loser: EntityRow) -> str:
    settings = ctx.rules.scars
    if settlement.ending is not WarEnding.CONQUEST or (war.violence or 0) < settings.salted_violence:
        return ""
    if not ctx.rng(f"salt.{war.id}").chance(settings.salted_chance):
        return ""
    ground = await region_environment(ctx.session, loser.id)
    if ground is None:
        return ""
    add_scar(ground, ScarKind.SALTED_EARTH, settings.salted_depth)
    return f" The conquerors salted the fields of {loser.name}."


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
        text = f"{event.name} ended with no victor; both sides were exhausted."
        await ctx.chronicle(
            ChronicleKind.WAR,
            text,
            template_key="war.ended_white_peace",
            entity_ids=(war.event_entity_id, attacker.id, defender.id),
            feed_category=FeedCategory.WAR,
        )
        return settlement
    settlement = await end_war(ctx, war, WarEnding.VICTORY, victor_id=victor.id, loser_id=loser.id)
    salted = await _salt_earth(ctx, war, settlement, loser)
    terms = f"conquered {loser.name}" if settlement.ending is WarEnding.CONQUEST else f"{loser.name} will pay tribute"
    rout = f" {armies[routed][0].name} disbanded." if routed is not None else ""
    extra = "".join(f" {note}" for note in settlement.notes)
    text = f"{event.name} ended: {victor.name} won ({terms}).{rout}{extra}{salted}"
    await ctx.chronicle(
        ChronicleKind.WAR,
        text,
        template_key=f"war.ended_{settlement.ending.value}",
        entity_ids=(war.event_entity_id, attacker.id, defender.id),
        feed_category=FeedCategory.WAR,
    )
    return settlement


async def _outbreak(ctx: TickContext, war: WarRow, attacker: EntityRow, defender: EntityRow, armies: dict[int, tuple[EntityRow, ArmyRow]]) -> None:
    first, second = armies[attacker.id][0], armies[defender.id][0]
    text = (
        f"War broke out between {attacker.name} and {defender.name}: {first.name} ({stat(first, 'size') or 0} soldiers) "
        f"faces {second.name} ({stat(second, 'size') or 0} soldiers)."
    )
    ids = (war.event_entity_id, attacker.id, defender.id, first.id, second.id)
    await ctx.chronicle(ChronicleKind.WAR, text, template_key="war.outbreak", entity_ids=ids, feed_category=FeedCategory.WAR)


async def _armies(ctx: TickContext, theatre: Theatre, war: WarRow, attacker: EntityRow, defender: EntityRow) -> dict[int, tuple[EntityRow, ArmyRow]]:
    return {side.id: await army_or_raise(ctx, theatre.strength, theatre.sides, side, war) for side in (attacker, defender)}


def _battle_chance(ctx: TickContext, theatre: Theatre, attacker: EntityRow, defender: EntityRow) -> int:
    banned = theatre.laws.has(NaturalLaw.WAR_BAN, attacker.world_id) or theatre.laws.has(NaturalLaw.WAR_BAN, defender.world_id)
    return ctx.rules.campaigns.battle_chance_war_ban if banned else ctx.rules.campaigns.battle_chance


def _acclimatised(ctx: TickContext, theatre: Theatre, side: EntityRow, ground: BattleGround) -> bool:
    home = theatre.ground.region_of(side.id)
    if home is None or ground.region is None:
        return True
    return abs(home.temperature - ground.region.temperature) <= ctx.rules.weather.acclimatised_within


def _weather_losses(
    ctx: TickContext, theatre: Theatre, ground: BattleGround, sides: tuple[EntityRow, ...], armies: dict[int, tuple[EntityRow, ArmyRow]]
) -> int:
    lost = 0
    cap = ctx.rules.limits.army_soldier_cap
    for side in sides:
        army = armies[side.id][0]
        size = stat(army, "size") or 0
        share = season_losses(
            ctx.rules, ground.weather, ground.region, armour_pct=stat(army, "equipment") or 0, acclimatised=_acclimatised(ctx, theatre, side, ground)
        )
        dead = round_half_up(size * share)
        if dead:
            set_stats(army, size=clamp_int(size - dead, 0, cap))
            lost += dead
    return lost


async def _marches(ctx: TickContext, theatre: Theatre, sides: tuple[EntityRow, EntityRow], armies: dict[int, tuple[EntityRow, ArmyRow]]) -> list[March]:
    attacker, defender = sides
    knowledge = await KnowledgeMap.load(ctx.session)
    found: list[March] = []
    for side, goal, attacking in ((attacker, defender, True), (defender, defender, False)):
        army = armies[side.id][0]
        await muster(ctx, army, side, knowledge)
        profile = await profile_of(ctx, army, side)
        found.append(March(army, side, profile, profile.target_entity_id or theatre.neighbourhood.top_region(goal.id), attacking))
    return found


async def _manoeuvre(ctx: TickContext, theatre: Theatre, marches: list[March], index: int, *, ground: BattleGround, war_id: int) -> bool:
    atlas = theatre.neighbourhood.atlas
    weather = ground.weather.kind if ground.weather is not None else None
    knowledge = await KnowledgeMap.load(ctx.session)
    for march in marches:
        log = await campaign_season(ctx, atlas, theatre.ground, march, index)
        ctx.count("march_regions", log.moved)
        ctx.count("attrition_dead", log.dead)
        ctx.count("deserters", log.deserted)
        ctx.count("storm_losses", await weather_the_storm(ctx, march, weather, knowledge))
    if ctx.rng(f"sea.{marches[0].army.id}.{index}").chance(ctx.rules.campaigns.season_engagement_pct):
        fight = await sea_battle(ctx, marches, weather, f"{ctx.epoch}.{index}.{marches[0].army.id}")
        if fight is not None:
            await _sea_report(ctx, fight)
    contact = in_contact(atlas, marches[0].profile, marches[1].profile)
    if contact:
        await mark_front(ctx, war_id, marches[0].profile, marches[1].profile)
    return contact


async def _sea_report(ctx: TickContext, fight: SeaFight) -> None:
    lost = fight.sunk.get(fight.loser.army.id, 0)
    text = f"At sea the ships of {fight.winner.owner.name} beat those of {fight.loser.owner.name}, sank {lost} crews and closed its harbours."
    await ctx.chronicle(
        ChronicleKind.WAR,
        text,
        template_key="war.sea_battle",
        entity_ids=(fight.winner.owner.id, fight.loser.owner.id, fight.winner.army.id, fight.loser.army.id),
        feed_category=FeedCategory.WAR,
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
    dead = await sack(ctx, defender, marches[0].profile, homeward=[march for march in marches if march.owner.id == defender.id])
    event = await war_event(ctx.session, war)
    hunger = "starving" if siege.starvation is not StarvationStage.NONE else "weary"
    text = (
        f"{event.name}: {defender.name}, {hunger} after {siege.rounds} seasons of siege, opened its gates to {attacker.name}; "
        f"{dead} townsfolk died in the sack."
    )
    await ctx.chronicle(
        ChronicleKind.WAR,
        text,
        template_key="war.siege.surrender",
        entity_ids=(war.event_entity_id, attacker.id, defender.id),
        feed_category=FeedCategory.WAR,
        place_entity_id=defender.id,
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
    seasons = grant_sub_steps(ctx.environment, settings.seasons_per_war_epoch)
    if not seasons:
        report = await fight_battle(ctx, theatre, item, armies)
        return int(report is not None)
    count = max(1, len(theatre.ground.seasons_of(defender.world_id)))
    ctx.count("war_aims_set", await set_aims(ctx, war, attacker, defender))
    marches = await _marches(ctx, theatre, (attacker, defender), armies)
    rng = ctx.rng(f"campaign.{war.id}")
    start = rng.below(count)
    years = ctx.rules.time.years_per_epoch
    first_year = rng.below(years)
    base = epoch_start_year(ctx.epoch, years)
    fought = 0
    lost = 0
    winter_shamed = False
    for index in range(seasons):
        year = base + min(years - 1, first_year + (start + index) // count)
        ground = theatre.battleground(ctx, war, defender, slot=f"war.{war.id}.{index}", season_index=start + index, year=year)
        lost += _weather_losses(ctx, theatre, ground, (attacker, defender), armies)
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
        if not contact or fought >= cap or not (storm or rng.chance(settings.season_engagement_pct * suitability / PERCENT)):
            continue
        report = await fight_battle(ctx, theatre, item, armies, ground)
        fought += 1
        if report is None or report.settlement is not None:
            break
    if fought == 0 and war.status is WarStatus.ONGOING:
        await check_war_end(ctx, item, attacker, defender, armies)
    ctx.count("campaign_seasons", seasons)
    ctx.count("weather_dead", lost)
    return fought


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
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "people.martiality",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "settlement.defense",
    "settlement.population",
    "table.armies",
    "table.army_profiles",
    "table.army_units",
    "table.beast_profiles",
    "table.bodies",
    "table.bonds",
    "table.calendars",
    "table.campaign_fronts",
    "table.captive_cohorts",
    "table.captives",
    "table.claims",
    "table.commander_traits",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.cosmos",
    "table.cult_tenets",
    "table.culture_values",
    "table.designated_heirs",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.forced_weather",
    "table.herds",
    "table.holder_levels",
    "table.holder_techniques",
    "table.injuries",
    "table.item_profiles",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.lexemes",
    "table.maimed_cohorts",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_materials",
    "table.nodes",
    "table.occupations",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.polity_treasury",
    "table.prostheses",
    "table.region_environment",
    "table.routes",
    "table.sieges",
    "table.skills",
    "table.sky_events",
    "table.son_powers",
    "table.son_relations",
    "table.speaker_cohorts",
    "table.spy_networks",
    "table.traits",
    "table.tributes",
    "table.vassalages",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
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
    "table.armies",
    "table.army_movements",
    "table.army_profiles",
    "table.army_units",
    "table.battle_phases",
    "table.battles",
    "table.bodies",
    "table.bonds",
    "table.campaign_fronts",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.maimed_cohorts",
    "table.memories",
    "table.name_registry",
    "table.occupations",
    "table.region_environment",
    "table.sieges",
    "table.skills",
    "table.son_relations",
    "table.sons",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.tributes",
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
    battles = new_wars = 0
    rng = ctx.rng("clash")
    for first_id, second_id in pairs:
        if battles >= rules.campaigns.battle_cap and new_wars >= rules.campaigns.new_war_cap:
            break
        first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
        if first is None or second is None:
            continue
        item = by_pair.get(unordered(first_id, second_id))
        if (battles >= rules.campaigns.battle_cap) if item is not None else (new_wars >= rules.campaigns.new_war_cap):
            continue
        if item is None:
            open_count = len(ongoing)
            if open_count >= rules.diplomacy.world_war_cap or any(
                sum(1 for war in ongoing if war.involves(side)) >= rules.diplomacy.community_war_cap for side in (first_id, second_id)
            ):
                continue
        if not rng.chance(_battle_chance(ctx, theatre, first, second)):
            continue
        if item is None:
            new_wars += 1
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
        battles += await campaign(ctx, theatre, item, armies, max(1, rules.campaigns.battle_cap - battles))


async def force_battle(ctx: TickContext, war_id: int) -> BattleReport:
    item = await require_ongoing_war(ctx.session, war_id)
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        raise ConflictError("Both sides must still stand to fight.")
    theatre = await Theatre.load(ctx)
    ground = theatre.battleground(ctx, item.war, defender, slot=f"forced.{item.war.id}.{item.war.battles}", season_index=item.war.battles, year=None)
    report = await fight_battle(ctx, theatre, item, await _armies(ctx, theatre, item.war, attacker, defender), ground)
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
    text = (await duel(ctx, theatre, first, second, war=war, anchor_id=war.event_entity_id if war is not None else None)).strip()
    await ctx.chronicle(ChronicleKind.WAR, text, template_key="war.duel_decree", entity_ids=(first.id, second.id), feed_category=FeedCategory.WAR)
    return text


async def grant_victory(ctx: TickContext, war_id: int, victor_id: int) -> WarSettlement:
    item = await require_ongoing_war(ctx.session, war_id)
    if not item.involves(victor_id):
        raise ValidationFailedError("The victor must be a side of the war.")
    loser_id = item.defender_id if victor_id == item.attacker_id else item.attacker_id
    return await end_war(ctx, item.war, WarEnding.VICTORY, victor_id=victor_id, loser_id=loser_id)


async def end_war_by_decree(ctx: TickContext, war_id: int, ending: WarEnding = WarEnding.PEACE) -> WarSettlement:
    if ending in (WarEnding.VICTORY, WarEnding.CONQUEST, WarEnding.TRIBUTE):
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
