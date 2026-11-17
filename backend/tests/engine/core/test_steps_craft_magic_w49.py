import pytest

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.session import Database
from aerona.db.tables.culture import CastingRow, RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.powers import PowerRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.couplings import RiteComponent
from aerona.domain.enums.culture import BacklashKind, MagicSchool, MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import QualityTier
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction, StepOutcome
from aerona.domain.models.entity_stats import MortalStats, RiteStats
from aerona.engine.context import TickContext
from aerona.engine.couplings import control
from aerona.engine.lore.items import masterwork_steps
from aerona.engine.lore.rites import casting_steps
from aerona.engine.powers.phase import power_steps
from aerona.engine.powers.use import Outcome
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import checked_steps, record
from aerona.rules.registry import Rules
from aerona.tools.mortal.production import MadeItem, making_steps
from tests.engine.core.factories import entity
from tests.engine.integration.factories import RichCosmos, seed_rich_cosmos

DECLARED = {
    "power.used": {StepAction.USE_POWER, StepAction.BACKLASH},
    "magic.rite": {StepAction.INSCRIBE, StepAction.CAST, StepAction.BACKLASH},
    "magic.war_mages": {StepAction.INSCRIBE, StepAction.CAST, StepAction.BACKLASH},
    "magic.item_enchanted": {StepAction.ENCHANT},
    "arcana.enchantment_laid": {StepAction.ENCHANT},
    "living.line_blessed": {StepAction.BLESS},
    "tools.mortal.produced": {
        StepAction.GATHER,
        StepAction.WORK,
        StepAction.ASSEMBLE,
        StepAction.TEMPER,
        StepAction.ENCHANT,
        StepAction.FLAW,
        StepAction.FINISH_WORK,
    },
    "item.masterwork": {StepAction.WORK, StepAction.FINISH_WORK, StepAction.SIGN_WORK},
    "ecology.extinct": {StepAction.DIE_OUT},
    "ecology.extinct_hunted": {StepAction.DIE_OUT},
    "ecology.extinct_starved": {StepAction.DIE_OUT},
    "mortals.ghost": {StepAction.AGE},
    "galaxy.aged": {StepAction.AGE},
    "gathering.performance": {StepAction.PERFORM},
    "industry.energy_short": {StepAction.WORK},
}


@pytest.mark.parametrize("key", sorted(DECLARED))
def test_every_kind_declares_the_stages_its_process_records(key: str) -> None:
    assert DECLARED[key] <= INCIDENT_KINDS[key].steps


def test_the_energy_shortfall_is_told_in_energy() -> None:
    short = INCIDENT_KINDS["industry.energy_short"].fact("short")
    assert short is not None and short.unit is FactUnit.ENERGY


def holder(node_id: int) -> EntityRow:
    return EntityRow(id=node_id, name=f"Holder {node_id}", entity_type=EntityType.MORTAL)


def a_power() -> PowerRow:
    return PowerRow(id=11, holder_node_id=1, technique=next(iter(SpellTechnique)), form=next(iter(SpellForm)))


def test_a_steady_power_is_used_on_its_target_and_nothing_turns_back() -> None:
    steps = power_steps(a_power(), holder(1), holder(2), Outcome("eased", misfired=False, strained=False, resisted=False))
    assert [step.action for step in steps] == [StepAction.USE_POWER]
    used = steps[0]
    assert (used.actor, used.target, used.instrument_kind, used.outcome) == (1, 2, InstrumentKind.POWER, StepOutcome.SUCCESS)
    assert (used.record_table, used.record_key) == (PowerRow.__tablename__, "11")
    checked_steps(INCIDENT_KINDS["power.used"], steps)


def test_a_misfired_power_turns_back_on_its_holder() -> None:
    steps = power_steps(a_power(), holder(1), holder(2), Outcome("burned", misfired=True, strained=False, resisted=True))
    assert [step.action for step in steps] == [StepAction.USE_POWER, StepAction.BACKLASH]
    assert steps[0].outcome is StepOutcome.FAILURE
    assert (steps[1].target, steps[1].parent) == (1, 0)
    checked_steps(INCIDENT_KINDS["power.used"], steps)


def resources(*ids: int) -> list[EntityRow]:
    return [EntityRow(id=node_id, name=f"Seam {node_id}", entity_type=EntityType.RESOURCE) for node_id in ids]


def test_a_making_records_each_stage_the_maker_really_went_through() -> None:
    made = MadeItem(maker_id=1, item_id=9, resources=resources(4, 5), worked=60, quality=QualityTier.POOR)
    steps = making_steps(made, tempered=True, enchanted=12, flawed=7, abundance_loss=3)
    assert [step.action for step in steps] == [
        StepAction.GATHER,
        StepAction.GATHER,
        StepAction.WORK,
        StepAction.ASSEMBLE,
        StepAction.TEMPER,
        StepAction.ENCHANT,
        StepAction.FLAW,
        StepAction.FINISH_WORK,
    ]
    assert [step.target for step in steps[:2]] == [4, 5]
    assert steps[-1].outcome is StepOutcome.PARTIAL
    checked_steps(INCIDENT_KINDS["tools.mortal.produced"], steps)


def test_a_plain_making_from_one_seam_is_gathered_worked_and_finished() -> None:
    made = MadeItem(maker_id=1, item_id=9, resources=resources(4), worked=60, quality=QualityTier.FINE)
    steps = making_steps(made, tempered=False, enchanted=0, flawed=0, abundance_loss=3)
    assert [step.action for step in steps] == [StepAction.GATHER, StepAction.WORK, StepAction.FINISH_WORK]
    assert steps[-1].outcome is StepOutcome.SUCCESS


def test_a_masterwork_is_signed_only_by_a_known_smith() -> None:
    signed = masterwork_steps(3, 9, 70, 95)
    assert [step.action for step in signed] == [StepAction.WORK, StepAction.FINISH_WORK, StepAction.SIGN_WORK]
    assert signed[-1].actor == 3
    unsigned = masterwork_steps(None, 9, 70, 95)
    assert StepAction.SIGN_WORK not in [step.action for step in unsigned]
    checked_steps(INCIDENT_KINDS["item.masterwork"], signed)


async def rite(ctx: TickContext, cosmos: RichCosmos, name: str) -> int:
    made = await entity(ctx.session, name, EntityType.RITE, RiteStats(), world_id=cosmos.home.world.id)
    ctx.session.add(RiteProfileRow(rite_entity_id=made.id, school=next(iter(MagicSchool)), source=MagicSource.LEY, requirements={}, cost={}, locked=[]))
    await ctx.session.flush()
    return made.id


async def test_an_inscribed_rite_is_inscribed_before_it_is_cast_and_its_backlash_is_kept(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w49_rite_steps", Rules())
        rite_id = await rite(ctx, cosmos, "Graven Ward")
        await control.set_component(ctx, rite_id, RiteComponent.INSCRIBED, True)
        mage = await entity(
            ctx.session,
            "Orre",
            EntityType.MORTAL,
            MortalStats(hp=60, age=30, lifespan=70),
            world_id=cosmos.home.world.id,
            location_id=cosmos.home.regions[0].id,
        )
        casting = CastingRow(
            rite_entity_id=rite_id,
            caster_entity_id=mage.id,
            target_entity_id=None,
            epoch=ctx.epoch,
            succeeded=False,
            backlash=next(iter(BacklashKind)),
            effect="the rite turned on its caster",
        )
        ctx.session.add(casting)
        await ctx.session.flush()
        steps = await casting_steps(ctx, casting)
        assert [step.action for step in steps] == [StepAction.INSCRIBE, StepAction.CAST, StepAction.BACKLASH]
        assert steps[1].outcome is StepOutcome.FAILURE and steps[1].record_key == str(casting.id)
        assert (steps[2].parent, steps[2].instrument_kind, steps[2].instrument_node) == (1, InstrumentKind.RITE, rite_id)
        told = await record(
            ctx,
            "magic.rite",
            roles={IncidentRole.SUBJECT: [mage.id, rite_id]},
            facts={"rite": "Graven Ward", "effect": casting.effect},
            steps=steps,
        )
        assert told.incident_id > 0


async def test_a_rite_with_no_inscription_is_only_cast(database: Database) -> None:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        ctx = await manual_context(session, "w49_rite_plain", Rules())
        rite_id = await rite(ctx, cosmos, "Spoken Ward")
        await control.set_component(ctx, rite_id, RiteComponent.SPOKEN, True)
        casting = CastingRow(rite_entity_id=rite_id, caster_entity_id=None, target_entity_id=None, epoch=ctx.epoch, succeeded=True, effect="")
        ctx.session.add(casting)
        await ctx.session.flush()
        steps = await casting_steps(ctx, casting)
        assert [step.action for step in steps] == [StepAction.CAST]
        assert steps[0].outcome is StepOutcome.SUCCESS
