from sqlalchemy import select

from aerona.catalog.flora import world_life
from aerona.catalog.kinds.terraform import TERRAFORM_AIMS
from aerona.catalog.life.cosmos import AIR_GAS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.flora import WorldBiochemistryRow
from aerona.db.tables.physics import TerraformingRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.physics import AirNeed, TerraformAim
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.cosmos.lifeforms import habitability
from aerona.engine.cosmos.orbits import air_band
from aerona.engine.ecology.biochemistry import bearable
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.knowledge import knows
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import scale_stat
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

ABUNDANCE_KEY = "abundance"


def shift(physics: WorldPhysicsRow, key: str, amount: int) -> bool:
    if key in physics.locked or not amount:
        return False
    setattr(physics, key, clamp_percent(getattr(physics, key) + amount))
    return True


def reshape(rules: Rules, physics: WorldPhysicsRow, aim: TerraformAim, step: int, breath: str = AIR_GAS[AirNeed.OXYGEN]) -> bool:
    spec = TERRAFORM_AIMS[aim]
    if spec.reshaping == "pressure":
        if "pressure" in physics.locked:
            return False
        sign = spec.sign
        physics.pressure = max(0.0, round(physics.pressure + sign * step * rules.terraforming.pressure_hundredths / PERCENT, 3))
        return True
    if spec.reshaping == "breathable":
        moved = shift(physics, breath, step)
        for gas in sorted(set(AIR_GAS.values()) - {breath, AIR_GAS[AirNeed.OXYGEN]}):
            moved |= shift(physics, gas, -min(step, getattr(physics, gas)))
        return moved
    key = spec.column or ""
    amount = -min(step, getattr(physics, key)) if spec.floored else spec.sign * step
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
            if TERRAFORM_AIMS[project.aim].touches_air:
                await harm_natives(ctx, world, physics, project)
                await settle_chemistry(ctx, world, physics)
        if "epochs_left" not in project.locked:
            project.epochs_left -= 1
        if project.epochs_left <= 0:
            await record(
                ctx,
                "terraform.finished",
                roles={IncidentRole.SUBJECT: world.id, IncidentRole.ACTOR: project.by_node_id},
                facts={"aim": project.aim, "step": project.step},
                steps=(StepDraft(StepAction.END, actor=project.by_node_id, locus_kind=StepLocus.REALM, locus_node=world.id),),
                world_id=world.id,
            )
            await ctx.session.delete(project)
    await ctx.session.flush()
    return moved


async def begin(
    ctx: TickContext, world_id: int, aim: TerraformAim, by_node_id: int | None, *, step: int | None = None, epochs: int | None = None
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
    await record(
        ctx,
        "terraform.begun",
        roles={IncidentRole.ACTOR: by_node_id, IncidentRole.SUBJECT: world.id},
        facts={"aim": aim, "step": project.step, "epochs": project.epochs_left},
        steps=(StepDraft(StepAction.BEGIN, actor=by_node_id, locus_kind=StepLocus.REALM, locus_node=world.id),),
        world_id=world.id,
    )
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
        await begin(ctx, physics.world_id, aim, people.id)
        working.add(physics.world_id)
        begun += 1
    return begun
