from sqlalchemy import select

from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow, MovementProfileRow, MovementSupportRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import EstatePrivilege, FactionKind, FactionRank, MovementCause
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.factions.estates import EstateTally, exempt_share, grant, immune, tend_estates
from aerona.engine.factions.guilds import GuildTally, rank_members
from aerona.engine.factions.movements import MovementTally, tend_movements
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned


async def realm_with(realm: Realm, town: EntityRow, ruler: EntityRow, rule: DecisionRule = DecisionRule.AUTOCRATIC) -> EntityRow:
    polity = await make(realm.session, "Kingdom of Ash Vale", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.CHIEFDOM,
            decision_rule=rule,
            capital_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[]))
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await realm.session.flush()
    return polity


async def test_classes_gather_as_estates_and_privileges_spare_them_taxes_and_courts(realm: Realm) -> None:
    ctx = context(realm.session, tuned(estates={"found_share": 0, "found_pct": 100}))
    town = await settlement(realm, "Marrow")
    ruler = await mortal(realm, "Nell", location_id=town.id)
    polity = await realm_with(realm, town, ruler)
    tally = EstateTally()
    await tend_estates(ctx, tally)
    assert tally.founded >= 1
    nobles = await realm.session.scalar(
        select(EstateProfileRow).where(EstateProfileRow.polity_entity_id == polity.id, EstateProfileRow.social_class == SocialClass.NOBLE)
    )
    assert nobles is not None
    profile = await realm.session.get(FactionProfileRow, nobles.faction_entity_id)
    assert profile is not None and profile.kind is FactionKind.ESTATE and str(polity.id) in profile.influence_over
    assert await grant(ctx, nobles, EstatePrivilege.TAX_EXEMPTION)
    assert not await grant(ctx, nobles, EstatePrivilege.JUDICIAL_IMMUNITY)
    realm.session.add(HolderTechniqueRow(holder_entity_id=polity.id, technique=Technique.CODIFIED_LAW, since_epoch=1, secret=False))
    await realm.session.flush()
    assert await grant(ctx, nobles, EstatePrivilege.JUDICIAL_IMMUNITY)
    assert await realm.session.get(EstatePrivilegeRow, (nobles.faction_entity_id, EstatePrivilege.TAX_EXEMPTION)) is not None
    assert await exempt_share(ctx, town.id) >= 0
    lord = await mortal(realm, "Orrin", location_id=town.id)
    lord.social_class = SocialClass.NOBLE
    await realm.session.flush()
    assert await immune(ctx, lord)


async def test_a_pressed_cause_gathers_a_movement_that_becomes_a_party(realm: Realm) -> None:
    ctx = context(realm.session, tuned(movements={"found_at": 0, "found_pct": 100, "party_at": 0, "drift_pct": 100}))
    town = await settlement(realm, "Pell")
    ruler = await mortal(realm, "Quin", location_id=town.id)
    polity = await realm_with(realm, town, ruler, DecisionRule.COUNCIL)
    tally = MovementTally()
    await tend_movements(ctx, tally)
    rows = list(await realm.session.scalars(select(MovementProfileRow).where(MovementProfileRow.polity_entity_id == polity.id)))
    assert rows and tally.founded == len(rows)
    assert all(row.is_party for row in rows) and tally.parties == len(rows)
    revival = next(row for row in rows if row.cause is MovementCause.REVIVAL)
    assert await realm.session.get(MovementSupportRow, (revival.faction_entity_id, town.id)) is not None


async def test_guild_members_rank_by_their_craft(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Rook")
    smith = await mortal(realm, "Sev", location_id=town.id)
    guild = await make(realm.session, "Smiths of Rook", EntityType.FACTION, FactionStats(), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.CRAFT_GUILD, home_entity_id=town.id, influence_over={}, locked=[]))
    realm.session.add(FactionMembershipRow(faction_entity_id=guild.id, mortal_entity_id=smith.id, rank=FactionRank.LEADER))
    await realm.session.flush()
    tally = GuildTally()
    await rank_members(ctx, guild, tally)
    member = await realm.session.get(FactionMembershipRow, (guild.id, smith.id))
    assert member is not None and member.rank is FactionRank.NOVICE and tally.promoted == 1
