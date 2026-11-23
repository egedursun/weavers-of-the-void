from pydantic import BaseModel, Field

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.demography import wills
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class WillShare(BaseModel):
    heir_id: int
    share: int = Field(ge=1, le=100)


class SetWill(Command):
    testator_id: int
    heirs: list[WillShare] = Field(min_length=1)
    witnesses: list[int] = Field(default_factory=list)
    forged: bool = False
    hold: bool | None = None


class WillTarget(Command):
    testator_id: int


async def testator(scope: PlayerScope, testator_id: int) -> EntityRow:
    mortal = await scope.session.get(EntityRow, testator_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal makes a will.")
    return mortal


@player_action("will:set", ActionKind.EDIT_RECORD)
async def set_will(scope: PlayerScope, command: SetWill) -> Effect:
    mortal = await testator(scope, command.testator_id)
    ctx = await scope.context("will_set")
    will = await wills.make_will(
        ctx, mortal, [(line.heir_id, line.share) for line in command.heirs], witnesses=command.witnesses, forged=command.forged, hold=command.hold
    )
    heirs = await wills.heirs_of_will(scope.session, will.id)
    return Effect(f"{mortal.name}'s will now names {several(len(heirs), 'heir', 'heirs')}.", mortal.id)


@player_action("will:remove", ActionKind.EDIT_RECORD)
async def remove_will(scope: PlayerScope, command: WillTarget) -> Effect:
    mortal = await testator(scope, command.testator_id)
    removed = await wills.remove_will(await scope.context("will_remove"), mortal.id)
    return Effect(f"{mortal.name}'s will is torn up." if removed else f"{mortal.name} had made no will.", mortal.id)
