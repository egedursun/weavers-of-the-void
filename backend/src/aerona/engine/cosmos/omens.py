from collections import Counter

from sqlalchemy import select

from aerona.catalog.lore import DOMAIN_SCHOOLS
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import CelestialReadingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OmenReading
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.book import values_of
from aerona.engine.notes import note
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import shift_bounded, stat_or
from aerona.rules.registry import Rules

BRIGHT = PERCENT // 2


def influence_share(body: EntityRow) -> float:
    influence = stat_or(body, "influence", 0)
    visibility = stat_or(body, "visibility", PERCENT)
    return influence / PERCENT * visibility / PERCENT


def reading_of(rules: Rules, body: EntityRow, superstition: int) -> OmenReading:
    table = rules.celestial_bodies
    bright = stat_or(body, "brightness", BRIGHT) >= BRIGHT
    if superstition >= table.superstition_evil and not bright:
        return OmenReading.EVIL
    if superstition <= table.superstition_good and bright:
        return OmenReading.GOOD
    return OmenReading.NEUTRAL


def returns_now(rules: Rules, body: EntityRow, epoch: int) -> bool:
    cycle = stat_or(body, "cycle", 0)
    if cycle <= 0:
        return False
    years = rules.time.years_per_epoch
    return (epoch * years) // cycle != ((epoch - 1) * years) // cycle


async def epoch_body(ctx: TickContext, world: WorldRow) -> EntityRow | None:
    if world.epoch_star_entity_id is None:
        return None
    body = await ctx.session.get(EntityRow, world.epoch_star_entity_id)
    return body if body is not None and body.entity_type is EntityType.CELESTIAL else None


async def celestial_rite_pct(ctx: TickContext, world_id: int | None, school: MagicSchool) -> float:
    world = await ctx.session.get(WorldRow, world_id) if world_id is not None else None
    body = await epoch_body(ctx, world) if world is not None else None
    if body is None or body.domain is None or school not in DOMAIN_SCHOOLS.get(body.domain, ()):
        return 1.0
    return 1 + influence_share(body) * ctx.rules.celestial_bodies.rite_pct / PERCENT


async def read_body(ctx: TickContext, body: EntityRow, peoples: list[EntityRow]) -> Counter[OmenReading]:
    tally: Counter[OmenReading] = Counter()
    for people in peoples:
        row = await ctx.session.get(CelestialReadingRow, (body.id, people.id))
        if row is not None and "reading" in row.locked:
            tally[row.reading] += 1
            continue
        reading = reading_of(ctx.rules, body, (await values_of(ctx.session, people)).get(ValueAxis.SUPERSTITION, 0))
        if row is None:
            row = CelestialReadingRow(celestial_entity_id=body.id, people_entity_id=people.id, reading=reading, epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
        else:
            row.reading, row.epoch = reading, ctx.epoch
        tally[reading] += 1
    return tally


async def body_returns(ctx: TickContext, world: WorldRow, body: EntityRow, peoples: list[EntityRow], tally: Counter[OmenReading]) -> None:
    table = ctx.rules.celestial_bodies
    for people in peoples:
        row = await ctx.session.get(CelestialReadingRow, (body.id, people.id))
        reading = row.reading if row is not None else OmenReading.NEUTRAL
        shift = {OmenReading.GOOD: table.return_piety, OmenReading.EVIL: -table.return_piety, OmenReading.NEUTRAL: 0}[reading]
        if shift:
            shift_bounded(ctx.rules, people, "piety", shift)
    if tally[OmenReading.EVIL] > len(peoples) / 2:
        await advance_doom(ctx.session, ctx.rules, table.return_doom)
    await note(ctx, f"{body.name} returned to the skies of {world.name}.", key="celestial.returned", ids=[body.id], world_id=world.id, kind=ChronicleKind.SKY)


async def epoch_body_sway(ctx: TickContext, world: WorldRow) -> None:
    table = ctx.rules.celestial_bodies
    body = await epoch_body(ctx, world)
    if body is None or body.domain is None:
        return
    share = influence_share(body)
    for cult in await canon(ctx.session, [EntityType.CULT], world.id):
        patron = await ctx.session.get(SonRow, cult.creator_son_id) if cult.creator_son_id is not None else None
        if patron is not None and body.domain in (patron.domain_primary, patron.domain_secondary) and not held(cult.id):
            shift_bounded(ctx.rules, cult, "piety", round(share * table.piety_pct / 10))
    if MagicSchool.DIVINATION in DOMAIN_SCHOOLS.get(body.domain, ()):
        for prophecy in await canon(ctx.session, [EntityType.PROPHECY], world.id):
            if not held(prophecy.id):
                shift_bounded(ctx.rules, prophecy, "certainty", round(share * table.prophecy_pct / 10))


@reads("celestial.brightness", "celestial.cycle", "table.celestial_readings")
@writes("table.celestial_readings")
async def celestial_omens(ctx: TickContext) -> None:
    for world in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id)):
        if held(world.id):
            continue
        peoples = [people for people in await canon(ctx.session, [EntityType.PEOPLE], world.id) if not held(people.id)]
        for body in await canon(ctx.session, [EntityType.CELESTIAL], world.id):
            if held(body.id):
                continue
            tally = await read_body(ctx, body, peoples)
            if returns_now(ctx.rules, body, ctx.epoch):
                await body_returns(ctx, world, body, peoples, tally)
        await epoch_body_sway(ctx, world)
    await ctx.session.flush()
