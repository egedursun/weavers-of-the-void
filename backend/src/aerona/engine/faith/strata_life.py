from collections.abc import Awaitable, Callable, Mapping

from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, SpiritProfileRow
from aerona.domain.enums.faith import AfterlifeState, StratumPermanence
from aerona.engine.context import TickContext
from aerona.engine.faith.judgement import judge, leave_realm
from aerona.engine.faith.souls import reincarnate
from aerona.engine.primitives.records import retire_in

Turn = Callable[[TickContext, AfterlifeStratumRow, SpiritProfileRow, EntityRow], Awaitable[str | None]]


async def stays(_ctx: TickContext, _stratum: AfterlifeStratumRow, _profile: SpiritProfileRow, _spirit: EntityRow) -> str | None:
    return None


async def fades(ctx: TickContext, _stratum: AfterlifeStratumRow, profile: SpiritProfileRow, spirit: EntityRow) -> str | None:
    if "memory_strength" not in profile.locked:
        profile.memory_strength = max(0, profile.memory_strength - ctx.rules.afterlife.stratum_fade)
    if profile.memory_strength > 0:
        return None
    await leave_realm(ctx, profile, AfterlifeState.CONSUMED)
    await retire_in(ctx, spirit, "faded from the realm of the dead", close_bonds=True)
    return "faded"


async def reborn(ctx: TickContext, _stratum: AfterlifeStratumRow, profile: SpiritProfileRow, spirit: EntityRow) -> str | None:
    if ctx.epoch - profile.updated_epoch < ctx.rules.afterlife.rebirth_wait:
        return None
    return "reborn" if await reincarnate(ctx, profile, spirit) is not None else None


async def judged_again(ctx: TickContext, stratum: AfterlifeStratumRow, profile: SpiritProfileRow, spirit: EntityRow) -> str | None:
    if ctx.epoch - profile.updated_epoch < ctx.rules.afterlife.rejudge_wait or profile.origin_mortal_id is None:
        return None
    mortal = await ctx.session.get(EntityRow, profile.origin_mortal_id)
    realm = await ctx.session.get(EntityRow, stratum.realm_entity_id)
    if mortal is None:
        return None
    verdict = await judge(ctx, spirit, mortal, realm)
    profile.updated_epoch = ctx.epoch
    return "judged_again" if verdict.stratum is None or verdict.stratum.id != stratum.id else None


PERMANENCE: Mapping[StratumPermanence, Turn] = total(
    StratumPermanence,
    {
        StratumPermanence.ETERNAL: stays,
        StratumPermanence.UNTIL_REBIRTH: reborn,
        StratumPermanence.UNTIL_JUDGEMENT: judged_again,
        StratumPermanence.FADING: fades,
    },
)


async def stratum_turn(ctx: TickContext, profile: SpiritProfileRow, spirit: EntityRow) -> str | None:
    if profile.state is not AfterlifeState.IN_REALM or profile.stratum_id is None:
        return None
    stratum = await ctx.session.get(AfterlifeStratumRow, profile.stratum_id)
    if stratum is None:
        return None
    return await PERMANENCE[stratum.permanence](ctx, stratum, profile, spirit)
