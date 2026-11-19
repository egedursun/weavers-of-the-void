from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.facets import FacetPracticeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import FuneralCustom, InheritanceCustom, MartialStyle
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.demography import control
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, require_essence

FIELD_WORDS = {
    "martial_style": "way of war",
    "ornament": "ornament",
    "geometry": "geometric form",
    "colour": "colour",
    "scale": "scale",
    "symmetry": "symmetry",
    "funeral_rite": "funeral rite",
    "remains_treatment": "treatment of the dead",
    "inheritance": "inheritance",
    "diet": "diet",
}


class ShapeFolkInput(ToolInput):
    people_id: int
    martial_style: MartialStyle | None = None
    ornament: Annotated[int, Field(ge=0, le=100)] | None = None
    geometry: Annotated[int, Field(ge=0, le=100)] | None = None
    colour: Annotated[int, Field(ge=0, le=100)] | None = None
    scale: Annotated[int, Field(ge=0, le=100)] | None = None
    symmetry: Annotated[int, Field(ge=0, le=100)] | None = None
    funeral_rite: FuneralCustom | None = None
    remains_treatment: RemainsTreatment | None = None
    inheritance: InheritanceCustom | None = None
    diet: Diet | None = None
    practice: FacetKind | None = None
    practice_level: Annotated[int, Field(ge=0, le=100)] | None = None
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


def chosen(args: ShapeFolkInput) -> dict[str, str | bool | int]:
    found: dict[str, str | bool | int] = {}
    for key in FIELD_WORDS:
        value = getattr(args, key)
        if value is not None:
            found[key] = value if isinstance(value, (bool, int)) else str(value)
    return found


def change_text(key: str, value: str | bool | int) -> str:
    if isinstance(value, bool):
        return f"{FIELD_WORDS[key]} {'yes' if value else 'no'}"
    if isinstance(value, int):
        return f"{FIELD_WORDS[key]} {value} of 100"
    return f"{FIELD_WORDS[key]} {value.replace('_', ' ')}"


async def keep_practice(call: SonCall, community_id: int, practice: FacetKind, level: int) -> None:
    row = await call.session.scalar(select(FacetPracticeRow).where(FacetPracticeRow.community_entity_id == community_id, FacetPracticeRow.facet == practice))
    if row is None:
        row = FacetPracticeRow(community_entity_id=community_id, facet=practice, since_epoch=call.tick.epoch, locked=[])
        call.session.add(row)
    row.level, row.updated_epoch = level, call.tick.epoch
    await call.session.flush()


async def shape_folk(call: SonCall, args: ShapeFolkInput) -> str:
    table = call.rules.customs
    people = await require_canon(call.session, args.people_id)
    require_type(people, {EntityType.PEOPLE}, SonResult.FOLK_NOT_PEOPLE)
    await ensure_in_reach(call, people)
    if await BondRepository(call.session).patron(people.id) != call.son.id:
        fail(SonResult.FOLK_NOT_YOURS, name=people.name)
    values = chosen(args)
    practice = args.practice if args.practice is not None and args.practice_level is not None else None
    if not values and practice is None:
        fail(SonResult.FOLK_NOTHING)
    cost = table.son_shape_essence * (len(values) + (1 if practice is not None else 0))
    require_essence(call, cost)
    if values:
        await control.edit_people(call.tick, people.id, values, release=[])
    shaped = [change_text(key, value) for key, value in values.items()]
    if practice is not None and args.practice_level is not None:
        await keep_practice(call, people.id, practice, args.practice_level)
        shaped.append(f"practice of {spoken(practice)} {args.practice_level} of 100")
    call.spend_essence(cost)
    call.target(people.id)
    changes = ", ".join(shaped)
    await call.record(
        "tools.son.shape_folk",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: people.id},
        facts={"changes": str(changes), "reason": str(args.reason)},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.FOLK_SHAPED, name=people.name, changes=changes)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.SHAPE_FOLK,
            AgentKind.SON,
            ShapeFolkInput,
            ToolMeta(
                ActionKind.INFLUENCE,
                lambda rules: rules.customs.son_shape_ap,
                essence_cost=lambda rules: rules.customs.son_shape_essence,
                rarity_gate=gate(Gate.INFLUENCE_TOOLS),
            ),
            shape_folk,
        )
    ]
