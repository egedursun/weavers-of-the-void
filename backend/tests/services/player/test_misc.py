import pytest
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityTagRow
from aerona.db.tables.meta import ScenarioRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import LedgerOperation, ScenarioKey, ScenarioStatus
from aerona.domain.enums.world import FateMode, ImageStyle, SonDistribution
from aerona.rules.registry import Rules
from aerona.services.player import catalog, cheats, creator, diplomacy, goals, settings
from aerona.services.player.scope import Effect, PlayerScope, perform
from tests.services.player.factories import PlayerWorld, action_kinds, ledger_changes, make_entity, make_son


async def test_creator_actions(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    await creator.set_creator_note(scope, creator.CreatorNote(text="x" * (rules.god_actions.note_max_chars + 50)))
    assert world.creator.note is not None and len(world.creator.note) == rules.god_actions.note_max_chars
    await creator.set_passions(scope, creator.SetPassions(passions=(CreatorPassion.ORDER, CreatorPassion.MERCY)))
    assert world.creator.passions == [CreatorPassion.ORDER, CreatorPassion.MERCY] and not world.creator.passions_automatic
    await creator.set_passions(scope, creator.SetPassions(automatic=True))
    assert world.creator.passions_automatic
    son = await make_son(session, "Velkar", world.world.id)
    with pytest.raises(ValidationFailedError):
        await creator.nudge_reputation(scope, creator.NudgeReputation(son_id=son.id))
    nudged = await creator.nudge_reputation(scope, creator.NudgeReputation(son_id=son.id, love=20))
    assert nudged.values["love"] is not None
    profile = await creator.creator_profile(scope)
    assert profile.name == world.creator.name and profile.traces


async def test_scenarios(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await goals.start_scenario(scope, goals.StartScenario(key=ScenarioKey.LONG_PEACE))
    row = await session.scalar(select(ScenarioRow).where(ScenarioRow.key == ScenarioKey.LONG_PEACE))
    assert row is not None and row.status is ScenarioStatus.RUNNING
    with pytest.raises(Exception, match="already running"):
        await goals.start_scenario(scope, goals.StartScenario(key=ScenarioKey.LONG_PEACE))
    await goals.abandon_scenario(scope, goals.AbandonScenario(scenario_id=row.id))
    await session.refresh(row)
    assert row.status is ScenarioStatus.ABANDONED
    with pytest.raises(ValidationFailedError):
        await goals.abandon_scenario(scope, goals.AbandonScenario(scenario_id=row.id))


async def test_settings_and_cheat(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    await settings.update_settings(
        scope, settings.WorldSettings(fate_mode=FateMode.OFF, son_distribution=SonDistribution.MANUAL, council_every_epochs=0, mortal_agent_parallelism=2)
    )
    assert world.cosmos.fate_mode is FateMode.OFF and world.cosmos.son_distribution is SonDistribution.MANUAL
    with pytest.raises(ValidationFailedError):
        await settings.update_settings(scope, settings.WorldSettings(mortal_agent_parallelism=0))
    before = world.creator.essence
    outcome = await cheats.cheat_essence(scope, cheats.CheatEssence(amount=40))
    assert world.creator.essence == before + 40 and outcome.essence_gained == 40
    with pytest.raises(ValidationFailedError):
        await cheats.cheat_essence(scope, cheats.CheatEssence(amount=rules.server.cheat_essence_max + 1))


async def test_the_image_style_is_chosen_from_the_list_or_written_by_the_god(scope: PlayerScope, world: PlayerWorld) -> None:
    painted = next(style for style in ImageStyle if style is not ImageStyle.CUSTOM)
    told = await settings.update_settings(scope, settings.WorldSettings(image_style=painted))
    assert world.cosmos.image_style is painted and "style" in told.message
    with pytest.raises(ValidationFailedError):
        await settings.update_settings(scope, settings.WorldSettings(image_style=ImageStyle.CUSTOM, image_style_custom="   "))
    with pytest.raises(ValidationFailedError):
        await settings.update_settings(scope, settings.WorldSettings(image_style=ImageStyle.CUSTOM, image_style_custom="x" * 10000))
    custom = await settings.update_settings(scope, settings.WorldSettings(image_style=ImageStyle.CUSTOM, image_style_custom="  a look of my own  "))
    assert world.cosmos.image_style is ImageStyle.CUSTOM and world.cosmos.image_style_custom == "a look of my own"
    assert "a look of my own" in custom.message
    with pytest.raises(ValidationFailedError):
        await settings.update_settings(scope, settings.WorldSettings())


async def test_seek_route_refuses_when_nothing(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    try:
        outcome = await diplomacy.seek_route(scope, diplomacy.EntityTarget(entity_id=town.id))
    except ValidationFailedError as error:
        assert "road to every known world" in error.message
        return
    assert outcome.ledger_entry_id is not None


async def test_catalog_lists_every_action(scope: PlayerScope, rules: Rules) -> None:
    descriptors = catalog.describe(rules)
    ids = [item.id for item in descriptors]
    assert len(ids) == len(set(ids))
    rows = {row for spec in catalog.ACTIONS for row in spec.rows}
    assert {"ACT-074", "INT-019", "SVC-130", "ACT-163", "SVC-197"} <= rows
    merge = next(item for item in descriptors if item.id == "record:merge")
    assert merge.confirmation == "MERGE"
    deify = next(item for item in descriptors if item.id == "deify")
    assert str(rules.god_power.deify_cost) in deify.cost
    assert all(item.input_schema.get("type") == "object" for item in descriptors)
    outcome = await catalog.run_ledgered(scope, "creator:mood", {"anger": 10})
    assert outcome.action == "creator:mood"
    with pytest.raises(NotFoundError):
        catalog.action("nothing")


async def test_journal_captures_core_statements(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    session.add(EntityTagRow(entity_id=world.region.id, tag="old"))
    await session.flush()

    async def body() -> Effect:
        await session.execute(insert(EntityTagRow).values(entity_id=world.region.id, tag="new"))
        await session.execute(delete(EntityTagRow).where(EntityTagRow.tag == "old"))
        await session.execute(update(EntityTagRow).where(EntityTagRow.tag == "new").values(tag="newer"))
        return Effect("tags shuffled", world.region.id)

    outcome = await perform(scope, "test:tags", ActionKind.EDIT_RECORD, creator.CreatorNote(), body)
    assert outcome.ledger_entry_id is not None
    changes = [change for change in await ledger_changes(session, outcome.ledger_entry_id) if change.table_name == "entity_tags"]
    operations = sorted(change.operation for change in changes)
    assert operations == sorted([LedgerOperation.DELETE, LedgerOperation.INSERT])
    inserted = next(change for change in changes if change.operation is LedgerOperation.INSERT)
    assert inserted.after is not None and inserted.after["tag"] == "newer"
    assert await session.scalar(select(func.count()).select_from(EntityTagRow)) == 1
    assert await action_kinds(session) == [ActionKind.EDIT_RECORD]
