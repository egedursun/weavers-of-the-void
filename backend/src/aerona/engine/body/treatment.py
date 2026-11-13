from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import OPEN_INJURY_STATES, InjuryKind, TreatmentStep
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.mind import SkillKind
from aerona.engine.body.strike import worn_layers
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.mind.book import skills_of
from aerona.rules.registry import Rules

S = TreatmentStep
OPEN_WOUNDS = frozenset(
    {
        InjuryKind.CUT,
        InjuryKind.DEEP_CUT,
        InjuryKind.PUNCTURE,
        InjuryKind.BITE,
        InjuryKind.BURN,
        InjuryKind.GUNSHOT,
        InjuryKind.SHRAPNEL,
        InjuryKind.CHEMICAL_BURN,
        InjuryKind.ELECTRICAL_BURN,
    }
)
BROKEN = frozenset({InjuryKind.FRACTURE, InjuryKind.CRUSH})
SUPPLIES: dict[TreatmentStep, CommodityKind] = {
    S.CLEAN: CommodityKind.MEDICINE,
    S.SUTURE: CommodityKind.CLOTH,
    S.DRESS: CommodityKind.CLOTH,
    S.SPLINT: CommodityKind.TIMBER,
    S.CRUTCH: CommodityKind.TIMBER,
}


def step_level(rules: Rules, step: TreatmentStep) -> int:
    table = rules.tissues
    return {
        S.SUTURE: table.suture_level,
        S.SET_BONE: table.set_bone_level,
        S.SPLINT: table.set_bone_level,
        S.AMPUTATE: table.amputate_level,
        S.CAUTERISE: table.cauterise_level,
        S.TRACTION: table.traction_level,
    }.get(step, 0)


def wanted_steps(row: InjuryRow, *, walking: bool) -> list[TreatmentStep]:
    steps: list[TreatmentStep] = []
    if row.bleeding > 0:
        steps.append(S.SUTURE)
    if row.kind in OPEN_WOUNDS:
        steps.extend((S.CLEAN, S.DRESS))
    if row.kind in BROKEN:
        steps.extend((S.SET_BONE, S.SPLINT))
        if walking:
            steps.append(S.TRACTION)
    if walking:
        steps.append(S.CRUTCH)
    return [step for step in steps if step.value not in row.treatments]


def diagnosis_chance(rules: Rules, skill: int) -> float:
    table = rules.tissues
    return table.diagnose_floor_pct + (table.diagnose_pct - table.diagnose_floor_pct) * min(PERCENT, skill) / PERCENT


async def supplied(ctx: TickContext, community_id: int | None, step: TreatmentStep) -> bool:
    commodity = SUPPLIES.get(step)
    if commodity is None:
        return True
    if community_id is None:
        return False
    return bool(await goods_of(ctx.session, ctx.epoch).take(community_id, commodity, 1, GoodsFlow.CONSUMPTION))


def stanch(row: InjuryRow, step: TreatmentStep) -> None:
    row.treatments = [*row.treatments, step.value]
    if step in (S.SUTURE, S.CAUTERISE):
        row.bleeding = 0


async def treat(ctx: TickContext, row: InjuryRow, *, skill: int, medicine: int, community_id: int | None, walking: bool, rng: SeededRandom) -> bool:
    if row.state not in OPEN_INJURY_STATES:
        return False
    if S.DIAGNOSE.value not in row.treatments:
        if not rng.chance(diagnosis_chance(ctx.rules, skill)):
            row.misdiagnosed = True
            return True
        row.misdiagnosed = False
        row.treatments = [*row.treatments, S.DIAGNOSE.value]
    changed = False
    for step in wanted_steps(row, walking=walking):
        chosen = step
        if medicine < step_level(ctx.rules, step) or not await supplied(ctx, community_id, step):
            if step is not S.SUTURE or medicine < step_level(ctx.rules, S.CAUTERISE):
                continue
            chosen = S.CAUTERISE
        stanch(row, chosen)
        changed = True
    return changed


async def first_aid(ctx: TickContext, bearer: EntityRow) -> int:
    rows = await skills_of(ctx.session, bearer.id)
    found = rows.get(SkillKind.MEDICINE)
    return found.level if found is not None else 0


async def bleed(ctx: TickContext, bearer: EntityRow, body: BodyRow, rows: list[InjuryRow], *, healer: bool, rng: SeededRandom) -> int:
    table = ctx.rules.tissues
    aid = await first_aid(ctx, bearer)
    lost = 0
    for row in rows:
        if row.bleeding <= 0 or row.state not in OPEN_INJURY_STATES:
            continue
        chance = table.bind_healer_pct if healer else table.bind_first_aid_pct * aid / PERCENT
        if rng.chance(chance):
            row.bleeding = 0
            continue
        lost += row.bleeding
    if "blood" not in body.locked:
        body.blood = max(0, body.blood - lost)
    return lost


async def exert(ctx: TickContext, bearer: EntityRow) -> int:
    body = await ctx.session.get(BodyRow, bearer.id)
    if body is None or "exertion" in body.locked:
        return 0
    layers = await worn_layers(ctx.session, bearer.id)
    density = sum(layer.props.density for layer in layers) / len(layers) if layers else 0
    cost = round(ctx.rules.tissues.exertion_per_fight * (1 + density * ctx.rules.tissues.armour_exertion_pct / PERCENT / PERCENT))
    body.exertion = min(PERCENT, body.exertion + cost)
    return cost


def regain_blood(rules: Rules, body: BodyRow, bleeding: bool) -> None:
    if not bleeding and "blood" not in body.locked:
        body.blood = min(PERCENT, body.blood + rules.tissues.blood_regen)
    if "exertion" not in body.locked:
        body.exertion = max(0, body.exertion - rules.tissues.exertion_recovery)
