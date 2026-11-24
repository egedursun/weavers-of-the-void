from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.cosmography import GalacticStructureRow, GalaxyRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import GalacticStructureKind, PhenomenonCause, PhenomenonKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.cosmos.climate import cold_snap
from aerona.engine.cosmos.ladder import settle_star
from aerona.engine.cosmos.phenomena import form_phenomenon
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.environment.long_seasons import supernova_winter
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import record


async def after_supernova(ctx: TickContext, star: StarRow) -> None:
    galaxy = await ctx.session.get(GalaxyRow, star.galaxy_id) if star.galaxy_id is not None else None
    if galaxy is not None and not held(galaxy.id):
        if "metallicity" not in galaxy.locked:
            galaxy.metallicity = clamp_int(galaxy.metallicity + ctx.rules.galaxies.metallicity_per_supernova, 0, PERCENT)
        remnant = GalacticStructureRow(
            galaxy_id=galaxy.id,
            kind=GalacticStructureKind.SUPERNOVA_REMNANT,
            name=f"Remnant of {star.name}",
            x=star.x,
            y=star.y,
            radius=galaxy.radius * ctx.rules.galaxies.core_reach_pct / PERCENT,
            intensity=PERCENT,
            created_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(remnant)
        await ctx.session.flush()
        if not held(star.id):
            settle_star(ctx.rules, await Cosmography.load(ctx.session), star)
    cosmography = await Cosmography.load(ctx.session)
    for world in cosmography.worlds.values():
        if held(world.id) or cosmography.place_world(world).star is not star:
            continue
        winter = await supernova_winter(ctx, world, star.id)
        cooled = 0 if winter is not None else await cold_snap(ctx, world.id, ctx.rules.world_life.supernova_cold)
        if cooled:
            await record(
                ctx,
                "climate.star_cold",
                roles={IncidentRole.ACTOR: star.id, IncidentRole.SUBJECT: world.id},
                facts={"cold": ctx.rules.world_life.supernova_cold, "regions": cooled},
                world_id=world.id,
            )
        regions = sorted(await canon(ctx.session, [EntityType.REGION], world.id), key=lambda row: row.id)
        rng = ctx.rng(f"supernova_shard.{star.id}.{world.id}")
        if regions and rng.chance(ctx.rules.phenomena.sky_shard_chance):
            await form_phenomenon(ctx, PhenomenonKind.MINERAL_GROWTH, rng.pick(regions), PhenomenonCause.SKY_EVENT, cause_node_id=star.id)
