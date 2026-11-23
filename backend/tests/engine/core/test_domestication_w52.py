from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domestication import STAGES
from aerona.catalog.evolution import STAGE_DOCILITY
from aerona.db.tables.evolution import SpeciesTraitRow
from aerona.domain.enums.ecology import DomesticationStage
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.engine.ecology.domestication import taming_ease
from aerona.engine.ecology.evolution import docility_of
from aerona.engine.ecology.living_ways import KEPT_BEFORE
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind

RULES = Rules()


def test_seven_stages_with_the_two_new_ones_between_wild_and_kept() -> None:
    order = list(DomesticationStage)
    assert len(STAGES) == len(order) == 7
    assert order.index(DomesticationStage.COMMENSAL) == order.index(DomesticationStage.WILD) + 1
    assert not STAGES[DomesticationStage.COMMENSAL].kept and not STAGES[DomesticationStage.FERAL].kept
    assert {stage for stage, spec in STAGES.items() if spec.kept} == KEPT_BEFORE
    assert STAGE_DOCILITY[DomesticationStage.WILD] < STAGE_DOCILITY[DomesticationStage.COMMENSAL] < STAGE_DOCILITY[DomesticationStage.BREED]


def test_living_beside_people_and_running_feral_each_change_how_fast_a_kind_is_tamed() -> None:
    assert taming_ease(RULES, DomesticationStage.COMMENSAL) == 1 + RULES.domestication_depth.commensal_tame_gain / 100
    assert taming_ease(RULES, DomesticationStage.FERAL) == 1 + RULES.domestication_depth.feral_retake_gain / 100
    slow = tuned_rules(domestication_depth={"commensal_tame_gain": 0, "feral_retake_gain": 0})
    assert taming_ease(slow, DomesticationStage.COMMENSAL) == taming_ease(slow, DomesticationStage.FERAL) == 1.0


async def test_docility_is_the_mean_of_a_kind_s_lands_and_neutral_where_unrecorded(session: AsyncSession, world: CoreWorld) -> None:
    first, second = world.regions[0], world.regions[1]
    tame = await kind(session, world, "Yard Goat", first, 40)
    bare = await kind(session, world, "Hill Goat", first, 40)
    for region, mean in ((first, 80), (second, 60)):
        session.add(
            SpeciesTraitRow(
                species_entity_id=tame.id, region_entity_id=region.id, trait=EvolvedTrait.DOCILITY, mean=mean, variance=10, updated_epoch=1, locked=[]
            )
        )
    await session.flush()
    assert await docility_of(session, tame.id) == 70
    assert await docility_of(session, bare.id) == 50
