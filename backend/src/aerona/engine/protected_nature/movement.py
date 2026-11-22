from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.protected_nature import ConservationMovementRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionBasis, ProtectionMeasure
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.polity.book import Realm
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import has_flag, living_entity
from aerona.engine.primitives.society import class_shares
from aerona.engine.protected_nature.areas import protect_area
from aerona.engine.protected_nature.book import NatureTally
from aerona.engine.protected_nature.species import protect_species

ENDANGERED_WEIGHT = 10
AIMS = [ProtectedUse.HUNTING.value, ProtectedUse.LOGGING.value, ProtectionMeasure.HUNTING_BAN.value]
FOR_THE_WILD = frozenset({SocialClass.PRIEST, SocialClass.MONASTIC, SocialClass.SCRIBE, SocialClass.PROFESSIONAL})
AGAINST_THE_WILD = frozenset({SocialClass.FARMER, SocialClass.WORKER})

GUARDED = (ProtectionMeasure.HUNTING_BAN, ProtectionMeasure.HABITAT_GUARD)


def leaning(support: int, social: SocialClass) -> int:
    tilt = PERCENT // 5 if social in FOR_THE_WILD else -PERCENT // 5 if social in AGAINST_THE_WILD else 0
    return max(0, min(PERCENT, support + tilt))


async def loss_of_wild(ctx: TickContext, community: EntityRow) -> float:
    region = (await RegionAtlas.load(ctx.session)).top_region(community.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    if land is None:
        return 0.0
    cleared = max(0, land.base_forest - land.forest_cover)
    species = await ctx.session.scalars(select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == land.entity_id))
    endangered = sum([1 for species_id in sorted(set(species)) if await has_flag(ctx.session, species_id, EntityFlag.ENDANGERED)])
    return (cleared + endangered * ENDANGERED_WEIGHT) * ctx.rules.protected_nature.conservation_loss_pct / PERCENT


async def aims_of(ctx: TickContext, movement_id: int) -> list[str]:
    row = await ctx.session.get(ConservationMovementRow, movement_id)
    return list(row.aims) if row is not None and row.aims else list(AIMS)


async def protect_for_movement(ctx: TickContext, realm: Realm, row: MovementProfileRow) -> None:
    profile = await ctx.session.get(FactionProfileRow, row.faction_entity_id)
    home = await living_entity(ctx.session, profile.home_entity_id) if profile is not None and profile.home_entity_id is not None else None
    region_id = (await RegionAtlas.load(ctx.session)).top_region(home.id) if home is not None else None
    region = await living_entity(ctx.session, region_id) if region_id is not None else None
    if region is None or held(region.id):
        return
    known = {item.value: item for item in ProtectedUse}
    uses = [known[aim] for aim in await aims_of(ctx, row.faction_entity_id) if aim in known]
    tally = NatureTally()
    await protect_area(ctx, region, ProtectionBasis.LAW, uses, tally, protector=realm.entity.id)
    ranged = select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == region.id).distinct()
    for species_id in sorted(set(await ctx.session.scalars(ranged))):
        species = await living_entity(ctx.session, species_id)
        if species is None or held(species.id) or not await has_flag(ctx.session, species.id, EntityFlag.ENDANGERED):
            continue
        await protect_species(ctx, species, ProtectionBasis.LAW, list(GUARDED), tally, holder=realm.entity.id)


async def tend_movements(ctx: TickContext, tally: NatureTally) -> None:
    query = select(MovementProfileRow).where(MovementProfileRow.cause == MovementCause.CONSERVATION).order_by(MovementProfileRow.faction_entity_id)
    for movement in list(await ctx.session.scalars(query)):
        if held(movement.faction_entity_id):
            continue
        row = await ctx.session.get(ConservationMovementRow, movement.faction_entity_id)
        if row is None:
            row = ConservationMovementRow(movement_entity_id=movement.faction_entity_id, aims=list(AIMS), cohort_support={}, locked=[])
            ctx.session.add(row)
            tally.movements += 1
        profile = await ctx.session.get(FactionProfileRow, movement.faction_entity_id)
        home = profile.home_entity_id if profile is not None else None
        shares = await class_shares(ctx.session, ctx.rules, home) if home is not None else {}
        if "cohort_support" not in (row.locked or []):
            row.cohort_support = {social.value: leaning(movement.support, social) for social in sorted(shares)}
    await ctx.session.flush()
