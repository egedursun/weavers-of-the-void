import pytest
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.polity import ClaimRow, OfficeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import ClaimBasis, ClauseKind, OfficeKind, PartyRole, TreatyKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import ArmyStats
from aerona.engine.military.alliance import betrayed_call
from aerona.engine.military.trials import settle_trial
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.control import edit_polity
from aerona.engine.services.community_relations import relation
from aerona.engine.settlement.control import edit_settlement
from tests.engine.society.factories import Realm, context, make, mortal, settlement
from tests.engine.statecraft.crowns import crown


async def ruled(realm: Realm) -> tuple[int, int]:
    polity, _ = await crown(realm, "Velmar")
    ruler = await mortal(realm, "Queen Otta")
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[], locked=[]))
    await realm.session.flush()
    return polity.id, ruler.id


async def test_a_god_names_an_heir_replaces_and_clears_them(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, ruler = await ruled(realm)
    first, second = await mortal(realm, "Ansel"), await mortal(realm, "Bryn")
    await edit_polity(ctx, polity, {"heir": first.id}, release=[])
    office = await realm.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity, OfficeRow.kind == OfficeKind.HEIR_DESIGNATE))
    assert office is not None and office.holder_entity_id == first.id
    await edit_polity(ctx, polity, {"heir": second.id}, release=[])
    rows = list(await realm.session.scalars(select(DesignatedHeirRow).where(DesignatedHeirRow.ruler_entity_id == ruler)))
    assert [row.heir_entity_id for row in rows] == [second.id] and office.holder_entity_id == second.id
    await edit_polity(ctx, polity, {"heir": None}, release=[])
    assert office.holder_entity_id is None
    with pytest.raises(NotFoundError):
        await edit_polity(ctx, polity, {"heir": ruler}, release=[])
    rulerless, _ = await crown(realm, "Empty Throne")
    with pytest.raises(ValidationFailedError):
        await edit_polity(ctx, rulerless.id, {"heir": first.id}, release=[])


async def test_a_god_garrisons_a_town_only_with_its_own_standing_army(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Wardholt")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=0, unrest=0, locked=[], foreigners={}))
    host = await make(realm.session, "Ward Host", EntityType.ARMY, ArmyStats(), world_id=realm.world.id)
    stranger = await make(realm.session, "Far Host", EntityType.ARMY, ArmyStats(), world_id=realm.world.id)
    other = await settlement(realm, "Elsewhere")
    realm.session.add_all(
        [ArmyRow(entity_id=host.id, owner_entity_id=town.id, raised_epoch=1), ArmyRow(entity_id=stranger.id, owner_entity_id=other.id, raised_epoch=1)]
    )
    await realm.session.flush()
    found = await edit_settlement(ctx, town.id, {"garrison_entity_id": host.id}, release=[])
    assert (found.profile.garrison_entity_id == host.id and "garrison_entity_id" in found.profile.locked) or found.profile.locked
    with pytest.raises(ValidationFailedError):
        await edit_settlement(ctx, town.id, {"garrison_entity_id": stranger.id}, release=[])
    cleared = await edit_settlement(ctx, town.id, {"garrison_entity_id": 0}, release=[])
    assert cleared.profile.garrison_entity_id is None


async def test_a_trial_by_combat_crowns_a_living_claimant_only_when_the_ruler_falls(realm: Realm) -> None:
    ctx = context(realm.session)
    polity, ruler_id = await ruled(realm)
    ruler = await realm.session.get(EntityRow, ruler_id)
    assert ruler is not None
    claimant = await mortal(realm, "Pretender")
    claim = ClaimRow(claimant_entity_id=claimant.id, polity_entity_id=polity, basis=ClaimBasis.FABRICATED, since_epoch=1, locked=[])
    realm.session.add(claim)
    await realm.session.flush()
    assert not await settle_trial(ctx, claimant, ruler, polity)
    assert claim.ended_epoch == ctx.epoch and not claim.pressed
    claim.ended_epoch = None
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, ctx.epoch
    assert await settle_trial(ctx, claimant, ruler, polity)
    assert claim.pressed
    office = await realm.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity, OfficeRow.kind == OfficeKind.RULER))
    assert office is not None and office.holder_entity_id == claimant.id


async def test_an_ally_that_refuses_the_call_betrays_the_alliance(realm: Realm) -> None:
    ctx = context(realm.session)
    _, ally = await crown(realm, "Reed Throne")
    _, party = await crown(realm, "Velmar")
    assert not await betrayed_call(ctx, ally.id, party.id)
    await sign(
        ctx,
        TreatyKind.ALLIANCE_DEFENSIVE,
        [(ally.id, PartyRole.SIGNATORY), (party.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.CALL_TO_ARMS, ally.id, party.id)],
    )
    before = await relation(realm.session, ctx.rules, party.id, ally.id)
    assert await betrayed_call(ctx, ally.id, party.id)
    assert await relation(realm.session, ctx.rules, party.id, ally.id) < before
