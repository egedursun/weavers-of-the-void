from typing import Literal

from pydantic import Field
from sqlalchemy import delete

from aerona.catalog.place_terrain import kind_spec
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretKind, SecretOrigin
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import PlaceStats
from aerona.engine.environment import control
from aerona.engine.environment.places import KIND_LOCK, MYSTERY_KEY, SACREDNESS_LOCK, write_kind
from aerona.engine.environment.secrets import SEALED_KINDS, SecretDraft, hide, release, reveal
from aerona.engine.phases.environment import new_place_environment
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.queries import remove_flag
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 60
PLACE_HOLD_REASON = "player.place_hold"
PlaceField = Literal["kind", "sacredness", "mystery", "terrain", "cover", "water_source", "height_advantage", "chokepoint", "nexus"]
PROFILE_LOCKS = frozenset({KIND_LOCK, SACREDNESS_LOCK})
LAND = (EntityType.REGION, EntityType.PLACE)


class CreatePlace(Command):
    region_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX)
    kind: PlaceKind
    mystery: int = Field(default=50, ge=0, le=100)
    danger: int = Field(default=30, ge=0, le=100)
    fertility: int = Field(default=50, ge=0, le=100)
    sacredness: int | None = Field(default=None, ge=0, le=100)


class EditPlace(Command):
    place_id: int
    kind: PlaceKind | None = None
    sacredness: int | None = Field(default=None, ge=0, le=100)
    mystery: int | None = Field(default=None, ge=0, le=100)
    hold: bool = True


class ReleasePlace(Command):
    place_id: int
    field: PlaceField


class HideSecret(Command):
    place_id: int
    kind: SecretKind
    strength: int = Field(default=50, ge=0, le=100)
    material: MaterialKind | None = None
    school: MagicSchool | None = None
    branch: KnowledgeBranch | None = None


class EditSecret(Command):
    secret_id: int
    kind: SecretKind | None = None
    strength: int | None = Field(default=None, ge=0, le=100)
    sealed: bool | None = None
    held: bool | None = None
    material: MaterialKind | None = None
    school: MagicSchool | None = None
    branch: KnowledgeBranch | None = None


class RevealSecret(Command):
    secret_id: int
    release: bool = False


class SecretTarget(Command):
    secret_id: int


class SiteTarget(Command):
    entity_id: int


async def _place(scope: PlayerScope, place_id: int) -> EntityRow:
    return guards.of_types(await guards.canon_entity(scope.session, place_id, "The place"), [EntityType.PLACE], "Only a place can be shaped this way.")


async def _profile(scope: PlayerScope, place: EntityRow) -> PlaceProfileRow:
    profile = await scope.session.get(PlaceProfileRow, place.id)
    if profile is None:
        raise NotFoundError(f"{place.name} has not been surveyed yet; run the environment survey first.")
    return profile


async def _secret(scope: PlayerScope, secret_id: int) -> PlaceSecretRow:
    secret = await scope.session.get(PlaceSecretRow, secret_id)
    if secret is None:
        raise NotFoundError("No such secret.")
    return secret


async def _clear_hold(scope: PlayerScope, place_id: int) -> int:
    result = await scope.session.execute(
        delete(ModifierRow).where(ModifierRow.target_node_id == place_id, ModifierRow.target_key == MYSTERY_KEY, ModifierRow.source_kind == ModifierSource.PIN)
    )
    return int(getattr(result, "rowcount", 0) or 0)


def _lock(profile: PlaceProfileRow, key: str, hold: bool) -> None:
    locked = set(profile.locked)
    if hold:
        locked.add(key)
    profile.locked = sorted(locked)


@player_action("place:create", ActionKind.CREATE_ENTITY)
async def create_place(scope: PlayerScope, command: CreatePlace) -> Effect:
    region = guards.of_types(await guards.canon_entity(scope.session, command.region_id, "The region"), LAND, "A place stands in a region or another place.")
    ctx = await scope.context("place_create")
    creator = await scope.creator()
    spec = kind_spec(command.kind)
    place = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PLACE,
            name=guards.clip(command.name, NAME_MAX),
            body=f"A {spec.label.lower()} of {region.name}, brought forth by {creator.name}.",
            stats=PlaceStats(danger=command.danger, fertility=command.fertility, mystery=command.mystery),
            power=scope.rules.geography.place_power,
            world_id=region.world_id,
            location_id=region.id,
        ),
    )
    profile = await write_kind(scope.session, scope.rules, place.id, command.kind)
    if command.sacredness is not None:
        profile.sacredness = command.sacredness
        _lock(profile, SACREDNESS_LOCK, True)
    region_id = (await RegionAtlas.load(scope.session)).top_region(place.id)
    scope.session.add(new_place_environment(scope.rules, place, region_id, 1.0, command.kind))
    await scope.session.flush()
    return Effect(f"{place.name}, a {spec.label.lower()}, rose in {region.name}.", place.id, created_ids=(place.id,))


@player_action("place:edit", ActionKind.OTHER)
async def edit_place(scope: PlayerScope, command: EditPlace) -> Effect:
    place = await _place(scope, command.place_id)
    profile = await _profile(scope, place)
    changed: list[str] = []
    if command.kind is not None:
        await write_kind(scope.session, scope.rules, place.id, command.kind)
        _lock(profile, KIND_LOCK, command.hold)
        changed.append(f"is now a {kind_spec(command.kind).label.lower()}")
    if command.sacredness is not None:
        profile.sacredness = command.sacredness
        _lock(profile, SACREDNESS_LOCK, command.hold)
        changed.append(f"has sacredness {command.sacredness}")
    if command.mystery is not None:
        set_stats(place, mystery=command.mystery)
        if command.hold:
            await _clear_hold(scope, place.id)
            await add_modifier(
                scope.session, ModifierDraft(place.id, MYSTERY_KEY, ModifierOp.ADD, 0, ModifierSource.PIN, PLACE_HOLD_REASON, start_epoch=await scope.epoch())
            )
        changed.append(f"has mystery {command.mystery}")
    if not changed:
        raise ValidationFailedError("Name a kind, sacredness or mystery to change.")
    held = " and is held there" if command.hold else ""
    return Effect(f"{place.name} {', '.join(changed)}{held}.", target_node_id=place.id)


@player_action("place:release", ActionKind.OTHER)
async def release_place(scope: PlayerScope, command: ReleasePlace) -> Effect:
    place = await _place(scope, command.place_id)
    label = command.field.replace("_", " ")
    if command.field in PROFILE_LOCKS:
        profile = await _profile(scope, place)
        if command.field not in profile.locked:
            raise ValidationFailedError(f"{place.name}'s {label} is not held.")
        profile.locked = sorted(set(profile.locked) - {command.field})
    elif command.field == MYSTERY_KEY:
        if not await _clear_hold(scope, place.id):
            raise ValidationFailedError(f"{place.name}'s mystery is not held.")
    else:
        ground = await control.place_ground(scope.session, place.id)
        if not control.unlock_place_field(ground, command.field):
            raise ValidationFailedError(f"{place.name}'s {label} is not held.")
    return Effect(f"{place.name}'s {label} follows the world again.", target_node_id=place.id)


@player_action("place:secret", ActionKind.HIDE_SECRET)
async def hide_secret(scope: PlayerScope, command: HideSecret) -> Effect:
    place = await _place(scope, command.place_id)
    ctx = await scope.context("place_secret")
    draft = SecretDraft(command.kind, command.strength, command.material, command.school, command.branch)
    secret = hide(ctx, place.id, draft, SecretOrigin.PLAYER)
    await scope.session.flush()
    return Effect(f"A secret now lies hidden in {place.name}.", place.id, values={"secret_id": secret.id})


@player_action("place:secret_edit", ActionKind.OTHER)
async def edit_secret(scope: PlayerScope, command: EditSecret) -> Effect:
    secret = await _secret(scope, command.secret_id)
    place = await _place(scope, secret.place_entity_id)
    values = command.model_dump(exclude={"secret_id"}, exclude_none=True)
    if not values:
        raise ValidationFailedError("Name something about the secret to change.")
    for key, value in values.items():
        setattr(secret, key, value)
    if command.kind is not None and command.sealed is None and secret.released_epoch is None:
        secret.sealed = secret.kind in SEALED_KINDS
    held = " The land keeps it hidden." if secret.held else ""
    return Effect(f"The secret of {place.name} was reshaped.{held}", target_node_id=place.id)


@player_action("place:reveal", ActionKind.REVEAL_SECRET)
async def reveal_secret(scope: PlayerScope, command: RevealSecret) -> Effect:
    secret = await _secret(scope, command.secret_id)
    place = await _place(scope, secret.place_entity_id)
    ctx = await scope.context("place_reveal")
    region_id = (await RegionAtlas.load(scope.session)).top_region(place.id)
    region = await scope.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    created: tuple[int, ...] = ()
    if secret.revealed_epoch is None:
        result = await reveal(ctx, secret, DiscoveryMode.PLAYER, None, region)
        created = (result.id,) if result is not None and result.id != place.id else ()
    elif not command.release:
        raise ValidationFailedError(f"The secret of {place.name} is already known.")
    if command.release:
        if not secret.sealed:
            raise ValidationFailedError(f"Nothing is sealed in {place.name}.")
        await release(ctx, secret, place, region)
        created = (*created, *((secret.result_entity_id,) if secret.result_entity_id is not None else ()))
    await scope.session.flush()
    verb = "broken open" if command.release else "laid bare"
    return Effect(f"The secret of {place.name} was {verb}.", place.id, created_ids=created)


@player_action("place:secret_delete", ActionKind.OTHER)
async def delete_secret(scope: PlayerScope, command: SecretTarget) -> Effect:
    secret = await _secret(scope, command.secret_id)
    place = await _place(scope, secret.place_entity_id)
    await scope.session.delete(secret)
    return Effect(f"The secret of {place.name} is gone from the world.", target_node_id=place.id)


@player_action("pilgrimage:clear", ActionKind.OTHER)
async def clear_pilgrimage_site(scope: PlayerScope, command: SiteTarget) -> Effect:
    site = await guards.canon_entity(scope.session, command.entity_id, "The site")
    if not await remove_flag(scope.session, site.id, EntityFlag.PILGRIMAGE_SITE):
        raise ValidationFailedError(f"{site.name} is not a pilgrimage site.")
    return Effect(f"{site.name} is no longer a pilgrimage site.", target_node_id=site.id)
