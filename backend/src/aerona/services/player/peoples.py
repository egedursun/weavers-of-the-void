from pydantic import Field

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
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
    from_condition: CohortCondition | None = None


class SetCohort(Command):
    community_id: int
    age_band: AgeBand
    sex: Sex
    social_class: SocialClass
    condition: CohortCondition = CohortCondition.NONE
    count: int = Field(ge=0, le=10**9)


class Dormancy(Command):
    mortal_id: int
    dormant: bool | None = None
    hold: bool | None = None


@player_action("people:edit", ActionKind.EDIT_RECORD)
async def edit_people(scope: PlayerScope, command: EditPeople) -> Effect:
    biology, culture = await control.edit_people(await scope.context("people_edit"), command.people_id, command.values, release=command.release)
    return Effect(
        f"The people come of age at {biology.maturity_years}, fight as {spoken(culture.martial_style)}, cohesion {culture.cohesion}.",
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
        from_condition=command.from_condition,
    )
    return Effect(f"{moved} {spoken(command.source)}s became {spoken(command.target)}s.", command.community_id, values={"moved": moved})


@player_action("cohort:set", ActionKind.EDIT_RECORD)
async def set_cohort(scope: PlayerScope, command: SetCohort) -> Effect:
    key = (command.age_band, command.sex, command.social_class, command.condition)
    total = await control.set_cohort(await scope.context("cohort_set"), command.community_id, key, command.count)
    label = " ".join(part.value.replace("_", " ") for part in key)
    return Effect(f"The {label} now number {command.count}; the community holds {total}.", command.community_id, values={"population": total})


@player_action("mortal:dormancy", ActionKind.EDIT_RECORD)
async def set_dormancy(scope: PlayerScope, command: Dormancy) -> Effect:
    asleep = await control.set_dormancy(await scope.context("mortal_dormancy"), command.mortal_id, dormant=command.dormant, hold=command.hold)
    state = "sleeps through the ages" if asleep else "is awake to the world"
    held = {True: "; the engine will keep it so", False: "; the engine may change it again", None: ""}[command.hold]
    return Effect(f"The mortal {state}{held}.", command.mortal_id, values={"dormant": asleep})
