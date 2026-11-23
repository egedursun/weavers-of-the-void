from pydantic import Field

from aerona.catalog.transmission import ROUTES
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.demography import AgeBand
from aerona.engine.disease import control
from aerona.engine.disease.control import DiseaseDesign, ProfileValue
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 120


class Loose(Command):
    target_id: int
    disease_id: int | None = None
    severity: int = Field(default=60, ge=1, le=100)
    son_id: int | None = None


class CreateDisease(Command):
    region_id: int
    name: str | None = Field(default=None, min_length=2, max_length=NAME_MAX)
    values: dict[str, ProfileValue] = Field(default_factory=dict)
    hold: bool = True
    loose_on: int | None = None
    severity: int = Field(default=60, ge=1, le=100)


class EditDisease(Command):
    disease_id: int
    values: dict[str, ProfileValue] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)
    hold: bool = True


class CureTarget(Command):
    disease_id: int
    community_id: int
    revoke: bool = False


class Quarantine(Command):
    region_id: int
    epochs: int | None = Field(default=None, ge=0, le=1000)


class Immunity(Command):
    community_id: int
    disease_id: int
    immune_pct: int = Field(default=100, ge=0, le=100)
    age_band: AgeBand | None = None
    hold: bool | None = None
    forget: bool = False


class OutbreakTarget(Command):
    outbreak_id: int


class EditOutbreak(Command):
    outbreak_id: int
    values: dict[str, int | str | bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)
    hold: bool = True


class Endemic(Command):
    region_id: int
    disease_id: int
    load: int = Field(default=20, ge=1, le=100)
    hold: bool | None = None


class Route(Command):
    disease_id: int
    route: Transmission
    share: int = Field(default=20, ge=1, le=99)
    hold: bool | None = None


class RouteTarget(Command):
    disease_id: int
    route: Transmission


class EndemicTarget(Command):
    region_id: int
    disease_id: int


@player_action("disease:loose", ActionKind.CURSE)
async def loose(scope: PlayerScope, command: Loose) -> Effect:
    disease, event = await control.loose(
        await scope.context("disease_loose"), command.target_id, disease_id=command.disease_id, severity=command.severity, son_id=command.son_id
    )
    created = (disease.id, event.id) if command.disease_id is None else (event.id,)
    return Effect(f"{disease.name.capitalize()} was loosed.", command.target_id, created_ids=created)


@player_action("disease:create", ActionKind.CREATE_ENTITY)
async def create_disease(scope: PlayerScope, command: CreateDisease) -> Effect:
    ctx = await scope.context("disease_create")
    design = DiseaseDesign(name=command.name, values=command.values, hold=command.hold)
    if command.loose_on is not None:
        disease, event = await control.loose(ctx, command.loose_on, disease_id=None, severity=command.severity, son_id=None, design=design)
        return Effect(f"{disease.name.capitalize()} was forged and loosed.", disease.id, created_ids=(disease.id, event.id))
    disease = await control.create_disease(ctx, command.region_id, design, son_id=None)
    return Effect(f"{disease.name.capitalize()} was forged.", disease.id, created_ids=(disease.id,))


@player_action("disease:edit", ActionKind.EDIT_RECORD)
async def edit_disease(scope: PlayerScope, command: EditDisease) -> Effect:
    profile = await control.edit_disease(await scope.context("disease_edit"), command.disease_id, command.values, release=command.release, hold=command.hold)
    if command.release and not command.values:
        return Effect(f"The disease is free to change again: {', '.join(item.replace('_', ' ') for item in command.release)}.", command.disease_id)
    return Effect(f"The disease now spreads at {profile.virulence} and kills at {profile.lethality}.", command.disease_id)


@player_action("disease:cure", ActionKind.OTHER)
async def cure(scope: PlayerScope, command: CureTarget) -> Effect:
    ctx = await scope.context("disease_cure")
    if command.revoke:
        await control.revoke_cure(ctx, command.disease_id, command.community_id)
        return Effect("The cure is forgotten there.", command.community_id)
    await control.cure(ctx, command.disease_id, command.community_id)
    return Effect("The healers there now know the cure.", command.community_id)


@player_action("disease:quarantine", ActionKind.OTHER)
async def quarantine(scope: PlayerScope, command: Quarantine) -> Effect:
    row = await control.quarantine(await scope.context("disease_quarantine"), command.region_id, epochs=command.epochs, son_id=None)
    if row is None:
        return Effect("The quarantine is lifted.", command.region_id)
    return Effect(f"The land is sealed until epoch {row.until_epoch}.", command.region_id)


@player_action("disease:immunity", ActionKind.BLESS_STAT)
async def immunity(scope: PlayerScope, command: Immunity) -> Effect:
    ctx = await scope.context("disease_immunity")
    if command.forget:
        removed = await control.forget_immunity(ctx, command.community_id, command.disease_id, command.age_band)
        return Effect(f"The community forgot its resistance ({removed} age bands).", command.community_id)
    held = await control.grant_immunity(ctx, command.community_id, command.disease_id, command.immune_pct, band=command.age_band, hold=command.hold)
    who = f"{command.age_band.value}s" if command.age_band is not None else "community"
    return Effect(f"{held}% of the {who} now resist the disease.", command.community_id)


@player_action("outbreak:end", ActionKind.OTHER)
async def end_outbreak(scope: PlayerScope, command: OutbreakTarget) -> Effect:
    row = await control.end_outbreak(await scope.context("outbreak_end"), command.outbreak_id)
    return Effect("The outbreak ended on its own.", row.region_entity_id)


@player_action("outbreak:edit", ActionKind.EDIT_RECORD)
async def edit_outbreak(scope: PlayerScope, command: EditOutbreak) -> Effect:
    row = await control.edit_outbreak(await scope.context("outbreak_edit"), command.outbreak_id, command.values, release=command.release, hold=command.hold)
    return Effect(f"The outbreak now stands at {row.severity}, {row.infected} sick and {row.dead} dead.", row.region_entity_id)


@player_action("endemic:set", ActionKind.EDIT_RECORD)
async def set_endemic(scope: PlayerScope, command: Endemic) -> Effect:
    row = await control.set_endemic(await scope.context("endemic_set"), command.region_id, command.disease_id, command.load, hold=command.hold)
    return Effect(f"The sickness now lingers in the land at load {row.load}.", command.region_id)


@player_action("endemic:remove", ActionKind.EDIT_RECORD)
async def remove_endemic(scope: PlayerScope, command: EndemicTarget) -> Effect:
    removed = await control.remove_endemic(await scope.context("endemic_remove"), command.region_id, command.disease_id)
    return Effect("The land is free of the sickness." if removed else "The sickness did not linger there.", command.region_id)


@player_action("disease_route:set", ActionKind.EDIT_RECORD)
async def set_route(scope: PlayerScope, command: Route) -> Effect:
    row = await control.set_route(await scope.context("disease_route_set"), command.disease_id, command.route, command.share, hold=command.hold)
    return Effect(f"The sickness now passes by {ROUTES[row.route].label} for {row.share}% of its spread.", command.disease_id)


@player_action("disease_route:remove", ActionKind.EDIT_RECORD)
async def remove_route(scope: PlayerScope, command: RouteTarget) -> Effect:
    removed = await control.remove_route(await scope.context("disease_route_remove"), command.disease_id, command.route)
    return Effect("The sickness no longer passes that way." if removed else "The sickness never passed that way.", command.disease_id)
