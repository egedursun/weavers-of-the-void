import math
from dataclasses import dataclass

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.chronicle import write_line
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.siblings import relations_of
from aerona.agents.context.world_header import world_header
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import sanitize
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import RARITY_LABELS
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import CouncilRow, ThreadRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.agent import CouncilCaller, CouncilVote
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, ThreadStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarStatus
from aerona.domain.models.records import CouncilBallot, CouncilMinutes, CouncilSpeech
from aerona.engine.primitives.doom import step_doom
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.council import AgendaKind, CouncilAgendaContext, CouncilMember, CouncilRelation, CouncilSessionContext
from aerona.prompts.schemas.council import AllianceChange, CouncilDecision, CouncilOutput, VoteOutput
from aerona.rules.registry import Rules

PERCENT = 100
MEMBER_STATUSES = (SonStatus.ACTIVE, SonStatus.ASLEEP)
TRAILING_PUNCTUATION = " .!?;:"
DEFAULT_CROWD = 100


@dataclass(frozen=True)
class CouncilResult:
    council_id: int
    topic: str
    passed: bool
    motion: str
    notes: list[str]


def cut(text: str | None, limit: int) -> str:
    value = text or ""
    return value if len(value) <= limit else value[:limit]


def member_of(rules: Rules, scope: Scope, son: SonRow) -> CouncilMember:
    council = rules.council
    personality = son.personality
    return CouncilMember(
        id=son.id,
        name=son.name,
        title=son.title,
        rarity_label=RARITY_LABELS[son.rarity],
        domain_1=DOMAIN_LABELS[son.domain_primary],
        domain_2=DOMAIN_LABELS[son.domain_secondary],
        rebel=son.rebel,
        temperament=cut(personality.temperament, council.persona_temperament_chars),
        speech_style=cut(personality.speech_style, council.persona_style_chars),
        obsession=cut(personality.obsession, council.persona_obsession_chars),
        loyalty=son.loyalty,
        ambition=son.ambition,
        wrath=son.wrath,
        plan=cut(son.plan, council.persona_plan_chars) or None,
        current_world=scope.world_name(son.current_world_id) or None if scope.multi_world else None,
    )


async def agenda(scope: Scope) -> str:
    rules = scope.rules
    threshold = rules.balance.apocalypse_threshold
    kind, subject = AgendaKind.DEFAULT, ""
    rebel = await scope.session.scalar(select(SonRow).where(SonRow.rebel.is_(True), SonRow.status != SonStatus.DEAD).limit(1))
    dead = await scope.session.scalar(select(SonRow).where(SonRow.status == SonStatus.DEAD).order_by(SonRow.death_epoch.desc()).limit(1))
    war = await scope.session.scalar(
        select(EntityRow.name).join(WarRow, WarRow.event_entity_id == EntityRow.id).where(WarRow.status == WarStatus.ONGOING).limit(1)
    )
    thread = await scope.session.scalar(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN).order_by(ThreadRow.epoch).limit(1))
    if scope.cosmos.doom_clock * PERCENT >= threshold * rules.council.agenda_apocalypse_pct and scope.cosmos.doom_clock > 0:
        kind = AgendaKind.DOOMSDAY
    elif rebel is not None:
        kind, subject = AgendaKind.REBEL, rebel.name
    elif dead is not None and dead.death_epoch is not None and scope.epoch - dead.death_epoch <= 1:
        kind, subject = AgendaKind.DEAD_BROTHER, dead.name
    elif war:
        kind, subject = AgendaKind.WAR, war
    elif thread is not None:
        text = (
            thread.text if len(thread.text) <= rules.council.agenda_thread_max_chars else thread.text[: rules.council.agenda_cut_chars].rsplit(" ", 1)[0] + "…"
        )
        kind, subject = AgendaKind.OPEN_THREAD, text
    context = CouncilAgendaContext(rules=rules, kind=kind, doom=scope.cosmos.doom_clock, doom_threshold=threshold, subject=subject)
    return render(PromptId.COUNCIL_AGENDA, context)


async def covenant_between(scope: Scope, first: int, second: int) -> list[BondRow]:
    return await BondRepository(scope.session).active_between(first, second, [BondKind.ALLY])


async def session_context(scope: Scope, members: list[SonRow], topic: str, god_asked: bool) -> CouncilSessionContext:
    rules = scope.rules
    relations: list[CouncilRelation] = []
    for index, son in enumerate(members):
        values = await relations_of(scope, son.id)
        for other in members[index + 1 :]:
            value = values.get(other.id, 0)
            covenant = bool(await covenant_between(scope, son.id, other.id))
            if abs(value) >= rules.council.relation_min_magnitude or covenant:
                relations.append(CouncilRelation(a=son.name, b=other.name, label="ally" if value >= 0 else "rival", value=value, covenant=covenant))
    ids = {son.id for son in members}
    absent = [son.name for son in await scope.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)) if son.id not in ids]
    return CouncilSessionContext(
        lore_language=scope.cosmos.lore_language,
        rules=rules,
        world_name=scope.cosmos.name,
        creator_name=scope.creator.name,
        world_header=await world_header(scope),
        topic=topic,
        god_asked=god_asked,
        members=[member_of(rules, scope, son) for son in members],
        absent=absent,
        multi_world=scope.multi_world,
        relationships=relations,
    )


def crowd(entity: EntityRow) -> int:
    return int(getattr(entity.stats, "population", None) or getattr(entity.stats, "followers", None) or DEFAULT_CROWD)


async def call_for_peace(scope: Scope, member_ids: set[int], epoch: int) -> str | None:
    bonds = list(await scope.session.scalars(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE)))
    repository = BondRepository(scope.session)
    best: tuple[float, BondRow, EntityRow, EntityRow] | None = None
    for bond in bonds:
        source = await scope.session.get(EntityRow, bond.source_node_id)
        target = await scope.session.get(EntityRow, bond.target_node_id)
        if source is None or target is None or source.status is not EntityStatus.CANON or target.status is not EntityStatus.CANON:
            continue
        score = math.log10(crowd(source) + crowd(target))
        score += 2 if await repository.patron(source.id) in member_ids else 0
        score += 2 if await repository.patron(target.id) in member_ids else 0
        if best is None or score > best[0]:
            best = (score, bond, source, target)
    if best is None:
        return None
    _, _, source, target = best
    await repository.close_between(source.id, target.id, [BondKind.ENEMY], epoch, "council peace")
    return f"by the gods' command {source.name} and {target.name} made peace"


async def tally(scope: Scope, names: dict[int, str], output: CouncilOutput) -> dict[int, VoteOutput]:
    votes: dict[int, VoteOutput] = {}
    for vote in output.votes:
        if vote.son_id in names and vote.son_id not in votes:
            votes[vote.son_id] = vote
    sons = SonRepository(scope.session)
    closeness = scope.rules.council.same_vote_closeness
    cast = [vote for vote in votes.values() if vote.vote is not CouncilVote.ABSTAIN]
    for index, first in enumerate(cast):
        for second in cast[index + 1 :]:
            await sons.change_relation(first.son_id, second.son_id, closeness if first.vote is second.vote else -closeness)
    return votes


async def apply_alliances(scope: Scope, names: dict[int, str], output: CouncilOutput, notes: list[str]) -> None:
    council = scope.rules.council
    bonds = BondRepository(scope.session)
    sons = SonRepository(scope.session)
    for alliance in [item for item in output.alliances if item.a != item.b and item.a in names and item.b in names][: council.alliance_rupture_cap]:
        existing = await bonds.active_between(alliance.a, alliance.b, [BondKind.ALLY])
        if alliance.kind is AllianceChange.COVENANT and not existing:
            await bonds.connect(BondDraft(alliance.a, alliance.b, BondKind.ALLY, scope.epoch, f"Council covenant: {sanitize(alliance.reason)}"))
            await sons.change_relation(alliance.a, alliance.b, council.covenant_relation)
            notes.append(f"{names[alliance.a]} and {names[alliance.b]} made a covenant in the council")
        elif alliance.kind is AllianceChange.BREAK:
            await bonds.close_between(alliance.a, alliance.b, [BondKind.ALLY], scope.epoch, "council break")
            await sons.change_relation(alliance.a, alliance.b, -council.rupture_relation)
            notes.append(f"{names[alliance.a]} and {names[alliance.b]} broke apart in the council")


async def apply_decision(scope: Scope, members: list[SonRow], decision: CouncilDecision, notes: list[str]) -> None:
    council = scope.rules.council
    if decision is CouncilDecision.AGAINST_DOOMSDAY:
        step_doom(scope.rules, scope.cosmos, -council.apocalypse_motion_push)
        notes.append(f"the doomsday clock was pushed back {council.apocalypse_motion_push}")
    elif decision is CouncilDecision.JOINT_BLESSING:
        for son in members:
            son.existence = max(0, min(PERCENT, son.existence + council.blessing_existence))
        notes.append("every son's existence grew stronger")
    elif decision is CouncilDecision.CONDEMN_REBEL:
        for son in [member for member in members if member.rebel]:
            son.fame = max(0, son.fame - council.censure_renown_cost)
            notes.append(f"{son.name}'s fame was shaken by condemnation")
    elif decision is CouncilDecision.CALL_FOR_PEACE:
        peace = await call_for_peace(scope, {son.id for son in members}, scope.epoch)
        if peace:
            notes.append(peace)


async def apply_council(scope: Scope, members: list[SonRow], output: CouncilOutput, topic: str, *, caller: CouncilCaller, god_asked: bool) -> CouncilResult:
    names = {son.id: son.name for son in members}
    votes = await tally(scope, names, output)
    yes = sum(1 for vote in votes.values() if vote.vote is CouncilVote.YES)
    no = sum(1 for vote in votes.values() if vote.vote is CouncilVote.NO)
    passed = yes > no
    notes: list[str] = []
    await apply_alliances(scope, names, output, notes)
    if passed:
        await apply_decision(scope, members, output.decision, notes)
    minutes = CouncilMinutes(
        topic=topic,
        convened_by=caller.value,
        speeches=tuple(
            CouncilSpeech(son_id=item.son_id, name=names[item.son_id], words=sanitize(item.words)) for item in output.speeches if item.son_id in names
        ),
        motion=sanitize(output.motion),
        ballots=tuple(CouncilBallot(son_id=vote.son_id, name=names[vote.son_id], vote=vote.vote, reason=sanitize(vote.reason)) for vote in votes.values()),
        passed=passed,
        decision=output.decision.value,
        notes=tuple(notes),
        summary=sanitize(output.minutes),
    )
    row = CouncilRow(epoch=scope.epoch, topic=topic, minutes=minutes, passed=passed)
    scope.session.add(row)
    await scope.session.flush()
    subject = output.agenda.strip().rstrip(TRAILING_PUNCTUATION) if god_asked else topic
    verdict = "passed" if passed else "rejected"
    note_text = f" {'; '.join(notes)}." if notes else ""
    text = f'The Council of the Gods convened ({subject}). Motion: "{minutes.motion}" — {verdict} ({yes} yes, {no} no).{note_text} {minutes.summary}'
    await write_line(scope.session, scope.rules, scope.epoch, ChronicleKind.COUNCIL, text, key="council.held")
    return CouncilResult(row.id, topic, passed, minutes.motion, notes)


async def convene_council(runtime: AgentRuntime, topic: str | None = None, caller: CouncilCaller = CouncilCaller.FATE) -> CouncilResult:
    runtime.require_llm("council")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        members = list(await session.scalars(select(SonRow).where(SonRow.status.in_(MEMBER_STATUSES)).order_by(SonRow.id).limit(rules.council.max_members)))
        if len(members) < rules.council.min_members:
            raise ValidationFailedError(f"At least {rules.council.min_members} sons are needed for a council.")
        god_asked = bool(topic and topic.strip())
        subject = topic.strip() if topic and god_asked else await agenda(scope)
        context = await session_context(scope, members, subject, god_asked)
    runtime.step(f'The Council of the Gods is gathering: "{subject}"')
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.COUNCIL,
        system=(PromptId.COUNCIL_SESSION_SYSTEM, context),
        user=(PromptId.COUNCIL_SESSION_USER, context),
        output=CouncilOutput,
        time_limit=rules.council.timeout,
        variables={"attendance": str(len(members))},
    )
    async with runtime.database.write() as session:
        scope = await load_scope(session, rules)
        fresh = [son for son in [await session.get(SonRow, son.id) for son in members] if son is not None]
        result = await apply_council(scope, fresh, output, subject, caller=caller, god_asked=god_asked)
    runtime.publish(EventKind.COUNCIL_HELD, {"id": result.council_id, "topic": result.topic, "passed": result.passed, "motion": result.motion})
    return result
