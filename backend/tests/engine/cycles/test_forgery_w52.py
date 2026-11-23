from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.market_kinds import FORGERIES, FORGERY_CRIMES
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import ClaimRow
from aerona.domain.enums.arts import ForgeryKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.models.entity_stats import TitleStats
from aerona.engine.arts.control import forge_work
from aerona.engine.arts.forgery import expose
from tests.engine.core.factories import CoreWorld, entity, mortal
from tests.engine.core.test_cycles_w21 import context, realm_of, town_of


def test_every_forgery_kind_maps_to_its_crime_and_every_forgery_crime_has_a_kind() -> None:
    assert set(FORGERIES) == set(ForgeryKind)
    assert FORGERIES[ForgeryKind.COIN].crime is CrimeKind.COUNTERFEITING
    assert FORGERIES[ForgeryKind.LINEAGE].crime is CrimeKind.FORGED_LINE
    assert {CrimeKind.COUNTERFEITING, CrimeKind.FORGED_LINE} <= FORGERY_CRIMES


async def test_false_coin_costs_its_currency_trust(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    realm = await realm_of(session, world, town, treasury=500)
    forger = await mortal(session, "Forger", world, town.id)
    currency = CurrencyRow(issuer_entity_id=realm.id, name="crowns", purity=90, supply=100, trust=80, minted_epoch=1)
    session.add(currency)
    await session.flush()
    row = await forge_work(await context(session), realm.id, forger.id, ForgeryKind.COIN)
    assert row.kind is ForgeryKind.COIN and currency.trust < 80


async def test_a_forged_lineage_presses_a_claim_that_fails_when_exposed(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world, "Ashby")
    realm = await realm_of(session, world, town, treasury=500)
    forger = await mortal(session, "Claimant", world, town.id)
    title = await entity(session, "Seat of Ashby", EntityType.TITLE, TitleStats(), world_id=world.world.id, location_id=None)
    title.affiliated_entity_id = realm.id
    await session.flush()
    ctx = await context(session)
    row = await forge_work(ctx, title.id, forger.id, ForgeryKind.LINEAGE)
    claim = await session.get(ClaimRow, row.claim_id)
    assert claim is not None and claim.basis is ClaimBasis.INHERITANCE and claim.ended_epoch is None
    await expose(ctx, row, None)
    assert claim.ended_epoch == ctx.epoch
    assert "arts.exposed" in set(await session.scalars(select(IncidentRow.kind)))
