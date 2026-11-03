from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.engine.disease import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Loose(Command):
    target_id: int
    disease_id: int | None = None
    severity: int = Field(default=60, ge=1, le=100)
    son_id: int | None = None


class EditDisease(Command):
    disease_id: int
    values: dict[str, int | str] = Field(default_factory=dict)


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


class OutbreakTarget(Command):
    outbreak_id: int


@player_action("disease:loose", ActionKind.CURSE)
async def loose(scope: PlayerScope, command: Loose) -> Effect:
    disease, event = await control.loose(
        await scope.context("disease_loose"), command.target_id, disease_id=command.disease_id, severity=command.severity, son_id=command.son_id
    )
    created = (disease.id, event.id) if command.disease_id is None else (event.id,)
    return Effect(f"{disease.name.capitalize()} was loosed.", command.target_id, created_ids=created)


@player_action("disease:edit", ActionKind.EDIT_RECORD)
async def edit_disease(scope: PlayerScope, command: EditDisease) -> Effect:
    profile = await control.edit_disease(await scope.context("disease_edit"), command.disease_id, command.values)
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
    held = await control.grant_immunity(await scope.context("disease_immunity"), command.community_id, command.disease_id, command.immune_pct)
    return Effect(f"{held}% of the community now resists the disease.", command.community_id)


@player_action("outbreak:end", ActionKind.OTHER)
async def end_outbreak(scope: PlayerScope, command: OutbreakTarget) -> Effect:
    row = await control.end_outbreak(await scope.context("outbreak_end"), command.outbreak_id)
    return Effect("The outbreak burned itself out.", row.region_entity_id)
