from sqlalchemy import select

from aerona.catalog.laws import LAW_PARAMS, PENALTY_CRUELTY, PENALTY_HARM
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import ClaimRow, PolityMemberRow, SentenceRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import CrimeKind, LawKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarStatus
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.faith.book import patron_node
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.repute import shift_infamy
from aerona.engine.primitives.queries import add_flag
from aerona.engine.settlement.book import Town, ledger

RECENT_EPOCHS = 2
CRUEL = 60
BANDIT_ENGINE_KINDS = frozenset({EngineKind.REBELS, EngineKind.VOID_PIRATES})
TREASON_ENGINE_KINDS = frozenset({EngineKind.REBELS})


async def _members_of(ctx: TickContext, mortals: list[EntityRow]) -> dict[int, set[EngineKind]]:
    ids = [mortal.id for mortal in mortals]
    found: dict[int, set[EngineKind]] = {}
    if not ids:
        return found
    statement = (
        select(BondRow.source_node_id, EntityRow.engine_kind)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.kind == BondKind.MEMBER_OF,
            BondRow.state == BondState.ACTIVE,
            BondRow.source_node_id.in_(ids),
            EntityRow.entity_type == EntityType.FACTION,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    for mortal_id, engine_kind in await ctx.session.execute(statement):
        if engine_kind is not None:
            found.setdefault(mortal_id, set()).add(engine_kind)
    return found


async def _at_war(ctx: TickContext, town_id: int) -> bool:
    polity = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    sides = [town_id, *([polity] if polity is not None else [])]
    found = await ctx.session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(sides), WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        .limit(1)
    )
    return found is not None


async def offenders(ctx: TickContext, town_id: int, laws: LawBook) -> dict[CrimeKind, list[EntityRow]]:
    mortals = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == town_id)
            .order_by(EntityRow.id)
        )
    )
    found: dict[CrimeKind, list[EntityRow]] = {kind: [] for kind in CrimeKind}
    if not mortals:
        return found
    ids = {mortal.id for mortal in mortals}
    bands = await _members_of(ctx, mortals)
    killers = set(
        await ctx.session.scalars(
            select(MemoryRow.subject_node_id).where(
                MemoryRow.kind == MemoryKind.KILLED_KIN, MemoryRow.epoch >= ctx.epoch - RECENT_EPOCHS, MemoryRow.subject_node_id.in_(list(ids))
            )
        )
    )
    pressing = set(await ctx.session.scalars(select(ClaimRow.claimant_entity_id).where(ClaimRow.pressed.is_(True), ClaimRow.ended_epoch.is_(None))))
    banned = laws.param(town_id, LawKind.WORSHIP_BAN, "son_id")
    tolerance = laws.param(town_id, LawKind.RELIGIOUS_TOLERANCE, "level")
    home_god = await patron_node(ctx.session, town_id)
    worship = {
        source: target
        for source, target in await ctx.session.execute(
            select(BondRow.source_node_id, BondRow.target_node_id).where(
                BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(list(ids))
            )
        )
    }
    commanders = set(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.COMMANDS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(list(ids)))
        )
    )
    war = await _at_war(ctx, town_id)
    for mortal in mortals:
        kinds = bands.get(mortal.id, set())
        if kinds & TREASON_ENGINE_KINDS or mortal.id in pressing:
            found[CrimeKind.TREASON].append(mortal)
        if mortal.id in killers:
            found[CrimeKind.MURDER].append(mortal)
        god = worship.get(mortal.id)
        if god is not None and ((banned and god == int(banned)) or (tolerance == "persecution" and home_god is not None and god != home_god)):
            found[CrimeKind.BLASPHEMY].append(mortal)
        if war and mortal.social_class is SocialClass.WARRIOR and mortal.id not in commanders:
            found[CrimeKind.DESERTION].append(mortal)
        if mortal.social_class is SocialClass.OUTCAST or kinds & BANDIT_ENGINE_KINDS:
            found[CrimeKind.THEFT].append(mortal)
    return found


async def sentence(ctx: TickContext, town: Town, laws: LawBook, *, ruler_id: int | None) -> SentenceRow | None:
    table = ctx.rules.crime
    found = {kind: rows for kind, rows in (await offenders(ctx, town.entity.id, laws)).items() if rows}
    if not found:
        return None
    rng = ctx.rng(f"culprit.{town.entity.id}")
    crime = rng.pick(sorted(found, key=lambda kind: list(CrimeKind).index(kind)))
    culprit = rng.pick(found[crime])
    row = laws.in_force(town.entity.id, LawKind.PENAL_CODE)
    default = LAW_PARAMS[LawKind.PENAL_CODE][crime.value].default
    penalty = str(row.params.get(crime.value, default) if row is not None else default)
    record = SentenceRow(
        mortal_entity_id=culprit.id,
        settlement_entity_id=town.entity.id,
        law_entity_id=row.law_entity_id if row is not None else None,
        crime=crime,
        penalty=penalty,
        epoch=ctx.epoch,
    )
    ctx.session.add(record)
    if penalty == "exile":
        culprit.location_id = None
        await add_flag(ctx.session, culprit.id, EntityFlag.EXILE, ctx.epoch)
    elif penalty in {"fine", "wergild"}:
        ledger(ctx, town, TreasuryEntry.TAX, ctx.rules.legislation.fine_amount, f"{crime.value} {penalty}")
    else:
        hp = PENALTY_HARM.get(penalty, table.punishment_hp)
        if hp > 0:
            await apply_hits(ctx, culprit, Harm(hp, HarmCause.PUNISHMENT, f"punished for {crime.value} in {town.entity.name}"))
    if ruler_id is not None and PENALTY_CRUELTY.get(penalty, 0) >= CRUEL:
        await shift_infamy(ctx, ruler_id, ctx.rules.legislation.penal_infamy * PENALTY_CRUELTY.get(penalty, 0) // PERCENT)
    ctx.count(f"sentence.{crime.value}")
    return record
