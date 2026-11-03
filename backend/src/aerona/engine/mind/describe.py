from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import MEMORIES, NEED_LABELS, PRESSURE_LABELS, SKILLS, TRAITS, VALUE_LABELS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.mind.book import Holder, holder_kind, needs_of, pressures_of, skills_of, traits_of, values_of
from aerona.engine.mind.memories import strongest
from aerona.engine.mind.space import top_values
from aerona.rules.registry import Rules

HOLDER_WORDS = {
    ValueHolder.CULTURE: "Culture",
    ValueHolder.DOCTRINE: "Doctrine",
    ValueHolder.AGENDA: "Agenda",
    ValueHolder.PERSONAL: "Values",
    ValueHolder.DIVINE: "Divine values",
    ValueHolder.COMMUNITY: "Culture",
}
STRONG = 60
FAINT = 25


def strength_word(strength: float) -> str:
    size = abs(strength)
    return "strongly" if size >= STRONG else "faintly" if size < FAINT else "clearly"


def value_phrase(values: Mapping[ValueAxis, int], count: int) -> str:
    parts = []
    for axis, value in top_values(values, count):
        low, high = VALUE_LABELS[axis]
        parts.append(f"{(high if value > 0 else low).lower()} ({value:+d})")
    return ", ".join(parts)


async def name_of(session: AsyncSession, node_id: int) -> str:
    for table in (EntityRow, SonRow, ForeignGodRow):
        found = await session.get(table, node_id)
        if found is not None:
            return str(found.name)
    return f"#{node_id}"


async def mind_lines(session: AsyncSession, rules: Rules, node: Holder, epoch: int, *, private: bool = False) -> list[str]:
    kind = holder_kind(node)
    if kind is None:
        return []
    table = rules.context
    lines: list[str] = []
    traits = sorted(await traits_of(session, node.id))
    if traits:
        lines.append("Temperament: " + ", ".join(TRAITS[trait].label.lower() for trait in traits))
    values = await values_of(session, node)
    if values:
        lines.append(f"{HOLDER_WORDS[kind]} prizes most: {value_phrase(values, table.mind_values_shown)}")
    if not private:
        return lines
    skills = sorted((await skills_of(session, node.id)).values(), key=lambda row: (-row.level, row.skill))[: table.mind_skills_shown]
    if skills:
        lines.append("Best skills: " + ", ".join(f"{SKILLS[row.skill].label.lower()} {row.level}" for row in skills))
    needs = await needs_of(session, node.id)
    pressing = sorted(needs.items(), key=lambda item: (item[1], item[0]))[: table.mind_pressures_shown]
    if pressing:
        lines.append("Most pressing needs: " + ", ".join(f"{NEED_LABELS[need].lower()} met {value}/{PERCENT}" for need, value in pressing))
    pressures = await pressures_of(session, node.id)
    heaviest = sorted(pressures.items(), key=lambda item: (-item[1], item[0]))[: table.mind_pressures_shown]
    if heaviest:
        lines.append("Pressures on you: " + ", ".join(f"{PRESSURE_LABELS[kind_].lower()} {value}/{PERCENT}" for kind_, value in heaviest))
    for item in await strongest(session, node.id, epoch, table.mind_memories_shown):
        name = await name_of(session, item.row.subject_node_id)
        feeling = "warmly" if item.strength > 0 else "bitterly"
        tail = f" ({item.row.note})" if item.row.note else ""
        what = MEMORIES[item.row.kind].label.lower()
        lines.append(f"You remember {feeling} and {strength_word(item.strength)}: {name}: {what}{tail}, epoch {item.row.epoch}")
    return lines
