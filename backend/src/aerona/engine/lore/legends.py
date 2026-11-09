from sqlalchemy import func, select

from aerona.catalog.lore import DISTORTED, LEGEND_MORALS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow, LegendProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import MemoryRow, SkillRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CustomCatalog, LegendArchetype
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import MemoryKind, SkillKind, ValueAxis, ValueHolder
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.context import TickContext
from aerona.engine.lore.kinds import ArchetypeParams, kind_of, params_of
from aerona.engine.lore.language import standardisation_of
from aerona.engine.mind.book import stored_values, values_for, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity, spoken_language
from aerona.engine.primitives.stats import stat

A = LegendArchetype
CATEGORY_ARCHETYPES = {
    LegendCategory.CREATURE: A.MONSTER,
    LegendCategory.SPIRIT: A.HAUNTED_PLACE,
    LegendCategory.RESOURCE: A.LOST_PARADISE,
    LegendCategory.RELIC: A.HERO_QUEST,
}
EVENT_ARCHETYPES = {
    EngineKind.FLOOD: A.FLOOD,
    EngineKind.STORM: A.FLOOD,
    EngineKind.WAR: A.BETRAYAL,
    EngineKind.UPRISING: A.RETURN_OF_THE_KING,
    EngineKind.BATTLE: A.HERO_QUEST,
    EngineKind.SIEGE: A.BETRAYAL,
    EngineKind.PLAGUE: A.CURSED_LINE,
    EngineKind.FAMINE: A.LOST_PARADISE,
    EngineKind.DROUGHT: A.LOST_PARADISE,
    EngineKind.EARTHQUAKE: A.CREATION,
    EngineKind.MAGIC_STORM: A.HAUNTED_PLACE,
    EngineKind.ECLIPSE_PROPHECY: A.CHOSEN_ONE,
}
CONFIRMING = {archetype: frozenset(kind for kind, found in EVENT_ARCHETYPES.items() if found is archetype) for archetype in set(EVENT_ARCHETYPES.values())}
TELLERS = (BondKind.CELEBRATES, BondKind.TELLS_OF)
FORETOLD = "the king of legend returned"
BARD_SKILLS = (SkillKind.ORATORY, SkillKind.LORE)


async def subject_of(ctx: TickContext, legend_id: int) -> EntityRow | None:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == legend_id, BondRow.kind == BondKind.TELLS_OF, BondRow.state == BondState.ACTIVE)
    target = await ctx.session.scalar(statement.order_by(BondRow.id).limit(1))
    return await ctx.session.get(EntityRow, target) if target is not None else None


def archetype_of(legend: EntityRow, subject: EntityRow | None) -> LegendArchetype:
    if legend.legend_category is not None:
        return CATEGORY_ARCHETYPES.get(legend.legend_category, A.HERO_QUEST)
    if subject is not None and subject.entity_type is EntityType.EVENT and subject.engine_kind is not None:
        return EVENT_ARCHETYPES.get(subject.engine_kind, A.HERO_QUEST)
    if subject is not None and subject.entity_type in {EntityType.MORTAL, EntityType.HOUSE}:
        return A.HERO_QUEST
    if subject is not None and subject.entity_type in {EntityType.PLACE, EntityType.REGION}:
        return A.HAUNTED_PLACE
    return A.CREATION


def credence_from(ctx: TickContext, legend: EntityRow) -> int:
    table = ctx.rules.belief
    spread = stat(legend, "spread") or 0
    category = table.category_credence if legend.legend_category is not None else 0
    return clamp_int(table.credence_base + round_half_up(spread * table.spread_credence_pct / PERCENT) + category, 0, PERCENT)


async def source_of(ctx: TickContext, subject: EntityRow | None) -> int | None:
    if subject is None or subject.entity_type is not EntityType.EVENT:
        return None
    statement = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == subject.id).order_by(IncidentParticipantRow.incident_id)
    return await ctx.session.scalar(statement.limit(1))


async def bards_of(ctx: TickContext, communities: list[int]) -> list[int]:
    if not communities:
        return []
    mortals = select(EntityRow.id).where(
        await present_among(ctx.session, communities), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    rows = await ctx.session.scalars(
        select(SkillRow.holder_node_id)
        .where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill.in_(list(BARD_SKILLS)), SkillRow.level >= ctx.rules.belief.bard_skill)
        .order_by(SkillRow.level.desc(), SkillRow.holder_node_id)
    )
    return list(dict.fromkeys(rows))[: ctx.rules.belief.bards_per_legend]


async def tellers_of(ctx: TickContext, legend_id: int) -> list[int]:
    statement = select(BondRow.source_node_id).where(BondRow.target_node_id == legend_id, BondRow.kind.in_(TELLERS), BondRow.state == BondState.ACTIVE)
    found = []
    for teller in await ctx.session.scalars(statement):
        if await living_entity(ctx.session, teller) is not None:
            found.append(teller)
    communities = sorted(set(found))
    return sorted(set(communities) | set(await bards_of(ctx, communities)))


async def profile_of(ctx: TickContext, legend: EntityRow, archetype: LegendArchetype | None = None) -> LegendProfileRow:
    row = await ctx.session.get(LegendProfileRow, legend.id)
    if row is not None:
        return row
    subject = await subject_of(ctx, legend.id)
    chosen = archetype or archetype_of(legend, subject)
    row = LegendProfileRow(
        legend_entity_id=legend.id,
        archetype=chosen,
        credence=credence_from(ctx, legend),
        distortion=0,
        source_incident_id=await source_of(ctx, subject),
        subject_node_id=subject.id if subject is not None else None,
        moral={axis.value: value for axis, value in LEGEND_MORALS[chosen].items()},
        tellers=await tellers_of(ctx, legend.id),
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def literate(ctx: TickContext, teller: int) -> float:
    culture = await ctx.session.get(PeopleCultureRow, teller)
    return (culture.literacy if culture is not None else 0) / PERCENT


async def standard(ctx: TickContext, teller: int) -> float:
    language = await spoken_language(ctx.session, teller)
    return await standardisation_of(ctx.session, language.id if language is not None else None) / PERCENT


async def resolve_kind(ctx: TickContext, row: LegendProfileRow) -> None:
    custom = await kind_of(ctx.session, row.custom_archetype_id, CustomCatalog.ARCHETYPE)
    if custom is None:
        return
    if "archetype" not in row.locked:
        row.archetype = LegendArchetype(custom.base)
    moral = params_of(custom, ArchetypeParams).moral
    if "moral" not in row.locked:
        row.moral = {ValueAxis(key).value: value for key, value in moral.items()} or {axis.value: value for axis, value in LEGEND_MORALS[row.archetype].items()}


async def fix(ctx: TickContext, row: LegendProfileRow) -> int | None:
    if "fixed_in_entity_id" in row.locked:
        return row.fixed_in_entity_id
    current = await living_entity(ctx.session, row.fixed_in_entity_id)
    if current is not None:
        return current.id
    works = await ctx.session.scalars(
        select(ArtworkProfileRow.artwork_entity_id)
        .where(ArtworkProfileRow.subject_node_id == row.legend_entity_id)
        .order_by(ArtworkProfileRow.artwork_entity_id)
    )
    for work_id in works:
        if await living_entity(ctx.session, work_id) is not None:
            row.fixed_in_entity_id = work_id
            return work_id
    row.fixed_in_entity_id = None
    return None


async def drift_step(ctx: TickContext, row: LegendProfileRow, communities: list[int]) -> int:
    table = ctx.rules.belief
    letters = sum([await literate(ctx, teller) for teller in communities]) / len(communities)
    written = sum([await standard(ctx, teller) for teller in communities]) / len(communities)
    rate = table.distortion_rate * (1 - letters) * (1 - written * ctx.rules.prestige.standard_distortion_pct / PERCENT)
    rate *= sum([await ctx.hook_easing(teller, DomainHook.MEMORY_KEEPING) for teller in communities]) / len(communities)
    incident = await ctx.session.get(IncidentRow, row.source_incident_id) if row.source_incident_id is not None else None
    if incident is None:
        return clamp_int(row.distortion + round_half_up(rate), 0, PERCENT)
    measured = round_half_up(max(0, ctx.epoch - incident.epoch) * rate)
    return clamp_int(max(row.distortion, measured), 0, PERCENT)


async def tell(ctx: TickContext, legend: EntityRow, row: LegendProfileRow) -> bool:
    table = ctx.rules.belief
    await resolve_kind(ctx, row)
    if "tellers" not in row.locked:
        row.tellers = await tellers_of(ctx, legend.id)
    communities = [teller for teller in row.tellers if (await ctx.session.get(EntityRow, teller)) is not None and not await is_mortal(ctx, teller)]
    bards = len(row.tellers) - len(communities)
    if communities and (await ctx.laws()).has(NaturalLaw.THE_DEAD_SPEAK, legend.world_id):
        spirits = await ctx.session.scalar(
            select(func.count(EntityRow.id)).where(
                EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(communities)
            )
        )
        bards += int(spirits or 0)
    if await fix(ctx, row) is None and "distortion" not in row.locked and communities:
        row.distortion = await drift_step(ctx, row, communities)
    if "credence" not in row.locked:
        voices = sum([await ctx.hook_factor(teller, DomainHook.LEGEND_SPREAD) for teller in communities])
        gain = round_half_up(voices * table.credence_per_teller) + bards * table.credence_per_bard
        row.credence = clamp_int(row.credence + gain - table.credence_decay, 0, PERCENT)
    drifted = False
    if communities and "archetype" not in row.locked and row.custom_archetype_id is None and row.distortion >= PERCENT // 2:
        values = await values_for(ctx.session, communities[0])
        if values:
            axis = max(values, key=lambda key: values[key])
            target = DISTORTED.get(axis)
            if target is not None and target is not row.archetype:
                row.archetype = target
                if "moral" not in row.locked:
                    row.moral = {key.value: value for key, value in LEGEND_MORALS[target].items()}
                drifted = True
    row.updated_epoch = ctx.epoch
    return drifted


async def is_mortal(ctx: TickContext, entity_id: int) -> bool:
    entity = await ctx.session.get(EntityRow, entity_id)
    return entity is not None and entity.entity_type is EntityType.MORTAL


async def confirmed(ctx: TickContext, legend: EntityRow, row: LegendProfileRow) -> bool:
    kinds = CONFIRMING.get(row.archetype, frozenset())
    if not kinds or legend.location_id is None:
        return False
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.EVENT,
            EntityRow.birth_epoch == ctx.epoch,
            EntityRow.location_id == legend.location_id,
            EntityRow.engine_kind.in_(list(kinds)),
        )
        .limit(1)
    )
    return found is not None


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


async def houses_of(ctx: TickContext, subject: EntityRow | None) -> set[int]:
    if subject is None:
        return set()
    if subject.entity_type is EntityType.HOUSE:
        return {subject.id}
    return set(await ctx.session.scalars(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == subject.id)))


async def returning_king(ctx: TickContext, row: LegendProfileRow, subject: EntityRow | None) -> str | None:
    table = ctx.rules.belief
    houses = await houses_of(ctx, subject)
    if subject is None:
        return None
    matching = select(ClaimRow).where(ClaimRow.ended_epoch.is_(None))
    matching = matching.where((ClaimRow.claimant_entity_id == subject.id) | (ClaimRow.house_entity_id.in_(list(houses))))
    claims = list(await ctx.session.scalars(matching.order_by(ClaimRow.strength.desc(), ClaimRow.id)))
    for claim in claims:
        claim.strength = clamp_int(claim.strength + round_half_up(table.return_king_claim * row.credence / PERCENT), 0, PERCENT)
    return "a pretender of the foretold line gains strength" if claims else None


async def foretold_return(ctx: TickContext, ruler: EntityRow) -> dict[str, int]:
    houses = await houses_of(ctx, ruler)
    best = 0
    rows = await ctx.session.scalars(select(LegendProfileRow).where(LegendProfileRow.archetype == A.RETURN_OF_THE_KING))
    for row in rows:
        subject = await ctx.session.get(EntityRow, row.subject_node_id) if row.subject_node_id is not None else None
        if subject is None or (subject.id != ruler.id and not houses & await houses_of(ctx, subject)):
            continue
        best = max(best, round_half_up(ctx.rules.belief.return_king_usurper * row.credence / PERCENT))
    return {FORETOLD: best} if best else {}


async def consequences(ctx: TickContext, row: LegendProfileRow) -> str | None:
    table = ctx.rules.belief
    subject = await ctx.session.get(EntityRow, row.subject_node_id) if row.subject_node_id is not None else None
    if row.archetype is A.RETURN_OF_THE_KING:
        return await returning_king(ctx, row, subject)
    if row.archetype is A.CURSED_LINE and subject is not None:
        house_id = next(iter(sorted(await houses_of(ctx, subject))), None)
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
