from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.folkways import CharmPower, DecisionBias, ImpuritySource, LuckReach, LuckSign, MishapKind, Nutrient, Purification
from aerona.domain.enums.mind import Profession
from aerona.engine.folkways import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000
NAME = 80


class HolderValues(Command):
    holder_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)


class NeedDraft(Command):
    people_id: int
    nutrient: Nutrient = Nutrient.PROTEIN
    weight: int = Field(default=50, ge=0, le=SPAN)


class Feed(Command):
    pass


class BiasDraft(Command):
    holder_id: int
    bias: DecisionBias = DecisionBias.OVERCONFIDENCE
    weight: int = Field(default=50, ge=0, le=SPAN)


class HolderTarget(Command):
    holder_id: int


class PurityDraft(Command):
    mortal_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)


class MortalTarget(Command):
    mortal_id: int


class SourceDraft(Command):
    people_id: int
    source: ImpuritySource = ImpuritySource.THE_DEAD
    weight: int = Field(default=50, ge=0, le=SPAN)
    lasts: int = Field(default=1, ge=1, le=MANY)


class MethodDraft(Command):
    people_id: int
    method: Purification = Purification.WASHING
    epochs: int = Field(default=1, ge=0, le=MANY)
    cost: int = Field(default=0, ge=0, le=MANY)
    success: int = Field(default=80, ge=0, le=SPAN)


class RankDraft(Command):
    people_id: int
    name: str = Field(min_length=1, max_length=NAME)
    standing: int = Field(default=50, ge=0, le=SPAN)
    professions: list[str] = Field(default_factory=list)


class RankProfession(Command):
    rank_id: int
    profession: Profession = Profession.FARMER
    member: bool = True


class MishapDraft(Command):
    town_id: int
    kind: MishapKind = MishapKind.BAD_LUCK
    victim_id: int | None = None
    cause_id: int | None = None


class BeliefDraft(Command):
    people_id: int
    sign: LuckSign = LuckSign.DAY
    reach: LuckReach = LuckReach.HARVEST
    lucky: bool = True
    name: str = Field(min_length=1, max_length=NAME)


class CharmDraft(Command):
    item_id: int
    power: CharmPower = CharmPower.PROTECTION
    strength: int = Field(default=50, ge=0, le=SPAN)


class AccusationDraft(Command):
    town_id: int
    accuser_id: int | None = None
    mishap_id: int | None = None


class HuntDraft(Command):
    town_id: int
    fervour: int = Field(default=60, ge=0, le=SPAN)


class DietTarget(Command):
    holder_id: int


class DietEdit(Edited):
    holder_id: int


class NutrientNeedTarget(Command):
    people_id: int
    nutrient: Nutrient


class NutrientNeedEdit(Edited):
    people_id: int
    nutrient: Nutrient


class NutritionScoreTarget(Command):
    holder_id: int


class NutritionScoreEdit(Edited):
    holder_id: int


class BiasWeightTarget(Command):
    holder_id: int
    bias: DecisionBias


class BiasWeightEdit(Edited):
    holder_id: int
    bias: DecisionBias


class PurityTarget(Command):
    mortal_id: int


class PurityEdit(Edited):
    mortal_id: int


class ImpuritySourceTarget(Command):
    people_id: int
    source: ImpuritySource


class ImpuritySourceEdit(Edited):
    people_id: int
    source: ImpuritySource


class PurificationTarget(Command):
    people_id: int
    method: Purification


class PurificationEdit(Edited):
    people_id: int
    method: Purification


class PurityRankTarget(Command):
    rank_id: int


class PurityRankEdit(Edited):
    rank_id: int


class MishapTarget(Command):
    mishap_id: int


class MishapEdit(Edited):
    mishap_id: int


class LuckBeliefTarget(Command):
    belief_id: int


class LuckBeliefEdit(Edited):
    belief_id: int


class CharmTarget(Command):
    item_id: int


class CharmEdit(Edited):
    item_id: int


class AccusationTarget(Command):
    accusation_id: int


class AccusationEdit(Edited):
    accusation_id: int


class WitchHuntTarget(Command):
    hunt_id: int


class WitchHuntEdit(Edited):
    hunt_id: int


@player_action("diet:set", ActionKind.EDIT_RECORD)
async def diet_set(scope: PlayerScope, command: HolderValues) -> Effect:
    await control.set_diet(await scope.context("diet_set"), command.holder_id, command.values)
    return Effect("The diet is set.", command.holder_id)


@player_action("nutrient_need:set", ActionKind.EDIT_RECORD)
async def nutrient_need_set(scope: PlayerScope, command: NeedDraft) -> Effect:
    await control.set_need(await scope.context("nutrient_need_set"), command.people_id, command.nutrient, command.weight)
    return Effect("The people's need is set.", command.people_id)


@player_action("nutrition_score:set", ActionKind.EDIT_RECORD)
async def nutrition_score_set(scope: PlayerScope, command: HolderValues) -> Effect:
    await control.set_score(await scope.context("nutrition_score_set"), command.holder_id, command.values)
    return Effect("The nutrition is set.", command.holder_id)


@player_action("nutrition:feed", ActionKind.EDIT_RECORD)
async def nutrition_feed(scope: PlayerScope, command: Feed) -> Effect:
    tally = await control.feed_now(await scope.context("nutrition_feed"))
    return Effect(f"Diets were read in {tally.diets} towns and {tally.scored} lives were fed.")


@player_action("bias_weight:set", ActionKind.EDIT_RECORD)
async def bias_weight_set(scope: PlayerScope, command: BiasDraft) -> Effect:
    await control.set_bias(await scope.context("bias_weight_set"), command.holder_id, command.bias, command.weight)
    return Effect("The bias is set.", command.holder_id)


@player_action("bias:read", ActionKind.EDIT_RECORD)
async def bias_read(scope: PlayerScope, command: HolderTarget) -> Effect:
    count = await control.read_biases(await scope.context("bias_read"), command.holder_id)
    return Effect(f"{count} biases were read from its character.", command.holder_id)


@player_action("purity:set", ActionKind.EDIT_RECORD)
async def purity_set(scope: PlayerScope, command: PurityDraft) -> Effect:
    await control.set_purity(await scope.context("purity_set"), command.mortal_id, command.values)
    return Effect("The purity is set.", command.mortal_id)


@player_action("purity:cleanse", ActionKind.EDIT_RECORD)
async def purity_cleanse(scope: PlayerScope, command: MortalTarget) -> Effect:
    await control.cleanse(await scope.context("purity_cleanse"), command.mortal_id)
    return Effect("The mortal is made pure.", command.mortal_id)


@player_action("impurity_source:set", ActionKind.EDIT_RECORD)
async def impurity_source_set(scope: PlayerScope, command: SourceDraft) -> Effect:
    await control.set_source(await scope.context("impurity_source_set"), command.people_id, command.source, command.weight, command.lasts)
    return Effect("The people count it impure.", command.people_id)


@player_action("purification:set", ActionKind.EDIT_RECORD)
async def purification_set(scope: PlayerScope, command: MethodDraft) -> Effect:
    values = {"epochs": command.epochs, "cost": command.cost, "success": command.success}
    await control.set_method(await scope.context("purification_set"), command.people_id, command.method, values)
    return Effect("The people purify so.", command.people_id)


@player_action("purity_rank:create", ActionKind.EDIT_RECORD)
async def purity_rank_create(scope: PlayerScope, command: RankDraft) -> Effect:
    row = await control.add_rank(await scope.context("purity_rank_create"), command.people_id, command.name, command.standing, command.professions)
    return Effect("The rank is set among the people.", command.people_id, values={"rank_id": row.id})


@player_action("purity_rank:profession", ActionKind.EDIT_RECORD)
async def purity_rank_profession(scope: PlayerScope, command: RankProfession) -> Effect:
    row = await control.rank_profession(await scope.context("purity_rank_profession"), command.rank_id, command.profession, member=command.member)
    return Effect("The rank takes up that work." if command.member else "The rank gives up that work.", row.people_entity_id)


@player_action("mishap:create", ActionKind.EDIT_RECORD)
async def mishap_create(scope: PlayerScope, command: MishapDraft) -> Effect:
    row = await control.add_mishap(await scope.context("mishap_create"), command.town_id, command.kind, command.victim_id, command.cause_id)
    return Effect("A misfortune befalls the town.", command.town_id, values={"mishap_id": row.id})


@player_action("luck_belief:create", ActionKind.EDIT_RECORD)
async def luck_belief_create(scope: PlayerScope, command: BeliefDraft) -> Effect:
    row = await control.add_belief(
        await scope.context("luck_belief_create"), command.people_id, command.sign, command.reach, lucky=command.lucky, name=command.name
    )
    return Effect("The people believe it.", command.people_id, values={"belief_id": row.id})


@player_action("charm:set", ActionKind.EDIT_RECORD)
async def charm_set(scope: PlayerScope, command: CharmDraft) -> Effect:
    row = await control.set_charm(await scope.context("charm_set"), command.item_id, command.power, command.strength)
    return Effect("The item is a charm, and its power is real." if row.real else "The item is a charm, believed in.", command.item_id)


@player_action("accusation:create", ActionKind.EDIT_RECORD)
async def accusation_create(scope: PlayerScope, command: AccusationDraft) -> Effect:
    row = await control.accuse_by_hand(await scope.context("accusation_create"), command.town_id, command.accuser_id, command.mishap_id)
    return Effect("An accusation of witchcraft is made.", row.accused_node_id, values={"accusation_id": row.id})


@player_action("witch_hunt:create", ActionKind.EDIT_RECORD)
async def witch_hunt_create(scope: PlayerScope, command: HuntDraft) -> Effect:
    row = await control.start_hunt(await scope.context("witch_hunt_create"), command.town_id, command.fervour)
    return Effect("A witch hunt takes hold of the town.", command.town_id, values={"hunt_id": row.id})


@player_action("diet:edit", ActionKind.EDIT_RECORD)
async def diet_edit(scope: PlayerScope, command: DietEdit) -> Effect:
    await control.edit_record(await scope.context("diet_edit"), "diet", command.holder_id, command.values, command.release)
    return Effect("The diet is set so.", command.holder_id)


@player_action("diet:delete", ActionKind.EDIT_RECORD)
async def diet_delete(scope: PlayerScope, command: DietTarget) -> Effect:
    await control.delete_record(await scope.context("diet_delete"), "diet", command.holder_id)
    return Effect("The diet is forgotten.", command.holder_id)


@player_action("nutrient_need:edit", ActionKind.EDIT_RECORD)
async def nutrient_need_edit(scope: PlayerScope, command: NutrientNeedEdit) -> Effect:
    await control.edit_record(
        await scope.context("nutrient_need_edit"), "nutrient_need", (command.people_id, command.nutrient), command.values, command.release
    )
    return Effect("The need is set so.", command.people_id)


@player_action("nutrient_need:delete", ActionKind.EDIT_RECORD)
async def nutrient_need_delete(scope: PlayerScope, command: NutrientNeedTarget) -> Effect:
    await control.delete_record(await scope.context("nutrient_need_delete"), "nutrient_need", (command.people_id, command.nutrient))
    return Effect("The need is struck.", command.people_id)


@player_action("nutrition_score:edit", ActionKind.EDIT_RECORD)
async def nutrition_score_edit(scope: PlayerScope, command: NutritionScoreEdit) -> Effect:
    await control.edit_record(await scope.context("nutrition_score_edit"), "nutrition_score", command.holder_id, command.values, command.release)
    return Effect("The nutrition is set so.", command.holder_id)


@player_action("nutrition_score:delete", ActionKind.EDIT_RECORD)
async def nutrition_score_delete(scope: PlayerScope, command: NutritionScoreTarget) -> Effect:
    await control.delete_record(await scope.context("nutrition_score_delete"), "nutrition_score", command.holder_id)
    return Effect("The nutrition is forgotten.", command.holder_id)


@player_action("bias_weight:edit", ActionKind.EDIT_RECORD)
async def bias_weight_edit(scope: PlayerScope, command: BiasWeightEdit) -> Effect:
    await control.edit_record(await scope.context("bias_weight_edit"), "bias_weight", (command.holder_id, command.bias), command.values, command.release)
    return Effect("The bias is set so.", command.holder_id)


@player_action("bias_weight:delete", ActionKind.EDIT_RECORD)
async def bias_weight_delete(scope: PlayerScope, command: BiasWeightTarget) -> Effect:
    await control.delete_record(await scope.context("bias_weight_delete"), "bias_weight", (command.holder_id, command.bias))
    return Effect("The bias is struck.", command.holder_id)


@player_action("purity:edit", ActionKind.EDIT_RECORD)
async def purity_edit(scope: PlayerScope, command: PurityEdit) -> Effect:
    await control.edit_record(await scope.context("purity_edit"), "purity", command.mortal_id, command.values, command.release)
    return Effect("The purity is set so.", command.mortal_id)


@player_action("purity:delete", ActionKind.EDIT_RECORD)
async def purity_delete(scope: PlayerScope, command: PurityTarget) -> Effect:
    await control.delete_record(await scope.context("purity_delete"), "purity", command.mortal_id)
    return Effect("The purity is forgotten.", command.mortal_id)


@player_action("impurity_source:edit", ActionKind.EDIT_RECORD)
async def impurity_source_edit(scope: PlayerScope, command: ImpuritySourceEdit) -> Effect:
    await control.edit_record(
        await scope.context("impurity_source_edit"), "impurity_source", (command.people_id, command.source), command.values, command.release
    )
    return Effect("The source of impurity is set so.", command.people_id)


@player_action("impurity_source:delete", ActionKind.EDIT_RECORD)
async def impurity_source_delete(scope: PlayerScope, command: ImpuritySourceTarget) -> Effect:
    await control.delete_record(await scope.context("impurity_source_delete"), "impurity_source", (command.people_id, command.source))
    return Effect("The source of impurity is struck.", command.people_id)


@player_action("purification:edit", ActionKind.EDIT_RECORD)
async def purification_edit(scope: PlayerScope, command: PurificationEdit) -> Effect:
    await control.edit_record(await scope.context("purification_edit"), "purification", (command.people_id, command.method), command.values, command.release)
    return Effect("The purification is set so.", command.people_id)


@player_action("purification:delete", ActionKind.EDIT_RECORD)
async def purification_delete(scope: PlayerScope, command: PurificationTarget) -> Effect:
    await control.delete_record(await scope.context("purification_delete"), "purification", (command.people_id, command.method))
    return Effect("The purification is struck.", command.people_id)


@player_action("purity_rank:edit", ActionKind.EDIT_RECORD)
async def purity_rank_edit(scope: PlayerScope, command: PurityRankEdit) -> Effect:
    await control.edit_record(await scope.context("purity_rank_edit"), "purity_rank", command.rank_id, command.values, command.release)
    return Effect("The rank is set so.")


@player_action("purity_rank:delete", ActionKind.EDIT_RECORD)
async def purity_rank_delete(scope: PlayerScope, command: PurityRankTarget) -> Effect:
    await control.delete_record(await scope.context("purity_rank_delete"), "purity_rank", command.rank_id)
    return Effect("The rank is struck.")


@player_action("mishap:edit", ActionKind.EDIT_RECORD)
async def mishap_edit(scope: PlayerScope, command: MishapEdit) -> Effect:
    await control.edit_record(await scope.context("mishap_edit"), "mishap", command.mishap_id, command.values, command.release)
    return Effect("The misfortune is set so.")


@player_action("mishap:delete", ActionKind.EDIT_RECORD)
async def mishap_delete(scope: PlayerScope, command: MishapTarget) -> Effect:
    await control.delete_record(await scope.context("mishap_delete"), "mishap", command.mishap_id)
    return Effect("The misfortune is struck from the record.")


@player_action("luck_belief:edit", ActionKind.EDIT_RECORD)
async def luck_belief_edit(scope: PlayerScope, command: LuckBeliefEdit) -> Effect:
    await control.edit_record(await scope.context("luck_belief_edit"), "luck_belief", command.belief_id, command.values, command.release)
    return Effect("The belief is set so.")


@player_action("luck_belief:delete", ActionKind.EDIT_RECORD)
async def luck_belief_delete(scope: PlayerScope, command: LuckBeliefTarget) -> Effect:
    await control.delete_record(await scope.context("luck_belief_delete"), "luck_belief", command.belief_id)
    return Effect("The belief is struck.")


@player_action("charm:edit", ActionKind.EDIT_RECORD)
async def charm_edit(scope: PlayerScope, command: CharmEdit) -> Effect:
    await control.edit_record(await scope.context("charm_edit"), "charm", command.item_id, command.values, command.release)
    return Effect("The charm is set so.", command.item_id)


@player_action("charm:delete", ActionKind.EDIT_RECORD)
async def charm_delete(scope: PlayerScope, command: CharmTarget) -> Effect:
    await control.delete_record(await scope.context("charm_delete"), "charm", command.item_id)
    return Effect("The charm is undone.", command.item_id)


@player_action("accusation:edit", ActionKind.EDIT_RECORD)
async def accusation_edit(scope: PlayerScope, command: AccusationEdit) -> Effect:
    await control.edit_record(await scope.context("accusation_edit"), "accusation", command.accusation_id, command.values, command.release)
    return Effect("The accusation is set so.")


@player_action("accusation:delete", ActionKind.EDIT_RECORD)
async def accusation_delete(scope: PlayerScope, command: AccusationTarget) -> Effect:
    await control.delete_record(await scope.context("accusation_delete"), "accusation", command.accusation_id)
    return Effect("The accusation is struck from the record.")


@player_action("witch_hunt:edit", ActionKind.EDIT_RECORD)
async def witch_hunt_edit(scope: PlayerScope, command: WitchHuntEdit) -> Effect:
    await control.edit_record(await scope.context("witch_hunt_edit"), "witch_hunt", command.hunt_id, command.values, command.release)
    return Effect("The witch hunt is set so.")


@player_action("witch_hunt:delete", ActionKind.EDIT_RECORD)
async def witch_hunt_delete(scope: PlayerScope, command: WitchHuntTarget) -> Effect:
    await control.delete_record(await scope.context("witch_hunt_delete"), "witch_hunt", command.hunt_id)
    return Effect("The witch hunt is struck from the record.")
