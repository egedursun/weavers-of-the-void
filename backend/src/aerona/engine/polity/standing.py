from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.body import LASTING_INJURY_STATES
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.polity import LawKind, RegionalStanding
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.lore.items import regalia_holder
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import bond_exists, connect, has_flag
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.war import declare_war
from aerona.engine.structures.readers import palace_legitimacy

RECENT_EPOCHS = 3
TEN = 10
TWENTY = 20


async def war_record(ctx: TickContext, realm: Realm) -> tuple[int, int, bool]:
    members = list(realm.members)
    if not members:
        return 0, 0, False
    since = ctx.epoch - RECENT_EPOCHS
    won = lost = 0
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch >= since)):
        won += 1 if war.victor_entity_id in members else 0
        lost += 1 if war.loser_entity_id in members else 0
    fighting = await ctx.session.scalar(
        select(WarSideRow.war_id)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(members), WarRow.status == WarStatus.ONGOING, WarSideRow.left_epoch.is_(None))
        .limit(1)
    )
    return won, lost, fighting is not None


async def legitimacy(ctx: TickContext, book: RealmBook, realm: Realm, laws: LawBook) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts: dict[str, int] = {"base": table.base}
    ruler = await ctx.session.get(EntityRow, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        parts["no ruler"] = -table.child
        return parts
    if "usurper" in realm.profile.legitimacy_parts:
        parts["usurper"] = -table.usurper
    else:
        parts["rightful heir"] = table.rightful
    if bool(laws.param(realm.entity.id, LawKind.SUCCESSION_RULE, "wholeness_required")):
        maimed = await ctx.session.scalar(
            select(InjuryRow.id).where(InjuryRow.bearer_node_id == ruler.id, InjuryRow.state.in_(list(LASTING_INJURY_STATES))).limit(1)
        )
        if maimed is not None:
            parts["maimed where wholeness is law"] = -table.unwhole
    parts["renown"] = round_half_up((ruler.importance or 0) / TEN * table.renown_per_10)
    if await has_flag(ctx.session, ruler.id, EntityFlag.OATHBREAKER):
        parts["oathbreaker"] = -table.oathbreaker
    if realm.profile.state_religion_id is not None:
        faithful = await bond_exists(ctx.session, ruler.id, realm.profile.state_religion_id, BondKind.WORSHIPS)
        parts["the temples' blessing" if faithful else "the temples' scorn"] = table.sanction if faithful else -table.excommunication
    church = await ctx.session.get(CultDoctrineRow, realm.profile.state_religion_id) if realm.profile.state_religion_id is not None else None
    sacred = church is not None and await ctx.session.get(CultTenetRow, (church.cult_entity_id, TenetKind.DIVINE_KINGSHIP)) is not None
    if await has_flag(ctx.session, ruler.id, EntityFlag.CHOSEN) or ruler.creator_son_id is not None or sacred:
        parts["divine kingship"] = table.divine_kingship
    if church is not None and ruler.id in church.excommunicated:
        parts["excommunicated"] = -table.excommunication
    held, lost = await regalia_holder(ctx, realm.entity.id, ruler.id)
    if held:
        parts["the crown of the realm"] = ctx.rules.regalia.legitimacy
    if lost:
        parts["regalia in other hands"] = -ctx.rules.regalia.lost_legitimacy
    palace = await palace_legitimacy(ctx.session, ctx.rules, [realm.profile.capital_entity_id, *realm.members])
    parts.update({label: value for label, value in (("a palace worthy of the crown", palace),) if value})
    pacifist = church is not None and await ctx.session.get(CultTenetRow, (church.cult_entity_id, TenetKind.PACIFISM)) is not None
    if pacifist and (await war_record(ctx, realm))[2]:
        parts["a pacifist faith at war"] = -ctx.rules.doctrine.pacifist_legitimacy
    parts.update(await fortunes(ctx, book, realm, ruler))
    return parts


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
    if age < ctx.rules.succession.regency_age:
        parts["a child on the throne"] = -table.child
    elif lifespan and age * PERCENT >= lifespan * ctx.rules.succession.senile_age_pct:
        parts["an old and failing ruler"] = -table.senile
    return parts


async def stability(ctx: TickContext, book: RealmBook, realm: Realm, legit: int) -> dict[str, int]:
    table = ctx.rules.legitimacy
    parts = {"legitimacy": legit}
    _, _, fighting = await war_record(ctx, realm)
    profile = realm.profile
    worn = await ctx.session.scalar(
        select(func.max(WarSideRow.weariness)).where(WarSideRow.entity_id.in_([realm.entity.id, *realm.members]), WarSideRow.left_epoch.is_(None))
    )
    eased = profile.war_weariness - table.weariness_decay
    profile.war_weariness = clamp_int(max(int(worn or 0), eased) if fighting else eased, 0, PERCENT)
    if profile.war_weariness:
        parts["war weariness"] = -round_half_up(profile.war_weariness * table.weariness_pct / PERCENT)
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
    roads = 0
    for member in members:
        infra = await ctx.session.get(SettlementInfrastructureRow, member.id)
        roads += infra.roads if infra is not None else 0
    capacity = (
        table.base
        + literacy // TEN * table.per_literacy
        + round_half_up(scribes * table.per_scribe_pct)
        + knowledge.level(core_id, KnowledgeBranch.WRITING) * table.per_writing_level
        + roads * table.per_road
    )
    need = len(realm.territory) * table.land_weight + len(members) * table.member_weight
    return capacity, need


async def overreach(ctx: TickContext, book: RealmBook, realm: Realm, capacity: int, need: int) -> list[EntityRow]:
    table = ctx.rules.overextension
    profile = realm.profile
    profile.administration = capacity
    profile.overextension = clamp_int(need * PERCENT / max(1, capacity), 0, PERCENT * 10)
    over = profile.overextension > PERCENT
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
            row.autonomy = clamp_int(row.autonomy + table.autonomy_gain * distance * (profile.overextension - PERCENT) / PERCENT, 0, PERCENT)
        else:
            row.autonomy = clamp_int(row.autonomy - table.autonomy_decay, 0, PERCENT)
        member = book.entities.get(member_id)
        if member is not None and row.autonomy >= table.secession_autonomy and ctx.rng(f"secession.{member_id}.{ctx.epoch}").chance(table.secession_chance):
            breaking.append(member)
    return breaking


async def secede(ctx: TickContext, book: RealmBook, realm: Realm, member: EntityRow) -> None:
    row = realm.members.pop(member.id, None)
    if row is not None:
        await ctx.session.delete(row)
    book.member_of.pop(member.id, None)
    for bond in await ctx.session.scalars(select(PolityMemberRow).where(PolityMemberRow.member_entity_id == member.id)):
        await ctx.session.delete(bond)
    await connect(ctx.session, member.id, realm.entity.id, BondKind.ENEMY, ctx.epoch, description="broke away")
    core = book.entities.get(realm.profile.core_entity_id or -1)
    if core is not None:
        await declare_war(ctx, member.id, core.id, f"{member.name} broke away from {realm.entity.name}")
    await note(
        ctx,
        f"{member.name}, far from the throne and long left to itself, broke away from {realm.entity.name}.",
        key="polity.secession",
        ids=[member.id, realm.entity.id],
        kind=ChronicleKind.CIVILIZATION,
    )


def rank(book: RealmBook) -> None:
    by_world: dict[int, list[Realm]] = {}
    for realm in book.realms.values():
        by_world.setdefault(realm.entity.world_id or 0, []).append(realm)
    for realms in by_world.values():
        ordered = sorted(realms, key=lambda item: (-(stat(item.entity, "subjects") or 0) * item.profile.legitimacy, item.entity.id))
        for index, realm in enumerate(ordered):
            if "standing" in realm.profile.locked:
                continue
            if realm.entity.id in book.vassals:
                realm.profile.standing = RegionalStanding.CLIENT
            elif index == 0 and len(ordered) > 1:
                realm.profile.standing = RegionalStanding.HEGEMON
            elif index < max(2, len(ordered) // 4):
                realm.profile.standing = RegionalStanding.GREAT_POWER
            else:
                realm.profile.standing = RegionalStanding.MINOR_POWER


def realm_tier(book: RealmBook, realm: Realm) -> int:
    tiers = [member.civ_tier or 0 for member in book.members(realm)]
    provinces = 1 if len(realm.territory) >= TWENTY // 4 else 0
    return max(tiers, default=0) + provinces


def settle(realm: Realm, legit: dict[str, int], steady: dict[str, int]) -> None:
    profile = realm.profile
    if "legitimacy" not in profile.locked:
        profile.legitimacy = clamp_int(sum(legit.values()), 0, PERCENT)
    if "stability" not in profile.locked:
        profile.stability = clamp_int(profile.legitimacy + sum(value for key, value in steady.items() if key != "legitimacy"), 0, PERCENT)
    kept = {key: value for key, value in profile.legitimacy_parts.items() if key == "usurper"}
    profile.legitimacy_parts = {
        **kept,
        **{f"legitimacy: {key}": value for key, value in legit.items()},
        **{f"stability: {key}": value for key, value in steady.items() if key != "legitimacy"},
    }
    set_stats(realm.entity, legitimacy=profile.legitimacy, stability=profile.stability)
