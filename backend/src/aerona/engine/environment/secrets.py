from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.materials import MATERIALS
from aerona.catalog.place_terrain import DEEPENS, kind_spec
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.economy import CommodityKind, MaterialFamily
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindSeat
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import DiscoveryMode, SecretKind, SecretOrigin
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats, KnowledgeStats, ResourceStats, SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.places import KIND_LOCK, write_kind
from aerona.engine.lore.rites import devise, rite_of
from aerona.engine.notes import note
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon, connect, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat
from aerona.rules.registry import Rules

SEALED_KINDS = frozenset({SecretKind.SEALED_SPIRIT, SecretKind.UNDERWORLD_ENTRANCE})
MINEABLE = (MaterialFamily.METAL, MaterialFamily.PRECIOUS, MaterialFamily.STONE, MaterialFamily.EXOTIC)
SECRET_LABELS: dict[SecretKind, str] = {
    SecretKind.HIDDEN_RESOURCE: "a hidden seam",
    SecretKind.BURIED_RELIC: "a buried relic",
    SecretKind.SEALED_SPIRIT: "a sealed spirit",
    SecretKind.LOST_KNOWLEDGE: "lost knowledge",
    SecretKind.LOST_RITE: "a lost rite",
    SecretKind.UNDERWORLD_ENTRANCE: "a way down to the underworld",
    SecretKind.HIDDEN_PEOPLE: "a hidden people",
    SecretKind.DORMANT_MIND: "a sleeping mind",
    SecretKind.SEALED_REALM: "a sealed realm",
}
MODE_VERBS: dict[DiscoveryMode, str] = {
    DiscoveryMode.EXPLORER: "searching",
    DiscoveryMode.SEER: "a seer's vision",
    DiscoveryMode.MINER: "deep digging",
    DiscoveryMode.MYSTERY: "solving its mystery",
    DiscoveryMode.PLAYER: "the will of the Creator",
    DiscoveryMode.SON: "a god's sign",
}


@dataclass(frozen=True)
class SecretDraft:
    kind: SecretKind
    strength: int
    material: MaterialKind | None = None
    school: MagicSchool | None = None
    branch: KnowledgeBranch | None = None


def mineable_materials(region: RegionEnvironmentRow | None) -> list[MaterialKind]:
    seams = [MaterialKind(key) for key in sorted(region.mineral_layers)] if region is not None else []
    return seams or sorted((kind for kind, spec in MATERIALS.items() if spec.family in MINEABLE), key=lambda kind: kind.value)


def draft_for(kind: SecretKind, strength: int, rng: SeededRandom, region: RegionEnvironmentRow | None) -> SecretDraft:
    if kind is SecretKind.HIDDEN_RESOURCE:
        return SecretDraft(kind, strength, material=rng.pick(mineable_materials(region)))
    if kind is SecretKind.LOST_RITE:
        return SecretDraft(kind, strength, school=rng.pick(list(MagicSchool)))
    if kind is SecretKind.LOST_KNOWLEDGE:
        return SecretDraft(kind, strength, branch=rng.pick(list(KnowledgeBranch)))
    return SecretDraft(kind, strength)


def hide(ctx: TickContext, place_id: int, draft: SecretDraft, origin: SecretOrigin, son_id: int | None = None) -> PlaceSecretRow:
    row = PlaceSecretRow(
        place_entity_id=place_id,
        kind=draft.kind,
        strength=clamp_int(draft.strength, 0, PERCENT),
        sealed=draft.kind in SEALED_KINDS,
        held=False,
        origin=origin,
        material=draft.material,
        school=draft.school,
        branch=draft.branch,
        hidden_by_son_id=son_id,
        created_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    return row


def seeded_draft(rules: Rules, rng: SeededRandom, profile: PlaceProfileRow, mystery: int, region: RegionEnvironmentRow | None) -> SecretDraft | None:
    table = rules.places
    options = kind_spec(profile.kind).secrets
    if not options or not rng.chance(mystery * table.secret_chance_pct / PERCENT):
        return None
    strength = table.secret_strength_min + rng.below(table.secret_strength_die)
    return draft_for(rng.pick(list(options)), strength, rng, region)


def find_chance(rules: Rules, *, skill: int, mystery: int, strength: int, called: bool) -> float:
    table = rules.places
    chance = (
        table.discover_base_pct
        + skill * table.discover_skill_pct / PERCENT
        + mystery * table.discover_mystery_pct / PERCENT
        - strength * table.discover_strength_pct / PERCENT
        + (table.discover_role_pct if called else 0)
    )
    return max(0.0, min(float(table.discover_cap_pct), chance))


def miner_chance(rules: Rules, mined: int, strength: int) -> float:
    table = rules.places
    if mined < table.miner_mined_min:
        return 0.0
    return mined * table.miner_pct / PERCENT * (PERCENT - strength) / PERCENT


def release_chance(rules: Rules, mined: int) -> float:
    table = rules.places
    if mined < table.miner_mined_min:
        return 0.0
    return mined * table.release_pct / PERCENT


async def home_community(ctx: TickContext, finder: EntityRow | None) -> EntityRow | None:
    if finder is None:
        return None
    if finder.entity_type in COMMUNITY_TYPES:
        return finder
    home = await living_entity(ctx.session, finder.location_id)
    return home if home is not None and home.entity_type in COMMUNITY_TYPES else None


async def unearth_resource(ctx: TickContext, secret: PlaceSecretRow, place: EntityRow, region: RegionEnvironmentRow | None) -> EntityRow:
    material = secret.material or mineable_materials(region)[0]
    if region is not None:
        region.mineral_layers = {**region.mineral_layers, material.value: max(region.mineral_layers.get(material.value, 0), secret.strength)}
    spec = MATERIALS.get(material)
    resource = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.RESOURCE,
            name=f"{spec.label if spec is not None else material.value.title()} of {place.name}",
            body=f"A seam of {material.value.replace('_', ' ')} that lay hidden in {place.name} until it was found.",
            stats=ResourceStats(abundance=secret.strength, value=secret.strength, might=secret.strength // 2),
            power=ctx.rules.places.resource_power,
            world_id=place.world_id,
            location_id=place.id,
        ),
    )
    commodity = CommodityKind.STONE if spec is not None and spec.family is MaterialFamily.STONE else CommodityKind.ORE
    await set_resource_yield(ctx.session, ctx.rules, resource.id, commodity, material)
    return resource


async def unearth_relic(ctx: TickContext, secret: PlaceSecretRow, place: EntityRow) -> EntityRow:
    cursed = ctx.rng(f"relic_curse.{secret.id}").chance(ctx.rules.places.relic_curse_pct)
    return await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=f"The Buried Relic of {place.name}",
            body=f"An old and holy thing that lay buried in {place.name}.",
            stats=ItemStats(might=secret.strength, curse=secret.strength if cursed else 0),
            power=ctx.rules.places.relic_power,
            world_id=place.world_id,
            location_id=place.id,
            flags=(EntityFlag.CURSED,) if cursed else (),
        ),
    )


async def recover_knowledge(ctx: TickContext, secret: PlaceSecretRow, place: EntityRow, learner: EntityRow | None) -> EntityRow:
    lost = await flags_by_entity(ctx.session, EntityFlag.LOST)
    found = next((item for item in await canon(ctx.session, [EntityType.KNOWLEDGE], place.world_id) if item.id in lost), None)
    if found is None:
        found = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.KNOWLEDGE,
                name=f"The Lore of {place.name}",
                body=f"Knowledge that was lost long ago and lay hidden in {place.name}.",
                stats=KnowledgeStats(level=ctx.rules.places.knowledge_level, spread=0),
                power=ctx.rules.places.knowledge_power,
                world_id=place.world_id,
                knowledge_branch=secret.branch or KnowledgeBranch.MAGIC,
            ),
        )
    else:
        await remove_flag(ctx.session, found.id, EntityFlag.LOST)
    if learner is not None:
        await teach(ctx, learner.id, found, f"found in {place.name}")
    return found


async def recover_rite(ctx: TickContext, secret: PlaceSecretRow, place: EntityRow, finder: EntityRow | None) -> EntityRow | None:
    school = secret.school or MagicSchool.DIVINATION
    known = await rite_of(ctx, school)
    if known is not None:
        if finder is not None:
            await connect(ctx.session, finder.id, known[0].id, BondKind.OWNS, ctx.epoch, description=f"found in {place.name}")
        return known[0]
    if finder is None:
        return None
    rite, _ = await devise(ctx, school, finder)
    return rite


async def release(ctx: TickContext, secret: PlaceSecretRow, place: EntityRow, region: RegionEnvironmentRow | None) -> str:
    table = ctx.rules.places
    secret.sealed = False
    secret.released_epoch = ctx.epoch
    if region is not None:
        add_scar(region, ScarKind.HAUNTED, table.haunted_depth)
    if secret.kind is SecretKind.SEALED_SPIRIT:
        spirit = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.SPIRIT,
                name=f"The Unbound of {place.name}",
                body=f"A spirit sealed beneath {place.name} long ago, set loose when the seal broke.",
                stats=SpiritStats(strength=secret.strength, unrest=table.released_unrest),
                power=table.spirit_power,
                world_id=place.world_id,
                location_id=place.id,
            ),
        )
        secret.result_entity_id = spirit.id
        await note(
            ctx,
            f"The seal beneath {place.name} broke and {spirit.name} went free; the land around it is haunted.",
            key="place.secret_released",
            ids=[place.id, spirit.id],
            roles={spirit.id: IncidentRole.ACTOR, place.id: IncidentRole.PLACE},
        )
        return spirit.name
    shift_stat(place, "danger", table.entrance_danger)
    profile = await ctx.session.get(PlaceProfileRow, place.id)
    if profile is not None and KIND_LOCK not in profile.locked and profile.kind in DEEPENS:
        await write_kind(ctx.session, ctx.rules, place.id, DEEPENS[profile.kind])
    await note(
        ctx,
        f"The way down beneath {place.name} lies open; the dead walk near it and the deep breathes out.",
        key="place.secret_opened",
        ids=[place.id],
        roles={place.id: IncidentRole.PLACE},
    )
    return place.name


async def underworld_of(ctx: TickContext, world_id: int | None) -> EntityRow | None:
    if world_id is None:
        return None
    return await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.world_id == world_id,
            EntityRow.is_underworld.is_(True),
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type == EntityType.REGION,
        )
        .order_by(EntityRow.id)
        .limit(1)
    )


async def hidden_people(ctx: TickContext, place: EntityRow) -> EntityRow | None:
    return await ctx.session.scalar(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.location_id == place.id, EntityRow.status == EntityStatus.CANON).limit(1)
    )


async def sleeping_mind(ctx: TickContext, place: EntityRow) -> EntityRow | None:
    here = select(EntityRow.id).where(EntityRow.location_id == place.id, EntityRow.status == EntityStatus.CANON)
    mind = await ctx.session.scalar(select(MindProfileRow).where(MindProfileRow.node_id.in_(here), MindProfileRow.seat != MindSeat.BODY).limit(1))
    if mind is None:
        return None
    if "stability" not in mind.locked:
        mind.stability = clamp_int(mind.stability + ctx.rules.places.woken_stability, 0, PERCENT)
    return await ctx.session.get(EntityRow, mind.node_id)


async def sealed_realm(ctx: TickContext, place: EntityRow) -> EntityRow | None:
    realm = await ctx.session.scalar(select(MadeRealmRow).where(MadeRealmRow.host_node_id == place.id).limit(1))
    if realm is None:
        return None
    if "sealed" not in realm.locked:
        realm.sealed = False
    return await ctx.session.get(EntityRow, realm.dimension_id)


UNCOVERED: dict[SecretKind, Callable[[TickContext, EntityRow], Awaitable[EntityRow | None]]] = {
    SecretKind.HIDDEN_PEOPLE: hidden_people,
    SecretKind.DORMANT_MIND: sleeping_mind,
    SecretKind.SEALED_REALM: sealed_realm,
}


async def reveal(
    ctx: TickContext, secret: PlaceSecretRow, mode: DiscoveryMode, finder: EntityRow | None, region: RegionEnvironmentRow | None
) -> EntityRow | None:
    place = await living_entity(ctx.session, secret.place_entity_id)
    if place is None or secret.revealed_epoch is not None:
        return None
    secret.revealed_epoch = ctx.epoch
    secret.revealed_by = mode
    secret.revealed_by_entity_id = finder.id if finder is not None else None
    learner = await home_community(ctx, finder)
    result: EntityRow | None = None
    if secret.kind is SecretKind.HIDDEN_RESOURCE:
        result = await unearth_resource(ctx, secret, place, region)
    elif secret.kind is SecretKind.BURIED_RELIC:
        result = await unearth_relic(ctx, secret, place)
    elif secret.kind is SecretKind.LOST_KNOWLEDGE:
        result = await recover_knowledge(ctx, secret, place, learner)
    elif secret.kind is SecretKind.LOST_RITE:
        result = await recover_rite(ctx, secret, place, finder or learner)
    elif secret.kind in UNCOVERED:
        result = await UNCOVERED[secret.kind](ctx, place)
    elif secret.kind is SecretKind.UNDERWORLD_ENTRANCE:
        result = await underworld_of(ctx, place.world_id)
        if result is not None:
            await connect(ctx.session, place.id, result.id, BondKind.DISCOVERED, ctx.epoch, description="a way down")
    if result is not None and secret.kind is not SecretKind.UNDERWORLD_ENTRANCE:
        secret.result_entity_id = result.id
        if finder is not None:
            await connect(ctx.session, finder.id, result.id, BondKind.DISCOVERED, ctx.epoch, description=f"found in {place.name}")
    who = finder.name if finder is not None else "No one living"
    found = f": {result.name}" if result is not None else ""
    ids = [item.id for item in (place, finder, result) if item is not None]
    roles = {place.id: IncidentRole.PLACE, **({finder.id: IncidentRole.ACTOR} if finder is not None else {})}
    await note(
        ctx,
        f"{who} found {SECRET_LABELS[secret.kind]} in {place.name} by {MODE_VERBS[mode]}{found}.",
        key=f"place.secret_{secret.kind.value}",
        ids=ids,
        kind=ChronicleKind.KNOWLEDGE if secret.kind in (SecretKind.LOST_KNOWLEDGE, SecretKind.LOST_RITE) else ChronicleKind.WORLD,
        roles=roles,
    )
    if secret.sealed and mode is DiscoveryMode.MINER and not secret.held:
        await release(ctx, secret, place, region)
    return result
