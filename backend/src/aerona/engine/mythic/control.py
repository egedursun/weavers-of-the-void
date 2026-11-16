from sqlalchemy import delete

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.mythic import (
    GEAS_FIELDS,
    HEROQUEST_FIELDS,
    MANTLING_FIELDS,
    OFFICE_FIELDS,
    SERVITOR_FIELDS,
    CosmicOfficeRow,
    GeasRow,
    HeroquestMemberRow,
    HeroquestRow,
    MantlingRow,
    ServitorRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import CosmicOffice, GeasLayer, GeasMode, GeasState, HeroquestState, OfficeChoice, ServitorRole
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found, node
from aerona.engine.mythic.geasa import doom, lay_geas
from aerona.engine.mythic.heroquests import QuestTally, advance, begin_quest, settle_souls
from aerona.engine.mythic.offices import appoint, offices
from aerona.engine.mythic.servitors import make_servitor


async def start_quest(ctx: TickContext, quester_id: int, legend_id: int, members: list[int]) -> HeroquestRow:
    quester = await entity(ctx, quester_id, "quester")
    if quester.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can undertake a heroquest.")
    legend = await found(ctx, LegendProfileRow, legend_id, "legend")
    await companions(ctx, quester.id, members)
    return await begin_quest(ctx, quester, legend, members)


async def companions(ctx: TickContext, quester_id: int, members: list[int]) -> None:
    for member in members:
        companion = await entity(ctx, member, "companion")
        if companion.entity_type is not EntityType.MORTAL or companion.id == quester_id:
            raise ValidationFailedError(f"{companion.name} cannot walk beside this quester.")


async def set_party(ctx: TickContext, quest_id: int, members: list[int]) -> HeroquestRow:
    row = await found(ctx, HeroquestRow, quest_id, "heroquest")
    chosen = list(dict.fromkeys(members))
    await companions(ctx, row.quester_entity_id, chosen)
    await ctx.session.execute(delete(HeroquestMemberRow).where(HeroquestMemberRow.heroquest_id == row.id))
    ctx.session.add_all(HeroquestMemberRow(heroquest_id=row.id, entity_id=member) for member in chosen)
    await ctx.session.flush()
    await settle_souls(ctx)
    await ctx.session.flush()
    return row


async def edit_quest(ctx: TickContext, quest_id: int, values: Values, release: list[str]) -> HeroquestRow:
    row = apply(await found(ctx, HeroquestRow, quest_id, "heroquest"), allowed(values, HEROQUEST_FIELDS, "heroquest"), release)
    await ctx.session.flush()
    return row


async def step_quest(ctx: TickContext, quest_id: int) -> HeroquestRow:
    row = await found(ctx, HeroquestRow, quest_id, "heroquest")
    if row.state is not HeroquestState.QUESTING:
        raise ValidationFailedError("This heroquest is over.")
    await advance(ctx, row, QuestTally())
    await ctx.session.flush()
    return row


async def delete_quest(ctx: TickContext, quest_id: int) -> None:
    await ctx.session.delete(await found(ctx, HeroquestRow, quest_id, "heroquest"))
    await ctx.session.flush()


async def edit_mantling(ctx: TickContext, mortal_id: int, values: Values, release: list[str]) -> MantlingRow:
    await entity(ctx, mortal_id, "mortal")
    row = await ctx.session.get(MantlingRow, mortal_id)
    if row is None:
        row = MantlingRow(mortal_entity_id=mortal_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    apply(row, allowed(values, MANTLING_FIELDS, "mantling"), release)
    await ctx.session.flush()
    return row


async def delete_mantling(ctx: TickContext, mortal_id: int) -> None:
    await ctx.session.delete(await found(ctx, MantlingRow, mortal_id, "mantling"))
    await ctx.session.flush()


async def create_servitor(ctx: TickContext, god_id: int, *, name: str, role: ServitorRole, post_id: int | None) -> ServitorRow:
    await node(ctx, god_id, "god")
    post = await entity(ctx, post_id, "post") if post_id is not None else None
    return await make_servitor(ctx, god_id, name=name, role=role, post_id=post.id if post else None, world_id=post.world_id if post else None)


async def edit_servitor(ctx: TickContext, spirit_id: int, values: Values, release: list[str]) -> ServitorRow:
    row = apply(await found(ctx, ServitorRow, spirit_id, "servitor"), allowed(values, SERVITOR_FIELDS, "servitor"), release)
    await ctx.session.flush()
    return row


async def release_servitor(ctx: TickContext, spirit_id: int) -> None:
    await ctx.session.delete(await found(ctx, ServitorRow, spirit_id, "servitor"))
    await ctx.session.flush()


async def place_geas(ctx: TickContext, bearer_id: int, layer_id: int | None, *, layer: GeasLayer, mode: GeasMode, act: ActKind) -> GeasRow:
    bearer = await entity(ctx, bearer_id, "bearer")
    if bearer.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("A geas is laid on a mortal.")
    if layer_id is not None:
        await node(ctx, layer_id, "layer")
    return await lay_geas(ctx, bearer, layer_node_id=layer_id, layer=layer, mode=mode, act=act)


async def edit_geas(ctx: TickContext, geas_id: int, values: Values, release: list[str]) -> GeasRow:
    row = apply(await found(ctx, GeasRow, geas_id, "geas"), allowed(values, GEAS_FIELDS, "geas"), release)
    await ctx.session.flush()
    return row


async def break_geas_now(ctx: TickContext, geas_id: int) -> GeasRow:
    row = await found(ctx, GeasRow, geas_id, "geas")
    if row.state is GeasState.BROKEN:
        raise ValidationFailedError("This geas is already broken.")
    await doom(ctx, row, await entity(ctx, row.bearer_entity_id, "bearer"), "the gods willed it")
    await ctx.session.flush()
    return row


async def delete_geas(ctx: TickContext, geas_id: int) -> None:
    await ctx.session.delete(await found(ctx, GeasRow, geas_id, "geas"))
    await ctx.session.flush()


async def office_row(ctx: TickContext, office: CosmicOffice) -> CosmicOfficeRow:
    return next(row for row in await offices(ctx) if row.office is office)


async def seat_office(ctx: TickContext, office: CosmicOffice, holder_id: int) -> CosmicOfficeRow:
    await node(ctx, holder_id, "holder")
    return await appoint(ctx, office, holder_id, OfficeChoice.CREATOR)


async def edit_office(ctx: TickContext, office: CosmicOffice, values: Values, release: list[str]) -> CosmicOfficeRow:
    row = apply(await office_row(ctx, office), allowed(values, OFFICE_FIELDS, "office"), release)
    await ctx.session.flush()
    return row


async def vacate_office(ctx: TickContext, office: CosmicOffice) -> CosmicOfficeRow:
    row = await office_row(ctx, office)
    if row.holder_node_id is None:
        raise ValidationFailedError("No one holds this office.")
    row.holder_node_id, row.since_epoch = None, None
    await ctx.session.flush()
    return row
