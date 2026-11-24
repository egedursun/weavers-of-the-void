from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domestication import KEPT_STAGES
from aerona.catalog.life.domain import GROWN
from aerona.core.grammar import an
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesProfileRow, SpeciesUseRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import AnimalRole, BeastTemper
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.beasts import profile_beast
from aerona.engine.mind.grief import start_grief
from aerona.engine.mind.hooks import practised
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import StepDraft, record

PET_USES = frozenset({AnimalRole.COMPANION, AnimalRole.GUARD, AnimalRole.WAR, AnimalRole.PEST_CONTROL})
HUNTING_USES = frozenset({AnimalRole.HUNTING})


@dataclass
class PetTally:
    taken: int = 0
    mourned: int = 0
    orphaned: int = 0
    comforted: int = 0
    hunted: int = 0


async def pet_of(ctx: TickContext, owner_id: int) -> EntityRow | None:
    for bond in await active_bonds(ctx.session, [BondKind.PET_OF], targets=[owner_id]):
        beast = await living_entity(ctx.session, bond.source_node_id)
        if beast is not None:
            return beast
    return None


async def pet_kind_ids(session: AsyncSession, community_id: int | None) -> list[int]:
    if community_id is None:
        return []
    uses = select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use.in_(list(PET_USES)))
    kept = select(HerdRow.species_entity_id).where(
        HerdRow.community_entity_id == community_id, HerdRow.head > 0, HerdRow.stage.in_(list(KEPT_STAGES)), HerdRow.species_entity_id.in_(uses)
    )
    return list(await session.scalars(kept.order_by(HerdRow.species_entity_id)))


async def animal_kind_ids(session: AsyncSession) -> list[int]:
    statement = (
        select(SpeciesProfileRow.species_entity_id)
        .join(EntityRow, EntityRow.id == SpeciesProfileRow.species_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, SpeciesProfileRow.species_class.not_in(list(GROWN)))
        .order_by(EntityRow.name, EntityRow.id)
    )
    return list(await session.scalars(statement))


async def pet_kinds(ctx: TickContext, community_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    for species_id in await pet_kind_ids(ctx.session, community_id):
        species = await living_entity(ctx.session, species_id)
        if species is not None:
            found.append(species)
    return found


async def hunting_kinds(session: AsyncSession, species_ids: list[int]) -> set[int]:
    if not species_ids:
        return set()
    used = set(
        await session.scalars(
            select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.species_entity_id.in_(species_ids), SpeciesUseRow.use.in_(list(HUNTING_USES)))
        )
    )
    flying = set(
        await session.scalars(select(EntityTraitRow.entity_id).where(EntityTraitRow.entity_id.in_(species_ids), EntityTraitRow.trait == CreatureTrait.FLYING))
    )
    return used | flying


async def take_pet(ctx: TickContext, owner: EntityRow, species: EntityRow) -> EntityRow:
    profile = await ctx.session.get(SpeciesProfileRow, species.id)
    pet = await create_record(
        ctx,
        RecordSpec(
            name=f"{species.name} of {owner.name}",
            entity_type=EntityType.BEAST,
            stats=BeastStats(hp=stat(species, "hp"), danger=0, strength=stat(species, "strength"), agility=stat(species, "agility"), terror=0, renown=0),
            body=f"{an(species.name, capital=True)} that {owner.name} keeps at their side.",
            power=1,
            world_id=owner.world_id,
            location_id=owner.location_id,
            subtype="pet",
        ),
    )
    row = await profile_beast(ctx, pet, species, size=profile.size_class if profile is not None else None)
    row.temper, row.bound_to_node_id, row.lair_place_id = BeastTemper.COMPANION, owner.id, None
    row.lifespan = max(1, profile.lifespan_years if profile is not None else row.lifespan)
    await connect(ctx.session, pet.id, owner.id, BondKind.PET_OF, ctx.epoch, description="kept at their side")
    return pet


async def adopt_pets(ctx: TickContext) -> int:
    table = ctx.rules.husbandry
    owners = set(await ctx.session.scalars(select(BondRow.target_node_id).where(BondRow.kind == BondKind.PET_OF, BondRow.state == BondState.ACTIVE)))
    living = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
    mortals = await ctx.session.scalars(living.order_by(EntityRow.id))
    taken = 0
    kinds_of: dict[int, list[EntityRow]] = {}
    for mortal in list(mortals):
        if mortal.id in owners or held(mortal.id) or mortal.location_id is None:
            continue
        if mortal.location_id not in kinds_of:
            kinds_of[mortal.location_id] = await pet_kinds(ctx, mortal.location_id)
        kinds = kinds_of[mortal.location_id]
        rng = ctx.rng(f"pet.{mortal.id}.{ctx.epoch}")
        if not kinds or not rng.chance(table.pet_chance):
            continue
        species = rng.pick(kinds)
        pet = await take_pet(ctx, mortal, species)
        taken += 1
        await record(
            ctx,
            "pets.taken",
            roles={IncidentRole.OWNER: mortal.id, IncidentRole.SUBJECT: pet.id, IncidentRole.ORIGIN: species.id},
            steps=(StepDraft(StepAction.BEFRIEND, actor=mortal.id, target=pet.id),),
            place=mortal.location_id,
        )
    return taken


async def hunts_beside(ctx: TickContext, pet: EntityRow) -> bool:
    row = await ctx.session.get(BeastProfileRow, pet.id)
    return row is not None and row.species_entity_id is not None and row.species_entity_id in await hunting_kinds(ctx.session, [row.species_entity_id])


async def tend_pets(ctx: TickContext) -> PetTally:
    tally = PetTally()
    for bond in await active_bonds(ctx.session, [BondKind.PET_OF]):
        pet = await ctx.session.get(EntityRow, bond.source_node_id)
        owner = await ctx.session.get(EntityRow, bond.target_node_id)
        if pet is None or owner is None or held(pet.id, owner.id):
            continue
        if pet.status is not EntityStatus.CANON:
            await close(ctx.session, bond, ctx.epoch, "the pet died")
            if owner.status is EntityStatus.CANON:
                await think(ctx.session, ctx.rules, owner.id, ThoughtKind.LOST_PET, ctx.epoch, subject_id=pet.id)
                await start_grief(ctx.session, ctx.rules, owner.id, pet.id, strength=ctx.rules.husbandry.pet_grief_strength, epoch=ctx.epoch)
                tally.mourned += 1
            continue
        if owner.status is not EntityStatus.CANON:
            await close(ctx.session, bond, ctx.epoch, "its owner died")
            row = await ctx.session.get(BeastProfileRow, pet.id)
            if row is not None and "temper" not in row.locked:
                row.temper, row.bound_to_node_id = BeastTemper.TAMED, None
            tally.orphaned += 1
            continue
        pet.location_id = owner.location_id
        await think(ctx.session, ctx.rules, owner.id, ThoughtKind.COMFORTED_BY_PET, ctx.epoch, subject_id=pet.id)
        tally.comforted += 1
        if await hunts_beside(ctx, pet):
            await practised(ctx, owner.id, SkillKind.HUNTING, ctx.rules.husbandry.pet_hunt_xp)
            tally.hunted += 1
    return tally
