from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.tongues import POLICIES
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import LanguageStandingRow, SpeakerCohortRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.tongues import LanguagePolicyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.tongues import LanguagePolicy, LanguageStage
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.language import learn_second
from aerona.engine.primitives.folk import homes_for
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, has_flag, spoken_language
from aerona.engine.recording.record import record as record_incident
from aerona.engine.tongues.stages import revived_tongue

HOLDER_TYPES = frozenset({EntityType.POLITY, EntityType.CULT, EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION})


@dataclass
class PolicyTally:
    set: int = 0
    taught: int = 0
    suppressed: int = 0
    revived: int = 0
    protected: int = 0
    standardised: int = 0


async def communities_under(ctx: TickContext, holder_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    for place_id in sorted(await homes_for(ctx.session, [holder_id]) | {holder_id}):
        place = await ctx.session.get(EntityRow, place_id)
        if place is not None and place.entity_type in COMMUNITY_TYPES and not held(place.id):
            found.append(place)
    return found


async def set_policy(ctx: TickContext, holder_id: int, language_id: int, policy: LanguagePolicy, strength: int) -> LanguagePolicyRow:
    row = await ctx.session.get(LanguagePolicyRow, (holder_id, language_id, policy))
    if row is None:
        row = LanguagePolicyRow(holder_entity_id=holder_id, language_entity_id=language_id, policy=policy, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "strength" not in row.locked:
        row.strength = clamp_int(strength, 0, PERCENT)
    await ctx.session.flush()
    return row


async def choose_official(ctx: TickContext, polity: EntityRow, tally: PolicyTally) -> LanguagePolicyRow | None:
    existing = await ctx.session.scalar(
        select(LanguagePolicyRow).where(LanguagePolicyRow.holder_entity_id == polity.id, LanguagePolicyRow.policy == LanguagePolicy.OFFICIAL).limit(1)
    )
    if existing is not None or not ctx.rng(f"policy.official.{polity.id}.{ctx.epoch}").chance(ctx.rules.language_policy.official_pct):
        return None
    tongues: Counter[int] = Counter()
    for community in await communities_under(ctx, polity.id):
        tongue = await spoken_language(ctx.session, community.id)
        if tongue is not None:
            tongues[tongue.id] += 1
    if not tongues:
        return None
    language_id = max(sorted(tongues), key=lambda item: tongues[item])
    row = await set_policy(ctx, polity.id, language_id, LanguagePolicy.OFFICIAL, PERCENT // 2)
    tally.set += 1
    await record_incident(ctx, "tongues.official", roles={IncidentRole.AUTHORITY: polity.id, IncidentRole.SUBJECT: language_id})
    return row


async def teaching_gain(ctx: TickContext, row: LanguagePolicyRow) -> int:
    profile = await ctx.session.get(LanguageProfileRow, row.language_entity_id)
    if profile is not None and profile.stage is LanguageStage.CONSTRUCTED:
        return ctx.rules.tongues.constructed_spread_pct
    return ctx.rules.language_policy.official_gain


async def shield(ctx: TickContext, community: EntityRow, row: LanguagePolicyRow, weight: float) -> None:
    table = ctx.rules.tongues
    native = await ctx.session.get(SpeakerCohortRow, (community.id, row.language_entity_id, SpeakerKind.NATIVE))
    if native is not None and "share" not in native.locked and native.share < table.protected_floor:
        native.share = table.protected_floor
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest - round_half_up(table.protected_grievance_cut * weight), 0, PERCENT)


async def standardise(ctx: TickContext, row: LanguagePolicyRow, weight: float) -> None:
    standing = await ctx.session.get(LanguageStandingRow, row.language_entity_id)
    if standing is not None and "standardisation" not in standing.locked:
        standing.standardisation = clamp_int(standing.standardisation + round_half_up(ctx.rules.tongues.standard_gain * weight), 0, PERCENT)


async def press(ctx: TickContext, row: LanguagePolicyRow, tally: PolicyTally) -> None:
    table = ctx.rules.language_policy
    weight = row.strength / PERCENT
    spec = POLICIES[row.policy]
    if spec.standardises:
        await standardise(ctx, row, weight)
        tally.standardised += 1
    for community in await communities_under(ctx, row.holder_entity_id):
        native = await spoken_language(ctx.session, community.id)
        speaks_it = native is not None and native.id == row.language_entity_id
        if row.policy is LanguagePolicy.OFFICIAL and not speaks_it:
            await learn_second(ctx, community.id, row.language_entity_id, round_half_up(await teaching_gain(ctx, row) * weight))
            tally.taught += 1
        elif spec.shields and speaks_it:
            await shield(ctx, community, row, weight)
            tally.protected += 1
        elif spec.standardises and not speaks_it:
            await learn_second(ctx, community.id, row.language_entity_id, round_half_up(await teaching_gain(ctx, row) * weight / 2))
            tally.taught += 1
        elif row.policy is LanguagePolicy.LITURGICAL:
            await liturgy(ctx, community.id, row.language_entity_id, round_half_up(table.official_gain * weight))
        elif row.policy is LanguagePolicy.REVIVAL and not speaks_it:
            await learn_second(ctx, community.id, row.language_entity_id, round_half_up(table.revival_gain * weight))
            tally.taught += 1
        elif row.policy is LanguagePolicy.SUPPRESSED:
            await suppress(ctx, community, row, speaks_it, weight)
            tally.suppressed += 1


async def liturgy(ctx: TickContext, community_id: int, language_id: int, gain: int) -> None:
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, SpeakerKind.LITURGICAL))
    if row is None:
        row = SpeakerCohortRow(
            community_entity_id=community_id, language_entity_id=language_id, kind=SpeakerKind.LITURGICAL, share=0, since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
    if "share" not in row.locked:
        row.share = clamp_int(row.share + gain, 0, PERCENT)


async def suppress(ctx: TickContext, community: EntityRow, row: LanguagePolicyRow, native: bool, weight: float) -> None:
    table = ctx.rules.language_policy
    second = await ctx.session.get(SpeakerCohortRow, (community.id, row.language_entity_id, SpeakerKind.SECOND))
    if second is not None and "share" not in second.locked:
        second.share = clamp_int(second.share - round_half_up(table.suppress_loss * weight), 0, PERCENT)
    if not native:
        return
    people = await people_of(ctx.session, community)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is not None and "cohesion" not in culture.locked and not held(culture.people_entity_id):
        culture.cohesion = clamp_int(culture.cohesion - round_half_up(table.suppress_cohesion * weight), 0, PERCENT)
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is not None and "unrest" not in town.locked:
        town.unrest = clamp_int(town.unrest + round_half_up(table.suppress_unrest * weight), 0, PERCENT)


async def revive(ctx: TickContext, row: LanguagePolicyRow, tally: PolicyTally) -> bool:
    language = await ctx.session.get(EntityRow, row.language_entity_id)
    if language is None or held(language.id) or not await has_flag(ctx.session, language.id, EntityFlag.DEAD_LANGUAGE):
        return False
    if not ctx.rng(f"policy.revive.{row.holder_entity_id}.{language.id}.{ctx.epoch}").chance(ctx.rules.language_policy.revival_pct * row.strength / PERCENT):
        return False
    homes = await communities_under(ctx, row.holder_entity_id)
    if not homes:
        return False
    restored = await revived_tongue(ctx, language, homes[0])
    if "language_entity_id" not in row.locked:
        await ctx.session.delete(row)
        await ctx.session.flush()
        await set_policy(ctx, row.holder_entity_id, restored.id, LanguagePolicy.REVIVAL, row.strength)
    tally.revived += 1
    await record_incident(
        ctx, "tongues.revived", roles={IncidentRole.SUBJECT: language.id, IncidentRole.LEARNER: homes[0].id, IncidentRole.AUTHORITY: row.holder_entity_id}
    )
    return True


async def minorities_under(ctx: TickContext, polity: EntityRow) -> list[int]:
    official = await ctx.session.scalar(
        select(LanguagePolicyRow.language_entity_id)
        .where(LanguagePolicyRow.holder_entity_id == polity.id, LanguagePolicyRow.policy == LanguagePolicy.OFFICIAL)
        .limit(1)
    )
    found: set[int] = set()
    for community in await communities_under(ctx, polity.id):
        tongue = await spoken_language(ctx.session, community.id)
        if tongue is not None and tongue.id != official:
            found.add(tongue.id)
    return sorted(found)


async def choose_shield(ctx: TickContext, polity: EntityRow, tally: PolicyTally) -> None:
    table = ctx.rules.tongues
    for language_id in await minorities_under(ctx, polity):
        if await ctx.session.get(LanguagePolicyRow, (polity.id, language_id, LanguagePolicy.PROTECTED)) is not None:
            continue
        if await ctx.session.get(LanguagePolicyRow, (polity.id, language_id, LanguagePolicy.SUPPRESSED)) is not None:
            continue
        if not ctx.rng(f"policy.protect.{polity.id}.{language_id}.{ctx.epoch}").chance(table.protect_pct):
            continue
        await set_policy(ctx, polity.id, language_id, LanguagePolicy.PROTECTED, PERCENT // 2)
        tally.set += 1
        await record_incident(
            ctx, "language.policy_set", roles={IncidentRole.AUTHORITY: polity.id, IncidentRole.SUBJECT: language_id}, facts={"policy": LanguagePolicy.PROTECTED}
        )
        return


async def choose_academy(ctx: TickContext, polity: EntityRow, tally: PolicyTally) -> None:
    official = await ctx.session.scalar(
        select(LanguagePolicyRow).where(LanguagePolicyRow.holder_entity_id == polity.id, LanguagePolicyRow.policy == LanguagePolicy.OFFICIAL).limit(1)
    )
    if official is None or await ctx.session.get(LanguagePolicyRow, (polity.id, official.language_entity_id, LanguagePolicy.STANDARDISED)) is not None:
        return
    standing = await ctx.session.get(LanguageStandingRow, official.language_entity_id)
    if standing is None or standing.prestige < ctx.rules.script_evolution.reform_standard:
        return
    if not ctx.rng(f"policy.academy.{polity.id}.{ctx.epoch}").chance(ctx.rules.language_policy.official_pct):
        return
    await set_policy(ctx, polity.id, official.language_entity_id, LanguagePolicy.STANDARDISED, PERCENT // 2)
    tally.set += 1
    await record_incident(
        ctx,
        "language.policy_set",
        roles={IncidentRole.AUTHORITY: polity.id, IncidentRole.SUBJECT: official.language_entity_id},
        facts={"policy": LanguagePolicy.STANDARDISED},
    )


async def keep_policies(ctx: TickContext, tally: PolicyTally) -> None:
    for polity in await canon(ctx.session, [EntityType.POLITY]):
        if not held(polity.id):
            await choose_official(ctx, polity, tally)
            await choose_shield(ctx, polity, tally)
            await choose_academy(ctx, polity, tally)
    for row in list(await ctx.session.scalars(select(LanguagePolicyRow).order_by(LanguagePolicyRow.holder_entity_id, LanguagePolicyRow.language_entity_id))):
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None or held(holder.id):
            continue
        await press(ctx, row, tally)
        if row.policy is LanguagePolicy.REVIVAL:
            await revive(ctx, row, tally)
    await ctx.session.flush()
