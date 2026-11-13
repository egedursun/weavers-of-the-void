from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.battle_depth import BASE_DISCIPLINE, formation_for
from aerona.catalog.equipment import ROLE_ARMS, UNIT_SLOTS
from aerona.catalog.techniques import UNIT_TECHNIQUES
from aerona.catalog.units import ROLE_STYLES, UNITS, weapon_of
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import UnitDesignEquipmentRow, UnitDesignTechniqueRow
from aerona.db.tables.military import ArmyTemplateRow, ArmyUnitRow, UnitDesignRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.equipment import ArmamentSlot
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.collective.makers import makers_of
from aerona.engine.context import TickContext
from aerona.engine.equipment.models import model_for
from aerona.engine.military.templates import weights_of
from aerona.engine.military.units import allowed, choose_design, design_spec, designs_of
from aerona.engine.notes import note
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.queries import living_entity
from aerona.engine.vehicles.fleet import CREW_ROLES, role_design

S = ArmamentSlot


BACKFILL = "unit_types.reach_the_world"


@dataclass
class TypeTally:
    linked: int = 0
    drawn: int = 0
    refitted: int = 0
    spread: int = 0


async def types_of(session: AsyncSession, owner_id: int) -> list[UnitDesignRow]:
    statement = select(UnitDesignRow).where(UnitDesignRow.owner_entity_id == owner_id, UnitDesignRow.retired.is_(False))
    return list(await session.scalars(statement.order_by(UnitDesignRow.id)))


async def doctrine_of(session: AsyncSession, owner: EntityRow) -> PeopleCultureRow | None:
    people = await people_of(session, owner)
    return await session.get(PeopleCultureRow, people.id) if people is not None else None


async def style_for(session: AsyncSession, owner: EntityRow | None, role: UnitKind) -> MartialStyle:
    culture = await doctrine_of(session, owner) if owner is not None else None
    return culture.martial_style if culture is not None and culture.martial_style is not None else ROLE_STYLES[role]


async def loadout(ctx: TickContext, owner: EntityRow, role: UnitKind, knowledge: KnowledgeMap) -> list[int]:
    spec = UNITS[role]
    found = []
    kit = ROLE_ARMS[role]
    for slot in UNIT_SLOTS[spec.family]:
        if slot not in kit or (slot is S.MISSILE_WEAPON and spec.missile <= 0) or (slot is S.SHIELD and spec.shield.value == "none"):
            continue
        model = await model_for(ctx, owner, slot, knowledge, kit[slot])
        if model is not None:
            found.append(model.id)
    return found


async def draw_type(
    ctx: TickContext, owner: EntityRow, role: UnitKind, knowledge: KnowledgeMap, *, parent: UnitDesignRow | None = None, name: str | None = None
) -> UnitDesignRow:
    spec = UNITS[role]
    profile = weapon_of(spec)
    vehicle = await role_design(ctx, owner, role, knowledge) if role in CREW_ROLES else None
    row = UnitDesignRow(
        name=name or (parent.name if parent is not None else await made_name(ctx.session, ctx.rules, owner, spec.label, role.value, ctx.epoch)),
        base_kind=role,
        family=spec.family,
        melee=spec.melee,
        missile=spec.missile,
        defence=spec.defence,
        speed=spec.speed,
        mass=spec.mass,
        cost=spec.cost,
        upkeep=spec.upkeep,
        armour=spec.armour,
        shield=spec.shield,
        terror=spec.terror,
        counters_charge=spec.counters_charge,
        flying=spec.flying,
        social_class=spec.social_class,
        owner_entity_id=owner.id,
        origin_node_id=owner.id,
        world_id=owner.world_id,
        created_epoch=ctx.epoch,
        retired=False,
        reach=profile.reach,
        volleys=profile.volleys,
        accuracy=profile.accuracy,
        piercing=profile.piercing,
        doctrine=await style_for(ctx.session, owner, role),
        formation=formation_for(role, spec.family),
        discipline=BASE_DISCIPLINE[role],
        training_epochs=1 + spec.level,
        vehicle_design_id=vehicle.id if vehicle is not None else None,
        crew_per_vehicle=vehicle.crew if vehicle is not None else 0,
        parent_design_id=parent.id if parent is not None else None,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    for model_id in await loadout(ctx, owner, role, knowledge):
        ctx.session.add(UnitDesignEquipmentRow(design_id=row.id, model_id=model_id, count=1))
    needed = UNIT_TECHNIQUES.get(role)
    if needed is not None:
        ctx.session.add(UnitDesignTechniqueRow(design_id=row.id, technique=needed))
    await ctx.session.flush()
    return row


async def loadout_ids(session: AsyncSession, design_id: int) -> set[int]:
    return set(await session.scalars(select(UnitDesignEquipmentRow.model_id).where(UnitDesignEquipmentRow.design_id == design_id)))


async def refit_type(ctx: TickContext, design: UnitDesignRow, owner: EntityRow, knowledge: KnowledgeMap) -> UnitDesignRow | None:
    current = await loadout_ids(ctx.session, design.id)
    newer = set(await loadout(ctx, owner, design.base_kind, knowledge))
    if not newer - current:
        return None
    successor = await draw_type(ctx, owner, design.base_kind, knowledge, parent=design)
    design.retired = True
    return successor


async def copy_type(ctx: TickContext, design: UnitDesignRow, taker: EntityRow) -> UnitDesignRow:
    spec = design_spec(design)
    row = UnitDesignRow(
        name=design.name,
        base_kind=design.base_kind,
        family=design.family,
        melee=spec.melee,
        missile=spec.missile,
        defence=spec.defence,
        speed=spec.speed,
        mass=spec.mass,
        cost=spec.cost,
        upkeep=spec.upkeep,
        armour=spec.armour,
        shield=spec.shield,
        terror=spec.terror,
        counters_charge=spec.counters_charge,
        flying=spec.flying,
        social_class=spec.social_class,
        owner_entity_id=taker.id,
        origin_node_id=design.origin_node_id,
        world_id=taker.world_id,
        description=design.description,
        doctrine=design.doctrine,
        formation=design.formation,
        discipline=design.discipline,
        training_epochs=design.training_epochs,
        mount_species_id=design.mount_species_id,
        vehicle_design_id=design.vehicle_design_id,
        crew_per_vehicle=design.crew_per_vehicle,
        parent_design_id=design.id,
        created_epoch=ctx.epoch,
        retired=False,
        reach=design.reach,
        volleys=design.volleys,
        accuracy=design.accuracy,
        piercing=design.piercing,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def wanted_roles(ctx: TickContext) -> dict[int, dict[UnitKind, bool]]:
    wanted: dict[int, dict[UnitKind, bool]] = {}
    for template in await ctx.session.scalars(select(ArmyTemplateRow).where(ArmyTemplateRow.active.is_(True)).order_by(ArmyTemplateRow.id)):
        for role in weights_of(template):
            wanted.setdefault(template.polity_entity_id, {}).setdefault(role, False)
    armies = await ctx.session.execute(
        select(ArmyRow.owner_entity_id, ArmyUnitRow.kind)
        .join(ArmyUnitRow, ArmyUnitRow.army_entity_id == ArmyRow.entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), ArmyUnitRow.count > 0)
        .order_by(ArmyRow.entity_id, ArmyUnitRow.id)
    )
    for owner_id, kind in list(armies):
        owner = await living_entity(ctx.session, owner_id)
        if owner is not None:
            wanted.setdefault((await makers_of(ctx.session, owner))[-1], {})[kind] = True
    return wanted


async def marshal_types(ctx: TickContext, knowledge: KnowledgeMap, tally: TypeTally, *, every: bool) -> None:
    table = ctx.rules.unit_types
    for holder_id, roles in sorted((await wanted_roles(ctx)).items()):
        realm = await living_entity(ctx.session, holder_id)
        if realm is None or held(realm.id):
            continue
        have = {design.base_kind: design for design in await types_of(ctx.session, realm.id)}
        for role, fielded in roles.items():
            design = have.get(role)
            chosen = every or fielded or ctx.rng(f"unit_type.{realm.id}.{role.value}.{ctx.epoch}").chance(table.draw_pct)
            if design is None and (fielded or allowed(UNITS[role], realm.id, knowledge)) and chosen:
                drawn = await draw_type(ctx, realm, role, knowledge)
                tally.drawn += 1
                await note(ctx, f"{realm.name} raised a new kind of soldier: {drawn.name}.", key="unit_types.drawn", ids=[realm.id])
            elif design is not None and "retired" not in design.locked and ctx.rng(f"unit_refit.{design.id}.{ctx.epoch}").chance(table.refit_pct):
                newer = await refit_type(ctx, design, realm, knowledge)
                tally.refitted += newer is not None


async def link_stacks(ctx: TickContext, knowledge: KnowledgeMap, tally: TypeTally) -> None:
    armies = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))
    for army in list(armies):
        owner = await living_entity(ctx.session, army.owner_entity_id)
        if owner is None or held(army.entity_id):
            continue
        designs = await designs_of(ctx.session, owner)
        metallurgy = knowledge.level(owner.id, KnowledgeBranch.METALLURGY)
        for stack in await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army.entity_id, ArmyUnitRow.design_id.is_(None))):
            if "design_id" in (stack.locked or []):
                continue
            design = await choose_design(ctx, owner, stack.kind, stack.count, metallurgy=metallurgy, designs=designs)
            if design is not None:
                stack.design_id = design.id
                tally.linked += 1


async def settle_doctrines(ctx: TickContext) -> int:
    settled = 0
    for design in list(await ctx.session.scalars(select(UnitDesignRow).where(UnitDesignRow.doctrine.is_(None)).order_by(UnitDesignRow.id))):
        owner = await living_entity(ctx.session, design.owner_entity_id) if design.owner_entity_id is not None else None
        if "doctrine" in design.locked or (owner is not None and held(owner.id)):
            continue
        design.doctrine = await style_for(ctx.session, owner, design.base_kind)
        settled += 1
    return settled


async def spread_types(ctx: TickContext, tally: TypeTally) -> None:
    table = ctx.rules.unit_types
    allies = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    )
    for giver_id, taker_id in list(allies):
        taker = await living_entity(ctx.session, taker_id)
        if taker is None or held(taker.id):
            continue
        roles = {design.base_kind for design in await types_of(ctx.session, taker.id)}
        for design in await types_of(ctx.session, giver_id):
            if design.base_kind in roles or not ctx.rng(f"unit_spread.{design.id}.{taker.id}.{ctx.epoch}").chance(table.spread_pct):
                continue
            await copy_type(ctx, design, taker)
            tally.spread += 1
            break


async def run_unit_types(ctx: TickContext) -> TypeTally:
    tally = TypeTally()
    knowledge = await KnowledgeMap.load(ctx.session)
    first = await ctx.session.get(AppliedFixupRow, BACKFILL) is None
    await marshal_types(ctx, knowledge, tally, every=first)
    await spread_types(ctx, tally)
    await link_stacks(ctx, knowledge, tally)
    if first:
        ctx.session.add(AppliedFixupRow(key=BACKFILL, result={"drawn": tally.drawn, "linked": tally.linked, "doctrines": await settle_doctrines(ctx)}))
    return tally
