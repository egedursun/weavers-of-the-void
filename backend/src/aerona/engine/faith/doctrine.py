from sqlalchemy import select

from aerona.catalog.tenets import DOMAIN_JUDGEMENT, DOMAIN_TENETS, OPPOSED, VALUE_TENETS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultOfficeRow, CultTenetRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import ClergyOffice, JudgementDoctrine, TenetKind
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.environment.places import holy_place_ids
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.mind.book import skill_level, values_for
from aerona.engine.phases.births import NOTABLE_ROLES, raise_notable
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat

CLERGY_ROLES = (MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER)
FOODS = (CommodityKind.LIVESTOCK, CommodityKind.FISH, CommodityKind.GRAIN)
PRIESTS_PER_OFFICE = 3


def wanted_tenets(rules_min: int, rules_max: int, church: Church, values: dict[ValueAxis, int], threshold: int) -> list[TenetKind]:
    found: list[TenetKind] = []
    god = church.god
    if god is not None:
        for domain in (god.domain_primary, god.domain_secondary):
            found.extend(DOMAIN_TENETS.get(domain, ()))
    for axis, (high, low) in VALUE_TENETS.items():
        value = values.get(axis, 0)
        if value >= threshold:
            found.append(high)
        elif value <= -threshold:
            found.append(low)
    chosen: list[TenetKind] = []
    for tenet in dict.fromkeys(found):
        if any(frozenset({tenet, other}) in OPPOSED for other in chosen):
            continue
        chosen.append(tenet)
        if len(chosen) >= rules_max:
            break
    for filler in (TenetKind.PROSELYTISM, TenetKind.JUDGEMENT_BY_DEEDS, TenetKind.ANCESTOR_VENERATION):
        if len(chosen) >= rules_min:
            break
        if filler not in chosen and not any(frozenset({filler, other}) in OPPOSED for other in chosen):
            chosen.append(filler)
    return chosen


async def target_for(ctx: TickContext, church: Church, tenet: TenetKind) -> str | None:
    if tenet is TenetKind.DIETARY_LAW:
        return ctx.rng(f"diet.{church.cult.id}").pick(list(FOODS)).value
    if tenet is TenetKind.SACRED_SPECIES:
        species = await ctx.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.entity_type == EntityType.SPECIES, EntityRow.world_id == church.cult.world_id, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
            .limit(1)
        )
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


async def found_doctrine(ctx: TickContext, church: Church) -> CultDoctrineRow:
    table = ctx.rules.doctrine
    values = await values_for(ctx.session, church.cult.id)
    tenets = wanted_tenets(table.tenets_min, table.tenets_max, church, values, table.value_tenet)
    for tenet in tenets:
        row = CultTenetRow(cult_entity_id=church.cult.id, tenet=tenet, target=await target_for(ctx, church, tenet), since_epoch=ctx.epoch)
        ctx.session.add(row)
        church.tenets[tenet] = row
    doctrine = CultDoctrineRow(
        cult_entity_id=church.cult.id,
        judgement=judgement_of(church, tenets),
        orthodoxy=clamp_int(PERCENT // 2 + values.get(ValueAxis.TRADITION, 0) // 2 - values.get(ValueAxis.XENOPHILIA, 0) // 4, 0, PERCENT),
        tithe_rate=ctx.rules.tithes.rate,
        treasury=0,
        clergy_count=0,
        clergy_quality=0,
        zeal_parts={},
        excommunicated=[],
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
                EntityRow.location_id.in_(homes),
                EntityRow.mortal_role.in_(list(CLERGY_ROLES)),
            )
            .order_by(EntityRow.id)
        )
    )


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
    priests = 0
    for member in church.members:
        society = await ctx.session.get(CommunitySocietyRow, member.id)
        if society is not None:
            priests += round_half_up((stat(member, "population") or 0) * society.share(SocialClass.PRIEST) / PERCENT)
    if "clergy_count" not in doctrine.locked:
        doctrine.clergy_count = priests + len(clergy)
    if "clergy_quality" not in doctrine.locked:
        doctrine.clergy_quality = clamp_int(
            sum(score for score, _, _ in scored[:PRIESTS_PER_OFFICE]) / max(1, min(PRIESTS_PER_OFFICE, len(scored))), 0, PERCENT
        )
    wanted = [ClergyOffice.HIGH_PRIEST, ClergyOffice.PRIEST]
    if church.holds(TenetKind.MONASTIC_LEARNING) or church.holds(TenetKind.ASCETICISM):
        wanted.append(ClergyOffice.MONK)
    if doctrine.orthodoxy >= ctx.rules.inquisition.orthodoxy_suppress:
        wanted.append(ClergyOffice.INQUISITOR)
    offices = {row.kind: row for row in await ctx.session.scalars(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == church.cult.id))}
    filled = 0
    for index, kind in enumerate(wanted):
        holder = scored[index][2] if index < len(scored) else None
        row = offices.get(kind)
        if row is None:
            row = CultOfficeRow(cult_entity_id=church.cult.id, kind=kind, since_epoch=ctx.epoch)
            ctx.session.add(row)
        living = row.holder_entity_id is not None and any(mortal.id == row.holder_entity_id for mortal in clergy)
        if not living:
            row.holder_entity_id, row.since_epoch = (holder.id if holder is not None else None), ctx.epoch
            filled += int(holder is not None)
    return filled


async def ensure_doctrines(ctx: TickContext, book: FaithBook) -> int:
    founded = 0
    for church in book.churches.values():
        if church.doctrine is None:
            await found_doctrine(ctx, church)
            founded += 1
    await ctx.session.flush()
    return founded
