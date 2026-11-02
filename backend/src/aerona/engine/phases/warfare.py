from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.constants.warfare import BATTLE_NAME_TEMPLATE, SIEGE_NAME_TEMPLATE
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.war import BattleOutcome, SiegeStatus, WarCause, WarEnding, WarStatus
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.levies import demobilise
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_float, clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
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

    @classmethod
    async def load(cls, ctx: TickContext) -> "Theatre":
        neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
        return cls(
            await MilitaryStrength.load(ctx.session, ctx.rules),
            await SideIndex.load(ctx.session, neighbourhood),
            neighbourhood,
            await ctx.laws(),
        )


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
        await declare_war(ctx, rebels.id, target.id, bond.description or "uprising", world_cap=False, since_epoch=bond.epoch)
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


async def war_upkeep(ctx: TickContext) -> None:
    ctx.count("armies_stood_down", await idle_armies(ctx))
    ctx.count("stale_wars_closed", await close_stale_wars(ctx))
    ctx.count("uprisings_redirected", await redirect_uprisings(ctx))
    ctx.count("subject_wars_ended", await end_wars_with_subjects(ctx))


async def battle_power(ctx: TickContext, theatre: Theatre, community: EntityRow, army: EntityRow, army_row: ArmyRow) -> float:
    campaigns = ctx.rules.campaigns
    commander = await commander_of(ctx.session, army_row)
    command = 0.0
    if commander is not None:
        total = (stat(commander, "strength") or 0) + (stat(commander, "intellect") or 0) + (stat(commander, "charisma") or 0)
        command = total / campaigns.strength_commander_divisor
    patron = await theatre.strength.patron_bonus(community)
    return (
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


async def _siege_row(ctx: TickContext, war: WarRow, besieged: EntityRow, besieger: EntityRow) -> SiegeRow:
    statement = select(SiegeRow).where(SiegeRow.war_id == war.id, SiegeRow.besieged_entity_id == besieged.id, SiegeRow.status == SiegeStatus.ONGOING)
    row = await ctx.session.scalar(statement.limit(1))
    if row is None:
        row = SiegeRow(
            war_id=war.id, besieged_entity_id=besieged.id, besieger_entity_id=besieger.id, status=SiegeStatus.ONGOING, started_epoch=ctx.epoch, rounds=0
        )
        ctx.session.add(row)
    row.rounds += 1
    return row


async def _siege(
    ctx: TickContext, war: WarRow, besieged: EntityRow, winner: EntityRow, *, armies: dict[int, EntityRow], gap: float, attacker_id: int
) -> tuple[BattleOutcome, str, SiegeRow]:
    campaigns = ctx.rules.campaigns
    besieger = next(entity_id for entity_id in armies if entity_id != besieged.id)
    besieger_entity = await living_entity(ctx.session, besieger)
    siege = await _siege_row(ctx, war, besieged, besieger_entity or besieged)
    attacker_army = armies[besieger]
    society = await _society(ctx, besieged.id)
    food = society.stock_food if society is not None else campaigns.siege_default_supplies
    starving = campaigns.breach_starving_bonus_pct / PERCENT if food < campaigns.breach_starving_supplies else 0
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
        society.stock_food = max(0, society.stock_food - campaigns.siege_supply_loss)
    shift_stat(attacker_army, "morale", -campaigns.siege_attacker_morale_loss)
    return BattleOutcome.SIEGE_STARVATION, f"{besieger_name} laid siege to {besieged.name}; the walls hold but food is running low in the city", siege


async def _society(ctx: TickContext, entity_id: int) -> CommunitySocietyRow | None:
    return await ctx.session.get(CommunitySocietyRow, entity_id)


def _casualties(ctx: TickContext, winner_army: EntityRow, loser_army: EntityRow, gap: float) -> float:
    campaigns = ctx.rules.campaigns
    loss_loser = campaigns.loser_base_loss_pct / PERCENT + min(campaigns.loser_extra_loss_max_pct / PERCENT, gap / campaigns.loser_extra_loss_divisor)
    loss_winner = campaigns.winner_base_loss_pct / PERCENT + min(campaigns.winner_extra_loss_max_pct / PERCENT, gap / campaigns.winner_extra_loss_divisor)
    cap = ctx.rules.limits.army_soldier_cap
    set_stats(loser_army, size=clamp_int((stat(loser_army, "size") or 0) * (1 - loss_loser), 0, cap))
    set_stats(winner_army, size=clamp_int((stat(winner_army, "size") or 0) * (1 - loss_winner), 0, cap))
    shift_stat(loser_army, "morale", -campaigns.loser_morale_loss - round_half_up(gap / campaigns.loser_morale_diff_divisor))
    shift_stat(winner_army, "morale", campaigns.winner_morale_gain)
    shift_stat(winner_army, "experience", campaigns.winner_experience_gain)
    shift_stat(loser_army, "experience", campaigns.loser_experience_gain)
    return loss_loser


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


async def duel_power(ctx: TickContext, theatre: Theatre, hero: EntityRow) -> float:
    campaigns = ctx.rules.campaigns
    return (
        (stat(hero, "strength") or 0)
        + (stat(hero, "agility") or 0) / campaigns.duel_agility_divisor
        + await theatre.strength.weapon_power(hero, campaigns.duel_weapon_mult)
        + ctx.rng("duel").die(campaigns.duel_die) * campaigns.duel_die_mult
    )


async def duel(ctx: TickContext, theatre: Theatre, first: EntityRow, second: EntityRow, *, war: WarRow | None, anchor_id: int | None) -> str:
    campaigns = ctx.rules.campaigns
    bonds = BondRepository(ctx.session)
    event = await war_event(ctx.session, war) if war is not None else None
    context = event.name if event is not None else "single combat"
    if not await bonds.exists_between(first.id, second.id, BondKind.RIVAL):
        await bonds.connect(BondDraft(first.id, second.id, BondKind.RIVAL, ctx.epoch, context))
    if event is not None and war is not None:
        for hero in (first, second):
            await bonds.connect(BondDraft(event.id, hero.id, BondKind.PARTY_TO, ctx.epoch, "dueled", role=BondRole.DUELED, war_id=war.id))
    first_power = await duel_power(ctx, theatre, first)
    second_power = await duel_power(ctx, theatre, second)
    winner, loser = (first, second) if first_power >= second_power else (second, first)
    if ctx.rng("duel_death").chance(ctx.rules.campaigns.duel_death_chance):
        await death_path(ctx, loser, f"fell in a duel with {winner.name} in {context}", winner.id, f"{context} duel", forced=True, event_id=anchor_id)
        if anchor_id is not None:
            await bonds.connect(BondDraft(anchor_id, loser.id, BondKind.CAUSED, ctx.epoch, "fell in a duel"))
        shift_stat(winner, "charisma", campaigns.duel_winner_charisma)
        winner_side, loser_side = theatre.sides.side_of(winner), theatre.sides.side_of(loser)
        if winner_side is not None and loser_side is not None and winner_side != loser_side:
            await start_blood_feud(ctx, winner_side, loser_side, f"the blood of {loser.name}")
        return f" In a duel {winner.name} killed {loser.name}; now there is a blood feud between the two sides."
    hp = stat(loser, "hp")
    set_stats(loser, hp=clamp_int((hp if hp else campaigns.hero_default_hp) - campaigns.duel_loser_hp_loss, 1, ctx.rules.limits.hp_cap))
    return f" {winner.name} and {loser.name} dueled; {loser.name} was badly wounded."


async def _heroics(ctx: TickContext, theatre: Theatre, report: BattleReport) -> None:
    anchor = report.record.id if report.record is not None else report.war.event_entity_id
    winners, losers = theatre.sides.heroes_of(report.winner.id), theatre.sides.heroes_of(report.loser.id)
    if winners and losers and ctx.rng("duel_roll").chance(ctx.rules.campaigns.duel_chance):
        first, second = ctx.rng("duelists").pick(winners), ctx.rng("duelists").pick(losers)
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


async def fight_battle(ctx: TickContext, theatre: Theatre, item: OngoingWar, armies: dict[int, tuple[EntityRow, ArmyRow]]) -> BattleReport | None:
    campaigns = ctx.rules.campaigns
    war = item.war
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        return None
    besieged = _besieged(ctx.rules, defender)
    attacker_power = await battle_power(ctx, theatre, attacker, *armies[attacker.id])
    defender_power = await battle_power(ctx, theatre, defender, *armies[defender.id])
    winner, loser = (attacker, defender) if attacker_power >= defender_power else (defender, attacker)
    gap = abs(attacker_power - defender_power)
    war.status = WarStatus.ONGOING
    war.battles += 1
    war.last_clash_epoch = ctx.epoch
    war.violence = violence_after(ctx.rules, war, gap)
    event = await war_event(ctx.session, war)
    if (war.battles - 1) % campaigns.war_power_battle_interval == 0:
        event.power_level = clamp_int(event.power_level + campaigns.war_power_step, campaigns.war_power_min, campaigns.war_power_max)
    set_stats(event, severity=war.violence)
    army_entities = {side: army for side, (army, _) in armies.items()}
    siege: SiegeRow | None = None
    if besieged is not None:
        outcome, summary, siege = await _siege(ctx, war, besieged, winner, armies=army_entities, gap=gap, attacker_id=attacker.id)
    else:
        great = gap >= campaigns.great_victory_diff
        war.score += (1 if winner.id == attacker.id else -1) * (campaigns.great_victory_score if great else 1)
        outcome = BattleOutcome.GREAT_VICTORY if great else BattleOutcome.FIELD_VICTORY
        summary = f"{winner.name} prevailed over {loser.name}"
    loss = _casualties(ctx, army_entities[winner.id], army_entities[loser.id], gap)
    _community_losses(ctx, winner, loser, loss)
    await change_relation(ctx, attacker.id, defender.id, -campaigns.battle_relation, "battle")
    son_id = await _patron_effects(ctx, theatre, winner, loser)
    place = await _place(ctx, theatre, loser, besieged)
    report = BattleReport(war, winner, loser, gap, outcome, summary)
    await _record(ctx, report, place, army_entities, war.battles)
    await ctx.session.flush()
    ctx.session.add(
        BattleRow(
            war_id=war.id,
            epoch=ctx.epoch,
            sequence=war.battles,
            record_entity_id=report.record.id if report.record is not None else None,
            place_entity_id=place.id if place is not None else None,
            winner_entity_id=winner.id,
            loser_entity_id=loser.id,
            outcome=outcome,
            gap=gap,
            siege_id=siege.id if siege is not None else None,
        )
    )
    await _heroics(ctx, theatre, report)
    ids = [*([report.record.id] if report.record is not None else []), war.event_entity_id, winner.id, loser.id, *report.ids]
    text = f"{event.name}: {summary}.{''.join(report.hero_texts)}"
    await ctx.chronicle(ChronicleKind.WAR, text, template_key=f"war.battle.{outcome.value}", entity_ids=ids, son_id=son_id, feed_category=FeedCategory.WAR)
    ctx.count("battles")
    report.settlement = await check_war_end(ctx, item, attacker, defender, armies)
    return report


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
    terms = f"conquered {loser.name}" if settlement.ending is WarEnding.CONQUEST else f"{loser.name} will pay tribute"
    rout = f" {armies[routed][0].name} disbanded." if routed is not None else ""
    extra = "".join(f" {note}" for note in settlement.notes)
    text = f"{event.name} ended: {victor.name} won ({terms}).{rout}{extra}"
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
            battles += 1
            attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
            if attacker is None or defender is None:
                continue
            armies = await _armies(ctx, theatre, item.war, attacker, defender)
        await fight_battle(ctx, theatre, item, armies)


async def force_battle(ctx: TickContext, war_id: int) -> BattleReport:
    item = await require_ongoing_war(ctx.session, war_id)
    attacker, defender = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    if attacker is None or defender is None:
        raise ConflictError("Both sides must still stand to fight.")
    theatre = await Theatre.load(ctx)
    report = await fight_battle(ctx, theatre, item, await _armies(ctx, theatre, item.war, attacker, defender))
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
    demobilise(ctx.rules, await living_entity(ctx.session, row.owner_entity_id), stat(army, "size") or 0)
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
    return await declare_war(ctx, community.id, target.id, "uprising", world_cap=False)


PHASES = (Phase("war_upkeep", war_upkeep), Phase("campaigns", campaigns))
