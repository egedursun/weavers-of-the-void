from sqlalchemy import select

from aerona.catalog.rocks import GASSY_ROCKS, ROCKS
from aerona.catalog.theories import ANOMALY_DOMAINS
from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.discovery import TheoryAnomalyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.place import PlaceSecretRow
from aerona.db.tables.sites import BattlefieldFeatureRow
from aerona.db.write_guard import held
from aerona.domain.enums.discovery import AnomalyKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.geology import UndergroundStratum
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import SecretKind
from aerona.domain.enums.site import BattlefieldFeature, ExcavationRisk
from aerona.engine.context import TickContext
from aerona.engine.environment.columns import POROUS, columns_by_region
from aerona.engine.lore.truth import ruling
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.recording.record import record
from aerona.rules.model import keyed

SITES_FIXUP = "sites.w52"


async def home_of(ctx: TickContext, finder: EntityRow) -> EntityRow | None:
    if finder.entity_type in COMMUNITY_TYPES:
        return finder
    home = await ctx.session.get(EntityRow, finder.location_id) if finder.location_id is not None else None
    return home if home is not None and home.entity_type in COMMUNITY_TYPES and home.status is EntityStatus.CANON else None


async def unsettle_accounts(ctx: TickContext, finder: EntityRow, kind: AnomalyKind, place_id: int) -> int:
    home = await home_of(ctx, finder)
    if home is None:
        return 0
    weight = max(1, keyed(ctx.rules.theories, kind.value, "weight") // 10)
    shaken = 0
    for domain in ANOMALY_DOMAINS[kind]:
        held_theory = await ruling(ctx.session, home.id, domain)
        if held_theory is None or held(held_theory.theory_entity_id):
            continue
        ctx.session.add(TheoryAnomalyRow(theory_entity_id=held_theory.theory_entity_id, kind=kind, weight=weight, witness_entity_id=home.id, epoch=ctx.epoch))
        await record(
            ctx,
            "theory.challenged",
            roles={IncidentRole.SUBJECT: held_theory.theory_entity_id, IncidentRole.WITNESS: home.id, IncidentRole.PLACE: place_id},
            facts={"anomaly": kind, "domain": domain, "weight": weight},
            place=place_id,
        )
        shaken += 1
    return shaken


async def ground_risks(ctx: TickContext, site: EntityRow) -> list[ExcavationRisk]:
    atlas = await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(site.id)
    found: list[ExcavationRisk] = []
    columns = (await columns_by_region(ctx.session, [region_id])).get(region_id, []) if region_id is not None else []
    if any(ROCKS[row.rock].porosity(ctx.rules) >= POROUS for row in columns):
        found.append(ExcavationRisk.FLOODING)
    reservoir = (
        await ctx.session.scalar(
            select(RegionStratumRow.id).where(RegionStratumRow.region_entity_id == region_id, RegionStratumRow.stratum == UndergroundStratum.RESERVOIR).limit(1)
        )
        if region_id is not None
        else None
    )
    if reservoir is not None or any(row.rock in GASSY_ROCKS for row in columns):
        found.append(ExcavationRisk.GAS)
    places = [place for place in (site.id, region_id) if place is not None]
    sealed = await ctx.session.scalar(
        select(PlaceSecretRow.id).where(PlaceSecretRow.place_entity_id.in_(places), PlaceSecretRow.kind == SecretKind.DORMANT_DISEASE).limit(1)
    )
    graves = await ctx.session.scalar(
        select(BattlefieldFeatureRow.id)
        .where(BattlefieldFeatureRow.place_entity_id == site.id, BattlefieldFeatureRow.feature == BattlefieldFeature.MASS_GRAVE)
        .limit(1)
    )
    if sealed is not None or graves is not None:
        found.append(ExcavationRisk.DISEASE)
    return found


async def sealed_disease(ctx: TickContext, site: EntityRow) -> int | None:
    atlas = await RegionAtlas.load(ctx.session)
    places = [place for place in (site.id, atlas.top_region(site.id)) if place is not None]
    found: int | None = await ctx.session.scalar(
        select(PlaceSecretRow.subject_entity_id)
        .where(PlaceSecretRow.place_entity_id.in_(places), PlaceSecretRow.kind == SecretKind.DORMANT_DISEASE)
        .order_by(PlaceSecretRow.id)
        .limit(1)
    )
    return found


async def remnant_near(ctx: TickContext, place: EntityRow) -> WarRemnantRow | None:
    atlas = await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(place.id)
    if region_id is None:
        return None
    found: WarRemnantRow | None = await ctx.session.scalar(
        select(WarRemnantRow).where(WarRemnantRow.region_entity_id == region_id, WarRemnantRow.cleared < PERCENT).order_by(WarRemnantRow.id).limit(1)
    )
    return found


async def mark_ordnance(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, SITES_FIXUP):
        return 0
    marked = 0
    fields = await ctx.session.execute(
        select(BattlefieldFeatureRow.place_entity_id, BattlefieldFeatureRow.battle_id)
        .where(BattlefieldFeatureRow.feature == BattlefieldFeature.MASS_GRAVE)
        .order_by(BattlefieldFeatureRow.place_entity_id, BattlefieldFeatureRow.id)
    )
    seen: set[int] = set()
    for place_id, battle_id in fields.all():
        if place_id in seen or held(place_id):
            continue
        seen.add(place_id)
        place = await ctx.session.get(EntityRow, place_id)
        remnant = await remnant_near(ctx, place) if place is not None else None
        if remnant is None:
            continue
        ctx.session.add(
            BattlefieldFeatureRow(
                place_entity_id=place_id,
                feature=BattlefieldFeature.ORDNANCE,
                strength=max(1, remnant.density * (PERCENT - remnant.cleared) // PERCENT),
                battle_id=battle_id,
                remnant_id=remnant.id,
                epoch=ctx.epoch,
                locked=[],
            )
        )
        marked += 1
    ctx.session.add(AppliedFixupRow(key=SITES_FIXUP, result={"ordnance": marked}))
    await ctx.session.flush()
    return marked
