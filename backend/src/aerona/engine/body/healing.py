from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import SIGHT_PARTS, Part
from aerona.catalog.conditions import FESTERING, FRESH_STATES, OPEN_INJURY_STATES, SENSE_CONDITIONS
from aerona.catalog.goods_tables import WORKABILITY
from aerona.catalog.goods_traits import materials_with
from aerona.catalog.harm_kinds import INJURIES, SET, STEPS
from aerona.catalog.life.domain import MEDICINE_ORDER
from aerona.catalog.medicine import MEDICINE, infection_cut, tier_of
from aerona.catalog.mind import HEALING_SKILLS
from aerona.catalog.tissues import COUNTED_PARTS, DIGIT_LIMBS
from aerona.constants.units import PERCENT
from aerona.core.grammar import an, spoken
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow, InjuryRow, ProsthesisRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyFunction, BodyPart, BodyRegion, ConditionKind, HarmCause, InjuryKind, InjuryState, MedicineTier, TreatmentStep
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import Attribute, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause, HarshnessScale
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.body.book import Bearer, anatomy_for, bearer_stats, ensure_body, injuries_of, prostheses_of
from aerona.engine.body.conditions import end_condition, gain_condition
from aerona.engine.body.digits import full_counts, lose_all, restore
from aerona.engine.body.hits import CLEAN_HEALING_KINDS, MARK_KINDS, PERMANENT_KINDS, TOTAL_LOSS_KINDS
from aerona.engine.body.state import refresh
from aerona.engine.body.treatment import Treatment, bleed, regain_blood, treat
from aerona.engine.body.variants import ORDINARY, folk_biology, shaped
from aerona.engine.context import TickContext
from aerona.engine.disease.book import hospital_strengths
from aerona.engine.disease.load import DiseaseLoads
from aerona.engine.dominion.effects import step_here
from aerona.engine.economy.materials import set_node_material
from aerona.engine.folk_knowledge.factor import folk_factor
from aerona.engine.genetics.life import healing_factor
from aerona.engine.gods.queries import community_of
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lore.research import lacks
from aerona.engine.mind.hooks import failed_to_heal, healed
from aerona.engine.mind.split import attribute, lean_factor
from aerona.engine.mind.thoughts import think
from aerona.engine.museums.reading import physic_share
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.harshness import harshness
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, connect, directed_bond
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record
from aerona.rules.registry import Rules
from aerona.rules.registry.body import HealingRules, ProstheticsRules

HEALER_ROLES = frozenset({MortalRole.HEALER, MortalRole.PRIEST, MortalRole.SAINT, MortalRole.PHYSICIAN})
FESTER_DEATH = "died of a festering wound"
BLED_OUT = "bled to death from an open wound"
PRECIOUS = frozenset(materials_with(MaterialTrait.PRECIOUS))


async def known_tier(session: AsyncSession, holder_id: int | None, tier: MedicineTier) -> MedicineTier:
    for candidate in reversed(MEDICINE_ORDER[: tier_index(tier) + 1]):
        technique = MEDICINE[candidate].technique
        if technique is None or not await lacks(session, holder_id, technique):
            return candidate
    return MedicineTier.NONE


def tier_index(tier: MedicineTier) -> int:
    return MEDICINE_ORDER.index(tier)


def infection_base(rules: HealingRules, kind: InjuryKind) -> int:
    found = INJURIES[kind].infection
    return found(rules) if found is not None else rules.infection_other


def permanent_chance(rules: HealingRules, kind: InjuryKind) -> int:
    found = INJURIES[kind].lasting
    return found(rules) if found is not None else rules.permanent_other


def heal_chance(rules: HealingRules, severity: int, kind: InjuryKind) -> float:
    by_severity = (rules.heal_severity_1, rules.heal_severity_2, rules.heal_severity_3, rules.heal_severity_4, rules.heal_severity_5)[severity - 1]
    found = INJURIES[kind].healing
    by_kind = found(rules) if found is not None else PERCENT
    return by_severity * by_kind / PERCENT


def lasting_chance(rules: HealingRules, kind: InjuryKind, severity: int) -> float:
    by_severity = (
        rules.permanent_severity_1_pct,
        rules.permanent_severity_2_pct,
        rules.permanent_severity_3_pct,
        rules.permanent_severity_4_pct,
        rules.permanent_severity_5_pct,
    )[severity - 1]
    return permanent_chance(rules, kind) * by_severity / PERCENT


@dataclass(frozen=True)
class Healer:
    mortal: EntityRow
    skill: int
    region: int | None


@dataclass
class Care:
    tier: MedicineTier
    healer: Healer | None
    disease: int
    metallurgy: int
    artisan: EntityRow | None
    amputation: bool = True
    hospital: float = 0.0
    medicine: int = 0
    community_id: int | None = None
    physic: float = 0.0


@dataclass
class HealingWorld:
    rules: Rules
    atlas: RegionAtlas
    knowledge: KnowledgeMap
    healers: dict[int | None, list[Healer]]
    disease: dict[int, int]
    artisans: dict[int | None, list[EntityRow]]
    hospitals: dict[int, float] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "HealingWorld":
        atlas = await RegionAtlas.load(session)
        knowledge = await KnowledgeMap.load(session)
        healers: dict[int | None, list[Healer]] = defaultdict(list)
        artisans: dict[int | None, list[EntityRow]] = defaultdict(list)
        trained: dict[int, int] = defaultdict(int)
        hospitals = await hospital_strengths(session, atlas)
        for skill_row in await session.scalars(select(SkillRow).where(SkillRow.skill.in_(HEALING_SKILLS), SkillRow.subject_node_id.is_(None))):
            trained[skill_row.holder_node_id] = max(trained[skill_row.holder_node_id], skill_row.level)
        for mortal in await canon(session, [EntityType.MORTAL]):
            region = atlas.top_region(mortal.id)
            if mortal.mortal_role is MortalRole.ARTISAN:
                artisans[region].append(mortal)
            level = trained.get(mortal.id, 0)
            if mortal.mortal_role not in HEALER_ROLES and level < rules.careers.min_level:
                continue
            body = await session.get(BodyRow, mortal.id)
            hands = body.craft / PERCENT if body is not None else 1.0
            raw = level * rules.skills.healer_scale_pct / PERCENT
            ward = 1 + hospitals.get(region, 0.0) * (rules.epidemiology.hospital_healer_pct / PERCENT - 1) if region is not None else 1.0
            healers[region].append(Healer(mortal, clamp_int(raw * hands * ward, 0, PERCENT), region))
        disease = dict((await DiseaseLoads.load(session, rules)).regions)
        return cls(rules=rules, atlas=atlas, knowledge=knowledge, healers=healers, disease=disease, artisans=artisans, hospitals=hospitals)

    def best_healer(self, bearer: EntityRow) -> Healer | None:
        region = self.atlas.top_region(bearer.id)
        reach = self.rules.healing.healer_reach
        candidates = [
            healer
            for place, group in self.healers.items()
            for healer in group
            if healer.mortal.id != bearer.id and (place == region or ((hops := self.atlas.region_hops(region, place)) is not None and hops <= reach))
        ]
        return max(candidates, key=lambda healer: (healer.skill, -healer.mortal.id), default=None)

    def best_artisan(self, bearer: EntityRow) -> EntityRow | None:
        group = self.artisans.get(self.atlas.top_region(bearer.id), [])
        return max(group, key=lambda mortal: (stat(mortal, "intellect") or 0, -mortal.id), default=None)

    async def care_for(self, session: AsyncSession, bearer: Bearer) -> Care:
        rules = self.rules
        if not isinstance(bearer, EntityRow):
            return Care(MedicineTier.NONE, None, 0, 0, None)
        community = await community_of(session, bearer)
        holders = [bearer.id, *([community.id] if community is not None else [])]
        medicine = max(self.knowledge.level(holder, KnowledgeBranch.MEDICINE) for holder in holders)
        magic = max(self.knowledge.level(holder, KnowledgeBranch.MAGIC) for holder in holders)
        biomancy = any(self.knowledge.knows(holder, KnowledgeBranch.BIOMANCY) for holder in holders)
        metallurgy = max(self.knowledge.level(holder, KnowledgeBranch.METALLURGY) for holder in holders)
        notable = is_notable(rules, bearer, await EntityRepository(session).flags(bearer.id))
        healer = self.best_healer(bearer) if notable else None
        region = self.atlas.top_region(bearer.id)
        disease = self.disease.get(region, rules.healing.disease_reference) if region is not None else rules.healing.disease_reference
        artisan = self.best_artisan(bearer) if notable else None
        home = community.id if community is not None else None
        tier = await known_tier(session, home, tier_of(rules.healing, medicine, magic, biomancy))
        ward = self.hospitals.get(region, 0.0) if region is not None else 0.0
        return Care(
            tier,
            healer,
            disease,
            metallurgy,
            artisan,
            amputation=not await lacks(session, home, Technique.AMPUTATION),
            hospital=ward,
            medicine=medicine,
            community_id=home,
            physic=await physic_share(session, rules, home),
        )


async def _renown(ctx: TickContext, healer: Healer | None, *, mended: bool) -> None:
    if healer is None:
        return
    body = await ensure_body(ctx.session, ctx.rules, healer.mortal, ctx.epoch)
    table = ctx.rules.healing
    if mended:
        body.patients_healed += 1
        healer.mortal.importance = (healer.mortal.importance or 0) + table.healer_renown_heal
    else:
        body.patients_lost += 1
        healer.mortal.importance = max(0, (healer.mortal.importance or 0) - table.healer_renown_loss)


async def _treated(ctx: TickContext, bearer: Bearer, row: InjuryRow, healer: Healer | None) -> None:
    if healer is None:
        return
    row.treated_by_node_id = healer.mortal.id
    if await directed_bond(ctx.session, bearer.id, healer.mortal.id, BondKind.TREATED_BY) is None:
        await connect(ctx.session, bearer.id, healer.mortal.id, BondKind.TREATED_BY, ctx.epoch, description="tended their wounds")


def _part(body: BodyRow, row: InjuryRow) -> Part | None:
    return anatomy_for(body).part(row.part)


def _limb(part: Part | None) -> bool:
    return part is not None and part.severable and part.region in {BodyRegion.ARMS, BodyRegion.LEGS, BodyRegion.WINGS, BodyRegion.TAIL}


@dataclass
class Tending:
    died: bool = False
    changed: bool = False
    handled: bool = False


async def _fester(ctx: TickContext, bearer: Bearer, body: BodyRow, row: InjuryRow, *, care: Care, rng_key: str) -> Tending:
    table = ctx.rules.healing
    rng = ctx.rng(seed_of("fester", rng_key))
    row.infected_epochs += 1
    part = _part(body, row)
    vital = part is not None and part.vital
    index = tier_index(care.tier)
    deadly = (table.lethal_infected_vital if vital else table.lethal_infected_limb) * max(0, PERCENT - index * table.lethal_medicine_cut_pct) / PERCENT
    deadly *= 1 - care.physic
    deadly *= 1 - care.hospital * ctx.rules.structure_functions.hospital_death_cut_pct / PERCENT
    deadly *= harshness(ctx.rules, HarshnessScale.INFECTION) * bled(ctx.rules, row)
    lethal = row.infected_epochs >= table.lethal_after_epochs or rng.chance(deadly)
    if row.state is InjuryState.GANGRENOUS:
        drained = 1 - ctx.rules.treatment.drain_infection_cut_pct / PERCENT if TreatmentStep.DRAIN.value in row.treatments else 1
        lethal = rng.chance(
            ctx.rules.injury_states.gangrene_death_pct
            * max(0, PERCENT - index * table.lethal_medicine_cut_pct)
            / PERCENT
            * (1 - care.physic)
            * drained
            * bled(ctx.rules, row)
        )
    saw = index >= tier_index(MedicineTier.SURGERY) and care.amputation and _limb(part)
    if saw and (row.infected_epochs >= ctx.rules.tissues.amputate_at or (lethal and rng.chance(table.amputation_chance))):
        row.kind, row.function_loss, row.state, row.infected_epochs = InjuryKind.SEVERED, PERCENT, InjuryState.HEALING, 0
        row.treatments = [*row.treatments, TreatmentStep.AMPUTATE.value]
        counted = COUNTED_PARTS.get(row.part)
        if row.part in DIGIT_LIMBS:
            row.digits = sorted({*row.digits, *lose_all(body, row.part)})
        elif counted is not None:
            setattr(body, counted, 0)
        await _treated(ctx, bearer, row, care.healer)
        if care.healer is not None:
            await healed(ctx, care.healer.mortal.id, bearer.id, saved=True)
        if isinstance(bearer, EntityRow):
            healer = care.healer.mortal.id if care.healer is not None else None
            roles: dict[IncidentRole, RoleValue] = {IncidentRole.PATIENT: bearer.id, IncidentRole.HEALER: healer}
            steps = (
                StepDraft(
                    StepAction.AMPUTATE,
                    actor=healer,
                    target=bearer.id,
                    locus_kind=StepLocus.BODY_PART,
                    locus_key=row.part.value,
                    outcome=StepOutcome.SEVERED,
                    record_table="injuries",
                    record_key=str(row.id),
                ),
            )
            facts: dict[str, FactInput] = {"part": row.part, "infected_epochs": row.infected_epochs, "medicine": care.tier}
            await record(ctx, "healing.amputated", roles=roles, facts=facts, steps=steps)
        return Tending(changed=True)
    if lethal:
        return await _succumb(ctx, bearer, row, care, rng)
    skill = care.healer.skill if care.healer is not None else 0
    clear = table.infection_clear * (1 + index * table.infection_clear_medicine_pct / PERCENT) * (1 + skill / PERCENT)
    if row.state is InjuryState.GANGRENOUS and index < tier_index(MedicineTier.SURGERY):
        return Tending()
    if rng.chance(clear):
        row.state = InjuryState.HEALING
        await _treated(ctx, bearer, row, care.healer)
        return Tending(changed=True)
    return Tending()


async def _succumb(ctx: TickContext, bearer: Bearer, row: InjuryRow, care: Care, rng: SeededRandom) -> Tending:
    if row.state is InjuryState.INFECTED and rng.chance(ctx.rules.injury_states.gangrene_pct):
        row.state = InjuryState.GANGRENOUS
        if isinstance(bearer, EntityRow):
            await record(ctx, "body.gangrene", roles={IncidentRole.PATIENT: bearer.id}, facts={"part": row.part, "infected_epochs": row.infected_epochs})
        return Tending(changed=True)
    row.state = InjuryState.LETHAL
    await _renown(ctx, care.healer, mended=False)
    if care.healer is not None and isinstance(bearer, EntityRow):
        await failed_to_heal(ctx, care.healer.mortal.id, bearer)
    if isinstance(bearer, EntityRow) and bearer.entity_type is EntityType.BEAST:
        await retire_in(ctx, bearer, FESTER_DEATH)
        return Tending(died=True, changed=True)
    if isinstance(bearer, EntityRow):
        await die(ctx, bearer, cause=FESTER_DEATH, manner=DeathCause.WOUNDS, event_id=row.event_entity_id)
        return Tending(died=True, changed=True)
    row.state = InjuryState.PERMANENT
    return Tending(changed=True)


async def _close(ctx: TickContext, bearer: Bearer, row: InjuryRow, care: Care, rng_key: str) -> None:
    table = ctx.rules.healing
    rng = ctx.rng(seed_of("scar", rng_key))
    set_right = {step.value for step in SET} <= set(row.treatments)
    spared = 1 - ctx.rules.tissues.set_bone_loss_pct / PERCENT if set_right else 1
    lasting = row.kind in PERMANENT_KINDS or rng.chance(
        lasting_chance(table, row.kind, row.severity) * harshness(ctx.rules, HarshnessScale.PERMANENT_INJURY) * spared
    )
    if lasting:
        row.state = InjuryState.PERMANENT
        if row.kind not in TOTAL_LOSS_KINDS:
            row.function_loss = round_half_up(row.function_loss * table.permanent_residual_pct / PERCENT)
    elif row.kind in CLEAN_HEALING_KINDS:
        row.state, row.function_loss, row.visible = InjuryState.HEALED_SCAR, 0, False
    else:
        row.state = InjuryState.HEALED_SCAR
        row.function_loss = round_half_up(row.function_loss * table.scar_residual_pct / PERCENT)
        row.visible = row.visible and row.severity >= table.scar_visible_severity
    row.healed_epoch = ctx.epoch
    await _treated(ctx, bearer, row, care.healer)
    await _renown(ctx, care.healer, mended=True)
    if care.healer is not None:
        await healed(ctx, care.healer.mortal.id, bearer.id, saved=row.severity >= table.saved_severity)
    if lasting and row.kind in TOTAL_LOSS_KINDS:
        await think(ctx.session, ctx.rules, bearer.id, ThoughtKind.LOST_LIMB_BUT_LIVED, ctx.epoch, subject_id=row.cause_node_id)
    if lasting and row.kind is InjuryKind.CURSE_WITHER and row.severity >= ctx.rules.conditions.wither_condition_severity:
        await gain_condition(ctx, bearer, ConditionKind.WITHERED_LIMB, row.cause_kind, severity=row.severity, part=row.part, source_node_id=row.cause_node_id)
    if lasting and row.kind is InjuryKind.VENOM:
        await gain_condition(ctx, bearer, ConditionKind.CHRONIC_ILLNESS, row.cause_kind, severity=row.severity, source_node_id=row.cause_node_id)
    if lasting and row.severity >= ctx.rules.conditions.pain_severity:
        await gain_condition(ctx, bearer, ConditionKind.CHRONIC_PAIN, row.cause_kind, severity=row.severity, part=row.part, source_node_id=row.cause_node_id)
    if lasting and row.part is BodyPart.GROIN:
        await gain_condition(ctx, bearer, ConditionKind.INFERTILITY, row.cause_kind, severity=row.severity, part=row.part, source_node_id=row.cause_node_id)
    if lasting and row.kind is InjuryKind.SICKNESS:
        await gain_condition(ctx, bearer, ConditionKind.CHRONIC_ILLNESS, row.cause_kind, severity=row.severity, part=row.part, source_node_id=row.cause_node_id)


HEALING_KEY = "healing"
INJURY_HOLD = "injuries"


def infection_chance(ctx: TickContext, row: InjuryRow, body: BodyRow, care: Care, skill: int) -> float:
    table = ctx.rules.healing
    chance = infection_base(table, row.kind) * care.disease / table.disease_reference
    chance *= harshness(ctx.rules, HarshnessScale.INFECTION) * (1 + (PERCENT - body.vital) * table.vital_infection_pct / PERCENT / PERCENT)
    chance *= (PERCENT - infection_cut(table, care.tier)) / PERCENT * (PERCENT - min(table.healer_skill_cap, skill)) / PERCENT
    chance *= 1 - care.hospital * ctx.rules.structure_functions.hospital_infection_cut_pct / PERCENT
    chance *= 1 - care.physic
    chance *= 1 - ctx.rules.treatment.drain_infection_cut_pct / PERCENT if TreatmentStep.DRAIN.value in row.treatments else 1
    return chance * (1 - ctx.rules.tissues.clean_infection_pct / PERCENT if TreatmentStep.CLEAN.value in row.treatments else 1)


async def bled_out(ctx: TickContext, bearer: Bearer, body: BodyRow, wounds: list[InjuryRow], care: Care) -> Tending:
    if not isinstance(bearer, EntityRow):
        return Tending()
    if not await bleed(ctx, bearer, body, wounds, healer=care.healer is not None, rng=ctx.rng(seed_of("bleed", bearer.id, ctx.epoch))):
        return Tending()
    if body.blood > ctx.rules.tissues.bleed_death_at:
        return Tending(changed=True)
    await die(ctx, bearer, cause=BLED_OUT, manner=DeathCause.WOUNDS, event_id=max(wounds, key=lambda row: row.bleeding).event_entity_id)
    return Tending(died=True, changed=True)


async def _progress(ctx: TickContext, bearer: Bearer, row: InjuryRow, care: Care, key: str, *, mended: bool) -> bool:
    if mended:
        await _close(ctx, bearer, row, care, key)
        return True
    if row.state in FRESH_STATES:
        row.state = InjuryState.HEALING
        return True
    return False


BLED_INSIDE = "bled to death inside"


async def bleeding_inside(ctx: TickContext, bearer: Bearer, row: InjuryRow, care: Care, key: str) -> Tending:
    if row.kind is not InjuryKind.INTERNAL_BLEEDING or row.treatments or not isinstance(bearer, EntityRow):
        return Tending()
    cut = max(0, PERCENT - tier_index(care.tier) * ctx.rules.healing.lethal_medicine_cut_pct) / PERCENT * (1 - care.physic)
    if not ctx.rng(seed_of("inside", key)).chance(ctx.rules.injuries.internal_bleed_death_pct * cut):
        return Tending()
    row.state = InjuryState.LETHAL
    if bearer.entity_type is EntityType.BEAST:
        await retire_in(ctx, bearer, BLED_INSIDE)
    else:
        await die(ctx, bearer, cause=BLED_INSIDE, manner=DeathCause.WOUNDS, event_id=row.event_entity_id)
    return Tending(died=True, changed=True)


async def shift_wound(ctx: TickContext, bearer: Bearer, body: BodyRow, row: InjuryRow, wounds: list[InjuryRow], *, care: Care, key: str) -> Tending:
    inside = await bleeding_inside(ctx, bearer, row, care, key)
    if inside.died:
        return inside
    reopened = await strained_open(ctx, bearer, row, wounds, key)
    if row.state not in FESTERING:
        return Tending(changed=reopened)
    result = await _fester(ctx, bearer, body, row, care=care, rng_key=key)
    return Tending(died=result.died, changed=reopened or result.changed, handled=True)


async def strained_open(ctx: TickContext, bearer: Bearer, row: InjuryRow, wounds: list[InjuryRow], key: str) -> bool:
    strained = any(other.epoch == ctx.epoch and other.id != row.id for other in wounds)
    if row.state is not InjuryState.HEALING or not strained or not ctx.rng(seed_of("reopen", key)).chance(ctx.rules.injury_states.reopen_strain_pct):
        return False
    row.state = InjuryState.REOPENED
    if isinstance(bearer, EntityRow):
        await record(ctx, "body.wound_reopened", roles={IncidentRole.PATIENT: bearer.id}, facts={"part": row.part, "injury": row.kind})
    return True


async def mending_of(ctx: TickContext, bearer: Bearer) -> float:
    mending = 1 + lean_factor(await attribute(ctx.session, ctx.rules, bearer, Attribute.RECUPERATION), ctx.rules.mind_split.recuperation_pct)
    mending *= await ctx.hook_factor(bearer.id, DomainHook.HEALING)
    if isinstance(bearer, EntityRow):
        mending *= await folk_factor(ctx.session, ctx.rules, bearer, FolkDomain.BODY)
        mending *= await step_here(ctx, bearer.id, DivineScale.GROWTH, ctx.rules.dominion.healing_per_step_pct)
        mending *= healing_factor(ctx.rules, await ctx.session.get(GenomeRow, bearer.id))
    return mending


async def tend(ctx: TickContext, bearer: Bearer, world: HealingWorld) -> Tending:
    if blocked(bearer.id, HEALING_KEY):
        return Tending()
    body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
    if INJURY_HOLD in body.locked:
        return Tending()
    anatomy = shaped(anatomy_for(body), await folk_biology(ctx.session, bearer) if isinstance(bearer, EntityRow) else ORDINARY)
    table = ctx.rules.healing
    care = await world.care_for(ctx.session, bearer)
    stats = bearer_stats(bearer)
    divine = isinstance(bearer, SonRow | ForeignGodRow)
    wounds = await injuries_of(ctx.session, bearer.id)
    outcome = await bled_out(ctx, bearer, body, wounds, care)
    if outcome.died:
        return outcome
    walking = {part.key for part in anatomy.with_function(BodyFunction.LOCOMOTION)}
    skill = care.healer.skill if care.healer is not None else 0
    split = ctx.rules.mind_split
    ward = 1 - lean_factor(await attribute(ctx.session, ctx.rules, bearer, Attribute.DISEASE_RESISTANCE), split.resistance_pct)
    mending = await mending_of(ctx, bearer)
    healer_id = care.healer.mortal.id if care.healer is not None else None
    steps: list[StepDraft] = []
    for row in wounds:
        if row.state not in OPEN_INJURY_STATES:
            continue
        key = f"{bearer.id}.{row.id}.{ctx.epoch}"
        rng = ctx.rng(seed_of("heal", key))
        treated, done = await _treat_wound(ctx, row, care, walking=row.part in walking, key=key, patient=bearer.id)
        outcome.changed = treated or outcome.changed
        steps.extend(done)
        campaign = row.cause_kind is HarmCause.BATTLE and row.epoch == ctx.epoch
        if anatomy.infects and infected(ctx, row, body, care, skill=skill, ward=max(0.0, ward), rng=rng, campaign=campaign):
            outcome.changed = True
            steps.append(wound_step(StepAction.WORSEN, row, None, bearer.id, StepOutcome.WOUNDED))
        shifted = await shift_wound(ctx, bearer, body, row, wounds, care=care, key=key)
        outcome.changed = outcome.changed or shifted.changed
        if shifted.died:
            outcome.died = True
            return outcome
        if shifted.handled:
            continue
        if anatomy.heals:
            mended = rng.chance(
                mend_chance(table, row, care, (1 + stats.endurance / PERCENT) * max(0.0, mending), skill, campaign=campaign, divine=divine)
                * remedied(ctx.rules, row)
            )
            if await _progress(ctx, bearer, row, care, key, mended=mended):
                outcome.changed = True
                steps.append(mending_step(row, healer_id, bearer.id, mended=mended))
    if isinstance(bearer, EntityRow):
        outcome.changed = await _restore(ctx, bearer, body, care) or outcome.changed
        if steps:
            await record_tending(ctx, bearer, healer_id, care.tier, steps)
    return outcome


def infected(ctx: TickContext, row: InjuryRow, body: BodyRow, care: Care, *, skill: int, ward: float, rng: SeededRandom, campaign: bool) -> bool:
    if row.state in FESTERING:
        return False
    campaigns = ctx.rules.campaigns
    checks = 1 + campaigns.war_seasons() // campaigns.years_per_epoch if campaign else 1
    chance = infection_chance(ctx, row, body, care, skill) * ward
    if not any(rng.chance(chance) for _ in range(checks)):
        return False
    row.state = InjuryState.INFECTED
    return True


def bled(rules: Rules, row: InjuryRow) -> float:
    return max(0.0, 1 + rules.treatment.bleed_harm_pct / PERCENT) if TreatmentStep.BLEED.value in row.treatments else 1.0


def remedied(rules: Rules, row: InjuryRow) -> float:
    harmed = max(0.0, 1 - rules.treatment.bleed_harm_pct / PERCENT) if TreatmentStep.BLEED.value in row.treatments else 1.0
    return harmed * (1 + rules.treatment.medicate_effect_pct / PERCENT if TreatmentStep.MEDICATE.value in row.treatments else 1.0)


def mend_chance(table: HealingRules, row: InjuryRow, care: Care, vigour: float, skill: int, *, campaign: bool, divine: bool) -> float:
    chance = heal_chance(table, row.severity, row.kind) * vigour
    chance *= table.campaign_rest_pct / PERCENT if campaign else 1
    chance *= 1 + table.healer_heal_bonus_pct * skill / PERCENT / PERCENT
    chance *= 1 + table.divine_heal_bonus_pct / PERCENT if divine else 1
    return chance * (1 + table.mind_care_pct / PERCENT if row.kind is InjuryKind.MIND_SCAR and MEDICINE[care.tier].mind_care else 1)


async def _treat_wound(ctx: TickContext, row: InjuryRow, care: Care, *, walking: bool, key: str, patient: int) -> tuple[bool, list[StepDraft]]:
    if care.healer is None:
        return False, []
    rng = ctx.rng(seed_of("treat", key))
    treatment = await treat(ctx, row, skill=care.healer.skill, medicine=care.medicine, community_id=care.community_id, walking=walking, rng=rng)
    for step in treatment.steps:
        if STEPS[step].noted:
            await record(
                ctx, "body.treated", roles={IncidentRole.PATIENT: patient, IncidentRole.HEALER: care.healer.mortal.id}, facts={"step": step, "part": row.part}
            )
    return treatment.changed, treatment_steps(treatment, row, care.healer.mortal.id, patient)


def wound_step(action: StepAction, row: InjuryRow, actor: int | None, patient: int, outcome: StepOutcome) -> StepDraft:
    return StepDraft(
        action,
        actor=actor,
        target=patient,
        locus_kind=StepLocus.BODY_PART,
        locus_key=row.part.value,
        outcome=outcome,
        record_table=InjuryRow.__tablename__,
        record_key=str(row.id),
    )


def treatment_steps(treatment: Treatment, row: InjuryRow, healer: int | None, patient: int) -> list[StepDraft]:
    if treatment.misdiagnosed:
        return [wound_step(StepAction.EXAMINE, row, healer, patient, StepOutcome.FAILURE)]
    return [wound_step(STEPS[step].action, row, healer, patient, StepOutcome.SUCCESS) for step in treatment.steps]


def mending_step(row: InjuryRow, healer: int | None, patient: int, *, mended: bool) -> StepDraft:
    if not mended:
        return wound_step(StepAction.EASE, row, None, patient, StepOutcome.PARTIAL)
    closed = StepOutcome.PARTIAL if row.state is InjuryState.PERMANENT else StepOutcome.SUCCESS
    return wound_step(StepAction.RECOVER, row, healer, patient, closed)


async def record_tending(ctx: TickContext, bearer: EntityRow, healer: int | None, tier: MedicineTier, steps: list[StepDraft]) -> None:
    wounds = len({step.record_key for step in steps})
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.PATIENT: bearer.id, IncidentRole.HEALER: healer}
    await record(ctx, "healing.tended", roles=roles, facts={"wounds": wounds, "medicine": tier}, steps=steps)


async def _restore(ctx: TickContext, bearer: EntityRow, body: BodyRow, care: Care) -> bool:
    table = ctx.rules.healing
    changed = False
    fitted = {row.injury_id for row in await prostheses_of(ctx.session, bearer.id)}
    for row in await injuries_of(ctx.session, bearer.id):
        if row.state is not InjuryState.PERMANENT or row.kind not in TOTAL_LOSS_KINDS or row.id in fitted:
            continue
        part = _part(body, row)
        if part is None or part.vital:
            continue
        rng = ctx.rng(seed_of("restore", bearer.id, row.id, ctx.epoch))
        if care.tier is MedicineTier.REATTACHMENT and care.healer is not None and rng.chance(table.reattachment_chance):
            row.kind, row.state = InjuryKind.DEEP_CUT, InjuryState.HEALED_SCAR
            row.function_loss = table.reattachment_residual_pct
            counted = COUNTED_PARTS.get(row.part)
            if row.part in DIGIT_LIMBS:
                restore(body, row.part, row.digits)
            elif counted is not None:
                setattr(body, counted, full_counts(body)[row.part])
            await _treated(ctx, bearer, row, care.healer)
            roles = {IncidentRole.PATIENT: bearer.id, IncidentRole.HEALER: care.healer.mortal.id}
            steps = (
                StepDraft(
                    StepAction.OPERATE,
                    actor=care.healer.mortal.id,
                    target=bearer.id,
                    locus_kind=StepLocus.BODY_PART,
                    locus_key=row.part.value,
                    outcome=StepOutcome.SUCCESS,
                    record_table="injuries",
                    record_key=str(row.id),
                ),
            )
            await record(ctx, "healing.reattached", roles=roles, facts={"part": row.part, "residual_loss": row.function_loss}, steps=steps)
            changed = True
            continue
        if tier_index(care.tier) >= tier_index(MedicineTier.PROSTHETICS) and rng.chance(ctx.rules.prosthetics.fit_chance):
            await fit_prosthesis(ctx, bearer, row, part, material_for(ctx.rules.prosthetics, part, care.metallurgy), maker=care.artisan)
            changed = True
    return changed


def material_for(rules: ProstheticsRules, part: Part, metallurgy: int) -> MaterialKind:
    if part.key in SIGHT_PARTS:
        return MaterialKind.GLASS
    if part.region is BodyRegion.HEAD:
        return MaterialKind.SILVER if metallurgy >= rules.metal_level else MaterialKind.CALCIFIED_TISSUE
    return MaterialKind.IRON if metallurgy >= rules.metal_level else MaterialKind.WOOD


def workability(rules: ProstheticsRules, material: MaterialKind) -> int:
    found = WORKABILITY.get(material)
    return found(rules) if found is not None else rules.other


def material_workability(rules: ProstheticsRules, material: MaterialKind, world_material: WorldMaterialRow | None) -> int:
    if world_material is None:
        return workability(rules, material)
    if world_material.base_kind is not None:
        return workability(rules, world_material.base_kind)
    return clamp_int((world_material.toughness + world_material.hardness) / 2 + world_material.sanctity * rules.world_sanctity_pct / PERCENT, 0, PERCENT)


async def fit_prosthesis(
    ctx: TickContext,
    bearer: EntityRow,
    row: InjuryRow,
    part: Part,
    material: MaterialKind,
    *,
    maker: EntityRow | None,
    quality: int | None = None,
    item: EntityRow | None = None,
    world_material: WorldMaterialRow | None = None,
) -> ProsthesisRow:
    table = ctx.rules.prosthetics
    if maker is not None and await lacks(ctx.session, maker.location_id, Technique.PROSTHETICS):
        quality = min(quality if quality is not None else table.default_quality, table.default_quality // 2)
    if quality is None:
        quality = (
            clamp_int(
                (stat_or(maker, "intellect", table.default_quality)) * table.maker_intellect_pct / PERCENT
                + table.default_quality * (PERCENT - table.maker_intellect_pct) / PERCENT,
                0,
                PERCENT,
            )
            if maker is not None
            else table.default_quality
        )
        if maker is not None:
            hands = await ctx.session.get(BodyRow, maker.id)
            quality = clamp_int(quality * (hands.craft if hands is not None else PERCENT) / PERCENT, 0, PERCENT)
    restored = clamp_int(material_workability(table, material, world_material) * quality / PERCENT, 0, PERCENT)
    relic = material in PRECIOUS and quality >= table.relic_quality
    if item is None:
        made = spoken(material)
        item = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.ITEM,
                name=f"The {made.title()} {part.label.split()[-1].title()} of {bearer.name}" if relic else f"{made.capitalize()} {part.label.lower()}",
                body=f"{an(made, capital=True)} {part.label.lower()} made for {bearer.name}.",
                stats=ItemStats(might=quality),
                power=max(1, quality // table.relic_power_div),
                location_id=bearer.location_id,
                world_id=bearer.world_id,
                subtype="prosthesis",
                maker_entity_id=maker.id if maker is not None else None,
            ),
        )
        await connect(ctx.session, bearer.id, item.id, BondKind.OWNS, ctx.epoch, description="wears it in place of what was lost")
    await prosthesis_profile(ctx, item, row.part, material, quality, relic=relic, maker=maker)
    prosthesis = ProsthesisRow(
        bearer_node_id=bearer.id,
        injury_id=row.id,
        part=row.part,
        material=material,
        quality=quality,
        restored_pct=restored,
        item_entity_id=item.id if item is not None else None,
        maker_node_id=maker.id if maker is not None else None,
        world_material_id=world_material.id if world_material is not None else None,
        epoch=ctx.epoch,
    )
    ctx.session.add(prosthesis)
    await ctx.session.flush()
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.PATIENT: bearer.id,
        IncidentRole.MAKER: maker.id if maker is not None else None,
        IncidentRole.PRODUCT: item.id if item else None,
    }
    steps = (
        StepDraft(
            StepAction.FIT_PROSTHESIS,
            actor=maker.id if maker is not None else None,
            target=bearer.id,
            locus_kind=StepLocus.BODY_PART,
            locus_key=row.part.value,
            outcome=StepOutcome.SUCCESS,
        ),
    )
    facts: dict[str, FactInput] = {"part": row.part, "material": material, "quality": quality, "restored": restored}
    await record(ctx, "healing.prosthesis_made" if maker is not None else "healing.prosthesis", roles=roles, facts=facts, steps=steps)
    return prosthesis


async def prosthesis_profile(
    ctx: TickContext, item: EntityRow, part: str, material: MaterialKind, quality: int, *, relic: bool, maker: EntityRow | None
) -> ItemProfileRow:
    row = await ctx.session.get(ItemProfileRow, item.id)
    if row is None:
        row = ItemProfileRow(item_entity_id=item.id, item_class=ItemClass.PROSTHESIS, locked=[])
        ctx.session.add(row)
    row.item_class = ItemClass.PROSTHESIS
    row.prosthesis_for = part
    row.quality = quality
    row.value = quality
    row.renown = quality if relic else row.renown or 0
    row.symbol = relic
    row.maker_entity_id = maker.id if maker is not None else row.maker_entity_id
    row.updated_epoch = ctx.epoch
    await set_node_material(ctx.session, item.id, MaterialSlot.BODY, material, None, force=True)
    await ctx.session.flush()
    return row


def hp_ceiling(rules: Rules, bearer: EntityRow) -> int:
    endurance = stat(bearer, "endurance")
    if endurance is None:
        return 0
    return round_half_up(rules.world_effects.heir_hp + endurance * rules.healing.endurance_hp_pct / PERCENT)


def regenerate(rules: Rules, bearer: EntityRow, body: BodyRow, infected: bool) -> None:
    hp = stat(bearer, "hp")
    if hp is None:
        return
    body.hp_max = max(body.hp_max, hp, hp_ceiling(rules, bearer))
    if infected or hp >= body.hp_max:
        return
    gain = rules.healing.hp_regen_base + bearer_stats(bearer).endurance / rules.healing.endurance_div
    set_stats(bearer, hp=min(body.hp_max, round_half_up(hp + gain)))


async def heal_wounds(ctx: TickContext) -> None:
    world = await HealingWorld.load(ctx.session, ctx.rules)
    list(await ctx.session.scalars(select(BodyRow)))
    bearers: list[Bearer] = [*await canon(ctx.session, [EntityType.MORTAL, EntityType.BEAST, EntityType.COSMIC_BEING, EntityType.OUTER_BEING])]
    bearers.extend(await ctx.session.scalars(select(SonRow)))
    bearers.extend(await ctx.session.scalars(select(ForeignGodRow)))
    open_bearers = set(await ctx.session.scalars(select(InjuryRow.bearer_node_id).where(InjuryRow.state.in_(OPEN_INJURY_STATES))))
    for bearer in bearers:
        outcome = await tend(ctx, bearer, world) if bearer.id in open_bearers else Tending()
        if outcome.died:
            ctx.count("festered")
            continue
        if isinstance(bearer, EntityRow) and not held(bearer.id):
            body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
            open_rows = await injuries_of(ctx.session, bearer.id) if bearer.id in open_bearers else []
            infected = any(row.state is InjuryState.INFECTED for row in open_rows)
            regenerate(ctx.rules, bearer, body, infected)
            regain_blood(ctx.rules, body, any(row.bleeding > 0 and row.state in OPEN_INJURY_STATES for row in open_rows))
        if outcome.changed:
            ctx.count("tended")
            await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)


async def mend(ctx: TickContext, bearer: Bearer, *, lasting: bool = False, healer_id: int | None = None) -> int:
    table = ctx.rules.healing
    mended = 0
    body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
    for row in await injuries_of(ctx.session, bearer.id):
        opened = row.state in OPEN_INJURY_STATES
        restorable = lasting and row.state is InjuryState.PERMANENT and row.kind not in MARK_KINDS
        if not opened and not restorable:
            continue
        if row.part in COUNTED_PARTS and row.kind is InjuryKind.SEVERED and lasting:
            if row.part in DIGIT_LIMBS:
                restore(body, row.part, row.digits)
            else:
                setattr(body, COUNTED_PARTS[row.part], full_counts(body)[row.part])
        if restorable and row.kind in TOTAL_LOSS_KINDS:
            row.kind = InjuryKind.DEEP_CUT
        row.state = InjuryState.HEALED_SCAR
        row.function_loss = round_half_up(row.function_loss * table.scar_residual_pct / PERCENT) if not lasting and row.kind not in CLEAN_HEALING_KINDS else 0
        row.visible = row.visible and row.kind not in CLEAN_HEALING_KINDS
        row.infected_epochs = 0
        row.healed_epoch = ctx.epoch
        row.treated_by_node_id = healer_id or row.treated_by_node_id
        mended += 1
    if mended:
        await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
    return mended


async def restore_body_senses(ctx: TickContext, bearer: Bearer) -> int:
    ended = 0
    for kind in SENSE_CONDITIONS:
        if await end_condition(ctx, bearer, kind):
            ended += 1
    return ended
