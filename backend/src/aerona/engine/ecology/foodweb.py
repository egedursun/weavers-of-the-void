from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import HUNTERS, SIZE_ORDER, Diet
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.domestication import guarded
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import shift_stat, stat

INEDIBLE = frozenset({Diet.VOID, Diet.MINERAL})
T = CreatureTrait


async def regions_of(ctx: TickContext) -> dict[int, dict[int, int]]:
    found: dict[int, dict[int, int]] = defaultdict(dict)
    for row in await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0)):
        found[row.species_entity_id][row.region_entity_id] = row.abundance
    return found


def can_take(rules_reach: int, hunter: SpeciesProfileRow, prey: SpeciesProfileRow, prey_traits: set[CreatureTrait]) -> bool:
    if hunter.diet not in HUNTERS or prey.diet in INEDIBLE or T.POISONOUS_FLESH in prey_traits:
        return False
    if hunter.diet is Diet.SOUL:
        return T.SOUL_EATER not in prey_traits
    return SIZE_ORDER.index(prey.size_class) <= SIZE_ORDER.index(hunter.size_class) + rules_reach


@dataclass
class WebChange:
    formed: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    broken: int = 0


async def wanted_prey(ctx: TickContext, species: list[EntityRow], ranges: dict[int, dict[int, int]]) -> dict[int, set[int]]:
    reach = ctx.rules.food_web.size_reach
    known = {item.id for item in species}
    profiles = {item.id: await profile_of(ctx, item) for item in species}
    marks = {item.id: await traits_of(ctx.session, item.id) for item in species}
    lands = {item.id: set(ranges.get(item.id, {})) for item in species}
    wanted: dict[int, set[int]] = {}
    for hunter in species:
        profile = profiles[hunter.id]
        found: set[int] = set()
        if profile.diet in HUNTERS and lands[hunter.id]:
            found = {
                prey.id
                for prey in species
                if prey.id != hunter.id
                and prey.world_id == hunter.world_id
                and lands[hunter.id] & lands[prey.id]
                and can_take(reach, profile, profiles[prey.id], marks[prey.id])
            }
        found -= set(profile.barred_prey)
        found |= {prey for prey in profile.pinned_prey if prey in known and prey != hunter.id}
        wanted[hunter.id] = found
    return wanted


async def derive_links(ctx: TickContext, species: list[EntityRow]) -> WebChange:
    wanted = await wanted_prey(ctx, species, await regions_of(ctx))
    change = WebChange()
    held: set[tuple[int, int]] = set()
    bonds = BondRepository(ctx.session)
    for bond in await active_bonds(ctx.session, [BondKind.HUNTS]):
        if bond.source_node_id not in wanted or bond.target_node_id not in wanted:
            continue
        if bond.target_node_id in wanted[bond.source_node_id]:
            held.add((bond.source_node_id, bond.target_node_id))
            continue
        await bonds.deactivate(bond, ctx.epoch, "their lands or appetites parted")
        change.broken += 1
    for hunter_id, prey_ids in wanted.items():
        for prey_id in sorted(prey_ids):
            if (hunter_id, prey_id) not in held:
                await bonds.connect(BondDraft(hunter_id, prey_id, BondKind.HUNTS, ctx.epoch, "predator and prey"))
                change.formed[hunter_id].append(prey_id)
    return change


def prey_mean(hunter_id: int, prey_ids: list[int], ranges: dict[int, dict[int, int]]) -> float | None:
    shared = [abundance for prey in prey_ids for region, abundance in ranges.get(prey, {}).items() if region in ranges.get(hunter_id, {})]
    return sum(shared) / len(shared) if shared else None


async def appetites(ctx: TickContext, species: list[EntityRow], *, adjust: bool) -> dict[int, float]:
    table = ctx.rules.food_web
    ranges = await regions_of(ctx)
    prey_of: dict[int, list[int]] = defaultdict(list)
    for bond in await active_bonds(ctx.session, [BondKind.HUNTS]):
        prey_of[bond.source_node_id].append(bond.target_node_id)
    hunger: dict[int, float] = {}
    for item in species:
        profile = await profile_of(ctx, item)
        if profile.diet not in HUNTERS or (adjust and "aggression" in profile.locked):
            continue
        mean = prey_mean(item.id, prey_of.get(item.id, []), ranges)
        threshold = ctx.rules.ecology.hunger_threshold
        hungry = mean is None or mean < threshold
        hunger[item.id] = 1 + (threshold - (mean or 0)) / max(1, threshold) if hungry else 1.0
        if adjust:
            profile.aggression = clamp_int(profile.aggression + (table.hunger_aggression if hungry else -table.calm_aggression), 0, PERCENT)
    return hunger


async def raid_herds(ctx: TickContext, raider: EntityRow, settlement: EntityRow) -> int:
    table = ctx.rules.food_web
    traits = await traits_of(ctx.session, raider.id)
    want = round_half_up(table.raid_livestock * (1 + table.ambush_pct / PERCENT if T.AMBUSH_PREDATOR in traits else 1) * await guarded(ctx, settlement.id))
    taken = await GoodsLedger(ctx.session, ctx.epoch).take_units(settlement.id, CommodityKind.LIVESTOCK, want, GoodsFlow.LOSS)
    if traits & {T.FIRE_BREATHING, T.COLD_BREATHING} and stat(settlement, "prosperity") is not None:
        shift_stat(settlement, "prosperity", -table.breath_prosperity)
    return taken


async def raid_chance(ctx: TickContext, monster: EntityRow, hunger: dict[int, float]) -> float:
    profile = await ctx.session.get(SpeciesProfileRow, monster.id)
    aggression = profile.aggression if profile is not None else stat(monster, "danger") or 0
    bold = 1 - profile.fear_of_people / PERCENT * ctx.rules.food_web.fear_pct / PERCENT if profile is not None else 1.0
    return aggression * hunger.get(monster.id, 1.0) * bold / ctx.rules.world_engine.raid_danger_divisor
