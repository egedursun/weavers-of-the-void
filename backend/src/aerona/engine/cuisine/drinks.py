from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.drink_roles import BONDING_ROLES, DRINK_ROLES
from aerona.catalog.life.cuisine import CATEGORY_WORDS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.food_kinds import DrinkKindRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kinds import DrinkCategory, DrinkRole, GoodLegality, KindConcept, KindSpread, KindStance
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holding
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.community_relations import change_relation

CARRIED = frozenset({KindStance.MAKES, KindStance.USES, KindStance.FAVOURS})
LEGAL_CRIME = total(
    GoodLegality,
    {GoodLegality.FREE: 1.0, GoodLegality.LICENSED: 1.0, GoodLegality.RESTRICTED: 1.5, GoodLegality.FORBIDDEN: 2.0},
)
D = DrinkCategory


@dataclass(frozen=True)
class DrinkStart:
    category: DrinkCategory
    water_safety: int
    strength: int
    stimulation: int
    nourishment: int
    keeps: int


STARTS = total(
    DrinkCategory,
    {
        D.WATER: DrinkStart(D.WATER, 0, 0, 0, 0, 0),
        D.INFUSION: DrinkStart(D.INFUSION, 50, 0, 20, 5, 1),
        D.FERMENTED: DrinkStart(D.FERMENTED, 40, 30, 0, 20, 2),
        D.DISTILLED: DrinkStart(D.DISTILLED, 60, 70, 0, 0, 10),
        D.PRESSED: DrinkStart(D.PRESSED, 10, 0, 5, 20, 0),
        D.MILK_BASED: DrinkStart(D.MILK_BASED, 20, 0, 0, 35, 1),
        D.BROTH: DrinkStart(D.BROTH, 50, 0, 0, 30, 0),
        D.STIMULANT_BREW: DrinkStart(D.STIMULANT_BREW, 45, 0, 50, 0, 1),
        D.INTOXICANT: DrinkStart(D.INTOXICANT, 30, 60, 0, 0, 3),
        D.MEDICINAL: DrinkStart(D.MEDICINAL, 40, 0, 10, 5, 2),
        D.RITUAL: DrinkStart(D.RITUAL, 30, 20, 10, 5, 2),
        D.SYNTHESISED: DrinkStart(D.SYNTHESISED, 80, 0, 10, 20, 8),
    },
)
FIRST_DRINKS: tuple[tuple[CommodityKind, DrinkCategory], ...] = (
    (CommodityKind.BREW_BASE, D.FERMENTED),
    (CommodityKind.MILK, D.MILK_BASED),
    (CommodityKind.HERBS, D.INFUSION),
    (CommodityKind.FRUIT, D.PRESSED),
)


@dataclass
class DrinkTally:
    founded: int = 0
    derived: int = 0
    shared: int = 0
    drunk: int = 0


async def holdings_of(session: AsyncSession, holder_id: int) -> list[tuple[KindHoldingRow, DrinkKindRow]]:
    rows = await session.execute(
        select(KindHoldingRow, DrinkKindRow)
        .join(DrinkKindRow, DrinkKindRow.id == KindHoldingRow.kind_id)
        .where(KindHoldingRow.concept == KindConcept.DRINK, KindHoldingRow.holder_node_id == holder_id, DrinkKindRow.retired.is_(False))
        .order_by(KindHoldingRow.id)
    )
    return [(holding_row, drink) for holding_row, drink in rows.all() if holding_row.stance in CARRIED]


async def drink_safety(session: AsyncSession) -> dict[int, int]:
    rows = await session.execute(
        select(KindHoldingRow.holder_node_id, KindHoldingRow.stance, DrinkKindRow.water_safety, DrinkKindRow.role)
        .join(DrinkKindRow, DrinkKindRow.id == KindHoldingRow.kind_id)
        .where(KindHoldingRow.concept == KindConcept.DRINK, DrinkKindRow.retired.is_(False))
    )
    safety: dict[int, int] = {}
    for holder_id, stance, value, _ in rows.all():
        if stance in CARRIED:
            safety[holder_id] = max(safety.get(holder_id, 0), value)
    peoples = await session.scalars(select(EntityRow).where(EntityRow.id.in_(sorted(safety)), EntityRow.entity_type == EntityType.PEOPLE))
    for people in list(peoples):
        for home in await homes_of(session, people):
            safety[home] = max(safety.get(home, 0), safety[people.id])
    return safety


async def found_drink(ctx: TickContext, people: EntityRow, category: DrinkCategory, *, parent: DrinkKindRow | None = None) -> DrinkKindRow:
    start = STARTS[category]
    drink = DrinkKindRow(
        name=await made_name(ctx.session, ctx.rules, people, CATEGORY_WORDS[category], "drink", ctx.epoch),
        category=category,
        world_id=people.world_id,
        origin_node_id=people.id,
        derived_from_id=parent.id if parent is not None else None,
        role=parent.role if parent is not None else DrinkRole.DAILY,
        strength=parent.strength if parent is not None else start.strength,
        stimulation=parent.stimulation if parent is not None else start.stimulation,
        nourishment=parent.nourishment if parent is not None else start.nourishment,
        water_safety=parent.water_safety if parent is not None else start.water_safety,
        keeps=parent.keeps if parent is not None else start.keeps,
        prestige=clamp_int((parent.prestige if parent is not None else 10) + 5, 0, PERCENT),
        dependence=parent.dependence if parent is not None else start.strength // 3,
        built_in=False,
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
    )
    ctx.session.add(drink)
    await ctx.session.flush()
    spread = KindSpread.INVENTED if parent is None else KindSpread.CONTACT
    ctx.session.add(
        KindHoldingRow(
            concept=KindConcept.DRINK,
            kind_id=drink.id,
            holder_node_id=people.id,
            stance=KindStance.MAKES,
            strength=60,
            spread=spread,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    return drink


async def first_drink(ctx: TickContext, people: EntityRow, tally: DrinkTally) -> None:
    if await ctx.session.scalar(select(DrinkKindRow.id).where(DrinkKindRow.origin_node_id == people.id).limit(1)) is not None:
        return
    homes = await homes_of(ctx.session, people)
    for good, category in FIRST_DRINKS:
        if sum([await holding(ctx.session, home, good) for home in sorted(homes)]) > 0:
            drink = await found_drink(ctx, people, category)
            tally.founded += 1
            await record(
                ctx,
                "drink.founded",
                roles={IncidentRole.MAKER: people.id},
                facts={"drink": drink.name, "category": category, "good": good},
                steps=(StepDraft(StepAction.PREPARE, actor=people.id),),
            )
            return


async def derive_drinks(ctx: TickContext, people: EntityRow, tally: DrinkTally) -> None:
    table = ctx.rules.drink
    for holding_row, drink in await holdings_of(ctx.session, people.id):
        if drink.origin_node_id == people.id or holding_row.strength < table.derive_strength:
            continue
        mine = await ctx.session.scalar(select(DrinkKindRow.id).where(DrinkKindRow.derived_from_id == drink.id, DrinkKindRow.origin_node_id == people.id))
        if mine is not None or not ctx.rng(f"drink.derive.{people.id}.{drink.id}.{ctx.epoch}").chance(table.derive_pct):
            continue
        made = await found_drink(ctx, people, drink.category, parent=drink)
        tally.derived += 1
        await record(
            ctx,
            "drink.derived",
            roles={IncidentRole.MAKER: people.id, IncidentRole.ORIGIN: drink.origin_node_id},
            facts={"drink": made.name, "from": drink.name, "category": drink.category},
            steps=(StepDraft(StepAction.COPY, actor=people.id),),
        )


async def drink_in(ctx: TickContext, people: EntityRow, tally: DrinkTally) -> None:
    table = ctx.rules.drink
    drinks = await holdings_of(ctx.session, people.id)
    if not drinks:
        return
    strength = max(round_half_up(drink.strength * row.strength / PERCENT * LEGAL_CRIME[drink.legality]) for row, drink in drinks)
    stimulation = max((drink.stimulation + drink.nourishment // 2) * row.strength // PERCENT for row, drink in drinks)
    stored = any(drink.keeps >= ctx.rules.cuisine.ration_keeping for _, drink in drinks)
    dependence = 0 if stored else max(drink.dependence * row.strength // PERCENT for row, drink in drinks)
    for home in sorted(await homes_of(ctx.session, people)):
        town = await ctx.session.get(EntityRow, home)
        if town is None or town.entity_type is not EntityType.SETTLEMENT or held(home):
            continue
        profile = await ctx.session.get(SettlementProfileRow, home)
        if profile is not None and "crime" not in profile.locked:
            profile.crime = clamp_int(profile.crime + round_half_up(strength * table.strength_crime_pct / PERCENT), 0, PERCENT)
        if stimulation:
            shift_stat(town, "prosperity", round_half_up(stimulation * table.stimulation_pct / PERCENT), low=0, high=PERCENT)
        if dependence and profile is not None and "unrest" not in profile.locked and await holding(ctx.session, home, CommodityKind.BREW_BASE) == 0:
            profile.unrest = clamp_int(profile.unrest + round_half_up(dependence * table.dependence_unrest_pct / PERCENT), 0, PERCENT)
        for row, drink in drinks:
            keep_role(ctx, town, profile, drink.role, row.strength)
        tally.drunk += 1


def keep_role(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow | None, role: DrinkRole, strength: int) -> None:
    effect = DRINK_ROLES[role]
    if effect.rule is None or effect.bonds:
        return
    amount = round_half_up(getattr(ctx.rules.drink, effect.rule) * strength / PERCENT) * (-1 if effect.lowers else 1)
    if not amount:
        return
    if effect.town_stat is not None:
        shift_stat(town, effect.town_stat, amount, low=0, high=PERCENT)
    if effect.profile_field is not None and profile is not None and effect.profile_field not in profile.locked:
        setattr(profile, effect.profile_field, clamp_int(getattr(profile, effect.profile_field) + amount, 0, PERCENT))


async def share_hospitality(ctx: TickContext, tally: DrinkTally) -> None:
    rows = await ctx.session.execute(
        select(KindHoldingRow.holder_node_id, KindHoldingRow.kind_id, KindHoldingRow.stance, DrinkKindRow.role)
        .join(DrinkKindRow, DrinkKindRow.id == KindHoldingRow.kind_id)
        .join(EntityRow, EntityRow.id == KindHoldingRow.holder_node_id)
        .where(KindHoldingRow.concept == KindConcept.DRINK, DrinkKindRow.role.in_(sorted(BONDING_ROLES)), EntityRow.entity_type == EntityType.PEOPLE)
        .order_by(KindHoldingRow.kind_id, KindHoldingRow.holder_node_id)
    )
    sharers: dict[tuple[int, DrinkRole], list[int]] = {}
    for holder_id, kind_id, stance, role in rows.all():
        if stance in CARRIED:
            sharers.setdefault((kind_id, role), []).append(holder_id)
    for (_, role), holders in sharers.items():
        effect = DRINK_ROLES[role]
        regard = getattr(ctx.rules.drink, effect.rule) if effect.rule is not None else 0
        if not regard or effect.memory is None:
            continue
        for index, first in enumerate(holders):
            for second in holders[index + 1 :]:
                if held(first, second):
                    continue
                await change_relation(ctx, first, second, regard, effect.memory, note=effect.note)
                tally.shared += 1


async def keep_drinks(ctx: TickContext) -> DrinkTally:
    tally = DrinkTally()
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        await first_drink(ctx, people, tally)
        await derive_drinks(ctx, people, tally)
        await drink_in(ctx, people, tally)
    await share_hospitality(ctx, tally)
    await ctx.session.flush()
    return tally
