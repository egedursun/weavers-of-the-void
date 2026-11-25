from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.job import JobRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import DivineWillMode
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.registry import Rules
from aerona.services.player.catalog import run_ledgered
from aerona.services.player.scope import PlayerScope
from tests.tools.divine_will_case import WillCase, WillStep, WillWorld

W = DivineWillToolId
MOOD = {"contentment": 70, "anger": 10}
JOB_ID = "will-job-1"
FIRST_MECHANIC = sorted(REGISTERED)[0]


async def told(session: AsyncSession, world: WillWorld) -> dict[str, int]:
    realm = world.realm
    first = ChronicleRow(epoch=2, year=60, kind=ChronicleKind.CREATION, world_id=realm.cosmos.world_id, text="The Kessar Folk settled the vale.")
    second = ChronicleRow(epoch=3, year=110, kind=ChronicleKind.FATE, world_id=realm.cosmos.world_id, text="The Kessar Folk raised Brinewatch.")
    session.add_all([first, second])
    await session.flush()
    session.add_all([ChronicleEntityRow(chronicle_id=first.id, entity_id=realm.people_id, position=0)])
    cause = IncidentRow(kind="player.history", epoch=2, year=60, world_id=realm.cosmos.world_id, chronicle_id=first.id, magnitude=10, locked=[])
    session.add(cause)
    await session.flush()
    effect = IncidentRow(
        kind="player.history",
        epoch=3,
        year=110,
        world_id=realm.cosmos.world_id,
        place_entity_id=realm.settlement_id,
        cause_incident_id=cause.id,
        chronicle_id=second.id,
        magnitude=20,
        locked=[],
    )
    session.add(effect)
    await session.flush()
    session.add_all(
        [
            IncidentParticipantRow(incident_id=cause.id, node_id=realm.people_id, role=IncidentRole.SUBJECT),
            IncidentParticipantRow(incident_id=effect.id, node_id=realm.people_id, role=IncidentRole.SUBJECT),
        ]
    )
    return {"cause": cause.id, "effect": effect.id, "line": second.id}


async def acted(session: AsyncSession, _world: WillWorld) -> dict[str, int]:
    outcome = await run_ledgered(PlayerScope(session, Rules()), "creator:mood", MOOD)
    assert outcome.ledger_entry_id is not None
    return {"entry": outcome.ledger_entry_id}


async def queued(session: AsyncSession, _world: WillWorld) -> dict[str, int]:
    session.add(JobRow(id=JOB_ID, kind=JobKind.DIVINE_WILL, status=JobStatus.SUCCEEDED, progress=1.0, stage="answered", params={}, result={"cycle_id": 1}))
    return {}


READ_CASES: dict[DivineWillToolId, WillCase] = {
    W.READ_NODE: WillCase(arguments=lambda world: {"node_id": world.realm.people_id}, expect=("Kessar Folk", "## Bonds")),
    W.READ_RECORDS: WillCase(arguments=lambda world: {"node_id": world.realm.people_id}, expect=("bonds",)),
    W.ENUMERATE: WillCase(
        arguments=lambda world: {"kind": "mortal", "filters": {"world_id": world.realm.cosmos.world_id}, "sort": ["-power_level", "name"]},
        expect=("Ilsa Morrow",),
    ),
    W.GRAPH_NEIGHBOURS: WillCase(arguments=lambda world: {"node_id": world.realm.people_id, "depth": 2}, expect=("Kessari", "Thalor")),
    W.GRAPH_PATH: WillCase(arguments=lambda world: {"first_id": world.realm.mortal_id, "second_id": world.realm.son_id}, expect=("Path of",)),
    W.CHRONICLE: WillCase(setup=told, arguments=lambda world: {"node_id": world.realm.people_id}, expect=("settled the vale",)),
    W.EXPLAIN: WillCase(setup=told, arguments=lambda world: {"incident_id": world.ids["effect"]}, expect=("caused by incident", "raised Brinewatch")),
    W.STATE_AT: WillCase(arguments=lambda world: {"epoch": 2, "node_id": world.realm.people_id}, expect=("entities",)),
    W.LEDGER: WillCase(setup=acted, arguments=lambda _world: {"tool": "creator:mood"}, expect=("creator:mood",)),
    W.WORLD_OVERVIEW: WillCase(expect=("Aerona", "Thalor", "Orvael")),
    W.READ_MORE: WillCase(
        prelude=(WillStep(W.ENUMERATE, lambda _world: {"kind": "tables"}),),
        arguments=lambda world: {"handle": world.handles[0]},
        expect=('"page": 2',),
    ),
    W.SEARCH_ACTIONS: WillCase(arguments=lambda _world: {"query": "creator mood"}, expect=("creator:mood",)),
    W.DESCRIBE_ACTION: WillCase(arguments=lambda _world: {"action_id": "creator:mood"}, expect=("contentment", "JSON schema")),
    W.PERFORM_ACTION: WillCase(arguments=lambda _world: {"action_id": "creator:mood", "input": MOOD}, expect=("ledger entry",)),
    W.JOB_STATUS: WillCase(setup=queued, arguments=lambda _world: {"job_id": JOB_ID}, expect=("succeeded",)),
    W.UNDO_ACTION: WillCase(setup=acted, arguments=lambda world: {"ledger_entry_id": world.ids["entry"]}, expect=("is undone",)),
    W.SET_RULE: WillCase(arguments=lambda _world: {"namespace": "divine_will", "name": "page_tokens", "value": 7000}, expect=("changed from 6000 to 7000",)),
    W.RESET_RULE: WillCase(arguments=lambda _world: {"namespace": "divine_will", "name": "page_tokens"}, expect=("reset_rule", "page_tokens")),
    W.SEARCH_RULES: WillCase(
        mode=DivineWillMode.MECHANICS_GUIDE, arguments=lambda _world: {"query": "remembered cycles"}, expect=("divine_will.remembered_cycles",)
    ),
    W.READ_RULE: WillCase(
        mode=DivineWillMode.MECHANICS_GUIDE, arguments=lambda _world: {"namespace": "divine_will", "name": "page_tokens"}, expect=("default: 6000",)
    ),
    W.SEARCH_MECHANICS: WillCase(mode=DivineWillMode.MECHANICS_GUIDE, arguments=lambda _world: {"query": FIRST_MECHANIC}, expect=(FIRST_MECHANIC,)),
    W.READ_MECHANIC: WillCase(mode=DivineWillMode.MECHANICS_GUIDE, arguments=lambda _world: {"key": FIRST_MECHANIC}, expect=(FIRST_MECHANIC,)),
    W.READ_GAME_RULES: WillCase(mode=DivineWillMode.MECHANICS_GUIDE, arguments=lambda _world: {"section": "Agents and model"}, expect=("Agents and model",)),
    W.SUGGEST_MODE: WillCase(arguments=lambda _world: {"mode": "plan", "reason": "The request has many stages."}, expect=("plan mode",)),
}
