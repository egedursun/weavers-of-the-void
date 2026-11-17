from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.ages import AgeEchoRow, ArcBeatRow, ArcFigureRow, ArcRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, LegendaryQuestRow, ThreadLinkRow
from aerona.db.tables.mind import TraitRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.mythic import MantlingRow
from aerona.db.tables.polity import HouseProfileRow, OathRow, OfficeHistoryRow, OfficeRow, SentenceRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import ArcOutcome, ArcRole, ArcStage, ArcTemplate
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import OathStatus, OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record as record_incident

STAGES = (ArcStage.INCITING, ArcStage.RISING, ArcStage.CRISIS, ArcStage.CLIMAX, ArcStage.RESOLUTION)
MONOMYTH = (ArcStage.CALL, ArcStage.REFUSAL, ArcStage.MENTOR, ArcStage.THRESHOLD, ArcStage.ORDEAL, ArcStage.RETURN, ArcStage.RESOLUTION)
YOUNG = frozenset({LifeStage.CHILD, LifeStage.YOUTH})
FLAWS = (TraitKind.WRATHFUL, TraitKind.PROUD, TraitKind.PARANOID, TraitKind.CRUEL)
KIN = (BondKind.PARENT_OF, BondKind.SPOUSE_OF, BondKind.SWORN_KIN)
FALLEN = 15
INFAMOUS = 50
RENOWNED = 30
RECENT = 3
ENDS_IN_DEATH = frozenset({ArcTemplate.TRAGEDY, ArcTemplate.FALL_OF_A_HOUSE, ArcTemplate.RISE_AND_FALL})

Figure = tuple[int, ArcRole]


def stages_of(template: ArcTemplate) -> tuple[ArcStage, ...]:
    return MONOMYTH if template is ArcTemplate.QUEST else STAGES


@dataclass(frozen=True)
class Candidate:
    subject_id: int
    template: ArcTemplate
    figures: tuple[Figure, ...] = ()


@dataclass
class ArcTally:
    begun: int = 0
    beats: int = 0
    fulfilled: int = 0
    failed: int = 0
    twisted: int = 0
    ironic: int = 0


async def living(ctx: TickContext, node_id: int | None) -> bool:
    return await living_entity(ctx.session, node_id) is not None


async def bonds(ctx: TickContext, kind: BondKind) -> list[BondRow]:
    rows = await ctx.session.scalars(select(BondRow).where(BondRow.kind == kind, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    return list(rows)


async def revenge(ctx: TickContext) -> list[Candidate]:
    found: list[Candidate] = []
    killings = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.KILLED, BondRow.epoch >= ctx.epoch - RECENT).order_by(BondRow.id))
    for killing in list(killings):
        if not await living(ctx, killing.source_node_id):
            continue
        kin = await ctx.session.scalars(
            select(BondRow).where(
                BondRow.kind.in_(KIN), (BondRow.source_node_id == killing.target_node_id) | (BondRow.target_node_id == killing.target_node_id)
            )
        )
        for tie in kin:
            avenger = tie.target_node_id if tie.source_node_id == killing.target_node_id else tie.source_node_id
            if avenger != killing.source_node_id and await living(ctx, avenger):
                found.append(Candidate(avenger, ArcTemplate.REVENGE, ((killing.source_node_id, ArcRole.FOE),)))
    return found


async def paired(ctx: TickContext, kind: BondKind, template: ArcTemplate, role: ArcRole) -> list[Candidate]:
    found: list[Candidate] = []
    for bond in await bonds(ctx, kind):
        if await living(ctx, bond.source_node_id) and await living(ctx, bond.target_node_id):
            found.append(Candidate(bond.source_node_id, template, ((bond.target_node_id, role),)))
    return found


async def rivalry(ctx: TickContext) -> list[Candidate]:
    return await paired(ctx, BondKind.RIVAL, ArcTemplate.RIVALRY, ArcRole.RIVAL)


async def apprenticeship(ctx: TickContext) -> list[Candidate]:
    found: list[Candidate] = []
    for candidate in await paired(ctx, BondKind.APPRENTICE_OF, ArcTemplate.MENTOR_AND_HEIR, ArcRole.MENTOR):
        profile = await ctx.session.get(MortalProfileRow, candidate.subject_id)
        young = profile is not None and profile.life_stage in YOUNG
        found.append(Candidate(candidate.subject_id, ArcTemplate.COMING_OF_AGE if young else ArcTemplate.MENTOR_AND_HEIR, candidate.figures))
    return found


async def forbidden_love(ctx: TickContext) -> list[Candidate]:
    found: list[Candidate] = []
    for bond in await bonds(ctx, BondKind.LOVES):
        lover, beloved = bond.source_node_id, bond.target_node_id
        if not (await living(ctx, lover) and await living(ctx, beloved)):
            continue
        wed = await ctx.session.scalar(
            select(BondRow.id)
            .where(
                BondRow.kind == BondKind.SPOUSE_OF,
                BondRow.state == BondState.ACTIVE,
                ((BondRow.source_node_id == beloved) & (BondRow.target_node_id != lover))
                | ((BondRow.target_node_id == beloved) & (BondRow.source_node_id != lover)),
            )
            .limit(1)
        )
        one, two = await ctx.session.get(EntityRow, lover), await ctx.session.get(EntityRow, beloved)
        sides = [item.affiliated_entity_id for item in (one, two) if item is not None and item.affiliated_entity_id is not None]
        feud = len(sides) == 2 and await ctx.session.scalar(
            select(BondRow.id)
            .where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == sides[0], BondRow.target_node_id == sides[1])
            .limit(1)
        )
        if wed is not None or feud:
            found.append(Candidate(lover, ArcTemplate.FORBIDDEN_LOVE, ((beloved, ArcRole.BELOVED),)))
    return found


async def exile(ctx: TickContext) -> list[Candidate]:
    rows = await ctx.session.scalars(
        select(SentenceRow).where(SentenceRow.penalty == "exile", SentenceRow.epoch >= ctx.epoch - RECENT).order_by(SentenceRow.id)
    )
    return [Candidate(row.mortal_entity_id, ArcTemplate.EXILE_AND_RETURN) for row in rows if await living(ctx, row.mortal_entity_id)]


async def rulers(ctx: TickContext) -> list[Candidate]:
    found: list[Candidate] = []
    for office in await ctx.session.scalars(
        select(OfficeRow).where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id)
    ):
        ruler = office.holder_entity_id
        if ruler is None or not await living(ctx, ruler):
            continue
        flawed = await ctx.session.scalar(select(TraitRow.trait).where(TraitRow.node_id == ruler, TraitRow.trait.in_(FLAWS)).limit(1))
        if flawed is not None:
            found.append(Candidate(ruler, ArcTemplate.TRAGEDY))
        profile = await ctx.session.get(MortalProfileRow, ruler)
        heir_born = await ctx.session.scalar(select(BondRow.id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.target_node_id == ruler).limit(1))
        if profile is not None and heir_born is None and office.since_epoch >= ctx.epoch - RECENT:
            found.append(Candidate(ruler, ArcTemplate.RAGS_TO_RICHES))
    return found


async def deposed(ctx: TickContext) -> list[Candidate]:
    rows = await ctx.session.scalars(
        select(OfficeHistoryRow).where(OfficeHistoryRow.to_epoch.is_not(None), OfficeHistoryRow.to_epoch >= ctx.epoch - RECENT).order_by(OfficeHistoryRow.id)
    )
    return [
        Candidate(row.holder_entity_id, ArcTemplate.RISE_AND_FALL)
        for row in rows
        if row.holder_entity_id is not None and await living(ctx, row.holder_entity_id)
    ]


async def redemption(ctx: TickContext) -> list[Candidate]:
    rows = await ctx.session.scalars(
        select(MortalProfileRow).where(MortalProfileRow.infamy >= INFAMOUS, MortalProfileRow.renown >= RENOWNED).order_by(MortalProfileRow.entity_id)
    )
    return [Candidate(row.entity_id, ArcTemplate.REDEMPTION) for row in rows if await living(ctx, row.entity_id)]


async def corruption(ctx: TickContext) -> list[Candidate]:
    return [
        Candidate(bond.target_node_id, ArcTemplate.CORRUPTION, ((bond.source_node_id, ArcRole.FOE),))
        for bond in await bonds(ctx, BondKind.CURSED)
        if (await ctx.session.get(EntityRow, bond.target_node_id)) is not None and await living(ctx, bond.target_node_id)
    ]


async def houses(ctx: TickContext) -> list[Candidate]:
    found: list[Candidate] = []
    for row in await ctx.session.scalars(select(HouseProfileRow).where(HouseProfileRow.extinct_epoch.is_(None)).order_by(HouseProfileRow.house_entity_id)):
        if row.prestige <= FALLEN and await living(ctx, row.house_entity_id):
            found.append(Candidate(row.house_entity_id, ArcTemplate.FALL_OF_A_HOUSE, ((row.head_entity_id, ArcRole.HEIR),) if row.head_entity_id else ()))
        if row.founded_epoch >= ctx.epoch - RECENT and row.founder_entity_id is not None and await living(ctx, row.founder_entity_id):
            found.append(Candidate(row.founder_entity_id, ArcTemplate.FOUNDING))
    return found


async def quests(ctx: TickContext) -> list[Candidate]:
    rows = await ctx.session.execute(
        select(ThreadLinkRow.entity_id, LegendaryQuestRow.target_entity_id)
        .join(LegendaryQuestRow, LegendaryQuestRow.thread_id == ThreadLinkRow.thread_id)
        .where(LegendaryQuestRow.outcome.is_(None))
        .order_by(ThreadLinkRow.thread_id)
    )
    found: list[Candidate] = []
    for hero, target in rows:
        figure = ((target, ArcRole.FOE),) if target is not None else ()
        hero_row = await living_entity(ctx.session, hero)
        if hero_row is not None and hero_row.entity_type is EntityType.MORTAL:
            found.append(Candidate(hero, ArcTemplate.QUEST, figure))
    return found


async def apotheosis(ctx: TickContext) -> list[Candidate]:
    rows = await ctx.session.scalars(select(MantlingRow).order_by(MantlingRow.mortal_entity_id))
    return [
        Candidate(row.mortal_entity_id, ArcTemplate.APOTHEOSIS, ((row.god_node_id, ArcRole.MENTOR),) if row.god_node_id else ())
        for row in rows
        if await living(ctx, row.mortal_entity_id)
    ]


async def betrayals(ctx: TickContext) -> list[Candidate]:
    rows = await ctx.session.execute(
        select(OathRow.swearer_entity_id, OathRow.recipient_node_id)
        .where(OathRow.status == OathStatus.BROKEN, OathRow.recipient_node_id.is_not(None), OathRow.ended_epoch == ctx.epoch)
        .order_by(OathRow.id)
    )
    found: list[Candidate] = []
    for breaker, wronged in rows.all():
        if wronged is not None and await living(ctx, wronged) and await living(ctx, breaker):
            found.append(Candidate(wronged, ArcTemplate.REVENGE, ((breaker, ArcRole.BETRAYER),)))
    return found


DETECTORS: tuple[Callable[[TickContext], Awaitable[list[Candidate]]], ...] = (
    revenge,
    betrayals,
    rivalry,
    apprenticeship,
    forbidden_love,
    exile,
    rulers,
    deposed,
    redemption,
    corruption,
    houses,
    quests,
    apotheosis,
)


async def open_arcs_of(ctx: TickContext, subject_id: int) -> list[ArcRow]:
    rows = await ctx.session.scalars(select(ArcRow).where(ArcRow.subject_node_id == subject_id, ArcRow.outcome == ArcOutcome.OPEN))
    return list(rows)


async def open_arc(ctx: TickContext, subject_id: int, template: ArcTemplate, figures: tuple[Figure, ...] = (), *, echo_id: int | None = None) -> ArcRow:
    first = stages_of(template)[0]
    row = ArcRow(subject_node_id=subject_id, template=template, stage=first, echo_id=echo_id, started_epoch=ctx.epoch, last_beat_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    for node_id, role in figures:
        if node_id != subject_id and await ctx.session.get(ArcFigureRow, (row.id, node_id)) is None:
            ctx.session.add(ArcFigureRow(arc_id=row.id, node_id=node_id, role=role, locked=[]))
    ctx.session.add(ArcBeatRow(arc_id=row.id, stage=first, text=template.value.replace("_", " "), epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    return row


async def echo_weight(ctx: TickContext, template: ArcTemplate) -> int:
    weight = await ctx.session.scalar(select(func.max(AgeEchoRow.weight)).where(AgeEchoRow.template == template, AgeEchoRow.echo_node_id.is_(None)))
    return int(weight or 0)


async def detect(ctx: TickContext, tally: ArcTally) -> None:
    table = ctx.rules.arcs
    for detector in DETECTORS:
        for candidate in await detector(ctx):
            if tally.begun >= table.arcs_per_epoch:
                return
            if held(candidate.subject_id):
                continue
            current = await open_arcs_of(ctx, candidate.subject_id)
            if len(current) >= table.open_arcs or any(row.template is candidate.template for row in current):
                continue
            chance = clamp_int(table.detect_chance * (PERCENT + await echo_weight(ctx, candidate.template)) // PERCENT, 0, PERCENT)
            if not ctx.rng(f"arc.detect.{candidate.subject_id}.{candidate.template.value}.{ctx.epoch}").chance(chance):
                continue
            row = await open_arc(ctx, candidate.subject_id, candidate.template, candidate.figures)
            tally.begun += 1
            await record_incident(
                ctx,
                "arcs.begun",
                roles={IncidentRole.SUBJECT: row.subject_node_id, IncidentRole.MEMBER: [node for node, _ in candidate.figures]},
                facts={
                    "template": candidate.template,
                },
            )


async def shared_incident(ctx: TickContext, subject_id: int, figure_ids: list[int], since: int) -> ChronicleRow | None:
    mine = select(ChronicleEntityRow.chronicle_id).where(ChronicleEntityRow.entity_id == subject_id)
    query = select(ChronicleRow).where(ChronicleRow.id.in_(mine), ChronicleRow.epoch > since)
    if figure_ids:
        theirs = select(ChronicleEntityRow.chronicle_id).where(ChronicleEntityRow.entity_id.in_(figure_ids))
        query = query.where(ChronicleRow.id.in_(theirs))
    return await ctx.session.scalar(query.order_by(ChronicleRow.id.desc()).limit(1))


async def figures_of(ctx: TickContext, arc_id: int) -> list[ArcFigureRow]:
    rows = await ctx.session.scalars(select(ArcFigureRow).where(ArcFigureRow.arc_id == arc_id).order_by(ArcFigureRow.node_id))
    return list(rows)


def outcome_on_death(arc: ArcRow, subject_alive: bool, foes_alive: bool, killed_by_subject: bool) -> ArcOutcome | None:
    if not subject_alive:
        return ArcOutcome.FULFILLED if arc.template in ENDS_IN_DEATH else ArcOutcome.FAILED
    if arc.template is ArcTemplate.REVENGE and not foes_alive:
        return ArcOutcome.FULFILLED if killed_by_subject else ArcOutcome.IRONIC
    return None


async def close(ctx: TickContext, arc: ArcRow, outcome: ArcOutcome, tally: ArcTally) -> None:
    arc.outcome = outcome
    arc.ended_epoch = ctx.epoch
    arc.stage = ArcStage.RESOLUTION
    setattr(tally, outcome.value, getattr(tally, outcome.value) + 1)
    ctx.session.add(ArcBeatRow(arc_id=arc.id, stage=ArcStage.RESOLUTION, text=outcome.value, epoch=ctx.epoch, locked=[]))
    await record_incident(ctx, "arcs.ended", roles={IncidentRole.SUBJECT: arc.subject_node_id}, facts={"template": arc.template, "outcome": outcome})


async def advance(ctx: TickContext, arc: ArcRow, tally: ArcTally) -> bool:
    figures = await figures_of(ctx, arc.id)
    foe_ids = [row.node_id for row in figures if row.role in (ArcRole.FOE, ArcRole.RIVAL)]
    subject_alive = await living(ctx, arc.subject_node_id)
    foes_alive = not foe_ids or any([await living(ctx, node) for node in foe_ids])
    killed = await ctx.session.scalar(
        select(BondRow.id)
        .where(BondRow.kind == BondKind.KILLED, BondRow.source_node_id == arc.subject_node_id, BondRow.target_node_id.in_(foe_ids or [0]))
        .limit(1)
    )
    ending = outcome_on_death(arc, subject_alive, foes_alive, killed is not None)
    if ending is not None and "outcome" not in arc.locked:
        await close(ctx, arc, ending, tally)
        return True
    incident = await shared_incident(ctx, arc.subject_node_id, [row.node_id for row in figures], arc.last_beat_epoch)
    if incident is None or "stage" in arc.locked:
        return False
    stages = stages_of(arc.template)
    position = stages.index(arc.stage) if arc.stage in stages else 0
    if position + 1 >= len(stages) - 1:
        if "outcome" not in arc.locked:
            await close(ctx, arc, ArcOutcome.TWISTED if arc.drama >= PERCENT else ArcOutcome.FULFILLED, tally)
        return True
    arc.stage = stages[position + 1]
    arc.beats += 1
    arc.last_beat_epoch = ctx.epoch
    ctx.session.add(ArcBeatRow(arc_id=arc.id, stage=arc.stage, text=incident.text, epoch=ctx.epoch, locked=[]))
    tally.beats += 1
    return True


async def keep_arcs(ctx: TickContext, tally: ArcTally) -> list[ArcRow]:
    moved: list[ArcRow] = []
    for arc in list(await ctx.session.scalars(select(ArcRow).where(ArcRow.outcome == ArcOutcome.OPEN).order_by(ArcRow.id))):
        if held(arc.subject_node_id):
            continue
        if await advance(ctx, arc, tally):
            moved.append(arc)
    await ctx.session.flush()
    return moved
