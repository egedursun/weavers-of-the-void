from collections import Counter, defaultdict

from sqlalchemy import func, select

from aerona.catalog.place_terrain import BATTLEFIELD_FROM, kind_spec
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretOrigin
from aerona.engine.context import TickContext
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
from aerona.engine.environment.secrets import find_chance, hide, miner_chance, release, release_chance, reveal, seeded_draft
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import best_skill
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import shift_stat, stat, stat_or

EXPLORER_ROLES = frozenset({MortalRole.EXPLORER, MortalRole.HUNTER, MortalRole.HERO})
SEER_ROLES = frozenset({MortalRole.SEER, MortalRole.PRIEST, MortalRole.SAGE, MortalRole.SAINT})
CALLED = frozenset({MortalRole.EXPLORER, MortalRole.SEER})
EXPLORER_SKILLS = (SkillKind.TRACKING, SkillKind.NAVIGATION, SkillKind.MOUNTAINEERING)
SEER_SKILLS = (SkillKind.PROPHECY, SkillKind.SPIRIT_SPEAKING, SkillKind.LORE)


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
    "settlement.population",
    "table.battles",
    "table.entity_flags",
    "table.place_environment",
    "table.place_profiles",
    "table.region_environment",
    "table.relics",
    "table.world_maps",
)
@writes(
    "people.piety",
    "settlement.piety",
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
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
            await note(
                ctx,
                f"So many battles were fought at {place.name} that it is now remembered as a battlefield.",
                key="place.became_battlefield",
                ids=[place.id],
                roles={place.id: IncidentRole.PLACE},
            )
        if SACREDNESS_LOCK not in profile.locked:
            inputs = SacredInputs(temples.get(place.id, 0), relics.get(place.id, 0), place.id in marked, ground is not None and ground.nexus)
            profile.sacredness = drift_toward(profile.sacredness, sacred_target(rules, profile.kind, inputs), table.sacred_drift)
        profile.pilgrims = pilgrims_drawn(rules, profile.sacredness, people[region_id] if region_id is not None else 0)
        if profile.pilgrims:
            pilgrims += profile.pilgrims
            await send_pilgrims(ctx, atlas, place, region_id, communities)
        if not profile.secrets_seeded:
            profile.secrets_seeded = True
            draft = seeded_draft(rules, ctx.rng(f"secret.{place.id}"), profile, stat_or(place, "mystery", 0), regions.get(region_id) if region_id else None)
            if draft is not None:
                hide(ctx, place.id, draft, SecretOrigin.LAND)
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
        chance = find_chance(ctx.rules, skill=skill, mystery=mystery, strength=secret.strength, called=mortal.mortal_role in CALLED)
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
    "place.mystery",
    "resource.abundance",
    "resource.might",
    "resource.value",
    "table.bonds",
    "table.epoch_year_cursors",
    "table.name_registry",
    "table.nodes",
    "table.place_profiles",
    "table.place_secrets",
    "table.region_environment",
    "table.resource_profiles",
    "table.rite_profiles",
    "table.skills",
    "table.world_maps",
)
@writes(
    "place.danger",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
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
