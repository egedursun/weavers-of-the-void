from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.intimacy_shapes import ENFORCER_FORCE_PCT
from aerona.catalog.life.intimacy import CLOSE_KIN, EXTENDED_KIN, STRICT_AXES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import IntimacyNormRow
from aerona.db.tables.kin import KinGroupMemberRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intimacy import KinScope, NormEnforcer, NormSanction, NormStance, RelationContext
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.mind import ValueHolder
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.relations import RelationType
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import sexes_fixed, system_of
from aerona.engine.economy.purse import shift_points
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.kin.roles import kin_by_role
from aerona.engine.mind.book import stored_values
from aerona.engine.mortal.kin import parents_of
from aerona.engine.mortal.kinship import marriage_between
from aerona.engine.polity.book import sex_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.engine.relations.book import ensure_relation, shift

STANCES = tuple(NormStance)
SANCTIONED = frozenset({NormStance.FORBIDDEN, NormStance.DISCOURAGED})
SCOPE_ROLES = {KinScope.CLOSE: CLOSE_KIN, KinScope.EXTENDED: EXTENDED_KIN, KinScope.GROUP: EXTENDED_KIN}
OUTSIDE_WEIGHTS = {
    NormStance.FORBIDDEN: 2.0,
    NormStance.DISCOURAGED: 1.5,
    NormStance.TOLERATED: 1.0,
    NormStance.ACCEPTED: 0.5,
    NormStance.HONOURED: 0.0,
}
STRICT_AT = 50


@dataclass
class NormTally:
    scandals: int = 0
    sanctions: int = 0
    fled: int = 0
    hidden: int = 0
    changed: int = 0


async def made(session: AsyncSession, being: EntityRow) -> bool:
    profile = await session.get(MindProfileRow, being.id)
    return profile is not None and profile.origin is not MindOrigin.BORN


async def are_kin(session: AsyncSession, first: EntityRow, second: EntityRow, scope: KinScope) -> bool:
    for role in SCOPE_ROLES[scope]:
        if second.id in await kin_by_role(session, first.id, role):
            return True
    if scope is not KinScope.GROUP:
        return False
    mine = select(KinGroupMemberRow.group_id).where(KinGroupMemberRow.member_node_id == first.id)
    shared = await session.scalar(
        select(KinGroupMemberRow.group_id).where(KinGroupMemberRow.member_node_id == second.id, KinGroupMemberRow.group_id.in_(mine)).limit(1)
    )
    return shared is not None


async def contexts_of(session: AsyncSession, first: EntityRow, second: EntityRow, affair: bool) -> set[RelationContext]:
    found: set[RelationContext] = set()
    if await marriage_between(session, first.id, second.id) is not None:
        found.add(RelationContext.WITHIN_UNION)
    elif affair:
        found.add(RelationContext.OUTSIDE_UNION)
    else:
        found.add(RelationContext.BEFORE_UNION)
    mine, theirs = await people_of(session, first), await people_of(session, second)
    if mine is not None and theirs is not None and mine.id != theirs.id:
        found.add(RelationContext.WITH_OTHER_KINDS)
    if await made(session, first) or await made(session, second):
        found.add(RelationContext.WITH_MADE_MINDS)
    if sexes_fixed(await system_of(session, first)) and sex_of(first) == sex_of(second):
        found.add(RelationContext.BETWEEN_ANY_SEXES)
    return found


async def ruling_norm(session: AsyncSession, first: EntityRow, second: EntityRow, affair: bool) -> IntimacyNormRow | None:
    folk = await people_of(session, first)
    if folk is None:
        return None
    rows = {row.context: row for row in await session.scalars(select(IntimacyNormRow).where(IntimacyNormRow.people_entity_id == folk.id))}
    contexts = await contexts_of(session, first, second, affair)
    kin = rows.get(RelationContext.WITH_KIN)
    if kin is not None and await are_kin(session, first, second, kin.kin_scope or KinScope.CLOSE):
        contexts.add(RelationContext.WITH_KIN)
    found = [rows[context] for context in sorted(contexts) if context in rows]
    return min(found, key=lambda row: STANCES.index(row.stance)) if found else None


async def outside_union_weight(session: AsyncSession, spouse: EntityRow) -> float:
    folk = await people_of(session, spouse)
    row = await session.get(IntimacyNormRow, (folk.id, RelationContext.OUTSIDE_UNION)) if folk is not None else None
    return OUTSIDE_WEIGHTS[row.stance] if row is not None else 1.0


async def lover_pairs(ctx: TickContext) -> list[tuple[EntityRow, EntityRow, RelationshipRow]]:
    rows = await ctx.session.scalars(
        select(RelationshipRow)
        .where(RelationshipRow.romance >= ctx.rules.social.lover_at // 2, RelationshipRow.holder_node_id < RelationshipRow.subject_node_id)
        .order_by(RelationshipRow.id)
    )
    pairs: list[tuple[EntityRow, EntityRow, RelationshipRow]] = []
    for row in list(rows):
        if RelationType.LOVER.value not in row.kinds or held(row.holder_node_id) or held(row.subject_node_id):
            continue
        first, second = await ctx.session.get(EntityRow, row.holder_node_id), await ctx.session.get(EntityRow, row.subject_node_id)
        if first is None or second is None or first.status is not EntityStatus.CANON or second.status is not EntityStatus.CANON:
            continue
        pairs.append((first, second, row))
    return pairs


async def lose_honour(ctx: TickContext, being: EntityRow, amount: int, key: str) -> None:
    profile = await ctx.session.get(MortalProfileRow, being.id)
    if profile is None or "honour" in (profile.locked or []):
        return
    with explaining():
        term(key, -amount, source_node_id=being.id)
        profile.honour = clamp_int(profile.honour - amount, 0, PERCENT)


async def shun(ctx: TickContext, being: EntityRow) -> None:
    for kin_id in await parents_of(ctx.session, being.id):
        view = await ensure_relation(ctx.session, kin_id, being.id, ctx.epoch)
        if view is not None and not held(kin_id):
            shift(ctx.rules, view, ctx.epoch, friendship=-ctx.rules.unions_and_birth.shun_relation)


async def sanction(ctx: TickContext, norm: IntimacyNormRow, pair: tuple[EntityRow, EntityRow], tally: NormTally) -> None:
    if norm.sanction is NormSanction.NONE or norm.enforcer is NormEnforcer.NONE:
        return
    table = ctx.rules.unions_and_birth
    for being in pair:
        force = ENFORCER_FORCE_PCT[norm.enforcer]
        if norm.sanction is NormSanction.SHAMING:
            await lose_honour(ctx, being, round_half_up(table.scandal_shame * force / PERCENT), "unions_and_birth.scandal_shame")
        elif norm.sanction is NormSanction.FINE:
            await shift_points(ctx.session, being, -round_half_up(table.sanction_fine * force / PERCENT))
        elif norm.sanction is NormSanction.SHUNNING:
            await shun(ctx, being)
        elif norm.sanction is NormSanction.EXILE:
            being.location_id = None
            await add_flag(ctx.session, being.id, EntityFlag.EXILE, ctx.epoch)
    await record(
        ctx,
        "unions.sanction",
        roles={IncidentRole.ACTOR: pair[0].id, IncidentRole.TARGET: pair[1].id},
        facts={"sanction": norm.sanction, "enforcer": norm.enforcer, "context": norm.context},
        place=pair[0].location_id,
    )
    tally.sanctions += 1


async def refuge(ctx: TickContext, being: EntityRow) -> EntityRow | None:
    folk = await people_of(ctx.session, being)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == being.world_id)
        .order_by(EntityRow.id)
    )
    for town in towns:
        theirs = await people_of(ctx.session, town)
        if folk is None or theirs is None or theirs.id != folk.id:
            return town
    return None


async def flee(ctx: TickContext, pair: tuple[EntityRow, EntityRow], tally: NormTally) -> bool:
    if not ctx.rng(f"union_flight.{pair[0].id}.{pair[1].id}.{ctx.epoch}").chance(ctx.rules.unions_and_birth.persecution_flight_pct):
        return False
    town = await refuge(ctx, pair[0])
    if town is None:
        return False
    for being in pair:
        being.location_id = town.id
    tally.fled += 1
    return True


async def judge_pair(ctx: TickContext, first: EntityRow, second: EntityRow, row: RelationshipRow, tally: NormTally) -> None:
    norm = await ruling_norm(ctx.session, first, second, row.affair)
    if norm is None or norm.stance not in SANCTIONED:
        return
    table = ctx.rules.unions_and_birth
    odds = table.scandal_pct * (2 if norm.stance is NormStance.FORBIDDEN else 1)
    if not ctx.rng(f"union_scandal.{first.id}.{second.id}.{ctx.epoch}").chance(min(PERCENT, odds)):
        if norm.stance is NormStance.FORBIDDEN:
            await keep_secret(ctx, first.id, IntrigueSecret.AFFAIR, about_id=second.id, known_by=(second.id,), source="forbidden_relation")
            tally.hidden += 1
        return
    for being in (first, second):
        await lose_honour(ctx, being, table.scandal_shame, "unions_and_birth.scandal_shame")
    fled = norm.stance is NormStance.FORBIDDEN and await flee(ctx, (first, second), tally)
    await record(
        ctx,
        "unions.scandal",
        roles={IncidentRole.ACTOR: first.id, IncidentRole.TARGET: second.id},
        facts={"context": norm.context, "stance": norm.stance, "fled": int(fled)},
        place=first.location_id,
    )
    tally.scandals += 1
    if not fled:
        await sanction(ctx, norm, (first, second), tally)


def target_stance(current: NormStance, strict: int) -> NormStance:
    if current is NormStance.FORBIDDEN:
        return NormStance.DISCOURAGED if strict <= 0 else current
    if current is NormStance.HONOURED:
        return NormStance.ACCEPTED if strict >= 0 else current
    if strict >= STRICT_AT:
        return NormStance.DISCOURAGED
    if strict <= -STRICT_AT:
        return NormStance.ACCEPTED
    return NormStance.TOLERATED


async def drift_norms(ctx: TickContext, tally: NormTally) -> None:
    for row in list(await ctx.session.scalars(select(IntimacyNormRow).order_by(IntimacyNormRow.people_entity_id, IntimacyNormRow.context))):
        if held(row.people_entity_id) or "stance" in (row.locked or []):
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, row.people_entity_id)
        strict = sum(values.get(axis, 0) for axis in STRICT_AXES) // len(STRICT_AXES)
        target = target_stance(row.stance, strict)
        if target is row.stance or not ctx.rng(f"norm_drift.{row.people_entity_id}.{row.context.value}.{ctx.epoch}").chance(
            ctx.rules.unions_and_birth.norm_drift_pct
        ):
            continue
        step = 1 if STANCES.index(target) > STANCES.index(row.stance) else -1
        before, row.stance, row.since_epoch = row.stance, STANCES[STANCES.index(row.stance) + step], ctx.epoch
        await record(
            ctx,
            "unions.norm_changed",
            roles={IncidentRole.SUBJECT: row.people_entity_id},
            facts={"context": row.context, "before": before, "after": row.stance},
        )
        tally.changed += 1


async def keep_norms(ctx: TickContext, tally: NormTally) -> None:
    for first, second, row in await lover_pairs(ctx):
        await judge_pair(ctx, first, second, row, tally)
    await drift_norms(ctx, tally)
