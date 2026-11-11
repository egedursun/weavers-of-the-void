from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.law_depth import HUNT_TEXT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import MoleHuntRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.law_depth import MoleHuntOutcome
from aerona.domain.enums.military import AgentStatus
from aerona.domain.enums.mind import MemoryKind, SkillKind, TraitKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.military.spy_depth import compromise, defect
from aerona.engine.mind.book import skill_level, traits_of
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.relations.book import relation
from aerona.engine.services.war import held_captive, take_captive

KEPT_OFFICES = frozenset({OfficeKind.RULER, OfficeKind.SPYMASTER})
DILIGENCE = "diligence"


@dataclass
class MoleTally:
    hunts: int = 0
    caught: int = 0
    purged: int = 0
    defected: int = 0
    cleared: int = 0


async def moles_in(ctx: TickContext, polity_id: int) -> list[tuple[SpyAgentRow, SpyNetworkRow]]:
    towns = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))
    targets = [polity_id, *towns]
    networks = {row.id: row for row in await ctx.session.scalars(select(SpyNetworkRow).where(SpyNetworkRow.target_entity_id.in_(targets)))}
    if not networks:
        return []
    present = set(
        await ctx.session.scalars(
            select(EntityRow.id).where(
                EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, towns)
            )
        )
    )
    agents = await ctx.session.scalars(
        select(SpyAgentRow).where(SpyAgentRow.network_id.in_(list(networks)), SpyAgentRow.status == AgentStatus.ACTIVE).order_by(SpyAgentRow.id)
    )
    return [(agent, networks[agent.network_id]) for agent in agents if agent.mortal_entity_id in present and not held(agent.mortal_entity_id)]


async def record(ctx: TickContext, polity_id: int, spymaster_id: int, suspect_id: int | None, outcome: MoleHuntOutcome, *, mole: bool) -> None:
    ctx.session.add(
        MoleHuntRow(polity_entity_id=polity_id, spymaster_entity_id=spymaster_id, suspect_entity_id=suspect_id, mole=mole, outcome=outcome, epoch=ctx.epoch)
    )
    realm, spymaster = await ctx.session.get(EntityRow, polity_id), await ctx.session.get(EntityRow, spymaster_id)
    suspect = await ctx.session.get(EntityRow, suspect_id) if suspect_id is not None else None
    if realm is not None and spymaster is not None:
        whom = f": {suspect.name}" if suspect is not None else ""
        await note(
            ctx,
            f"{spymaster.name}, spymaster of {realm.name}, hunted for moles and {HUNT_TEXT[outcome]}{whom}.",
            key=f"espionage.mole_{outcome.value}",
            ids=[spymaster.id, realm.id, *([suspect_id] if suspect_id is not None else [])],
            kind=ChronicleKind.WAR,
        )


async def catch_mole(ctx: TickContext, polity_id: int, spymaster_id: int, agent: SpyAgentRow, network: SpyNetworkRow) -> None:
    agent.status, agent.ended_epoch = AgentStatus.CAUGHT, ctx.epoch
    await compromise(ctx, network, agent)
    mortal = await living_entity(ctx.session, agent.mortal_entity_id) if agent.mortal_entity_id is not None else None
    realm = await ctx.session.get(EntityRow, polity_id)
    if mortal is not None and realm is not None and await held_captive(ctx.session, mortal.id) is None:
        await take_captive(ctx, realm, mortal, None, description="a mole caught at court", home_id=network.side_entity_id)
    await record(ctx, polity_id, spymaster_id, agent.mortal_entity_id, MoleHuntOutcome.CAUGHT, mole=True)


async def officials(ctx: TickContext, polity_id: int) -> list[OfficeRow]:
    rows = await ctx.session.scalars(
        select(OfficeRow).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id)
    )
    return [row for row in rows if row.kind not in KEPT_OFFICES and not held(row.holder_entity_id)]


async def rival_of(ctx: TickContext, polity_id: int) -> int | None:
    return await ctx.session.scalar(
        select(SpyNetworkRow.owner_entity_id).where(SpyNetworkRow.target_entity_id == polity_id).order_by(SpyNetworkRow.depth.desc()).limit(1)
    )


async def purge(ctx: TickContext, polity_id: int, spymaster_id: int, office: OfficeRow, accused: EntityRow) -> None:
    office.holder_entity_id = None
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=accused.id,
        subject_id=spymaster_id,
        kind=MemoryKind.BETRAYED_ME,
        magnitude=-PERCENT // 4,
        epoch=ctx.epoch,
        note="accused falsely",
    )
    for other in await officials(ctx, polity_id):
        if DILIGENCE not in (other.locked or []):
            other.diligence = clamp_int(other.diligence - ctx.rules.mole_hunts.purge_loyalty, 0, PERCENT)
    await record(ctx, polity_id, spymaster_id, accused.id, MoleHuntOutcome.PURGED, mole=False)


async def accuse_innocent(ctx: TickContext, polity_id: int, spymaster_id: int, tally: MoleTally) -> None:
    table = ctx.rules.mole_hunts
    found = await officials(ctx, polity_id)
    if not found:
        return
    office = ctx.rng(f"espionage.suspect.{polity_id}.{ctx.epoch}").pick(found)
    accused = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
    if accused is None:
        return
    ruler = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    trust = await relation(ctx.session, ruler, accused.id) if ruler is not None else None
    if trust is not None and trust.friendship >= ctx.rules.pardons.friend_at:
        await record(ctx, polity_id, spymaster_id, accused.id, MoleHuntOutcome.CLEARED, mole=False)
        tally.cleared += 1
        return
    rival = await rival_of(ctx, polity_id)
    if rival is not None and ctx.rng(f"espionage.flee.{accused.id}.{ctx.epoch}").chance(table.defect_pct):
        office.holder_entity_id = None
        await defect(ctx, accused, polity_id, rival)
        await record(ctx, polity_id, spymaster_id, accused.id, MoleHuntOutcome.DEFECTED, mole=False)
        tally.defected += 1
        return
    await purge(ctx, polity_id, spymaster_id, office, accused)
    tally.purged += 1


async def hunt(ctx: TickContext, polity_id: int, spymaster: EntityRow, tally: MoleTally, *, forced: bool = False) -> None:
    table = ctx.rules.mole_hunts
    paranoid = table.paranoid_pct if TraitKind.PARANOID in await traits_of(ctx.session, spymaster.id) else 0
    rng = ctx.rng(f"espionage.hunt.{polity_id}.{ctx.epoch}")
    if not forced and not rng.chance(table.hunt_pct + paranoid):
        return
    tally.hunts += 1
    skill = await skill_level(ctx.session, spymaster.id, SkillKind.INTRIGUE)
    moles = await moles_in(ctx, polity_id)
    if moles and rng.chance(round_half_up(table.catch_pct * max(skill, PERCENT // 4) / PERCENT)):
        agent, network = max(moles, key=lambda item: (item[0].exposure, item[0].id))
        await catch_mole(ctx, polity_id, spymaster.id, agent, network)
        tally.caught += 1
        return
    if rng.chance(table.false_pct + paranoid):
        await accuse_innocent(ctx, polity_id, spymaster.id, tally)


async def hunt_moles(ctx: TickContext, tally: MoleTally) -> None:
    offices = await ctx.session.scalars(
        select(OfficeRow).where(OfficeRow.kind == OfficeKind.SPYMASTER, OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.polity_entity_id)
    )
    for office in list(offices):
        spymaster = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
        if spymaster is None or held(office.polity_entity_id, spymaster.id):
            continue
        await hunt(ctx, office.polity_entity_id, spymaster, tally)
    await ctx.session.flush()
