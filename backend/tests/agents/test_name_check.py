from aerona.agents.fate.name_check import dialect_letters, is_weak, name_problems, type_named_subtype
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.prompts.contexts.narrative import NameProblem
from aerona.rules.registry import Rules
from aerona.services.name_report import name_report
from tests.agents.world import PHONOLOGY, AgentWorld


def test_weak_and_dialect_names() -> None:
    rules = Rules()
    assert is_weak("Imi", rules)
    assert is_weak("Isal", rules)
    assert not is_weak("Korvessa", rules)
    assert dialect_letters("Kuzat", PHONOLOGY) == ["u", "z"]
    assert dialect_letters("Kalmor", PHONOLOGY) == []


async def test_name_problems_flag_a_lookalike_of_a_god(database: Database, rules: Rules, world: AgentWorld) -> None:
    son = world.core.son
    lookalike = son.name[:-1] + ("a" if son.name[-1] != "a" else "e")
    async with database.write() as session:
        entity = await session.get(EntityRow, world.pending.id)
        assert entity is not None
        warning = await name_problems(session, rules, entity, lookalike, phonology=None)
        clean = await name_problems(session, rules, entity, "Torvamelkis", phonology=None)
    assert warning is not None
    assert NameProblem.SIMILAR in warning.problems
    assert warning.similar_to is not None
    assert clean is None


async def test_dialect_fit_report_counts_misfit_names(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        entity = await session.get(EntityRow, world.creation.id)
        assert entity is not None
        entity.name = "Uzbek Hollow"
        await session.flush()
        report = await name_report(session, rules)
    home = next(item for item in report.worlds if item.world_id == world.core.world.id)
    assert home.misfits >= 1
    assert report.misfits >= 1


def test_a_subtype_naming_only_the_type_is_refused() -> None:
    assert type_named_subtype("legend", EntityType.LEGEND) is None
    assert type_named_subtype("legend (the drowned bell)", EntityType.LEGEND) == "the drowned bell"
    assert type_named_subtype("salt cave", EntityType.PLACE) == "salt cave"
