from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import JSON, Column, ColumnElement, CompoundSelect, Enum, Integer, RowMapping, Select, Table, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.invariants import DERIVED_REASONS, GENERIC, TYPED, GenericCheck, Remedy
from aerona.catalog.life_traits import ORDER_KIND_TRAITS, having
from aerona.db import tables
from aerona.db.base import Base
from aerona.db.columns import column_bounds
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow
from aerona.db.tables.council_order import DivineSeatRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.pantheon import PantheonTieRow, SyncretismRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import OrderKindTrait
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.mortal.readings import mend_death_cause, mismatched_deaths
from aerona.services.integrity.agent_d_links import (
    clear_identity_target,
    lost_identity_targets,
    misfit_revivals,
    refit_revival,
    slot_tradition,
    strike_unbacked_implant,
    unbacked_implants,
    unslotted_traditions,
)
from aerona.services.integrity.ages_links import free_keeper_seat, keepers_not_mortal
from aerona.services.integrity.arsenal_links import (
    dismantle,
    forget_war,
    misplaced_remnants,
    place_remnant,
    self_postures,
    unended_wars,
    unskilled_weapons,
    widen_posture,
)
from aerona.services.integrity.city_links import mend_conurbation, odd_conurbations, stray_rules, widen_rule
from aerona.services.integrity.cohort_sexes import resplit_cohort_sexes, stray_cohort_sexes
from aerona.services.integrity.competition_links import (
    call_off_war,
    drop_outsiders,
    even_shares,
    marketless_wars,
    outside_members,
    uneven_shares,
)
from aerona.services.integrity.conception_links import false_gods, strike_false_god
from aerona.services.integrity.condition_links import absent_systems, unkind_condition
from aerona.services.integrity.cult_links import end_godly, godly_cults, keep_promoters, lost_promoters, mend_end, mismatched_ends
from aerona.services.integrity.departure_links import align_office, clear_successor, early_returns, handed_to_self, mend_return, stray_offices
from aerona.services.integrity.fertility_links import barren_means, strike_barren_means, strike_unknown_use, unknown_uses
from aerona.services.integrity.genome_alleles import mend_alleles, stray_alleles
from aerona.services.integrity.governance_links import (
    claimless_creditors,
    even_votes,
    partyless_mergers,
    prune_creditors,
    strangers_seated,
    uneven_votes,
    unseat_stranger,
    withdraw_merger,
)
from aerona.services.integrity.grave_links import gather_grave_goods, loose_grave_goods
from aerona.services.integrity.group_links import foreign_leaders, unseat_leader
from aerona.services.integrity.honour_links import lapse_honour, mend_privileges, odd_privileges, overfull_honours
from aerona.services.integrity.interpretation_links import unseat_reader, unskilled_readers
from aerona.services.integrity.interworld_links import astray_campaigns, astray_migrations, end_migration, stranded_landings, withdraw_campaign
from aerona.services.integrity.kin_dynamic_links import (
    dead_elders,
    drop_self_favour,
    end_elder,
    lopsided_rivalries,
    order_rivalry,
    scope_dynamic,
    self_ties,
    unscoped_dynamics,
)
from aerona.services.integrity.kind_links import bring_into_range, cut_lineage, drop_holding, kinds_out_of_range, stray_holdings, tangled_lineage
from aerona.services.integrity.labour_links import (
    bodiless_contracts,
    drop_body,
    drop_unknown_trades,
    overfull_disputes,
    trim_out,
    unknown_trades,
)
from aerona.services.integrity.league_links import back_union, give_organ, non_polity_members, organless_decisions, strike_member, unbacked_unions
from aerona.services.integrity.life_links import (
    adopt_stranger,
    clear_head,
    drop_misread,
    drop_policy,
    drop_practice,
    drop_sexless_norm,
    drop_works,
    even_budget,
    even_upbringing,
    false_captures,
    fit_item,
    fit_remains_to_rite,
    foreign_works,
    free_endowment,
    grown_members,
    headless_heads,
    misfit_classes,
    misfit_remains,
    misread_numbers,
    move_to_square,
    order_ages,
    overreaching_items,
    release_grown,
    return_instrument,
    return_stage,
    sexless_norms,
    strangers_in_kin,
    stray_policies,
    strayed_instruments,
    strayed_practices,
    strayed_stages,
    strike_class,
    uneven_budgets,
    uneven_upbringing,
    unordered_ages,
    unowned_leases,
    venueless_speeches,
    void_lease,
)
from aerona.services.integrity.market_links import beastless_clubs, bind_right, loose_fixings, settle_fixing, unbeast_club, unbound_rights
from aerona.services.integrity.monetary_links import align_issuer, bad_pegs, clear_peg, stray_issuers
from aerona.services.integrity.money_links import clear_metal, clear_source, metal_paper, stray_sources
from aerona.services.integrity.mood_links import mend_mood, odd_moods
from aerona.services.integrity.nature_links import (
    balance_will,
    drop_aims,
    drop_protection,
    ground_outbreak,
    kindless_protections,
    landless_areas,
    lift_landless,
    refit_dwelling,
    settle_strayed_wound,
    stray_aims,
    strayed_wounds,
    strike_unsourced_products,
    unbalanced_wills,
    uncarried_outbreaks,
    unfit_dwellings,
    unsourced_products,
)
from aerona.services.integrity.occupation_links import (
    end_loose_measure,
    end_orphan,
    end_stranger,
    loose_measures,
    mend_service,
    mismatched_service,
    misplaced_measures,
    orphan_regimes,
    place_measure,
    strangers,
)
from aerona.services.integrity.order_links import bad_axes, clean_axes, doubled_orders, drop_order, fail_transition, orphan_transitions
from aerona.services.integrity.package_links import aimless_charms, end_aimless_charm, formless_changes, mend_formless_change, sign_fortune, unsigned_fortunes
from aerona.services.integrity.reckoning_links import align_measure, keep_recorded, mend_fall, reckonings_before_the_fall, stray_measures, unrecorded_acts
from aerona.services.integrity.record_links import (
    absent_witnesses,
    ahead_of_births,
    begin_at_start,
    births_unknown,
    broken_checkpoints,
    clear_nesting,
    crossed_nesting,
    date_birth,
    drop_fact,
    drop_step,
    drop_witness,
    early_moments,
    follow_births,
    follow_cause,
    follow_step,
    give_witness_mode,
    late_beginnings,
    misfit_facts,
    modeless_witnesses,
    retake_checkpoint,
    retire_kind,
    scope_change,
    steps_out_of_order,
    undeclared_steps,
    unknown_kinds,
    unscoped_changes,
)
from aerona.services.integrity.referendum_links import aimless_votes, align_franchise, early_votes, mend_held, stray_franchises, void_vote
from aerona.services.integrity.restoration_links import end_living_fallen, link_restored, living_fallen, unlinked_restored
from aerona.services.integrity.restoration_links import mend_end as mend_restoration_end
from aerona.services.integrity.restoration_links import mismatched_ends as restoration_ends
from aerona.services.integrity.season_shares import even_year, follow_forecast, mend_spell, strayed_forecasts, strayed_spells, uneven_years
from aerona.services.integrity.securities_links import align_price, delist, issuerless, overheld, scale_holdings, stray_prices
from aerona.services.integrity.w52_agent_b import (
    clear_stake,
    dead_promises,
    drop_intoxicant,
    end_promise,
    name_partner,
    partnerless,
    unnamed_stakes,
    unsourced_intoxicants,
)
from aerona.services.integrity.wave_links import stray_coasts, strike_stray_coast

LOCKED = "locked"
NODE_ID_LIST = "_node_ids"
PAST_EPOCHS = frozenset(
    {
        "created_epoch",
        "since_epoch",
        "updated_epoch",
        "registered_epoch",
        "granted_epoch",
        "founded_epoch",
        "made_epoch",
        "taken_epoch",
        "built_epoch",
        "chartered_epoch",
        "defeated_epoch",
        "last_used_epoch",
        "started_epoch",
    }
)
TARGETED_ORDERS = having(ORDER_KIND_TRAITS, OrderKindTrait.TARGETED_ORDERS)
_ = tables


@dataclass(frozen=True)
class Finding:
    check: GenericCheck | None
    invariant: str | None
    table: str
    column: str | None
    key: str
    problem: str
    resolution: str
    remedy: Remedy


@dataclass
class Sweep:
    repaired: dict[str, int]
    findings: list[Finding]


def every_table() -> dict[str, Table]:
    return dict(sorted(Base.metadata.tables.items()))


def free_json(table: Table) -> list[Column[object]]:
    return [column for column in table.columns if type(column.type) is JSON and column.name != LOCKED and not column.name.endswith(NODE_ID_LIST)]


def keyed_by_thing(table: Table) -> bool:
    keys = list(table.primary_key.columns)
    return len(keys) == 1 and any(foreign.column.table.name in {"nodes", "entities"} for foreign in keys[0].foreign_keys)


def coverage() -> dict[str, str]:
    typed: dict[str, list[str]] = {}
    for spec in TYPED:
        typed.setdefault(spec.table, []).append(spec.text)
    found: dict[str, str] = {}
    for name, table in every_table().items():
        if name in typed:
            found[name] = "; ".join(typed[name])
        elif free_json(table):
            found[name] = DERIVED_REASONS["free_json"]
        elif keyed_by_thing(table):
            found[name] = DERIVED_REASONS["profile"]
        else:
            found[name] = DERIVED_REASONS["columns"]
    return found


def row_key(table: Table, row: RowMapping) -> str:
    return ",".join(f"{column.name}={row[column.name]}" for column in table.primary_key.columns)


def key_filter(table: Table, key: str) -> list[ColumnElement[bool]]:
    pairs = dict(part.split("=", 1) for part in key.split(","))
    return [column == type_of(column)(pairs[column.name]) for column in table.primary_key.columns]


def type_of(column: Column[object]) -> Callable[[str], object]:
    return int if isinstance(column.type, Integer) else str


def changed(result: object) -> int:
    return max(0, int(getattr(result, "rowcount", 0) or 0))


async def clamp_bounds(session: AsyncSession, table: Table) -> int:
    mended = 0
    for name, (low, high) in column_bounds(table).items():
        column = table.columns.get(name)
        if column is None:
            continue
        if low is not None:
            mended += changed(await session.execute(update(table).where(column < low).values({name: low})))
        if high is not None:
            mended += changed(await session.execute(update(table).where(column > high).values({name: high})))
    return mended


async def settle_epochs(session: AsyncSession, table: Table, epoch: int) -> int:
    mended = 0
    for column in table.columns:
        if column.name in PAST_EPOCHS and isinstance(column.type, Integer):
            mended += changed(await session.execute(update(table).where(column > epoch).values({column.name: epoch})))
    return mended


async def prune_node_lists(session: AsyncSession, table: Table, nodes: set[int]) -> int:
    mended = 0
    for column in table.columns:
        if not column.name.endswith(NODE_ID_LIST) or type(column.type) is not JSON:
            continue
        for row in (await session.execute(select(table))).mappings().all():
            ids = row[column.name] or []
            kept = [item for item in ids if item in nodes]
            if len(kept) != len(ids):
                await session.execute(update(table).where(*key_filter(table, row_key(table, row))).values({column.name: kept}))
                mended += 1
    return mended


async def odd_enums(session: AsyncSession, table: Table) -> list[Finding]:
    spec = GENERIC[GenericCheck.ENUM_VALUES]
    found: list[Finding] = []
    for column in table.columns:
        if not isinstance(column.type, Enum) or not column.type.enums:
            continue
        rows = (await session.execute(select(table).where(column.is_not(None), column.not_in(list(column.type.enums))))).mappings().all()
        found.extend(
            Finding(GenericCheck.ENUM_VALUES, None, table.name, column.name, row_key(table, row), f"holds {row[column.name]!r}", spec.resolution, spec.remedy)
            for row in rows
        )
    return found


async def stray_locks(session: AsyncSession, table: Table) -> list[Finding]:
    column = table.columns.get(LOCKED)
    if column is None or type(column.type) is not JSON:
        return []
    spec = GENERIC[GenericCheck.LOCKED_NAMES]
    names = set(table.columns.keys())
    found: list[Finding] = []
    for row in (await session.execute(select(table).where(column.is_not(None)))).mappings().all():
        locked = row[LOCKED]
        stray = sorted(str(item) for item in locked if str(item) not in names) if isinstance(locked, list) else []
        if stray:
            found.append(
                Finding(GenericCheck.LOCKED_NAMES, None, table.name, LOCKED, row_key(table, row), f"holds {', '.join(stray)}", spec.resolution, spec.remedy)
            )
    return found


async def generic_sweep(session: AsyncSession, epoch: int) -> Sweep:
    nodes = set(await session.scalars(select(NodeRow.id)))
    repaired = {GenericCheck.BOUNDED.value: 0, GenericCheck.PAST_EPOCHS.value: 0, GenericCheck.NODE_ID_LISTS.value: 0}
    findings: list[Finding] = []
    for table in every_table().values():
        repaired[GenericCheck.BOUNDED.value] += await clamp_bounds(session, table)
        repaired[GenericCheck.PAST_EPOCHS.value] += await settle_epochs(session, table, epoch)
        repaired[GenericCheck.NODE_ID_LISTS.value] += await prune_node_lists(session, table, nodes)
        findings.extend(await odd_enums(session, table))
        findings.extend(await stray_locks(session, table))
    return Sweep(repaired, findings)


async def resolve_generic(session: AsyncSession, finding: Finding) -> None:
    table = every_table()[finding.table]
    where = key_filter(table, finding.key)
    if finding.check is GenericCheck.LOCKED_NAMES:
        row = (await session.execute(select(table).where(*where))).mappings().first()
        if row is not None:
            kept = [item for item in row[LOCKED] or [] if str(item) in table.columns]
            await session.execute(update(table).where(*where).values({LOCKED: kept}))
        return
    column = table.columns[finding.column or ""]
    given = getattr(column.default, "arg", None)
    default = None if callable(given) else given
    if default is not None:
        await session.execute(update(table).where(*where).values({column.name: default}))
    else:
        await session.execute(delete(table).where(*where))


Find = Callable[[AsyncSession], Awaitable[list[int]]]
Fix = Callable[[AsyncSession, int], Awaitable[None]]


async def dead_captors(session: AsyncSession) -> list[int]:
    living = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    query = select(CaptiveRow.id).where(CaptiveRow.status == CaptiveStatus.HELD, CaptiveRow.captor_entity_id.not_in(living))
    return list(await session.scalars(query.order_by(CaptiveRow.id)))


async def dead_ranges(session: AsyncSession) -> list[int]:
    living = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    query = select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.abundance > 0, SpeciesRangeRow.species_entity_id.not_in(living)).distinct()
    return list(await session.scalars(query.order_by(SpeciesRangeRow.species_entity_id)))


async def empty_ranges(session: AsyncSession, species_id: int) -> None:
    await session.execute(update(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == species_id).values(abundance=0))


async def release_captive(session: AsyncSession, captive_id: int) -> None:
    await session.execute(update(CaptiveRow).where(CaptiveRow.id == captive_id).values(status=CaptiveStatus.RELEASED))


async def targetless_orders(session: AsyncSession) -> list[int]:
    query = select(InstructionOrderRow.id).where(
        InstructionOrderRow.kind.in_(TARGETED_ORDERS), InstructionOrderRow.target_node_id.is_(None), InstructionOrderRow.lapsed.is_(False)
    )
    return list(await session.scalars(query.order_by(InstructionOrderRow.id)))


async def lapse_order(session: AsyncSession, order_id: int) -> None:
    await session.execute(update(InstructionOrderRow).where(InstructionOrderRow.id == order_id).values(lapsed=True))


async def self_made(session: AsyncSession) -> list[int]:
    query = select(ConstructRow.entity_id).where(
        (ConstructRow.maker_entity_id == ConstructRow.entity_id) | (ConstructRow.soul_entity_id == ConstructRow.entity_id)
    )
    return list(await session.scalars(query.order_by(ConstructRow.entity_id)))


async def clear_self(session: AsyncSession, construct_id: int) -> None:
    row = await session.get(ConstructRow, construct_id)
    if row is None:
        return
    if row.maker_entity_id == construct_id:
        row.maker_entity_id = None
    if row.soul_entity_id == construct_id:
        row.soul_entity_id = None


async def dead_rulers(session: AsyncSession) -> list[int]:
    living = select(NodeRow.id).where(NodeRow.id.not_in(select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)))
    query = select(BondRow.id).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.not_in(living))
    return list(await session.scalars(query.order_by(BondRow.id)))


async def close_rule(session: AsyncSession, bond_id: int) -> None:
    await session.execute(update(BondRow).where(BondRow.id == bond_id).values(state=BondState.PAST, closed_reason="the ruler is gone"))


def peoples() -> Select[int]:
    return select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE)


def gods() -> CompoundSelect[int]:
    return select(SonRow.id).union(select(ForeignGodRow.id))


async def stray_covenants(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(CovenantRow.id).where(CovenantRow.people_entity_id.not_in(peoples())).order_by(CovenantRow.id)))


async def strike_covenant(session: AsyncSession, covenant_id: int) -> None:
    await session.execute(delete(CovenantRow).where(CovenantRow.id == covenant_id))


async def stray_seats(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(DivineSeatRow.god_node_id).where(DivineSeatRow.god_node_id.not_in(gods())).order_by(DivineSeatRow.god_node_id)))


async def unseat(session: AsyncSession, god_id: int) -> None:
    await session.execute(delete(DivineSeatRow).where(DivineSeatRow.god_node_id == god_id))


async def stray_ties(session: AsyncSession) -> list[int]:
    query = select(PantheonTieRow.god_node_id).where(PantheonTieRow.god_node_id.not_in(gods()) | PantheonTieRow.other_node_id.not_in(gods()))
    return sorted(set(await session.scalars(query)))


async def untie(session: AsyncSession, god_id: int) -> None:
    await session.execute(delete(PantheonTieRow).where((PantheonTieRow.god_node_id == god_id) | (PantheonTieRow.other_node_id == god_id)))


async def stray_syncretisms(session: AsyncSession) -> list[int]:
    query = select(SyncretismRow.id).where(
        SyncretismRow.people_entity_id.not_in(peoples())
        | SyncretismRow.son_id.not_in(select(SonRow.id))
        | SyncretismRow.foreign_god_id.not_in(select(ForeignGodRow.id))
    )
    return list(await session.scalars(query.order_by(SyncretismRow.id)))


async def part_gods(session: AsyncSession, syncretism_id: int) -> None:
    await session.execute(delete(SyncretismRow).where(SyncretismRow.id == syncretism_id))


CHECKS: dict[str, tuple[Find, Fix]] = {
    "cohort_sex_kinds": (stray_cohort_sexes, resplit_cohort_sexes),
    "living_captor": (dead_captors, release_captive),
    "living_range": (dead_ranges, empty_ranges),
    "order_target": (targetless_orders, lapse_order),
    "maker_not_self": (self_made, clear_self),
    "living_ruler": (dead_rulers, close_rule),
    "covenant_people": (stray_covenants, strike_covenant),
    "seat_god": (stray_seats, unseat),
    "tie_gods": (stray_ties, untie),
    "syncretism_kinds": (stray_syncretisms, part_gods),
    "money_metal": (metal_paper, clear_metal),
    "material_source": (stray_sources, clear_source),
    "holding_kind": (stray_holdings, drop_holding),
    "kind_lineage": (tangled_lineage, cut_lineage),
    "kind_ranges": (kinds_out_of_range, bring_into_range),
    "genome_alleles": (stray_alleles, mend_alleles),
    "fact_schema": (misfit_facts, drop_fact),
    "step_nesting": (crossed_nesting, clear_nesting),
    "step_action": (undeclared_steps, drop_step),
    "moment_after_cause": (early_moments, follow_cause),
    "genesis_at_start": (late_beginnings, begin_at_start),
    "moment_after_births": (ahead_of_births, follow_births),
    "birth_dated": (births_unknown, date_birth),
    "step_moment_order": (steps_out_of_order, follow_step),
    "time_shares": (uneven_budgets, even_budget),
    "season_shares": (uneven_years, even_year),
    "long_season_source": (strayed_spells, mend_spell),
    "forecast_world": (strayed_forecasts, follow_forecast),
    "child_ages": (unordered_ages, order_ages),
    "upbringing_shares": (uneven_upbringing, even_upbringing),
    "norm_sexes": (sexless_norms, drop_sexless_norm),
    "youth_years": (grown_members, release_grown),
    "policy_holder": (stray_policies, drop_policy),
    "lease_owner": (unowned_leases, void_lease),
    "works_place": (foreign_works, drop_works),
    "media_reach": (overreaching_items, fit_item),
    "god_reading_real": (false_gods, strike_false_god),
    "creature_group_one_kind": (foreign_leaders, unseat_leader),
    "wave_coast_on_sea": (stray_coasts, strike_stray_coast),
    "honour_holder_limit": (overfull_honours, lapse_honour),
    "honour_privileges": (odd_privileges, mend_privileges),
    "fertility_means_conceive": (barren_means, strike_barren_means),
    "fertility_use_known": (unknown_uses, strike_unknown_use),
    "condition_body_system": (absent_systems, unkind_condition),
    "grave_goods_held": (loose_grave_goods, gather_grave_goods),
    "interpretation_reader": (unskilled_readers, unseat_reader),
    "feeling_spread_values": (odd_moods, mend_mood),
    "plant_product_part": (unsourced_products, strike_unsourced_products),
    "will_shares_whole": (unbalanced_wills, balance_will),
    "dwelling_fits_body": (unfit_dwellings, refit_dwelling),
    "identity_value_target": (lost_identity_targets, clear_identity_target),
    "revival_way_goal": (misfit_revivals, refit_revival),
    "implant_mark_augment": (unbacked_implants, strike_unbacked_implant),
    "tradition_slot_fit": (unslotted_traditions, slot_tradition),
    "outbreak_path_carrier": (uncarried_outbreaks, ground_outbreak),
    "wound_part_in_plan": (strayed_wounds, settle_strayed_wound),
    "betrothal_living": (dead_promises, end_promise),
    "contest_stake_named": (unnamed_stakes, clear_stake),
    "intoxicant_source": (unsourced_intoxicants, drop_intoxicant),
    "symbiotic_partner": (partnerless, name_partner),
    "death_cause_last_wound": (mismatched_deaths, mend_death_cause),
    "charm_names_living_target": (aimless_charms, end_aimless_charm),
    "transformation_target_valid": (formless_changes, mend_formless_change),
    "fortune_has_sign": (unsigned_fortunes, sign_fortune),
    "kin_dynamic_scope": (unscoped_dynamics, scope_dynamic),
    "kin_favour_other": (self_ties, drop_self_favour),
    "kin_rivalry_pair": (lopsided_rivalries, order_rivalry),
    "elder_sway_living": (dead_elders, end_elder),
    "protected_area_region": (landless_areas, lift_landless),
    "species_protection_kind": (kindless_protections, drop_protection),
    "conservation_movement_cause": (stray_aims, drop_aims),
    "right_sources": (unbound_rights, bind_right),
    "club_sport_animals": (beastless_clubs, unbeast_club),
    "fixing_names_match": (loose_fixings, settle_fixing),
    "land_use_rule_district": (stray_rules, widen_rule),
    "conurbation_members": (odd_conurbations, mend_conurbation),
    "interworld_campaign_route": (astray_campaigns, withdraw_campaign),
    "interworld_campaign_landed": (stranded_landings, withdraw_campaign),
    "interworld_migration_route": (astray_migrations, end_migration),
    "mass_weapon_technique": (unskilled_weapons, dismantle),
    "war_remnant_war": (unended_wars, forget_war),
    "war_remnant_place": (misplaced_remnants, place_remnant),
    "deterrence_posture_self": (self_postures, widen_posture),
    "occupation_regime_open": (orphan_regimes, end_orphan),
    "collaboration_place": (strangers, end_stranger),
    "collaboration_end": (mismatched_service, mend_service),
    "occupation_measure_regime": (loose_measures, end_loose_measure),
    "occupation_measure_region": (misplaced_measures, place_measure),
    "restoration_fallen": (living_fallen, end_living_fallen),
    "restoration_predecessor": (unlinked_restored, link_restored),
    "restoration_end": (restoration_ends, mend_restoration_end),
    "leader_cult_leader": (godly_cults, end_godly),
    "leader_cult_promoters": (lost_promoters, keep_promoters),
    "leader_cult_end": (mismatched_ends, mend_end),
    "reckoning_case_acts": (unrecorded_acts, keep_recorded),
    "reckoning_after_fall": (reckonings_before_the_fall, mend_fall),
    "reckoning_measure_realm": (stray_measures, align_measure),
    "referendum_franchise": (stray_franchises, align_franchise),
    "referendum_subject": (aimless_votes, void_vote),
    "referendum_held": (early_votes, mend_held),
    "departure_successor": (handed_to_self, clear_successor),
    "departure_office": (stray_offices, align_office),
    "departure_return": (early_returns, mend_return),
    "economic_order_single": (doubled_orders, drop_order),
    "order_transition_axes": (bad_axes, clean_axes),
    "order_transition_realm": (orphan_transitions, fail_transition),
    "league_members_polities": (non_polity_members, strike_member),
    "league_currency_union": (unbacked_unions, back_union),
    "league_decision_organ": (organless_decisions, give_organ),
    "security_holdings_within": (overheld, scale_holdings),
    "security_issuer_living": (issuerless, delist),
    "security_price_issuer": (stray_prices, align_price),
    "monetary_peg_target": (bad_pegs, clear_peg),
    "monetary_issuer": (stray_issuers, align_issuer),
    "labour_contract_body": (bodiless_contracts, drop_body),
    "labour_dispute_workers": (overfull_disputes, trim_out),
    "worker_body_trades": (unknown_trades, drop_unknown_trades),
    "market_shares_whole": (uneven_shares, even_shares),
    "cartel_sellers": (outside_members, drop_outsiders),
    "price_war_market": (marketless_wars, call_off_war),
    "org_seats_members": (strangers_seated, unseat_stranger),
    "org_votes_whole": (uneven_votes, even_votes),
    "org_merger_parties": (partyless_mergers, withdraw_merger),
    "insolvency_claims": (claimless_creditors, prune_creditors),
    "speech_venue": (venueless_speeches, move_to_square),
    "folk_class_kind": (misfit_classes, strike_class),
    "stage_builder": (strayed_stages, return_stage),
    "endowment_capture": (false_captures, free_endowment),
    "remains_rite": (misfit_remains, fit_remains_to_rite),
    "practice_holder": (strayed_practices, drop_practice),
    "numerology_keys": (misread_numbers, drop_misread),
    "instrument_policy": (strayed_instruments, return_instrument),
    "kin_head_member": (headless_heads, clear_head),
    "kin_member_rule": (strangers_in_kin, adopt_stranger),
    "witness_present": (absent_witnesses, drop_witness),
    "witness_mode": (modeless_witnesses, give_witness_mode),
    "change_in_scope": (unscoped_changes, scope_change),
    "checkpoint_holds": (broken_checkpoints, retake_checkpoint),
    "kind_known": (unknown_kinds, retire_kind),
    "keeper_mortal": (keepers_not_mortal, free_keeper_seat),
}


async def typed_sweep(session: AsyncSession) -> Sweep:
    repaired: dict[str, int] = {}
    findings: list[Finding] = []
    for spec in TYPED:
        find, fix = CHECKS[spec.key]
        broken = await find(session)
        if spec.remedy is Remedy.REPAIR:
            for key in broken:
                await fix(session, key)
            repaired[spec.key] = len(broken)
        else:
            findings.extend(Finding(None, spec.key, spec.table, None, str(key), spec.text, spec.resolution, spec.remedy) for key in broken)
    return Sweep(repaired, findings)


async def sweep(session: AsyncSession) -> Sweep:
    cosmos = await CosmosRepository(session).get()
    epoch = cosmos.epoch if cosmos is not None else 0
    generic = await generic_sweep(session, epoch)
    typed = await typed_sweep(session)
    await session.flush()
    return Sweep({**generic.repaired, **typed.repaired}, [*generic.findings, *typed.findings])


async def findings(session: AsyncSession) -> list[Finding]:
    found: list[Finding] = []
    for table in every_table().values():
        found.extend(await odd_enums(session, table))
        found.extend(await stray_locks(session, table))
    for spec in TYPED:
        if spec.remedy is Remedy.REPORT:
            broken = await CHECKS[spec.key][0](session)
            found.extend(Finding(None, spec.key, spec.table, None, str(key), spec.text, spec.resolution, spec.remedy) for key in broken)
    return found


async def resolve(session: AsyncSession, finding: Finding) -> None:
    if finding.invariant is not None:
        await CHECKS[finding.invariant][1](session, int(finding.key))
    else:
        await resolve_generic(session, finding)
    await session.flush()


async def schema_repairs(session: AsyncSession) -> int:
    return sum((await sweep(session)).repaired.values())
