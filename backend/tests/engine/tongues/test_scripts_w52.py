from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.entities import LanguageProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.tongues import DivineTongueRow, ScriptRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.tongues import LanguagePolicy, ScriptChangeCause
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.tongues.policy import set_policy
from aerona.engine.tongues.scripts import ScriptTally, impose_scripts, record_script, reveal_scripts
from tests.engine.core.factories import CoreWorld, bond, entity, settlement
from tests.engine.tongues.helpers import tongue, tuned


async def test_a_realm_imposes_its_script_on_a_subject_tongue_and_its_speakers_resent_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, script={"imposition_pct": 100, "imposition_grievance": 15})
    realm = await entity(session, "Vale Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    town = await settlement(session, "Lowmere", world, world.regions[0])
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=next(iter(SizeTier))))
    ruling = await tongue(session, world, "Highspeech")
    subject = await tongue(session, world, "Lowtongue")
    await record_script(ctx, ruling, await session.get(LanguageProfileRow, ruling.id), WritingSystem.ALPHABET, cause=ScriptChangeCause.INVENTION)
    await bond(session, town.id, subject.id, BondKind.SPEAKS)
    await set_policy(ctx, realm.id, ruling.id, LanguagePolicy.OFFICIAL, 80)
    before = (await session.get(SettlementProfileRow, town.id)).unrest
    tally = ScriptTally()
    await impose_scripts(ctx, tally)
    assert tally.imposed == 1
    script = await session.get(ScriptRow, (await session.get(LanguageProfileRow, subject.id)).script_id)
    assert script is not None and script.cause is ScriptChangeCause.IMPOSITION and script.system is WritingSystem.ALPHABET
    assert (await session.get(SettlementProfileRow, town.id)).unrest == before + 15
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "script.imposed")) is not None


async def test_a_gods_unwritten_tongue_is_revealed_a_sacred_script(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, script={"revelation_pct": 100})
    sacred = await tongue(session, world, "Godspeech")
    session.add(DivineTongueRow(god_node_id=world.son.id, language_entity_id=sacred.id, locked=[]))
    session.add(LanguageStandingRow(language_entity_id=sacred.id, prestige=50, standardisation=0, locked=[]))
    await session.flush()
    tally = ScriptTally()
    await reveal_scripts(ctx, tally)
    profile = await session.get(LanguageProfileRow, sacred.id)
    script = await session.get(ScriptRow, profile.script_id)
    assert tally.revealed == 1 and script.cause is ScriptChangeCause.REVELATION
    assert (await session.get(LanguageStandingRow, sacred.id)).liturgical
