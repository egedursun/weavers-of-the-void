import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.renown import DeedClaimRow, DeedRow, LoreTradeRow, ReputationRow, RulerCurrencyRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LoreKind, ReputationAxis
from aerona.services.player import renown
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def hero(session: AsyncSession, world: PlayerWorld, name: str) -> int:
    found = await make_entity(session, name, EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    return found.id


async def test_the_god_sets_holds_and_erases_a_reputation_and_a_standing(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    subject = await hero(session, world, "Aldo")
    made = await renown.set_reputation(scope, renown.SetReputation(subject_id=subject, community_id=world.region.id, axis=ReputationAxis.WISDOM, value=70))
    row = await session.get(ReputationRow, made.values["reputation_id"])
    assert row is not None and row.value == 70 and row.locked == ["value"]
    await renown.remove_reputation(scope, renown.ReputationTarget(reputation_id=row.id))
    assert await session.get(ReputationRow, row.id) is None
    with pytest.raises(ValidationFailedError):
        await renown.set_reputation(scope, renown.SetReputation(subject_id=subject, community_id=subject, axis=ReputationAxis.WISDOM, value=10))
    await renown.set_currency(scope, renown.SetStanding(subject_id=subject, prestige=40, dread=30, silenced_until=9))
    purse = await session.get(RulerCurrencyRow, subject)
    assert purse is not None and purse.prestige == 40 and purse.dread == 30 and purse.silenced_until == 9 and "prestige" in purse.locked
    await renown.remove_currency(scope, renown.StandingTarget(subject_id=subject))
    assert await session.get(RulerCurrencyRow, subject) is None


async def test_the_god_records_retells_and_strikes_deeds_and_their_claims(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    doer, liar = await hero(session, world, "Bede"), await hero(session, world, "Cuth")
    made = await renown.add_deed(scope, renown.RecordDeed(doer_id=doer, axis=ReputationAxis.HEROISM, magnitude=40, place_id=world.region.id))
    deed = await session.get(DeedRow, made.values["deed_id"])
    assert deed is not None and deed.witnesses == 1
    await renown.edit_deed(scope, renown.EditDeed(deed_id=deed.id, magnitude=60, token=True, note="the wolf's tongue"))
    assert deed.magnitude == 60 and deed.token and "magnitude" in deed.locked
    claimed = await renown.set_claim(scope, renown.SetDeedClaim(deed_id=deed.id, claimant_id=liar, kind=ClaimKind.FALSE, hold=False))
    claim = await session.get(DeedClaimRow, claimed.values["claim_id"])
    assert claim is not None and claim.kind is ClaimKind.FALSE
    await renown.expose_claim(scope, renown.DeedClaimTarget(claim_id=claim.id))
    assert claim.status is ClaimStatus.EXPOSED
    with pytest.raises(ValidationFailedError):
        await renown.expose_claim(scope, renown.DeedClaimTarget(claim_id=claim.id))
    await renown.remove_claim(scope, renown.DeedClaimTarget(claim_id=claim.id))
    assert await session.get(DeedClaimRow, claim.id) is None
    await renown.remove_deed(scope, renown.DeedTarget(deed_id=deed.id))
    assert await session.get(DeedRow, deed.id) is None


async def test_the_god_passes_lore_and_strikes_the_record(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    seller = await make_entity(session, "Dale", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    buyer = await make_entity(session, "Eske", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    technique = next(iter(Technique))
    session.add(HolderTechniqueRow(holder_entity_id=seller.id, technique=technique, since_epoch=1, secret=False))
    await session.flush()
    made = await renown.trade_lore(scope, renown.TradeLore(seller_id=seller.id, buyer_id=buyer.id, kind=LoreKind.TECHNIQUE, key=technique.value))
    trade = await session.get(LoreTradeRow, made.values["trade_id"])
    assert trade is not None and await session.get(HolderTechniqueRow, (buyer.id, technique)) is not None
    with pytest.raises(ValidationFailedError):
        await renown.trade_lore(scope, renown.TradeLore(seller_id=seller.id, buyer_id=buyer.id, kind=LoreKind.TECHNIQUE, key=technique.value))
    await renown.remove_trade(scope, renown.TradeTarget(trade_id=trade.id))
    assert await session.get(LoreTradeRow, trade.id) is None
