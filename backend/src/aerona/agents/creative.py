from dataclasses import dataclass
from typing import Protocol

from aerona.agents.awakening import awaken_peoples
from aerona.agents.bard import write_son_epic
from aerona.agents.deepener import creator_deepen, creator_epic, deepen_foreign_god, refresh_awakened_god
from aerona.agents.genesis import creator_portrait
from aerona.agents.mortal import run_mortal_turn
from aerona.agents.revelation import reveal
from aerona.agents.runtime import AgentRuntime
from aerona.agents.summoner import birth_child, summon_son
from aerona.agents.world_birth import BirthPlan, birth_world
from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import StarType, WorldType
from aerona.domain.models.son_design import SonDesign

CREATOR_PORTRAIT = "creator_portrait"
CREATOR_EPIC = "creator_epic"
CREATOR_DEEPEN = "creator_deepen"
SON_EPIC = "son_epic"
FOREIGN_GOD_DEEPEN = "foreign_god_deepen"
FOREIGN_GOD_AWAKENED = "foreign_god_awakened"


class RevelationOrder(Protocol):
    @property
    def content(self) -> str: ...

    @property
    def entity_type(self) -> str | None: ...

    @property
    def world_id(self) -> int | None: ...

    @property
    def mechanic(self) -> str | None: ...


class WorldOrder(Protocol):
    @property
    def world_type(self) -> WorldType | None: ...

    @property
    def inspiration(self) -> str: ...

    @property
    def star_id(self) -> int | None: ...

    @property
    def parent_world_id(self) -> int | None: ...

    @property
    def new_star(self) -> bool: ...

    @property
    def new_star_type(self) -> StarType | None: ...

    @property
    def galaxy_id(self) -> int | None: ...


class ContentOrder(Protocol):
    @property
    def kind(self) -> str: ...

    @property
    def target_id(self) -> int | None: ...


def parse[E: (EntityType, NaturalLaw)](enum: type[E], value: str | None, label: str) -> E | None:
    if value is None or not value.strip():
        return None
    try:
        return enum(value.strip())
    except ValueError as error:
        raise ValidationFailedError(f"Unknown {label}: {value}.") from error


class AgentSonSummoner:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def summon(self, world_id: int | None, design: SonDesign | None = None) -> int:
        return (await summon_son(self._runtime, world_id, design=design)).id

    async def birth(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> int:
        return (await birth_child(self._runtime, parent_son_id, inspiration or None, co_parent_son_id)).id


class AgentMortalActor:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def act(self, entity_id: int) -> str:
        return (await run_mortal_turn(self._runtime, entity_id)).word


class AgentRevelationAuthor:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def reveal(self, request: RevelationOrder) -> int:
        entity = await reveal(
            self._runtime,
            request.content,
            parse(EntityType, request.entity_type, "record type"),
            request.world_id,
            parse(NaturalLaw, request.mechanic, "law mechanic"),
        )
        return entity.id


class AgentWorldMaker:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def create(self, request: WorldOrder) -> int:
        plan = BirthPlan(
            world_type=request.world_type,
            inspiration=request.inspiration or None,
            star_id=request.star_id,
            parent_world_id=request.parent_world_id,
            new_star=request.new_star,
            new_star_type=request.new_star_type,
            galaxy_id=request.galaxy_id,
        )
        return (await birth_world(self._runtime, plan)).id


class AgentPeopleAwakener:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def awaken(self, count: int, world_id: int | None) -> list[int]:
        return await awaken_peoples(self._runtime, count, world_id)


class AgentContentWriter:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def write(self, job: ContentOrder) -> str:
        kind = str(job.kind)
        if kind == CREATOR_PORTRAIT:
            return (await creator_portrait(self._runtime)).title
        if kind == CREATOR_EPIC:
            return (await creator_epic(self._runtime)).title
        if kind == CREATOR_DEEPEN:
            return (await creator_deepen(self._runtime)).desire
        if kind == SON_EPIC and job.target_id is not None:
            return (await write_son_epic(self._runtime, job.target_id)).title
        if kind == FOREIGN_GOD_DEEPEN and job.target_id is not None:
            return (await deepen_foreign_god(self._runtime, job.target_id)).history
        if kind == FOREIGN_GOD_AWAKENED and job.target_id is not None:
            return (await refresh_awakened_god(self._runtime, job.target_id)).history
        raise ValidationFailedError(f"Unknown content job: {kind}.")


@dataclass(frozen=True)
class AgentCreativePorts:
    summoner: AgentSonSummoner
    revelations: AgentRevelationAuthor
    worlds: AgentWorldMaker
    awakener: AgentPeopleAwakener
    writer: AgentContentWriter
    mortals: AgentMortalActor


def agent_creative_ports(runtime: AgentRuntime) -> AgentCreativePorts:
    return AgentCreativePorts(
        summoner=AgentSonSummoner(runtime),
        revelations=AgentRevelationAuthor(runtime),
        worlds=AgentWorldMaker(runtime),
        awakener=AgentPeopleAwakener(runtime),
        writer=AgentContentWriter(runtime),
        mortals=AgentMortalActor(runtime),
    )
