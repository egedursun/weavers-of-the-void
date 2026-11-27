from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.death_causes import death_cause_of
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause, DeathReading
from aerona.engine.context import TickContext
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.kinship import widow
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.mortal.readings import reading_for
from aerona.engine.mortal.standing import add_renown, add_stress
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

GLORY: Mapping[DeathReading, int] = total(
    DeathReading,
    {DeathReading.GLORIOUS: 2, DeathReading.HONOURABLE: 1, DeathReading.PLAIN: 0, DeathReading.SHAMEFUL: -1, DeathReading.CURSED: -2, DeathReading.PITIED: 0},
)


def manner_of(harm: HarmCause | None, default: DeathCause = DeathCause.UNKNOWN, damage: DamageType | None = None) -> DeathCause:
    return death_cause_of(harm, damage, default)


async def death_place(ctx: TickContext, mortal: EntityRow) -> int | None:
    location = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
    if location is not None:
        return location.id
    atlas = await RegionAtlas.load(ctx.session)
    return atlas.top_region(mortal.id)


async def pity_household(ctx: TickContext, mortal: EntityRow) -> None:
    household = await ctx.session.scalar(select(HouseholdRow).where(HouseholdRow.head_node_id == mortal.id).limit(1))
    if household is None or "wealth" in (household.locked or []) or held(mortal.id):
        return
    household.wealth += ctx.rules.life_course.pitied_care


async def house_prestige(ctx: TickContext, mortal: EntityRow, manner: DeathCause) -> int:
    table = ctx.rules.standing
    glory = GLORY[await reading_for(ctx.session, ctx.rules, mortal, manner)]
    change = table.glorious_death_prestige * glory // 2 if glory > 0 else table.shameful_death_prestige * glory // 2 if glory < 0 else 0
    if glory > 1:
        await add_renown(ctx.session, mortal.id, ctx.rules.death_readings.glorious_renown, ctx.epoch)
    if not change:
        return 0
    changed = 0
    for row in await ctx.session.scalars(select(HouseMemberRow).where(HouseMemberRow.mortal_entity_id == mortal.id)):
        house = await ctx.session.get(HouseProfileRow, row.house_entity_id)
        if house is None or "prestige" in (house.locked or []):
            continue
        house.prestige = clamp_int(house.prestige + change, 0, 100)
        changed += change
    if changed:
        await record(
            ctx,
            "mortal.death_prestige" if changed > 0 else "mortal.death_shame",
            roles={IncidentRole.SUBJECT: mortal.id},
            facts={"manner": manner, "prestige": changed, "reading": await reading_for(ctx.session, ctx.rules, mortal, manner)},
        )
    return changed


async def record_end(ctx: TickContext, mortal: EntityRow, manner: DeathCause) -> None:
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    if not is_held(profile, "cause_of_death"):
        profile.cause_of_death = manner
    if not is_held(profile, "death_place_id"):
        profile.death_place_id = await death_place(ctx, mortal)
    if not is_held(profile, "health"):
        profile.health = 0
    kinship = ctx.rules.kinship
    reading = await reading_for(ctx.session, ctx.rules, mortal, manner)
    lament = kinship.widowed_magnitude * (ctx.rules.death_readings.lament_pct / PERCENT if abs(GLORY[reading]) > 1 else 1)
    for spouse in await widow(ctx.session, mortal.id, ctx.epoch):
        await remember(ctx.session, ctx.rules, holder_id=spouse, subject_id=mortal.id, kind=MemoryKind.LAMENTED, magnitude=lament, epoch=ctx.epoch)
    for kin_id in await close_kin_of(ctx.session, mortal.id):
        if await living_entity(ctx.session, kin_id) is not None:
            await add_stress(ctx.session, kin_id, ctx.rules.stress.loss_stress, ctx.epoch)
    if reading is DeathReading.PITIED:
        await pity_household(ctx, mortal)
    await house_prestige(ctx, mortal, manner)
