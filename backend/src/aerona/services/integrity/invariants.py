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
from aerona.services.integrity.adult_births import adults_born_at_first_sight, date_adult_birth
from aerona.services.integrity.agent_d_links import (
    clear_identity_target,
    lone_disputes,
    lost_identity_targets,
    misfit_revivals,
    name_service_task,
    refit_revival,
    reopen_unnamed_mediation,
    settle_lone_dispute,
    slot_tradition,
    strike_unbacked_implant,
    taskless_services,
    unbacked_implants,
    unnamed_mediations,
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
from aerona.services.integrity.birth_sign_epochs import date_birth_sign, signs_born_too_late
from aerona.services.integrity.chronology import close_judgment, early_judgments, early_rites, follow_rite, heard_later, overaged, set_age, unborn_witnesses
from aerona.services.integrity.city_links import mend_conurbation, odd_conurbations, stray_rules, widen_rule
from aerona.services.integrity.cohort_sexes import resplit_cohort_sexes, stray_cohort_sexes
from aerona.services.integrity.collection_titles import mixed_collection_titles, provisional_collection_titles, retitle_collection, retitle_provisional
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
from aerona.services.integrity.derived_names import follow_old_names, stale_derived_names
from aerona.services.integrity.dwelling_places import mortals_in_no_place, settle_in_place
from aerona.services.integrity.ended_rebuilds import close_rebuild, rebuilds_of_the_ended
from aerona.services.integrity.ended_remains import (
    armies_led_by_the_dead,
    dead_with_health,
    empty_the_ruin,
    release_their_commands,
    ruins_still_peopled,
    still_the_dead,
)
from aerona.services.integrity.fact_keys import drop_undeclared_facts, facts_beyond_their_kind
from aerona.services.integrity.fertility_links import barren_means, strike_barren_means, strike_unknown_use, unknown_uses
from aerona.services.integrity.generation_counts import fit_generations, generations_beyond_people
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
from aerona.services.integrity.habitable_homes import (
    homes_moved_off_their_orbit,
    homes_too_harsh,
    light_star_by_its_kind,
    return_home_to_its_orbit,
    settle_home_climate,
    stars_lit_astray,
)
from aerona.services.integrity.history_splits import name_plague_by_its_sickness, occasions_joined_in_one, plagues_named_otherwise, split_occasions
from aerona.services.integrity.honour_links import lapse_honour, mend_privileges, odd_privileges, overfull_honours
from aerona.services.integrity.injury_years import date_injury_in_its_time, injuries_out_of_their_time
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
from aerona.services.integrity.law_names import laws_named_twice, name_law_once
from aerona.services.integrity.league_links import back_union, give_organ, non_polity_members, organless_decisions, strike_member, unbacked_unions
from aerona.services.integrity.league_names import leagues_without_article, name_league_properly, name_offshoot_after_its_leader, offshoots_named_after_a_clique
from aerona.services.integrity.life_labels import drop_child_label, grown_children
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
from aerona.services.integrity.memory_causes import causes_without_their_subject, unlink_cause
from aerona.services.integrity.monetary_links import align_issuer, bad_pegs, clear_peg, stray_issuers
from aerona.services.integrity.money_links import clear_metal, clear_source, metal_paper, stray_sources
from aerona.services.integrity.mood_links import mend_mood, odd_moods, retell_mood_line, stray_mood_lines
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
from aerona.services.integrity.polity_mirror import mirror_polity_stats, polity_stats_astray
from aerona.services.integrity.reckoning_links import align_measure, keep_recorded, mend_fall, reckonings_before_the_fall, stray_measures, unrecorded_acts
from aerona.services.integrity.record_links import (
    absent_witnesses,
    ahead_of_births,
    begin_at_start,
    births_after_sighting,
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
    redate_birth,
    retake_checkpoint,
    retire_kind,
    scope_change,
    steps_out_of_order,
    undeclared_steps,
    unknown_kinds,
    unscoped_changes,
)
from aerona.services.integrity.referendum_links import aimless_votes, align_franchise, early_votes, mend_held, stray_franchises, void_vote
from aerona.services.integrity.remembrances import remember_what_it_tells, remembrances_forgetting
from aerona.services.integrity.restoration_links import end_living_fallen, link_restored, living_fallen, unlinked_restored
from aerona.services.integrity.restoration_links import mend_end as mend_restoration_end
from aerona.services.integrity.restoration_links import mismatched_ends as restoration_ends
from aerona.services.integrity.rite_collections import file_rite_under_its_dead, rites_in_another_dead
from aerona.services.integrity.route_waters import roads_over_water, sail_road
from aerona.services.integrity.season_names import rename_twin_season, twin_season_names
from aerona.services.integrity.season_shares import even_year, follow_forecast, mend_spell, strayed_forecasts, strayed_spells, uneven_years
from aerona.services.integrity.securities_links import align_price, delist, issuerless, overheld, scale_holdings, stray_prices
from aerona.services.integrity.son_contact import count_divine_mind_epochs, divine_minds_behind, remember_the_audience, sons_unaware_of_an_audience
from aerona.services.integrity.son_essence import fit_son_essence, sons_over_their_cap
from aerona.services.integrity.son_relation_notes import (
    bonds_described_by_a_fragment,
    covenants_between_enemies,
    end_covenant_of_enemies,
    name_both_in_grudges,
    nameless_grudges,
    restore_bond_description,
)
from aerona.services.integrity.star_clocks import clocks_past_their_age, wind_clock_to_age
from aerona.services.integrity.strain_names import name_strain_once, stacked_strains
from aerona.services.integrity.tenures import bound_tenure, tenures_beyond_presence
from aerona.services.integrity.title_names import rank_worded_titles, rename_by_rank
from aerona.services.integrity.tradition_kinds import give_tradition_its_kind, traditions_unlike_their_kind
from aerona.services.integrity.tradition_slots import misfit_traditions, refit_tradition
from aerona.services.integrity.untimely_keepings import keepings_told_as_timely, tell_keeping_out_of_time
from aerona.services.integrity.w52_agent_a import (
    command_by_word,
    drop_hand_over,
    end_adoption,
    faceless_hand_overs,
    last_an_epoch,
    link_by_name,
    mark_residence,
    nameless_commands,
    orphaned_adoptions,
    reach_by_sight,
    run_by_day,
    unconditioned_rites,
    unknown_true_names,
    unlinked_rites,
    unpartnered_unions,
    untimed_orders,
)
from aerona.services.integrity.w52_agent_b import (
    accountless_tellings,
    ancestorless_revivals,
    clear_stake,
    dead_promises,
    drop_intoxicant,
    drop_positioning,
    end_promise,
    gift_material,
    misfit_carriers,
    name_partner,
    open_unseasoned,
    paper_record,
    partnerless,
    realign_method,
    settle_unheard,
    sourceless_materials,
    stray_methods,
    tell_of_holder,
    unheard_tongues,
    unlinked_positioning,
    unload_carrier,
    unnamed_stakes,
    unpowered_records,
    unrevive,
    unseasoned_routes,
    unsourced_intoxicants,
)
from aerona.services.integrity.w52_agent_c import (
    drop_aid,
    drop_lift,
    made_servitor,
    masterless_defectors,
    nameless_regalia,
    open_penances,
    plain_hospitality,
    plain_piece,
    set_penance,
    siteless_moves,
    stay_in_place,
    unchartered_freedom,
    unknown_aids,
    unknown_dealer,
    unknown_locks,
    unlock,
    unnamed_slayers,
    unpowered_lifts,
)
from aerona.services.integrity.w52_agent_d import (
    band_by_mass,
    breathe_by_chemistry,
    drop_end_source,
    keep_fitting_places,
    kindless_exemptions,
    let_it_pass,
    misbanded_worlds,
    misplaced_life,
    sourceless_falls,
    spare_no_one,
    stray_end_sources,
    unfit_breaths,
)
from aerona.services.integrity.w52_agent_e import (
    drop_flood,
    dry_floods,
    misplaced_grounds,
    misplaced_moles,
    place_honour,
    refit_settle_mode,
    reground_battle,
    unfit_settle_modes,
    unplace_mole,
    unplaced_honours,
)
from aerona.services.integrity.w52_agent_f import misplaced_crews, oathless_paroles, release_oathless, release_unwed, strike_misplaced_crew, unwed_joiners
from aerona.services.integrity.w52_agent_g import (
    dismiss_petition,
    drop_sign,
    kindless_rebirths,
    misplaced_spirits,
    rebirth_by_people,
    refit_spirit,
    targetless_vengeance,
    unmarked_signs,
)
from aerona.services.integrity.w52_agent_h import clear_ordnance, misgrounded_expeditions, reground_expedition, remnantless_ordnance
from aerona.services.integrity.w52_agent_i import place_regional_being, sourceless_rifts, unplaced_regional_beings, unsource_rift
from aerona.services.integrity.w52_agent_j import (
    drop_passage,
    lift_to_surface,
    misplaced_below,
    settle_passage_state,
    unbound_passages,
    wrong_passage_states,
)
from aerona.services.integrity.war_names import name_war_by_its_parties, wars_named_after_strangers
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
    "birth_at_first_sight": (births_after_sighting, redate_birth),
    "age_since_birth": (overaged, set_age),
    "judgment_at_epoch_close": (early_judgments, close_judgment),
    "rite_after_death": (early_rites, follow_rite),
    "witness_born": (unborn_witnesses, heard_later),
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
    "mood_told_of_its_own": (stray_mood_lines, retell_mood_line),
    "mortal_dwells_in_a_place": (mortals_in_no_place, settle_in_place),
    "grown_out_of_childhood": (grown_children, drop_child_label),
    "route_mode_fits_water": (roads_over_water, sail_road),
    "polity_stats_follow_record": (polity_stats_astray, mirror_polity_stats),
    "collection_title_one_standing": (mixed_collection_titles, retitle_collection),
    "collection_title_current_names": (provisional_collection_titles, retitle_provisional),
    "title_named_plainly": (rank_worded_titles, rename_by_rank),
    "season_names_distinct": (twin_season_names, rename_twin_season),
    "tradition_slot_fits_kind": (misfit_traditions, refit_tradition),
    "strain_named_once": (stacked_strains, name_strain_once),
    "injury_dated_in_its_time": (injuries_out_of_their_time, date_injury_in_its_time),
    "tenure_within_presence": (tenures_beyond_presence, bound_tenure),
    "law_named_once": (laws_named_twice, name_law_once),
    "birth_sign_by_age": (signs_born_too_late, date_birth_sign),
    "generations_within_people": (generations_beyond_people, fit_generations),
    "son_essence_within_cap": (sons_over_their_cap, fit_son_essence),
    "son_knows_its_audience": (sons_unaware_of_an_audience, remember_the_audience),
    "son_bond_described_plainly": (bonds_described_by_a_fragment, restore_bond_description),
    "god_grudge_names_both": (nameless_grudges, name_both_in_grudges),
    "son_covenant_between_friends": (covenants_between_enemies, end_covenant_of_enemies),
    "divine_mind_counts_its_epochs": (divine_minds_behind, count_divine_mind_epochs),
    "adult_born_before_first_sight": (adults_born_at_first_sight, date_adult_birth),
    "star_lit_by_its_kind": (stars_lit_astray, light_star_by_its_kind),
    "remembrance_names_its_past": (remembrances_forgetting, remember_what_it_tells),
    "star_clock_follows_its_age": (clocks_past_their_age, wind_clock_to_age),
    "home_on_its_lived_orbit": (homes_moved_off_their_orbit, return_home_to_its_orbit),
    "peopled_world_habitable": (homes_too_harsh, settle_home_climate),
    "rebuild_of_a_standing_town": (rebuilds_of_the_ended, close_rebuild),
    "dead_without_health": (dead_with_health, still_the_dead),
    "army_led_by_the_living": (armies_led_by_the_dead, release_their_commands),
    "ruin_without_people": (ruins_still_peopled, empty_the_ruin),
    "war_named_by_its_parties": (wars_named_after_strangers, name_war_by_its_parties),
    "rite_filed_under_its_dead": (rites_in_another_dead, file_rite_under_its_dead),
    "occasion_holds_one_occasion": (occasions_joined_in_one, split_occasions),
    "league_named_with_article": (leagues_without_article, name_league_properly),
    "offshoot_named_after_a_person": (offshoots_named_after_a_clique, name_offshoot_after_its_leader),
    "plague_named_by_its_sickness": (plagues_named_otherwise, name_plague_by_its_sickness),
    "memory_cause_names_its_subject": (causes_without_their_subject, unlink_cause),
    "incident_facts_declared": (facts_beyond_their_kind, drop_undeclared_facts),
    "tradition_kind_fits_subtype": (traditions_unlike_their_kind, give_tradition_its_kind),
    "untimely_keeping_told": (keepings_told_as_timely, tell_keeping_out_of_time),
    "derived_names_follow": (stale_derived_names, follow_old_names),
    "plant_product_part": (unsourced_products, strike_unsourced_products),
    "will_shares_whole": (unbalanced_wills, balance_will),
    "dwelling_fits_body": (unfit_dwellings, refit_dwelling),
    "identity_value_target": (lost_identity_targets, clear_identity_target),
    "revival_way_goal": (misfit_revivals, refit_revival),
    "crisis_mediator_named": (unnamed_mediations, reopen_unnamed_mediation),
    "disputed_claim_contender": (lone_disputes, settle_lone_dispute),
    "service_names_task": (taskless_services, name_service_task),
    "implant_mark_augment": (unbacked_implants, strike_unbacked_implant),
    "tradition_slot_fit": (unslotted_traditions, slot_tradition),
    "outbreak_path_carrier": (uncarried_outbreaks, ground_outbreak),
    "wound_part_in_plan": (strayed_wounds, settle_strayed_wound),
    "betrothal_living": (dead_promises, end_promise),
    "spirit_fits_place": (misplaced_spirits, refit_spirit),
    "deep_positions_valid": (misplaced_below, lift_to_surface),
    "passage_state_fits": (wrong_passage_states, settle_passage_state),
    "passage_ends_exist": (unbound_passages, drop_passage),
    "vengeance_names_target": (targetless_vengeance, dismiss_petition),
    "luck_sign_marked": (unmarked_signs, drop_sign),
    "rebirth_kind_named": (kindless_rebirths, rebirth_by_people),
    "contest_stake_named": (unnamed_stakes, clear_stake),
    "relocation_names_site": (siteless_moves, stay_in_place),
    "mortal_slayer_named": (unnamed_slayers, unknown_dealer),
    "penance_names_deed": (open_penances, set_penance),
    "defector_names_former_god": (masterless_defectors, made_servitor),
    "regalia_names_polity": (nameless_regalia, plain_piece),
    "free_city_has_charter": (unchartered_freedom, plain_hospitality),
    "lock_technique_known": (unknown_locks, unlock),
    "lift_energy_known": (unpowered_lifts, drop_lift),
    "aid_technique_known": (unknown_aids, drop_aid),
    "revived_tongue_ancestor": (ancestorless_revivals, unrevive),
    "tongue_modality_heard": (unheard_tongues, settle_unheard),
    "electronic_record_technique": (unpowered_records, paper_record),
    "seasonal_route_season": (unseasoned_routes, open_unseasoned),
    "route_carrier_medium": (misfit_carriers, unload_carrier),
    "positioning_needs_network": (unlinked_positioning, drop_positioning),
    "material_origin_source": (sourceless_materials, gift_material),
    "method_in_its_process": (stray_methods, realign_method),
    "account_tells_something": (accountless_tellings, tell_of_holder),
    "hand_over_names_person": (faceless_hand_overs, drop_hand_over),
    "law_named_kind": (kindless_exemptions, spare_no_one),
    "air_fits_biochemistry": (unfit_breaths, breathe_by_chemistry),
    "life_place_fits_world": (misplaced_life, keep_fitting_places),
    "fall_has_source": (sourceless_falls, let_it_pass),
    "world_end_source": (stray_end_sources, drop_end_source),
    "gravity_fits_mass": (misbanded_worlds, band_by_mass),
    "union_names_spouse": (unpartnered_unions, mark_residence),
    "adoption_names_adopter": (orphaned_adoptions, end_adoption),
    "spy_institution_in_target": (misplaced_moles, unplace_mole),
    "siege_flood_has_water": (dry_floods, drop_flood),
    "settle_mode_fits": (unfit_settle_modes, refit_settle_mode),
    "battle_ground_fits": (misplaced_grounds, reground_battle),
    "unit_honour_names_place": (unplaced_honours, place_honour),
    "linked_rite_has_link": (unlinked_rites, reach_by_sight),
    "rite_condition_named": (unconditioned_rites, last_an_epoch),
    "true_name_link_known": (unknown_true_names, link_by_name),
    "timed_order_has_times": (untimed_orders, run_by_day),
    "true_name_command_named": (nameless_commands, command_by_word),
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
    "crew_station_fits": (misplaced_crews, strike_misplaced_crew),
    "being_scale_reach": (unplaced_regional_beings, place_regional_being),
    "rift_cause_source": (sourceless_rifts, unsource_rift),
    "parole_names_oath": (oathless_paroles, release_oathless),
    "ordnance_names_remnant": (remnantless_ordnance, clear_ordnance),
    "expedition_ground_fits": (misgrounded_expeditions, reground_expedition),
    "married_in_names_union": (unwed_joiners, release_unwed),
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
