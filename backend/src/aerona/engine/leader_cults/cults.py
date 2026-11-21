from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.belonging import SatireRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import OathRow, OfficeRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import AccountKind, AccountMedium
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leader_cults import CultFate, CultInstrument
from aerona.domain.enums.made import Authenticity
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OathKind, OathStatus, OfficeKind
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.context import TickContext
from aerona.engine.minds.profiles import MADE_ORIGINS
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record

CI = CultInstrument
INSTRUMENT_INTENSITY = total(
    CultInstrument,
    {
        CI.IMAGES_IN_PUBLIC: 15,
        CI.OFFICIAL_BIOGRAPHY: 10,
        CI.HOLIDAYS: 10,
        CI.OATHS_OF_LOYALTY: 15,
        CI.NAMING_OF_PLACES: 10,
        CI.TEACHING_IN_SCHOOLS: 15,
        CI.STAGED_GATHERINGS: 15,
        CI.BAN_ON_CRITICISM: 10,
    },
)
SINCERITY_COST = total(
    CultInstrument,
    {
        CI.IMAGES_IN_PUBLIC: 1,
        CI.OFFICIAL_BIOGRAPHY: 0,
        CI.HOLIDAYS: 0,
        CI.OATHS_OF_LOYALTY: 2,
        CI.NAMING_OF_PLACES: 1,
        CI.TEACHING_IN_SCHOOLS: -2,
        CI.STAGED_GATHERINGS: 2,
        CI.BAN_ON_CRITICISM: 3,
    },
)
APOTHEOSIS_ZEAL = 60
FATE_RECORDS = total(
    CultFate,
    {
        CultFate.LIVING: "cult.begun",
        CultFate.PASSED_ON: "cult.passed_on",
        CultFate.FADED: "cult.faded",
        CultFate.BECAME_FAITH: "cult.became_faith",
        CultFate.TORN_DOWN: "cult.torn_down",
    },
)
FOLLOWER_SHARE = 10


@dataclass
class CultTally:
    begun: int = 0
    added: int = 0
    punished: int = 0
    passed: int = 0
    faded: int = 0
    faiths: int = 0
    torn: int = 0


def instruments_of(cult: LeaderCultRow) -> list[CultInstrument]:
    known = {item.value: item for item in CultInstrument}
    return [known[value] for value in cult.instruments or [] if value in known]


async def may_lead(session: AsyncSession, node_id: int | None) -> EntityRow | None:
    leader = await living_entity(session, node_id) if node_id is not None else None
    if leader is None:
        return None
    if leader.entity_type is EntityType.MORTAL:
        return leader
    mind = await session.get(MindProfileRow, leader.id)
    return leader if mind is not None and mind.origin in MADE_ORIGINS else None


async def cult_of(session: AsyncSession, leader_id: int) -> LeaderCultRow | None:
    query = select(LeaderCultRow).where(LeaderCultRow.leader_node_id == leader_id, LeaderCultRow.fate == CultFate.LIVING)
    return await session.scalar(query.order_by(LeaderCultRow.id).limit(1))


async def realm_ruled_by(session: AsyncSession, leader_id: int) -> int | None:
    query = select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == leader_id, OfficeRow.kind == OfficeKind.RULER)
    return await session.scalar(query.order_by(OfficeRow.id).limit(1))


async def begin(ctx: TickContext, leader: EntityRow, promoters: list[int], tally: CultTally) -> LeaderCultRow:
    found = await cult_of(ctx.session, leader.id)
    if found is not None:
        return found
    cult = LeaderCultRow(
        leader_node_id=leader.id,
        polity_entity_id=await realm_ruled_by(ctx.session, leader.id),
        promoters=sorted(set(promoters)),
        instruments=[],
        begun_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(cult)
    await ctx.session.flush()
    tally.begun += 1
    await record(
        ctx, "cult.begun", roles={IncidentRole.SUBJECT: leader.id, IncidentRole.PLACE: cult.polity_entity_id}, facts={"promoters": len(cult.promoters)}
    )
    return cult


async def chronicle(ctx: TickContext, cult: LeaderCultRow) -> None:
    ctx.session.add(
        AccountRow(
            holder_entity_id=cult.polity_entity_id or cult.leader_node_id,
            author_node_id=cult.promoters[0] if cult.promoters else None,
            kind=AccountKind.OFFICIAL_CHRONICLE,
            medium=AccountMedium.BOOK,
            subject_node_id=cult.leader_node_id,
            fidelity=clamp_int(cult.sincerity, 0, PERCENT),
            credence=clamp_int(cult.intensity, 0, PERCENT),
            epoch=ctx.epoch,
            authenticity=Authenticity.ALTERED,
            locked=[],
        )
    )


async def swear(ctx: TickContext, cult: LeaderCultRow) -> None:
    if cult.polity_entity_id is None:
        return
    query = select(OfficeRow.holder_entity_id).where(
        OfficeRow.polity_entity_id == cult.polity_entity_id, OfficeRow.holder_entity_id.is_not(None), OfficeRow.kind != OfficeKind.RULER
    )
    officers = {officer for officer in await ctx.session.scalars(query) if officer is not None}
    for officer in sorted(officers):
        if officer == cult.leader_node_id or held(officer):
            continue
        ctx.session.add(
            OathRow(swearer_entity_id=officer, recipient_node_id=cult.leader_node_id, kind=OathKind.FEALTY, status=OathStatus.SWORN, sworn_epoch=ctx.epoch)
        )


async def add_instrument(ctx: TickContext, cult: LeaderCultRow, instrument: CultInstrument, tally: CultTally) -> bool:
    if instrument in instruments_of(cult) or "instruments" in (cult.locked or []):
        return False
    cult.instruments = sorted({*(cult.instruments or []), instrument.value})
    if instrument is CultInstrument.OFFICIAL_BIOGRAPHY:
        await chronicle(ctx, cult)
    elif instrument is CultInstrument.OATHS_OF_LOYALTY:
        await swear(ctx, cult)
    tally.added += 1
    await record(ctx, "cult.instrument_added", roles={IncidentRole.SUBJECT: cult.leader_node_id}, facts={"instrument": instrument})
    return True


async def punish_critics(ctx: TickContext, cult: LeaderCultRow, tally: CultTally) -> None:
    query = select(SatireRow).where(SatireRow.target_entity_id == cult.leader_node_id, SatireRow.punished.is_(False), SatireRow.epoch >= ctx.epoch - 1)
    for satire in list(await ctx.session.scalars(query.order_by(SatireRow.id))):
        if "punished" in (satire.locked or []):
            continue
        satire.punished, satire.tolerated = True, False
        tally.punished += 1
        await record(
            ctx,
            "cult.critic_punished",
            roles={IncidentRole.SUBJECT: cult.leader_node_id, IncidentRole.VICTIM: satire.satirist_entity_id},
            facts={"bite": satire.bite},
        )


async def tend_living(ctx: TickContext, cult: LeaderCultRow, tally: CultTally) -> None:
    table = ctx.rules.leader_cults
    locked = cult.locked or []
    instruments = instruments_of(cult)
    realm = await ctx.session.get(PolityProfileRow, cult.polity_entity_id) if cult.polity_entity_id is not None else None
    cost = table.cost_per_instrument * len(instruments)
    paid = realm is not None and "treasury" not in (realm.locked or []) and realm.treasury >= cost
    if paid and realm is not None:
        realm.treasury -= cost
    target = min(PERCENT, sum(INSTRUMENT_INTENSITY[item] for item in instruments)) if paid or not cost else 0
    if "intensity" not in locked:
        step = table.intensity_step
        cult.intensity = clamp_int(cult.intensity + max(-step, min(step, target - cult.intensity)), 0, PERCENT)
    if "sincerity" not in locked:
        ahead = realm is not None and cult.intensity > realm.stability
        cost_of_show = sum(SINCERITY_COST[item] for item in instruments)
        cult.sincerity = clamp_int(cult.sincerity - (table.sincerity_decay if ahead else -table.sincerity_decay // 2) - cost_of_show, 0, PERCENT)
    if realm is not None and "legitimacy" not in (realm.locked or []):
        realm.legitimacy = clamp_int(realm.legitimacy + round_half_up(cult.intensity * table.legitimacy_per_intensity_pct / (PERCENT * 10)), 0, PERCENT)
    town = await ctx.session.get(SettlementProfileRow, realm.capital_entity_id) if realm is not None and realm.capital_entity_id is not None else None
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest - cult.intensity * table.dissent_relief // PERCENT, 0, PERCENT)
    if CultInstrument.BAN_ON_CRITICISM in instruments:
        await punish_critics(ctx, cult, tally)


async def end(ctx: TickContext, cult: LeaderCultRow, fate: CultFate, tally: CultTally) -> None:
    cult.fate, cult.ended_epoch = fate, ctx.epoch
    await record(
        ctx,
        FATE_RECORDS[fate],
        roles={IncidentRole.SUBJECT: cult.leader_node_id, IncidentRole.SUCCESSOR: cult.heir_node_id or cult.faith_entity_id},
        facts={"intensity": cult.intensity},
    )


async def deify(ctx: TickContext, cult: LeaderCultRow, leader: EntityRow) -> EntityRow:
    realm = await ctx.session.get(PolityProfileRow, cult.polity_entity_id) if cult.polity_entity_id is not None else None
    seat = await ctx.session.get(EntityRow, realm.capital_entity_id) if realm is not None and realm.capital_entity_id is not None else None
    faith = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"the veneration of {leader.name}",
            body=f"Those who kept the cult of {leader.name} came to worship them after their death.",
            stats=CultStats(followers=max(1, cult.intensity * FOLLOWER_SHARE), zeal=APOTHEOSIS_ZEAL, influence=cult.intensity),
            power=max(1, leader.power_level),
            world_id=leader.world_id,
            location_id=seat.id if seat is not None else leader.location_id,
            subtype="veneration of a ruler",
        ),
    )
    await connect(ctx.session, faith.id, leader.id, BondKind.WORSHIPS, ctx.epoch, description="its object of worship")
    cult.faith_entity_id = faith.id
    return faith


async def after_death(ctx: TickContext, cult: LeaderCultRow, leader: EntityRow, tally: CultTally) -> None:
    table = ctx.rules.leader_cults
    realm = await ctx.session.get(PolityProfileRow, cult.polity_entity_id) if cult.polity_entity_id is not None else None
    heir_office = (
        await ctx.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == cult.polity_entity_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
        if realm
        else None
    )
    heir = await may_lead(ctx.session, heir_office.holder_entity_id) if heir_office is not None else None
    if heir is not None and heir.id != leader.id and cult.intensity >= table.pass_on_from:
        cult.heir_node_id = heir.id
        await end(ctx, cult, CultFate.PASSED_ON, tally)
        successor = await begin(ctx, heir, list(cult.promoters or []), tally)
        successor.intensity = cult.intensity // 2
        tally.passed += 1
    elif ctx.rng(f"cults.apotheosis.{cult.id}").chance(table.apotheosis_chance_pct * cult.intensity // PERCENT):
        await deify(ctx, cult, leader)
        await end(ctx, cult, CultFate.BECAME_FAITH, tally)
        tally.faiths += 1
    else:
        await end(ctx, cult, CultFate.FADED, tally)
        tally.faded += 1


async def tear_down(ctx: TickContext, cult: LeaderCultRow, tally: CultTally) -> None:
    if cult.fate is not CultFate.LIVING or "fate" in (cult.locked or []):
        return
    await end(ctx, cult, CultFate.TORN_DOWN, tally)
    tally.torn += 1


async def tend_cults(ctx: TickContext) -> CultTally:
    tally = CultTally()
    for cult in list(await ctx.session.scalars(select(LeaderCultRow).where(LeaderCultRow.fate == CultFate.LIVING).order_by(LeaderCultRow.id))):
        if held(cult.leader_node_id) or (cult.polity_entity_id is not None and held(cult.polity_entity_id)):
            continue
        leader = await ctx.session.get(EntityRow, cult.leader_node_id)
        if leader is None or leader.status is not EntityStatus.CANON:
            if leader is not None:
                await after_death(ctx, cult, leader, tally)
            continue
        await tend_living(ctx, cult, tally)
    await raise_cults(ctx, tally)
    return tally


async def raise_cults(ctx: TickContext, tally: CultTally) -> None:
    query = select(OfficeRow).where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id)
    for office in list(await ctx.session.scalars(query)):
        leader = await may_lead(ctx.session, office.holder_entity_id)
        if leader is None or held(leader.id) or held(office.polity_entity_id) or await cult_of(ctx.session, leader.id) is not None:
            continue
        if not ctx.rng(f"cults.raise.{leader.id}.{ctx.epoch}").chance(ctx.rules.leader_cults.start_chance_pct):
            continue
        cult = await begin(ctx, leader, [], tally)
        await add_instrument(ctx, cult, CultInstrument.IMAGES_IN_PUBLIC, tally)
