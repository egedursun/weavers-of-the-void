from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import FINGER_COUNT, FINGERS, SIGHT_PARTS, Part
from aerona.catalog.mind import HEALING_SKILLS
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow, InjuryRow, ProsthesisRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import (
    MADNESS_CONDITIONS,
    MEDICINE_ORDER,
    OPEN_INJURY_STATES,
    BodyRegion,
    ConditionKind,
    HarmCause,
    InjuryKind,
    InjuryState,
    MedicineTier,
)
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mortal import HarshnessScale
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.body.book import Bearer, anatomy_for, bearer_stats, ensure_body, injuries_of, prostheses_of
from aerona.engine.body.conditions import end_condition, gain_condition
from aerona.engine.body.hits import MARK_KINDS, PERMANENT_KINDS, TOTAL_LOSS_KINDS
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.disease.book import hospital_regions
from aerona.engine.disease.load import DiseaseLoads
from aerona.engine.gods.queries import community_of
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.lifecycle.mortal_death import die
from aerona.engine.lore.research import lacks
from aerona.engine.mind.hooks import failed_to_heal, healed
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.harshness import harshness
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, connect, directed_bond
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from aerona.rules.registry.body import HealingRules, ProstheticsRules

HEALER_ROLES = frozenset({MortalRole.HEALER, MortalRole.PRIEST, MortalRole.SAINT})
FESTER_DEATH = "died of a festering wound"
PRECIOUS = frozenset({MaterialKind.SILVER, MaterialKind.GOLD, MaterialKind.STAR_METAL, MaterialKind.CRYSTAL, MaterialKind.DRAGONBONE, MaterialKind.SKYSTEEL})


def tier_of(rules: HealingRules, medicine: int, magic: int, biomancy: bool) -> MedicineTier:
    if biomancy or medicine >= rules.reattachment_level or magic >= rules.magic_reattachment_level:
        return MedicineTier.REATTACHMENT
    if medicine >= rules.prosthetics_level:
        return MedicineTier.PROSTHETICS
    if medicine >= rules.surgery_level:
        return MedicineTier.SURGERY
    if medicine >= rules.herbs_level:
        return MedicineTier.HERBS
    return MedicineTier.NONE


async def known_tier(session: AsyncSession, holder_id: int | None, tier: MedicineTier) -> MedicineTier:
    if tier is MedicineTier.NONE or tier_index(tier) > tier_index(MedicineTier.SURGERY):
        return tier
    if await lacks(session, holder_id, Technique.HERBALISM):
        return MedicineTier.NONE
    if tier is MedicineTier.SURGERY and await lacks(session, holder_id, Technique.SURGERY):
        return MedicineTier.HERBS
    return tier


def tier_index(tier: MedicineTier) -> int:
    return MEDICINE_ORDER.index(tier)


def infection_base(rules: HealingRules, kind: InjuryKind) -> int:
    table = {
        InjuryKind.CUT: rules.infection_cut,
        InjuryKind.DEEP_CUT: rules.infection_deep_cut,
        InjuryKind.PUNCTURE: rules.infection_puncture,
        InjuryKind.BITE: rules.infection_bite,
        InjuryKind.BURN: rules.infection_burn,
        InjuryKind.SEVERED: rules.infection_severed,
        InjuryKind.GOUGED: rules.infection_gouged,
        InjuryKind.CRUSH: rules.infection_crush,
        InjuryKind.FROSTBITE: rules.infection_frostbite,
    }
    return table.get(kind, rules.infection_other)


def permanent_chance(rules: HealingRules, kind: InjuryKind) -> int:
    table = {
        InjuryKind.FRACTURE: rules.permanent_fracture,
        InjuryKind.CRUSH: rules.permanent_crush,
        InjuryKind.DEEP_CUT: rules.permanent_deep_cut,
        InjuryKind.BURN: rules.permanent_burn,
        InjuryKind.FROSTBITE: rules.permanent_frostbite,
        InjuryKind.VENOM: rules.permanent_venom,
        InjuryKind.CURSE_WITHER: rules.permanent_wither,
    }
    return table.get(kind, rules.permanent_other)


def heal_chance(rules: HealingRules, severity: int, kind: InjuryKind) -> float:
    by_severity = (rules.heal_severity_1, rules.heal_severity_2, rules.heal_severity_3, rules.heal_severity_4, rules.heal_severity_5)[severity - 1]
    by_kind = {
        InjuryKind.BRUISE: rules.heal_bruise_pct,
        InjuryKind.CUT: rules.heal_cut_pct,
        InjuryKind.DEEP_CUT: rules.heal_deep_cut_pct,
        InjuryKind.PUNCTURE: rules.heal_puncture_pct,
        InjuryKind.FRACTURE: rules.heal_fracture_pct,
        InjuryKind.CRUSH: rules.heal_crush_pct,
        InjuryKind.BURN: rules.heal_burn_pct,
        InjuryKind.FROSTBITE: rules.heal_frostbite_pct,
        InjuryKind.BITE: rules.heal_bite_pct,
        InjuryKind.VENOM: rules.heal_venom_pct,
        InjuryKind.CURSE_WITHER: rules.heal_curse_wither_pct,
    }.get(kind, PERCENT)
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


def medicine_cut(rules: HealingRules, tier: MedicineTier) -> int:
    if tier is MedicineTier.NONE:
        return 0
    return rules.herbs_infection_cut_pct if tier is MedicineTier.HERBS else rules.surgery_infection_cut_pct


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


@dataclass
class HealingWorld:
    rules: Rules
    atlas: RegionAtlas
    knowledge: KnowledgeMap
    healers: dict[int | None, list[Healer]]
    disease: dict[int, int]
    artisans: dict[int | None, list[EntityRow]]

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "HealingWorld":
        atlas = await RegionAtlas.load(session)
        knowledge = await KnowledgeMap.load(session)
        healers: dict[int | None, list[Healer]] = defaultdict(list)
        artisans: dict[int | None, list[EntityRow]] = defaultdict(list)
        trained: dict[int, int] = defaultdict(int)
        hospitals = await hospital_regions(session, atlas)
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
            ward = rules.epidemiology.hospital_healer_pct / PERCENT if region in hospitals else 1.0
            healers[region].append(Healer(mortal, clamp_int(raw * hands * ward, 0, PERCENT), region))
        disease = dict((await DiseaseLoads.load(session)).regions)
        return cls(rules=rules, atlas=atlas, knowledge=knowledge, healers=healers, disease=disease, artisans=artisans)

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
        return Care(tier, healer, disease, metallurgy, artisan, amputation=not await lacks(session, home, Technique.AMPUTATION))


async def _renown(ctx: TickContext, healer: Healer | None, *, healed: bool) -> None:
    if healer is None:
        return
    body = await ensure_body(ctx.session, ctx.rules, healer.mortal, ctx.epoch)
    table = ctx.rules.healing
    if healed:
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


async def _fester(ctx: TickContext, bearer: Bearer, body: BodyRow, row: InjuryRow, *, care: Care, rng_key: str) -> Tending:
    table = ctx.rules.healing
    rng = ctx.rng(seed_of("fester", rng_key))
    row.infected_epochs += 1
    part = _part(body, row)
    vital = part is not None and part.vital
    index = tier_index(care.tier)
    deadly = (table.lethal_infected_vital if vital else table.lethal_infected_limb) * max(0, PERCENT - index * table.lethal_medicine_cut_pct) / PERCENT
    deadly *= harshness(ctx.rules, HarshnessScale.INFECTION)
    if row.infected_epochs >= table.lethal_after_epochs or rng.chance(deadly):
        if index >= tier_index(MedicineTier.SURGERY) and care.amputation and _limb(part) and rng.chance(table.amputation_chance):
            row.kind, row.function_loss, row.state, row.infected_epochs = InjuryKind.SEVERED, PERCENT, InjuryState.HEALING, 0
            if row.part == FINGERS:
                body.fingers = 0
            await _treated(ctx, bearer, row, care.healer)
            if care.healer is not None:
                await healed(ctx, care.healer.mortal.id, bearer.id, saved=True)
            if isinstance(bearer, EntityRow):
                await note(
                    ctx,
                    f"{bearer.name} lost a festering {part.label.lower() if part else row.part} to the surgeon's saw and lived.",
                    key="healing.amputated",
                    ids=[bearer.id],
                )
            return Tending(changed=True)
        row.state = InjuryState.LETHAL
        await _renown(ctx, care.healer, healed=False)
        if care.healer is not None and isinstance(bearer, EntityRow):
            await failed_to_heal(ctx, care.healer.mortal.id, bearer)
        if isinstance(bearer, EntityRow) and bearer.entity_type is EntityType.BEAST:
            await retire_in(ctx, bearer, FESTER_DEATH)
            return Tending(died=True, changed=True)
        if isinstance(bearer, EntityRow):
            await die(ctx, bearer, cause=FESTER_DEATH, event_id=row.event_entity_id)
            return Tending(died=True, changed=True)
        row.state = InjuryState.PERMANENT
        return Tending(changed=True)
    skill = care.healer.skill if care.healer is not None else 0
    clear = table.infection_clear * (1 + index * table.infection_clear_medicine_pct / PERCENT) * (1 + skill / PERCENT)
    if rng.chance(clear):
        row.state = InjuryState.HEALING
        await _treated(ctx, bearer, row, care.healer)
        return Tending(changed=True)
    return Tending()


async def _close(ctx: TickContext, bearer: Bearer, row: InjuryRow, care: Care, rng_key: str) -> None:
    table = ctx.rules.healing
    rng = ctx.rng(seed_of("scar", rng_key))
    lasting = row.kind in PERMANENT_KINDS or rng.chance(lasting_chance(table, row.kind, row.severity) * harshness(ctx.rules, HarshnessScale.PERMANENT_INJURY))
    if lasting:
        row.state = InjuryState.PERMANENT
        if row.kind not in TOTAL_LOSS_KINDS:
            row.function_loss = round_half_up(row.function_loss * table.permanent_residual_pct / PERCENT)
    else:
        row.state = InjuryState.HEALED_SCAR
        row.function_loss = round_half_up(row.function_loss * table.scar_residual_pct / PERCENT)
        row.visible = row.visible and row.severity >= table.scar_visible_severity
    row.healed_epoch = ctx.epoch
    await _treated(ctx, bearer, row, care.healer)
    await _renown(ctx, care.healer, healed=True)
    if care.healer is not None:
        await healed(ctx, care.healer.mortal.id, bearer.id, saved=row.severity >= table.saved_severity)
    if lasting and row.kind is InjuryKind.CURSE_WITHER and row.severity >= ctx.rules.conditions.wither_condition_severity:
        await gain_condition(ctx, bearer, ConditionKind.WITHERED_LIMB, row.cause_kind, severity=row.severity, part=row.part, source_node_id=row.cause_node_id)
    if lasting and row.kind is InjuryKind.VENOM:
        await gain_condition(ctx, bearer, ConditionKind.CHRONIC_ILLNESS, row.cause_kind, severity=row.severity, source_node_id=row.cause_node_id)


HEALING_KEY = "healing"


async def tend(ctx: TickContext, bearer: Bearer, world: HealingWorld) -> Tending:
    if blocked(bearer.id, HEALING_KEY):
        return Tending()
    body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
    anatomy = anatomy_for(body)
    table = ctx.rules.healing
    care = await world.care_for(ctx.session, bearer)
    stats = bearer_stats(bearer)
    divine = isinstance(bearer, SonRow | ForeignGodRow)
    outcome = Tending()
    for row in await injuries_of(ctx.session, bearer.id):
        if row.state not in OPEN_INJURY_STATES:
            continue
        key = f"{bearer.id}.{row.id}.{ctx.epoch}"
        rng = ctx.rng(seed_of("heal", key))
        campaign = row.cause_kind is HarmCause.BATTLE and row.epoch == ctx.epoch
        skill = care.healer.skill if care.healer is not None else 0
        if row.state is not InjuryState.INFECTED and anatomy.infects:
            chance = infection_base(table, row.kind) * care.disease / table.disease_reference
            chance *= harshness(ctx.rules, HarshnessScale.INFECTION) * (1 + (PERCENT - body.vital) * table.vital_infection_pct / PERCENT / PERCENT)
            chance *= (PERCENT - medicine_cut(table, care.tier)) / PERCENT * (PERCENT - min(table.healer_skill_cap, skill)) / PERCENT
            checks = max(1, ctx.rules.campaigns.seasons_per_war_epoch) if campaign else 1
            if any(rng.chance(chance) for _ in range(checks)):
                row.state = InjuryState.INFECTED
                outcome.changed = True
        if row.state is InjuryState.INFECTED:
            result = await _fester(ctx, bearer, body, row, care=care, rng_key=key)
            outcome.changed = outcome.changed or result.changed
            if result.died:
                outcome.died = True
                return outcome
            continue
        if not anatomy.heals:
            continue
        chance = heal_chance(table, row.severity, row.kind) * (1 + stats.endurance / PERCENT)
        chance *= table.campaign_rest_pct / PERCENT if campaign else 1
        chance *= 1 + table.healer_heal_bonus_pct * skill / PERCENT / PERCENT
        chance *= 1 + table.divine_heal_bonus_pct / PERCENT if divine else 1
        if rng.chance(chance):
            await _close(ctx, bearer, row, care, key)
            outcome.changed = True
        elif row.state is InjuryState.FRESH:
            row.state = InjuryState.HEALING
            outcome.changed = True
    if isinstance(bearer, EntityRow):
        outcome.changed = await _restore(ctx, bearer, body, care) or outcome.changed
    return outcome


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
            if row.part == FINGERS:
                body.fingers = FINGER_COUNT
            await _treated(ctx, bearer, row, care.healer)
            await note(
                ctx,
                f"{bearer.name}'s lost {part.label.lower()} was made whole again by {care.healer.mortal.name}.",
                key="healing.reattached",
                ids=[bearer.id, care.healer.mortal.id],
            )
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
        return MaterialKind.SILVER if metallurgy >= rules.metal_level else MaterialKind.BONE
    return MaterialKind.IRON if metallurgy >= rules.metal_level else MaterialKind.WOOD


def workability(rules: ProstheticsRules, material: MaterialKind) -> int:
    table = {
        MaterialKind.WOOD: rules.wood,
        MaterialKind.BONE: rules.bone,
        MaterialKind.IVORY: rules.ivory,
        MaterialKind.COPPER: rules.copper,
        MaterialKind.BRONZE: rules.bronze,
        MaterialKind.IRON: rules.iron,
        MaterialKind.STEEL: rules.steel,
        MaterialKind.SILVER: rules.silver,
        MaterialKind.GOLD: rules.gold,
        MaterialKind.GLASS: rules.glass,
        MaterialKind.CRYSTAL: rules.crystal,
        MaterialKind.STAR_METAL: rules.star_metal,
        MaterialKind.LIVING_WOOD: rules.living_wood,
        MaterialKind.DRAGONBONE: rules.dragonbone,
        MaterialKind.SKYSTEEL: rules.skysteel,
    }
    return table.get(material, rules.other)


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
) -> ProsthesisRow:
    table = ctx.rules.prosthetics
    if maker is not None and await lacks(ctx.session, maker.location_id, Technique.PROSTHETICS):
        quality = min(quality if quality is not None else table.default_quality, table.default_quality // 2)
    if quality is None:
        quality = (
            clamp_int(
                (stat(maker, "intellect") or table.default_quality) * table.maker_intellect_pct / PERCENT
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
    restored = clamp_int(workability(table, material) * quality / PERCENT, 0, PERCENT)
    relic = material in PRECIOUS and quality >= table.relic_quality
    if item is None:
        made = material.value.replace("_", " ")
        item = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.ITEM,
                name=f"The {made.title()} {part.label.split()[-1].title()} of {bearer.name}" if relic else f"{made.capitalize()} {part.label.lower()}",
                body=f"A {made} {part.label.lower()} made for {bearer.name}.",
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
        epoch=ctx.epoch,
    )
    ctx.session.add(prosthesis)
    await ctx.session.flush()
    maker_text = f" made by {maker.name}" if maker is not None else ""
    await note(
        ctx,
        f"{bearer.name} was fitted with a {material.value.replace('_', ' ')} {part.label.lower()}{maker_text}.",
        key="healing.prosthesis",
        ids=[bearer.id, *([item.id] if item else [])],
    )
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
    row.material = material.value
    row.quality = quality
    row.value = quality
    row.renown = quality if relic else row.renown or 0
    row.symbol = relic
    row.maker_entity_id = maker.id if maker is not None else row.maker_entity_id
    row.updated_epoch = ctx.epoch
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
    bearers: list[Bearer] = [*await canon(ctx.session, [EntityType.MORTAL, EntityType.BEAST])]
    bearers.extend(await ctx.session.scalars(select(SonRow)))
    bearers.extend(await ctx.session.scalars(select(ForeignGodRow)))
    open_bearers = set(await ctx.session.scalars(select(InjuryRow.bearer_node_id).where(InjuryRow.state.in_(OPEN_INJURY_STATES))))
    for bearer in bearers:
        outcome = await tend(ctx, bearer, world) if bearer.id in open_bearers else Tending()
        if outcome.died:
            ctx.count("festered")
            continue
        if isinstance(bearer, EntityRow):
            body = await ensure_body(ctx.session, ctx.rules, bearer, ctx.epoch)
            infected = bearer.id in open_bearers and any(row.state is InjuryState.INFECTED for row in await injuries_of(ctx.session, bearer.id))
            regenerate(ctx.rules, bearer, body, infected)
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
        if row.part == FINGERS and row.kind is InjuryKind.SEVERED and lasting:
            body.fingers = FINGER_COUNT
        if restorable and row.kind in TOTAL_LOSS_KINDS:
            row.kind = InjuryKind.DEEP_CUT
        row.state = InjuryState.HEALED_SCAR
        row.function_loss = round_half_up(row.function_loss * table.scar_residual_pct / PERCENT) if not lasting else 0
        row.infected_epochs = 0
        row.healed_epoch = ctx.epoch
        row.treated_by_node_id = healer_id or row.treated_by_node_id
        mended += 1
    if mended:
        await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
    return mended


SENSE_CONDITIONS = (ConditionKind.AGE_BLINDNESS, ConditionKind.AGE_DEAFNESS, *MADNESS_CONDITIONS)


async def restore_body_senses(ctx: TickContext, bearer: Bearer) -> int:
    ended = 0
    for kind in SENSE_CONDITIONS:
        if await end_condition(ctx, bearer, kind):
            ended += 1
    return ended
