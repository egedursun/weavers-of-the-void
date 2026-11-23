from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.conditions import FESTERING, OPEN_INJURY_STATES
from aerona.catalog.harm_kinds import FESTERING_STEPS, INJURIES, STEPS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.discovery import TheoryAdherentRow, TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import TreatmentStep
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.mind import SkillKind
from aerona.engine.body.strike import worn_layers
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.mind.book import skills_of
from aerona.rules.registry import Rules

S = TreatmentStep


@dataclass(frozen=True)
class Treatment:
    steps: tuple[TreatmentStep, ...] = ()
    misdiagnosed: bool = False

    @property
    def changed(self) -> bool:
        return self.misdiagnosed or any(step is not S.DIAGNOSE for step in self.steps)


def step_level(rules: Rules, step: TreatmentStep) -> int:
    level = STEPS[step].level
    return level(rules.tissues) if level is not None else 0


def wanted_steps(row: InjuryRow, *, walking: bool, bleeds: bool = False) -> list[TreatmentStep]:
    steps: list[TreatmentStep] = []
    if row.bleeding > 0:
        steps.append(S.SUTURE)
    if row.state in FESTERING:
        steps.extend(FESTERING_STEPS)
    if bleeds:
        steps.append(S.BLEED)
    injury = INJURIES[row.kind]
    steps.extend(injury.care)
    if injury.broken and walking:
        steps.append(S.TRACTION)
    if walking:
        steps.append(S.CRUTCH)
    return [step for step in steps if step.value not in row.treatments]


def diagnosis_chance(rules: Rules, skill: int) -> float:
    table = rules.tissues
    return table.diagnose_floor_pct + (table.diagnose_pct - table.diagnose_floor_pct) * min(PERCENT, skill) / PERCENT


async def supplied(ctx: TickContext, community_id: int | None, step: TreatmentStep) -> bool:
    commodity = STEPS[step].supply
    if commodity is None:
        return True
    if community_id is None:
        return False
    return bool(await goods_of(ctx.session, ctx.epoch).take(community_id, commodity, 1, GoodsFlow.CONSUMPTION))


def stanch(row: InjuryRow, step: TreatmentStep) -> None:
    row.treatments = [*row.treatments, step.value]
    if STEPS[step].stanches:
        row.bleeding = 0


async def treat(ctx: TickContext, row: InjuryRow, *, skill: int, medicine: int, community_id: int | None, walking: bool, rng: SeededRandom) -> Treatment:
    if row.state not in OPEN_INJURY_STATES:
        return Treatment()
    done: list[TreatmentStep] = []
    if S.DIAGNOSE.value not in row.treatments:
        if not rng.chance(diagnosis_chance(ctx.rules, skill)):
            row.misdiagnosed = True
            return Treatment(misdiagnosed=True)
        row.misdiagnosed = False
        row.treatments = [*row.treatments, S.DIAGNOSE.value]
        done.append(S.DIAGNOSE)
    for step in wanted_steps(row, walking=walking, bleeds=await bloodletters(ctx, community_id)):
        chosen = step
        if medicine < step_level(ctx.rules, step) or not await supplied(ctx, community_id, step):
            if step is not S.SUTURE or medicine < step_level(ctx.rules, S.CAUTERISE):
                continue
            chosen = S.CAUTERISE
        stanch(row, chosen)
        done.append(chosen)
    return Treatment(tuple(done))


async def bloodletters(ctx: TickContext, community_id: int | None) -> bool:
    if community_id is None:
        return False
    found = await ctx.session.scalar(
        select(TheoryAdherentRow.theory_entity_id)
        .join(TheoryProfileRow, TheoryProfileRow.theory_entity_id == TheoryAdherentRow.theory_entity_id)
        .where(
            TheoryAdherentRow.adherent_entity_id == community_id,
            TheoryProfileRow.domain == TheoryDomain.MEDICINE,
            TheoryProfileRow.correctness < ctx.rules.treatment.bleeding_belief,
        )
        .limit(1)
    )
    return found is not None


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
