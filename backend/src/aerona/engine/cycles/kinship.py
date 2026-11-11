from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.cycles import KinshipSystemRow, MarriageAllianceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import ResidenceRule
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import MarriageEnd, MarriageKind, MortalSex
from aerona.domain.enums.polity import TreatyKind
from aerona.engine.collective.book import realm_of_town
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import kinship_of, line_of, sex_value
from aerona.engine.cycles.standing import raise_standing, regard
from aerona.engine.demography.kinship import may_wed
from aerona.engine.mortal.kin import parents_of, siblings_of
from aerona.engine.mortal.kinship import marry
from aerona.engine.notes import note
from aerona.engine.polity.treaties import sign_derived
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or


@dataclass
class KinshipTally:
    moved: int = 0
    levirate: int = 0
    sororate: int = 0
    alliances: int = 0
    pacts: int = 0


def age_of(mortal: EntityRow) -> int:
    return stat_or(mortal, "age", 0)


async def giver_and_taker(ctx: TickContext, first: EntityRow, second: EntityRow, system: KinshipSystemRow) -> tuple[EntityRow, EntityRow]:
    sexes = (sex_value(first), sex_value(second))
    if system.residence in {ResidenceRule.PATRILOCAL, ResidenceRule.AVUNCULOCAL} and MortalSex.MALE.value in sexes and sexes[0] != sexes[1]:
        return (second, first) if sexes[0] == MortalSex.MALE.value else (first, second)
    if system.residence is ResidenceRule.MATRILOCAL and MortalSex.FEMALE.value in sexes and sexes[0] != sexes[1]:
        return (second, first) if sexes[0] == MortalSex.FEMALE.value else (first, second)
    return (first, second) if (age_of(first), -first.id) <= (age_of(second), -second.id) else (second, first)


async def mothers_brother(ctx: TickContext, mortal: EntityRow) -> EntityRow | None:
    for parent_id in await parents_of(ctx.session, mortal.id):
        parent = await ctx.session.get(EntityRow, parent_id)
        if sex_value(parent) != MortalSex.FEMALE.value:
            continue
        for sibling_id in await siblings_of(ctx.session, parent_id):
            sibling = await living_entity(ctx.session, sibling_id)
            if sibling is not None and sex_value(sibling) == MortalSex.MALE.value:
                return sibling
    return None


async def reside(ctx: TickContext, marriage: MarriageRow, tally: KinshipTally) -> None:
    first = await living_entity(ctx.session, marriage.first_id)
    second = await living_entity(ctx.session, marriage.second_id)
    if first is None or second is None or held(first.id, second.id):
        return
    system = await kinship_of(ctx.session, first)
    if system is None or system.residence is ResidenceRule.NEOLOCAL:
        return
    leaving, staying = await giver_and_taker(ctx, first, second, system)
    home = staying.location_id
    if system.residence is ResidenceRule.AVUNCULOCAL:
        uncle = await mothers_brother(ctx, staying)
        home = uncle.location_id if uncle is not None and uncle.location_id is not None else home
        if staying.location_id != home:
            staying.location_id = home
            tally.moved += 1
    if home is not None and leaving.location_id != home:
        leaving.location_id = home
        tally.moved += 1


async def next_spouse(ctx: TickContext, survivor: EntityRow, dead_id: int) -> EntityRow | None:
    dead = await ctx.session.get(EntityRow, dead_id)
    wanted = sex_value(dead)
    for sibling_id in await siblings_of(ctx.session, dead_id):
        sibling = await living_entity(ctx.session, sibling_id)
        if sibling is None or held(sibling.id) or (wanted is not None and sex_value(sibling) != wanted):
            continue
        if await may_wed(ctx.session, ctx.rules, survivor, sibling):
            return sibling
    return None


async def remarry(ctx: TickContext, marriage: MarriageRow, tally: KinshipTally) -> None:
    alive = [await living_entity(ctx.session, marriage.first_id), await living_entity(ctx.session, marriage.second_id)]
    survivors = [mortal for mortal in alive if mortal is not None]
    if len(survivors) != 1 or held(survivors[0].id):
        return
    survivor = survivors[0]
    dead_id = marriage.second_id if survivor.id == marriage.first_id else marriage.first_id
    dead = await ctx.session.get(EntityRow, dead_id)
    system = await kinship_of(ctx.session, survivor)
    if system is None or dead is None:
        return
    levirate = system.levirate and sex_value(dead) != MortalSex.FEMALE.value
    sororate = system.sororate and sex_value(dead) != MortalSex.MALE.value
    if not levirate and not sororate:
        return
    spouse = await next_spouse(ctx, survivor, dead_id)
    if spouse is None:
        return
    custom = "levirate" if levirate else "sororate"
    await marry(ctx.session, survivor, spouse, ctx.epoch, kind=MarriageKind.MONOGAMOUS, description=custom)
    if levirate:
        tally.levirate += 1
    else:
        tally.sororate += 1
    await note(
        ctx,
        f"By the custom of {custom}, {survivor.name} wed {spouse.name}, kin of the departed {dead.name}.",
        key=f"kinship.{custom}",
        ids=[survivor.id, spouse.id, dead.id],
    )


async def alliance_row(ctx: TickContext, giver: int, taker: int) -> MarriageAllianceRow:
    row = await ctx.session.get(MarriageAllianceRow, (giver, taker))
    if row is None:
        row = MarriageAllianceRow(giver_entity_id=giver, taker_entity_id=taker, marriages=0, since_epoch=ctx.epoch, last_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def pact(ctx: TickContext, row: MarriageAllianceRow, tally: KinshipTally) -> None:
    table = ctx.rules.marriage_alliance
    if row.treaty_id is not None or row.marriages < table.pact_at or "treaty_id" in row.locked:
        return
    giver = await ctx.session.get(EntityRow, row.giver_entity_id)
    taker = await ctx.session.get(EntityRow, row.taker_entity_id)
    if giver is None or taker is None or giver.location_id is None or taker.location_id is None:
        return
    first = await realm_of_town(ctx, giver.location_id)
    second = await realm_of_town(ctx, taker.location_id)
    if first is None or second is None or first.polity_entity_id == second.polity_entity_id:
        return
    treaty = await sign_derived(ctx, TreatyKind.MARRIAGE_PACT, first.polity_entity_id, second.polity_entity_id, until=ctx.epoch + table.pact_epochs)
    if treaty is None:
        return
    row.treaty_id = treaty.id
    tally.pacts += 1
    await note(ctx, f"Their many marriages bound {giver.name} and {taker.name} in {treaty.name}.", key="kinship.pact", ids=[giver.id, taker.id, treaty.id])


async def ally_lines(ctx: TickContext, marriage: MarriageRow, tally: KinshipTally) -> None:
    table = ctx.rules.marriage_alliance
    first = await ctx.session.get(EntityRow, marriage.first_id)
    second = await ctx.session.get(EntityRow, marriage.second_id)
    if first is None or second is None:
        return
    system = await kinship_of(ctx.session, first)
    if system is None:
        return
    leaving, staying = await giver_and_taker(ctx, first, second, system)
    giver = await line_of(ctx.session, leaving.id, system.descent_group)
    taker = await line_of(ctx.session, staying.id, system.descent_group)
    if giver is None or taker is None or giver == taker or held(giver, taker):
        return
    row = await alliance_row(ctx, giver, taker)
    if "marriages" not in row.locked:
        row.marriages += 1
    row.last_epoch = ctx.epoch
    tally.alliances += 1
    await regard(ctx, (giver, taker), table.alliance_regard, MemoryKind.MARRIED_INTO, "a marriage between the lines")
    reverse = await ctx.session.get(MarriageAllianceRow, (taker, giver))
    gap = row.marriages - (reverse.marriages if reverse is not None else 0)
    if gap > 0:
        await raise_standing(ctx, giver, gap * table.giver_rank)
        await raise_standing(ctx, taker, -gap * table.giver_rank)
    await pact(ctx, row, tally)


async def keep_kinship(ctx: TickContext, tally: KinshipTally) -> None:
    started = list(await ctx.session.scalars(select(MarriageRow).where(MarriageRow.start_epoch == ctx.epoch).order_by(MarriageRow.id)))
    for marriage in started:
        await reside(ctx, marriage, tally)
        await ally_lines(ctx, marriage, tally)
    ended = await ctx.session.scalars(
        select(MarriageRow).where(MarriageRow.end_epoch == ctx.epoch, MarriageRow.cause_end == MarriageEnd.DEATH).order_by(MarriageRow.id)
    )
    for marriage in list(ended):
        await remarry(ctx, marriage, tally)
    await ctx.session.flush()
