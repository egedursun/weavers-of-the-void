from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import ProphecyPredicate, ProphecyState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import ProphecyStats
from aerona.engine.context import TickContext
from aerona.engine.lore.prophecy import cult_of, fail
from aerona.engine.mind.drives import rulers_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat


async def pending(ctx: TickContext) -> list[ProphecyConditionRow]:
    rows = await ctx.session.scalars(
        select(ProphecyConditionRow).where(ProphecyConditionRow.state == ProphecyState.PENDING).order_by(ProphecyConditionRow.prophecy_entity_id)
    )
    return list(rows)


async def retell(ctx: TickContext, row: ProphecyConditionRow) -> bool:
    table = ctx.rules.prophecy
    if held(row.prophecy_entity_id) or not row.audience or "deadline_epoch" in row.locked or row.deadline_epoch is None:
        return False
    rng = ctx.rng(f"prophecy_retold.{row.prophecy_entity_id}.{ctx.epoch}")
    if not rng.chance(table.retell_chance):
        return False
    shift = rng.integer(-table.retell_epochs, table.retell_epochs)
    row.deadline_epoch = max(ctx.epoch + 1, row.deadline_epoch + shift)
    row.retold += 1
    return True


async def pair_rivals(ctx: TickContext, rows: list[ProphecyConditionRow]) -> int:
    paired = 0
    open_rows = [row for row in rows if row.rival_entity_id is None and "rival_entity_id" not in row.locked]
    for index, first in enumerate(open_rows):
        for second in open_rows[index + 1 :]:
            if first.rival_entity_id is not None or second.rival_entity_id is not None or first.predicate is not second.predicate:
                continue
            one, two = await ctx.session.get(EntityRow, first.prophecy_entity_id), await ctx.session.get(EntityRow, second.prophecy_entity_id)
            if one is None or two is None or one.world_id != two.world_id or first.args == second.args:
                continue
            first.rival_entity_id, second.rival_entity_id = second.prophecy_entity_id, first.prophecy_entity_id
            await note(
                ctx, f"{one.name} and {two.name} are told as rivals; believers take one side or the other.", key="lore.prophecy_rivals", ids=[one.id, two.id]
            )
            paired += 1
    return paired


async def contest(ctx: TickContext) -> int:
    table = ctx.rules.prophecy
    settled = 0
    for row in list(await ctx.session.scalars(select(ProphecyConditionRow).where(ProphecyConditionRow.rival_entity_id.is_not(None)))):
        rival = await ctx.session.get(ProphecyConditionRow, row.rival_entity_id) if row.rival_entity_id is not None else None
        if rival is None or held(row.prophecy_entity_id):
            continue
        if row.state is ProphecyState.PENDING and rival.state is ProphecyState.PENDING and "pressure" not in row.locked:
            row.pressure = clamp_int(row.pressure - table.rival_pressure, 0, PERCENT)
        if row.state is ProphecyState.FULFILLED and row.resolved_epoch == ctx.epoch and rival.state is ProphecyState.PENDING:
            await fail(ctx, rival)
            seer = await ctx.session.get(EntityRow, row.seer_entity_id) if row.seer_entity_id is not None else None
            cult = await cult_of(ctx, seer) if seer is not None else None
            if cult is not None:
                shift_stat(cult, "zeal", table.tradition_gain)
            settled += 1
    return settled


async def forge_for(ctx: TickContext, ruler: EntityRow, realm: PolityProfileRow) -> EntityRow:
    told = await create_record(
        ctx,
        RecordSpec(
            name=f"The Foretelling of {ruler.name}",
            entity_type=EntityType.PROPHECY,
            stats=ProphecyStats(certainty=PERCENT // 2),
            body=f"A prophecy that {ruler.name} was always meant to rule.",
            power=1,
            world_id=ruler.world_id,
            location_id=ruler.location_id,
            maker_entity_id=ruler.id,
        ),
    )
    row = ProphecyConditionRow(
        prophecy_entity_id=told.id, predicate=ProphecyPredicate.RULER_OF, args={"subject": ruler.id, "realm": realm.polity_entity_id}, seer_entity_id=ruler.id
    )
    row.audience, row.state, row.forged, row.locked = [realm.polity_entity_id], ProphecyState.PENDING, True, []
    ctx.session.add(row)
    if "legitimacy" not in realm.locked:
        realm.legitimacy = clamp_int(realm.legitimacy + ctx.rules.prophecy.forge_gain, 0, PERCENT)
    await ctx.session.flush()
    return told


async def forgeries(ctx: TickContext) -> int:
    table = ctx.rules.prophecy
    forged = 0
    for realm in list(
        await ctx.session.scalars(
            select(PolityProfileRow).where(PolityProfileRow.legitimacy < table.forge_legitimacy).order_by(PolityProfileRow.polity_entity_id)
        )
    ):
        rulers = await rulers_of(ctx.session, realm.polity_entity_id)
        ruler = rulers[0] if rulers else None
        if ruler is None or ruler.status is not EntityStatus.CANON or held(ruler.id, realm.polity_entity_id):
            continue
        if ctx.rng(f"prophecy_forged.{realm.polity_entity_id}.{ctx.epoch}").chance(table.forge_chance):
            told = await forge_for(ctx, ruler, realm)
            await note(ctx, f"{told.name} began to be told in the realm.", key="lore.prophecy_forged", ids=[told.id, ruler.id])
            forged += 1
    return forged


async def exposures(ctx: TickContext) -> int:
    table = ctx.rules.prophecy
    exposed = 0
    for row in list(
        await ctx.session.scalars(
            select(ProphecyConditionRow).where(ProphecyConditionRow.forged.is_(True), ProphecyConditionRow.state == ProphecyState.PENDING)
        )
    ):
        if held(row.prophecy_entity_id) or not ctx.rng(f"prophecy_exposed.{row.prophecy_entity_id}.{ctx.epoch}").chance(table.exposure_chance):
            continue
        await fail(ctx, row)
        for realm_id in row.audience:
            realm = await ctx.session.get(PolityProfileRow, realm_id)
            if realm is not None and "legitimacy" not in realm.locked:
                realm.legitimacy = clamp_int(realm.legitimacy - table.exposure_loss, 0, PERCENT)
        await note(ctx, "A forged prophecy was exposed.", key="lore.prophecy_exposed", ids=[row.prophecy_entity_id])
        exposed += 1
    return exposed


async def keep_prophecy_tales(ctx: TickContext) -> None:
    rows = await pending(ctx)
    ctx.count("prophecies_retold", sum([await retell(ctx, row) for row in rows]))
    ctx.count("prophecy_rivals", await pair_rivals(ctx, rows))
    ctx.count("prophecy_contests", await contest(ctx))
    ctx.count("prophecies_forged", await forgeries(ctx))
    ctx.count("prophecies_exposed", await exposures(ctx))
