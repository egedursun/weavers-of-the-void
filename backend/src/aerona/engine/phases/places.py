from collections import Counter, defaultdict

from sqlalchemy import func, select

from aerona.catalog.life.domain import GONE_STATES
from aerona.catalog.life.phases import EXPLORER_SKILLS, SEER_SKILLS
from aerona.catalog.place_terrain import BATTLEFIELD_FROM, DEBRIS_FROM, MEGA_RUIN_FROM, WRECK_FROM, kind_spec
from aerona.catalog.stats import PERCENT
from aerona.catalog.structures import MEGASTRUCTURES
from aerona.catalog.vehicles import FRAMES
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretKind, SecretOrigin
from aerona.engine.context import TickContext
from aerona.engine.environment.place_traits import bathe, collapse_sinkhole, trap_beasts
from aerona.engine.environment.places import (
    KIND_LOCK,
    SACREDNESS_LOCK,
    SacredInputs,
    drift_toward,
    pilgrims_drawn,
    relics_at,
    sacred_target,
    temples_at,
    write_kind,
)
from aerona.engine.environment.secrets import find_chance, hide, miner_chance, release, release_chance, reveal, seeded_draft, subject_for
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import best_skill
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.vehicles.wrecks import VOID_DOMAINS
from aerona.rules.registry import Rules

EXPLORER_ROLES = frozenset({MortalRole.EXPLORER, MortalRole.HUNTER, MortalRole.HERO, MortalRole.SCIENTIST, MortalRole.PILOT})
SEER_ROLES = frozenset({MortalRole.SEER, MortalRole.PRIEST, MortalRole.SAGE, MortalRole.SAINT})
CALLED = frozenset({MortalRole.EXPLORER, MortalRole.SEER})


async def wrecks_by_region(ctx: TickContext) -> tuple[Counter[int], Counter[int]]:
    wrecks: Counter[int] = Counter()
    debris: Counter[int] = Counter()
    rows = await ctx.session.execute(
        select(VesselProfileRow.region_entity_id, VesselProfileRow.frame).where(
            VesselProfileRow.status == VesselStatus.WRECKED, VesselProfileRow.region_entity_id.is_not(None)
        )
    )
    for region_id, frame in rows:
        if region_id is not None:
            (debris if FRAMES[frame].domain in VOID_DOMAINS else wrecks)[region_id] += 1
    return wrecks, debris


async def fallen_megastructures(ctx: TickContext) -> set[int]:
    atlas = await RegionAtlas.load(ctx.session)
    hosts = await ctx.session.scalars(
        select(StructureProfileRow.host_entity_id).where(
            StructureProfileRow.kind.in_(list(MEGASTRUCTURES)), StructureProfileRow.construction_state.in_(list(GONE_STATES))
        )
    )
    return {region for host in hosts if host is not None and (region := atlas.top_region(int(host))) is not None}


def remade_kind(
    rules: Rules, profile: PlaceProfileRow, region_id: int | None, *, wrecks: Counter[int], debris: Counter[int], fallen: set[int]
) -> PlaceKind | None:
    if region_id is None:
        return None
    table = rules.places
    if profile.kind in WRECK_FROM and wrecks[region_id] >= table.wreck_site_wrecks:
        return PlaceKind.WRECK_SITE
    if profile.kind in DEBRIS_FROM and debris[region_id] >= table.wreck_site_wrecks:
        return PlaceKind.DEBRIS_FIELD
    return PlaceKind.MEGASTRUCTURE_RUIN if profile.kind in MEGA_RUIN_FROM and region_id in fallen else None


async def battles_at(ctx: TickContext, place_ids: list[int]) -> Counter[int]:
    if not place_ids:
        return Counter()
    rows = await ctx.session.execute(
        select(BattleRow.place_entity_id, func.count()).where(BattleRow.place_entity_id.in_(place_ids)).group_by(BattleRow.place_entity_id)
    )
    return Counter({place_id: count for place_id, count in rows if place_id is not None})


async def region_people(ctx: TickContext, atlas: RegionAtlas) -> Counter[int]:
    people: Counter[int] = Counter()
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        region_id = atlas.top_region(community.id)
        if region_id is not None:
            people[region_id] += stat_or(community, "population", 0)
    return people


async def send_pilgrims(ctx: TickContext, atlas: RegionAtlas, place: EntityRow, region_id: int | None, communities: list[EntityRow]) -> None:
    table = ctx.rules.places
    for community in communities:
        if atlas.top_region(community.id) != region_id:
            continue
        if stat(community, "piety") is not None:
            shift_stat(community, "piety", table.pilgrim_piety)
        if community.location_id == place.id and stat(community, "prosperity") is not None:
            shift_stat(community, "prosperity", table.pilgrim_prosperity)


@reads(
    "people.population",
    "place.mystery",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.battles",
    "table.deep_passages",
    "table.disease_profiles",
    "table.entities",
    "table.entity_flags",
    "table.nodes",
    "table.place_environment",
    "table.place_profiles",
    "table.region_environment",
    "table.relics",
    "table.structure_profiles",
    "table.vessel_profiles",
    "table.world_maps",
)
@writes(
    "people.piety",
    "settlement.piety",
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.place_environment",
    "table.place_profiles",
    "table.place_secrets",
)
async def place_profiles(ctx: TickContext) -> None:
    rules = ctx.rules
    table = rules.places
    profiles = {row.entity_id: row for row in await ctx.session.scalars(select(PlaceProfileRow))}
    places = [place for place in await canon(ctx.session, [EntityType.PLACE]) if place.id in profiles]
    ids = [place.id for place in places]
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(PlaceEnvironmentRow).where(PlaceEnvironmentRow.entity_id.in_(ids)))}
    regions = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    temples, relics, battles = await temples_at(ctx.session, ids), await relics_at(ctx.session, ids), await battles_at(ctx, ids)
    wrecks, debris = await wrecks_by_region(ctx)
    fallen = await fallen_megastructures(ctx)
    marked = await flags_by_entity(ctx.session, EntityFlag.PILGRIMAGE_SITE)
    atlas = await RegionAtlas.load(ctx.session)
    people = await region_people(ctx, atlas)
    communities = await canon(ctx.session, COMMUNITY_TYPES)
    turned = seeded = pilgrims = 0
    for place in places:
        profile = profiles[place.id]
        ground = grounds.get(place.id)
        region_id = atlas.top_region(place.id)
        if KIND_LOCK not in profile.locked and profile.kind in BATTLEFIELD_FROM and battles[place.id] >= table.battlefield_battles:
            await write_kind(ctx.session, rules, place.id, PlaceKind.BATTLEFIELD)
            turned += 1
            await record(ctx, "place.became_battlefield", roles={IncidentRole.PLACE: place.id}, facts={"battles": battles[place.id]}, place=place.id)
        remade = remade_kind(rules, profile, region_id, wrecks=wrecks, debris=debris, fallen=fallen)
        if KIND_LOCK not in profile.locked and remade is not None:
            await write_kind(ctx.session, rules, place.id, remade)
            turned += 1
        if SACREDNESS_LOCK not in profile.locked:
            inputs = SacredInputs(temples.get(place.id, 0), relics.get(place.id, 0), place.id in marked, ground is not None and ground.nexus)
            profile.sacredness = drift_toward(profile.sacredness, sacred_target(rules, profile.kind, inputs), table.sacred_drift)
        profile.pilgrims = pilgrims_drawn(rules, profile.sacredness, people[region_id] if region_id is not None else 0)
        if profile.pilgrims:
            pilgrims += profile.pilgrims
            await send_pilgrims(ctx, atlas, place, region_id, communities)
        if profile.kind is PlaceKind.SINKHOLE:
            await collapse_sinkhole(ctx, place)
        elif profile.kind is PlaceKind.HOT_SPRING:
            await bathe(ctx, place)
        elif profile.kind is PlaceKind.TAR_PIT:
            await trap_beasts(ctx, place, region_id)
        if not profile.secrets_seeded:
            profile.secrets_seeded = True
            draft = seeded_draft(rules, ctx.rng(f"secret.{place.id}"), profile, stat_or(place, "mystery", 0), regions.get(region_id) if region_id else None)
            if draft is not None:
                row = hide(ctx, place.id, draft, SecretOrigin.LAND)
                row.subject_entity_id = await subject_for(ctx, draft.kind, region_id)
                seeded += 1
    await ctx.session.flush()
    ctx.count("battlefields", turned)
    ctx.count("secrets_seeded", seeded)
    ctx.count("pilgrims", pilgrims)


async def searchers_by_region(ctx: TickContext, atlas: RegionAtlas) -> dict[int, list[EntityRow]]:
    found: dict[int, list[EntityRow]] = defaultdict(list)
    mortals = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role.in_(list(EXPLORER_ROLES | SEER_ROLES)))
        .order_by(EntityRow.id)
    )
    for mortal in mortals:
        region_id = atlas.top_region(mortal.id)
        if region_id is not None:
            found[region_id].append(mortal)
    return found


async def search(ctx: TickContext, secret: PlaceSecretRow, place: EntityRow, searchers: list[EntityRow]) -> tuple[EntityRow, DiscoveryMode] | None:
    mystery = stat_or(place, "mystery", 0)
    for mortal in searchers:
        seer = mortal.mortal_role in SEER_ROLES
        skill = await best_skill(ctx.session, mortal.id, SEER_SKILLS if seer else EXPLORER_SKILLS)
        chance = find_chance(ctx.rules, skill=skill, mystery=mystery, strength=secret.strength, called=mortal.mortal_role in CALLED, kind=secret.kind)
        if ctx.rng(f"search.{secret.id}.{mortal.id}").chance(chance):
            return mortal, DiscoveryMode.SEER if seer else DiscoveryMode.EXPLORER
    return None


async def miner_of(ctx: TickContext, atlas: RegionAtlas, region_id: int | None) -> EntityRow | None:
    if region_id is None:
        return None
    for community_id in atlas.communities_in(region_id):
        community = await ctx.session.get(EntityRow, community_id)
        if community is not None and community.status is EntityStatus.CANON:
            return community
    return None


@reads(
    "item.damage",
    "item.might",
    "item.protection",
    "knowledge.spread",
    "place.mystery",
    "resource.abundance",
    "resource.might",
    "resource.value",
    "table.bonds",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.item_profiles",
    "table.lifecycle_states",
    "table.name_registry",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.place_profiles",
    "table.place_secrets",
    "table.region_environment",
    "table.resource_profiles",
    "table.rite_profiles",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.state_changes",
    "table.world_maps",
    "table.world_materials",
    "table.worlds",
)
@writes(
    "knowledge.spread",
    "place.danger",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.place_environment",
    "table.place_profiles",
    "table.place_secrets",
    "table.region_environment",
    "table.resource_profiles",
    "table.rite_effects",
    "table.rite_profiles",
)
async def place_secrets(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    searchers = await searchers_by_region(ctx, atlas)
    regions = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    profiles = {row.entity_id: row for row in await ctx.session.scalars(select(PlaceProfileRow))}
    secrets = list(
        await ctx.session.scalars(select(PlaceSecretRow).where(PlaceSecretRow.held.is_(False)).order_by(PlaceSecretRow.place_entity_id, PlaceSecretRow.id))
    )
    revealed = released = 0
    for secret in secrets:
        place = await ctx.session.get(EntityRow, secret.place_entity_id)
        if place is None or place.status is not EntityStatus.CANON or held(place.id):
            continue
        region_id = atlas.top_region(place.id)
        region = regions.get(region_id) if region_id is not None else None
        profile = profiles.get(place.id)
        deep = profile is not None and kind_spec(profile.kind).deep
        mined = region.mined if region is not None and deep else 0
        if (
            secret.revealed_epoch is None
            and secret.kind is SecretKind.SLEEPING_BEAST
            and ctx.rng(f"wake.{secret.id}.{ctx.epoch}").chance(ctx.rules.secrets.sleeping_beast_wake_pct + mined * ctx.rules.places.miner_pct / PERCENT)
        ):
            await reveal(ctx, secret, DiscoveryMode.MINER if mined else DiscoveryMode.MYSTERY, None, region)
            revealed += 1
            continue
        if secret.revealed_epoch is None:
            found = await search(ctx, secret, place, searchers.get(region_id, []) if region_id is not None else [])
            if found is None and ctx.rng(f"dig.{secret.id}").chance(miner_chance(ctx.rules, mined, secret.strength)):
                found = (await miner_of(ctx, atlas, region_id) or place, DiscoveryMode.MINER)
            if found is not None and not held(found[0].id):
                finder, mode = found
                await reveal(ctx, secret, mode, finder if finder.id != place.id else None, region)
                revealed += 1
            continue
        if secret.sealed and ctx.rng(f"breach.{secret.id}").chance(release_chance(ctx.rules, mined)):
            await release(ctx, secret, place, region)
            released += 1
    await ctx.session.flush()
    ctx.count("secrets_revealed", revealed)
    ctx.count("secrets_released", released)


PHASES = (Phase("place_profiles", place_profiles), Phase("place_secrets", place_secrets))
