from sqlalchemy import select

from aerona.cartography.terrain import default_terrain
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import agree, an, several, spoken
from aerona.db.repositories.names import NameRepository, normalize_name
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world import Atmosphere, Discovery, Gravity, WorldType
from aerona.engine.cosmos.orbits import match_air, match_gravity, match_kind
from aerona.engine.cosmos.world_types import mechanics_of
from aerona.engine.cosmos.worlds import forget_world, set_mirror_twin
from aerona.engine.primitives.renames import rewrite_name
from aerona.engine.recording.record import record
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

TEXT_FIELDS = ("cosmology", "description", "image_prompt")


class EditWorld(Command):
    world_id: int
    name: str | None = None
    cosmology: str | None = None
    description: str | None = None
    image_prompt: str | None = None
    world_type: WorldType | None = None
    gravity: Gravity | None = None
    atmosphere: Atmosphere | None = None
    time_factor: float | None = None
    leakage: int | None = None
    mortal_agents: int | None = None
    automatic_mortal_agents: bool = False
    guardian_son_id: int | None = None
    mirror_twin_id: int | None = None
    discovery: Discovery | None = None
    terrain_seed: str | None = None
    sea_pct: int | None = None
    mountains_pct: int | None = None
    moisture_pct: int | None = None


async def _rename(scope: PlayerScope, world: WorldRow, requested: str) -> str | None:
    name = requested.strip()
    if not name:
        raise ValidationFailedError("A world's name cannot be empty.")
    if normalize_name(name) == normalize_name(world.name):
        return None
    names = NameRepository(scope.session)
    if await names.is_taken(name, ignore_node_id=world.id):
        raise ValidationFailedError(f'"{name}" is already used in the cosmos; choose another name.')
    old = world.name
    await names.rename(world.id, name)
    await rewrite_name(scope.session, world.id, old, world.name)
    return old


def _percent_field(value: int, low: int, label: str) -> float:
    if not low <= value <= PERCENT_MAX:
        raise ValidationFailedError(f"{label} must be between {low} and {PERCENT_MAX}.")
    return value / PERCENT


def _terrain(world: WorldRow, command: EditWorld, notes: list[str]) -> None:
    if command.terrain_seed is not None:
        seed = command.terrain_seed.strip()
        if not seed:
            raise ValidationFailedError("The terrain seed cannot be empty.")
        world.terrain_seed = seed
        notes.append(f"terrain seed {seed}")
    if command.sea_pct is not None:
        world.terrain_sea = _percent_field(command.sea_pct, PERCENT_MIN, "Sea")
        notes.append(f"sea {command.sea_pct}%")
    if command.mountains_pct is not None:
        world.terrain_mountains = _percent_field(command.mountains_pct, PERCENT_MIN, "Mountains")
        notes.append(f"mountains {command.mountains_pct}%")
    if command.moisture_pct is not None:
        world.terrain_humidity = _percent_field(command.moisture_pct, -PERCENT_MAX, "Moisture")
        notes.append(f"moisture {command.moisture_pct}%")


def _physics(scope: PlayerScope, world: WorldRow, command: EditWorld, notes: list[str]) -> None:
    if command.world_type is not None and command.world_type is not world.world_type:
        world.world_type = command.world_type
        terrain = default_terrain(command.world_type, scope.rules)
        world.terrain_sea = (terrain.sea_pct or 0) / PERCENT
        world.terrain_mountains = (terrain.mountains_pct or 0) / PERCENT
        world.terrain_humidity = max(-1.0, min(1.0, (terrain.moisture_pct or 0) / PERCENT))
        notes.append(f"it became {an(WORLD_TYPES[command.world_type].label.lower())}")
        mechanics = mechanics_of(command.world_type)
        if mechanics.forced_gravity is not None and command.gravity is None:
            world.gravity = mechanics.forced_gravity
            notes.append(f"its nature set gravity {spoken(mechanics.forced_gravity)}")
        if mechanics.forced_atmosphere is not None and command.atmosphere is None:
            world.atmosphere = mechanics.forced_atmosphere
            notes.append(f"its nature set atmosphere {spoken(mechanics.forced_atmosphere)}")
    _terrain(world, command, notes)
    if command.gravity is not None:
        world.gravity = command.gravity
        notes.append(f"gravity {command.gravity.value}")
    if command.atmosphere is not None:
        world.atmosphere = command.atmosphere
        notes.append(f"atmosphere {command.atmosphere.value}")
    if command.time_factor is not None:
        if command.time_factor <= 0:
            raise ValidationFailedError("Time factor must be greater than zero (1 normal flow; 2 twice as fast, 0.5 half as fast).")
        world.time_factor = command.time_factor
        notes.append(f"time flows x{command.time_factor:g}")
    if command.leakage is not None:
        if not PERCENT_MIN <= command.leakage <= PERCENT_MAX:
            raise ValidationFailedError("Leak must be between 0 and 100.")
        world.leakage = command.leakage
        notes.append(f"leak {command.leakage}")


def _agents(scope: PlayerScope, world: WorldRow, command: EditWorld, notes: list[str]) -> None:
    if command.automatic_mortal_agents:
        world.mortal_agents = None
        notes.append("mortal agents chosen automatically")
        return
    if command.mortal_agents is None:
        return
    cap = scope.rules.god_hand.mortal_agents_per_world_cap
    if not 0 <= command.mortal_agents <= cap:
        raise ValidationFailedError(f"At most {cap} mortal agents per world per epoch (world rule god_hand.mortal_agents_per_world_cap).")
    world.mortal_agents = command.mortal_agents
    notes.append(f"{command.mortal_agents} mortal agents each epoch")


async def _body(scope: PlayerScope, world: WorldRow, command: EditWorld) -> None:
    physics = await scope.session.get(WorldPhysicsRow, world.id)
    if physics is None:
        return
    if command.world_type is not None:
        star_id = await WorldRepository(scope.session).root_star_id(world)
        star = await scope.session.get(StarRow, star_id) if star_id is not None else None
        match_kind(scope.rules, world, physics, star)
    if command.world_type is not None or command.gravity is not None:
        match_gravity(physics, world.gravity)
    if command.world_type is not None or command.atmosphere is not None:
        match_air(physics, world.atmosphere)


async def _discovery(scope: PlayerScope, world: WorldRow, discovery: Discovery, notes: list[str]) -> None:
    if discovery is world.discovery:
        return
    if discovery is Discovery.FORGOTTEN:
        creator = await scope.creator()
        ctx = await scope.context("forget_world")
        await forget_world(ctx, world.id, creator.id)
        notes.append("it was forgotten")
        return
    remembered = world.discovery is Discovery.FORGOTTEN
    reopened = await WorldRepository(scope.session).set_discovery(world, discovery)
    if not remembered:
        notes.append(f"it is now {spoken(discovery)}")
        return
    closed = await scope.session.scalars(
        select(RouteRow.id).where(((RouteRow.world_a_id == world.id) | (RouteRow.world_b_id == world.id)) & RouteRow.active.is_(False))
    )
    still = len(list(closed))
    note = "was remembered again"
    if reopened:
        note += f"; {several(len(reopened), 'road', 'roads')} closed during forgetting {agree(len(reopened), 'was', 'were')} reopened"
    if still:
        note += (
            f"; {several(still, 'road', 'roads')} {agree(still, 'remains', 'remain')} closed "
            "(closed for another reason or the other end is forgotten; reopen with Open road if needed)"
        )
    notes.append(note)


def _edit_kind(remembered: bool, discovery: Discovery | None) -> ActionKind:
    if remembered:
        return ActionKind.REMEMBER_WORLD
    return ActionKind.FORGET_WORLD if discovery is Discovery.FORGOTTEN else ActionKind.EDIT_RECORD


@player_action("world:edit", ActionKind.EDIT_RECORD)
async def edit_world(scope: PlayerScope, command: EditWorld) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    ctx = await scope.context("edit_world")
    notes: list[str] = []
    messages: list[str] = []
    if command.name is not None:
        old = await _rename(scope, world, command.name)
        if old is not None:
            messages.append(
                (
                    await record(
                        ctx,
                        "player.world.renamed",
                        roles={IncidentRole.SUBJECT: world.id},
                        facts={"old": old},
                        kind=ChronicleKind.CREATOR_HAND,
                        world_id=world.id,
                    )
                ).text
            )
    for field in TEXT_FIELDS:
        value = getattr(command, field)
        if value is not None:
            setattr(world, field, value.strip() or None)
            notes.append(f"{field.replace('_', ' ')} rewritten")
    _physics(scope, world, command, notes)
    await _body(scope, world, command)
    _agents(scope, world, command, notes)
    if command.guardian_son_id is not None and command.guardian_son_id != world.patron_son_id:
        guardian = await guards.son(scope.session, command.guardian_son_id)
        world.patron_son_id = guardian.id
        world.patron_automatic = False
        notes.append(f"{guardian.name} guards it")
    if command.mirror_twin_id is not None and command.mirror_twin_id != world.mirror_twin_id:
        await set_mirror_twin(scope.session, world.id, command.mirror_twin_id)
        notes.append("its mirror twin changed")
    remembered = world.discovery is Discovery.FORGOTTEN and command.discovery not in (None, Discovery.FORGOTTEN)
    if command.discovery is not None:
        await _discovery(scope, world, command.discovery, notes)
    if not notes and not messages:
        raise ValidationFailedError(f"Nothing to change in {world.name}.")
    cosmos = await scope.cosmos()
    cosmos.map_version += 1
    if notes:
        detail = f": {'; '.join(notes)}"
        kind = _edit_kind(remembered, command.discovery)
        messages.append(
            (
                await record(
                    ctx,
                    "player.world.reshaped",
                    roles={IncidentRole.SUBJECT: world.id},
                    facts={"notes": detail},
                    kind=ChronicleKind.CREATOR_HAND,
                    world_id=world.id,
                )
            ).text
        )
        return Effect(" ".join(messages), world.id, kind=kind)
    return Effect(" ".join(messages), world.id)
