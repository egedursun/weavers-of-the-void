from collections.abc import Mapping

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civics import OFFICE_GATES, OFFICE_LEVELS
from aerona.catalog.life.polity import CLAIM_STRENGTHS, COUNCIL, DEFAULT_POWERS, OFFICE_SKILLS, POWER_SKILLS, SUCCESSION_LINE_SUCCESSION_RULES
from aerona.catalog.life_traits import OFFICE_KIND_TRAITS, having
from aerona.catalog.reproduction import kind_of_sex, sex_rule_fit
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.read_memo import memoized
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow, OfficeHistoryRow, OfficeRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import RoleKind
from aerona.domain.enums.customs import MemberRight
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand
from aerona.domain.enums.life_traits import OfficeKindTrait
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import MemoryKind, SkillKind, TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis, CoupCause, LawKind, OathBreach, OathKind, OfficeKind, OfficePower, SexRule, SuccessionRule, TreatyStatus
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.settlement import TIER_ORDER
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.storyteller import SpontaneousKind
from aerona.domain.enums.war import WarSide
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.belonging.peers import companions_of
from aerona.engine.body.customs import people_id_of
from aerona.engine.body.marks import marked
from aerona.engine.collective.roles import RANK_PREFERRED, freed_rank, role_rank
from aerona.engine.context import TickContext
from aerona.engine.customs.rights import has_right
from aerona.engine.cycles.book import stress_factor
from aerona.engine.cycles.sides import PAIRED, drawn_side, second_sex, system_of_people
from aerona.engine.factions.privileges import reserved_class
from aerona.engine.folkways.biases import lean
from aerona.engine.interconnect.causes import succession_incident
from aerona.engine.intrigue.favours import hook_on, owe, use_hook
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.civics import reaches, realm_allows, realm_levels
from aerona.engine.military.causes import press_claim_war
from aerona.engine.military.support import new_side
from aerona.engine.mind.book import traits_of
from aerona.engine.mortal.kin import children_of, siblings_of
from aerona.engine.polity.book import Realm, RealmBook, sex_of
from aerona.engine.polity.formation import set_ruler
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.oaths import break_on, swear
from aerona.engine.polity.repute import shift_infamy
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.knowledge import BranchLevels
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, bond_exists, close, connect, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.regime.book import appointment_weights, coup_factor, credential_rank, plotter
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import war_event
from aerona.engine.settlement.book import towns
from aerona.engine.settlement.districts import office_tier
from aerona.engine.storyteller.pace import paced
from aerona.rules.registry import Rules

MANY_SEATS = having(OFFICE_KIND_TRAITS, OfficeKindTrait.MANY_SEATS)
POWER_VALUES = frozenset(item.value for item in OfficePower)


def powers_of(office: OfficeRow) -> set[OfficePower]:
    if office.powers:
        return {OfficePower(item) for item in office.powers if item in POWER_VALUES}
    return set(DEFAULT_POWERS.get(office.kind, ()))


async def power_skill(ctx: TickContext, office: OfficeRow, power: OfficePower) -> float:
    holder = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
    if holder is None:
        return 0.0
    score = await skill_score(ctx, holder, POWER_SKILLS[power])
    return min(1.0, score / max(1, ctx.rules.government.skill_full))


async def wielders(ctx: TickContext, realm: Realm, power: OfficePower) -> list[tuple[OfficeRow, float]]:
    found = []
    for office in realm.offices:
        if office.holder_entity_id is not None and power in powers_of(office):
            found.append((office, await power_skill(ctx, office, power)))
    return found


async def best_skill(ctx: TickContext, realm: Realm, power: OfficePower) -> float:
    return max((skill for _, skill in await wielders(ctx, realm, power)), default=0.0)


async def subjects(ctx: TickContext, realm: Realm) -> list[EntityRow]:
    members = list(realm.members)
    if not members:
        return []
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, members)
    )
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def skill_score(ctx: TickContext, mortal: EntityRow, office: OfficeKind) -> float:
    skills, attribute = OFFICE_SKILLS[office]
    return await skill_sum(ctx.session, mortal.id, tuple(skills)) * 5 + (stat(mortal, attribute) or 0) + (mortal.importance or 0) / 10


@memoized(SkillRow)
async def skill_sum(session: AsyncSession, mortal_id: int, skills: tuple[SkillKind, ...]) -> int:
    return sum(await session.scalars(select(SkillRow.level).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill.in_(list(skills)))))


def adult(ctx: TickContext, mortal: EntityRow) -> bool:
    return (stat(mortal, "age") or 0) >= ctx.rules.succession.regency_age


KEPT_OFFICES = having(OFFICE_KIND_TRAITS, OfficeKindTrait.SEATS_KEPT)


async def pressed_candidate(ctx: TickContext, realm: Realm, candidates: list[EntityRow]) -> EntityRow | None:
    if realm.ruler_id is None:
        return None
    for mortal in candidates:
        hook = await hook_on(ctx, mortal.id, realm.ruler_id)
        if hook is not None and await use_hook(ctx, hook, HookDemand.APPOINTMENT):
            return mortal
    return None


async def appoint(ctx: TickContext, realm: Realm, office: OfficeRow, holder: EntityRow | None, *, by_id: int | None, reason: str) -> None:
    if holder is not None and ctx.rules.citizenship.rightless_office and not await has_right(ctx.session, holder.id, MemberRight.OFFICE, realm.entity.id):
        return
    kept = await reserved_class(ctx.session, realm.entity.id)
    if holder is not None and kept is not None and holder.social_class is not kept and office.kind not in KEPT_OFFICES:
        return
    if office.holder_entity_id is not None and office.id is not None:
        ctx.session.add(
            OfficeHistoryRow(office_id=office.id, holder_entity_id=office.holder_entity_id, from_epoch=office.since_epoch, to_epoch=ctx.epoch, reason=reason)
        )
    office.holder_entity_id = holder.id if holder is not None else None
    office.appointed_by_entity_id = by_id
    office.since_epoch = ctx.epoch
    if holder is not None and ctx.rules.oaths.fealty_on_office and realm.ruler_id is not None and holder.id != realm.ruler_id:
        await swear(ctx, holder, OathKind.FEALTY, recipient_id=realm.ruler_id, note_text=f"as {spoken(office.kind)} of {realm.entity.name}")
    if holder is not None and ctx.rules.oaths.silence_on_office and OfficePower.SPY in powers_of(office):
        await swear(ctx, holder, OathKind.SILENCE, recipient_id=realm.entity.id, note_text="the secrets of the realm")


def largest_tier(book: RealmBook, region: int, held_towns: Mapping[int, SettlementProfileRow]) -> int:
    return max((TIER_ORDER.index(held_towns[place].size_tier) for place in book.atlas.communities_in(region) if place in held_towns), default=0)


def province_seats(book: RealmBook, realm: Realm) -> list[int]:
    capital_region = book.atlas.top_region(realm.profile.capital_entity_id or -1)
    seats: dict[str, int] = {}
    for region, row in sorted(realm.territory.items()):
        seats.setdefault(row.province or str(region), region)
    return sorted(region for region in seats.values() if region != capital_region)


async def embassy_targets(ctx: TickContext, book: RealmBook, realm: Realm) -> list[int]:
    core = realm.profile.core_entity_id
    if core is None or realm.profile.tier < ctx.rules.realm_tiers.embassies:
        return []
    scored = []
    for other in book.realms.values():
        other_core = other.profile.core_entity_id
        if other.entity.id == realm.entity.id or other_core is None or other.entity.world_id != realm.entity.world_id:
            continue
        scored.append((await relation(ctx.session, ctx.rules, core, other_core), other.entity.id))
    return [realm_id for _, realm_id in sorted(scored, key=lambda item: (-item[0], item[1]))[: ctx.rules.government.embassy_count]]


def wanted_offices(
    book: RealmBook, realm: Realm, embassies: list[int], rules: Rules, held_towns: Mapping[int, SettlementProfileRow], *, subjects: int
) -> list[tuple[OfficeKind, int | None, int | None]]:
    seat = held_towns.get(realm.profile.capital_entity_id or -1)
    seat_tier = TIER_ORDER.index(seat.size_tier) if seat is not None else 0
    extra = max(0, subjects) // rules.scale.council_seat_people
    wanted: list[tuple[OfficeKind, int | None, int | None]] = [
        (kind, None, None) for kind in COUNCIL if seat_tier >= office_tier(rules, kind) for _ in range(1 + (extra if kind in MANY_SEATS else 0))
    ]
    if seat_tier >= office_tier(rules, OfficeKind.JESTER):
        wanted.append((OfficeKind.JESTER, None, None))
    if realm.profile.tier >= rules.realm_tiers.provinces:
        wanted.extend(
            (OfficeKind.GOVERNOR, region, None)
            for region in province_seats(book, realm)
            if largest_tier(book, region, held_towns) >= office_tier(rules, OfficeKind.GOVERNOR)
        )
    wanted.extend((OfficeKind.AMBASSADOR, None, target) for target in embassies)
    return wanted


async def staff(ctx: TickContext, book: RealmBook, realm: Realm, occupied: set[int]) -> int:
    people = [mortal for mortal in await subjects(ctx, realm) if adult(ctx, mortal) and mortal.id != realm.ruler_id]
    filled = 0
    embassies = await embassy_targets(ctx, book, realm)
    for seat in list(realm.offices):
        recalled = seat.kind is OfficeKind.AMBASSADOR and seat.target_entity_id not in embassies
        if recalled and seat.holder_entity_id is not None and "offices" not in realm.profile.locked and "holder" not in seat.locked:
            await appoint(ctx, realm, seat, None, by_id=realm.ruler_id, reason="the embassy was recalled")
    opened: dict[OfficeKind, bool] = {}
    levels: dict[int, BranchLevels] | None = None
    matched: set[int] = set()
    for kind, region, target in wanted_offices(book, realm, embassies, ctx.rules, await towns(ctx.session), subjects=stat_or(realm.entity, "subjects", 0)):
        office = next(
            (row for row in realm.offices if row.kind is kind and row.region_entity_id == region and row.target_entity_id == target and row.id not in matched),
            None,
        )
        if office is None and kind not in opened:
            gate = OFFICE_LEVELS.get(kind)
            allowed = await realm_allows(ctx.session, realm, OFFICE_GATES.get(kind))
            if allowed and gate is not None and levels is None:
                levels = await realm_levels(ctx.session, realm)
            opened[kind] = allowed and reaches(levels, realm, gate)
        if office is None and not opened[kind]:
            continue
        if office is None:
            office = OfficeRow(
                polity_entity_id=realm.entity.id,
                kind=kind,
                region_entity_id=region,
                target_entity_id=target,
                since_epoch=ctx.epoch,
                powers=[power.value for power in DEFAULT_POWERS.get(kind, ())],
                locked=[],
            )
            ctx.session.add(office)
            realm.offices.append(office)
            await ctx.session.flush()
        matched.add(office.id)
        holder = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
        if holder is not None and holder.status is EntityStatus.CANON:
            occupied.add(holder.id)
            continue
        if "offices" in realm.profile.locked or "holder" in office.locked:
            continue
        candidates = [mortal for mortal in people if mortal.id not in occupied]
        if not candidates:
            continue
        weights = await appointment_weights(ctx.session, ctx.rules, realm.entity.id, realm.ruler_id, [mortal.id for mortal in candidates])
        friends = await companions_of(ctx, realm.ruler_id)
        bonus = ctx.rules.peer_groups.companion_weight
        scores = {mortal.id: await skill_score(ctx, mortal, kind) + weights[mortal.id] + (bonus if mortal.id in friends else 0) for mortal in candidates}
        best = max(candidates, key=lambda mortal: (scores[mortal.id], -mortal.id))
        best = await pressed_candidate(ctx, realm, candidates) or best
        await appoint(ctx, realm, office, best, by_id=realm.ruler_id, reason="the seat was empty")
        occupied.add(best.id)
        filled += 1
    return filled


async def purge(ctx: TickContext, realm: Realm) -> int:
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None or TraitKind.PARANOID not in await traits_of(ctx.session, ruler.id) or "offices" in realm.profile.locked:
        return 0
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == ruler.id).limit(1))
    kin = set(await ctx.session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house))) if house else set()
    purged = 0
    for office in realm.offices:
        if office.kind is OfficeKind.RULER or office.holder_entity_id is None or office.holder_entity_id in kin:
            continue
        if ctx.rng(f"purge.{realm.entity.id}.{office.id}.{ctx.epoch}").chance(ctx.rules.government.purge_paranoia):
            await appoint(ctx, realm, office, None, by_id=ruler.id, reason="purged by a fearful ruler")
            purged += 1
    return purged


async def kin(ctx: TickContext, ruler: EntityRow) -> tuple[list[EntityRow], list[EntityRow], list[EntityRow]]:
    children = [child for child_id in await children_of(ctx.session, ruler.id) if (child := await living_mortal(ctx, child_id)) is not None]
    grandchildren: list[EntityRow] = []
    for child in children:
        for grandchild_id in await children_of(ctx.session, child.id):
            found = await living_mortal(ctx, grandchild_id)
            if found is not None:
                grandchildren.append(found)
    siblings = [sibling for sibling_id in await siblings_of(ctx.session, ruler.id) if (sibling := await living_mortal(ctx, sibling_id)) is not None]
    return children, grandchildren, siblings


async def living_mortal(ctx: TickContext, node_id: int) -> EntityRow | None:
    found = await living_entity(ctx.session, node_id)
    return found if found is not None and found.entity_type is EntityType.MORTAL else None


RANK_SPAN = 10


def sex_rank(rule: SexRule, mortal: EntityRow) -> int | None:
    sex = sex_of(mortal)
    fit = sex_rule_fit(rule, kind_of_sex(sex))
    if fit is None:
        return None
    return 0 if fit >= 1 else 1


async def whole(ctx: TickContext, mortal: EntityRow) -> bool:
    found = await ctx.session.scalar(select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal.id, marked()).limit(1))
    return found is None


async def second_side_of(ctx: TickContext, ruler: EntityRow) -> str:
    people_id = await people_id_of(ctx.session, ruler)
    system = await system_of_people(ctx.session, people_id)
    return second_sex(system) if system is not None else PAIRED.get(drawn_side(people_id or ruler.id), SexKind.BOTH).value


async def succession_line(ctx: TickContext, realm: Realm, laws: LawBook) -> list[EntityRow]:
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        return []
    polity = realm.entity.id
    rule = SuccessionRule(str(laws.param(polity, LawKind.SUCCESSION_RULE, "rule") or SuccessionRule.PRIMOGENITURE.value))
    sex_rule = SexRule(str(laws.param(polity, LawKind.SUCCESSION_RULE, "sex_rule") or SexRule.ANY.value))
    wholeness = bool(laws.param(polity, LawKind.SUCCESSION_RULE, "wholeness_required"))
    min_age = int(laws.param(polity, LawKind.SUCCESSION_RULE, "min_age") or 0)
    children, grandchildren, siblings = await kin(ctx, ruler)
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == ruler.id).limit(1))
    housemates: list[EntityRow] = []
    if house is not None:
        for member_id in await ctx.session.scalars(select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house)):
            found = await living_entity(ctx.session, member_id)
            if found is not None and found.entity_type is EntityType.MORTAL and found.id != ruler.id:
                housemates.append(found)
    pools = {
        SuccessionRule.PRIMOGENITURE: [*children, *grandchildren, *siblings],
        SuccessionRule.SENIORITY: [*siblings, *children, *housemates],
        SuccessionRule.ELECTIVE: [*housemates, *children, *siblings, *await subjects(ctx, realm)],
        SuccessionRule.TANISTRY: [*housemates, *children, *siblings],
        SuccessionRule.THROUGH_SECOND_LINE: [*[item for item in siblings if sex_of(item) == await second_side_of(ctx, ruler)], *grandchildren, *children],
        SuccessionRule.BY_COMBAT: [*children, *siblings, *housemates],
        SuccessionRule.DIVINE_CHOICE: [*children, *housemates, *siblings],
        SuccessionRule.ULTIMOGENITURE: [*sorted(children, key=lambda item: (stat(item, "age") or 0, item.id)), *grandchildren, *siblings],
        SuccessionRule.DESIGNATION: [*children, *housemates, *siblings, *grandchildren, *await subjects(ctx, realm)],
    }
    seen: set[int] = set()
    pool: list[EntityRow] = []
    for item in pools[rule]:
        if item.id not in seen:
            seen.add(item.id)
            pool.append(item)
    eligible = []
    for item in pool:
        rank = sex_rank(sex_rule, item)
        custom = await credential_rank(
            ctx.session,
            item.id,
            await freed_rank(ctx.session, ctx.rules, item, RoleKind.OFFICE, await role_rank(ctx.session, item, RoleKind.OFFICE)),
            RANK_PREFERRED,
        )
        if rank is None or custom is None or (wholeness and not await whole(ctx, item)):
            continue
        eligible.append((rank * RANK_SPAN + custom, item))
    grown = [entry for entry in eligible if (stat(entry[1], "age") or 0) >= min_age]
    eligible = grown or eligible
    table = ctx.rules.succession
    order = {item.id: index for index, item in enumerate(pool)}
    favour = await divine_favour(ctx, realm, [item for _, item in eligible]) if rule is SuccessionRule.DIVINE_CHOICE else {}
    named = await ctx.session.scalar(select(DesignatedHeirRow.heir_entity_id).where(DesignatedHeirRow.ruler_entity_id == ruler.id))

    def key(entry: tuple[int, EntityRow]) -> tuple[float, ...]:
        rank, item = entry
        age = stat(item, "age") or 0
        if rule in SUCCESSION_LINE_SUCCESSION_RULES:
            return (order[item.id] >= len(children), rank, age if rule is SuccessionRule.ULTIMOGENITURE else -age, item.id)
        if rule is SuccessionRule.SENIORITY:
            return (rank, -age, item.id)
        if rule is SuccessionRule.ELECTIVE:
            return (
                rank,
                -((stat(item, "charisma") or 0) * table.elective_charisma_pct + (item.importance or 0) * (PERCENT - table.elective_charisma_pct)),
                item.id,
            )
        if rule is SuccessionRule.BY_COMBAT:
            return (
                rank,
                -((stat(item, "strength") or 0) * table.combat_strength_pct + (stat(item, "agility") or 0) * (PERCENT - table.combat_strength_pct)),
                item.id,
            )
        if rule is SuccessionRule.THROUGH_SECOND_LINE:
            return (order[item.id], item.id)
        merit = (stat(item, "strength") or 0) + (stat(item, "charisma") or 0) + (item.importance or 0)
        return (rank, -(favour.get(item.id, 0) * PERCENT + merit), item.id)

    def chosen(entry: tuple[int, EntityRow]) -> tuple[float, ...]:
        rank, item = entry
        return (0 if item.id == named else 1, rank, -((stat(item, "intellect") or 0) + (stat(item, "charisma") or 0) + (item.importance or 0)), item.id)

    return [item for _, item in sorted(eligible, key=chosen if rule is SuccessionRule.DESIGNATION else key)]


async def divine_favour(ctx: TickContext, realm: Realm, people: list[EntityRow]) -> dict[int, int]:
    weight = ctx.rules.succession.patron_favour
    patron = realm.profile.patron_son_id
    son = await ctx.session.get(SonRow, patron) if patron is not None else None
    favour: dict[int, int] = {}
    for item in people:
        score = 0
        if son is not None and await bond_exists(ctx.session, item.id, son.id, BondKind.WORSHIPS):
            score += weight
        if son is not None and item.creator_son_id == son.id:
            score += weight * 2
        if await has_flag(ctx.session, item.id, EntityFlag.CHOSEN):
            score += weight
        favour[item.id] = score
    return favour


async def favoured_heir(ctx: TickContext, ruler_id: int, line: list[EntityRow]) -> EntityRow | None:
    if len(line) < 2:
        return line[0] if line else None
    swayed = max(0.0, 1 - await lean(ctx, ruler_id, BiasedDecision.SUCCESSION))
    return line[1] if ctx.rng(f"heir_sway.{ruler_id}.{ctx.epoch}").chance(round(swayed * PERCENT)) else line[0]


async def name_heir(ctx: TickContext, realm: Realm, line: list[EntityRow]) -> EntityRow | None:
    if realm.ruler_id is None or "heir" in realm.profile.locked:
        return None
    heir = await favoured_heir(ctx, realm.ruler_id, line)
    await ctx.session.execute(delete(DesignatedHeirRow).where(DesignatedHeirRow.ruler_entity_id == realm.ruler_id))
    designate = next((row for row in realm.offices if row.kind is OfficeKind.HEIR_DESIGNATE), None)
    if heir is None:
        if designate is not None:
            designate.holder_entity_id = None
        return None
    ctx.session.add(DesignatedHeirRow(ruler_entity_id=realm.ruler_id, heir_entity_id=heir.id, epoch=ctx.epoch))
    if designate is None:
        designate = OfficeRow(polity_entity_id=realm.entity.id, kind=OfficeKind.HEIR_DESIGNATE, since_epoch=ctx.epoch, powers=[])
        ctx.session.add(designate)
        realm.offices.append(designate)
    if designate.holder_entity_id != heir.id:
        designate.holder_entity_id = heir.id
        designate.since_epoch = ctx.epoch
        await owe(ctx, heir.id, realm.ruler_id, FavourOrigin.SUCCESSION_SUPPORT, ctx.rules.intrigue.succession_favour)
        await claim_by_rule(ctx, realm, heir)
    return heir


async def claim_by_rule(ctx: TickContext, realm: Realm, heir: EntityRow) -> None:
    laws = await LawBook.load(ctx.session)
    rule = SuccessionRule(str(laws.param(realm.entity.id, LawKind.SUCCESSION_RULE, "rule") or SuccessionRule.PRIMOGENITURE.value))
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        return
    if rule is SuccessionRule.ELECTIVE:
        await make_claim(ctx, realm, heir, ClaimBasis.ELECTION, ctx.rules.claims.adopted_claim, backer=None)
        return
    if rule is not SuccessionRule.DESIGNATION:
        return
    children, grandchildren, siblings = await kin(ctx, ruler)
    blood = [*children, *grandchildren, *siblings]
    await record(
        ctx,
        "succession.designated",
        roles={IncidentRole.ACTOR: ruler.id, IncidentRole.SUCCESSOR: heir.id, IncidentRole.AUTHORITY: realm.entity.id},
    )
    if heir.id in {item.id for item in blood}:
        return
    await make_claim(ctx, realm, heir, ClaimBasis.ADOPTION, ctx.rules.claims.adopted_claim, backer=ruler.id)
    rival = next((item for item in blood if not held(item.id)), None)
    if rival is not None and ctx.rng(f"designation.contest.{realm.entity.id}.{heir.id}").chance(ctx.rules.succession.designation_contest_pct):
        await make_claim(ctx, realm, rival, ClaimBasis.INHERITANCE, ctx.rules.succession.claim_press_pct, backer=None)


async def make_claim(ctx: TickContext, realm: Realm, claimant: EntityRow, basis: ClaimBasis, strength: int, *, backer: int | None) -> ClaimRow | None:
    if held(claimant.id):
        return None
    found = await ctx.session.scalar(
        select(ClaimRow).where(
            ClaimRow.claimant_entity_id == claimant.id, ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.basis == basis, ClaimRow.ended_epoch.is_(None)
        )
    )
    if found is not None:
        return found
    row = ClaimRow(
        claimant_entity_id=claimant.id,
        polity_entity_id=realm.entity.id,
        basis=basis,
        strength=strength,
        backer_entity_id=backer,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        "claim.made",
        roles={IncidentRole.ACTOR: claimant.id, IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.PATRON: backer},
        facts={"basis": basis, "strength": strength},
    )
    return row


async def ensure_regent(ctx: TickContext, realm: Realm, ruler: EntityRow, occupied: set[int]) -> tuple[OfficeRow, EntityRow | None, bool]:
    office = next((row for row in realm.offices if row.kind is OfficeKind.REGENT), None)
    if office is None:
        office = OfficeRow(polity_entity_id=realm.entity.id, kind=OfficeKind.REGENT, since_epoch=ctx.epoch, powers=["rule"])
        ctx.session.add(office)
        realm.offices.append(office)
        await ctx.session.flush()
    regent = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
    if regent is not None:
        return office, regent, False
    people = [mortal for mortal in await subjects(ctx, realm) if adult(ctx, mortal) and mortal.id != ruler.id]
    if not people:
        return office, None, False
    scores = {mortal.id: await skill_score(ctx, mortal, OfficeKind.REGENT) for mortal in people}
    regent = max(people, key=lambda mortal: (scores[mortal.id], -mortal.id))
    await appoint(ctx, realm, office, regent, by_id=None, reason="the heir is a child")
    occupied.add(regent.id)
    return office, regent, True


async def regency(ctx: TickContext, realm: Realm, occupied: set[int]) -> str | None:
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        return None
    office = next((row for row in realm.offices if row.kind is OfficeKind.REGENT), None)
    if adult(ctx, ruler):
        if office is None or office.holder_entity_id is None:
            return None
        await appoint(ctx, realm, office, None, by_id=ruler.id, reason="the ruler came of age")
        return "ended"
    office, regent, fresh = await ensure_regent(ctx, realm, ruler, occupied)
    if regent is None or fresh:
        return "appointed" if fresh else None
    ambitious = TraitKind.AMBITIOUS in await traits_of(ctx.session, regent.id)
    ambition = await paced(ctx, realm.entity.world_id, SpontaneousKind.CLAIMANT, ctx.rules.succession.usurp_chance) if ambitious else 0.0
    ambition = await lagged(ctx, BalanceLoop.REGENCY, realm.entity.id, ambition, subject=regent.id)
    if ambition and ctx.rng(f"usurp.{realm.entity.id}.{ctx.epoch}").chance(ambition):
        await usurp(ctx, realm, regent, ruler)
        return "usurped"
    return None


async def usurp(ctx: TickContext, realm: Realm, usurper: EntityRow, ruler: EntityRow) -> None:
    await seize_throne(ctx, realm, usurper, CoupCause.REGENT)
    office = next((row for row in realm.offices if row.kind is OfficeKind.REGENT), None)
    if office is not None and office.holder_entity_id is not None:
        await appoint(ctx, realm, office, None, by_id=usurper.id, reason="the regent took power")


async def house_of(ctx: TickContext, mortal_id: int | None) -> HouseProfileRow | None:
    if mortal_id is None:
        return None
    house_id = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).limit(1))
    return await ctx.session.get(HouseProfileRow, house_id) if house_id is not None else None


async def backing(ctx: TickContext, claimant_id: int) -> int:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.kind == BondKind.MEMBER_OF,
            BondRow.state == BondState.ACTIVE,
            BondRow.source_node_id == claimant_id,
            EntityRow.entity_type == EntityType.FACTION,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    return sum(stat(faction, "strength") or 0 for faction in await ctx.session.scalars(statement))


async def support(ctx: TickContext, realm: Realm, claim: ClaimRow) -> tuple[int, int]:
    table = ctx.rules.succession
    rival = await house_of(ctx, claim.claimant_entity_id)
    crown = await house_of(ctx, realm.ruler_id)
    society = await ctx.session.get(CommunitySocietyRow, realm.profile.core_entity_id or -1)
    discontent = (PERCENT // 2 - society.satisfaction(SocialClass.NOBLE)) if society is not None else 0
    claimant_side = (
        claim.strength * getattr(ctx.rules.claims, CLAIM_STRENGTHS[claim.basis]) / PERCENT
        + (rival.prestige if rival is not None else 0) * table.house_support_pct / PERCENT
        + await backing(ctx, claim.claimant_entity_id) * table.faction_support_pct / PERCENT
        + discontent * table.opinion_support_pct / PERCENT
    )
    throne_side = realm.profile.legitimacy + (crown.prestige if crown is not None else 0) * table.house_support_pct / PERCENT
    return round_half_up(claimant_side), round_half_up(throne_side)


async def house_sides(ctx: TickContext, realm: Realm, war: WarRow, claimant_id: int, host_id: int) -> int:
    rival = await house_of(ctx, claimant_id)
    crown = await house_of(ctx, realm.ruler_id)
    officers = {office.holder_entity_id for office in realm.offices if office.holder_entity_id is not None}
    claimants = set(
        await ctx.session.scalars(select(ClaimRow.house_entity_id).where(ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.ended_epoch.is_(None)))
    )
    present = set(await ctx.session.scalars(select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id)))
    event = await war_event(ctx.session, war)
    joined = 0
    for house in await ctx.session.scalars(
        select(HouseProfileRow).where(HouseProfileRow.polity_entity_id == realm.entity.id, HouseProfileRow.extinct_epoch.is_(None))
    ):
        if rival is not None and house.house_entity_id == rival.house_entity_id:
            side = WarSide.ATTACKER
        elif (crown is not None and house.house_entity_id == crown.house_entity_id) or house.head_entity_id in officers:
            side = WarSide.DEFENDER
        elif house.house_entity_id in claimants:
            side = WarSide.ATTACKER
        else:
            continue
        if not ctx.rng(f"house_side.{war.id}.{house.house_entity_id}").chance(ctx.rules.succession.house_join_chance):
            continue
        await connect(ctx.session, house.house_entity_id, event.id, BondKind.PARTY_TO, ctx.epoch, description=f"fought for the {spoken(side)}")
        for seat in house.seats:
            place = await living_entity(ctx.session, seat)
            if place is None or seat in present or place.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE} or seat == host_id:
                continue
            ctx.session.add(new_side(ctx, war.id, seat, side))
            present.add(seat)
        joined += 1
    return joined


async def press_claims(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    table = ctx.rules.succession
    if realm.ruler_id is None:
        return 0
    claims = await ctx.session.scalars(
        select(ClaimRow).where(ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.ended_epoch.is_(None), ClaimRow.strength >= table.claim_press_pct)
    )
    wars = 0
    for claim in list(claims):
        claimant = await living_entity(ctx.session, claim.claimant_entity_id)
        if claimant is None or claimant.id == realm.ruler_id or claim.pressed or "pressed" in claim.locked:
            continue
        backers, throne = await support(ctx, realm, claim)
        margin = backers - throne
        if margin < table.support_press or not ctx.rng(f"press.{claim.id}.{ctx.epoch}").chance(table.war_chance * min(2.0, 1 + margin / PERCENT)):
            continue
        core = book.entities.get(realm.profile.core_entity_id or -1)
        if core is None:
            continue
        claim.pressed = True
        host = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.FACTION,
                name=f"the party of {claimant.name}",
                body=f"Those who hold that {claimant.name}, not the ruler in power, is the rightful ruler of {realm.entity.name}.",
                stats=FactionStats(strength=round_half_up(claim.strength / 2), wealth=20, sway=claim.strength),
                power=max(1, claimant.power_level),
                location_id=core.id,
                world_id=core.world_id,
                subtype="pretender's host",
                engine_kind=EngineKind.REBELS,
                affiliated_entity_id=core.id,
                pending=False,
            ),
        )
        claim.backer_entity_id = host.id
        await connect(ctx.session, claimant.id, host.id, BondKind.MEMBER_OF, ctx.epoch, description="claimant")
        war = await press_claim_war(ctx, host.id, core.id, claim_id=claim.id, succession=True, reason=f"{claimant.name} pressed a claim to {realm.entity.name}")
        if war is None:
            continue
        ctx.count("houses_took_sides", await house_sides(ctx, realm, war, claimant.id, host.id))
        wars += 1
        await record(
            ctx,
            "polity.succession_war",
            roles={IncidentRole.ACTOR: claimant.id, IncidentRole.TARGET: realm.entity.id, IncidentRole.ALLY: host.id, IncidentRole.OPPONENT: realm.ruler_id},
            facts={"war": war.event_entity_id, "claim": claim.strength, "basis": claim.basis},
            place=realm.profile.capital_entity_id,
            cause=await succession_incident(ctx.session, realm.entity.id, [realm.ruler_id]),
        )
    return wars


async def office_effects(ctx: TickContext, book: RealmBook, realm: Realm) -> dict[str, int]:
    table = ctx.rules.government
    counts = {"negotiated": 0, "drilled": 0, "governed": 0, "embassies": 0}
    core = realm.profile.core_entity_id
    negotiate = await best_skill(ctx, realm, OfficePower.NEGOTIATE)
    if core is not None and negotiate > 0:
        parties = set(realm.members) | {realm.entity.id}
        treaties = set(
            await ctx.session.scalars(
                select(TreatyPartyRow.treaty_entity_id)
                .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyPartyRow.treaty_entity_id)
                .where(TreatyPartyRow.party_node_id.in_(list(parties)), TreatyProfileRow.status == TreatyStatus.IN_FORCE)
            )
        )
        partners = set(
            await ctx.session.scalars(
                select(TreatyPartyRow.party_node_id).where(
                    TreatyPartyRow.treaty_entity_id.in_(list(treaties)), TreatyPartyRow.party_node_id.not_in(list(parties))
                )
            )
        )
        for partner in sorted(partners):
            other = await living_entity(ctx.session, partner)
            if other is not None and other.entity_type in COMMUNITY_TYPES:
                await change_relation(ctx, core, partner, table.chancellor_relation * negotiate, MemoryKind.GOODWILL, note="courted by the chancellor")
                counts["negotiated"] += 1
    command = await best_skill(ctx, realm, OfficePower.COMMAND)
    banner = table.emblem_cohesion if realm.profile.emblem else 0
    gain = round_half_up(table.marshal_cohesion * command) + banner
    if gain and realm.members:
        for army in await ctx.session.scalars(
            select(ArmyProfileRow)
            .join(ArmyRow, ArmyRow.entity_id == ArmyProfileRow.army_entity_id)
            .where(ArmyRow.owner_entity_id.in_(list(realm.members)), ArmyRow.disbanded_epoch.is_(None))
        ):
            army.cohesion = clamp_int(army.cohesion + gain, 0, PERCENT)
            counts["drilled"] += 1
    counts["governed"] = await govern(ctx, book, realm)
    for office, skill in await wielders(ctx, realm, OfficePower.EMBASSY):
        host = book.realms.get(office.target_entity_id or -1)
        if host is None or core is None or host.profile.core_entity_id is None or skill <= 0:
            continue
        await change_relation(ctx, core, host.profile.core_entity_id, table.ambassador_relation * skill, MemoryKind.GOODWILL, note="an embassy at court")
        counts["embassies"] += 1
    counts["preached"] = await preach(ctx, book, realm)
    return counts


async def preach(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    preached = 0
    for _, skill in await wielders(ctx, realm, OfficePower.PREACH):
        if skill <= 0:
            continue
        for member in book.members(realm):
            if not held(member.id) and stat(member, "piety") is not None:
                shift_stat(member, "piety", ctx.rules.government.chaplain_piety * skill)
        preached += 1
    return preached


async def govern(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    table = ctx.rules.government
    governed = 0
    for office, skill in await wielders(ctx, realm, OfficePower.GOVERN):
        if office.region_entity_id is None or skill <= 0:
            continue
        seat = realm.territory.get(office.region_entity_id)
        province = seat.province if seat is not None else None
        regions = {
            region for region, row in realm.territory.items() if (province is not None and row.province == province) or region == office.region_entity_id
        }
        for member_id, member in realm.members.items():
            if book.atlas.top_region(member_id) in regions and "autonomy" not in member.locked:
                member.autonomy = clamp_int(member.autonomy - table.governor_autonomy * skill, 0, PERCENT)
        for region in regions:
            row = realm.territory[region]
            if "control" not in row.locked and "control" not in realm.profile.locked:
                row.control = clamp_int(row.control + table.governor_control * skill, 0, PERCENT)
        governed += 1
    return governed


async def seize_throne(ctx: TickContext, realm: Realm, usurper: EntityRow, reason: CoupCause, *, backer_id: int | None = None) -> bool:
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is not None and ruler.id == usurper.id:
        return False
    if ruler is not None:
        for bond in await active_bonds(ctx.session, [BondKind.RULES], sources=[ruler.id]):
            await close(ctx.session, bond, ctx.epoch, "overthrown")
            await connect(ctx.session, usurper.id, bond.target_node_id, BondKind.RULES, ctx.epoch, description="seized")
    core = realm.profile.core_entity_id
    if core is not None and not await active_bonds(ctx.session, [BondKind.RULES], sources=[usurper.id], targets=[core]):
        await connect(ctx.session, usurper.id, core, BondKind.RULES, ctx.epoch, description="seized")
    set_ruler(ctx, realm, usurper.id, spoken(reason), usurped=True)
    realm.profile.legitimacy_parts = {**realm.profile.legitimacy_parts, "usurper": ctx.epoch}
    if ruler is not None:
        await break_on(ctx, [usurper.id], OathKind.FEALTY, OathBreach.THRONE_SEIZED, recipient_id=ruler.id)
    await shift_infamy(ctx, usurper.id, ctx.rules.legitimacy.usurper_infamy)
    await record(
        ctx,
        "polity.coup" if ruler is not None else "polity.coup_empty_throne",
        roles={
            IncidentRole.ACTOR: usurper.id,
            IncidentRole.TARGET: realm.entity.id,
            IncidentRole.PREDECESSOR: ruler.id if ruler is not None else None,
            IncidentRole.ALLY: backer_id,
        },
        facts={"cause": reason, "infamy": ctx.rules.legitimacy.usurper_infamy},
        place=realm.profile.capital_entity_id,
        steps=(
            *((StepDraft(StepAction.DEPOSE, actor=usurper.id, target=ruler.id),) if ruler is not None else ()),
            StepDraft(StepAction.CROWN, actor=usurper.id, target=realm.entity.id),
        ),
    )
    return True


async def coups(ctx: TickContext, realm: Realm) -> int:
    table = ctx.rules.government
    if realm.ruler_id is None or realm.profile.legitimacy >= table.coup_legitimacy or "ruler" in realm.profile.locked:
        return 0
    holder, reason = await usurper_for(ctx, realm)
    if holder is None:
        return 0
    chance = table.coup_chance * await stress_factor(ctx.session, realm.entity.id, ctx.rules.structural_demography.coup_lift)
    if not ctx.rng(f"coup.{realm.entity.id}.{ctx.epoch}").chance(chance * await coup_factor(ctx.session, ctx.rules, realm.entity.id)):
        return 0
    return 1 if await seize_throne(ctx, realm, holder, reason) else 0


async def usurper_for(ctx: TickContext, realm: Realm) -> tuple[EntityRow | None, CoupCause]:
    plotting = await plotter(ctx.session, realm.entity.id)
    schemer = await living_entity(ctx.session, plotting) if plotting is not None else None
    if schemer is not None:
        return schemer, CoupCause.POWER_BASE
    marshal = next((office for office in realm.offices if OfficePower.COMMAND in powers_of(office) and office.holder_entity_id is not None), None)
    holder = await living_entity(ctx.session, marshal.holder_entity_id) if marshal is not None and marshal.holder_entity_id is not None else None
    if holder is None or TraitKind.AMBITIOUS not in await traits_of(ctx.session, holder.id):
        return None, CoupCause.MARSHAL
    return holder, CoupCause.MARSHAL
