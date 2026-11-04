from collections import defaultdict

from sqlalchemy import func, select

from aerona.catalog.lore import IDEOLOGY_VALUES
from aerona.catalog.mind import DOMAIN_VALUES
from aerona.constants.units import PERCENT
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.culture import IdeologyTenetRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow, QuarantineRow
from aerona.db.tables.mind import PersonalityValueRow
from aerona.db.tables.polity import LawProfileRow, PolityTreasuryRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import MarriageCustom
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.mind import TraitKind, ValueAxis
from aerona.domain.enums.polity import DecisionRule, LawKind, LegitimacyBasis, OfficeKind, SuccessionRule
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import INHERITANCE_RULES
from aerona.engine.lore.research import lacks
from aerona.engine.mind.book import traits_of
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import LawBook, discord, enact, repeal, settle_justice
from aerona.engine.polity.standing import war_record
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import add_district

CREED_SCALE = 10
LEAN = 25
BASELINE_LAWS = frozenset({LawKind.SUCCESSION_RULE, LawKind.SLAVERY, LawKind.RELIGIOUS_TOLERANCE, LawKind.TAX_RATE, LawKind.PENAL_CODE})
COUNCIL_KINDS = 5


async def base_will(ctx: TickContext, realm: Realm) -> dict[ValueAxis, int]:
    profile = realm.profile
    core = profile.core_entity_id
    if profile.decision_rule is DecisionRule.DIVINE and profile.patron_son_id is not None:
        son = await ctx.session.get(SonRow, profile.patron_son_id)
        if son is not None:
            merged: dict[ValueAxis, int] = defaultdict(int)
            for domain in (son.domain_primary, son.domain_secondary):
                for axis, value in DOMAIN_VALUES.get(domain, {}).items():
                    merged[axis] += value
            return dict(merged)
    if profile.decision_rule is DecisionRule.AUTOCRATIC and realm.ruler_id is not None:
        own = {row.axis: row.value for row in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id == realm.ruler_id))}
        if own:
            return own
    if profile.decision_rule is DecisionRule.COUNCIL:
        holders = [office.holder_entity_id for office in realm.offices if office.holder_entity_id is not None][:COUNCIL_KINDS]
        if holders:
            sums: dict[ValueAxis, list[int]] = defaultdict(list)
            for row in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id.in_(holders))):
                sums[row.axis].append(row.value)
            if sums:
                return {axis: round_half_up(sum(values) / len(values)) for axis, values in sums.items()}
    return await culture_of(ctx.session, core) if core is not None else {}


async def will(ctx: TickContext, realm: Realm) -> dict[ValueAxis, int]:
    found = await base_will(ctx, realm)
    creed = realm.profile.ideology_entity_id
    if creed is None:
        return found
    weight = ctx.rules.ideologies.decision_pct / PERCENT
    merged = dict(found)
    for tenet in await ctx.session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creed)):
        for axis, value in IDEOLOGY_VALUES[tenet].items():
            merged[axis] = merged.get(axis, 0) + round_half_up(value * CREED_SCALE * weight)
    return merged


async def plagued(ctx: TickContext, realm: Realm) -> bool:
    regions = list(realm.territory)
    if not regions:
        return False
    found = await ctx.session.scalar(
        select(OutbreakRow.id).where(OutbreakRow.region_entity_id.in_(regions), OutbreakRow.status != OutbreakStatus.ENDED).limit(1)
    )
    return found is not None


async def wanted_laws(
    ctx: TickContext, realm: Realm, laws: LawBook, values: dict[ValueAxis, int], *, lost: bool, fighting: bool
) -> list[tuple[LawKind, dict[str, int | str | bool]]]:
    table = ctx.rules.legislation
    polity = realm.entity
    rng = ctx.rng(f"wanted_laws.{polity.id}.{ctx.epoch}")
    wants: list[tuple[LawKind, dict[str, int | str | bool]]] = []
    if laws.in_force(polity.id, LawKind.SUCCESSION_RULE) is None and realm.profile.tier >= 1:
        core = await ctx.session.get(PeopleCultureRow, realm.profile.core_entity_id or -1)
        rule = INHERITANCE_RULES[core.inheritance].value if core is not None else SuccessionRule.PRIMOGENITURE.value
        if values.get(ValueAxis.KINSHIP, 0) <= -LEAN and core is not None and core.marriage is MarriageCustom.POLYANDRY:
            rule = SuccessionRule.MATRILINEAL.value
        wants.append((LawKind.SUCCESSION_RULE, {"rule": rule}))
    if await plagued(ctx, realm) and laws.in_force(polity.id, LawKind.QUARANTINE) is None and rng.chance(table.plague_quarantine_chance):
        wants.append((LawKind.QUARANTINE, {}))
    if lost and laws.in_force(polity.id, LawKind.CONSCRIPTION) is None and rng.chance(table.defeat_conscription_chance):
        wants.append((LawKind.CONSCRIPTION, {}))
    if fighting and laws.in_force(polity.id, LawKind.LEVY_LAW) is None:
        wants.append((LawKind.LEVY_LAW, {"share": clamp_int(10 + values.get(ValueAxis.MARTIAL, 0) // 5, 0, 50)}))
    if laws.in_force(polity.id, LawKind.PENAL_CODE) is None and realm.profile.tier >= 1:
        harsh = values.get(ValueAxis.MERCY, 0) <= -LEAN
        wants.append((LawKind.PENAL_CODE, {"theft": "hand" if harsh else "fine", "murder": "death" if harsh else "wergild"}))
    if laws.in_force(polity.id, LawKind.SLAVERY) is None:
        lawful = values.get(ValueAxis.HIERARCHY, 0) >= LEAN and values.get(ValueAxis.MERCY, 0) <= -LEAN
        wants.append((LawKind.SLAVERY, {"status": "allowed" if lawful else "banned"}))
    if laws.in_force(polity.id, LawKind.RELIGIOUS_TOLERANCE) is None:
        level = "free" if values.get(ValueAxis.XENOPHILIA, 0) >= LEAN else "persecution" if values.get(ValueAxis.PIETY, 0) >= LEAN * 2 else "tolerated"
        wants.append((LawKind.RELIGIOUS_TOLERANCE, {"level": level}))
    maimed = await ctx.session.scalar(
        select(func.coalesce(func.sum(MaimedCohortRow.count), 0)).where(MaimedCohortRow.community_entity_id.in_(list(realm.members)))
    )
    if (
        int(maimed or 0) > 0
        and realm.profile.treasury > 0
        and laws.in_force(polity.id, LawKind.VETERAN_PENSION) is None
        and values.get(ValueAxis.MARTIAL, 0) > 0
    ):
        wants.append((LawKind.VETERAN_PENSION, {}))
    if values.get(ValueAxis.HIERARCHY, 0) >= LEAN * 2 and laws.in_force(polity.id, LawKind.SUMPTUARY) is None:
        wants.append((LawKind.SUMPTUARY, {}))
    return wants


async def agenda(ctx: TickContext, book: RealmBook, realm: Realm, laws: LawBook) -> list[str]:
    table = ctx.rules.legislation
    polity = realm.entity
    values = await will(ctx, realm)
    rng = ctx.rng(f"agenda.{polity.id}.{ctx.epoch}")
    taken: list[str] = []
    _, lost, fighting = await war_record(ctx, realm)
    wants = await wanted_laws(ctx, realm, laws, values, lost=bool(lost), fighting=fighting)
    for kind, params in wants:
        if len(taken) >= ctx.rules.government.decision_cap:
            break
        if kind not in {LawKind.SUCCESSION_RULE, LawKind.SLAVERY, LawKind.RELIGIOUS_TOLERANCE} and not rng.chance(table.enact_chance * 3):
            continue
        basis = (
            LegitimacyBasis.DIVINE
            if realm.profile.decision_rule is DecisionRule.DIVINE
            else LegitimacyBasis.COUNCIL
            if realm.profile.decision_rule is not DecisionRule.AUTOCRATIC
            else LegitimacyBasis.DECREE
        )
        law = await enact(ctx, polity, kind, params, by_id=realm.ruler_id, basis=basis)
        laws.laws[law.id] = law
        profile = await ctx.session.get(LawProfileRow, law.id)
        if profile is not None:
            laws.profiles[law.id] = profile
            laws.by_node[polity.id].append(law.id)
        taken.append(f"enacted {kind.value}")
        if kind in BASELINE_LAWS:
            continue
        await note(ctx, f"{polity.name} laid down {law.name}.", key="polity.law_enacted", ids=[polity.id, law.id], kind=ChronicleKind.CIVILIZATION)
    taken.extend(await taxes(ctx, realm, laws, values))
    taken.extend(await temples(ctx, realm, values))
    return taken


async def taxes(ctx: TickContext, realm: Realm, laws: LawBook, values: dict[ValueAxis, int]) -> list[str]:
    table = ctx.rules.government
    row = laws.in_force(realm.entity.id, LawKind.TAX_RATE)
    if row is None:
        law = await enact(ctx, realm.entity, LawKind.TAX_RATE, {"rate": ctx.rules.taxation.default_tax}, by_id=realm.ruler_id)
        profile = await ctx.session.get(LawProfileRow, law.id)
        if profile is not None:
            laws.profiles[law.id] = profile
            laws.by_node[realm.entity.id].append(law.id)
        return ["set taxes"]
    if "params" in row.locked:
        return []
    ruler_traits = await traits_of(ctx.session, realm.ruler_id) if realm.ruler_id is not None else set()
    upkeep = table.office_upkeep * len(realm.offices)
    rate = int(row.params.get("rate", ctx.rules.taxation.default_tax))
    if TraitKind.GREEDY in ruler_traits or values.get(ValueAxis.WEALTH, 0) >= LEAN:
        if realm.profile.treasury < upkeep * 2:
            row.params = {**row.params, "rate": min(PERCENT // 2, rate + table.tax_greed_step)}
            return ["raised taxes"]
    elif realm.profile.stability < PERCENT // 3 and rate > table.tax_greed_step:
        row.params = {**row.params, "rate": rate - table.tax_greed_step}
        return ["eased taxes"]
    return []


async def temples(ctx: TickContext, realm: Realm, values: dict[ValueAxis, int]) -> list[str]:
    table = ctx.rules.government
    if values.get(ValueAxis.PIETY, 0) < table.temple_piety or realm.profile.treasury < table.temple_cost or realm.profile.capital_entity_id is None:
        return []
    capital = await living_entity(ctx.session, realm.profile.capital_entity_id)
    if capital is None:
        return []
    town = await town_of(ctx, capital, await KnowledgeMap.load(ctx.session))
    if town.levels(DistrictKind.TEMPLE_QUARTER) >= 3:
        return []
    await add_district(ctx, town, DistrictKind.TEMPLE_QUARTER, material=BuildMaterial.STONE, builder_id=realm.entity.id)
    spend(ctx, realm, -table.temple_cost, TreasuryEntry.BUILDING, "temples")
    return ["funded temples"]


async def repeal_discord(ctx: TickContext, realm: Realm, laws: LawBook) -> int:
    table = ctx.rules.legislation
    values = await culture_of(ctx.session, realm.profile.core_entity_id) if realm.profile.core_entity_id is not None else {}
    repealed = 0
    for law_id in list(laws.by_node.get(realm.entity.id, [])):
        profile = laws.profiles.get(law_id)
        law = laws.laws.get(law_id)
        if profile is None or law is None or "repeal" in profile.locked:
            continue
        gap = discord(profile.kind, profile.params, values)
        if gap < table.discord_distance and profile.conflict < table.discord_distance:
            continue
        resist = (stat(law, "rigidity") or 0) / PERCENT * table.rigidity_resist_pct / PERCENT if profile.legitimacy_basis is LegitimacyBasis.CUSTOM else 0.0
        if ctx.rng(f"repeal.{law_id}.{ctx.epoch}").chance(table.repeal_chance * (1 - resist)):
            await repeal(ctx, law, "the people would not bear it")
            laws.by_node[realm.entity.id].remove(law_id)
            laws.profiles.pop(law_id, None)
            repealed += 1
    return repealed


def spend(ctx: TickContext, realm: Realm, amount: int, entry: TreasuryEntry, label: str) -> int:
    profile = realm.profile
    profile.treasury += amount
    if profile.treasury < 0:
        profile.debt += -profile.treasury
        profile.treasury = 0
    ctx.session.add(
        PolityTreasuryRow(polity_entity_id=realm.entity.id, epoch=ctx.epoch, entry=entry, amount=amount, balance=profile.treasury, note=label[:120])
    )
    return amount


async def collect(ctx: TickContext, book: RealmBook, realm: Realm) -> int:
    table = ctx.rules.government
    leak = ctx.rules.overextension.tax_leak_pct / PERCENT
    gathered = 0
    for member_id, member in realm.members.items():
        income = await ctx.session.scalar(
            select(func.coalesce(func.sum(SettlementTreasuryRow.amount), 0)).where(
                SettlementTreasuryRow.settlement_entity_id == member_id,
                SettlementTreasuryRow.epoch == ctx.epoch,
                SettlementTreasuryRow.entry == TreasuryEntry.TAX,
            )
        )
        town = await ctx.session.get(SettlementProfileRow, member_id)
        if town is None or town.free_city or not income:
            continue
        share = round_half_up(int(income) * table.polity_tax_pct / PERCENT)
        arriving = round_half_up(share * (1 - leak * member.autonomy / PERCENT))
        taken = min(town.treasury, share)
        town.treasury -= taken
        ctx.session.add(
            SettlementTreasuryRow(
                settlement_entity_id=member_id,
                epoch=ctx.epoch,
                entry=TreasuryEntry.TAX,
                amount=-taken,
                balance=town.treasury,
                note=f"to {realm.entity.name}"[:120],
            )
        )
        gathered += min(arriving, taken)
    if gathered:
        spend(ctx, realm, gathered, TreasuryEntry.TAX, "taxes from the realm")
    upkeep = table.office_upkeep * sum(1 for office in realm.offices if office.holder_entity_id is not None)
    if upkeep:
        spend(ctx, realm, -upkeep, TreasuryEntry.GARRISON, "offices")
    if realm.profile.debt and realm.profile.treasury:
        paid = min(realm.profile.debt, realm.profile.treasury)
        realm.profile.debt -= paid
        realm.profile.treasury -= paid
    return gathered


async def member_effects(ctx: TickContext, member_id: int, laws: LawBook, polity: int) -> None:
    table = ctx.rules.legislation
    rate = laws.param(polity, LawKind.TAX_RATE, "rate")
    status = laws.param(polity, LawKind.SLAVERY, "status")
    marriage = laws.param(polity, LawKind.MARRIAGE_LAW, "custom")
    sanitation = laws.param(polity, LawKind.SANITATION, "works")
    pension = laws.in_force(polity, LawKind.VETERAN_PENSION)
    sumptuary = laws.in_force(polity, LawKind.SUMPTUARY)
    town = await ctx.session.get(SettlementProfileRow, member_id)
    if town is not None:
        if rate is not None and "tax_rate" not in town.locked:
            town.tax_rate = int(rate)
        if sanitation is not None and "sanitation" not in town.locked:
            town.sanitation = clamp_int(town.sanitation + int(sanitation) * table.sanitation_gain // PERCENT * 10, 0, PERCENT)
    culture = await ctx.session.get(PeopleCultureRow, member_id)
    if culture is not None:
        if status is not None and "slavery_lawful" not in culture.locked:
            culture.slavery_lawful = status in {"allowed", "debt_only"}
        if marriage is not None and "marriage" not in culture.locked:
            culture.marriage = MarriageCustom(str(marriage))
    society = await ctx.session.get(CommunitySocietyRow, member_id)
    if society is not None and pension is not None:
        society.satisfaction_warrior = clamp_int(society.satisfaction_warrior + table.pension_opinion * pension.enforcement // PERCENT, 0, PERCENT)
        outcasts = society.share(SocialClass.OUTCAST)
        if outcasts > 0:
            society.share_outcast = round(outcasts * (1 - table.pension_outcast_pct / PERCENT * pension.enforcement / PERCENT / 4), 2)
            society.share_farmer = round(society.share_farmer + outcasts - society.share_outcast, 2)
    if society is not None and sumptuary is not None:
        noble = int(sumptuary.params.get("noble_luxury", 60)) - PERCENT // 2
        merchant = int(sumptuary.params.get("merchant_luxury", 20)) - PERCENT // 2
        scale = table.sumptuary_pct / PERCENT / 10
        society.satisfaction_noble = clamp_int(society.satisfaction_noble + noble * scale, 0, PERCENT)
        society.satisfaction_merchant = clamp_int(society.satisfaction_merchant + merchant * scale, 0, PERCENT)


async def church_and_guild(ctx: TickContext, realm: Realm, laws: LawBook) -> None:
    polity = realm.entity.id
    tithe = laws.in_force(polity, LawKind.TITHE)
    if tithe is not None and bool(tithe.params.get("enforced")) and realm.profile.state_religion_id is not None:
        cult = await living_entity(ctx.session, realm.profile.state_religion_id)
        if cult is not None:
            shift_stat(cult, "influence", int(tithe.params.get("rate", 5)) * tithe.enforcement // PERCENT, ctx.rules.society.default_stat)
    charter = laws.in_force(polity, LawKind.GUILD_CHARTER)
    if charter is not None and int(charter.params.get("guild_id", 0)):
        guild = await living_entity(ctx.session, int(charter.params["guild_id"]))
        if guild is not None:
            shift_stat(guild, "strength", 5 if bool(charter.params.get("monopoly")) else 2, ctx.rules.society.default_stat)
    rite = laws.param(polity, LawKind.BURIAL_LAW, "rite")
    if rite in {"burning", "exposure"} and realm.territory:
        for outbreak in await ctx.session.scalars(
            select(OutbreakRow).where(OutbreakRow.region_entity_id.in_(list(realm.territory)), OutbreakRow.status != OutbreakStatus.ENDED)
        ):
            outbreak.severity = clamp_int(outbreak.severity * (0.85 if rite == "burning" else 1.1), 0, PERCENT)


async def law_effects(ctx: TickContext, book: RealmBook, realm: Realm, laws: LawBook) -> None:
    polity = realm.entity.id
    await church_and_guild(ctx, realm, laws)
    quarantine = laws.in_force(polity, LawKind.QUARANTINE)
    for member_id in realm.members:
        await member_effects(ctx, member_id, laws, polity)
    known = not await lacks(ctx.session, realm.profile.core_entity_id, Technique.QUARANTINE)
    if quarantine is not None and bool(quarantine.params.get("automatic", True)) and known:
        for outbreak in await ctx.session.scalars(
            select(OutbreakRow).where(OutbreakRow.region_entity_id.in_(list(realm.territory)), OutbreakRow.status != OutbreakStatus.ENDED)
        ):
            if await ctx.session.get(QuarantineRow, outbreak.region_entity_id) is None:
                epochs = int(quarantine.params.get("epochs", ctx.rules.epidemiology.quarantine_epochs))
                ctx.session.add(
                    QuarantineRow(
                        region_entity_id=outbreak.region_entity_id, started_epoch=ctx.epoch, until_epoch=ctx.epoch + epochs, ordered_by_entity_id=polity
                    )
                )


async def enforce(ctx: TickContext, realm: Realm, laws: LawBook) -> int:
    table = ctx.rules.legislation
    orders = []
    for member_id in realm.members:
        town = await ctx.session.get(SettlementProfileRow, member_id)
        if town is not None:
            orders.append(town.public_order)
    order = sum(orders) / len(orders) if orders else PERCENT / 2
    judge = next((office for office in realm.offices if office.kind is OfficeKind.HIGH_JUDGE and office.holder_entity_id is not None), None)
    judge_skill = 0
    if judge is not None:
        mortal = await living_entity(ctx.session, judge.holder_entity_id)
        judge_skill = (stat(mortal, "intellect") or 0) if mortal is not None else 0
    values = await culture_of(ctx.session, realm.profile.core_entity_id) if realm.profile.core_entity_id is not None else {}
    unrest = 0
    for law_id in laws.by_node.get(realm.entity.id, []):
        profile = laws.profiles.get(law_id)
        law = laws.laws.get(law_id)
        if profile is None or law is None:
            continue
        if "enforcement" not in profile.locked:
            gap = discord(profile.kind, profile.params, values)
            base = order * table.enforcement_order_pct / PERCENT + judge_skill * table.enforcement_judge_pct / PERCENT
            profile.enforcement = clamp_int(base - gap / 2, 0, PERCENT)
        profile.conflict = max(0, profile.conflict - table.conflict_decay)
        if discord(profile.kind, profile.params, values) >= table.discord_distance:
            unrest += table.discord_unrest
        unrest += round_half_up(profile.conflict * table.conflict_unrest_pct / PERCENT)
        settle_justice(law, profile, values)
    if unrest:
        for member_id in realm.members:
            town = await ctx.session.get(SettlementProfileRow, member_id)
            if town is not None and "unrest" not in town.locked:
                town.unrest = clamp_int(town.unrest + unrest, 0, PERCENT)
    return unrest


async def conquest_conflict(ctx: TickContext, book: RealmBook, realm: Realm, laws: LawBook, newcomers: list[int]) -> int:
    table = ctx.rules.legislation
    if not newcomers or not laws.by_node.get(realm.entity.id):
        return 0
    marked = 0
    for member_id in newcomers:
        for law_id in laws.by_node.get(member_id, []):
            profile = laws.profiles.get(law_id)
            if profile is None:
                continue
            rival = laws.in_force(realm.entity.id, profile.kind)
            if rival is not None and rival.params != profile.params:
                profile.conflict = max(profile.conflict, table.conquest_conflict)
                marked += 1
    return marked
