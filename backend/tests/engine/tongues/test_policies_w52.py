from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import POLICIES
from aerona.db.tables.culture import LanguageStandingRow, SpeakerCohortRow
from aerona.db.tables.entities import LanguageProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.tongues import LanguagePolicyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.tongues import LanguagePolicy, LanguageStage
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.tongues.drift import drift_scale
from aerona.engine.tongues.policy import PolicyTally, choose_shield, press, set_policy
from tests.engine.core.factories import CoreWorld, bond, entity, settlement
from tests.engine.tongues.helpers import tongue, tuned


async def realm_with(session: AsyncSession, world: CoreWorld, name: str) -> tuple:
    realm = await entity(session, name, EntityType.POLITY, PolityStats(), world_id=world.world.id)
    town = await settlement(session, f"{name} Town", world, world.regions[0])
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=next(iter(SizeTier))))
    await session.flush()
    return realm, town


async def test_a_protected_tongue_keeps_its_speakers_and_eases_their_unrest(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, tongues={"protected_floor": 30, "protected_grievance_cut": 10})
    realm, town = await realm_with(session, world, "Vale")
    minority = await tongue(session, world, "Hillspeech")
    await bond(session, town.id, minority.id, BondKind.SPEAKS)
    session.add(SpeakerCohortRow(community_entity_id=town.id, language_entity_id=minority.id, kind=SpeakerKind.NATIVE, share=5, since_epoch=1, locked=[]))
    profile = await session.get(SettlementProfileRow, town.id)
    profile.unrest = 40
    row = await set_policy(ctx, realm.id, minority.id, LanguagePolicy.PROTECTED, 100)
    await press(ctx, row, PolicyTally())
    assert (await session.get(SpeakerCohortRow, (town.id, minority.id, SpeakerKind.NATIVE))).share == 30
    assert profile.unrest == 30
    assert POLICIES[LanguagePolicy.PROTECTED].shields


async def test_an_academy_raises_standardisation_and_slows_drift(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, tongues={"standard_gain": 10, "standard_drift_cut_pct": 50})
    realm, _town = await realm_with(session, world, "Vale")
    language = await tongue(session, world, "Highspeech")
    session.add(LanguageStandingRow(language_entity_id=language.id, prestige=50, standardisation=0, locked=[]))
    await session.flush()
    free = await drift_scale(ctx, language.id)
    row = await set_policy(ctx, realm.id, language.id, LanguagePolicy.STANDARDISED, 100)
    await press(ctx, row, PolicyTally())
    assert (await session.get(LanguageStandingRow, language.id)).standardisation == 10
    assert await drift_scale(ctx, language.id) < free


async def test_a_made_tongue_spreads_by_law_at_its_own_rate(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, tongues={"constructed_spread_pct": 9}, language_policy={"official_gain": 1})
    realm, town = await realm_with(session, world, "Vale")
    made = await tongue(session, world, "Ordal")
    (await session.get(LanguageProfileRow, made.id)).stage = LanguageStage.CONSTRUCTED
    row = await set_policy(ctx, realm.id, made.id, LanguagePolicy.OFFICIAL, 100)
    await press(ctx, row, PolicyTally())
    second = await session.get(SpeakerCohortRow, (town.id, made.id, SpeakerKind.SECOND))
    assert second is not None and second.share == 9


async def test_a_realm_chooses_to_protect_a_minority_tongue(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, tongues={"protect_pct": 100})
    realm, town = await realm_with(session, world, "Vale")
    minority = await tongue(session, world, "Hillspeech")
    await bond(session, town.id, minority.id, BondKind.SPEAKS)
    await choose_shield(ctx, realm, PolicyTally())
    assert await session.get(LanguagePolicyRow, (realm.id, minority.id, LanguagePolicy.PROTECTED)) is not None
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "language.policy_set")) is not None
