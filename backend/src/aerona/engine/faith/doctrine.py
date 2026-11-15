from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tenets import DOMAIN_JUDGEMENT, DOMAIN_TENETS, OPPOSED, PASSION_TENETS, VALUE_TENETS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultOfficeRow, CultTenetRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import ClergyOffice, JudgementDoctrine, RebirthPath, TenetKind
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.environment.places import holy_place_ids
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.mind.book import skill_level, values_for
from aerona.engine.phases.births import NOTABLE_ROLES, raise_notable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

CLERGY_ROLES = (MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER)
FOODS = (CommodityKind.LIVESTOCK, CommodityKind.FISH, CommodityKind.GRAIN)
FILLERS = (TenetKind.PROSELYTISM, TenetKind.JUDGEMENT_BY_DEEDS, TenetKind.ANCESTOR_VENERATION)


def passion_tenets(church: Church, threshold: int) -> list[TenetKind]:
    god = church.god
    if god is None:
        return []
    passions = sorted(((getattr(god, passion.value), passion) for passion in PASSION_TENETS), key=lambda item: -item[0])
    return [tenet for value, passion in passions if value >= threshold for tenet in PASSION_TENETS[passion]]


def wanted_tenets(rules: Rules, church: Church, values: dict[ValueAxis, int], seeded: tuple[TenetKind, ...] = ()) -> list[TenetKind]:
    table = rules.doctrine
    found: list[TenetKind] = list(seeded)
    god = church.god
    if god is not None:
        for domain in (god.domain_primary, god.domain_secondary):
            found.extend(DOMAIN_TENETS.get(domain, ()))
    found.extend(passion_tenets(church, table.passion_tenet))
    for axis, (high, low) in VALUE_TENETS.items():
        value = values.get(axis, 0)
        if value >= table.value_tenet:
            found.append(high)
        elif value <= -table.value_tenet:
            found.append(low)
    chosen: list[TenetKind] = []
    for tenet in dict.fromkeys(found):
        if any(frozenset({tenet, other}) in OPPOSED for other in chosen):
            continue
        chosen.append(tenet)
        if len(chosen) >= max(table.tenets_max, len(seeded)):
            break
    for filler in FILLERS:
        if len(chosen) >= table.tenets_min:
            break
        if filler not in chosen and not any(frozenset({filler, other}) in OPPOSED for other in chosen):
            chosen.append(filler)
    return chosen


async def sacred_species(ctx: TickContext, church: Church) -> int | None:
    atlas = await RegionAtlas.load(ctx.session)
    regions = sorted({region for member in church.members for region in [atlas.top_region(member.id)] if region is not None})
    domains = {church.god.domain_primary, church.god.domain_secondary} if church.god is not None else set()
    species = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.SPECIES, EntityRow.world_id == church.cult.world_id, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
    )
    if not species:
        return None
    ranges = await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id.in_(regions), SpeciesRangeRow.species_entity_id.in_([row.id for row in species]))
    )
    abundance: Counter[int] = Counter()
    for row in ranges:
        abundance[row.species_entity_id] += row.abundance
    best = max(species, key=lambda row: (row.domain in domains, abundance.get(row.id, 0), -row.id))
    return best.id


async def target_for(ctx: TickContext, church: Church, tenet: TenetKind) -> str | None:
    if tenet is TenetKind.DIETARY_LAW:
        return ctx.rng(f"diet.{church.cult.id}").pick(list(FOODS)).value
    if tenet is TenetKind.SACRED_SPECIES:
        species = await sacred_species(ctx, church)
        return str(species) if species is not None else None
    if tenet is TenetKind.PILGRIMAGE_DUTY:
        holy = await holy_place_ids(ctx.session, ctx.rules, church.cult.world_id) if church.cult.world_id is not None else []
        place = holy[0] if holy else church.cult.location_id
        return str(place) if place is not None else None
    return None


def judgement_of(church: Church, tenets: list[TenetKind]) -> JudgementDoctrine:
    if TenetKind.JUDGEMENT_BY_DEEDS in tenets:
        return JudgementDoctrine.DEEDS
    if TenetKind.JUDGEMENT_BY_FAITH in tenets:
        return JudgementDoctrine.FAITH
    if church.god is None:
        return JudgementDoctrine.NONE
    return DOMAIN_JUDGEMENT.get(church.god.domain_primary, JudgementDoctrine.DEEDS)


def rebirth_path_of(rules: Rules, values: dict[ValueAxis, int], judgement: JudgementDoctrine) -> RebirthPath:
    threshold = rules.doctrine.value_tenet
    if values.get(ValueAxis.KINSHIP, 0) >= threshold:
        return RebirthPath.HOUSE
    if judgement in {JudgementDoctrine.DEEDS, JudgementDoctrine.FAITH} and values.get(ValueAxis.HIERARCHY, 0) >= threshold:
        return RebirthPath.MERIT
    return RebirthPath.PEOPLE


async def spoken_by(session: AsyncSession, community_ids: list[int]) -> Counter[int]:
    if not community_ids:
        return Counter()
    languages = select(EntityRow.id).where(EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON)
    rows = await session.scalars(
        select(BondRow.target_node_id).where(
            BondRow.source_node_id.in_(community_ids),
            BondRow.kind == BondKind.SPEAKS,
            BondRow.state == BondState.ACTIVE,
            BondRow.target_node_id.in_(languages),
        )
    )
    return Counter(rows)


async def liturgy_for(session: AsyncSession, church: Church) -> int | None:
    spoken = await spoken_by(session, [member.id for member in church.members] or [church.cult.id])
    if not spoken:
        return None
    return max(spoken, key=lambda language: (spoken[language], -language))


async def liturgy_reach(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None or doctrine.liturgical_language_id is None or not church.members:
        return PERCENT
    speakers = 0
    for member in church.members:
        if doctrine.liturgical_language_id in await spoken_by(ctx.session, [member.id]):
            speakers += 1
    share = speakers * PERCENT // len(church.members)
    return round_half_up(share + (PERCENT - share) * ctx.rules.doctrine.liturgy_preaching_pct / PERCENT)


async def found_doctrine(
    ctx: TickContext, church: Church, *, seeded: tuple[TenetKind, ...] = (), judgement: JudgementDoctrine | None = None
) -> CultDoctrineRow:
    values = await values_for(ctx.session, church.cult.id)
    tenets = wanted_tenets(ctx.rules, church, values, seeded)
    for tenet in tenets:
        row = CultTenetRow(
            cult_entity_id=church.cult.id,
            tenet=tenet,
            target=await target_for(ctx, church, tenet),
            since_epoch=ctx.epoch,
            revealed_by_son_id=church.god.id if tenet in seeded and church.god is not None else None,
        )
        ctx.session.add(row)
        church.tenets[tenet] = row
    chosen = judgement or judgement_of(church, tenets)
    doctrine = CultDoctrineRow(
        cult_entity_id=church.cult.id,
        judgement=chosen,
        orthodoxy=clamp_int(PERCENT // 2 + values.get(ValueAxis.TRADITION, 0) // 2 - values.get(ValueAxis.XENOPHILIA, 0) // 4, 0, PERCENT),
        tithe_rate=ctx.rules.tithes.rate,
        treasury=0,
        clergy_count=0,
        clergy_quality=0,
        zeal_parts={},
        excommunicated=[],
        liturgical_language_id=await liturgy_for(ctx.session, church),
        rebirth_path=rebirth_path_of(ctx.rules, values, chosen),
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(doctrine)
    church.doctrine = doctrine
    return doctrine


async def clergy_of(ctx: TickContext, church: Church) -> list[EntityRow]:
    homes = [member.id for member in church.members] + [member.location_id for member in church.members if member.location_id is not None]
    if not homes:
        return []
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                await present_among(ctx.session, homes),
                EntityRow.mortal_role.in_(list(CLERGY_ROLES)),
            )
            .order_by(EntityRow.id)
        )
    )


async def divine_king(ctx: TickContext, church: Church) -> EntityRow | None:
    if not church.holds(TenetKind.DIVINE_KINGSHIP):
        return None
    realm = await ctx.session.scalar(
        select(PolityProfileRow).where(PolityProfileRow.state_religion_id == church.cult.id).order_by(PolityProfileRow.polity_entity_id).limit(1)
    )
    if realm is None:
        return None
    ruler_id = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm.polity_entity_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return await living_entity(ctx.session, ruler_id) if ruler_id is not None else None


async def clergy_numbers(
    ctx: TickContext, church: Church, doctrine: CultDoctrineRow, clergy: list[EntityRow], scored: list[tuple[int, int, EntityRow]]
) -> None:
    priests = 0
    for member in church.members:
        society = await ctx.session.get(CommunitySocietyRow, member.id)
        if society is not None:
            priests += round_half_up((stat(member, "population") or 0) * society.share(SocialClass.PRIEST) / PERCENT)
    if "clergy_count" not in doctrine.locked:
        doctrine.clergy_count = priests + len(clergy)
    best = ctx.rules.doctrine.clergy_per_office
    if "clergy_quality" not in doctrine.locked:
        doctrine.clergy_quality = clamp_int(sum(score for score, _, _ in scored[:best]) / max(1, min(best, len(scored))), 0, PERCENT)


async def staff(ctx: TickContext, church: Church) -> int:
    doctrine = church.doctrine
    if doctrine is None:
        return 0
    clergy = await clergy_of(ctx, church)
    if not clergy and church.members:
        seat = max(church.members, key=lambda member: (member.entity_type is EntityType.SETTLEMENT, stat(member, "population") or 0, -member.id))
        clergy = [await raise_notable(ctx, seat, SocialClass.PRIEST, NOTABLE_ROLES[SocialClass.PRIEST][0])]
    scored = sorted(
        [(await skill_level(ctx.session, mortal.id, SkillKind.THEOLOGY), -mortal.id, mortal) for mortal in clergy],
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    await clergy_numbers(ctx, church, doctrine, clergy, scored)
    wanted = [ClergyOffice.HIGH_PRIEST, ClergyOffice.PRIEST]
    if church.holds(TenetKind.MONASTIC_LEARNING) or church.holds(TenetKind.ASCETICISM):
        wanted.append(ClergyOffice.MONK)
    if doctrine.orthodoxy >= ctx.rules.inquisition.orthodoxy_suppress:
        wanted.append(ClergyOffice.INQUISITOR)
    offices = {row.kind: row for row in await ctx.session.scalars(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == church.cult.id))}
    god_king = await divine_king(ctx, church)
    candidates = [item[2] for item in scored]
    filled = 0
    for kind in wanted:
        row = offices.get(kind)
        if row is None:
            row = CultOfficeRow(cult_entity_id=church.cult.id, kind=kind, since_epoch=ctx.epoch, locked=False)
            ctx.session.add(row)
        if row.locked:
            continue
        if kind is ClergyOffice.HIGH_PRIEST and god_king is not None:
            if row.holder_entity_id != god_king.id:
                row.holder_entity_id, row.since_epoch = god_king.id, ctx.epoch
                filled += 1
            continue
        if row.holder_entity_id is not None and any(mortal.id == row.holder_entity_id for mortal in clergy):
            candidates = [mortal for mortal in candidates if mortal.id != row.holder_entity_id]
            continue
        holder = candidates.pop(0) if candidates else None
        row.holder_entity_id, row.since_epoch = (holder.id if holder is not None else None), ctx.epoch
        filled += int(holder is not None)
    return filled


async def ensure_doctrines(ctx: TickContext, book: FaithBook) -> int:
    founded = 0
    for church in book.churches.values():
        if church.doctrine is None and not held(church.cult.id):
            await found_doctrine(ctx, church)
            founded += 1
    await ctx.session.flush()
    return founded
