import math
from typing import Any

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind, DiplomacyOutcome, TreatyKind
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.polity.accords import Clause
from aerona.engine.polity.treaties import sign_derived
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import impose_tribute
from aerona.engine.services.war_resolution import settle_peace
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import DiplomacyInput, DiplomacyKind
from aerona.tools.mortal.support import STRENGTH_CHAIN, enemies, fail_with_candidates, first_stat, headcount_key, is_community, near, practised, require_target

PERCENT = 100
HEADCOUNT_FALLBACK = 100
LOG_FLOOR = 10
PERCENT_DIE = 100
UNION_KINDS = (DiplomacyKind.ALLIANCE, DiplomacyKind.MARRIAGE)
DIPLOMACY_MEMORIES = {DiplomacyKind.ALLIANCE: MemoryKind.ALLIED_WITH, DiplomacyKind.MARRIAGE: MemoryKind.MARRIED_INTO}
PARTIES = COMMUNITY_TYPES | {EntityType.MORTAL}


def strength_of(call: MortalCall, entity: EntityRow) -> float:
    tools = call.rules.mortal_tools
    key = headcount_key(entity)
    crowd = stat(entity, key) if key is not None else None
    return (
        first_stat(entity, STRENGTH_CHAIN, tools.diplomacy_default_strength)
        + math.log10(max(LOG_FLOOR, crowd or HEADCOUNT_FALLBACK)) * tools.diplomacy_population_mult
    )


async def _union(call: MortalCall, target: EntityRow, args: DiplomacyInput, roll: int) -> DiplomacyOutcome:
    tools = call.rules.mortal_tools
    if roll <= tools.diplomacy_alliance_threshold:
        clauses = [Clause(ClauseKind.CALL_TO_ARMS, call.me.id, target.id), Clause(ClauseKind.CALL_TO_ARMS, target.id, call.me.id)]
        await sign_derived(
            call.tick,
            TreatyKind.MARRIAGE_PACT if args.kind is DiplomacyKind.MARRIAGE else TreatyKind.ALLIANCE_DEFENSIVE,
            call.me.id,
            target.id,
            until=call.epoch + call.rules.treaties.alliance_epochs,
            clauses=clauses,
        )
        await BondRepository(call.session).connect(
            BondDraft(call.me.id, target.id, BondKind.ALLY, call.epoch, lines.UNION_BOND.format(kind=args.kind.value, terms=args.terms))
        )
        gain = tools.diplomacy_marriage_relation if args.kind is DiplomacyKind.MARRIAGE else tools.diplomacy_alliance_relation
        await change_relation(call.tick, call.me.id, target.id, gain, DIPLOMACY_MEMORIES.get(args.kind, MemoryKind.GOODWILL), note=spoken(args.kind))
        return DiplomacyOutcome.MARRIAGE_ACCEPTED if args.kind is DiplomacyKind.MARRIAGE else DiplomacyOutcome.ALLIANCE_ACCEPTED
    await change_relation(call.tick, call.me.id, target.id, -tools.diplomacy_reject_relation, MemoryKind.HUMILIATED_ME, note=spoken(args.kind))
    return DiplomacyOutcome.UNION_REFUSED


async def _peace(call: MortalCall, target: EntityRow, args: DiplomacyInput, roll: int) -> DiplomacyOutcome:
    tools = call.rules.mortal_tools
    if roll <= tools.diplomacy_peace_threshold:
        await settle_peace(call.tick, call.me.id, target.id, WarEnding.PEACE, args.terms[:KEY_MAX_LENGTH], apply_relation=False)
        await change_relation(call.tick, call.me.id, target.id, tools.diplomacy_peace_relation, MemoryKind.MADE_PEACE, note=spoken(args.kind))
        return DiplomacyOutcome.PEACE_MADE
    return DiplomacyOutcome.PEACE_REFUSED


async def _tribute(call: MortalCall, target: EntityRow, args: DiplomacyInput) -> DiplomacyOutcome:
    tools = call.rules.mortal_tools
    if strength_of(call, call.me) < strength_of(call, target) * tools.tribute_superiority_pct / PERCENT:
        await BondRepository(call.session).connect(
            BondDraft(target.id, call.me.id, BondKind.ENEMY, call.epoch, lines.INSOLENT_TRIBUTE, war_cause=WarCause.TRIBUTE_REVOLT)
        )
        await change_relation(call.tick, call.me.id, target.id, -tools.tribute_insolence_relation, MemoryKind.HUMILIATED_ME, note=lines.INSOLENT_TRIBUTE)
        return DiplomacyOutcome.TRIBUTE_SCORNED
    await shift_points(call.session, target, -min(await points_of(call.session, target), tools.tribute_payer_loss))
    prosperity = stat(target, "prosperity")
    if prosperity is not None:
        set_stats(target, prosperity=max(0, prosperity - tools.tribute_payer_loss))
    if add_prosperity(call.rules, call.me, tools.tribute_taker_gain) is None:
        await shift_points(call.session, call.me, tools.tribute_taker_gain)
    await impose_tribute(call.tick, target, call.me, None, args.terms)
    await change_relation(call.tick, call.me.id, target.id, -tools.tribute_relation, MemoryKind.DEMANDED_TRIBUTE, note=spoken(args.kind))
    return DiplomacyOutcome.TRIBUTE_AGREED


async def diplomacy(call: MortalCall, args: DiplomacyInput) -> str:
    await practised(call, (SkillKind.NEGOTIATION, SkillKind.ETIQUETTE), call.rules.skills.preach_xp)
    tools = call.rules.mortal_tools
    target = await require_target(call, args.target_id)
    if target.id == call.me.id or not (is_community(target) or target.entity_type is EntityType.MORTAL):
        await fail_with_candidates(call, MortalResult.INVALID_TARGET, PARTIES)
    if not await near(call, target):
        await fail_with_candidates(call, MortalResult.TOO_FAR, PARTIES)
    bonds = BondRepository(call.session)
    if args.kind in UNION_KINDS and await bonds.exists_between(call.me.id, target.id, BondKind.ALLY):
        fail(MortalResult.ALREADY_ALLIED, name=target.name)
    if args.kind is DiplomacyKind.TRIBUTE and await bonds.active_between(call.me.id, target.id, [BondKind.PAYS_TRIBUTE, BondKind.RULES]):
        fail(MortalResult.ALREADY_BOUND, name=target.name)
    hostile = await enemies(call, call.me.id, target.id)
    if args.kind in UNION_KINDS and hostile:
        fail(MortalResult.NO_ALLIANCE_WITH_ENEMY)
    if args.kind is DiplomacyKind.PEACE and not hostile:
        fail(MortalResult.NOT_ENEMIES)
    current = await relation(call.session, call.rules, call.me.id, target.id) if is_community(target) else 0
    roll = call.die(PERCENT_DIE, "diplomacy") - round(current / tools.diplomacy_relation_divisor)
    call.target(target.id)
    if args.kind in UNION_KINDS:
        outcome = await _union(call, target, args, roll)
    elif args.kind is DiplomacyKind.PEACE:
        outcome = await _peace(call, target, args, roll)
    else:
        outcome = await _tribute(call, target, args)
    await call.record(f"tools.mortal.diplomacy_{outcome.value}", roles={IncidentRole.ENVOY: call.me.id, IncidentRole.TARGET: target.id}, facts={"roll": roll})
    told = lines.DIPLOMACY_OUTCOMES[outcome.value].format(target=target.name)
    return result(MortalResult.DIPLOMACY_DONE, outcome=told[:1].upper() + told[1:])


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.DIPLOMACY, AgentKind.MORTAL, DiplomacyInput, ToolMeta(ActionKind.DIPLOMACY, mortal_standard_action), diplomacy)]
