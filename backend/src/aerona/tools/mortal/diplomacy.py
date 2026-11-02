import math
from typing import Any

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.war import WarEnding
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
from aerona.tools.mortal.support import STRENGTH_CHAIN, enemies, fail_with_candidates, first_stat, headcount_key, is_community, near, require_target

PERCENT = 100
HEADCOUNT_FALLBACK = 100
LOG_FLOOR = 10
PERCENT_DIE = 100
UNION_KINDS = (DiplomacyKind.ALLIANCE, DiplomacyKind.MARRIAGE)
PARTIES = COMMUNITY_TYPES | {EntityType.MORTAL}


def strength_of(call: MortalCall, entity: EntityRow) -> float:
    tools = call.rules.mortal_tools
    key = headcount_key(entity)
    crowd = stat(entity, key) if key is not None else None
    return (
        first_stat(entity, STRENGTH_CHAIN, tools.diplomacy_default_strength)
        + math.log10(max(LOG_FLOOR, crowd or HEADCOUNT_FALLBACK)) * tools.diplomacy_population_mult
    )


async def _union(call: MortalCall, target: EntityRow, args: DiplomacyInput, roll: int) -> str:
    tools = call.rules.mortal_tools
    if roll <= tools.diplomacy_alliance_threshold:
        await BondRepository(call.session).connect(
            BondDraft(call.me.id, target.id, BondKind.ALLY, call.epoch, lines.UNION_BOND.format(kind=args.kind.value, terms=args.terms))
        )
        gain = tools.diplomacy_marriage_relation if args.kind is DiplomacyKind.MARRIAGE else tools.diplomacy_alliance_relation
        await change_relation(call.tick, call.me.id, target.id, gain, args.kind.value)
        return lines.DIPLOMACY_OUTCOMES["accepted"].format(target=target.name)
    await change_relation(call.tick, call.me.id, target.id, -tools.diplomacy_reject_relation, args.kind.value)
    return lines.DIPLOMACY_OUTCOMES["refused"].format(target=target.name)


async def _peace(call: MortalCall, target: EntityRow, args: DiplomacyInput, roll: int) -> str:
    tools = call.rules.mortal_tools
    if roll <= tools.diplomacy_peace_threshold:
        await settle_peace(call.tick, call.me.id, target.id, WarEnding.PEACE, args.terms[:KEY_MAX_LENGTH], apply_relation=False)
        await change_relation(call.tick, call.me.id, target.id, tools.diplomacy_peace_relation, args.kind.value)
        return lines.DIPLOMACY_OUTCOMES["peace"]
    return lines.DIPLOMACY_OUTCOMES["no_peace"]


async def _tribute(call: MortalCall, target: EntityRow, args: DiplomacyInput) -> str:
    tools = call.rules.mortal_tools
    if strength_of(call, call.me) < strength_of(call, target) * tools.tribute_superiority_pct / PERCENT:
        await BondRepository(call.session).connect(BondDraft(target.id, call.me.id, BondKind.ENEMY, call.epoch, lines.INSOLENT_TRIBUTE))
        await change_relation(call.tick, call.me.id, target.id, -tools.tribute_insolence_relation, lines.INSOLENT_TRIBUTE)
        return lines.DIPLOMACY_OUTCOMES["laughed"].format(target=target.name)
    for key in ("wealth", "prosperity"):
        paid = stat(target, key)
        if paid is not None:
            set_stats(target, **{key: max(0, paid - tools.tribute_payer_loss)})
    if add_prosperity(call.rules, call.me, tools.tribute_taker_gain) is None:
        wealth = stat(call.me, "wealth")
        if wealth is not None:
            set_stats(call.me, wealth=min(PERCENT, wealth + tools.tribute_taker_gain))
    await impose_tribute(call.tick, target, call.me, None, args.terms)
    await change_relation(call.tick, call.me.id, target.id, -tools.tribute_relation, args.kind.value)
    return lines.DIPLOMACY_OUTCOMES["tribute"].format(target=target.name)


async def diplomacy(call: MortalCall, args: DiplomacyInput) -> str:
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
    await call.chronicle(
        ChronicleKind.DIPLOMACY,
        lines.DIPLOMACY,
        entity_ids=[call.me.id, target.id],
        me=call.me.name,
        offer=args.kind.value,
        target=target.name,
        outcome=outcome,
    )
    return result(MortalResult.DIPLOMACY_DONE, outcome=outcome[:1].upper() + outcome[1:])


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.DIPLOMACY, AgentKind.MORTAL, DiplomacyInput, ToolMeta(ActionKind.DIPLOMACY, mortal_standard_action), diplomacy)]
