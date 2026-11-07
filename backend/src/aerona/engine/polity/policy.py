from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.policy import LAW_POLICY, MANDATE_POLICY
from aerona.constants.units import PERCENT
from aerona.db.tables.affairs import MandateRow, PolicyApprovalRow
from aerona.db.tables.polity import LawProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind, LegitimacyBasis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import MandateState
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import LawBook, enact
from aerona.engine.primitives.numbers import clamp_int, round_half_up

APPROVAL = "approval"
GOVERNMENT = "government"
RULE = "decision_rule"
PARAMS = "params"
REVOLUTION_TERMS: dict[str, int | str | bool] = {"decision_rule": DecisionRule.ASSEMBLY.value, "voters": "all", "estates_rights": False}


@dataclass
class PolicyTally:
    weighed: int = 0
    charters: int = 0
    revolutions: int = 0


def parts_for(laws: LawBook, realm: Realm, mandates: list[MandateRow]) -> dict[SocialClass, dict[str, int]]:
    parts: dict[SocialClass, dict[str, int]] = {social_class: {} for social_class in SocialClass}
    for law_id in laws.by_node.get(realm.entity.id, []):
        profile = laws.profiles.get(law_id)
        effect = LAW_POLICY.get(profile.kind) if profile is not None else None
        if profile is None or effect is None:
            continue
        for social_class, shift in effect(profile.params).items():
            parts[social_class][f"law:{profile.kind.value}"] = shift
    for mandate in mandates:
        for social_class, shift in MANDATE_POLICY[mandate.kind].items():
            key = f"mandate:{mandate.kind.value}"
            parts[social_class][key] = parts[social_class].get(key, 0) + shift
    return parts


async def weigh(ctx: TickContext, book: RealmBook, laws: LawBook, realm: Realm, tally: PolicyTally) -> None:
    mandates = list(
        await ctx.session.scalars(select(MandateRow).where(MandateRow.polity_entity_id == realm.entity.id, MandateRow.state == MandateState.ACTIVE))
    )
    parts = parts_for(laws, realm, mandates)
    drift = ctx.rules.affairs.policy_drift_pct
    societies = [
        society for member in book.members(realm) if not held(member.id) and (society := await ctx.session.get(CommunitySocietyRow, member.id)) is not None
    ]
    for social_class, items in parts.items():
        row = await ctx.session.get(PolicyApprovalRow, (realm.entity.id, social_class))
        if row is None:
            row = PolicyApprovalRow(polity_entity_id=realm.entity.id, social_class=social_class, locked=[])
            ctx.session.add(row)
        if APPROVAL not in row.locked:
            row.approval = clamp_int(sum(items.values()), -PERCENT, PERCENT)
            row.parts = dict(items)
        row.epoch = ctx.epoch
        nudge = round_half_up(row.approval * drift / PERCENT)
        if nudge:
            key = f"satisfaction_{social_class.value}"
            for society in societies:
                setattr(society, key, clamp_int(getattr(society, key) + nudge, 0, PERCENT))
    tally.weighed += 1


async def approval_of(ctx: TickContext, realm_id: int, social_class: SocialClass) -> int:
    row = await ctx.session.get(PolicyApprovalRow, (realm_id, social_class))
    return row.approval if row is not None else 0


def charter(laws: LawBook, realm: Realm, tally: PolicyTally) -> None:
    profile = laws.in_force(realm.entity.id, LawKind.CONSTITUTION)
    if profile is None:
        return
    government = profile.params.get(GOVERNMENT)
    rule = profile.params.get(RULE)
    changed = False
    if GOVERNMENT not in realm.profile.locked and isinstance(government, str) and government != realm.profile.government.value:
        realm.profile.government = GovernmentKind(government)
        changed = True
    if RULE not in realm.profile.locked and isinstance(rule, str) and rule != realm.profile.decision_rule.value:
        realm.profile.decision_rule = DecisionRule(rule)
        changed = True
    tally.charters += changed


async def revolution(ctx: TickContext, realm: Realm, laws: LawBook) -> bool:
    if held(realm.entity.id):
        return False
    current = laws.in_force(realm.entity.id, LawKind.CONSTITUTION)
    if current is not None:
        if PARAMS in (current.locked or []):
            return False
        current.params = {**current.params, **REVOLUTION_TERMS}
    else:
        law = await enact(
            ctx, realm.entity, LawKind.CONSTITUTION, {**REVOLUTION_TERMS, GOVERNMENT: GovernmentKind.REPUBLIC.value}, basis=LegitimacyBasis.COUNCIL
        )
        profile = await ctx.session.get(LawProfileRow, law.id)
        if profile is not None:
            laws.laws[law.id] = law
            laws.profiles[law.id] = profile
            laws.by_node.setdefault(realm.entity.id, []).append(law.id)
    await note(
        ctx,
        f"The people of {realm.entity.name} rose and wrote a new fundamental law, giving the vote to all.",
        key="affairs.revolution",
        ids=[realm.entity.id],
        kind=ChronicleKind.CIVILIZATION,
    )
    return True


async def tend_policy(ctx: TickContext, tally: PolicyTally) -> None:
    book = await RealmBook.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        charter(laws, realm, tally)
        await weigh(ctx, book, laws, realm, tally)
