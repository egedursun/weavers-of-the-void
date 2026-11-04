from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow, HeirloomRow, HouseMemberRow, HouseProfileRow, OfficeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import ClaimBasis, HouseTrait, OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import HouseStats
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import has_room, match_bonus, may_wed, terms_of
from aerona.engine.faith.book import faith_tenets
from aerona.engine.lifecycle.succession import dynasty_root
from aerona.engine.mind.space import value_distance
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook, sex_of
from aerona.engine.polity.offices import whole
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat

TWENTY = 20
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
        emblem={"charge": root.lower(), "field": "or" if house.id % 2 else "sable"},
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
    if mortal.id in book.members[house_id]:
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
    if profile is None or mortal.birth_epoch < ctx.epoch:
        return
    traits = set(profile.traits)
    if HouseTrait.LONG_LIVED in traits:
        set_stats(mortal, lifespan=round_half_up((stat(mortal, "lifespan") or 0) * 1.15))
    if HouseTrait.GIANT_BLOODED in traits:
        set_stats(mortal, strength=clamp_int((stat(mortal, "strength") or 0) + 10, 0, PERCENT))
    if HouseTrait.SEER_GIFT in traits:
        set_stats(mortal, intellect=clamp_int((stat(mortal, "intellect") or 0) + 5, 0, PERCENT))
    if HouseTrait.CURSED in traits:
        set_stats(mortal, lifespan=round_half_up((stat(mortal, "lifespan") or 0) * 0.85))


async def values_of(ctx: TickContext, mortal: EntityRow) -> dict[ValueAxis, int]:
    people = await people_of(ctx.session, mortal)
    return await culture_of(ctx.session, people.id) if people is not None else {}


async def kin_ids(ctx: TickContext, mortal_id: int) -> tuple[set[int], set[int], set[int]]:
    up = {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], sources=[mortal_id])}
    down = {bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.DESCENDS_FROM], targets=[mortal_id])}
    spouses = {bond.other_end(mortal_id) for bond in await active_bonds(ctx.session, [BondKind.LOVES], sources=[mortal_id])}
    spouses |= {bond.other_end(mortal_id) for bond in await active_bonds(ctx.session, [BondKind.LOVES], targets=[mortal_id])}
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


async def gather_kin(ctx: TickContext, book: HouseBook) -> int:
    joined = 0
    for house_id, members in list(book.members.items()):
        for member_id in list(members):
            up, down, spouses = await kin_ids(ctx, member_id)
            for child_id in down | up:
                child = await living_entity(ctx.session, child_id)
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


async def inherit_claims(ctx: TickContext, child: EntityRow, parent_id: int) -> None:
    if child.birth_epoch < ctx.epoch - 1:
        return
    table = ctx.rules.houses
    throne = await ctx.session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == parent_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    if throne is not None:
        ctx.session.add(
            ClaimRow(
                claimant_entity_id=child.id,
                house_entity_id=None,
                polity_entity_id=throne.polity_entity_id,
                office=OfficeKind.RULER,
                strength=table.marriage_claim,
                basis=ClaimBasis.MARRIAGE,
                pressed=False,
                since_epoch=ctx.epoch,
            )
        )
    for claim in await ctx.session.scalars(select(ClaimRow).where(ClaimRow.claimant_entity_id == parent_id, ClaimRow.ended_epoch.is_(None))):
        strength = round_half_up(claim.strength * table.claim_inherit_pct / PERCENT)
        if strength <= 0:
            continue
        ctx.session.add(
            ClaimRow(
                claimant_entity_id=child.id,
                house_entity_id=claim.house_entity_id,
                polity_entity_id=claim.polity_entity_id,
                office=claim.office,
                strength=strength,
                basis=ClaimBasis.INHERITANCE,
                pressed=False,
                since_epoch=ctx.epoch,
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
        if profile is None:
            continue
        alive = await living(ctx, {member for member in book.members[house_id] if member in book.house_of and book.house_of[member] == house_id})
        if not alive:
            await extinguish(ctx, book, house_id, "its last member died")
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
            profile.prestige = clamp_int(profile.prestige - table.prestige_decay + gain, 0, PERCENT)
        set_stats(house, prestige=profile.prestige, members=len(alive), wealth=clamp_int(profile.wealth, 0, PERCENT))
        if len(alive) >= table.branch_members:
            await branch(ctx, book, house_id, alive)
            counts["branches"] += 1
        await keep_heirlooms(ctx, house_id, alive)
    return counts


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
    await note(
        ctx,
        f"{founder.name} split from {book.houses[house_id].name} and founded {cadet.name}, keeping a claim against the elder line.",
        key="houses.branch",
        ids=[cadet.id, house_id, founder.id],
        kind=ChronicleKind.CIVILIZATION,
    )


async def extinguish(ctx: TickContext, book: HouseBook, house_id: int, reason: str) -> None:
    house = book.houses.pop(house_id)
    profile = book.profiles.get(house_id)
    if profile is not None:
        profile.extinct_epoch = ctx.epoch
    for claim in await ctx.session.scalars(select(ClaimRow).where(ClaimRow.house_entity_id == house_id, ClaimRow.ended_epoch.is_(None))):
        claim.ended_epoch = ctx.epoch
    for heirloom in await ctx.session.scalars(select(HeirloomRow).where(HeirloomRow.house_entity_id == house_id)):
        item = await ctx.session.get(EntityRow, heirloom.item_entity_id)
        if item is not None and item.status is EntityStatus.CANON:
            await add_flag(ctx.session, item.id, EntityFlag.LOST, ctx.epoch)
        await ctx.session.delete(heirloom)
    await retire_in(ctx, house, reason, status=EntityStatus.DESTROYED)
    await note(ctx, f"{house.name} died out; {reason}. Its treasures were lost.", key="houses.extinct", ids=[house.id], kind=ChronicleKind.CIVILIZATION)


async def keep_heirlooms(ctx: TickContext, house_id: int, alive: list[EntityRow]) -> None:
    owners = [mortal.id for mortal in alive]
    held = set(await ctx.session.scalars(select(HeirloomRow.item_entity_id).where(HeirloomRow.house_entity_id == house_id)))
    items = await ctx.session.scalars(
        select(BondRow.target_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(owners))
    )
    for item_id in items:
        item = await ctx.session.get(EntityRow, item_id)
        if item is None or item.entity_type is not EntityType.ITEM or item.id in held or item.power_level < HEIRLOOM_POWER:
            continue
        if ctx.epoch - item.birth_epoch >= 1:
            ctx.session.add(HeirloomRow(item_entity_id=item.id, house_entity_id=house_id, since_epoch=ctx.epoch))
            held.add(item.id)


async def eligible(ctx: TickContext, mortal: EntityRow) -> bool:
    if (stat(mortal, "age") or 0) < ctx.rules.society.love_min_age:
        return False
    return await has_room(ctx.session, ctx.rules, mortal)


async def arrange_marriages(ctx: TickContext, book: HouseBook, realms: RealmBook) -> list[tuple[EntityRow, EntityRow]]:
    table = ctx.rules.houses
    pool: list[tuple[int, EntityRow]] = []
    for house_id in sorted(book.houses):
        for mortal in await living(ctx, book.members[house_id]):
            if book.house_of.get(mortal.id) == house_id and await eligible(ctx, mortal):
                pool.append((house_id, mortal))
    made: list[tuple[EntityRow, EntityRow]] = []
    taken: set[int] = set()
    for house_id, mortal in pool:
        if len(made) >= table.marriage_cap or mortal.id in taken:
            continue
        if not ctx.rng(f"marriage.{mortal.id}.{ctx.epoch}").chance(table.marriage_chance):
            continue
        mine = await values_of(ctx, mortal)
        best: tuple[float, EntityRow] | None = None
        for other_house, other in pool:
            if other_house == house_id or other.id in taken or other.world_id != mortal.world_id or sex_of(other) == sex_of(mortal):
                continue
            if not await may_wed(ctx.session, ctx.rules, mortal, other):
                continue
            theirs = await values_of(ctx, other)
            distance = value_distance(mine, theirs)
            if distance > FIT_DISTANCE:
                continue
            gain = (
                book.profiles[other_house].prestige
                - distance / 2
                + (TWENTY if realms.member_of.get(other.location_id or -1) != realms.member_of.get(mortal.location_id or -1) else 0)
                + match_bonus(ctx.rules, await terms_of(ctx.session, mortal), await terms_of(ctx.session, other))
            )
            if best is None or gain > best[0]:
                best = (gain, other)
        if best is None:
            continue
        spouse = best[1]
        await connect(ctx.session, mortal.id, spouse.id, BondKind.LOVES, ctx.epoch, description="arranged marriage")
        taken |= {mortal.id, spouse.id}
        made.append((mortal, spouse))
    return made
