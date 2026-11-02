from collections import Counter
from dataclasses import dataclass

from sqlalchemy import delete, func, select

from aerona.agents.ask import ask
from aerona.agents.chronicle_audit import drop_sentences, mentioned
from aerona.agents.context.chronicle_facts import unique_rejected
from aerona.agents.context.chronicler import age_events, events_by_world, living_world_items
from aerona.agents.context.entity_line import line_item
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import epoch_mentions, sanitize, sentences
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.rarities import RARITY_LABELS
from aerona.constants.agents import CREATOR_PSEUDO_SON_ID
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, FolkBeliefRow, HistorianViewRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.profiles import Epic
from aerona.engine.primitives.folk_names import clashes, folk_god_name, guarded_names
from aerona.engine.primitives.naming import Namer
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.common import ChronicleRow as ChronicleLine
from aerona.prompts.contexts.narrative import BeliefPair, EpicCreation, HistorianEntry, SonEpicContext, VoicesContext
from aerona.prompts.schemas.narrative import SonEpicOutput, VoicesOutput

PERCENT = 100
ALWAYS_BANNED = ("«…they think, whereas…»", "«In truth …»")
PATTERN_WORDS = 3
BELIEF_BONDS = (BondKind.CURSED, BondKind.BLESSED, BondKind.ENEMY, BondKind.PROTECTS)
CREATOR_DOMAIN_LABELS = ("Creation", "Everything")
MECHANICAL_KINDS = (
    ChronicleKind.RESOURCE,
    ChronicleKind.STAR,
    ChronicleKind.SYSTEM,
    ChronicleKind.CREATOR_REPUTATION,
    ChronicleKind.ENGINE_RAW,
    ChronicleKind.ASCENSION,
)


@dataclass(frozen=True)
class VoicesResult:
    views: int
    beliefs: int


def population(entity: EntityRow) -> int:
    return int(getattr(entity.stats, "population", 0) or 0)


async def historians(scope: Scope, peoples: list[EntityRow]) -> list[HistorianEntry]:
    last = dict(
        (row[0], row[1])
        for row in await scope.session.execute(
            select(HistorianViewRow.people_entity_id, func.max(HistorianViewRow.epoch)).group_by(HistorianViewRow.people_entity_id)
        )
    )
    chosen = sorted(peoples, key=lambda people: (last.get(people.id, -1), -population(people)))[: scope.rules.fate.historians_per_epoch]
    entries = []
    for people in chosen:
        world = scope.world_name(people.world_id) if scope.multi_world else ""
        previous = await scope.session.scalar(
            select(HistorianViewRow).where(HistorianViewRow.people_entity_id == people.id).order_by(HistorianViewRow.epoch.desc()).limit(1)
        )
        entries.append(
            HistorianEntry(
                people=line_item(people),
                world=world or None,
                previous_historian=previous.historian if previous else None,
                previous_age=previous.epoch if previous else None,
                previous_opening=previous.text[: scope.rules.fate.historian_opening_chars] if previous else None,
            )
        )
    return entries


async def belief_pairs(scope: Scope, peoples: list[EntityRow]) -> list[BeliefPair]:
    existing = set(await scope.session.execute(select(FolkBeliefRow.people_entity_id, FolkBeliefRow.god_node_id)))
    sons = {son.id: son for son in await scope.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD))}
    bonds = BondRepository(scope.session)
    patrons: list[BeliefPair] = []
    others: list[BeliefPair] = []
    creator_pairs: list[BeliefPair] = []
    namer = Namer(scope.session, scope.rules)
    for people in peoples:
        patron = await bonds.patron(people.id)
        linked = await scope.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == people.id, BondRow.kind.in_(BELIEF_BONDS), BondRow.state == BondState.ACTIVE)
        )
        for son_id in dict.fromkeys([*([patron] if patron is not None else []), *linked]):
            son = sons.get(son_id)
            if son is None or (people.id, son.id) in existing:
                continue
            pair = BeliefPair(
                people_id=people.id,
                people_name=people.name,
                son_id=son.id,
                son_name=son.name,
                son_title=son.title,
                domain_1=DOMAIN_LABELS[son.domain_primary],
                domain_2=DOMAIN_LABELS[son.domain_secondary],
                known_name=await folk_god_name(namer, scope.rules, people, son.id, guarded_names(son.name, son.title)),
                worshipped=son.id == patron,
            )
            (patrons if pair.worshipped else others).append(pair)
        if (people.id, scope.creator.id) not in existing and len(creator_pairs) < scope.rules.fate.creator_belief_max_people:
            creator_pairs.append(
                BeliefPair(
                    people_id=people.id,
                    people_name=people.name,
                    son_id=CREATOR_PSEUDO_SON_ID,
                    son_name=scope.creator.name,
                    son_title=scope.creator.title or "creator",
                    domain_1=CREATOR_DOMAIN_LABELS[0],
                    domain_2=CREATOR_DOMAIN_LABELS[1],
                    known_name=await folk_god_name(namer, scope.rules, people, scope.creator.id, guarded_names(scope.creator.name, scope.creator.title)),
                )
            )
    return (patrons + others + creator_pairs)[: scope.rules.fate.folk_beliefs_per_epoch]


async def piled_patterns(scope: Scope) -> list[str]:
    settings = scope.rules.folk_belief
    rows = list(await scope.session.scalars(select(FolkBeliefRow.misconception).where(FolkBeliefRow.misconception.is_not(None)).limit(settings.pattern_window)))
    openings = Counter(" ".join((text or "").split()[:PATTERN_WORDS]).casefold() for text in rows if text)
    floor = max(2, len(rows) * settings.pattern_threshold_pct / PERCENT)
    return [f"«{opening}…»" for opening, count in openings.items() if opening and count >= floor]


def without_rejected(text: str, rejected: list[str], min_letters: int) -> str:
    banned = {sentence for sentence in sentences(text) if any(mentioned(sentence, name, min_letters, distinct_first=False) for name in rejected)}
    return drop_sentences(text, banned)[0] if banned else text


def valid_belief_name(name: str, son: SonRow | None, creator: CreatorRow, limit: int) -> bool:
    cleaned = name.strip()
    if not cleaned or len(cleaned) > limit:
        return False
    guarded = guarded_names(creator.name, creator.title) if son is None else guarded_names(son.name, son.title)
    return not clashes(cleaned, guarded)


async def voices_of_peoples(runtime: AgentRuntime, epoch: int) -> VoicesResult:
    runtime.require_llm("voices of the peoples")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        peoples = sorted(
            await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)),
            key=lambda people: -population(people),
        )
        writers = await historians(scope, peoples)
        pairs = await belief_pairs(scope, peoples)
        if not writers and not pairs:
            return VoicesResult(0, 0)
        voices = {entry.people.id for entry in writers} | {pair.people_id for pair in pairs}
        seen_worlds = {people.world_id for people in peoples if people.id in voices}
        world_items = [world for world in living_world_items(scope, epoch) if world.id in seen_worlds] if scope.multi_world else []
        sections = await events_by_world(scope, epoch, world_items) if len(world_items) > 1 else []
        context = VoicesContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope),
            age=epoch,
            age_events=await age_events(scope, epoch, rules.fate.voices_events_chars),
            world_events=[section for section in sections if section.world_id is not None],
            historians=writers,
            beliefs=pairs,
        )
        banned = ", ".join([*ALWAYS_BANNED, *await piled_patterns(scope)])
        rejected = list((await unique_rejected(scope)).values())
    runtime.step(f"The peoples' historians and bards are writing their own accounts ({len(writers)} chronicles, {len(pairs)} beliefs)…")
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.VOICES,
        system=(PromptId.VOICES_SYSTEM, context),
        user=(PromptId.VOICES_USER, context),
        output=VoicesOutput,
        time_limit=rules.fate.voices_timeout,
        variables={"banned_patterns": banned},
    )
    allowed_views = {entry.people.id for entry in writers}
    allowed_pairs = {(pair.people_id, pair.son_id): pair for pair in pairs}
    views = beliefs = 0
    async with runtime.database.write() as session:
        scope = await load_scope(session, rules)
        for view in output.views:
            text = without_rejected(sanitize(view.text), rejected, rules.chronicle_audit.name_min_letters)
            if view.people_id not in allowed_views or not text:
                continue
            await session.execute(delete(HistorianViewRow).where(HistorianViewRow.epoch == epoch, HistorianViewRow.people_entity_id == view.people_id))
            session.add(HistorianViewRow(epoch=epoch, people_entity_id=view.people_id, historian=view.historian.strip() or None, text=text))
            views += 1
        for belief in output.beliefs:
            pair = allowed_pairs.get((belief.people_id, belief.son_id))
            story = sanitize(belief.story)
            if pair is None or not story:
                continue
            god_id = scope.creator.id if belief.son_id == CREATOR_PSEUDO_SON_ID else belief.son_id
            son = await session.get(SonRow, belief.son_id) if belief.son_id != CREATOR_PSEUDO_SON_ID else None
            name = pair.known_name or (
                belief.name.strip() if valid_belief_name(belief.name, son, scope.creator, rules.folk_belief.god_name_max_letters) else ""
            )
            name = name or f"Lord of {pair.domain_1}"
            row = await session.get(FolkBeliefRow, (belief.people_id, god_id))
            if row is None:
                session.add(
                    FolkBeliefRow(
                        people_entity_id=belief.people_id, god_node_id=god_id, local_name=name, account=story, misconception=belief.wrong or None, epoch=epoch
                    )
                )
            else:
                row.local_name, row.account, row.misconception, row.epoch = name, story, belief.wrong or None, epoch
            beliefs += 1
    runtime.step(f"The voices of the peoples were written: {views} partisan chronicles, {beliefs} folk beliefs.")
    return VoicesResult(views, beliefs)


async def write_son_epic(runtime: AgentRuntime, son_id: int) -> Epic:
    runtime.require_llm("son epic")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        son = await session.get(SonRow, son_id)
        if son is None:
            raise LookupError("No such son.")
        creations = list(
            await session.scalars(
                select(EntityRow).where(EntityRow.creator_son_id == son.id).order_by(EntityRow.id.desc()).limit(rules.context.memory_creations_count)
            )
        )
        records = list(
            await session.scalars(
                select(ChronicleRow)
                .where(ChronicleRow.son_id == son.id, ChronicleRow.visible.is_(True), ChronicleRow.kind.not_in(MECHANICAL_KINDS))
                .order_by(ChronicleRow.id.desc())
                .limit(rules.context.memory_recollections_count)
            )
        )
        context = SonEpicContext(
            lore_language=scope.cosmos.lore_language,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope),
            name=son.name,
            title=son.title,
            rarity_label=RARITY_LABELS[son.rarity],
            stars=son.stars,
            domain_1=DOMAIN_LABELS[son.domain_primary],
            domain_2=DOMAIN_LABELS[son.domain_secondary],
            temperament=son.personality.temperament,
            obsession=son.personality.obsession,
            secret=son.personality.secret,
            plan=son.plan,
            creations=[
                EpicCreation(
                    name=item.name, type_label=line_item(item).type_label, subtype=item.subtype, age=item.birth_epoch, status_label=line_item(item).status_label
                )
                for item in creations
            ],
            records=[ChronicleLine(age=row.epoch, text=row.text) for row in reversed(records)],
        )

    async def write(attempt: SonEpicContext) -> SonEpicOutput:
        return await ask(
            runtime.model,
            rules,
            label=AgentRole.SON_EPIC,
            system=(PromptId.SON_EPIC_SYSTEM, attempt),
            user=(PromptId.SON_EPIC_USER, attempt),
            output=SonEpicOutput,
        )

    output = await write(context)
    for _ in range(rules.narrative.epic_retries):
        listed = epoch_mentions(output.epic, scope.epoch)
        if listed <= rules.narrative.epic_epoch_mentions:
            break
        try:
            again = await write(context.model_copy(update={"listed_ages": listed}))
        except Exception:
            break
        if epoch_mentions(again.epic, scope.epoch) < listed:
            output = again
    epic = Epic(title=sanitize(output.title), verse=sanitize(output.line), body=sanitize(output.epic), epoch=scope.epoch)
    async with runtime.database.write() as session:
        son = await session.get(SonRow, son_id)
        if son is not None:
            son.epic = epic
    runtime.publish(EventKind.EPIC_WRITTEN, {"son_id": son_id, "title": epic.title})
    return epic
