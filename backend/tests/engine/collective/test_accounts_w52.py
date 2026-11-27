from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.collective import ACCOUNT_KINDS, ACCOUNT_STANCES, REMEMBERING_KINDS
from aerona.db.tables.collective import AccountRow, AccountStanceRow, CommemorationRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import ClaimRow
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.collective.accounts import HistoryTally, age_accounts, distance_from_truth, record, strike
from aerona.engine.context import TickContext
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, mortal, tuned_rules


def test_songs_and_genealogies_and_the_three_new_stances_live_in_the_catalogue() -> None:
    assert ACCOUNT_KINDS[AccountKind.SONG].sung and AccountKind.SONG in REMEMBERING_KINDS
    assert ACCOUNT_KINDS[AccountKind.GENEALOGY].backs_claims
    assert ACCOUNT_STANCES[AccountStance.LAMENT].grieves and ACCOUNT_STANCES[AccountStance.MOCK].standing_rule == "mock_standing_effect"


async def test_a_mocking_song_lowers_its_targets_fame_and_is_told_as_made(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    ruler = await mortal(session, "Corvan", world, None)
    session.add(MortalProfileRow(entity_id=ruler.id, renown=50))
    await session.flush()
    song = await record(
        ctx,
        world.people,
        AccountKind.SONG,
        fidelity=50,
        stances={ruler.id: AccountStance.MOCK},
        subject_id=ruler.id,
        medium=AccountMedium.PERFORMANCE,
        credence=100,
    )
    assert song is not None
    assert (await session.get(MortalProfileRow, ruler.id)).renown == 50 + ctx.rules.historiography.mock_standing_effect
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "account.made")) is not None
    told = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.template_key == "account.made"))
    assert told == f"{world.people.name} came to keep a song of Corvan, told through performance."
    assert distance_from_truth(song, [AccountStance.MOCK]) == 60


async def test_a_song_changes_with_each_singer_gains_hearers_and_outlasts_a_striking(session: AsyncSession, world: CoreWorld) -> None:
    drift = {"song_drift_pct": 10, "song_spread": 5, "credence_decay": 0, "fidelity_decay": 0}
    ctx = await manual_context(session, "test", rules=tuned_rules(historiography=drift))
    ruler = await mortal(session, "Corvan", world, None)
    song = await record(ctx, world.people, AccountKind.SONG, fidelity=50, stances={ruler.id: AccountStance.MOCK}, subject_id=ruler.id, credence=40)
    await age_accounts(ctx, HistoryTally())
    assert song.fidelity == 45 and song.credence == 45
    await strike(ctx, world.people.id, ruler.id, HistoryTally())
    kept = await session.get(AccountStanceRow, (song.id, ruler.id))
    assert kept is not None and kept.stance is AccountStance.MOCK


async def test_a_lament_keeps_the_memory_of_a_loss(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    plague = CollectionRow(kind=CollectionKind.PLAGUE, name="The Grey Year", world_id=world.world.id, start_epoch=1)
    session.add(plague)
    await session.flush()
    await record(ctx, world.people, AccountKind.FOLK_MEMORY, fidelity=50, stances={world.people.id: AccountStance.LAMENT}, collection_id=plague.id)
    memory = await session.get(CommemorationRow, (world.people.id, plague.id))
    assert memory is not None and not memory.pride and memory.strength == ctx.rules.historiography.lament_grief


async def test_a_genealogy_glorifying_a_claimant_backs_its_claims(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm = await entity(session, "Vale Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    heir = await mortal(session, "Ilsa", world, None)
    claim = ClaimRow(claimant_entity_id=heir.id, polity_entity_id=realm.id, strength=40, basis=next(iter(ClaimBasis)), locked=[])
    session.add(claim)
    await session.flush()
    written = await record(ctx, world.people, AccountKind.GENEALOGY, fidelity=60, stances={heir.id: AccountStance.GLORIFY}, subject_id=heir.id, credence=100)
    assert written is not None
    assert claim.strength == 40 + ctx.rules.historiography.genealogy_claim_weight
    stored = await session.scalar(select(AccountRow.kind).where(AccountRow.id == written.id))
    assert stored is AccountKind.GENEALOGY
