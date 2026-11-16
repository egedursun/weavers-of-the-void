from sqlalchemy import select

from aerona.catalog.flora import world_life
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.flora import WorldBiochemistryRow
from aerona.db.tables.physics import TerraformingRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.physics import AirNeed, TerraformAim
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.cosmos.lifeforms import AIR_GAS, habitability
from aerona.engine.cosmos.orbits import air_band
from aerona.engine.ecology.biochemistry import bearable
from aerona.engine.mind.hooks import judged
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import scale_stat
from aerona.rules.registry import Rules

ABUNDANCE_KEY = "abundance"
AIR_AIMS = frozenset({TerraformAim.THICKEN_AIR, TerraformAim.THIN_AIR, TerraformAim.BREATHABLE_AIR, TerraformAim.WARM, TerraformAim.COOL})
AIM_LABELS: dict[TerraformAim, str] = {
    TerraformAim.THICKEN_AIR: "thicken its air",
    TerraformAim.THIN_AIR: "thin its air",
    TerraformAim.BREATHABLE_AIR: "make its air breathable",
    TerraformAim.WARM: "warm it",
    TerraformAim.COOL: "cool it",
    TerraformAim.WATER: "give it water",
    TerraformAim.DRY: "dry it",
    TerraformAim.BRIGHTEN: "raise its brightness",
    TerraformAim.DARKEN: "lower its brightness",
}


def shift(physics: WorldPhysicsRow, key: str, amount: int) -> bool:
    if key in physics.locked or not amount:
        return False
    setattr(physics, key, clamp_percent(getattr(physics, key) + amount))
    return True


def reshape(rules: Rules, physics: WorldPhysicsRow, aim: TerraformAim, step: int, breath: str = AIR_GAS[AirNeed.OXYGEN]) -> bool:
    if aim in (TerraformAim.THICKEN_AIR, TerraformAim.THIN_AIR):
        if "pressure" in physics.locked:
            return False
        sign = 1 if aim is TerraformAim.THICKEN_AIR else -1
        physics.pressure = max(0.0, round(physics.pressure + sign * step * rules.terraforming.pressure_hundredths / PERCENT, 3))
        return True
    if aim is TerraformAim.BREATHABLE_AIR:
        moved = shift(physics, breath, step)
        for gas in sorted(set(AIR_GAS.values()) - {breath, AIR_GAS[AirNeed.OXYGEN]}):
            moved |= shift(physics, gas, -min(step, getattr(physics, gas)))
        return moved
    moves = {
        TerraformAim.WARM: ("carbon_dioxide", step),
        TerraformAim.COOL: ("carbon_dioxide", -min(step, physics.carbon_dioxide)),
        TerraformAim.WATER: ("hydrosphere", step),
        TerraformAim.DRY: ("hydrosphere", -step),
        TerraformAim.BRIGHTEN: ("albedo", step),
        TerraformAim.DARKEN: ("albedo", -step),
    }
    key, amount = moves[aim]
    return shift(physics, key, amount)


async def harm_natives(ctx: TickContext, world: WorldRow, physics: WorldPhysicsRow, project: TerraformingRow) -> int:
    table = ctx.rules.terraforming
    allowed = world_life(world.world_type, air_band(ctx.rules, physics))
    harmed = 0
    for species in await canon(ctx.session, [EntityType.SPECIES], world.id):
        profile = await ctx.session.get(SpeciesProfileRow, species.id)
        if profile is None or held(species.id) or bearable(profile.biochemistry, allowed):
            continue
        scale_stat(ctx.rules, species, ABUNDANCE_KEY, (PERCENT - table.native_harm_pct) / PERCENT)
        harmed += 1
    if harmed and "biosphere_health" not in world.locked:
        world.biosphere_health = clamp_percent(world.biosphere_health - table.biosphere_harm)
    if harmed and project.by_node_id is not None:
        natives = sorted(await canon(ctx.session, COMMUNITY_TYPES, world.id), key=lambda row: row.id)
        if natives:
            await judged(ctx, project.by_node_id, natives[0].id, ActKind.DESECRATION, note=f"unmade the native life of {world.name}")
    return harmed


async def settle_chemistry(ctx: TickContext, world: WorldRow, physics: WorldPhysicsRow) -> None:
    allowed = set(world_life(world.world_type, air_band(ctx.rules, physics)))
    present = set(await ctx.session.scalars(select(WorldBiochemistryRow.biochemistry).where(WorldBiochemistryRow.world_id == world.id)))
    for biochemistry in sorted(allowed - present):
        ctx.session.add(WorldBiochemistryRow(world_id=world.id, biochemistry=biochemistry))


async def breath_of(ctx: TickContext, maker_id: int | None) -> str:
    biology = await ctx.session.get(PeopleBiologyRow, maker_id) if maker_id is not None else None
    return AIR_GAS.get(biology.air, AIR_GAS[AirNeed.OXYGEN]) if biology is not None else AIR_GAS[AirNeed.OXYGEN]


async def terraform_cycle(ctx: TickContext) -> int:
    moved = 0
    for project in list(await ctx.session.scalars(select(TerraformingRow).order_by(TerraformingRow.id))):
        world = await ctx.session.get(WorldRow, project.world_id)
        physics = await ctx.session.get(WorldPhysicsRow, project.world_id)
        if world is None or physics is None or held(world.id) or (project.by_node_id is not None and held(project.by_node_id)):
            continue
        if reshape(ctx.rules, physics, project.aim, project.step, await breath_of(ctx, project.by_node_id)):
            moved += 1
            if project.aim in AIR_AIMS:
                await harm_natives(ctx, world, physics, project)
                await settle_chemistry(ctx, world, physics)
        if "epochs_left" not in project.locked:
            project.epochs_left -= 1
        if project.epochs_left <= 0:
            await note(
                ctx,
                f"The work to {AIM_LABELS[project.aim]} came to its end on {world.name}.",
                key="terraform.finished",
                world_id=world.id,
                kind=ChronicleKind.WORLD,
            )
            await ctx.session.delete(project)
    await ctx.session.flush()
    return moved


async def begin(
    ctx: TickContext, world_id: int, aim: TerraformAim, by_node_id: int | None, by: str, *, step: int | None = None, epochs: int | None = None
) -> TerraformingRow:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    if await ctx.session.get(WorldPhysicsRow, world_id) is None:
        raise ValidationFailedError(f"{world.name} has no physics to reshape yet; let an epoch pass first.")
    table = ctx.rules.terraforming
    project = TerraformingRow(
        world_id=world.id,
        aim=aim,
        by_node_id=by_node_id,
        step=max(1, min(PERCENT, step if step is not None else table.step)),
        epochs_left=max(1, epochs if epochs is not None else table.epochs),
        started_epoch=max(1, ctx.epoch),
        locked=[],
    )
    ctx.session.add(project)
    await note(ctx, f"{by} began to {AIM_LABELS[aim]}: {world.name}.", key="terraform.begun", world_id=world.id, kind=ChronicleKind.MIRACLE)
    await ctx.session.flush()
    return project


def wanted_aim(biology: PeopleBiologyRow, physics: WorldPhysicsRow, rules: Rules) -> TerraformAim | None:
    gas = AIR_GAS.get(biology.air)
    if gas is not None and getattr(physics, gas) < rules.life_classes.breathable_oxygen:
        return TerraformAim.BREATHABLE_AIR
    if physics.pressure < rules.orbits.thin_air_hundredths / PERCENT:
        return TerraformAim.THICKEN_AIR
    if physics.hydrosphere < rules.planetary_climate.drought_hydrosphere:
        return TerraformAim.WATER
    return None


async def powers_reshape(ctx: TickContext) -> int:
    table = ctx.rules.terraforming
    begun = 0
    working = set(await ctx.session.scalars(select(TerraformingRow.world_id)))
    for people in sorted(await canon(ctx.session, [EntityType.PEOPLE]), key=lambda row: row.id):
        if held(people.id) or (people.civ_tier or 0) < table.polity_tier or people.world_id in working:
            continue
        if not await knows(ctx.session, people.id, KnowledgeBranch.SKY_NAVIGATION):
            continue
        biology = await ctx.session.get(PeopleBiologyRow, people.id)
        physics = await ctx.session.get(WorldPhysicsRow, people.world_id) if people.world_id is not None else None
        if biology is None or physics is None or held(physics.world_id):
            continue
        if await habitability(ctx.session, ctx.rules, biology, people.world_id) >= ctx.rules.life_classes.settle_floor:
            continue
        aim = wanted_aim(biology, physics, ctx.rules)
        if aim is None or not ctx.rng(f"terraform.{people.id}.{ctx.epoch}").chance(table.polity_chance):
            continue
        await begin(ctx, physics.world_id, aim, people.id, people.name)
        working.add(physics.world_id)
        begun += 1
    return begun
