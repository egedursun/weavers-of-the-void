from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.discovery import FIELDS
from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderTechniqueRow, LanguageStandingRow, ResearchFocusRow, ResearchProgressRow
from aerona.db.tables.discovery import GreatPersonRow, GreatPointsRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.region import PolityMapKnowledgeRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.discovery import GreatField
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillSource
from aerona.domain.enums.structure import ConstructionState
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.lore.learning import realm_of
from aerona.engine.lore.research import holder_levels
from aerona.engine.lore.research_depth import open_techniques
from aerona.engine.mind.book import set_skill
from aerona.engine.mind.ethics import church_of
from aerona.engine.mortal.standing import add_renown
from aerona.engine.notes import note
from aerona.engine.phases.births import NOTABLE_ROLES, raise_notable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.structures.readers import working
from aerona.rules.registry import Rules


async def communities(session: AsyncSession) -> list[EntityRow]:
    rows = await session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return list(rows)


async def residents(session: AsyncSession) -> dict[int, list[int]]:
    found: dict[int, list[int]] = defaultdict(list)
    rows = await session.execute(
        select(EntityRow.location_id, EntityRow.id).where(
            EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None)
        )
    )
    for home, mortal in rows.all():
        if home is not None:
            found[home].append(mortal)
    return found


async def skill_book(session: AsyncSession, mortals: list[int]) -> dict[int, dict[str, int]]:
    found: dict[int, dict[str, int]] = defaultdict(dict)
    if not mortals:
        return found
    rows = await session.execute(select(SkillRow.holder_node_id, SkillRow.skill, SkillRow.level).where(SkillRow.holder_node_id.in_(mortals)))
    for mortal, skill, level in rows.all():
        found[mortal][skill.value] = max(found[mortal].get(skill.value, 0), int(level))
    return found


def field_level(skills: dict[str, int], field: GreatField) -> int:
    return max((skills.get(skill.value, 0) for skill in FIELDS[field].skills), default=0)


async def gather_points(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    homes = await residents(ctx.session)
    skills = await skill_book(ctx.session, [mortal for group in homes.values() for mortal in group])
    kinds = {kind for spec in FIELDS.values() for kind in spec.structures}
    built: dict[int, list[str]] = defaultdict(list)
    for item in await working(ctx.session, kinds):
        if item.profile.host_entity_id is not None:
            built[item.profile.host_entity_id].append(item.profile.kind.value)
    rows = {(row.holder_entity_id, row.field): row for row in await ctx.session.scalars(select(GreatPointsRow))}
    gained = 0
    for community in await communities(ctx.session):
        if held(community.id):
            continue
        for field, spec in FIELDS.items():
            levels = sorted((field_level(skills.get(mortal, {}), field) for mortal in homes.get(community.id, [])), reverse=True)
            structures = sum(1 for kind in built.get(community.id, []) if kind in {item.value for item in spec.structures})
            gain = sum(levels[: table.skilled_counted]) // table.skill_divisor + structures * table.structure_points
            if gain <= 0:
                continue
            row = rows.get((community.id, field))
            if row is None:
                row = GreatPointsRow(holder_entity_id=community.id, field=field, points=0, updated_epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
                rows[(community.id, field)] = row
            if "points" in row.locked:
                continue
            row.points += gain
            row.updated_epoch = ctx.epoch
            gained += 1
    await ctx.session.flush()
    return gained


async def threshold(ctx: TickContext, world_id: int | None) -> int:
    return await great_threshold(ctx.session, ctx.rules, world_id)


async def great_threshold(session: AsyncSession, rules: Rules, world_id: int | None) -> int:
    table = rules.discovery
    risen = await session.scalar(
        select(func.count()).select_from(GreatPersonRow).join(EntityRow, EntityRow.id == GreatPersonRow.mortal_entity_id).where(EntityRow.world_id == world_id)
    )
    return table.great_threshold + int(risen or 0) * table.threshold_growth


async def candidate(ctx: TickContext, community: EntityRow, field: GreatField) -> EntityRow | None:
    great = select(GreatPersonRow.mortal_entity_id)
    mortals = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(
                await folk_of(ctx.session, community),
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                EntityRow.id.not_in(great),
            )
            .order_by(EntityRow.id)
        )
    )
    skills = await skill_book(ctx.session, [mortal.id for mortal in mortals])
    ranked = sorted(mortals, key=lambda mortal: (-field_level(skills.get(mortal.id, {}), field), mortal.id))
    return next((mortal for mortal in ranked if not held(mortal.id)), None)


async def raise_great(ctx: TickContext, community: EntityRow, field: GreatField) -> GreatPersonRow:
    spec = FIELDS[field]
    mortal = await candidate(ctx, community, field)
    if mortal is None:
        mortal = await raise_notable(ctx, community, spec.social_class, NOTABLE_ROLES[spec.social_class][0])
    skills = (await skill_book(ctx.session, [mortal.id])).get(mortal.id, {})
    best = max(spec.skills, key=lambda skill: (skills.get(skill.value, 0), -spec.skills.index(skill)))
    level = clamp_int(skills.get(best.value, 0) + ctx.rules.discovery.great_skill, 0, PERCENT)
    await set_skill(ctx.session, mortal.id, best, level, epoch=ctx.epoch, source=SkillSource.PRACTICE)
    await add_renown(ctx.session, mortal.id, ctx.rules.discovery.great_renown, ctx.epoch, rules=ctx.rules)
    row = GreatPersonRow(mortal_entity_id=mortal.id, field=field, holder_entity_id=community.id, promoted_epoch=ctx.epoch, deed_done=False, locked=[])
    ctx.session.add(row)
    await note(
        ctx,
        f"{mortal.name} rose as {an(spec.label.lower())} of {community.name}.",
        key="discovery.great_person",
        ids=[mortal.id, community.id],
        kind=ChronicleKind.KNOWLEDGE,
    )
    return row


async def promote_great(ctx: TickContext) -> int:
    raised = 0
    rows = list(await ctx.session.scalars(select(GreatPointsRow).order_by(GreatPointsRow.points.desc(), GreatPointsRow.holder_entity_id)))
    for row in rows:
        community = await ctx.session.get(EntityRow, row.holder_entity_id)
        if community is None or community.status is not EntityStatus.CANON or held(community.id) or "points" in row.locked:
            continue
        needed = await threshold(ctx, community.world_id)
        if row.points < needed:
            continue
        great = await raise_great(ctx, community, row.field)
        row.points -= needed
        await ctx.session.flush()
        await perform_deed(ctx, great)
        raised += 1
    return raised


async def breakthrough(ctx: TickContext, community: EntityRow) -> bool:
    focus = await ctx.session.get(ResearchFocusRow, community.id)
    known = {row for row in await ctx.session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == community.id))}
    open_now = await open_techniques(ctx.session, community.id, (await holder_levels(ctx.session)).get(community.id, {}))
    chosen = focus.technique if focus is not None and focus.technique not in known else (open_now[0] if open_now else None)
    if chosen is None:
        return False
    ctx.session.add(HolderTechniqueRow(holder_entity_id=community.id, technique=chosen, since_epoch=ctx.epoch, secret=False))
    progress = await ctx.session.get(ResearchProgressRow, (community.id, chosen))
    if progress is not None:
        await ctx.session.delete(progress)
    await note(ctx, f"A breakthrough gave {community.name} {TECHNIQUES[chosen].label.lower()}.", key="discovery.breakthrough", ids=[community.id])
    return True


async def great_work(ctx: TickContext, community: EntityRow) -> bool:
    people = await people_of(ctx.session, community)
    tongue = await spoken_language(ctx.session, (people or community).id)
    standing = await ctx.session.get(LanguageStandingRow, tongue.id) if tongue is not None else None
    if standing is None or "prestige" in standing.locked:
        return False
    standing.prestige = clamp_int(standing.prestige + ctx.rules.discovery.great_prestige, 0, PERCENT)
    return True


async def campaign(ctx: TickContext, community: EntityRow) -> bool:
    armies = list(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == community.id, BondRow.kind == BondKind.PROTECTS, BondRow.state == BondState.ACTIVE)
        )
    )
    lifted = 0
    for army_id in armies:
        army = await ctx.session.get(EntityRow, army_id)
        if army is not None and army.entity_type is EntityType.ARMY and army.status is EntityStatus.CANON and not held(army.id):
            shift_stat(army, "morale", ctx.rules.discovery.great_morale)
            lifted += 1
    return lifted > 0


async def doctrine(ctx: TickContext, community: EntityRow) -> bool:
    people = await people_of(ctx.session, community)
    kindled = 0
    for cult_id in await church_of(ctx.session, people or community):
        cult = await ctx.session.get(EntityRow, cult_id)
        if cult is not None and cult.status is EntityStatus.CANON and not held(cult.id):
            shift_stat(cult, "zeal", ctx.rules.discovery.great_zeal)
            kindled += 1
    return kindled > 0


async def building_rush(ctx: TickContext, community: EntityRow) -> bool:
    works = list(
        await ctx.session.scalars(
            select(StructureProfileRow).where(
                StructureProfileRow.host_entity_id == community.id, StructureProfileRow.construction_state == ConstructionState.BUILDING
            )
        )
    )
    for row in works:
        if "progress" not in row.locked and not held(row.structure_entity_id):
            row.progress = clamp_int(row.progress + ctx.rules.discovery.great_rush, 0, PERCENT - 1)
    return bool(works)


async def monopoly(ctx: TickContext, community: EntityRow) -> bool:
    realm = await realm_of(ctx.session, community.id)
    profile = await ctx.session.get(PolityProfileRow, realm) if realm is not None else None
    if profile is not None and "treasury" not in profile.locked:
        profile.treasury += ctx.rules.discovery.great_wealth
        return True
    give_coin(ctx.rules, community, ctx.rules.discovery.great_wealth)
    return True


async def discovery(ctx: TickContext, community: EntityRow) -> bool:
    realm = await realm_of(ctx.session, community.id)
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(community.id)
    if realm is None or region is None:
        return False
    for land in sorted({region, *atlas.neighbour_regions(region), *(far for near in atlas.neighbour_regions(region) for far in atlas.neighbour_regions(near))}):
        row = await ctx.session.get(PolityMapKnowledgeRow, (realm, land))
        if row is None:
            row = PolityMapKnowledgeRow(polity_entity_id=realm, region_entity_id=land, level=0, held=False, updated_epoch=ctx.epoch)
            ctx.session.add(row)
        if not row.held:
            row.level = max(row.level, ctx.rules.discovery.great_charting)
            row.updated_epoch = ctx.epoch
    return True


DEEDS = {
    GreatField.SCHOLAR: breakthrough,
    GreatField.ARTIST: great_work,
    GreatField.GENERAL: campaign,
    GreatField.PROPHET: doctrine,
    GreatField.ENGINEER: building_rush,
    GreatField.MERCHANT: monopoly,
    GreatField.EXPLORER: discovery,
}


async def perform_deed(ctx: TickContext, great: GreatPersonRow) -> bool:
    if great.deed_done or "deed_done" in great.locked or great.holder_entity_id is None:
        return False
    community = await ctx.session.get(EntityRow, great.holder_entity_id)
    if community is None or community.status is not EntityStatus.CANON:
        return False
    if await DEEDS[great.field](ctx, community):
        great.deed_done, great.deed_epoch = True, ctx.epoch
        return True
    return False


async def pending_deeds(ctx: TickContext) -> int:
    done = 0
    for great in list(await ctx.session.scalars(select(GreatPersonRow).where(GreatPersonRow.deed_done.is_(False)).order_by(GreatPersonRow.mortal_entity_id))):
        mortal = await ctx.session.get(EntityRow, great.mortal_entity_id)
        if mortal is not None and mortal.status is EntityStatus.CANON and not held(mortal.id):
            done += int(await perform_deed(ctx, great))
    return done


async def great_people(ctx: TickContext) -> dict[str, int]:
    return {"great_points": await gather_points(ctx), "great_people": await promote_great(ctx), "great_deeds": await pending_deeds(ctx)}
