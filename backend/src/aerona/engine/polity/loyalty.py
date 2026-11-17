from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import PolityLoyaltyRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import GRIEVANCE_PARTS, LoyaltyPart
from aerona.engine.belonging.effects import identity_loyalty, realm_fault
from aerona.engine.belonging.mockery import suppressed
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import Values, values_for
from aerona.engine.mind.space import value_distance
from aerona.engine.polity.book import Realm
from aerona.engine.polity.trials import injustices
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, bond_exists
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import relation
from aerona.rules.registry import Rules

RECENT_EPOCHS = 3
MIDDLE = PERCENT // 2


async def member_values(ctx: TickContext, member: EntityRow) -> Values:
    found = await values_for(ctx.session, member.id)
    if found:
        return dict(found)
    people = await people_of(ctx.session, member)
    return dict(await culture_of(ctx.session, people.id)) if people is not None else {}


async def victories(ctx: TickContext, realm: Realm) -> int:
    members = [realm.entity.id, *realm.members]
    statement = select(WarRow.id).where(WarRow.ended_epoch >= ctx.epoch - RECENT_EPOCHS, WarRow.victor_entity_id.in_(members))
    return len(list(await ctx.session.scalars(statement)))


def mean_satisfaction(society: CommunitySocietyRow | None) -> int:
    if society is None:
        return MIDDLE
    weights = {social_class: society.share(social_class) for social_class in SocialClass if society.share(social_class) > 0}
    whole = sum(weights.values())
    if whole <= 0:
        return MIDDLE
    return round_half_up(sum(society.satisfaction(social_class) * weight for social_class, weight in weights.items()) / whole)


async def loyalty_parts(ctx: TickContext, realm: Realm, member: EntityRow, won: int) -> dict[LoyaltyPart, int]:
    table = ctx.rules.realm_loyalty
    parts: dict[LoyaltyPart, int] = {}
    tribute = len(await active_bonds(ctx.session, [BondKind.PAYS_TRIBUTE], sources=[member.id]))
    if tribute:
        parts[LoyaltyPart.TRIBUTE] = tribute * table.tribute_grievance
    if realm.profile.war_weariness:
        parts[LoyaltyPart.WEARINESS] = round_half_up(realm.profile.war_weariness * table.weariness_grievance_pct / PERCENT)
    rulers = {realm.entity.id, *(item for item in (realm.profile.core_entity_id, realm.ruler_id) if item is not None)}
    conquered = await ctx.session.scalar(
        select(MemoryRow.id)
        .where(MemoryRow.holder_node_id == member.id, MemoryRow.kind == MemoryKind.CONQUERED_US, MemoryRow.subject_node_id.in_(list(rulers)))
        .limit(1)
    )
    if conquered is not None:
        parts[LoyaltyPart.CONQUEST] = table.conquest_grievance
    town = await ctx.session.get(SettlementProfileRow, member.id)
    if town is not None and town.tax_rate > table.tax_ordinary:
        parts[LoyaltyPart.TAX] = round_half_up((town.tax_rate - table.tax_ordinary) * table.tax_grievance_pct / PERCENT)
    routes = len(await active_bonds(ctx.session, [BondKind.TRADES_WITH], sources=[member.id])) + len(
        await active_bonds(ctx.session, [BondKind.TRADES_WITH], targets=[member.id])
    )
    if routes:
        parts[LoyaltyPart.ROUTES] = min(table.route_benefit_cap, routes * table.route_benefit)
    if won:
        parts[LoyaltyPart.VICTORIES] = won * table.victory_benefit
    faith = realm.profile.state_religion_id
    if faith is not None and await bond_exists(ctx.session, member.id, faith, BondKind.WORSHIPS):
        parts[LoyaltyPart.FAITH] = table.faith_benefit
    prosperity = stat(member, "prosperity")
    if prosperity is not None and prosperity > MIDDLE:
        parts[LoyaltyPart.PROSPERITY] = round_half_up((prosperity - MIDDLE) * table.prosperity_benefit_pct / PERCENT)
    wronged = await injustices(ctx, member.id)
    if wronged:
        parts[LoyaltyPart.INJUSTICE] = wronged * ctx.rules.trials.injustice_grievance
    fault = await realm_fault(ctx.session, ctx.rules, sorted(realm.members))
    cohesion, separatism = await identity_loyalty(ctx.session, ctx.rules, realm.entity.id, member.id, ruler_id=realm.ruler_id, fault=fault)
    if cohesion:
        parts[LoyaltyPart.IDENTITY] = cohesion
    if separatism:
        parts[LoyaltyPart.SEPARATISM] = separatism
    silenced = await suppressed(ctx.session, ctx.rules, realm.entity.id, ctx.epoch)
    if silenced:
        parts[LoyaltyPart.SUPPRESSION] = silenced
    return parts


def loyalty_of(rules: Rules, distance: int, grievances: int, benefits: int, satisfaction: int) -> int:
    table = rules.realm_loyalty
    return clamp_int(round_half_up(table.base - distance * table.distance_pct / PERCENT - grievances + benefits + satisfaction), 0, PERCENT)


def satisfaction_term(rules: Rules, mood: int) -> int:
    return round_half_up((mood - MIDDLE) * rules.realm_loyalty.satisfaction_pct / PERCENT)


async def member_loyalty(ctx: TickContext, realm: Realm, member: EntityRow, won: int) -> PolityLoyaltyRow:
    row = await ctx.session.get(PolityLoyaltyRow, (realm.entity.id, member.id))
    if row is None:
        row = PolityLoyaltyRow(polity_entity_id=realm.entity.id, member_entity_id=member.id, parts={}, locked=[], loyalty=MIDDLE, epoch=ctx.epoch)
        ctx.session.add(row)
    before = row.loyalty
    ruler = await values_for(ctx.session, realm.ruler_id) if realm.ruler_id is not None else {}
    mine = await member_values(ctx, member)
    parts = await loyalty_parts(ctx, realm, member, won)
    row.value_distance = value_distance(mine, ruler) if mine and ruler else 0
    if "grievances" not in row.locked:
        row.grievances = sum(value for part, value in parts.items() if part in GRIEVANCE_PARTS)
    if "benefits" not in row.locked:
        row.benefits = sum(value for part, value in parts.items() if part not in GRIEVANCE_PARTS)
    row.satisfaction = satisfaction_term(ctx.rules, mean_satisfaction(await ctx.session.get(CommunitySocietyRow, member.id)))
    row.parts = {part.value: value for part, value in parts.items()}
    if "loyalty" not in row.locked:
        row.loyalty = loyalty_of(ctx.rules, row.value_distance, row.grievances, row.benefits, row.satisfaction)
    row.epoch = ctx.epoch
    if row.loyalty < ctx.rules.realm_loyalty.wavering_loyalty <= before:
        await record(
            ctx,
            "loyalty.wavering",
            roles={IncidentRole.SUBJECT: member.id, IncidentRole.AUTHORITY: realm.entity.id},
            facts={"loyalty": row.loyalty, "before": before, "grievances": row.grievances, "benefits": row.benefits},
            terms=[Term(f"loyalty.{part.value}", value) for part, value in parts.items()],
            place=member.id,
        )
    return row


def autonomy_pull(rules: Rules, loyalty: int) -> int:
    return round_half_up((MIDDLE - loyalty) * rules.realm_loyalty.autonomy_pct / PERCENT)


async def loyalty_autonomy(ctx: TickContext, realm: Realm, member: EntityRow | None) -> int:
    if member is None:
        return 0
    row = await member_loyalty(ctx, realm, member, await victories(ctx, realm))
    return autonomy_pull(ctx.rules, row.loyalty)


async def vassal_loyalty(ctx: TickContext, vassal_id: int, overlord_id: int, tribute_pct: int) -> int:
    table = ctx.rules.realm_loyalty
    vassal = await ctx.session.get(EntityRow, vassal_id)
    lord_values = await values_for(ctx.session, overlord_id)
    mine = await member_values(ctx, vassal) if vassal is not None else {}
    distance = value_distance(mine, lord_values) if mine and lord_values else 0
    regard = await relation(ctx.session, ctx.rules, vassal_id, overlord_id)
    grievances = round_half_up(tribute_pct * table.vassal_tribute_pct / PERCENT) + round_half_up(max(0, -regard) * table.vassal_regard_pct / PERCENT)
    benefits = round_half_up(max(0, regard) * table.vassal_regard_pct / PERCENT)
    mood = satisfaction_term(ctx.rules, mean_satisfaction(await ctx.session.get(CommunitySocietyRow, vassal_id)))
    return loyalty_of(ctx.rules, distance, grievances, benefits, mood)
