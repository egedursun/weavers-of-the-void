from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SchemeRow, SecretRow
from aerona.db.tables.polity import ClaimRow, OfficeRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import IntrigueSecret, PlotKind
from aerona.domain.enums.mind import TraitKind, TraitSource
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import ItemStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.intrigue.schemes import STRIKES, begin_scheme, choose_kind, owned_relic, realm_of, strike
from aerona.engine.mind.book import add_trait
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, context, make, mortal, people, settlement, son


async def plot(ctx: TickContext, owner: EntityRow, kind: PlotKind, target: EntityRow) -> SchemeRow:
    scheme = await begin_scheme(ctx, owner, kind, target)
    assert scheme is not None
    return scheme


async def pair(realm: Realm) -> tuple[TickContext, EntityRow, EntityRow, EntityRow]:
    ctx = context(realm.session)
    town = await settlement(realm, "Hollin")
    plotter = await mortal(realm, "Sela", location_id=town.id)
    rival = await mortal(realm, "Tor", location_id=town.id)
    return ctx, town, plotter, rival


async def throne(realm: Realm, holder: EntityRow) -> EntityRow:
    polity = await make(realm.session, "Kingdom of Hollin", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=holder.id, powers=[], since_epoch=1))
    await realm.session.flush()
    return polity


async def test_a_struck_rival_dies_vanishes_or_falls_in_love(realm: Realm) -> None:
    ctx, _, plotter, rival = await pair(realm)
    assert await strike(ctx, await plot(ctx, plotter, PlotKind.SWAY, rival), plotter, None) == "it found no target"
    assert "came to like" in await STRIKES[PlotKind.SWAY](ctx, await plot(ctx, plotter, PlotKind.SWAY, rival), plotter, rival)
    assert "secret love affair" in await STRIKES[PlotKind.SEDUCE](ctx, await plot(ctx, plotter, PlotKind.SEDUCE, rival), plotter, rival)
    affair = await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == rival.id, SecretRow.kind == IntrigueSecret.AFFAIR))
    assert affair is not None
    assert "eloped" in await STRIKES[PlotKind.ELOPE](ctx, await plot(ctx, plotter, PlotKind.ELOPE, rival), plotter, rival)
    victim = await mortal(realm, "Ivo")
    assert "taken captive" in await STRIKES[PlotKind.ABDUCT](ctx, await plot(ctx, plotter, PlotKind.ABDUCT, victim), plotter, victim)
    assert await realm.session.scalar(select(CaptiveRow).where(CaptiveRow.captive_entity_id == victim.id)) is not None
    doomed = await mortal(realm, "Rask")
    assert "found dead" in await STRIKES[PlotKind.MURDER](ctx, await plot(ctx, plotter, PlotKind.MURDER, doomed), plotter, doomed)
    assert doomed.status is EntityStatus.DEAD


async def test_thrones_are_claimed_and_seized(realm: Realm) -> None:
    ctx, _, plotter, rival = await pair(realm)
    assert (
        await STRIKES[PlotKind.FABRICATE_CLAIM](ctx, await plot(ctx, plotter, PlotKind.FABRICATE_CLAIM, rival), plotter, rival)
        == "there was no throne to claim"
    )
    assert await STRIKES[PlotKind.COUP](ctx, await plot(ctx, plotter, PlotKind.COUP, rival), plotter, rival) == "the throne could not be seized"
    polity = await throne(realm, rival)
    assert await realm_of(ctx, rival.id) == polity.id
    assert "forged claim" in await STRIKES[PlotKind.FABRICATE_CLAIM](ctx, await plot(ctx, plotter, PlotKind.FABRICATE_CLAIM, rival), plotter, rival)
    assert await realm.session.scalar(select(ClaimRow).where(ClaimRow.claimant_entity_id == plotter.id)) is not None
    assert "seized the throne" in await STRIKES[PlotKind.COUP](ctx, await plot(ctx, plotter, PlotKind.COUP, rival), plotter, rival)
    office = await realm.session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == polity.id))
    assert office is not None and office.holder_entity_id == plotter.id


async def test_relics_are_stolen_faiths_spread_and_weddings_spoiled(realm: Realm) -> None:
    ctx, _, plotter, rival = await pair(realm)
    assert await owned_relic(ctx, rival.id) is None
    assert await STRIKES[PlotKind.STEAL_RELIC](ctx, await plot(ctx, plotter, PlotKind.STEAL_RELIC, rival), plotter, rival) == "there was nothing worth stealing"
    relic = await make(realm.session, "The Pale Cup", EntityType.ITEM, ItemStats(), world_id=realm.world.id)
    await connect(realm.session, rival.id, relic.id, BondKind.OWNS, 1)
    assert "stolen" in await STRIKES[PlotKind.STEAL_RELIC](ctx, await plot(ctx, plotter, PlotKind.STEAL_RELIC, rival), plotter, rival)
    owner = await realm.session.scalar(
        select(BondRow.source_node_id).where(BondRow.target_node_id == relic.id, BondRow.kind == BondKind.OWNS, BondRow.state == "active")
    )
    assert owner == plotter.id
    assert (
        await STRIKES[PlotKind.CONVERT_SECRETLY](ctx, await plot(ctx, plotter, PlotKind.CONVERT_SECRETLY, rival), plotter, rival)
        == "there was no faith to share"
    )
    god = await son(realm.session, "Vael", realm.world.id)
    await connect(realm.session, plotter.id, god.id, BondKind.WORSHIPS, 1)
    assert "hidden faith" in await STRIKES[PlotKind.CONVERT_SECRETLY](ctx, await plot(ctx, plotter, PlotKind.CONVERT_SECRETLY, rival), plotter, rival)
    assert (
        await STRIKES[PlotKind.SABOTAGE_WEDDING](ctx, await plot(ctx, plotter, PlotKind.SABOTAGE_WEDDING, rival), plotter, rival)
        == "there was no wedding to spoil"
    )
    beloved = await mortal(realm, "Mira")
    await connect(realm.session, rival.id, beloved.id, BondKind.BETROTHED_TO, 1)
    assert "fell apart" in await STRIKES[PlotKind.SABOTAGE_WEDDING](ctx, await plot(ctx, plotter, PlotKind.SABOTAGE_WEDDING, rival), plotter, rival)


async def test_prisoners_are_freed_wells_poisoned_and_names_sought(realm: Realm) -> None:
    ctx, town, plotter, rival = await pair(realm)
    assert (
        await STRIKES[PlotKind.FREE_PRISONER](ctx, await plot(ctx, plotter, PlotKind.FREE_PRISONER, rival), plotter, rival) == "there was no prisoner to free"
    )
    realm.session.add(CaptiveRow(captive_entity_id=rival.id, captor_entity_id=town.id, status=CaptiveStatus.HELD, taken_epoch=1, locked=[]))
    await realm.session.flush()
    assert "freed" in await STRIKES[PlotKind.FREE_PRISONER](ctx, await plot(ctx, plotter, PlotKind.FREE_PRISONER, rival), plotter, rival)
    folk = await people(realm, "Reed Folk", population=1000)
    assert "poisoned" in await STRIKES[PlotKind.POISON_WELL](ctx, await plot(ctx, plotter, PlotKind.POISON_WELL, folk), plotter, folk)
    assert (stat(folk, "population") or 0) < 1000
    assert await STRIKES[PlotKind.POISON_WELL](ctx, await plot(ctx, plotter, PlotKind.POISON_WELL, rival), plotter, rival) == "there was no well to poison"
    assert "no true name" in await STRIKES[PlotKind.LEARN_TRUE_NAME](ctx, await plot(ctx, plotter, PlotKind.LEARN_TRUE_NAME, rival), plotter, rival)
    assert "blamed" in await STRIKES[PlotKind.FRAME](ctx, await plot(ctx, plotter, PlotKind.FRAME, rival), plotter, rival)
    assert await STRIKES[PlotKind.FORGE_LETTER](ctx, await plot(ctx, plotter, PlotKind.FORGE_LETTER, rival), plotter, rival) == "there was no one to deceive"
    assert "blight" in await STRIKES[PlotKind.ECOSABOTAGE](ctx, await plot(ctx, plotter, PlotKind.ECOSABOTAGE, rival), plotter, rival)


async def test_a_plotter_picks_its_scheme_by_its_nature(realm: Realm) -> None:
    ctx, _, plotter, rival = await pair(realm)
    assert await choose_kind(ctx, plotter, rival) in {PlotKind.SWAY, PlotKind.FABRICATE_HOOK}
    await add_trait(realm.session, plotter.id, TraitKind.DECEITFUL, TraitSource.BIRTH, 1)
    assert await choose_kind(ctx, plotter, rival) is PlotKind.FRAME
    await throne(realm, rival)
    await add_trait(realm.session, plotter.id, TraitKind.AMBITIOUS, TraitSource.BIRTH, 1)
    assert await choose_kind(ctx, plotter, rival) is PlotKind.COUP
    await add_trait(realm.session, plotter.id, TraitKind.CRUEL, TraitSource.BIRTH, 1)
    assert await choose_kind(ctx, plotter, rival) is PlotKind.MURDER
