from sqlalchemy import select

from aerona.db.tables.culture import RiteEffectRow, RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import PossessionRow
from aerona.domain.enums.culture import MagicSchool, RiteEffectKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.engine.context import TickContext
from aerona.engine.faith.souls import burden
from aerona.engine.lore.rites import cast, devise
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.queries import living_entity

CLERGY = (MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER)


async def exorcism_rite(ctx: TickContext, world_id: int | None) -> tuple[EntityRow, RiteProfileRow] | None:
    rites = select(RiteEffectRow.rite_entity_id).where(RiteEffectRow.effect == RiteEffectKind.EXORCISE)
    statement = select(RiteProfileRow).where(RiteProfileRow.rite_entity_id.in_(rites))
    rows = await ctx.session.scalars(statement.order_by(RiteProfileRow.power.desc(), RiteProfileRow.rite_entity_id))
    for row in rows:
        rite = await living_entity(ctx.session, row.rite_entity_id)
        if rite is not None and (world_id is None or rite.world_id in {world_id, None}):
            return rite, row
    return None


async def priest_at(ctx: TickContext, place_id: int | None) -> EntityRow | None:
    if place_id is None:
        return None
    statement = select(EntityRow).where(
        EntityRow.location_id == place_id,
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.mortal_role.in_(list(CLERGY)),
    )
    return await ctx.session.scalar(statement.order_by(EntityRow.id).limit(1))


async def possessions(ctx: TickContext) -> tuple[int, int]:
    table = ctx.rules.necromancy
    held = await burden(ctx)
    realms: RealmBook | None = None
    exorcised = 0
    for _, host, _ in held:
        priest = await priest_at(ctx, host.location_id)
        if priest is None or not ctx.rng(f"exorcism.{host.id}.{ctx.epoch}").chance(table.exorcism_chance):
            continue
        found = await exorcism_rite(ctx, host.world_id)
        if found is None and ctx.rng(f"exorcism.devise.{priest.id}.{ctx.epoch}").chance(ctx.rules.rites.invention_chance):
            found = await devise(ctx, MagicSchool.WARDING, priest)
        if found is None:
            continue
        realms = realms or await RealmBook.load(ctx.session)
        casting = await cast(ctx, priest, found[0], found[1], target=host, realms=realms, forced=True)
        if casting is not None and casting.succeeded and await ctx.session.get(PossessionRow, host.id) is None:
            exorcised += 1
    return len(held) - exorcised, exorcised
