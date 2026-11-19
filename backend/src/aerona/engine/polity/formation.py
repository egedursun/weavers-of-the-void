from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.civics import GOVERNMENT_GATES
from aerona.catalog.collective import HERALDIC_NAMES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.polity import OfficeHistoryRow, OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow, VassalageRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import Tincture
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, OfficeKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.statecraft import SubjectKind
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.lore.civics import holders_know
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record
from aerona.engine.transform.record import record_transformation

COMMUNITIES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
PRIESTLY = frozenset({MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER})
RULES_OF = total(
    GovernmentKind,
    {
        GovernmentKind.CHIEFDOM: DecisionRule.AUTOCRATIC,
        GovernmentKind.MONARCHY: DecisionRule.AUTOCRATIC,
        GovernmentKind.EMPIRE: DecisionRule.AUTOCRATIC,
        GovernmentKind.OCCUPATION: DecisionRule.AUTOCRATIC,
        GovernmentKind.THEOCRACY: DecisionRule.DIVINE,
        GovernmentKind.GOD_REALM: DecisionRule.DIVINE,
        GovernmentKind.OLIGARCHY: DecisionRule.COUNCIL,
        GovernmentKind.TRIBAL_CONFEDERATION: DecisionRule.COUNCIL,
        GovernmentKind.REPUBLIC: DecisionRule.ASSEMBLY,
        GovernmentKind.HIVE_COUNCIL: DecisionRule.ASSEMBLY,
        GovernmentKind.JUNTA: DecisionRule.AUTOCRATIC,
        GovernmentKind.COLONIAL_ADMINISTRATION: DecisionRule.AUTOCRATIC,
        GovernmentKind.CORPORATE_STATE: DecisionRule.COUNCIL,
        GovernmentKind.TECHNOCRACY: DecisionRule.COUNCIL,
        GovernmentKind.MACHINE_RULE: DecisionRule.COUNCIL,
        GovernmentKind.FEDERATION: DecisionRule.ASSEMBLY,
        GovernmentKind.COMMUNE: DecisionRule.ASSEMBLY,
    },
)
TITLES = total(
    GovernmentKind,
    {
        GovernmentKind.CHIEFDOM: "Chiefdom",
        GovernmentKind.MONARCHY: "Kingdom",
        GovernmentKind.EMPIRE: "Empire",
        GovernmentKind.OCCUPATION: "Occupied Lands",
        GovernmentKind.THEOCRACY: "Holy Realm",
        GovernmentKind.GOD_REALM: "Divine Kingdom",
        GovernmentKind.OLIGARCHY: "Merchant League",
        GovernmentKind.TRIBAL_CONFEDERATION: "Confederation",
        GovernmentKind.REPUBLIC: "Republic",
        GovernmentKind.HIVE_COUNCIL: "Hive",
        GovernmentKind.JUNTA: "Military Government",
        GovernmentKind.COLONIAL_ADMINISTRATION: "Colony",
        GovernmentKind.CORPORATE_STATE: "Corporate State",
        GovernmentKind.TECHNOCRACY: "Technocracy",
        GovernmentKind.MACHINE_RULE: "Machine Rule",
        GovernmentKind.FEDERATION: "Federation",
        GovernmentKind.COMMUNE: "Commune",
    },
)

LITERATE_RULE = Technique.WRITTEN_LAW


async def lords(ctx: TickContext) -> tuple[dict[int, int], dict[int, int], dict[int, int]]:
    community_lord: dict[int, int] = {}
    mortal_rules: dict[int, int] = {}
    kin_root: dict[int, int] = {}
    entities = {
        row.id: row
        for row in await ctx.session.scalars(
            select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_([*COMMUNITIES, EntityType.MORTAL]))
        )
    }
    free = set(await ctx.session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.INDEPENDENT)))
    bonds = await ctx.session.scalars(
        select(BondRow).where(BondRow.state == BondState.ACTIVE, BondRow.kind.in_([BondKind.RULES, BondKind.DESCENDS_FROM])).order_by(BondRow.id)
    )
    for bond in bonds:
        source, target = entities.get(bond.source_node_id), entities.get(bond.target_node_id)
        if source is None or target is None:
            continue
        if bond.kind is BondKind.RULES and target.entity_type in COMMUNITIES:
            if source.entity_type in COMMUNITIES and source.id != target.id:
                community_lord[target.id] = source.id
            elif source.entity_type is EntityType.MORTAL:
                mortal_rules.setdefault(target.id, source.id)
        elif (
            bond.kind is BondKind.DESCENDS_FROM
            and source.entity_type is EntityType.SETTLEMENT
            and target.entity_type is EntityType.PEOPLE
            and source.id not in free
        ):
            kin_root.setdefault(source.id, target.id)
    return community_lord, mortal_rules, kin_root


def root_of(entity_id: int, community_lord: dict[int, int], kin_root: dict[int, int], shared: dict[int, int]) -> int:
    seen: set[int] = set()
    current = entity_id
    while current not in seen:
        seen.add(current)
        if current in community_lord:
            current = community_lord[current]
        elif current in shared and shared[current] != current:
            current = shared[current]
        elif current in kin_root:
            current = kin_root[current]
        else:
            break
    return current


async def subject_government(ctx: TickContext, realm_id: int | None) -> GovernmentKind | None:
    subject = await ctx.session.get(VassalageRow, realm_id) if realm_id is not None else None
    if subject is None:
        return None
    if subject.kind is SubjectKind.COLONY:
        return GovernmentKind.COLONIAL_ADMINISTRATION
    return GovernmentKind.OCCUPATION if subject.loyalty <= ctx.rules.government.occupation_loyalty else None


async def government_for(ctx: TickContext, core: EntityRow, members: list[EntityRow], ruler: EntityRow | None, realm_id: int | None = None) -> GovernmentKind:
    table = ctx.rules.government
    imposed = await subject_government(ctx, realm_id)
    if imposed is not None:
        return imposed
    values = await culture_of(ctx.session, core.id)
    society = await ctx.session.get(CommunitySocietyRow, core.id)
    merchants = society.share(SocialClass.MERCHANT) if society is not None else 0.0
    peoples = sum(1 for member in members if member.entity_type is EntityType.PEOPLE)
    tier = core.civ_tier or 0
    hierarchy = values.get(ValueAxis.HIERARCHY, 0)
    priestly = ruler is not None and ruler.mortal_role in PRIESTLY and values.get(ValueAxis.PIETY, 0) >= table.theocracy_piety
    imperial = len(members) >= table.empire_members or await has_flag(ctx.session, core.id, EntityFlag.EMPIRE)
    civics = (await known_levels(ctx.session, [core.id])).get(core.id, {}).get(KnowledgeBranch.CIVICS, 0)
    workers = society.share(SocialClass.WORKER) if society is not None else 0.0
    professionals = society.share(SocialClass.PROFESSIONAL) if society is not None else 0.0
    soldiers = society.share(SocialClass.WARRIOR) if society is not None else 0.0
    citizens = society.share(SocialClass.CITIZEN) if society is not None else 0.0
    ladder = (
        (priestly, GovernmentKind.THEOCRACY),
        (ruler is not None and ruler.mortal_role is MortalRole.OFFICER and soldiers >= table.junta_warrior_pct, GovernmentKind.JUNTA),
        (
            professionals >= table.machine_professional_pct
            and civics >= table.machine_civics_level
            and await law_param(ctx.session, core.id, LawKind.MACHINE_LAW, "level") != "banned",
            GovernmentKind.MACHINE_RULE,
        ),
        (citizens >= table.republic_citizen_pct and hierarchy <= table.citizen_hierarchy, GovernmentKind.REPUBLIC),
        (professionals >= table.technocracy_professional_pct and civics >= table.technocracy_civics_level, GovernmentKind.TECHNOCRACY),
        (workers >= table.commune_worker_pct and hierarchy <= table.republic_hierarchy, GovernmentKind.COMMUNE),
        (merchants >= table.oligarchy_merchant_pct and workers >= table.corporate_worker_pct, GovernmentKind.CORPORATE_STATE),
        (len(members) >= table.federation_members and civics >= table.federation_civics_level and hierarchy <= 0, GovernmentKind.FEDERATION),
        (merchants >= table.oligarchy_merchant_pct and hierarchy <= table.republic_hierarchy, GovernmentKind.REPUBLIC),
        (merchants >= table.oligarchy_merchant_pct, GovernmentKind.OLIGARCHY),
        (ruler is None and hierarchy <= table.republic_hierarchy, GovernmentKind.REPUBLIC),
        (peoples >= table.confederation_peoples and hierarchy < 0, GovernmentKind.TRIBAL_CONFEDERATION),
        (imperial, GovernmentKind.EMPIRE),
        (tier <= table.chiefdom_tier and not await holders_know(ctx.session, [core.id], LITERATE_RULE), GovernmentKind.CHIEFDOM),
    )
    for matched, kind in ladder:
        if matched and await holders_know(ctx.session, [core.id], GOVERNMENT_GATES.get(kind)):
            return kind
    return GovernmentKind.MONARCHY


FOUNDINGS = {EntityType.SETTLEMENT: TransformKind.CITY_STATE, EntityType.FACTION: TransformKind.SECESSION, EntityType.CULT: TransformKind.THEOCRACY}


async def found_polity(ctx: TickContext, book: RealmBook, core: EntityRow, *, told: bool = True) -> Realm:
    entity = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.POLITY,
            name=f"the realm of {core.name}",
            body=f"The lands and peoples that answer to {core.name}.",
            stats=PolityStats(legitimacy=50, stability=50, subjects=0, territory=0),
            power=max(1, core.power_level),
            location_id=None,
            world_id=core.world_id,
            subtype="realm",
            pending=False,
        ),
    )
    profile = PolityProfileRow(
        polity_entity_id=entity.id,
        government=await government_for(ctx, core, [core], None),
        decision_rule=DecisionRule.AUTOCRATIC,
        core_entity_id=core.id,
        capital_entity_id=core.id if core.entity_type is EntityType.SETTLEMENT else None,
        founded_epoch=ctx.epoch,
        updated_epoch=ctx.epoch,
        emblem={},
        legitimacy_parts={},
        locked=[],
    )
    ctx.session.add(profile)
    ctx.session.add(OfficeRow(polity_entity_id=entity.id, kind=OfficeKind.RULER, since_epoch=ctx.epoch, powers=[]))
    await ctx.session.flush()
    realm = Realm(entity, profile)
    realm.offices = list(await ctx.session.scalars(select(OfficeRow).where(OfficeRow.polity_entity_id == entity.id)))
    book.realms[entity.id] = realm
    ctx.count("polities_founded")
    kind = FOUNDINGS.get(core.entity_type)
    if told and kind is not None:
        await record_transformation(ctx, kind, core.id, entity.id)
    return realm


def set_ruler(ctx: TickContext, realm: Realm, ruler_id: int | None, reason: str, *, usurped: bool = False) -> bool:
    office = realm.office(OfficeKind.RULER)
    if held(realm.entity.id, ruler_id, office.holder_entity_id if office is not None else None):
        return False
    if office is None:
        office = OfficeRow(polity_entity_id=realm.entity.id, kind=OfficeKind.RULER, since_epoch=ctx.epoch, powers=[])
        ctx.session.add(office)
        realm.offices.append(office)
    if office.holder_entity_id == ruler_id:
        return False
    if office.id is not None and office.holder_entity_id is not None:
        ctx.session.add(
            OfficeHistoryRow(office_id=office.id, holder_entity_id=office.holder_entity_id, from_epoch=office.since_epoch, to_epoch=ctx.epoch, reason=reason)
        )
    office.holder_entity_id = ruler_id
    office.since_epoch = ctx.epoch
    if not usurped and "usurper" in realm.profile.legitimacy_parts:
        realm.profile.legitimacy_parts = {key: value for key, value in realm.profile.legitimacy_parts.items() if key != "usurper"}
    return True


async def sync_members(ctx: TickContext, book: RealmBook, realm: Realm, wanted: set[int]) -> tuple[int, int]:
    joined = left = 0
    for member_id in sorted(set(realm.members) - wanted):
        if held(member_id):
            continue
        await ctx.session.delete(realm.members.pop(member_id))
        book.member_of.pop(member_id, None)
        left += 1
    for member_id in sorted(wanted - set(realm.members)):
        if held(member_id):
            continue
        other = book.realm_of(member_id)
        if other is not None and other.entity.id != realm.entity.id and member_id in other.members:
            await ctx.session.delete(other.members.pop(member_id))
        row = PolityMemberRow(polity_entity_id=realm.entity.id, member_entity_id=member_id, joined_epoch=ctx.epoch, autonomy=0)
        ctx.session.add(row)
        realm.members[member_id] = row
        book.member_of[member_id] = realm.entity.id
        joined += 1
    return joined, left


async def dissolve(ctx: TickContext, book: RealmBook, live: set[int]) -> int:
    dissolved = 0
    for realm in list(book.realms.values()):
        if realm.entity.id in live:
            continue
        await retire_in(ctx, realm.entity, "its lands passed to others", status=EntityStatus.DESTROYED)
        for member_id in list(realm.members):
            await ctx.session.delete(realm.members.pop(member_id))
            book.member_of.pop(member_id, None)
        book.realms.pop(realm.entity.id)
        dissolved += 1
    return dissolved


async def refresh_realms(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    table = ctx.rules.government
    community_lord, mortal_rules, kin_root = await lords(ctx)
    first_ruled: dict[int, int] = {}
    shared: dict[int, int] = {}
    for community_id, mortal_id in sorted(mortal_rules.items()):
        first_ruled.setdefault(mortal_id, community_id)
        shared[community_id] = first_ruled[mortal_id]
    communities = {
        row.id: row
        for row in await ctx.session.scalars(select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITIES))))
    }
    groups: dict[int, list[int]] = defaultdict(list)
    for community_id in sorted(communities):
        root = root_of(community_id, community_lord, kin_root, shared)
        groups[root if root in communities else community_id].append(community_id)
    by_core = {realm.profile.core_entity_id: realm for realm in book.realms.values() if realm.profile.core_entity_id is not None}
    counts = {"founded": 0, "dissolved": 0, "joined": 0, "left": 0}
    surveying = not book.realms
    live: set[int] = set()
    for core_id, member_ids in sorted(groups.items()):
        core = communities[core_id]
        population = sum(stat(communities[item], "population") or 0 for item in member_ids)
        realm = by_core.get(core_id)
        if realm is None:
            if population < table.min_founding_population or held(core_id):
                continue
            realm = await found_polity(ctx, book, core)
            counts["founded"] += 1
            if not surveying:
                await record(
                    ctx,
                    "polity.founded",
                    roles={IncidentRole.PRODUCT: realm.entity.id, IncidentRole.ACTOR: core.id},
                    facts={"population": population, "members": len(member_ids)},
                    place=core.id,
                )
        live.add(realm.entity.id)
        joined, left = await sync_members(ctx, book, realm, set(member_ids))
        counts["joined"] += joined
        counts["left"] += left
        wanted = set(member_ids)
        for member_id in wanted:
            book.entities[member_id] = communities[member_id]
        ruler_id = mortal_rules.get(core_id) or next((mortal_rules[item] for item in member_ids if item in mortal_rules), None)
        set_ruler(ctx, realm, ruler_id, "the throne passed")
        await shape(ctx, book, realm)
    counts["dissolved"] = await dissolve(ctx, book, live)
    await ctx.session.flush()
    return counts


async def shape(ctx: TickContext, book: RealmBook, realm: Realm) -> None:
    profile = realm.profile
    members = book.members(realm)
    core = book.entities.get(profile.core_entity_id or -1) or (members[0] if members else None)
    if core is None:
        return
    ruler = await ctx.session.get(EntityRow, realm.ruler_id) if realm.ruler_id is not None else None
    if "government" not in profile.locked:
        government = await government_for(ctx, core, members, ruler, realm.entity.id)
        if government is not profile.government:
            profile.government = government
            if "name" not in profile.locked:
                realm.entity.name = f"the {TITLES[government]} of {core.name}"
    if "decision_rule" not in profile.locked:
        profile.decision_rule = RULES_OF[profile.government]
    settlements = [member for member in members if member.entity_type is EntityType.SETTLEMENT]
    if "capital" not in profile.locked:
        flagged = [member for member in settlements if await has_flag(ctx.session, member.id, EntityFlag.CAPITAL)]
        pool = flagged or settlements
        profile.capital_entity_id = max(pool, key=lambda item: (stat(item, "population") or 0, -item.id)).id if pool else core.id
    patron = await living_patron(ctx.session, core)
    if "patron" not in profile.locked:
        profile.patron_son_id = patron.id if patron is not None else None
    if "state_religion" not in profile.locked:
        cults = await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_([member.id for member in members])
            )
        )
        chosen = max(cults, key=lambda cult: (stat(cult, "followers") or 0, -cult.id), default=None)
        profile.state_religion_id = chosen.id if chosen is not None else None
    if not profile.emblem:
        profile.emblem = {"field": HERALDIC_NAMES[ctx.rng(f"realm.field.{realm.entity.id}").pick(list(Tincture))], "charge": core.name.split()[-1].lower()}
    await map_territory(ctx, book, realm, members)
    set_stats(
        realm.entity,
        subjects=sum(stat(member, "population") or 0 for member in members),
        territory=len(realm.territory),
        legitimacy=profile.legitimacy,
        stability=profile.stability,
    )
    realm.entity.world_id = core.world_id
    profile.updated_epoch = ctx.epoch


async def map_territory(ctx: TickContext, book: RealmBook, realm: Realm, members: list[EntityRow]) -> None:
    if held(realm.entity.id):
        return
    weights: dict[int, int] = defaultdict(int)
    for member in members:
        region = book.atlas.top_region(member.id)
        if region is not None and not held(region):
            weights[region] += stat(member, "population") or 0
    for region_id in sorted(set(realm.territory) - set(weights)):
        if not held(region_id):
            await ctx.session.delete(realm.territory.pop(region_id))
    for region_id, people in weights.items():
        everyone = sum(stat(item, "population") or 0 for item_id in book.atlas.communities_in(region_id) if (item := book.entities.get(item_id)) is not None)
        control = clamp_int(people * PERCENT / max(1, people, everyone), 0, PERCENT)
        row = realm.territory.get(region_id)
        if row is None:
            row = PolityTerritoryRow(polity_entity_id=realm.entity.id, region_entity_id=region_id, control=control, locked=[])
            ctx.session.add(row)
            realm.territory[region_id] = row
        elif "control" not in realm.profile.locked and "control" not in row.locked:
            row.control = control
    await provinces(ctx, book, realm, members)


async def provinces(ctx: TickContext, book: RealmBook, realm: Realm, members: list[EntityRow]) -> int:
    if realm.profile.tier < ctx.rules.realm_tiers.provinces:
        for row in realm.territory.values():
            if "province" not in row.locked:
                row.province = None
        return 0
    seats: dict[int, EntityRow] = {}
    for member in members:
        region = book.atlas.top_region(member.id)
        if region is not None and (region not in seats or (stat(member, "population") or 0) > (stat(seats[region], "population") or 0)):
            seats[region] = member
    named = 0
    for region, row in realm.territory.items():
        if "province" in row.locked:
            continue
        seat = seats.get(region)
        if seat is None:
            near = [other for other in book.atlas.neighbour_regions(region) if other in seats]
            seat = seats[min(near)] if near else None
        row.province = f"the province of {seat.name}" if seat is not None else row.province
        named += 1
    return named
