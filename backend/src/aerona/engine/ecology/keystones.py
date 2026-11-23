from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import PLANT_EATERS, keystone_of
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import EcosystemServiceRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.evolution import KeystoneRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.environment.book import add_scar
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.rules.registry import Rules

Services = dict[KeystoneRole, int]


@dataclass
class KeystoneTally:
    assigned: int = 0
    services: int = 0
    lost: int = 0


async def services_by_region(session: AsyncSession) -> dict[int, Services]:
    found: dict[int, Services] = defaultdict(dict)
    for row in await session.scalars(select(EcosystemServiceRow)):
        found[row.region_entity_id][row.role] = row.strength
    return found


def pollination(rules: Rules, services: Services | None) -> float:
    if services is None or KeystoneRole.POLLINATOR not in services:
        return 1.0
    strength = services[KeystoneRole.POLLINATOR]
    if strength <= 0:
        return 1 - rules.keystones.lost_decay / PERCENT
    return 1 + rules.keystones.harvest_gain * strength / PERCENT / PERCENT


def dammed(rules: Rules, services: Services | None) -> int:
    return round_half_up(rules.keystones.wetland_gain * (services or {}).get(KeystoneRole.DAM_BUILDER, 0) / PERCENT)


def scavenged(rules: Rules, services: Services | None) -> int:
    return round_half_up(rules.keystones.disease_relief * (services or {}).get(KeystoneRole.SCAVENGER, 0) / PERCENT)


def dispersal(rules: Rules, services: Services | None) -> float:
    if services is None or KeystoneRole.SEED_DISPERSER not in services:
        return 1.0
    return 1.0 if services[KeystoneRole.SEED_DISPERSER] > 0 else 1 - rules.keystones.disperser_succession_pct / PERCENT


def reef_shield(rules: Rules, services: Services | None) -> float:
    return 1 - rules.keystones.reef_wave_cut_pct * (services or {}).get(KeystoneRole.REEF_BUILDER, 0) / PERCENT / PERCENT


def serve_land(rules: Rules, env: RegionEnvironmentRow, services: Services | None) -> None:
    if "wetland" not in env.locked:
        env.wetland = clamp_int(env.wetland + dammed(rules, services), 0, PERCENT)
    if "disease_load" not in env.locked:
        env.disease_load = clamp_int(env.disease_load - scavenged(rules, services), 0, PERCENT)


async def assign_roles(ctx: TickContext) -> int:
    assigned = 0
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        profile = await ctx.session.get(SpeciesProfileRow, species.id)
        if profile is None or profile.keystone is not None or "keystone" in profile.locked or held(species.id):
            continue
        role = keystone_of(profile.body_plan, profile.diet, profile.size_class, await traits_of(ctx.session, species.id))
        if role is not None:
            profile.keystone = role
            assigned += 1
    return assigned


async def strongest(ctx: TickContext) -> dict[tuple[int, KeystoneRole], tuple[int, int]]:
    roles = {
        row.species_entity_id: row.keystone
        for row in await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.keystone.is_not(None)))
        if row.keystone is not None
    }
    best: dict[tuple[int, KeystoneRole], tuple[int, int]] = {}
    for row in await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0).order_by(SpeciesRangeRow.species_entity_id)):
        role = roles.get(row.species_entity_id)
        if role is None:
            continue
        key = (row.region_entity_id, role)
        if key not in best or row.abundance > best[key][0]:
            best[key] = (row.abundance, row.species_entity_id)
    return best


async def unchecked_grazers(ctx: TickContext, region_id: int) -> None:
    rise = ctx.rules.keystones.regulator_grazer_rise_pct
    grazers = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.diet.in_(sorted(PLANT_EATERS)))
    rows = await ctx.session.scalars(
        select(SpeciesRangeRow)
        .where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.species_entity_id.in_(grazers), SpeciesRangeRow.abundance > 0)
        .order_by(SpeciesRangeRow.species_entity_id)
    )
    land = await ctx.session.get(RegionEnvironmentRow, region_id)
    for row in list(rows):
        if held(row.species_entity_id) or "abundance" in (row.locked or []):
            continue
        row.abundance = clamp_int(row.abundance + round_half_up(row.abundance * rise / PERCENT / 10), 0, PERCENT)
        if land is not None and row.abundance >= PERCENT * 3 // 4:
            add_scar(land, ScarKind.OVERGRAZED, rise // 10)


async def hold_reef_fish(ctx: TickContext, region_id: int, strength: int) -> None:
    share = ctx.rules.keystones.reef_fish_pct
    for ground in await ctx.session.scalars(
        select(CatchGroundRow).where(CatchGroundRow.region_entity_id == region_id).order_by(CatchGroundRow.source_entity_id)
    ):
        if "stock" in (ground.locked or []) or held(ground.source_entity_id):
            continue
        floor = round_half_up(ground.first_stock * share / PERCENT * strength / PERCENT)
        if strength <= 0:
            ground.stock = max(0, ground.stock - share // 10)
        elif ground.stock < floor:
            ground.stock = floor


async def keep_services(ctx: TickContext, tally: KeystoneTally) -> None:
    table = ctx.rules.keystones
    tally.assigned = await assign_roles(ctx)
    await ctx.session.flush()
    best = await strongest(ctx)
    stored = {(row.region_entity_id, row.role): row for row in await ctx.session.scalars(select(EcosystemServiceRow))}
    for key in sorted(set(best) | set(stored), key=lambda item: (item[0], item[1].value)):
        region_id, role = key
        if held(region_id):
            continue
        strength, species_id = best.get(key, (0, None))
        row = stored.get(key)
        if row is None:
            row = EcosystemServiceRow(region_entity_id=region_id, role=role, species_entity_id=species_id, strength=strength, epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
        elif "strength" in row.locked:
            strength = row.strength
        elif row.strength > 0 and strength <= 0:
            tally.lost += 1
            await record(
                ctx,
                "ecology.keystone_lost",
                roles={IncidentRole.PLACE: region_id, IncidentRole.SUBJECT: row.species_entity_id},
                facts={"role": role, "strength": row.strength},
                place=region_id,
            )
        if "strength" not in row.locked:
            with explaining_alone():
                term("keystone.strongest_species", strength, source_node_id=species_id)
                row.strength = strength
        if "species_entity_id" not in row.locked:
            row.species_entity_id = species_id
        row.epoch = ctx.epoch
        tally.services += int(strength > 0)
        if role is KeystoneRole.REGULATOR and strength <= 0:
            await unchecked_grazers(ctx, region_id)
        if role is KeystoneRole.REEF_BUILDER:
            await hold_reef_fish(ctx, region_id, strength)
        land = await ctx.session.get(RegionEnvironmentRow, region_id)
        if land is None or "soil_fertility" in land.locked:
            continue
        if role is KeystoneRole.SOIL_MAKER and strength > 0:
            land.soil_fertility = clamp_int(land.soil_fertility + round_half_up(table.soil_gain * strength / PERCENT), 0, PERCENT)
        elif strength <= 0:
            land.soil_fertility = clamp_int(land.soil_fertility - table.lost_decay, 0, PERCENT)
    await ctx.session.flush()
