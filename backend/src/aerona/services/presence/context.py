from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.mortal import mortal_context
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.son_turn import son_system_context, son_user_context
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_summary import world_summary
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.stats import EXISTENCE_MODES
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.repositories.presence import events_by_exchange, forgotten_before, window_exchanges
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.presence import PresenceEventRow, PresenceExchangeRow, PresenceSessionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.presence import PresenceEventKind, PresenceGuise, PresenceRecord
from aerona.engine.body.describe import body_lines
from aerona.engine.mind.describe import mind_lines
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.presence import (
    PresenceAct,
    PresenceBlock,
    PresenceClosingContext,
    PresenceRemembered,
    PresenceSystemContext,
    PresenceTraceLine,
    PresenceUserContext,
)
from aerona.prompts.contexts.son_turn import SonTurnSystemContext
from aerona.rules.registry import Rules
from aerona.services.divine_will.language import player_language
from aerona.services.presence.speakers import Speaker, death_of
from aerona.services.presence.tools import SpeakerTools
from aerona.tools.framework.runtime import ToolCatalogue

E = PresenceEventKind
GOD_KIND = "god"
UNANSWERED = "no result came back"
CALLERS: dict[PresenceGuise, str] = {
    PresenceGuise.UNNAMED_POWER: "the presence",
    PresenceGuise.DREAM_VOICE: "the voice in the dream",
    PresenceGuise.ORDINARY: "the one who speaks",
}
GUISE_NOTES: Mapping[PresenceGuise, str] = total(
    PresenceGuise,
    {
        PresenceGuise.CREATOR: "The Creator spoke with me",
        PresenceGuise.UNNAMED_POWER: "A divine presence spoke with me",
        PresenceGuise.DREAM_VOICE: "A voice spoke to me in a dream",
        PresenceGuise.ORDINARY: "Someone of my own world spoke with me",
    },
)


def caller_of(guise: PresenceGuise, creator_name: str) -> str:
    return creator_name if guise is PresenceGuise.CREATOR else CALLERS.get(guise, "")


def guise_note(guise: PresenceGuise, remember: str, limit: int) -> str:
    line = " ".join(remember.split())
    text = f"{GUISE_NOTES[guise]}: {line}" if line else GUISE_NOTES[guise]
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def labelled(label: str, value: str | None) -> list[str]:
    return [f"{label}: {value}"] if value else []


def joined(label: str, values: Sequence[str]) -> list[str]:
    return [f"{label}: {'; '.join(values)}"] if values else []


def son_lines(found: SonTurnSystemContext) -> list[str]:
    existence = found.existence
    lines = [
        f"One of the divine children of {found.god_name}",
        f"{found.rarity_label}, level {found.level}, of the domains {found.domain_1} and {found.domain_2}",
    ]
    lines += labelled("Your essential nature", existence.nature)
    lines += labelled("Your state of existence", existence.state_label)
    lines += labelled("Your manifestation", existence.manifestation)
    lines += labelled("Your true name", existence.true_name)
    lines += joined("True names you know", existence.names_known)
    lines += labelled("Appearance", found.appearance)
    lines += labelled("Temperament", found.temperament)
    lines += labelled("Obsession", found.obsession)
    lines += labelled("Fear", found.fear)
    lines += labelled("Speech style", found.speech_style)
    lines += labelled("Your secret", found.secret)
    lines.append("Stats: " + ", ".join(f"{stat.label} {stat.value}" for stat in found.stats))
    passions = found.passions
    lines.append(f"Passions (0 to 100): loyalty {passions.loyalty}, ambition {passions.ambition}, wrath {passions.wrath}, mercy {passions.mercy}")
    lines.append(f"Life {found.hp}/{found.max_hp}, essence {found.essence}/{found.max_essence}, faith {found.faith}, fame {found.fame}")
    lines += joined("Your divine body", found.wounds)
    lines += joined("Your divine mind", found.mind)
    lines.append(f"Your existence: {found.existence_value}/100 ({found.existence_band_label}: {found.existence_band_effect})")
    if found.anchor is not None:
        lines.append(f"Your anchor: {found.anchor.name} ({found.anchor.status_label})")
    lines += joined("Structures dedicated to you", [shrine.name for shrine in found.shrines])
    lines += joined("Wars you incited", found.incitements)
    lines += list(found.divine)
    lines += joined("Divine powers you wield", found.divine_powers)
    lines += joined("Whom you trust and the tension of your world", found.trust_and_tension)
    if found.clouded:
        lines.append(f"Your mind is unsound (sanity {found.sanity}): you misjudge what you perceive")
    if found.rebel:
        lines.append("In rebellion against the Creator")
    return lines


async def son_sources(scope: Scope, son: SonRow, points: int, catalogue: ToolCatalogue) -> tuple[list[str], list[PresenceBlock]]:
    system = await son_system_context(scope, son, points, catalogue)
    user = await son_user_context(scope, son, points, catalogue, resumed=False)
    blocks = [PresenceBlock(title="YOUR POWERS", text=system.powers)] if system.powers.strip() else []
    blocks.append(PresenceBlock(title="THE WORLD", text=user.world_summary))
    blocks.append(PresenceBlock(title="YOUR MEMORY", text=user.memory))
    if user.faith.strip():
        blocks.append(PresenceBlock(title="YOUR FAITHFUL", text=user.faith))
    if user.changes:
        blocks.append(PresenceBlock(title="CHANGES OF KIND UNDER WAY", text="\n".join(f"- {line}" for line in user.changes)))
    return son_lines(system), blocks


async def foreign_god_sources(scope: Scope, god: ForeignGodRow) -> tuple[list[str], list[PresenceBlock]]:
    session = scope.session
    rules = scope.rules
    lines = [f"A god of this world, not one of the divine children of {scope.creator.name}"]
    domains = [DOMAIN_LABELS[domain] for domain in (god.domain_primary, god.domain_secondary) if domain is not None]
    lines.append(f"Your domains: {' and '.join(domains)}")
    lines.append(f"Status: {spoken(god.status)}; power {god.power}/100, faith {god.faith}")
    lines.append(f"Your stance toward the children of {scope.creator.name}: {god.stance} (from -100 to 100)")
    lines += labelled("What is told of you", god.description)
    personality = god.personality
    if personality is not None:
        lines += labelled("Appearance", personality.appearance)
        lines += labelled("Temperament", personality.temperament)
        lines += labelled("Obsession", personality.obsession)
        lines += labelled("Fear", personality.fear)
        lines += labelled("Speech style", personality.speech_style)
        lines += labelled("Your secret", personality.secret)
    profile = god.existence_profile
    if profile is not None:
        lines += labelled("Your essential nature", profile.nature)
        lines += labelled("Your state of existence", EXISTENCE_MODES[profile.mode] if profile.mode is not None else None)
        lines += labelled("Your manifestation", profile.manifestation)
        lines += labelled("Your true name", profile.true_name)
    powers = await session.scalars(select(ForeignGodPowerRow).where(ForeignGodPowerRow.god_id == god.id).order_by(ForeignGodPowerRow.slot))
    lines += [f"Your power {power.name}: {power.description}" for power in powers]
    lines += joined("Your divine body", await body_lines(session, rules, god, private=True))
    lines += joined("Your divine mind", await mind_lines(session, rules, god, scope.epoch, private=True))
    header = await world_header(scope, god.world_id)
    blocks = [PresenceBlock(title="YOUR WORLD", text=header), PresenceBlock(title="THE PANTHEON AND THE WORLD", text=await world_summary(scope))]
    return lines, blocks


async def entity_sources(scope: Scope, entity: EntityRow) -> tuple[list[str], list[PresenceBlock]]:
    lines: list[str] = []
    if entity.sanity is not None and entity.sanity < scope.rules.cosmic_horror.clouding_threshold:
        lines.append(f"Your mind is unsound (sanity {entity.sanity}): you misjudge what you perceive")
    situation = render(PromptId.MORTAL_CONTEXT, await mortal_context(scope, entity))
    return lines, [PresenceBlock(title="YOU AND YOUR WORLD", text=situation)]


def kind_label(speaker: Speaker) -> str:
    entity_type = speaker.entity_type
    return ENTITY_TYPES[entity_type].label.lower() if entity_type is not None else GOD_KIND


async def world_of(scope: Scope, speaker: Speaker) -> str:
    node = speaker.node
    world_id = node.current_world_id if isinstance(node, SonRow) else node.world_id
    return scope.world_name(world_id) or scope.cosmos.name


async def system_context(session: AsyncSession, rules: Rules, speaker: Speaker, holder: PresenceSessionRow, tools: SpeakerTools) -> PresenceSystemContext:
    scope = await load_scope(session, rules)
    node = speaker.node
    catalogue = tools.toolkit.catalogue if tools.toolkit is not None else ToolCatalogue()
    if isinstance(node, SonRow):
        lines, blocks = await son_sources(scope, node, tools.points, catalogue)
    elif isinstance(node, ForeignGodRow):
        lines, blocks = await foreign_god_sources(scope, node)
    else:
        lines, blocks = await entity_sources(scope, node)
    death = await death_of(session, speaker)
    on_record = holder.record is PresenceRecord.ON_RECORD
    return PresenceSystemContext(
        lore_language=scope.cosmos.lore_language,
        rules=rules,
        speaker_name=speaker.name,
        epithet=speaker.epithet,
        kind_label=kind_label(speaker),
        world_name=await world_of(scope, speaker),
        caller=caller_of(holder.guise, scope.creator.name),
        guise=holder.guise,
        on_record=on_record,
        may_act=tools.acting,
        acting_paused=on_record and not tools.acting and tools.paused,
        acts_deferred=tools.deferred,
        action_points=tools.points,
        read_tools=sorted(tools.read_only),
        dead=death is not None,
        death_epoch=death.epoch if death is not None else None,
        death_how=death.how if death is not None else "",
        death_line=death.line if death is not None else "",
        self_lines=lines,
        blocks=[block for block in blocks if block.text.strip()],
    )


def acts_of(events: Sequence[PresenceEventRow]) -> list[PresenceAct]:
    calls: dict[str, PresenceEventRow] = {}
    acts: list[PresenceAct] = []
    for event in events:
        if event.kind is E.TOOL_CALL:
            calls[str(event.payload.get("call_id", ""))] = event
        elif event.kind is E.TOOL_RESULT:
            calls.pop(str(event.payload.get("call_id", "")), None)
            acts.append(PresenceAct(tool=event.tool, outcome=str(event.payload.get("outcome", "")), failed=bool(event.payload.get("is_error"))))
    acts.extend(PresenceAct(tool=call.tool, outcome=UNANSWERED, failed=True) for call in calls.values())
    return acts


def trace_text(event: PresenceEventRow) -> str:
    if event.kind is E.TOOL_CALL:
        return str(event.payload.get("arguments", {}))
    if event.kind is E.TOOL_RESULT:
        return str(event.payload.get("outcome", ""))
    if event.kind is E.RETRY:
        return str(event.payload.get("reason", ""))
    return str(event.payload.get("text", ""))


def trace_of(events: Sequence[PresenceEventRow]) -> list[PresenceTraceLine]:
    return [PresenceTraceLine(kind=event.kind.value, text=trace_text(event), tool=event.tool) for event in events]


async def user_context(
    session: AsyncSession, rules: Rules, holder: PresenceSessionRow, exchange: PresenceExchangeRow, creator_name: str
) -> PresenceUserContext:
    scope = await load_scope(session, rules)
    window = await window_exchanges(session, holder.id, rules.presence.remembered_exchanges, before_ordinal=exchange.ordinal)
    events = await events_by_exchange(session, [row.id for row in window] + [exchange.id])
    return PresenceUserContext(
        lore_language=scope.cosmos.lore_language,
        rules=rules,
        caller=caller_of(holder.guise, creator_name),
        player_text=exchange.player_text,
        player_language=player_language(exchange.player_text, [row.player_text for row in window]),
        forgotten=await forgotten_before(session, exchange, len(window)),
        remembered=[
            PresenceRemembered(ordinal=row.ordinal, player_text=row.player_text, reply_text=row.reply_text or row.error, acts=acts_of(events[row.id]))
            for row in window
        ],
        trace=trace_of(events[exchange.id]),
    )


def closing_context(
    rules: Rules,
    holder: PresenceSessionRow,
    exchange: PresenceExchangeRow,
    *,
    creator_name: str,
    reply: str,
    language: str,
    events: Sequence[PresenceEventRow],
) -> PresenceClosingContext:
    return PresenceClosingContext(
        rules=rules,
        caller=caller_of(holder.guise, creator_name),
        guise=holder.guise,
        player_text=exchange.player_text,
        reply_text=reply,
        player_language=language,
        acts=acts_of(events),
    )
