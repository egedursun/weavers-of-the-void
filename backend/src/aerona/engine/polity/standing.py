from math import log2, log10

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import MEMORIES
from aerona.catalog.pacts import DECLARED_STANDINGS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow, MaimedCohortRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.culture import ArtworkProfileRow, ItemProfileRow
from aerona.db.tables.demography import LabourRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.communication import OpinionSubject
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.demography import Job
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind, OathBreach, OathKind, RegionalStanding
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.war import WarCause, WarStatus
from aerona.engine.body.customs import customs_of, maimed_for_rule, presence_pct
from aerona.engine.body.decline import decline_severity, failing_part
from aerona.engine.body.marks import leaves_mark
from aerona.engine.communication.opinion import mean_approval
from aerona.engine.context import TickContext
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.items import regalia_holder
from aerona.engine.lore.legends import foretold_return
from aerona.engine.mind.book import values_for
from aerona.engine.mind.memories import strength_of
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.held_titles import title_prestige
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.loyalty import loyalty_autonomy
from aerona.engine.polity.oaths import break_on
from aerona.engine.polity.repute import repute_of
from aerona.engine.primitives.folk import folk_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.modifiers import combine, live_contributions
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import bond_exists, connect, has_flag
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record
from aerona.engine.regime.book import legitimacy_kinds
from aerona.engine.services.war import declare_war
from aerona.engine.structures.readers import palace_legitimacy
from aerona.rules.registry import Rules

RECENT_EPOCHS = 3
HEIRLOOM_CLASSES = frozenset({ItemClass.PROSTHESIS, ItemClass.HOLY_RELIC})
TEN = 10


async def war_record(ctx: TickContext, realm: Realm) -> tuple[int, int, bool]:
    members = list(realm.members)
    if not members:
        return 0, 0, False
    since = ctx.epoch - RECENT_EPOCHS
    won = lost = 0
    for victor, loser in await ended_wars(ctx.session, since):
        won += 1 if victor in members else 0
        lost += 1 if loser in members else 0
    return won, lost, await fighting_now(ctx.session, tuple(members))


@memoized(WarRow)
async def ended_wars(session: AsyncSession, since: int) -> tuple[tuple[int | None, int | None], ...]:
    return tuple((war.victor_entity_id, war.loser_entity_id) for war in await session.scalars(select(WarRow).where(WarRow.ended_epoch >= since)))


@memoized(WarRow, WarSideRow)
async def fighting_now(session: AsyncSession, members: tuple[int, ...]) -> bool:
    fighting = await session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(members), WarRow.status == WarStatus.ONGOING, WarSideRow.left_epoch.is_(None))
        .limit(1)
    )
    return fighting is not None


async def legitimacy(ctx: TickContext, book: RealmBook, realm: Realm, laws: LawBook) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts: dict[str, int] = {"base": table.base}
    ruler = await ctx.session.get(EntityRow, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        parts["no ruler"] = -table.child
        return parts
    parts.update(await claim_to_rule(ctx, realm, ruler))
    parts.update(await body_and_name(ctx, realm, ruler, laws))
    if await has_flag(ctx.session, ruler.id, EntityFlag.OATHBREAKER):
        parts["oathbreaker"] = -table.oathbreaker
    if realm.profile.state_religion_id is not None:
        faithful = await bond_exists(ctx.session, ruler.id, realm.profile.state_religion_id, BondKind.WORSHIPS)
        parts["the temples' blessing" if faithful else "the temples' scorn"] = table.sanction if faithful else -table.excommunication
    church = await ctx.session.get(CultDoctrineRow, realm.profile.state_religion_id) if realm.profile.state_religion_id is not None else None
    sacred = church is not None and await ctx.session.get(CultTenetRow, (church.cult_entity_id, TenetKind.DIVINE_RULE)) is not None
    if await has_flag(ctx.session, ruler.id, EntityFlag.CHOSEN) or ruler.creator_son_id is not None or sacred:
        parts["divine rule"] = table.divine_rule
    if church is not None and ruler.id in church.excommunicated:
        parts["excommunicated"] = -table.excommunication
    held, lost = await regalia_holder(ctx, realm.entity.id, ruler.id)
    if held:
        parts["the crown of the realm"] = ctx.rules.regalia.legitimacy
    if lost:
        parts["regalia in other hands"] = -ctx.rules.regalia.lost_legitimacy
    palace = await palace_legitimacy(ctx.session, ctx.rules, [realm.profile.capital_entity_id, *realm.members])
    parts.update({label: value for label, value in (("a palace worthy of the ruler", palace),) if value})
    pacifist = church is not None and await ctx.session.get(CultTenetRow, (church.cult_entity_id, TenetKind.PACIFISM)) is not None
    if pacifist and (await war_record(ctx, realm))[2]:
        parts["a pacifist faith at war"] = -ctx.rules.doctrine.pacifist_legitimacy
    crowned = (await title_prestige(ctx.session, [ruler.id])).get(ruler.id, 0) * table.title_prestige_pct // PERCENT
    if crowned:
        parts["the titles the ruler holds"] = min(table.title_cap, crowned)
    parts.update(await fortunes(ctx, book, realm, ruler))
    parts.update(await bearing(ctx, realm, ruler))
    parts.update(await legitimacy_kinds(ctx.session, ctx.rules, realm.entity.id))
    voice = round_half_up(await mean_approval(ctx, list(realm.members), ruler.id) * ctx.rules.communication.legitimacy_pct / PERCENT)
    if voice:
        parts["the people's approval" if voice > 0 else "the people's disapproval"] = voice
    return parts


async def claim_to_rule(ctx: TickContext, realm: Realm, ruler: EntityRow) -> dict[str, int]:
    table = ctx.rules.legitimacy
    mark = realm.profile.legitimacy_parts.get("usurper")
    if mark is not None and mark > 1 and ctx.epoch - mark >= table.usurper_fade_epochs:
        realm.profile.legitimacy_parts = {key: value for key, value in realm.profile.legitimacy_parts.items() if key != "usurper"}
        await record(
            ctx,
            "polity.usurper_accepted",
            roles={IncidentRole.LEADER: ruler.id, IncidentRole.SUBJECT: realm.entity.id},
            facts={"epochs": ctx.epoch - mark},
            place=realm.profile.capital_entity_id,
        )
    if "usurper" in realm.profile.legitimacy_parts:
        return {"usurper": -table.usurper, **await foretold_return(ctx, ruler)}
    return {"rightful heir": table.rightful}


async def body_and_name(ctx: TickContext, realm: Realm, ruler: EntityRow, laws: LawBook) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts: dict[str, int] = {}
    injuries = list(await ctx.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == ruler.id)))
    core = await ctx.session.get(EntityRow, realm.profile.core_entity_id) if realm.profile.core_entity_id is not None else None
    custom = await customs_of(ctx.session, ctx.rules, core) if core is not None else None
    wholeness = bool(laws.param(realm.entity.id, LawKind.SUCCESSION_RULE, "wholeness_required"))
    if (wholeness and any(leaves_mark(row) for row in injuries)) or maimed_for_rule(custom, injuries):
        parts["maimed where wholeness is law"] = -table.unwhole
    conditions = list(await ctx.session.scalars(select(ConditionRow).where(ConditionRow.bearer_node_id == ruler.id)))
    genome = await ctx.session.get(GenomeRow, ruler.id)
    presence = presence_pct(
        ctx.rules,
        custom,
        injuries,
        conditions,
        role=ruler.mortal_role,
        patron_id=realm.profile.patron_son_id,
        beauty=genome.beauty if genome is not None else None,
    )
    reading = round_half_up((presence - PERCENT) * table.body_reading_pct / PERCENT)
    if reading:
        parts["the people's reading of the ruler's body"] = reading
    parts["renown"] = round_half_up((ruler.importance or 0) / TEN * table.renown_per_10)
    repute = await repute_of(ctx.session, ruler.id)
    honour = round_half_up((repute.honour - PERCENT // 2) * 2 * table.honour_pct / PERCENT)
    if honour:
        parts["honour"] = honour
    if repute.infamy:
        parts["infamy"] = -round_half_up(repute.infamy * table.infamy_pct / PERCENT)
    emblem = await emblem_art(ctx, realm)
    if emblem:
        parts["the realm's emblem displayed"] = emblem
    return parts


async def emblem_art(ctx: TickContext, realm: Realm) -> int:
    table = ctx.rules.government
    if not realm.profile.emblem or not realm.members:
        return 0
    works = await ctx.session.scalar(
        select(func.count(ArtworkProfileRow.artwork_entity_id))
        .join(EntityRow, EntityRow.id == ArtworkProfileRow.artwork_entity_id)
        .where(
            ArtworkProfileRow.patron_entity_id == realm.entity.id,
            ArtworkProfileRow.propaganda.is_(True),
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id.in_(list(realm.members)),
        )
    )
    return min(table.emblem_artwork_cap, int(works or 0) * table.emblem_artwork)


async def bearing(ctx: TickContext, realm: Realm, ruler: EntityRow) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts: dict[str, int] = {}
    body = await ctx.session.get(BodyRow, ruler.id)
    if body is not None and body.presence < PERCENT:
        parts["a diminished presence"] = -round_half_up((PERCENT - body.presence) * table.presence_pct / PERCENT)
    values = await values_for(ctx.session, ruler.location_id) if ruler.location_id is not None else {}
    if body is not None and body.melee < PERCENT and values.get(ValueAxis.MARTIAL, 0) >= table.martial_value:
        parts["a warlord who can no longer fight"] = -round_half_up((PERCENT - body.melee) * table.martial_melee_pct / PERCENT)
    acts = await deeds_reading(ctx, realm, ruler)
    if acts:
        parts["the realm's judgement of their deeds"] = acts
    if await heirloom_relic(ctx, ruler):
        parts["an heirloom relic of the line"] = table.relic_legitimacy
    return parts


async def deeds_reading(ctx: TickContext, realm: Realm, ruler: EntityRow) -> int:
    table = ctx.rules.legitimacy
    holders = [realm.entity.id, *realm.members]
    rows = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id.in_(holders), MemoryRow.subject_node_id == ruler.id))
    weight = sum(strength_of(row, ctx.epoch) for row in rows if MEMORIES[row.kind].act is not None)
    cap = table.acts_cap
    return max(-cap, min(cap, round_half_up(weight * table.acts_pct / PERCENT / max(1, len(holders)))))


async def heirloom_relic(ctx: TickContext, ruler: EntityRow) -> bool:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == ruler.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.item_class.in_(list(HEIRLOOM_CLASSES)), ItemProfileRow.symbol.is_(True))
        .limit(1)
    )
    return found is not None


async def fortunes(ctx: TickContext, book: RealmBook, realm: Realm, ruler: EntityRow) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts: dict[str, int] = {}
    won, lost, _ = await war_record(ctx, realm)
    if won:
        parts["victories"] = won * table.victory
    if lost:
        parts["defeats"] = -lost * table.defeat
    members = book.members(realm)
    prosperity = [stat(member, "prosperity") for member in members if stat(member, "prosperity") is not None]
    if prosperity:
        parts["prosperity"] = (
            round_half_up(sum(value or 0 for value in prosperity) / len(prosperity) * table.prosperity_pct / PERCENT) - table.prosperity_pct // 2
        )
    age = stat(ruler, "age") or 0
    lifespan = stat(ruler, "lifespan") or 0
    failing = await decline_severity(ctx.session, ruler.id)
    if age < ctx.rules.succession.regency_age:
        parts["a child as ruler"] = -table.child
    elif failing:
        parts["a ruler whose mind is failing"] = failing_part(failing, table.senile)
    elif lifespan and age * PERCENT >= lifespan * ctx.rules.succession.senile_age_pct:
        parts["an old and failing ruler"] = -table.senile // 2
    return parts


async def war_support(ctx: TickContext, realm: Realm) -> float:
    warring = PublicOpinionRow.subject == OpinionSubject.WAR
    enemies = await ctx.session.scalars(
        select(PublicOpinionRow.subject_node_id).where(PublicOpinionRow.community_node_id.in_(list(realm.members)), warring).distinct()
    )
    found = [await mean_approval(ctx, list(realm.members), enemy) for enemy in enemies]
    return sum(found) / len(found) if found else 0.0


async def recovery(ctx: TickContext, realm: Realm) -> int:
    table = ctx.rules.war_weariness
    places = [realm.entity.id, *realm.members]
    maimed = await ctx.session.scalar(select(func.sum(MaimedCohortRow.veterans)).where(MaimedCohortRow.community_entity_id.in_(places)))
    wars = select(CollectionRow.id).where(CollectionRow.kind == CollectionKind.WAR)
    told = await ctx.session.scalar(
        select(AccountRow.id).where(AccountRow.holder_entity_id.in_(places), AccountRow.collection_id.in_(wars), AccountRow.defaced.is_(False)).limit(1)
    )
    pace = 1 - min(1.0, int(maimed or 0) / table.maimed_full) * table.maimed_slow_pct / PERCENT
    pace *= 1 - (table.memory_slow_pct / PERCENT if told is not None else 0.0)
    return round_half_up(max(ctx.rules.legitimacy.weariness_decay, realm.profile.war_weariness * table.recovery_pct / PERCENT) * pace)


async def stability(ctx: TickContext, book: RealmBook, realm: Realm, legit: int) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts = {"legitimacy": legit}
    _, _, fighting = await war_record(ctx, realm)
    profile = realm.profile
    worn = await ctx.session.scalar(
        select(func.max(WarSideRow.weariness)).where(WarSideRow.entity_id.in_([realm.entity.id, *realm.members]), WarSideRow.left_epoch.is_(None))
    )
    eased = profile.war_weariness - await recovery(ctx, realm)
    support = round_half_up(await war_support(ctx, realm) * ctx.rules.communication.war_support_pct / PERCENT)
    profile.war_weariness = clamp_int((max(int(worn or 0), eased) if fighting else eased) - support, 0, PERCENT)
    if profile.war_weariness:
        parts["war weariness"] = -round_half_up(profile.war_weariness * table.weariness_pct / PERCENT)
    disapproval = min(0.0, await mean_approval(ctx, list(realm.members), realm.ruler_id))
    if disapproval:
        parts["the people's discontent"] = round_half_up(disapproval * ctx.rules.communication.stability_pct / PERCENT)
    unrest = []
    for member in book.members(realm):
        town = await ctx.session.get(SettlementProfileRow, member.id)
        if town is not None:
            unrest.append(town.unrest)
    if unrest:
        parts["unrest"] = -round_half_up(sum(unrest) / len(unrest) * table.unrest_pct / PERCENT)
    factions = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.affiliated_entity_id.in_(list(realm.members))
        )
    )
    strengths: list[int] = [stat(faction, "strength") or 0 for faction in factions]
    whole = sum(strengths)
    if len(strengths) > 1 and whole > 0:
        share = max(strengths) / whole
        parts["one faction overwhelms the rest"] = -round_half_up(max(0.0, share - 0.5) * 2 * table.faction_pct)
    return parts


async def administration(ctx: TickContext, book: RealmBook, realm: Realm, knowledge: KnowledgeMap) -> tuple[int, int]:
    table = ctx.rules.administration
    members = book.members(realm)
    core_id = realm.profile.core_entity_id or (members[0].id if members else 0)
    literacy = 0
    culture = await ctx.session.get(PeopleCultureRow, core_id)
    if culture is not None:
        literacy = culture.literacy
    society = await ctx.session.get(CommunitySocietyRow, core_id)
    scribes = society.share(SocialClass.SCRIBE) if society is not None else 0.0
    officials = society.share(SocialClass.OFFICIAL) if society is not None else 0.0
    service = await ctx.session.scalar(select(LabourRow.workers).where(LabourRow.community_entity_id == core_id, LabourRow.job == Job.SERVICE)) or 0
    roads = 0
    for member in members:
        infra = await ctx.session.get(SettlementInfrastructureRow, member.id)
        roads += infra.roads if infra is not None else 0
    capacity = (
        table.base
        + literacy // TEN * table.per_literacy
        + round_half_up(scribes * table.per_scribe_pct)
        + round_half_up(officials * table.per_official_pct)
        + service // table.service_per_point
        + knowledge.level(core_id, KnowledgeBranch.WRITING) * table.per_writing_level
        + roads * table.per_road
    )
    discount = ctx.rules.networks.admin_discount_pct
    shares = [PERCENT - discount * await network_dependence(ctx.session, member.id) // PERCENT for member in members]
    need = len(realm.territory) * table.land_weight + round_half_up(sum(shares) * table.member_weight / PERCENT)
    return capacity, need


async def network_dependence(session: AsyncSession, member_id: int) -> int:
    found = await session.scalar(select(func.max(NetworkNodeRow.dependency_pct)).where(NetworkNodeRow.member_node_id == member_id))
    return int(found or 0)


async def overreach(ctx: TickContext, book: RealmBook, realm: Realm, capacity: int, need: int) -> list[EntityRow]:
    table = ctx.rules.overextension
    profile = realm.profile
    profile.administration = capacity
    profile.overextension = clamp_int(need * PERCENT / max(1, capacity), 0, PERCENT * 10)
    strain = await lagged(ctx, BalanceLoop.OVEREXTENSION, realm.entity.id, profile.overextension)
    over = strain > PERCENT
    capital_region = book.atlas.top_region(profile.capital_entity_id or -1)
    breaking: list[EntityRow] = []
    for member_id, row in realm.members.items():
        if member_id == profile.core_entity_id:
            row.autonomy = 0
            continue
        region = book.atlas.top_region(member_id)
        hops = book.atlas.region_hops(capital_region, region) if capital_region is not None and region is not None else None
        distance = 1 + (hops or 0)
        if over:
            row.autonomy = clamp_int(row.autonomy + table.autonomy_gain * distance * (strain - PERCENT) / PERCENT, 0, PERCENT)
        else:
            row.autonomy = clamp_int(row.autonomy - table.autonomy_decay, 0, PERCENT)
        member = book.entities.get(member_id)
        row.autonomy = clamp_int(row.autonomy + await loyalty_autonomy(ctx, realm, member), 0, PERCENT)
        if member is not None and row.autonomy >= table.secession_autonomy and ctx.rng(f"secession.{member_id}.{ctx.epoch}").chance(table.secession_chance):
            breaking.append(member)
    return breaking


async def secede(ctx: TickContext, book: RealmBook, realm: Realm, member: EntityRow) -> None:
    if realm.ruler_id is not None:
        sworn = list(
            await ctx.session.scalars(
                select(EntityRow.id).where(
                    EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_of(ctx.session, member)
                )
            )
        )
        await break_on(ctx, sworn, OathKind.FEALTY, OathBreach.MEMBER_BROKE_AWAY, recipient_id=realm.ruler_id, occasion=member.id)
    row = realm.members.pop(member.id, None)
    autonomy = row.autonomy if row is not None else None
    if row is not None:
        await ctx.session.delete(row)
    book.member_of.pop(member.id, None)
    for bond in await ctx.session.scalars(select(PolityMemberRow).where(PolityMemberRow.member_entity_id == member.id)):
        await ctx.session.delete(bond)
    await connect(ctx.session, member.id, realm.entity.id, BondKind.ENEMY, ctx.epoch, description="broke away")
    core = book.entities.get(realm.profile.core_entity_id or -1)
    if core is not None:
        await declare_war(ctx, member.id, core.id, f"{member.name} broke away from {realm.entity.name}", cause=WarCause.INDEPENDENCE)
    await record(
        ctx,
        "polity.secession",
        roles={IncidentRole.ACTOR: member.id, IncidentRole.PREDECESSOR: realm.entity.id, IncidentRole.LEADER: realm.ruler_id},
        facts={"autonomy": autonomy},
        place=member.id,
    )


def rank(book: RealmBook) -> None:
    by_world: dict[int, list[Realm]] = {}
    for realm in book.realms.values():
        by_world.setdefault(realm.entity.world_id or 0, []).append(realm)
    for realms in by_world.values():
        ordered = sorted(realms, key=lambda item: (-(stat(item.entity, "subjects") or 0) * item.profile.legitimacy, item.entity.id))
        for index, realm in enumerate(ordered):
            if "standing" in realm.profile.locked or realm.profile.standing in DECLARED_STANDINGS:
                continue
            if realm.entity.id in book.vassals:
                realm.profile.standing = RegionalStanding.CLIENT
            elif index == 0 and len(ordered) > 1:
                realm.profile.standing = RegionalStanding.HEGEMON
            elif index < max(2, len(ordered) // 4):
                realm.profile.standing = RegionalStanding.GREAT_POWER
            else:
                realm.profile.standing = RegionalStanding.MINOR_POWER


def doubling_tier(amount: float) -> int:
    return int(log2(1 + max(0.0, amount)))


def people_tier(subjects: int, first: int) -> int:
    return 1 + int(log10(subjects / first)) if subjects >= first else 0


def tier_score(book: RealmBook, realm: Realm, rules: Rules, knowledge: KnowledgeMap) -> int:
    table = rules.realm_tiers
    members = book.members(realm)
    base = max((member.civ_tier or 0 for member in members), default=0)
    land = doubling_tier(len(realm.territory) / table.territory_per_tier)
    admin = doubling_tier(realm.profile.administration / table.administration_per_tier)
    core = realm.profile.core_entity_id
    writing = doubling_tier(knowledge.level(core, KnowledgeBranch.WRITING) / table.knowledge_tier_level) if core is not None else 0
    people = people_tier(stat(realm.entity, "subjects") or 0, rules.scale.realm_subjects_tier)
    worlds = len({member.world_id for member in members if member.world_id is not None})
    over = 1 if realm.profile.overextension > PERCENT * 2 else 0
    return max(0, base + land + admin + writing + people + max(0, worlds - 1) * table.worlds_tier - over)


async def realm_tier(ctx: TickContext, book: RealmBook, realm: Realm, knowledge: KnowledgeMap) -> int:
    table = ctx.rules.realm_tiers
    profile = realm.profile
    if "tier" in profile.locked:
        return profile.tier
    score = tier_score(book, realm, ctx.rules, knowledge)
    if score >= profile.tier + 1 + table.rise_margin or (profile.tier == 0 and score > 0):
        profile.tier_strain = 0
        risen = min(score, profile.tier + 1) if profile.tier else score
        if risen > profile.tier:
            await record(
                ctx,
                "polity.tier_rose",
                roles={IncidentRole.SUBJECT: realm.entity.id},
                facts={"tier": risen, "score": score},
                place=profile.capital_entity_id,
            )
        return risen
    if score < profile.tier:
        profile.tier_strain += 1
        if profile.tier_strain >= table.decline_epochs:
            profile.tier_strain = 0
            await record(
                ctx,
                "polity.tier_fell",
                roles={IncidentRole.SUBJECT: realm.entity.id},
                facts={"tier": profile.tier - 1, "score": score, "strain_epochs": table.decline_epochs},
                place=profile.capital_entity_id,
            )
            return profile.tier - 1
        return profile.tier
    profile.tier_strain = 0
    return profile.tier


def settle(realm: Realm, legit: dict[str, int], steady: dict[str, int]) -> None:
    profile = realm.profile
    if "legitimacy" not in profile.locked:
        profile.legitimacy = clamp_int(combine(sum(legit.values()), live_contributions(realm.entity.id, "legitimacy")).value, 0, PERCENT)
    if "stability" not in profile.locked:
        steady_sum = profile.legitimacy + sum(value for key, value in steady.items() if key != "legitimacy")
        profile.stability = clamp_int(combine(steady_sum, live_contributions(realm.entity.id, "stability")).value, 0, PERCENT)
    kept = {key: value for key, value in profile.legitimacy_parts.items() if key == "usurper"}
    profile.legitimacy_parts = {
        **kept,
        **{f"legitimacy: {key}": value for key, value in legit.items()},
        **{f"stability: {key}": value for key, value in steady.items() if key != "legitimacy"},
    }
    set_stats(realm.entity, legitimacy=profile.legitimacy, stability=profile.stability)
