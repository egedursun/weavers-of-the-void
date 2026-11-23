from sqlalchemy import select

from aerona.catalog.gatherings import ROOMS
from aerona.catalog.kinds.resolves import RESOLVES
from aerona.catalog.life.sites import DIG_RISKS, FEATURES, FIND_ANOMALIES, ROOM_CHALLENGES
from aerona.catalog.operations import AFFLICTIONS, AIRLESS, GROUNDS, QUIRK_ORIGINS, ROLES, VIRTUES
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.operations import ExpeditionMemberRow, ExpeditionRow
from aerona.db.tables.sites import BattlefieldFeatureRow
from aerona.domain.enums.discovery import AnomalyKind
from aerona.domain.enums.operations import ExpeditionEvent, ExpeditionGround, ExpeditionRole, QuirkKind, ResolveKind
from aerona.domain.enums.site import BattlefieldFeature, ExcavationFind, ExcavationRisk, SiteChallenge, SiteRoomKind
from aerona.engine.operations.expeditions import Party, danger_of, legs_for
from aerona.engine.sites.accounts import SITES_FIXUP, mark_ordnance
from tests.engine.society.factories import Realm, context


def party(ground: ExpeditionGround, role: ExpeditionRole, resolve: ResolveKind = ResolveKind.STEADY) -> Party:
    row = ExpeditionRow(id=1, name="Test", ground=ground, danger=60, darkness=0, tools=0, legs_done=0, locked=[])
    member = ExpeditionMemberRow(id=1, expedition_id=1, mortal_entity_id=1, role=role, resolve=resolve, fallen=False, departed=False, locked=[])
    return Party(row, None, [member], {}, {})


def test_roles_grounds_resolves_and_quirks_are_whole() -> None:
    assert len(ExpeditionRole) == 10 and set(ROLES) == set(ExpeditionRole)
    assert len(ExpeditionGround) == 7 and {ExpeditionGround.UNDER_WATER, ExpeditionGround.SPACE} == AIRLESS
    assert len(ResolveKind) == 12 and set(RESOLVES) == set(ResolveKind) and AFFLICTIONS | VIRTUES | {ResolveKind.STEADY} == set(ResolveKind)
    assert len(QuirkKind) == 16 and {QuirkKind.LUCKY, QuirkKind.SWIMMER} <= {quirk for pair in QUIRK_ORIGINS.values() for quirk in pair}
    assert {ExpeditionEvent.DISCOVERY, ExpeditionEvent.QUARREL} <= set(QUIRK_ORIGINS)
    assert all(GROUNDS[ground].label for ground in ExpeditionGround)


async def test_each_ground_has_its_legs_and_warders_and_engineers_cut_danger(realm: Realm) -> None:
    ctx = context(realm.session)
    assert all(legs_for(ctx, ground) >= 1 for ground in ExpeditionGround)
    plain = danger_of(ctx, party(ExpeditionGround.UNDERWORLD, ExpeditionRole.PORTER))
    assert danger_of(ctx, party(ExpeditionGround.UNDERWORLD, ExpeditionRole.WARDER)) < plain
    assert danger_of(ctx, party(ExpeditionGround.UNDERWORLD, ExpeditionRole.ENGINEER)) < plain
    assert danger_of(ctx, party(ExpeditionGround.UNDERWORLD, ExpeditionRole.PORTER, ResolveKind.IRRATIONAL)) > plain


def test_site_values_are_whole() -> None:
    assert len(SiteRoomKind) == 17 and set(ROOMS) == set(SiteRoomKind)
    assert len(SiteChallenge) == 7 and not ROOM_CHALLENGES[SiteChallenge.SEAL].harms and not ROOM_CHALLENGES[SiteChallenge.MAZE].harms
    assert len(ExcavationRisk) == 7 and {risk for risk, spec in DIG_RISKS.items() if spec.rule} == {
        ExcavationRisk.FLOODING,
        ExcavationRisk.GAS,
        ExcavationRisk.DISEASE,
    }
    assert len(ExcavationFind) == 9 and FIND_ANOMALIES[ExcavationFind.RECORDS] is AnomalyKind.CONTRARY_RECORD
    assert len(BattlefieldFeature) == 5 and not FEATURES[BattlefieldFeature.ORDNANCE].decays


async def test_battlefields_over_war_remnants_gain_ordnance_once(realm: Realm) -> None:
    remnant = WarRemnantRow(region_entity_id=realm.region.id, density=40, cleared=10, created_epoch=1, locked=[])
    realm.session.add(remnant)
    realm.session.add(BattlefieldFeatureRow(place_entity_id=realm.region.id, feature=BattlefieldFeature.MASS_GRAVE, strength=30, epoch=1, locked=[]))
    await realm.session.flush()
    ctx = context(realm.session)
    assert await mark_ordnance(ctx) == 1
    assert await mark_ordnance(ctx) == 0
    ordnance = list(await realm.session.scalars(select(BattlefieldFeatureRow).where(BattlefieldFeatureRow.feature == BattlefieldFeature.ORDNANCE)))
    assert len(ordnance) == 1 and ordnance[0].remnant_id == remnant.id
    assert await realm.session.get(AppliedFixupRow, SITES_FIXUP) is not None
