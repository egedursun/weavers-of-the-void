from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sacred import FORTUNE_MAX, FORTUNE_MIN, BirthSignRow, DivinationSystemRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.sacred import DivinationKind, SignInfluence
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.omens import BRIGHT, influence_share, returns_now
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import town_of

MIDDLING = PERCENT // 2
SHAPED = ("willpower", "perception")


@dataclass
class SignTally:
    signed: int = 0
    real: int = 0
    dreaded: int = 0
    fostered: int = 0


async def celestials_of(ctx: TickContext, world_id: int | None) -> list[EntityRow]:
    if world_id is None:
        return []
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.CELESTIAL, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world_id)
        .order_by(EntityRow.id)
    )
    return list(rows)


async def ruling_body(ctx: TickContext, world_id: int | None, bodies: list[EntityRow]) -> EntityRow | None:
    world = await ctx.session.get(WorldRow, world_id) if world_id is not None else None
    if world is not None and world.epoch_star_entity_id is not None:
        star = next((body for body in bodies if body.id == world.epoch_star_entity_id), None)
        if star is not None:
            return star
    returning = [body for body in bodies if returns_now(ctx.rules, body, ctx.epoch)]
    return max(returning or bodies, key=lambda body: (influence_share(body), -body.id), default=None)


async def real_sky(ctx: TickContext, world_id: int | None) -> bool:
    floor = ctx.rules.astrology.real_influence
    return any(stat_or(body, "influence", 0) >= floor for body in await celestials_of(ctx, world_id))


async def reads_stars(ctx: TickContext, people_id: int | None) -> bool:
    if people_id is None:
        return False
    found = await ctx.session.scalar(
        select(DivinationSystemRow.id).where(DivinationSystemRow.people_entity_id == people_id, DivinationSystemRow.kind == DivinationKind.ASTROLOGY).limit(1)
    )
    return found is not None


def fortune_of(ctx: TickContext, body: EntityRow | None, dreaded: bool) -> int:
    if body is None:
        return 0
    lean = abs(stat_or(body, "influence", 0) - MIDDLING) // ctx.rules.astrology.fortune_scale
    return clamp_int(-lean if dreaded else lean, FORTUNE_MIN, FORTUNE_MAX)


async def foster_away(ctx: TickContext, mortal: EntityRow, home: EntityRow) -> bool:
    kin = [town for town in await towns_of_people(ctx.session, await people_id_of(ctx.session, home)) if town != home.id]
    other = await ctx.session.get(EntityRow, kin[0]) if kin else None
    if other is None or held(other.id):
        return False
    mortal.location_id = other.id
    return True


async def read_by_folk(ctx: TickContext, mortal: EntityRow, row: BirthSignRow) -> None:
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None:
        return
    if row.dreaded and "infamy" not in profile.locked:
        profile.infamy = clamp_int(profile.infamy + ctx.rules.astrology.dread_infamy, 0, PERCENT)
    elif row.fortune > 0 and "renown" not in profile.locked:
        profile.renown = clamp_int(profile.renown + row.fortune, 0, PERCENT)


async def sign_birth(ctx: TickContext, mortal: EntityRow, tally: SignTally) -> BirthSignRow:
    table = ctx.rules.astrology
    bodies = await celestials_of(ctx, mortal.world_id)
    body = await ruling_body(ctx, mortal.world_id, bodies)
    rng = ctx.rng(f"sign.{mortal.id}")
    dark = any(returns_now(ctx.rules, item, ctx.epoch) and stat_or(item, "brightness", BRIGHT) < BRIGHT for item in bodies)
    dreaded = dark and rng.chance(table.dread_chance)
    influence = SignInfluence.REAL if body is not None and stat_or(body, "influence", 0) >= table.real_influence else SignInfluence.BELIEVED
    fortune = fortune_of(ctx, body, dreaded) if influence is SignInfluence.REAL else 0
    row = BirthSignRow(
        mortal_entity_id=mortal.id,
        season=ctx.epoch % max(1, len(bodies)),
        ruling_celestial_entity_id=body.id if body is not None else None,
        dreaded=dreaded,
        influence=influence,
        fortune=fortune,
        born_epoch=mortal.birth_epoch or ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    if fortune:
        set_stats(mortal, **{key: clamp_int(stat_or(mortal, key, MIDDLING) + fortune, 0, PERCENT) for key in SHAPED})
    home = await town_of(ctx.session, mortal)
    if (
        dreaded
        and home is not None
        and not held(home.id)
        and await reads_stars(ctx, await people_id_of(ctx.session, home))
        and rng.chance(table.foster_chance)
        and await foster_away(ctx, mortal, home)
    ):
        row.exposed = True
        tally.fostered += 1
        await record(ctx, "sign.fostered", roles={IncidentRole.SUBJECT: [mortal.id, home.id]}, facts={"home": str(home.name)})
    if home is not None and await reads_stars(ctx, await people_id_of(ctx.session, home)):
        await read_by_folk(ctx, mortal, row)
    tally.signed += 1
    tally.real += influence is SignInfluence.REAL
    tally.dreaded += dreaded
    return row


async def sign_births(ctx: TickContext, tally: SignTally) -> None:
    signed = select(BirthSignRow.mortal_entity_id)
    born = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.birth_epoch >= ctx.epoch - 1,
            EntityRow.id.not_in(signed),
        )
        .order_by(EntityRow.id)
    )
    for mortal in list(born):
        if not held(mortal.id):
            await sign_birth(ctx, mortal, tally)
    await ctx.session.flush()
