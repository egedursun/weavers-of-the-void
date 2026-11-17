from collections.abc import Mapping

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.aspirations import FEARS, GOALS, INSPIRATION_LABELS, WANTS
from aerona.catalog.ethics import ACT_LABELS, HONOUR_MODELS, STANCE_LABELS, STANCE_READINGS
from aerona.catalog.mind import MEMORIES, NEED_LABELS, PRESSURE_LABELS, SKILLS, TRAITS, VALUE_LABELS
from aerona.catalog.mind_split import ATTRIBUTES, FACETS, IDEAS
from aerona.catalog.preferences import target_label
from aerona.catalog.relations import CONTESTS, PASSION_LABELS, RELATION_LABELS
from aerona.catalog.renown import AXIS_LABELS
from aerona.catalog.thoughts import DREAM_LABELS, EMOTIONS, READING_LABELS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import CultureHonourRow, DreamRow, FearRow, GriefRow, InspirationRow, LifeDreamRow, WantRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import ContestRow, GroupRankRow, PassionRow, RelationshipRow
from aerona.db.tables.renown import DeedClaimRow, ReputationRow, RulerCurrencyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import DreamReading, Emotion, EthicalStance, GriefStage, IdeaState, InspirationState, PressureKind, ValueAxis, ValueHolder
from aerona.domain.enums.relations import ContestEnd, RelationType
from aerona.domain.enums.renown import ClaimKind, ClaimStatus
from aerona.engine.mind.book import Holder, holder_kind, needs_of, pressures_of, skills_of, traits_of, values_of
from aerona.engine.mind.ethics import culture_of, ethics_of
from aerona.engine.mind.ideas import ideas_of
from aerona.engine.mind.memories import strongest
from aerona.engine.mind.preferences import rows_of
from aerona.engine.mind.space import top_values
from aerona.engine.mind.split import attributes_of, facets_of
from aerona.engine.mind.thoughts import strength_of as thought_strength
from aerona.engine.mind.thoughts import thoughts_of
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
OPEN_GRIEF = (GriefStage.SHOCK, GriefStage.MOURNING)
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


async def taste_lines(session: AsyncSession, rules: Rules, node_id: int) -> list[str]:
    table = rules.context
    lines: list[str] = []
    rows = sorted(await rows_of(session, node_id), key=lambda row: (-abs(row.strength), row.id))
    loves = [row for row in rows if row.strength >= rules.preferences.noted_above][: table.mind_preferences_shown]
    hates = [row for row in rows if row.strength <= -rules.preferences.noted_above][: table.mind_preferences_shown]
    names = await node_names(session, [row.target_node_id for row in loves + hates if row.target_node_id is not None])
    if loves or hates:
        loved = ", ".join(names.get(row.target_node_id or 0) or target_label(row.kind, row.target) for row in loves) or "nothing in particular"
        hated = ", ".join(names.get(row.target_node_id or 0) or target_label(row.kind, row.target) for row in hates) or "nothing in particular"
        lines.append(f"Loves: {loved}; dislikes: {hated}")
    culture = await culture_of(session, node_id)
    if culture is None:
        return lines
    ethics = sorted((await ethics_of(session, culture.id)).values(), key=lambda row: (-abs(STANCE_READINGS[row.stance]), row.act.value))
    marked = [row for row in ethics if row.stance is not EthicalStance.ACCEPTABLE][: table.mind_ethics_shown]
    if marked:
        lines.append("Held right and wrong: " + "; ".join(f"{ACT_LABELS[row.act].lower()} is {STANCE_LABELS[row.stance].lower()}" for row in marked))
    honour = await session.get(CultureHonourRow, culture.id)
    if honour is not None:
        lines.append(f"Honour model: {HONOUR_MODELS[honour.model].label}")
    return lines


async def node_names(session: AsyncSession, node_ids: list[int]) -> dict[int, str]:
    return {node_id: await name_of(session, node_id) for node_id in node_ids}


async def aspiration_lines(session: AsyncSession, node_id: int) -> list[str]:
    lines: list[str] = []
    dream = await session.get(LifeDreamRow, node_id)
    if dream is not None:
        about = f" ({await name_of(session, dream.target_node_id)})" if dream.target_node_id is not None else ""
        lines.append(f"Life's dream: {GOALS[dream.goal].label.lower()}{about}, {spoken(dream.state)}, {dream.progress}% of the way")
    wants = list(await session.scalars(select(WantRow).where(WantRow.holder_node_id == node_id, WantRow.fulfilled_epoch.is_(None))))
    if wants:
        lines.append("What you want now: " + ", ".join(WANTS[row.kind].label.lower() for row in wants))
    fears = list(await session.scalars(select(FearRow).where(FearRow.holder_node_id == node_id)))
    if fears:
        lines.append("What you fear: " + ", ".join(f"{FEARS[row.kind].label.lower()} ({row.strength})" for row in fears))
    profile = await session.get(MortalProfileRow, node_id)
    if profile is not None:
        focus = f"; your focus is {spoken(profile.focus)}" if profile.focus is not None else ""
        lines.append(f"Conviction {profile.conviction}/{PERCENT}{focus}")
    spark = await session.scalar(
        select(InspirationRow).where(InspirationRow.holder_node_id == node_id, InspirationRow.state == InspirationState.BURNING).limit(1)
    )
    if spark is not None:
        lines.append(f"Seized by {INSPIRATION_LABELS[spark.kind].lower()} until epoch {spark.deadline_epoch}")
    return lines


async def bond_lines(session: AsyncSession, rules: Rules, node_id: int) -> list[str]:
    table = rules.context
    lines: list[str] = []
    rows = [row for row in await session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id == node_id)) if row.kinds]
    rows.sort(key=lambda row: (-(abs(row.friendship) + row.romance + row.rivalry), row.id))
    shown = []
    for row in rows[: table.mind_bonds_shown]:
        kinds = ", ".join(RELATION_LABELS[RelationType(kind)].lower() for kind in row.kinds)
        hidden = "; a secret love" if row.affair and not row.affair_known else ""
        shown.append(f"{await name_of(session, row.subject_node_id)} ({kinds}{hidden})")
    if shown:
        lines.append("Your bonds: " + "; ".join(shown))
    passions = list(await session.scalars(select(PassionRow).where(PassionRow.holder_node_id == node_id).order_by(PassionRow.strength.desc(), PassionRow.id)))
    if passions:
        told = [
            f"{PASSION_LABELS[row.kind].lower()} for {await name_of(session, row.object_node_id)} ({row.strength})"
            for row in passions[: table.mind_passions_shown]
        ]
        lines.append("Passions that move you: " + ", ".join(told))
    ranks = list(await session.scalars(select(GroupRankRow).where(GroupRankRow.member_node_id == node_id).order_by(GroupRankRow.group_node_id)))
    if ranks:
        lines.append("Your standing: " + ", ".join([f"rank {row.rank} in {await name_of(session, row.group_node_id)}" for row in ranks]))
    contest = await session.scalar(
        select(ContestRow)
        .where(or_(ContestRow.challenger_node_id == node_id, ContestRow.defender_node_id == node_id))
        .order_by(ContestRow.epoch.desc(), ContestRow.id.desc())
        .limit(1)
    )
    if contest is not None:
        won = (contest.outcome is ContestEnd.CHALLENGER) == (contest.challenger_node_id == node_id) and contest.outcome is not ContestEnd.DRAWN
        other = contest.defender_node_id if contest.challenger_node_id == node_id else contest.challenger_node_id
        result = "drew" if contest.outcome is ContestEnd.DRAWN else "won" if won else "lost"
        lines.append(f"Last contest of wit: {CONTESTS[contest.kind].label.lower()} with {await name_of(session, other)}, which you {result}")
    return lines


async def renown_lines(session: AsyncSession, rules: Rules, node_id: int) -> list[str]:
    lines: list[str] = []
    rows = list(
        await session.scalars(select(ReputationRow).where(ReputationRow.subject_node_id == node_id).order_by(ReputationRow.value.desc(), ReputationRow.id))
    )
    told = [f"{AXIS_LABELS[row.axis].lower()} {row.value} in {await name_of(session, row.community_node_id)}" for row in rows[: rules.context.renown_shown]]
    if told:
        lines.append("Known for: " + "; ".join(told))
    purse = await session.get(RulerCurrencyRow, node_id)
    if purse is not None:
        lines.append(f"As a ruler: prestige {purse.prestige}, piety {purse.piety}, dread {purse.dread}, tyranny {purse.tyranny}")
    false = await session.scalar(
        select(DeedClaimRow)
        .where(DeedClaimRow.claimant_node_id == node_id, DeedClaimRow.kind == ClaimKind.FALSE, DeedClaimRow.status == ClaimStatus.STANDING)
        .limit(1)
    )
    if false is not None:
        lines.append("Believed to have done a deed that was another's")
    return lines


async def feeling_lines(session: AsyncSession, rules: Rules, node_id: int, epoch: int) -> list[str]:
    lines: list[str] = []
    profile = await session.get(MortalProfileRow, node_id)
    if profile is not None:
        lines.append(f"Mood: {spoken(profile.mood)} ({profile.mood_score:+d})")
    totals: dict[Emotion, float] = {}
    for row in await thoughts_of(session, node_id):
        totals[row.emotion] = totals.get(row.emotion, 0.0) + thought_strength(row, epoch)
    strongest = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[: rules.context.mind_feelings_shown]
    if strongest:
        lines.append("Strongest feelings: " + ", ".join(f"{EMOTIONS[emotion].label.lower()} {round(total)}" for emotion, total in strongest))
    griefs = list(await session.scalars(select(GriefRow).where(GriefRow.mourner_node_id == node_id, GriefRow.stage.in_(OPEN_GRIEF))))
    for grief in griefs:
        lines.append(f"Grieving {await name_of(session, grief.deceased_node_id)}: {spoken(grief.stage)}")
    dream = await session.scalar(select(DreamRow).where(DreamRow.dreamer_node_id == node_id).order_by(DreamRow.epoch.desc(), DreamRow.id.desc()).limit(1))
    if dream is not None:
        reading = f", read as {READING_LABELS[dream.reading].lower()}" if dream.reading is not DreamReading.UNREAD else ""
        lines.append(f"Your last dream: {DREAM_LABELS[dream.kind].lower()} in epoch {dream.epoch}{reading}")
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
    lines.extend(await taste_lines(session, rules, node.id))
    if isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL:
        lines.extend(await life_lines(session, rules, node, private=private))
    if not private:
        return lines
    lines.extend(await idea_lines(session, node.id))
    lines.extend(await feeling_lines(session, rules, node.id, epoch))
    lines.extend(await aspiration_lines(session, node.id))
    lines.extend(await bond_lines(session, rules, node.id))
    lines.extend(await renown_lines(session, rules, node.id))
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
