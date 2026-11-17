from types import MappingProxyType

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.engine.context import TickContext
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.kinship import widow
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

HARM_DEATHS: MappingProxyType[HarmCause, DeathCause] = total(
    HarmCause,
    {
        HarmCause.BATTLE: DeathCause.BATTLE,
        HarmCause.DUEL: DeathCause.DUEL,
        HarmCause.PUNISHMENT: DeathCause.EXECUTION,
        HarmCause.TORTURE: DeathCause.EXECUTION,
        HarmCause.ACCIDENT: DeathCause.ACCIDENT,
        HarmCause.MONSTER: DeathCause.MONSTER,
        HarmCause.DISASTER: DeathCause.DISASTER,
        HarmCause.CURSE: DeathCause.CURSE,
        HarmCause.MAGIC_BACKLASH: DeathCause.MAGIC,
        HarmCause.GOD: DeathCause.DIVINE,
        HarmCause.POISON: DeathCause.POISON,
        HarmCause.QUEST: DeathCause.HARDSHIP,
        HarmCause.ESCAPE: DeathCause.MURDER,
        HarmCause.SACRIFICE: DeathCause.SACRIFICE,
        HarmCause.AGE: DeathCause.OLD_AGE,
        HarmCause.PLAYER: DeathCause.DIVINE,
        HarmCause.EXPOSURE: DeathCause.EXPOSURE,
        HarmCause.RITUAL: DeathCause.ACCIDENT,
        HarmCause.BOMBARDMENT: DeathCause.BOMBARDMENT,
        HarmCause.INDUSTRIAL: DeathCause.INDUSTRIAL,
        HarmCause.CRASH: DeathCause.CRASH,
        HarmCause.RADIATION: DeathCause.RADIATION,
        HarmCause.DECOMPRESSION: DeathCause.DECOMPRESSION,
        HarmCause.EXPERIMENT: DeathCause.EXPERIMENT,
        HarmCause.POWER: DeathCause.MAGIC,
    },
)
GLORIOUS_DEATHS = frozenset({DeathCause.BATTLE, DeathCause.DUEL, DeathCause.MONSTER, DeathCause.SACRIFICE})
SHAMEFUL_DEATHS = frozenset({DeathCause.EXECUTION, DeathCause.DESPAIR})


def manner_of(harm: HarmCause | None, default: DeathCause = DeathCause.UNKNOWN) -> DeathCause:
    return HARM_DEATHS.get(harm, default) if harm is not None else default


async def death_place(ctx: TickContext, mortal: EntityRow) -> int | None:
    location = await living_entity(ctx.session, mortal.location_id) if mortal.location_id is not None else None
    if location is not None:
        return location.id
    atlas = await RegionAtlas.load(ctx.session)
    return atlas.top_region(mortal.id)


async def house_prestige(ctx: TickContext, mortal: EntityRow, manner: DeathCause) -> int:
    table = ctx.rules.standing
    change = table.glorious_death_prestige if manner in GLORIOUS_DEATHS else -table.shameful_death_prestige if manner in SHAMEFUL_DEATHS else 0
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
            facts={"manner": manner, "prestige": changed},
        )
    return changed


async def record_end(ctx: TickContext, mortal: EntityRow, manner: DeathCause) -> None:
    profile, _ = await ensure_profile(ctx.session, mortal.id, ctx.epoch)
    if not is_held(profile, "cause_of_death"):
        profile.cause_of_death = manner
    if not is_held(profile, "death_place_id"):
        profile.death_place_id = await death_place(ctx, mortal)
    kinship = ctx.rules.kinship
    for spouse in await widow(ctx.session, mortal.id, ctx.epoch):
        await remember(
            ctx.session, ctx.rules, holder_id=spouse, subject_id=mortal.id, kind=MemoryKind.LAMENTED, magnitude=kinship.widowed_magnitude, epoch=ctx.epoch
        )
    for kin_id in await close_kin_of(ctx.session, mortal.id):
        if await living_entity(ctx.session, kin_id) is not None:
            await add_stress(ctx.session, kin_id, ctx.rules.stress.loss_stress, ctx.epoch)
    await house_prestige(ctx, mortal, manner)
