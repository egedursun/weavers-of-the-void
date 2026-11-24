from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, select

from aerona.catalog.kinds.crafts_labels import CLEANSING_FURNISHINGS, WORKING_WEAR
from aerona.catalog.life_traits import FURNISHING_CATEGORY_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.collective import ArmsRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.crafts import GameRow
from aerona.db.tables.customs import AgeSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import PurityRankRow
from aerona.db.tables.kind_crafts import (
    ColourMeaningRow,
    ColourTermRow,
    EmblemSystemRow,
    FurnishingKindRow,
    GarmentKindRow,
    InstrumentKindRow,
    MusicTraditionRow,
    ScentKindRow,
    SubstanceKindRow,
    ToolKindRow,
)
from aerona.db.tables.kinds import KindHoldingRow, KindRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.kind_crafts import ColourMeaning, EmblemSystem, FurnishingCategory, GarmentCategory, ToolCategory
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.domain.enums.life_traits import FurnishingCategoryTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.kinds.acts import HOLDINGS
from aerona.engine.lore.civics import holders_know
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import count_communities
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import realm_of_town
from aerona.rules.registry import Rules

CARRIED = (KindStance.MAKES, KindStance.USES, KindStance.FAVOURS)
PROFILE_COLUMNS = ("unrest", "crime", "prestige", "sanitation", "fire_risk", "public_order")


@dataclass
class TownShift:
    unrest: float = 0.0
    crime: float = 0.0
    prestige: float = 0.0
    sanitation: float = 0.0
    fire_risk: float = 0.0
    public_order: float = 0.0
    prosperity: float = 0.0
    treasury: float = 0.0

    def add(self, other: "TownShift") -> None:
        for name in vars(self):
            setattr(self, name, getattr(self, name) + getattr(other, name))


@dataclass
class CraftTally:
    towns: int = 0
    restricted: int = 0
    smuggled: int = 0
    repealed: int = 0
    forbidden_use: int = 0
    fine_dress: int = 0
    revived: int = 0
    arms_linked: int = 0
    worn: int = 0
    meanings: int = 0


@dataclass(frozen=True)
class Exposure:
    dressed: bool = False
    warmth: int = 0
    wear: int = 0
    violence: int = 0


FURNISHING_SANITATION = CLEANSING_FURNISHINGS
FURNISHING_PLAY = frozenset({FurnishingCategory.PLAY})
GARMENT_WORK = WORKING_WEAR
GARMENT_REST = frozenset({GarmentCategory.SLEEPWEAR})
FURNISHING_FIRE = having(FURNISHING_CATEGORY_TRAITS, FurnishingCategoryTrait.FURNISHING_FIRE)
TOOL_SANITATION = frozenset({ToolCategory.MEDICAL})
TOOL_FIRE = frozenset({ToolCategory.FIRE_MAKING})


def garment_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.dress
    return TownShift(
        prestige=kind.prestige * kind.status_signal / PERCENT * weight * table.prestige_pct / PERCENT,
        prosperity=weight * table.work_wear_prosperity if kind.category in GARMENT_WORK else 0.0,
        unrest=-weight * table.rest_wear_calm if kind.category in GARMENT_REST else 0.0,
    )


def colour_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    return TownShift(prestige=kind.prestige * weight * rules.dress.prestige_pct / PERCENT)


def scent_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.scents
    return TownShift(
        prestige=kind.prestige * weight * table.prestige_pct / PERCENT,
        unrest=-kind.rite_weight * weight * table.rite_calm_pct / PERCENT,
        treasury=kind.trade_value * weight * table.trade_pct / PERCENT,
    )


def emblem_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.household_goods
    return TownShift(public_order=kind.legibility * weight * table.emblem_order_pct / PERCENT, prestige=kind.prestige * weight * table.prestige_pct / PERCENT)


def furnishing_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.household_goods
    comfort = kind.comfort * weight
    return TownShift(
        unrest=-comfort * table.comfort_calm_pct / PERCENT,
        prestige=kind.prestige * weight * table.prestige_pct / PERCENT,
        sanitation=comfort * table.sanitation_pct / PERCENT if kind.category in FURNISHING_SANITATION else 0.0,
        fire_risk=comfort * table.fire_pct / PERCENT if kind.category in FURNISHING_FIRE else 0.0,
        prosperity=comfort * table.play_skill_pct / PERCENT if kind.category in FURNISHING_PLAY else 0.0,
    )


def tool_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.household_goods
    quality = kind.quality * weight
    return TownShift(
        prosperity=kind.craft_bonus * quality / PERCENT * table.craft_pct / PERCENT,
        sanitation=quality * table.sanitation_pct / PERCENT if kind.category in TOOL_SANITATION else 0.0,
        fire_risk=-quality * table.fire_pct / PERCENT if kind.category in TOOL_FIRE else 0.0,
    )


def instrument_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    return TownShift(
        unrest=-kind.loudness * weight * rules.music.loud_pct / PERCENT,
        prestige=kind.prestige * weight * rules.household_goods.prestige_pct / PERCENT,
    )


def music_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.music
    return TownShift(
        unrest=-(kind.rite_weight * table.rite_calm_pct / PERCENT + kind.ensemble_size // 10 * table.ensemble_calm) * weight,
        prestige=kind.prestige * weight * rules.household_goods.prestige_pct / PERCENT,
    )


def substance_shift(rules: Rules, kind: Any, weight: float) -> TownShift:
    table = rules.substances
    return TownShift(
        crime=kind.dependence * kind.potency / PERCENT * weight * table.crime_pct / PERCENT,
        sanitation=-kind.harm * weight * table.harm_pct / PERCENT,
        unrest=-kind.rite_weight * weight * table.rite_calm_pct / PERCENT,
        treasury=kind.trade_value * weight * table.trade_pct / PERCENT,
    )


Shift = Callable[[Rules, Any, float], TownShift]
EFFECTS: Mapping[KindConcept, tuple[type[KindRow], Shift]] = {
    KindConcept.GARMENT: (GarmentKindRow, garment_shift),
    KindConcept.COLOUR_TERM: (ColourTermRow, colour_shift),
    KindConcept.SCENT: (ScentKindRow, scent_shift),
    KindConcept.EMBLEM_SYSTEM: (EmblemSystemRow, emblem_shift),
    KindConcept.FURNISHING: (FurnishingKindRow, furnishing_shift),
    KindConcept.TOOL: (ToolKindRow, tool_shift),
    KindConcept.INSTRUMENT: (InstrumentKindRow, instrument_shift),
    KindConcept.MUSIC_TRADITION: (MusicTraditionRow, music_shift),
    KindConcept.SUBSTANCE: (SubstanceKindRow, substance_shift),
}
MAKERS_ONLY_TREASURY = total(
    KindStance,
    {KindStance.MAKES: True, KindStance.USES: False, KindStance.FAVOURS: False, KindStance.FORBIDS: False, KindStance.BLESSES: False},
)


@dataclass
class Held:
    holding: KindHoldingRow
    kind: Any


@dataclass
class HolderKinds:
    by_concept: dict[KindConcept, list[Held]] = field(default_factory=dict)


async def holdings_by_holder(ctx: TickContext, concepts: tuple[KindConcept, ...]) -> dict[int, HolderKinds]:
    found: dict[int, HolderKinds] = {}
    rows = await ctx.session.scalars(
        select(KindHoldingRow).where(KindHoldingRow.concept.in_(list(concepts)), KindHoldingRow.stance.in_(list(CARRIED))).order_by(KindHoldingRow.id)
    )
    for row in list(rows):
        table = EFFECTS[row.concept][0] if row.concept in EFFECTS else GameRow
        kind = await ctx.session.get(table, row.kind_id)
        if kind is None or kind.retired:
            continue
        found.setdefault(row.holder_node_id, HolderKinds()).by_concept.setdefault(row.concept, []).append(Held(row, kind))
    return found


def shift_of(ctx: TickContext, kinds: HolderKinds) -> TownShift:
    total_shift = TownShift()
    for concept, items in kinds.by_concept.items():
        if concept not in EFFECTS:
            continue
        effect = EFFECTS[concept][1]
        for item in items:
            part = effect(ctx.rules, item.kind, item.holding.strength / PERCENT)
            if not MAKERS_ONLY_TREASURY[item.holding.stance]:
                part.treasury = 0.0
            total_shift.add(part)
    return total_shift


def apply_shift(town: EntityRow, profile: SettlementProfileRow | None, shift: TownShift) -> None:
    if shift.prosperity:
        shift_stat(town, "prosperity", shift.prosperity, low=0, high=PERCENT)
    if profile is None:
        return
    for column in PROFILE_COLUMNS:
        delta = round_half_up(getattr(shift, column))
        if delta and column not in profile.locked:
            setattr(profile, column, clamp_int(getattr(profile, column) + delta, 0, PERCENT))
    gain = round_half_up(shift.treasury)
    if gain and "treasury" not in profile.locked:
        profile.treasury = max(0, profile.treasury + gain)


async def live_towns(ctx: TickContext, holder_id: int) -> list[EntityRow]:
    towns: list[EntityRow] = []
    for town_id in await towns_of_people(ctx.session, holder_id):
        town = await ctx.session.get(EntityRow, town_id)
        if town is not None and not held(town_id):
            towns.append(town)
    return towns


async def forbidden_by_realm(ctx: TickContext, town_id: int, concept: KindConcept, kind_id: int) -> int | None:
    realm = await realm_of_town(ctx.session, town_id)
    if realm is None:
        return None
    found = await ctx.session.scalar(
        select(KindHoldingRow.id).where(
            KindHoldingRow.concept == concept,
            KindHoldingRow.kind_id == kind_id,
            KindHoldingRow.holder_node_id == realm,
            KindHoldingRow.stance == KindStance.FORBIDS,
        )
    )
    return realm if found is not None else None


async def restraints(ctx: TickContext, town: EntityRow, kinds: HolderKinds, tally: CraftTally) -> TownShift:
    shift = TownShift()
    garments = kinds.by_concept.get(KindConcept.GARMENT, [])
    sumptuary = bool(garments) and await law_param(ctx.session, town.id, LawKind.SUMPTUARY, "merchant_luxury") is not None
    for item in garments:
        if sumptuary and item.kind.status_signal >= ctx.rules.dress.signal_floor:
            shift.crime += ctx.rules.dress.sumptuary_crime * item.holding.strength / PERCENT
            tally.fine_dress += 1
    for item in kinds.by_concept.get(KindConcept.SUBSTANCE, []):
        if await forbidden_by_realm(ctx, town.id, KindConcept.SUBSTANCE, item.kind.id) is not None:
            shift.crime += ctx.rules.substances.forbidden_crime * item.holding.strength / PERCENT
            tally.forbidden_use += 1
    for item in kinds.by_concept.get(KindConcept.COLOUR_TERM, []):
        if await forbidden_by_realm(ctx, town.id, KindConcept.COLOUR_TERM, item.kind.id) is not None:
            weight = item.holding.strength / PERCENT
            shift.crime += ctx.rules.colours.smuggling_crime * weight
            shift.unrest += ctx.rules.colours.restriction_unrest * weight
            tally.smuggled += 1
    return shift


def colour_prestige(ctx: TickContext, colour: ColourTermRow) -> None:
    if "prestige" in colour.locked:
        return
    colour.prestige = clamp_int(colour.rarity * ctx.rules.colours.rarity_prestige_pct // PERCENT, 0, PERCENT)


async def restrict_colour(ctx: TickContext, realm_id: int, colour: ColourTermRow, tally: CraftTally) -> None:
    if held(realm_id):
        return
    ctx.session.add(
        KindHoldingRow(
            concept=KindConcept.COLOUR_TERM,
            kind_id=colour.id,
            holder_node_id=realm_id,
            stance=KindStance.FORBIDS,
            strength=PERCENT,
            spread=KindSpread.DECREE,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    meaning = await ctx.session.scalar(
        select(ColourMeaningRow).where(
            ColourMeaningRow.colour_term_id == colour.id, ColourMeaningRow.culture_node_id == realm_id, ColourMeaningRow.meaning == ColourMeaning.RANK
        )
    )
    if meaning is None:
        ctx.session.add(ColourMeaningRow(colour_term_id=colour.id, culture_node_id=realm_id, meaning=ColourMeaning.RANK, since_epoch=ctx.epoch, locked=[]))
    await ctx.session.flush()
    tally.restricted += 1
    await record(
        ctx,
        "colours.restricted",
        roles={IncidentRole.AUTHORITY: realm_id},
        facts={"colour": colour.name, "category": colour.category},
        steps=(StepDraft(StepAction.DECREE, actor=realm_id),),
    )


async def repeal_colour(ctx: TickContext, realm_id: int, colour: ColourTermRow, tally: CraftTally) -> None:
    ctx.session.info.pop(HOLDINGS, None)
    await ctx.session.execute(
        delete(KindHoldingRow).where(
            KindHoldingRow.concept == KindConcept.COLOUR_TERM,
            KindHoldingRow.kind_id == colour.id,
            KindHoldingRow.holder_node_id == realm_id,
            KindHoldingRow.stance == KindStance.FORBIDS,
        )
    )
    await ctx.session.execute(
        delete(ColourMeaningRow).where(
            ColourMeaningRow.colour_term_id == colour.id, ColourMeaningRow.culture_node_id == realm_id, ColourMeaningRow.meaning == ColourMeaning.RANK
        )
    )
    tally.repealed += 1
    await record(
        ctx,
        "colours.repealed",
        roles={IncidentRole.AUTHORITY: realm_id},
        facts={"colour": colour.name, "category": colour.category},
        steps=(StepDraft(StepAction.REFUSE, target=realm_id, outcome=StepOutcome.REVERSED),),
    )


async def colour_laws(ctx: TickContext, holders: dict[int, HolderKinds], tally: CraftTally) -> None:
    for colour in list(await ctx.session.scalars(select(ColourTermRow).where(ColourTermRow.retired.is_(False)).order_by(ColourTermRow.id))):
        colour_prestige(ctx, colour)
    for holder_id, kinds in holders.items():
        if held(holder_id):
            continue
        for item in kinds.by_concept.get(KindConcept.COLOUR_TERM, []):
            for town in await live_towns(ctx, holder_id):
                realm = await realm_of_town(ctx.session, town.id)
                if realm is None or realm == holder_id:
                    continue
                forbidding = await forbidden_by_realm(ctx, town.id, KindConcept.COLOUR_TERM, item.kind.id)
                profile = await ctx.session.get(SettlementProfileRow, town.id)
                if forbidding is not None and profile is not None and profile.unrest >= ctx.rules.colours.repeal_unrest and not held(realm):
                    await repeal_colour(ctx, realm, item.kind, tally)
                elif forbidding is None and item.kind.prestige >= ctx.rules.colours.restrict_at:
                    await restrict_colour(ctx, realm, item.kind, tally)


async def meanings_of(ctx: TickContext, people_id: int) -> list[ColourMeaning]:
    found: list[ColourMeaning] = []
    if await holders_know(ctx.session, [people_id], Technique.HOSPITALS) or await holders_know(ctx.session, [people_id], Technique.HERBALISM):
        found.append(ColourMeaning.HEALTH)
    if await ctx.session.scalar(select(PurityRankRow.id).where(PurityRankRow.people_entity_id == people_id).limit(1)) is not None:
        found.append(ColourMeaning.PURITY)
    if await ctx.session.scalar(select(AgeSetRow.id).where(AgeSetRow.people_entity_id == people_id).limit(1)) is not None:
        found.append(ColourMeaning.LIFE_STAGE)
    return found


async def held_meanings(ctx: TickContext, holders: dict[int, HolderKinds]) -> int:
    written = 0
    for holder_id, kinds in sorted(holders.items()):
        colours = sorted(kinds.by_concept.get(KindConcept.COLOUR_TERM, []), key=lambda item: (-item.holding.strength, item.kind.id))
        if held(holder_id) or not colours:
            continue
        for index, meaning in enumerate(await meanings_of(ctx, holder_id)):
            colour = colours[index % len(colours)].kind
            present = await ctx.session.scalar(
                select(ColourMeaningRow.id).where(ColourMeaningRow.culture_node_id == holder_id, ColourMeaningRow.meaning == meaning).limit(1)
            )
            if present is not None:
                continue
            ctx.session.add(ColourMeaningRow(colour_term_id=colour.id, culture_node_id=holder_id, meaning=meaning, since_epoch=ctx.epoch, locked=[]))
            written += 1
    await ctx.session.flush()
    return written


async def garment_fashion(ctx: TickContext, tally: CraftTally) -> None:
    table = ctx.rules.fashion
    garments = list(await ctx.session.scalars(select(GarmentKindRow).where(GarmentKindRow.retired.is_(False)).order_by(GarmentKindRow.id)))
    everywhere = max(1, await count_communities(ctx.session) * table.saturation // PERCENT)
    for garment in garments:
        holdings = list(
            await ctx.session.scalars(
                select(KindHoldingRow).where(
                    KindHoldingRow.concept == KindConcept.GARMENT, KindHoldingRow.kind_id == garment.id, KindHoldingRow.stance.in_(list(CARRIED))
                )
            )
        )
        weight = garment.fashion / PERCENT
        if "novelty" not in garment.locked:
            adoption = clamp_int(len(holdings) * PERCENT // everywhere, 0, PERCENT)
            before = garment.novelty
            change = (table.recovery * (PERCENT - adoption) - table.drain * adoption) / PERCENT * weight
            garment.novelty = clamp_int(garment.novelty + round_half_up(change), 0, PERCENT)
            if before < table.revival_floor <= garment.novelty:
                tally.revived += 1
                await record(
                    ctx,
                    "dress.revival",
                    roles={IncidentRole.ORIGIN: garment.origin_node_id},
                    facts={"garment": garment.name, "novelty": garment.novelty, "adoption": adoption},
                )
        pull = (garment.novelty - PERCENT // 2) * weight * ctx.rules.dress.fashion_pull_pct / PERCENT
        for holding in holdings:
            if "strength" in holding.locked or held(holding.holder_node_id):
                continue
            holding.strength = clamp_int(holding.strength + round_half_up(pull), 0, PERCENT)
            tally.worn += 1


HERALDRY_FIXUP = "emblems.heraldry_system"


async def heraldry_system(ctx: TickContext) -> EmblemSystemRow | None:
    found = await ctx.session.scalar(
        select(EmblemSystemRow)
        .where(EmblemSystemRow.built_in.is_(True), EmblemSystemRow.category == EmblemSystem.HERALDRY)
        .order_by(EmblemSystemRow.id)
        .limit(1)
    )
    if found is not None or await ctx.session.get(AppliedFixupRow, HERALDRY_FIXUP) is not None:
        return found
    made = EmblemSystemRow(
        name="Heraldry",
        description="Arms borne on a shield: a field, its divisions and lines, charges, a rim, supporters, a crest and a motto.",
        category=EmblemSystem.HERALDRY,
        built_in=True,
        complexity=70,
        legibility=60,
        prestige=40,
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(made)
    await ctx.session.flush()
    ctx.session.add(AppliedFixupRow(key=HERALDRY_FIXUP, result={"emblem_system_id": made.id}))
    return made


async def link_arms(ctx: TickContext, tally: CraftTally) -> None:
    system = await heraldry_system(ctx)
    if system is None:
        return
    bearers: set[int] = set()
    for arms in list(await ctx.session.scalars(select(ArmsRow).order_by(ArmsRow.holder_entity_id))):
        if held(arms.holder_entity_id):
            continue
        if arms.emblem_system_id is None and "emblem_system_id" not in arms.locked:
            arms.emblem_system_id = system.id
            tally.arms_linked += 1
        if arms.emblem_system_id == system.id:
            bearers.add(arms.holder_entity_id)
    known = set(
        await ctx.session.scalars(
            select(KindHoldingRow.holder_node_id).where(KindHoldingRow.concept == KindConcept.EMBLEM_SYSTEM, KindHoldingRow.kind_id == system.id)
        )
    )
    for bearer in sorted(bearers - known):
        ctx.session.add(
            KindHoldingRow(
                concept=KindConcept.EMBLEM_SYSTEM,
                kind_id=system.id,
                holder_node_id=bearer,
                stance=KindStance.USES,
                strength=PERCENT // 2,
                spread=KindSpread.INVENTED,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
    await ctx.session.flush()


async def keep_crafts_of_life(ctx: TickContext) -> CraftTally:
    tally = CraftTally()
    await link_arms(ctx, tally)
    await garment_fashion(ctx, tally)
    holders = await holdings_by_holder(ctx, tuple(EFFECTS))
    await colour_laws(ctx, holders, tally)
    tally.meanings += await held_meanings(ctx, holders)
    for holder_id, kinds in holders.items():
        if held(holder_id):
            continue
        base = shift_of(ctx, kinds)
        for town in await live_towns(ctx, holder_id):
            shift = TownShift()
            shift.add(base)
            shift.add(await restraints(ctx, town, kinds, tally))
            apply_shift(town, await ctx.session.get(SettlementProfileRow, town.id), shift)
            tally.towns += 1
    await ctx.session.flush()
    return tally


async def exposure_of(ctx: TickContext, people_id: int) -> Exposure:
    rows = await ctx.session.execute(
        select(KindHoldingRow.concept, KindHoldingRow.kind_id, KindHoldingRow.strength).where(
            KindHoldingRow.holder_node_id == people_id,
            KindHoldingRow.concept.in_([KindConcept.GARMENT, KindConcept.TOOL, KindConcept.GAME]),
            KindHoldingRow.stance.in_(list(CARRIED)),
        )
    )
    warmth = wear = violence = 0
    dressed = False
    for concept, kind_id, strength in rows.all():
        if concept is KindConcept.GARMENT:
            garment = await ctx.session.get(GarmentKindRow, kind_id)
            dressed = dressed or garment is not None
            warmth = max(warmth, garment.warmth * strength // PERCENT if garment is not None and not garment.retired else 0)
        elif concept is KindConcept.TOOL:
            tool = await ctx.session.get(ToolKindRow, kind_id)
            wear = max(wear, tool.wear * strength // PERCENT if tool is not None and not tool.retired else 0)
        else:
            game = await ctx.session.get(GameRow, kind_id)
            violence = max(violence, game.violence * strength // PERCENT if game is not None and not game.retired else 0)
    return Exposure(dressed=dressed, warmth=warmth, wear=wear, violence=violence)


async def furnishing_worth(ctx: TickContext, people_id: int | None) -> int:
    if people_id is None:
        return 0
    rows = await ctx.session.execute(
        select(FurnishingKindRow.cost, KindHoldingRow.strength)
        .join(KindHoldingRow, KindHoldingRow.kind_id == FurnishingKindRow.id)
        .where(
            KindHoldingRow.concept == KindConcept.FURNISHING,
            KindHoldingRow.holder_node_id == people_id,
            KindHoldingRow.stance.in_(list(CARRIED)),
            FurnishingKindRow.retired.is_(False),
        )
    )
    return max((cost * strength // PERCENT for cost, strength in rows.all()), default=0)
