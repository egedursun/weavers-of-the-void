from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CarrierRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.outbreaks import open_outbreak
from aerona.engine.lore.truth import ruling_truths
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import RoleValue, record


@dataclass
class CarrierTally:
    found: int = 0
    seeded: int = 0
    identified: int = 0


async def folk_by_region(ctx: TickContext, book: DiseaseBook) -> dict[int, list[int]]:
    found: dict[int, list[int]] = defaultdict(list)
    for community in await canon(ctx.session, SOCIETY_TYPES):
        region = book.atlas.top_region(community.id)
        if region is not None:
            found[region].append(community.id)
    return found


async def mortals_among(ctx: TickContext, community_ids: list[int]) -> list[EntityRow]:
    if not community_ids:
        return []
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, community_ids))
            .order_by(EntityRow.id)
        )
    )


async def physicians_among(ctx: TickContext, community_ids: list[int], skill: int) -> bool:
    if not community_ids:
        return False
    found = await ctx.session.scalar(
        select(SkillRow.id)
        .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
        .where(SkillRow.skill == SkillKind.MEDICINE, SkillRow.level >= skill, await present_among(ctx.session, community_ids))
        .limit(1)
    )
    return found is not None


async def name_carriers(ctx: TickContext, book: DiseaseBook, folk: dict[int, list[int]], tally: CarrierTally) -> None:
    table = ctx.rules.carriers
    for outbreak in book.outbreaks:
        if tally.found >= table.per_epoch:
            return
        for mortal in await mortals_among(ctx, folk.get(outbreak.region_entity_id, [])):
            if tally.found >= table.per_epoch:
                return
            if held(mortal.id) or await ctx.session.get(CarrierRow, (mortal.id, outbreak.disease_entity_id)) is not None:
                continue
            if not ctx.rng(f"carrier.{mortal.id}.{outbreak.disease_entity_id}").chance(table.carrier_pct):
                continue
            ctx.session.add(
                CarrierRow(
                    mortal_entity_id=mortal.id,
                    disease_entity_id=outbreak.disease_entity_id,
                    home_region_id=outbreak.region_entity_id,
                    identified=False,
                    seeded=0,
                    since_epoch=ctx.epoch,
                    locked=[],
                )
            )
            tally.found += 1
    await ctx.session.flush()


async def walk_carriers(ctx: TickContext, book: DiseaseBook, folk: dict[int, list[int]], tally: CarrierTally) -> None:
    table = ctx.rules.carriers
    truths = await ruling_truths(ctx.session, TheoryDomain.MEDICINE)
    for row in list(await ctx.session.scalars(select(CarrierRow).order_by(CarrierRow.mortal_entity_id, CarrierRow.disease_entity_id))):
        mortal = await ctx.session.get(EntityRow, row.mortal_entity_id)
        disease = book.diseases.get(row.disease_entity_id)
        if mortal is None or disease is None or held(mortal.id, disease.id) or mortal.status is not EntityStatus.CANON:
            continue
        region_id = book.atlas.top_region(mortal.id)
        if region_id is None:
            continue
        here = folk.get(region_id, [])
        knowing = any(truths.get(community, 0) >= table.theory_truth for community in here)
        if not row.identified and knowing and "identified" not in row.locked and await physicians_among(ctx, here, table.identify_skill):
            row.identified = True
            tally.identified += 1
            await record(
                ctx,
                "disease.carrier_found",
                roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.INSTRUMENT: disease.id},
                facts={"skill": table.identify_skill},
                place=region_id,
            )
            continue
        if row.identified or region_id == row.home_region_id or book.active_of(disease.id, region_id) is not None:
            continue
        if not ctx.rng(f"carrier_seed.{mortal.id}.{disease.id}").chance(table.seed_pct):
            continue
        await open_outbreak(ctx, book, disease, region_id, path=SpreadPath.JOURNEY, severity=ctx.rules.carriers.seed_severity)
        if "seeded" not in row.locked:
            row.seeded += 1
        row.home_region_id = region_id
        tally.seeded += 1
        region = await ctx.session.get(EntityRow, region_id)
        if region is not None:
            roles: dict[IncidentRole, RoleValue] = {IncidentRole.SUBJECT: mortal.id, IncidentRole.INSTRUMENT: disease.id, IncidentRole.DESTINATION: region.id}
            await record(
                ctx, "disease.carrier_seeded", roles=roles, facts={"severity": ctx.rules.carriers.seed_severity, "seeded": row.seeded}, place=region.id
            )


async def keep_carriers(ctx: TickContext, tally: CarrierTally) -> None:
    book = await DiseaseBook.load(ctx.session, ctx.rules, ctx.epoch)
    folk = await folk_by_region(ctx, book)
    await name_carriers(ctx, book, folk, tally)
    await walk_carriers(ctx, book, folk, tally)
    await ctx.session.flush()
