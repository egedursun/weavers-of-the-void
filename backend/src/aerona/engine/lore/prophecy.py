from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import LegendProfileRow, ProphecyConditionRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow, OfficeRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import LegendArchetype, ProphecyConsequence, ProphecyPredicate, ProphecyState
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.son import PowerEffect
from aerona.domain.enums.war import WarStatus
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.gods.progress import grant_progress
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.legends import resonance
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
from aerona.engine.services.community_relations import change_relation

P = ProphecyPredicate
Args = dict[str, int | str]
DEFAULT_OMEN = EngineKind.WAR


@dataclass(frozen=True)
class Foretelling:
    predicate: ProphecyPredicate
    subject_id: int | None = None
    second_id: int | None = None
    archetype: LegendArchetype | None = None
    sky_kind: SkyEventKind | None = None
    event_kind: EngineKind | None = None
    within_epochs: int | None = None
    consequence: ProphecyConsequence | None = None
    consequence_id: int | None = None


def arg(args: Args, key: str) -> int | None:
    value = args.get(key)
    return int(value) if isinstance(value, int) or (isinstance(value, str) and value.isdigit()) else None


def args_of(told: Foretelling) -> Args:
    found: Args = {}
    subject = told.subject_id
    if told.predicate is P.DIES and subject is not None:
        found["entity"] = subject
    elif told.predicate is P.FALLS and subject is not None:
        found["settlement"] = subject
    elif told.predicate is P.BORN_IN and subject is not None:
        found["house"] = subject
    elif told.predicate is P.SKY_EVENT:
        found["kind"] = (told.sky_kind or SkyEventKind.ECLIPSE).value
    elif told.predicate is P.WAR_BETWEEN and subject is not None and told.second_id is not None:
        found["first"], found["second"] = subject, told.second_id
    elif told.predicate is P.RULER_OF and subject is not None:
        found["polity"] = subject
        if told.archetype is not None:
            found["archetype"] = told.archetype.value
    elif told.predicate is P.WITHIN_EPOCHS:
        found["event"] = (told.event_kind or DEFAULT_OMEN).value
        if subject is not None:
            found["place"] = subject
    if told.within_epochs is not None:
        found["epochs"] = max(1, told.within_epochs)
    return found


async def dies(ctx: TickContext, args: Args, since: int) -> bool:
    target = await ctx.session.get(EntityRow, arg(args, "entity") or 0)
    return target is not None and target.status is not EntityStatus.CANON and (target.end_epoch or 0) >= since


async def falls(ctx: TickContext, args: Args, since: int) -> bool:
    target_id = arg(args, "settlement") or 0
    target = await ctx.session.get(EntityRow, target_id)
    if target is None or target.status is not EntityStatus.CANON:
        return True
    conquered = await ctx.session.scalar(
        select(BondRow.id)
        .where(BondRow.target_node_id == target_id, BondRow.kind == BondKind.RULES, BondRow.epoch >= since, BondRow.state == BondState.ACTIVE)
        .limit(1)
    )
    return conquered is not None


async def born_in(ctx: TickContext, args: Args, since: int) -> bool:
    house = arg(args, "house") or 0
    statement = (
        select(HouseMemberRow.mortal_entity_id)
        .join(EntityRow, EntityRow.id == HouseMemberRow.mortal_entity_id)
        .where(HouseMemberRow.house_entity_id == house, HouseMemberRow.by_marriage.is_(False), EntityRow.birth_epoch >= since)
        .limit(1)
    )
    return await ctx.session.scalar(statement) is not None


async def sky_event(ctx: TickContext, args: Args, since: int) -> bool:
    kind = args.get("kind")
    return await ctx.session.scalar(select(SkyEventRow.id).where(SkyEventRow.kind == kind, SkyEventRow.epoch > since).limit(1)) is not None


async def war_between(ctx: TickContext, args: Args, since: int) -> bool:
    first, second = arg(args, "first") or 0, arg(args, "second") or 0
    wars = select(WarSideRow.war_id).where(WarSideRow.entity_id == first)
    found = await ctx.session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id == second, WarSideRow.war_id.in_(wars), WarRow.started_epoch >= since, WarRow.status != WarStatus.MOBILIZING)
        .limit(1)
    )
    return found is not None


async def fits_archetype(ctx: TickContext, ruler_id: int, archetype: LegendArchetype) -> bool:
    if archetype is LegendArchetype.CHOSEN_ONE and await ctx.session.get(EntityFlagRow, (ruler_id, EntityFlag.CHOSEN)) is not None:
        return True
    houses = select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == ruler_id)
    found = await ctx.session.scalar(
        select(LegendProfileRow.legend_entity_id)
        .where(
            LegendProfileRow.archetype == archetype,
            (LegendProfileRow.subject_node_id == ruler_id) | LegendProfileRow.subject_node_id.in_(houses),
        )
        .limit(1)
    )
    return found is not None


async def ruler_of(ctx: TickContext, args: Args, since: int) -> bool:
    polity = arg(args, "polity") or 0
    ruler = await ctx.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity, OfficeRow.kind == OfficeKind.RULER).limit(1))
    if ruler is None or ruler.holder_entity_id is None or ruler.since_epoch < since:
        return False
    house = arg(args, "house")
    if house is not None and await ctx.session.get(HouseMemberRow, (house, ruler.holder_entity_id)) is None:
        return False
    archetype = args.get("archetype")
    if isinstance(archetype, str) and archetype in {item.value for item in LegendArchetype}:
        return await fits_archetype(ctx, ruler.holder_entity_id, LegendArchetype(archetype))
    if args.get("chosen"):
        return await ctx.session.get(EntityFlagRow, (ruler.holder_entity_id, EntityFlag.CHOSEN)) is not None
    return True


async def within_epochs(ctx: TickContext, args: Args, since: int) -> bool:
    event = args.get("event")
    kind = EngineKind(event) if isinstance(event, str) and event in {item.value for item in EngineKind} else DEFAULT_OMEN
    statement = select(EntityRow.id).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind == kind, EntityRow.birth_epoch >= since)
    place = arg(args, "place")
    if place is not None:
        statement = statement.where(EntityRow.location_id == place)
    return await ctx.session.scalar(statement.limit(1)) is not None


CHECKS: dict[ProphecyPredicate, Callable[[TickContext, Args, int], Awaitable[bool]]] = {
    P.DIES: dies,
    P.FALLS: falls,
    P.BORN_IN: born_in,
    P.SKY_EVENT: sky_event,
    P.WAR_BETWEEN: war_between,
    P.RULER_OF: ruler_of,
    P.WITHIN_EPOCHS: within_epochs,
}


async def met(ctx: TickContext, predicate: ProphecyPredicate, args: Args, since: int) -> bool:
    return await CHECKS[predicate](ctx, args, since)


RESONANT = {
    P.RULER_OF: frozenset({LegendArchetype.CHOSEN_ONE, LegendArchetype.RETURN_OF_THE_KING}),
    P.FALLS: frozenset({LegendArchetype.BETRAYAL, LegendArchetype.LOST_PARADISE}),
    P.DIES: frozenset({LegendArchetype.CURSED_LINE, LegendArchetype.HERO_QUEST}),
    P.BORN_IN: frozenset({LegendArchetype.CHOSEN_ONE}),
    P.SKY_EVENT: frozenset({LegendArchetype.CREATION, LegendArchetype.FLOOD}),
    P.WAR_BETWEEN: frozenset({LegendArchetype.BETRAYAL, LegendArchetype.MONSTER}),
    P.WITHIN_EPOCHS: frozenset({LegendArchetype.FLOOD}),
}


async def subjects(ctx: TickContext, prophecy: EntityRow) -> list[EntityRow]:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == prophecy.id, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    found = []
    for target in dict.fromkeys(await ctx.session.scalars(statement)):
        entity = await living_entity(ctx.session, target)
        if entity is not None:
            found.append(entity)
    return found


async def audience_of(ctx: TickContext, prophecy_id: int) -> list[int]:
    statement = select(BondRow.source_node_id).where(
        BondRow.target_node_id == prophecy_id, BondRow.kind == BondKind.PROPHESIES, BondRow.state == BondState.ACTIVE
    )
    return sorted(set(await ctx.session.scalars(statement)))


async def claimed_polity(ctx: TickContext, house_id: int) -> int | None:
    return await ctx.session.scalar(select(ClaimRow.polity_entity_id).where(ClaimRow.house_entity_id == house_id, ClaimRow.ended_epoch.is_(None)).limit(1))


async def ruling_condition(ctx: TickContext, by_type: dict[EntityType, list[EntityRow]]) -> tuple[ProphecyPredicate, Args] | None:
    if EntityType.HOUSE in by_type:
        house = by_type[EntityType.HOUSE][0]
        polity = await claimed_polity(ctx, house.id)
        return (P.RULER_OF, {"polity": polity, "house": house.id}) if polity is not None else (P.BORN_IN, {"house": house.id})
    if EntityType.POLITY in by_type:
        return P.RULER_OF, {"polity": by_type[EntityType.POLITY][0].id, "chosen": 1}
    return None


async def derive(ctx: TickContext, prophecy: EntityRow, targets: list[EntityRow]) -> tuple[ProphecyPredicate, Args]:
    by_type: dict[EntityType, list[EntityRow]] = {}
    for target in targets:
        by_type.setdefault(target.entity_type, []).append(target)
    communities = [target for target in targets if target.entity_type in COMMUNITY_TYPES]
    if prophecy.engine_kind is EngineKind.ECLIPSE_PROPHECY:
        return P.SKY_EVENT, {"kind": SkyEventKind.ECLIPSE.value}
    ruling = await ruling_condition(ctx, by_type)
    if ruling is not None:
        return ruling
    if len(communities) >= 2:
        return P.WAR_BETWEEN, {"first": communities[0].id, "second": communities[1].id}
    if EntityType.SETTLEMENT in by_type:
        return P.FALLS, {"settlement": by_type[EntityType.SETTLEMENT][0].id}
    if EntityType.MORTAL in by_type:
        return P.DIES, {"entity": by_type[EntityType.MORTAL][0].id}
    return P.WITHIN_EPOCHS, {"event": DEFAULT_OMEN.value}


def deadline_for(ctx: TickContext, prophecy: EntityRow, args: Args) -> int | None:
    epochs = arg(args, "epochs")
    if epochs is not None:
        return prophecy.birth_epoch + epochs
    limit = ctx.rules.deep_life.prophecy_forget_epochs
    return prophecy.birth_epoch + limit if limit > 0 else None


async def condition_of(ctx: TickContext, prophecy: EntityRow) -> ProphecyConditionRow:
    row = await ctx.session.get(ProphecyConditionRow, prophecy.id)
    if row is not None:
        return row
    predicate, args = await derive(ctx, prophecy, await subjects(ctx, prophecy))
    clean = {key: value for key, value in args.items() if value is not None}
    row = ProphecyConditionRow(
        prophecy_entity_id=prophecy.id,
        predicate=predicate,
        args=clean,
        deadline_epoch=deadline_for(ctx, prophecy, clean),
        consequence_kind=None,
        seer_entity_id=prophecy.maker_entity_id,
        audience=await audience_of(ctx, prophecy.id),
        pressure=PERCENT // 5,
        state=ProphecyState.PENDING,
        locked=[],
    )
    ctx.session.add(row)
    return row


async def typed_condition(ctx: TickContext, prophecy: EntityRow, told: Foretelling) -> ProphecyConditionRow:
    row = await condition_of(ctx, prophecy)
    args = args_of(told)
    row.predicate, row.args = told.predicate, args
    row.deadline_epoch = deadline_for(ctx, prophecy, args)
    row.consequence_kind = told.consequence
    consequence = await ctx.session.get(EntityRow, told.consequence_id) if told.consequence_id is not None else None
    row.consequence_entity_id = consequence.id if consequence is not None else None
    await ctx.session.flush()
    return row


async def seer_power(ctx: TickContext, son: SonRow) -> bool:
    levels = ctx.rules.power_unlock_levels
    unlock = (levels.power_1_unlock_level, levels.power_2_unlock_level, levels.power_3_unlock_level)
    powers = await ctx.session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == son.id, SonPowerRow.effect == PowerEffect.SEER))
    return any(son.level >= unlock[min(power.slot, len(unlock) - 1)] for power in powers)


async def reward_fulfilment(ctx: TickContext, prophecy: EntityRow, *, misread: bool) -> None:
    fate = ctx.rules.fate
    seer = await ctx.session.get(EntityRow, prophecy.maker_entity_id) if prophecy.maker_entity_id is not None else None
    if seer is not None and seer.status is EntityStatus.CANON and isinstance(seer.stats, MortalStats):
        change = -fate.seer_wrong_charisma_loss if misread else fate.seer_correct_charisma
        charisma = max(0, min(PERCENT, (seer.stats.charisma if seer.stats.charisma is not None else fate.seer_default_charisma) + change))
        seer.stats = seer.stats.model_copy(update={"charisma": charisma})
    son = await ctx.session.get(SonRow, prophecy.creator_son_id) if prophecy.creator_son_id is not None else None
    if son is not None:
        factor = fate.seer_power_mult if await seer_power(ctx, son) else 1
        await grant_progress(ctx, son, xp=fate.prophecy_xp * factor, fame=fate.prophecy_renown * factor)


async def omen(ctx: TickContext, row: ProphecyConditionRow, target: EntityRow | None) -> str | None:
    for member in row.audience:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, member)
        if values:
            values[ValueAxis.SUPERSTITION] = values.get(ValueAxis.SUPERSTITION, 0) + ctx.rules.prophecy.omen_superstition
            await write_values(ctx.session, ValueHolder.CULTURE, member, values)
    return "the people grow more fearful of signs" if row.audience else None


async def rule(ctx: TickContext, row: ProphecyConditionRow, target: EntityRow | None) -> str | None:
    if target is None:
        return None
    gain = ctx.rules.prophecy.consequence_claim
    for claim in list(await ctx.session.scalars(select(ClaimRow).where(ClaimRow.claimant_entity_id == target.id, ClaimRow.ended_epoch.is_(None)))):
        claim.strength = clamp_int(claim.strength + gain, 0, PERCENT)
    target.importance = (target.importance or 0) + gain
    return f"{target.name} is hailed as the one foretold to rule"


async def fall(ctx: TickContext, row: ProphecyConditionRow, target: EntityRow | None) -> str | None:
    if target is None or stat(target, "defense") is None:
        return None
    shift_stat(target, "defense", -ctx.rules.prophecy.consequence_unrest)
    return f"{target.name} braces for the fall it was promised"


async def death(ctx: TickContext, row: ProphecyConditionRow, target: EntityRow | None) -> str | None:
    if target is None or target.entity_type is not EntityType.MORTAL:
        return None
    await apply_hits(ctx, target, Harm(damage=ctx.rules.prophecy.consequence_harm, cause=HarmCause.CURSE, death_cause="died as was foretold"))
    return f"doom closes on {target.name}"


async def war(ctx: TickContext, row: ProphecyConditionRow, target: EntityRow | None) -> str | None:
    if target is None or not row.audience:
        return None
    for member in row.audience:
        await change_relation(ctx, member, target.id, -ctx.rules.prophecy.consequence_unrest, MemoryKind.ILL_WILL, note="foretold enemies")
    return f"its hearers turn against {target.name}"


async def birth(ctx: TickContext, row: ProphecyConditionRow, target: EntityRow | None) -> str | None:
    if target is None:
        return None
    house_id = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == target.id).limit(1))
    house = await ctx.session.get(HouseProfileRow, house_id if house_id is not None else target.id)
    if house is None:
        return None
    house.prestige = clamp_int(house.prestige + ctx.rules.prophecy.consequence_claim, 0, PERCENT)
    return "a house rises on the strength of a foretold birth"


OUTCOMES: dict[ProphecyConsequence, Callable[[TickContext, ProphecyConditionRow, EntityRow | None], Awaitable[str | None]]] = {
    ProphecyConsequence.OMEN: omen,
    ProphecyConsequence.RULE: rule,
    ProphecyConsequence.FALL: fall,
    ProphecyConsequence.DEATH: death,
    ProphecyConsequence.WAR: war,
    ProphecyConsequence.BIRTH: birth,
}


async def consequences(ctx: TickContext, row: ProphecyConditionRow) -> str | None:
    if row.consequence_kind is None:
        return None
    return await OUTCOMES[row.consequence_kind](ctx, row, await living_entity(ctx.session, row.consequence_entity_id))


async def fulfil(ctx: TickContext, prophecy: EntityRow, row: ProphecyConditionRow) -> str | None:
    row.state, row.resolved_epoch = ProphecyState.FULFILLED, ctx.epoch
    await retire(ctx.session, prophecy, ctx.epoch, f"Epoch {ctx.epoch}: what was foretold came to pass.", status=EntityStatus.FULFILLED)
    await reward_fulfilment(ctx, prophecy, misread=False)
    return await consequences(ctx, row)


async def cult_of(ctx: TickContext, seer: EntityRow) -> EntityRow | None:
    if seer.entity_type is EntityType.CULT:
        return seer
    cult_id = await ctx.session.scalar(
        select(BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.source_node_id == seer.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, EntityRow.entity_type == EntityType.CULT
        )
        .limit(1)
    )
    return await living_entity(ctx.session, cult_id)


async def mock_seer(ctx: TickContext, row: ProphecyConditionRow) -> bool:
    seer = await living_entity(ctx.session, row.seer_entity_id)
    if seer is None:
        return False
    table = ctx.rules.prophecy
    if seer.entity_type is EntityType.MORTAL:
        if stat(seer, "charisma") is not None:
            shift_stat(seer, "charisma", -ctx.rules.fate.seer_wrong_charisma_loss)
        seer.importance = max(0, (seer.importance or 0) - table.failure_importance)
        for member in row.audience:
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=member,
                subject_id=seer.id,
                kind=MemoryKind.ILL_WILL,
                magnitude=-table.failure_importance,
                epoch=ctx.epoch,
                note="a false seer",
            )
    cult = await cult_of(ctx, seer)
    if cult is not None:
        shift_stat(cult, "zeal", -table.failure_zeal)
    return True


async def fail(ctx: TickContext, row: ProphecyConditionRow) -> int:
    row.state, row.resolved_epoch = ProphecyState.FAILED, ctx.epoch
    doubted = 0
    for member in row.audience:
        values = await stored_values(ctx.session, ValueHolder.CULTURE, member)
        if not values:
            continue
        values[ValueAxis.SUPERSTITION] = values.get(ValueAxis.SUPERSTITION, 0) - ctx.rules.prophecy.failure_rationalism
        await write_values(ctx.session, ValueHolder.CULTURE, member, values)
        doubted += 1
    await mock_seer(ctx, row)
    return doubted


async def threatened_ruler(ctx: TickContext, row: ProphecyConditionRow) -> str | None:
    polity, house = arg(row.args, "polity"), arg(row.args, "house")
    if polity is None or house is None:
        return None
    office = await ctx.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity, OfficeRow.kind == OfficeKind.RULER).limit(1))
    ruler = await living_entity(ctx.session, office.holder_entity_id) if office is not None else None
    if ruler is None or await ctx.session.get(HouseMemberRow, (house, ruler.id)) is not None:
        return None
    if not ctx.rng(f"paranoia.{row.prophecy_entity_id}.{ctx.epoch}").chance(ctx.rules.prophecy.paranoia_chance):
        return None
    child = await ctx.session.scalar(
        select(EntityRow)
        .join(HouseMemberRow, HouseMemberRow.mortal_entity_id == EntityRow.id)
        .where(HouseMemberRow.house_entity_id == house, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.birth_epoch.desc(), EntityRow.id)
        .limit(1)
    )
    if child is None:
        return None
    harm = Harm(damage=ctx.rules.backlash.injury_hp * 2, cause=HarmCause.PUNISHMENT, death_cause="slain to cheat a prophecy", killer_id=ruler.id)
    await apply_hits(ctx, child, harm)
    kin = list(await ctx.session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house)))
    for keeper in [house, *kin]:
        if keeper != child.id:
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=keeper,
                subject_id=ruler.id,
                kind=MemoryKind.HARMED_ME,
                magnitude=-ctx.rules.prophecy.infanticide_grudge,
                epoch=ctx.epoch,
                note=f"moved against {child.name}",
            )
    await note(ctx, f"{ruler.name} moved against {child.name}, the child a prophecy named.", key="lore.infanticide", ids=[ruler.id, child.id, house])
    return f"{ruler.name} moved against {child.name}, the child the prophecy named"


async def press(ctx: TickContext, prophecy: EntityRow, row: ProphecyConditionRow) -> str | None:
    table = ctx.rules.prophecy
    certainty = stat(prophecy, "certainty") or 0
    boost = await resonance(ctx, RESONANT[row.predicate])
    if boost:
        set_stats(prophecy, certainty=clamp_int(certainty + boost, 0, PERCENT))
    if certainty < ctx.rules.record_schema.certainty_threshold:
        return None
    if "pressure" not in row.locked:
        row.pressure = clamp_int(row.pressure + round_half_up(table.pressure_gain * await ctx.hook_factor(prophecy.id, DomainHook.PROPHECY)), 0, PERCENT)
    weight = row.pressure / PERCENT
    if row.predicate is P.RULER_OF and arg(row.args, "house") is not None:
        claims = await ctx.session.scalars(select(ClaimRow).where(ClaimRow.house_entity_id == arg(row.args, "house"), ClaimRow.ended_epoch.is_(None)))
        for claim in claims:
            claim.strength = clamp_int(claim.strength + round_half_up(table.claim_strength * weight), 0, PERCENT)
        return await threatened_ruler(ctx, row) or "the named house's claim swells"
    if row.predicate is P.WAR_BETWEEN:
        first, second = arg(row.args, "first"), arg(row.args, "second")
        if first is not None and second is not None:
            await change_relation(ctx, first, second, -round_half_up(table.pressure_gain * weight), MemoryKind.ILL_WILL, note="a prophecy of war")
            return "the foretold enemies eye each other"
    if row.predicate is P.FALLS:
        town = await living_entity(ctx.session, arg(row.args, "settlement"))
        if town is not None and stat(town, "defense") is not None:
            set_stats(town, defense=clamp_int((stat(town, "defense") or 0) - round_half_up(table.pressure_gain * weight), 0, PERCENT))
            return f"{town.name} loses heart"
    return None


async def resolve(ctx: TickContext, prophecy: EntityRow) -> tuple[ProphecyState, str | None]:
    row = await condition_of(ctx, prophecy)
    if row.state is not ProphecyState.PENDING:
        return row.state, None
    if await met(ctx, row.predicate, row.args, prophecy.birth_epoch):
        return ProphecyState.FULFILLED, await fulfil(ctx, prophecy, row)
    return ProphecyState.PENDING, await press(ctx, prophecy, row)
