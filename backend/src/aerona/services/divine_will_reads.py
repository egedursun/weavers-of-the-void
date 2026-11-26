from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.rules.registry import Rules
from aerona.services.books.records import node_change_lines
from aerona.services.books.typed import TypedIndex
from aerona.services.player.catalog import ACTIONS
from aerona.services.search import find_path, neighbours
from aerona.tools.divine_will.ports import ActionCard, LinkView, PathView, SectionView

SANITY = "sanity"
DEVOTION = "devotion"


class LoreReads:
    async def typed_sections(self, session: AsyncSession, names: Mapping[int, str], node_id: int) -> list[SectionView]:
        index = await TypedIndex.load_node(session, dict(names), node_id)
        return [SectionView(section.title, tuple((fact.label, fact.value) for fact in section.facts), tuple(section.lines)) for section in index.of(node_id)]

    async def change_lines(self, session: AsyncSession, names: Mapping[int, str], node_id: int) -> list[str]:
        return await node_change_lines(session, dict(names), node_id)

    async def links(self, session: AsyncSession, node_id: int) -> list[LinkView]:
        return [LinkView(step.source, other, step.kind, step.forward, step.description) for other, step in await neighbours(session, node_id)]

    async def path(self, session: AsyncSession, first: int, second: int, depth: int) -> PathView:
        found = await find_path(session, first, second, depth)
        steps = tuple(LinkView(step.source, step.target, step.kind, step.forward, step.description) for step in found.steps)
        return PathView(found.found, tuple(found.path), dict(found.names), steps)


def stat_words() -> tuple[str, ...]:
    keys = {stat.key for spec in ENTITY_TYPES.values() for stat in spec.stats}
    return tuple(sorted(keys | {SANITY, DEVOTION}))


FIELD_WORDS: Mapping[tuple[str, str], Callable[[], tuple[str, ...]]] = {("entity:stat", "stat"): stat_words}


def accepted(action_id: str) -> dict[str, tuple[str, ...]]:
    return {name: words() for (action, name), words in FIELD_WORDS.items() if action == action_id}


class ActionDesk:
    def cards(self, rules: Rules) -> list[ActionCard]:
        return [
            ActionCard(
                id=spec.id,
                title=spec.title,
                group=spec.group.value,
                is_job=spec.job is not None,
                cost=spec.cost(rules),
                confirmation=spec.confirmation.value if spec.confirmation is not None else None,
                input_model=spec.input_model,
                accepts=accepted(spec.id),
            )
            for spec in ACTIONS
        ]


@dataclass(frozen=True)
class WillReadServices:
    lore_reads: LoreReads = field(default_factory=LoreReads)
    action_desk: ActionDesk = field(default_factory=ActionDesk)
