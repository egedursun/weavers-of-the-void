from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.intrigue import FavourRow
from aerona.db.tables.polity import HouseProfileRow, OfficeRow
from aerona.db.tables.regime import CoalitionMemberRow, PatronageTieRow, PowerBaseRow, RegimeRow, VenalOfficeRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.mind import ActKind, TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind, OfficePower
from aerona.domain.enums.regime import ClientRole, PowerStance
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.unions import UnionPurpose
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import may_wed
from aerona.engine.economy.purse import coin_of, points_of, receive_coin, take_coin, wealth_points
from aerona.engine.lore.civics import realm_allows
from aerona.engine.mind.book import traits_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mortal.kin import children_of, siblings_of, spouses_of
from aerona.engine.mortal.kinship import marry
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.offices import adult, appoint, powers_of, subjects
from aerona.engine.polity.revenue import mean_justice
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining
from aerona.engine.regime.book import HALF, clients_of

SEATS_KEPT = frozenset({OfficeKind.RULER, OfficeKind.HEIR_DESIGNATE, OfficeKind.REGENT})
TROOP_UNIT = 100


@dataclass
class PatronageTally:
    ties: int = 0
    lapsed: int = 0
    sold: int = 0
    recouped: int = 0
    sinecures: int = 0
    defiant: int = 0
    extorted: int = 0
    plotting: int = 0
    rotated: int = 0
    married: int = 0
    split: int = 0
    purged: int = 0


async def tie(ctx: TickContext, patron_id: int, client_id: int, *, role: ClientRole, strength: int, tally: PatronageTally) -> PatronageTieRow | None:
    if patron_id == client_id or held(client_id):
        return None
    row = await ctx.session.scalar(
        select(PatronageTieRow).where(PatronageTieRow.patron_node_id == patron_id, PatronageTieRow.client_entity_id == client_id).limit(1)
    )
    if row is None:
        row = PatronageTieRow(patron_node_id=patron_id, client_entity_id=client_id, role=role, strength=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        tally.ties += 1
    if "strength" not in row.locked:
        row.strength = clamp_int(max(row.strength, strength), 0, PERCENT)
    return row


async def bind_clients(ctx: TickContext, book: RealmBook, tally: PatronageTally) -> None:
    table = ctx.rules.clientelism
    favours = await ctx.session.execute(
        select(FavourRow, EntityRow)
        .join(EntityRow, EntityRow.id == FavourRow.owed_by_node_id)
        .where(FavourRow.honoured.is_(None), FavourRow.magnitude >= table.favour_at, EntityRow.entity_type == EntityType.MORTAL)
        .order_by(FavourRow.id)
    )
    for favour, client in favours.all():
        await tie(ctx, favour.owed_to_node_id, client.id, role=ClientRole.RETAINER, strength=favour.magnitude, tally=tally)
    servants = await ctx.session.execute(
        select(HouseholdRow.head_node_id, HouseholdMemberRow.member_node_id)
        .join(HouseholdMemberRow, HouseholdMemberRow.household_id == HouseholdRow.id)
        .where(HouseholdMemberRow.role == HouseholdRole.SERVANT, HouseholdRow.head_node_id.is_not(None))
        .order_by(HouseholdMemberRow.member_node_id)
    )
    for head, servant in servants.all():
        if head is not None and head != servant:
            await tie(ctx, head, servant, role=ClientRole.HOUSEHOLD, strength=table.office_strength, tally=tally)
    for realm in book.realms.values():
        for office in realm.offices:
            if office.holder_entity_id is None or office.appointed_by_entity_id is None:
                continue
            role = ClientRole.COMMANDER if OfficePower.COMMAND in powers_of(office) else ClientRole.OFFICIAL
            await tie(ctx, office.appointed_by_entity_id, office.holder_entity_id, role=role, strength=table.office_strength, tally=tally)
    await ctx.session.flush()


async def loosen_ties(ctx: TickContext, tally: PatronageTally) -> None:
    for row in list(await ctx.session.scalars(select(PatronageTieRow).order_by(PatronageTieRow.id))):
        if held(row.client_entity_id):
            continue
        shift(row, "strength", -ctx.rules.clientelism.decay)
        client = await living_entity(ctx.session, row.client_entity_id)
        if (row.strength <= 0 or client is None) and not row.locked:
            await ctx.session.delete(row)
            tally.lapsed += 1


async def institutional_strength(ctx: TickContext, laws: LawBook, realm: Realm) -> int:
    table = ctx.rules.clientelism
    capital = await ctx.session.get(EntityRow, realm.profile.capital_entity_id) if realm.profile.capital_entity_id is not None else None
    people = await people_of(ctx.session, capital) if capital is not None else None
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    literacy = culture.literacy if culture is not None else 0
    clerks = table.bureaucracy_strength * await realm_allows(ctx.session, realm, Technique.BUREAUCRACY)
    justice = await mean_justice(ctx, laws, realm)
    return clamp_int(clerks + justice * table.justice_weight / PERCENT + literacy * table.literacy_weight / PERCENT, 0, PERCENT)


def open_seat(office: OfficeRow) -> bool:
    return office.kind not in SEATS_KEPT and office.holder_entity_id is None and "holder" not in office.locked


async def unsold_seat(ctx: TickContext, realm: Realm) -> OfficeRow | None:
    for office in realm.offices:
        if open_seat(office) and await ctx.session.get(VenalOfficeRow, office.id) is None:
            return office
    return None


async def richest_buyer(ctx: TickContext, realm: Realm, taken: set[int]) -> EntityRow | None:
    best: tuple[int, EntityRow] | None = None
    for mortal in await subjects(ctx, realm):
        if mortal.id in taken or mortal.id == realm.ruler_id or held(mortal.id) or not adult(ctx, mortal):
            continue
        purse = await coin_of(ctx.session, ctx.rules, mortal)
        if best is None or (purse, -mortal.id) > (best[0], -best[1].id):
            best = (purse, mortal)
    return best[1] if best is not None else None


async def sell_office(ctx: TickContext, realm: Realm, row: RegimeRow, tally: PatronageTally) -> VenalOfficeRow | None:
    table = ctx.rules.venality
    short = max(0, HALF - row.horizon) / HALF
    if realm.profile.debt <= 0 and short <= 0:
        return None
    if not ctx.rng(f"regime.venal.{realm.entity.id}.{ctx.epoch}").chance(table.sell_pct * (1 + short)):
        return None
    seat = await unsold_seat(ctx, realm)
    if seat is None:
        return None
    return await sell_seat(ctx, realm, seat, price=table.base_price, tally=tally)


async def sell_seat(
    ctx: TickContext, realm: Realm, seat: OfficeRow, *, price: int, tally: PatronageTally, buyer: EntityRow | None = None
) -> VenalOfficeRow | None:
    taken = {office.holder_entity_id for office in realm.offices if office.holder_entity_id is not None}
    buyer = buyer or await richest_buyer(ctx, realm, taken)
    if buyer is None or not await take_coin(ctx.session, ctx.rules, buyer, price):
        return None
    spend(ctx, realm, price, TreasuryEntry.OFFICE_SALE, f"the seat of {spoken(seat.kind)} sold")
    await appoint(ctx, realm, seat, buyer, by_id=realm.ruler_id, reason="the seat was bought")
    venal = VenalOfficeRow(office_id=seat.id, price=price, buyer_entity_id=buyer.id, sinecure=False, recouped=0, sold_epoch=ctx.epoch, locked=[])
    ctx.session.add(venal)
    tally.sold += 1
    if realm.ruler_id is not None:
        await judged(ctx, realm.ruler_id, buyer.id, ActKind.SELLING_OFFICES, note=f"sold the seat of {spoken(seat.kind)}")
    await record(
        ctx,
        "venality.sold",
        roles={IncidentRole.BUYER: buyer.id, IncidentRole.SELLER: realm.entity.id, IncidentRole.AUTHORITY: realm.ruler_id},
        facts={"office": seat.kind, "price": price},
        place=realm.profile.capital_entity_id,
    )
    await ctx.session.flush()
    return venal


async def recoup(ctx: TickContext, realm: Realm, tally: PatronageTally) -> None:
    table = ctx.rules.venality
    for office in realm.offices:
        venal = await ctx.session.get(VenalOfficeRow, office.id)
        if venal is None or venal.sinecure or office.holder_entity_id is None or held(office.holder_entity_id):
            continue
        cap = venal.price * table.recoup_cap_pct // PERCENT
        if venal.recouped >= cap or "recouped" in venal.locked:
            continue
        holder = await living_entity(ctx.session, office.holder_entity_id)
        amount = min(cap - venal.recouped, venal.price * table.recoup_pct // PERCENT)
        if holder is None or amount <= 0:
            continue
        await receive_coin(ctx.session, ctx.rules, holder, amount)
        venal.recouped += amount
        tally.recouped += amount


async def grant_sinecure(ctx: TickContext, realm: Realm, row: RegimeRow, tally: PatronageTally) -> VenalOfficeRow | None:
    table = ctx.rules.venality
    if row.coalition_loyalty >= table.sinecure_at:
        return None
    seat = await unsold_seat(ctx, realm)
    members = list(
        await ctx.session.scalars(
            select(CoalitionMemberRow)
            .where(CoalitionMemberRow.polity_entity_id == realm.entity.id)
            .order_by(CoalitionMemberRow.reward, CoalitionMemberRow.mortal_entity_id)
        )
    )
    member = next((member for member in members if not held(member.mortal_entity_id)), None)
    holder = await living_entity(ctx.session, member.mortal_entity_id) if member is not None else None
    if seat is None or member is None or holder is None:
        return None
    return await make_sinecure(ctx, realm, seat, holder, member=member, tally=tally)


async def make_sinecure(
    ctx: TickContext, realm: Realm, seat: OfficeRow, holder: EntityRow, *, member: CoalitionMemberRow | None, tally: PatronageTally
) -> VenalOfficeRow:
    await appoint(ctx, realm, seat, holder, by_id=realm.ruler_id, reason="a sinecure for the ruler's circle")
    if "diligence" not in seat.locked:
        seat.diligence = 0
    if member is not None:
        shift(member, "reward", ctx.rules.venality.sinecure_reward)
    venal = await ctx.session.get(VenalOfficeRow, seat.id)
    if venal is None:
        venal = VenalOfficeRow(office_id=seat.id, price=0, buyer_entity_id=holder.id, sinecure=True, recouped=0, sold_epoch=ctx.epoch, locked=[])
        ctx.session.add(venal)
    venal.sinecure = True
    tally.sinecures += 1
    await record(
        ctx,
        "venality.sinecure",
        roles={IncidentRole.RECEIVER: holder.id, IncidentRole.GIVER: realm.entity.id, IncidentRole.AUTHORITY: realm.ruler_id},
        facts={"office": seat.kind, "reward": ctx.rules.venality.sinecure_reward if member is not None else 0},
        place=realm.profile.capital_entity_id,
    )
    await ctx.session.flush()
    return venal


async def holdings_of(ctx: TickContext, book: RealmBook, realm: Realm, mortal_id: int) -> int:
    towns = 0
    for office in realm.offices:
        if office.holder_entity_id == mortal_id and office.kind is OfficeKind.GOVERNOR and office.region_entity_id is not None:
            towns += len(book.atlas.communities_in(office.region_entity_id))
    houses = await ctx.session.scalars(select(HouseProfileRow).where(HouseProfileRow.head_entity_id == mortal_id))
    return towns + sum(len(house.seats) for house in houses)


async def troops_of(ctx: TickContext, mortal_id: int, clients: set[int]) -> int:
    commanders = [mortal_id, *clients]
    armies = await ctx.session.scalars(select(ArmyRow.entity_id).where(ArmyRow.commander_entity_id.in_(commanders), ArmyRow.disbanded_epoch.is_(None)))
    total = 0
    for army_id in armies:
        army = await ctx.session.get(EntityRow, army_id)
        total += stat_or(army, "size", 0) if army is not None else 0
    return total // TROOP_UNIT


async def weigh_base(ctx: TickContext, book: RealmBook, realm: Realm, mortal: EntityRow) -> tuple[int, int, int, int, int, int]:
    table = ctx.rules.power_bases
    clients = await clients_of(ctx.session, mortal.id)
    holdings = await holdings_of(ctx, book, realm, mortal.id)
    troops = await troops_of(ctx, mortal.id, clients)
    offices = sum(1 for office in realm.offices if office.holder_entity_id in {mortal.id, *clients} and office.kind is not OfficeKind.RULER)
    wealth = await points_of(ctx.session, mortal)
    popularity = clamp_int(mortal.importance or 0, 0, PERCENT)
    total = round_half_up(
        holdings * table.holding_weight
        + troops * table.troop_weight
        + offices * table.office_weight
        + wealth * table.wealth_weight / PERCENT
        + popularity * table.popularity_weight / PERCENT
    )
    return holdings, troops, offices, wealth, popularity, total


async def contenders(ctx: TickContext, realm: Realm) -> list[EntityRow]:
    found: dict[int, EntityRow] = {}
    holders = [office.holder_entity_id for office in realm.offices if office.holder_entity_id is not None and office.kind is not OfficeKind.RULER]
    heads = await ctx.session.scalars(select(HouseProfileRow.head_entity_id).where(HouseProfileRow.polity_entity_id == realm.entity.id))
    commanders = await ctx.session.scalars(
        select(ArmyRow.commander_entity_id).where(ArmyRow.owner_entity_id.in_([realm.entity.id, *realm.members]), ArmyRow.disbanded_epoch.is_(None))
    )
    for mortal_id in [*holders, *heads, *commanders]:
        if mortal_id is None or mortal_id == realm.ruler_id or mortal_id in found:
            continue
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is not None and mortal.entity_type is EntityType.MORTAL:
            found[mortal_id] = mortal
    return sorted(found.values(), key=lambda mortal: mortal.id)


async def stance_of(ctx: TickContext, mortal: EntityRow, threat: int, *, armed: bool) -> PowerStance:
    table = ctx.rules.power_bases
    if armed and threat >= table.plot_at and TraitKind.AMBITIOUS in await traits_of(ctx.session, mortal.id):
        return PowerStance.PLOTTING
    if armed and threat >= table.extort_at:
        return PowerStance.EXTORTING
    if threat >= table.defy_at:
        return PowerStance.DEFIANT
    return PowerStance.LOYAL


async def act_on_base(ctx: TickContext, realm: Realm, mortal: EntityRow, row: PowerBaseRow, tally: PatronageTally) -> None:
    table = ctx.rules.power_bases
    if row.stance is PowerStance.EXTORTING:
        spend(ctx, realm, -table.extortion, TreasuryEntry.GRANT, f"wrung from the treasury by {mortal.name}")
        await receive_coin(ctx.session, ctx.rules, mortal, table.extortion)
        tally.extorted += 1
        with explaining():
            await record(
                ctx,
                "power_bases.extorted",
                roles={IncidentRole.ACTOR: mortal.id, IncidentRole.VICTIM: realm.entity.id},
                facts={"amount": ctx.rules.power_bases.extortion, "threat": row.threat},
                place=mortal.location_id,
            )
    elif row.stance is PowerStance.DEFIANT:
        shift(realm.profile, "stability", -table.defiance_stability)
        tally.defiant += 1
    elif row.stance is PowerStance.PLOTTING:
        tally.plotting += 1


async def rotate(ctx: TickContext, realm: Realm, row: RegimeRow, bases: list[PowerBaseRow], tally: PatronageTally) -> None:
    if not row.rotation:
        return
    feared = next(
        (base for base in sorted(bases, key=lambda base: (-base.threat, base.mortal_entity_id)) if base.threat >= ctx.rules.power_bases.defy_at), None
    )
    if feared is None:
        return
    for office in realm.offices:
        if office.holder_entity_id == feared.mortal_entity_id and office.kind is not OfficeKind.RULER and "holder" not in office.locked:
            await appoint(ctx, realm, office, None, by_id=realm.ruler_id, reason="rotated so no command grows too strong")
            tally.rotated += 1


async def unwed_kin(ctx: TickContext, mortal_id: int | None) -> list[EntityRow]:
    if mortal_id is None:
        return []
    found: list[EntityRow] = []
    for kin_id in [mortal_id, *await children_of(ctx.session, mortal_id), *await siblings_of(ctx.session, mortal_id)]:
        kin = await living_entity(ctx.session, kin_id)
        if kin is not None and not held(kin.id) and adult(ctx, kin) and not await spouses_of(ctx.session, kin.id):
            found.append(kin)
    return found


async def bind_by_marriage(ctx: TickContext, realm: Realm, base: PowerBaseRow, subject: EntityRow) -> bool:
    for ours in await unwed_kin(ctx, realm.ruler_id):
        for theirs in await unwed_kin(ctx, subject.id):
            if ours.id != theirs.id and await may_wed(ctx.session, ctx.rules, ours, theirs):
                await marry(ctx.session, ours, theirs, ctx.epoch, purpose=UnionPurpose.ALLIANCE, description="a match to bind an overmighty subject")
                shift(base, "threat", -ctx.rules.power_bases.marriage_cut)
                if "stance" not in base.locked:
                    base.stance = PowerStance.LOYAL
                with explaining():
                    await record(
                        ctx,
                        "power_bases.married",
                        roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.TARGET: subject.id, IncidentRole.SPOUSE: [ours.id, theirs.id]},
                        facts={"threat_cut": ctx.rules.power_bases.marriage_cut, "threat": base.threat},
                        place=realm.profile.capital_entity_id,
                    )
                return True
    return False


async def split_command(ctx: TickContext, realm: Realm, subject: EntityRow) -> bool:
    armies = list(
        await ctx.session.scalars(
            select(ArmyRow).where(ArmyRow.commander_entity_id == subject.id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id)
        )
    )
    loose = [army for army in armies if not held(army.entity_id)]
    for army in loose:
        army.commander_entity_id = None
    if loose:
        await record(
            ctx,
            "power_bases.split",
            roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.TARGET: subject.id, IncidentRole.INSTRUMENT: [army.entity_id for army in loose]},
            facts={"hosts": len(loose)},
            place=realm.profile.capital_entity_id,
        )
    return bool(loose)


async def purge_subject(ctx: TickContext, realm: Realm, subject: EntityRow) -> bool:
    purged = False
    seats = 0
    for office in realm.offices:
        if office.holder_entity_id == subject.id and office.kind is not OfficeKind.RULER and "holder" not in office.locked:
            await appoint(ctx, realm, office, None, by_id=realm.ruler_id, reason="purged as an overmighty subject")
            purged = True
            seats += 1
    member = await ctx.session.get(CoalitionMemberRow, (realm.entity.id, subject.id))
    if member is not None and not member.locked:
        await ctx.session.delete(member)
        purged = True
    if purged:
        await record(
            ctx,
            "power_bases.purged",
            roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.VICTIM: subject.id},
            facts={"seats": seats},
            place=realm.profile.capital_entity_id,
        )
    return purged


async def answer_plotters(ctx: TickContext, realm: Realm, bases: list[PowerBaseRow], tally: PatronageTally) -> None:
    if realm.ruler_id is None or held(realm.ruler_id):
        return
    for base in sorted(bases, key=lambda base: (-base.threat, base.mortal_entity_id)):
        if base.stance is not PowerStance.PLOTTING or not ctx.rng(f"regime.counter.{realm.entity.id}.{base.mortal_entity_id}.{ctx.epoch}").chance(
            ctx.rules.power_bases.counter_pct
        ):
            continue
        subject = await living_entity(ctx.session, base.mortal_entity_id)
        if subject is None:
            continue
        if await bind_by_marriage(ctx, realm, base, subject):
            tally.married += 1
        elif await split_command(ctx, realm, subject):
            tally.split += 1
        elif await purge_subject(ctx, realm, subject):
            tally.purged += 1
        return


async def crown_strength(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    table = ctx.rules.power_bases
    ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
    own = (await weigh_base(ctx, book, realm, ruler))[-1] if ruler is not None else 0
    armies = await ctx.session.scalars(
        select(ArmyRow.entity_id).where(ArmyRow.owner_entity_id.in_([realm.entity.id, *realm.members]), ArmyRow.disbanded_epoch.is_(None))
    )
    soldiers = 0
    for army_id in armies:
        army = await ctx.session.get(EntityRow, army_id)
        soldiers += stat_or(army, "size", 0) if army is not None else 0
    purse = wealth_points(ctx.rules, max(0, realm.profile.treasury)) * table.wealth_weight / PERCENT
    standing = realm.profile.legitimacy * table.popularity_weight / PERCENT
    return round_half_up(own + len(realm.members) * table.holding_weight + soldiers // TROOP_UNIT * table.troop_weight + purse + standing)


async def measure_bases(ctx: TickContext, book: RealmBook, realm: Realm, row: RegimeRow, tally: PatronageTally) -> None:
    crown = await crown_strength(ctx, book, realm)
    cap = ctx.rules.coup_proofing.hostage_cap if row.hostages else PERCENT
    bases: list[PowerBaseRow] = []
    seen: set[int] = set()
    for mortal in await contenders(ctx, realm):
        if held(mortal.id):
            continue
        seen.add(mortal.id)
        base = await ctx.session.get(PowerBaseRow, mortal.id)
        if base is None:
            base = PowerBaseRow(mortal_entity_id=mortal.id, locked=[])
            ctx.session.add(base)
        holdings, troops, offices, wealth, popularity, total = await weigh_base(ctx, book, realm, mortal)
        for field, value in (
            ("holdings", holdings),
            ("troops", troops),
            ("offices", offices),
            ("wealth", wealth),
            ("popularity", popularity),
            ("total", total),
        ):
            if field not in base.locked:
                setattr(base, field, value)
        base.polity_entity_id = realm.entity.id
        if "threat" not in base.locked:
            base.threat = clamp_int(min(cap, base.total * HALF / max(1, crown)), 0, PERCENT)
        if "stance" not in base.locked:
            base.stance = await stance_of(ctx, mortal, base.threat, armed=base.holdings > 0 or base.troops > 0)
        base.updated_epoch = ctx.epoch
        await act_on_base(ctx, realm, mortal, base, tally)
        bases.append(base)
    for base in list(await ctx.session.scalars(select(PowerBaseRow).where(PowerBaseRow.polity_entity_id == realm.entity.id))):
        if base.mortal_entity_id not in seen and not base.locked and not held(base.mortal_entity_id):
            await ctx.session.delete(base)
    await rotate(ctx, realm, row, bases, tally)
    await answer_plotters(ctx, realm, bases, tally)


async def keep_patronage(ctx: TickContext, tally: PatronageTally) -> None:
    book = await RealmBook.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    await bind_clients(ctx, book, tally)
    await loosen_ties(ctx, tally)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        row = await ctx.session.get(RegimeRow, realm.entity.id)
        if row is None or held(realm.entity.id):
            continue
        if "institutions" not in row.locked:
            row.institutions = await institutional_strength(ctx, laws, realm)
        await sell_office(ctx, realm, row, tally)
        await recoup(ctx, realm, tally)
        await grant_sinecure(ctx, realm, row, tally)
        await measure_bases(ctx, book, realm, row, tally)
    await ctx.session.flush()
