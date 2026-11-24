from dataclasses import dataclass, field

from sqlalchemy import and_, or_, select

from aerona.catalog.life_traits import TREATY_KIND_TRAITS, having
from aerona.catalog.pacts import STANDINGS
from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.life_traits import TreatyKindTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind, LawKind, PartyRole, RegionalStanding, TreatyBreach, TreatyKind, TreatyStatus
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.storyteller import RecoveryKind
from aerona.domain.enums.unions import UnionPurpose
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.engine.body.cohorts import war_appetite
from aerona.engine.context import TickContext
from aerona.engine.economy.routes import blockade_pressure
from aerona.engine.folkways.biases import lean_community
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.intrigue.beliefs import daring
from aerona.engine.mind.drives import betrayal_drive, closeness, war_drive
from aerona.engine.mortal.kinship import marry
from aerona.engine.phase import Phase
from aerona.engine.phases.afterlife import cosmic_court
from aerona.engine.polity.accords import Clause, end_treaty, sign, treaty_between
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.queries import BondIndex, active_bonds, canon, count_communities, living_entity
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.recording.record import FactInput, StepDraft, record
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
    diplomacy_cap,
    expire_truces,
    hostile_pair_count,
    hostile_pairs,
    ongoing_war_count,
    ongoing_wars,
)
from aerona.engine.services.war_geography import Neighbourhood
from aerona.engine.services.war_resolution import end_war, settle_peace
from aerona.engine.storyteller.pace import recovered
from aerona.rules.registry import Rules

MARRIAGE_AGE_FALLBACK_KEY = "age"
HOSTILITY_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
ALLIANCES = having(TREATY_KIND_TRAITS, TreatyKindTrait.ALLIANCES)


@dataclass
class DiplomacyCounters:
    declared: int = 0
    peaces: int = 0
    alliances: int = 0
    betrayals: int = 0
    exhaustion_peaces: int = 0
    communities: int = 0

    def cap(self, rules: Rules, base: int) -> int:
        return diplomacy_cap(rules, base, self.communities)


@reads("table.bonds")
@writes("table.bonds")
async def expire_truces_phase(ctx: TickContext) -> None:
    ctx.count("truces_expired", await expire_truces(ctx.session, ctx.rules, ctx.epoch))


async def told(ctx: TickContext, key: str, pair: tuple[int, int], *, place: int | None = None, **facts: FactInput) -> None:
    first = await living_entity(ctx.session, pair[0])
    await record(ctx, key, roles={IncidentRole.SUBJECT: list(pair)}, facts=facts, place=place if place is not None else first.location_id if first else None)


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


def grudge_limits(all_rules: Rules, pairs: int, communities: int) -> tuple[int, int]:
    rules = all_rules.diplomacy
    pool = max(1, round(diplomacy_cap(all_rules, rules.world_war_cap, communities) * rules.grudge_pool_pct / PERCENT))
    excess = max(0, pairs - pool)
    fade_cap = diplomacy_cap(all_rules, rules.grudge_fade_cap, communities) + round(excess * rules.grudge_overflow_share_pct / PERCENT)
    forget_age = 0
    if rules.grudge_forget_epochs > 0:
        forget_age = max(rules.grudge_fade_min_age, round(rules.grudge_forget_epochs * min(1, pool / max(1, pairs))))
    return fade_cap, forget_age


async def _fade_grudges(ctx: TickContext, candidates: list[tuple[int, int, int]], communities: int) -> set[frozenset[int]]:
    rules = ctx.rules.diplomacy
    fade_cap, forget_age = grudge_limits(ctx.rules, await hostile_pair_count(ctx.session), communities)
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
            await told(ctx, "diplomacy.grudge_faded", (first_id, second_id), epochs=age, relation=await relation(ctx.session, ctx.rules, first_id, second_id))
        else:
            await told(ctx, "diplomacy.grudge_forgotten", (first_id, second_id), epochs=age)
    ctx.count("grudges_faded", len(faded))
    return faded


async def _exhaustion_peaces(ctx: TickContext, candidates: list[tuple[int, int, int]], faded: set[frozenset[int]], counters: DiplomacyCounters) -> None:
    rules = ctx.rules.diplomacy
    rng = ctx.rng("exhaustion")
    for first_id, second_id, _ in candidates:
        if counters.exhaustion_peaces >= counters.cap(ctx.rules, rules.exhaustion_peace_cap):
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
        await told(
            ctx,
            "diplomacy.exhaustion_peace",
            (first_id, second_id),
            war=war.event_entity_id,
            epochs=duration,
            chance=min(rules.exhaustion_cap_pct, rules.exhaustion_growth_pct * duration),
        )


async def form_alliance(ctx: TickContext, first: EntityRow, second: EntityRow, sides: SideIndex, marriage: bool) -> tuple[EntityRow, EntityRow] | None:
    rules = ctx.rules.diplomacy
    spouses: tuple[EntityRow, EntityRow] | None = None
    if marriage:
        first_heir = next(iter(_marriageable(ctx, sides, first.id)), None)
        second_heir = next(iter(_marriageable(ctx, sides, second.id)), None)
        if first_heir is not None and second_heir is not None:
            spouses = (first_heir, second_heir)
    clauses = [Clause(ClauseKind.CALL_TO_ARMS, first.id, second.id), Clause(ClauseKind.CALL_TO_ARMS, second.id, first.id)]
    if spouses is not None:
        clauses.append(Clause(ClauseKind.MARRIAGE, first.id, second.id, {"first_id": spouses[0].id, "second_id": spouses[1].id}))
    treaty = await sign(
        ctx,
        TreatyKind.MARRIAGE_PACT if marriage else TreatyKind.ALLIANCE_DEFENSIVE,
        [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)],
        clauses=clauses,
        until=ctx.epoch + (ctx.rules.treaties.marriage_treaty_epochs if marriage else ctx.rules.treaties.alliance_epochs),
    )
    if marriage and spouses is not None:
        await marry(ctx.session, spouses[0], spouses[1], ctx.epoch, purpose=UnionPurpose.ALLIANCE, treaty_id=treaty.id, description="marriage alliance")
    if marriage:
        await change_relation(ctx, first.id, second.id, rules.marriage_relation, MemoryKind.MARRIED_INTO, note="marriage")
    ctx.count("alliances")
    return spouses


def _marriageable(ctx: TickContext, sides: SideIndex, community_id: int) -> list[EntityRow]:
    rules = ctx.rules.diplomacy
    return [hero for hero in sides.heroes_of(community_id) if (stat_or(hero, MARRIAGE_AGE_FALLBACK_KEY, rules.default_hero_age)) >= rules.marriage_min_age]


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
        enemy_id = item.foe_id
        enemy = await living_entity(ctx.session, enemy_id)
        if enemy is None or enemy.id == traitor.id or not rng.chance(ctx.rules.diplomacy.betrayal_war_collapse_chance):
            continue
        event = await living_entity(ctx.session, item.war.event_entity_id)
        await end_war(ctx, item.war, WarEnding.BETRAYAL, victor_id=enemy.id, loser_id=item.own_id or victim.id, reason="betrayal", apply_relation=False)
        await record(
            ctx,
            "diplomacy.betrayal_war_lost",
            roles={IncidentRole.ACTOR: traitor.id, IncidentRole.VICTIM: victim.id, IncidentRole.OPPONENT: enemy.id},
            facts={"war": event.id if event is not None else None, "chance": ctx.rules.diplomacy.betrayal_war_collapse_chance},
            place=victim.location_id,
        )
        collapsed += 1
    ctx.count("wars_lost_to_betrayal", collapsed)
    return collapsed


async def betray(ctx: TickContext, first: EntityRow, second: EntityRow, neighbourhood: Neighbourhood, war_roll: bool) -> EntityRow:
    rules = ctx.rules.diplomacy
    traitor, victim = (first, second) if _weight(ctx, first) >= _weight(ctx, second) else (second, first)
    pact = await treaty_between(ctx.session, first.id, second.id, list(ALLIANCES))
    if pact is not None:
        await breach(ctx, pact, traitor.id, clause=None, reason=TreatyBreach.ALLY_BETRAYED)
    await BondRepository(ctx.session).close_between(first.id, second.id, [BondKind.ALLY], ctx.epoch, "betrayal")
    await change_relation(ctx, victim.id, traitor.id, -rules.betrayal_relation, MemoryKind.BETRAYED_ME, note="betrayal", reverse=MemoryKind.ILL_WILL)
    await abandon_mid_war(ctx, traitor, victim)
    if war_roll:
        await declare_war(ctx, traitor.id, victim.id, "betrayal", cause=WarCause.BETRAYAL)
    await record(
        ctx,
        "diplomacy.betrayal_war" if war_roll else "diplomacy.betrayal",
        roles={IncidentRole.ACTOR: traitor.id, IncidentRole.VICTIM: victim.id},
        facts={"relation_lost": rules.betrayal_relation, "treaty": pact.treaty_entity_id if pact is not None else None},
        place=traitor.location_id,
        steps=(StepDraft(StepAction.BETRAY, actor=traitor.id, target=victim.id, amount=rules.betrayal_relation, unit=FactUnit.STANDING),),
    )
    await cosmic_court(ctx, traitor.id, victim.id)
    ctx.count("betrayals")
    return traitor


@dataclass(frozen=True)
class PairContext:
    bonds: BondIndex
    feuds: set[tuple[int, int]]
    standing: dict[int, RegionalStanding] = field(default_factory=dict)
    weights: dict[RegionalStanding, int] = field(default_factory=dict)
    balance_pct: int = PERCENT

    def war_weight(self, first: int, second: int) -> float:
        return max(self.weights.get(self.standing.get(item, RegionalStanding.MINOR_POWER), PERCENT) for item in (first, second)) / PERCENT

    def alliance_weight(self, first: int, second: int) -> float:
        if any(not STANDINGS[self.standing.get(item, RegionalStanding.MINOR_POWER)].allies for item in (first, second)):
            return 0.0
        threatened = any(self.standing.get(item) is RegionalStanding.HEGEMON for item in self.standing if item not in (first, second))
        return self.balance_pct / PERCENT if threatened else 1.0


async def _pair_context(ctx: TickContext, book: RealmBook | None = None) -> PairContext:
    bonds = await BondIndex.load(ctx.session, [BondKind.TRADES_WITH, BondKind.ALLY, BondKind.ENEMY, BondKind.PAYS_TRIBUTE])
    table = ctx.rules.treaties
    standing = (
        {realm.profile.core_entity_id: realm.profile.standing for realm in book.realms.values() if realm.profile.core_entity_id is not None}
        if book is not None
        else {}
    )
    weights = {standing: spec.war_pct(ctx.rules) for standing, spec in STANDINGS.items()}
    return PairContext(bonds, await blood_feud_pairs(ctx.session), standing, weights, table.balance_alliance_pct)


def realm_actors(communities: list[EntityRow], book: RealmBook) -> tuple[list[EntityRow], dict[int, list[int]]]:
    actors: list[EntityRow] = []
    lands: dict[int, list[int]] = {}
    for community in communities:
        realm = book.realm_of(community.id)
        core = realm.profile.core_entity_id if realm is not None else None
        if realm is not None and core is not None and core != community.id and core in {item.id for item in communities}:
            continue
        actors.append(community)
        lands[community.id] = sorted(realm.members) if realm is not None and core == community.id else [community.id]
    return actors, lands


async def settled_by_wergild(ctx: TickContext, first: EntityRow, second: EntityRow) -> bool:
    if not ctx.rng(f"wergild.{first.id}.{second.id}.{ctx.epoch}").chance(ctx.rules.vendetta.wergild_chance):
        return False
    if not await law_param(ctx.session, first.id, LawKind.BLOOD_FEUD, "wergild_allowed"):
        return False
    await change_relation(ctx, first.id, second.id, ctx.rules.treaties.wergild_value // 3, MemoryKind.GIFTED_ME, note="blood money paid")
    await told(ctx, "diplomacy.wergild", (first.id, second.id), relation_gained=ctx.rules.treaties.wergild_value // 3)
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
        and counters.declared < counters.cap(ctx.rules, rules.declarations_cap)
        and await ongoing_war_count(ctx.session, first.id) < cap
        and await ongoing_war_count(ctx.session, second.id) < cap
        and rng.chance(
            rules.war_declaration_chance
            * pair.war_weight(first.id, second.id)
            * min(await war_appetite(ctx, first), await war_appetite(ctx, second))
            * max(await war_drive(ctx.session, ctx.rules, first.id), await war_drive(ctx.session, ctx.rules, second.id))
            * await daring(ctx, first.id, second.id)
        )
        and await declare_war(
            ctx, first.id, second.id, "blood feud turned to war" if feud else "accumulated grudge", cause=WarCause.VENDETTA if feud else WarCause.GRUDGE
        )
    ):
        counters.declared += 1
        await told(ctx, "diplomacy.feud_war_declared" if feud else "diplomacy.war_declared", (first.id, second.id), relation=value)
    elif (
        enemy
        and (
            (
                value >= rules.peace_threshold
                and rng.chance(
                    await recovered(ctx, first.world_id, RecoveryKind.PEACE_ENVOY, rules.peace_chance) + await blockade_pressure(ctx, first.id, second.id)
                )
            )
            or tired
        )
        and counters.peaces < counters.cap(ctx.rules, rules.peace_cap)
    ):
        await settle_peace(ctx, first.id, second.id, WarEnding.PEACE, "peace")
        counters.peaces += 1
        if tired:
            await told(ctx, "diplomacy.peace_exhausted", (first.id, second.id), epochs=duration, relation=value)
        else:
            await told(ctx, "diplomacy.peace", (first.id, second.id), relation=value)
    elif (
        not enemy
        and not ally
        and value >= rules.alliance_threshold
        and counters.alliances < counters.cap(ctx.rules, rules.alliance_cap)
        and rng.chance(
            min(PERCENT, rules.alliance_chance * pair.alliance_weight(first.id, second.id) * await lean_community(ctx, first.id, BiasedDecision.ALLIANCE))
        )
    ):
        marriage = (
            bool(_marriageable(ctx, sides, first.id))
            and bool(_marriageable(ctx, sides, second.id))
            and rng.chance(rules.marriage_alliance_share_pct * await closeness(ctx.session, first.id, second.id))
        )
        spouses = await form_alliance(ctx, first, second, sides, marriage)
        counters.alliances += 1
        if marriage:
            await record(
                ctx,
                "diplomacy.marriage_alliance" if spouses is not None else "diplomacy.marriage_pact",
                roles={IncidentRole.SUBJECT: [first.id, second.id], IncidentRole.SPOUSE: [spouse.id for spouse in spouses or ()]},
                facts={"relation": value},
                place=first.location_id,
            )
        else:
            await told(ctx, "diplomacy.alliance", (first.id, second.id), relation=value)
    elif (
        ally
        and value < 0
        and counters.betrayals < counters.cap(ctx.rules, rules.betrayal_cap)
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


async def alliance_lifetimes(ctx: TickContext, communities: int) -> int:
    settings = ctx.rules.diplomacy
    if settings.alliance_lifetime <= 0 or settings.alliance_end_chance <= 0:
        return 0
    ended = 0
    limit = diplomacy_cap(ctx.rules, settings.alliance_end_cap, communities)
    statement = select(BondRow).where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE, BondRow.epoch <= ctx.epoch - settings.alliance_lifetime)
    for bond in ctx.rng("alliance_end").shuffled(list(await ctx.session.scalars(statement.order_by(BondRow.epoch, BondRow.id)))):
        if ended >= limit:
            break
        if held(bond.source_node_id, bond.target_node_id):
            continue
        first, second = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        if await enemies_of(ctx, first.id) & await enemies_of(ctx, second.id):
            continue
        if not ctx.rng(f"alliance_end.{bond.id}").chance(settings.alliance_end_chance):
            continue
        pact = await treaty_between(ctx.session, first.id, second.id, list(ALLIANCES))
        if pact is not None:
            await end_treaty(ctx, pact, TreatyStatus.EXPIRED, "no common threat remained")
        await BondRepository(ctx.session).deactivate(bond, ctx.epoch, "alliance lapsed")
        ended += 1
        await told(ctx, "diplomacy.alliance_lapsed", (first.id, second.id), epochs=ctx.epoch - bond.epoch, chance=settings.alliance_end_chance)
    return ended


@reads(
    "army.size",
    "cult.followers",
    "cult.zeal",
    "mortal.age",
    "people.population",
    "settlement.population",
    "table.armies",
    "table.army_units",
    "table.bias_weights",
    "table.body_customs",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.community_relations",
    "table.cosmos",
    "table.creator",
    "table.creator_taboos",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.feeling_spread",
    "table.feuds",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.held_identities",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.language_registers",
    "table.maimed_cohorts",
    "table.marriages",
    "table.memories",
    "table.mind_profiles",
    "table.minds",
    "table.museum_collections",
    "table.museum_pieces",
    "table.name_registry",
    "table.network_nodes",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.pressures",
    "table.professions_of_value",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.routes",
    "table.ruler_currencies",
    "table.sieges",
    "table.skills",
    "table.sons",
    "table.speaker_cohorts",
    "table.spy_networks",
    "table.stars",
    "table.storytellers",
    "table.trade_route_profiles",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vassalages",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "army.size",
    "cult.followers",
    "cult.zeal",
    "people.population",
    "settlement.population",
    "table.armies",
    "table.army_units",
    "table.bias_weights",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.marriages",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.oaths",
    "table.peace_terms",
    "table.polity_regard",
    "table.professions_of_value",
    "table.reputations",
    "table.sons",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.war_sides",
    "table.wars",
)
async def diplomacy(ctx: TickContext) -> None:
    counters = DiplomacyCounters(communities=await count_communities(ctx.session))
    ctx.count("alliances_lapsed", await alliance_lifetimes(ctx, counters.communities))
    candidates = [pair for pair in ctx.rng("candidates").shuffled(await hostile_pairs(ctx.session)) if not held(pair[0], pair[1])]
    faded = await _fade_grudges(ctx, candidates, counters.communities)
    ctx.count("mortal_grudges_forgotten", await forget_mortal_grudges(ctx))
    await _exhaustion_peaces(ctx, candidates, faded, counters)
    communities = unheld(await canon(ctx.session, COMMUNITY_TYPES))
    neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
    sides = await SideIndex.load(ctx.session, neighbourhood)
    book = await RealmBook.load(ctx.session)
    pair = await _pair_context(ctx, book)
    actors, lands = realm_actors(communities, book)
    actors = ctx.rng("actors").shuffled(actors)
    for index, first in enumerate(actors):
        for second in actors[index + 1 :]:
            if any(neighbourhood.are_neighbours(one, two) for one in lands[first.id] for two in lands[second.id]):
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
    await told(ctx, "diplomacy.peace_decree", (first.id, second.id))
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
    await told(ctx, "diplomacy.alliance_decree", (first.id, second.id), pact=TreatyKind.MARRIAGE_PACT if marriage else TreatyKind.ALLIANCE_DEFENSIVE)
    return spouses


async def decree_betrayal(ctx: TickContext, traitor_id: int, victim_id: int, war: bool = False) -> EntityRow:
    traitor, victim = await _require_communities(ctx, traitor_id, victim_id)
    if not await BondRepository(ctx.session).exists_between(traitor.id, victim.id, BondKind.ALLY):
        raise ConflictError(f"{traitor.name} and {victim.name} are not allies.")
    return await betray(ctx, traitor, victim, await Neighbourhood.load(ctx.session, ctx.rules), war)


PHASES = (Phase("expire_truces", expire_truces_phase), Phase("diplomacy", diplomacy))
