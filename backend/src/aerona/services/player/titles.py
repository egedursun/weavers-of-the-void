from pydantic import Field
from sqlalchemy import delete

from aerona.catalog.titles import RANK_WORDS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.titles import TITLE_FIELDS, DeJureLinkRow, TitleProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.titles import TitleRank, TitleTenure
from aerona.domain.models.entity_stats import TitleStats
from aerona.engine.polity.titles import POWER, emblem_of, record_holder
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class CreateTitle(Command):
    rank: TitleRank
    name: str = Field(min_length=1, max_length=200)
    holder_id: int | None = None
    polity_id: int | None = None
    liege_id: int | None = None
    lands: list[int] = Field(default_factory=list)


class TitleTarget(Command):
    title_id: int


class EditTitle(Command):
    title_id: int
    rank: TitleRank | None = None
    liege_id: int | None = None
    clear_liege: bool = False
    polity_id: int | None = None
    capital_id: int | None = None
    succession_law_id: int | None = None
    emblem: str | None = Field(default=None, min_length=1, max_length=60)
    prestige: int | None = Field(default=None, ge=0, le=SPAN)
    regalia: list[int] | None = None
    hold: bool = True


class PassTitle(Command):
    title_id: int
    holder_id: int | None = None
    usurped: bool = False
    hold: bool = True


class SetDeJure(Command):
    title_id: int
    member_id: int
    hold: bool = True


class DeJureTarget(Command):
    title_id: int
    member_id: int


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def entity(scope: PlayerScope, entity_id: int | None, label: str, kinds: frozenset[EntityType] | None = None) -> EntityRow:
    found = await scope.session.get(EntityRow, entity_id) if entity_id is not None else None
    if found is None or (kinds is not None and found.entity_type not in kinds):
        raise ValidationFailedError(f"{label} is not the right kind of record.")
    return found


async def title(scope: PlayerScope, title_id: int) -> TitleProfileRow:
    row = await scope.session.get(TitleProfileRow, title_id)
    if row is None:
        raise NotFoundError("No such title.")
    return row


async def link(scope: PlayerScope, title_id: int, member_id: int, epoch: int, hold: bool) -> None:
    await scope.session.execute(delete(DeJureLinkRow).where(DeJureLinkRow.member_entity_id == member_id))
    scope.session.add(DeJureLinkRow(title_entity_id=title_id, member_entity_id=member_id, since_epoch=epoch, locked=hold))


@player_action("title:create", ActionKind.EDIT_RECORD)
async def create(scope: PlayerScope, command: CreateTitle) -> Effect:
    holder = await scope.session.get(NodeRow, command.holder_id) if command.holder_id is not None else None
    if command.holder_id is not None and holder is None:
        raise ValidationFailedError("The holder must be a living thing of the cosmos.")
    realm = await entity(scope, command.polity_id, "The realm", frozenset({EntityType.POLITY})) if command.polity_id is not None else None
    if command.liege_id is not None:
        await title(scope, command.liege_id)
    ctx = await manual_context(scope.session, "title.create")
    record = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TITLE,
            name=command.name,
            body=f"A {RANK_WORDS[command.rank].lower()} created by the Creator's word.",
            stats=TitleStats(prestige=SPAN // 4, territory=len(command.lands)),
            power=POWER,
            world_id=realm.world_id if realm is not None else None,
            subtype=RANK_WORDS[command.rank].lower(),
        ),
    )
    row = TitleProfileRow(
        title_entity_id=record.id,
        rank=command.rank,
        de_jure_liege_entity_id=command.liege_id,
        polity_entity_id=realm.id if realm is not None else None,
        emblem=emblem_of(ctx, seed_of("title.emblem", record.id)),
        prestige=SPAN // 4,
        regalia=[],
        drift={},
        created_epoch=ctx.epoch,
        locked=[],
    )
    scope.session.add(row)
    for land in command.lands:
        await entity(scope, land, "A de jure land", frozenset({EntityType.REGION}))
        await link(scope, record.id, land, ctx.epoch, False)
    await record_holder(ctx, row, command.holder_id, TitleTenure.CREATED)
    await scope.session.flush()
    return Effect(f"{command.name} now stands, a {RANK_WORDS[command.rank].lower()}.", target_node_id=record.id, values={"title_id": record.id})


@player_action("title:edit", ActionKind.EDIT_RECORD)
async def edit(scope: PlayerScope, command: EditTitle) -> Effect:
    row = await title(scope, command.title_id)
    touched: list[str] = []
    if command.rank is not None:
        row.rank = command.rank
        touched.append("rank")
    if command.liege_id is not None:
        if command.liege_id == row.title_entity_id:
            raise ValidationFailedError("A title cannot be its own liege.")
        await title(scope, command.liege_id)
        row.de_jure_liege_entity_id = command.liege_id
        touched.append("de_jure_liege_entity_id")
    elif command.clear_liege:
        row.de_jure_liege_entity_id = None
        touched.append("de_jure_liege_entity_id")
    if command.polity_id is not None:
        row.polity_entity_id = (await entity(scope, command.polity_id, "The realm", frozenset({EntityType.POLITY}))).id
        touched.append("polity_entity_id")
    if command.capital_id is not None:
        row.capital_entity_id = (await entity(scope, command.capital_id, "The capital", frozenset({EntityType.SETTLEMENT}))).id
        touched.append("capital_entity_id")
    if command.succession_law_id is not None:
        row.succession_law_entity_id = (await entity(scope, command.succession_law_id, "The law", frozenset({EntityType.LAW}))).id
        touched.append("succession_law_entity_id")
    if command.emblem is not None:
        row.emblem = command.emblem
        touched.append("emblem")
    if command.prestige is not None:
        row.prestige = command.prestige
        touched.append("prestige")
    if command.regalia is not None:
        row.regalia = sorted({(await entity(scope, item, "The regalia", frozenset({EntityType.ITEM}))).id for item in command.regalia})
        touched.append("regalia")
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"A {RANK_WORDS[row.rank].lower()} of prestige {row.prestige}, its arms {row.emblem}.", target_node_id=row.title_entity_id)


@player_action("title:hold", ActionKind.EDIT_RECORD)
async def hold_title(scope: PlayerScope, command: EditTitle) -> Effect:
    row = await title(scope, command.title_id)
    row.locked = held(row.locked, [*TITLE_FIELDS, "drift"], command.hold)
    await scope.session.flush()
    return Effect("The title is held against the world." if command.hold else "The title moves with the world again.", target_node_id=row.title_entity_id)


@player_action("title:grant", ActionKind.EDIT_RECORD)
async def grant(scope: PlayerScope, command: PassTitle) -> Effect:
    row = await title(scope, command.title_id)
    if command.holder_id is not None and await scope.session.get(NodeRow, command.holder_id) is None:
        raise ValidationFailedError("The holder must be a living thing of the cosmos.")
    ctx = await manual_context(scope.session, "title.grant")
    await record_holder(ctx, row, command.holder_id, TitleTenure.USURPED if command.usurped else TitleTenure.GRANTED)
    row.locked = held(row.locked, ["holder_node_id"], command.hold)
    await scope.session.flush()
    verb = "seized" if command.usurped else "granted"
    return Effect(f"The title was {verb}." if command.holder_id is not None else "The title lies dormant, held by no one.", target_node_id=row.title_entity_id)


@player_action("title:destroy", ActionKind.EDIT_RECORD)
async def destroy(scope: PlayerScope, command: TitleTarget) -> Effect:
    row = await title(scope, command.title_id)
    if row.destroyed_epoch is not None:
        raise ValidationFailedError("That title is already destroyed.")
    ctx = await manual_context(scope.session, "title.destroy")
    await record_holder(ctx, row, None, TitleTenure.GRANTED)
    row.destroyed_epoch, row.polity_entity_id = ctx.epoch, None
    await scope.session.flush()
    return Effect("The title was destroyed; it may be restored by one who holds its lands.", target_node_id=row.title_entity_id)


@player_action("title:restore", ActionKind.EDIT_RECORD)
async def restore(scope: PlayerScope, command: PassTitle) -> Effect:
    row = await title(scope, command.title_id)
    ctx = await manual_context(scope.session, "title.restore")
    row.destroyed_epoch = None
    await record_holder(ctx, row, command.holder_id, TitleTenure.RESTORED)
    await scope.session.flush()
    return Effect("The old title was restored.", target_node_id=row.title_entity_id)


@player_action("title:remove", ActionKind.EDIT_RECORD)
async def remove(scope: PlayerScope, command: TitleTarget) -> Effect:
    row = await title(scope, command.title_id)
    await scope.session.execute(delete(DeJureLinkRow).where(DeJureLinkRow.title_entity_id == row.title_entity_id))
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The title's record was struck; its lands answer to no title until the world draws them anew.", target_node_id=command.title_id)


@player_action("de_jure:set", ActionKind.EDIT_RECORD)
async def set_de_jure(scope: PlayerScope, command: SetDeJure) -> Effect:
    row = await title(scope, command.title_id)
    member = await entity(scope, command.member_id, "A de jure land", frozenset({EntityType.REGION, EntityType.TITLE}))
    await link(scope, row.title_entity_id, member.id, await scope.epoch(), command.hold)
    await scope.session.flush()
    return Effect(f"{member.name} now belongs by right to this title.", target_node_id=row.title_entity_id)


@player_action("de_jure:remove", ActionKind.EDIT_RECORD)
async def remove_de_jure(scope: PlayerScope, command: DeJureTarget) -> Effect:
    found = await scope.session.get(DeJureLinkRow, (command.title_id, command.member_id))
    if found is None:
        raise NotFoundError("That land does not belong to this title.")
    await scope.session.delete(found)
    await scope.session.flush()
    return Effect("The land was struck from the title's right.", target_node_id=command.title_id)
