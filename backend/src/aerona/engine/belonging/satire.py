from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.belonging import SatireRow
from aerona.db.tables.collective import SocialNormRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import BiasWeightRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import SatireSource
from aerona.domain.enums.collective import NormBehaviour, NormSituation
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.folkways import DecisionBias
from aerona.domain.enums.mind import EthicalStance
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import ruler_id
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.law.prisons import imprison
from aerona.engine.mind.opinion import opinion
from aerona.engine.mortal.standing import add_renown
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

TOLERANT = frozenset({EthicalStance.REQUIRED, EthicalStance.ADMIRABLE, EthicalStance.ACCEPTABLE})


@dataclass
class SatireTally:
    jests: int = 0
    works: int = 0
    tolerated: int = 0
    punished: int = 0
    relieved: int = 0


async def tolerates(ctx: TickContext, polity_id: int | None) -> bool:
    if polity_id is None:
        return True
    profile = await ctx.session.get(PolityProfileRow, polity_id)
    seat = await ctx.session.get(EntityRow, profile.capital_entity_id) if profile is not None and profile.capital_entity_id is not None else None
    folk = await people_of(ctx.session, seat) if seat is not None else None
    holders = [polity_id, *([seat.id] if seat is not None else []), *([folk.id] if folk is not None else [])]
    stances = list(
        await ctx.session.scalars(
            select(SocialNormRow.stance).where(
                SocialNormRow.holder_entity_id.in_(holders), SocialNormRow.situation == NormSituation.COURT, SocialNormRow.behaviour == NormBehaviour.JEST
            )
        )
    )
    return not stances or any(stance in TOLERANT for stance in stances)


async def jests(ctx: TickContext, tally: SatireTally) -> None:
    table = ctx.rules.satire
    for office in list(
        await ctx.session.scalars(select(OfficeRow).where(OfficeRow.kind == OfficeKind.JESTER, OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id))
    ):
        fool = await living_entity(ctx.session, office.holder_entity_id)
        ruler = await ruler_id(ctx, office.polity_entity_id)
        if fool is None or ruler is None or held(fool.id, ruler):
            continue
        bias = await ctx.session.get(BiasWeightRow, (ruler, DecisionBias.GROUPTHINK))
        if bias is not None and "weight" not in bias.locked:
            bias.weight = clamp_int(bias.weight - table.groupthink_relief, 0, PERCENT)
            tally.relieved += 1
        if ctx.rng(seed_of("satire.jest", office.id, ctx.epoch)).chance(table.jest_chance):
            ctx.session.add(
                SatireRow(
                    satirist_entity_id=fool.id,
                    target_entity_id=ruler,
                    polity_entity_id=office.polity_entity_id,
                    source=SatireSource.JESTER,
                    bite=table.bite,
                    tolerated=True,
                    epoch=ctx.epoch,
                    locked=[],
                )
            )
            tally.jests += 1


async def rulers(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    for holder, polity in await ctx.session.execute(
        select(OfficeRow.holder_entity_id, OfficeRow.polity_entity_id).where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
    ):
        if holder is not None:
            found.setdefault(holder, polity)
    return found


async def works(ctx: TickContext, tally: SatireTally) -> None:
    table = ctx.rules.satire
    seated = await rulers(ctx)
    if not seated:
        return
    known = set(await ctx.session.scalars(select(SatireRow.work_entity_id).where(SatireRow.work_entity_id.is_not(None))))
    rows = await ctx.session.execute(
        select(ArtworkProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == ArtworkProfileRow.artwork_entity_id)
        .where(
            ArtworkProfileRow.subject_node_id.in_(list(seated)),
            ArtworkProfileRow.author_entity_id.is_not(None),
            ArtworkProfileRow.quality >= table.artwork_quality,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.birth_epoch >= ctx.epoch - 1,
        )
        .order_by(ArtworkProfileRow.artwork_entity_id)
    )
    for work, entity in rows:
        if entity.id in known or work.author_entity_id is None or work.subject_node_id is None or held(work.author_entity_id):
            continue
        view = await opinion(ctx.session, ctx.rules, ctx.epoch, work.author_entity_id, work.subject_node_id)
        if view.value >= 0:
            continue
        ctx.session.add(
            SatireRow(
                satirist_entity_id=work.author_entity_id,
                target_entity_id=work.subject_node_id,
                polity_entity_id=seated[work.subject_node_id],
                work_entity_id=entity.id,
                source=SatireSource.ARTWORK,
                bite=clamp_int(round_half_up(table.bite * work.quality / table.artwork_quality), 0, PERCENT),
                epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.works += 1


async def judge(ctx: TickContext, row: SatireRow, tally: SatireTally) -> None:
    table = ctx.rules.satire
    row.judged = True
    if "tolerated" not in row.locked and row.source is not SatireSource.JESTER:
        row.tolerated = await tolerates(ctx, row.polity_entity_id or await realm_of(ctx.session, row.target_entity_id))
    target = await living_entity(ctx.session, row.target_entity_id)
    if row.tolerated:
        if target is not None and not held(target.id):
            await add_renown(ctx.session, target.id, -table.prestige * row.bite / PERCENT, ctx.epoch)
        tally.tolerated += 1
        return
    satirist = await living_entity(ctx.session, row.satirist_entity_id) if row.satirist_entity_id is not None else None
    if satirist is not None and not held(satirist.id) and "punished" not in row.locked:
        row.punished = True
        await imprison(ctx, satirist, term=table.punish_term)
        tally.punished += 1
        await record(
            ctx,
            "satire.punished",
            roles={
                IncidentRole.ACCUSED: satirist.id,
                IncidentRole.VICTIM: target.id if target is not None else None,
                IncidentRole.AUTHORITY: row.polity_entity_id,
            },
            facts={"source": row.source, "bite": row.bite, "term": table.punish_term},
            place=satirist.location_id,
        )


async def keep_satire(ctx: TickContext, tally: SatireTally) -> None:
    await jests(ctx, tally)
    await works(ctx, tally)
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(SatireRow).where(SatireRow.judged.is_(False)).order_by(SatireRow.id))):
        if held(row.target_entity_id):
            continue
        await judge(ctx, row, tally)
    await ctx.session.flush()
