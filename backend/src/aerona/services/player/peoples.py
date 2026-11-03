from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import AgeBand, CohortCondition
from aerona.domain.enums.society import SocialClass
from aerona.engine.demography import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditPeople(Command):
    people_id: int
    values: dict[str, int | str | bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class MoveCohort(Command):
    community_id: int
    count: int = Field(ge=1)
    source: SocialClass
    target: SocialClass
    band: AgeBand | None = None
    condition: CohortCondition | None = None


@player_action("people:edit", ActionKind.EDIT_RECORD)
async def edit_people(scope: PlayerScope, command: EditPeople) -> Effect:
    biology, culture = await control.edit_people(await scope.context("people_edit"), command.people_id, command.values, release=command.release)
    return Effect(
        f"The people come of age at {biology.maturity_years}, fight as {culture.martial_style.value.replace('_', ' ')}, cohesion {culture.cohesion}.",
        command.people_id,
    )


@player_action("cohort:move", ActionKind.EDIT_RECORD)
async def move_cohort(scope: PlayerScope, command: MoveCohort) -> Effect:
    moved = await control.move_cohort(
        await scope.context("cohort_move"),
        command.community_id,
        count=command.count,
        source=command.source,
        target=command.target,
        band=command.band,
        condition=command.condition,
    )
    return Effect(
        f"{moved} {command.source.value.replace('_', ' ')}s became {command.target.value.replace('_', ' ')}s.", command.community_id, values={"moved": moved}
    )
