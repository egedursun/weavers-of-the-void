from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import MEMORIES, NEED_LABELS, PRESSURE_LABELS, SKILLS, TRAITS, VALUE_LABELS
from aerona.catalog.mind_split import ATTRIBUTES, FACETS, IDEAS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import IdeaState, PressureKind, ValueAxis, ValueHolder
from aerona.engine.mind.book import Holder, holder_kind, needs_of, pressures_of, skills_of, traits_of, values_of
from aerona.engine.mind.ideas import ideas_of
from aerona.engine.mind.memories import strongest
from aerona.engine.mind.space import top_values
from aerona.engine.mind.split import attributes_of, facets_of
from aerona.engine.mortal.describe import life_lines
from aerona.engine.primitives.queries import active_bonds, living_entity
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
HOME_BONDS = (BondKind.LIVES_IN, BondKind.MEMBER_OF, BondKind.PROTECTS, BondKind.DESCENDS_FROM)


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


def pressure_phrase(pressures: Mapping[PressureKind, int], count: int, floor: int) -> str:
    heaviest = sorted(((kind, value) for kind, value in pressures.items() if value >= floor), key=lambda item: (-item[1], item[0]))[:count]
    return ", ".join(f"{PRESSURE_LABELS[kind].lower()} {value}/{PERCENT}" for kind, value in heaviest)


async def mortal_home(session: AsyncSession, mortal: EntityRow) -> EntityRow | None:
    location = await living_entity(session, mortal.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    for kind in HOME_BONDS:
        for bond in await active_bonds(session, [kind], sources=[mortal.id]):
            home = await living_entity(session, bond.target_node_id)
            if home is not None and home.entity_type in COMMUNITY_TYPES:
                return home
    return None


async def borne_pressures(session: AsyncSession, rules: Rules, node: Holder) -> list[str]:
    table = rules.context
    if isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL:
        home = await mortal_home(session, node)
        phrase = pressure_phrase(await pressures_of(session, home.id), table.mind_pressures_shown, table.pressure_shown_above) if home else ""
        return [f"Your home {home.name} is pressed by: {phrase}"] if home is not None and phrase else []
    if not isinstance(node, SonRow):
        return []
    lines: list[str] = []
    for bond in await active_bonds(session, [BondKind.WORSHIPS], targets=[node.id]):
        people = await living_entity(session, bond.source_node_id)
        if people is None or people.entity_type not in COMMUNITY_TYPES:
            continue
        phrase = pressure_phrase(await pressures_of(session, people.id), table.mind_pressures_shown, table.pressure_shown_above)
        if phrase:
            lines.append(f"Your worshippers {people.name} (#{people.id}) are pressed by: {phrase}")
    return lines


async def split_lines(session: AsyncSession, rules: Rules, node: Holder) -> list[str]:
    table = rules.context
    lines: list[str] = []
    attributes = await attributes_of(session, node.id)
    if attributes and table.mind_attributes_shown:
        ranked = sorted(attributes.items(), key=lambda item: (-item[1], item[0]))
        best = ", ".join(f"{ATTRIBUTES[member].label.lower()} {value}" for member, value in ranked[: table.mind_attributes_shown])
        worst = ", ".join(f"{ATTRIBUTES[member].label.lower()} {value}" for member, value in reversed(ranked[-table.mind_attributes_shown :]))
        lines.append(f"Strongest attributes: {best}; weakest: {worst}")
    facets = await facets_of(session, node.id)
    marked = sorted(facets.items(), key=lambda item: (-abs(item[1]), item[0]))[: table.mind_facets_shown]
    if marked:
        lines.append("Most marked facets: " + ", ".join(f"{FACETS[facet].label.lower()} {value:+d}" for facet, value in marked))
    return lines


async def idea_lines(session: AsyncSession, node_id: int) -> list[str]:
    rows = await ideas_of(session, node_id)
    turning = [f"{IDEAS[row.idea].label.lower()} ({row.progress}%)" for row in rows if row.state is IdeaState.INCUBATING]
    settled = [IDEAS[row.idea].label.lower() for row in rows if row.state is IdeaState.INTERNALISED]
    lines: list[str] = []
    if turning:
        lines.append("Ideas still turning over in your mind: " + ", ".join(turning))
    if settled:
        lines.append("Ideas you have taken to heart: " + ", ".join(settled))
    return lines


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
    lines.extend(await split_lines(session, rules, node))
    if isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL:
        lines.extend(await life_lines(session, rules, node, private=private))
    if not private:
        return lines
    lines.extend(await idea_lines(session, node.id))
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
    lines.extend(await borne_pressures(session, rules, node))
    for item in await strongest(session, node.id, epoch, table.mind_memories_shown):
        name = await name_of(session, item.row.subject_node_id)
        feeling = "warmly" if item.strength > 0 else "bitterly"
        tail = f" ({item.row.note})" if item.row.note else ""
        what = MEMORIES[item.row.kind].label.lower()
        lines.append(f"You remember {feeling} and {strength_word(item.strength)}: {name}: {what}{tail}, epoch {item.row.epoch}")
    return lines
