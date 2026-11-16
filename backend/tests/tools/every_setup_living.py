from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import GeneBankRow, GeneBankSampleRow, LivingLineRow, LivingLineTraitRow, SymbiontRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.renown import ReputationRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.living import CultivationMethod, HostPlacement, HostRelation, LineTrait
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.models.entity_stats import DiseaseStats
from tests.tools.every_setup import second_mortal, wealthy
from tests.tools.factories import Realm, make_entity

EPOCH = 1
CRAFTS = (SkillKind.SCIENCE, SkillKind.MEDICINE, SkillKind.BEAST_HANDLING, SkillKind.FORAGING, SkillKind.SPELLCRAFT)


async def skilled(session: AsyncSession, holder_id: int) -> None:
    for skill in CRAFTS:
        session.add(
            SkillRow(
                holder_node_id=holder_id,
                skill=skill,
                subject_node_id=None,
                level=80,
                peak=80,
                xp=0,
                last_used_epoch=EPOCH,
                source=SkillSource.PRACTICE,
            )
        )
    session.add(HolderTechniqueRow(holder_entity_id=holder_id, technique=Technique.GENETIC_ENGINEERING, since_epoch=EPOCH))
    await session.flush()


async def held_line(session: AsyncSession, owner_id: int, species_id: int | None, *traits: tuple[LineTrait, int]) -> LivingLineRow:
    line = LivingLineRow(
        name="the long-legged line",
        method=CultivationMethod.SELECTIVE_BREEDING,
        stability=70,
        owner_node_id=owner_id,
        maker_node_id=owner_id,
        species_entity_id=species_id,
        founded_epoch=EPOCH,
        locked=[],
    )
    session.add(line)
    await session.flush()
    for trait, strength in traits:
        session.add(LivingLineTraitRow(line_id=line.id, trait=trait, strength=strength, side_effect=False, locked=[]))
    await session.flush()
    return line


async def breeder(session: AsyncSession, realm: Realm) -> dict[str, int]:
    await skilled(session, realm.mortal_id)
    return {}


async def bred_line(session: AsyncSession, realm: Realm) -> dict[str, int]:
    await skilled(session, realm.mortal_id)
    line = await held_line(session, realm.mortal_id, realm.species_id, (LineTrait.NERVOUS_SYSTEM, 40), (LineTrait.POTENCY, 50))
    return {"line": line.id}


async def bank_held(session: AsyncSession, realm: Realm) -> dict[str, int]:
    await skilled(session, realm.mortal_id)
    works = await make_entity(session, "the seed vault", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    session.add(GeneBankRow(structure_entity_id=works.id, holder_node_id=realm.mortal_id, upkeep=2, unpaid_epochs=0, locked=[]))
    await session.flush()
    sample = GeneBankSampleRow(bank_entity_id=works.id, organism_node_id=realm.species_id, quality=80, taken_epoch=EPOCH, locked=[])
    session.add(sample)
    await session.flush()
    return {"bank": works.id, "sample": sample.id}


async def hosted(session: AsyncSession, realm: Realm) -> dict[str, int]:
    line = await held_line(session, realm.mortal_id, realm.species_id)
    row = SymbiontRow(
        host_node_id=realm.mortal_id,
        line_id=line.id,
        placement=HostPlacement.SKIN,
        relation=HostRelation.MUTUAL,
        strength=30,
        since_epoch=EPOCH,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return {"symbiont": row.id}


async def sickness_and_line(session: AsyncSession, realm: Realm) -> dict[str, int]:
    found = await bred_line(session, realm)
    stats = DiseaseStats(virulence=30, lethality=20, infected=0, dead=0)
    disease = await make_entity(session, "the grey cough", EntityType.DISEASE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=stats)
    return {**found, "disease": disease.id}


async def line_of_another(session: AsyncSession, realm: Realm) -> dict[str, int]:
    other = (await second_mortal(session, realm))["mortal"]
    line = await held_line(session, other, realm.species_id)
    return {"line": line.id}


async def son_line(session: AsyncSession, realm: Realm) -> dict[str, int]:
    line = await held_line(session, realm.mortal_id, realm.species_id)
    return {"line": line.id}


async def founder(session: AsyncSession, realm: Realm) -> dict[str, int]:
    await wealthy(session, realm)
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    session.add(ReputationRow(subject_node_id=me.id, community_node_id=realm.settlement_id, axis=ReputationAxis.HONOUR, value=50, heard_epoch=0, locked=[]))
    await session.flush()
    return {}
