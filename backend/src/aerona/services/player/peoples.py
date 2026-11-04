from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import AgeBand, CohortCondition
from aerona.domain.enums.society import SocialClass
from aerona.engine.demography import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MIN = 2


ProfileValue = int | str | bool | list[int] | list[str] | None


class EditPeople(Command):
    people_id: int
    values: dict[str, ProfileValue] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class FoundPeople(Command):
    name: str = Field(min_length=NAME_MIN, max_length=NAME_MAX_LENGTH)
    region_id: int
    population: int = Field(ge=1)
    species_id: int | None = None
    language_id: int | None = None
    values: dict[str, ProfileValue] = Field(default_factory=dict)


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


@player_action("people:found", ActionKind.CREATE_ENTITY)
async def found_people(scope: PlayerScope, command: FoundPeople) -> Effect:
    founded = await control.found_people(
        await scope.context("people_found"),
        name=command.name,
        region_id=command.region_id,
        population=command.population,
        species_id=command.species_id,
        language_id=command.language_id,
        values=command.values,
    )
    return Effect(f"{founded.name} rose as a new people, {command.population} strong.", founded.id, created_ids=(founded.id,))


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
