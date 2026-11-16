from sqlalchemy import select

from aerona.catalog.stats import max_essence
from aerona.constants.units import PERCENT
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.divine import DivineWoundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import WoundCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.domain.enums.transform import GodDeathMode
from aerona.domain.models.entity_stats import MortalStats, OuterBeingStats
from aerona.engine.context import TickContext
from aerona.engine.divine.outer import outer_profile
from aerona.engine.gods.god_death import god_death
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.mythic.heroquests import renown_of
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import living_sons, top_region
from aerona.engine.primitives.records import RecordSpec
from aerona.engine.primitives.stats import stat_or
from aerona.engine.transform.bodies import fallen_in, living_body
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, end, make

DIVINE = (SonStatus.ACTIVE, SonStatus.ASLEEP, SonStatus.EXILED)
MORTAL_BASE = 50


def fallen_stats(ctx: TickContext, son: SonRow) -> MortalStats:
    lift = ctx.rules.transform.fallen_attribute_bonus

    def keep(value: int) -> int:
        return clamp_percent(max(MORTAL_BASE, value) + lift)

    return MortalStats(
        strength=keep(son.strength),
        agility=keep(son.agility),
        endurance=keep(son.endurance),
        intellect=keep(son.cunning),
        wisdom=keep(son.wisdom),
        willpower=keep(son.will),
        creativity=keep(son.creativity),
        charisma=keep(son.charisma),
    )


async def home_of(ctx: TickContext, son: SonRow) -> EntityRow | None:
    for worshipper in await worshippers_of(ctx.session, son.id):
        if worshipper.entity_type is EntityType.SETTLEMENT:
            return worshipper
        place = await top_region(ctx.session, worshipper)
        if place is not None:
            return place
    if son.current_world_id is None:
        return None
    return await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == son.current_world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )


async def fall_pressures(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status.in_(DIVINE), SonRow.fading_epochs > 0).order_by(SonRow.id)):
        if await living_body(ctx.session, son) is not None:
            found[son.id] = PERCENT
    return found


async def fall_check(ctx: TickContext, son_id: int) -> str | None:
    son = await ctx.session.get(SonRow, son_id)
    if son is None:
        return "Only a son of the Creator can fall from godhood."
    if son.status not in DIVINE:
        return f"{son.name} is not a living god."
    return None


async def recognise(ctx: TickContext, ledger: Ledger, son: SonRow, body_id: int) -> int:
    remnant = 0
    for worshipper in await worshippers_of(ctx.session, son.id):
        if held(worshipper.id) or worshipper.id == body_id:
            continue
        chance = stat_or(worshipper, "piety", ctx.rules.society.default_stat) * ctx.rules.transform.remnant_pct / PERCENT
        if ctx.rng(f"fall.remnant.{son.id}.{worshipper.id}").chance(chance):
            await bind(ctx, ledger, (worshipper.id, body_id, BondKind.WORSHIPS), f"knows its fallen god {son.name} in the mortal it became")
            remnant += 1
    return remnant


async def cast_down(ctx: TickContext, son_id: int, ledger: Ledger) -> int:
    son = await ctx.session.get_one(SonRow, son_id)
    body = await living_body(ctx.session, son)
    if body is None:
        home = await home_of(ctx, son)
        body = await make(
            ctx,
            ledger,
            RecordSpec(
                entity_type=EntityType.MORTAL,
                name=await NameRepository(ctx.session).unique_name(son.name),
                body=f"The mortal body {son.name} wakes in after falling from godhood, remembering all of it.",
                stats=fallen_stats(ctx, son),
                power=clamp_percent(son.level * 10),
                world_id=home.world_id if home is not None else son.current_world_id,
                location_id=home.id if home is not None else None,
            ),
        )
    if await ctx.session.get(TrueNameRow, body.id) is None:
        name = TrueNameRow(bearer_node_id=body.id, name=son.name, language_node_id=None, known_by=[], since_epoch=ctx.epoch, locked=[])
        ctx.session.add(name)
        await ctx.session.flush()
        ledger.added(name)
    await recognise(ctx, ledger, son, body.id)
    ledger.set(son, "status", SonStatus.FALLEN)
    ledger.set(son, "essence", 0)
    ledger.set(son, "fading_epochs", 0)
    ledger.set(son, "body_entity_id", body.id)
    return body.id


async def tend_fallen(ctx: TickContext) -> int:
    drift = ctx.rules.transform.fallen_drift_pct
    moved = 0
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.FALLEN).order_by(SonRow.id)):
        body = await living_body(ctx.session, son)
        if body is None or held(son.id):
            continue
        target = max(await renown_of(ctx, body.id), clamp_percent(son.faith))
        son.existence = clamp_percent(son.existence + round((target - son.existence) * drift / PERCENT))
        moved += 1
    return moved


async def restoration_pressures(ctx: TickContext) -> dict[int, int]:
    need = ctx.rules.transform.restoration_existence
    found: dict[int, int] = {}
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.FALLEN).order_by(SonRow.id)):
        body = await living_body(ctx.session, son)
        if body is not None:
            found[body.id] = clamp_percent(son.existence * PERCENT // need)
    return found


async def restoration_check(ctx: TickContext, body_id: int) -> str | None:
    son = await fallen_in(ctx, body_id)
    if son is None:
        return "Only the living body of a fallen son can climb back to godhood."
    return None


async def restore(ctx: TickContext, body_id: int, ledger: Ledger) -> int:
    son = await fallen_in(ctx, body_id)
    body = await ctx.session.get_one(EntityRow, body_id)
    if son is None:
        return body_id
    ledger.set(son, "status", SonStatus.ACTIVE)
    ledger.set(son, "body_entity_id", None)
    ledger.set(son, "essence", round(max_essence(ctx.rules, son.might) * ctx.rules.transform.restoration_essence_pct / PERCENT))
    end(ctx, ledger, body, EntityStatus.DEAD)
    return son.id


async def bargained(ctx: TickContext, son_id: int) -> bool:
    found = await ctx.session.scalar(
        select(DivineWoundRow.id).where(DivineWoundRow.god_node_id == son_id, DivineWoundRow.cause == WoundCause.OUTER_BARGAIN).limit(1)
    )
    return found is not None


async def corruption_pressures(ctx: TickContext) -> dict[int, int]:
    band = ctx.rules.transform.corruption_warning_sanity
    found: dict[int, int] = {}
    statement = select(SonRow).where(SonRow.status.in_(DIVINE), SonRow.sanity.is_not(None), SonRow.sanity <= band).order_by(SonRow.id)
    for son in await ctx.session.scalars(statement):
        if await bargained(ctx, son.id):
            found[son.id] = clamp_percent((band - (son.sanity or 0)) * PERCENT // band)
    return found


async def corruption_check(ctx: TickContext, son_id: int) -> str | None:
    son = await ctx.session.get(SonRow, son_id)
    if son is None:
        return "Only a son of the Creator can be corrupted."
    if son.status not in DIVINE:
        return f"{son.name} is not a living god."
    return None


async def corrupt(ctx: TickContext, son_id: int, ledger: Ledger) -> int:
    son = await ctx.session.get_one(SonRow, son_id)
    being = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.OUTER_BEING,
            name=await NameRepository(ctx.session).unique_name(f"{son.name} Beyond"),
            body=f"What {son.name} became after passing out of the cosmos. It remembers its godhood and its siblings.",
            stats=OuterBeingStats(size=clamp_percent(son.might), interest=PERCENT, influence=clamp_percent(son.fame)),
            power=clamp_percent(son.might),
            world_id=son.current_world_id,
        ),
    )
    await outer_profile(ctx, being)
    threshold = ctx.rules.death.god_death_relation_threshold
    repository = SonRepository(ctx.session)
    for sibling in await living_sons(ctx.session):
        if sibling.id != son.id and await repository.relation(sibling.id, son.id) <= -threshold:
            await bind(ctx, ledger, (being.id, sibling.id, BondKind.ENEMY), f"a grudge {son.name} carried out of the cosmos")
    await bind(ctx, ledger, (being.id, son.id, BondKind.DESCENDS_FROM), f"what {son.name} became")
    await god_death(ctx, son, "passed out of the cosmos", SonDeathCause.COSMIC_HORROR, mode=GodDeathMode.LEFT_COSMOS, successor_id=being.id, ledger=ledger)
    return being.id
