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
