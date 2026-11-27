from sqlalchemy import select

from aerona.catalog.domestication import SOLVENT_BIOCHEMISTRY
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesUseRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import AnimalRole, Biochemistry, HerdTraining, Sociality, SpeciesClass
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.ecology.biochemistry import tolerated
from aerona.engine.ecology.uses import give_use

SOCIAL_FIXUP = "species.w52_social"
BIOCHEMISTRY_FIXUP = "biochemistry.w52"
ROLES_FIXUP = "species_roles.w52"


def free(profile: SpeciesProfileRow, field: str) -> bool:
    return not held(profile.species_entity_id) and field not in (profile.locked or [])


async def fixed(ctx: TickContext, key: str, result: dict[str, int]) -> None:
    ctx.session.add(AppliedFixupRow(key=key, result=result))
    await ctx.session.flush()


async def backfill_social(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, SOCIAL_FIXUP):
        return 0
    breeders = select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == CreatureTrait.SWARM_BREEDER)
    moved = 0
    for profile in await ctx.session.scalars(
        select(SpeciesProfileRow).where(SpeciesProfileRow.species_entity_id.in_(breeders)).order_by(SpeciesProfileRow.species_entity_id)
    ):
        if free(profile, "sociality") and profile.sociality is not Sociality.SWARM:
            profile.sociality = Sociality.SWARM
            moved += 1
    await fixed(ctx, SOCIAL_FIXUP, {"swarms": moved})
    return moved


async def backfill_biochemistry(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, BIOCHEMISTRY_FIXUP):
        return 0
    moved = 0
    found = await ctx.session.execute(
        select(SpeciesProfileRow, EntityRow.world_id)
        .join(EntityRow, EntityRow.id == SpeciesProfileRow.species_entity_id)
        .order_by(SpeciesProfileRow.species_entity_id)
    )
    for profile, world_id in list(found):
        if not free(profile, "biochemistry"):
            continue
        native = await tolerated(ctx.session, world_id)
        if profile.species_class is SpeciesClass.ENERGY and profile.biochemistry is not Biochemistry.PLASMA:
            profile.biochemistry = Biochemistry.PLASMA
            moved += 1
        elif (
            Biochemistry.CARBON_METHANE in native
            and Biochemistry.CARBON_WATER not in native
            and profile.biochemistry in SOLVENT_BIOCHEMISTRY
            and profile.biochemistry is not Biochemistry.CARBON_METHANE
        ):
            profile.biochemistry = Biochemistry.CARBON_METHANE
            moved += 1
    await fixed(ctx, BIOCHEMISTRY_FIXUP, {"species": moved})
    return moved


async def backfill_hunting_role(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, ROLES_FIXUP):
        return 0
    known = set(await ctx.session.scalars(select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use == AnimalRole.HUNTING)))
    trained = await ctx.session.scalars(
        select(HerdRow.species_entity_id).where(HerdRow.training == HerdTraining.HUNTING).distinct().order_by(HerdRow.species_entity_id)
    )
    gained = 0
    for species_id in trained:
        if species_id in known or held(species_id):
            continue
        await give_use(ctx.session, species_id, AnimalRole.HUNTING)
        known.add(species_id)
        gained += 1
    await fixed(ctx, ROLES_FIXUP, {"species": gained})
    return gained
