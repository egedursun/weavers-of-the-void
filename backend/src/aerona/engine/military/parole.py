from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathBreach, OathKind, OathStatus
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.military.captivity import wring_intel
from aerona.engine.military.terms import war_between
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.polity.oaths import break_oath, swear
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import release_captive


@dataclass
class ParoleTally:
    kept: int = 0
    broken: int = 0
    bridged: int = 0
    betrayed: int = 0


async def offer_parole(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow, home: EntityRow | None) -> bool:
    if row.war_id is None or home is None or "status" in row.locked or frozen(captive.id, captor.id):
        return False
    if not ctx.rng(f"parole.{row.id}.{ctx.epoch}").chance(ctx.rules.captives.parole_pct):
        return False
    oath = await swear(ctx, captive, OathKind.NONVIOLENCE, recipient_id=captor.id, note_text=f"parole given to {captor.name}")
    row.oath_id = oath.id
    await release_captive(ctx, row, CaptiveStatus.PAROLED)
    await record(
        ctx,
        "captive.paroled",
        roles={IncidentRole.ACTOR: captor.id, IncidentRole.SUBJECT: captive.id, IncidentRole.ORIGIN: home.id},
        facts={"oath_kind": OathKind.NONVIOLENCE},
        place=home.id,
    )
    return True


async def join_captors(ctx: TickContext, row: CaptiveRow, captive: EntityRow, captor: EntityRow, home: EntityRow | None) -> bool:
    if row.married_entity_id is None or "status" in row.locked or frozen(captive.id, captor.id):
        return False
    spouse = await living_entity(ctx.session, row.married_entity_id)
    if spouse is None or not ctx.rng(f"married_in.{row.id}.{ctx.epoch}").chance(ctx.rules.captives.married_in_pct):
        return False
    await release_captive(ctx, row, CaptiveStatus.MARRIED_IN)
    people = await people_id_of(ctx.session, captor)
    bonds = BondRepository(ctx.session)
    if people is not None and not await bonds.exists_between(captive.id, people, BondKind.MEMBER_OF):
        await bonds.connect(BondDraft(captive.id, people, BondKind.MEMBER_OF, ctx.epoch, "married into the people"))
    theirs = await values_for(ctx.session, captor.id)
    if theirs:
        own = await stored_values(ctx.session, ValueHolder.PERSONAL, captive.id)
        await write_values(ctx.session, ValueHolder.PERSONAL, captive.id, {axis: (own.get(axis, 0) + theirs.get(axis, 0)) // 2 for axis in ValueAxis})
    captive.location_id = captor.id if captor.entity_type is EntityType.SETTLEMENT else (captor.location_id or captive.location_id)
    await record(
        ctx,
        "captive.married_in",
        roles={IncidentRole.ACTOR: captor.id, IncidentRole.SUBJECT: captive.id, IncidentRole.SPOUSE: spouse.id, IncidentRole.ORIGIN: home.id if home else None},
        place=captor.id,
    )
    return True


async def keep_paroles(ctx: TickContext, tally: ParoleTally) -> None:
    rows = list(await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.status == CaptiveStatus.PAROLED).order_by(CaptiveRow.id)))
    for row in rows:
        captive, captor = await living_entity(ctx.session, row.captive_entity_id), await living_entity(ctx.session, row.captor_entity_id)
        oath = await ctx.session.get(OathRow, row.oath_id) if row.oath_id is not None else None
        home = await living_entity(ctx.session, row.home_entity_id) if row.home_entity_id is not None else None
        if captive is None or captor is None or home is None or oath is None or oath.status is not OathStatus.SWORN or frozen(captive.id, captor.id):
            continue
        if await war_between(ctx, home.id, captor.id) is None:
            continue
        if ctx.rng(f"parole_kept.{row.id}.{ctx.epoch}").chance(ctx.rules.captives.parole_kept_pct):
            tally.kept += 1
            continue
        await break_oath(ctx, oath, OathBreach.BLOOD_SHED, occasion=home.id)
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=captor.id,
            subject_id=captive.id,
            kind=MemoryKind.BETRAYED_ME,
            magnitude=-ctx.rules.captives.parole_shame,
            epoch=ctx.epoch,
            note="fought again after parole",
        )
        tally.broken += 1


async def married_in_wars(ctx: TickContext, tally: ParoleTally) -> None:
    rows = list(await ctx.session.scalars(select(CaptiveRow).where(CaptiveRow.status == CaptiveStatus.MARRIED_IN).order_by(CaptiveRow.id)))
    for row in rows:
        captive, captor = await living_entity(ctx.session, row.captive_entity_id), await living_entity(ctx.session, row.captor_entity_id)
        home = await living_entity(ctx.session, row.home_entity_id) if row.home_entity_id is not None else None
        if captive is None or captor is None or home is None or frozen(captive.id, captor.id, home.id):
            continue
        if await war_between(ctx, home.id, captor.id) is None:
            continue
        if ctx.rng(f"married_in_turn.{row.id}.{ctx.epoch}").chance(ctx.rules.captives.married_in_traitor_pct):
            await wring_intel(ctx, captor, home)
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=home.id,
                subject_id=captive.id,
                kind=MemoryKind.BETRAYED_ME,
                magnitude=-ctx.rules.captives.parole_shame,
                epoch=ctx.epoch,
            )
            tally.betrayed += 1
            continue
        await change_relation(ctx, home.id, captor.id, ctx.rules.captives.married_in_bridge, MemoryKind.GOODWILL, note=f"{captive.name} speaks for both")
        tally.bridged += 1
