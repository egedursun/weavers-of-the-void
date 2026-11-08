from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.ecology.pets import pet_of, take_pet
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity


async def owner_of(ctx: TickContext, owner_id: int) -> EntityRow:
    owner = await living_entity(ctx.session, owner_id)
    if owner is None or owner.entity_type is not EntityType.MORTAL:
        raise NotFoundError("Only a living mortal keeps a pet.")
    return owner


async def set_pet(ctx: TickContext, beast_id: int, owner_id: int | None) -> BeastProfileRow:
    beast = await living_entity(ctx.session, beast_id)
    row = await ctx.session.get(BeastProfileRow, beast_id)
    if beast is None or row is None:
        raise NotFoundError("No such living beast.")
    for bond in await active_bonds(ctx.session, [BondKind.PET_OF], sources=[beast_id]):
        await close(ctx.session, bond, ctx.epoch, "set free by the Creator")
    if owner_id is None:
        row.temper, row.bound_to_node_id = BeastTemper.TAMED, None
        await ctx.session.flush()
        return row
    owner = await owner_of(ctx, owner_id)
    row.temper, row.bound_to_node_id, row.lair_place_id = BeastTemper.COMPANION, owner.id, None
    beast.location_id = owner.location_id
    await connect(ctx.session, beast.id, owner.id, BondKind.PET_OF, ctx.epoch, description="given by the Creator")
    await ctx.session.flush()
    return row


async def give_pet(ctx: TickContext, owner_id: int, species_id: int) -> EntityRow:
    owner = await owner_of(ctx, owner_id)
    species = await living_entity(ctx.session, species_id)
    if species is None or species.entity_type is not EntityType.SPECIES:
        raise NotFoundError("No such living kind.")
    if await pet_of(ctx, owner.id) is not None:
        raise ValidationFailedError(f"{owner.name} already keeps a pet; set it free first.")
    pet = await take_pet(ctx, owner, species)
    await ctx.session.flush()
    return pet
