from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.structure import STANDING_STATES, ConstructionState
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, fraction
from aerona.engine.primitives.queries import add_flag
from aerona.engine.structures.profiles import material_props, refresh, standing_state
from aerona.engine.structures.workshops import unlink


async def harm(ctx: TickContext, work: EntityRow, profile: StructureProfileRow, loss: float, *, cause: str, quiet: bool = False) -> bool:
    if "condition" in profile.locked or loss <= 0:
        return False
    before = profile.condition
    profile.condition = clamp_int(profile.condition - loss, 0, PERCENT)
    if profile.construction_state in STANDING_STATES and "construction_state" not in profile.locked:
        profile.construction_state = standing_state(ctx.rules, profile)
    collapsed = profile.condition <= 0
    if collapsed:
        profile.construction_state = ConstructionState.RUINED
        await add_flag(ctx.session, work.id, EntityFlag.RUIN, ctx.epoch)
        await unlink(ctx.session, work.id)
    await refresh(ctx.session, ctx.rules, work, profile)
    if not quiet:
        tail = " and fell to ruin" if collapsed else f" (condition {before} to {profile.condition})"
        await note(ctx, f"{work.name} was damaged by {cause}{tail}.", key="structures.damaged", ids=[work.id], kind=ChronicleKind.CONSTRUCTION)
    return collapsed


async def ruin_profile(session: AsyncSession, structure_id: int) -> None:
    profile = await session.get(StructureProfileRow, structure_id)
    if profile is None:
        return
    profile.construction_state = ConstructionState.RUINED
    profile.effect_pct = 0
    await unlink(session, structure_id)


async def quake_loss(ctx: TickContext, work: EntityRow, base: float) -> float:
    props = await material_props(ctx.session, work)
    toughness = props.toughness if props is not None else 0
    return base * (1 - fraction(toughness) * fraction(ctx.rules.upkeep.quake_toughness_pct))
