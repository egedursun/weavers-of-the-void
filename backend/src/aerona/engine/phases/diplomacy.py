from dataclasses import dataclass

from sqlalchemy import and_, or_, select

from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.engine.body.cohorts import war_appetite
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import blockade_pressure
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import betrayal_drive, closeness, war_drive
from aerona.engine.phase import Phase
from aerona.engine.phases.afterlife import cosmic_court
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.queries import BondIndex, active_bonds, canon, living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import (
    blood_feud_pairs,
    change_relation,
    pair_key,
    relation,
)
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import (
    current_war,
    declare_war,
    expire_truces,
    hostile_pair_count,
    hostile_pairs,
    ongoing_war_count,
    ongoing_wars,
)
from aerona.engine.services.war_geography import Neighbourhood
from aerona.engine.services.war_resolution import end_war, settle_peace
from aerona.rules.registry import Rules

MARRIAGE_AGE_FALLBACK_KEY = "age"
HOSTILITY_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})


@dataclass
class DiplomacyCounters:
    declared: int = 0
    peaces: int = 0
    alliances: int = 0
    betrayals: int = 0
    exhaustion_peaces: int = 0


@reads("table.bonds")
@writes("table.bonds")
async def expire_truces_phase(ctx: TickContext) -> None:
    ctx.count("truces_expired", await expire_truces(ctx.session, ctx.rules, ctx.epoch))


async def _note(ctx: TickContext, text: str, key: str, ids: tuple[int, ...], kind: ChronicleKind = ChronicleKind.DIPLOMACY) -> None:
    feed = FeedCategory.WAR if kind is ChronicleKind.WAR else None
    await ctx.chronicle(kind, text, template_key=key, entity_ids=ids, feed_category=feed)


async def forget_mortal_grudges(ctx: TickContext) -> int:
    age = ctx.rules.diplomacy.mortal_grudge_forget_epochs
    if age <= 0:
        return 0
    horizon = ctx.epoch - age
    bonds = list(
        await ctx.session.scalars(
            select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE, BondRow.epoch <= horizon).order_by(BondRow.id)
        )
    )
    repository = BondRepository(ctx.session)
    forgotten = 0
    for bond in bonds:
        ends = [await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)]
        types = [end.entity_type for end in ends if end is not None]
        if len(types) != len(ends) or EntityType.MORTAL not in types or any(kind not in HOSTILITY_TYPES for kind in types):
            continue
        pair = or_(
            and_(BondRow.source_node_id == bond.source_node_id, BondRow.target_node_id == bond.target_node_id),
            and_(BondRow.source_node_id == bond.target_node_id, BondRow.target_node_id == bond.source_node_id),
        )
        recent = await ctx.session.scalar(select(BondRow.id).where(pair, BondRow.id != bond.id, BondRow.epoch > horizon).limit(1))
        if recent is not None:
            continue
        await repository.deactivate(bond, ctx.epoch, "grudge forgotten")
        forgotten += 1
    return forgotten


def grudge_limits(all_rules: Rules, pairs: int) -> tuple[int, int]:
    rules = all_rules.diplomacy
    pool = max(1, round(rules.world_war_cap * rules.grudge_pool_pct / PERCENT))
    excess = max(0, pairs - pool)
    fade_cap = rules.grudge_fade_cap + round(excess * rules.grudge_overflow_share_pct / PERCENT)
    forget_age = 0
    if rules.grudge_forget_epochs > 0:
        forget_age = max(rules.grudge_fade_min_age, round(rules.grudge_forget_epochs * min(1, pool / max(1, pairs))))
    return fade_cap, forget_age


async def _fade_grudges(ctx: TickContext, candidates: list[tuple[int, int, int]]) -> set[frozenset[int]]:
    rules = ctx.rules.diplomacy
    fade_cap, forget_age = grudge_limits(ctx.rules, await hostile_pair_count(ctx.session))
    faded: set[frozenset[int]] = set()
    for first_id, second_id, since in candidates:
        if len(faded) >= fade_cap:
            break
        age = ctx.epoch - since
        if age < rules.grudge_fade_min_age:
            continue
        first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
        if first is None or second is None or await current_war(ctx.session, first_id, second_id) is not None:
            continue
        improved = await relation(ctx.session, ctx.rules, first_id, second_id) >= rules.grudge_fade_relation
        forgotten = forget_age > 0 and age >= forget_age
        if not improved and not forgotten:
            continue
        await settle_peace(ctx, first_id, second_id, WarEnding.PEACE, "grudge faded" if improved else "grudge forgotten", apply_relation=False)
        faded.add(frozenset((first_id, second_id)))
        if improved:
            text = f"The old grudge between {first.name} and {second.name} has faded; no one remembers why they called each other enemies."
            await _note(ctx, text, "diplomacy.grudge_faded", (first_id, second_id))
        else:
            text = (
                f"The grudge between {first.name} and {second.name} lasted {age} epochs without a sword drawn and was forgotten; "
                "only the elders remember the enmity."
            )
            await _note(ctx, text, "diplomacy.grudge_forgotten", (first_id, second_id))
    ctx.count("grudges_faded", len(faded))
    return faded


async def _exhaustion_peaces(ctx: TickContext, candidates: list[tuple[int, int, int]], faded: set[frozenset[int]], counters: DiplomacyCounters) -> None:
    rules = ctx.rules.diplomacy
    rng = ctx.rng("exhaustion")
    for first_id, second_id, _ in candidates:
        if counters.exhaustion_peaces >= rules.exhaustion_peace_cap:
            break
        if frozenset((first_id, second_id)) in faded:
            continue
        first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
        war = await current_war(ctx.session, first_id, second_id)
        if first is None or second is None or war is None:
            continue
        duration = ctx.epoch - war.started_epoch
        if duration < rules.exhaustion_start_epoch or not rng.chance(min(rules.exhaustion_cap_pct, rules.exhaustion_growth_pct * duration)):
            continue
        await end_war(ctx, war, WarEnding.EXHAUSTION, reason="exhaustion peace")
        counters.exhaustion_peaces += 1
        text = f"The {duration}-epoch war between {first.name} and {second.name} ended in exhaustion."
        await _note(ctx, text, "diplomacy.exhaustion_peace", (war.event_entity_id, first_id, second_id), ChronicleKind.WAR)


async def form_alliance(ctx: TickContext, first: EntityRow, second: EntityRow, sides: SideIndex, marriage: bool) -> tuple[EntityRow, EntityRow] | None:
    rules = ctx.rules.diplomacy
    bonds = BondRepository(ctx.session)
    spouses: tuple[EntityRow, EntityRow] | None = None
    if marriage:
        first_heir = next(iter(_marriageable(ctx, sides, first.id)), None)
        second_heir = next(iter(_marriageable(ctx, sides, second.id)), None)
        if first_heir is not None and second_heir is not None:
            spouses = (first_heir, second_heir)
    await bonds.connect(BondDraft(first.id, second.id, BondKind.ALLY, ctx.epoch, "marriage alliance" if marriage else "oath of friendship"))
    if marriage and spouses is not None and not await bonds.exists_between(spouses[0].id, spouses[1].id, BondKind.LOVES):
        await bonds.connect(BondDraft(spouses[0].id, spouses[1].id, BondKind.LOVES, ctx.epoch, "marriage alliance"))
    if marriage:
        await change_relation(ctx, first.id, second.id, rules.marriage_relation, MemoryKind.MARRIED_INTO, note="marriage")
    ctx.count("alliances")
    return spouses


def _marriageable(ctx: TickContext, sides: SideIndex, community_id: int) -> list[EntityRow]:
    rules = ctx.rules.diplomacy
    return [hero for hero in sides.heroes_of(community_id) if (stat(hero, MARRIAGE_AGE_FALLBACK_KEY) or rules.default_hero_age) >= rules.marriage_min_age]


def _weight(ctx: TickContext, entity: EntityRow) -> int:
    for key in ("sway", "influence", "strength"):
        value = stat(entity, key)
        if value is not None:
            return value
    return ctx.rules.diplomacy.traitor_default_strength


async def abandon_mid_war(ctx: TickContext, traitor: EntityRow, victim: EntityRow) -> int:
    collapsed = 0
    rng = ctx.rng(f"betrayal.collapse.{traitor.id}.{victim.id}")
    for item in await ongoing_wars(ctx.session, victim.id):
        enemy_id = item.defender_id if item.attacker_id == victim.id else item.attacker_id
        enemy = await living_entity(ctx.session, enemy_id)
        if enemy is None or enemy.id == traitor.id or not rng.chance(ctx.rules.diplomacy.betrayal_war_collapse_chance):
            continue
        event = await living_entity(ctx.session, item.war.event_entity_id)
        await end_war(ctx, item.war, WarEnding.BETRAYAL, victor_id=enemy.id, loser_id=victim.id, reason="betrayal", apply_relation=False)
        war_name = event.name if event is not None else "the war"
        text = f"Abandoned by its ally {traitor.name}, {victim.name} could not hold the field and {war_name} was lost to {enemy.name}."
        await _note(ctx, text, "diplomacy.betrayal_war_lost", (victim.id, enemy.id, traitor.id))
        collapsed += 1
    ctx.count("wars_lost_to_betrayal", collapsed)
    return collapsed


async def betray(ctx: TickContext, first: EntityRow, second: EntityRow, neighbourhood: Neighbourhood, war_roll: bool) -> EntityRow:
    rules = ctx.rules.diplomacy
    await BondRepository(ctx.session).close_between(first.id, second.id, [BondKind.ALLY], ctx.epoch, "betrayal")
    traitor, victim = (first, second) if _weight(ctx, first) >= _weight(ctx, second) else (second, first)
    await change_relation(ctx, victim.id, traitor.id, -rules.betrayal_relation, MemoryKind.BETRAYED_ME, note="betrayal", reverse=MemoryKind.ILL_WILL)
    await abandon_mid_war(ctx, traitor, victim)
    if war_roll:
        await declare_war(ctx, traitor.id, victim.id, "betrayal", cause=WarCause.BETRAYAL)
    text = f"{traitor.name} stabbed its ally {victim.name} in the back; the oath was broken."
    await _note(ctx, text, "diplomacy.betrayal", (traitor.id, victim.id))
    await cosmic_court(ctx, traitor.id, victim.id)
    ctx.count("betrayals")
    return traitor


@dataclass(frozen=True)
class PairContext:
    bonds: BondIndex
    feuds: set[tuple[int, int]]


async def _pair_context(ctx: TickContext) -> PairContext:
    bonds = await BondIndex.load(ctx.session, [BondKind.TRADES_WITH, BondKind.ALLY, BondKind.ENEMY, BondKind.PAYS_TRIBUTE])
    return PairContext(bonds, await blood_feud_pairs(ctx.session))


async def settled_by_wergild(ctx: TickContext, first: EntityRow, second: EntityRow) -> bool:
    if not ctx.rng(f"wergild.{first.id}.{second.id}.{ctx.epoch}").chance(ctx.rules.vendetta.wergild_chance):
        return False
    if not await law_param(ctx.session, first.id, LawKind.BLOOD_FEUD, "wergild_allowed"):
        return False
    await change_relation(ctx, first.id, second.id, ctx.rules.treaties.wergild_value // 3, MemoryKind.GIFTED_ME, note="blood money paid")
    await _note(ctx, f"{first.name} and {second.name} settled their blood feud with wergild instead of war.", "diplomacy.wergild", (first.id, second.id))
    return True


async def _neighbour_pair(
    ctx: TickContext,
    first: EntityRow,
    second: EntityRow,
    *,
    pair: PairContext,
    sides: SideIndex,
    neighbourhood: Neighbourhood,
    counters: DiplomacyCounters,
) -> None:
    rules = ctx.rules.diplomacy
    rng = ctx.rng("neighbours")
    value = await relation(ctx.session, ctx.rules, first.id, second.id)
    enemy = pair.bonds.between(first.id, second.id, BondKind.ENEMY)
    ally = pair.bonds.between(first.id, second.id, BondKind.ALLY)
    war = await current_war(ctx.session, first.id, second.id) if enemy else None
    duration = ctx.epoch - war.started_epoch if war is not None else 0
    tired = (
        war is not None
        and duration >= rules.neighbor_exhaustion_start
        and rng.chance(min(rules.neighbor_exhaustion_cap_pct, rules.neighbor_exhaustion_growth_pct * duration))
    )
    feud = pair_key(first.id, second.id) in pair.feuds
    cap = rules.community_war_cap
    if (
        not enemy
        and value <= rules.grudge_threshold
        and not (feud and await settled_by_wergild(ctx, first, second))
        and counters.declared < rules.declarations_cap
        and await ongoing_war_count(ctx.session, first.id) < cap
        and await ongoing_war_count(ctx.session, second.id) < cap
        and rng.chance(
            rules.war_declaration_chance
            * min(await war_appetite(ctx, first), await war_appetite(ctx, second))
            * max(await war_drive(ctx.session, ctx.rules, first.id), await war_drive(ctx.session, ctx.rules, second.id))
        )
        and await declare_war(
            ctx, first.id, second.id, "blood feud turned to war" if feud else "accumulated grudge", cause=WarCause.VENDETTA if feud else WarCause.GRUDGE
        )
    ):
        counters.declared += 1
        tail = "; the blood feud is now a campaign" if feud else ""
        text = f"The grudge that had built up for years between {first.name} and {second.name} turned into open enmity{tail}."
        await _note(ctx, text, "diplomacy.war_declared", (first.id, second.id), ChronicleKind.WAR)
    elif (
        enemy
        and ((value >= rules.peace_threshold and rng.chance(rules.peace_chance + await blockade_pressure(ctx, first.id, second.id))) or tired)
        and counters.peaces < rules.peace_cap
    ):
        await settle_peace(ctx, first.id, second.id, WarEnding.PEACE, "peace")
        counters.peaces += 1
        how = f"worn out by {duration} epochs of war the two sides made a truce" if tired else "envoys swore a peace oath"
        await _note(ctx, f"{first.name} and {second.name} laid down arms; {how}.", "diplomacy.peace", (first.id, second.id))
    elif not enemy and not ally and value >= rules.alliance_threshold and counters.alliances < rules.alliance_cap and rng.chance(rules.alliance_chance):
        marriage = (
            bool(_marriageable(ctx, sides, first.id))
            and bool(_marriageable(ctx, sides, second.id))
            and rng.chance(rules.marriage_alliance_share_pct * await closeness(ctx.session, first.id, second.id))
        )
        spouses = await form_alliance(ctx, first, second, sides, marriage)
        counters.alliances += 1
        if marriage:
            wed = f": {spouses[0].name} married {spouses[1].name}" if spouses is not None else ""
            ids = (first.id, second.id, *(spouse.id for spouse in spouses or ()))
            await _note(ctx, f"{first.name} and {second.name} were bound by a marriage{wed}.", "diplomacy.marriage_alliance", ids)
        else:
            await _note(ctx, f"{first.name} and {second.name} became allies by an oath of friendship.", "diplomacy.alliance", (first.id, second.id))
    elif (
        ally
        and value < 0
        and counters.betrayals < rules.betrayal_cap
        and rng.chance(
            rules.betrayal_chance * max(await betrayal_drive(ctx.session, ctx.rules, first.id), await betrayal_drive(ctx.session, ctx.rules, second.id))
        )
    ):
        await betray(ctx, first, second, neighbourhood, rng.chance(rules.betrayal_war_chance))
        counters.betrayals += 1


async def enemies_of(ctx: TickContext, entity_id: int) -> set[int]:
    return {
        bond.other_end(entity_id)
        for bond in await active_bonds(ctx.session, [BondKind.ENEMY], sources=[entity_id])
        + await active_bonds(ctx.session, [BondKind.ENEMY], targets=[entity_id])
    }


async def alliance_lifetimes(ctx: TickContext) -> int:
    settings = ctx.rules.diplomacy
    if settings.alliance_lifetime <= 0 or settings.alliance_end_chance <= 0:
        return 0
    ended = 0
    statement = select(BondRow).where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE, BondRow.epoch <= ctx.epoch - settings.alliance_lifetime)
    for bond in list(await ctx.session.scalars(statement.order_by(BondRow.epoch, BondRow.id))):
        if ended >= settings.alliance_end_cap:
            break
        first, second = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        if await enemies_of(ctx, first.id) & await enemies_of(ctx, second.id):
            continue
        if not ctx.rng(f"alliance_end.{bond.id}").chance(settings.alliance_end_chance):
            continue
        await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "alliance lapsed")
        ended += 1
        text = f"The {ctx.epoch - bond.epoch}-epoch alliance of {first.name} and {second.name} loosened once no common threat remained; the oath quietly ended."
        await _note(ctx, text, "diplomacy.alliance_lapsed", (first.id, second.id))
    return ended


@reads(
    "army.size",
    "cult.followers",
    "mortal.age",
    "people.population",
    "settlement.population",
    "table.armies",
    "table.body_customs",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.community_relations",
    "table.cosmos",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.maimed_cohorts",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.personality_values",
    "table.pressures",
    "table.routes",
    "table.sieges",
    "table.speaker_cohorts",
    "table.trade_route_profiles",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "army.size",
    "cult.followers",
    "people.population",
    "settlement.population",
    "table.armies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.war_sides",
    "table.wars",
)
@writes("table.memories", "table.sons")
async def diplomacy(ctx: TickContext) -> None:
    ctx.count("alliances_lapsed", await alliance_lifetimes(ctx))
    counters = DiplomacyCounters()
    candidates = ctx.rng("candidates").shuffled(await hostile_pairs(ctx.session))
    faded = await _fade_grudges(ctx, candidates)
    ctx.count("mortal_grudges_forgotten", await forget_mortal_grudges(ctx))
    await _exhaustion_peaces(ctx, candidates, faded, counters)
    communities = await canon(ctx.session, COMMUNITY_TYPES)
    neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
    sides = await SideIndex.load(ctx.session, neighbourhood)
    pair = await _pair_context(ctx)
    for index, first in enumerate(communities):
        for second in communities[index + 1 :]:
            if neighbourhood.are_neighbours(first.id, second.id):
                await _neighbour_pair(ctx, first, second, pair=pair, sides=sides, neighbourhood=neighbourhood, counters=counters)
    ctx.count("wars_declared", counters.declared)
    ctx.count("peaces", counters.peaces)
    ctx.count("exhaustion_peaces", counters.exhaustion_peaces)


async def _require_communities(ctx: TickContext, first_id: int, second_id: int) -> tuple[EntityRow, EntityRow]:
    if first_id == second_id:
        raise ValidationFailedError("Choose two different communities.")
    first, second = await living_entity(ctx.session, first_id), await living_entity(ctx.session, second_id)
    if first is None or second is None:
        raise NotFoundError("Both communities must be living records.")
    if first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Only communities make treaties.")
    return first, second


async def decree_peace(ctx: TickContext, first_id: int, second_id: int, truce: bool = True) -> bool:
    first, second = await _require_communities(ctx, first_id, second_id)
    ended = await settle_peace(ctx, first.id, second.id, WarEnding.PEACE, "peace by decree", truce=truce)
    await _note(ctx, f"By decree {first.name} and {second.name} laid down arms.", "diplomacy.peace_decree", (first.id, second.id))
    return ended


async def decree_alliance(ctx: TickContext, first_id: int, second_id: int, marriage: bool = False) -> tuple[EntityRow, EntityRow] | None:
    first, second = await _require_communities(ctx, first_id, second_id)
    bonds = BondRepository(ctx.session)
    if await bonds.exists_between(first.id, second.id, BondKind.ENEMY):
        raise ConflictError(f"{first.name} and {second.name} are enemies; make peace first.")
    if await bonds.exists_between(first.id, second.id, BondKind.ALLY):
        raise ConflictError(f"{first.name} and {second.name} are already allies.")
    neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
    sides = await SideIndex.load(ctx.session, neighbourhood)
    spouses = await form_alliance(ctx, first, second, sides, marriage)
    await _note(ctx, f"By decree {first.name} and {second.name} became allies.", "diplomacy.alliance_decree", (first.id, second.id))
    return spouses


async def decree_betrayal(ctx: TickContext, traitor_id: int, victim_id: int, war: bool = False) -> EntityRow:
    traitor, victim = await _require_communities(ctx, traitor_id, victim_id)
    if not await BondRepository(ctx.session).exists_between(traitor.id, victim.id, BondKind.ALLY):
        raise ConflictError(f"{traitor.name} and {victim.name} are not allies.")
    return await betray(ctx, traitor, victim, await Neighbourhood.load(ctx.session, ctx.rules), war)


PHASES = (Phase("expire_truces", expire_truces_phase), Phase("diplomacy", diplomacy))
