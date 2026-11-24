from sqlalchemy import or_, select

from aerona.catalog.strata import STRATA
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import DeepPassageRow, PolityDeepKnowledgeRow, RegionStratumRow
from aerona.domain.enums.action import ActionKind
from aerona.services.player.record_rows import CreateRow, EditRow, RowTarget, make_row, reshape_row, unmake_row
from aerona.services.player.scope import Effect, PlayerScope, player_action

CELLS = "region_underground"
PASSAGES = "deep_passages"
KNOWLEDGE = "polity_deep_knowledge"


def same(table: str, expected: str) -> None:
    if table != expected:
        raise ValidationFailedError(f"This lever shapes {expected.replace('_', ' ')}, not {table.replace('_', ' ')}.")


@player_action("deep_cell:create", ActionKind.EDIT_RECORD)
async def create_cell(scope: PlayerScope, command: CreateRow) -> Effect:
    same(command.table, CELLS)
    return await make_row(scope, command)


@player_action("deep_cell:edit", ActionKind.EDIT_RECORD)
async def edit_cell(scope: PlayerScope, command: EditRow) -> Effect:
    same(command.table, CELLS)
    return await reshape_row(scope, command)


@player_action("deep_cell:hold", ActionKind.EDIT_RECORD)
async def hold_cell(scope: PlayerScope, command: EditRow) -> Effect:
    same(command.table, CELLS)
    return await reshape_row(scope, command.model_copy(update={"hold": True}))


@player_action("deep_cell:delete", ActionKind.EDIT_RECORD)
async def delete_cell(scope: PlayerScope, command: RowTarget) -> Effect:
    same(command.table, CELLS)
    cell = await scope.session.get(RegionStratumRow, command.key.get("id"))
    if cell is None:
        raise ValidationFailedError("No such cell.")
    order = list(STRATA)
    above = None
    rows = {row.stratum: row for row in await scope.session.scalars(select(RegionStratumRow).where(RegionStratumRow.region_entity_id == cell.region_entity_id))}
    for stratum in reversed(order[: order.index(cell.stratum)]):
        if stratum in rows and STRATA[stratum].dwellable:
            above = stratum
            break
    for entity in await scope.session.scalars(select(EntityRow).where(EntityRow.location_id == cell.region_entity_id, EntityRow.stratum == cell.stratum)):
        entity.stratum = above
    for passage in await scope.session.scalars(
        select(DeepPassageRow).where(
            or_(
                (DeepPassageRow.first_region_entity_id == cell.region_entity_id) & (DeepPassageRow.first_stratum == cell.stratum),
                (DeepPassageRow.second_region_entity_id == cell.region_entity_id) & (DeepPassageRow.second_stratum == cell.stratum),
            )
        )
    ):
        await scope.session.delete(passage)
    return await unmake_row(scope, command)


@player_action("deep_passage:create", ActionKind.EDIT_RECORD)
async def create_passage(scope: PlayerScope, command: CreateRow) -> Effect:
    same(command.table, PASSAGES)
    return await make_row(scope, command)


@player_action("deep_passage:edit", ActionKind.EDIT_RECORD)
async def edit_passage(scope: PlayerScope, command: EditRow) -> Effect:
    same(command.table, PASSAGES)
    return await reshape_row(scope, command)


@player_action("deep_passage:hold", ActionKind.EDIT_RECORD)
async def hold_passage(scope: PlayerScope, command: EditRow) -> Effect:
    same(command.table, PASSAGES)
    return await reshape_row(scope, command.model_copy(update={"hold": True}))


@player_action("deep_passage:delete", ActionKind.EDIT_RECORD)
async def delete_passage(scope: PlayerScope, command: RowTarget) -> Effect:
    same(command.table, PASSAGES)
    return await unmake_row(scope, command)


@player_action("deep_knowledge:set", ActionKind.EDIT_RECORD)
async def set_knowledge(scope: PlayerScope, command: CreateRow) -> Effect:
    same(command.table, KNOWLEDGE)
    key = (command.values.get("polity_entity_id"), command.values.get("cell_id"))
    if await scope.session.get(PolityDeepKnowledgeRow, key) is None:
        return await make_row(scope, command)
    rest = {column: value for column, value in command.values.items() if column not in {"polity_entity_id", "cell_id"}}
    return await reshape_row(scope, EditRow(table=KNOWLEDGE, key={"polity_entity_id": key[0], "cell_id": key[1]}, values=rest))


@player_action("deep_knowledge:delete", ActionKind.EDIT_RECORD)
async def delete_knowledge(scope: PlayerScope, command: RowTarget) -> Effect:
    same(command.table, KNOWLEDGE)
    return await unmake_row(scope, command)
