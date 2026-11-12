from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.total import total
from aerona.db.tables.cycles import GiftRow
from aerona.db.tables.dominion import MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.regime import CoalitionMemberRow, RegimeRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.polity import ClaimBasis, DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.regime import LeadershipMode, LegitimacyType, Routinisation, SelectorateKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import psi_of
from aerona.engine.factions.balance import power_balance
from aerona.engine.lore.civics import realm_allows
from aerona.engine.lore.legends import foretold_return
from aerona.engine.mortal.kin import children_of, siblings_of
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.control import grant_claim
from aerona.engine.polity.governance import spend
from aerona.engine.polity.offices import appoint, subjects
from aerona.engine.polity.standing import secede, war_record
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import has_flag, living_entity
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.regime.book import HALF, PROOFING, dominant, strongest_threat
from aerona.engine.relations.book import relation

SELECTORATES = total(
    GovernmentKind,
    {
        GovernmentKind.CHIEFDOM: SelectorateKind.TRIBE,
        GovernmentKind.TRIBAL_CONFEDERATION: SelectorateKind.TRIBE,
        GovernmentKind.MONARCHY: SelectorateKind.NOBLES,
        GovernmentKind.EMPIRE: SelectorateKind.NOBLES,
        GovernmentKind.OLIGARCHY: SelectorateKind.COUNCIL,
        GovernmentKind.HIVE_COUNCIL: SelectorateKind.COUNCIL,
        GovernmentKind.REPUBLIC: SelectorateKind.CITIZENS,
        GovernmentKind.THEOCRACY: SelectorateKind.PRIESTS,
        GovernmentKind.GOD_KINGDOM: SelectorateKind.PRIESTS,
        GovernmentKind.OCCUPATION: SelectorateKind.ARMY,
    },
)
SELECTING_CLASSES = total(
    SelectorateKind,
    {
        SelectorateKind.TRIBE: (),
        SelectorateKind.NOBLES: (SocialClass.NOBLE,),
        SelectorateKind.COUNCIL: (SocialClass.NOBLE, SocialClass.MERCHANT),
        SelectorateKind.ARMY: (SocialClass.WARRIOR,),
        SelectorateKind.PRIESTS: (SocialClass.PRIEST,),
        SelectorateKind.CITIZENS: (),
    },
)
COALITION_RULES = total(
    DecisionRule,
    {
        DecisionRule.AUTOCRATIC: "autocratic_pct",
        DecisionRule.COUNCIL: "council_rule_pct",
        DecisionRule.ASSEMBLY: "assembly_pct",
        DecisionRule.DIVINE: "divine_pct",
    },
)
TRIBAL = frozenset({GovernmentKind.CHIEFDOM, GovernmentKind.TRIBAL_CONFEDERATION})
LOWER_CLASSES = (SocialClass.FARMER, SocialClass.ARTISAN)
ELITES = (SocialClass.NOBLE, SocialClass.PRIEST, SocialClass.WARRIOR, SocialClass.SCRIBE, SocialClass.MERCHANT)
LAW_TECHNIQUES = (Technique.WRITTEN_LAW, Technique.CODIFIED_LAW)


@dataclass
class RegimeTally:
    seeded: int = 0
    public_goods: int = 0
    private_goods: int = 0
    purged: int = 0
    routinised: int = 0
    schisms: int = 0
    fragmented: int = 0
    chiefdoms: int = 0
    measures: int = 0


def ruling_mode(government: GovernmentKind) -> LeadershipMode:
    return LeadershipMode.ACHIEVED if government in TRIBAL else LeadershipMode.STATE


async def regime_row(ctx: TickContext, realm: Realm, tally: RegimeTally | None = None) -> RegimeRow:
    row = await ctx.session.get(RegimeRow, realm.entity.id)
    if row is not None:
        return row
    founder = realm.ruler_id if ctx.epoch - realm.profile.founded_epoch <= ctx.rules.charisma_routinisation.founder_epochs else None
    row = RegimeRow(
        polity_entity_id=realm.entity.id,
        selectorate=SELECTORATES[realm.profile.government],
        leadership=ruling_mode(realm.profile.government),
        founder_entity_id=founder,
        ruler_entity_id=realm.ruler_id,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if tally is not None:
        tally.seeded += 1
    return row


async def selectorate_size(ctx: TickContext, book: RealmBook, realm: Realm, kind: SelectorateKind) -> int:
    found = await choosers(ctx, book, realm, kind, SELECTING_CLASSES[kind])
    if found <= 0 and SELECTING_CLASSES[kind]:
        found = await choosers(ctx, book, realm, kind, ELITES)
    return round_half_up(found)


async def choosers(ctx: TickContext, book: RealmBook, realm: Realm, kind: SelectorateKind, classes: tuple[SocialClass, ...]) -> float:
    table = ctx.rules.selectorate
    found = 0.0
    for member in book.members(realm):
        people = stat_or(member, "population", 0)
        if kind is SelectorateKind.TRIBE:
            found += people * table.adult_pct / PERCENT
            continue
        if kind is SelectorateKind.CITIZENS:
            found += people * table.citizen_pct / PERCENT
            continue
        shares = await class_shares(ctx.session, ctx.rules, member.id)
        share = sum(shares.get(social_class, 0.0) for social_class in classes) / PERCENT
        found += people * share * (table.council_pct / PERCENT if kind is SelectorateKind.COUNCIL else 1)
    return found


async def concentration(ctx: TickContext, realm: Realm) -> float:
    shares = await power_balance(ctx, realm)
    whole = sum(shares.values())
    return max(shares.values()) / whole if whole else 0.0


async def size_coalition(ctx: TickContext, book: RealmBook, realm: Realm, row: RegimeRow) -> None:
    table = ctx.rules.selectorate
    if "selectorate" not in row.locked:
        row.selectorate = SELECTORATES[realm.profile.government]
    if "selectorate_size" not in row.locked:
        row.selectorate_size = await selectorate_size(ctx, book, realm, row.selectorate)
    if "coalition_size" not in row.locked:
        narrowed = 1 - await concentration(ctx, realm) * table.balance_weight / PERCENT
        row.coalition_size = round_half_up(row.selectorate_size * getattr(table, COALITION_RULES[realm.profile.decision_rule]) / PERCENT * narrowed)
    if "public_share" in row.locked:
        return
    reach = row.coalition_size / max(1, row.selectorate_size)
    invest = max(0, row.horizon - HALF) * ctx.rules.time_horizon.invest_public / HALF
    row.public_share = clamp_int(table.public_floor + (PERCENT - table.public_floor) * reach + invest, 0, PERCENT)


async def members_of(ctx: TickContext, polity_id: int) -> list[CoalitionMemberRow]:
    return list(
        await ctx.session.scalars(
            select(CoalitionMemberRow).where(CoalitionMemberRow.polity_entity_id == polity_id).order_by(CoalitionMemberRow.mortal_entity_id)
        )
    )


async def keep_members(ctx: TickContext, realm: Realm, row: RegimeRow) -> list[CoalitionMemberRow]:
    table = ctx.rules.selectorate
    classes = SELECTING_CLASSES[row.selectorate]
    subjects_of = await subjects(ctx, realm)
    if classes and not any(mortal.social_class in classes for mortal in subjects_of):
        classes = ELITES
    pool = [
        mortal
        for mortal in subjects_of
        if mortal.id != realm.ruler_id and mortal.status is EntityStatus.CANON and (not classes or mortal.social_class in classes)
    ]
    chosen = {mortal.id for mortal in sorted(pool, key=lambda mortal: (-(mortal.importance or 0), mortal.id))[: table.coalition_seats]}
    rows = {member.mortal_entity_id: member for member in await members_of(ctx, realm.entity.id)}
    for mortal_id in sorted(chosen - set(rows)):
        if held(mortal_id):
            continue
        rows[mortal_id] = CoalitionMemberRow(polity_entity_id=realm.entity.id, mortal_entity_id=mortal_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(rows[mortal_id])
    for mortal_id, member in list(rows.items()):
        if mortal_id not in chosen and not member.locked and not held(mortal_id) and await living_entity(ctx.session, mortal_id) is None:
            await ctx.session.delete(member)
            del rows[mortal_id]
    await ctx.session.flush()
    return list(rows.values())


def forget_rewards(ctx: TickContext, members: list[CoalitionMemberRow]) -> None:
    for member in members:
        if not held(member.mortal_entity_id):
            shift(member, "reward", -ctx.rules.selectorate.reward_decay)


async def spend_goods(ctx: TickContext, book: RealmBook, realm: Realm, row: RegimeRow, *, members: list[CoalitionMemberRow], tally: RegimeTally) -> None:
    table = ctx.rules.selectorate
    budget = realm.profile.treasury * table.spend_pct // PERCENT
    if budget <= 0:
        return
    public = budget * row.public_share // PERCENT
    private = budget - public
    towns = [member for member in book.members(realm) if not held(member.id)]
    if public > 0 and towns:
        rise = min(table.prosperity_cap, public / len(towns) / table.coin_per_prosperity)
        content = min(table.satisfaction_cap, public / len(towns) / table.coin_per_prosperity)
        for town in towns:
            shift_stat(town, "prosperity", rise)
            society = await ctx.session.get(CommunitySocietyRow, town.id)
            if society is not None:
                for social_class in LOWER_CLASSES:
                    field = f"satisfaction_{social_class.value}"
                    setattr(society, field, clamp_int(getattr(society, field) + content, 0, PERCENT))
        spend(ctx, realm, -public, TreasuryEntry.INVESTMENT, "public goods")
        tally.public_goods += public
    if private > 0 and members:
        each = private / len(members) / table.reward_per_coin
        for member in members:
            if not held(member.mortal_entity_id):
                shift(member, "reward", each)
        spend(ctx, realm, -private, TreasuryEntry.GRANT, "gifts to the winning coalition")
        tally.private_goods += private


async def sway_members(ctx: TickContext, realm: Realm, row: RegimeRow, members: list[CoalitionMemberRow]) -> None:
    table = ctx.rules.selectorate
    offer = await strongest_threat(ctx.session, realm.entity.id) * table.rival_offer_pct / PERCENT
    for member in members:
        if held(member.mortal_entity_id):
            continue
        regard = await relation(ctx.session, member.mortal_entity_id, realm.ruler_id) if realm.ruler_id is not None else None
        opinion = (regard.friendship - regard.rivalry) * table.opinion_weight / PERCENT if regard is not None else 0
        target = HALF + member.reward - offer + opinion
        shift(member, "loyalty", (target - member.loyalty) * table.loyalty_drift_pct / PERCENT)
    if members and "coalition_loyalty" not in row.locked:
        row.coalition_loyalty = clamp_int(sum(member.loyalty for member in members) / len(members), 0, PERCENT)


async def purge_coalition(ctx: TickContext, realm: Realm, row: RegimeRow, members: list[CoalitionMemberRow], tally: RegimeTally) -> int | None:
    table = ctx.rules.selectorate
    open_members = [member for member in members if not member.locked and not held(member.mortal_entity_id)]
    if row.coalition_loyalty >= table.purge_at or not open_members or not ctx.rng(f"regime.purge.{realm.entity.id}.{ctx.epoch}").chance(table.purge_pct):
        return None
    victim = min(open_members, key=lambda member: (member.loyalty, member.mortal_entity_id))
    return await purge_member(ctx, realm, victim, tally)


async def purge_member(ctx: TickContext, realm: Realm, victim: CoalitionMemberRow, tally: RegimeTally) -> int:
    mortal_id = victim.mortal_entity_id
    await ctx.session.delete(victim)
    for office in realm.offices:
        if office.holder_entity_id == mortal_id and office.kind is not OfficeKind.RULER and "holder" not in office.locked:
            await appoint(ctx, realm, office, None, by_id=realm.ruler_id, reason="purged from the ruling circle")
    tally.purged += 1
    mortal = await ctx.session.get(EntityRow, mortal_id)
    await note(
        ctx,
        f"{realm.entity.name} cast {mortal.name if mortal else 'a courtier'} out of the ruling circle.",
        key="regime.purged",
        ids=[realm.entity.id, mortal_id],
    )
    await ctx.session.flush()
    return mortal_id


async def has_heir(ctx: TickContext, realm: Realm) -> bool:
    if realm.ruler_id is None:
        return False
    designate = realm.office(OfficeKind.HEIR_DESIGNATE)
    if designate is not None and designate.holder_entity_id is not None:
        return True
    return await ctx.session.get(DesignatedHeirRow, realm.ruler_id) is not None


async def wonders_of(ctx: TickContext, ruler: EntityRow | None) -> float:
    table = ctx.rules.legitimacy_types
    if ruler is None:
        return 0.0
    since = ctx.epoch - table.miracle_epochs
    miracles = int(
        await ctx.session.scalar(
            select(func.count()).select_from(MiracleRecordRow).where(MiracleRecordRow.credited_node_id == ruler.id, MiracleRecordRow.epoch > since)
        )
        or 0
    )
    foretold = table.prophecy_charisma if await foretold_return(ctx, ruler) else 0
    return miracles * table.miracle_charisma + foretold


async def legitimacy_targets(ctx: TickContext, realm: Realm, ruler: EntityRow | None) -> dict[LegitimacyType, float]:
    table = ctx.rules.legitimacy_types
    seat = realm.office(OfficeKind.RULER)
    tenure = ctx.epoch - seat.since_epoch if seat is not None else 0
    usurped = "usurper" in realm.profile.legitimacy_parts
    traditional = min(PERCENT, tenure * PERCENT / table.tenure_epochs) + table.heir_tradition * await has_heir(ctx, realm) - table.usurper_tradition * usurped
    won, lost, _ = await war_record(ctx, realm)
    charisma = (stat_or(ruler, "charisma", 0) + (ruler.importance or 0)) / 2 if ruler is not None else 0
    chosen = (
        table.chosen_charisma if ruler is not None and (ruler.creator_son_id is not None or await has_flag(ctx.session, ruler.id, EntityFlag.CHOSEN)) else 0
    )
    charismatic = charisma + chosen + won * table.victory_charisma - lost * table.defeat_charisma + await wonders_of(ctx, ruler)
    rational = (
        table.bureaucracy_rational * await realm_allows(ctx.session, realm, Technique.BUREAUCRACY)
        + sum([table.law_rational for technique in LAW_TECHNIQUES if await realm_allows(ctx.session, realm, technique)])
        - realm.profile.corruption * table.corruption_rational / PERCENT
    )
    return {LegitimacyType.TRADITIONAL: traditional, LegitimacyType.CHARISMATIC: charismatic, LegitimacyType.RATIONAL: rational}


async def weigh_legitimacy(ctx: TickContext, realm: Realm, row: RegimeRow, ruler: EntityRow | None) -> None:
    drift = ctx.rules.legitimacy_types.drift_pct
    for kind, target in (await legitimacy_targets(ctx, realm, ruler)).items():
        field = kind.value
        shift(row, field, (clamp_int(target, 0, PERCENT) - getattr(row, field)) * drift / PERCENT)


async def routinise(ctx: TickContext, book: RealmBook, realm: Realm, row: RegimeRow, tally: RegimeTally) -> None:
    table = ctx.rules.charisma_routinisation
    previous = row.ruler_entity_id
    if row.founder_entity_id is None and realm.ruler_id is not None and "founder_entity_id" not in row.locked and row.charismatic >= table.founder_charisma:
        row.founder_entity_id = realm.ruler_id
    if row.routinisation is Routinisation.PENDING and "routinisation" not in row.locked and (row.crisis_epoch or 0) < ctx.epoch:
        await turn_charisma(ctx, realm, row, tally)
    if previous == realm.ruler_id:
        return
    row.ruler_entity_id = realm.ruler_id
    if previous is None:
        return
    dead = await living_entity(ctx.session, previous) is None
    if not dead:
        shift(row, "traditional", -ctx.rules.legitimacy_types.usurper_tradition)
    if dead and previous == row.founder_entity_id and dominant(row) is LegitimacyType.CHARISMATIC and "routinisation" not in row.locked:
        row.routinisation = Routinisation.PENDING
        row.crisis_epoch = ctx.epoch
        await note(
            ctx, f"The founder of {realm.entity.name} is dead, and all ask what will hold the realm together now.", key="regime.crisis", ids=[realm.entity.id]
        )
    if dead and row.leadership is LeadershipMode.ACHIEVED:
        await fragment(ctx, book, realm, tally)


async def rival_claim(ctx: TickContext, realm: Realm, founder_id: int | None) -> int | None:
    kin = await living_kin(ctx, founder_id)
    claimant = next((mortal for mortal in kin if mortal.id != realm.ruler_id and not held(mortal.id)), None)
    if claimant is None:
        return None
    try:
        await grant_claim(ctx, claimant.id, realm.entity.id, strength=ctx.rules.charisma_routinisation.schism_claim, basis=ClaimBasis.INHERITANCE)
    except (NotFoundError, ValidationFailedError):
        return None
    await note(
        ctx,
        f"{claimant.name} claimed {realm.entity.name} for the founder's line against the heir.",
        key="regime.rival_claim",
        ids=[realm.entity.id, claimant.id],
    )
    return claimant.id


async def living_kin(ctx: TickContext, founder_id: int | None) -> list[EntityRow]:
    if founder_id is None:
        return []
    found: list[EntityRow] = []
    for kin_id in [*await children_of(ctx.session, founder_id), *await siblings_of(ctx.session, founder_id)]:
        mortal = await living_entity(ctx.session, kin_id)
        if mortal is not None:
            found.append(mortal)
    return sorted(found, key=lambda mortal: (-(mortal.importance or 0), mortal.id))


async def turn_charisma(ctx: TickContext, realm: Realm, row: RegimeRow, tally: RegimeTally) -> None:
    table = ctx.rules.charisma_routinisation
    founder_id = row.founder_entity_id
    converted = row.charismatic * table.convert_pct / PERCENT
    if ctx.rng(f"regime.schism.{realm.entity.id}.{ctx.epoch}").chance(table.schism_pct):
        row.routinisation = Routinisation.SCHISM
        shift(realm.profile, "stability", -table.schism_stability)
        tally.schisms += 1
        await rival_claim(ctx, realm, founder_id)
        await note(
            ctx,
            f"The death of its founder split {realm.entity.name}: the faithful of the founder would not follow the heir.",
            key="regime.schism",
            ids=[realm.entity.id],
        )
    elif await realm_allows(ctx.session, realm, Technique.BUREAUCRACY) or await realm_allows(ctx.session, realm, Technique.WRITTEN_LAW):
        row.routinisation = Routinisation.INSTITUTION
        shift(row, "rational", converted)
        await note(ctx, f"{realm.entity.name} turned its founder's charisma into offices and written rules.", key="regime.institution", ids=[realm.entity.id])
    else:
        row.routinisation = Routinisation.DYNASTY
        shift(row, "traditional", converted)
        await note(ctx, f"{realm.entity.name} turned its founder's charisma into the right of a dynasty.", key="regime.dynasty", ids=[realm.entity.id])
    shift(row, "charismatic", -converted)
    if "founder_entity_id" not in row.locked:
        row.founder_entity_id = None
    tally.routinised += 1


async def fragment(ctx: TickContext, book: RealmBook, realm: Realm, tally: RegimeTally) -> None:
    capital = realm.profile.capital_entity_id
    members = [member for member in book.members(realm) if member.id != capital and not held(member.id)]
    leaving = members[: round_half_up(len(members) * ctx.rules.charisma_routinisation.fragment_pct / PERCENT)]
    for member in leaving:
        await secede(ctx, book, realm, member)
    if leaving:
        tally.fragmented += len(leaving)
        await note(
            ctx,
            f"With its big-man dead, {len(leaving)} of the following of {realm.entity.name} went their own way.",
            key="regime.fragmented",
            ids=[realm.entity.id],
        )


async def reckon_horizon(ctx: TickContext, realm: Realm, row: RegimeRow, ruler: EntityRow | None) -> None:
    table = ctx.rules.time_horizon
    if ruler is None:
        span = 0.0
    else:
        lifespan = max(1, stat_or(ruler, "lifespan", 1))
        span = max(0, lifespan - stat_or(ruler, "age", 0)) * PERCENT / lifespan * stat_or(ruler, "hp", PERCENT) / PERCENT
    threat = max(await psi_of(ctx.session, realm.entity.id), await strongest_threat(ctx.session, realm.entity.id))
    _, _, fighting = await war_record(ctx, realm)
    horizon = (
        span / 2
        + realm.profile.legitimacy * table.legitimacy_weight / PERCENT
        + table.heir_horizon * await has_heir(ctx, realm)
        - threat * table.threat_weight / PERCENT
        - table.war_horizon * fighting
    )
    if "horizon" not in row.locked:
        row.horizon = clamp_int(horizon, 0, PERCENT)
    if "extraction" not in row.locked:
        gap = (HALF - row.horizon) / HALF
        row.extraction = clamp_int(PERCENT + gap * (table.plunder_pct if gap > 0 else table.invest_pct), 0, PERCENT * 2)


async def proof_against_coups(ctx: TickContext, realm: Realm, row: RegimeRow, tally: RegimeTally) -> None:
    table = ctx.rules.coup_proofing
    danger = max(await psi_of(ctx.session, realm.entity.id), await strongest_threat(ctx.session, realm.entity.id))
    if danger >= table.insecure_at and ctx.rng(f"regime.proof.{realm.entity.id}.{ctx.epoch}").chance(table.adopt_pct):
        field = next((field for field in PROOFING if not getattr(row, field) and field not in row.locked), None)
        if field is not None:
            setattr(row, field, True)
            tally.measures += 1
            await note(ctx, f"{realm.entity.name} guarded its throne against the army: {field.replace('_', ' ')}.", key="regime.proofed", ids=[realm.entity.id])
    elif danger < table.secure_at:
        field = next((field for field in reversed(PROOFING) if getattr(row, field) and field not in row.locked), None)
        if field is not None:
            setattr(row, field, False)
    if row.parallel_guard:
        spend(ctx, realm, -table.guard_upkeep, TreasuryEntry.UPKEEP, "a parallel guard")


async def lead(ctx: TickContext, realm: Realm, row: RegimeRow, tally: RegimeTally) -> None:
    table = ctx.rules.leadership_modes
    if "leadership" in row.locked:
        return
    if realm.profile.government not in TRIBAL:
        row.leadership = LeadershipMode.STATE
        return
    if row.leadership is LeadershipMode.STATE:
        row.leadership = ruling_mode(realm.profile.government)
    if row.leadership is LeadershipMode.ACHIEVED and realm.ruler_id is not None:
        given = int(
            await ctx.session.scalar(select(func.count()).select_from(GiftRow).where(GiftRow.giver_node_id == realm.ruler_id, GiftRow.epoch == ctx.epoch)) or 0
        )
        shift(realm.profile, "legitimacy", given * table.gift_following)
        if row.horizon >= table.chief_horizon and ctx.rng(f"regime.chief.{realm.entity.id}.{ctx.epoch}").chance(table.chief_pct):
            row.leadership = LeadershipMode.ASCRIBED
            tally.chiefdoms += 1
            await note(ctx, f"The following of {realm.entity.name} became a chiefdom that passes by descent.", key="regime.chiefdom", ids=[realm.entity.id])


async def keep_regimes(ctx: TickContext, tally: RegimeTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        row = await regime_row(ctx, realm, tally)
        ruler = await living_entity(ctx.session, realm.ruler_id) if realm.ruler_id is not None else None
        await reckon_horizon(ctx, realm, row, ruler)
        await size_coalition(ctx, book, realm, row)
        members = await keep_members(ctx, realm, row)
        forget_rewards(ctx, members)
        await spend_goods(ctx, book, realm, row, members=members, tally=tally)
        await sway_members(ctx, realm, row, members)
        await purge_coalition(ctx, realm, row, members, tally)
        await weigh_legitimacy(ctx, realm, row, ruler)
        await routinise(ctx, book, realm, row, tally)
        await proof_against_coups(ctx, realm, row, tally)
        await lead(ctx, realm, row, tally)
        row.updated_epoch = ctx.epoch
    await ctx.session.flush()
