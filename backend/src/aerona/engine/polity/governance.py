from collections import defaultdict

from sqlalchemy import func, select

from aerona.catalog.ethics import ACT_CRIMES, HONOUR_MODELS
from aerona.catalog.laws import PENALTY_CRUELTY
from aerona.catalog.lore import IDEOLOGY_VALUES
from aerona.catalog.mind import DOMAIN_VALUES
from aerona.constants.units import PERCENT
from aerona.db.tables.body import MaimedCohortRow
from aerona.db.tables.culture import IdeologyTenetRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow, QuarantineRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.mind import PersonalityValueRow
from aerona.db.tables.polity import LawProfileRow, PolityTreasuryRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import MarriageCustom
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import EthicalStance, MemoryKind, TraitKind, ValueAxis
from aerona.domain.enums.polity import DecisionRule, LawKind, LegitimacyBasis, OfficeKind, OfficePower, SuccessionRule
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, TreasuryEntry
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import INHERITANCE_RULES
from aerona.engine.factions.balance import faction_pull
from aerona.engine.lore.research import lacks
from aerona.engine.mind.book import traits_of
from aerona.engine.mind.ethics import ethics_of, honour_of
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.law_effects import jubilee, levy_terms, standing_soldiers, tenure_and_serfdom
from aerona.engine.polity.laws import LawBook, discord, enact, repeal, settle_justice, validate
from aerona.engine.polity.offices import best_skill, powers_of
from aerona.engine.polity.standing import war_record
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.relations.persuasion import council_lift
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import declare_war
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import add_district

CREED_SCALE = 10
LEAN = 25
BASELINE_LAWS = frozenset({LawKind.SUCCESSION_RULE, LawKind.SLAVERY, LawKind.RELIGIOUS_TOLERANCE, LawKind.TAX_RATE, LawKind.PENAL_CODE})
COUNCIL_KINDS = 5
SWAY_SCALE = 10
COUNCIL_OFFICES = frozenset({OfficeKind.CHANCELLOR, OfficeKind.MARSHAL, OfficeKind.TREASURER, OfficeKind.HIGH_JUDGE, OfficeKind.SPYMASTER, OfficeKind.REGENT})
T = TenetKind
CHURCH_LAWS: dict[TenetKind, tuple[LawKind, dict[str, int | str | bool]]] = {
    T.ANTI_MAGIC: (LawKind.MAGIC_BAN, {"severity": 70}),
    T.SANCTIFIED_MAGIC: (LawKind.LICENSED_MAGIC, {"fee": 10}),
    T.EXCLUSIVITY: (LawKind.RELIGIOUS_TOLERANCE, {"level": "persecution"}),
    T.SYNCRETIC_OPENNESS: (LawKind.RELIGIOUS_TOLERANCE, {"level": "free"}),
    T.PROSELYTISM: (LawKind.TITHE, {"rate": 10, "enforced": True}),
    T.ANCESTOR_VENERATION: (LawKind.BURIAL_LAW, {"rite": "burial"}),
    T.HOLY_WAR: (LawKind.LEVY_LAW, {"share": 20, "duration": 2}),
    T.PURITY_OF_BODY: (LawKind.SANITATION, {"works": 20}),
    T.SACRED_SUFFERING: (LawKind.PENAL_CODE, {"blasphemy": "flogging"}),
}
CULT_LAWS: dict[TenetKind, tuple[LawKind, dict[str, int | str | bool]]] = {
    T.ANCESTOR_VENERATION: (LawKind.BURIAL_LAW, {"rite": "burial"}),
    T.ANTI_MAGIC: (LawKind.MAGIC_BAN, {"severity": 60}),
    T.CELIBATE_CLERGY: (LawKind.MARRIAGE_LAW, {"custom": "monogamy", "endogamy": False}),
    T.EXCLUSIVITY: (LawKind.MARRIAGE_LAW, {"custom": "monogamy", "endogamy": True}),
    T.SANCTIFIED_MAGIC: (LawKind.RITE_RESTRICTIONS, {"level": 20}),
    T.ASCETICISM: (LawKind.SUMPTUARY, {"noble_luxury": 30, "merchant_luxury": 10}),
    T.PROSELYTISM: (LawKind.TITHE, {"rate": 5, "enforced": False}),
}


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
            advisers = await counsel(ctx, realm, exclude=realm.ruler_id)
            if not advisers:
                return own
            weight = ctx.rules.government.ruler_weight_pct / PERCENT
            return {axis: round_half_up(own.get(axis, 0) * weight + advisers.get(axis, 0) * (1 - weight)) for axis in set(own) | set(advisers)}
    if profile.decision_rule is DecisionRule.COUNCIL:
        voted = await counsel(ctx, realm, exclude=None)
        if voted:
            return voted
    return await culture_of(ctx.session, core) if core is not None else {}


async def counsel(ctx: TickContext, realm: Realm, *, exclude: int | None) -> dict[ValueAxis, int]:
    seats = [
        office for office in realm.offices if office.holder_entity_id is not None and office.holder_entity_id != exclude and office.kind in COUNCIL_OFFICES
    ]
    if not seats:
        return {}
    sway: dict[int, float] = {}
    for office in seats:
        holder = await living_entity(ctx.session, office.holder_entity_id)
        if holder is not None and office.holder_entity_id is not None:
            sway[office.holder_entity_id] = sway.get(office.holder_entity_id, 0.0) + 1 + (holder.importance or 0) / SWAY_SCALE + len(powers_of(office))
    sums: dict[ValueAxis, float] = defaultdict(float)
    weights: dict[ValueAxis, float] = defaultdict(float)
    for row in await ctx.session.scalars(select(PersonalityValueRow).where(PersonalityValueRow.node_id.in_(list(sway)))):
        sums[row.axis] += row.value * sway[row.node_id]
        weights[row.axis] += sway[row.node_id]
    return {axis: round_half_up(sums[axis] / weights[axis]) for axis in sums if weights[axis] > 0}


async def will(ctx: TickContext, realm: Realm) -> dict[ValueAxis, int]:
    found = await base_will(ctx, realm)
    for axis, value in (await faction_pull(ctx, realm)).items():
        found = {**found, axis: found.get(axis, 0) + value}
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


async def outraged_laws(ctx: TickContext, realm: Realm, laws: LawBook, values: dict[ValueAxis, int]) -> list[tuple[LawKind, dict[str, int | str | bool]]]:
    code = laws.in_force(realm.entity.id, LawKind.PENAL_CODE)
    core = realm.profile.core_entity_id
    if code is None or core is None:
        return []
    table = ctx.rules.ethics
    severe = {EthicalStance.UNTHINKABLE} | ({EthicalStance.SHAMEFUL} if HONOUR_MODELS[await honour_of(ctx.session, core)].law_pct > PERCENT else set())
    harsher = dict(code.params)
    for act, row in (await ethics_of(ctx.session, core)).items():
        crime = ACT_CRIMES.get(act)
        if crime is None or row.stance not in severe or PENALTY_CRUELTY.get(str(harsher.get(crime)), 0) >= table.law_cruelty:
            continue
        harsher[crime] = "death" if values.get(ValueAxis.MERCY, 0) < 0 else "exile"
    if harsher == code.params or not ctx.rng(f"outrage.{realm.entity.id}.{ctx.epoch}").chance(table.law_chance):
        return []
    return [(LawKind.PENAL_CODE, harsher)]


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
    wants.extend(await outraged_laws(ctx, realm, laws, values))
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
        swayed = await council_lift(ctx, realm.ruler_id, polity.id) if realm.ruler_id and realm.profile.decision_rule is not DecisionRule.AUTOCRATIC else 1.0
        if kind not in {LawKind.SUCCESSION_RULE, LawKind.SLAVERY, LawKind.RELIGIOUS_TOLERANCE} and not rng.chance(table.enact_chance * 3 * swayed):
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
    taken.extend(await works(ctx, realm, values, fighting=fighting))
    return taken


async def works(ctx: TickContext, realm: Realm, values: dict[ValueAxis, int], *, fighting: bool) -> list[str]:
    table = ctx.rules.government
    if "works" in realm.profile.locked or realm.profile.treasury < table.build_cost * 2:
        return []
    if not ctx.rng(f"works.{realm.entity.id}.{ctx.epoch}").chance(table.build_chance):
        return []
    knowledge = await KnowledgeMap.load(ctx.session)
    choices: list[tuple[int, int, DistrictKind]] = []
    for member_id in sorted(realm.members):
        place = await living_entity(ctx.session, member_id)
        town_row = await ctx.session.get(SettlementProfileRow, member_id)
        if place is None or town_row is None:
            continue
        need = DistrictKind.CITADEL if fighting or town_row.crime >= PERCENT // 2 else DistrictKind.MARKET
        if not fighting and values.get(ValueAxis.WEALTH, 0) < LEAN and values.get(ValueAxis.HIERARCHY, 0) >= LEAN:
            need = DistrictKind.PALACE if member_id == realm.profile.capital_entity_id else need
        choices.append((town_row.unrest + town_row.crime, member_id, need))
    if not choices:
        return []
    _, member_id, need = max(choices)
    place = await living_entity(ctx.session, member_id)
    if place is None:
        return []
    town = await town_of(ctx, place, knowledge)
    await add_district(ctx, town, need, material=BuildMaterial.STONE, builder_id=realm.entity.id)
    spend(ctx, realm, -table.build_cost, TreasuryEntry.BUILDING, f"{need.value.replace('_', ' ')} in {place.name}")
    await note(
        ctx,
        f"{realm.entity.name} paid for a {need.value.replace('_', ' ')} in {place.name}.",
        key="polity.works",
        ids=[realm.entity.id, place.id],
        kind=ChronicleKind.CONSTRUCTION,
    )
    return [f"built {need.value}"]


async def consider(
    ctx: TickContext,
    realm: Realm,
    laws: LawBook,
    kind: LawKind,
    params: dict[str, int | str | bool],
    *,
    sponsor_id: int | None,
    sway: int,
) -> EntityRow | None:
    table = ctx.rules.legislation
    polity = realm.entity
    merged = validate(kind, params)
    values = await will(ctx, realm)
    gap = discord(kind, merged, values)
    bar = table.proposal_threshold + sway * table.sponsor_weight_pct / PERCENT
    sponsor = await living_entity(ctx.session, sponsor_id) if sponsor_id is not None else None
    who = sponsor.name if sponsor is not None else "the crisis"
    if gap > bar:
        await note(
            ctx,
            f"{polity.name} would not hear {who}: the {kind.value.replace('_', ' ')} it urged was set aside.",
            key="polity.law_rejected",
            ids=[polity.id, *([sponsor.id] if sponsor is not None else [])],
            kind=ChronicleKind.CIVILIZATION,
        )
        return None
    current = next(
        (laws.profiles[law_id] for law_id in laws.by_node.get(polity.id, []) if law_id in laws.profiles and laws.profiles[law_id].kind is kind),
        None,
    )
    if current is not None:
        if "params" in current.locked or current.params == merged:
            return None
        current.params = merged
        current.enacted_by_entity_id = sponsor_id if sponsor_id is not None else current.enacted_by_entity_id
        law = laws.laws.get(current.law_entity_id)
        if law is not None:
            await note(
                ctx, f"{polity.name} rewrote {law.name}, urged on by {who}.", key="polity.law_amended", ids=[polity.id, law.id], kind=ChronicleKind.CIVILIZATION
            )
        return law
    basis = (
        LegitimacyBasis.DIVINE
        if sponsor is not None and sponsor.entity_type is EntityType.CULT
        else LegitimacyBasis.COUNCIL
        if sponsor
        else LegitimacyBasis.DECREE
    )
    law = await enact(ctx, polity, kind, merged, by_id=sponsor_id if sponsor_id is not None else realm.ruler_id, basis=basis)
    laws.laws[law.id] = law
    profile = await ctx.session.get(LawProfileRow, law.id)
    if profile is not None:
        laws.profiles[law.id] = profile
        laws.by_node[polity.id].append(law.id)
    await note(ctx, f"{polity.name} laid down {law.name}, as {who} urged.", key="polity.law_proposed", ids=[polity.id, law.id], kind=ChronicleKind.CIVILIZATION)
    return law


async def crises(ctx: TickContext, realm: Realm, laws: LawBook) -> list[tuple[LawKind, dict[str, int | str | bool]]]:
    table = ctx.rules.legislation
    polity = realm.entity.id
    found: list[tuple[LawKind, dict[str, int | str | bool]]] = []
    crime = []
    for member_id in realm.members:
        town = await ctx.session.get(SettlementProfileRow, member_id)
        if town is not None:
            crime.append(town.crime)
    if crime and sum(crime) / len(crime) >= table.crisis_crime:
        found.append((LawKind.PENAL_CODE, {"theft": "hand", "murder": "death", "desertion": "death"}))
    if realm.profile.debt >= table.crisis_debt and laws.in_force(polity, LawKind.DEBT_LAW) is None:
        found.append((LawKind.DEBT_LAW, {"remedy": "jubilee"}))
    if await plagued(ctx, realm) and laws.in_force(polity, LawKind.BURIAL_LAW) is None:
        found.append((LawKind.BURIAL_LAW, {"rite": "burning"}))
    return found


async def proposals(ctx: TickContext, realm: Realm, laws: LawBook) -> list[str]:
    table = ctx.rules.legislation
    taken: list[str] = []
    for kind, params in await crises(ctx, realm, laws):
        if await consider(ctx, realm, laws, kind, params, sponsor_id=None, sway=0) is not None:
            taken.append(f"crisis {kind.value}")
    church_id = realm.profile.state_religion_id
    church = await living_entity(ctx.session, church_id) if church_id is not None else None
    if church is None or not ctx.rng(f"church_law.{realm.entity.id}.{ctx.epoch}").chance(table.cult_proposal_chance):
        return taken
    tenets = set(await ctx.session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == church.id)))
    for tenet, (kind, params) in CHURCH_LAWS.items():
        if tenet in tenets and laws.in_force(realm.entity.id, kind) is None:
            sway = stat(church, "influence") or 0
            if await consider(ctx, realm, laws, kind, dict(params), sponsor_id=church.id, sway=sway) is not None:
                taken.append(f"church {kind.value}")
            break
    return taken


async def cult_laws(ctx: TickContext, laws: LawBook) -> int:
    table = ctx.rules.legislation
    made = 0
    for cult in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if not ctx.rng(f"cult_law.{cult.id}.{ctx.epoch}").chance(table.cult_law_chance):
            continue
        tenets = set(await ctx.session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult.id)))
        held = {laws.profiles[law_id].kind for law_id in laws.by_node.get(cult.id, []) if law_id in laws.profiles}
        for tenet, (kind, params) in CULT_LAWS.items():
            if tenet in tenets and kind not in held:
                law = await enact(ctx, cult, kind, dict(params), by_id=cult.id, basis=LegitimacyBasis.DIVINE)
                laws.laws[law.id] = law
                profile = await ctx.session.get(LawProfileRow, law.id)
                if profile is not None:
                    laws.profiles[law.id] = profile
                    laws.by_node[cult.id].append(law.id)
                await note(
                    ctx, f"{cult.name} laid {law.name} upon its faithful.", key="polity.cult_law", ids=[cult.id, law.id], kind=ChronicleKind.CIVILIZATION
                )
                made += 1
                break
    return made


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
    leak = ctx.rules.overextension.tax_leak_pct / PERCENT * (1 - table.treasurer_leak_pct / PERCENT * await best_skill(ctx, realm, OfficePower.TREASURY))
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
    await service_debt(ctx, book, realm)
    return gathered


def owed(loan: LoanRow) -> int:
    return max(0, round_half_up(loan.principal * (1 + loan.interest_pct / PERCENT)) - loan.repaid)


async def lender_for(ctx: TickContext, book: RealmBook, realm: Realm) -> EntityRow | None:
    guilds = list(
        await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type == EntityType.FACTION,
                EntityRow.status == EntityStatus.CANON,
                EntityRow.engine_kind == EngineKind.MERCHANT_GUILD,
                EntityRow.affiliated_entity_id.in_(list(realm.members) or [-1]),
            )
        )
    )
    if guilds:
        return max(guilds, key=lambda guild: (stat(guild, "wealth") or 0, -guild.id))
    rich = [
        other
        for other in book.realms.values()
        if other.entity.id != realm.entity.id and other.entity.world_id == realm.entity.world_id and other.profile.treasury > realm.profile.debt
    ]
    if rich:
        return max(rich, key=lambda other: (other.profile.treasury, -other.entity.id)).entity
    return None


async def service_debt(ctx: TickContext, book: RealmBook, realm: Realm) -> None:
    table = ctx.rules.government
    profile = realm.profile
    loans = list(
        await ctx.session.scalars(select(LoanRow).where(LoanRow.borrower_entity_id == realm.entity.id, LoanRow.status == LoanStatus.OPEN).order_by(LoanRow.id))
    )
    outstanding = sum(owed(loan) for loan in loans)
    paid = outstanding - profile.debt
    for loan in loans:
        if paid <= 0:
            break
        share = min(paid, owed(loan))
        loan.repaid += share
        paid -= share
        if owed(loan) == 0:
            loan.status = LoanStatus.REPAID
    covered = sum(owed(loan) for loan in loans if loan.status is LoanStatus.OPEN)
    if profile.debt > covered and "debt" not in profile.locked:
        lender = await lender_for(ctx, book, realm)
        if lender is not None:
            principal = profile.debt - covered
            ctx.session.add(
                LoanRow(
                    lender_entity_id=lender.id,
                    borrower_entity_id=realm.entity.id,
                    principal=principal,
                    interest_pct=table.loan_interest_pct,
                    repaid=0,
                    issued_epoch=ctx.epoch,
                    due_epoch=ctx.epoch + table.loan_epochs,
                    status=LoanStatus.OPEN,
                    purpose="crown debt",
                )
            )
            profile.debt += round_half_up(principal * table.loan_interest_pct / PERCENT)
            if lender.entity_type is EntityType.POLITY:
                other = book.realms.get(lender.id)
                if other is not None:
                    other.profile.treasury = max(0, other.profile.treasury - principal)
            elif stat(lender, "wealth") is not None:
                shift_stat(lender, "wealth", -principal // PERCENT, ctx.rules.society.default_stat)
    for loan in loans:
        if loan.status is LoanStatus.OPEN and loan.due_epoch < ctx.epoch and owed(loan) > 0:
            await default(ctx, book, realm, loan)


async def default(ctx: TickContext, book: RealmBook, realm: Realm, loan: LoanRow) -> None:
    table = ctx.rules.government
    loan.status = LoanStatus.DEFAULTED
    realm.profile.debt = max(0, realm.profile.debt - owed(loan))
    lender = await living_entity(ctx.session, loan.lender_entity_id)
    core = realm.profile.core_entity_id
    if lender is None or core is None:
        return
    lender_side = book.realms[lender.id].profile.core_entity_id if lender.id in book.realms else lender.id
    if lender_side is not None:
        target = await living_entity(ctx.session, lender_side)
        if target is not None and target.entity_type in COMMUNITY_TYPES:
            await change_relation(ctx, lender_side, core, -table.default_relation, MemoryKind.CHEATED_US, note="defaulted on the crown's debt")
            if lender.entity_type is EntityType.POLITY and ctx.rng(f"debt_war.{loan.id}").chance(table.default_war_chance):
                await declare_war(ctx, lender_side, core, f"{realm.entity.name} would not pay its debts", cause=WarCause.DEBT)
    if lender.entity_type is EntityType.FACTION:
        shift_stat(lender, "sway", table.default_relation // 5, ctx.rules.society.default_stat)
    await note(
        ctx,
        f"{realm.entity.name} could not repay {lender.name}; the debt was left unpaid.",
        key="polity.debt_default",
        ids=[realm.entity.id, lender.id],
        kind=ChronicleKind.DEBT,
    )


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
        await tenure_and_serfdom(ctx, member_id, laws)
    ctx.count("jubilee_debts", await jubilee(ctx, realm, laws))
    ctx.count("levies_home", await levy_terms(ctx, realm, laws))
    soldiers = await standing_soldiers(ctx, realm)
    cost = round_half_up(soldiers * ctx.rules.legislation.standing_upkeep_per_100 / PERCENT)
    if cost:
        spend(ctx, realm, -cost, TreasuryEntry.GARRISON, "the standing army")
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
    judge = next((office for office in realm.offices if OfficePower.JUDGE in powers_of(office) and office.holder_entity_id is not None), None)
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
