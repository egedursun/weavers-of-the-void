import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds import g09_faith, g15_gods
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactValue
from aerona.domain.enums.son import Stat
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.duels import son_duel
from aerona.engine.recording.render import render_incident
from aerona.engine.transform.record import record_transformation
from tests.engine.core.factories import CoreWorld, entity, son_draft

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
OWNED_ELSEWHERE = frozenset({"creator.hand"})


def sample(spec: IncidentKindSpec) -> dict[str, object]:
    found: dict[str, object] = {}
    for fact in spec.facts:
        if fact.value is FactValue.NUMBER:
            found[fact.key] = 3
        elif fact.value is FactValue.ENUM and fact.enum is not None:
            found[fact.key] = next(iter(fact.enum))
        else:
            found[fact.key] = "Sample"
    return found


def test_every_faith_and_god_kind_is_real_and_told_from_its_roles_and_facts() -> None:
    kinds = [spec for module in (g09_faith, g15_gods) for spec in module.KINDS if spec.told and spec.key not in OWNED_ELSEWHERE]
    drafts = [spec.key for spec in kinds if spec.draft]
    roleless = [spec.key for spec in kinds if not spec.roles]
    assert drafts == [] and roleless == []
    for spec in kinds:
        text = render_incident(spec, {role.role: ["Ana", "Bel", "Cor"] for role in spec.roles}, sample(spec))
        assert text and "{" not in text, spec.key


async def test_a_transformation_is_one_record_with_its_subject_and_product(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    mortal = await entity(session, "Orel", EntityType.MORTAL, MortalStats(), world_id=world.world.id)
    row = await record_transformation(ctx, TransformKind.SPIRIT_RISING, mortal.id, world.son.id)
    incident = await session.get_one(IncidentRow, row.incident_id)
    roles = {
        (item.node_id, item.role) for item in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident.id))
    }
    facts = {item.key: item.name for item in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id))}
    assert incident.kind == "transform.spirit_rising"
    assert {(mortal.id, IncidentRole.SUBJECT), (world.son.id, IncidentRole.PRODUCT)} <= roles
    assert facts == {"subject_name": "Orel", "result_name": world.son.name}


async def test_a_feud_duel_is_told_once_under_its_own_kind_with_typed_scores(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    rival = await SonRepository(session).create(son_draft("Velmar", world.world.id))
    await son_duel(ctx, world.son, rival, Stat.WILL, "old feud", key="pantheon.rival_clash")
    incidents = list(await session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(["pantheon.rival_clash", "pantheon.duel"]))))
    assert [item.kind for item in incidents] == ["pantheon.rival_clash"]
    facts = {item.key: item for item in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incidents[0].id))}
    assert {"stat", "winner", "loser", "first", "second", "wound", "stolen"} <= set(facts)
    assert {facts["winner"].node_id, facts["loser"].node_id} == {world.son.id, rival.id}
    assert facts["stat"].enum_value == Stat.WILL.value


ENTITY_PLACES = ("place", "origin", "destination")
NODES_OUTSIDE_ENTITIES = frozenset({"ClusterRow", "CreatorRow", "DimensionRow", "ForeignGodRow", "GalaxyRow", "NodeRow", "SonRow", "StarRow", "WorldRow"})


def scanner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("incident_sites", REPOSITORY_ROOT / "scripts" / "incident_sites.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["incident_sites"] = module
    spec.loader.exec_module(module)
    return module


def test_no_happening_is_placed_at_a_node_that_is_not_an_entity() -> None:
    sites = scanner()
    index = sites.build_index()
    found: list[str] = []
    for path, tree in index.modules.items():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and sites.called_name(node) in {"record", "record_incident"}):
                continue
            for keyword in node.keywords:
                value = keyword.value
                if keyword.arg in ENTITY_PLACES and isinstance(value, ast.Attribute) and value.attr == "id":
                    kind = sites.type_of(index, value.value, sites.enclosing_function(index, node))
                    if kind in NODES_OUTSIDE_ENTITIES:
                        found.append(f"{path.relative_to(sites.SOURCE)}:{node.lineno} {keyword.arg}={ast.unparse(value)} ({kind})")
    assert found == []
