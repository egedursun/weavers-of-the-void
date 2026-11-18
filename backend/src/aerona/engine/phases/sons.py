from itertools import combinations

from aerona.catalog.rarities import build_rarity_table
from aerona.catalog.stats import EXISTENCE_BAND_LABELS, existence_band, max_essence, max_hp
from aerona.constants.schema import SINGLETON_ID
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.son import ExistenceBand, PowerEffect, SonStatus
from aerona.domain.enums.structure import STANDING_STATES
from aerona.engine.context import TickContext
from aerona.engine.divine.decrees import council_chained
from aerona.engine.divine.standing import mean_neglect
from aerona.engine.dominion.book import DominionBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.loops.delay import lagged
from aerona.engine.phase import Phase
from aerona.engine.primitives.faith import has_unlocked_power, son_faith, worshipper_count
from aerona.engine.primitives.ledger import LedgerKey, record
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, entity, living_entity, living_sons
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record as record_incident
from aerona.rules.registry import Rules

ANCHOR_ALIVE_STATUSES = frozenset({EntityStatus.CANON, EntityStatus.FULFILLED})
REMEMBERING_TYPES = frozenset({EntityType.ARTWORK, EntityType.LEGEND})


def existence_target(rules: Rules, faith: int, fame: int, anchor_alive: bool, worshippers: int) -> int:
    core = rules.core_rules
    value = (
        core.existence_base
        + min(core.existence_faith_cap, faith / core.existence_faith_divisor)
        + min(core.existence_renown_cap, fame / core.existence_renown_divisor)
        + (core.existence_anchor_bonus if anchor_alive else -core.existence_anchorless_penalty)
        - (0 if worshippers else core.existence_no_worshipper_penalty)
    )
    return clamp_int(value, 0, PERCENT)


def step_toward(current: int, target: int, step: int) -> int:
    if target > current:
        return min(target, current + step)
    return max(target, current - step)


async def epoch_star(ctx: TickContext, son: SonRow) -> EntityRow | None:
    cosmos = await ctx.session.get(CosmosRow, SINGLETON_ID)
    world_ids = [son.current_world_id, cosmos.primary_world_id if cosmos is not None else None]
    for world_id in world_ids:
        world = await ctx.session.get(WorldRow, world_id) if world_id is not None else None
        star = await entity(ctx.session, world.epoch_star_entity_id) if world is not None else None
        if star is not None and star.domain is not None:
            return star
    return None


def star_bonus(rules: Rules, star: EntityRow) -> int:
    transition = rules.world_epoch_transition
    influence = stat(star, "influence")
    weight = transition.star_influence_pivot if influence is None else influence
    return round_half_up(transition.star_domain_essence_bonus * weight / transition.star_influence_pivot)


async def wake_or_heal(ctx: TickContext, son: SonRow) -> None:
    transition = ctx.rules.world_epoch_transition
    ceiling = max_hp(ctx.rules, son.endurance)
    if son.status is SonStatus.ASLEEP:
        son.sleep_epochs_left = max(0, son.sleep_epochs_left - 1)
        if son.sleep_epochs_left == 0:
            son.status = SonStatus.ACTIVE
            son.hp = round_half_up(ceiling / transition.wake_hp_divisor)
            await record_incident(ctx, "sons.woke", roles={IncidentRole.ACTOR: son.id}, kind=ChronicleKind.SYSTEM, son_id=son.id)
        return
    son.hp = min(ceiling, son.hp + transition.heal_base + round_half_up(son.endurance / transition.heal_endurance_divisor))


async def renew_existence(ctx: TickContext, son: SonRow, faith: int) -> ExistenceBand:
    rules = ctx.rules
    anchor = await entity(ctx.session, son.anchor_entity_id)
    anchor_alive = anchor is None or anchor.status in ANCHOR_ALIVE_STATUSES
    target = existence_target(rules, faith, son.fame, anchor_alive, await worshipper_count(ctx.session, son.id))
    neglect = await lagged(ctx, BalanceLoop.GOD_NEGLECT, son.id, await mean_neglect(ctx, son.id))
    target = clamp_int(target - neglect * rules.divine_standing.neglect_existence_pct / PERCENT, 0, PERCENT)
    ruled = len((await DominionBook.load(ctx.session)).ruled_regions(rules, son.id))
    target = clamp_int(target + min(rules.dominion.existence_cap, ruled * rules.dominion.existence_per_region), 0, PERCENT)
    before = existence_band(rules, son.existence)
    son.existence = step_toward(son.existence, target, rules.world_epoch_transition.existence_step)
    after = existence_band(rules, son.existence)
    if after is not before:
        tail = " Because their anchor perished, they began to fade." if not anchor_alive else ""
        await record_incident(
            ctx,
            "sons.existence",
            roles={IncidentRole.SUBJECT: son.id},
            facts={"band": after, "band_label": EXISTENCE_BAND_LABELS[after].lower(), "existence": son.existence, "tail": tail},
            kind=ChronicleKind.EXISTENCE,
            son_id=son.id,
        )
    return after


async def regenerate_essence(ctx: TickContext, son: SonRow, faith: int, band: ExistenceBand) -> None:
    rules = ctx.rules
    transition = rules.world_epoch_transition
    faith_income = faith // transition.faith_essence_divisor
    cap_pct = rules.faith.essence_income_cap_pct
    if cap_pct > 0:
        faith_income = min(faith_income, max_essence(rules, son.might) * cap_pct // PERCENT)
    regen = build_rarity_table(rules)[son.rarity].essence_regen + faith_income
    if await has_unlocked_power(ctx.session, rules, son, PowerEffect.ESSENCE_SPRING):
        regen += transition.essence_spring_bonus
    if band is ExistenceBand.RADIANT:
        regen += transition.radiant_essence_bonus
    star = await epoch_star(ctx, son)
    if star is not None and star.domain in son.domains:
        regen += star_bonus(rules, star)
    if son.status is SonStatus.EXILED:
        regen = regen * rules.essence.exile_regen_pct // PERCENT
    son.essence = min(max_essence(rules, son.might), son.essence + regen)


@reads(
    "celestial.influence",
    "cult.followers",
    "cult.influence",
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.bonds",
    "table.cosmos",
    "table.council_rulings",
    "table.divine_standing",
    "table.divine_wounds",
    "table.dominions",
    "table.entities",
    "table.god_designs",
    "table.god_scales",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.region_dominion",
    "table.reverences",
    "table.son_powers",
    "table.sons",
)
@writes("table.chronicle", "table.incident_facts", "table.incident_participants", "table.incidents", "table.sons")
async def sons_renewal(ctx: TickContext) -> None:
    total = 0
    for son in await living_sons(ctx.session):
        son.chained = await council_chained(ctx, son.id)
        await wake_or_heal(ctx, son)
        faith = await son_faith(ctx.session, ctx.rules, son)
        son.faith = faith
        total += faith
        son.fame = son.fame * ctx.rules.essence.renown_keep_pct // PERCENT
        band = await renew_existence(ctx, son, faith)
        await regenerate_essence(ctx, son, faith, band)
    record(ctx, LedgerKey.TOTAL_FAITH, total)


@reads("table.bonds", "table.nodes", "table.sons", "table.structure_profiles")
@writes("table.sons")
async def works_remember_gods(ctx: TickContext) -> None:
    transition = ctx.rules.world_epoch_transition
    for son in await living_sons(ctx.session):
        for bond in await active_bonds(ctx.session, [BondKind.TELLS_OF], targets=[son.id]):
            work = await living_entity(ctx.session, bond.source_node_id)
            if work is None or work.entity_type not in REMEMBERING_TYPES:
                continue
            son.fame += transition.artwork_renown
            son.existence = min(PERCENT, son.existence + transition.artwork_existence)
        for bond in await active_bonds(ctx.session, [BondKind.WORSHIPS], targets=[son.id]):
            work = await living_entity(ctx.session, bond.source_node_id)
            if work is None or work.entity_type is not EntityType.STRUCTURE:
                continue
            profile = await ctx.session.get(StructureProfileRow, work.id)
            share = (
                profile.effect_pct / PERCENT if profile is not None and profile.construction_state in STANDING_STATES else 0.0 if profile is not None else 1.0
            )
            son.fame += round(transition.dedicated_work_renown * share)
            son.existence = min(PERCENT, son.existence + round(transition.dedicated_work_existence * share))


@reads("table.nodes", "table.son_relations", "table.sons")
@writes("table.son_relations")
async def domain_rivalry(ctx: TickContext) -> None:
    transition = ctx.rules.world_epoch_transition
    repository = SonRepository(ctx.session)
    for first, second in combinations(await living_sons(ctx.session), 2):
        shared = len(set(first.domains) & set(second.domains))
        if not shared:
            continue
        relation = await repository.relation(first.id, second.id)
        if relation > -transition.domain_rivalry_floor:
            await repository.change_relation(first.id, second.id, -min(transition.domain_rivalry * shared, relation + transition.domain_rivalry_floor))


@reads("table.nodes", "table.sons")
@writes("table.chronicle", "table.incident_participants", "table.incidents", "table.sons")
async def rebel_theft(ctx: TickContext) -> None:
    transition = ctx.rules.world_epoch_transition
    stolen = 0
    for son in await living_sons(ctx.session):
        if not son.rebel or son.status is not SonStatus.ACTIVE:
            continue
        amount = transition.rebel_steal_base + son.level * transition.rebel_steal_per_level
        son.essence += amount
        stolen += amount
        await record_incident(
            ctx, "sons.rebel_theft", roles={IncidentRole.ACTOR: son.id}, facts={"amount": amount}, kind=ChronicleKind.REBELLION, son_id=son.id
        )
    record(ctx, LedgerKey.STOLEN_ESSENCE, stolen)


async def set_son_relation(ctx: TickContext, first_id: int, second_id: int, value: int) -> int:
    if first_id == second_id:
        raise ValidationFailedError("A son has no relation with themselves.")
    if not RELATION_MIN <= value <= RELATION_MAX:
        raise ValidationFailedError(f"A relation lies between {RELATION_MIN} and {RELATION_MAX}.")
    repository = SonRepository(ctx.session)
    current = await repository.relation(first_id, second_id)
    return await repository.change_relation(first_id, second_id, value - current, "set by the Creator")


RENEWAL_PHASES = (Phase("sons_renewal", sons_renewal),)
REMEMBRANCE_PHASES = (Phase("works_remember_gods", works_remember_gods),)
RIVALRY_PHASES = (Phase("domain_rivalry", domain_rivalry),)
REBEL_PHASES = (Phase("rebel_theft", rebel_theft),)
PHASES = RENEWAL_PHASES + REMEMBRANCE_PHASES + RIVALRY_PHASES + REBEL_PHASES
