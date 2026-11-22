from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.ethics import HONOUR_MODELS
from aerona.catalog.life.polity import MODEL_PENALTIES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OathPenalty, OathStatus
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.context import TickContext
from aerona.engine.divine.laws import binds
from aerona.engine.economy.purse import take_coin
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.mind.ethics import culture_of, honour_of
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.standing import add_honour
from aerona.engine.primitives.queries import add_flag


@dataclass(frozen=True)
class OathTerms:
    witness_node_id: int | None = None
    penalty: OathPenalty | None = None
    clear_penalty: bool = False


async def by_shame(ctx: TickContext, swearer: EntityRow) -> None:
    await add_honour(ctx.session, swearer.id, -ctx.rules.oaths.shame, ctx.epoch)


async def by_fine(ctx: TickContext, swearer: EntityRow) -> None:
    await take_coin(ctx.session, ctx.rules, swearer, ctx.rules.oaths.fine)


async def by_exile(ctx: TickContext, swearer: EntityRow) -> None:
    await add_flag(ctx.session, swearer.id, EntityFlag.EXILE, ctx.epoch)


async def by_outlawry(ctx: TickContext, swearer: EntityRow) -> None:
    if swearer.location_id is not None:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=swearer.location_id,
            subject_id=swearer.id,
            kind=MemoryKind.ILL_WILL,
            magnitude=-ctx.rules.oaths.breach_relation,
            epoch=ctx.epoch,
            note="an outlaw",
        )


async def by_curse(ctx: TickContext, swearer: EntityRow) -> None:
    await shift_fortune(ctx, swearer.id, -ctx.rules.oaths.curse_fortune, FortuneSourceKind.OATH_BROKEN)


WITNESS_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.POLITY})
PENALTIES: Mapping[OathPenalty, Callable[[TickContext, EntityRow], Awaitable[None]]] = total(
    OathPenalty,
    {
        OathPenalty.SHAME: by_shame,
        OathPenalty.FINE: by_fine,
        OathPenalty.EXILE: by_exile,
        OathPenalty.OUTLAWRY: by_outlawry,
        OathPenalty.CURSE: by_curse,
    },
)


async def honour_weight(ctx: TickContext, swearer: EntityRow) -> int:
    culture = await culture_of(ctx.session, swearer.id)
    return HONOUR_MODELS[await honour_of(ctx.session, culture.id if culture is not None else None)].oath_pct


async def answer_breach(ctx: TickContext, oath: OathRow, swearer: EntityRow) -> None:
    if oath.penalty is not None and not held(swearer.id):
        await PENALTIES[oath.penalty](ctx, swearer)
    await witness_answer(ctx, oath, kept=False)


async def witness_answer(ctx: TickContext, oath: OathRow, *, kept: bool) -> None:
    if oath.witness_node_id is None or oath.witness_node_id == oath.swearer_entity_id:
        return
    weight = ctx.rules.oaths.witness_relation
    kind = MemoryKind.KEPT_OATH if kept else MemoryKind.BROKE_OATH
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=oath.witness_node_id,
        subject_id=oath.swearer_entity_id,
        kind=kind,
        magnitude=weight if kept else -weight,
        epoch=ctx.epoch,
        note="a witnessed oath",
    )


async def releases(ctx: TickContext) -> int:
    table = ctx.rules.oaths
    freed = 0
    sworn = select(OathRow).where(OathRow.status == OathStatus.SWORN, OathRow.recipient_node_id.is_not(None)).order_by(OathRow.id)
    for oath in list(await ctx.session.scalars(sworn)):
        if held(oath.swearer_entity_id) or oath.recipient_node_id is None:
            continue
        warmth = await ctx.session.scalar(
            select(RelationshipRow.friendship).where(
                RelationshipRow.holder_node_id == oath.recipient_node_id, RelationshipRow.subject_node_id == oath.swearer_entity_id
            )
        )
        if int(warmth or 0) < table.release_friendship or not ctx.rng(f"oath_release.{oath.id}.{ctx.epoch}").chance(table.release_chance):
            continue
        oath.status, oath.ended_epoch = OathStatus.KEPT, ctx.epoch
        oath.note = (oath.note or "") + " Released by the one it was sworn to."
        freed += 1
    return freed


async def terms_for(ctx: TickContext, swearer: EntityRow) -> tuple[int | None, OathPenalty | None]:
    culture = await culture_of(ctx.session, swearer.id)
    penalty = MODEL_PENALTIES[await honour_of(ctx.session, culture.id if culture is not None else None)]
    if await binds(ctx, NaturalLaw.OATHS_BIND, swearer):
        penalty = OathPenalty.CURSE
    home = await ctx.session.get(EntityRow, swearer.location_id) if swearer.location_id is not None else None
    witness = home.id if home is not None and home.entity_type in WITNESS_TYPES else None
    return witness, penalty


def scaled_loss(loss: int, weight: int) -> int:
    return loss * weight // PERCENT
