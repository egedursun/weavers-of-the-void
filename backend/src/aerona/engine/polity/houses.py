from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.collective import HERALDIC_NAMES
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import ClaimRow, HeirloomRow, HouseMemberRow, HouseProfileRow, OfficeRow, SentenceRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import Tincture
from aerona.domain.enums.entity import HERO_ROLES, EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.intrigue import HookDemand
from aerona.domain.enums.mind import ActKind, MemoryKind, TraitKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import PunishmentKind
from aerona.domain.enums.polity import ClaimBasis, GenderRule, HouseEnd, HouseTrait, LawKind, OathBreach, OathKind, OfficeKind, OfficePower
from aerona.domain.enums.quests import QuestAim, QuestTargetKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.unions import PluralSide, UnionArrangement, UnionForm, UnionPurpose
from aerona.domain.enums.war import WarEnding
from aerona.domain.models.entity_stats import HouseStats
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import preference_bonus, sexes_fixed, system_of, union_of
from aerona.engine.cycles.sides import first_sex, second_sex, system_of_people
from aerona.engine.demography.kinship import has_room, match_bonus, may_wed, terms_of
from aerona.engine.faith.book import faith_tenets
from aerona.engine.genetics.genome import consanguinity
from aerona.engine.genetics.life import bless_blood, found_genome
from aerona.engine.genetics.lineage import blood_traits
from aerona.engine.intrigue.favours import hook_on
from aerona.engine.intrigue.leverage import leaned_on
from aerona.engine.lifecycle.succession import dynasty_root
from aerona.engine.mind.book import traits_of
from aerona.engine.mind.ethics import ethic_reading
from aerona.engine.mind.memories import remember
from aerona.engine.mind.space import value_distance
from aerona.engine.mortal.kin import children_of, parents_of, spouses_of
from aerona.engine.mortal.kinship import marriages_of, marry
from aerona.engine.phases.heroes import active_quest, start_quest
from aerona.engine.phases.society_support.quests import QuestOption
from aerona.engine.polity.book import RealmBook, sex_of
from aerona.engine.polity.law_effects import endogamous
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.oaths import break_oath, oaths_of
from aerona.engine.polity.offices import best_skill, whole
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import add_flag, connect, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record
from aerona.engine.unions.axes import Spousing, spousing_of
from aerona.engine.unions.customs import CONSENTS_NEEDED, line_house
from aerona.engine.unions.purpose import purpose_gain
from aerona.rules.registry import Rules

TWENTY = 20
SEEKER_ROLES = HERO_ROLES
FIT_DISTANCE = 50
HEIRLOOM_POWER = 3


class HouseBook:
    def __init__(self, profiles: dict[int, HouseProfileRow], houses: dict[int, EntityRow], members: dict[int, set[int]], house_of: dict[int, int]) -> None:
        self.profiles = profiles
        self.houses = houses
        self.members = members
        self.house_of = house_of

    @classmethod
    async def load(cls, ctx: TickContext) -> "HouseBook":
        houses = {
            row.id: row
            for row in await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.HOUSE, EntityRow.status == EntityStatus.CANON))
        }
        profiles = {row.house_entity_id: row for row in await ctx.session.scalars(select(HouseProfileRow)) if row.house_entity_id in houses}
        members: dict[int, set[int]] = defaultdict(set)
        house_of: dict[int, int] = {}
        for row in await ctx.session.scalars(select(HouseMemberRow)):
            if row.house_entity_id in houses:
                members[row.house_entity_id].add(row.mortal_entity_id)
                house_of.setdefault(row.mortal_entity_id, row.house_entity_id)
        return cls(profiles, houses, members, house_of)


async def found_house(ctx: TickContext, book: HouseBook, founder: EntityRow, *, parent: int | None = None, polity_id: int | None = None) -> EntityRow:
    root = dynasty_root(founder.name).split()[-1] if founder.name else "the Nameless"
    house = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.HOUSE,
            name=f"House {root}" if parent is None else f"House {root} the Younger",
            body=f"The kin of {founder.name}.",
            stats=HouseStats(prestige=20, members=1, wealth=0),
            power=max(1, founder.power_level),
            location_id=None,
            world_id=founder.world_id,
            subtype="cadet branch" if parent is not None else "house",
            pending=False,
        ),
    )
    traits: list[HouseTrait] = []
    if founder.creator_son_id is not None:
        traits.append(HouseTrait.GOD_BLOODED)
    profile = HouseProfileRow(
        house_entity_id=house.id,
        founder_entity_id=founder.id,
        head_entity_id=founder.id,
        parent_house_id=parent,
        polity_entity_id=polity_id,
        divine_son_id=founder.creator_son_id,
        prestige=20 + (ctx.rules.houses.divine_prestige if traits else 0),
        wealth=0,
        motto=None,
        emblem={"charge": root.lower(), "field": HERALDIC_NAMES[ctx.rng(f"house.field.{house.id}").pick(list(Tincture))]},
        traits=traits,
        seats=[founder.location_id] if founder.location_id is not None else [],
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(profile)
    book.houses[house.id] = house
    book.profiles[house.id] = profile
    await join(ctx, book, house.id, founder, by_marriage=False)
    if parent is not None:
        await connect(ctx.session, house.id, parent, BondKind.DESCENDS_FROM, ctx.epoch, description="cadet branch")
    ctx.count("houses_founded")
    return house


async def join(ctx: TickContext, book: HouseBook, house_id: int, mortal: EntityRow, *, by_marriage: bool) -> None:
    if mortal.id in book.members[house_id] or held(mortal.id, house_id):
        return
    previous = book.house_of.get(mortal.id)
    if previous is not None and not by_marriage:
        for row in await ctx.session.scalars(select(HouseMemberRow).where(HouseMemberRow.mortal_entity_id == mortal.id)):
            await ctx.session.delete(row)
        book.members[previous].discard(mortal.id)
    ctx.session.add(HouseMemberRow(house_entity_id=house_id, mortal_entity_id=mortal.id, joined_epoch=ctx.epoch, by_marriage=by_marriage))
    book.members[house_id].add(mortal.id)
    book.house_of[mortal.id] = house_id
    if not by_marriage:
        await bless(ctx, book.profiles.get(house_id), mortal)


async def bless(ctx: TickContext, profile: HouseProfileRow | None, mortal: EntityRow) -> None:
    if profile is None or mortal.birth_epoch < ctx.epoch or not profile.traits:
        return
    bless_blood(ctx.rules, mortal, await found_genome(ctx, mortal), [HouseTrait(trait) for trait in profile.traits])


async def values_of(ctx: TickContext, mortal: EntityRow) -> dict[ValueAxis, int]:
    people = await people_of(ctx.session, mortal)
    return await culture_of(ctx.session, people.id) if people is not None else {}


async def kin_ids(ctx: TickContext, mortal_id: int) -> tuple[set[int], set[int], set[int]]:
    up = set(await parents_of(ctx.session, mortal_id))
    down = set(await children_of(ctx.session, mortal_id))
    spouses = set(await spouses_of(ctx.session, mortal_id))
    return up, down, spouses


CLERGY = frozenset({MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER})


async def celibate(ctx: TickContext, mortal: EntityRow) -> bool:
    return mortal.mortal_role in CLERGY and mortal.location_id is not None and TenetKind.CELIBATE_CLERGY in await faith_tenets(ctx.session, mortal.location_id)


async def seed_houses(ctx: TickContext, book: HouseBook, realms: RealmBook) -> int:
    founded = 0
    for realm in realms.realms.values():
        ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
        if ruler is None or ruler.id in book.house_of:
            continue
        await found_house(ctx, book, ruler, polity_id=realm.entity.id)
        founded += 1
    nobles = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.social_class == SocialClass.NOBLE)
    )
    for noble in nobles:
        if noble.id not in book.house_of and not await celibate(ctx, noble):
            await found_house(ctx, book, noble, polity_id=realms.member_of.get(noble.location_id or -1))
            founded += 1
    return founded


async def claimed_elsewhere(ctx: TickContext, book: HouseBook, child_id: int, house_id: int) -> bool:
    parents = await parents_of(ctx.session, child_id)
    if len(parents) < 2:
        return False
    marriage = next((row for row in await marriages_of(ctx.session, parents[0]) if parents[1] in {row.first_id, row.second_id}), None)
    if marriage is None:
        return False
    prestige = {house: profile.prestige for house, profile in book.profiles.items()}
    line = await line_house(ctx.session, marriage, prestige, child_id)
    return line is not None and line != house_id and line in book.houses


async def gather_kin(ctx: TickContext, book: HouseBook) -> int:
    joined = 0
    for house_id, members in list(book.members.items()):
        for member_id in list(members):
            up, down, spouses = await kin_ids(ctx, member_id)
            for child_id in down | up:
                child = await living_entity(ctx.session, child_id)
                if child_id in down and await claimed_elsewhere(ctx, book, child_id, house_id):
                    continue
                if child is not None and child.entity_type is EntityType.MORTAL and child.id not in book.house_of:
                    await join(ctx, book, house_id, child, by_marriage=False)
                    await inherit_claims(ctx, child, member_id)
                    joined += 1
            for spouse_id in spouses:
                spouse = await living_entity(ctx.session, spouse_id)
                if spouse is not None and spouse.entity_type is EntityType.MORTAL and spouse.id not in book.house_of:
                    await join(ctx, book, house_id, spouse, by_marriage=True)
                    joined += 1
    return joined


def gender_share(rule: str | None, mortal: EntityRow) -> float:
    sex = sex_of(mortal)
    if rule == GenderRule.MALE_ONLY.value:
        return 1.0 if sex == "male" else 0.0
    if rule == GenderRule.FEMALE_ONLY.value:
        return 1.0 if sex == "female" else 0.0
    if rule == GenderRule.MALE_PREFERENCE.value:
        return 1.0 if sex == "male" else 0.5
    if rule == GenderRule.FEMALE_PREFERENCE.value:
        return 1.0 if sex == "female" else 0.5
    return 1.0


async def inherit_claims(ctx: TickContext, child: EntityRow, parent_id: int) -> None:
    if child.birth_epoch < ctx.epoch - 1:
        return
    table = ctx.rules.houses
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == child.id).limit(1))
    throne = await ctx.session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == parent_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    if throne is not None and not held(child.id, throne.polity_entity_id):
        rule = await law_param(ctx.session, throne.polity_entity_id, LawKind.SUCCESSION_RULE, "gender")
        share = gender_share(str(rule) if rule is not None else None, child)
        if share > 0:
            ctx.session.add(
                ClaimRow(
                    claimant_entity_id=child.id,
                    house_entity_id=house,
                    polity_entity_id=throne.polity_entity_id,
                    office=OfficeKind.RULER,
                    strength=round_half_up(PERCENT * table.claim_inherit_pct / PERCENT * share),
                    basis=ClaimBasis.INHERITANCE,
                    pressed=False,
                    since_epoch=ctx.epoch,
                    locked=[],
                )
            )
    for claim in await ctx.session.scalars(select(ClaimRow).where(ClaimRow.claimant_entity_id == parent_id, ClaimRow.ended_epoch.is_(None))):
        rule = await law_param(ctx.session, claim.polity_entity_id, LawKind.SUCCESSION_RULE, "gender")
        strength = round_half_up(claim.strength * table.claim_inherit_pct / PERCENT * gender_share(str(rule) if rule is not None else None, child))
        if strength <= 0:
            continue
        ctx.session.add(
            ClaimRow(
                claimant_entity_id=child.id,
                house_entity_id=claim.house_entity_id,
                polity_entity_id=claim.polity_entity_id,
                office=claim.office,
                strength=strength,
                basis=claim.basis if claim.basis in {ClaimBasis.CONQUEST, ClaimBasis.DIVINE} else ClaimBasis.INHERITANCE,
                pressed=False,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )


async def marriage_claims(ctx: TickContext, mortal: EntityRow, spouse: EntityRow) -> None:
    table = ctx.rules.houses
    for claim in await ctx.session.scalars(select(ClaimRow).where(ClaimRow.claimant_entity_id == spouse.id, ClaimRow.ended_epoch.is_(None))):
        rival = await ctx.session.scalar(
            select(ClaimRow.id).where(
                ClaimRow.claimant_entity_id == mortal.id, ClaimRow.polity_entity_id == claim.polity_entity_id, ClaimRow.ended_epoch.is_(None)
            )
        )
        if rival is None:
            ctx.session.add(
                ClaimRow(
                    claimant_entity_id=mortal.id,
                    house_entity_id=claim.house_entity_id,
                    polity_entity_id=claim.polity_entity_id,
                    office=claim.office,
                    strength=round_half_up(claim.strength * table.marriage_claim / PERCENT),
                    basis=ClaimBasis.MARRIAGE,
                    pressed=False,
                    since_epoch=ctx.epoch,
                    locked=[],
                )
            )


async def living(ctx: TickContext, ids: set[int]) -> list[EntityRow]:
    found = []
    for member_id in sorted(ids):
        mortal = await living_entity(ctx.session, member_id)
        if mortal is not None and mortal.status is EntityStatus.CANON:
            found.append(mortal)
    return found


async def tend(ctx: TickContext, book: HouseBook, realms: RealmBook) -> dict[str, int]:
    table = ctx.rules.houses
    counts = {"branches": 0, "extinct": 0}
    offices = {office.holder_entity_id: office for realm in realms.realms.values() for office in realm.offices if office.holder_entity_id is not None}
    for house_id, house in list(book.houses.items()):
        profile = book.profiles.get(house_id)
        if profile is None or held(house_id):
            continue
        alive = await living(ctx, {member for member in book.members[house_id] if member in book.house_of and book.house_of[member] == house_id})
        if not alive:
            await extinguish(ctx, book, house_id, HouseEnd.LAST_MEMBER_DIED)
            counts["extinct"] += 1
            continue
        if "head" not in profile.locked:
            head = next((mortal for mortal in alive if mortal.id in offices and offices[mortal.id].kind is OfficeKind.RULER), None)
            profile.head_entity_id = (head or max(alive, key=lambda mortal: (stat(mortal, "age") or 0, -mortal.id))).id
        if "prestige" not in profile.locked:
            gain = sum(table.prestige_office for mortal in alive if mortal.id in offices) + sum(
                round_half_up((mortal.importance or 0) / TWENTY * table.prestige_renown_per_20) for mortal in alive
            )
            if profile.polity_entity_id is not None and profile.polity_entity_id in realms.realms:
                parts = realms.realms[profile.polity_entity_id].profile.legitimacy_parts
                gain += table.prestige_victory if parts.get("legitimacy: victories", 0) > 0 else 0
                gain -= table.prestige_defeat if parts.get("legitimacy: defeats", 0) < 0 else 0
            if (await values_of(ctx, alive[0])).get(ValueAxis.PURITY, 0) > 0:
                maimed = len([mortal for mortal in alive if await realm_maimed(ctx, mortal)])
                gain -= maimed * table.prestige_maimed_purity
            gain += await deeds(ctx, realms, profile, alive)
            profile.prestige = clamp_int(profile.prestige - table.prestige_decay + gain, 0, PERCENT)
        await keep_seats(ctx, profile, alive)
        await earn(ctx, profile, alive, offices)
        await gain_traits(ctx, book, profile, alive)
        set_stats(house, prestige=profile.prestige, members=len(alive), wealth=clamp_int(profile.wealth, 0, PERCENT))
        if len(alive) >= table.branch_members:
            await branch(ctx, book, house_id, alive)
            counts["branches"] += 1
        await keep_heirlooms(ctx, house_id, alive)
        counts["feuds"] = counts.get("feuds", 0) + await feuds(ctx, book, house_id, alive)
        await anchor(ctx, profile, alive)
    counts["disputes"] = await disputes(ctx, book)
    return counts


async def ruling_realms(realms: RealmBook, alive: list[EntityRow]) -> list[int]:
    ids = {mortal.id for mortal in alive}
    return [realm.entity.id for realm in realms.realms.values() if realm.ruler_id in ids]


async def deeds(ctx: TickContext, realms: RealmBook, profile: HouseProfileRow, alive: list[EntityRow]) -> int:
    table = ctx.rules.houses
    gain = 0
    for realm_id in await ruling_realms(realms, alive):
        members = list(realms.realms[realm_id].members)
        wonders = await ctx.session.scalar(
            select(func.count(EntityRow.id)).where(
                EntityRow.engine_kind == EngineKind.WONDER, EntityRow.birth_epoch == ctx.epoch, EntityRow.location_id.in_(members or [-1])
            )
        )
        gain += int(wonders or 0) * table.prestige_wonder
        executed = await ctx.session.scalar(
            select(func.count(SentenceRow.id)).where(
                SentenceRow.epoch == ctx.epoch, SentenceRow.penalty == PunishmentKind.DEATH, SentenceRow.settlement_entity_id.in_(members or [-1])
            )
        )
        gain -= int(executed or 0) * table.prestige_execution
    for mortal in alive:
        repute = await ctx.session.get(MortalProfileRow, mortal.id)
        if repute is not None and repute.infamy:
            gain -= round_half_up(repute.infamy / PERCENT * table.prestige_infamy)
    return gain


async def keep_seats(ctx: TickContext, profile: HouseProfileRow, alive: list[EntityRow]) -> None:
    if "seats" in profile.locked:
        return
    ruled = await ctx.session.scalars(
        select(BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.kind == BondKind.RULES,
            BondRow.state == BondState.ACTIVE,
            BondRow.source_node_id.in_([mortal.id for mortal in alive]),
            EntityRow.entity_type == EntityType.SETTLEMENT,
        )
    )
    seats = sorted({*ruled, *(mortal.location_id for mortal in alive if mortal.id == profile.head_entity_id and mortal.location_id is not None)})
    profile.seats = seats or profile.seats


async def earn(ctx: TickContext, profile: HouseProfileRow, alive: list[EntityRow], offices: dict[int, OfficeRow]) -> None:
    if "wealth" in profile.locked:
        return
    table = ctx.rules.houses
    income = sum(table.office_income for mortal in alive if mortal.id in offices)
    for seat in profile.seats:
        place = await living_entity(ctx.session, seat)
        if place is not None:
            income += round_half_up((stat(place, "prosperity") or 0) * table.seat_income_pct / PERCENT)
    profile.wealth = max(0, profile.wealth + income - round_half_up(profile.wealth * table.wealth_decay_pct / PERCENT))


async def gain_traits(ctx: TickContext, book: HouseBook, profile: HouseProfileRow, alive: list[EntityRow]) -> None:
    if "traits" in profile.locked:
        return
    table = ctx.rules.houses
    owned = {HouseTrait(trait) for trait in profile.traits}
    found: list[HouseTrait] = []
    if HouseTrait.SEER_GIFT not in owned and any(mortal.mortal_role is MortalRole.SEER for mortal in alive):
        found.append(HouseTrait.SEER_GIFT)
    if HouseTrait.GIANT_BLOODED not in owned and sum(1 for mortal in alive if (stat(mortal, "strength") or 0) >= table.giant_strength) >= table.trait_members:
        found.append(HouseTrait.GIANT_BLOODED)
    elders = [mortal for mortal in alive if (stat(mortal, "lifespan") or 0) and (stat(mortal, "age") or 0) > (stat(mortal, "lifespan") or 0)]
    if HouseTrait.LONG_LIVED not in owned and len(elders) >= table.trait_members:
        found.append(HouseTrait.LONG_LIVED)
    young = [mortal for mortal in alive if (stat(mortal, "age") or 0) < ctx.rules.succession.regency_age]
    if HouseTrait.FERTILE not in owned and len(young) >= table.fertile_children:
        found.append(HouseTrait.FERTILE)
    cursed = [mortal for mortal in alive if await has_flag(ctx.session, mortal.id, EntityFlag.CURSED)]
    if HouseTrait.CURSED not in owned and len(cursed) >= table.trait_members:
        found.append(HouseTrait.CURSED)
    if HouseTrait.GOD_BLOODED not in owned and any(mortal.creator_son_id is not None for mortal in alive):
        found.append(HouseTrait.GOD_BLOODED)
        if profile.divine_son_id is None:
            profile.divine_son_id = next(mortal.creator_son_id for mortal in alive if mortal.creator_son_id is not None)
    found.extend(trait for trait in await blood_traits(ctx, alive, owned | set(found)) if trait not in found)
    for trait in found:
        if not ctx.rng(f"house_trait.{profile.house_entity_id}.{trait.value}.{ctx.epoch}").chance(table.trait_chance):
            continue
        profile.traits = [*profile.traits, trait]
        if profile.house_entity_id in book.houses:
            await record(
                ctx,
                f"houses.trait_{trait.value}",
                roles={IncidentRole.SUBJECT: profile.house_entity_id, IncidentRole.MEMBER: [mortal.id for mortal in alive]},
                facts={"chance": table.trait_chance, "members": len(alive)},
            )


async def bloodline_fertility(session: AsyncSession, rules: Rules, *mortal_ids: int) -> float:
    houses = set(await session.scalars(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id.in_(list(mortal_ids)))))
    if not houses:
        return 1.0
    traits = [set(row.traits) for row in await session.scalars(select(HouseProfileRow).where(HouseProfileRow.house_entity_id.in_(list(houses))))]
    factor = 1.0
    if any(HouseTrait.FERTILE in item for item in traits):
        factor *= rules.houses.fertile_pct / PERCENT
    if any(HouseTrait.CURSED in item for item in traits):
        factor *= rules.houses.cursed_fertility_pct / PERCENT
    return factor


async def feuds(ctx: TickContext, book: HouseBook, house_id: int, alive: list[EntityRow]) -> int:
    table = ctx.rules.houses
    ids = [mortal.id for mortal in alive]
    rows = await ctx.session.scalars(
        select(MemoryRow).where(
            MemoryRow.holder_node_id.in_(ids), MemoryRow.kind == MemoryKind.KILLED_KIN, MemoryRow.epoch == ctx.epoch, MemoryRow.subject_node_id.not_in(ids)
        )
    )
    made = 0
    for row in rows:
        rival = book.house_of.get(row.subject_node_id)
        if rival is None or rival == house_id:
            continue
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=house_id,
            subject_id=rival,
            kind=MemoryKind.KILLED_KIN,
            magnitude=-table.feud_memory,
            epoch=ctx.epoch,
            note="blood between the houses",
        )
        made += 1
    return made


async def feuding(session: AsyncSession, first: int, second: int) -> bool:
    found = await session.scalar(
        select(MemoryRow.id)
        .where(
            MemoryRow.kind == MemoryKind.KILLED_KIN,
            ((MemoryRow.holder_node_id == first) & (MemoryRow.subject_node_id == second))
            | ((MemoryRow.holder_node_id == second) & (MemoryRow.subject_node_id == first)),
        )
        .limit(1)
    )
    return found is not None


async def anchor(ctx: TickContext, profile: HouseProfileRow, alive: list[EntityRow]) -> None:
    if profile.divine_son_id is None or HouseTrait.GOD_BLOODED not in profile.traits:
        return
    son = await ctx.session.get(SonRow, profile.divine_son_id)
    if son is None or son.status is not SonStatus.ACTIVE:
        return
    son.existence = clamp_int(son.existence + min(ctx.rules.houses.anchor_cap, len(alive) * ctx.rules.houses.anchor_per_member), 0, PERCENT)


async def disputes(ctx: TickContext, book: HouseBook) -> int:
    split = 0
    pressed = await ctx.session.scalars(select(ClaimRow).where(ClaimRow.pressed.is_(True), ClaimRow.ended_epoch.is_(None), ClaimRow.since_epoch <= ctx.epoch))
    for claim in pressed:
        house_id = book.house_of.get(claim.claimant_entity_id)
        profile = book.profiles.get(house_id) if house_id is not None else None
        if profile is None or profile.head_entity_id == claim.claimant_entity_id or "branches" in profile.locked:
            continue
        ruler = await ctx.session.scalar(
            select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == claim.polity_entity_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
        )
        if ruler is None or book.house_of.get(ruler) != house_id:
            continue
        claimant = await living_entity(ctx.session, claim.claimant_entity_id)
        if claimant is None or house_id is None:
            continue
        cadet = await found_house(ctx, book, claimant, parent=house_id, polity_id=profile.polity_entity_id)
        claim.house_entity_id = cadet.id
        _, down, _ = await kin_ids(ctx, claimant.id)
        for member_id in sorted(down & book.members[house_id]):
            child = await living_entity(ctx.session, member_id)
            if child is not None:
                await join(ctx, book, cadet.id, child, by_marriage=False)
        await record(
            ctx,
            "houses.dispute_split",
            roles={IncidentRole.ACTOR: claimant.id, IncidentRole.PREDECESSOR: house_id, IncidentRole.PRODUCT: cadet.id, IncidentRole.OPPONENT: ruler},
            facts={"realm": claim.polity_entity_id, "claim": claim.strength, "kin": len(down & book.members[house_id])},
            place=claimant.location_id,
        )
        split += 1
    return split


async def realm_maimed(ctx: TickContext, mortal: EntityRow) -> bool:
    return not await whole(ctx, mortal)


async def branch(ctx: TickContext, book: HouseBook, house_id: int, alive: list[EntityRow]) -> None:
    profile = book.profiles[house_id]
    candidates = [mortal for mortal in alive if mortal.id != profile.head_entity_id]
    scored = []
    for mortal in candidates:
        _, down, _ = await kin_ids(ctx, mortal.id)
        scored.append((len(down & book.members[house_id]), mortal))
    if not scored:
        return
    count, founder = max(scored, key=lambda item: (item[0], -item[1].id))
    if count <= 0:
        return
    cadet = await found_house(ctx, book, founder, parent=house_id, polity_id=profile.polity_entity_id)
    _, down, _ = await kin_ids(ctx, founder.id)
    for member_id in sorted(down & book.members[house_id]):
        child = await living_entity(ctx.session, member_id)
        if child is not None:
            await join(ctx, book, cadet.id, child, by_marriage=False)
    if profile.polity_entity_id is not None:
        ctx.session.add(
            ClaimRow(
                claimant_entity_id=founder.id,
                house_entity_id=cadet.id,
                polity_entity_id=profile.polity_entity_id,
                office=OfficeKind.RULER,
                strength=30,
                basis=ClaimBasis.INHERITANCE,
                pressed=False,
                since_epoch=ctx.epoch,
            )
        )
    await record(
        ctx,
        "houses.branch",
        roles={IncidentRole.ACTOR: founder.id, IncidentRole.PREDECESSOR: house_id, IncidentRole.PRODUCT: cadet.id},
        facts={"kin": count, "claim_on": profile.polity_entity_id},
        place=founder.location_id,
    )


async def extinguish(ctx: TickContext, book: HouseBook, house_id: int, reason: HouseEnd, *, occasion: int | None = None) -> None:
    house = book.houses.pop(house_id)
    profile = book.profiles.get(house_id)
    if profile is not None:
        profile.extinct_epoch = ctx.epoch
    for claim in await ctx.session.scalars(select(ClaimRow).where(ClaimRow.house_entity_id == house_id, ClaimRow.ended_epoch.is_(None))):
        claim.ended_epoch = ctx.epoch
    heir_house = await heir_house_of(ctx, book, profile)
    passed = lost = 0
    for heirloom in await ctx.session.scalars(select(HeirloomRow).where(HeirloomRow.house_entity_id == house_id)):
        item = await ctx.session.get(EntityRow, heirloom.item_entity_id)
        if heir_house is not None and item is not None and item.status is EntityStatus.CANON:
            heirloom.house_entity_id = heir_house
            heirloom.since_epoch = ctx.epoch
            passed += 1
            continue
        if item is not None and item.status is EntityStatus.CANON:
            await add_flag(ctx.session, item.id, EntityFlag.LOST, ctx.epoch)
            await relic_quest(ctx, item, house)
            lost += 1
        await ctx.session.delete(heirloom)
    await retire_in(ctx, house, spoken(reason), status=EntityStatus.DESTROYED)
    if profile is not None and profile.divine_son_id is not None and HouseTrait.GOD_BLOODED in profile.traits:
        son = await ctx.session.get(SonRow, profile.divine_son_id)
        if son is not None and son.status is SonStatus.ACTIVE:
            son.existence = clamp_int(son.existence - ctx.rules.houses.anchor_loss, 0, PERCENT)
            await record(
                ctx,
                "houses.divine_line_ended",
                roles={IncidentRole.SUBJECT: house.id, IncidentRole.PATRON: son.id},
                facts={"existence_lost": ctx.rules.houses.anchor_loss},
                son_id=son.id,
            )
    heir = heir_house if heir_house is not None and heir_house in book.houses else None
    await record(
        ctx,
        "houses.extinct" if heir is not None else "houses.extinct_lost",
        roles={IncidentRole.SUBJECT: house.id, IncidentRole.HEIR: heir},
        facts={"end": reason, "occasion": occasion, "passed": passed, "lost": lost},
    )
    ctx.count("heirlooms_passed", passed)
    ctx.count("heirlooms_lost", lost)


async def heir_house_of(ctx: TickContext, book: HouseBook, profile: HouseProfileRow | None) -> int | None:
    if profile is None:
        return None
    split = await law_param(ctx.session, profile.polity_entity_id, LawKind.INHERITANCE_SPLIT, "split") if profile.polity_entity_id is not None else None
    if split is None:
        return None
    if profile.parent_house_id is not None and profile.parent_house_id in book.houses:
        return profile.parent_house_id
    cadets = [other for other, row in book.profiles.items() if row.parent_house_id == profile.house_entity_id and other in book.houses]
    return min(cadets) if cadets else None


async def relic_quest(ctx: TickContext, item: EntityRow, house: EntityRow) -> None:
    seekers = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role.in_(list(SEEKER_ROLES)))
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )
    seeker = next(iter(seekers), None)
    if seeker is not None and not await active_quest(ctx.session, seeker.id):
        await start_quest(ctx, seeker, QuestOption(QuestAim.FIND, QuestTargetKind.ITEM, item.id, 1.0, f"to find {item.name}, lost with {house.name}"))
        await record(
            ctx,
            "houses.relic_quest",
            roles={IncidentRole.ACTOR: seeker.id, IncidentRole.INSTRUMENT: item.id, IncidentRole.PREDECESSOR: house.id},
            place=seeker.location_id,
        )


async def keep_heirlooms(ctx: TickContext, house_id: int, alive: list[EntityRow]) -> None:
    owners = [mortal.id for mortal in alive]
    kept = set(await ctx.session.scalars(select(HeirloomRow.item_entity_id)))
    items = await ctx.session.scalars(
        select(BondRow.target_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(owners))
    )
    for item_id in items:
        item = await ctx.session.get(EntityRow, item_id)
        if item is None or item.entity_type is not EntityType.ITEM or item.id in kept or item.power_level < HEIRLOOM_POWER:
            continue
        if ctx.epoch - item.birth_epoch >= 1:
            ctx.session.add(HeirloomRow(item_entity_id=item.id, house_entity_id=house_id, since_epoch=ctx.epoch))
            kept.add(item.id)


async def eligible(ctx: TickContext, mortal: EntityRow) -> bool:
    if (stat(mortal, "age") or 0) < ctx.rules.society.love_min_age:
        return False
    return await has_room(ctx.session, ctx.rules, mortal)


async def arrange_marriages(ctx: TickContext, book: HouseBook, realms: RealmBook) -> list[tuple[EntityRow, EntityRow]]:
    table = ctx.rules.houses
    pool: list[tuple[int, EntityRow]] = []
    for house_id in sorted(book.houses):
        for mortal in await living(ctx, book.members[house_id]):
            if book.house_of.get(mortal.id) == house_id and not held(mortal.id) and await eligible(ctx, mortal):
                pool.append((house_id, mortal))
    made: list[tuple[EntityRow, EntityRow]] = []
    taken: set[int] = set()
    for house_id, mortal in pool:
        if len(made) >= table.marriage_cap or mortal.id in taken:
            continue
        if not ctx.rng(f"marriage.{mortal.id}.{ctx.epoch}").chance(table.marriage_chance):
            continue
        mine = await values_of(ctx, mortal)
        kin_admired = await ethic_reading(ctx.session, ctx.rules, mortal.id, ActKind.INCEST, mine) > 0
        custom = await custom_of(ctx, mortal)
        closed = bool(ctx.rules.legislation.endogamy_strict) and await endogamous(ctx.session, mortal.location_id)
        people = await people_of(ctx.session, mortal)
        best: tuple[float, EntityRow] | None = None
        for other_house, other in pool:
            if (
                other_house == house_id
                or other.id in taken
                or not await suitable(ctx, (house_id, mortal), (other_house, other), custom, people if closed else None)
            ):
                continue
            if not await may_wed(ctx.session, ctx.rules, mortal, other):
                continue
            theirs = await values_of(ctx, other)
            distance = value_distance(mine, theirs)
            if distance > FIT_DISTANCE and await hook_on(ctx, mortal.id, other.id) is None:
                continue
            blood = await consanguinity(ctx.session, ctx.rules, mortal.id, other.id)
            kin_pull = ctx.rules.genetics.kin_claim_pull if kin_admired else -ctx.rules.genetics.kin_marriage_fear
            gain = (
                blood * kin_pull / PERCENT
                + book.profiles[other_house].prestige
                - distance / 2
                + (TWENTY if realms.member_of.get(other.location_id or -1) != realms.member_of.get(mortal.location_id or -1) else 0)
                + match_bonus(ctx.rules, await terms_of(ctx.session, mortal), await terms_of(ctx.session, other))
                + await preference_bonus(ctx.session, ctx.rules, mortal, other)
                + await claim_weight(ctx, other) * table.claim_weight_pct / PERCENT
                + await purpose_gain(ctx, mortal, other, book.profiles[other_house].prestige)
            )
            if best is None or gain > best[0]:
                best = (gain, other)
        union = await union_of(ctx.session, mortal)
        if best is None or not await consents(ctx, union, (mortal, mine), best[1]):
            continue
        spouse = best[1]
        await marry(ctx.session, mortal, spouse, ctx.epoch, purpose=UnionPurpose.ALLIANCE, description="arranged marriage")
        await marriage_claims(ctx, mortal, spouse)
        await union_portion(ctx, book, house_id, spouse)
        await break_celibacy(ctx, mortal, spouse)
        taken |= wed(custom, mortal, spouse, await plural_sex(ctx, mortal, custom))
        made.append((mortal, spouse))
    return made


async def willing_match(ctx: TickContext, mortal: EntityRow, mine: dict[ValueAxis, int], spouse: EntityRow) -> bool:
    if value_distance(mine, await values_of(ctx, spouse)) <= FIT_DISTANCE:
        return True
    return await leaned_on(ctx, mortal.id, spouse.id, HookDemand.MARRIAGE)


async def consents(ctx: TickContext, union: UnionCustomRow | None, mine: tuple[EntityRow, dict[ValueAxis, int]], spouse: EntityRow) -> bool:
    mortal, values = mine
    needed = CONSENTS_NEEDED[union.arrangement] if union is not None else 1
    if needed >= 1 and not await willing_match(ctx, mortal, values, spouse):
        return False
    return needed < CONSENTS_NEEDED[UnionArrangement.BOTH_CONSENT] or await willing_match(ctx, spouse, await values_of(ctx, spouse), mortal)


async def suitable(ctx: TickContext, mine: tuple[int, EntityRow], theirs: tuple[int, EntityRow], custom: Spousing, people: EntityRow | None) -> bool:
    house_id, mortal = mine
    other_house, other = theirs
    fixed = sexes_fixed(await system_of(ctx.session, mortal))
    if other.world_id != mortal.world_id or (custom.form is not UnionForm.GROUP and fixed and sex_of(other) == sex_of(mortal)):
        return False
    if people is not None and (await people_of(ctx.session, other)) != people:
        return False
    return not await feuding(ctx.session, house_id, other_house)


def wed(custom: Spousing, mortal: EntityRow, spouse: EntityRow, plural: str | None) -> set[int]:
    if custom.form is UnionForm.GROUP:
        return {spouse.id}
    if custom.form is UnionForm.PLURAL:
        return {spouse.id} | ({mortal.id} if plural is not None and sex_of(mortal) != plural else set())
    return {mortal.id, spouse.id}


async def plural_sex(ctx: TickContext, mortal: EntityRow, custom: Spousing) -> str | None:
    if custom.form is not UnionForm.PLURAL or custom.side is PluralSide.EITHER:
        return None
    people = await people_of(ctx.session, mortal)
    system = await system_of_people(ctx.session, people.id if people is not None else None)
    if system is None:
        return None
    return first_sex(system) if custom.side is PluralSide.FIRST else second_sex(system)


async def custom_of(ctx: TickContext, mortal: EntityRow) -> Spousing:
    custom = spousing_of(await union_of(ctx.session, mortal))
    if mortal.location_id is None:
        return custom
    form = await law_param(ctx.session, mortal.location_id, LawKind.MARRIAGE_LAW, "form")
    side = await law_param(ctx.session, mortal.location_id, LawKind.MARRIAGE_LAW, "plural_side")
    return Spousing(UnionForm(str(form)) if form is not None else custom.form, PluralSide(str(side)) if side is not None else custom.side, custom.endogamy)


async def claim_weight(ctx: TickContext, mortal: EntityRow) -> int:
    return sum(await ctx.session.scalars(select(ClaimRow.strength).where(ClaimRow.claimant_entity_id == mortal.id, ClaimRow.ended_epoch.is_(None))))


async def union_portion(ctx: TickContext, book: HouseBook, house_id: int, spouse: EntityRow) -> None:
    giver = book.house_of.get(spouse.id)
    if giver is None or giver not in book.profiles or house_id not in book.profiles:
        return
    amount = round_half_up(book.profiles[giver].wealth * ctx.rules.houses.union_portion_pct / PERCENT)
    if amount:
        move_amount(book.profiles[giver], book.profiles[house_id], "wealth", amount)


async def break_celibacy(ctx: TickContext, *mortals: EntityRow) -> None:
    for mortal in mortals:
        for oath in await oaths_of(ctx, mortal.id, OathKind.CELIBACY):
            await break_oath(ctx, oath, OathBreach.MARRIAGE_MADE)


DYNASTY_FIXUP = "houses_dynasty_ancestors"
ANCESTOR_DEPTH = 6


async def dynasty_backfill(ctx: TickContext, book: HouseBook) -> int:
    if await ctx.session.get(AppliedFixupRow, DYNASTY_FIXUP) is not None:
        return 0
    added = 0
    for house_id, house in list(book.houses.items()):
        root = house.name.removeprefix("House ").removesuffix(" the Younger")
        frontier = set(book.members.get(house_id, set()))
        seen = set(frontier)
        for _ in range(ANCESTOR_DEPTH):
            parents = set(
                await ctx.session.scalars(
                    select(BondRow.source_node_id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.target_node_id.in_(list(frontier) or [-1]))
                )
            )
            closed = set(
                await ctx.session.scalars(
                    select(BondRow.target_node_id).where(BondRow.kind == BondKind.DESCENDS_FROM, BondRow.source_node_id.in_(list(frontier) or [-1]))
                )
            )
            frontier = (parents | closed) - seen
            if not frontier:
                break
            seen |= frontier
            for ancestor_id in sorted(frontier):
                ancestor = await ctx.session.get(EntityRow, ancestor_id)
                if ancestor is None or ancestor.entity_type is not EntityType.MORTAL or ancestor.status is EntityStatus.CANON:
                    continue
                if dynasty_root(ancestor.name).split()[-1] != root or ancestor.id in book.house_of:
                    continue
                ctx.session.add(HouseMemberRow(house_entity_id=house_id, mortal_entity_id=ancestor.id, joined_epoch=ancestor.birth_epoch, by_marriage=False))
                book.house_of[ancestor.id] = house_id
                added += 1
    ctx.session.add(AppliedFixupRow(key=DYNASTY_FIXUP, result={"ancestors": added}))
    await ctx.session.flush()
    return added


async def conquest_claims(ctx: TickContext, realms: RealmBook) -> int:
    made = 0
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch == ctx.epoch, WarRow.ending == WarEnding.CONQUEST)):
        victor, loser = realms.realm_of(war.victor_entity_id), realms.realm_of(war.loser_entity_id)
        if victor is None or loser is None or victor.entity.id == loser.entity.id or victor.ruler_id is None:
            continue
        rival = await ctx.session.scalar(
            select(ClaimRow.id).where(
                ClaimRow.claimant_entity_id == victor.ruler_id, ClaimRow.polity_entity_id == loser.entity.id, ClaimRow.ended_epoch.is_(None)
            )
        )
        if rival is not None:
            continue
        ctx.session.add(
            ClaimRow(
                claimant_entity_id=victor.ruler_id,
                house_entity_id=await ctx.session.scalar(
                    select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == victor.ruler_id).limit(1)
                ),
                polity_entity_id=loser.entity.id,
                office=OfficeKind.RULER,
                strength=ctx.rules.houses.conquest_claim,
                basis=ClaimBasis.CONQUEST,
                pressed=False,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        made += 1
    return made


async def fabricate_claims(ctx: TickContext, realms: RealmBook) -> int:
    table = ctx.rules.houses
    made = 0
    for realm in realms.realms.values():
        if realm.ruler_id is None or realm.profile.core_entity_id is None:
            continue
        ruler = await living_entity(ctx.session, realm.ruler_id)
        if ruler is None or TraitKind.AMBITIOUS not in await traits_of(ctx.session, ruler.id):
            continue
        spy = await best_skill(ctx, realm, OfficePower.SPY)
        if spy <= 0 or not ctx.rng(f"fabricate.{realm.entity.id}.{ctx.epoch}").chance(table.fabricate_chance * spy):
            continue
        rivals = [other for other in realms.realms.values() if other.entity.id != realm.entity.id and other.entity.world_id == realm.entity.world_id]
        if not rivals:
            continue
        target = ctx.rng(f"fabricate_target.{realm.entity.id}.{ctx.epoch}").pick(sorted(rivals, key=lambda other: other.entity.id))
        ctx.session.add(
            ClaimRow(
                claimant_entity_id=ruler.id,
                house_entity_id=await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == ruler.id).limit(1)),
                polity_entity_id=target.entity.id,
                office=OfficeKind.RULER,
                strength=round_half_up(table.fabricated_claim * spy),
                basis=ClaimBasis.FABRICATED,
                pressed=False,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        await record(
            ctx,
            "houses.fabricated_claim",
            roles={IncidentRole.SUBJECT: realm.entity.id, IncidentRole.TARGET: target.entity.id, IncidentRole.ACTOR: ruler.id},
            facts={"strength": round_half_up(table.fabricated_claim * spy), "chance": table.fabricate_chance * spy, "basis": ClaimBasis.FABRICATED},
            place=realm.profile.capital_entity_id,
        )
        made += 1
    return made
