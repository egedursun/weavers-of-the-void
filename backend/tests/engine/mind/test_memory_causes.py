from sqlalchemy import select

from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.mind.memories import remember
from aerona.engine.phases.religion_spread import ConversionSource, _announce
from aerona.engine.primitives.faith import FaithIndex
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules
from tests.engine.core.factories import son_draft
from tests.engine.society.factories import Realm, context, mortal, settlement

RULES = Rules()


async def test_a_memory_skips_a_happening_that_leaves_out_the_one_who_remembers(realm: Realm) -> None:
    ctx = context(realm.session)
    holder, giver, receiver = [await mortal(realm, name) for name in ("Ines", "Saral", "Othmem")]
    await record(ctx, "society.rivalry", roles={IncidentRole.ACTOR: giver.id, IncidentRole.CO_ACTOR: receiver.id})
    memory = await remember(realm.session, RULES, holder_id=holder.id, subject_id=giver.id, kind=MemoryKind.GOODWILL, magnitude=10, epoch=ctx.epoch)
    assert memory is not None and memory.incident_id is None and memory.step_id is None


async def test_a_god_who_lost_faithful_remembers_the_very_conversion(realm: Realm) -> None:
    ctx = context(realm.session)
    sons = SonRepository(realm.session)
    robbed = await sons.create(son_draft("Oskel", realm.world.id))
    taker = await sons.create(son_draft("Haskel", realm.world.id))
    elsewhere = await settlement(realm, "Domar")
    town = await settlement(realm, "Zera")
    faith = FaithIndex({}, {robbed.id: robbed, taker.id: taker}, None, {}, set())
    await _announce(ctx, elsewhere, faith, taker.id, ConversionSource(robbed.id, 0.5, "a sign"), syncretic=False)
    await _announce(ctx, town, faith, robbed.id, ConversionSource(taker.id, 0.5, "a sign"), syncretic=False)
    await realm.session.flush()
    memory = await realm.session.scalar(
        select(MemoryRow).where(MemoryRow.holder_node_id == robbed.id, MemoryRow.subject_node_id == taker.id, MemoryRow.kind == MemoryKind.STOLE_FAITHFUL)
    )
    assert memory is not None and memory.incident_id is not None
    roles = dict(
        (role, node)
        for node, role in await realm.session.execute(
            select(IncidentParticipantRow.node_id, IncidentParticipantRow.role).where(IncidentParticipantRow.incident_id == memory.incident_id)
        )
    )
    assert roles[IncidentRole.SUBJECT] == town.id
    assert roles[IncidentRole.PREDECESSOR] == robbed.id
    assert roles[IncidentRole.TARGET] == taker.id


async def test_offerings_added_beside_an_old_god_leave_its_altars_warm(realm: Realm) -> None:
    ctx = context(realm.session)
    sons = SonRepository(realm.session)
    kept = await sons.create(son_draft("Oskel", realm.world.id))
    added = await sons.create(son_draft("Haskel", realm.world.id))
    faith = FaithIndex({}, {kept.id: kept, added.id: added}, None, {}, set())
    both = await settlement(realm, "Kevek")
    turned = await settlement(realm, "Zera")
    await _announce(ctx, both, faith, kept.id, ConversionSource(added.id, 0.5, "a sign"), syncretic=True)
    await _announce(ctx, turned, faith, kept.id, ConversionSource(added.id, 0.5, "a sign"), syncretic=False)
    await realm.session.flush()
    facts = {
        (kind, key, name)
        for kind, key, name in await realm.session.execute(
            select(IncidentRow.kind, IncidentFactRow.key, IncidentFactRow.name).join(IncidentFactRow, IncidentFactRow.incident_id == IncidentRow.id)
        )
    }
    assert not any(kind == "religion.syncretism" and key in {"cold", "forsaken"} for kind, key, _ in facts)
    assert ("religion.conversion", "forsaken", "Oskel") in facts
