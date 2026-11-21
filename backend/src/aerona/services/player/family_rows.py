from collections.abc import Awaitable, Callable

from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.services.player.record_rows import (
    CreateRow,
    EditRow,
    RowTarget,
    make_row,
    reshape_row,
    unmake_row,
)
from aerona.services.player.scope import ActionOutcome, Command, Effect, PlayerScope, player_action

FAMILY_TABLES: dict[str, str] = {
    "care_custom": "care_customs",
    "housework": "housework",
    "domestic_service": "domestic_service",
    "leisure_pursuit": "leisure_pursuits",
    "space_norm": "space_norms",
    "kin_role_duty": "kin_role_duties",
    "kin_group": "kin_groups",
    "kin_group_member": "kin_group_members",
    "infant_care": "infant_care",
    "child_standing": "child_standing",
    "socialization": "socialization",
    "pedagogy": "pedagogy",
    "intimacy_norm": "intimacy_norms",
    "restraint_custom": "restraint_customs",
    "reproductive_course": "reproductive_courses",
    "legitimacy_rule": "legitimacy_rules",
    "child_recognition": "child_recognitions",
    "youth_standing": "youth_standing",
    "youth_group": "youth_groups",
    "youth_group_member": "youth_group_members",
    "population_policy": "population_policies",
    "population_instrument": "population_instruments",
    "shop": "shops",
    "shop_good": "shop_goods",
    "supply_tier": "supply_tiers",
    "promotion": "promotions",
    "lease": "leases",
    "public_works": "public_works",
    "public_work_stage": "public_work_stages",
    "state_enterprise": "state_enterprises",
    "record_medium": "record_media",
    "media_outlet": "media_outlets",
    "media_item": "media_items",
    "humour_style": "humour_styles",
    "speech": "speeches",
    "folk_knowledge": "folk_knowledge",
    "folk_class": "folk_classes",
    "endowment": "endowments",
    "death_work": "death_work",
    "facet_practice": "facet_practices",
    "profession_of_value": "professions_of_value",
    "weather_work": "weather_works",
    "observation_method": "observation_methods",
    "plant_part": "plant_parts",
    "plant_anatomy": "plant_anatomy",
    "sensitivity": "sensitivities",
    "body_system": "body_systems",
    "disease_agent": "disease_agents",
    "local_climate": "local_climates",
    "coast": "coasts",
    "sediment_flow": "sediment_flows",
    "region_cryosphere": "region_cryosphere",
    "space_weather_event": "space_weather_events",
    "star_activity": "star_activity",
    "world_field": "world_fields",
    "org_governance": "org_governance",
    "org_seat": "org_seats",
    "org_clique": "org_cliques",
    "org_merger": "org_mergers",
    "org_research": "org_research",
    "insolvency_case": "insolvency_cases",
    "market_structure": "market_structures",
    "cartel": "cartels",
    "price_war": "price_wars",
    "worker_body": "worker_bodies",
    "labour_contract": "labour_contracts",
    "labour_dispute": "labour_disputes",
    "monetary_authority": "monetary_authorities",
    "stock_exchange": "stock_exchanges",
    "issued_security": "issued_securities",
    "security_holding": "security_holdings",
    "security_price": "security_prices",
    "polity_league": "polity_leagues",
    "league_member": "league_members",
    "league_decision": "league_decisions",
    "departure": "departures",
    "referendum": "referendums",
    "reckoning": "reckonings",
    "reckoning_measure": "reckoning_measures",
    "reckoning_case": "reckoning_cases",
    "leader_cult": "leader_cults",
    "restoration": "restorations",
    "occupation_regime": "occupation_regimes",
    "collaboration": "collaborations",
    "occupation_measure": "occupation_measures",
    "mass_weapon": "mass_weapons",
    "deterrence_posture": "deterrence_postures",
    "war_remnant": "war_remnants",
    "interworld_campaign": "interworld_campaigns",
    "orbital_control": "orbital_control",
    "interworld_migration": "interworld_migrations",
    "land_use_rule": "land_use_rules",
    "municipal_service": "municipal_services",
    "conurbation": "conurbations",
    "protected_area": "protected_areas",
    "species_protection": "species_protections",
    "conservation_movement": "conservation_movements",
    "kin_dynamic": "kin_dynamics",
    "kin_favour": "kin_favours",
    "kin_rivalry": "kin_rivalries",
    "kin_disowning": "kin_disownings",
    "kin_blend": "kin_blends",
    "elder_sway": "elder_sway",
    "feeling_spread": "feeling_spread",
    "interpretation": "interpretations",
    "grave_good": "grave_goods",
    "agentless_condition": "agentless_conditions",
    "fertility_means": "fertility_means",
    "fertility_use": "fertility_uses",
    "honour_kind": "honour_kinds",
    "honour_held": "honours_held",
    "sea_wave": "sea_waves",
    "sea_wave_coast": "sea_wave_coasts",
    "wave_warning": "wave_warnings",
    "creature_group": "creature_groups",
    "divine_conception": "divine_conceptions",
    "god_reading": "god_readings",
}


type Handler[C: Command] = Callable[[PlayerScope, C], Awaitable[ActionOutcome]]


def fixed(prefix: str, table: str) -> str:
    expected = FAMILY_TABLES[prefix]
    if table != expected:
        raise ValidationFailedError(f"This lever shapes {expected.replace('_', ' ')}, not {table.replace('_', ' ')}.")
    return expected


def creator(prefix: str) -> Handler[CreateRow]:
    async def body(scope: PlayerScope, command: CreateRow) -> Effect:
        fixed(prefix, command.table)
        return await make_row(scope, command)

    return player_action(f"{prefix}:create", ActionKind.EDIT_RECORD)(body)


def editor(prefix: str) -> Handler[EditRow]:
    async def body(scope: PlayerScope, command: EditRow) -> Effect:
        fixed(prefix, command.table)
        return await reshape_row(scope, command)

    return player_action(f"{prefix}:edit", ActionKind.EDIT_RECORD)(body)


def remover(prefix: str) -> Handler[RowTarget]:
    async def body(scope: PlayerScope, command: RowTarget) -> Effect:
        fixed(prefix, command.table)
        return await unmake_row(scope, command)

    return player_action(f"{prefix}:delete", ActionKind.EDIT_RECORD)(body)
