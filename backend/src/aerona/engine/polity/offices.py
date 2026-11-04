from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, OfficeHistoryRow, OfficeRow
from aerona.domain.enums.body import LASTING_INJURY_STATES
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind, TraitKind
from aerona.domain.enums.polity import GenderRule, LawKind, OathKind, OfficeKind, SuccessionRule
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.military.causes import press_claim_war
from aerona.engine.mind.book import traits_of
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook, sex_of
from aerona.engine.polity.formation import set_ruler
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.oaths import swear
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat

S = SkillKind
OFFICE_SKILLS: Mapping[OfficeKind, tuple[tuple[SkillKind, ...], str]] = MappingProxyType(
    {
        OfficeKind.CHANCELLOR: ((S.NEGOTIATION, S.ETIQUETTE, S.ORATORY), "charisma"),
        OfficeKind.MARSHAL: ((S.TACTICS, S.STRATEGY, S.LEADERSHIP), "strength"),
        OfficeKind.TREASURER: ((S.ACCOUNTING, S.WRITING), "intellect"),
        OfficeKind.HIGH_JUDGE: ((S.LAW, S.LORE), "intellect"),
        OfficeKind.SPYMASTER: ((S.INTRIGUE, S.DECEPTION), "agility"),
        OfficeKind.GOVERNOR: ((S.LEADERSHIP, S.LAW, S.LOGISTICS), "charisma"),
        OfficeKind.AMBASSADOR: ((S.NEGOTIATION, S.LANGUAGES, S.ETIQUETTE), "charisma"),
        OfficeKind.REGENT: ((S.LEADERSHIP, S.LAW), "charisma"),
    }
)
COUNCIL = (OfficeKind.CHANCELLOR, OfficeKind.MARSHAL, OfficeKind.TREASURER, OfficeKind.HIGH_JUDGE, OfficeKind.SPYMASTER)
PROVINCE_TIER = 2
EMBASSY_TIER = 2


async def subjects(ctx: TickContext, realm: Realm) -> list[EntityRow]:
    members = list(realm.members)
    if not members:
        return []
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(members))
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def skill_score(ctx: TickContext, mortal: EntityRow, office: OfficeKind) -> float:
    skills, attribute = OFFICE_SKILLS[office]
    levels = await ctx.session.scalars(select(SkillRow.level).where(SkillRow.holder_node_id == mortal.id, SkillRow.skill.in_(list(skills))))
    return sum(levels) * 5 + (stat(mortal, attribute) or 0) + (mortal.importance or 0) / 10


def adult(ctx: TickContext, mortal: EntityRow) -> bool:
    return (stat(mortal, "age") or 0) >= ctx.rules.succession.regency_age


async def appoint(ctx: TickContext, realm: Realm, office: OfficeRow, holder: EntityRow | None, *, by_id: int | None, reason: str) -> None:
    if office.holder_entity_id is not None and office.id is not None:
        ctx.session.add(
            OfficeHistoryRow(
                office_id=office.id, holder_entity_id=office.holder_entity_id, from_epoch=office.since_epoch, to_epoch=ctx.epoch, reason=reason[:120]
            )
        )
    office.holder_entity_id = holder.id if holder is not None else None
    office.appointed_by_entity_id = by_id
    office.since_epoch = ctx.epoch
    if holder is not None and ctx.rules.oaths.fealty_on_office and realm.ruler_id is not None and holder.id != realm.ruler_id:
        await swear(ctx, holder, OathKind.FEALTY, recipient_id=realm.ruler_id, note_text=f"as {office.kind.value.replace('_', ' ')} of {realm.entity.name}")


def wanted_offices(book: RealmBook, realm: Realm) -> list[tuple[OfficeKind, int | None]]:
    tier = realm.profile.tier
    wanted: list[tuple[OfficeKind, int | None]] = [(kind, None) for kind in COUNCIL]
    if tier >= PROVINCE_TIER:
        capital_region = book.atlas.top_region(realm.profile.capital_entity_id or -1)
        wanted.extend((OfficeKind.GOVERNOR, region) for region in sorted(realm.territory) if region != capital_region)
    return wanted


async def staff(ctx: TickContext, book: RealmBook, realm: Realm, held: set[int]) -> int:
    people = [mortal for mortal in await subjects(ctx, realm) if adult(ctx, mortal) and mortal.id != realm.ruler_id]
    filled = 0
    for kind, region in wanted_offices(book, realm):
        office = next((row for row in realm.offices if row.kind is kind and row.region_entity_id == region), None)
        if office is None:
            office = OfficeRow(polity_entity_id=realm.entity.id, kind=kind, region_entity_id=region, since_epoch=ctx.epoch, powers=[])
            ctx.session.add(office)
            realm.offices.append(office)
            await ctx.session.flush()
        holder = await living_entity(ctx.session, office.holder_entity_id) if office.holder_entity_id is not None else None
        if holder is not None and holder.status is EntityStatus.CANON:
            held.add(holder.id)
            continue
        if "offices" in realm.profile.locked:
            continue
        candidates = [mortal for mortal in people if mortal.id not in held]
        if not candidates:
            continue
        scores = {mortal.id: await skill_score(ctx, mortal, kind) for mortal in candidates}
        best = max(candidates, key=lambda mortal: (scores[mortal.id], -mortal.id))
        await appoint(ctx, realm, office, best, by_id=realm.ruler_id, reason="the seat was empty")
        held.add(best.id)
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
    bonds = await ctx.session.scalars(
        select(BondRow).where(BondRow.kind == BondKind.DESCENDS_FROM, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == ruler.id)
    )
    children = [
        child for bond in bonds if (child := await living_entity(ctx.session, bond.source_node_id)) is not None and child.entity_type is EntityType.MORTAL
    ]
    grandchildren: list[EntityRow] = []
    for child in children:
        for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], targets=[child.id]):
            found = await living_entity(ctx.session, bond.source_node_id)
            if found is not None and found.entity_type is EntityType.MORTAL:
                grandchildren.append(found)
    parents = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[ruler.id])]
    siblings: list[EntityRow] = []
    for parent in parents:
        for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], targets=[parent]):
            found = await living_entity(ctx.session, bond.source_node_id)
            if found is not None and found.entity_type is EntityType.MORTAL and found.id != ruler.id and found not in siblings:
                siblings.append(found)
    return children, grandchildren, siblings


def gender_rank(rule: GenderRule, mortal: EntityRow) -> int | None:
    sex = sex_of(mortal)
    if rule is GenderRule.MALE_ONLY:
        return 0 if sex == "male" else None
    if rule is GenderRule.FEMALE_ONLY:
        return 0 if sex == "female" else None
    if rule is GenderRule.MALE_PREFERENCE:
        return 0 if sex == "male" else 1
    if rule is GenderRule.FEMALE_PREFERENCE:
        return 0 if sex == "female" else 1
    return 0


async def whole(ctx: TickContext, mortal: EntityRow) -> bool:
    found = await ctx.session.scalar(
        select(InjuryRow.id).where(InjuryRow.bearer_node_id == mortal.id, InjuryRow.state.in_(list(LASTING_INJURY_STATES))).limit(1)
    )
    return found is None


async def succession_line(ctx: TickContext, realm: Realm, laws: LawBook) -> list[EntityRow]:
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        return []
    polity = realm.entity.id
    rule = SuccessionRule(str(laws.param(polity, LawKind.SUCCESSION_RULE, "rule") or SuccessionRule.PRIMOGENITURE.value))
    gender = GenderRule(str(laws.param(polity, LawKind.SUCCESSION_RULE, "gender") or GenderRule.MALE_PREFERENCE.value))
    wholeness = bool(laws.param(polity, LawKind.SUCCESSION_RULE, "wholeness_required"))
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
        SuccessionRule.MATRILINEAL: [*[item for item in siblings if sex_of(item) == "female"], *grandchildren, *children],
        SuccessionRule.BY_COMBAT: [*children, *siblings, *housemates],
        SuccessionRule.DIVINE_CHOICE: [*children, *housemates, *siblings],
    }
    seen: set[int] = set()
    pool: list[EntityRow] = []
    for item in pools[rule]:
        if item.id not in seen:
            seen.add(item.id)
            pool.append(item)
    eligible = []
    for item in pool:
        rank = gender_rank(gender, item)
        if rank is None or (wholeness and not await whole(ctx, item)):
            continue
        eligible.append((rank, item))
    table = ctx.rules.succession
    order = {item.id: index for index, item in enumerate(pool)}

    def key(entry: tuple[int, EntityRow]) -> tuple[float, ...]:
        rank, item = entry
        age = stat(item, "age") or 0
        if rule is SuccessionRule.PRIMOGENITURE:
            return (order[item.id] >= len(children), rank, -age, item.id)
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
        if rule is SuccessionRule.MATRILINEAL:
            return (order[item.id], item.id)
        return (rank, -((stat(item, "strength") or 0) + (stat(item, "charisma") or 0) + (item.importance or 0)), item.id)

    return [item for _, item in sorted(eligible, key=key)]


async def name_heir(ctx: TickContext, realm: Realm, line: list[EntityRow]) -> EntityRow | None:
    if realm.ruler_id is None or "heir" in realm.profile.locked:
        return None
    heir = line[0] if line else None
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
    return heir


async def ensure_regent(ctx: TickContext, realm: Realm, ruler: EntityRow, held: set[int]) -> tuple[OfficeRow, EntityRow | None, bool]:
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
    held.add(regent.id)
    return office, regent, True


async def regency(ctx: TickContext, realm: Realm, held: set[int]) -> str | None:
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    if ruler is None:
        return None
    office = next((row for row in realm.offices if row.kind is OfficeKind.REGENT), None)
    if adult(ctx, ruler):
        if office is None or office.holder_entity_id is None:
            return None
        await appoint(ctx, realm, office, None, by_id=ruler.id, reason="the ruler came of age")
        return "ended"
    office, regent, fresh = await ensure_regent(ctx, realm, ruler, held)
    if regent is None or fresh:
        return "appointed" if fresh else None
    ambitious = TraitKind.AMBITIOUS in await traits_of(ctx.session, regent.id)
    if ambitious and ctx.rng(f"usurp.{realm.entity.id}.{ctx.epoch}").chance(ctx.rules.succession.usurp_chance):
        await usurp(ctx, realm, regent, ruler)
        return "usurped"
    return None


async def usurp(ctx: TickContext, realm: Realm, usurper: EntityRow, ruler: EntityRow) -> None:
    for bond in await active_bonds(ctx.session, [BondKind.RULES], sources=[ruler.id]):
        await close(ctx.session, bond, ctx.epoch, "usurped")
        await connect(ctx.session, usurper.id, bond.target_node_id, BondKind.RULES, ctx.epoch, description="usurped")
    set_ruler(ctx, realm, usurper.id, "usurped")
    realm.profile.legitimacy_parts = {**realm.profile.legitimacy_parts, "usurper": 1}
    await note(
        ctx,
        f"{usurper.name}, regent for the child {ruler.name}, took the throne of {realm.entity.name} for themself.",
        key="polity.usurped",
        ids=[usurper.id, ruler.id, realm.entity.id],
        kind=ChronicleKind.CIVILIZATION,
    )


async def press_claims(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    table = ctx.rules.succession
    if realm.ruler_id is None or realm.profile.legitimacy >= PERCENT // 2:
        return 0
    claims = await ctx.session.scalars(
        select(ClaimRow).where(ClaimRow.polity_entity_id == realm.entity.id, ClaimRow.ended_epoch.is_(None), ClaimRow.strength >= table.claim_press_pct)
    )
    wars = 0
    for claim in claims:
        claimant = await living_entity(ctx.session, claim.claimant_entity_id)
        if claimant is None or claimant.id == realm.ruler_id or claim.pressed:
            continue
        if not ctx.rng(f"press.{claim.id}.{ctx.epoch}").chance(table.war_chance * (PERCENT - realm.profile.legitimacy) / PERCENT * 2):
            continue
        claim.pressed = True
        core = book.entities.get(realm.profile.core_entity_id or -1)
        if core is None:
            continue
        host = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.FACTION,
                name=f"the party of {claimant.name}",
                body=f"Those who hold that {claimant.name}, not the crowned one, is the rightful ruler of {realm.entity.name}.",
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
        await connect(ctx.session, claimant.id, host.id, BondKind.MEMBER_OF, ctx.epoch, description="claimant")
        await press_claim_war(ctx, host.id, core.id, claim_id=claim.id, succession=True, reason=f"{claimant.name} pressed a claim to {realm.entity.name}")
        wars += 1
        await note(
            ctx,
            f"{claimant.name} would not bow: a war of succession broke out over {realm.entity.name}.",
            key="polity.succession_war",
            ids=[claimant.id, realm.entity.id, host.id],
            kind=ChronicleKind.CIVILIZATION,
        )
    return wars
