from aerona.agents.context.society import sickness_lines
from aerona.agents.context.statecraft import statecraft_lines
from aerona.agents.context.wilds import nature_lines
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.statecraft import CrisisDemand
from aerona.domain.models.entity_stats import BeastStats, SpeciesStats
from aerona.engine.ecology.beasts import profile_beast
from tests.engine.society.factories import Realm, context, make, mortal, settlement
from tests.engine.society.test_disease_depth import forge
from tests.engine.statecraft.crowns import crown


async def test_a_raging_sickness_is_named_with_its_traits(realm: Realm) -> None:
    town = await settlement(realm, "Ashby")
    disease = await forge(realm)
    outbreak = OutbreakRow(disease_entity_id=disease.id, region_entity_id=realm.region.id, path=SpreadPath.ORIGIN, severity=40, started_epoch=1)
    outbreak.status = OutbreakStatus.ACTIVE
    realm.session.add(outbreak)
    await realm.session.flush()
    lines = await sickness_lines(realm.session, town, realm.region.id)
    assert any(line.startswith(f"{disease.name} (raging") for line in lines)
    assert await sickness_lines(realm.session, town, None) == []


async def test_a_ruler_sees_the_crises_its_realm_is_caught_in(realm: Realm) -> None:
    polity, _ = await crown(realm, "Velmar")
    rival, _ = await crown(realm, "Reed Throne")
    ruler = await mortal(realm, "Queen Otta")
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[], locked=[]))
    realm.session.add(
        CrisisRow(demander_entity_id=rival.id, target_entity_id=polity.id, demand=next(iter(CrisisDemand)), escalation=2, opened_epoch=1, locked=[])
    )
    await realm.session.flush()
    lines = await statecraft_lines(realm.session, ruler)
    assert any(line.startswith("crisis #") and f"Reed Throne demands that #{polity.id} Velmar" in line and "at step 2" in line for line in lines)
    assert await statecraft_lines(realm.session, await mortal(realm, "Nobody")) == []


async def test_a_beast_is_described_by_its_own_profile(realm: Realm) -> None:
    ctx = context(realm.session)
    species = await make(realm.session, "Ridge Cat", EntityType.SPECIES, SpeciesStats(danger=60), world_id=realm.world.id)
    beast = await make(realm.session, "The Ridge Cat", EntityType.BEAST, BeastStats(danger=80), world_id=realm.world.id)
    assert await nature_lines(realm.session, beast) == []
    await profile_beast(ctx, beast, species)
    lines = await nature_lines(realm.session, beast)
    assert lines and lines[0].startswith("beast: ") and "endurance" in lines[0]
