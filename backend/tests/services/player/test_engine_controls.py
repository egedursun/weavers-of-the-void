import ast
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import aerona.services.player as player_package
from aerona.core.errors import AeronaError, ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.phases.factions import FactionKind
from aerona.rules.registry import Rules
from aerona.services.player import beyond, catalog, cosmic_orders, creatures, divine, heroes, memory, pantheon, settlements, society, warfare
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, make_entity, make_son

ENGINE_MANUAL_FUNCTIONS = (
    "protect_from_ruin",
    "abandon_settlement",
    "order_resettlement",
    "bless_with_child",
    "raise_notable_by_hand",
    "crown_ruler",
    "order_village",
    "trigger_ethnogenesis",
    "awaken_species",
    "designate_heir",
    "lay_spirit_to_rest",
    "retire_record",
    "set_class_shares",
    "set_satisfaction",
    "set_stores",
    "send_famine",
    "send_plenty",
    "order_forge",
    "incite_class_uprising",
    "set_resource_yield",
    "order_minting",
    "commission_work",
    "order_exodus",
    "order_cultural_contact",
    "proclaim_golden_age",
    "end_golden_age",
    "set_tier",
    "grant_independence",
    "reclaim_colony",
    "order_previous_creation",
    "impose_loan",
    "forgive_debt",
    "enforce_debt",
    "order_barter",
    "order_adoption",
    "order_treaty",
    "raise_hero",
    "send_on_quest",
    "resolve_quest",
    "recall_hero",
    "assign_apprentice",
    "send_hero_to_hunt",
    "decree_faction",
    "dissolve_faction",
    "force_battle",
    "open_war_now",
    "raise_war_army",
    "disband_army",
    "bless_army",
    "order_duel",
    "grant_victory",
    "end_war_by_decree",
    "incite_uprising",
    "order_spy_operation",
    "free_prisoner",
    "order_ransom",
    "decree_tribute",
    "forgive_tribute",
    "decree_betrayal",
    "decree_alliance",
    "end_blood_feud",
    "order_feeding",
    "force_mutation",
    "force_people_split",
    "cross_species",
    "place_megafauna_trail",
    "cull_species",
    "spare_prey",
    "introduce_species",
    "force_soul_descent",
    "order_soul_harvest",
    "order_planet_act",
    "order_archive",
    "order_archive_reading",
    "order_cosmic_plague",
    "order_mirror_birth",
    "set_immortal",
    "abandon_legendary_quest",
    "order_time_echo",
    "order_horror_event",
    "order_outer_being",
    "spawn_outer_cult",
    "suppress_outer_cult",
    "set_son_sanity",
    "trigger_apocalypse",
    "set_doom_clock",
    "provoke_duel",
    "order_god_war",
    "order_temple_raid",
    "wake_foreign_god",
    "set_son_relation",
    "retire_legend",
    "revive_legend",
    "event_to_legend",
    "manifest_legend",
    "fulfil_prophecy",
    "retire_prophecy",
    "regenerate_world_map",
    "set_epoch_star",
    "teach_route_knowledge",
    "order_foreign_god_land",
    "set_deposit_owner",
    "found_wandering_market",
    "spawn_route_raiders",
    "disband_faction",
    "set_route_danger",
    "pour_essence",
    "trigger_sign",
    "grant_protection",
    "order_foreign_strike",
    "apply_drift_now",
    "evaluate_now",
    "give_first_faith",
)
NEW_GROUPS = (
    catalog.SETTLEMENT_ACTIONS
    + catalog.SOCIETY_ACTIONS
    + catalog.CIVILIZATION_ACTIONS
    + catalog.HERO_ACTIONS
    + catalog.WARFARE_ACTIONS
    + catalog.CREATURE_ACTIONS
    + catalog.BEYOND_ACTIONS
    + catalog.PANTHEON_ACTIONS
    + catalog.MEMORY_ACTIONS
    + catalog.COSMIC_ORDER_ACTIONS
    + catalog.DIVINE_ACTIONS
)
NEW_SYNC_ACTIONS = tuple(spec for spec in NEW_GROUPS if spec.sync is not None)
MISSING_ID = 987654


def _called_names() -> set[str]:
    names: set[str] = set()
    for path in Path(player_package.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, ast.Attribute):
                    names.add(target.attr)
    return names


def test_every_engine_manual_function_has_a_player_action() -> None:
    assert sorted(set(ENGINE_MANUAL_FUNCTIONS) - _called_names()) == []
    assert all((spec.sync is None) != (spec.job is None) for spec in NEW_GROUPS)


def _value(annotation: Any) -> Any:
    options = [item for item in get_args(annotation) if item is not type(None)] if get_origin(annotation) is not None else [annotation]
    kind = options[0] if options else annotation
    if get_origin(kind) is dict:
        return {}
    if isinstance(kind, type) and issubclass(kind, Enum):
        return next(iter(kind)).value
    if kind is bool:
        return True
    if kind is int:
        return MISSING_ID
    if kind is float:
        return 1.0
    return "missing"


def _payload(model: type[BaseModel]) -> dict[str, Any]:
    return {name: _value(field.annotation) for name, field in model.model_fields.items() if field.is_required() or name.endswith("_id")}


@pytest.mark.parametrize("spec", NEW_SYNC_ACTIONS, ids=lambda spec: spec.id)
async def test_engine_controls_refuse_missing_targets_cleanly(scope: PlayerScope, world: PlayerWorld, spec: catalog.ActionSpec) -> None:
    payload = _payload(spec.input_model)
    if not any(isinstance(value, int) and value == MISSING_ID for value in payload.values()):
        return
    with pytest.raises((AeronaError, ValueError)):
        await catalog.run_ledgered(scope, spec.id, payload)


async def test_ruin_shelter_and_settlement_orders(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    outcome = await settlements.shelter_from_ruin(scope, settlements.RuinShelter(settlement_id=town.id))
    assert outcome.values["changed"] is True and outcome.ledger_entry_id is not None
    assert await EntityRepository(session).has_flag(town.id, EntityFlag.PROTECTED_FROM_RUIN)
    await settlements.shelter_from_ruin(scope, settlements.RuinShelter(settlement_id=town.id, protected=False))
    assert not await EntityRepository(session).has_flag(town.id, EntityFlag.PROTECTED_FROM_RUIN)
    with pytest.raises(ValidationFailedError):
        await settlements.shelter_from_ruin(scope, settlements.RuinShelter(settlement_id=world.region.id))
    retired = await settlements.retire(scope, settlements.RetireRecord(entity_id=town.id, status=EntityStatus.DESTROYED))
    assert retired.target_node_id == town.id and town.status is EntityStatus.DESTROYED
    assert await action_kinds(session) == [ActionKind.SHELTER_FROM_RUIN, ActionKind.SHELTER_FROM_RUIN, ActionKind.DESTROY]


async def test_doom_clock_and_apocalypse_guard(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await beyond.doom_clock(scope, beyond.DoomClock(value=3))
    cosmos = (await session.scalars(select(CosmosRow))).one()
    assert cosmos.doom_clock == 3 and outcome.values["doom_clock"] == 3
    with pytest.raises(ValidationFailedError):
        await beyond.doom_clock(scope, beyond.DoomClock(value=-1))
    with pytest.raises(ValidationFailedError):
        await beyond.apocalypse(scope, beyond.Apocalypse(calling=True))


async def test_map_regeneration_and_golden_age(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    redrawn = await cosmic_orders.regenerate_map(scope, cosmic_orders.WorldTarget(world_id=world.world.id))
    assert redrawn.target_node_id == world.world.id and int(redrawn.values["regions"] or 0) >= 1
    await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    golden = await society.golden_age(scope, society.WorldTarget(world_id=world.world.id))
    assert int(golden.values["communities"] or 0) >= 1
    ended = await society.close_golden_age(scope, society.WorldTarget(world_id=world.world.id))
    assert ended.message == "The golden age ended."


async def test_spare_prey_and_feeding_guards(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    prey = await make_entity(session, "Ash Deer", EntityType.SPECIES, world_id=world.world.id, location_id=world.region.id)
    with pytest.raises(ValidationFailedError):
        await creatures.spare(scope, creatures.SpeciesTarget(species_id=prey.id))
    with pytest.raises(ValidationFailedError):
        await creatures.feed(scope, creatures.Feeding(species_id=prey.id))


async def test_factions_heroes_and_legends(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    founded = await heroes.found_faction(scope, heroes.Faction(community_id=town.id, kind=next(iter(FactionKind))))
    assert founded.created_ids
    dissolved = await heroes.dissolve(scope, heroes.FactionTarget(faction_id=founded.created_ids[0]))
    faction = await session.get(EntityRow, dissolved.target_node_id)
    assert faction is not None and faction.status is not EntityStatus.CANON
    legend = await make_entity(session, "The Ash Song", EntityType.LEGEND, world_id=world.world.id, stats=LegendStats(spread=30))
    await memory.forget_legend(scope, memory.LegendTarget(legend_id=legend.id))
    assert legend.status is not EntityStatus.CANON
    await memory.revive(scope, memory.LegendTarget(legend_id=legend.id))
    assert legend.status is EntityStatus.CANON


async def test_pantheon_and_divine_controls(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    first = await make_son(session, "Velkar", world.world.id)
    second = await make_son(session, "Oruna", world.world.id)
    outcome = await pantheon.relation(scope, pantheon.SonRelation(first_id=first.id, second_id=second.id, value=40))
    assert outcome.values["relation"] == 40
    with pytest.raises(ValidationFailedError):
        await pantheon.relation(scope, pantheon.SonRelation(first_id=first.id, second_id=first.id, value=10))
    sane = await beyond.sanity(scope, beyond.Sanity(son_id=first.id, value=55))
    assert sane.values["sanity"] == 55
    son = await session.get(SonRow, first.id)
    assert son is not None and son.sanity == 55
    before = world.creator.essence
    poured = await divine.pour(scope, divine.Pour(amount=1))
    assert world.creator.essence == before - 1 and poured.essence_spent == 1
    weighed = await divine.evaluate(scope, divine.Empty())
    assert "completed" in weighed.values
    with pytest.raises(ValidationFailedError):
        await divine.pour(scope, divine.Pour(amount=0))
    assert ActionKind.SET_SON_RELATION in await action_kinds(session)


async def test_warfare_orders(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    opened = await warfare.open_war(scope, warfare.OpenWar(attacker_id=first.id, defender_id=second.id))
    war_id = int(opened.values["war_id"] or 0)
    assert war_id
    ended = await warfare.end_war(scope, warfare.EndWar(war_id=war_id))
    assert ended.values["ending"] == "peace"
    with pytest.raises(ValidationFailedError):
        await warfare.bless(scope, warfare.ArmyBlessing(army_id=first.id))
    with pytest.raises(ValidationFailedError):
        await warfare.end_feud(scope, warfare.Feud(first_id=first.id, second_id=second.id))
