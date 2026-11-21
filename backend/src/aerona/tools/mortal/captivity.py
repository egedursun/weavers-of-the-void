from typing import Any

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.body import Capacity, HarmCause
from aerona.domain.enums.bond import KIN_BOND_KINDS, BondKind
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome, StepState
from aerona.domain.enums.war import CaptiveStatus, WarCause
from aerona.engine.body.book import effective, factor
from aerona.engine.body.hits import Harm
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.faith import patron_son
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import StepDraft
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import held_captive, release_captive
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import EscapeInput, RansomInput, RescueInput
from aerona.tools.mortal.support import STRENGTH_CHAIN, enemies, first_stat, near, same_region

PERCENT = 100
KIN_BONDS = (
    BondKind.PROTECTS,
    BondKind.COMPANION,
    *KIN_BOND_KINDS,
)
GUARD_CHAIN = ("defense", "strength", "martiality")
RANSOM_EVENT = "ransom"


async def _captor(call: MortalCall, row: CaptiveRow) -> EntityRow:
    captor = await call.session.get(EntityRow, row.captor_entity_id)
    if captor is None:
        fail(MortalResult.NOT_YOUR_CAPTIVE)
    return captor


async def escape(call: MortalCall, args: EscapeInput) -> str:
    tools = call.rules.mortal_tools
    row = await held_captive(call.session, call.me.id)
    if row is None:
        fail(MortalResult.NOT_CAPTIVE)
    captor = await _captor(call, row)
    default = tools.escape_default_stat
    raw = (
        await effective(call.session, call.me, "agility", default, rules=call.rules) / 2
        + await effective(call.session, call.me, "intellect", default, rules=call.rules) / tools.escape_intellect_divisor
        - stat_or(captor, "defense", tools.default_stat) / tools.escape_captor_defense_divisor
    )
    chance = max(tools.escape_min_pct, min(max(tools.escape_min_pct, tools.escape_max_pct), round(raw)))
    call.target(captor.id)
    if call.die(PERCENT, "escape") <= chance:
        await release_captive(call.tick, row, CaptiveStatus.ESCAPED)
        await call.record(
            "tools.mortal.escaped",
            roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OPPONENT: captor.id},
            facts={"chance": chance, "how": args.how},
            steps=(StepDraft(StepAction.FLEE, actor=call.me.id, target=captor.id, outcome=StepOutcome.ESCAPED, states=((call.me.id, StepState.FREED),)),),
        )
        return result(MortalResult.ESCAPED, chance=chance)
    await apply_hits(
        call.tick, call.me, Harm(tools.escape_caught_wound, HarmCause.ESCAPE, "died after a failed escape", source_node_id=captor.id), lethal=False
    )
    await call.record(
        "tools.mortal.escape_failed",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OPPONENT: captor.id},
        facts={"chance": chance, "wound": tools.escape_caught_wound},
        steps=(
            StepDraft(StepAction.FLEE, actor=call.me.id, target=captor.id, outcome=StepOutcome.FAILURE),
            StepDraft(
                StepAction.PURSUE,
                actor=captor.id,
                target=call.me.id,
                amount=tools.escape_caught_wound,
                unit=FactUnit.HP,
                outcome=StepOutcome.CAPTURED,
                states=((call.me.id, StepState.CAPTURED),),
            ),
        ),
    )
    return result(MortalResult.ESCAPE_FAILED, chance=chance)


async def is_my_captive(call: MortalCall, captive: EntityRow) -> bool:
    if await BondRepository(call.session).active_between(call.me.id, captive.id, KIN_BONDS):
        return True
    if await same_region(call, captive):
        return True
    mine, theirs = await patron_son(call.session, call.me), await patron_son(call.session, captive)
    return mine is not None and theirs is not None and mine.id == theirs.id


async def pay_ransom(call: MortalCall, args: RansomInput) -> str:
    tools = call.rules.mortal_tools
    captive = await call.session.get(EntityRow, args.captive_id)
    row = await held_captive(call.session, args.captive_id) if captive is not None else None
    if captive is None or row is None or not await is_my_captive(call, captive):
        fail(MortalResult.NOT_YOUR_CAPTIVE)
    if row.captor_entity_id == call.me.id:
        fail(MortalResult.OWN_CAPTIVE_RANSOM, name=captive.name)
    wealth, prosperity = await points_of(call.session, call.me), stat(call.me, "prosperity")
    rich = (wealth or 0) >= tools.ransom_min_wealth or (prosperity or 0) >= tools.ransom_min_wealth + tools.ransom_prosperity_extra
    if not rich:
        fail(MortalResult.NO_RANSOM_WEALTH)
    captor = await _captor(call, row)
    key = "wealth" if (wealth or 0) >= tools.ransom_min_wealth else "prosperity"
    if key == "wealth":
        await shift_points(call.session, call.me, -tools.ransom_amount)
    else:
        set_stats(call.me, prosperity=max(0, (prosperity or 0) - tools.ransom_amount))
    if add_prosperity(call.rules, captor, tools.ransom_amount) is None:
        await shift_points(call.session, captor, tools.ransom_amount)
    await release_captive(call.tick, row, CaptiveStatus.RANSOMED, tools.ransom_amount)
    await change_relation(call.tick, call.me.id, captor.id, tools.ransom_relation, MemoryKind.FREED_US, note=RANSOM_EVENT)
    await judged(call.tick, captor.id, call.me.id, ActKind.RANSOM, note=RANSOM_EVENT)
    call.target(captive.id)
    await call.record(
        "tools.mortal.ransomed",
        roles={IncidentRole.GIVER: call.me.id, IncidentRole.RECEIVER: captor.id, IncidentRole.SUBJECT: captive.id},
        facts={"ransom": tools.ransom_amount},
        steps=(
            StepDraft(StepAction.PAY, actor=call.me.id, target=captor.id, amount=tools.ransom_amount, unit=FactUnit.WEALTH_POINTS),
            StepDraft(StepAction.BUY_FREEDOM, actor=call.me.id, target=captive.id, outcome=StepOutcome.SUCCESS),
        ),
    )
    return result(MortalResult.RANSOMED, name=captive.name)


async def rescue_captive(call: MortalCall, args: RescueInput) -> str:
    tools = call.rules.mortal_tools
    captive = await call.session.get(EntityRow, args.captive_id)
    row = await held_captive(call.session, args.captive_id) if captive is not None else None
    if captive is None or row is None:
        fail(MortalResult.NO_CAPTIVE_TO_RESCUE)
    captor = await _captor(call, row)
    if not (await is_my_captive(call, captive) or await near(call, captor)):
        fail(MortalResult.NO_CAPTIVE_TO_RESCUE)
    if captor.id == call.me.id:
        fail(MortalResult.OWN_CAPTIVE_RAID, name=captive.name)
    mine = first_stat(call.me, STRENGTH_CHAIN, tools.default_stat) * await factor(call.session, call.me.id, Capacity.MELEE) + call.die(
        tools.rescue_die, "raiders"
    )
    theirs = first_stat(captor, GUARD_CHAIN, tools.default_stat) + call.die(tools.rescue_die, "guards")
    call.target(captive.id)
    if mine >= theirs:
        await release_captive(call.tick, row, CaptiveStatus.RESCUED)
        await call.record(
            "tools.mortal.rescued",
            roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: captive.id, IncidentRole.OPPONENT: captor.id},
            facts={"plan": args.plan, "strength": round(mine), "guard": round(theirs)},
            steps=(
                StepDraft(
                    StepAction.RESCUE,
                    actor=call.me.id,
                    target=captive.id,
                    amount=round(mine),
                    unit=FactUnit.STRENGTH,
                    outcome=StepOutcome.SUCCESS,
                    states=((captive.id, StepState.FREED),),
                ),
            ),
        )
        return result(MortalResult.RESCUED, name=captive.name, mine=mine, theirs=theirs)
    if not await enemies(call, call.me.id, captor.id):
        await BondRepository(call.session).connect(
            BondDraft(captor.id, call.me.id, BondKind.ENEMY, call.epoch, lines.RAID_BOND.format(captive=captive.name), war_cause=WarCause.GRUDGE)
        )
    await call.record(
        "tools.mortal.rescue_failed",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: captive.id, IncidentRole.OPPONENT: captor.id},
        facts={"plan": args.plan, "strength": round(mine), "guard": round(theirs)},
        steps=(StepDraft(StepAction.RESCUE, actor=call.me.id, target=captive.id, amount=round(mine), unit=FactUnit.STRENGTH, outcome=StepOutcome.FAILURE),),
    )
    return result(MortalResult.RESCUE_FAILED, mine=mine, theirs=theirs)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    standard = mortal_standard_action
    return [
        ToolSpec(MortalToolId.ESCAPE, mortal, EscapeInput, ToolMeta(ActionKind.ESCAPE, standard), escape),
        ToolSpec(MortalToolId.PAY_RANSOM, mortal, RansomInput, ToolMeta(ActionKind.PAY_RANSOM, standard), pay_ransom),
        ToolSpec(MortalToolId.RESCUE_CAPTIVE, mortal, RescueInput, ToolMeta(ActionKind.RESCUE_CAPTIVE, standard), rescue_captive),
    ]
