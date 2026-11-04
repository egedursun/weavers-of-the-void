from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ArtworkProfileRow, LegendProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ArtMedium, LegendArchetype
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.models.entity_stats import ArtworkStats, EventStats, HouseStats, LegendStats
from aerona.engine.lore import legends
from aerona.engine.lore.backfill import TYPED_KINDS_FIXUP, backfill_typed_kinds
from aerona.engine.lore.display_bonds import derived_bonds
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, settlement


async def legend(realm: Realm, name: str, spread: int = 20) -> object:
    return await make(realm.session, name, EntityType.LEGEND, LegendStats(spread=spread), world_id=realm.world.id)


async def incident_of(session: AsyncSession, node_id: int, epoch: int) -> IncidentRow:
    row = IncidentRow(kind="war.battle", epoch=epoch, magnitude=40, note="the battle")
    session.add(row)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=row.id, node_id=node_id, role=IncidentRole.ACTOR, position=0))
    await session.flush()
    return row


async def test_the_archetype_comes_from_the_typed_event_it_tells_not_from_its_name(realm: Realm) -> None:
    session = realm.session
    battle = await make(session, "Red Field", EntityType.EVENT, EventStats(severity=60), world_id=realm.world.id, engine_kind=EngineKind.BATTLE)
    incident = await incident_of(session, battle.id, 2)
    tale = await legend(realm, "The Great Flood of the Throne")
    await link(session, tale.id, battle.id, BondKind.TELLS_OF)
    row = await legends.profile_of(context(session, epoch=3), tale)
    assert row.archetype is LegendArchetype.HERO_QUEST
    assert row.source_incident_id == incident.id
    assert row.credence == Rules().belief.credence_base + 20 * Rules().belief.spread_credence_pct // 100


async def test_distortion_is_measured_from_the_true_incident(realm: Realm) -> None:
    session = realm.session
    battle = await make(session, "Red Field", EntityType.EVENT, EventStats(severity=60), world_id=realm.world.id, engine_kind=EngineKind.BATTLE)
    await incident_of(session, battle.id, 1)
    home = await settlement(realm, "Ashford")
    tale = await legend(realm, "A Song of the Field")
    await link(session, tale.id, battle.id, BondKind.TELLS_OF)
    await link(session, home.id, tale.id, BondKind.CELEBRATES)
    ctx = context(session, epoch=11)
    row = await legends.profile_of(ctx, tale)
    await legends.tell(ctx, tale, row)
    assert row.distortion == 10 * Rules().belief.distortion_rate


async def test_bards_tell_and_a_portraying_work_fixes_the_tale(realm: Realm) -> None:
    session = realm.session
    home = await settlement(realm, "Ashford")
    bard = await mortal(realm, "Ilse", location_id=home.id)
    session.add(SkillRow(holder_node_id=bard.id, skill=SkillKind.ORATORY, level=70, peak=70, xp=0, last_used_epoch=1, source=next(iter(SkillSource))))
    tale = await legend(realm, "The Lost Garden")
    await link(session, home.id, tale.id, BondKind.CELEBRATES)
    work = await make(session, "The Garden Fresco", EntityType.ARTWORK, ArtworkStats(renown=40, influence=30), world_id=realm.world.id)
    session.add(ArtworkProfileRow(artwork_entity_id=work.id, medium=ArtMedium.FRESCO, subject_node_id=tale.id, message={}, translations=[], locked=[]))
    await session.flush()
    ctx = context(session, epoch=4)
    row = await legends.profile_of(ctx, tale)
    before = row.distortion
    await legends.tell(ctx, tale, row)
    assert bard.id in row.tellers
    assert row.fixed_in_entity_id == work.id
    assert row.distortion == before
    kinds = {bond.kind for bond in await derived_bonds(session, tale.id)}
    assert kinds >= {BondKind.TELLS, BondKind.FIXED_IN}


async def test_the_returning_king_strengthens_only_the_claim_of_his_line(realm: Realm) -> None:
    session = realm.session
    house = await make(session, "House Aren", EntityType.HOUSE, HouseStats(), world_id=realm.world.id)
    other = await make(session, "House Vel", EntityType.HOUSE, HouseStats(), world_id=realm.world.id)
    heir = await mortal(realm, "Aren the Younger")
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=heir.id, by_marriage=False))
    town = await settlement(realm, "Crown Town")
    matching = ClaimRow(claimant_entity_id=heir.id, house_entity_id=house.id, polity_entity_id=town.id, strength=40, basis=next(iter(ClaimBasis)))
    stranger = ClaimRow(claimant_entity_id=other.id, house_entity_id=other.id, polity_entity_id=town.id, strength=60, basis=next(iter(ClaimBasis)))
    session.add_all([matching, stranger])
    tale = await legend(realm, "The King Under the Hill")
    await link(session, tale.id, heir.id, BondKind.TELLS_OF)
    await session.flush()
    ctx = context(session, epoch=4)
    row = await legends.profile_of(ctx, tale, LegendArchetype.RETURN_OF_THE_KING)
    row.credence = 100
    assert await legends.consequences(ctx, row) is not None
    assert matching.strength == 40 + Rules().belief.return_king_claim
    assert stranger.strength == 60
    assert await legends.foretold_return(ctx, heir) == {legends.FORETOLD: Rules().belief.return_king_usurper}


async def test_the_typed_backfill_reads_old_names_once_and_never_again(realm: Realm) -> None:
    session = realm.session
    tale = await legend(realm, "The Deluge of Old", spread=40)
    ctx = context(session, epoch=4)
    assert await backfill_typed_kinds(ctx) > 0
    row = await session.get(LegendProfileRow, tale.id)
    assert row is not None and row.archetype is LegendArchetype.FLOOD
    assert await session.get(AppliedFixupRow, TYPED_KINDS_FIXUP) is not None
    assert await backfill_typed_kinds(ctx) == 0
