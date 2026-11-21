from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.occupation_regimes import OccupationRegimeRow
from aerona.db.tables.polity import LawJurisdictionRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.occupation_regimes import OccupationEnding, OccupationRule
from aerona.domain.enums.polity import Jurisdiction
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.occupation_regime.book import RegimeTally, locals_of, occupation_of, owner_of, towns_of
from aerona.engine.occupation_regime.effects import capped, serving
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import refresh_realms
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity, remove_flag
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record

R = OccupationRule
CONTROL_SHIFT = total(OccupationRule, {R.MILITARY: 0, R.CIVIL_BY_OCCUPIER: 5, R.LOCAL_PUPPET: 10, R.ANNEXATION: 0, R.PROTECTORATE: 5})
GRIEVANCE_SHIFT = total(OccupationRule, {R.MILITARY: 5, R.CIVIL_BY_OCCUPIER: 3, R.LOCAL_PUPPET: -3, R.ANNEXATION: 8, R.PROTECTORATE: -5})
UPKEEP_PCT = total(OccupationRule, {R.MILITARY: 100, R.CIVIL_BY_OCCUPIER: 80, R.LOCAL_PUPPET: 40, R.ANNEXATION: 90, R.PROTECTORATE: 30})
TAX_PCT = total(OccupationRule, {R.MILITARY: 100, R.CIVIL_BY_OCCUPIER: 110, R.LOCAL_PUPPET: 70, R.ANNEXATION: 100, R.PROTECTORATE: 50})
IMPOSING = frozenset({OccupationRule.CIVIL_BY_OCCUPIER, OccupationRule.ANNEXATION})
SETTLING = frozenset({OccupationRule.CIVIL_BY_OCCUPIER, OccupationRule.ANNEXATION})
LEGACY_FIXUP = "occupation_regimes.legacy"
CIVIL_FROM = 60


async def found_regime(ctx: TickContext, occupation: OccupationRow, tally: RegimeTally) -> OccupationRegimeRow:
    regime = OccupationRegimeRow(
        region_entity_id=occupation.region_entity_id,
        occupier_entity_id=occupation.occupier_entity_id,
        owner_polity_id=await owner_of(ctx, occupation.region_entity_id, occupation.occupier_entity_id),
        tax_pct=capped(ctx.rules, ctx.rules.occupation.tax_pct),
        begun_epoch=ctx.epoch,
        administrators=[],
        imposed_laws=[],
        locked=[],
    )
    ctx.session.add(regime)
    await ctx.session.flush()
    tally.founded += 1
    return regime


async def lift_laws(ctx: TickContext, regime: OccupationRegimeRow) -> None:
    towns = [town.id for town in await locals_of(ctx, regime)]
    for law in regime.imposed_laws or []:
        for row in list(
            await ctx.session.scalars(select(LawJurisdictionRow).where(LawJurisdictionRow.law_entity_id == law, LawJurisdictionRow.node_entity_id.in_(towns)))
        ):
            await ctx.session.delete(row)
    regime.imposed_laws = []


async def impose_laws(ctx: TickContext, regime: OccupationRegimeRow) -> None:
    laws = sorted(
        set(await ctx.session.scalars(select(LawJurisdictionRow.law_entity_id).where(LawJurisdictionRow.node_entity_id == regime.occupier_entity_id)))
    )
    for town in await locals_of(ctx, regime):
        for law in laws:
            if await ctx.session.get(LawJurisdictionRow, (law, town.id)) is None:
                ctx.session.add(LawJurisdictionRow(law_entity_id=law, node_entity_id=town.id, jurisdiction=Jurisdiction.SETTLEMENT))
    regime.imposed_laws = laws
    await ctx.session.flush()


async def set_rule(ctx: TickContext, regime: OccupationRegimeRow, rule: OccupationRule, tally: RegimeTally, *, by: int | None = None) -> bool:
    if regime.rule is rule or "rule" in (regime.locked or []):
        return False
    if regime.rule in IMPOSING and rule not in IMPOSING:
        await lift_laws(ctx, regime)
    regime.rule = rule
    if rule in IMPOSING:
        await impose_laws(ctx, regime)
    if "tax_pct" not in (regime.locked or []):
        regime.tax_pct = capped(ctx.rules, ctx.rules.occupation.tax_pct * TAX_PCT[rule] // PERCENT)
    tally.rules_set += 1
    await record(
        ctx,
        "occupation.rule_set",
        roles={IncidentRole.ACTOR: by or regime.occupier_entity_id, IncidentRole.SUBJECT: regime.region_entity_id},
        facts={"rule": rule},
    )
    return True


async def pay_for_rule(ctx: TickContext, regime: OccupationRegimeRow) -> None:
    occupier = await living_entity(ctx.session, regime.occupier_entity_id)
    if occupier is None:
        return
    helpers = len(await serving(ctx.session, regime.id))
    cut = min(PERCENT, helpers * ctx.rules.occupation.collaborator_cost_cut_pct)
    await take_coin(ctx.session, ctx.rules, occupier, ctx.rules.occupation.rule_upkeep * UPKEEP_PCT[regime.rule] * (PERCENT - cut) // (PERCENT * PERCENT))


async def labour(ctx: TickContext, regime: OccupationRegimeRow, control: int) -> None:
    rate = capped(ctx.rules, regime.labour_pct)
    if not rate:
        return
    for town in await towns_of(ctx, regime):
        if not held(town.id):
            shift_stat(town, "prosperity", -round_half_up(ctx.rules.occupation.labour_prosperity * rate / PERCENT * control / PERCENT))


async def settle(ctx: TickContext, regime: OccupationRegimeRow, control: int, tally: RegimeTally) -> None:
    towns = [town for town in await towns_of(ctx, regime) if not held(town.id)]
    if regime.rule not in SETTLING or not towns or "settlers" in (regime.locked or []):
        return
    largest = max(towns, key=lambda town: (stat(town, "population") or 0, -town.id))
    arrivals = ctx.rules.occupation.settle_per_epoch * control // PERCENT
    shift_stat(largest, "population", arrivals)
    regime.settlers += arrivals
    tally.settlers += arrivals


async def annex(ctx: TickContext, regime: OccupationRegimeRow, occupation: OccupationRow, tally: RegimeTally) -> bool:
    lord = await ctx.session.get(PolityProfileRow, regime.occupier_entity_id)
    if lord is None or lord.core_entity_id is None:
        return False
    towns = [town for town in await towns_of(ctx, regime) if not held(town.id)]
    for town in towns:
        for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[town.id]):
            await close(ctx.session, bond, ctx.epoch, "annexed by the occupier")
        await remove_flag(ctx.session, town.id, EntityFlag.INDEPENDENT)
        await connect(ctx.session, lord.core_entity_id, town.id, BondKind.RULES, ctx.epoch, description="annexed")
    await refresh_realms(ctx, await RealmBook.load(ctx.session))
    regime.ended_epoch, regime.ending = ctx.epoch, OccupationEnding.ANNEXED
    await ctx.session.delete(occupation)
    tally.annexed += 1
    await record(
        ctx,
        "occupation.annexed",
        roles={IncidentRole.ACTOR: regime.occupier_entity_id, IncidentRole.SUBJECT: regime.region_entity_id, IncidentRole.VICTIM: regime.owner_polity_id},
        facts={"towns": len(towns), "settlers": regime.settlers},
    )
    return True


async def govern(ctx: TickContext, regime: OccupationRegimeRow, tally: RegimeTally) -> None:
    occupation = await occupation_of(ctx, regime)
    if occupation is None:
        return
    await pay_for_rule(ctx, regime)
    if "control" not in (occupation.locked or []):
        occupation.control = clamp_int(occupation.control + CONTROL_SHIFT[regime.rule], 0, PERCENT)
    if "resistance" not in (occupation.locked or []):
        occupation.resistance = clamp_int(occupation.resistance + GRIEVANCE_SHIFT[regime.rule], 0, PERCENT)
    await labour(ctx, regime, occupation.control)
    await settle(ctx, regime, occupation.control, tally)
    table = ctx.rules.occupation
    shifting = ctx.rng(f"occupation.rule.{regime.id}.{ctx.epoch}").chance(table.rule_shift_chance_pct)
    if regime.rule is OccupationRule.ANNEXATION and occupation.control >= table.annex_control:
        await annex(ctx, regime, occupation, tally)
    elif shifting and regime.rule is OccupationRule.MILITARY and occupation.control >= CIVIL_FROM:
        await set_rule(ctx, regime, OccupationRule.CIVIL_BY_OCCUPIER, tally)


async def ensure_regimes(ctx: TickContext, tally: RegimeTally) -> None:
    for occupation in list(await ctx.session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id))):
        if held(occupation.region_entity_id):
            continue
        query = select(OccupationRegimeRow.id).where(
            OccupationRegimeRow.region_entity_id == occupation.region_entity_id,
            OccupationRegimeRow.occupier_entity_id == occupation.occupier_entity_id,
            OccupationRegimeRow.ended_epoch.is_(None),
        )
        if await ctx.session.scalar(query.limit(1)) is None:
            await found_regime(ctx, occupation, tally)


async def apply_legacy(ctx: TickContext, tally: RegimeTally) -> None:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return
    before = tally.founded
    await ensure_regimes(ctx, tally)
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"regimes": tally.founded - before}))
    await ctx.session.flush()
