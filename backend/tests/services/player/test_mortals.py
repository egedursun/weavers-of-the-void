import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.body import ConditionRow, InjuryRow, ProsthesisRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.mind import MemoryRow, SkillRow, TraitRow
from aerona.db.tables.mortal import MarriageRow, MortalEquipmentRow, MortalProfileRow
from aerona.domain.enums.body import BodyPart, ConditionKind, InjuryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import KindFamily, MemoryKind, NeedKind, SkillKind, TraitKind, ValueAxis
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.mortal import Ability, CrimeKind, EquipmentSlot, LifeStage, MarriageEnd, MortalSex, PunishmentKind
from aerona.domain.models.entity_stats import ItemStats, MortalStats
from aerona.engine.lore.items import profile_of
from aerona.engine.mortal.kin import spouses_of
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import body, mind, mortals, variants
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def _mortal(session: AsyncSession, world: PlayerWorld, name: str) -> int:
    row = await make_entity(
        session,
        name,
        EntityType.MORTAL,
        world_id=world.world.id,
        location_id=world.region.id,
        stats=MortalStats(hp=80, strength=50, agility=50, intellect=50, charisma=50, age=30, lifespan=70),
        mortal_role=MortalRole.COMMONER,
    )
    return row.id


async def _undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    names = label_names(changes, await node_names(session, changes))
    return (await UndoRun(session, epoch, changes, names).run()).conflicts


async def test_a_life_value_is_set_held_released_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Asha")
    outcome = await mortals.set_mortal(scope, mortals.SetMortal(mortal_id=mortal_id, field="stress", value=70))
    profile = await session.get(MortalProfileRow, mortal_id)
    assert profile is not None and profile.stress == 70 and "stress" in profile.locked
    await mortals.set_mortal(scope, mortals.SetMortal(mortal_id=mortal_id, field="life_stage", value="elder"))
    assert profile.life_stage is LifeStage.ELDER
    await mortals.release_mortal(scope, mortals.ReleaseMortal(mortal_id=mortal_id, field="stress"))
    assert "stress" not in profile.locked
    with pytest.raises(ValidationFailedError):
        await mortals.release_mortal(scope, mortals.ReleaseMortal(mortal_id=mortal_id, field="stress"))
    with pytest.raises(ValidationFailedError):
        await mortals.set_mortal(scope, mortals.SetMortal(mortal_id=mortal_id, field="stress", value=500))
    with pytest.raises(ValidationFailedError):
        await mortals.set_mortal(scope, mortals.SetMortal(mortal_id=mortal_id, field="name", value=1))
    assert await _undo(session, outcome.ledger_entry_id, world.cosmos.epoch) == []


async def test_an_ability_is_pinned_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Brin")
    await mortals.set_ability(scope, mortals.SetAbility(mortal_id=mortal_id, ability=Ability.WISDOM, value=90))
    pins = list(
        await session.scalars(select(ModifierRow.target_key).where(ModifierRow.target_node_id == mortal_id, ModifierRow.source_kind == ModifierSource.PIN))
    )
    assert pins == ["wisdom"]
    await mortals.release_ability(scope, mortals.ReleaseAbility(mortal_id=mortal_id, ability=Ability.WISDOM))
    with pytest.raises(ValidationFailedError):
        await mortals.release_ability(scope, mortals.ReleaseAbility(mortal_id=mortal_id, ability=Ability.WISDOM))
    await mortals.set_sex(scope, mortals.SetSex(mortal_id=mortal_id, sex=MortalSex.OTHER))


async def test_marriages_are_made_forced_ended_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await _mortal(session, world, "Cora")
    second = await _mortal(session, world, "Dain")
    await mortals.set_betrothal(scope, mortals.PairCommand(first_id=first, second_id=second))
    outcome = await mortals.force_marriage(scope, mortals.ForceMarriage(first_id=first, second_id=second))
    marriage_id = int((outcome.values or {})["marriage_id"])
    assert await spouses_of(session, first) == [second]
    grudges = list(await session.scalars(select(MemoryRow).where(MemoryRow.holder_node_id == first, MemoryRow.kind == MemoryKind.ILL_WILL)))
    assert grudges
    with pytest.raises(ValidationFailedError):
        await mortals.force_marriage(scope, mortals.ForceMarriage(first_id=first, second_id=second))
    await mortals.edit_marriage(scope, mortals.EditMarriage(marriage_id=marriage_id, start_epoch=0))
    await mortals.end_marriage_action(scope, mortals.EndMarriage(marriage_id=marriage_id, cause=MarriageEnd.DIVORCE))
    assert await spouses_of(session, first) == []
    await mortals.delete_marriage(scope, mortals.MarriageTarget(marriage_id=marriage_id))
    assert list(await session.scalars(select(MarriageRow))) == []


async def test_kin_bonds_are_made_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    parent = await _mortal(session, world, "Ena")
    child = await _mortal(session, world, "Fio")
    outcome = await mortals.add_kin_bond(scope, mortals.KinBond(source_id=parent, target_id=child, kind=BondKind.PARENT_OF.value))
    bond_id = int((outcome.values or {})["bond_id"])
    await mortals.remove_kin_bond(scope, mortals.KinBondTarget(bond_id=bond_id))
    with pytest.raises(ValidationFailedError):
        await mortals.add_kin_bond(scope, mortals.KinBond(source_id=parent, target_id=parent, kind=BondKind.SWORN_KIN.value))


async def test_gear_is_equipped_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Gar")
    sword = await make_entity(session, "Old Sword", EntityType.ITEM, world_id=world.world.id, stats=ItemStats(damage=40))
    ctx = await scope.context("test_gear")
    await profile_of(ctx, sword)
    await mortals.equip(scope, mortals.Equip(mortal_id=mortal_id, slot=EquipmentSlot.WIELDED_MAIN, item_id=sword.id))
    row = await session.get(MortalEquipmentRow, mortal_id)
    assert row is not None and row.wielded_main_id == sword.id and "wielded_main_id" in row.locked
    with pytest.raises(ValidationFailedError):
        await mortals.equip(scope, mortals.Equip(mortal_id=mortal_id, slot=EquipmentSlot.ARMOUR_HEAD, item_id=sword.id))
    await mortals.release_slot(scope, mortals.ReleaseSlot(mortal_id=mortal_id, slot=EquipmentSlot.WIELDED_MAIN))
    assert "wielded_main_id" not in row.locked


async def test_a_sentence_maims_and_a_pardon_lifts_exile(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Hob")
    await mortals.sentence_mortal(scope, mortals.Sentence(mortal_id=mortal_id, crime=CrimeKind.BLASPHEMY, punishment=PunishmentKind.TONGUE))
    rows = list(await session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == mortal_id)))
    assert any(row.part is BodyPart.TONGUE for row in rows)
    await mortals.sentence_mortal(scope, mortals.Sentence(mortal_id=mortal_id, crime=CrimeKind.THEFT, punishment=PunishmentKind.EXILE))
    await mortals.pardon(scope, mortals.Pardon(mortal_id=mortal_id, return_to_id=world.region.id))


async def test_body_controls_edit_conditions_prostheses_and_holds(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Ilse")
    added = await body.add_condition(scope, body.AddCondition(bearer_id=mortal_id, kind=ConditionKind.MELANCHOLY))
    condition_id = int((added.values or {})["condition_id"])
    await body.edit_condition(scope, body.EditCondition(condition_id=condition_id, severity=4))
    row = await session.get(ConditionRow, condition_id)
    assert row is not None and row.severity == 4
    maimed = await body.maim(scope, body.Maim(bearer_id=mortal_id, part="left_hand", kind=InjuryKind.SEVERED, severity=5))
    injury_id = int((maimed.values or {})["injury_id"])
    await body.edit_injury(scope, body.EditInjury(injury_id=injury_id, part=BodyPart.RIGHT_HAND))
    injury = await session.get(InjuryRow, injury_id)
    assert injury is not None and injury.part is BodyPart.RIGHT_HAND
    await body.hold_injuries(scope, body.HoldInjuries(bearer_id=mortal_id))
    await body.hold_injuries(scope, body.HoldInjuries(bearer_id=mortal_id, hold=False))


async def test_mind_levers_shape_values_traits_skills_memories_and_needs(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Jor")
    other = await _mortal(session, world, "Kai")
    await mind.set_values(scope, mind.SetValues(node_id=mortal_id, values={ValueAxis.MERCY: 60}))
    await mind.unlock_mind(scope, mind.LockMind(node_id=mortal_id, field="values"))
    await mind.lock_mind(scope, mind.LockMind(node_id=mortal_id, field="values"))
    await mind.give_trait(scope, mind.TraitCommand(node_id=mortal_id, trait=TraitKind.BRAVE))
    await mind.take_trait(scope, mind.TraitCommand(node_id=mortal_id, trait=TraitKind.BRAVE))
    await mind.give_skill(scope, mind.SetSkill(node_id=mortal_id, skill=SkillKind.LANGUAGES, level=40, subject_id=other))
    skill = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == mortal_id, SkillRow.skill == SkillKind.LANGUAGES))
    assert skill is not None and skill.subject_node_id == other
    await mind.edit_skill(scope, mind.EditSkill(skill_id=skill.id, xp=5, peak=60, clear_subject=True))
    assert skill.subject_node_id is None and skill.peak == 60
    await mind.forget_skill(scope, mind.SkillTarget(node_id=mortal_id, skill=SkillKind.LANGUAGES))
    planted = await mind.add_memory(scope, mind.AddMemory(holder_id=mortal_id, subject_id=other, kind=MemoryKind.SAVED_ME, magnitude=40))
    memory_id = int((planted.values or {})["memory_id"])
    await mind.edit_memory(scope, mind.EditMemory(memory_id=memory_id, magnitude=20))
    await mind.forget_memory(scope, mind.MemoryTarget(memory_id=memory_id))
    await mind.set_need(scope, mind.SetNeed(node_id=mortal_id, need=NeedKind.FAITH, value=10))
    await mind.set_role(scope, mind.SetRole(node_id=mortal_id, role=MortalRole.SCRIBE))


async def test_world_made_kinds_are_forged_given_and_unmade(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Lark")
    made = await variants.create_variant(
        scope, variants.CreateVariant(family=KindFamily.TRAIT, base=TraitKind.BRAVE.value, name="Lion-hearted", strength_pct=150)
    )
    variant_id = int((made.values or {})["variant_id"])
    with pytest.raises(ValidationFailedError):
        await variants.create_variant(scope, variants.CreateVariant(family=KindFamily.TRAIT, base="flying", name="Bad"))
    await mind.give_trait(scope, mind.TraitCommand(node_id=mortal_id, trait=TraitKind.BRAVE, variant_id=variant_id))
    held = await session.get(TraitRow, (mortal_id, TraitKind.BRAVE))
    assert held is not None and held.variant_id == variant_id
    await variants.edit_variant(scope, variants.EditVariant(variant_id=variant_id, strength_pct=180))
    await variants.release_variant(scope, variants.VariantField(variant_id=variant_id, field="strength_pct"))
    await variants.delete_variant(scope, variants.VariantTarget(variant_id=variant_id))
    await session.refresh(held)
    assert held.variant_id is None


async def test_a_prosthesis_of_a_world_material(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mortal_id = await _mortal(session, world, "Orla")
    material = WorldMaterialRow(
        world_id=world.world.id,
        origin=MaterialOrigin.GOD_REMAINS,
        name="Godbone",
        family=MaterialFamily.PRECIOUS,
        hardness=90,
        toughness=90,
        weight=20,
        edge=40,
        conductivity=10,
        sanctity=80,
        corruption=0,
        rarity=90,
        base_value=90,
        decay=0,
        created_epoch=1,
    )
    session.add(material)
    await session.flush()
    maimed = await body.maim(scope, body.Maim(bearer_id=mortal_id, part="left_hand", kind=InjuryKind.SEVERED, severity=5))
    injury_id = int((maimed.values or {})["injury_id"])
    fitted = await body.apply_prosthesis(scope, body.FitProsthesis(injury_id=injury_id, material=MaterialKind.WOOD, quality=80, world_material_id=material.id))
    prosthesis = await session.get(ProsthesisRow, int((fitted.values or {})["prosthesis_id"]))
    assert prosthesis is not None and prosthesis.world_material_id == material.id
    assert prosthesis.restored_pct > 0
