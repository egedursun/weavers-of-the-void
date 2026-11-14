from aerona.core.errors import ValidationFailedError
from aerona.db.tables.eras import PROGRAMME_FIELDS, TechProgrammeRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.eras.progress import EraTally, keep_eras
from aerona.engine.gatherings.control import Values, allowed, found

LABEL = "programme"


async def checked(ctx: TickContext, values: Values) -> None:
    polity = values.get("polity_entity_id")
    if isinstance(polity, int) and await ctx.session.get(PolityProfileRow, polity) is None:
        raise ValidationFailedError("Only a realm runs a programme.")


async def create_programme(ctx: TickContext, values: Values) -> TechProgrammeRow:
    await checked(ctx, values)
    return await saved(ctx, TechProgrammeRow(**values, started_epoch=ctx.epoch, locked=[]))


async def edit_programme(ctx: TickContext, record_id: int, values: Values, release: list[str]) -> TechProgrammeRow:
    row = apply(await found(ctx, TechProgrammeRow, record_id, LABEL), allowed(values, PROGRAMME_FIELDS, LABEL), release)
    await ctx.session.flush()
    return row


async def delete_programme(ctx: TickContext, record_id: int) -> None:
    await ctx.session.delete(await found(ctx, TechProgrammeRow, record_id, LABEL))
    await ctx.session.flush()


async def run_eras(ctx: TickContext) -> EraTally:
    tally = EraTally()
    await keep_eras(ctx, tally)
    return tally
