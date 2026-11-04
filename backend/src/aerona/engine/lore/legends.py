from sqlalchemy import select

from aerona.catalog.lore import DISTORTED, LEGEND_MORALS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.entity import EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity

A = LegendArchetype
CATEGORY_ARCHETYPES = {
    LegendCategory.CREATURE: A.MONSTER,
    LegendCategory.SPIRIT: A.HAUNTED_PLACE,
    LegendCategory.RESOURCE: A.LOST_PARADISE,
    LegendCategory.RELIC: A.HERO_QUEST,
}
WORD_ARCHETYPES = (
    (("flood", "deluge"), A.FLOOD),
    (("king", "return", "throne"), A.RETURN_OF_THE_KING),
    (("betray", "traitor"), A.BETRAYAL),
    (("curse", "doom"), A.CURSED_LINE),
    (("ghost", "haunt", "shade"), A.HAUNTED_PLACE),
    (("chosen", "prophet"), A.CHOSEN_ONE),
    (("trick", "fox", "thief"), A.TRICKSTER),
    (("beginning", "creation", "first"), A.CREATION),
    (("paradise", "golden", "lost"), A.LOST_PARADISE),
    (("beast", "dragon", "monster", "serpent"), A.MONSTER),
)
TELLERS = (BondKind.CELEBRATES, BondKind.TELLS_OF)


async def subject_of(ctx: TickContext, legend_id: int) -> EntityRow | None:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == legend_id, BondRow.kind == BondKind.TELLS_OF, BondRow.state == BondState.ACTIVE)
    target = await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))
    return await ctx.session.get(EntityRow, target) if target is not None else None


def archetype_of(legend: EntityRow, subject: EntityRow | None) -> LegendArchetype:
    text = f"{legend.name} {legend.subtype or ''}".lower()
    for words, archetype in WORD_ARCHETYPES:
        if any(word in text for word in words):
            return archetype
    if legend.legend_category is not None:
        return CATEGORY_ARCHETYPES.get(legend.legend_category, A.HERO_QUEST)
    if subject is not None and subject.entity_type is EntityType.MORTAL:
        return A.HERO_QUEST
    if subject is not None and subject.entity_type is EntityType.EVENT:
        return A.BETRAYAL if "war" in subject.name.lower() else A.FLOOD
    return A.CREATION


async def tellers_of(ctx: TickContext, legend_id: int) -> list[int]:
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == legend_id, BondRow.kind.in_(TELLERS), BondRow.state == BondState.ACTIVE)
    found = []
    for teller in await ctx.session.scalars(statement):
        if await living_entity(ctx.session, teller) is not None:
            found.append(teller)
    return sorted(set(found))


async def profile_of(ctx: TickContext, legend: EntityRow) -> LegendProfileRow:
    row = await ctx.session.get(LegendProfileRow, legend.id)
    if row is not None:
        return row
    subject = await subject_of(ctx, legend.id)
    archetype = archetype_of(legend, subject)
    row = LegendProfileRow(
        legend_entity_id=legend.id,
        archetype=archetype,
        credence=clamp_int(30 + (legend.power_level * 5), 0, PERCENT),
        distortion=0,
        subject_node_id=subject.id if subject is not None else None,
        moral={axis.value: value for axis, value in LEGEND_MORALS[archetype].items()},
        tellers=await tellers_of(ctx, legend.id),
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def literate(ctx: TickContext, teller: int) -> float:
    culture = await ctx.session.get(PeopleCultureRow, teller)
    return (culture.literacy if culture is not None else 0) / PERCENT


async def tell(ctx: TickContext, legend: EntityRow, row: LegendProfileRow) -> bool:
    table = ctx.rules.belief
    row.tellers = await tellers_of(ctx, legend.id)
    if row.fixed_in_entity_id is None and "distortion" not in row.locked and row.tellers:
        letters = sum([await literate(ctx, teller) for teller in row.tellers]) / len(row.tellers)
        row.distortion = clamp_int(row.distortion + round_half_up(table.distortion_rate * (1 - letters)), 0, PERCENT)
    if "credence" not in row.locked:
        row.credence = clamp_int(row.credence + len(row.tellers) * table.credence_per_teller - table.credence_decay, 0, PERCENT)
    drifted = False
    if row.tellers and "archetype" not in row.locked and row.distortion >= PERCENT // 2:
        values = await values_for(ctx.session, row.tellers[0])
        if values:
            axis = max(values, key=lambda key: values[key])
            target = DISTORTED.get(axis)
            if target is not None and target is not row.archetype:
                row.archetype = target
                row.moral = {key.value: value for key, value in LEGEND_MORALS[target].items()}
                drifted = True
    row.updated_epoch = ctx.epoch
    return drifted


async def press_morals(ctx: TickContext, row: LegendProfileRow) -> int:
    weight = row.credence / PERCENT * ctx.rules.belief.moral_pressure_pct / PERCENT
    pressed = 0
    for teller in row.tellers:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, teller)
        if not values:
            continue
        for key, value in row.moral.items():
            step = round_half_up(value * weight)
            if step:
                values[ValueAxis(key)] = values.get(ValueAxis(key), 0) + step
        await write_values(ctx.session, ValueHolder.CULTURE, teller, values)
        pressed += 1
    return pressed


async def consequences(ctx: TickContext, row: LegendProfileRow) -> str | None:
    table = ctx.rules.belief
    subject = await ctx.session.get(EntityRow, row.subject_node_id) if row.subject_node_id is not None else None
    if row.archetype is A.RETURN_OF_THE_KING:
        claims = list(await ctx.session.scalars(select(ClaimRow).where(ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.strength.desc()).limit(1)))
        for claim in claims:
            claim.strength = clamp_int(claim.strength + round_half_up(table.return_king_claim * row.credence / PERCENT), 0, PERCENT)
            return "a pretender's claim grows"
    if row.archetype is A.CURSED_LINE and subject is not None:
        house_id = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == subject.id).limit(1))
        house = await ctx.session.get(HouseProfileRow, house_id) if house_id is not None else None
        if house is not None:
            house.prestige = clamp_int(house.prestige - round_half_up(table.cursed_line_prestige * row.credence / PERCENT), 0, PERCENT)
            return "a house is shunned as cursed"
    return None


async def haunted_regions(ctx: TickContext) -> set[int]:
    rows = await ctx.session.scalars(
        select(LegendProfileRow).where(LegendProfileRow.archetype == A.HAUNTED_PLACE, LegendProfileRow.credence >= ctx.rules.belief.haunted_avoidance)
    )
    found: set[int] = set()
    for row in rows:
        legend = await ctx.session.get(EntityRow, row.legend_entity_id)
        if legend is not None and legend.status is EntityStatus.CANON and legend.location_id is not None:
            found.add(legend.location_id)
    return found


async def believed(ctx: TickContext, legend: EntityRow) -> bool:
    row = await profile_of(ctx, legend)
    return row.credence >= ctx.rules.belief.manifestation_credence


async def resonance(ctx: TickContext, archetypes: frozenset[LegendArchetype]) -> int:
    found = await ctx.session.scalar(
        select(LegendProfileRow.legend_entity_id).where(LegendProfileRow.archetype.in_(list(archetypes)), LegendProfileRow.credence >= PERCENT // 2).limit(1)
    )
    return ctx.rules.belief.resonance_certainty if found is not None else 0


ARCHETYPE_MEMORIES: dict[LegendArchetype, tuple[MemoryKind, int]] = {
    LegendArchetype.BETRAYAL: (MemoryKind.BETRAYED_ME, -1),
    LegendArchetype.MONSTER: (MemoryKind.HARMED_ME, -1),
    LegendArchetype.CURSED_LINE: (MemoryKind.ILL_WILL, -1),
    LegendArchetype.TRICKSTER: (MemoryKind.CHEATED_US, -1),
    LegendArchetype.HERO_QUEST: (MemoryKind.SAVED_ME, 1),
    LegendArchetype.CHOSEN_ONE: (MemoryKind.GOODWILL, 1),
    LegendArchetype.RETURN_OF_THE_KING: (MemoryKind.GOODWILL, 1),
}
LEGEND_NOTE = "as the legend tells it"


async def remember_legend(ctx: TickContext, legend: EntityRow, row: LegendProfileRow) -> int:
    table = ctx.rules.belief
    subject = row.subject_node_id
    if subject is None or not row.tellers:
        return 0
    changed = 0
    swell = 1 + row.distortion / PERCENT * table.memory_distortion_pct / PERCENT
    planted = ARCHETYPE_MEMORIES.get(row.archetype)
    for teller in row.tellers:
        if teller == subject:
            continue
        held = list(await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == teller, MemoryRow.subject_node_id == subject)))
        for memory in held:
            if memory.event_entity_id == legend.id or memory.note == LEGEND_NOTE:
                continue
            memory.magnitude = clamp_int(memory.magnitude * swell, RELATION_MIN, RELATION_MAX)
            memory.note = LEGEND_NOTE
            memory.event_entity_id = legend.id
            changed += 1
        if planted is None or row.credence < table.false_memory_credence or row.distortion < table.false_memory_distortion:
            continue
        kind, sign = planted
        if any(memory.kind is kind for memory in held):
            continue
        if not ctx.rng(f"false_memory.{legend.id}.{teller}.{ctx.epoch}").chance(table.false_memory_chance):
            continue
        made = await remember(
            ctx.session,
            ctx.rules,
            holder_id=teller,
            subject_id=subject,
            kind=kind,
            magnitude=sign * table.false_memory_magnitude,
            epoch=ctx.epoch,
            note=LEGEND_NOTE,
        )
        if made is not None:
            made.event_entity_id = legend.id
            changed += 1
    return changed
