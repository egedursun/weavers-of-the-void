import re
from collections.abc import Sequence

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.bond_lines import bond_line_lists
from aerona.agents.context.briefs import son_brief
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.naming import naming_item
from aerona.agents.context.recent_chronicle import prompt_text, recent_chronicle
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import epoch_mentions, replace_name, sanitize, strip_meta_sentences
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.lore import SAYING_KIND_LABELS
from aerona.catalog.rarities import RARITY_LABELS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.agents import (
    EMBEDDED_SECTION_PATTERN,
    PLACEHOLDER_VALUES,
    TEMPLATE_NOTE_LINE_PATTERN,
    TEMPLATE_SHORT_LINE,
    TEMPLATE_TAG_LINE_PATTERN,
    TEMPLATE_WORD_PATTERN,
)
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.foreign_gods import ForeignGodRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.lore import ChronicleRow, FolkBeliefRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import SayingKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.profiles import EntityDepth, Epic, EpicChapter, GodDepth, GodName, Personality, Saying
from aerona.engine.cosmos.foreign_gods import clean_existence, clean_powers, unwrap_text
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.blocks import FolkBeliefLine
from aerona.prompts.contexts.common import ChronicleRow as ChronicleLine
from aerona.prompts.contexts.common import LabelValue
from aerona.prompts.contexts.narrative import (
    AgeSummary,
    CreatorDeepenContext,
    CreatorEpicContext,
    DeepenEntityContext,
    EpicSon,
    EpicWorld,
    ForeignGodDeepenContext,
    ForeignGodKnown,
    ForeignPowerLine,
    GodKnown,
    HomeWorld,
    TraceRow,
    WorshipperLine,
)
from aerona.prompts.schemas.narrative import CreatorDepthOutput, CreatorEpicOutput, DeepenOutput, ForeignGodDepthOutput, SayingOutput

EMBEDDED = re.compile(EMBEDDED_SECTION_PATTERN, re.IGNORECASE | re.MULTILINE)
LIST_MARK = re.compile(r"^\s*[-*•]\s*")
TEMPLATE_TAG_LINE = re.compile(TEMPLATE_TAG_LINE_PATTERN)
TEMPLATE_NOTE_LINE = re.compile(TEMPLATE_NOTE_LINE_PATTERN, re.IGNORECASE)
TEMPLATE_WORD = re.compile(TEMPLATE_WORD_PATTERN, re.IGNORECASE)
TRACE_KINDS = (ChronicleKind.CREATOR_HAND, ChronicleKind.DIVINE_SIGN, ChronicleKind.MIRACLE)


def template_leftover(line: str) -> bool:
    if TEMPLATE_TAG_LINE.match(line) or TEMPLATE_NOTE_LINE.match(line):
        return True
    return len(line.strip()) < TEMPLATE_SHORT_LINE and TEMPLATE_WORD.search(line) is not None


def strip_leftovers(text: str) -> str:
    lines = [line for line in text.split("\n") if not template_leftover(line)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def clean(text: str | None, old: str | None = None, new: str | None = None, protected: tuple[str, ...] = ()) -> str:
    value = strip_leftovers(sanitize(text))
    if old and new and old != new:
        value = replace_name(value, old, new, protected)
    value = strip_meta_sentences(value) or value
    return "" if value.strip().casefold() in PLACEHOLDER_VALUES else value.strip()


def clean_list(items: Sequence[str], old: str | None = None, new: str | None = None) -> tuple[str, ...]:
    return tuple(value for value in (clean(item, old, new) for item in items) if value)


def split_embedded(history: str) -> tuple[str, dict[str, list[str]]]:
    match = EMBEDDED.search(history)
    if match is None:
        return history, {}
    head, tail = history[: match.start()].strip(), history[match.start() :]
    sections: dict[str, list[str]] = {}
    current = ""
    for line in tail.split("\n"):
        heading = EMBEDDED.match(line)
        if heading:
            current = (heading.group(1) or heading.group(2) or "").casefold()
            rest = line[heading.end() :].strip()
            if rest:
                sections.setdefault(current, []).append(rest)
            continue
        text = LIST_MARK.sub("", line).strip()
        if text and current:
            sections.setdefault(current, []).append(text)
    return head, sections


def normalize_depth(output: DeepenOutput, epoch: int, old: str | None, new: str | None) -> EntityDepth:
    history, embedded = split_embedded(clean(output.history, old, new))
    rumours = clean_list(output.rumours, old, new) or clean_list(embedded.get("rumours", []) + embedded.get("rumors", []))
    details = clean_list(output.details, old, new) or clean_list(embedded.get("details", []))
    sayings = tuple(Saying(form=SAYING_KIND_LABELS[item.kind], text=text) for item in output.sayings if (text := clean(item.text, old, new))) or tuple(
        Saying(form=SAYING_KIND_LABELS[SayingKind.PROVERB], text=text) for text in clean_list(embedded.get("sayings", []))
    )
    hidden = clean(output.hidden_truth, old, new) or " ".join(clean_list(embedded.get("hidden truth", [])))
    special = {key: value for key, raw in (output.special or {}).items() if (value := clean(raw, old, new))}
    return EntityDepth(history=history, rumours=rumours, sayings=sayings, details=details, hidden_truth=hidden, specifics=special, epoch=epoch)


async def deepen_entity(runtime: AgentRuntime, entity_id: int) -> EntityDepth:
    runtime.require_llm("deepening")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        son = await session.get(SonRow, entity.creator_son_id) if entity.creator_son_id is not None else None
        outgoing, incoming = await bond_line_lists(session, entity.id)
        context = DeepenEntityContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope, entity.world_id if scope.multi_world else None),
            entity_type=entity.entity_type,
            entity_detail=await entity_detail(scope, entity),
            creator_son=son_brief(son) if son is not None else None,
            bond_lines=[f"{line.label} {line.other.name}" for line in outgoing + incoming],
            recent_events=await recent_chronicle(scope, rules.context.chronicle_default, entity.world_id),
        )
        old_name = entity.name
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.DEEPENING,
        system=(PromptId.DEEPEN_ENTITY_SYSTEM, context),
        user=(PromptId.DEEPEN_ENTITY_USER, context),
        output=DeepenOutput,
    )
    async with runtime.database.write() as session:
        entity = await session.get(EntityRow, entity_id)
        if entity is None:
            raise NotFoundError("No such record.")
        epoch = (await load_scope(session, rules)).epoch
        depth = normalize_depth(output, epoch, old_name, entity.name)
        entity.depth = depth
    runtime.publish(EventKind.ENTITY_DEEPENED, {"entity_id": entity_id, "name": entity.name})
    return depth


async def creator_traces(scope: Scope) -> list[TraceRow]:
    rows = await scope.session.scalars(
        select(ChronicleRow).where(ChronicleRow.kind.in_(TRACE_KINDS)).order_by(ChronicleRow.id.desc()).limit(scope.rules.context.memory_recollections_count)
    )
    return [TraceRow(age=row.epoch, year=row.year or 0, text=prompt_text(row.text)) for row in reversed(list(rows))]


def god_known(scope: Scope) -> GodKnown:
    creator = scope.creator
    return GodKnown(title=creator.title, appearance=creator.appearance, temperament=creator.temperament, note=creator.note)


async def creator_epic(runtime: AgentRuntime) -> Epic:
    runtime.require_llm("creator epic")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        sons = list(await session.scalars(select(SonRow).order_by(SonRow.id)))
        ages = list(await session.scalars(select(EpochRow).where(EpochRow.narrative.is_not(None)).order_by(EpochRow.epoch)))
        beliefs = await session.execute(
            select(FolkBeliefRow, EntityRow.name)
            .join(EntityRow, EntityRow.id == FolkBeliefRow.people_entity_id)
            .where(FolkBeliefRow.god_node_id == scope.creator.id)
        )
        context = CreatorEpicContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope),
            god_name=scope.creator.name,
            known=god_known(scope),
            cosmology=scope.cosmos.cosmology,
            sons=[
                EpicSon(
                    name=son.name,
                    title=son.title,
                    rarity_label=RARITY_LABELS[son.rarity],
                    domain_1=DOMAIN_LABELS[son.domain_primary],
                    domain_2=DOMAIN_LABELS[son.domain_secondary],
                    status_label=None if son.status is SonStatus.ACTIVE else son.status.value,
                    rebel=son.rebel,
                    loyalty=son.loyalty,
                )
                for son in sons
            ],
            worlds=[EpicWorld(name=world.name, type_label=WORLD_TYPES[world.world_type].label, age=world.created_epoch) for world in scope.living_worlds],
            ages=[AgeSummary(age=row.epoch, name=row.name or "", summary=row.summary or "") for row in ages],
            traces=await creator_traces(scope),
            beliefs=[FolkBeliefLine(people=people, name=belief.local_name or scope.creator.name, story=belief.account) for belief, people in beliefs],
        )

    async def write(attempt: CreatorEpicContext) -> CreatorEpicOutput:
        return await ask(
            runtime.model,
            rules,
            label=AgentRole.CREATOR_EPIC,
            system=(PromptId.CREATOR_EPIC_SYSTEM, attempt),
            user=(PromptId.CREATOR_EPIC_USER, attempt),
            output=CreatorEpicOutput,
        )

    def listed(output: CreatorEpicOutput) -> int:
        return epoch_mentions(" ".join(section.text for section in output.sections), scope.epoch)

    output = await write(context)
    for _ in range(rules.narrative.epic_retries):
        count = listed(output)
        if count <= rules.narrative.epic_epoch_mentions:
            break
        try:
            again = await write(context.model_copy(update={"listed_ages": count}))
        except Exception:
            break
        if listed(again) < count:
            output = again
    epic = Epic(
        title=clean(output.title),
        verse=clean(output.line),
        chapters=tuple(
            EpicChapter(title=clean(section.title), text=clean(section.text), epoch_start=max(0, section.age_start), epoch_end=max(0, section.age_end))
            for section in output.sections
        ),
        epoch=scope.epoch,
    )
    async with runtime.database.write() as session:
        (await load_scope(session, rules)).creator.epic = epic
    runtime.publish(EventKind.EPIC_WRITTEN, {"creator": True, "title": epic.title})
    return epic


def sayings_of(items: Sequence[SayingOutput]) -> tuple[Saying, ...]:
    return tuple(Saying(form=SAYING_KIND_LABELS[item.kind], text=text) for item in items if (text := clean(item.text)))


async def creator_deepen(runtime: AgentRuntime) -> GodDepth:
    runtime.require_llm("creator deepening")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        sons = list(await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)))
        context = CreatorDeepenContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            world_header=await world_header(scope),
            god_name=scope.creator.name,
            known=god_known(scope),
            cosmology=scope.cosmos.cosmology,
            epic_line=scope.creator.epic.verse if scope.creator.epic is not None else None,
            sons=[son_brief(son) for son in sons],
            traces=await creator_traces(scope),
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.CREATOR_DEPTH,
        system=(PromptId.CREATOR_DEEPEN_SYSTEM, context),
        user=(PromptId.CREATOR_DEEPEN_USER, context),
        output=CreatorDepthOutput,
    )
    depth = GodDepth(
        history=clean(output.history),
        names=tuple(GodName(name=item.name.strip(), used_by=clean(item.who), meaning=clean(item.meaning)) for item in output.names if item.name.strip()),
        secrets=clean_list(output.secrets),
        fears=clean_list(output.fears),
        taboos=clean_list(output.prohibitions),
        gifts=clean_list(output.gifts),
        desire=clean(output.desire),
        sayings=sayings_of(output.sayings),
        rumours=clean_list(output.rumours),
        hidden_truth=clean(output.hidden_truth),
        epoch=scope.epoch,
    )
    async with runtime.database.write() as session:
        (await load_scope(session, rules)).creator.depth = depth
    return depth


async def foreign_context(scope: Scope, god: ForeignGodRow) -> ForeignGodDeepenContext:
    world = scope.worlds.get(god.world_id)
    powers = await scope.session.scalars(select(ForeignGodPowerRow).where(ForeignGodPowerRow.god_id == god.id).order_by(ForeignGodPowerRow.slot))
    worshippers = await scope.session.scalars(
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    pattern = re.compile(rf"(?<![^\W\d_]){re.escape(god.name)}(?![^\W\d_])")
    mentions = [
        row
        for row in await scope.session.scalars(
            select(ChronicleRow).where(ChronicleRow.text.contains(god.name)).order_by(ChronicleRow.id.desc()).limit(scope.rules.context.chronicle_default)
        )
        if pattern.search(row.text)
    ]
    personality = god.personality or Personality()
    domains = DOMAIN_LABELS[god.domain_primary] + (f"/{DOMAIN_LABELS[god.domain_secondary]}" if god.domain_secondary else "")
    return ForeignGodDeepenContext(
        lore_language=scope.cosmos.lore_language,
        rules=scope.rules,
        world_name=scope.cosmos.name,
        world_header=await world_header(scope, god.world_id if scope.multi_world else None),
        name=god.name,
        home_world=HomeWorld(name=world.name, type_label=WORLD_TYPES[world.world_type].label, dialect=naming_item(world.phonology), cosmology=world.cosmology)
        if world is not None
        else None,
        known=ForeignGodKnown(
            title=god.title,
            domains=domains,
            description=god.description,
            dead=god.death_epoch is not None,
            death_age=god.death_epoch,
            status_label=god.status.value,
            power=god.power,
            attitude=god.stance,
            contact=god.contacted,
            stats=[LabelValue(label=key, value=str(getattr(god, key))) for key in ("strength", "will", "charisma", "cunning", "wisdom")],
            powers=[ForeignPowerLine(name=power.name, effect_label=power.effect.value.replace("_", " ")) for power in powers],
            personality=[LabelValue(label=key, value=value) for key, value in personality.model_dump().items() if value],
        ),
        worshippers=[WorshipperLine(name=entity.name, type_label=entity.entity_type.value, subtype=entity.subtype) for entity in worshippers],
        chronicle=[ChronicleLine(age=row.epoch, text=prompt_text(row.text)) for row in reversed(mentions)],
    )


async def deepen_foreign_god(runtime: AgentRuntime, god_id: int) -> GodDepth:
    runtime.require_llm("foreign god deepening")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        god = await session.get(ForeignGodRow, god_id)
        if god is None:
            raise NotFoundError("No such foreign god.")
        context = await foreign_context(scope, god)
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.FOREIGN_GOD_DEPTH,
        system=(PromptId.FOREIGN_GOD_DEEPEN_SYSTEM, context),
        user=(PromptId.FOREIGN_GOD_DEEPEN_USER, context),
        output=ForeignGodDepthOutput,
    )
    history = clean(unwrap_text(output.history))
    if not history:
        raise ValidationFailedError("The deepening output has an empty history; it will be retried.")
    async with runtime.database.write() as session:
        god = await session.get(ForeignGodRow, god_id)
        if god is None:
            raise NotFoundError("No such foreign god.")
        model_personality = {key: clean(unwrap_text(value)) for key, value in output.personality.model_dump().items()}
        model_personality["speech_style"] = model_personality.pop("speech", "")
        existing = (god.personality or Personality()).model_dump()
        god.personality = Personality(**{key: existing.get(key) or model_personality.get(key, "") for key in Personality.model_fields})
        if god.existence_profile is None or not god.existence_profile.nature:
            god.existence_profile = clean_existence(output.existence.model_dump() | {"mode": output.existence.state.value})
        repository = ForeignGodRepository(session)
        if not list(await session.scalars(select(ForeignGodPowerRow.god_id).where(ForeignGodPowerRow.god_id == god.id))):
            await repository.set_powers(god.id, clean_powers([power.model_dump(mode="json") for power in output.powers]))
        depth = GodDepth(
            history=history,
            names=tuple(GodName(name=item.name.strip(), used_by=clean(item.who), meaning=clean(item.meaning)) for item in output.names if item.name.strip()),
            secrets=clean_list(output.secrets),
            sayings=sayings_of(output.sayings),
            rumours=clean_list(output.rumours),
            desire=clean(output.desire),
            view_of_pantheon=clean(output.view_of_pantheon),
            worship=clean(output.worship),
            hidden_truth=clean(output.hidden_truth),
            epoch=scope.epoch,
        )
        god.depth = depth
        god.image_prompt = god.image_prompt or output.image_prompt.strip() or None
    runtime.publish(EventKind.FOREIGN_GOD_DEEPENED, {"id": god_id, "name": god.name})
    return depth


async def refresh_awakened_god(runtime: AgentRuntime, god_id: int) -> GodDepth:
    depth = await deepen_foreign_god(runtime, god_id)
    paragraph = depth.history.split("\n\n", 1)[0].strip()
    if paragraph:
        async with runtime.database.write() as session:
            god = await session.get(ForeignGodRow, god_id)
            if god is not None:
                god.description = paragraph
    return depth
